# Changelog

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
