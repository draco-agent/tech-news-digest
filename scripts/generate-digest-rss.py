#!/usr/bin/env python3
"""
Generate an RSS 2.0 feed from the merged digest JSON for RSS readers (e.g., Lire).

Reads the merged JSON output from the pipeline and produces an RSS XML feed
with one item per article, grouped by topic.

Usage:
    python3 generate-digest-rss.py \
      --input /tmp/td-merged.json \
      --output /mnt/data/tech-digest/rss.xml \
      --feed-url https://nas.local/tech-digest/ \
      [--limit 50] \
      [--verbose]
"""

import json
import sys
import argparse
import logging
from datetime import datetime, timezone
from xml.sax.saxutils import escape as xml_escape
from pathlib import Path
from typing import Any, Dict, List, Optional

# Topic emoji map (matches topics.json defaults)
TOPIC_EMOJI = {
    "llm": "🧠",
    "ai-agent": "🤖",
    "crypto": "₿",
    "frontier-tech": "🔬",
    "apple": "🍎",
    "consumer-tech": "📱",
}


def setup_logging(verbose: bool) -> logging.Logger:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger(__name__)


def rfc822_date(dt_str: str) -> str:
    """Convert ISO 8601 datetime string to RFC 822 format for RSS."""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.strftime("%a, %d %b %Y %H:%M:%S %z")
    except (ValueError, AttributeError):
        return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")


def format_description(article: Dict[str, Any]) -> str:
    """Build a human-readable description for an RSS item."""
    parts = []

    snippet = article.get("snippet", "")
    if snippet:
        parts.append(snippet)

    # Add source metrics
    source_type = article.get("source_type", "")
    if source_type == "reddit":
        upvotes = article.get("upvotes", 0)
        comments = article.get("comments", 0)
        parts.append(f"Reddit: {upvotes} upvotes, {comments} comments.")
    elif source_type == "twitter":
        metrics = article.get("metrics", {})
        if metrics:
            likes = metrics.get("like_count", 0)
            rts = metrics.get("retweet_count", 0)
            parts.append(f"Twitter: {likes} likes, {rts} retweets.")
    elif source_type == "github":
        stars = article.get("stars", 0)
        if stars:
            parts.append(f"GitHub: {stars} stars.")
    elif source_type == "github_trending":
        stars = article.get("stars", 0)
        daily = article.get("daily_stars_est", 0)
        language = article.get("language", "")
        lang_str = f", {language}" if language else ""
        parts.append(f"GitHub Trending: {stars} stars (+{daily}/day{lang_str}).")

    return " ".join(parts) if parts else article.get("title", "")


def build_rss(
    merged_data: Dict[str, Any],
    feed_url: str,
    limit: int,
    version: str = "3.16.2",
) -> str:
    """Build RSS 2.0 XML string from merged digest data."""
    topics = merged_data.get("topics", {})
    generated = merged_data.get("generated", datetime.now(timezone.utc).isoformat())
    now_rfc822 = rfc822_date(generated)

    # Collect all articles across topics, sorted by quality_score desc
    all_articles: List[Dict[str, Any]] = []
    for topic_id, topic_data in topics.items():
        articles = topic_data.get("articles", [])
        for a in articles:
            a["_topic"] = topic_id
            all_articles.append(a)

    all_articles.sort(key=lambda a: a.get("quality_score", 0), reverse=True)
    all_articles = all_articles[:limit]

    # Build XML
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        "  <channel>",
        f"    <title>Tech News Digest</title>",
        f"    <link>{xml_escape(feed_url)}</link>",
        f"    <description>Daily tech news digest powered by OpenClaw</description>",
        f"    <language>en</language>",
        f'    <atom:link href="{xml_escape(feed_url)}rss.xml" rel="self" type="application/rss+xml"/>',
        f"    <lastBuildDate>{now_rfc822}</lastBuildDate>",
        f"    <generator>tech-news-digest v{version}</generator>",
        "",
    ]

    for article in all_articles:
        title = article.get("title", "Untitled")
        link = article.get("link", "")
        score = article.get("quality_score", 0)
        topic = article.get("_topic", "")
        date_str = article.get("date", generated)
        desc = format_description(article)

        lines.append("    <item>")
        lines.append(f"      <title>[{score}pts] {xml_escape(title)}</title>")
        lines.append(f"      <link>{xml_escape(link)}</link>")
        lines.append(f"      <description>{xml_escape(desc)}</description>")
        if topic:
            lines.append(f"      <category>{xml_escape(topic)}</category>")
        lines.append(f"      <pubDate>{rfc822_date(date_str)}</pubDate>")
        lines.append("    </item>")

    lines.append("  </channel>")
    lines.append("</rss>")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate RSS 2.0 feed from merged digest JSON.",
    )
    parser.add_argument("--input", "-i", type=Path, required=True, help="Merged JSON input file")
    parser.add_argument("--output", "-o", type=Path, required=True, help="Output RSS XML file")
    parser.add_argument("--feed-url", type=str, default="https://nas.local/tech-digest/", help="Base URL for the feed")
    parser.add_argument("--limit", type=int, default=50, help="Max number of articles in the feed")
    parser.add_argument("--version", type=str, default="3.16.2", help="Version string for generator tag")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()
    logger = setup_logging(args.verbose)

    if not args.input.exists():
        logger.error(f"Input file not found: {args.input}")
        return 1

    with open(args.input, "r", encoding="utf-8") as f:
        merged_data = json.load(f)

    total = sum(t.get("count", 0) for t in merged_data.get("topics", {}).values())
    logger.info(f"📰 Generating RSS feed from {total} articles (limit: {args.limit})")

    rss_xml = build_rss(merged_data, args.feed_url, args.limit, args.version)

    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(rss_xml)

    article_count = min(total, args.limit)
    logger.info(f"✅ Wrote {article_count} articles to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())