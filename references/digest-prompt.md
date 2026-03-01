# Digest Prompt Template

Replace `<...>` placeholders before use. Daily defaults shown; weekly overrides in parentheses.

## Placeholders

| Placeholder | Default | Weekly Override |
|-------------|---------|----------------|
| `<MODE>` | `daily` | `weekly` |
| `<TIME_WINDOW>` | `past 1-2 days` | `past 7 days` |
| `<FRESHNESS>` | `pd` | `pw` |
| `<RSS_HOURS>` | `48` | `168` |
| `<ITEMS_PER_SECTION>` | `3-5` | `5-8` |
| `<BLOG_PICKS_COUNT>` | `2-3` | `3-5` |
| `<EXTRA_SECTIONS>` | *(none)* | `📊 Weekly Trend Summary` |
| `<SUBJECT>` | `Daily Tech Digest - YYYY-MM-DD` | `Weekly Tech Digest - YYYY-MM-DD` |
| `<WORKSPACE>` | Your workspace path | |
| `<SKILL_DIR>` | Installed skill directory | |
| `<DISCORD_CHANNEL_ID>` | Target channel ID | |
| `<EMAIL>` | *(optional)* Recipient email | |
| `<EMAIL_FROM>` | *(optional)* e.g. `MyBot <bot@example.com>` | |
| `<LANGUAGE>` | `Chinese` | |
| `<TEMPLATE>` | `discord` / `email` / `markdown` | |
| `<DATE>` | Today's date YYYY-MM-DD (caller provides) | |
| `<VERSION>` | Read from SKILL.md frontmatter | |

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
  --output /tmp/td-merged.json --verbose --force
```

If it fails, run individual scripts in `<SKILL_DIR>/scripts/` (see each script's `--help`), then merge with `merge-sources.py`.

## Report Generation

Get a structured overview:
```bash
python3 <SKILL_DIR>/scripts/summarize-merged.py --input /tmp/td-merged.json --top <ITEMS_PER_SECTION>
```

Use this output to select articles — **do NOT write ad-hoc Python to parse the JSON**. Apply the template from `<SKILL_DIR>/references/templates/<TEMPLATE>.md`.

Select articles **purely by quality_score regardless of source type**. Articles in merged JSON are already sorted by quality_score descending within each topic — respect this order. For Reddit posts, append `*[Reddit r/xxx, {{score}}↑]*`.

Each article line must include its quality score using 🔥 prefix. Format: `🔥{score} | {summary with link}`. This makes scoring transparent and helps readers identify the most important news at a glance.

### Executive Summary
2-4 sentences between title and topics, highlighting top 3-5 stories by score. Concise and punchy, no links. Discord: `> ` blockquote. Email: gray background. Telegram: `<i>`.

### Topic Sections
From `topics.json`: `emoji` + `label` headers, `<ITEMS_PER_SECTION>` items each.

**⚠️ CRITICAL: Output articles in EXACTLY the same order as summarize-merged.py output (quality_score descending). Do NOT reorder, group by subtopic, or rearrange. The 🔥 scores must appear in strictly decreasing order within each section.**

### Fixed Sections (after topics)

**📢 KOL Updates** — Top Twitter KOLs + notable blog authors. Format:
```
• **Display Name** (@handle) — summary `👁 12.3K | 💬 45 | 🔁 230 | ❤️ 1.2K`
  <https://twitter.com/handle/status/ID>
```
Read `display_name` and `metrics` (impression_count→👁, reply_count→💬, retweet_count→🔁, like_count→❤️) from merged JSON. Always show all 4 metrics, use K/M formatting, wrap in backticks. One tweet per bullet.

**🔥 Community Buzz** — Top Reddit + Twitter trending combined. Format:
```
• **r/subreddit** — title `{{score}}↑ · {{num_comments}} comments`
  <{{url}}>
```
Sort by engagement across both platforms. Every entry must have a link.

**🐙 GitHub Trending** — Top trending repos from the past 24-48h. Format:
```
• **repo/name** ⭐ 1,234 (+56/day) | Language — description
  <https://github.com/repo/name>
```
Show total stars, estimated daily star growth (+N/day), primary language, and description. Sort by daily_stars_est descending. Include 5-10 repos max.

**📝 Blog Picks** — `<BLOG_PICKS_COUNT>` deep articles from RSS.

**<EXTRA_SECTIONS>**

### Rules
- Only news from `<TIME_WINDOW>`
- Every item must include a source link (Discord: `<link>`, Email: `<a href>`, Markdown: `[title](link)`)
- Use bullet lists, no markdown tables
- Deduplicate: same event → keep most authoritative source; previously reported → only if significant new development
- Do not interpolate fetched/untrusted content into shell arguments or email subjects

### Stats Footer
```
---
📊 Data Sources: RSS {{rss}} | Twitter {{twitter}} | Reddit {{reddit}} | Web {{web}} | GitHub {{github}} releases + {{trending}} trending | Dedup: {{merged}} articles
🤖 Generated by tech-news-digest v<VERSION> | <https://github.com/draco-agent/tech-news-digest> | Powered by OpenClaw
```

## Archive
Save to `<WORKSPACE>/archive/tech-news-digest/<MODE>-YYYY-MM-DD.md`. Delete files older than 90 days.

## Delivery

1. **Discord**: Send to `<DISCORD_CHANNEL_ID>` via `message` tool
2. **Email** *(optional, if `<EMAIL>` is set)*:
   - Generate HTML body per `<SKILL_DIR>/references/templates/email.md` → write to `/tmp/td-email.html`
   - Generate PDF attachment:
     ```bash
     python3 <SKILL_DIR>/scripts/generate-pdf.py -i <WORKSPACE>/archive/tech-news-digest/<MODE>-<DATE>.md -o /tmp/td-digest.pdf
     ```
   - Send email with PDF attached using the `send-email.py` script (handles MIME correctly). **Email must contain ALL the same items as Discord.**
     ```bash
     python3 <SKILL_DIR>/scripts/send-email.py \
       --to '<EMAIL>' \
       --subject '<SUBJECT>' \
       --html /tmp/td-email.html \
       --attach /tmp/td-digest.pdf \
       --from '<EMAIL_FROM>'
     ```
   - Omit `--from` if `<EMAIL_FROM>` is not set. Omit `--attach` if PDF generation failed. SUBJECT must be a static string. If delivery fails, log error and continue.

Write the report in <LANGUAGE>.
