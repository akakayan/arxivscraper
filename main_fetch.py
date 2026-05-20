"""
Daily fetch job entry point.

  1. Load seen_ids.json, pending.json, authors.json
  2. Fetch new math.AP papers from arxiv
  3. Run four-tier relevance filter
  4. Append relevant papers to pending.json
  5. Update seen_ids.json (trimmed to last 90 days)
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from filter import filter_papers, load_authors
from scraper import fetch_new_papers

SEEN_IDS_FILE = "seen_ids.json"
PENDING_FILE = "pending.json"
AUTHORS_FILE = "authors.json"
LOOKBACK_DAYS = 3
SEEN_TTL_DAYS = 90


def _load(path: str, default):
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return default
    return json.loads(p.read_text(encoding="utf-8-sig"))


def _save(path: str, data) -> None:
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _trim_seen(seen: list[dict]) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=SEEN_TTL_DAYS)
    return [e for e in seen if datetime.fromisoformat(e["seen_at"]) > cutoff]


def main() -> None:
    seen_raw = _trim_seen(_load(SEEN_IDS_FILE, []))
    seen_ids = {e["id"] for e in seen_raw}
    pending = _load(PENDING_FILE, [])
    authors_set = load_authors(AUTHORS_FILE)

    print(f"State: {len(seen_ids)} seen IDs, {len(pending)} pending, {len(authors_set)} authors")

    papers = fetch_new_papers(seen_ids, lookback_days=LOOKBACK_DAYS)
    print(f"Fetched {len(papers)} new papers from arxiv math.AP")

    relevant = filter_papers(papers, authors_set)
    print(f"Relevant after filtering: {len(relevant)}")
    for p in relevant:
        print(f"  [{p['filter_reason']}] {p['title'][:80]}")

    now = datetime.now(timezone.utc).isoformat()
    seen_raw.extend({"id": p["id"], "seen_at": now} for p in papers)
    pending.extend(relevant)

    _save(SEEN_IDS_FILE, seen_raw)
    _save(PENDING_FILE, pending)
    print(f"Saved: {len(seen_raw)} seen IDs, {len(pending)} total pending")


if __name__ == "__main__":
    main()
