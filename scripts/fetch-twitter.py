#!/usr/bin/env python3
"""
Fetch Twitter/X posts from KOL accounts using X API.

Reads sources.json, filters Twitter sources, fetches recent posts using
X API v2 with bearer token authentication, and outputs structured JSON.

Usage:
    python3 fetch-twitter.py [--config CONFIG_DIR] [--hours 48] [--output FILE] [--verbose]

Environment:
    X_BEARER_TOKEN - Twitter/X API bearer token (required)
"""

import json
import sys
import os
import argparse
import logging
import time
import tempfile
import re
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode
from pathlib import Path
from typing import Dict, List, Any, Optional

TIMEOUT = 15
MAX_WORKERS = 5  # Lower for API rate limits
RETRY_COUNT = 1
RETRY_DELAY = 2.0
MAX_TWEETS_PER_USER = 10
ID_CACHE_PATH = "/tmp/tech-digest-twitter-id-cache.json"
ID_CACHE_TTL_DAYS = 7

# Twitter API v2 endpoints
API_BASE = "https://api.x.com/2"
USER_LOOKUP_ENDPOINT = f"{API_BASE}/users/by"


def setup_logging(verbose: bool) -> logging.Logger:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)


def get_bearer_token() -> Optional[str]:
    """Get X API bearer token from environment."""
    token = os.getenv('X_BEARER_TOKEN')
    if not token:
        logging.error("X_BEARER_TOKEN environment variable not set")
        return None
    return token


def parse_twitter_date(date_str: str) -> Optional[datetime]:
    """Parse Twitter API date format to datetime."""
    try:
        # Twitter API v2 format: "2023-01-01T12:00:00.000Z"
        if date_str.endswith('Z'):
            date_str = date_str[:-1] + '+00:00'
        return datetime.fromisoformat(date_str)
    except (ValueError, TypeError):
        logging.debug(f"Failed to parse Twitter date: {date_str}")
        return None


def clean_tweet_text(text: str) -> str:
    """Clean tweet text for better display."""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Truncate if too long
    if len(text) > 200:
        text = text[:197] + "..."
    return text


def load_id_cache() -> Dict[str, Any]:
    """Load the username→ID cache from disk."""
    try:
        with open(ID_CACHE_PATH, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_id_cache(cache: Dict[str, Any]) -> None:
    """Save the username→ID cache to disk."""
    try:
        with open(ID_CACHE_PATH, 'w') as f:
            json.dump(cache, f)
    except Exception as e:
        logging.warning(f"Failed to save ID cache: {e}")


def batch_resolve_user_ids(handles: List[str], bearer_token: str, no_cache: bool = False) -> Dict[str, str]:
    """Batch resolve Twitter usernames to user IDs with caching.
    
    Returns a dict mapping lowercase handle → user_id.
    """
    now = time.time()
    cache = {} if no_cache else load_id_cache()
    ttl_seconds = ID_CACHE_TTL_DAYS * 86400
    
    # Check cache for each handle
    result = {}
    to_resolve = []
    for handle in handles:
        key = handle.lower()
        entry = cache.get(key)
        if entry and (now - entry.get("ts", 0)) < ttl_seconds:
            result[key] = entry["id"]
        else:
            to_resolve.append(handle)
    
    if to_resolve:
        logging.info(f"Batch resolving {len(to_resolve)} usernames (cached: {len(result)})")
        # Twitter API supports up to 100 usernames per request
        for i in range(0, len(to_resolve), 100):
            batch = to_resolve[i:i+100]
            url = f"{USER_LOOKUP_ENDPOINT}?{urlencode({'usernames': ','.join(batch)})}"
            headers = {
                "Authorization": f"Bearer {bearer_token}",
                "User-Agent": "TechDigest/2.0"
            }
            try:
                req = Request(url, headers=headers)
                with urlopen(req, timeout=TIMEOUT) as resp:
                    data = json.loads(resp.read().decode())
                
                if 'data' in data:
                    for user in data['data']:
                        key = user['username'].lower()
                        result[key] = user['id']
                        cache[key] = {"id": user['id'], "ts": now}
                        
                # Log errors for users not found
                if 'errors' in data:
                    for err in data['errors']:
                        logging.warning(f"User lookup error: {err.get('detail', err)}")
                        
            except Exception as e:
                logging.error(f"Batch user lookup failed: {e}")
                # Fall back to individual lookups for this batch
                for handle in batch:
                    try:
                        fallback_url = f"{USER_LOOKUP_ENDPOINT}?{urlencode({'usernames': handle})}"
                        req = Request(fallback_url, headers=headers)
                        with urlopen(req, timeout=TIMEOUT) as resp:
                            fallback_data = json.loads(resp.read().decode())
                        if 'data' in fallback_data and fallback_data['data']:
                            key = handle.lower()
                            result[key] = fallback_data['data'][0]['id']
                            cache[key] = {"id": result[key], "ts": now}
                    except Exception as e2:
                        logging.warning(f"Individual lookup failed for @{handle}: {e2}")
        
        if not no_cache:
            save_id_cache(cache)
    else:
        logging.info(f"All {len(result)} usernames resolved from cache")
    
    return result


def fetch_user_tweets(source: Dict[str, Any], bearer_token: str, cutoff: datetime, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Fetch recent tweets for a Twitter user."""
    source_id = source["id"]
    name = source["name"] 
    handle = source["handle"].lstrip('@')  # Remove @ if present
    priority = source["priority"]
    topics = source["topics"]
    
    for attempt in range(RETRY_COUNT + 1):
        try:
            # Build request parameters
            params = {
                "max_results": min(MAX_TWEETS_PER_USER, 100),  # API limit
                "tweet.fields": "created_at,public_metrics,context_annotations,referenced_tweets",
                "expansions": "author_id",
                "user.fields": "verified,public_metrics"
            }
            
            if not user_id:
                # Fallback: resolve individually if no pre-resolved ID
                user_url = f"{USER_LOOKUP_ENDPOINT}?{urlencode({'usernames': handle})}"
                headers = {
                    "Authorization": f"Bearer {bearer_token}",
                    "User-Agent": "TechDigest/2.0"
                }
                
                req = Request(user_url, headers=headers)
                with urlopen(req, timeout=TIMEOUT) as resp:
                    user_data = json.loads(resp.read().decode())
                    
                if 'data' not in user_data or not user_data['data']:
                    raise ValueError(f"User not found: {handle}")
                    
                user_id = user_data['data'][0]['id']
            
            headers = {
                "Authorization": f"Bearer {bearer_token}",
                "User-Agent": "TechDigest/2.0"
            }
            
            # Rate limit: space out API calls
            time.sleep(0.3)
            
            # Then get user tweets
            tweets_url = f"{API_BASE}/users/{user_id}/tweets?{urlencode(params)}"
            req = Request(tweets_url, headers=headers)
            
            with urlopen(req, timeout=TIMEOUT) as resp:
                tweets_data = json.loads(resp.read().decode())
                
            articles = []
            if 'data' in tweets_data:
                for tweet in tweets_data['data']:
                    created_at = parse_twitter_date(tweet.get('created_at', ''))
                    if not created_at or created_at < cutoff:
                        continue
                        
                    # Filter out retweets and replies for cleaner feed
                    text = tweet.get('text', '')
                    if text.startswith('RT @'):
                        continue
                    # Skip replies (but not tweets that merely mention someone)
                    referenced = tweet.get('referenced_tweets', [])
                    if any(ref.get('type') == 'replied_to' for ref in referenced):
                        continue
                        
                    articles.append({
                        "title": clean_tweet_text(text),
                        "link": f"https://twitter.com/{handle}/status/{tweet['id']}",
                        "date": created_at.isoformat(),
                        "topics": topics[:],
                        "metrics": tweet.get('public_metrics', {}),
                        "tweet_id": tweet['id']
                    })
            
            return {
                "source_id": source_id,
                "source_type": "twitter",
                "name": name,
                "handle": handle,
                "priority": priority,
                "topics": topics,
                "status": "ok",
                "attempts": attempt + 1,
                "count": len(articles),
                "articles": articles,
            }
            
        except HTTPError as e:
            if e.code == 429:  # Rate limit
                error_msg = "Rate limit exceeded"
                logging.warning(f"Rate limit hit for @{handle}, attempt {attempt + 1}")
                if attempt < RETRY_COUNT:
                    # Wait longer for rate limit
                    time.sleep(60)
                    continue
            else:
                error_msg = f"HTTP {e.code}: {e.reason}"
                
        except Exception as e:
            error_msg = str(e)[:100]
            logging.debug(f"Attempt {attempt + 1} failed for @{handle}: {error_msg}")
            
        if attempt < RETRY_COUNT:
            time.sleep(RETRY_DELAY * (2 ** attempt))
            continue
            
        return {
            "source_id": source_id,
            "source_type": "twitter",
            "name": name,
            "handle": handle,
            "priority": priority,
            "topics": topics,
            "status": "error",
            "attempts": attempt + 1,
            "error": error_msg,
            "count": 0,
            "articles": [],
        }


def load_twitter_sources(defaults_dir: Path, config_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load Twitter sources from unified configuration with overlay support."""
    try:
        from config_loader import load_merged_sources
    except ImportError:
        # Fallback for relative import
        import sys
        sys.path.append(str(Path(__file__).parent))
        from config_loader import load_merged_sources
    
    # Load merged sources from defaults + optional user overlay
    all_sources = load_merged_sources(defaults_dir, config_dir)
    
    # Filter Twitter sources that are enabled
    twitter_sources = []
    for source in all_sources:
        if source.get("type") == "twitter" and source.get("enabled", True):
            if not source.get("handle"):
                logging.warning(f"Twitter source {source.get('id')} missing handle, skipping")
                continue
            twitter_sources.append(source)
            
    logging.info(f"Loaded {len(twitter_sources)} enabled Twitter sources")
    return twitter_sources


def main():
    """Main Twitter fetching function."""
    parser = argparse.ArgumentParser(
        description="Fetch recent tweets from Twitter/X KOL accounts. "
                   "Requires X_BEARER_TOKEN environment variable.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    export X_BEARER_TOKEN="your_token_here"
    python3 fetch-twitter.py
    python3 fetch-twitter.py --defaults config/defaults --config workspace/config --hours 24 -o results.json
    python3 fetch-twitter.py --config workspace/config --verbose  # backward compatibility
        """
    )
    
    parser.add_argument(
        "--defaults",
        type=Path,
        default=Path("config/defaults"),
        help="Default configuration directory with skill defaults (default: config/defaults)"
    )
    
    parser.add_argument(
        "--config",
        type=Path,
        help="User configuration directory for overlays (optional)"
    )
    
    parser.add_argument(
        "--hours",
        type=int,
        default=48,
        help="Time window in hours for tweets (default: 48)"
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
    
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass username→ID cache"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-fetch even if cached output exists"
    )
    
    args = parser.parse_args()
    logger = setup_logging(args.verbose)
    
    # Resume support: skip if output exists, is valid JSON, and < 1 hour old
    if args.output and args.output.exists() and not args.force:
        try:
            age_seconds = time.time() - args.output.stat().st_mtime
            if age_seconds < 3600:
                with open(args.output, 'r') as f:
                    json.load(f)
                logger.info(f"Skipping (cached output exists): {args.output}")
                return 0
        except (json.JSONDecodeError, OSError):
            pass
    
    # Check for bearer token
    bearer_token = get_bearer_token()
    if not bearer_token:
        logger.warning("X_BEARER_TOKEN not set. Writing empty result and skipping Twitter fetch.")
        empty_result = {"source": "twitter", "fetched_at": datetime.now(timezone.utc).isoformat(), "tweets": [], "skipped_reason": "X_BEARER_TOKEN not set"}
        output_path = args.output or Path("/tmp/td-twitter.json")
        with open(output_path, "w") as f:
            json.dump(empty_result, f, indent=2)
        print(f"Output (empty): {output_path}")
        return 0
    
    # Auto-generate unique output path if not specified
    if not args.output:
        fd, temp_path = tempfile.mkstemp(prefix="tech-digest-twitter-", suffix=".json")
        os.close(fd)
        args.output = Path(temp_path)
    
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=args.hours)
        
        # Backward compatibility: if only --config provided, use old behavior
        if args.config and args.defaults == Path("config/defaults") and not args.defaults.exists():
            logger.debug("Backward compatibility mode: using --config as sole source")
            sources = load_twitter_sources(args.config, None)
        else:
            sources = load_twitter_sources(args.defaults, args.config)
        
        if not sources:
            logger.warning("No Twitter sources found or all disabled")
            
        logger.info(f"Fetching {len(sources)} Twitter accounts (window: {args.hours}h)")
        
        # Batch resolve all usernames to IDs
        all_handles = [s["handle"].lstrip('@') for s in sources]
        user_id_map = batch_resolve_user_ids(all_handles, bearer_token, no_cache=args.no_cache)
        
        results = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {}
            for source in sources:
                handle = source["handle"].lstrip('@')
                resolved_id = user_id_map.get(handle.lower())
                futures[pool.submit(fetch_user_tweets, source, bearer_token, cutoff, resolved_id)] = source
            
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                
                if result["status"] == "ok":
                    logger.debug(f"✅ @{result['handle']}: {result['count']} tweets")
                else:
                    logger.debug(f"❌ @{result['handle']}: {result['error']}")

        # Sort: priority first, then by article count
        results.sort(key=lambda x: (not x.get("priority", False), -x.get("count", 0)))

        ok_count = sum(1 for r in results if r["status"] == "ok")
        total_tweets = sum(r.get("count", 0) for r in results)

        output = {
            "generated": datetime.now(timezone.utc).isoformat(),
            "source_type": "twitter",
            "defaults_dir": str(args.defaults),
            "config_dir": str(args.config) if args.config else None,
            "hours": args.hours,
            "sources_total": len(results),
            "sources_ok": ok_count,
            "total_articles": total_tweets,
            "sources": results,
        }

        # Write output
        json_str = json.dumps(output, ensure_ascii=False, indent=2)
        with open(args.output, "w", encoding='utf-8') as f:
            f.write(json_str)

        logger.info(f"✅ Done: {ok_count}/{len(results)} accounts ok, "
                   f"{total_tweets} tweets → {args.output}")
        
        return 0
        
    except Exception as e:
        logger.error(f"💥 Twitter fetch failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())