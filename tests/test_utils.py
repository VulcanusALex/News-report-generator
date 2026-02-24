from __future__ import annotations

import unittest

from src.news_briefing.utils import dedupe_key


class TestUtils(unittest.TestCase):
    def test_dedupe_key_stable_and_normalized(self) -> None:
        a = dedupe_key("Hello ", "https://example.com/a", "BBC")
        b = dedupe_key("hello", "https://example.com/a", "bbc")
        c = dedupe_key("Different", "https://example.com/a", "bbc")
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)


if __name__ == "__main__":
    unittest.main()
