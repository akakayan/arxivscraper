"""
Fetch recent math.AP papers from the arxiv API.

Paginates in windows of 100 until all papers newer than `lookback_days` are
retrieved, then stops. Papers already in `seen_ids` are excluded.
"""
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import requests

ARXIV_API = "https://export.arxiv.org/api/query"
PAGE_SIZE = 100
POLITENESS_DELAY = 3   # seconds between pages, per arxiv API guidelines
MAX_RETRIES = 4
RETRY_BACKOFF = [15, 60, 120, 300]  # seconds to wait before each retry attempt

_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def _get_with_retry(params: dict) -> requests.Response:
    """GET the arxiv API with retries on timeout, 5xx, and 429 errors."""
    for attempt, default_wait in enumerate(RETRY_BACKOFF, start=1):
        try:
            resp = requests.get(ARXIV_API, params=params, timeout=30)
            resp.raise_for_status()
            return resp
        except (requests.Timeout, requests.ConnectionError) as exc:
            if attempt == MAX_RETRIES:
                raise
            print(f"arxiv request failed (attempt {attempt}/{MAX_RETRIES}): {exc} — retrying in {default_wait}s")
            time.sleep(default_wait)
        except requests.HTTPError as exc:
            status = resp.status_code
            retryable = status == 429 or status >= 500
            if not retryable or attempt == MAX_RETRIES:
                raise
            # Honour Retry-After if the server sends one, otherwise use backoff table.
            retry_after = resp.headers.get("Retry-After")
            wait = int(retry_after) if retry_after and retry_after.isdigit() else default_wait
            print(f"arxiv HTTP {status} (attempt {attempt}/{MAX_RETRIES}) — retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError("unreachable")


def fetch_new_papers(seen_ids: set, lookback_days: int = 3) -> list[dict]:
    """Return math.AP papers from the last `lookback_days` days not in `seen_ids`."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    papers = []
    start = 0

    while True:
        params = {
            "search_query": "cat:math.AP",
            "start": start,
            "max_results": PAGE_SIZE,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        resp = _get_with_retry(params)

        root = ET.fromstring(resp.text)
        entries = root.findall("atom:entry", _NS)

        if not entries:
            break

        stop = False
        for entry in entries:
            paper, submitted_dt = _parse_entry(entry)
            if submitted_dt < cutoff:
                stop = True
                break
            if paper["id"] not in seen_ids:
                papers.append(paper)

        if stop or len(entries) < PAGE_SIZE:
            break

        start += PAGE_SIZE
        time.sleep(POLITENESS_DELAY)

    return papers


def _parse_entry(entry) -> tuple[dict, datetime]:
    arxiv_id = entry.find("atom:id", _NS).text.split("/abs/")[-1]
    title = " ".join(entry.find("atom:title", _NS).text.split())
    abstract = " ".join(entry.find("atom:summary", _NS).text.split())

    authors = [
        a.find("atom:name", _NS).text.strip()
        for a in entry.findall("atom:author", _NS)
    ]

    published_str = entry.find("atom:published", _NS).text
    submitted_dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
    submitted_date = submitted_dt.strftime("%Y-%m-%d")

    categories = [c.get("term") for c in entry.findall("atom:category", _NS)]

    return {
        "id": arxiv_id,
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "submitted": submitted_date,
        "categories": categories,
        "link": f"https://arxiv.org/abs/{arxiv_id}",
    }, submitted_dt
