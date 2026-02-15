# Tech Digest

> 自动化科技资讯汇总 — 118 个数据源，4 层管道，一句话安装。

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## 💬 一句话安装

跟你的 [OpenClaw](https://openclaw.com) AI 助手说：

> **"安装 tech-digest，每天早上 9 点发科技日报到 #tech-news 频道"**

搞定。Bot 会自动安装、配置、定时、推送——全程对话完成。

更多示例：

> 🗣️ "配置一个每周 AI 周报，只要 LLM 和 AI Agent 板块，每周一发到 Discord #ai-weekly"

> 🗣️ "安装 tech-digest，加上我的 RSS 源，加密货币新闻发到 Telegram"

> 🗣️ "现在就给我生成一份科技日报，跳过 Twitter 数据源"

或通过 CLI 安装：
```bash
clawhub install tech-digest
```

## 📊 你会得到什么

基于 **118 个数据源** 的质量评分、去重科技日报：

| 层级 | 数量 | 内容 |
|------|------|------|
| 📡 RSS | 46 个订阅源 | OpenAI、Anthropic、HN、36氪、CoinDesk… |
| 🐦 Twitter/X | 44 个 KOL | @karpathy、@VitalikButerin、@sama… |
| 🔍 Web 搜索 | 4 个主题 | Brave Search API + 时效过滤 |
| 🐙 GitHub | 19 个仓库 | 关键项目的 Release 跟踪 |
| *(+ 9 个已禁用)* | | 随时可启用 |

### 数据管道

```
RSS + Twitter + Web + GitHub
        ↓
   merge-sources.py
        ↓
  质量评分 → 去重 → 主题分组
        ↓
  Discord / 邮件 / Markdown 输出
```

**质量评分**：优先级源 (+3)、多源交叉验证 (+5)、时效性 (+2)、互动度 (+1)、已报道过 (-3)。

## ⚙️ 配置

- `config/defaults/sources.json` — 118 个内置数据源
- `config/defaults/topics.json` — 4 个主题，含搜索查询和 Twitter 查询
- 用户自定义配置放 `workspace/config/`，优先级更高

## 🔧 环境要求

```bash
export X_BEARER_TOKEN="..."    # Twitter API（推荐）
export BRAVE_API_KEY="..."     # Web 搜索（可选）
export GITHUB_TOKEN="..."      # GitHub API（可选，提高速率限制）
```

## 📂 仓库地址

**GitHub**: [github.com/draco-agent/tech-digest](https://github.com/draco-agent/tech-digest)

## 📄 开源协议

MIT License — 详见 [LICENSE](LICENSE)
