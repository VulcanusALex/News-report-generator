from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .fetch import fetch_json, fetch_text, fetch_web_search
from .models import DailyBrief, NewsItem, StrikeItem, WeatherInfo
from .parse import (
    is_today_or_recent,
    parse_json_news_generic,
    parse_rss_news,
    parse_strikes_italy_mit_html,
    parse_strikes_italy_mit_rss,
    parse_strikes_italy_transport,
    parse_web_search_results,
)
from .render import render_markdown
from .storage import Store


WEATHER_CODE_MAP = {
    0: "晴",
    1: "大部晴朗",
    2: "局部多云",
    3: "阴",
    45: "雾",
    48: "冻雾",
    51: "小毛毛雨",
    53: "毛毛雨",
    55: "较强毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    80: "阵雨",
    95: "雷暴",
}

NEWS_PARSERS = {
    "generic_json_news_v1": parse_json_news_generic,
}

STRIKE_PARSERS = {
    "italy_transport_strikes_v1": parse_strikes_italy_transport,
}

STRIKE_RSS_PARSERS = {
    "italy_mit_strikes_rss_v1": parse_strikes_italy_mit_rss,
}

STRIKE_HTML_PARSERS = {
    "italy_mit_strikes_html_v1": parse_strikes_italy_mit_html,
}


class BriefingPipeline:
    def __init__(self, cfg: dict[str, Any], db_path: str | Path = "data/briefing.db"):
        self.cfg = cfg
        self.tz = ZoneInfo(cfg.get("timezone", "Europe/Rome"))
        self.city = cfg.get("city", "Milan")
        self.store = Store(db_path)

    def generate(
        self,
        report_day: date,
        dry_run: bool = False,
        layout: str | None = None,
        section_order: list[str] | None = None,
    ) -> tuple[DailyBrief, str, dict[str, Any]]:
        weather = self._fetch_weather(report_day)
        strikes = self._fetch_strikes(report_day)

        italian_news = self._collect_section("italian_news", report_day)
        world_news = self._collect_section("world_news", report_day)
        ai_news = self._collect_section("ai_news", report_day)
        events = self._collect_section("milan_events", report_day)

        brief = DailyBrief(
            report_date=report_day.isoformat(),
            weather=weather,
            strikes=strikes,
            italian_news=italian_news,
            world_news=world_news,
            ai_news=ai_news,
            milan_events=events,
        )
        render_cfg = self.cfg.get("render", {})
        effective_layout = layout or render_cfg.get("default_layout", "classic")
        effective_order = section_order or render_cfg.get("section_order")
        markdown = render_markdown(brief, layout=effective_layout, section_order=effective_order)
        meta = {
            "counts": {
                "italian_news": len(italian_news),
                "world_news": len(world_news),
                "ai_news": len(ai_news),
                "milan_events": len(events),
                "strikes": len(strikes),
            },
            "render": {
                "layout": effective_layout,
                "section_order": effective_order,
            },
        }
        if not dry_run:
            output_dir = Path("output")
            output_dir.mkdir(parents=True, exist_ok=True)
            run_dir = output_dir / "runs"
            run_dir.mkdir(parents=True, exist_ok=True)
            md_path = output_dir / f"{brief.report_date}.md"
            md_path.write_text(markdown, encoding="utf-8")

            run_payload = _brief_to_dict(brief)
            run_json_path = run_dir / f"{brief.report_date}.json"
            run_json_path.write_text(json.dumps(run_payload, ensure_ascii=False, indent=2), encoding="utf-8")

            run_id = self.store.create_run(brief.report_date, str(md_path), meta=meta)
            for item in italian_news + world_news + ai_news + events:
                self.store.store_item(run_id, brief.report_date, item)
            meta["output_markdown"] = str(md_path)
            meta["output_json"] = str(run_json_path)
        return brief, markdown, meta

    def close(self) -> None:
        self.store.close()

    def _fetch_weather(self, report_day: date) -> WeatherInfo:
        w_cfg = self.cfg.get("weather", {})
        lat = w_cfg.get("latitude", 45.4642)
        lon = w_cfg.get("longitude", 9.19)
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
            f"&timezone={self.cfg.get('timezone', 'Europe/Rome')}"
        )
        payload = fetch_json(url)
        daily = payload.get("daily", {})
        dates = daily.get("time", [])
        idx = 0
        try:
            idx = dates.index(report_day.isoformat())
        except ValueError:
            idx = 0
        weather_code = _safe_pick(daily.get("weathercode"), idx)
        return WeatherInfo(
            city=self.city,
            date_label=report_day.isoformat(),
            temperature_min=_safe_pick(daily.get("temperature_2m_min"), idx),
            temperature_max=_safe_pick(daily.get("temperature_2m_max"), idx),
            condition=WEATHER_CODE_MAP.get(weather_code, "未知"),
            precipitation_probability_max=_safe_pick(daily.get("precipitation_probability_max"), idx),
        )

    def _fetch_strikes(self, report_day: date) -> list[StrikeItem]:
        s_cfg = self.cfg.get("strikes", {})
        lookahead_days = int(s_cfg.get("lookahead_days", 20))
        sources = s_cfg.get("sources", [])
        all_items: list[StrikeItem] = []
        for src in sources:
            src_type = src.get("type")
            url = (src.get("url") or "").strip()
            if not url:
                continue
            try:
                if src_type == "json":
                    payload = fetch_json(url)
                    parser_name = src.get("parser", "italy_transport_strikes_v1")
                    parser = STRIKE_PARSERS.get(parser_name)
                    if parser:
                        all_items.extend(parser(payload, self.cfg.get("timezone", "Europe/Rome")))
                elif src_type == "rss":
                    parser_name = src.get("parser", "italy_mit_strikes_rss_v1")
                    parser = STRIKE_RSS_PARSERS.get(parser_name)
                    if parser:
                        all_items.extend(parser(url, self.cfg.get("timezone", "Europe/Rome")))
                elif src_type == "html":
                    page_html = fetch_text(url)
                    parser_name = src.get("parser", "italy_mit_strikes_html_v1")
                    parser = STRIKE_HTML_PARSERS.get(parser_name)
                    if parser:
                        all_items.extend(parser(page_html, self.cfg.get("timezone", "Europe/Rome")))
            except Exception:
                continue

        day_end = report_day + timedelta(days=lookahead_days)
        out: list[StrikeItem] = []
        for item in all_items:
            if item.start is None:
                continue
            item_day = item.start.astimezone(self.tz).date()
            city = (item.city or "").lower()
            is_milan = (
                (not city)
                or ("milan" in city)
                or ("milano" in city)
                or ("lombardia" in city)
                or ("italia" in city)
                or ("tutte" in city)
            )
            if is_milan and report_day <= item_day <= day_end:
                out.append(item)
        out.sort(key=lambda x: x.start or datetime.max.replace(tzinfo=self.tz))
        return out

    def _collect_section(self, section: str, report_day: date) -> list[NewsItem]:
        sec = self.cfg.get(section, {})
        count = int(sec.get("count", 5))
        only_today = bool(sec.get("only_today", False))
        fallback_days = int(sec.get("fallback_days", 2))
        sources = sec.get("sources", [])
        collected: list[NewsItem] = []
        for src in sources:
            src_type = src.get("type")
            src_name = src.get("name", "Unknown")
            url = (src.get("url") or "").strip()
            if not url:
                continue
            try:
                if src_type == "rss":
                    rows = parse_rss_news(section, src_name, url, self.cfg.get("timezone", "Europe/Rome"))
                elif src_type == "json":
                    payload = fetch_json(url)
                    parser_name = src.get("parser", "generic_json_news_v1")
                    parser = NEWS_PARSERS.get(parser_name)
                    rows = (
                        parser(section, src_name, payload, self.cfg.get("timezone", "Europe/Rome"))
                        if parser
                        else []
                    )
                elif src_type == "search":
                    # Web search: url field is used as the search query
                    search_query = url.strip()
                    count = src.get("count", 10)
                    country = src.get("country", "IT")
                    search_results = fetch_web_search(search_query, count=count, country=country)
                    rows = parse_web_search_results(
                        section, src_name, search_results, self.cfg.get("timezone", "Europe/Rome")
                    )
                else:
                    rows = []
            except Exception:
                rows = []

            for item in rows:
                if not is_today_or_recent(
                    item.published_at,
                    report_day=report_day,
                    timezone=self.cfg.get("timezone", "Europe/Rome"),
                    only_today=only_today,
                    fallback_days=fallback_days,
                ):
                    continue
                if self.store.has_seen(item):
                    continue
                collected.append(item)

        collected.sort(key=lambda x: x.published_at or datetime.min.replace(tzinfo=self.tz), reverse=True)
        return collected[:count]


def _safe_pick(arr: Any, idx: int) -> Any:
    if not isinstance(arr, list):
        return None
    if idx < 0 or idx >= len(arr):
        return None
    return arr[idx]


def _brief_to_dict(brief: DailyBrief) -> dict[str, Any]:
    def n(x: NewsItem) -> dict[str, Any]:
        return {
            "section": x.section,
            "title": x.title,
            "url": x.url,
            "source": x.source,
            "published_at": x.published_at.isoformat() if x.published_at else None,
            "summary": x.summary,
            "extra": x.extra,
        }

    def s(x: StrikeItem) -> dict[str, Any]:
        return {
            "title": x.title,
            "start": x.start.isoformat() if x.start else None,
            "end": x.end.isoformat() if x.end else None,
            "impact_window": x.impact_window,
            "city": x.city,
        }

    return {
        "report_date": brief.report_date,
        "weather": {
            "city": brief.weather.city,
            "date_label": brief.weather.date_label,
            "temperature_min": brief.weather.temperature_min,
            "temperature_max": brief.weather.temperature_max,
            "condition": brief.weather.condition,
            "precipitation_probability_max": brief.weather.precipitation_probability_max,
        },
        "strikes": [s(x) for x in brief.strikes],
        "italian_news": [n(x) for x in brief.italian_news],
        "world_news": [n(x) for x in brief.world_news],
        "ai_news": [n(x) for x in brief.ai_news],
        "milan_events": [n(x) for x in brief.milan_events],
    }
