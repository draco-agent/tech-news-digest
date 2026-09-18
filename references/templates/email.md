# Tech Digest Email Template

Hard report-body limits: daily ≤6500 characters, weekly ≤4800, excluding URL targets only (not headings, source labels or prose). No filling to the limit. A single concise coverage caveat without raw counts is allowed when missing/failed sources materially limit coverage; detailed failures remain in the operational log. These exceptions/limits apply to the shared canonical content in every format.

Use `markdown.md` for daily/weekly structure and `../digest-prompt.md` for authoritative editorial policy. Email is a rendering of the validated canonical archive, not a second selection pass.

## Editorial Contract

- Daily ≤30 unique items: 2–4 sentence overview; configured topic sections (normally 3–5 items each); KOL viewpoints ≤3; releases ≤3 repositories; project discovery ≤3; blog picks ≤3. Retain all daily headings, using a brief non-bullet coverage note for empty sections. News/blog explanations normally 2–3 sentences; do not reduce the report to headline fragments.
- Weekly ≤18 unique items: judgment, ≤3 evidence-backed syntheses, releases ≤5 repositories/actions, try ≤2, read ≤2, next-week proposed checks ≤3 (question + minimal test + metric, not performed).
- These are caps, not quotas. Count supporting events inside syntheses and standalone actions/checks too. Whole-report event/URL dedup; preserve daily topic sections; no extra weekly trend summary.
- Exactly the same selected items, claims and order as Discord, Markdown and PDF. Optional reading includes papers, docs, postmortems and essays.
- Daily retains KOL viewpoints without gossip; no quality scores, social/star metrics, source counts or operational/generator footer. Project discovery is not measured trending; no lifetime-derived growth.
- Apply the requested language, including Simplified Chinese explanations when configured. Do not dump untranslated titles/snippets.

## Safe Rendering and Delivery

1. Validate the archive: `python3 scripts/validate-digest.py --input FILE --mode daily` (or `weekly`). Fix all errors before delivery.
2. Convert via `sanitize-html.py` to an HTML **file**; do not interpolate fetched text/HTML into shell arguments or send raw Markdown.
3. Generate the optional PDF from the same archive; send with `send-email.py` as specified in `../digest-prompt.md`. Use static configured recipient, subject and optional sender values only. Do not substitute inline `gog --body-html` commands containing fetched content.
4. Check rendering preserves selections, links and language. Log missing PDF or delivery errors separately; do not claim unverified success.

Use a mobile-friendly width (about 640px), system fonts and inline styles. HTML must be escaped/sanitized, links restricted to HTTP(S). Use heading + list markup, bold item titles and compact inline source anchors, not raw URL rows or tables. No images needed.

Illustrative sanitized item shape (placeholders only):

```html
<li><strong>{{标题}}</strong> — {{变化与影响}}。<a href="{{HTTP_OR_HTTPS_URL}}">来源</a></li>
```

Operational statistics and attribution belong in the final operational log, never the email body or attachment.
