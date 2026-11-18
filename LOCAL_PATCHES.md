# Local Patches for tech-news-digest

These changes were made on top of the upstream v3.16.0 release and must be
re-applied after any upstream update.

## 1. config_loader.py — Disabled topic filtering

**File:** `scripts/config_loader.py` (around line 217)

The upstream `merge_topics()` returns all topics including disabled ones.
We filter out disabled topics so the pipeline never processes them.

```python
# UPSTREAM (v3.16.0):
    logger.info(f"Merged topics: {len(default_topics)} defaults + {len(user_topics)} user = {len(result)} total topics")
    return result

# LOCAL:
    # Filter out disabled topics
    enabled_result = [t for t in result if t.get("enabled", True)]
    disabled_ids = [t.get("id") for t in result if not t.get("enabled", True)]
    if disabled_ids:
        logger.info(f"Disabled topics filtered out: {disabled_ids}")
    logger.info(f"Merged topics: {len(default_topics)} defaults + {len(user_topics)} user = {len(enabled_result)} active topics ({len(result) - len(enabled_result)} disabled)")
    return enabled_result
```

## 2. fetch-github.py — Crypto topic search query

**File:** `scripts/fetch-github.py` (around line 573)

Added a GitHub trending search query for crypto/blockchain topics.

```python
    {"topic": "crypto", "q": "blockchain ethereum solidity defi in:topics,name,description"},
```

## 3. fetch-rss.py — Graceful priority fallback

**File:** `scripts/fetch-rss.py` (around line 279)

Changed from strict `source["priority"]` to `source.get("priority", False)`
so sources missing the priority field don't crash the pipeline.

```python
# UPSTREAM:
    priority = source["priority"]

# LOCAL:
    priority = source.get("priority", False)
```

## 4. fetch-twitter.py — Graceful priority fallback (2 locations)

**File:** `scripts/fetch-twitter.py` (around lines 110 and 125)

Same pattern as fetch-rss.py — use `.get("priority", False)` instead of
strict `source["priority"]`.

```python
# UPSTREAM (line 110):
            "priority": source["priority"],

# LOCAL:
            "priority": source.get("priority", False),

# UPSTREAM (line 125):
            "priority": source["priority"],

# LOCAL:
            "priority": source.get("priority", False),
```

## 5. merge-sources.py — Custom topic priority order

**File:** `scripts/merge-sources.py` (around line 404)

Replaced `crypto` topic with `frontier_tech` and `consumer_tech`, and
renumbered priorities.

```python
# UPSTREAM:
        "crypto": 2,
        "github": 3,
        "trending": 4,
        "uncategorized": 5,

# LOCAL:
        "frontier_tech": 2,
        "consumer_tech": 3,
        "github": 4,
        "trending": 5,
        "uncategorized": 6,
```

## 6. config/schema.json — Relaxed validation + descriptions

**File:** `config/schema.json`

Benji's version has:
- Relaxed `required` fields (only `id`, `type`, `name` required for sources;
  only `id`, `label` required for topics)
- Nullable types for optional fields (`url`, `handle`, `repo`, `subreddit`,
  `emoji`, `description`)
- `twitter_queries` kept in topic search definition
- `minimal` style option kept
- No `allOf` conditional validation
- No `$schema`/`title`/`version` header

The upstream v3.16.2 schema is stricter (requires `enabled`, `priority`,
`topics` on sources; requires `emoji`, `description`, `search`, `display` on
topics; adds conditional `allOf` rules). We keep the relaxed version because
our config files don't include all required fields.

---

_Updated: 2026-05-26 — baseline v3.16.0, target v3.16.2_