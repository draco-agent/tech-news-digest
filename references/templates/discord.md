# Tech Digest Discord Template

Discord-optimized format with bullet points and link suppression.

## Template Structure

```markdown
# 🚀 Tech Digest - {{DATE}}

{{#topics}}
## {{emoji}} {{label}}

{{#articles}}
• {{title}}
  <{{link}}>
  {{#multi_source}}*[{{source_count}} sources]*{{/multi_source}}

{{/articles}}
{{/topics}}

---
📊 数据源统计：RSS {{rss_count}} 篇 | Twitter {{twitter_count}} 条 | Web {{web_count}} 篇 | GitHub {{github_count}} 个 release | 合并去重后 {{merged_count}} 篇
```

## Delivery

- **Default: DM** — Send to user via Discord DM (not channel) unless explicitly configured otherwise
- Use `message` tool with `target` set to user ID for DM delivery

## Discord-Specific Features

- **Link suppression**: Wrap links in `<>` to prevent embeds
- **Bullet format**: Use `•` for clean mobile display  
- **No tables**: Discord mobile doesn't handle markdown tables well
- **Emoji headers**: Visual hierarchy with topic emojis
- **Concise metadata**: Source count and multi-source indicators
- **Character limits**: Discord messages have 2000 char limit, may need splitting

## Example Output

```markdown
# 🚀 Tech Digest - 2026-02-15

## 🧠 LLM / Large Models

• OpenAI releases GPT-5 with breakthrough reasoning capabilities
  <https://openai.com/blog/gpt5-announcement>
  *[3 sources]*

• Meta's Llama 3.1 achieves new MMLU benchmarks
  <https://ai.meta.com/blog/llama-31-release>

• Anthropic Claude 4 now supports 1M token context window
  <https://anthropic.com/news/claude-4-context>

## 🤖 AI Agent

• AutoGPT v0.5 introduces autonomous code deployment
  <https://github.com/Significant-Gravitas/AutoGPT/releases>

• LangChain launches production-ready agent framework
  <https://blog.langchain.dev/production-agents>

## 💰 Cryptocurrency

• Bitcoin reaches new ATH at $67,000 amid ETF approval
  <https://coindesk.com/markets/btc-ath-etf>
  *[2 sources]*

• Ethereum 2.1 upgrade reduces gas fees by 40%
  <https://blog.ethereum.org/eth21-upgrade>

---
📊 数据源统计：RSS 285 篇 | Twitter 67 条 | Web 60 篇 | GitHub 29 个 release | 合并去重后 95 篇
```

## Variables

- `{{DATE}}` - Report date (YYYY-MM-DD format)
- `{{topics}}` - Array of topic objects
- `{{emoji}}` - Topic emoji 
- `{{label}}` - Topic display name
- `{{articles}}` - Array of article objects per topic
- `{{title}}` - Article title (truncated if needed)
- `{{link}}` - Article URL
- `{{multi_source}}` - Boolean, true if article from multiple sources
- `{{source_count}}` - Number of sources for this article
- `{{total_sources}}` - Total number of sources used
- `{{total_articles}}` - Total articles in digest