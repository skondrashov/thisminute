# Skeptic Memory

## Last Review: 2026-03-10 23:45

### World-Switching Review (2026-03-10 23:45)

9 issues raised against the world-switching implementation. Current status:

| #   | Issue                                       | Status                                                                                                                                                                                |
| --- | ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | saveWorlds try/catch + duplicate name check | FIXED (v69)                                                                                                                                                                           |
| 2   | Sports world timing on URL load             | FIXED (v69, deferred matching)                                                                                                                                                        |
| 3   | News world URL not fully shareable          | By design, no action                                                                                                                                                                  |
| 4   | Invalid world IDs handled gracefully        | Positive finding                                                                                                                                                                      |
| 5   | Old preset code fully removed               | Positive finding                                                                                                                                                                      |
| 6   | Test coverage gaps                          | PARTIALLY FIXED — custom world persistence, worlds panel, URL load, `w` shortcut, duplicate name tests added. Still untested: light mode with worlds, Escape key closing panel/dialog |
| 7   | Sports keyword matching fragile             | RESOLVED — replaced with feed-tag filtering (v70)                                                                                                                                     |
| 8   | Info panel stays open on world switch       | By design per spec                                                                                                                                                                    |
| 9   | Architecture serves directive vision        | Positive assessment                                                                                                                                                                   |

### GDELT/Volume Review (2026-03-10 21:06, all resolved)

All 6 issues addressed:

- GDELT_SAMPLE_RATE reduced to 0.003 and deployed
- MAX_GDELT_PER_CYCLE=50 cap added in gdelt.py
- Health targets updated in tester.md (3,000-4,000 stories/day)
- AGENTS.md volume figure updated
- Economist cost model recalculated for 0.003 rate
- 25K excess events self-resolved via RESOLVE_HOURS=48

### What To Check Next Time

- Are the 2 remaining test gaps closed? (light mode worlds, Escape key closing panel/dialog)
- With 74 feeds (was 65), has cost changed significantly? Economist should verify.
- Is the Entertainment world showing relevant content from the 9 new feeds?
- Has event clustering improved with stable GDELT volume, or do single-story events remain too common?
- Is the extraction backfill limit (256/cycle) sufficient at current volume?

### Recurring Patterns to Watch

- **Stale documentation** -- targets, cost estimates, and architecture descriptions lag behind code changes. The librarian does cleanup but can only fix what's been noticed.
- **Claims without verification** -- always check deployed behavior, not just code.
- **Test coverage** -- untested areas are where the next bugs will be.

### Architecture Notes

- `RESOLVE_HOURS = 48` in `src/semantic_clusterer.py` -- events auto-resolve after 48h with no new stories
- `MAX_ACTIVE_EVENTS = 200` in `src/registry_manager.py` -- registry events (map labels) are capped at 200
- `get_active_events(conn, limit=500)` -- clustering only considers top 500 events
- `get_unassigned_stories(conn, limit=500)` -- clustering processes max 500 unassigned stories per cycle
- Backfill limit: 256 stories per cycle in `llm_extractor.py`
- Events API defaults to limit=20, min_stories=2 -- frontend isn't loading all events
- `MAX_GDELT_PER_CYCLE = 50` in `src/gdelt.py` -- caps GDELT stories per 15-min cycle regardless of sample rate
