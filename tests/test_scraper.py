from datetime import datetime, timezone

import scraper as scraper_module


def _record(arxiv_id: str, categories: str) -> dict:
    return {
        "id": arxiv_id,
        "title": f"Paper {arxiv_id}",
        "authors": ["A. Researcher"],
        "abstract": "Abstract",
        "created": str(datetime.now(timezone.utc).date()),
        "categories": categories,
        "url": f"https://arxiv.org/abs/{arxiv_id}",
    }


def test_fetch_includes_papers_found_only_in_gr_qc(monkeypatch):
    """Removing the gr-qc source must make this test fail."""
    records_by_category = {
        "math.AP": [_record("2609.00001", "math.AP")],
        "gr-qc": [_record("2609.00002", "gr-qc")],
    }

    class FakeScraper:
        def __init__(self, category, **_kwargs):
            self.category = category

        def scrape(self):
            return records_by_category[self.category]

    monkeypatch.setattr(scraper_module.arxivscraper, "Scraper", FakeScraper)

    papers = scraper_module.fetch_new_papers(set())

    assert {paper["id"] for paper in papers} == {"2609.00001", "2609.00002"}


def test_fetch_deduplicates_cross_listed_papers(monkeypatch):
    """Feed duplicates must merge category metadata into one paper."""
    records_by_category = {
        "math.AP": [_record("2609.00003", "math.AP")],
        "gr-qc": [_record("2609.00003", "gr-qc")],
    }

    class FakeScraper:
        def __init__(self, category, **_kwargs):
            self.category = category

        def scrape(self):
            return records_by_category[self.category]

    monkeypatch.setattr(scraper_module.arxivscraper, "Scraper", FakeScraper)

    papers = scraper_module.fetch_new_papers(set())

    assert [paper["id"] for paper in papers] == ["2609.00003"]
    assert set(papers[0]["categories"]) == {"math.AP", "gr-qc"}
