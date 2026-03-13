# Backend Reference

Read this if your task touches the pipeline, LLM extraction, clustering, geocoding, or data quality.

## Pipeline Flow

Every 15 minutes, `scheduler.py` runs `pipeline.py`:

1. **Scrape** — RSS feeds (`scraper.py`) + GDELT (`gdelt.py`, sampled via `GDELT_SAMPLE_RATE`)
2. **Process** — NER (`ner.py`) → geocode (`geocoder.py`) → categorize (`categorizer.py`)
3. **Store** — `database.py` inserts new stories
4. **Extract** — `llm_extractor.py` enriches batches of 8 via Haiku (topics, actors, severity, location_type, event_signature)
5. **Cluster** — `semantic_clusterer.py` groups stories into events via event_signature matching
6. **Analyze** — `event_analyzer.py` generates event titles/descriptions via Haiku
7. **Registry** — `registry_manager.py` maintains long-lived event registry (merge, retire, relabel)

Every 2 hours, `narrative_analyzer.py` synthesizes situations via Sonnet (one pass per domain: news, sports, entertainment, positive).

## Geocoding Pitfalls

- **Nominatim returns wrong results for contested territories.** "West Bank" → Minneapolis, "Gaza" → Mozambique. Always add contested places to `_HARDCODED` in `geocoder.py`.
- **The geocode cache caches bad results permanently.** If a location was geocoded wrong, delete the cache entry and re-run. Use `scripts/fix_geocode_cache.py`.
- **Event location recalculates** every 10 stories via median. Registry events recalculate every 5.

## Pipeline Pitfalls

- **`flush=True`** on ALL prints — Windows subprocess buffers stdout otherwise.
- **DB migrations**: always add columns with `DEFAULT`, run dedup BEFORE unique indexes.
- **SSH to VM**: `sudo -u thisminute` for DB write access.
- **CRLF**: Files created on Windows have CRLF. Always `sed -i 's/\r$//'` after deploy.
- **NEVER inline shell scripts in Python `-c` strings** — escaping Python+bash+SQL is impossible. Use base64 encoding or write a .py script.
- **gcloud path has spaces** (`Google Cloud SDK`). Must use Python `subprocess.run([GCLOUD, ...])`, not bash.

## Data Quality

- Event location accuracy depends on: NER extraction → geocoding → first-story assignment. Each step can fail independently.
- The LLM extracts `story_locations` with roles (`event_location`, `origin`, `mentioned`). The semantic clusterer uses `event_location` role for better accuracy.
- Narratives (situations) are Wikipedia-article-level groupings, not vague themes.
- `extraction.get("actors", [])` returns None when LLM sets `"actors": null`. Use `or []` pattern.

## Extraction Quality Signals

- **Topic diversity**: If >50% of stories get the same topic, the prompt is too coarse
- **Severity distribution**: Should be roughly normal (most = 2-3, few = 1 or 5). If everything is 3, the model is hedging
- **location_type accuracy**: Are space/internet/abstract stories correctly classified?
- **event_signature clustering**: Do similar stories get the same signature? Do unrelated stories get different ones?
- **Actor extraction**: Are actor roles correct? (victim vs perpetrator matters)

## Feedback Loop

When something looks wrong on the site:

1. **Identify the layer**: scraping (no stories), extraction (wrong categories), clustering (wrong groupings), analysis (bad descriptions), or frontend (display bug)?
2. **Check logs**: `sudo journalctl -u thisminute -n 100 --no-pager` on the VM
3. **Check DB**: Run the monitoring queries in `agents/tester.md`
4. **Fix at the right level**:
   - Bad categories → improve SYSTEM_PROMPT in `llm_extractor.py`
   - Bad clustering → adjust `FUZZY_MATCH_THRESHOLD` in `semantic_clusterer.py`
   - Bad event descriptions → improve prompt in `event_analyzer.py`
   - Bad narratives → improve prompt in `narrative_analyzer.py`
   - Display issues → fix in `app.js` / `style.css`
5. **Deploy and verify**: Bump version, deploy, wait 2 pipeline cycles (~30 min), check results

## Key Files

```
src/pipeline.py           # Orchestrates full scrape-extract-cluster-analyze cycle
src/llm_extractor.py      # Story extraction via Haiku (batches of 8)
src/semantic_clusterer.py # Event clustering via event_signatures
src/registry_manager.py   # Event registry: merge, retire, relabel
src/event_analyzer.py     # Event-level LLM analysis + world overview
src/narrative_analyzer.py # Situation synthesis (Sonnet, every 1-2h)
src/database.py           # SQLite schema, all DB operations, migrations
src/app.py                # FastAPI endpoints
src/geocoder.py           # Nominatim geocoding with cache + hardcoded overrides
src/ner.py                # Gazetteer-based named entity recognition
src/llm_utils.py          # Shared Anthropic client, model IDs, JSON parsing helpers
src/gdelt.py              # GDELT news scraping (sampled via GDELT_SAMPLE_RATE)
src/config.py             # Global config (GDELT_SAMPLE_RATE, etc.)
src/scheduler.py          # Background threading (15min pipeline + 2h narratives)
```
