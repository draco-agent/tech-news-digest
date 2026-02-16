# Tech News Digest

> Automated tech news digest — 131 sources, 5-layer pipeline, one chat message to install.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
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

A quality-scored, deduplicated tech digest built from **131 sources**:

| Layer | Sources | What |
|-------|---------|------|
| 📡 RSS | 50 feeds | OpenAI, Anthropic, Ben's Bites, HN, 36氪, CoinDesk… |
| 🐦 Twitter/X | 47 KOLs | @karpathy, @VitalikButerin, @sama, @zuck… |
| 🔍 Web Search | 4 topics | Brave Search API with freshness filters |
| 🐙 GitHub | 22 repos | Releases from key projects (LangChain, DeepSeek, Llama…) |
| 🗣️ Reddit | 13 subs | r/MachineLearning, r/LocalLLaMA, r/CryptoCurrency… |

### Pipeline

```
RSS + Twitter + Web + GitHub + Reddit
              ↓
        merge-sources.py
              ↓
  Quality Scoring → Deduplication → Topic Grouping
              ↓
    Discord / Email / Markdown output
```

**Quality scoring**: priority source (+3), multi-source cross-ref (+5), recency (+2), engagement (+1), Reddit score bonus (+1/+3/+5), already reported (-3).

## ⚙️ Configuration

- `config/defaults/sources.json` — 132 built-in sources
- `config/defaults/topics.json` — 4 topics with search queries & Twitter queries
- User overrides in `workspace/config/` take priority

## 🔧 Requirements

```bash
export X_BEARER_TOKEN="..."    # Twitter API (recommended)
export BRAVE_API_KEY="..."     # Web search (optional)
export GITHUB_TOKEN="..."      # GitHub API (optional, higher rate limits)
```

## 📂 Repository

**GitHub**: [github.com/draco-agent/tech-news-digest](https://github.com/draco-agent/tech-news-digest)

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
