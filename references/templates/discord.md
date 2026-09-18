# Tech Digest Discord Template

Hard report-body limits: daily ≤6500 characters, weekly ≤4800, excluding URL targets only (not headings, source labels or prose). No filling to the limit. A single concise coverage caveat without raw counts is allowed when missing/failed sources materially limit coverage; detailed failures remain in the operational log. These exceptions/limits apply to the shared canonical content in every format.

Use `markdown.md` for daily/weekly structure and `../digest-prompt.md` for authoritative editorial policy. Render the same selected items and judgments as the validated archive, email and PDF — do not reselect or append sections.

- Daily: ≤30 unique items overall; 2–4 sentence overview; configured topic sections, KOL viewpoints ≤3, releases ≤3 repositories, discovery ≤3, blog picks ≤3. Retain daily headings; use brief coverage notes if empty. News/blog items normally have 2–3 sentences of substance, not just headlines.
- Weekly: ≤18 unique items overall; judgment, ≤3 evidence-backed thematic syntheses, key releases ≤5 repositories with actions, try ≤2, read ≤2, proposed next-week checks ≤3 (question + minimal test + metric, explicitly not performed).
- Count unique supporting events inside themes and standalone action/check proposals, not just visible bullets. Caps are not quotas; retain daily headings and omit empty weekly sections. Preserve daily topic allocation; no duplicate weekly trend summary.

## Item Shape

```markdown
• **{{简短标题}}** — {{变化、意义或具体行动}}。[来源](<{{URL}}>)
```

Use plain bullet text with bold titles and concise inline `[来源](<URL>)` links (localized label for other languages). Angle brackets suppress embeds. Never put full URLs on a separate line. Add corroborating source links only within that event's single home. Daily includes substantive KOL viewpoints. No tables, scores, social/star metrics, source counts or operational/generator footers. Enforce `<LANGUAGE>`; Chinese output uses Simplified Chinese explanations, not raw English snippets.

## Delivery

- Send to the configured `DISCORD_CHANNEL_ID` with the available Discord/message tool. A DM requires an explicitly configured user target. Never put channel mentions in the body/archive.
- Validate the canonical report first with `scripts/validate-digest.py --input FILE --mode daily` or `--mode weekly`; fix errors before sending.
- Split at section boundaries, then between complete bullets as needed; label chunks `1/N`, `2/N`, etc. **Every chunk ≤1700 characters including numbering and continuation headings.** Shorten an oversized item; never cut a bullet or link in half.
- Keep only the current report in the batch. Read back sent messages; retry missing/failed chunks only. Delivery IDs, counts and failures go in the final operational log, not content.
