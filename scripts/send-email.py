#!/usr/bin/env python3
"""
Send HTML email with optional PDF attachment via Resend, msmtp, or sendmail.

Properly constructs MIME multipart message so HTML body renders correctly
when attachments are included, while also supporting direct API delivery.

Usage:
    python3 send-email.py --to user@example.com --subject "Daily Digest" \
        --html /tmp/td-email.html [--attach /tmp/td-digest.pdf] [--from "Bot <bot@example.com>"]
"""

import argparse
import base64
import json
import logging
import os
import subprocess
import sys
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


RESEND_API_BASE = "https://api.resend.com/emails"
RESEND_USER_AGENT = "tech-news-digest/1.0"


def build_message(subject: str, from_addr: str, to_addrs: list,
                  html_path: Path, attach_path: Path = None) -> str:
    """Build a proper MIME message with HTML body and optional attachment."""
    
    html_content = html_path.read_text(encoding='utf-8')
    
    if attach_path and attach_path.exists():
        # Multipart mixed: HTML body + attachment
        msg = MIMEMultipart('mixed')
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        pdf_data = attach_path.read_bytes()
        pdf_part = MIMEApplication(pdf_data, _subtype='pdf')
        pdf_part.add_header('Content-Disposition', 'attachment',
                           filename=attach_path.name)
        msg.attach(pdf_part)
    else:
        # Simple HTML message
        msg = MIMEText(html_content, 'html', 'utf-8')
    
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = ', '.join(to_addrs)
    msg['Date'] = formatdate(localtime=True)
    
    return msg.as_string()


def send_via_resend(subject: str, from_addr: str, to_addrs: list,
                    html_path: Path, attach_path: Path = None,
                    api_key: str = None) -> bool:
    """Send via Resend HTTP API."""
    if not api_key:
        logging.debug("Resend API key not set")
        return False

    try:
        payload = {
            "from": from_addr,
            "to": to_addrs,
            "subject": subject,
            "html": html_path.read_text(encoding='utf-8'),
        }
        if attach_path and attach_path.exists():
            payload["attachments"] = [{
                "filename": attach_path.name,
                "content": base64.b64encode(attach_path.read_bytes()).decode("ascii"),
            }]

        req = Request(
            RESEND_API_BASE,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": RESEND_USER_AGENT,
                "Accept": "application/json",
            },
            method="POST",
        )
        with urlopen(req, timeout=30) as resp:
            if 200 <= resp.status < 300:
                return True
            logging.error(f"Resend failed: HTTP {resp.status}")
            return False
    except HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        if e.code == 403 and "1010" in body:
            logging.error(
                "Resend failed: HTTP 403 error code 1010. "
                "This usually means the request was blocked before reaching the API, "
                "often because the HTTP request is missing a User-Agent header."
            )
        logging.error(f"Resend failed: HTTP {e.code} {body[:300]}")
        return False
    except URLError as e:
        logging.error(f"Resend network error: {e}")
        return False
    except Exception as e:
        logging.error(f"Resend error: {e}")
        return False


def send_via_msmtp(message: str, to_addrs: list) -> bool:
    """Send via msmtp (preferred)."""
    try:
        result = subprocess.run(
            ['msmtp', '--read-envelope-from'] + to_addrs,
            input=message.encode('utf-8'),
            capture_output=True,
            timeout=30
        )
        if result.returncode == 0:
            return True
        logging.error(f"msmtp failed: {result.stderr.decode()}")
        return False
    except FileNotFoundError:
        logging.debug("msmtp not found")
        return False
    except Exception as e:
        logging.error(f"msmtp error: {e}")
        return False


def send_via_sendmail(message: str, to_addrs: list) -> bool:
    """Send via sendmail (fallback)."""
    for cmd in ['sendmail', '/usr/sbin/sendmail']:
        try:
            result = subprocess.run(
                [cmd, '-t'] + to_addrs,
                input=message.encode('utf-8'),
                capture_output=True,
                timeout=30
            )
            if result.returncode == 0:
                return True
            logging.error(f"{cmd} failed: {result.stderr.decode()}")
        except FileNotFoundError:
            continue
        except Exception as e:
            logging.error(f"{cmd} error: {e}")
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Send HTML email with optional PDF attachment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
    python3 send-email.py --to user@example.com --subject "Daily Digest" --html /tmp/td-email.html
    python3 send-email.py --to a@x.com --to b@y.com --subject "Weekly" --html body.html --attach digest.pdf
    python3 send-email.py --to user@x.com --subject "Test" --html body.html --from "Bot <bot@x.com>"
    python3 send-email.py --to user@x.com --subject "Test" --html body.html --provider resend
"""
    )
    parser.add_argument('--to', action='append', required=True, help='Recipient email (repeatable)')
    parser.add_argument('--subject', '-s', required=True, help='Email subject')
    parser.add_argument('--html', required=True, type=Path, help='HTML body file')
    parser.add_argument('--attach', type=Path, default=None, help='PDF attachment file')
    parser.add_argument('--from', dest='from_addr', default=None, help='From address')
    parser.add_argument('--provider', choices=['auto', 'resend', 'msmtp', 'sendmail'], default='auto', help='Email delivery provider')
    parser.add_argument('--resend-api-key', default=None, help='Resend API key (default: RESEND_API_KEY env var)')
    parser.add_argument('--verbose', '-v', action='store_true')
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s"
    )
    
    if not args.html.exists():
        logging.error(f"HTML file not found: {args.html}")
        sys.exit(1)
    
    # Expand comma-separated addresses
    to_addrs = []
    for addr in args.to:
        to_addrs.extend([a.strip() for a in addr.split(',') if a.strip()])

    resend_api_key = args.resend_api_key or os.environ.get('RESEND_API_KEY')
    from_addr = args.from_addr or os.environ.get('RESEND_FROM') or 'noreply@localhost'

    logging.info(f"Building email: {args.subject} -> {', '.join(to_addrs)}")
    logging.info(f"Provider mode: {args.provider}")
    if args.attach:
        logging.info(f"Attachment: {args.attach} ({'exists' if args.attach.exists() else 'MISSING'})")

    provider_attempts = ['resend', 'msmtp', 'sendmail'] if args.provider == 'auto' else [args.provider]
    message = build_message(args.subject, from_addr, to_addrs, args.html, args.attach)

    for provider in provider_attempts:
        if provider == 'resend':
            if send_via_resend(args.subject, from_addr, to_addrs, args.html, args.attach, resend_api_key):
                logging.info("✅ Sent via Resend")
                return 0
        elif provider == 'msmtp':
            if send_via_msmtp(message, to_addrs):
                logging.info("✅ Sent via msmtp")
                return 0
        elif provider == 'sendmail':
            if send_via_sendmail(message, to_addrs):
                logging.info("✅ Sent via sendmail")
                return 0

    logging.error("❌ All send methods failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())



