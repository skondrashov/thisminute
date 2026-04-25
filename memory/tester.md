# Tester Memory

## Last Run: 2026-04-15

### Test Count
- **739/739 passing** (was 721 on 2026-03-15)
- +18 tests in `tests/test_new_features.py` (LLM geocoding, translated titles, curious prompt, feed counts)
- Correct command: `python -m pytest tests/ -x -q` (NOT `tests/run_all.py` — that file does not exist)

### Known Production Issues (as of 2026-04-15)

**CRITICAL:** `narrative_analyzer.py` has not run since 2026-03-28 (18 days). All 60 narratives are stale. `wiki_events.last_matched` also frozen at 2026-03-28. `event_analyzer.py` IS running (world_overview fresh). SSH and check journalctl for narrative errors.

**WARN:** 24h story volume = 6,158 (above 3,000-4,000 target). Driven by NOAA weather alerts + Iran war spike. Not a bug.

**NOTE:** NOAA events inflate active event count to 6,503 (target was 200-600 but that target predates NOAA integration). Default `/api/events` shows weather alert events with 50-53 stories each.

### API Gotchas
- `/api/registry` = old `event_registry` table (active=0, deprecated)
- `/api/wiki-events` = new `wiki_events` table (100 entries, newer system)
- `/api/events` returns a dict `{"events": [...]}` (not GeoJSON, not a plain list)
- `/api/stories` returns GeoJSON FeatureCollection
- curl | python pipelines fail in background mode — use `subprocess.run(..., capture_output=True)` with bytes decode

### Health Targets (updated)
- Active narratives: was 5-20, now correctly 40-80 (8 domains × 5-10 each)
- Active events: 200-600 target predates NOAA — NOAA alone adds thousands of weather alert events. Real signal: watch for 0 events.
- Events API max limit: 100 (enforced by Pydantic)

### tester.md Doc Issues to Fix
- `tests/run_all.py` path doesn't exist → use `python -m pytest tests/`
- Narrative active target (5-20) is outdated → 40-80
- `/api/registry` vs `/api/wiki-events` distinction not documented
