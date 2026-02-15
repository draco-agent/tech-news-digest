#!/usr/bin/env python3
"""
Fetch GitHub releases from unified sources configuration.

Reads sources.json, filters GitHub sources, fetches releases in parallel with retry
mechanism, and outputs structured JSON with releases tagged by topics.

Usage:
    python3 fetch-github.py [--config CONFIG_DIR] [--hours 48] [--output FILE] [--verbose]
"""

import json
import re
import sys
import os
import argparse
import logging
import time
import tempfile
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from pathlib import Path
from typing import Dict, List, Any, Optional

TIMEOUT = 15
MAX_WORKERS = 10
MAX_RELEASES_PER_REPO = 20
RETRY_COUNT = 2
RETRY_DELAY = 2.0  # seconds


def setup_logging(verbose: bool) -> logging.Logger:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)


def strip_markdown(text: str) -> str:
    """Strip basic markdown formatting from text."""
    if not text:
        return ""
    
    # Remove links [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Remove bold/italic **text** or *text* -> text
    text = re.sub(r'\*+([^*]+)\*+', r'\1', text)
    # Remove headers ### -> 
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    # Remove code blocks ```
    text = re.sub(r'```[^`]*```', '', text, flags=re.DOTALL)
    # Remove inline code `text` -> text
    text = re.sub(r'`([^`]+)`', r'\1', text)
    
    return text.strip()


def truncate_summary(text: str, max_chars: int = 200) -> str:
    """Truncate text to specified length with ellipsis."""
    if not text:
        return ""
    
    # Strip markdown first
    clean_text = strip_markdown(text)
    
    # Remove extra whitespace
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    if len(clean_text) <= max_chars:
        return clean_text
    
    # Find last space before limit
    truncated = clean_text[:max_chars]
    last_space = truncated.rfind(' ')
    
    if last_space > max_chars * 0.8:  # Don't cut too much
        truncated = truncated[:last_space]
    
    return truncated + "..."


def parse_github_date(date_str: str) -> Optional[datetime]:
    """Parse GitHub ISO date string."""
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return None


def get_repo_name(repo: str) -> str:
    """Extract repository name from owner/repo format."""
    return repo.split('/')[-1] if '/' in repo else repo


def fetch_releases_with_retry(source: Dict[str, Any], cutoff: datetime, github_token: Optional[str] = None) -> Dict[str, Any]:
    """Fetch GitHub releases with retry mechanism."""
    source_id = source["id"]
    name = source["name"]
    repo = source["repo"]
    priority = source["priority"]
    topics = source["topics"]
    
    repo_name = get_repo_name(repo)
    api_url = f"https://api.github.com/repos/{repo}/releases"
    
    # Setup headers
    headers = {
        "User-Agent": "TechDigest/2.0",
        "Accept": "application/vnd.github.v3+json",
    }
    if github_token:
        headers["Authorization"] = f"token {github_token}"
    
    for attempt in range(RETRY_COUNT + 1):
        try:
            req = Request(api_url, headers=headers)
            with urlopen(req, timeout=TIMEOUT) as resp:
                if resp.status != 200:
                    raise HTTPError(resp.url, resp.status, f"HTTP {resp.status}", resp.headers, None)
                
                content = resp.read().decode("utf-8", errors="replace")
                releases_data = json.loads(content)
            
            articles = []
            for release in releases_data[:MAX_RELEASES_PER_REPO]:
                # Skip drafts and prereleases optionally
                if release.get("draft", False):
                    continue
                
                published_at = release.get("published_at")
                if not published_at:
                    continue
                
                pub_date = parse_github_date(published_at)
                if not pub_date or pub_date < cutoff:
                    continue
                
                tag_name = release.get("tag_name", "")
                title = f"{repo_name} {tag_name}"
                link = release.get("html_url", "")
                body = release.get("body", "")
                summary = truncate_summary(body, 200)
                
                if title and link:
                    articles.append({
                        "title": title,
                        "link": link,
                        "date": pub_date.isoformat(),
                        "summary": summary,
                        "topics": topics[:],
                    })
            
            return {
                "source_id": source_id,
                "source_type": "github",
                "name": name,
                "repo": repo,
                "priority": priority,
                "topics": topics,
                "status": "ok",
                "attempts": attempt + 1,
                "count": len(articles),
                "articles": articles,
            }
            
        except Exception as e:
            error_msg = str(e)[:100]
            logging.debug(f"Attempt {attempt + 1} failed for {name}: {error_msg}")
            
            if attempt < RETRY_COUNT:
                # Exponential backoff with jitter for API rate limits
                delay = RETRY_DELAY * (2 ** attempt)
                time.sleep(delay)
                continue
            else:
                return {
                    "source_id": source_id,
                    "source_type": "github",
                    "name": name,
                    "repo": repo,
                    "priority": priority,
                    "topics": topics,
                    "status": "error",
                    "attempts": attempt + 1,
                    "error": error_msg,
                    "count": 0,
                    "articles": [],
                }


def load_sources(defaults_dir: Path, config_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load GitHub sources from unified configuration with overlay support."""
    try:
        from config_loader import load_merged_sources
    except ImportError:
        # Fallback for relative import
        import sys
        sys.path.append(str(Path(__file__).parent))
        from config_loader import load_merged_sources
    
    # Load merged sources from defaults + optional user overlay
    all_sources = load_merged_sources(defaults_dir, config_dir)
    
    # Filter GitHub sources that are enabled
    github_sources = []
    for source in all_sources:
        if source.get("type") == "github" and source.get("enabled", True):
            # Validate required fields
            if not source.get("repo"):
                logging.warning(f"GitHub source {source.get('id', 'unknown')} missing repo field, skipping")
                continue
            github_sources.append(source)
    
    logging.info(f"Loaded {len(github_sources)} enabled GitHub sources")
    return github_sources


def main():
    """Main GitHub releases fetching function."""
    parser = argparse.ArgumentParser(
        description="Parallel GitHub releases fetcher for tech-digest. "
                   "Fetches enabled GitHub sources from unified configuration, "
                   "filters by time window, and outputs structured release data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 fetch-github.py
    python3 fetch-github.py --defaults config/defaults --config workspace/config --hours 168 -o results.json
    python3 fetch-github.py --config workspace/config --verbose  # backward compatibility
    
Environment Variables:
    GITHUB_TOKEN    GitHub personal access token (optional, improves rate limits)
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
        default=168,  # 1 week default for releases
        help="Time window in hours for releases (default: 168 = 1 week)"
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
        fd, temp_path = tempfile.mkstemp(prefix="tech-digest-github-", suffix=".json")
        os.close(fd)
        args.output = Path(temp_path)
    
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=args.hours)
        
        # Backward compatibility: if only --config provided, use old behavior
        if args.config and args.defaults == Path("config/defaults") and not args.defaults.exists():
            logger.debug("Backward compatibility mode: using --config as sole source")
            sources = load_sources(args.config, None)
        else:
            sources = load_sources(args.defaults, args.config)
        
        if not sources:
            logger.warning("No GitHub sources found or all disabled")
        
        logger.info(f"Fetching {len(sources)} GitHub repositories (window: {args.hours}h)")
        
        # Check for GitHub token
        github_token = os.environ.get("GITHUB_TOKEN")
        if github_token:
            logger.debug("Using GitHub token for authentication")
        else:
            logger.info("No GITHUB_TOKEN found, using unauthenticated requests (lower rate limit)")
        
        results = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(fetch_releases_with_retry, source, cutoff, github_token): source 
                      for source in sources}
            
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                
                if result["status"] == "ok":
                    logger.debug(f"✅ {result['name']}: {result['count']} releases")
                else:
                    logger.debug(f"❌ {result['name']}: {result['error']}")

        # Sort: priority first, then by release count
        results.sort(key=lambda x: (not x.get("priority", False), -x.get("count", 0)))

        ok_count = sum(1 for r in results if r["status"] == "ok")
        total_articles = sum(r.get("count", 0) for r in results)

        output = {
            "generated": datetime.now(timezone.utc).isoformat(),
            "source_type": "github",
            "defaults_dir": str(args.defaults),
            "config_dir": str(args.config) if args.config else None,
            "hours": args.hours,
            "github_token_used": github_token is not None,
            "sources_total": len(results),
            "sources_ok": ok_count,
            "total_articles": total_articles,
            "sources": results,
        }

        # Write output
        json_str = json.dumps(output, ensure_ascii=False, indent=2)
        with open(args.output, "w", encoding='utf-8') as f:
            f.write(json_str)

        logger.info(f"✅ Done: {ok_count}/{len(results)} repos ok, "
                   f"{total_articles} releases → {args.output}")
        
        return 0
        
    except Exception as e:
        logger.error(f"💥 GitHub fetch failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())