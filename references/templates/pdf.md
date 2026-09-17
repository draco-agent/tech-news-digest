# Tech Digest PDF Template

Hard report-body limits: daily ≤2600 characters, weekly ≤4800, excluding URL targets only (not headings, source labels or prose). No filling to the limit. A single concise coverage caveat without raw counts is allowed when missing/failed sources materially limit coverage; detailed failures remain in the operational log. These exceptions/limits apply to the shared canonical content in every format.

Use `markdown.md` for daily/weekly structure and `../digest-prompt.md` for authoritative editorial policy. PDF is a rendering of the same validated canonical report used for Discord and email, never an expanded edition.

## Editorial Contract

Daily ≤12 unique items: one-line takeaway, normally 3–5 focus, optional actions ≤2, releases ≤3 repositories, discovery ≤1, reading ≤1. Weekly ≤18: judgment, ≤3 evidence-backed syntheses, releases ≤5 repositories/actions, try ≤2, read ≤2, proposed next-week checks ≤3 (question + minimal test + metric, explicitly not performed). Count unique events inside themes and standalone actions/checks. All ceilings are caps, not quotas.

Preserve whole-report event/URL dedup, exact release versions/links, evidence-backed concise explanations and requested language (Simplified Chinese when configured). No fixed topic quotas, extra weekly trend summary, mandatory reading, fixed KOL section, public scores, social/star metrics, source counts or operational/generator footer. Discovery is not verified trending; never derive growth from lifetime stars. Use plain bullets with bold titles and compact inline source links.

## Generation and Verification

Prerequisites are `weasyprint` and suitable Chinese fonts (Noto Sans CJK SC). Do not install dependencies without authorization; report missing prerequisites.

```bash
python3 scripts/validate-digest.py --input /tmp/td-report.md --mode daily
python3 scripts/generate-pdf.py --input /tmp/td-report.md --output /tmp/td-digest.pdf
```

Use `--mode weekly` for a weekly report. In production, use the actual archived canonical report path instead of the example `/tmp/td-report.md`. Fix all validation errors before rendering/delivery.

Check readable text, links, page breaks and selection parity with Markdown/Discord/email; renderer-added metadata must not introduce public operational statistics. A4 typography, page numbers and neutral page headers are presentation only. Do not create PDF-only content or repeat source URLs as a second item list.

Attach via the configured Discord tool or `send-email.py` following `../digest-prompt.md`, not a separate mail command with an empty body. If PDF generation fails, report it in the final operational log and omit the attachment rather than inventing a successful artifact.
