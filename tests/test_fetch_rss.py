#!/usr/bin/env python3
"""Tests for fetch-rss.py."""

import datetime
import importlib.util
import unittest
import urllib.error
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
spec = importlib.util.spec_from_file_location("fetch_rss", SCRIPTS_DIR / "fetch-rss.py")
fetch_rss = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch_rss)


class TestRssConditionalCache(unittest.TestCase):
    def test_not_modified_reuses_cached_articles(self):
        source = {
            "id": "example-rss",
            "name": "Example",
            "url": "https://example.test/feed",
            "priority": False,
            "topics": ["llm"],
        }
        cached_articles = [
            {
                "title": "Cached article",
                "link": "https://example.test/a",
                "date": "2026-01-01T00:00:00+00:00",
                "topics": ["llm"],
            }
        ]

        class NotModified(urllib.error.HTTPError):
            def __init__(self):
                super().__init__(source["url"], 304, "Not Modified", {}, None)

        def fake_urlopen(req, timeout=None):
            raise NotModified()

        old_cache = fetch_rss._rss_cache
        old_dirty = fetch_rss._rss_cache_dirty
        old_urlopen = fetch_rss.urlopen
        fetch_rss._rss_cache = {
            source["url"]: {
                "etag": '"abc"',
                "ts": 99999999999,
                "articles": cached_articles,
                "count": len(cached_articles),
            }
        }
        fetch_rss._rss_cache_dirty = False
        fetch_rss.urlopen = fake_urlopen
        try:
            result = fetch_rss.fetch_feed_with_retry(
                source,
                datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=48),
            )
        finally:
            fetch_rss._rss_cache = old_cache
            fetch_rss._rss_cache_dirty = old_dirty
            fetch_rss.urlopen = old_urlopen

        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["not_modified"])
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["articles"], cached_articles)


if __name__ == "__main__":
    unittest.main()
