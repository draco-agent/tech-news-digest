#!/usr/bin/env python3
"""Tests for enrich-articles.py."""

import importlib.util
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
spec = importlib.util.spec_from_file_location("enrich_articles", SCRIPTS_DIR / "enrich-articles.py")
enrich_articles = importlib.util.module_from_spec(spec)
spec.loader.exec_module(enrich_articles)


class TestFetchFullTextSafety(unittest.TestCase):
    def test_blocks_loopback_urls_without_requesting(self):
        calls = []

        def fake_urlopen(req, timeout=None):
            calls.append(req.full_url)
            raise AssertionError("loopback URL should not be requested")

        old_urlopen = enrich_articles.urlopen
        enrich_articles.urlopen = fake_urlopen
        try:
            result = enrich_articles.fetch_full_text("http://127.0.0.1:9/private")
        finally:
            enrich_articles.urlopen = old_urlopen

        self.assertEqual(result["method"], "blocked")
        self.assertEqual(calls, [])

    def test_blocks_non_http_urls_without_requesting(self):
        result = enrich_articles.fetch_full_text("file:///etc/passwd")
        self.assertEqual(result["method"], "blocked")


if __name__ == "__main__":
    unittest.main()
