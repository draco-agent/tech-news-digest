# Tech Digest Telegram Rich Template

Telegram-optimized format using Bot API 10.1 rich text via OpenClaw's `sendRichMessage` delivery. Tables, headings, blockquotes, and structured lists render natively.

## Format Rules

- **Section headers**: `**emoji Label**` (markdown bold)
- **Executive summary**: `> text` (blockquote — collapsible in Telegram)
- **Article entries**: GFM tables with `[title](url)` links inside cells
- **Footer**: `_italic text_`
- **Bare URLs below tables are NOT clickable** — always use `[text](url)` inline
- **Never use `<https://url>` angle brackets** — Telegram shows them as plain text
- **Never use em-dash `————` as table separators** — must use `|---|` GFM syntax

## Template Structure

```
🚀 **Daily Tech Digest — {{DATE}}**

> {{EXECUTIVE_SUMMARY}}

**🍎 Apple**

| 🔥 | Story |
|---:|-------|
| 12 | [At WWDC 2026, energy and optimism were high as Apple finally delivers](https://appleinsider.com/...) |
| 12 | [iPhone Fold, touchscreen MacBook evidence mounts in iOS 27](https://appleinsider.com/...) |
| 7 | [Siri AI in iOS 27: Features, Requirements, and How It Works](https://www.macrumors.com/...) |

**🔬 Frontier Tech**

| 🔥 | Story |
|---:|-------|
| 15 | [System prompts leaked from Anthropic, OpenAI, Google & more](https://github.com/asgeirtj/system_prompts_leaks) |
| 10 | [TensorFlow ⭐195,680 (+51/day)](https://github.com/tensorflow/tensorflow) |

**🤖 AI Agent**

| 🔥 | Story |
|---:|-------|
| 13 | [GenericAgent: self-evolving agent grows skill tree from 3.3K-line seed](https://github.com/lsdefine/GenericAgent) |

**🧠 LLM / Large Models**

| 🔥 | Story |
|---:|-------|
| 8 | [SGLang: high-performance serving framework for LLMs](https://github.com/sgl-project/sglang) |

**📱 Consumer Tech**

| 🔥 | Story |
|---:|-------|
| 7 | [EPOMAKER Glyph Review](https://www.digitallydownloaded.net/...) |

**📦 GitHub Releases**

| Repo | Version | Highlights |
|------|---------|-----------|
| openclaw | v2026.6.8-beta.2 | [Telegram/WhatsApp rich text delivery](https://github.com/openclaw/openclaw/releases/tag/v2026.6.8-beta.2) |
| transformers | v5.12.1 | PEFT lower bound + Mistral tokenizer fix |

**🐙 GitHub Trending**

| Repo | ⭐ Stars | +/day |
|------|--------|------|
| asgeirtj/system_prompts_leaks | 42,531 | +104 |
| lsdefine/GenericAgent | 12,895 | +86 |

**📝 Blog Picks**

| Title | Author | Summary |
|-------|--------|---------|
| [The Fable 5 Export Controls Harm US Cyber Defense](https://simonwillison.net/...) | Simon Willison | Export restrictions could backfire by limiting access to defensive AI |

_📊 RSS 290 · Twitter 0 · Reddit 0 · Web 64 · GitHub 14 releases + 45 trending · Dedup: 221 articles_
_🤖 tech-news-digest v3.17.0_
```

## Delivery Notes

- OpenClaw's Telegram channel uses `sendRichMessage` (Bot API 10.1) for structured delivery
- GFM pipe-delimited tables with `|---|` separators render as native Telegram tables
- Links in table cells MUST use `[text](url)` markdown syntax — bare URLs below tables are NOT clickable
- The archive .md file keeps standard Markdown with angle-bracket links for local storage
- Before sending, convert ALL links: `<https://url>` → `[title](https://url)` or bare `https://url`
- Rich messages handle longer content; split only at section boundaries if a single message is extremely large