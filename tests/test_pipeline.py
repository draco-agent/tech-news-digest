#!/usr/bin/env python3
"""Regression tests for run-pipeline.py."""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
spec = importlib.util.spec_from_file_location("run_pipeline", SCRIPTS_DIR / "run-pipeline.py")
run_pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_pipeline)


class TestRunPipeline(unittest.TestCase):
    def test_skip_trending_prevents_the_fetch_step(self):
        calls = []

        def fake_run_step(name, *args, **kwargs):
            calls.append(name)
            return {
                "name": name,
                "status": "ok",
                "elapsed_s": 0,
                "count": 0,
                "stderr_tail": [],
            }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "out.json"
            old_argv = sys.argv
            sys.argv = [
                "run-pipeline.py",
                "--skip",
                "rss,twitter,github,trending,reddit,web",
                "--output",
                str(output_path),
            ]
            try:
                with patch.object(run_pipeline, "run_step", side_effect=fake_run_step):
                    rc = run_pipeline.main()
            finally:
                sys.argv = old_argv

        self.assertEqual(rc, 0)
        self.assertEqual(calls, ["Merge", "Health"])

    def test_returns_nonzero_when_fetch_step_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "out.json"
            old_argv = sys.argv
            sys.argv = [
                "run-pipeline.py",
                "--defaults",
                "/no/such/defaults",
                "--only",
                "rss",
                "--step-timeout",
                "5",
                "--output",
                str(output_path),
            ]
            try:
                rc = run_pipeline.main()
            finally:
                sys.argv = old_argv

            self.assertNotEqual(rc, 0)

    def test_accepts_getxapi_twitter_backend(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "out.json"
            old_argv = sys.argv
            sys.argv = [
                "run-pipeline.py",
                "--twitter-backend",
                "getxapi",
                "--skip",
                "rss,twitter,github,trending,reddit,web",
                "--output",
                str(output_path),
            ]
            try:
                rc = run_pipeline.main()
            finally:
                sys.argv = old_argv

            self.assertEqual(rc, 0)

    def test_accepts_xquik_twitter_backend(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "out.json"
            old_argv = sys.argv
            sys.argv = [
                "run-pipeline.py",
                "--twitter-backend",
                "xquik",
                "--skip",
                "rss,twitter,github,trending,reddit,web",
                "--output",
                str(output_path),
            ]
            try:
                rc = run_pipeline.main()
            finally:
                sys.argv = old_argv

            self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
