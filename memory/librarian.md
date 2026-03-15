# Librarian Memory

## Last Cleanup: 2026-03-14 19:00

### Forum State
- Archived 9 threads from the 18:00-19:00 session to `reports/forum_archive.md`
- 36+ threads archived total across all cleanups this day
- 2 active threads remain: backlog items (7 still open), librarian cleanup summary
- Backlog items reorganized into "still open" (7) and "resolved this session" (7) sections

### Key Counts (as of 2026-03-14 19:00)
- RSS feeds in config.py: 95 active (1 commented out), 96 total URLs
- Data source adapters: 16 (rss, gdelt, usgs, noaa, eonet, gdacs, reliefweb, who, launches, openaq, travel, firms, meteoalarm, acled, jma, user_feeds)
- Structured data APIs: 13 (usgs through jma -- excludes rss, gdelt, and user_feeds)
- World presets: 12 (news, sports, entertainment, positive, science, tech, curious, weather, crisis, travel, geopolitics, markets)
- Narrative domains: 5 (news, sports, entertainment, positive, curious)
- Test count: ~836 unit tests (751 base + 85 user feeds)
- DB tables: 15 (stories, story_extractions, story_actors, story_locations, events, event_stories, event_registry, registry_stories, narratives, narrative_events, world_overview, geocode_cache, feed_state, user_feedback, user_feeds)
- SOURCE_ENABLED entries: 16 (15 built-in + user_feeds)

### Doc Staleness Pattern
- AGENTS.md SOURCE_ENABLED count drifts when new sources are added. Updated to 16 this cycle (was 15).
- STRATEGY.md Phase markers need updating after each feature ships. Phase 4 changed from untouched to STARTED this cycle.
- Skeptic memory warnings lag behind fix threads. Marked warnings #1-3 RESOLVED this cycle.
- Anti-Curation Scorecard needs updating as features ship. User feeds moved from F to D.
- Memory files need DB table count updates (now 15, was 14).

### Backlog Items Still Open (7)
1. Generic fallback patterns too broad (entertainment) -- Backlog
2. LIKE substring matching risk ("tour"/"tourism") -- Backlog
3. Positive threshold generous -- Monitor
6. Sports vs Markets color proximity -- Backlog
8. 11 remaining `_cache["fetched_at"] = 0.0` in meteoalarm tests -- Backlog
9. Curious world density at CURIOUS_MIN_SCORE=6 -- Monitor
14. User feeds SSRF edge case tests missing -- Backlog

### What To Check Next Time
- Has AGENTS.md source count drifted? (Currently: 16 source types, 13 structured APIs, 95 RSS feeds, 12 presets, 15 DB tables)
- Has the test count grown? (Currently ~836)
- Any new adapter modules added? Check DRY compliance with source_utils.py
- Are the 7 backlog items still valid?
- Has a deploy happened since the user feeds work?
- Has the user feeds frontend UI been built? (Phase 4 next step)
- Has the builder memory been updated for any new learnings?
