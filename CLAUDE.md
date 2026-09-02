# Arxiv Newsletter Scraper

## Project Goal
Build an automated arxiv paper scraper that:
- Runs daily via GitHub Actions to fetch new relevant papers
- Sends an HTML email newsletter twice a week (Monday and Thursday) if new papers exist
- Sends to: abakakayan@gmail.com

## Arxiv Fetch Strategy

**Source categories:** `math.AP` (Analysis of PDEs) and `gr-qc` (General Relativity and Quantum Cosmology). Fetch both feeds and deduplicate by arxiv ID.

**Relevance filtering logic:**
1. Papers carrying both `math.AP` and `gr-qc` are auto-included with relevance score 3.
2. Every other paper must match an approved topic pattern.
3. A topical `gr-qc` paper also carrying any `math.*` tag or `math-ph` receives relevance score 2.
4. Other topical papers receive relevance score 1.
5. Quantum-only papers are skipped when their only positive signal is a broad black-hole or relativity term. A strong approved PDE, field-equation, Einstein-equation, or numerical-black-hole signal can still include them.
6. For selected non-`gr-qc` papers, known authors change newsletter placement; author identity alone never includes a paper. Selected `gr-qc` papers remain in the appropriate GR section and display any known-author match there.

**Keyword matching strategy:**
- Use case-insensitive word-boundary regex patterns.
- Group synonyms into single patterns (e.g. `blow.?up|blowup`)
- Match against title + abstract, case-insensitive

**Keyword list:**
- `nonlinear wave|semilinear wave|quasilinear wave|wave equation`
- `hyperbolic (equation|PDE|system|conservation|problem|flow)`
- `shock wave`
- `dispersive (equation|PDE|estimate|decay|wave)`
- `Klein.?Gordon`
- `Maxwell`
- `Yang.?Mills`
- `Schrödinger|Schrodinger`
- `null condition`
- `blow.?up|blowup`
- `black hole|black-hole|Schwarzschild|Kerr`
- `general relativity|Einstein equation|Einstein equations`
- `spacetime|Minkowski|Lorentzian`
- `gravitational wave`

**Author matching strategy:**
- Maintained in `authors.json` — a curated list of key researchers in the field
- Seeded via a one-time Math Genealogy crawl (`genealogy_seed.py`) starting from key figures
- Genealogy candidates are filtered: only kept if they have at least one `math.AP` or `gr-qc` paper on arxiv within the last 3 years
- Name normalization: compare complete names after case, spacing, punctuation, and accent normalization. Initial-only forms match only when explicitly listed in `authors.json`.
- Store the matched curated name on the paper and show it in the newsletter reason.
- Authors can also be added manually at any time
- If `authors.json` is missing or empty, the filter degrades gracefully (author tier is skipped, other tiers still apply)

**Arxiv API pagination:**
- The `arxivscraper` OAI-PMH client follows each feed's resumption tokens until complete.

## Scheduling
- **Daily (8am UTC):** fetch new `math.AP` and `gr-qc` papers, filter, store in `pending.json`
- **Mon & Thu (9am UTC):** if `pending.json` is non-empty, send newsletter email, then clear it

Both workflows must use a shared `concurrency` group (e.g. `group: state-files`) to prevent simultaneous runs from conflicting on the committed JSON state files.

## State Persistence
GitHub Actions has no persistent disk. State is persisted by committing JSON files back to the repo after each run:
- `seen_ids.json` — list of arxiv IDs already processed (prevents duplicates); trim to last 90 days to prevent unbounded growth
- `pending.json` — papers accumulated since the last newsletter send
- `authors.json` — curated author allowlist (seeded from Math Genealogy + manual additions)

Both workflows require `permissions: contents: write` so `GITHUB_TOKEN` can push the state commits back.

## Repository Structure
```
arxivscraper/
├── .github/workflows/
│   ├── daily_fetch.yml       # cron: 0 8 * * *
│   └── send_newsletter.yml   # cron: 0 9 * * 1,4
├── scraper.py                # queries and deduplicates math.AP and gr-qc papers
├── filter.py                 # cross-listing, keyword, quantum-focus, and author filter
├── newsletter.py             # formats papers into HTML email
├── emailer.py                # sends via Gmail SMTP
├── main_fetch.py             # entry point for daily job
├── main_send.py              # entry point for send job
├── genealogy_seed.py         # one-time script: crawls Math Genealogy Project to seed authors.json
├── seen_ids.json             # persisted state (committed to repo)
├── pending.json              # persisted state (committed to repo)
├── authors.json              # curated author allowlist (committed to repo)
└── requirements.txt          # Python runtime dependencies
```

Install `requirements-dev.txt` to run the pytest regression suite locally.

## GitHub Secrets Required
| Secret | Description |
|---|---|
| `GMAIL_APP_PASSWORD` | 16-char Google App Password (not Gmail login password) |

`GITHUB_TOKEN` is auto-provided by GitHub Actions and is used to commit state files back to the repo.

## Error Alerting
GitHub Actions will send an email to the repo owner on workflow failure — this is the only alerting mechanism. No additional alerting is needed for an MVP. Monitor the Actions tab if emails stop arriving.

## Email Details
- **From/To:** abakakayan@gmail.com
- **Format:** HTML email, one section per paper: title, authors, date, abstract, arxiv link
- **Section order:**
  1. Mathematical General Relativity: selected `gr-qc` papers with any `math.*` or `math-ph` tag
  2. Known Authors: selected non-`gr-qc` papers with an exact curated-author match
  3. Nonlinear Waves & Dispersive PDEs: other selected non-`gr-qc` papers
  4. General Relativity & Physics: selected `gr-qc` papers without a mathematical tag
- **Subject:** `Arxiv Newsletter — N new papers — <date>`
- **Only sent** if there is at least one pending paper

## Gmail App Password Setup (one-time)
1. Enable 2FA on Google account
2. Go to myaccount.google.com/apppasswords
3. Generate an app password for "Mail"
4. Add it as `GMAIL_APP_PASSWORD` in the GitHub repo secrets

## Implementation Status
- [ ] scraper.py
- [ ] filter.py
- [ ] newsletter.py
- [ ] emailer.py
- [ ] main_fetch.py
- [ ] main_send.py
- [ ] genealogy_seed.py (one-time utility)
- [ ] .github/workflows/daily_fetch.yml
- [ ] .github/workflows/send_newsletter.yml
- [ ] requirements.txt
- [ ] seen_ids.json (initial empty state)
- [ ] pending.json (initial empty state)
- [ ] authors.json (seeded via genealogy_seed.py, then manually curated)
- [ ] GitHub repo created and pushed
