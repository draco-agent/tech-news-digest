# Changelog

## v3.3.1

- **Remove anthropic-rss mirror**: Removed third-party community RSS mirror (`anthropic-rss`) to eliminate supply chain risk flagged by VirusTotal Code Insights. Anthropic coverage remains via Twitter KOL, GitHub releases, and Reddit sources.
- **Remove Third-Party RSS Sources section** from SKILL.md security docs (no longer applicable)

## v3.3.0

- **RSS Domain Validation**: New `expected_domains` field in sources.json rejects articles from unexpected origins (applied to anthropic-rss mirror)
- **Email Shell Safety**: HTML body written to temp file before CLI delivery; subjects restricted to static format strings
- **Discord Embed Suppression**: Footer links wrapped in `<>` to prevent preview embeds

## v3.2.1

- **Mandatory Reddit Execution**: Agent explicitly required to run `fetch-reddit.py` script — cannot skip or generate fake output

## v3.2.0

- **Unified English Templates**: All prompt instructions, section titles, stats footer, and example content standardized to English. Output language controlled by `<LANGUAGE>` placeholder at runtime.

## v3.1.0

- **Executive Summary**: 2-4 sentence overview of top stories at the beginning of each digest
- **Community Buzz Section**: Merged Twitter/X Trending and Reddit Hot Discussions into unified 🔥 社区热议
- **Reddit in Topic Sections**: Reddit posts now selected by quality_score alongside other sources
- **Digest Footer Branding**: Shows skill version and OpenClaw link
- **Prompt Fix**: Agent explicitly instructed to read Reddit data from merged JSON

## v3.0.0

- **Reddit Data Source**: New `fetch-reddit.py` script — 5th data layer using Reddit's public JSON API (no auth required). 13 subreddits: r/MachineLearning, r/LocalLLaMA, r/CryptoCurrency, r/artificial, r/ethereum, r/ChatGPT, r/singularity, r/OpenAI, r/Bitcoin, r/programming, r/Anthropic, r/defi, r/ExperiencedDevs
- **Reddit Score Bonus**: Posts with score > 500 get +5, > 200 get +3, > 100 get +1 in quality scoring
- **10 New Non-Reddit Sources**: Ben's Bites, The Decoder, a16z Crypto, Bankless (RSS); @ClementDelangue, @GregBrockman, @zuck (Twitter); MCP Servers, DeepSeek-V3, Meta Llama (GitHub)
- **Tweet Engagement Metrics**: KOL entries display `👁|💬|🔁|❤️` stats in inline code blocks across all templates
- **Date Timezone Fix**: Report date explicitly provided via `<DATE>` placeholder, preventing UTC/local mismatch
- **Mandatory Links**: KOL Updates and Twitter/X Trending sections require source URLs for every entry
- **Graceful Twitter Degradation**: Missing `X_BEARER_TOKEN` outputs empty JSON instead of failing
- **URL Sanitization**: `resolve_link()` rejects non-HTTP(S) schemes
- **Security Documentation**: Added Security Considerations section to SKILL.md
- **Total Sources**: 132 (50 RSS + 47 Twitter + 22 GitHub + 13 Reddit + 4 web search topics)

## v2.8.1

- **Metrics Data Fix**: Agent now required to read actual `metrics` values from Twitter JSON data instead of defaulting to 0
- **Email Template Enhancement**: Added KOL metrics and Twitter/X Trending section to email template

## v2.8.0

- **Tweet Metrics Display**: KOL entries show `👁|💬|🔁|❤️` engagement stats wrapped in inline code to prevent emoji enlargement on Discord
- **Standardized Metrics Format**: Fixed 4-metric order, show 0 for missing values, one tweet per bullet with own URL
- **10 New Sources (119 total)**: Ben's Bites, The Decoder, a16z Crypto, Bankless (RSS); @ClementDelangue, @GregBrockman, @zuck (Twitter); MCP Servers, DeepSeek-V3, Meta Llama (GitHub)

## v2.7.0

- **Tweet Engagement Metrics**: KOL Updates now display 👁 views, 💬 replies, 🔁 retweets, ❤️ likes from Twitter public_metrics across all templates (Discord, Email, Telegram)

## v2.6.1

- **Graceful Twitter Degradation**: Missing `X_BEARER_TOKEN` now outputs empty JSON and exits 0 instead of failing with exit code 1, allowing the pipeline to continue without Twitter data

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
