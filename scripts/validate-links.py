#!/usr/bin/env python3
"""validate-links.py — URL fidelity gate for rendered digests.

The rendering agent (LLM) sometimes retypes article URLs instead of copying
them byte-for-byte from the merged JSON, most often mangling date-path
segments: `/2026-11-13/slug/` becomes `/2026-11-13/slug/`. MacRumors and
similar sites 404 on the dash variant; 9to5mac only 301-redirects, so the
bug hides half the time.

This script diffs every URL in a rendered markdown report against the
canonical `link` values in the merged pipeline JSON, auto-fixes known
mangling patterns when the fix is unambiguous, and exits non-zero for
anything it cannot resolve so the pipeline can stop before delivery.

Usage:
  python3 validate-links.py --report daily-2026-11-14.md --merged td-merged.json [--fix] [--verbose]

Exit codes: 0 = all URLs clean (or fixed with --fix), 1 = unresolved URLs,
2 = usage/IO error.
"""

import argparse
import json
import re
import sys
from urllib.parse import urlparse

# URL inside <angle brackets>, markdown [..](url), or bare
URL_RE = re.compile(
    r'''<(https?://[^\s<>]+)>      # angle-bracket link
      | \]\((https?://[^)\s]+)\)  # markdown inline link
      | (https?://[^\s<>()\[\]]+) # bare URL
    ''',
    re.VERBOSE,
)

# /YYYY-MM-DD/ path segment (the mangling pattern this guards against)
DASH_DATE_RE = re.compile(r'(?<=/)(\d{4})-(\d{2})-(\d{2})(?=/)')

# Non-article URLs that legitimately appear outside the merged JSON
ALLOWLIST_PREFIXES = (
    'https://github.com/draco-agent/tech-news-digest',
    'https://nas.local/tech-news-digest/',
)


def extract_urls(markdown_text):
    """Yield (full_match, url, group_index) for every URL occurrence."""
    for m in URL_RE.finditer(markdown_text):
        idx = next(i for i in (1, 2, 3) if m.group(i))
        yield m, m.group(idx), idx


def canonical_links(merged):
    """Collect every `link` value from the merged JSON, recursively."""
    out = set()

    def walk(node):
        if isinstance(node, dict):
            link = node.get('link') or node.get('url')
            if isinstance(link, str) and link.startswith('http'):
                out.add(link)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(merged)
    return out


def normalize_variants(url):
    """Candidate canonical forms a mangled URL might have come from."""
    variants = set()
    dashed_to_slashed = DASH_DATE_RE.sub(r'\1/\2/\3', url)
    if dashed_to_slashed != url:
        variants.add(dashed_to_slashed)
    # ensure trailing slash parity for matching only
    for base in list(variants) + [url]:
        variants.add(base.rstrip('/') + '/')
        if base.endswith('/'):
            variants.add(base[:-1])
    return variants


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--report', required=True, help='Rendered markdown digest')
    ap.add_argument('--merged', required=True, help='Merged pipeline JSON')
    ap.add_argument('--fix', action='store_true',
                    help='Rewrite report with unambiguously fixed URLs')
    ap.add_argument('--verbose', action='store_true')
    args = ap.parse_args()

    try:
        with open(args.report, encoding='utf-8') as f:
            text = f.read()
        with open(args.merged, encoding='utf-8') as f:
            merged = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f'ERROR: {e}', file=sys.stderr)
        return 2

    truth = canonical_links(merged)
    if args.verbose:
        print(f'canonical links in merged JSON: {len(truth)}')

    replacements = {}   # url -> fixed url
    unresolved = []
    ok = 0
    for m, url, _ in extract_urls(text):
        if url in truth or any(url.startswith(p) for p in ALLOWLIST_PREFIXES):
            ok += 1
            continue
        candidates = [v for v in normalize_variants(url) if v in truth]
        if len(candidates) == 1:
            replacements[url] = candidates[0]
        else:
            unresolved.append(url)

    fixed = 0
    if replacements:
        print(f'MANGLED URLs detected ({len(replacements)}):')
        for bad, good in sorted(replacements.items()):
            print(f'  - {bad}\n  + {good}')
        if args.fix:
            for bad, good in replacements.items():
                text = text.replace(bad, good)
            with open(args.report, 'w', encoding='utf-8') as f:
                f.write(text)
            fixed = len(replacements)
            print(f'report rewritten with {fixed} fixes')
        else:
            print('ACTION_NEEDED: re-run with --fix (or correct manually) before delivery.')

    if unresolved or (replacements and not args.fix):
        if unresolved:
            print(f'UNRESOLVED URLs not present in merged JSON ({len(unresolved)}):')
            for u in sorted(set(unresolved)):
                print(f'  ? {u}')
            print('ACTION_NEEDED: replace these from the merged JSON `link` field '
                  'or remove the items before delivery.')
        return 1

    print(f'links OK: {ok + fixed} verified, {fixed} fixed, 0 unresolved')
    return 0


if __name__ == '__main__':
    sys.exit(main())
