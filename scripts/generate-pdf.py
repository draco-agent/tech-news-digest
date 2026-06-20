#!/usr/bin/env python3
"""
Generate styled PDF from markdown digest report.

Converts a tech-news-digest markdown report into a professional PDF
with Chinese font support, emoji icons, and clean typography.

Usage:
    python3 generate-pdf.py --input /tmp/td-report.md --output /tmp/td-digest.pdf [--verbose]

Requirements:
    - weasyprint (pip install weasyprint)
    - Noto Sans CJK SC font (apt install fonts-noto-cjk)
    - Noto Color Emoji font (apt install fonts-noto-color-emoji)
"""

import argparse
import html
import re
import sys
import logging
from pathlib import Path
from urllib.parse import urlparse


# Emoji presentation characters used in digest headings and badges.
# We wrap them explicitly so WeasyPrint/Pango uses Noto Color Emoji instead of
# relying on font fallback from the CJK text stack. Without this, fontTools can
# try to subset an incompatible fallback font and fail with OS/2 unicode range
# values outside the supported range.
EMOJI_RE = re.compile(
    r'('
    r'(?:[\U0001F1E6-\U0001F1FF]{2})'  # regional indicator flags
    r'|(?:[\U0001F300-\U0001FAFF][\ufe0f\u20e3]?(?:\u200d[\U0001F300-\U0001FAFF][\ufe0f\u20e3]?)*?)'
    r'|(?:[\u2600-\u27BF]\ufe0f?)'
    r')'
)


def wrap_emoji_spans(html_fragment: str) -> str:
    """Wrap emoji codepoints in spans with the dedicated emoji font.

    This operates after HTML escaping/inline markdown conversion, and skips tags
    so attributes/URLs are never modified.
    """
    parts = re.split(r'(<[^>]+>)', html_fragment)
    for i, part in enumerate(parts):
        if not part or part.startswith('<'):
            continue
        parts[i] = EMOJI_RE.sub(r'<span class="emoji">\1</span>', part)
    return ''.join(parts)


# ---------------------------------------------------------------------------
# Markdown → HTML conversion (with sanitization)
# ---------------------------------------------------------------------------

def escape(text: str) -> str:
    return html.escape(text, quote=True)


def is_safe_url(url: str) -> bool:
    try:
        parsed = urlparse(url.strip())
        return parsed.scheme in ('http', 'https')
    except Exception:
        return False


def _process_inline(text: str, *, emoji: bool = False) -> str:
    """Process inline markdown with HTML escaping.

    PDF emoji rendering through Pango/WeasyPrint is unreliable on many Linux
    hosts. Keep emoji only when explicitly requested; otherwise remove emoji
    codepoints and rely on styled badges/headings for visual hierarchy.
    """
    if not emoji:
        text = EMOJI_RE.sub('', text)
    result = escape(text)

    # Bold: **text**
    result = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', result)

    # Italic: *text* (after bold so **...** is not consumed)
    result = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'<em>\1</em>', result)

    # Inline code: `text`
    result = re.sub(
        r'`(.+?)`',
        r'<code>\1</code>',
        result
    )

    # Angle-bracket links: <https://...>
    def restore_link(m):
        url = html.unescape(m.group(1))
        if is_safe_url(url):
            escaped_url = escape(url)
            try:
                domain = urlparse(url).netloc
                return f'<a href="{escaped_url}">{escape(domain)}</a>'
            except Exception:
                return f'<a href="{escaped_url}">{escaped_url}</a>'
        return escape(url)

    result = re.sub(r'&lt;(https?://[^&]+?)&gt;', restore_link, result)

    # Markdown links: [text](url)
    def restore_md_link(m):
        label = html.unescape(m.group(1))
        url = html.unescape(m.group(2))
        if is_safe_url(url):
            return f'<a href="{escape(url)}">{escape(label)}</a>'
        return escape(label)

    result = re.sub(r'\[([^\]]+?)\]\(([^)]+?)\)', restore_md_link, result)

    if emoji:
        result = wrap_emoji_spans(result)
    return result


def markdown_to_html(md_content: str) -> str:
    """Convert markdown digest to styled HTML for PDF rendering.

    The Discord markdown is optimized for chat, not print. For PDF we convert
    digest bullets into compact cards: score badge, summary, source domain, and
    optional metadata live in one block instead of becoming separate bullets.
    """
    lines = md_content.strip().split('\n')
    html_parts = []
    in_list = False
    open_card = False

    def close_list():
        nonlocal in_list
        if in_list:
            html_parts.append('</ul>')
            in_list = False

    def close_card():
        nonlocal open_card
        if open_card:
            html_parts.append('</div>')
            open_card = False

    def source_link_html(url_line: str) -> str:
        url = url_line.strip('<> ')
        if not is_safe_url(url):
            return ''
        escaped_url = escape(url)
        domain = escape(urlparse(url).netloc or url)
        return f'<div class="item-link"><a href="{escaped_url}">{domain}</a></div>'

    for line in lines:
        stripped = line.strip()

        if not stripped:
            close_list()
            continue

        # H1
        if stripped.startswith('# '):
            close_card(); close_list()
            title = _process_inline(stripped[2:])
            html_parts.append(f'<h1>{title}</h1>')
            continue

        # H2
        if stripped.startswith('## '):
            close_card(); close_list()
            section = _process_inline(stripped[3:])
            html_parts.append(f'<h2>{section}</h2>')
            continue

        # H3
        if stripped.startswith('### '):
            close_card(); close_list()
            section = _process_inline(stripped[4:])
            html_parts.append(f'<h3>{section}</h3>')
            continue

        # Blockquote
        if stripped.startswith('> '):
            close_card(); close_list()
            text = _process_inline(stripped[2:])
            html_parts.append(f'<blockquote>{text}</blockquote>')
            continue

        # Horizontal rule
        if stripped == '---':
            close_card(); close_list()
            html_parts.append('<hr>')
            continue

        # Digest item bullets, e.g. "• 🔥18 | summary".
        item_match = re.match(r'^[•\-]\s+(?:🔥\s*)?(\d+(?:\.\d+)?)\s*\|\s*(.+)$', stripped)
        if item_match:
            close_card(); close_list()
            score, summary = item_match.groups()
            html_parts.append('<div class="item-card">')
            html_parts.append(
                f'<div class="item-main"><span class="score-badge">{escape(score)}</span>'
                f'<span class="item-summary">{_process_inline(summary)}</span></div>'
            )
            open_card = True
            continue

        # Generic report bullets (KOL, releases, trending, blog picks).
        if stripped.startswith('• ') or stripped.startswith('- '):
            close_card(); close_list()
            item_text = stripped[2:]
            html_parts.append('<div class="item-card secondary">')
            html_parts.append(f'<div class="item-main"><span class="dot-badge"></span><span class="item-summary">{_process_inline(item_text)}</span></div>')
            open_card = True
            continue

        # Link after a card belongs to that card.
        if stripped.startswith('<http') and open_card:
            link = source_link_html(stripped)
            if link:
                html_parts.append(link)
            continue

        # Standalone link in a plain list.
        if stripped.startswith('<http') and in_list:
            link = source_link_html(stripped)
            if link:
                html_parts.append(f'<li class="source-link">{link}</li>')
            continue

        # Metadata after a card, e.g. *[2 sources]* or metrics.
        if open_card and (stripped.startswith('*[') or stripped.startswith('`') or stripped.startswith('*')):
            html_parts.append(f'<div class="item-meta">{_process_inline(stripped)}</div>')
            continue

        # Stats/footer
        if stripped.startswith('📊') or stripped.startswith('🤖'):
            close_card(); close_list()
            text = _process_inline(stripped)
            html_parts.append(f'<p class="footer">{text}</p>')
            continue

        # Regular paragraph
        close_card(); close_list()
        text = _process_inline(stripped)
        html_parts.append(f'<p>{text}</p>')

    close_card(); close_list()
    return '\n'.join(html_parts)


# ---------------------------------------------------------------------------
# PDF CSS
# ---------------------------------------------------------------------------

PDF_CSS = """
@page {
    size: A4;
    margin: 2cm 2.5cm;
    @top-center {
        content: "Tech Digest";
        font-size: 9px;
        color: #999;
        font-family: 'Noto Sans CJK SC', 'Noto Sans SC', sans-serif;
    }
    @bottom-center {
        content: counter(page) " / " counter(pages);
        font-size: 9px;
        color: #999;
        font-family: 'Noto Sans CJK SC', 'Noto Sans SC', sans-serif;
    }
}

@font-face {
    font-family: 'Noto Color Emoji PDF';
    src: url('file:///usr/share/fonts/truetype/noto/NotoColorEmoji.ttf') format('truetype');
    font-weight: 400;
    font-style: normal;
}

body {
    font-family: 'Noto Sans CJK SC', 'Noto Sans SC', 'PingFang SC',
                 'Microsoft YaHei', 'Segoe UI', Roboto, sans-serif;
    font-size: 10.2pt;
    line-height: 1.55;
    color: #172033;
    background: #ffffff;
}

h1 {
    font-size: 24pt;
    color: #0f172a;
    border-bottom: 3px solid #2563eb;
    padding-bottom: 9px;
    margin-bottom: 18px;
    margin-top: 0;
    letter-spacing: -0.02em;
}

h2 {
    font-size: 14.5pt;
    color: #1e40af;
    margin-top: 22px;
    margin-bottom: 10px;
    padding-bottom: 5px;
    border-bottom: 1px solid #dbe3f0;
    break-after: avoid;
}

h3 {
    font-size: 13pt;
    color: #374151;
    margin-top: 20px;
    margin-bottom: 8px;
}

blockquote {
    background: #f3f6ff;
    border-left: 4px solid #2563eb;
    padding: 11px 15px;
    margin: 14px 0 18px;
    color: #334155;
    font-size: 10.1pt;
    border-radius: 0 8px 8px 0;
}

.item-card {
    margin: 8px 0 10px;
    padding: 9px 11px;
    border: 1px solid #e6ebf5;
    border-left: 3px solid #3b82f6;
    border-radius: 8px;
    background: #ffffff;
    break-inside: avoid;
}

.item-card.secondary {
    border-left-color: #94a3b8;
}

.item-main {
    display: block;
}

.score-badge {
    display: inline-block;
    min-width: 22px;
    padding: 1px 7px;
    margin-right: 7px;
    border-radius: 999px;
    background: #2563eb;
    color: white;
    font-weight: 700;
    font-size: 8.5pt;
    line-height: 1.45;
    text-align: center;
}

.dot-badge {
    display: inline-block;
    width: 7px;
    height: 7px;
    margin-right: 8px;
    margin-bottom: 1px;
    border-radius: 50%;
    background: #64748b;
}

.item-summary {
    line-height: 1.55;
}

.item-link {
    margin-top: 5px;
    font-size: 8.5pt;
}

.item-meta {
    margin-top: 4px;
    color: #64748b;
    font-size: 8.6pt;
}

ul {
    padding-left: 18px;
    margin: 8px 0;
}

li {
    margin-bottom: 8px;
    line-height: 1.55;
}

li.source-link {
    list-style: none;
    margin-bottom: 2px;
    margin-top: -4px;
}

li.source-link a {
    font-size: 8.5pt;
}

a {
    color: #2563eb;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

strong {
    color: #111;
}

code {
    font-family: 'Noto Sans Mono CJK SC', 'SF Mono', 'Fira Code', monospace;
    font-size: 9pt;
    background: #f3f4f6;
    padding: 2px 5px;
    border-radius: 3px;
    color: #6b7280;
}

hr {
    border: none;
    border-top: 1px solid #e5e7eb;
    margin: 28px 0;
}

p.footer {
    font-size: 8.5pt;
    color: #9ca3af;
    margin-top: 4px;
}

/* First page title area */
h1 + blockquote {
    margin-top: 12px;
}

/* Emoji rendering */
body {
    -webkit-font-smoothing: antialiased;
}

.emoji {
    font-family: 'Noto Color Emoji PDF', 'Noto Color Emoji', 'Apple Color Emoji', 'Segoe UI Emoji', sans-serif;
    font-weight: 400;
}
"""


# ---------------------------------------------------------------------------
# HTML wrapper
# ---------------------------------------------------------------------------

def wrap_html(body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
{PDF_CSS}
</style>
</head>
<body>
{body}
</body>
</html>"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate styled PDF from markdown digest report",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
    python3 generate-pdf.py -i /tmp/td-report.md -o /tmp/td-digest.pdf
    python3 generate-pdf.py -i report.md -o digest.pdf --verbose

Requirements:
    pip install weasyprint
    apt install fonts-noto-cjk  (for Chinese support)
    apt install fonts-noto-color-emoji  (for emoji support)
"""
    )
    parser.add_argument("--input", "-i", required=True, help="Input markdown file")
    parser.add_argument("--output", "-o", required=True, help="Output PDF file")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s"
    )

    try:
        import weasyprint
    except ImportError:
        logging.error("weasyprint not installed. Run: pip install weasyprint")
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.exists():
        logging.error(f"Input file not found: {args.input}")
        sys.exit(1)

    md_content = input_path.read_text(encoding='utf-8')
    logging.info(f"Converting {args.input} ({len(md_content)} chars)")

    # Convert markdown → HTML → PDF
    body_html = markdown_to_html(md_content)
    full_html = wrap_html(body_html)

    # Optionally save intermediate HTML for debugging
    if args.verbose:
        html_debug = Path(args.output).with_suffix('.html')
        html_debug.write_text(full_html, encoding='utf-8')
        logging.debug(f"Debug HTML saved: {html_debug}")

    # Generate PDF
    logging.info("Generating PDF...")
    doc = weasyprint.HTML(string=full_html)
    doc.write_pdf(args.output)

    output_size = Path(args.output).stat().st_size
    logging.info(f"✅ PDF generated: {args.output} ({output_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
