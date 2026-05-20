"""
Thin wrapper around the arxivscraper package (github.com/mahdisadjadi/arxivscraper).
Handles date range, seen-ID deduplication, and normalises the output dict format.
"""
from datetime import datetime, timedelta, timezone

import arxivscraper


def fetch_new_papers(seen_ids: set, lookback_days: int = 3) -> list[dict]:
    """Return math.AP papers from the last `lookback_days` days not in `seen_ids`."""
    today = datetime.now(timezone.utc).date()
    date_from = str(today - timedelta(days=lookback_days))
    date_until = str(today)

    print(f"Fetching math.AP papers from {date_from} to {date_until}")
    scraper = arxivscraper.Scraper(
        category="math.AP",
        date_from=date_from,
        date_until=date_until,
        t=30,
        timeout=600,
    )
    records = scraper.scrape()

    papers = []
    for r in records:
        arxiv_id = r["id"]
        if arxiv_id in seen_ids:
            continue
        if r["created"] < date_from:
            continue
        papers.append({
            "id": arxiv_id,
            "title": r["title"],
            "authors": r["authors"],
            "abstract": r["abstract"],
            "submitted": r["created"],
            "categories": r["categories"].split(),
            "link": r["url"],
        })

    return papers
