#!/usr/bin/env python3
"""Tests for config_loader.py."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from config_loader import load_merged_sources, load_merged_topics  # noqa: E402

DEFAULTS_DIR = Path(__file__).parent.parent / "config" / "defaults"
README_EN = Path(__file__).parent.parent / "README.md"
README_ZH = Path(__file__).parent.parent / "README_CN.md"


def get_source_counts():
    sources = load_merged_sources(DEFAULTS_DIR)
    return {
        "total": len(sources),
        "rss": len([s for s in sources if s["type"] == "rss"]),
        "twitter": len([s for s in sources if s["type"] == "twitter"]),
        "github": len([s for s in sources if s["type"] == "github"]),
        "reddit": len([s for s in sources if s["type"] == "reddit"]),
    }


class TestLoadSources(unittest.TestCase):
    def test_loads_defaults(self):
        sources = load_merged_sources(DEFAULTS_DIR)
        self.assertGreater(len(sources), 100)

    def test_all_sources_have_required_fields(self):
        sources = load_merged_sources(DEFAULTS_DIR)
        for s in sources:
            self.assertIn("id", s, f"Source missing id: {s}")
            self.assertIn("type", s, f"Source missing type: {s}")
            self.assertIn("enabled", s, f"Source missing enabled: {s}")

    def test_source_types(self):
        sources = load_merged_sources(DEFAULTS_DIR)
        types = set(s["type"] for s in sources)
        self.assertIn("rss", types)
        self.assertIn("twitter", types)
        self.assertIn("github", types)
        self.assertIn("reddit", types)

    def test_user_overlay_merges(self):
        """User overlay should override matching IDs and add new ones."""
        with tempfile.TemporaryDirectory() as tmpdir:
            overlay = {
                "sources": [
                    {"id": "test-new-source", "type": "rss", "enabled": True, "url": "https://test.com/feed"},
                ]
            }
            overlay_path = Path(tmpdir) / "tech-news-digest-sources.json"
            with open(overlay_path, "w") as f:
                json.dump(overlay, f)

            sources = load_merged_sources(DEFAULTS_DIR, Path(tmpdir))
            ids = [s["id"] for s in sources]
            self.assertIn("test-new-source", ids)

    def test_user_overlay_disables(self):
        """User overlay with enabled=false should disable a default source."""
        defaults = load_merged_sources(DEFAULTS_DIR)
        first_id = defaults[0]["id"]

        with tempfile.TemporaryDirectory() as tmpdir:
            overlay = {
                "sources": [
                    {"id": first_id, "type": defaults[0]["type"], "enabled": False},
                ]
            }
            overlay_path = Path(tmpdir) / "tech-news-digest-sources.json"
            with open(overlay_path, "w") as f:
                json.dump(overlay, f)

            sources = load_merged_sources(DEFAULTS_DIR, Path(tmpdir))
            matched = [s for s in sources if s["id"] == first_id]
            self.assertEqual(len(matched), 1)
            self.assertFalse(matched[0]["enabled"])

    def test_no_overlay_dir(self):
        """Should work fine with no user config dir."""
        sources = load_merged_sources(DEFAULTS_DIR, None)
        self.assertGreater(len(sources), 100)


class TestLoadTopics(unittest.TestCase):
    def test_loads_defaults(self):
        topics = load_merged_topics(DEFAULTS_DIR)
        self.assertGreater(len(topics), 0)

    def test_topics_have_required_fields(self):
        topics = load_merged_topics(DEFAULTS_DIR)
        for t in topics:
            self.assertIn("id", t, f"Topic missing id: {t}")
            self.assertIn("label", t, f"Topic missing label: {t}")

    def test_topic_ids(self):
        topics = load_merged_topics(DEFAULTS_DIR)
        ids = [t["id"] for t in topics]
        self.assertIn("llm", ids)
        self.assertIn("crypto", ids)


class TestSourceCounts(unittest.TestCase):
    """Verify source counts match expectations."""

    def test_total_sources(self):
        sources = load_merged_sources(DEFAULTS_DIR)
        enabled = [s for s in sources if s.get("enabled", True)]
        self.assertGreaterEqual(len(enabled), 130)

    def test_twitter_count(self):
        counts = get_source_counts()
        self.assertEqual(counts["twitter"], 48)

    def test_rss_count(self):
        counts = get_source_counts()
        self.assertEqual(counts["rss"], 78)  # 62 original + 16 YouTube RSS

    def test_github_count(self):
        counts = get_source_counts()
        self.assertEqual(counts["github"], 29)

    def test_reddit_count(self):
        counts = get_source_counts()
        self.assertEqual(counts["reddit"], 13)


class TestReadmeCounts(unittest.TestCase):
    def test_english_readme_counts_are_current(self):
        counts = get_source_counts()
        content = README_EN.read_text(encoding="utf-8")
        self.assertIn(
            f"Automated tech news digest — {counts['total']} built-in sources, 6-source pipeline, one chat message to install.",
            content,
        )
        self.assertIn(
            f"A quality-scored, deduplicated tech digest built from **{counts['total']} built-in sources** plus **4 web search topics**:",
            content,
        )
        self.assertIn(
            f"| 📡 RSS | {counts['rss']} feeds |",
            content,
        )
        self.assertIn(
            f"| 🐙 GitHub | {counts['github']} repos |",
            content,
        )
        self.assertIn(
            f"`config/defaults/sources.json` — {counts['total']} built-in sources ({counts['rss']} RSS, {counts['twitter']} Twitter, {counts['github']} GitHub, {counts['reddit']} Reddit)",
            content,
        )

    def test_chinese_readme_counts_are_current(self):
        counts = get_source_counts()
        content = README_ZH.read_text(encoding="utf-8")
        self.assertIn(
            f"自动化科技资讯汇总 — {counts['total']} 个内置数据源，6 层管道，一句话安装。",
            content,
        )
        self.assertIn(
            f"基于 **{counts['total']} 个内置数据源** + **4 个 Web 搜索主题** 的质量评分、去重科技日报：",
            content,
        )
        self.assertIn(
            f"| 📡 RSS | {counts['rss']} 个订阅源 |",
            content,
        )
        self.assertIn(
            f"| 🐙 GitHub | {counts['github']} 个仓库 |",
            content,
        )
        self.assertIn(
            f"`config/defaults/sources.json` — {counts['total']} 个内置数据源（{counts['rss']} RSS、{counts['twitter']} Twitter、{counts['github']} GitHub、{counts['reddit']} Reddit）",
            content,
        )


if __name__ == "__main__":
    unittest.main()
