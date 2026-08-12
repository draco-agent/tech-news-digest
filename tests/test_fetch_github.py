#!/usr/bin/env python3
"""Tests for fetch-github.py."""

import datetime
import importlib.util
import io
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
spec = importlib.util.spec_from_file_location("fetch_github", SCRIPTS_DIR / "fetch-github.py")
fetch_github = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch_github)


def atom_entry(tag: str, updated: str, title: str = None) -> str:
    from urllib.parse import quote
    return f"""
  <entry>
    <id>tag:github.com,2008:Repository/65600975/{tag}</id>
    <updated>{updated}</updated>
    <link rel="alternate" type="text/html"
          href="https://github.com/pytorch/pytorch/releases/tag/{quote(tag, safe='')}"/>
    <title>{title or tag}</title>
    <content type="html">&lt;p&gt;Release notes&lt;/p&gt;</content>
  </entry>"""


class TestReleaseTagFilter(unittest.TestCase):
    def test_version_tags_are_releases(self):
        for tag in ["v2.13.0", "v6.19-rc4", "2.9.0", "langchain-core==0.3.1",
                    "sdk/v1.2.3", "2026.08.12"]:
            self.assertTrue(fetch_github.is_release_tag(tag), tag)

    def test_ci_tags_are_rejected(self):
        for tag in ["trunk/41645f27165b5fd74192164daea593eef5159926",
                    "viable/strict/1786490942", "ciflow/trunk/192980",
                    "nightly", "latest", ""]:
            self.assertFalse(fetch_github.is_release_tag(tag), tag)

    def test_tag_recovered_from_entry_id(self):
        self.assertEqual(
            fetch_github.atom_entry_tag(
                "tag:github.com,2008:Repository/65600975/viable/strict/1786490942", ""),
            "viable/strict/1786490942",
        )

    def test_tag_recovered_from_link_when_id_missing(self):
        self.assertEqual(
            fetch_github.atom_entry_tag(
                "", "https://github.com/pytorch/pytorch/releases/tag/v2.13.0"),
            "v2.13.0",
        )


class TestFetchReleasesAtom(unittest.TestCase):
    def _fetch(self, feed: str):
        source = {
            "id": "pytorch-github",
            "name": "PyTorch",
            "repo": "pytorch/pytorch",
            "priority": False,
            "topics": ["llm"],
        }

        class FakeResponse(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                self.close()
                return False

        old_urlopen = fetch_github.urlopen
        fetch_github.urlopen = lambda req, timeout=None: FakeResponse(feed.encode())
        try:
            cutoff = datetime.datetime(2026, 8, 1, tzinfo=datetime.timezone.utc)
            return fetch_github.fetch_releases_atom(source, cutoff)
        finally:
            fetch_github.urlopen = old_urlopen

    def test_ci_tags_are_filtered_out(self):
        feed = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<feed xmlns="http://www.w3.org/2005/Atom">'
            + atom_entry("trunk/41645f27165b5fd74192164daea593eef5159926",
                         "2026-08-12T00:43:11Z", "trunk/41645f27: [MPS] Implement put_")
            + atom_entry("viable/strict/1786490942", "2026-08-12T00:20:00Z")
            + atom_entry("v2.13.0", "2026-08-10T00:00:00Z")
            + "</feed>"
        )
        result = self._fetch(feed)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["skipped_tags"], 2)
        self.assertEqual(result["articles"][0]["title"], "pytorch v2.13.0")

    def test_ci_tags_do_not_crowd_out_the_real_release(self):
        """Filtering must happen before the per-repo cap, or a repo pushing more
        than MAX_RELEASES_PER_REPO CI tags would report zero releases."""
        noise = "".join(
            atom_entry(f"viable/strict/17864{i:05d}", "2026-08-12T00:20:00Z")
            for i in range(fetch_github.MAX_RELEASES_PER_REPO + 5)
        )
        feed = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<feed xmlns="http://www.w3.org/2005/Atom">'
            + noise + atom_entry("v2.13.0", "2026-08-10T00:00:00Z") + "</feed>"
        )
        result = self._fetch(feed)

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["articles"][0]["title"], "pytorch v2.13.0")

    def test_entries_older_than_cutoff_are_dropped(self):
        feed = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<feed xmlns="http://www.w3.org/2005/Atom">'
            + atom_entry("v2.13.0", "2026-08-10T00:00:00Z")
            + atom_entry("v2.12.0", "2026-06-01T00:00:00Z")
            + "</feed>"
        )
        result = self._fetch(feed)

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["articles"][0]["title"], "pytorch v2.13.0")


if __name__ == "__main__":
    unittest.main()
