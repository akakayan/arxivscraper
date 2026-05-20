"""
Newsletter send job entry point.

  1. Load pending.json
  2. If non-empty, render HTML and send email
  3. Clear pending.json
"""
import json
import os
import sys
from pathlib import Path

from emailer import send_newsletter
from newsletter import make_subject, render_html

PENDING_FILE = "pending.json"


def main() -> None:
    p = Path(PENDING_FILE)
    if not p.exists() or p.stat().st_size == 0:
        print("No pending.json or empty — nothing to send.")
        return

    pending = json.loads(p.read_text(encoding="utf-8"))
    if not pending:
        print("pending.json is empty — nothing to send.")
        return

    print(f"Sending newsletter with {len(pending)} paper(s)…")

    app_password = os.environ.get("GMAIL_APP_PASSWORD", "")
    if not app_password:
        print("ERROR: GMAIL_APP_PASSWORD environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    html = render_html(pending)
    subject = make_subject(pending)
    send_newsletter(html, subject, app_password)
    print(f"Sent: {subject}")

    p.write_text("[]", encoding="utf-8")
    print("Cleared pending.json.")


if __name__ == "__main__":
    main()
