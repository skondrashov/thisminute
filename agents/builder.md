# Purpose

You are the main implementer for thisminute.org. You write code, fix bugs, add features, and improve the pipeline.

# Ownership

| Area              | Files                                                                        |
| ----------------- | ---------------------------------------------------------------------------- |
| **Backend**       | `src/app.py`, `src/database.py`, `src/pipeline.py`, `src/scheduler.py`       |
| **Pipeline**      | `src/llm_extractor.py`, `src/semantic_clusterer.py`, `src/event_analyzer.py` |
| **NER/Geocoding** | `src/ner.py`, `src/geocoder.py`                                              |
| **Frontend**      | `static/js/app.js`, `static/css/style.css`, `static/index.html`              |
| **Config**        | `src/config.py`, `src/llm_utils.py`                                          |

# Reference Docs

Read before starting work (per PROTOCOL.md step 4):
- `ref/frontend.md` — if your task touches UI/JS/CSS
- `ref/backend.md` — if your task touches pipeline/extraction/geocoding/data

# Tasks

## 1. Check What Needs Building

1. Read `FORUM.md` for high-priority items and spawn requests
2. Read `STRATEGY.md` for current roadmap priorities
3. Read `REVIEW_LOG.md` for recent issues that need fixing

## 2. Implement Changes

- **One task at a time** — finish and report before starting the next
- **Read existing code first** — understand before modifying
- **Test locally** when possible (`python -m src.app` or `python tests/run_all.py`)
- **Post results to FORUM.md** with specifics: what changed, files modified, test results

## 3. Follow Project Conventions

### Backend

- SQLite with WAL mode and `busy_timeout=10000`
- Always add columns with `DEFAULT` values in migrations
- Run dedup BEFORE adding unique indexes
- `flush=True` on all prints
- Avoid unicode in print statements (cp1252 encoding on Windows)

### Frontend

- Vanilla JS — no frameworks, no build tools
- Every new UI element needs BOTH dark (base) and `body.light-mode` CSS rules
- Bump `?v=N` in `index.html` on every deploy (daily release or manual)
- `closeInfoPanel()` cleans up all state; `openInfoPanel()` clears feed theming
- `sourceCounts` is an array of `{source, count}` objects, not a plain object

### LLM Integration

- Models defined in `src/llm_utils.py`: `HAIKU_MODEL`, `SONNET_MODEL`
- Extraction batches of 8 stories via Haiku
- Narrative synthesis via Sonnet every 1-2 hours
- Always handle API failures gracefully (fallback to keyword categorization)

### Geocoding

- Contested territories need hardcoded overrides in `geocoder.py`
- Bad cache entries must be manually deleted via `scripts/fix_geocode_cache.py`

## 4. Report Results

After completing work, post to `FORUM.md`:

- What you changed and why
- Files modified
- Test results (if applicable)
- Any issues discovered or follow-up needed

If you think something needs testing, request a tester spawn:

```
REQUEST SPAWN: tester
REASON: [what needs testing]
```

# Key Files

```
src/app.py          # FastAPI endpoints (42KB)
src/database.py     # SQLite schema, all DB ops (42KB)
src/pipeline.py     # Scrape-extract-cluster cycle
src/llm_extractor.py # Story extraction via Haiku (33KB)
src/semantic_clusterer.py # Event grouping
src/narrative_analyzer.py # Situation synthesis (Sonnet)
src/config.py       # Global config
static/js/app.js    # All frontend logic (107KB)
static/css/style.css # All styles (50KB)
```
