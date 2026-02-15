#!/usr/bin/env python3
"""
Fetch web search results for tech digest topics.

Reads topics.json, performs web searches for each topic's search queries,
and outputs structured JSON with search results tagged by topics.

Usage:
    python3 fetch-web.py [--config CONFIG_DIR] [--freshness 48h] [--output FILE] [--verbose]

Note: This script can use Brave Search API if BRAVE_API_KEY is set, otherwise
it provides a JSON interface for agents to use web_search tool.
"""

import json
import sys
import os
import argparse
import logging
import time
import tempfile
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import URLError, HTTPError

TIMEOUT = 15
MAX_RESULTS_PER_QUERY = 5
RETRY_COUNT = 1
RETRY_DELAY = 2.0

# Brave Search API
BRAVE_API_BASE = "https://api.search.brave.com/res/v1/web/search"


def setup_logging(verbose: bool) -> logging.Logger:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)


def get_brave_api_key() -> Optional[str]:
    """Get Brave Search API key from environment."""
    return os.getenv('BRAVE_API_KEY')


def search_brave(query: str, api_key: str, freshness: Optional[str] = None) -> Dict[str, Any]:
    """Perform search using Brave Search API."""
    params = {
        'q': query,
        'count': MAX_RESULTS_PER_QUERY,
        'search_lang': 'en',
        'country': 'ALL',
        'safesearch': 'moderate',
        'text_decorations': 'false'
    }
    
    if freshness:
        params['freshness'] = freshness
    
    url = f"{BRAVE_API_BASE}?{urlencode(params)}"
    headers = {
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip',
        'X-Subscription-Token': api_key,
        'User-Agent': 'TechDigest/2.0'
    }
    
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
            
        results = []
        if 'web' in data and 'results' in data['web']:
            for result in data['web']['results']:
                results.append({
                    'title': result.get('title', ''),
                    'link': result.get('url', ''),
                    'snippet': result.get('description', ''),
                    'date': datetime.now(timezone.utc).isoformat()  # Search timestamp
                })
                
        return {
            'status': 'ok',
            'query': query,
            'results': results,
            'total': len(results)
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'query': query,
            'error': str(e)[:100],
            'results': [],
            'total': 0
        }


def filter_content(text: str, must_include: List[str], exclude: List[str]) -> bool:
    """Check if content matches inclusion/exclusion criteria."""
    text_lower = text.lower()
    
    # Check must_include (any match)
    if must_include:
        has_required = any(keyword.lower() in text_lower for keyword in must_include)
        if not has_required:
            return False
    
    # Check exclude (any match disqualifies)
    if exclude:
        has_excluded = any(keyword.lower() in text_lower for keyword in exclude)
        if has_excluded:
            return False
            
    return True


def search_topic_brave(topic: Dict[str, Any], api_key: str, freshness: Optional[str] = None) -> Dict[str, Any]:
    """Search all queries for a topic using Brave API."""
    topic_id = topic["id"]
    queries = topic["search"]["queries"]
    must_include = topic["search"].get("must_include", [])
    exclude = topic["search"].get("exclude", [])
    
    all_results = []
    query_stats = []
    
    for query in queries:
        search_result = search_brave(query, api_key, freshness)
        query_stats.append({
            'query': query,
            'status': search_result['status'],
            'count': search_result['total']
        })
        
        if search_result['status'] == 'ok':
            # Filter results based on content criteria
            for result in search_result['results']:
                combined_text = f"{result['title']} {result['snippet']}"
                if filter_content(combined_text, must_include, exclude):
                    result['topics'] = [topic_id]
                    all_results.append(result)
        
        # Be nice to the API
        time.sleep(0.5)
    
    return {
        'topic_id': topic_id,
        'status': 'ok',
        'queries_executed': len(queries),
        'queries_ok': sum(1 for q in query_stats if q['status'] == 'ok'),
        'query_stats': query_stats,
        'count': len(all_results),
        'articles': all_results
    }


def generate_search_interface(topic: Dict[str, Any]) -> Dict[str, Any]:
    """Generate JSON interface for agent web search."""
    topic_id = topic["id"]
    queries = topic["search"]["queries"]
    must_include = topic["search"].get("must_include", [])
    exclude = topic["search"].get("exclude", [])
    
    return {
        'topic_id': topic_id,
        'status': 'interface',
        'search_required': True,
        'queries': queries,
        'filters': {
            'must_include': must_include,
            'exclude': exclude
        },
        'instructions': [
            f"Use web_search tool for each query in 'queries' list",
            f"Filter results using 'filters.must_include' and 'filters.exclude'",
            f"Tag matching articles with topic: '{topic_id}'",
            f"Expected max results per query: {MAX_RESULTS_PER_QUERY}"
        ],
        'count': 0,
        'articles': []
    }


def load_topics(config_dir: Path) -> List[Dict[str, Any]]:
    """Load topics from configuration."""
    topics_path = config_dir / "topics.json"
    
    try:
        with open(topics_path) as f:
            data = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Topics config not found: {topics_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in topics config: {e}")
        
    topics = data.get("topics", [])
    logging.info(f"Loaded {len(topics)} topics for web search")
    return topics


def convert_freshness(hours: int) -> str:
    """Convert hours to Brave API freshness format."""
    if hours <= 24:
        return "pd"  # past day
    elif hours <= 168:  # 7 days
        return "pw"  # past week
    elif hours <= 720:  # 30 days
        return "pm"  # past month
    else:
        return "py"  # past year


def main():
    """Main web search function."""
    parser = argparse.ArgumentParser(
        description="Perform web searches for tech digest topics. "
                   "Can use Brave Search API (BRAVE_API_KEY) or generate interface for agents.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # With Brave API
    export BRAVE_API_KEY="your_key_here"
    python3 fetch-web.py --freshness 24h
    
    # Without API (generates interface)
    python3 fetch-web.py --output web-search-interface.json
        """
    )
    
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/defaults"),
        help="Configuration directory (default: config/defaults)"
    )
    
    parser.add_argument(
        "--freshness",
        default="48h",
        help="Search freshness: 24h, 48h, 1w, 1m (default: 48h)"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output JSON path (default: auto-generated temp file)"
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
        fd, temp_path = tempfile.mkstemp(prefix="tech-digest-web-", suffix=".json")
        os.close(fd)
        args.output = Path(temp_path)
    
    try:
        topics = load_topics(args.config)
        
        if not topics:
            logger.warning("No topics found")
            return 1
            
        # Check for Brave API
        api_key = get_brave_api_key()
        if api_key:
            logger.info(f"Using Brave Search API for {len(topics)} topics")
            
            # Convert freshness to hours for API
            freshness_hours = int(args.freshness.rstrip('h'))
            brave_freshness = convert_freshness(freshness_hours)
            
            results = []
            for topic in topics:
                if not topic.get("search", {}).get("queries"):
                    logger.debug(f"Topic {topic['id']} has no search queries, skipping")
                    continue
                    
                logger.debug(f"Searching topic: {topic['id']}")
                result = search_topic_brave(topic, api_key, brave_freshness)
                results.append(result)
            
            total_articles = sum(r.get("count", 0) for r in results)
            ok_topics = sum(1 for r in results if r["status"] == "ok")
            
            output = {
                "generated": datetime.now(timezone.utc).isoformat(),
                "source_type": "web",
                "config_dir": str(args.config),
                "freshness": args.freshness,
                "api_used": "brave",
                "topics_total": len(results),
                "topics_ok": ok_topics,
                "total_articles": total_articles,
                "topics": results
            }
            
            logger.info(f"✅ Searched {ok_topics}/{len(results)} topics, "
                       f"{total_articles} articles found")
            
        else:
            logger.info("No BRAVE_API_KEY found, generating search interface for agents")
            
            results = []
            for topic in topics:
                if not topic.get("search", {}).get("queries"):
                    continue
                result = generate_search_interface(topic)
                results.append(result)
            
            output = {
                "generated": datetime.now(timezone.utc).isoformat(),
                "source_type": "web",
                "config_dir": str(args.config),
                "freshness": args.freshness,
                "api_used": "interface",
                "topics_total": len(results),
                "topics_ok": 0,  # Requires manual execution
                "total_articles": 0,
                "topics": results,
                "agent_instructions": [
                    "This file contains search interface for web_search tool",
                    "For each topic, execute the queries using web_search",
                    "Apply the filters (must_include/exclude) to results",
                    "Tag matching articles with the topic_id",
                    "Update this file with results for merge-sources.py"
                ]
            }
            
            logger.info(f"✅ Generated search interface for {len(results)} topics")

        # Write output
        json_str = json.dumps(output, ensure_ascii=False, indent=2)
        with open(args.output, "w", encoding='utf-8') as f:
            f.write(json_str)

        logger.info(f"Output written to: {args.output}")
        return 0
        
    except Exception as e:
        logger.error(f"💥 Web search failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())