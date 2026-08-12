# Tech News Digest

> 自动化科技资讯汇总 — 213 个内置数据源，6 层管道，一句话安装。

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

基于 **213 个内置数据源** + **4 个 Web 搜索主题** 的质量评分、去重科技日报：

| 层级 | 数量 | 内容 |
|------|------|------|
| 📡 RSS | 93 个订阅源 | OpenAI、arXiv、Google Research、Techmeme、HN、Interconnects、CoinDesk… |
| 🐦 Twitter/X | 73 个 KOL | @karpathy、@simonw、@VitalikButerin、@sama、@deepseek_ai… |
| 🔍 Web 搜索 | 4 个主题 | Tavily 或 Brave Search API + 时效过滤 |
| 🐙 GitHub | 47 个仓库 | 关键项目的 Release 跟踪（llama.cpp、vLLM、SGLang、LangGraph、MCP…） |
| 🗣️ Reddit | 13 个子版块 *(默认关闭)* | r/MachineLearning、r/LocalLLaMA、r/CryptoCurrency — 需配置 OAuth，见下文 |

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

**质量评分**：优先级源 (+3，优先级 RSS 再 +2)、多源交叉验证 (每多一种源类型 +5)、24 小时内 (+2)、Twitter 互动度 (分档 +1/+2/+3/+5)、Reddit 热度加分 (+1/+3/+5)、已报道过 (-5)。

## ⚙️ 配置

- `config/defaults/sources.json` — 213 个内置数据源（93 RSS、73 Twitter、47 GitHub），另有 13 个可选启用的 Reddit
- `config/defaults/topics.json` — 4 个主题，含搜索查询和 Twitter 查询
- 用户自定义配置放 `workspace/config/`，优先级更高

### 🗣️ 启用 Reddit

13 个 Reddit 数据源**默认关闭**。Reddit 对服务器和机房 IP 的公开 JSON 接口一律返回
HTTP 403，`.rss` 兜底路径也会被限流，未配置凭据时这一层只会在日志里刷错误。启用方式：

1. 在 <https://www.reddit.com/prefs/apps> 创建 script 类型应用
2. 设置 `REDDIT_CLIENT_ID` 和 `REDDIT_CLIENT_SECRET`
3. 在 workspace 覆盖配置里重新启用：

```json
{
  "sources": [
    {"id": "reddit-localllama", "enabled": true},
    {"id": "reddit-machinelearning", "enabled": true}
  ]
}
```

## 🎨 自定义数据源

开箱即用，内置 213 个数据源——但完全可自定义。将默认配置复制到 workspace 并覆盖：

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

## 🔧 环境变量

# Twitter/X 后端（自动优先级：getxapi > xquik > twitterapiio > official）
export GETX_API_KEY="..."        # GetXAPI
export XQUIK_API_KEY="..."       # Xquik
export TWITTERAPI_IO_KEY="..."   # twitterapi.io
export X_BEARER_TOKEN="..."      # Twitter/X 官方 API v2
export TWITTER_API_BACKEND="auto"  # auto|getxapi|xquik|twitterapiio|official
# 网页搜索
export TAVILY_API_KEY="tvly-xxx"   # Tavily Search API
export BRAVE_API_KEYS="k1,k2,k3"   # Brave Search API 密钥（逗号分隔用于轮换）
export BRAVE_API_KEY="..."         # 单个密钥
export WEB_SEARCH_BACKEND="auto"   # auto|brave|tavily
# GitHub
export GITHUB_TOKEN="..."          # 可选。未设置时改用 github.com/<repo>/releases.atom
                                   # （不消耗 API 配额，Release 摘要略粗）
# Reddit — 不配置则 Reddit 这一层无法工作（见下文）
export REDDIT_CLIENT_ID="..."      # Reddit 应用 client ID
export REDDIT_CLIENT_SECRET="..."  # Reddit 应用 client secret
export REDDIT_USERNAME="..."       # 可选，仅用于 User-Agent 字符串
export TECH_NEWS_DIGEST_STATE_DIR="~/.local/state/tech-news-digest"  # 缓存与健康度记录目录
# 其他
export BRAVE_PLAN="free"           # 覆盖速率限制检测：free|pro

## 📦 依赖

### 核心依赖

本技能需要 Python 3.8+ 和两个可选依赖以增强功能：

```bash
pip install -r requirements.txt
# 或
pip install feedparser>=6.0.0 jsonschema>=4.0.0
```

- **feedparser** — RSS/Atom 订阅源解析（未安装时回退到正则匹配）
- **jsonschema** — 配置文件的 JSON Schema 验证

### 可选依赖

```bash
pip install weasyprint
```

- **weasyprint** — 启用 PDF 报告生成

## 🧪 测试

```bash
python -m unittest discover -s tests -v   # 41 个测试，纯标准库
```

## 📂 仓库地址

**GitHub**: [github.com/draco-agent/tech-news-digest](https://github.com/draco-agent/tech-news-digest)

## 🌟 相关引用

- [Awesome OpenClaw Use Cases](https://github.com/hesamsheikh/awesome-openclaw-usecases) — OpenClaw 社区精选用例合集

## 📄 开源协议

MIT License — 详见 [LICENSE](LICENSE)
