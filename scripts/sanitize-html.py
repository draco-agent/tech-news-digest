#!/usr/bin/env python3
"""
Sanitize media digest markdown report into safe HTML email.

Reads a markdown report file, escapes all text content to prevent XSS,
and outputs a styled HTML email body safe for injection into email clients.

Usage:
    python3 sanitize-html.py --input /tmp/md-report.md --output /tmp/md-email.html [--verbose]

Security:
    - All text content is HTML-escaped (prevents XSS from malicious RSS/Twitter/web content)
    - Only whitelisted tags/attributes are allowed
    - URLs are validated (must be http/https)
    - No JavaScript, event handlers, or data: URIs allowed
"""

import argparse
import html
import re
import sys
import logging
from urllib.parse import urlparse


def escape(text: str) -> str:
    """HTML-escape text content."""
    return html.escape(text, quote=True)


def is_safe_url(url: str) -> bool:
    """Validate URL is http(s) only — no javascript:, data:, etc."""
    try:
        parsed = urlparse(url.strip())
        return parsed.scheme in ('http', 'https')
    except Exception:
        return False


def safe_link(url: str, label: str = None, style: str = "color:#0969da;font-size:13px") -> str:
    """Generate a safe HTML link with escaped content."""
    url = url.strip()
    if not is_safe_url(url):
        return escape(label or url)
    escaped_url = escape(url)
    escaped_label = escape(label or url)
    return f'<a href="{escaped_url}" style="{style}">{escaped_label}</a>'


def markdown_to_safe_html(md_content: str) -> str:
    """Convert markdown digest report to sanitized HTML email."""
    lines = md_content.strip().split('\n')
    html_parts = []
    
    # Email wrapper open
    html_parts.append(
        '<div style="max-width:640px;margin:0 auto;font-family:'
        '-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif;'
        'color:#1a1a1a;line-height:1.6">'
    )
    
    in_list = False
    
    for line in lines:
        stripped = line.strip()
        
        # Skip empty lines
        if not stripped:
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            continue
        
        # H1: # Title
        if stripped.startswith('# '):
            title = escape(stripped[2:])
            html_parts.append(
                f'<h1 style="font-size:22px;border-bottom:2px solid #e5e5e5;'
                f'padding-bottom:8px">{title}</h1>'
            )
            continue
        
        # H2: ## Section
        if stripped.startswith('## '):
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            section = escape(stripped[3:])
            html_parts.append(
                f'<h2 style="font-size:17px;margin-top:24px;color:#333">{section}</h2>'
            )
            continue
        
        # Blockquote: > executive summary
        if stripped.startswith('> '):
            text = escape(stripped[2:])
            html_parts.append(
                f'<p style="color:#555;font-size:14px;background:#f8f9fa;'
                f'padding:12px;border-radius:6px">{text}</p>'
            )
            continue
        
        # Horizontal rule
        if stripped == '---':
            html_parts.append('<hr style="border:none;border-top:1px solid #e5e5e5;margin:24px 0">')
            continue
        
        # Bullet items: • or -
        if stripped.startswith('• ') or stripped.startswith('- '):
            if not in_list:
                html_parts.append('<ul style="padding-left:20px">')
                in_list = True
            item_text = stripped[2:]
            safe_item = _process_inline(item_text)
            html_parts.append(f'<li style="margin-bottom:10px">{safe_item}</li>')
            continue
        
        # Continuation of bullet (indented line with link)
        if stripped.startswith('<http') and in_list:
            url = stripped.strip('<> ')
            link = safe_link(url)
            html_parts.append(f'<li style="margin-bottom:2px;list-style:none">{link}</li>')
            continue
        
        # Stats/footer line
        if stripped.startswith('📊') or stripped.startswith('🤖'):
            text = _process_inline(stripped)
            html_parts.append(f'<p style="font-size:12px;color:#888">{text}</p>')
            continue
        
        # Regular paragraph
        text = _process_inline(stripped)
        html_parts.append(f'<p>{text}</p>')
    
    if in_list:
        html_parts.append('</ul>')
    
    html_parts.append('</div>')
    return '\n'.join(html_parts)


def _process_inline(text: str) -> str:
    """Render raw markdown tokens once, escaping every text/attribute value.

    Consume labelled links before angle autolinks so Discord's [label](<url>)
    cannot be rewritten into HTML and then mistaken for an unsafe URL. Never
    run markdown substitutions over generated HTML (or over code/URL content).
    """
    tokens = re.compile(
        r'`(?P<code>[^`]+)`'
        r'|\[(?P<label>[^\]\n]+)\]\('
        r'(?:<(?P<suppressed>[^<>\n]+)>|(?P<url>(?:[^()\n]|\([^()\n]*\))+))\)'
        r'|<(?P<angle>https?://[^<>\n]+)>'
        r'|\*\*(?P<bold>.+?)\*\*'
    )
    parts = []
    position = 0
    for match in tokens.finditer(text):
        parts.append(escape(text[position:match.start()]))
        if match.group('code') is not None:
            parts.append('<code style="font-size:12px;color:#888;background:#f4f4f4;padding:2px 6px;border-radius:3px">' + escape(match.group('code')) + '</code>')
        elif match.group('bold') is not None:
            parts.append('<strong>' + _process_inline(match.group('bold')) + '</strong>')
        else:
            url = (match.group('suppressed') or match.group('url') or match.group('angle')).strip()
            label = match.group('label')
            if is_safe_url(url):
                if label is None:
                    label = urlparse(url).netloc or url
                parts.append(f'<a href="{escape(url)}" style="color:#0969da;font-size:13px">{escape(label)}</a>')
            else:
                parts.append(escape(label if label is not None else url))
        position = match.end()
    parts.append(escape(text[position:]))
    result = ''.join(parts)
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Convert markdown digest to sanitized HTML email"
    )
    parser.add_argument("--input", "-i", required=True, help="Input markdown file")
    parser.add_argument("--output", "-o", required=True, help="Output HTML file")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s"
    )
    
    try:
        with open(args.input, 'r') as f:
            md_content = f.read()
    except FileNotFoundError:
        logging.error(f"Input file not found: {args.input}")
        sys.exit(1)
    
    logging.info(f"Converting {args.input} ({len(md_content)} chars)")
    
    html_output = markdown_to_safe_html(md_content)
    
    with open(args.output, 'w') as f:
        f.write(html_output)
    
    logging.info(f"Wrote sanitized HTML to {args.output} ({len(html_output)} chars)")


if __name__ == "__main__":
    main()
