from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class NewsItem:
    section: str
    title: str
    url: str
    source: str
    published_at: datetime | None = None
    summary: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class WeatherInfo:
    city: str
    date_label: str
    temperature_min: float | None
    temperature_max: float | None
    condition: str | None
    precipitation_probability_max: float | None


@dataclass
class StrikeItem:
    title: str
    start: datetime | None
    end: datetime | None
    impact_window: str | None
    city: str | None = None


@dataclass
class DailyBrief:
    report_date: str
    weather: WeatherInfo
    strikes: list[StrikeItem]
    italian_news: list[NewsItem]
    world_news: list[NewsItem]
    ai_news: list[NewsItem]
    milan_events: list[NewsItem]
