# Changelog

## v2.6.0

- **Date Timezone Fix**: Added `<DATE>` placeholder to digest prompt — report date now explicitly provided by caller, preventing UTC/local timezone mismatch
- **Mandatory Links in KOL/Trending**: KOL Updates and Twitter/X Trending sections now require source URLs for every entry (no link-free entries allowed)
- **URL Sanitization**: `resolve_link()` in fetch-rss.py rejects non-HTTP(S) schemes (javascript:, data:, etc.)
- **Third-Party Source Annotation**: Community-maintained RSS mirrors (e.g. anthropic-rss) are annotated with notes in sources.json
- **Security Documentation**: Added Security Considerations section to SKILL.md covering shell execution model, input sanitization, and network access

## v2.5.0

- **Twitter Reply Filter Fix**: Use `referenced_tweets` field instead of text prefix to distinguish replies from mentions
- **Scoring Consistency**: digest-prompt.md now matches code (`PENALTY_OLD_REPORT = -5`)
- **Template Version Cleanup**: Removed hardcoded version numbers from email/markdown/telegram templates
- **Article Count Fix**: `merge-sources.py` uses deduplicated count instead of inflated topic-grouped sum
- **Pipeline Resume Support**: All fetch scripts support `--force` flag; skip if cached output < 1 hour old
- **Source Health Monitoring**: New `scripts/source-health.py` tracks per-source success/failure history
- **End-to-End Test**: New `scripts/test-pipeline.sh` smoke test for the full pipeline
- **Archive Auto-Cleanup**: digest-prompt.md documents 90-day archive retention policy
- **Twitter Rate Limiting**: Moved sleep into `fetch_user_tweets` for actual per-request rate limiting
- **Web Article Scoring**: Web articles now use `calculate_base_score` instead of hardcoded 1.0
- **Dead Code Removal**: Removed unused `load_sources_with_overlay` / `load_topics_with_overlay` wrappers

## v2.4.0

- **Batch Twitter Lookup**: Single API call for all username→ID resolution + 7-day local cache (~88→~45 API calls)
- **Smart Dedup**: Token-based bucketing replaces O(n²) SequenceMatcher — only compares articles sharing 2+ key tokens
- **Conditional Fetch (RSS)**: ETag/Last-Modified caching, 304 responses skip parsing
- **Conditional Fetch (GitHub)**: Same caching pattern + prominent warning when GITHUB_TOKEN is unset
- **`--no-cache` flag**: All fetch scripts support bypassing cache

## v2.3.0

- **GitHub Releases**: 19 tracked repositories as a fourth data source
- **Data Source Stats Footer**: Pipeline statistics in all templates
- **Twitter Queries**: Added to all 4 topics for better coverage
- **Simplified Cron Prompts**: Reference digest-prompt.md with parameters only

## v2.1.0

- **Unified Source Model**: Single `sources.json` for RSS, Twitter, and web sources
- **Enhanced Topics**: Richer topic definitions with search queries and filters
- **Pipeline Scripts**: Modular fetch → merge → template workflow
- **Quality Scoring**: Multi-source detection, deduplication, priority weighting
- **Multiple Templates**: Discord, email, and markdown output formats
- **Configuration Validation**: JSON schema validation and consistency checks
- **User Customization**: Workspace config overrides for personalization
