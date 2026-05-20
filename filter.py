"""
Relevance filter for math.AP papers.

Tiers in priority order:
  1. gr-qc cross-listing       → auto-include
  2. Keyword match              → include
  3. Semantic similarity        → include if score >= SEMANTIC_THRESHOLD
     Known authors get a lower bar: SEMANTIC_THRESHOLD_KNOWN_AUTHOR
"""
import json
import os
import re
from pathlib import Path

SEMANTIC_ENABLED = os.environ.get("SEMANTIC", "1") != "0"

if SEMANTIC_ENABLED:
    from sentence_transformers import SentenceTransformer, util

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

TOPIC = "nonlinear wave equations, hyperbolic PDEs, mathematical general relativity, dispersive equations"
SEMANTIC_THRESHOLD = 0.50             # default threshold for unknown authors
SEMANTIC_THRESHOLD_KNOWN_AUTHOR = 0.20  # lower bar for authors in authors.json
MODEL_NAME = "all-MiniLM-L6-v2"

_model = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


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
    """
    Returns relevant papers with a 'filter_reason' field added to each.

    Known authors are not auto-included — their papers still go through
    keyword and semantic checks, but with a lower semantic threshold (0.20
    vs 0.35) so borderline-relevant work from the field gets through.
    """
    relevant = []
    needs_semantic = []

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
            continue

        # Tier 3: semantic — tag whether a known author is involved
        paper_authors = {normalize_author(a) for a in paper.get("authors", [])}
        is_known = bool(authors_set and paper_authors & authors_set)
        needs_semantic.append((paper, is_known))

    # Semantic scoring — batch encode for efficiency
    if needs_semantic and SEMANTIC_ENABLED:
        model = _get_model()
        topic_emb = model.encode(TOPIC, convert_to_tensor=True)
        texts = [f"{p['title']}. {p['abstract']}" for p, _ in needs_semantic]
        paper_embs = model.encode(texts, convert_to_tensor=True, batch_size=32, show_progress_bar=False)
        scores = util.cos_sim(topic_emb, paper_embs)[0]

        for (paper, is_known), score in zip(needs_semantic, scores):
            score_val = float(score)
            threshold = SEMANTIC_THRESHOLD_KNOWN_AUTHOR if is_known else SEMANTIC_THRESHOLD
            if score_val >= threshold:
                tag = " (known author)" if is_known else ""
                paper["filter_reason"] = f"semantic {score_val:.2f}{tag}"
                relevant.append(paper)
    elif needs_semantic:
        print(f"Semantic scoring disabled — skipping {len(needs_semantic)} papers")

    return relevant
