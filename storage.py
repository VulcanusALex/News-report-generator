from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from .models import NewsItem
from .utils import dedupe_key


SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  report_date TEXT NOT NULL,
  created_at TEXT NOT NULL,
  brief_path TEXT,
  meta_json TEXT
);

CREATE TABLE IF NOT EXISTS seen_items (
  item_key TEXT PRIMARY KEY,
  section TEXT NOT NULL,
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  source TEXT NOT NULL,
  published_at TEXT,
  first_seen_date TEXT NOT NULL,
  last_seen_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS run_items (
  run_id INTEGER NOT NULL,
  section TEXT NOT NULL,
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  source TEXT NOT NULL,
  published_at TEXT,
  item_key TEXT NOT NULL,
  FOREIGN KEY(run_id) REFERENCES runs(id)
);
"""


class Store:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def has_seen(self, item: NewsItem) -> bool:
        key = dedupe_key(item.title, item.url, item.source)
        row = self.conn.execute("SELECT 1 FROM seen_items WHERE item_key = ?", (key,)).fetchone()
        return row is not None

    def create_run(self, report_date: str, brief_path: str, meta: dict) -> int:
        cur = self.conn.execute(
            "INSERT INTO runs(report_date, created_at, brief_path, meta_json) VALUES (?, ?, ?, ?)",
            (report_date, datetime.utcnow().isoformat(), brief_path, json.dumps(meta, ensure_ascii=False)),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def store_item(self, run_id: int, report_date: str, item: NewsItem) -> None:
        key = dedupe_key(item.title, item.url, item.source)
        published_at = item.published_at.isoformat() if item.published_at else None
        self.conn.execute(
            """
            INSERT INTO seen_items(item_key, section, title, url, source, published_at, first_seen_date, last_seen_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(item_key) DO UPDATE SET last_seen_date = excluded.last_seen_date
            """,
            (
                key,
                item.section,
                item.title,
                item.url,
                item.source,
                published_at,
                report_date,
                report_date,
            ),
        )
        self.conn.execute(
            "INSERT INTO run_items(run_id, section, title, url, source, published_at, item_key) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (run_id, item.section, item.title, item.url, item.source, published_at, key),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
