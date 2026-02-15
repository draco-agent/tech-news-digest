# Digest Prompt Template

Unified template for both daily and weekly digests. Replace `<...>` placeholders before use.

## Placeholders

| Placeholder | Daily | Weekly |
|-------------|-------|--------|
| `<MODE>` | `daily` | `weekly` |
| `<TIME_WINDOW>` | `past 1-2 days` | `past 7 days` |
| `<FRESHNESS>` | `pd` | `pw` |
| `<RSS_HOURS>` | `48` | `168` |
| `<ITEMS_PER_SECTION>` | `3-5` | `5-8` |
| `<BLOG_PICKS_COUNT>` | `2-3` | `3-5` |
| `<EXTRA_SECTIONS>` | *(remove line)* | `- 📊 Weekly Trend Summary (2-3 sentences summarizing macro trends)` |
| `<SUBJECT>` | `Daily Tech News Digest - YYYY-MM-DD` | `Weekly Tech News Digest - YYYY-MM-DD` |
| `<WORKSPACE>` | Your workspace path | Your workspace path |
| `<SKILL_DIR>` | Path to the installed skill directory | Path to the installed skill directory |
| `<DISCORD_CHANNEL_ID>` | Target channel ID | Target channel ID |
| `<EMAIL>` | *(optional)* Recipient email | *(optional)* Recipient email |
| `<LANGUAGE>` | `Chinese` (default) | `Chinese` (default) |
| `<TEMPLATE>` | `discord` / `email` / `markdown` | `discord` / `email` / `markdown` |

---

Generate the <MODE> tech digest. Follow the steps below.

## Configuration

Read configuration files (user workspace overrides take priority over defaults):

1. **Sources**: `<WORKSPACE>/config/sources.json` → fallback `<SKILL_DIR>/config/defaults/sources.json`
2. **Topics**: `<WORKSPACE>/config/topics.json` → fallback `<SKILL_DIR>/config/defaults/topics.json`

Merge logic: user sources append to defaults (same `id` → user wins); user topics override by `id`.

## Context: Previous Report

Read the most recent archive file from `<WORKSPACE>/archive/tech-digest/` (if any). Use it to:
- **Avoid repeating** news already covered
- **Follow up** on developing stories with new information only
- If no previous report exists, skip this step.

## Data Collection Pipeline

### Step 1: RSS Feeds
```bash
python3 <SKILL_DIR>/scripts/fetch-rss.py \
  --defaults <SKILL_DIR>/config/defaults \
  --config <WORKSPACE>/config \
  --hours <RSS_HOURS> \
  --output /tmp/td-rss.json \
  --verbose
```
Reads `sources.json`, fetches all `type: "rss"` sources with `enabled: true`. Outputs structured JSON with articles tagged by topics. Includes retry mechanism and parallel fetching.

If the script fails, fall back to manually fetching priority feeds via `web_fetch`.

### Step 2: Twitter/X KOL Monitoring
```bash
python3 <SKILL_DIR>/scripts/fetch-twitter.py \
  --defaults <SKILL_DIR>/config/defaults \
  --config <WORKSPACE>/config \
  --hours <RSS_HOURS> \
  --output /tmp/td-twitter.json \
  --verbose
```
Reads `sources.json`, fetches all `type: "twitter"` sources. Requires `$X_BEARER_TOKEN` env var. If unavailable, skip this step.

### Step 3: Web Search
```bash
python3 <SKILL_DIR>/scripts/fetch-web.py \
  --defaults <SKILL_DIR>/config/defaults \
  --config <WORKSPACE>/config \
  --freshness <FRESHNESS> \
  --output /tmp/td-web.json \
  --verbose
```
Reads `topics.json` search queries. Uses Brave Search API if `$BRAVE_API_KEY` is set; otherwise generates queries for agent to execute via `web_search`.

Also search Twitter trending discussions using `web_search` with `freshness='<FRESHNESS>'` and the `twitter_queries` from topics.

### Step 4: GitHub Releases
```bash
python3 <SKILL_DIR>/scripts/fetch-github.py \
  --defaults <SKILL_DIR>/config/defaults \
  --config <WORKSPACE>/config \
  --hours <RSS_HOURS> \
  --output /tmp/td-github.json \
  --verbose
```
Reads `sources.json`, fetches all `type: "github"` sources with `enabled: true`. Fetches recent releases from GitHub API (optional `$GITHUB_TOKEN` for higher rate limits). Outputs structured JSON with releases tagged by topics.

### Step 5: Merge & Score
```bash
python3 <SKILL_DIR>/scripts/merge-sources.py \
  --rss /tmp/td-rss.json \
  --twitter /tmp/td-twitter.json \
  --web /tmp/td-web.json \
  --github /tmp/td-github.json \
  --archive-dir <WORKSPACE>/archive/tech-digest/ \
  --output /tmp/td-merged.json \
  --verbose
```
Merges all sources, deduplicates (title similarity + domain), applies quality scoring:
- Priority source: +3
- Multi-source cross-reference: +5
- Recency bonus: +2
- High engagement: +1
- Already in previous report: -5

Output is grouped by topic with articles sorted by score.

## Report Generation

Use the merged output and the appropriate template from `<SKILL_DIR>/references/templates/<TEMPLATE>.md` to generate the report.

### Topic Sections
Use sections defined in `topics.json`. Each topic has:
- `emoji` + `label` for headers
- `display.max_items` for item count (override with <ITEMS_PER_SECTION>)
- `search.must_include` / `search.exclude` for content filtering

### Fixed Sections (append after topic sections)
- 📢 KOL Updates (Twitter KOLs + notable blog posts from RSS authors — each entry must include the source tweet/post link)
- 🔥 Twitter/X Trending
- 📝 Blog Picks (<BLOG_PICKS_COUNT> high-quality deep articles from RSS)
<EXTRA_SECTIONS>

### Deduplication Rules
- Same event from multiple sources → keep only the most authoritative source link
- If covered in previous report → only include if significant new development
- Prefer primary sources (official blogs, announcements) over re-reporting

### Rules
- **Only include news from the <TIME_WINDOW>**
- **Every item in every section must include the source link** — no exceptions. Discord: wrap in `<link>`; Email: `<a href>`; Telegram: `<a href>`; Markdown: `[title](link)`
- **<ITEMS_PER_SECTION> items per section**
- **Use bullet lists, no markdown tables** (Discord compatibility)

### Data Source Stats Footer
At the end of the report, append a stats line showing raw data collected from each pipeline step. Read the counts from the merged JSON's `input_sources` field or from each step's output. Format:

```
---
📊 数据源统计：RSS {{rss_count}} 篇 | Twitter {{twitter_count}} 条 | Web {{web_count}} 篇 | GitHub {{github_count}} 个 release | 合并去重后 {{merged_count}} 篇
```

## Archive
Save the report to `<WORKSPACE>/archive/tech-digest/<MODE>-YYYY-MM-DD.md`

After saving, delete archive files older than 90 days to prevent unbounded growth.

## Delivery
1. Send to Discord channel `<DISCORD_CHANNEL_ID>` via `message` tool
2. *(Optional)* Send email to `<EMAIL>` via `gog` CLI
   - **Must use `--body-html`** for proper rendering (plain text markdown looks bad in email clients)
   - Generate HTML email body following `<SKILL_DIR>/references/templates/email.md` format (inline styles, max-width 640px, system fonts)
   - Use format: `gog gmail send --to '<EMAIL>' --subject '<SUBJECT>' --body-html '<HTML>'`
   - Subject must be plain text with no shell metacharacters
   - Do NOT interpolate untrusted content into shell arguments

If any delivery fails, log the error but continue with remaining channels.

Write the report in <LANGUAGE>.

## Validation
Before running the pipeline, optionally validate configuration:
```bash
python3 <SKILL_DIR>/scripts/validate-config.py \
  --config-dir <WORKSPACE>/config \
  --defaults-dir <SKILL_DIR>/config/defaults \
  --verbose
```
