# Tech News Digest

> 自动化科技资讯汇总 — 138 个数据源，5 层管道，一句话安装。

[English](README.md) | **中文**

[![Tests](https://github.com/draco-agent/tech-news-digest/actions/workflows/test.yml/badge.svg)](https://github.com/draco-agent/tech-news-digest/actions/workflows/test.yml)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![ClawHub](https://img.shields.io/badge/ClawHub-tech--news--digest-blueviolet)](https://clawhub.com/draco-agent/tech-news-digest)
[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## 💬 一句话安装

跟你的 [OpenClaw](https://openclaw.ai) AI 助手说：

> **"安装 tech-news-digest，每天早上 9 点发科技日报到 #tech-news 频道"**

搞定。Bot 会自动安装、配置、定时、推送——全程对话完成。

更多示例：

> 🗣️ "配置一个每周 AI 周报，只要 LLM 和 AI Agent 板块，每周一发到 Discord #ai-weekly"

> 🗣️ "安装 tech-news-digest，加上我的 RSS 源，发送科技新闻到 Telegram"

> 🗣️ "现在就给我生成一份科技日报，跳过 Twitter 数据源"

或通过 CLI 安装：
```bash
clawhub install tech-news-digest
```

## 📊 你会得到什么

基于 **138 个数据源** 的质量评分、去重科技日报：

| 层级 | 数量 | 内容 |
|------|------|------|
| 📡 RSS | 49 个订阅源 | OpenAI、Anthropic、Ben's Bites、HN、36氪、CoinDesk… |
| 🐦 Twitter/X | 48 个 KOL | @karpathy、@VitalikButerin、@sama、@elonmusk… |
| 🔍 Web 搜索 | 4 个主题 | Tavily 或 Brave Search API + 时效过滤 |
| 🐙 GitHub | 28 个仓库 | 关键项目的 Release 跟踪（LangChain、vLLM、DeepSeek、Llama…） |
| 🗣️ Reddit | 13 个子版块 | r/MachineLearning、r/LocalLLaMA、r/CryptoCurrency… |

### 数据管道

```
       run-pipeline.py (~30秒)
              ↓
  RSS ─┐
  Twitter ─┤
  Web ─────┤── 并行采集 ──→ merge-sources.py
  GitHub ──┤
  Reddit ──┘
              ↓
  质量评分 → 去重 → 主题分组
              ↓
    Discord / 邮件 / PDF 输出
```

**质量评分**：优先级源 (+3)、多源交叉验证 (+5)、时效性 (+2)、互动度 (+1~+5)、Reddit 热度加分 (+1/+3/+5)、已报道过 (-5)。

## ⚙️ 配置

- `config/defaults/sources.json` — 138 个内置数据源
- `config/defaults/topics.json` — 4 个主题，含搜索查询和 Twitter 查询
- 用户自定义配置放 `workspace/config/`，优先级更高

## 🎨 自定义数据源

开箱即用，内置 138 个数据源——但完全可自定义。将默认配置复制到 workspace 并覆盖：

```bash
# 复制并自定义
cp config/defaults/sources.json workspace/config/tech-news-digest-sources.json
cp config/defaults/topics.json workspace/config/tech-news-digest-topics.json
```

你的配置文件会与默认配置**合并**：
- **覆盖**：`id` 匹配的源会被你的版本替换
- **新增**：使用新的 `id` 即可添加自定义源
- **禁用**：对匹配的 `id` 设置 `"enabled": false`

```json
{
  "sources": [
    {"id": "my-blog", "type": "rss", "enabled": true, "url": "https://myblog.com/feed", "topics": ["llm"]},
    {"id": "openai-blog", "enabled": false}
  ]
}
```

不需要复制整个文件——只写你要改的部分。

## 🔧 可选配置

所有环境变量均为可选，管道会自动使用可用的数据源。

```bash
export TWITTERAPI_IO_KEY="..."    # twitterapi.io (~$5/月) — 启用 Twitter 数据层
export X_BEARER_TOKEN="..."       # Twitter/X 官方 API — 备选 Twitter 后端
export TWITTER_API_BACKEND="auto" # auto|twitterapiio|official（默认: auto）
export TAVILY_API_KEY="tvly-xxx"  # Tavily Search API（替代方案，免费 1000 次/月）
export BRAVE_API_KEYS="k1,k2,k3" # Brave Search API 密钥（逗号分隔，自动轮换）
export BRAVE_API_KEY="..."        # 单密钥回退
export BRAVE_PLAN="free"          # 覆盖速率限制检测: free|pro
export WEB_SEARCH_BACKEND="auto" # auto|brave|tavily（默认: auto）
export GITHUB_TOKEN="..."         # GitHub API — 提高速率限制（未设置时自动从 GitHub App 生成）
pip install weasyprint             # 启用 PDF 报告生成
```

## 🧪 测试

```bash
python -m unittest discover -s tests -v   # 41 个测试，纯标准库
```

## 📂 仓库地址

**GitHub**: [github.com/draco-agent/tech-news-digest](https://github.com/draco-agent/tech-news-digest)

## 📄 开源协议

MIT License — 详见 [LICENSE](LICENSE)
