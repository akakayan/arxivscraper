"""
Relevance filter for math.AP papers.

Tiers in priority order:
  1. gr-qc cross-listing  → auto-include
  2. Keyword match        → include
"""
import json
import re
from pathlib import Path

KEYWORDS = [
    r"nonlinear wave|semilinear wave|quasilinear wave|wave equation",
    r"hyperbolic (equation|PDE|system|conservation|problem|flow)",
    r"shock wave",
    r"dispersive (equation|PDE|estimate|decay|wave)",
    r"Klein.?Gordon",
    r"null condition",
    r"blow.?up|blowup",
    r"black hole|Schwarzschild|Kerr",
    r"general relativity|Einstein equation",
    r"spacetime|Minkowski|Lorentzian",
    r"gravitational wave",
]

_PATTERNS = [re.compile(r"\b(?:" + kw + r")\b", re.IGNORECASE) for kw in KEYWORDS]


def normalize_author(name: str) -> str:
    """'Daniel Tataru' or 'D. Tataru' → 'tataru d'."""
    parts = name.strip().split()
    if not parts:
        return ""
    last = parts[-1].lower()
    first_initial = parts[0][0].lower() if len(parts) > 1 else ""
    return f"{last} {first_initial}".strip()


def load_authors(path: str = "authors.json") -> set:
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return set()
    data = json.loads(p.read_text())
    if not isinstance(data, list):
        return set()
    return {normalize_author(a) for a in data if a}


def _matches_keyword(title: str, abstract: str) -> bool:
    text = f"{title} {abstract}"
    return any(pat.search(text) for pat in _PATTERNS)


def filter_papers(papers: list[dict], authors_set: set) -> list[dict]:
    """Returns relevant papers with a 'filter_reason' field added to each."""
    relevant = []

    for paper in papers:
        # Tier 1: gr-qc cross-listing — always relevant
        if "gr-qc" in paper.get("categories", []):
            paper["filter_reason"] = "gr-qc cross-listing"
            relevant.append(paper)
            continue

        # Tier 2: keyword match
        if _matches_keyword(paper["title"], paper["abstract"]):
            paper["filter_reason"] = "keyword match"
            relevant.append(paper)

    return relevant
