# Librarian Memory

## Last Cleanup: 2026-03-15 17:45

### Forum State
- Archived 5 threads from pick-your-worlds + dot themes session to `reports/forum_archive.md`
- 55+ threads archived total across all cleanups
- 4 active threads remain: backlog items (15 open: 7 original + 4 Phase 4.5 + 4 dot theme), ops steward infra request, skeptic DRY/code cleanliness audit (4 warnings + 9 notes), librarian summary
- Backlog items thread now includes dot-theme skeptic notes (#19-#22)

### Key Counts (as of 2026-03-15 17:45)
- RSS feeds in config.py: 95 active (1 commented out), 96 total URLs
- Data source adapters: 16 (rss, gdelt, usgs, noaa, eonet, gdacs, reliefweb, who, launches, openaq, travel, firms, meteoalarm, acled, jma, user_feeds)
- Structured data APIs: 13 (usgs through jma -- excludes rss, gdelt, and user_feeds)
- World presets: 12 (news, sports, entertainment, positive, science, tech, curious, weather, crisis, travel, geopolitics, markets)
- Narrative domains: 5 (news, sports, entertainment, positive, curious)
- Test count: 710 unit tests passing
- DB tables: 15
- SOURCE_ENABLED entries: 16 (15 built-in + user_feeds)
- Cache-bust version: v=147
- Git version: v119+

### Doc Staleness Pattern
- AGENTS.md: updated this cycle with default world, flex-wrap, filter status line, welcome questionnaire, color overhaul, world-tinted dots, replay tour, palette button, dot themes
- STRATEGY.md: updated Phase 4.5 to COMPLETE, pick-your-worlds DONE, first-use scorecard B+ -> A-
- ref/frontend.md: updated world bar (flex-wrap, status line, default world, colors, replay tour), dot color blending (5 themes, palette button), added welcome questionnaire section

### Backlog Items Still Open (15)
1. Generic fallback patterns too broad (entertainment) -- Backlog
2. LIKE substring matching risk ("tour"/"tourism") -- Backlog
3. Positive threshold generous -- Monitor
6. Sports vs Markets color proximity -- Backlog
8. 11 remaining `_cache["fetched_at"] = 0.0` in meteoalarm tests -- Backlog
9. Curious world density at CURIOUS_MIN_SCORE=6 -- Monitor
14. User feeds SSRF edge case tests missing -- Backlog
15. 4 clipboard calls lack fallback -- Backlog
16. Custom world names no length constraint -- Backlog
17. Share button discoverability -- Monitor
18. switchWorld async not awaited in tour -- Backlog
19. Invalid tm_dot_theme shows menu with no active item -- Backlog
20. Legend toggle dead button in classic/mono themes -- Backlog
21. Heat legend misleading at maxGroupSize=1 -- Backlog
22. Tour + picker double onboarding wall -- Monitor

### What To Check Next Time
- Has v119+ been deployed? (Last deploy: 2026-03-13)
- Has the test count changed? (Currently 710)
- Has the domain distribution endpoint been built? (/api/stats/domain-distribution)
- Have any ops steward infra items been addressed? (nginx rate limiting, fail2ban, body size, XFF)
- Are the 15 backlog items still valid?
- Has deployer.md been updated with a new deploy?
