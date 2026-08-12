#!/usr/bin/env python3
"""Regression tests for fetch-twitter.py."""

import importlib.util
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
spec = importlib.util.spec_from_file_location("fetch_twitter", SCRIPTS_DIR / "fetch-twitter.py")
fetch_twitter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch_twitter)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


class TestXquikBackend(unittest.TestCase):
    def test_select_backend_requires_xquik_api_key(self):
        with patch.dict(fetch_twitter.os.environ, {}, clear=True):
            backend = fetch_twitter.select_backend("xquik")

        self.assertIsNone(backend)

    def test_select_backend_uses_xquik_api_key(self):
        with patch.dict(fetch_twitter.os.environ, {"XQUIK_API_KEY": "xquik_test_key"}, clear=True):
            backend = fetch_twitter.select_backend("xquik")

        self.assertIsInstance(backend, fetch_twitter.XquikBackend)

    def test_xquik_backend_maps_tweets_to_articles(self):
        backend = fetch_twitter.XquikBackend("xquik_test_key")
        source = {
            "id": "openai-twitter",
            "name": "OpenAI",
            "handle": "@openai",
            "priority": True,
            "topics": ["llm"],
        }
        created_at = datetime.now(timezone.utc).isoformat()
        payload = {
            "tweets": [
                {
                    "id": "123",
                    "text": "Launch notes",
                    "createdAt": created_at,
                    "url": "https://x.com/openai/status/123",
                    "likeCount": 7,
                    "retweetCount": 2,
                    "replyCount": 1,
                    "quoteCount": 0,
                    "viewCount": 100,
                }
            ],
            "has_next_page": False,
            "next_cursor": "",
        }
        captured_requests = []

        def fake_urlopen(request, timeout):
            captured_requests.append(request)
            return FakeResponse(payload)

        with patch.object(fetch_twitter, "urlopen", side_effect=fake_urlopen):
            result = backend._fetch_user_tweets(source, datetime.now(timezone.utc) - timedelta(hours=1))

        headers = {key.lower(): value for key, value in captured_requests[0].header_items()}
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["articles"][0]["tweet_id"], "123")
        self.assertEqual(result["articles"][0]["metrics"]["like_count"], 7)
        self.assertIn("/x/users/openai/tweets", captured_requests[0].full_url)
        self.assertEqual(headers["x-api-key"], "xquik_test_key")
        self.assertEqual(headers["xquik-api-contract"], fetch_twitter.XQUIK_API_CONTRACT)


if __name__ == "__main__":
    unittest.main()
