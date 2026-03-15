# Librarian Memory

## Last Cleanup: 2026-03-15 08:12

### Forum State
- Archived 14 threads from the v119 session to `reports/forum_archive.md`
- 50+ threads archived total across all cleanups
- 3 active threads remain: backlog items (11 open: 7 original + 4 from Phase 4.5 skeptic), ops steward infra request, librarian summary
- Backlog items thread consolidated Phase 4.5 skeptic notes (#15-#18) into the main backlog

### Key Counts (as of 2026-03-15 08:12)
- RSS feeds in config.py: 95 active (1 commented out), 96 total URLs
- Data source adapters: 16 (rss, gdelt, usgs, noaa, eonet, gdacs, reliefweb, who, launches, openaq, travel, firms, meteoalarm, acled, jma, user_feeds)
- Structured data APIs: 13 (usgs through jma -- excludes rss, gdelt, and user_feeds)
- World presets: 12 (news, sports, entertainment, positive, science, tech, curious, weather, crisis, travel, geopolitics, markets)
- Narrative domains: 5 (news, sports, entertainment, positive, curious)
- Test count: 710 unit tests passing
- DB tables: 15 (stories, story_extractions, story_actors, story_locations, events, event_stories, event_registry, registry_stories, narratives, narrative_events, world_overview, geocode_cache, feed_state, user_feedback, user_feeds)
- SOURCE_ENABLED entries: 16 (15 built-in + user_feeds)
- Cache-bust version: v=145
- Git version: v119

### Doc Staleness Pattern
- AGENTS.md: updated this cycle with dot color system, world bar, share button, SEO, security hardening
- STRATEGY.md: updated Anti-Curation Scorecard (first-use D -> B+, shareability B -> A-), SEO marked done
- ref/frontend.md: added world bar, dot color blending, SEO files sections
- Memory files: builder.md already current, security.md already current, deployer.md still shows last deploy 2026-03-13

### Backlog Items Still Open (11)
1. Generic fallback patterns too broad (entertainment) -- Backlog
2. LIKE substring matching risk ("tour"/"tourism") -- Backlog
3. Positive threshold generous -- Monitor
6. Sports vs Markets color proximity -- Backlog
8. 11 remaining `_cache["fetched_at"] = 0.0` in meteoalarm tests -- Backlog
9. Curious world density at CURIOUS_MIN_SCORE=6 -- Monitor
14. User feeds SSRF edge case tests missing -- Backlog
15. 4 clipboard calls lack fallback (only world-share-btn has one) -- Backlog
16. Custom world names no length constraint in icon+label layout -- Backlog
17. Share button discoverability -- Monitor
18. switchWorld async not awaited in tour -- Backlog

### What To Check Next Time
- Has v119 been deployed? (Last deploy: 2026-03-13, pre-v119 work)
- Has the test count changed? (Currently 710)
- Has the "pick your worlds" first-visit selector been built? (Phase 4.5 remaining item)
- Has the domain distribution endpoint been built? (/api/stats/domain-distribution)
- Have any ops steward infra items been addressed? (nginx rate limiting, fail2ban, body size, XFF)
- Are the 11 backlog items still valid?
- Has deployer.md been updated with a new deploy?
