from __future__ import annotations

from datetime import datetime
from typing import Callable

from .models import DailyBrief, NewsItem, StrikeItem

SECTION_LABELS = {
    "weather": "米兰天气",
    "strikes": "未来 20 天米兰罢工信息",
    "italian_news": "意大利传统媒体（当日）",
    "world_news": "世界新闻（知名媒体）",
    "ai_news": "🤖 AI 研究动态",
    "milan_events": "米兰近期活动",
}


def render_markdown(
    brief: DailyBrief,
    layout: str = "classic",
    section_order: list[str] | None = None,
) -> str:
    order = section_order or ["weather", "strikes", "italian_news", "world_news", "ai_news", "milan_events"]
    fn = LAYOUT_RENDERERS.get(layout, _render_layout_classic)
    return fn(brief, order)


def _render_layout_classic(brief: DailyBrief, order: list[str]) -> str:
    lines: list[str] = [f"# 米兰新闻简报 | {brief.report_date}", ""]
    for idx, section in enumerate(order, start=1):
        lines.append(_render_section(section, brief, numbered=idx))
        lines.append("")
    lines.append(f"_生成时间: {datetime.now().isoformat(timespec='seconds')}_")
    return "\n".join(lines)


def _render_layout_editorial(brief: DailyBrief, order: list[str]) -> str:
    lines: list[str] = [
        f"# Milan Briefing Desk | {brief.report_date}",
        "",
        "## 今日导读",
        f"- 罢工条数: {len(brief.strikes)}",
        f"- 意大利头条: {len(brief.italian_news)}",
        f"- 世界头条: {len(brief.world_news)}",
        f"- AI 头条: {len(brief.ai_news)}",
        f"- 米兰活动: {len(brief.milan_events)}",
        "",
    ]
    for section in order:
        lines.append(_render_section(section, brief, numbered=None))
        lines.append("")
    lines.append(f"_生成时间: {datetime.now().isoformat(timespec='seconds')}_")
    return "\n".join(lines)


def _render_layout_brief(brief: DailyBrief, order: list[str]) -> str:
    lines: list[str] = [f"# 米兰简报 | {brief.report_date}", ""]
    for section in order:
        lines.append(_render_section(section, brief, numbered=None, compact=True))
        lines.append("")
    lines.append(f"_生成时间: {datetime.now().isoformat(timespec='seconds')}_")
    return "\n".join(lines)


def _render_section(section: str, brief: DailyBrief, numbered: int | None, compact: bool = False) -> str:
    title = SECTION_LABELS.get(section, section)
    if numbered is not None:
        title = f"{numbered}) {title}"

    if section == "weather":
        return _render_weather(brief, title=title)
    if section == "strikes":
        return _render_strikes(brief.strikes, title=title, compact=compact)
    if section == "italian_news":
        return _render_news_section(title, brief.italian_news, compact=compact)
    if section == "world_news":
        return _render_news_section(title, brief.world_news, compact=compact)
    if section == "ai_news":
        return _render_news_section(title, brief.ai_news, compact=compact)
    if section == "milan_events":
        return _render_news_section(title, brief.milan_events, compact=compact)
    return f"## {title}\n- 未知 section: {section}"


def _render_weather(brief: DailyBrief, title: str) -> str:
    w = brief.weather
    return (
        f"## {title}\n"
        f"- 日期: {w.date_label}\n"
        f"- 气温: {fmt_temp(w.temperature_min)} ~ {fmt_temp(w.temperature_max)}\n"
        f"- 天气: {w.condition or '未知'}\n"
        f"- 降雨概率(最大): {fmt_percent(w.precipitation_probability_max)}"
    )


def _render_strikes(strikes: list[StrikeItem], title: str, compact: bool = False) -> str:
    lines = [f"## {title}"]
    if not strikes:
        lines.append("- 未来 20 天暂无已确认罢工。")
        return "\n".join(lines)
    for i, s in enumerate(strikes, start=1):
        start = s.start.isoformat(timespec="minutes") if s.start else "未知"
        end = s.end.isoformat(timespec="minutes") if s.end else "未知"
        impact = s.impact_window or "未提供"
        city = s.city or "未标注城市"
        if compact:
            lines.append(f"- {i}. {s.title}（{start}~{end}，{city}）")
        else:
            lines.append(f"- {i}. {s.title} | 城市: {city} | 日期: {start} ~ {end} | 影响时段: {impact}")
    return "\n".join(lines)


def _render_news_section(title: str, items: list[NewsItem], compact: bool = False) -> str:
    lines = [f"## {title}"]
    if not items:
        lines.append("- 今日无可用新增条目。")
        return "\n".join(lines)
    for i, it in enumerate(items, start=1):
        pub = it.published_at.isoformat(timespec="minutes") if it.published_at else "时间未知"
        if compact:
            lines.append(f"- {i}. [{it.title}]({it.url})（{it.source}）")
        else:
            lines.append(f"- {i}. [{it.title}]({it.url})（{it.source}，{pub}）")
    return "\n".join(lines)


def fmt_temp(v: float | None) -> str:
    if v is None:
        return "未知"
    return f"{v:.1f}°C"


def fmt_percent(v: float | None) -> str:
    if v is None:
        return "未知"
    return f"{v:.0f}%"


LAYOUT_RENDERERS: dict[str, Callable[[DailyBrief, list[str]], str]] = {
    "classic": _render_layout_classic,
    "editorial": _render_layout_editorial,
    "brief": _render_layout_brief,
}
