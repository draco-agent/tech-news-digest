# Tech News Digest

> Automated tech news digest — 138 sources, 5-layer pipeline, one chat message to install.

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

A quality-scored, deduplicated tech digest built from **138 sources**:

| Layer | Sources | What |
|-------|---------|------|
| 📡 RSS | 49 feeds | OpenAI, Anthropic, Ben's Bites, HN, 36氪, CoinDesk… |
| 🐦 Twitter/X | 48 KOLs | @karpathy, @VitalikButerin, @sama, @elonmusk… |
| 🔍 Web Search | 4 topics | Tavily or Brave Search API with freshness filters |
| 🐙 GitHub | 28 repos | Releases from key projects (LangChain, vLLM, DeepSeek, Llama…) |
| 🗣️ Reddit | 13 subs | r/MachineLearning, r/LocalLLaMA, r/CryptoCurrency… |

### Pipeline

```
       run-pipeline.py (~30s)
              ↓
  RSS ─┐
  Twitter ─┤
  Web ─────┤── parallel fetch ──→ merge-sources.py
  GitHub ──┤
  Reddit ──┘
              ↓
  Quality Scoring → Deduplication → Topic Grouping
              ↓
    Discord / Email / PDF output
```

**Quality scoring**: priority source (+3), multi-source cross-ref (+5), recency (+2), engagement (+1), Reddit score bonus (+1/+3/+5), already reported (-5).

## ⚙️ Configuration

- `config/defaults/sources.json` — 138 built-in sources
- `config/defaults/topics.json` — 4 topics with search queries & Twitter queries
- User overrides in `workspace/config/` take priority

## 🎨 Customize Your Sources

Works out of the box with 138 built-in sources — but fully customizable. Copy the defaults to your workspace config and override:

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

## 🔧 Optional Setup

All environment variables are optional. The pipeline runs with whatever sources are available.

```bash
export TWITTERAPI_IO_KEY="..."  # twitterapi.io (~$5/mo) — enables Twitter layer
export X_BEARER_TOKEN="..."     # Twitter/X official API — alternative Twitter backend
export TAVILY_API_KEY="tvly-xxx"  # Tavily Search API (alternative, free 1000/mo)
export BRAVE_API_KEYS="k1,k2,k3" # Brave Search API keys (comma-separated, rotation)
export BRAVE_API_KEY="..."       # Fallback: single Brave key
export GITHUB_TOKEN="..."       # GitHub API — higher rate limits (auto-generated from GitHub App if unset)
export TWITTER_API_BACKEND="auto" # auto|twitterapiio|official (default: auto)
export BRAVE_PLAN="free"         # Override Brave rate limit detection: free|pro
export WEB_SEARCH_BACKEND="auto" # auto|brave|tavily (default: auto)
pip install weasyprint           # Enables PDF report generation
```

## 📂 Repository

**GitHub**: [github.com/draco-agent/tech-news-digest](https://github.com/draco-agent/tech-news-digest)

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
