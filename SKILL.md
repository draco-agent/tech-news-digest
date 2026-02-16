---
name: tech-news-digest
description: Generate tech news digests with unified source model, quality scoring, and multi-format output. Four-layer data collection from RSS feeds, Twitter/X KOLs, GitHub releases, and web search. Pipeline-based scripts with retry mechanisms and deduplication. Supports Discord, email, and markdown templates.
version: "2.8.1"
homepage: https://github.com/draco-agent/tech-news-digest
source: https://github.com/draco-agent/tech-news-digest
env:
  - name: X_BEARER_TOKEN
    required: false
    description: Twitter/X API bearer token for KOL monitoring
  - name: BRAVE_API_KEY
    required: false
    description: Brave Search API key for web search layer
  - name: GITHUB_TOKEN
    required: false
    description: GitHub personal access token for higher API rate limits
---

# Tech News Digest

Automated tech news digest system with unified data source model, quality scoring pipeline, and template-based output generation.

## Quick Start

1. **Configuration Setup**: Default configs are in `config/defaults/`. Copy to workspace for customization:
   ```bash
   mkdir -p workspace/config
   cp config/defaults/sources.json workspace/config/
   cp config/defaults/topics.json workspace/config/
   ```

2. **Environment Variables**: 
   - `X_BEARER_TOKEN` - Twitter API bearer token (optional)
   - `BRAVE_API_KEY` - Brave Search API key (optional)
   - `GITHUB_TOKEN` - GitHub personal access token (optional, improves rate limits)

3. **Generate Digest**:
   ```bash
   # Full pipeline
   python3 scripts/fetch-rss.py --config workspace/config
   python3 scripts/fetch-twitter.py --config workspace/config  
   python3 scripts/fetch-web.py --config workspace/config
   python3 scripts/fetch-github.py --config workspace/config
   python3 scripts/merge-sources.py --rss rss.json --twitter twitter.json --web web.json --github github.json
   ```

4. **Use Templates**: Apply Discord, email, or markdown templates to merged output

## Configuration Files

### `sources.json` - Unified Data Sources
```json
{
  "sources": [
    {
      "id": "openai-rss",
      "type": "rss",
      "name": "OpenAI Blog",
      "url": "https://openai.com/blog/rss.xml",
      "enabled": true,
      "priority": true,
      "topics": ["llm", "ai-agent"],
      "note": "Official OpenAI updates"
    },
    {
      "id": "sama-twitter",
      "type": "twitter", 
      "name": "Sam Altman",
      "handle": "sama",
      "enabled": true,
      "priority": true,
      "topics": ["llm", "frontier-tech"],
      "note": "OpenAI CEO"
    }
  ]
}
```

### `topics.json` - Enhanced Topic Definitions
```json
{
  "topics": [
    {
      "id": "llm",
      "emoji": "🧠",
      "label": "LLM / Large Models",
      "description": "Large Language Models, foundation models, breakthroughs",
      "search": {
        "queries": ["LLM latest news", "large language model breakthroughs"],
        "must_include": ["LLM", "large language model", "foundation model"],
        "exclude": ["tutorial", "beginner guide"]
      },
      "display": {
        "max_items": 8,
        "style": "detailed"
      }
    }
  ]
}
```

## Scripts Pipeline

### 1. `fetch-rss.py` - RSS Feed Fetcher
```bash
python3 scripts/fetch-rss.py [--config CONFIG_DIR] [--hours 48] [--output FILE] [--verbose]
```
- **Features**: Parallel fetching, retry mechanism, feedparser + regex fallback
- **Output**: Structured JSON with articles tagged by topics
- **Timeout**: 15s per feed with exponential backoff retry

### 2. `fetch-twitter.py` - Twitter/X KOL Monitor  
```bash
python3 scripts/fetch-twitter.py [--config CONFIG_DIR] [--hours 48] [--output FILE]
```
- **Requirements**: `X_BEARER_TOKEN` environment variable
- **Features**: Rate limit handling, engagement metrics, reply filtering
- **API**: Twitter API v2 with app-only authentication

### 3. `fetch-web.py` - Web Search Engine
```bash
python3 scripts/fetch-web.py [--config CONFIG_DIR] [--freshness 48h] [--output FILE]
```
- **With Brave API**: Automated search execution (requires `BRAVE_API_KEY`)
- **Without API**: Generates search interface for agents to execute
- **Filtering**: Content-based inclusion/exclusion rules

### 4. `fetch-github.py` - GitHub Releases Monitor
```bash
python3 scripts/fetch-github.py [--config CONFIG_DIR] [--hours 168] [--output FILE]
```
- **Features**: Parallel repository monitoring, release filtering, markdown stripping
- **Authentication**: Optional `GITHUB_TOKEN` for higher rate limits
- **Output**: Structured JSON with releases tagged by topics

### 5. `merge-sources.py` - Quality Scoring & Deduplication
```bash
python3 scripts/merge-sources.py --rss rss.json --twitter twitter.json --web web.json --github github.json
```
- **Quality Scoring**: Priority sources (+3), multi-source (+5), recency (+2), engagement (+1)
- **Deduplication**: Title similarity detection (85% threshold), domain saturation limits
- **Previous Digest Penalty**: Avoids repeating articles from recent digests
- **Output**: Topic-grouped articles with quality scores

### 6. `validate-config.py` - Configuration Validator
```bash
python3 scripts/validate-config.py [--defaults DEFAULTS_DIR] [--config CONFIG_DIR] [--verbose]
```
- **JSON Schema**: Validates structure and required fields
- **Consistency**: Checks topic references, duplicate IDs
- **Source Types**: Validates RSS URLs, Twitter handles

## User Customization

### Workspace Configuration Override
Place custom configs in `workspace/config/` to override defaults:

- **Sources**: Append new sources, disable defaults with `"enabled": false`
- **Topics**: Override topic definitions, search queries, display settings
- **Merge Logic**: 
  - Sources with same `id` → user version takes precedence
  - Sources with new `id` → appended to defaults
  - Topics with same `id` → user version completely replaces default

### Example Workspace Override
```json
// workspace/config/sources.json
{
  "sources": [
    {
      "id": "simonwillison-rss",
      "enabled": false,
      "note": "Disabled: too noisy for my use case"
    },
    {
      "id": "my-custom-blog", 
      "type": "rss",
      "name": "My Custom Tech Blog",
      "url": "https://myblog.com/rss",
      "enabled": true,
      "priority": true,
      "topics": ["frontier-tech"]
    }
  ]
}
```

## Templates & Output

### Discord Template (`references/templates/discord.md`)
- Bullet list format with link suppression (`<link>`)
- Mobile-optimized, emoji headers
- 2000 character limit awareness

### Email Template (`references/templates/email.md`) 
- Rich metadata, technical stats, archive links
- Executive summary, top articles section
- HTML-compatible formatting

### Markdown Template (`references/templates/markdown.md`)
- GitHub-compatible tables and formatting
- Technical details section
- Expandable sections support

## Default Sources (109 total)

- **RSS Feeds (46)**: AI labs, tech blogs, crypto news, Chinese tech media
- **Twitter/X KOLs (44)**: AI researchers, crypto leaders, tech executives
- **GitHub Repos (19)**: Major open-source projects (LangChain, vLLM, Foundry, etc.)
- **Web Search (4 topics)**: LLM, AI Agent, Crypto, Frontier Tech

All sources pre-configured with appropriate topic tags and priority levels.

## Dependencies

```bash
pip install -r requirements.txt
```

**Optional but Recommended**:
- `feedparser>=6.0.0` - Better RSS parsing (fallback to regex if unavailable)
- `jsonschema>=4.0.0` - Configuration validation

**All scripts work with Python 3.8+ standard library only.**

## Migration from v1.x

1. **Config Migration**: Old config files are automatically migrated to new structure
2. **Script Updates**: New command-line interfaces with better error handling
3. **Template System**: Replace old prompt-based generation with template system
4. **Quality Scoring**: New scoring system affects article ranking

## Monitoring & Operations

### Health Checks
```bash
# Validate configuration
python3 scripts/validate-config.py --verbose

# Test RSS feeds
python3 scripts/fetch-rss.py --hours 1 --verbose

# Check Twitter API
python3 scripts/fetch-twitter.py --hours 1 --verbose
```

### Archive Management
- Digests automatically archived to `workspace/archive/tech-digest/`
- Previous digest titles used for duplicate detection
- Old archives cleaned automatically (90+ days)

### Error Handling
- **Network Failures**: Retry with exponential backoff
- **Rate Limits**: Automatic retry with appropriate delays
- **Invalid Content**: Graceful degradation, detailed logging
- **Configuration Errors**: Schema validation with helpful messages

## API Keys & Environment

Set in `~/.zshenv` or similar:
```bash
export X_BEARER_TOKEN="your_twitter_bearer_token"
export BRAVE_API_KEY="your_brave_search_api_key"  # Optional
```

- **Twitter**: Read-only bearer token, pay-per-use pricing
- **Brave Search**: Optional, fallback to agent web_search if unavailable

## Cron / Scheduled Task Integration

### OpenClaw Cron (Recommended)

The cron prompt should **NOT** hardcode the pipeline steps. Instead, reference `references/digest-prompt.md` and only pass configuration parameters. This ensures the pipeline logic stays in the skill repo and is consistent across all installations.

#### Daily Digest Cron Prompt
```
读取 <SKILL_DIR>/references/digest-prompt.md，按照其中的完整流程生成日报。

用以下参数替换占位符：
- MODE = daily
- TIME_WINDOW = past 1-2 days
- FRESHNESS = pd
- RSS_HOURS = 48
- ITEMS_PER_SECTION = 3-5
- BLOG_PICKS_COUNT = 2-3
- EXTRA_SECTIONS = （无）
- SUBJECT = Daily Tech Digest - YYYY-MM-DD
- WORKSPACE = <your workspace path>
- SKILL_DIR = <your skill install path>
- DISCORD_CHANNEL_ID = <your channel id>
- EMAIL = （optional）
- LANGUAGE = Chinese
- TEMPLATE = discord

严格按 prompt 模板中的步骤执行，不要跳过任何步骤。
```

#### Weekly Digest Cron Prompt
```
读取 <SKILL_DIR>/references/digest-prompt.md，按照其中的完整流程生成周报。

用以下参数替换占位符：
- MODE = weekly
- TIME_WINDOW = past 7 days
- FRESHNESS = pw
- RSS_HOURS = 168
- ITEMS_PER_SECTION = 5-8
- BLOG_PICKS_COUNT = 3-5
- EXTRA_SECTIONS = 📊 Weekly Trend Summary (2-3 sentences summarizing macro trends)
- SUBJECT = Weekly Tech Digest - YYYY-MM-DD
- WORKSPACE = <your workspace path>
- SKILL_DIR = <your skill install path>
- DISCORD_CHANNEL_ID = <your channel id>
- EMAIL = （optional）
- LANGUAGE = Chinese
- TEMPLATE = discord

严格按 prompt 模板中的步骤执行，不要跳过任何步骤。
```

#### Why This Pattern?
- **Single source of truth**: Pipeline logic lives in `digest-prompt.md`, not scattered across cron configs
- **Portable**: Same skill on different OpenClaw instances, just change paths and channel IDs
- **Maintainable**: Update the skill → all cron jobs pick up changes automatically
- **Anti-pattern**: Do NOT copy pipeline steps into the cron prompt — it will drift out of sync

#### Multi-Channel Delivery Limitation
OpenClaw enforces **cross-provider isolation**: a single session can only send messages to one provider (e.g., Discord OR Telegram, not both). If you need to deliver digests to multiple platforms, create **separate cron jobs** for each provider:

```
# Job 1: Discord + Email
- DISCORD_CHANNEL_ID = 1470806864412414071
- EMAIL = user@example.com
- TEMPLATE = discord

# Job 2: Telegram DM
- DISCORD_CHANNEL_ID = （无）
- EMAIL = （无）
- TEMPLATE = telegram
```
Replace `DISCORD_CHANNEL_ID` delivery with Telegram delivery in the second job's prompt (use `message` tool with `channel=telegram`).

This is a security feature, not a bug — it prevents accidental cross-context data leakage.

## Security Notes

### Execution Model
This skill uses a **prompt template pattern**: the agent reads `digest-prompt.md` and follows its instructions. This is the standard OpenClaw skill execution model — the agent interprets structured instructions from skill-provided files. All instructions are shipped with the skill bundle and can be audited before installation.

### Network Access
The Python scripts make outbound requests to:
- RSS feed URLs (configured in `sources.json`)
- Twitter/X API (`api.x.com`)
- Brave Search API (`api.search.brave.com`)
- GitHub API (`api.github.com`)

No data is sent to any other endpoints. All API keys are read from environment variables declared in the skill metadata.

### Shell Safety
Email delivery uses the `gog` CLI with hardcoded subject formats (`Daily Tech Digest - YYYY-MM-DD`). The prompt template explicitly prohibits interpolating untrusted content into shell arguments.

### File Access
Scripts read from `config/` and write to `workspace/archive/`. No files outside the workspace are accessed.

## Support & Troubleshooting

### Common Issues
1. **RSS feeds failing**: Check network connectivity, use `--verbose` for details
2. **Twitter rate limits**: Reduce sources or increase interval
3. **Configuration errors**: Run `validate-config.py` for specific issues
4. **No articles found**: Check time window (`--hours`) and source enablement

### Debug Mode
All scripts support `--verbose` flag for detailed logging and troubleshooting.

### Performance Tuning
- **Parallel Workers**: Adjust `MAX_WORKERS` in scripts for your system
- **Timeout Settings**: Increase `TIMEOUT` for slow networks
- **Article Limits**: Adjust `MAX_ARTICLES_PER_FEED` based on needs
## Security Considerations

### Shell Execution
The digest prompt instructs agents to run Python scripts via shell commands. All script paths and arguments are skill-defined constants — no user input is interpolated into commands. Scripts themselves contain no subprocess/os.system calls.

### Third-Party RSS Sources
One RSS source (`anthropic-rss`) uses a community-maintained GitHub mirror since Anthropic has no official RSS feed. Users should be aware of supply chain risks from third-party mirrors. The source is clearly annotated in `sources.json`.

### Input Sanitization
- URL resolution rejects non-HTTP(S) schemes (javascript:, data:, etc.)
- RSS fallback parsing uses simple, non-backtracking regex patterns (no ReDoS risk)
- All fetched content is treated as untrusted data for display only

### Network Access
Scripts make outbound HTTP requests to configured RSS feeds, Twitter API, GitHub API, and Brave Search API. No inbound connections or listeners are created.
