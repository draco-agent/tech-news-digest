#!/usr/bin/env python3
"""Tests for source-health.py."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
import importlib.util

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
FIXTURES_DIR = Path(__file__).parent / "fixtures"

spec = importlib.util.spec_from_file_location("source_health", SCRIPTS_DIR / "source-health.py")
source_health = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source_health)


class TestSourceHealthHelpers(unittest.TestCase):
    def test_load_source_file_flexible_handles_web_topics(self):
        data = source_health.load_source_file_flexible(FIXTURES_DIR / "web.json")
        self.assertGreater(len(data), 0)
        self.assertTrue(all(item["source_id"].startswith("web-") for item in data))

    def test_interface_status_is_skipped_not_failed(self):
        health = {}
        now = 1_800_000_000
        sources = [{"source_id": "web-llm", "name": "Web: llm", "status": "interface"}]

        source_health.update_health(health, sources, now)
        source_health.update_health(health, sources, now + 1)

        checks = health["web-llm"]["checks"]
        self.assertEqual([check["ok"] for check in checks], [None, None])


class TestSourceHealthScript(unittest.TestCase):
    def test_writes_summary_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "health.json"
            old_health_file = source_health.HEALTH_FILE
            source_health.HEALTH_FILE = str(Path(tmpdir) / "health-store.json")
            try:
                old_argv = sys.argv
                sys.argv = [
                    "source-health.py",
                    "--rss", str(FIXTURES_DIR / "rss.json"),
                    "--twitter", str(FIXTURES_DIR / "twitter.json"),
                    "--github", str(FIXTURES_DIR / "github.json"),
                    "--reddit", str(FIXTURES_DIR / "reddit.json"),
                    "--web", str(FIXTURES_DIR / "web.json"),
                    "--output", str(output_path),
                ]
                try:
                    rc = source_health.main()
                finally:
                    sys.argv = old_argv

                self.assertEqual(rc, 0)
                self.assertTrue(output_path.exists())
                summary = json.loads(output_path.read_text())
                self.assertEqual(summary["status"], "ok")
                self.assertEqual(summary["tracked_sources"], 14)
                self.assertEqual(summary["unhealthy_sources"], 0)
                self.assertEqual({item["name"] for item in summary["inputs"]}, {"rss", "twitter", "github", "reddit", "web"})
            finally:
                source_health.HEALTH_FILE = old_health_file


if __name__ == "__main__":
    unittest.main()
