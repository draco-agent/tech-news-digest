# Tech News Digest

> Automated tech news digest — 213 built-in sources, 6-source pipeline, one chat message to install.

**English** | [中文](README_CN.md)

[![Tests](https://github.com/draco-agent/tech-news-digest/actions/workflows/test.yml/badge.svg)](https://github.com/draco-agent/tech-news-digest/actions/workflows/test.yml)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![ClawHub](https://img.shields.io/badge/ClawHub-tech--news--digest-blueviolet)](https://clawhub.com/draco-agent/tech-news-digest)
[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## 💬 Install in One Message

Tell your [OpenClaw](https://openclaw.ai) AI assistant:

> **"Install tech-news-digest and send a daily digest to #tech-news every morning at 9am"**

That's it. Your bot handles installation, configuration, scheduling, and delivery — all through conversation.

More examples:

> 🗣️ "Set up a weekly AI digest, only LLM and AI Agent topics, deliver to Discord #ai-weekly every Monday"

> 🗣️ "Install tech-news-digest, add my RSS feeds, and send crypto news to Telegram"

> 🗣️ "Give me a tech digest right now, skip Twitter sources"

Or install via CLI:
```bash
clawhub install tech-news-digest
```

## 📊 What You Get

A quality-scored, deduplicated tech digest built from **213 built-in sources** plus **4 web search topics**:

| Layer | Sources | What |
|-------|---------|------|
| 📡 RSS | 93 feeds | OpenAI, arXiv, Google Research, Techmeme, HN, Interconnects, CoinDesk… |
| 🐦 Twitter/X | 73 KOLs | @karpathy, @simonw, @VitalikButerin, @sama, @deepseek_ai… |
| 🔍 Web Search | 4 topics | Tavily or Brave Search API with freshness filters |
| 🐙 GitHub | 47 repos | Releases from key projects (llama.cpp, vLLM, SGLang, LangGraph, MCP…) |
| 🗣️ Reddit | 13 subs *(opt-in)* | r/MachineLearning, r/LocalLLaMA, r/CryptoCurrency — needs OAuth, see below |

### Pipeline

```
       run-pipeline.py (~30s)
              ↓
  RSS ────────┐
  Twitter ────┤
  Web ────────┤── parallel fetch ──→ merge-sources.py
  GitHub ─────┤                          ↓
  GitHub Tr. ─┤              enrich-articles.py (opt-in)
  Reddit ─────┘                          ↓
              Quality Scoring → Dedup → Topic Grouping
                             ↓
               Discord / Email / PDF output
```

**Quality scoring**: priority source (+3, +2 more for priority RSS), multi-source cross-ref (+5 per extra source type), recency <24h (+2), Twitter engagement (+1/+2/+3/+5 by tier), Reddit score bonus (+1/+3/+5), already reported (-5).

## ⚙️ Configuration

- `config/defaults/sources.json` — 213 built-in sources (93 RSS, 73 Twitter, 47 GitHub) plus 13 opt-in Reddit
- `config/defaults/topics.json` — 4 topics with search queries & Twitter queries
- User overrides in `workspace/config/` take priority

### 🗣️ Enabling Reddit

The 13 Reddit sources ship **disabled**. Reddit returns HTTP 403 for its public
JSON endpoints when called from servers and datacenter IPs, and rate-limits the
`.rss` fallback, so without credentials the layer contributes nothing but noise
in the logs. To turn it on:

1. Create a script-type app at <https://www.reddit.com/prefs/apps>
2. Export `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET`
3. Re-enable the sources in your workspace overlay:

```json
{
  "sources": [
    {"id": "reddit-localllama", "enabled": true},
    {"id": "reddit-machinelearning", "enabled": true}
  ]
}
```

## 🎨 Customize Your Sources

Works out of the box with 213 built-in sources (93 RSS, 73 Twitter, 47 GitHub) — but fully customizable. Copy the defaults to your workspace config and override:

```bash
# Copy and customize
cp config/defaults/sources.json workspace/config/tech-news-digest-sources.json
cp config/defaults/topics.json workspace/config/tech-news-digest-topics.json
```

Your overlay file **merges** with defaults:
- **Override** a source by matching its `id` — your version replaces the default
- **Add** new sources with a unique `id` — appended to the list
- **Disable** a built-in source — set `"enabled": false` on the matching `id`

```json
{
  "sources": [
    {"id": "my-blog", "type": "rss", "enabled": true, "url": "https://myblog.com/feed", "topics": ["llm"]},
    {"id": "openai-blog", "enabled": false}
  ]
}
```

No need to copy the entire file — just include what you want to change.

## 🔧 Environment Variables

All environment variables are optional. The pipeline runs with whatever sources are available.

```bash
# Twitter/X Backend (auto priority: getxapi > twitterapiio > official)
export GETX_API_KEY="..."        # GetXAPI
export TWITTERAPI_IO_KEY="..."   # twitterapi.io
export X_BEARER_TOKEN="..."      # Official X API v2
export TWITTER_API_BACKEND="auto"  # auto|getxapi|twitterapiio|official
# Web Search
export TAVILY_API_KEY="tvly-xxx"   # Tavily Search API
export BRAVE_API_KEYS="k1,k2,k3"   # Brave Search API keys (comma-separated for rotation)
export BRAVE_API_KEY="..."         # Single Brave key
export WEB_SEARCH_BACKEND="auto"   # auto|brave|tavily
# GitHub
export GITHUB_TOKEN="..."          # Optional. Without it, releases are read from
                                   # github.com/<repo>/releases.atom (no quota,
                                   # slightly coarser release notes)
# Reddit — required to enable the Reddit layer at all (see below)
export REDDIT_CLIENT_ID="..."      # Reddit app client ID
export REDDIT_CLIENT_SECRET="..."  # Reddit app client secret
export REDDIT_USERNAME="..."       # Optional, used only in the User-Agent string
# Other
export BRAVE_PLAN="free"           # Override Brave rate limit: free|pro
export TECH_NEWS_DIGEST_STATE_DIR="~/.local/state/tech-news-digest"  # Cache & health history location
```

## 📦 Dependencies

### Core (required)

The skill requires Python 3.8+ and two optional dependencies for enhanced functionality:

```bash
pip install -r requirements.txt
# or
pip install feedparser>=6.0.0 jsonschema>=4.0.0
```

- **feedparser** — RSS/Atom feed parsing (fallback to regex if not installed)
- **jsonschema** — JSON Schema validation for config files

### Optional

```bash
pip install weasyprint
```

- **weasyprint** — Enables PDF report generation

## 📂 Repository

**GitHub**: [github.com/draco-agent/tech-news-digest](https://github.com/draco-agent/tech-news-digest)

## 🌟 Featured In

- [Awesome OpenClaw Use Cases](https://github.com/hesamsheikh/awesome-openclaw-usecases) — Community-curated collection of OpenClaw agent use cases

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
