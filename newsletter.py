"""Format a list of papers into a sectioned HTML email."""
from datetime import date
from html import escape

SECTIONS = [
    ("Mathematical General Relativity",   lambda p: "gr-qc" in p.get("categories", [])),
    ("Known Authors",                     lambda p: bool(p.get("matched_author"))),
    ("Nonlinear Waves & Dispersive PDEs", lambda p: p.get("filter_reason", "").startswith("keyword")),
]

SECTION_COLORS = {
    "Mathematical General Relativity":    "#1a56db",
    "Known Authors":                      "#6b21a8",
    "Nonlinear Waves & Dispersive PDEs":  "#1a7a3c",
}


def _bucket(papers: list[dict]) -> list[tuple[str, list[dict]]]:
    """Assign each paper to its highest-priority section."""
    buckets: dict[str, list[dict]] = {title: [] for title, _ in SECTIONS}
    for paper in papers:
        for title, predicate in SECTIONS:
            if predicate(paper):
                buckets[title].append(paper)
                break
    return [
        (
            title,
            sorted(
                buckets[title],
                key=lambda paper: paper.get("relevance_score", 0),
                reverse=True,
            ),
        )
        for title, _ in SECTIONS
        if buckets[title]
    ]


def render_html(papers: list[dict]) -> str:
    today = date.today().strftime("%B %d, %Y")
    n = len(papers)
    sections_html = "\n".join(_render_section(title, ps) for title, ps in _bucket(papers))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body style="font-family: Georgia, 'Times New Roman', serif; max-width: 740px; margin: 40px auto; padding: 0 24px; color: #1a1a1a; line-height: 1.7; background: #fff;">
  <h1 style="font-size: 1.45em; border-bottom: 2px solid #1a56db; padding-bottom: 0.4em; margin-bottom: 1.8em; color: #111;">
    Arxiv Newsletter &mdash; {n} new paper{'s' if n != 1 else ''} &mdash; {today}
  </h1>
  {sections_html}
  <p style="margin-top: 3em; color: #aaa; font-size: 0.8em; border-top: 1px solid #eee; padding-top: 1em;">
    Sources: <a href="https://arxiv.org/list/math.AP/recent" style="color: #aaa;">math.AP</a>
    and <a href="https://arxiv.org/list/gr-qc/recent" style="color: #aaa;">gr-qc</a> recent listings
  </p>
</body>
</html>"""


def _render_section(title: str, papers: list[dict]) -> str:
    color = SECTION_COLORS.get(title, "#333")
    papers_html = "\n".join(_paper_block(p) for p in papers)
    return f"""  <div style="margin-bottom: 2.5em;">
    <h2 style="font-size: 1.1em; color: {color}; border-left: 4px solid {color}; padding-left: 0.6em; margin: 0 0 1.2em;">{title} ({len(papers)})</h2>
    {papers_html}
  </div>"""


def _paper_block(p: dict) -> str:
    authors_str = ", ".join(escape(str(author)) for author in p["authors"])
    reason = p.get("filter_reason", "")
    if p.get("matched_author"):
        reason = f"{reason}; known author: {p['matched_author']}"
    reason = escape(str(reason))
    cats = " &middot; ".join(
        escape(str(category)) for category in p.get("categories", [])
    )
    link = escape(str(p["link"]), quote=True)
    title = escape(str(p["title"]))
    submitted = escape(str(p["submitted"]))
    abstract = escape(str(p["abstract"]))
    return f"""  <div style="margin-bottom: 2em; padding-bottom: 1.6em; border-bottom: 1px solid #e8e8e8;">
    <h3 style="margin: 0 0 0.3em; font-size: 1.0em; font-weight: bold;">
      <a href="{link}" style="color: #1a56db; text-decoration: none;">{title}</a>
    </h3>
    <p style="margin: 0.15em 0; color: #444; font-size: 0.9em;">{authors_str}</p>
    <p style="margin: 0.15em 0; color: #888; font-size: 0.82em;">{submitted} &middot; {cats} &middot; <em>{reason}</em></p>
    <p style="margin: 0.9em 0 0; font-size: 0.95em; line-height: 1.65;">{abstract}</p>
  </div>"""


def make_subject(papers: list[dict]) -> str:
    n = len(papers)
    today = date.today().strftime("%Y-%m-%d")
    return f"Arxiv Newsletter — {n} new paper{'s' if n != 1 else ''} — {today}"
