# Canonical Markdown Template

Hard report-body limits: daily ≤2600 characters, weekly ≤4800, excluding URL targets only (not headings, source labels or prose). No filling to the limit. A single concise coverage caveat without raw counts is allowed when missing/failed sources materially limit coverage; detailed failures remain in the operational log. These exceptions/limits apply to the shared canonical content in every format.

Follow `../digest-prompt.md` as the authoritative editorial policy. Select once; all formats use the same items, judgments and order. These are structural placeholders, not factual examples or mandatory fill-in quotas. Translate headings to `<LANGUAGE>`; Chinese means Simplified Chinese.

## Daily — at most 12 unique items overall

```markdown
# 科技日报 — {{DATE}}

> {{一句话判断：只概括已选证据}}

## 今日重点
• **{{标题}}** — {{变化与影响}}。[来源](<{{URL}}>)

## 可行动
• **{{行动}}** — {{适用对象与理由；不重复重点事件}}。[来源](<{{URL}}>)

## 工具与发布
• **{{owner/repo vX.Y.Z}}** — {{已核实的关键变化；谁应行动}}。[来源](<{{RELEASE_URL}}>)

## 项目发现
• **{{项目}}** — {{用途与当前值得尝试的理由}}。[来源](<{{URL}}>)

## 值得读
• **{{论文、文档、复盘或文章}}** — {{阅读收益}}。[来源](<{{URL}}>)
```

Focus normally 3–5 (fewer if evidence is thin); optional standalone actions ≤2; releases ≤3 repositories; discovery ≤1; reading ≤1. All contribute to the global cap; omit empty optional sections. No fixed topic quotas.

## Weekly — at most 18 unique items overall

```markdown
# 科技周报 — {{DATE}}

> {{本周判断与仍存的不确定性}}

## 本周主题
• **{{主题结论}}** — {{连接多个已核实进展的综合判断、影响与局限}}。[来源](<{{ORIGINAL_URL}}>) [来源](<{{INDEPENDENT_URL}}>)

## 关键发布与行动
• **{{owner/repo vX.Y.Z}}** — {{关键变化；适用对象与行动}}。[来源](<{{RELEASE_URL}}>)

## 值得试
• **{{项目}}** — {{用途与当前尝试理由}}。[来源](<{{URL}}>)

## 值得读
• **{{论文、文档、复盘或文章}}** — {{阅读收益}}。[来源](<{{URL}}>)

## 下周验证（拟议，尚未执行）
• **{{问题}}** — 最小测试：{{测试设计}}；指标/判定阈值：{{可测量标准}}；依据：{{前文主题名，不重复其链接}}。
```

Themes ≤3, evidence-backed syntheses rather than an expanded daily list; releases ≤5 repositories; try ≤2; read ≤2; proposed validation checks ≤3. Count every unique evidence event inside themes, plus standalone actions/checks, toward 18. Weekly may synthesize daily coverage; daily repeats need an explicit incremental development. Do not append another trend summary from legacy cron parameters.

## Shared Checks

- All limits are caps, not quotas. Deduplicate canonical URLs and events across the entire report; one event has one home. Advice integrated in that home is preferable to a repeated action item.
- Titles bold, summaries plain and concise, links inline. Use `•` bullets compatible with existing renderers. No tables, raw URL lines, fixed KOL section, scores, social metrics or operational/generator footers.
- Releases: one repository per bullet, exact version and official release link, verified impact; Chinese explanation ≤80 characters excluding name/version/URL. Release caps apply anywhere in the report.
- Discovery is not proven popularity/trending. No lifetime-derived star growth; do not repeatedly feature mature repos without meaningful changes.
- Validate this exact canonical file with `scripts/validate-digest.py --input FILE --mode daily` or `--mode weekly`, fixing every error before delivery. Preserve this selection for Discord, email and PDF. Operational statistics belong only in the final log.
