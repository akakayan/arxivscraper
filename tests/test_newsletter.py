from newsletter import render_html


def _paper(**overrides) -> dict:
    paper = {
        "id": "2609.00001",
        "title": "A nonlinear wave equation",
        "abstract": "Abstract",
        "authors": ["Daniel Tataru"],
        "submitted": "2026-09-01",
        "categories": ["math.AP"],
        "link": "https://arxiv.org/abs/2609.00001",
        "filter_reason": "keyword match",
        "matched_author": "Daniel Tataru",
        "relevance_score": 1,
    }
    paper.update(overrides)
    return paper


def test_newsletter_renders_canonical_known_author_match():
    """Changing the reason prefix must not make a known-author paper disappear."""
    html = render_html([_paper()])

    assert "Known Authors (1)" in html
    assert "known author: Daniel Tataru" in html


def test_newsletter_links_both_source_feeds():
    """Removing either configured source link must make the footer test fail."""
    html = render_html([_paper()])

    assert "https://arxiv.org/list/math.AP/recent" in html
    assert "https://arxiv.org/list/gr-qc/recent" in html


def test_newsletter_orders_each_section_by_relevance_score():
    """Accumulation order must not bury a stronger cross-listed paper."""
    ordinary = _paper(
        title="Ordinary black hole paper",
        authors=["A. Researcher"],
        categories=["gr-qc"],
        filter_reason="keyword match",
        relevance_score=1,
    )
    overlap = _paper(
        id="2609.00002",
        title="High-priority overlap paper",
        authors=["B. Researcher"],
        categories=["math.AP", "gr-qc"],
        filter_reason="math.AP + gr-qc cross-listing",
        relevance_score=3,
    )

    html = render_html([ordinary, overlap])

    assert html.index("High-priority overlap paper") < html.index("Ordinary black hole paper")


def test_newsletter_escapes_arxiv_metadata_before_rendering_html():
    """Raw metadata markup must never be emitted as newsletter HTML."""
    paper = _paper(
        title="Wave <script>alert(1)</script>",
        abstract="A & B < C",
        authors=["A & B"],
        categories=["math.AP", "x&y"],
        link='https://arxiv.org/abs/2609.00001?x="quoted"',
        filter_reason="keyword <match>",
        matched_author="A & B",
    )

    html = render_html([paper])

    assert "<script>" not in html
    assert "Wave &lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "A &amp; B &lt; C" in html
    assert 'x=&quot;quoted&quot;' in html
