from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from src.news_briefing.models import NewsItem
from src.news_briefing.storage import Store


class TestStorage(unittest.TestCase):
    def test_store_and_seen(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "briefing.db"
            store = Store(db)
            try:
                item = NewsItem(
                    section="world_news",
                    title="Example title",
                    url="https://example.com/world",
                    source="Example Source",
                    published_at=datetime(2026, 2, 23, 10, 0, tzinfo=timezone.utc),
                )
                self.assertFalse(store.has_seen(item))
                run_id = store.create_run("2026-02-23", "output/2026-02-23.md", {"x": 1})
                store.store_item(run_id, "2026-02-23", item)
                self.assertTrue(store.has_seen(item))
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
