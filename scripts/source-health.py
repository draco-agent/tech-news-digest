#!/usr/bin/env python3
"""
Source health monitoring for tech-news-digest pipeline.

Tracks per-source success/failure history and reports unhealthy sources.

Usage:
    python3 source-health.py --rss rss.json --twitter twitter.json --github github.json [--output health.json]
"""

import json
import sys
import argparse
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone

try:
    from config_loader import get_state_path
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parent))
    from config_loader import get_state_path

# Health history spans several days and needs at least 2 samples before it can
# flag anything, so it must outlive /tmp.
HEALTH_FILE = str(get_state_path("source-health.json"))
DEFAULT_HEALTH_FILE = HEALTH_FILE
LEGACY_HEALTH_FILE = "/tmp/tech-news-digest-source-health.json"
HISTORY_DAYS = 7
FAILURE_THRESHOLD = 0.5  # >50% failure rate triggers warning
SKIPPED_STATUSES = {"interface", "skipped", "no_credentials"}


def setup_logging(verbose: bool) -> logging.Logger:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)


def load_health_data() -> Dict[str, Any]:
    # The legacy /tmp store is only consulted when HEALTH_FILE is the default —
    # a caller that redirects HEALTH_FILE (tests, sandboxes) must stay isolated.
    candidates = [HEALTH_FILE]
    if HEALTH_FILE == DEFAULT_HEALTH_FILE:
        candidates.append(LEGACY_HEALTH_FILE)
    for path in candidates:
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            continue
    return {}


def save_health_data(data: Dict[str, Any]) -> None:
    with open(HEALTH_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def load_source_file(path: Optional[Path]) -> list:
    if not path or not path.exists():
        return []
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        return data.get("sources", [])
    except (json.JSONDecodeError, OSError):
        return []


def load_source_file_flexible(path: Optional[Path]) -> list:
    """Load sources from a JSON file, trying 'sources', 'subreddits', and 'topics' keys."""
    if not path or not path.exists():
        return []
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        # Try standard keys
        if "sources" in data:
            return data["sources"]
        if "subreddits" in data:
            return data["subreddits"]
        if "topics" in data:
            # Create synthetic sources from topic results
            synthetic = []
            for topic in data["topics"]:
                synthetic.append({
                    "source_id": f"web-{topic.get('topic_id', 'unknown')}",
                    "name": f"Web: {topic.get('topic_id', 'unknown')}",
                    "status": topic.get("status", "ok"),
                    "articles": topic.get("articles", []),
                })
            return synthetic
        return []
    except (json.JSONDecodeError, OSError):
        return []


def update_health(health: Dict[str, Any], sources: list, now: float) -> None:
    cutoff = now - HISTORY_DAYS * 86400
    for source in sources:
        sid = source.get("source_id", source.get("id", "unknown"))
        if sid not in health:
            health[sid] = {"name": source.get("name", sid), "checks": []}
        # Prune old entries
        health[sid]["checks"] = [c for c in health[sid]["checks"] if c["ts"] > cutoff]
        status = source.get("status")
        ok = None if status in SKIPPED_STATUSES else status == "ok"
        health[sid]["checks"].append({
            "ts": now,
            "ok": ok,
        })


def report_unhealthy(health: Dict[str, Any], logger: logging.Logger) -> int:
    unhealthy = 0
    for sid, info in health.items():
        checks = info.get("checks", [])
        checked = [c for c in checks if c.get("ok") is not None]
        if len(checked) < 2:
            continue
        failures = sum(1 for c in checked if not c["ok"])
        rate = failures / len(checked)
        if rate > FAILURE_THRESHOLD:
            logger.warning(f"⚠️  Unhealthy source: {info.get('name', sid)} "
                         f"({failures}/{len(checked)} failures, {rate:.0%} failure rate)")
            unhealthy += 1
    return unhealthy


def main():
    parser = argparse.ArgumentParser(description="Track source health for tech-news-digest pipeline.")
    parser.add_argument("--rss", type=Path, help="RSS output JSON")
    parser.add_argument("--twitter", type=Path, help="Twitter output JSON")
    parser.add_argument("--github", type=Path, help="GitHub output JSON")
    parser.add_argument("--reddit", type=Path, help="Reddit output JSON")
    parser.add_argument("--web", type=Path, help="Web search output JSON")
    parser.add_argument("--output", type=Path, help="Optional JSON summary output path")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logger = setup_logging(args.verbose)
    health = load_health_data()
    now = time.time()
    processed_inputs = []

    # Standard sources (use 'sources' key)
    for label, path in [("rss", args.rss), ("twitter", args.twitter), ("github", args.github)]:
        sources = load_source_file(path)
        if sources:
            update_health(health, sources, now)
            processed_inputs.append({"name": label, "path": str(path), "count": len(sources)})

    # Reddit and Web use flexible loading (subreddits/topics keys)
    for label, path in [("reddit", args.reddit), ("web", args.web)]:
        sources = load_source_file_flexible(path)
        if sources:
            update_health(health, sources, now)
            processed_inputs.append({"name": label, "path": str(path), "count": len(sources)})

    save_health_data(health)
    unhealthy = report_unhealthy(health, logger)

    total = len(health)
    summary = {
        "status": "ok",
        "tracked_sources": total,
        "unhealthy_sources": unhealthy,
        "inputs": processed_inputs,
        "health_file": HEALTH_FILE,
        "checked_at": datetime.fromtimestamp(now, timezone.utc).isoformat(),
    }

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(summary, f, indent=2)

    logger.info(f"📊 Health check: {total} sources tracked, {unhealthy} unhealthy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
