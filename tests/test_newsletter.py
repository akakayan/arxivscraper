from newsletter import _bucket, render_html


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
        title="Ordinary mathematical GR paper",
        authors=["A. Researcher"],
        categories=["gr-qc", "math.dg"],
        filter_reason="mathematical cross-listing + keyword match",
        relevance_score=2,
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

    assert html.index("High-priority overlap paper") < html.index(
        "Ordinary mathematical GR paper"
    )


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


def test_nonmathematical_gr_qc_papers_are_in_the_final_physics_section():
    """Treating every gr-qc tag as mathematical must fail this taxonomy test."""
    physics = _paper(
        id="physics",
        title="A numerical relativity simulation",
        authors=["A. Physicist"],
        categories=["gr-qc", "astro-ph.he"],
        filter_reason="keyword match",
        matched_author=None,
        relevance_score=1,
    )
    pde = _paper(
        id="pde",
        title="A nonlinear wave estimate",
        categories=["math.ap"],
        filter_reason="keyword match",
        matched_author=None,
        relevance_score=1,
    )
    mathematical_gr = _paper(
        id="mathematical-gr",
        title="Lorentzian geometry for Einstein equations",
        categories=["gr-qc", "math.dg"],
        filter_reason="mathematical cross-listing + keyword match",
        matched_author=None,
        relevance_score=2,
    )

    buckets = _bucket([physics, pde, mathematical_gr])

    assert [title for title, _papers in buckets] == [
        "Mathematical General Relativity",
        "Nonlinear Waves & Dispersive PDEs",
        "General Relativity & Physics",
    ]
    assert [[paper["id"] for paper in papers] for _title, papers in buckets] == [
        ["mathematical-gr"],
        ["pde"],
        ["physics"],
    ]
