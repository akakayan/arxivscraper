"""
One-time script to seed authors.json from the Math Genealogy Project.

Usage (run locally, not via GitHub Actions):
    pip install requests
    python genealogy_seed.py

Algorithm:
  1. Start from SEED_NAMES — well-known researchers in nonlinear waves / math GR.
  2. Search MGP by name to find each person's MGP ID.
  3. Crawl their students (2 levels deep), using IDs directly (no re-searching).
  4. For each discovered name, verify they have at least one math.AP or gr-qc
     paper on arxiv (last-name + first-initial search).
  5. Write all verified names to authors.json.

SEED_NAMES are always included regardless of arxiv verification.
"""
import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

MGP_BASE = "https://www.genealogy.math.ndsu.nodak.edu"
ARXIV_API = "https://export.arxiv.org/api/query"
AUTHORS_FILE = "authors.json"
CRAWL_DEPTH = 2  # seed → students → grandstudents

SEED_NAMES = [
    "Sergiu Klainerman",
    "Demetrios Christodoulou",
    "Hans Lindblad",
    "Igor Rodnianski",
    "Daniel Tataru",
    "Wilhelm Schlag",
    "Christopher Sogge",
    "Mihalis Dafermos",
    "Jared Speck",
    "Jonathan Luk",
    "Sung-Jin Oh",
    "Qian Wang",
    "Nader Masmoudi",
]

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "arxivscraper/1.0 (research tool; contact: abakakayan@gmail.com)"

_NS = {"atom": "http://www.w3.org/2005/Atom"}


# ── MGP helpers ───────────────────────────────────────────────────────────────

def _mgp_search_id(full_name: str) -> int | None:
    """
    Search MGP for `full_name` and return the best-matching MGP person ID.

    MGP form: POST to query-prep.php with given_name / family_name fields,
    which redirects to results.php containing id.php?id=DIGITS links.
    """
    parts = full_name.strip().split()
    family = parts[-1] if parts else ""
    given = parts[0] if len(parts) > 1 else ""
    try:
        resp = SESSION.post(
            f"{MGP_BASE}/query-prep.php",
            data={"chrono": "0", "given_name": given, "family_name": family, "other_names": ""},
            timeout=15,
            allow_redirects=True,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"  MGP search failed for '{full_name}': {exc}")
        return None

    # Results page contains links like id.php?id=DIGITS
    ids = re.findall(r"id\.php\?id=(\d+)", resp.text)
    if not ids:
        return None

    # If only one result, return it directly
    if len(ids) == 1:
        return int(ids[0])

    # Multiple results — pick the one whose name text contains the family name
    family_lower = family.lower()
    matches = re.findall(r'id\.php\?id=(\d+)"[^>]*>([^<]+)<', resp.text)
    for mgp_id, name_text in matches:
        if family_lower in name_text.lower():
            return int(mgp_id)

    return int(ids[0])


def _mgp_students(mgp_id: int) -> list[tuple[int, str]]:
    """
    Fetch MGP person page and return listed students as [(id, 'First Last')].
    Names in MGP are 'Last, First'; we convert them here.
    """
    try:
        resp = SESSION.get(f"{MGP_BASE}/id.php", params={"id": mgp_id}, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"  MGP fetch failed for id {mgp_id}: {exc}")
        return []

    html = resp.text
    student_start = html.find("Students:")
    if student_start == -1:
        return []

    # Extract all id.php?id=DIGITS links with their text from the student section.
    # Exclude the chronological-order link (id.php?fChrono=1&id=...).
    student_html = html[student_start:]
    matches = re.findall(r'id\.php\?id=(\d+)"[^>]*>([^<]+)<', student_html)

    students = []
    for sid, raw_name in matches:
        # Convert "Last, First Middle" → "First Middle Last"
        if "," in raw_name:
            last, rest = raw_name.split(",", 1)
            name = f"{rest.strip()} {last.strip()}"
        else:
            name = raw_name.strip()
        students.append((int(sid), name))

    return students


RECENCY_YEARS = 3       # exclude authors with no papers in the last N years
ARXIV_DELAY = 3          # seconds between arxiv API calls (per arxiv guidelines)
ARXIV_RETRY_WAIT_429 = 60  # seconds to wait after a 429 (rate limit)
ARXIV_RETRY_WAIT_ERR = 5   # seconds to wait after a timeout or other network error
ARXIV_MAX_RETRIES = 2

# ── Arxiv verification ────────────────────────────────────────────────────────

def _has_recent_arxiv_papers(name: str) -> bool:
    """
    Return True if `name` has a math.AP or gr-qc paper within the last
    RECENCY_YEARS years. Retries up to ARXIV_MAX_RETRIES times on 429.
    """
    parts = name.strip().split()
    if not parts:
        return False
    last = parts[-1]
    first = parts[0] if len(parts) > 1 else ""
    # Try both name orderings: Last_First and First_Last
    candidates = [f"au:{last}_{first}", f"au:{first}_{last}"] if first else [f"au:{last}"]
    cutoff = datetime.now(timezone.utc) - timedelta(days=RECENCY_YEARS * 365)

    for author_q in candidates:
        params = {
            "search_query": f"{author_q} AND (cat:math.AP OR cat:gr-qc)",
            "max_results": 1,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        for attempt in range(1, ARXIV_MAX_RETRIES + 1):
            try:
                resp = SESSION.get(ARXIV_API, params=params, timeout=10)
                if resp.status_code == 429:
                    print(f"  429 rate-limited — waiting {ARXIV_RETRY_WAIT_429}s (attempt {attempt})")
                    time.sleep(ARXIV_RETRY_WAIT_429)
                    continue
                resp.raise_for_status()
                root = ET.fromstring(resp.text)
                entries = root.findall("atom:entry", _NS)
                if entries:
                    published = entries[0].find("atom:published", _NS).text
                    paper_date = datetime.fromisoformat(published.replace("Z", "+00:00"))
                    if paper_date >= cutoff:
                        return True
                break  # clean response (even if empty) — try next name ordering
            except requests.Timeout:
                print(f"  Timeout for '{name}' (attempt {attempt}) — skipping")
                break  # don't retry timeouts; move on
            except requests.RequestException as exc:
                print(f"  Arxiv check failed for '{name}' (attempt {attempt}): {exc}")
                if attempt < ARXIV_MAX_RETRIES:
                    time.sleep(ARXIV_RETRY_WAIT_ERR)
        time.sleep(ARXIV_DELAY)

    return False


# ── Crawl ─────────────────────────────────────────────────────────────────────

def _save_authors(authors: set[str], path: Path) -> None:
    """Write current verified set to disk immediately."""
    path.write_text(json.dumps(sorted(authors), indent=2, ensure_ascii=False), encoding="utf-8")


def crawl(existing: set[str], out_path: Path) -> list[str]:
    verified: set[str] = existing | set(SEED_NAMES)
    visited_ids: set[int] = set()

    # Flush seeds to disk right away
    _save_authors(verified, out_path)

    seed_queue: list[tuple[int | None, str, int]] = []
    for name in SEED_NAMES:
        print(f"Looking up MGP ID for seed: {name}")
        mgp_id = _mgp_search_id(name)
        print(f"  → ID: {mgp_id}")
        seed_queue.append((mgp_id, name, 0))
        time.sleep(1)

    queue = seed_queue

    while queue:
        mgp_id, name, depth = queue.pop(0)

        if mgp_id is None or mgp_id in visited_ids:
            continue
        visited_ids.add(mgp_id)

        print(f"[depth {depth}] {name} (id={mgp_id})")

        if depth < CRAWL_DEPTH:
            students = _mgp_students(mgp_id)
            print(f"  → {len(students)} students")
            for sid, sname in students:
                if sid not in visited_ids:
                    queue.append((sid, sname, depth + 1))
            time.sleep(1)

        if name not in SEED_NAMES:
            if name in verified:
                print(f"  already verified: {name}")
            elif _has_recent_arxiv_papers(name):
                print(f"  verified: {name}")
                verified.add(name)
                _save_authors(verified, out_path)  # persist immediately
                time.sleep(ARXIV_DELAY)
            else:
                print(f"  skip: {name}")
                time.sleep(ARXIV_DELAY)

    return sorted(verified)


def main() -> None:
    p = Path(AUTHORS_FILE)
    existing: set[str] = set()
    if p.exists() and p.stat().st_size > 2:
        existing = set(json.loads(p.read_text(encoding="utf-8")))
        print(f"Loaded {len(existing)} existing authors from {AUTHORS_FILE}")

    print(f"\nStarting Math Genealogy crawl (depth={CRAWL_DEPTH})…\n")
    try:
        crawl(existing, p)
    except KeyboardInterrupt:
        print("\nInterrupted — progress already saved to authors.json.")
        return

    print(f"\nDone. {len(json.loads(p.read_text()))} authors in {AUTHORS_FILE}")


if __name__ == "__main__":
    main()
