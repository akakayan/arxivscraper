"""
Fetch recent math.AP papers from the arXiv OAI-PMH harvesting interface.

OAI-PMH is designed for automated harvesting (unlike the search API which
rate-limits cloud IPs aggressively). We use metadataPrefix=arXiv for full
metadata including abstract and categories.
"""
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import requests

OAI_ENDPOINT = "https://export.arxiv.org/oai2"
POLITENESS_DELAY = 5  # seconds between paginated requests

_HEADERS = {
    "User-Agent": "arxivscraper/1.0 (mailto:abakakayan@gmail.com; math.AP newsletter bot)"
}

_OAI_NS = "http://www.openarchives.org/OAI/2.0/"
_ARXIV_NS = "http://arxiv.org/OAI/arXiv/"


def _get_with_retry(params: dict) -> requests.Response:
    """GET the OAI-PMH endpoint with basic retry on transient errors."""
    for attempt in range(1, 4):
        try:
            resp = requests.get(OAI_ENDPOINT, params=params, headers=_HEADERS, timeout=60)
            resp.raise_for_status()
            return resp
        except (requests.Timeout, requests.ConnectionError) as exc:
            if attempt == 3:
                raise
            wait = attempt * 30
            print(f"OAI request failed (attempt {attempt}/3): {exc} — retrying in {wait}s")
            time.sleep(wait)
        except requests.HTTPError as exc:
            if resp.status_code >= 500 and attempt < 3:
                wait = attempt * 30
                print(f"OAI HTTP {resp.status_code} (attempt {attempt}/3) — retrying in {wait}s")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("unreachable")


def fetch_new_papers(seen_ids: set, lookback_days: int = 3) -> list[dict]:
    """Return math.AP papers from the last `lookback_days` days not in `seen_ids`."""
    from_date = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    papers = []
    params = {
        "verb": "ListRecords",
        "set": "math.AP",
        "metadataPrefix": "arXiv",
        "from": from_date,
    }

    while True:
        resp = _get_with_retry(params)
        root = ET.fromstring(resp.text)

        for record in root.findall(f".//{{{_OAI_NS}}}record"):
            # Skip deleted records
            header = record.find(f"{{{_OAI_NS}}}header")
            if header is not None and header.get("status") == "deleted":
                continue

            paper = _parse_record(record)
            if paper and paper["id"] not in seen_ids:
                papers.append(paper)

        # Follow resumptionToken for pagination
        token_el = root.find(f".//{{{_OAI_NS}}}resumptionToken")
        if token_el is not None and token_el.text and token_el.text.strip():
            params = {"verb": "ListRecords", "resumptionToken": token_el.text.strip()}
            time.sleep(POLITENESS_DELAY)
        else:
            break

    return papers


def _parse_record(record) -> dict | None:
    meta = record.find(f".//{{{_ARXIV_NS}}}arXiv")
    if meta is None:
        return None

    arxiv_id = _text(meta, "id")
    if not arxiv_id:
        return None

    title = " ".join((_text(meta, "title") or "").split())
    abstract = " ".join((_text(meta, "abstract") or "").split())

    authors = []
    for author in meta.findall(f"{{{_ARXIV_NS}}}authors/{{{_ARXIV_NS}}}author"):
        keyname = _text(author, "keyname") or ""
        forenames = _text(author, "forenames") or ""
        name = f"{forenames} {keyname}".strip()
        if name:
            authors.append(name)

    submitted_str = _text(meta, "created") or ""
    try:
        submitted_dt = datetime.strptime(submitted_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None

    categories_str = _text(meta, "categories") or ""
    categories = categories_str.split()

    return {
        "id": arxiv_id,
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "submitted": submitted_str,
        "categories": categories,
        "link": f"https://arxiv.org/abs/{arxiv_id}",
    }


def _text(el, tag: str) -> str | None:
    child = el.find(f"{{{_ARXIV_NS}}}{tag}")
    return child.text.strip() if child is not None and child.text else None
