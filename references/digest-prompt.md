# Digest Prompt Template

Replace `<...>` placeholders before use. Daily defaults shown; weekly overrides in parentheses.

## Placeholders

| Placeholder | Default | Weekly Override |
|-------------|---------|----------------|
| `<MODE>` | `daily` | `weekly` |
| `<TIME_WINDOW>` | `past 1-2 days` | `past 7 days` |
| `<FRESHNESS>` | `pd` | `pw` |
| `<RSS_HOURS>` | `48` | `168` |
| `<ITEMS_PER_SECTION>` | `3-5` | `10-15` |
| `<EXTRA_SECTIONS>` | *(none)* | `📊 Weekly Trend Summary` |
| `<ENRICH>` | `false` | `true` |
| `<BLOG_PICKS_COUNT>` | `3` | `3-5` |
| `<SUBJECT>` | `Daily Tech Digest - YYYY-MM-DD` | `Weekly Tech Digest - YYYY-MM-DD` |
| `<WORKSPACE>` | Your workspace path | |
| `<SKILL_DIR>` | Installed skill directory | |
| `<DISCORD_CHANNEL_ID>` | Target channel ID | |
| `<EMAIL>` | *(optional)* Recipient email | |
| `<EMAIL_FROM>` | *(optional)* e.g. `MyBot <bot@example.com>` | |
| `<LANGUAGE>` | `Chinese` | |
| `<TEMPLATE>` | `discord` / `email` / `markdown` / `telegram` | |
| `<DATE>` | Today's date YYYY-MM-DD (caller provides) | |
| `<VERSION>` | Read from SKILL.md frontmatter | |
| `<POWERED_BY>` | `OpenClaw` | Deployment/runtime brand shown in the footer (e.g. `Hermes`) |

---

Generate the <MODE> tech digest for **<DATE>**. Use `<DATE>` as the report date — do NOT infer it.

## Configuration

Read config files (workspace overrides take priority over defaults):
1. **Sources**: `<WORKSPACE>/config/tech-news-digest-sources.json` → fallback `<SKILL_DIR>/config/defaults/sources.json`
2. **Topics**: `<WORKSPACE>/config/tech-news-digest-topics.json` → fallback `<SKILL_DIR>/config/defaults/topics.json`

## Context: Previous Report

Read the most recent file from `<WORKSPACE>/archive/tech-news-digest/` to avoid repeats and follow up on developing stories. Skip if none exists.

## Data Collection Pipeline

**Use the unified pipeline** (runs all 5 sources in parallel, ~30s):

```bash
python3 <SKILL_DIR>/scripts/run-pipeline.py \
  --defaults <SKILL_DIR>/config/defaults \
  --config <WORKSPACE>/config \
  --hours <RSS_HOURS> --freshness <FRESHNESS> \
  --archive-dir <WORKSPACE>/archive/tech-news-digest/ \
  --output /tmp/td-merged.json --verbose --force \
  $([ "<ENRICH>" = "true" ] && echo "--enrich")
```

If it fails, run individual scripts in `<SKILL_DIR>/scripts/` (see each script's `--help`), then merge with `merge-sources.py`.

## Report Generation

Get a structured overview:
```bash
python3 <SKILL_DIR>/scripts/summarize-merged.py --input /tmp/td-merged.json --top <ITEMS_PER_SECTION>
```

Use this output to select articles — **do NOT write ad-hoc Python to parse the JSON**. Apply the template from `<SKILL_DIR>/references/templates/<TEMPLATE>.md`.

Select articles **purely by quality_score regardless of source type**. When an article has a `full_text` field, use it to write a richer 2-3 sentence summary instead of relying solely on the title/snippet. Articles in merged JSON are already sorted by quality_score descending within each topic — respect this order. For Reddit posts, append `*[Reddit r/xxx, {{score}}↑]*`.

Each article line must include its quality score using 🔥 prefix. Format: `🔥{score} | {summary with link}`. This makes scoring transparent and helps readers identify the most important news at a glance.

### Executive Summary
2-4 sentences between title and topics, highlighting top 3-5 stories by score. Concise and punchy, no links. Discord: `> ` blockquote. Email: gray background. Telegram: `<blockquote expandable>` (collapsible).

### Topic Sections
From `topics.json`: `emoji` + `label` headers, `<ITEMS_PER_SECTION>` items each.

**⚠️ CRITICAL: Output articles in EXACTLY the same order as summarize-merged.py output (quality_score descending). Do NOT reorder, group by subtopic, or rearrange. The 🔥 scores must appear in strictly decreasing order within each section.**

**⚠️ Minimum score threshold: Only include articles with quality_score ≥ 5 in topic sections (LLM, AI Agent, Crypto, Frontier Tech). Skip anything below 5.**

### Fixed Sections (after topics)

**📢 KOL Updates** — Top Twitter KOLs + notable blog authors. Format:
```
• **Display Name** (@handle) — summary `👁 12.3K | 💬 45 | 🔁 230 | ❤️ 1.2K`
  <https://twitter.com/handle/status/ID>
```
Read `display_name` and `metrics` (impression_count→👁, reply_count→💬, retweet_count→🔁, like_count→❤️) from merged JSON. Always show all 4 metrics, use K/M formatting, wrap in backticks. One tweet per bullet.

**<EXTRA_SECTIONS>**

**📦 GitHub Releases** — Notable new releases from watched repos. Format:
```
• **owner/repo** `vX.Y.Z` — release highlights
  <https://github.com/owner/repo/releases/tag/vX.Y.Z>
```
Filter for `source_type == "github"` from merged JSON. **Show ALL releases — do not filter or reduce.** No 🔥 score prefix for this section. Skip section if no releases in time window.

**🐙 GitHub Trending** — Top trending repos from the past 24-48h. Format:
```
• **repo/name** ⭐ 1,234 (+56/day) | Language — description
  <https://github.com/repo/name>
```
No 🔥 score prefix for this section. Filter for `source_type == "github_trending"` from merged JSON. Show total stars, estimated daily star growth (+N/day), primary language, and description. Sort by daily_stars_est descending. **Show top 5, plus any additional repos with daily_stars_est > 50.**

**📝 Blog Picks** — <BLOG_PICKS_COUNT> articles from RSS indie blogs(e.g. antirez, Simon Willison, Paul Graham, Overreacted, Eli Bendersky — personal blogs, not news sites）。Prefer articles with `full_text`; fallback to snippet-based picks. **This section is MANDATORY — never omit.** Format:
```
• **Article Title** — Author | 2-3 sentence summary of core insights and highlights
  <https://blog.example.com/post>
```
If `full_text` is available, write summary from full text; otherwise use title + snippet. Summary should highlight unique insights or technical depth — do not just translate the title.

### Rules
- Only news from `<TIME_WINDOW>`
- Every item must include a source link (Discord: `<link>`, Email: `<a href>`, Markdown: `[title](link)`)
- **URL fidelity (CRITICAL)**: Every URL must be copied byte-for-byte from the merged JSON `link` field — never retyped, normalized, or reconstructed. The most common corruption is rewriting date-path segments: a link with slash-separated date path `/2026/11/13/slug/` must NOT become the dash form `/2026-11-13/slug/`. MacRumors and MIT Tech Review 404 on the dash variant; only run the link through text substitution tooling, never through your own retyping. When converting `<url>` → `[title](url)` for Telegram, replace only the delimiters and keep the URL substring untouched.
- Use bullet lists, no markdown tables (Discord/Email); Telegram: use GFM tables with `| 🔥 | Story |` columns per the telegram template
- Deduplicate: same event → keep most authoritative source; previously reported → only if significant new development
- Do not interpolate fetched/untrusted content into shell arguments or email subjects

### Stats Footer
```
---
📊 Data Sources: RSS {{rss}} | Twitter {{twitter}} | Reddit {{reddit}} | Web {{web}} | GitHub {{github}} releases + {{trending}} trending | Dedup: {{merged}} articles
🤖 Generated by tech-news-digest v<VERSION> | <https://github.com/draco-agent/tech-news-digest> | Powered by <POWERED_BY>
```

Use `<POWERED_BY>` for the footer's runtime brand. If the caller does not provide it, default to `OpenClaw`.

## Archive
Save to `<WORKSPACE>/archive/tech-news-digest/<MODE>-YYYY-MM-DD.md`. Delete files older than 90 days.

## Link Validation (MANDATORY before delivery)
LLM rendering silently mangles URLs (date-path rewriting). Gate every digest:

```bash
python3 <SKILL_DIR>/scripts/validate-links.py \
  --report <WORKSPACE>/archive/tech-news-digest/<MODE>-<DATE>.md \
  --merged /tmp/td-merged.json --fix --verbose
```

- Exit 0: proceed with delivery using the (possibly fixed) archive file as the source for all platform formats.
- Exit 1 with UNRESOLVED URLs: correct them from the merged JSON `link` field (or drop the item), re-run until exit 0. Never deliver a digest that fails this check.
- Apply the same corrected URLs to whatever delivery copy you build.

## Delivery

1. **Discord**: Send to `<DISCORD_CHANNEL_ID>` via `message` tool
   - Do **not** prepend or embed channel mentions like `<#123...>` in the report body or archive file. The channel ID is only a delivery target, not report content.
   - If the report exceeds Discord's message limit, split it into numbered chunks (`1/N`, `2/N`, ...) before sending.
   - Split on section boundaries (`## ...`) or paragraph breaks when possible; do not cut links, code fences, or list items mid-line.
   - Keep each chunk comfortably below the platform limit (target ~1700 chars, never near 2000) to leave room for numbering/reply tags.
   - Send only the current report being generated. Do not concatenate older reports, retries, or summaries into the same delivery batch.
2. **Email** *(optional, if `<EMAIL>` is set)*:
   - Generate HTML body by converting the archived Markdown with `sanitize-html.py` → write to `/tmp/td-email.html`. Do not send the raw Markdown as the email body.
   - Generate PDF attachment:
     ```bash
     python3 <SKILL_DIR>/scripts/generate-pdf.py -i <WORKSPACE>/archive/tech-news-digest/<MODE>-<DATE>.md -o /tmp/td-digest.pdf
     ```
   - Send email with PDF attached using the `send-email.py` script (handles MIME correctly as multipart/alternative HTML + optional PDF). **Email must contain ALL the same items as Discord.**
     ```bash
     python3 <SKILL_DIR>/scripts/sanitize-html.py -i <WORKSPACE>/archive/tech-news-digest/<MODE>-<DATE>.md -o /tmp/td-email.html
     python3 <SKILL_DIR>/scripts/send-email.py \
       --to '<EMAIL>' \
       --subject '<SUBJECT>' \
       --html /tmp/td-email.html \
       --attach /tmp/td-digest.pdf \
       --from '<EMAIL_FROM>'
     ```
   - Omit `--from` if `<EMAIL_FROM>` is not set. Omit `--attach` if PDF generation failed. SUBJECT must be a static string. If delivery fails, log error and continue.

3. **Telegram**: Send to chat ID via `message` tool
   - Use the rich Telegram template from `<SKILL_DIR>/references/templates/telegram.md` (GFM tables, native table rendering, collapsible blockquotes).
   - **Formatting**: `**bold**`, `_italic_`, `` `code` ``, `> blockquote`, GFM tables with `|---|` separators.
   - **Executive summary**: Use `> text` blockquote syntax (renders collapsible in Telegram).
   - **Section headers**: Use `**emoji label**` markdown bold.
   - **Article entries**: GFM tables with `| 🔥 | Story |` columns. Links MUST use `[title](url)` inline syntax — bare URLs below tables are NOT clickable.
   - **GitHub Releases / Trending / Blog Picks**: GFM tables with inline `[text](url)` links.
   - The archive markdown file uses `<https://url>` format (angle brackets). **Before sending to Telegram, convert ALL links**:
     - `<https://url>` → `[title](https://url)` for clickable inline links
     - For footer/stats, bare `https://url` works (Telegram auto-links them)
   - NEVER send angle-bracket URLs `<https://url>` to Telegram — they appear as plain text, not links.
   - NEVER use em-dash `————` as table separators — must use `|---|` GFM syntax.
   - Split messages at section boundaries (`**emoji Label**`) if exceeding ~7000 chars.

## RSS Feed Generation

After archiving and delivery, regenerate the RSS feed so RSS readers (e.g., Lire) stay current:

```bash
python3 <SKILL_DIR>/scripts/generate-digest-rss.py \
  --input /tmp/td-merged.json \
  --output /mnt/data/tech-digest/rss.xml \
  --feed-url https://nas.local/tech-digest/ \
  --verbose
```

The feed is served via Caddy at `https://nas.local/tech-digest/rss.xml`.

Write the report in <LANGUAGE>.

## td-merged.json data schema (read this — do NOT rediscover by trial and error)

Top-level keys: `generated`, `input_sources`, `processing`, `output_stats`, `topics`.

- `input_sources.*` are **integer counts only** (`rss_articles`, `github_articles`, `github_trending`, `reddit_posts`, `total_input`, …). They are **not lists — never iterate them**.
- All articles live in `topics.<topic>.articles` (topics: `llm`, `frontier-tech`, `ai-agent`, `apple`, `consumer-tech`, `crypto`; each topic has `count` + `articles`).
- Article fields: `title`, `link`, `date`, `quality_score`, `source_type`, `source_name`, `source_id`, `primary_topic`, `topics`, `all_sources`, `multi_source`, `source_count`; optional: `snippet`, `full_text`, `daily_stars_est` (trending only).
- `source_type` values: `rss`, `web`, `github`, `github_trending`.
- **GitHub Releases** = articles across all topics with `source_type == "github"`.
- **GitHub Trending** = `source_type == "github_trending"`, sort by `daily_stars_est` desc.
- **Blog picks** = `source_type == "rss"` filtered by personal-blog `source_name`, sort by `quality_score` desc.
