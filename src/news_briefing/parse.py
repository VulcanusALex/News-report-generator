from __future__ import annotations

import html
import re
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import feedparser
from dateutil import parser as dt_parser

from .models import NewsItem, StrikeItem
from .utils import dedupe_key


def parse_rss_news(section: str, source_name: str, url: str, tz_name: str) -> list[NewsItem]:
    feed = feedparser.parse(url)
    out: list[NewsItem] = []
    tz = ZoneInfo(tz_name)
    for entry in feed.entries:
        title = (entry.get("title") or "").strip()
        link = (entry.get("link") or "").strip()
        if not title or not link:
            continue
        published = _parse_entry_datetime(entry, tz)
        out.append(
            NewsItem(
                section=section,
                title=title,
                url=link,
                source=source_name,
                published_at=published,
                summary=(entry.get("summary") or "").strip() or None,
            )
        )
    return out


def parse_json_news_generic(section: str, source_name: str, payload: Any, tz_name: str) -> list[NewsItem]:
    tz = ZoneInfo(tz_name)
    rows: list[dict[str, Any]]
    if isinstance(payload, list):
        rows = [x for x in payload if isinstance(x, dict)]
    elif isinstance(payload, dict):
        candidates = payload.get("items") or payload.get("data") or payload.get("articles") or []
        rows = [x for x in candidates if isinstance(x, dict)]
    else:
        rows = []
    out: list[NewsItem] = []
    for row in rows:
        title = str(row.get("title", "")).strip()
        link = str(row.get("url", "")).strip()
        if not title or not link:
            continue
        published = _parse_datetime(row.get("published_at") or row.get("date"), tz)
        out.append(
            NewsItem(
                section=section,
                title=title,
                url=link,
                source=source_name,
                published_at=published,
                summary=(str(row.get("summary", "")).strip() or None),
            )
        )
    return out


def parse_strikes_italy_transport(payload: Any, tz_name: str) -> list[StrikeItem]:
    tz = ZoneInfo(tz_name)
    rows: list[dict[str, Any]]
    if isinstance(payload, list):
        rows = [x for x in payload if isinstance(x, dict)]
    elif isinstance(payload, dict):
        rows = [x for x in (payload.get("items") or payload.get("data") or []) if isinstance(x, dict)]
    else:
        rows = []
    out: list[StrikeItem] = []
    for row in rows:
        out.append(
            StrikeItem(
                title=str(row.get("title", "罢工")).strip() or "罢工",
                start=_parse_datetime(row.get("start"), tz),
                end=_parse_datetime(row.get("end"), tz),
                impact_window=(str(row.get("impact_window", "")).strip() or None),
                city=(str(row.get("city", "")).strip() or None),
            )
        )
    return out


def parse_strikes_italy_mit_rss(url: str, tz_name: str) -> list[StrikeItem]:
    feed = feedparser.parse(url)
    tz = ZoneInfo(tz_name)
    out: list[StrikeItem] = []
    for entry in feed.entries:
        text = " ".join(
            [
                str(entry.get("title", "")),
                str(entry.get("summary", "")),
                str(entry.get("description", "")),
            ]
        ).strip()
        if not text:
            continue
        start, end = _extract_dates_and_times(text, tz)
        impact = _extract_impact_window(text)
        city = _extract_city_hint(text)
        title = str(entry.get("title", "")).strip() or "罢工"
        out.append(StrikeItem(title=title, start=start, end=end, impact_window=impact, city=city))
    return out


def parse_strikes_italy_mit_html(page_html: str, tz_name: str) -> list[StrikeItem]:
    tz = ZoneInfo(tz_name)
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", page_html, flags=re.IGNORECASE | re.DOTALL)
    out: list[StrikeItem] = []
    for row in rows:
        cols = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, flags=re.IGNORECASE | re.DOTALL)
        clean_cols = [_clean_html(c) for c in cols]
        if len(clean_cols) < 12:
            continue
        # Expected MIT columns:
        # 0=inize,1=fine,2=sindacati,3=settore,4=categoria,5=modalita,6=rilevanza,7=note,8=data proclamazione,9=regione,10=provincia,11=data ricezione
        start = _parse_ddmmyyyy(clean_cols[0], tz)
        end = _parse_ddmmyyyy(clean_cols[1], tz)
        if start is None and end is None:
            continue
        title = f"{clean_cols[3]} | {clean_cols[4]}".strip(" |")
        region = clean_cols[9]
        province = clean_cols[10]
        city = "/".join([x for x in [region, province] if x]) or None
        impact = clean_cols[5] or None
        out.append(
            StrikeItem(
                title=title or "罢工",
                start=start,
                end=end,
                impact_window=impact,
                city=city,
            )
        )
    return out


def is_today_or_recent(
    dt: datetime | None,
    report_day: date,
    timezone: str,
    only_today: bool,
    fallback_days: int,
) -> bool:
    if dt is None:
        return not only_today
    local_day = dt.astimezone(ZoneInfo(timezone)).date()
    if only_today:
        return local_day == report_day
    return local_day >= report_day - timedelta(days=max(fallback_days, 0))


def _parse_entry_datetime(entry: Any, tz: ZoneInfo) -> datetime | None:
    value = entry.get("published") or entry.get("updated")
    return _parse_datetime(value, tz)


def _parse_datetime(value: Any, tz: ZoneInfo) -> datetime | None:
    if not value:
        return None
    try:
        dt = dt_parser.parse(str(value))
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt


def _clean_html(value: str) -> str:
    no_tags = re.sub(r"<[^>]+>", " ", value)
    normalized = re.sub(r"\s+", " ", no_tags).strip()
    return html.unescape(normalized)


def _parse_ddmmyyyy(value: str, tz: ZoneInfo) -> datetime | None:
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", value)
    if not m:
        return None
    day, month, year = map(int, m.groups())
    return datetime(year, month, day, 0, 0, tzinfo=tz)


def _extract_dates_and_times(text: str, tz: ZoneInfo) -> tuple[datetime | None, datetime | None]:
    date_matches = re.findall(r"(\d{2}/\d{2}/\d{4})", text)
    start = _parse_ddmmyyyy(date_matches[0], tz) if len(date_matches) >= 1 else None
    end = _parse_ddmmyyyy(date_matches[1], tz) if len(date_matches) >= 2 else start

    # Examples: "DALLE 13.00 ALLE 17.00", "DALLE 00:01 ALLE 24.00"
    tm = re.search(
        r"DALLE\s+(\d{1,2})[.:](\d{2})\s+ALLE\s+(\d{1,2})[.:](\d{2})",
        text,
        flags=re.IGNORECASE,
    )
    if tm and start:
        sh, sm, eh, em = map(int, tm.groups())
        sh = min(sh, 23)
        eh = min(eh, 23)
        start = start.replace(hour=sh, minute=sm)
        end = (end or start).replace(hour=eh, minute=em)
    return start, end


def _extract_impact_window(text: str) -> str | None:
    m = re.search(
        r"(\d{1,2}\s*ORE[^.;]*|INTERA\s+GIORNATA[^.;]*|DALLE\s+\d{1,2}[.:]\d{2}\s+ALLE\s+\d{1,2}[.:]\d{2})",
        text,
        flags=re.IGNORECASE,
    )
    if not m:
        return None
    return re.sub(r"\s+", " ", m.group(1)).strip()


def _extract_city_hint(text: str) -> str | None:
    low = text.lower()
    if "milano" in low or "milan" in low:
        return "Milano"
    if "lombardia" in low:
        return "Lombardia"
    if "italia" in low or "tutte" in low:
        return "Italia/Tutte"
    return None


def parse_web_search_results(section: str, source_name: str, results: list[dict[str, Any]], tz_name: str) -> list[NewsItem]:
    """
    Parse web search results into NewsItem list.
    
    Args:
        section: Section name (e.g., "milan_events")
        source_name: Source name for the search
        results: List of search result dicts with title, url, description
        tz_name: Timezone name
    
    Returns:
        List of NewsItem objects
    """
    tz = ZoneInfo(tz_name)
    out: list[NewsItem] = []
    
    for item in results:
        title = (item.get("title") or "").strip()
        url = (item.get("url") or "").strip()
        description = (item.get("description") or "").strip()
        
        if not title or not url:
            continue
        
        # Use current time as published_at (search results don't have timestamps)
        published = datetime.now(tz)
        
        out.append(
            NewsItem(
                section=section,
                title=title,
                url=url,
                source=source_name,
                published_at=published,
                summary=description or None,
            )
        )
    
    return out
