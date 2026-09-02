"""
Thin wrapper around the arxivscraper package (github.com/mahdisadjadi/arxivscraper).
Handles date range, seen-ID deduplication, and normalises the output dict format.
"""
from datetime import datetime, timedelta, timezone

import arxivscraper

SOURCE_CATEGORIES = ("math.AP", "gr-qc")


def fetch_new_papers(seen_ids: set, lookback_days: int = 3) -> list[dict]:
    """Return math.AP and gr-qc papers not seen within the lookback window."""
    today = datetime.now(timezone.utc).date()
    date_from = str(today - timedelta(days=lookback_days))
    date_until = str(today)

    records = []
    for category in SOURCE_CATEGORIES:
        print(f"Fetching {category} papers from {date_from} to {date_until}")
        category_scraper = arxivscraper.Scraper(
            category=category,
            date_from=date_from,
            date_until=date_until,
            t=30,
            timeout=600,
        )
        records.extend(category_scraper.scrape())

    papers = []
    papers_by_id = {}
    for r in records:
        arxiv_id = r["id"]
        if arxiv_id in seen_ids:
            continue
        if r["created"] < date_from:
            continue
        categories = r["categories"].split()
        if arxiv_id in papers_by_id:
            existing_categories = papers_by_id[arxiv_id]["categories"]
            existing_categories.extend(
                category for category in categories if category not in existing_categories
            )
            continue

        paper = {
            "id": arxiv_id,
            "title": r["title"],
            "authors": r["authors"],
            "abstract": r["abstract"],
            "submitted": r["created"],
            "categories": categories,
            "link": r["url"],
        }
        papers.append(paper)
        papers_by_id[arxiv_id] = paper

    return papers
