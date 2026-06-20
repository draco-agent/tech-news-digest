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
import base64
import html
import re
import sys
import logging
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen


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


def _twemoji_name(emoji_text: str) -> str:
    """Return Twemoji asset name for an emoji sequence.

    Twemoji filenames are hyphen-joined lowercase codepoints. Variation selector
    U+FE0F is omitted for standalone emoji such as ❤️ -> 2764, while ZWJ and
    keycap codepoints are preserved.
    """
    cps = []
    for ch in emoji_text:
        cp = ord(ch)
        if cp == 0xFE0F:
            continue
        cps.append(f"{cp:x}")
    return "-".join(cps)


@lru_cache(maxsize=128)
def _twemoji_data_uri(name: str) -> str:
    cache_dir = Path.home() / ".cache" / "tech-news-digest" / "twemoji"
    cache_dir.mkdir(parents=True, exist_ok=True)
    svg_path = cache_dir / f"{name}.svg"
    if not svg_path.exists():
        url = f"https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/{name}.svg"
        with urlopen(url, timeout=10) as resp:
            svg_path.write_bytes(resp.read())
    data = base64.b64encode(svg_path.read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{data}"


def _emoji_replacement(match: re.Match) -> str:
    emoji_text = match.group(1)
    name = _twemoji_name(emoji_text)
    try:
        src = _twemoji_data_uri(name)
        return f'<img class="emoji" alt="{escape(emoji_text)}" src="{src}">'
    except Exception as exc:
        logging.debug("Twemoji fallback failed for %s (%s): %s", emoji_text, name, exc)
        return f'<span class="emoji">{emoji_text}</span>'


def wrap_emoji_spans(html_fragment: str) -> str:
    """Render emoji as Twemoji SVG images for reliable PDF output.

    Noto Color Emoji works in browsers, but WeasyPrint/Pango can embed its
    bitmap strikes at the wrong visual size on some Linux hosts. Using Twemoji
    SVGs keeps the existing emoji-based design while avoiding host font quirks.
    This operates after HTML escaping/inline markdown conversion, and skips tags
    so attributes/URLs are never modified.
    """
    parts = re.split(r'(<[^>]+>)', html_fragment)
    for i, part in enumerate(parts):
        if not part or part.startswith('<'):
            continue
        parts[i] = EMOJI_RE.sub(_emoji_replacement, part)
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


def _process_inline(text: str) -> str:
    """Process inline markdown with HTML escaping."""
    result = escape(text)

    # Bold: **text**
    result = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', result)

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

    result = wrap_emoji_spans(result)
    return result


def markdown_to_html(md_content: str) -> str:
    """Convert markdown digest to styled HTML for PDF rendering."""
    lines = md_content.strip().split('\n')
    html_parts = []
    in_list = False

    for line in lines:
        stripped = line.strip()

        if not stripped:
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            continue

        # H1
        if stripped.startswith('# '):
            title = _process_inline(stripped[2:])
            html_parts.append(f'<h1>{title}</h1>')
            continue

        # H2
        if stripped.startswith('## '):
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            section = _process_inline(stripped[3:])
            html_parts.append(f'<h2>{section}</h2>')
            continue

        # H3
        if stripped.startswith('### '):
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            section = _process_inline(stripped[4:])
            html_parts.append(f'<h3>{section}</h3>')
            continue

        # Blockquote
        if stripped.startswith('> '):
            text = _process_inline(stripped[2:])
            html_parts.append(f'<blockquote>{text}</blockquote>')
            continue

        # Horizontal rule
        if stripped == '---':
            html_parts.append('<hr>')
            continue

        # Bullet items
        if stripped.startswith('• ') or stripped.startswith('- '):
            if not in_list:
                html_parts.append('<ul>')
                in_list = True
            item_text = stripped[2:]
            safe_item = _process_inline(item_text)
            html_parts.append(f'<li>{safe_item}</li>')
            continue

        # Angle-bracket link on its own line (often source URLs)
        if stripped.startswith('<http') and in_list:
            url = stripped.strip('<> ')
            if is_safe_url(url):
                escaped_url = escape(url)
                try:
                    domain = urlparse(url).netloc
                    label = escape(domain)
                except Exception:
                    label = escaped_url
                html_parts.append(f'<li class="source-link"><a href="{escaped_url}">{label}</a></li>')
            continue

        # Stats/footer
        if stripped.startswith('📊') or stripped.startswith('🤖'):
            text = _process_inline(stripped)
            html_parts.append(f'<p class="footer">{text}</p>')
            continue

        # Regular paragraph
        text = _process_inline(stripped)
        html_parts.append(f'<p>{text}</p>')

    if in_list:
        html_parts.append('</ul>')

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
    font-size: 11pt;
    line-height: 1.7;
    color: #1a1a1a;
}

h1 {
    font-size: 22pt;
    color: #111;
    border-bottom: 3px solid #2563eb;
    padding-bottom: 8px;
    margin-bottom: 20px;
    margin-top: 0;
}

h2 {
    font-size: 15pt;
    color: #1e40af;
    margin-top: 28px;
    margin-bottom: 12px;
    padding-bottom: 4px;
    border-bottom: 1px solid #e5e7eb;
}

h3 {
    font-size: 13pt;
    color: #374151;
    margin-top: 20px;
    margin-bottom: 8px;
}

blockquote {
    background: #f0f4ff;
    border-left: 4px solid #2563eb;
    padding: 12px 16px;
    margin: 16px 0;
    color: #374151;
    font-size: 10.5pt;
    border-radius: 0 6px 6px 0;
}

ul {
    padding-left: 20px;
    margin: 8px 0;
}

li {
    margin-bottom: 10px;
    line-height: 1.6;
}

li.source-link {
    list-style: none;
    margin-bottom: 2px;
    margin-top: -6px;
}

li.source-link a {
    font-size: 9pt;
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
    display: inline-block;
    width: 1.05em;
    height: 1.05em;
    margin: 0 0.06em;
    vertical-align: -0.16em;
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
