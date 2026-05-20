# Arxiv Newsletter Scraper

## Project Goal
Build an automated arxiv paper scraper that:
- Runs daily via GitHub Actions to fetch new relevant papers
- Sends an HTML email newsletter twice a week (Monday and Thursday) if new papers exist
- Sends to: abakakayan@gmail.com

## Arxiv Fetch Strategy

**Source category:** `math.AP` (Analysis of PDEs) — this is the only source, always fetched.

**Relevance filtering logic (applied to math.AP papers) — in priority order:**
1. If the paper is cross-listed in `gr-qc` (General Relativity & Quantum Cosmology) → **auto-include**
2. If the paper matches any keyword pattern (stemmed, word-boundary regex) → **include**
3. If semantic similarity score vs. topic description exceeds threshold → **include**
   - Default threshold: **0.35**
   - If any author is in `authors.json`: lower threshold **0.20** (extra attention, but still needs relevance signal — prevents including papers from authors who have moved to unrelated subfields)
4. Otherwise → **skip**

**Do NOT include** pure `gr-qc` papers that are not in `math.AP`.

**Keyword matching strategy:**
- Use stemmed word-boundary regex (`\b`) so root forms match inflections (e.g. `scatter` catches "scattering", "scattered")
- Group synonyms into single patterns (e.g. `blow.?up|blowup`)
- Match against title + abstract, case-insensitive

**Keyword list:**
- `nonlinear wave|semilinear wave|quasilinear wave|wave equation`
- `hyperbolic`
- `shock wave`
- `dispersive`
- `Klein.?Gordon`
- `Maxwell equation`
- `Dirac equation`
- `Cauchy problem`
- `null condition`
- `blow.?up|blowup`
- `global existence`
- `scatter`
- `energy estimate`
- `black hole|Schwarzschild|Kerr`
- `general relativity|Einstein equation`
- `spacetime|Minkowski|Lorentzian`
- `gravitational wave`

**Semantic scoring:**
- Model: `sentence-transformers` with `all-MiniLM-L6-v2` (local, offline, no API cost)
- Topic description: `"nonlinear wave equations, hyperbolic PDEs, mathematical general relativity, dispersive equations"`
- Threshold: 0.35 cosine similarity — papers above this are included even without a keyword hit
- The model (~90MB) must be cached in GitHub Actions using `actions/cache` keyed on the model name, otherwise every daily run re-downloads it

**Author matching strategy:**
- Maintained in `authors.json` — a curated list of key researchers in the field
- Seeded via a one-time Math Genealogy crawl (`genealogy_seed.py`) starting from key figures
- Genealogy candidates are filtered: only kept if they have at least one `math.AP` or `gr-qc` paper on arxiv within the last 3 years
- Name normalization: compare last name + first initial to handle "D. Tataru" vs "Daniel Tataru"
- Authors can also be added manually at any time
- If `authors.json` is missing or empty, the filter degrades gracefully (author tier is skipped, other tiers still apply)

**Arxiv API pagination:**
- Fetch in pages of 100 results using the `start` offset parameter; keep fetching until a page returns fewer than 100 results
- This handles busy days where `math.AP` has more than 100 new submissions

## Scheduling
- **Daily (8am UTC):** fetch new `math.AP` papers, filter, store in `pending.json`
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
├── scraper.py                # queries arxiv API for math.AP papers
├── filter.py                 # four-tier relevance filter (gr-qc, authors, keywords, semantic)
├── newsletter.py             # formats papers into HTML email
├── emailer.py                # sends via Gmail SMTP
├── main_fetch.py             # entry point for daily job
├── main_send.py              # entry point for send job
├── genealogy_seed.py         # one-time script: crawls Math Genealogy Project to seed authors.json
├── seen_ids.json             # persisted state (committed to repo)
├── pending.json              # persisted state (committed to repo)
├── authors.json              # curated author allowlist (committed to repo)
└── requirements.txt          # sentence-transformers, requests, torch (cpu)
```

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
