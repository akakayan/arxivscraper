"""Deterministic relevance filter for papers from math.AP and gr-qc."""
import json
import re
import unicodedata
from pathlib import Path

KEYWORDS = [
    r"nonlinear wave|semilinear wave|quasilinear wave|wave equation",
    r"hyperbolic (equation|PDE|system|conservation|problem|flow)",
    r"shock wave",
    r"dispersive (equation|PDE|estimate|decay|wave)",
    r"Klein.?Gordon",
    r"Maxwell",
    r"Yang.?Mills",
    r"Schr(?:o|ö)dinger",
    r"null condition",
    r"blow.?up|blowup",
    r"black.?hole|Schwarzschild|Kerr",
    r"general relativity|Einstein equations?",
    r"spacetime|Minkowski|Lorentzian",
    r"gravitational wave",
]

_PATTERNS = [re.compile(r"\b(?:" + kw + r")\b", re.IGNORECASE) for kw in KEYWORDS]

_QUANTUM_ONLY_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bquantum\b",
        r"\bquanti[sz]",
        r"\bquantum gravity\b",
        r"\bquantum cosmolog",
        r"\bholograph",
        r"\bAdS/CFT\b",
        r"\bstring theory\b",
        r"\bloop quantum",
        r"\bHawking radiation\b",
        r"\bblack hole information\b",
        r"\bentanglement entropy\b",
    ]
]

_STRONG_NONQUANTUM_PATTERNS = [
    re.compile(r"\b(?:" + pattern + r")\b", re.IGNORECASE)
    for pattern in [
        r"nonlinear wave|semilinear wave|quasilinear wave|wave equation",
        r"hyperbolic (equation|PDE|system|conservation|problem|flow)",
        r"shock wave",
        r"dispersive (equation|PDE|estimate|decay|wave)",
        r"Klein.?Gordon",
        r"Maxwell",
        r"Yang.?Mills",
        r"Schr(?:o|ö)dinger",
        r"null condition",
        r"blow.?up|blowup",
        r"Einstein equations?",
        r"numerical.{0,40}(black.?hole|Schwarzschild|Kerr)",
        r"(black.?hole|Schwarzschild|Kerr).{0,40}numerical",
    ]
]

def normalize_author(name: str) -> str:
    """Normalize a full name while preserving every name component."""
    decomposed = unicodedata.normalize("NFKD", name.casefold())
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    words = re.sub(r"[^\w]+", " ", without_marks, flags=re.UNICODE)
    return " ".join(words.split())


def normalize_categories(categories: list[str]) -> set[str]:
    """Return arXiv category tags in a consistent comparison form."""
    return {str(category).strip().casefold() for category in categories}


def has_mathematical_tag(categories: list[str] | set[str]) -> bool:
    """Return whether categories contain any math subject or math-ph."""
    normalized = normalize_categories(list(categories))
    return any(
        category.startswith("math.") or category == "math-ph"
        for category in normalized
    )


def load_authors(path: str = "authors.json") -> dict[str, str]:
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return {}
    data = json.loads(p.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list):
        return {}
    return {normalize_author(author): author for author in data if author}


def _matches_keyword(title: str, abstract: str) -> bool:
    text = f"{title} {abstract}"
    return any(pat.search(text) for pat in _PATTERNS)


def _is_quantum_only(title: str, abstract: str) -> bool:
    text = f"{title} {abstract}"
    has_quantum_focus = any(pattern.search(text) for pattern in _QUANTUM_ONLY_PATTERNS)
    has_strong_nonquantum_topic = any(
        pattern.search(text) for pattern in _STRONG_NONQUANTUM_PATTERNS
    )
    return has_quantum_focus and not has_strong_nonquantum_topic


def _match_known_author(
    paper_authors: list[str], authors_lookup: dict[str, str]
) -> str | None:
    for author in paper_authors:
        matched_author = authors_lookup.get(normalize_author(author))
        if matched_author:
            return matched_author
    return None


def filter_papers(papers: list[dict], authors_lookup: dict[str, str]) -> list[dict]:
    """Return relevant papers, highest score first, with auditable reasons."""
    relevant = []

    for paper in papers:
        categories = normalize_categories(paper.get("categories", []))
        matched_author = _match_known_author(
            paper.get("authors", []), authors_lookup
        )

        if {"math.ap", "gr-qc"} <= categories:
            paper["filter_reason"] = "math.AP + gr-qc cross-listing"
            paper["relevance_score"] = 3
            if matched_author:
                paper["matched_author"] = matched_author
            relevant.append(paper)
            continue

        if not _matches_keyword(paper["title"], paper["abstract"]):
            continue
        if _is_quantum_only(paper["title"], paper["abstract"]):
            continue

        has_mathematical_crosslist = (
            "gr-qc" in categories and has_mathematical_tag(categories)
        )
        paper["relevance_score"] = 2 if has_mathematical_crosslist else 1

        # Author identity is independent from the evidence that selected the paper.
        if matched_author:
            paper["matched_author"] = matched_author

        paper["filter_reason"] = (
            "mathematical cross-listing + keyword match"
            if has_mathematical_crosslist
            else "keyword match"
        )
        relevant.append(paper)

    return sorted(relevant, key=lambda paper: paper["relevance_score"], reverse=True)
