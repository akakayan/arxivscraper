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
POLITENESS_DELAY = 3  # seconds between requests, per arxiv API guidelines

_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


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
        resp = requests.get(ARXIV_API, params=params, timeout=30)
        resp.raise_for_status()

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
