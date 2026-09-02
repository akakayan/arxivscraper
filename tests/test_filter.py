from pathlib import Path

import pytest

from filter import filter_papers, load_authors, normalize_author


def test_author_normalization_preserves_full_given_name():
    """Changing the given name must not produce the same author identity."""
    assert normalize_author("Qian Wang") != normalize_author("Qiang Wang")


def test_author_normalization_tolerates_hyphen_and_spacing_variants():
    """Punctuation differences must not hide the same full author name."""
    assert normalize_author("Sung-Jin Oh") == normalize_author("  SUNG JIN OH ")


def test_loaded_authors_retain_canonical_display_names():
    """A successful match must be able to report the curated author name."""
    path = Path(__file__).with_name("fixtures") / "authors.json"

    assert load_authors(path) == {"daniel tataru": "Daniel Tataru"}


def test_filter_reports_the_exact_curated_author_that_matched():
    """Known-author placement must identify the matched allowlist entry."""
    paper = {
        "title": "Global dynamics for a nonlinear wave equation",
        "abstract": "We prove scattering for the equation.",
        "authors": ["Daniel Tataru"],
        "categories": ["math.AP"],
    }

    result = filter_papers([paper], {"daniel tataru": "Daniel Tataru"})

    assert result[0]["matched_author"] == "Daniel Tataru"
    assert result[0]["filter_reason"] == "keyword match"


def test_gr_qc_membership_alone_does_not_make_a_paper_relevant():
    """A gr-qc-only quantum paper without an approved topic must be skipped."""
    paper = {
        "title": "Quantum entanglement entropy in holographic duality",
        "abstract": "We study a quantum information model using holography.",
        "authors": ["A. Researcher"],
        "categories": ["gr-qc"],
    }

    assert filter_papers([paper], {}) == []


def test_math_ap_gr_qc_overlap_is_automatically_relevant():
    """Removing overlap auto-inclusion must make this test fail."""
    paper = {
        "title": "A specialized geometric construction",
        "abstract": "This abstract deliberately has no topical keyword.",
        "authors": ["A. Researcher"],
        "categories": ["math.ap", "gr-qc"],
    }

    result = filter_papers([paper], {})

    assert result[0]["filter_reason"] == "math.AP + gr-qc cross-listing"
    assert result[0]["relevance_score"] == 3


def test_overlap_paper_retains_its_exact_known_author_match():
    """The overlap fast path must not skip author auditing."""
    paper = {
        "title": "A specialized geometric construction",
        "abstract": "This abstract deliberately has no topical keyword.",
        "authors": ["Daniel Tataru"],
        "categories": ["math.AP", "gr-qc"],
    }

    result = filter_papers([paper], {"daniel tataru": "Daniel Tataru"})[0]

    assert result["matched_author"] == "Daniel Tataru"


def test_known_author_does_not_bypass_topical_relevance():
    """An allowlisted author alone must not admit unrelated work."""
    paper = {
        "title": "An unrelated elliptic optimization problem",
        "abstract": "We optimize a static functional on a bounded domain.",
        "authors": ["Daniel Tataru"],
        "categories": ["math.AP"],
    }

    assert filter_papers([paper], {"daniel tataru": "Daniel Tataru"}) == []


@pytest.mark.parametrize(
    "topic",
    [
        "Maxwell fields on curved backgrounds",
        "Global dynamics for the Yang-Mills system",
        "A nonlinear Schrödinger equation",
        "Solutions of the Einstein equations",
    ],
)
def test_user_approved_topics_are_relevant(topic):
    """Dropping any approved topic must exclude its representative paper."""
    paper = {
        "title": topic,
        "abstract": "We establish a new global estimate.",
        "authors": ["A. Researcher"],
        "categories": ["math.AP"],
    }

    result = filter_papers([paper], {})[0]

    assert result["filter_reason"] == "keyword match"
    assert result["relevance_score"] == 1


def test_quantum_only_black_hole_paper_is_excluded():
    """A broad black-hole term must not admit an otherwise quantum-only paper."""
    paper = {
        "title": "Quantum entropy of Kerr black holes",
        "abstract": (
            "We study holographic entanglement entropy, Hawking radiation, "
            "and the black hole information problem."
        ),
        "authors": ["A. Researcher"],
        "categories": ["gr-qc"],
    }

    assert filter_papers([paper], {}) == []


def test_generic_quantum_black_hole_paper_is_excluded():
    """Generic quantum wording must trigger the quantum-only guard."""
    paper = {
        "title": "Quantum corrections to Kerr black holes",
        "abstract": "We quantize horizon degrees of freedom and compute entropy.",
        "authors": ["A. Researcher"],
        "categories": ["gr-qc"],
    }

    assert filter_papers([paper], {}) == []


def test_numerical_black_hole_paper_is_included():
    """Hyphenation must not hide numerical black-hole work."""
    paper = {
        "title": "High-resolution numerical black-hole evolutions",
        "abstract": "We simulate binary horizons with a convergent evolution scheme.",
        "authors": ["A. Researcher"],
        "categories": ["gr-qc"],
    }

    assert filter_papers([paper], {})[0]["filter_reason"] == "keyword match"


def test_mathematical_cross_listing_receives_a_relevance_boost():
    """Dropping the math.DG/math-ph boost must lower this paper's score."""
    paper = {
        "title": "Lorentzian geometry for the Einstein equations",
        "abstract": "We study a geometric formulation on spacetime.",
        "authors": ["A. Researcher"],
        "categories": ["gr-qc", "math.DG"],
    }

    result = filter_papers([paper], {})[0]

    assert result["relevance_score"] == 2
    assert result["filter_reason"] == "mathematical cross-listing + keyword match"


def test_any_math_subject_cross_listing_receives_a_relevance_boost():
    """Restricting the boost to a hard-coded math shortlist must fail this test."""
    paper = {
        "title": "Einstein equations and geometric topology",
        "abstract": "We study Lorentzian spacetime geometry.",
        "authors": ["A. Researcher"],
        "categories": ["gr-qc", "math.gt"],
    }

    assert filter_papers([paper], {})[0]["relevance_score"] == 2


def test_higher_relevance_scores_are_returned_first():
    """Removing score ordering must put the lower-priority input first."""
    ordinary = {
        "id": "ordinary",
        "title": "Maxwell fields",
        "abstract": "A global estimate.",
        "authors": ["A. Researcher"],
        "categories": ["math.AP"],
    }
    cross_listed = {
        "id": "cross-listed",
        "title": "Einstein equations on a Lorentzian manifold",
        "abstract": "A geometric analysis.",
        "authors": ["B. Researcher"],
        "categories": ["gr-qc", "math.DG"],
    }

    result = filter_papers([ordinary, cross_listed], {})

    assert [paper["id"] for paper in result] == ["cross-listed", "ordinary"]
