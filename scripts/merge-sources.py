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
from urllib.parse import urlparse, parse_qsl, urlencode

# Quality scoring weights
SCORE_MULTI_SOURCE = 5      # Article appears in multiple sources
SCORE_PRIORITY_SOURCE = 3   # From high-priority source
SCORE_RECENT = 2            # Recent article (< 24h)
SCORE_ENGAGEMENT_VIRAL = 5   # Viral tweet (1000+ likes or 500+ RTs)
SCORE_ENGAGEMENT_HIGH = 3    # High engagement (500+ likes or 200+ RTs)
SCORE_ENGAGEMENT_MED = 2     # Medium engagement (100+ likes or 50+ RTs)
SCORE_ENGAGEMENT_LOW = 1     # Some engagement (50+ likes or 20+ RTs)
PENALTY_DUPLICATE = -10     # Duplicate/very similar title
PENALTY_OLD_REPORT = -5     # Already in previous digest

# Deduplication thresholds
TITLE_SIMILARITY_THRESHOLD = 0.75  # Lowered from 0.85 to catch more duplicates
DOMAIN_DUPLICATE_THRESHOLD = 0.95

# Fallback ordering when topics.json cannot be read; must match config/defaults/topics.json
DEFAULT_TOPIC_ORDER = ["llm", "ai-agent", "crypto", "frontier-tech"]


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
    except Exception:
        return ''


# Query parameters that carry no article identity — safe to drop when comparing URLs.
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "utm_id",
    "ref", "referrer", "source", "src", "fbclid", "gclid", "mc_cid", "mc_eid",
    "spm", "share_id", "_hsenc", "_hsmi", "igshid", "si", "feature", "at_medium",
}


def normalize_url(url: str) -> str:
    """Normalize URL for dedup comparison.

    Strips fragment, trailing slash, `www.` and known tracking parameters, but
    KEEPS the remaining query string: for sites like YouTube (`/watch?v=ID`) the
    query *is* the article identity, and dropping it collapses every video from
    every channel into a single entry.
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace('www.', '')
        path = parsed.path.rstrip('/')
        kept = [
            (k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if k.lower() not in TRACKING_PARAMS
        ]
        query = urlencode(sorted(kept)) if kept else ""
        return f"{domain}{path}?{query}" if query else f"{domain}{path}"
    except Exception:
        return url


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
    except Exception:
        pass
    
    # Twitter engagement bonus (tiered)
    if source.get("source_type") == "twitter" and "metrics" in article:
        metrics = article["metrics"]
        likes = metrics.get("like_count", 0)
        retweets = metrics.get("retweet_count", 0)
        
        if likes >= 1000 or retweets >= 500:
            score += SCORE_ENGAGEMENT_VIRAL
        elif likes >= 500 or retweets >= 200:
            score += SCORE_ENGAGEMENT_HIGH
        elif likes >= 100 or retweets >= 50:
            score += SCORE_ENGAGEMENT_MED
        elif likes >= 50 or retweets >= 20:
            score += SCORE_ENGAGEMENT_LOW

    # RSS from priority sources get extra weight (official blogs, research papers)
    if source.get("source_type") == "rss" and source.get("priority", False):
        score += 2  # Extra priority RSS bonus

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

    Two articles are candidates if they share 2+ significant tokens, or if their
    normalized titles are identical (which catches short titles like "GPT-5" that
    carry fewer than 2 significant tokens).
    Returns dict: article_index -> set of candidate article indices to compare against.
    """
    from collections import defaultdict

    # token -> list of article indices
    token_to_indices: Dict[str, List[int]] = defaultdict(list)
    title_to_indices: Dict[str, List[int]] = defaultdict(list)
    article_tokens: List[Set[str]] = []

    for i, article in enumerate(articles):
        title = article.get("title", "")
        tokens = _extract_tokens(title)
        article_tokens.append(tokens)
        for token in tokens:
            token_to_indices[token].append(i)
        norm = normalize_title(title)
        if norm:
            title_to_indices[norm].append(i)

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

    # Identical normalized titles are always candidates
    for indices in title_to_indices.values():
        if len(indices) > 1:
            for i in indices:
                candidates[i].update(j for j in indices if j != i)

    return candidates


def _absorb_duplicate(primary: Dict[str, Any], duplicate: Dict[str, Any]) -> None:
    """Fold a duplicate's provenance into the surviving article.

    Cross-source corroboration is tracked here rather than in a separate
    exact-title pass, so that near-duplicate headlines (which the similarity
    dedup catches but exact matching does not) still earn the multi-source bonus
    instead of being silently discarded.
    """
    types: Set[str] = primary.setdefault("_source_types", {primary.get("source_type", "")})
    types.add(duplicate.get("source_type", ""))

    names: List[str] = primary.setdefault("_source_names", [primary.get("source_name", "")])
    dup_name = duplicate.get("source_name", "")
    if dup_name and dup_name not in names:
        names.append(dup_name)


def apply_multi_source_bonus(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Reward articles corroborated by more than one source type.

    Bonus is SCORE_MULTI_SOURCE per *additional* source type, so a story seen in
    two source types gets +5 (matching the documented weighting).
    """
    boosted = 0
    for article in articles:
        types = {t for t in article.pop("_source_types", set()) if t}
        names = [n for n in article.pop("_source_names", []) if n]
        if len(types) < 2:
            continue
        article["quality_score"] = article.get("quality_score", 0) + SCORE_MULTI_SOURCE * (len(types) - 1)
        article["multi_source"] = True
        article["source_count"] = len(names) or len(types)
        article["all_sources"] = names[:3]
        boosted += 1

    logging.info(f"Multi-source bonus applied to {boosted} articles")
    return articles


def deduplicate_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate articles based on title similarity.
    
    Uses token-based bucketing to avoid O(n²) SequenceMatcher comparisons.
    Only articles sharing 2+ significant title tokens are compared.
    Domain saturation is handled separately per-topic after grouping.
    """
    if not articles:
        return articles
        
    # Sort by quality score (highest first) to keep best versions
    articles.sort(key=lambda x: x.get("quality_score", 0), reverse=True)

    # Phase 1: URL dedup (exact URL match after normalization)
    url_seen: Dict[str, int] = {}  # normalized_url -> index in articles
    url_duplicates: Set[int] = set()
    for i, article in enumerate(articles):
        url = article.get("link", "")
        if not url:
            continue
        norm_url = normalize_url(url)
        if norm_url in url_seen:
            # Keep the one with higher quality_score (articles already sorted by score)
            url_duplicates.add(i)
            _absorb_duplicate(articles[url_seen[norm_url]], article)
            logging.debug(f"URL duplicate: {url} ~= {articles[url_seen[norm_url]].get('link','')}")
        else:
            url_seen[norm_url] = i

    if url_duplicates:
        articles = [a for i, a in enumerate(articles) if i not in url_duplicates]
        logging.info(f"URL dedup: removed {len(url_duplicates)} duplicates")

    # Phase 2: Title similarity dedup
    deduplicated = []

    # Build token buckets for candidate pairs
    candidates = _build_token_buckets(articles)
    
    # Track which indices have been marked as duplicates
    duplicate_indices: Set[int] = set()
    
    for i, article in enumerate(articles):
        if i in duplicate_indices:
            continue
        
        title = article.get("title", "")
        
        # Mark future candidates as duplicates using SequenceMatcher (only within bucket)
        for j in candidates.get(i, set()):
            if j > i and j not in duplicate_indices:
                other_title = articles[j].get("title", "")
                # Quick length check — titles with >30% length difference are unlikely duplicates
                norm_i = normalize_title(title)
                norm_j = normalize_title(other_title)
                if abs(len(norm_i) - len(norm_j)) > 0.3 * max(len(norm_i), len(norm_j), 1):
                    continue
                similarity = calculate_title_similarity(title, other_title)
                if similarity >= TITLE_SIMILARITY_THRESHOLD:
                    logging.debug(f"Title duplicate: '{other_title}' ~= '{title}' ({similarity:.2f})")
                    duplicate_indices.add(j)
                    _absorb_duplicate(article, articles[j])
            
        deduplicated.append(article)
        
    logging.info(f"Deduplication: {len(articles)} → {len(deduplicated)} articles")
    return deduplicated


# Domains exempt from per-topic limits (multi-author platforms)
DOMAIN_LIMIT_EXEMPT = {"x.com", "twitter.com", "github.com", "reddit.com",
                       "youtube.com", "youtu.be", "arxiv.org"}

def apply_domain_limits(articles: List[Dict[str, Any]], max_per_domain: int = 3) -> List[Dict[str, Any]]:
    """Limit articles per domain within a single topic group.
    
    Should be called per-topic after group_by_topics() to ensure
    each topic gets its own domain budget.
    """
    domain_counts: Dict[str, int] = {}
    result = []
    for article in articles:
        domain = get_domain(article.get("link", ""))
        if domain and domain not in DOMAIN_LIMIT_EXEMPT:
            count = domain_counts.get(domain, 0)
            if count >= max_per_domain:
                logging.debug(f"Domain limit ({max_per_domain}): skipping {domain} article in topic")
                continue
            domain_counts[domain] = count + 1
        result.append(article)
    return result


def load_previous_digests(archive_dir: Path, days: int = 14) -> Set[str]:
    """Load titles from previous digests to avoid repeats.
    
    Args:
        archive_dir: Path to digest archive directory
        days: Number of days to look back (default: 14, increased from 7)
    """
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


def load_topic_order(defaults_dir: Optional[Path], config_dir: Optional[Path] = None) -> Optional[List[str]]:
    """Read configured topic ids, in file order, from defaults + user overlay."""
    if not defaults_dir:
        return None
    try:
        try:
            from config_loader import load_merged_topics
        except ImportError:
            sys.path.append(str(Path(__file__).resolve().parent))
            from config_loader import load_merged_topics
        topics = load_merged_topics(Path(defaults_dir), config_dir)
        ids = [t["id"] for t in topics if t.get("id")]
        return ids or None
    except Exception as e:
        logging.warning(f"Could not read topic order ({e}); using built-in ordering")
        return None


def build_topic_priority(topic_ids: Optional[List[str]] = None) -> Dict[str, int]:
    """Build the topic priority map used to assign multi-topic articles.

    Derived from the order topics appear in topics.json so the map cannot drift
    out of sync with the configured topic ids. `uncategorized` always sorts last.
    """
    ids = list(topic_ids) if topic_ids else list(DEFAULT_TOPIC_ORDER)
    priority = {topic_id: i for i, topic_id in enumerate(ids)}
    priority.setdefault("uncategorized", len(priority))
    return priority


def group_by_topics(articles: List[Dict[str, Any]], dedup_across_topics: bool = True,
                    topic_priority: Optional[Dict[str, int]] = None) -> Dict[str, List[Dict[str, Any]]]:
    """Group articles by their topics.

    Args:
        articles: List of articles to group
        dedup_across_topics: If True, ensure each article appears in only one topic
                           (first topic by priority order)
        topic_priority: topic_id -> rank; lower ranks win when an article matches
                        several topics. Defaults to the built-in topic order.
    """
    topic_groups = {}
    seen_article_ids: Set[str] = set()  # Track which articles have been placed

    if topic_priority is None:
        topic_priority = build_topic_priority()

    # Unknown topics sort after every configured one
    unknown_rank = len(topic_priority) + 1

    # Sort topics by priority for deterministic assignment
    def get_topic_priority(topic: str) -> int:
        return topic_priority.get(topic, unknown_rank)

    for article in articles:
        topics = article.get("topics", [])
        if not topics:
            topics = ["uncategorized"]
        
        # Sort topics by priority to pick the best one
        sorted_topics = sorted(topics, key=get_topic_priority)
        
        # Create unique article ID for tracking
        article_id = normalize_title(article.get("title", ""))
        
        if dedup_across_topics:
            # Check if this article has already been assigned to a topic
            if article_id in seen_article_ids:
                logging.debug(f"Skip duplicate across topics: '{article.get('title', '')[:50]}...'")
                continue
            seen_article_ids.add(article_id)
        
        # Assign to first (highest priority) topic
        primary_topic = sorted_topics[0]
        
        if primary_topic not in topic_groups:
            topic_groups[primary_topic] = []
        
        # Add copy with single topic for cleaner grouping
        article_copy = article.copy()
        article_copy["primary_topic"] = primary_topic
        article_copy["all_topics"] = topics  # Keep original topics for reference
        topic_groups[primary_topic].append(article_copy)
    
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
        "--trending",
        type=Path,
        help="GitHub trending repos JSON file"
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
        "--defaults",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "config" / "defaults",
        help="Skill defaults config dir, used to derive topic priority order"
    )

    parser.add_argument(
        "--config",
        type=Path,
        help="User configuration directory for overlays (optional)"
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
        fd, temp_path = tempfile.mkstemp(prefix="tech-news-digest-merged-", suffix=".json")
        os.close(fd)
        args.output = Path(temp_path)
    
    try:
        # Load source data
        rss_data = load_source_data(args.rss)
        twitter_data = load_source_data(args.twitter)
        web_data = load_source_data(args.web)
        github_data = load_source_data(args.github)
        trending_data = load_source_data(args.trending) if hasattr(args, "trending") else None
        reddit_data = load_source_data(args.reddit)
        
        logger.info(f"Loaded sources - RSS: {rss_data.get('total_articles', 0)}, "
                   f"Twitter: {twitter_data.get('total_articles', 0)}, "
                   f"Web: {web_data.get('total_articles', 0)}, "
                   f"GitHub: {github_data.get('total_articles', 0)} releases + {trending_data.get('total', 0) if trending_data else 0} trending, "
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
                article["display_name"] = source.get("name", "")
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
        

        # Load GitHub trending repos
        if trending_data:
            for repo in trending_data.get("repos", []):
                article = {
                    "title": f"{repo['repo']}: {repo['description']}" if repo.get('description') else repo['repo'],
                    "link": repo.get("url", f"https://github.com/{repo['repo']}"),
                    "snippet": repo.get("description", ""),
                    "date": repo.get("pushed_at", ""),
                    "source": "github-trending",
                    "source_type": "github_trending",
                    "topics": repo.get("topics", []),
                    "stars": repo.get("stars", 0),
                    "daily_stars_est": repo.get("daily_stars_est", 0),
                    "forks": repo.get("forks", 0),
                    "language": repo.get("language", ""),
                    "quality_score": 5 + min(10, repo.get("daily_stars_est", 0) // 10),
                }
                all_articles.append(article)
        total_collected = len(all_articles)
        logger.info(f"Total articles collected: {total_collected}")
        
        # Load previous digest titles for penalty
        previous_titles = set()
        if args.archive_dir:
            previous_titles = load_previous_digests(args.archive_dir)
        
        # Apply previous digest penalty
        all_articles = apply_previous_digest_penalty(all_articles, previous_titles)

        # Deduplicate articles, folding each duplicate's provenance into the survivor
        all_articles = deduplicate_articles(all_articles)

        # Reward stories corroborated across source types
        all_articles = apply_multi_source_bonus(all_articles)

        # Group by topics (with cross-topic deduplication)
        topic_priority = build_topic_priority(load_topic_order(args.defaults, args.config))
        logger.debug(f"Topic priority: {topic_priority}")
        topic_groups = group_by_topics(all_articles, dedup_across_topics=True,
                                       topic_priority=topic_priority)
        
        # Apply per-topic domain limits (max 3 articles per domain per topic)
        for topic in topic_groups:
            before = len(topic_groups[topic])
            topic_groups[topic] = apply_domain_limits(topic_groups[topic])
            after = len(topic_groups[topic])
            if before != after:
                logger.info(f"Domain limits ({topic}): {before} → {after}")
        
        # Recalculate total after domain limits
        total_after_domain_limits = sum(len(articles) for articles in topic_groups.values())


        topic_counts = {topic: len(articles) for topic, articles in topic_groups.items()}
        
        output = {
            "generated": datetime.now(timezone.utc).isoformat(),
            # Mirrored at the top level so run-pipeline.py can report the count
            "total_articles": total_after_domain_limits,
            "input_sources": {
                "rss_articles": rss_data.get("total_articles", 0),
                "twitter_articles": twitter_data.get("total_articles", 0),
                "web_articles": web_data.get("total_articles", 0),
                "github_articles": github_data.get("total_articles", 0),
                "github_trending": trending_data.get("total", 0) if trending_data else 0,
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
                "total_articles": total_after_domain_limits,
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
        
        logger.info("✅ Merged and scored articles:")
        logger.info(f"   Input: {total_collected} articles")
        logger.info(f"   Output: {total_after_domain_limits} articles across {len(topic_groups)} topics")
        logger.info(f"   File: {args.output}")
        
        return 0
        
    except Exception as e:
        logger.error(f"💥 Merge failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())