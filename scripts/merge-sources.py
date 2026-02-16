#!/usr/bin/env python3
"""
Merge data from all sources (RSS, Twitter, Web) with quality scoring.

Reads output from fetch-rss.py, fetch-twitter.py, and fetch-web.py,
merges articles, removes duplicates, applies quality scoring, and
groups by topics for final digest output.

Usage:
    python3 merge-sources.py [--rss FILE] [--twitter FILE] [--web FILE] [--output FILE] [--verbose]
"""

import json
import sys
import os
import argparse
import logging
import tempfile
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from difflib import SequenceMatcher
from urllib.parse import urlparse

# Quality scoring weights
SCORE_MULTI_SOURCE = 5      # Article appears in multiple sources
SCORE_PRIORITY_SOURCE = 3   # From high-priority source
SCORE_RECENT = 2            # Recent article (< 24h)
SCORE_ENGAGEMENT = 1        # High social engagement (Twitter)
PENALTY_DUPLICATE = -10     # Duplicate/very similar title
PENALTY_OLD_REPORT = -5     # Already in previous digest

# Deduplication thresholds
TITLE_SIMILARITY_THRESHOLD = 0.85
DOMAIN_DUPLICATE_THRESHOLD = 0.95


def setup_logging(verbose: bool) -> logging.Logger:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)


def load_source_data(file_path: Optional[Path]) -> Dict[str, Any]:
    """Load source data from JSON file."""
    if not file_path or not file_path.exists():
        return {"sources": [], "total_articles": 0}
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        logging.warning(f"Failed to load {file_path}: {e}")
        return {"sources": [], "total_articles": 0}


def normalize_title(title: str) -> str:
    """Normalize title for comparison."""
    # Remove common prefixes/suffixes
    title = re.sub(r'^(RT\s+@\w+:\s*)', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\s*[|\-–]\s*[^|]*$', '', title)  # Remove " | Site Name" endings
    
    # Normalize whitespace and punctuation
    title = re.sub(r'\s+', ' ', title).strip()
    title = re.sub(r'[^\w\s]', '', title.lower())
    
    return title


def calculate_title_similarity(title1: str, title2: str) -> float:
    """Calculate similarity between two titles."""
    norm1 = normalize_title(title1)
    norm2 = normalize_title(title2)
    
    if not norm1 or not norm2:
        return 0.0
        
    return SequenceMatcher(None, norm1, norm2).ratio()


def get_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        return urlparse(url).netloc.lower().replace('www.', '')
    except:
        return ''


def calculate_base_score(article: Dict[str, Any], source: Dict[str, Any]) -> float:
    """Calculate base quality score for an article."""
    score = 0.0
    
    # Priority source bonus
    if source.get("priority", False):
        score += SCORE_PRIORITY_SOURCE
        
    # Recency bonus (< 24 hours)
    try:
        article_date = datetime.fromisoformat(article["date"].replace('Z', '+00:00'))
        hours_old = (datetime.now(timezone.utc) - article_date).total_seconds() / 3600
        if hours_old < 24:
            score += SCORE_RECENT
    except:
        pass
    
    # Twitter engagement bonus
    if source.get("source_type") == "twitter" and "metrics" in article:
        metrics = article["metrics"]
        likes = metrics.get("like_count", 0)
        retweets = metrics.get("retweet_count", 0)
        
        # High engagement bonus
        if likes > 100 or retweets > 50:
            score += SCORE_ENGAGEMENT
            
    return score


def _extract_tokens(title: str) -> Set[str]:
    """Extract significant tokens from a normalized title for bucketing."""
    norm = normalize_title(title)
    # Split into tokens, filter short/common words
    stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'in', 'on', 'at',
                 'to', 'for', 'of', 'and', 'or', 'with', 'by', 'from', 'as', 'it',
                 'its', 'that', 'this', 'be', 'has', 'had', 'have', 'not', 'but',
                 'what', 'how', 'new', 'will', 'can', 'do', 'does', 'did'}
    tokens = set()
    for word in norm.split():
        if len(word) >= 3 and word not in stopwords:
            tokens.add(word)
    return tokens


def _build_token_buckets(articles: List[Dict[str, Any]]) -> Dict[int, Set[int]]:
    """Build token-based buckets mapping each article index to candidate duplicate indices.
    
    Two articles are candidates if they share 2+ significant tokens.
    Returns dict: article_index -> set of candidate article indices to compare against.
    """
    from collections import defaultdict
    
    # token -> list of article indices
    token_to_indices: Dict[str, List[int]] = defaultdict(list)
    article_tokens: List[Set[str]] = []
    
    for i, article in enumerate(articles):
        tokens = _extract_tokens(article.get("title", ""))
        article_tokens.append(tokens)
        for token in tokens:
            token_to_indices[token].append(i)
    
    # For each article, find candidates sharing 2+ tokens
    candidates: Dict[int, Set[int]] = defaultdict(set)
    for i, tokens in enumerate(article_tokens):
        # Count how many tokens each other article shares with this one
        overlap_count: Dict[int, int] = defaultdict(int)
        for token in tokens:
            for j in token_to_indices[token]:
                if j != i:
                    overlap_count[j] += 1
        for j, count in overlap_count.items():
            if count >= 2:
                candidates[i].add(j)
    
    return candidates


def deduplicate_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate articles based on title similarity and domain.
    
    Uses token-based bucketing to avoid O(n²) SequenceMatcher comparisons.
    Only articles sharing 2+ significant title tokens are compared.
    """
    if not articles:
        return articles
        
    deduplicated = []
    domain_counts = {}
    
    # Sort by quality score (highest first) to keep best versions
    articles.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
    
    # Build token buckets for candidate pairs
    candidates = _build_token_buckets(articles)
    
    # Track which indices have been marked as duplicates
    duplicate_indices: Set[int] = set()
    
    for i, article in enumerate(articles):
        if i in duplicate_indices:
            continue
        
        title = article.get("title", "")
        url = article.get("link", "")
        domain = get_domain(url)
        
        # Mark future candidates as duplicates using SequenceMatcher (only within bucket)
        for j in candidates.get(i, set()):
            if j > i and j not in duplicate_indices:
                other_title = articles[j].get("title", "")
                similarity = calculate_title_similarity(title, other_title)
                if similarity >= TITLE_SIMILARITY_THRESHOLD:
                    logging.debug(f"Title duplicate: '{other_title}' ~= '{title}' ({similarity:.2f})")
                    duplicate_indices.add(j)
            
        # Check domain saturation (too many articles from same domain)
        if domain:
            domain_count = domain_counts.get(domain, 0)
            if domain_count >= 3:  # Max 3 articles per domain per topic
                logging.debug(f"Domain oversaturation: {domain} ({domain_count} articles)")
                continue
            domain_counts[domain] = domain_count + 1
            
        deduplicated.append(article)
        
    logging.info(f"Deduplication: {len(articles)} → {len(deduplicated)} articles")
    return deduplicated


def merge_article_sources(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge articles that appear from multiple sources."""
    if not articles:
        return articles
        
    # Group articles by normalized title
    title_groups = {}
    for article in articles:
        norm_title = normalize_title(article.get("title", ""))
        if norm_title not in title_groups:
            title_groups[norm_title] = []
        title_groups[norm_title].append(article)
    
    merged = []
    for group in title_groups.values():
        if len(group) == 1:
            merged.append(group[0])
        else:
            # Multiple sources for same story - merge and boost score
            primary = max(group, key=lambda x: x.get("quality_score", 0))
            
            # Collect all source types
            source_types = set(article.get("source_type", "") for article in group)
            source_names = [article.get("source_name", "") for article in group]
            
            # Multi-source bonus
            multi_source_bonus = len(source_types) * SCORE_MULTI_SOURCE
            primary["quality_score"] = primary.get("quality_score", 0) + multi_source_bonus
            
            # Add metadata about multiple sources
            primary["multi_source"] = True
            primary["source_count"] = len(group)
            primary["all_sources"] = source_names[:3]  # Limit to avoid bloat
            
            logging.debug(f"Merged {len(group)} sources for: '{primary['title'][:50]}...'")
            merged.append(primary)
            
    return merged


def load_previous_digests(archive_dir: Path, days: int = 7) -> Set[str]:
    """Load titles from previous digests to avoid repeats."""
    if not archive_dir.exists():
        return set()
        
    seen_titles = set()
    cutoff = datetime.now() - timedelta(days=days)
    
    try:
        for file_path in archive_dir.glob("*.md"):
            # Extract date from filename
            match = re.search(r'(\d{4}-\d{2}-\d{2})', file_path.name)
            if match:
                try:
                    file_date = datetime.strptime(match.group(1), "%Y-%m-%d")
                    if file_date < cutoff:
                        continue
                except ValueError:
                    continue
                    
            # Extract titles from markdown
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Simple title extraction (assumes format like "- [Title](link)")
            for match in re.finditer(r'-\s*\[([^\]]+)\]', content):
                title = normalize_title(match.group(1))
                if title:
                    seen_titles.add(title)
                    
    except Exception as e:
        logging.debug(f"Failed to load previous digests: {e}")
        
    logging.info(f"Loaded {len(seen_titles)} titles from previous {days} days")
    return seen_titles


def apply_previous_digest_penalty(articles: List[Dict[str, Any]], 
                                previous_titles: Set[str]) -> List[Dict[str, Any]]:
    """Apply penalty to articles that appeared in previous digests."""
    if not previous_titles:
        return articles
        
    penalized_count = 0
    for article in articles:
        norm_title = normalize_title(article.get("title", ""))
        if norm_title in previous_titles:
            article["quality_score"] = article.get("quality_score", 0) + PENALTY_OLD_REPORT
            article["in_previous_digest"] = True
            penalized_count += 1
            
    logging.info(f"Applied previous digest penalty to {penalized_count} articles")
    return articles


def group_by_topics(articles: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group articles by their topics."""
    topic_groups = {}
    
    for article in articles:
        topics = article.get("topics", [])
        if not topics:
            topics = ["uncategorized"]
            
        for topic in topics:
            if topic not in topic_groups:
                topic_groups[topic] = []
            
            # Add copy with single topic for cleaner grouping
            article_copy = article.copy()
            article_copy["primary_topic"] = topic
            topic_groups[topic].append(article_copy)
    
    # Sort articles within each topic by quality score
    for topic in topic_groups:
        topic_groups[topic].sort(key=lambda x: x.get("quality_score", 0), reverse=True)
        
    return topic_groups


def main():
    """Main merge and scoring function."""
    parser = argparse.ArgumentParser(
        description="Merge articles from all sources with quality scoring and deduplication.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 merge-sources.py --rss rss.json --twitter twitter.json --web web.json
    python3 merge-sources.py --rss rss.json --output merged.json --verbose
    python3 merge-sources.py --archive-dir workspace/archive/tech-digest
        """
    )
    
    parser.add_argument(
        "--rss",
        type=Path,
        help="RSS fetch results JSON file"
    )
    
    parser.add_argument(
        "--twitter",
        type=Path,
        help="Twitter fetch results JSON file"
    )
    
    parser.add_argument(
        "--web",
        type=Path,
        help="Web search results JSON file"
    )
    
    parser.add_argument(
        "--github",
        type=Path,
        help="GitHub releases results JSON file"
    )
    
    parser.add_argument(
        "--reddit",
        type=Path,
        help="Reddit posts results JSON file"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output JSON path (default: auto-generated temp file)"
    )
    
    parser.add_argument(
        "--archive-dir",
        type=Path,
        help="Archive directory for previous digest penalty"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    logger = setup_logging(args.verbose)
    
    # Auto-generate unique output path if not specified
    if not args.output:
        fd, temp_path = tempfile.mkstemp(prefix="tech-digest-merged-", suffix=".json")
        os.close(fd)
        args.output = Path(temp_path)
    
    try:
        # Load source data
        rss_data = load_source_data(args.rss)
        twitter_data = load_source_data(args.twitter)
        web_data = load_source_data(args.web)
        github_data = load_source_data(args.github)
        reddit_data = load_source_data(getattr(args, 'reddit', None))
        
        logger.info(f"Loaded sources - RSS: {rss_data.get('total_articles', 0)}, "
                   f"Twitter: {twitter_data.get('total_articles', 0)}, "
                   f"Web: {web_data.get('total_articles', 0)}, "
                   f"GitHub: {github_data.get('total_articles', 0)}, "
                   f"Reddit: {reddit_data.get('total_posts', 0)}")
        
        # Collect all articles with source context
        all_articles = []
        
        # Process RSS articles
        for source in rss_data.get("sources", []):
            for article in source.get("articles", []):
                article["source_type"] = "rss"
                article["source_name"] = source.get("name", "")
                article["source_id"] = source.get("source_id", "")
                article["quality_score"] = calculate_base_score(article, source)
                all_articles.append(article)
        
        # Process Twitter articles
        for source in twitter_data.get("sources", []):
            for article in source.get("articles", []):
                article["source_type"] = "twitter"
                article["source_name"] = f"@{source.get('handle', '')}"
                article["source_id"] = source.get("source_id", "")
                article["quality_score"] = calculate_base_score(article, source)
                all_articles.append(article)
        
        # Process Web articles
        for topic_result in web_data.get("topics", []):
            for article in topic_result.get("articles", []):
                article["source_type"] = "web"
                article["source_name"] = "Web Search"
                article["source_id"] = f"web-{topic_result.get('topic_id', '')}"
                # Build a minimal source dict so web articles go through the same scoring
                web_source = {
                    "source_type": "web",
                    "priority": False,
                }
                article["quality_score"] = calculate_base_score(article, web_source)
                all_articles.append(article)
        
        # Process GitHub articles
        for source in github_data.get("sources", []):
            for article in source.get("articles", []):
                article["source_type"] = "github"
                article["source_name"] = source.get("name", "")
                article["source_id"] = source.get("source_id", "")
                article["quality_score"] = calculate_base_score(article, source)
                all_articles.append(article)
        
        # Process Reddit articles
        for source in reddit_data.get("subreddits", []):
            for article in source.get("articles", []):
                article["source_type"] = "reddit"
                article["source_name"] = f"r/{source.get('subreddit', '')}"
                article["source_id"] = source.get("source_id", "")
                reddit_source = {
                    "source_type": "reddit",
                    "priority": source.get("priority", False),
                }
                article["quality_score"] = calculate_base_score(article, reddit_source)
                # Reddit score bonus
                score = article.get("score", 0)
                if score > 500:
                    article["quality_score"] += 5
                elif score > 200:
                    article["quality_score"] += 3
                elif score > 100:
                    article["quality_score"] += 1
                all_articles.append(article)
        
        total_collected = len(all_articles)
        logger.info(f"Total articles collected: {total_collected}")
        
        # Load previous digest titles for penalty
        previous_titles = set()
        if args.archive_dir:
            previous_titles = load_previous_digests(args.archive_dir)
        
        # Apply previous digest penalty
        all_articles = apply_previous_digest_penalty(all_articles, previous_titles)
        
        # Merge multi-source articles
        all_articles = merge_article_sources(all_articles)
        logger.info(f"After merging multi-source: {len(all_articles)}")
        
        # Deduplicate articles
        all_articles = deduplicate_articles(all_articles)
        
        # Group by topics
        topic_groups = group_by_topics(all_articles)
        
        # Generate summary stats (use deduplicated count, not topic-grouped which double-counts)
        total_final = len(all_articles)
        topic_counts = {topic: len(articles) for topic, articles in topic_groups.items()}
        
        output = {
            "generated": datetime.now(timezone.utc).isoformat(),
            "input_sources": {
                "rss_articles": rss_data.get("total_articles", 0),
                "twitter_articles": twitter_data.get("total_articles", 0),
                "web_articles": web_data.get("total_articles", 0),
                "github_articles": github_data.get("total_articles", 0),
                "reddit_posts": reddit_data.get("total_posts", 0),
                "total_input": total_collected
            },
            "processing": {
                "deduplication_applied": True,
                "multi_source_merging": True,
                "previous_digest_penalty": len(previous_titles) > 0,
                "quality_scoring": True
            },
            "output_stats": {
                "total_articles": total_final,
                "topics_count": len(topic_groups),
                "topic_distribution": topic_counts
            },
            "topics": {
                topic: {
                    "count": len(articles),
                    "articles": articles
                } for topic, articles in topic_groups.items()
            }
        }
        
        # Write output
        json_str = json.dumps(output, ensure_ascii=False, indent=2)
        with open(args.output, "w", encoding='utf-8') as f:
            f.write(json_str)
        
        logger.info(f"✅ Merged and scored articles:")
        logger.info(f"   Input: {total_collected} articles")
        logger.info(f"   Output: {total_final} articles across {len(topic_groups)} topics")
        logger.info(f"   File: {args.output}")
        
        return 0
        
    except Exception as e:
        logger.error(f"💥 Merge failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())