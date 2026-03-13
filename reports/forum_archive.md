# Forum Archive

Threads archived by librarian. Newest archives first.

---

## Archived 2026-03-13 (librarian cleanup — all March 10-11 threads resolved)

All threads below shipped and deployed between v71-v76. No open items remain.

---

### Thread: v76 — Per-Domain Event Queries, Situation Accent Colors, Mobile Swipe, Narrative Caps (2026-03-11)

**Author:** builder | **Resolved:** 2026-03-11 ~14:00

Per-domain event queries (`_get_domain_events`), domain-colored situation accents (blue/green/purple/gold), narrative cap enforcement (20 news, 10 each for others), mobile swipe improvements, `/api/narratives` limit raised to 60. Deployed as v76.

---

### Thread: v73 — World-Aware Situations, Filter Independence, ESPN Expansion, UX Reorder, Pre-LLM Dedup, Loading Indicator (2026-03-11)

**Author:** builder | **Resolved:** 2026-03-11 ~04:00

Backend: domain-aware narrative analysis (news/sports/entertainment/positive), filter independence (time/search/opinion persist across world switches), 8 new ESPN feeds (total 13 ESPN, 20 sports), pre-LLM story dedup. Frontend: sidebar reorder, search icon-trigger, loading indicator. Deployed as v73+v74.

---

### Thread: v74 — Sources Popup, Test Reliability (2026-03-11)

**Author:** builder | **Resolved:** 2026-03-11 ~09:00

Sources filtering moved to popup. Test suite: `networkidle` replaced with `domcontentloaded`, `waitForDataLoad()` helper, `expandSearch()` helper. Deploy script sleep increased.

---

### Thread: v75 — Mobile Bottom Sheet (2026-03-11)

**Author:** builder | **Resolved:** 2026-03-11 ~10:30

Map fills 100vh on mobile. Floating bottom bar (56px). 3 sheet states (closed/half/full). Drag handle with swipe gestures. 63/63 Playwright tests.

---

### Thread: UX Overhaul Spec — Mobile Bottom Sheet + Desktop Sidebar Reorder (2026-03-11)

**Author:** designer | **Resolved:** 2026-03-11 02:41

Full spec for mobile bottom sheet + desktop sidebar reorder. Implemented in v73-v75. Spec in `reports/designer.md`.

---

### Thread: Strategist — World-Aware Situations (Phase 3 Priority 1) (2026-03-11)

**Author:** strategist | **Resolved:** 2026-03-11 02:41

Strategy for per-domain narrative analysis. Multiple analysis passes, positive situations as inherently positive, domain tagging. All implemented in v73-v76.

---

### Thread: v72 — Performance, Map Label Filtering, US Sports Feeds (2026-03-11)

**Author:** builder | **Resolved:** 2026-03-11 02:37

Deferred `loadFeedTags`, map label threshold fix, ESPN NFL/NBA/MLB feeds. Deployed as v72.

---

### Thread: DIRECTIVE: Diverse Worlds — Making thisminute Work for Everyone (2026-03-10)

**Author:** human + orchestrator | **Resolved (Phases 1-3):** 2026-03-11

Human directive for worlds system. Phases 1-3 complete (world presets, feed expansion, world-aware extraction). Phase 4 (deep customizability) and Phase 5 (feedback loop) remain as longer-term goals.

---

### Thread: Event Clustering Thresholds Tuned to Reduce Singletons (2026-03-11)

**Author:** builder | **Resolved:** 2026-03-11 01:27

Fuzzy match threshold 0.50 to 0.40, min overlap words 2 to 1, dynamic merge thresholds. Deployed, backend-only.

---

### Thread: v71 Deployed — Entertainment World Live, Tests Updated (2026-03-11)

**Author:** orchestrator | **Resolved:** 2026-03-11 01:15

v71 deployed. 61/61 Playwright. 74 RSS feeds, 15 entertainment sources.

---

### Thread: Phase 1 World-Switching Shipped + Verified (2026-03-10)

**Author:** orchestrator | **Resolved:** 2026-03-10 23:50

3 default worlds (News, Sports, Positive), custom save/delete, URL state, keyboard shortcut. Deployed as v68.

---

### Thread: World-Switching UX Design Spec (Phase 1) (2026-03-10)

**Author:** designer | **Resolved:** 2026-03-10 22:51

Spec in `reports/designer.md`. Implemented in v68-v69.

---

### Thread: Skeptic Review — World-Switching Code, Tests, and Spec Compliance (2026-03-10)

**Author:** skeptic | **Resolved:** 2026-03-10 23:45

9 issues raised, all addressed. 2 minor test gaps (light mode worlds, Escape key) remain low-priority.

---

### Thread: Docs Consolidation Complete (2026-03-10)

**Author:** librarian | **Resolved:** 2026-03-10

CLAUDE.md one-liner, AGENTS.md canonical, PROTOCOL.md replaced AGENT_INSTRUCTIONS.md, ROLES.md deleted.

---

### Thread: Librarian Cleanup — 2026-03-11 01:21

**Author:** librarian | **Resolved:** 2026-03-11 01:21

Archived 16 overnight loop threads. Updated AGENTS.md feed counts (74), STRATEGY.md phase completion, memory/skeptic.md. Forum reduced from ~1,260 to ~130 lines.

---

## Archived 2026-03-11 (librarian cleanup of overnight loop threads)

All threads below are resolved — fixes deployed, verified, and stable.

---

### Thread: System Health Check — GDELT Volume Crisis (2026-03-10)

**Author:** tester | **Resolved:** 2026-03-10 22:33

GDELT was ingesting ~45K stories/day (target ~100-125). At GDELT_SAMPLE_RATE=0.07, raw volume growth meant 7% was far too high. Extraction rate collapsed to 60.5%, 25K+ active events.

**Resolution:** GDELT_SAMPLE_RATE reduced to 0.003, MAX_GDELT_PER_CYCLE=50 cap added. Deployed, health check confirmed recovery. 25K excess events self-resolved via RESOLVE_HOURS=48.

---

### Thread: GDELT Sample Rate Fix + Playwright Status Update (2026-03-10)

**Author:** builder | **Resolved:** 2026-03-10 22:33

Reduced GDELT_SAMPLE_RATE from 0.07 to 0.003. Added "escalating"/"de-escalating" to Playwright allowed statuses. Both deployed and verified.

---

### Thread: Skeptic Review — GDELT Rate, Event Bloat, Agent Complexity, Doc Drift (2026-03-10)

**Author:** skeptic | **Resolved:** 2026-03-10 21:10+

6 issues raised, all addressed:
1. Health targets stale (150-250 vs actual 3,630) — updated in tester.md and AGENTS.md
2. 25K events self-resolve — confirmed, no manual cleanup needed
3. Agent system complexity — noted, useful parts are checklists
4. Economist cost data stale — recalculated for 0.003 rate
5. No volume safeguard — MAX_GDELT_PER_CYCLE=50 added
6. Severity distribution anomaly — informational, GDELT content naturally skews low

---

### Thread: Volume Safeguard + Health Target Updates (2026-03-10)

**Author:** builder | **Resolved:** 2026-03-10 22:33

MAX_GDELT_PER_CYCLE=50 cap added. Health targets updated in tester.md (3,000-4,000 stories/day). AGENTS.md volume figure updated to ~3,500/day. All deployed.

---

### Thread: Cost Model Recalculated for GDELT_SAMPLE_RATE=0.003 (2026-03-10)

**Author:** economist | **Resolved:** 2026-03-10 21:10

Full cost model recalculated: ~$14-16/day total at 0.003 rate (was ~$64/day actual at 0.07 crisis rate). Updated agents/economist.md and STRATEGY.md.

---

### Thread: Prompt Caching Implemented (2026-03-11)

**Author:** builder | **Resolved:** 2026-03-11 01:00

Added Anthropic prompt caching to llm_extractor.py and event_analyzer.py. Saving ~$1.22/day. Deployed with v70.

---

### Thread: Deploy Complete + Post-Deploy Verified (2026-03-10)

**Author:** orchestrator | **Resolved:** 2026-03-10 22:33

GDELT fix deployed. Health: OK. Playwright: 52/55 (3 flaky timeouts). Verdict: HEALTHY.

---

### Thread: Orchestrator Overnight Loop Started (2026-03-10)

**Author:** orchestrator | **Resolved:** 2026-03-11 01:15

Overnight loop ran 20+ cycles. Shipped: GDELT fix, world-switching (v68), skeptic fixes (v69), prompt caching, sports feeds + feed tagging (v70), entertainment feeds (v71).

---

### Thread: World-Switching UX Implemented (Phase 1, v68) (2026-03-10)

**Author:** builder | **Resolved:** 2026-03-10 23:50

Full world-switching UX from designer spec. 3 default worlds (News, Sports, Positive), custom save/delete, modified indicator, URL state, keyboard shortcut. Deployed as v68, 56/56 tests.

---

### Thread: Playwright Test Suite Updated for World System (v68) (2026-03-10)

**Author:** builder | **Resolved:** 2026-03-10 23:50

12 tests rewritten for world system. Old preset selectors fully removed. Test count 55 -> 56.

---

### Thread: Builder Response — Skeptic World-Switching Fixes (2026-03-10)

**Author:** builder | **Resolved:** 2026-03-11 00:20

All 5 skeptic warnings addressed: saveWorlds try/catch, duplicate name check, deferred sports matching, custom world persistence test, 4 additional coverage tests. Bumped to v69.

---

### Thread: v69 Deployed + Verified (2026-03-11)

**Author:** orchestrator | **Resolved:** 2026-03-11 00:20

61/61 Playwright pass. All skeptic fixes deployed.

---

### Thread: Roadmap Update — Phase 1 Complete, What's Next (2026-03-11)

**Author:** strategist | **Resolved:** 2026-03-11 01:15

Phase 1 complete. Priorities set: prompt caching (done), sports feeds (done), entertainment feeds (done). All completed in overnight loop.

---

### Thread: Phase 2 — Sports Feed Expansion + Feed Tagging System (2026-03-11)

**Author:** builder | **Resolved:** 2026-03-11 01:00

7 new sports feeds (ESPN, ESPN Soccer, ESPNcricinfo, Sky Sports, Sportstar, Autosport, Rugby World). Feed tagging system with 8 categories. /api/feed-tags endpoint. Sports world switched from keyword to feed-tag filtering. Deployed as v70.

---

### Thread: v70 Deployed + Verified (2026-03-11)

**Author:** orchestrator | **Resolved:** 2026-03-11 01:00

61/61 Playwright pass. 10 sports feeds live, feed tagging working.

---

### Thread: Phase 2 — Entertainment Feed Expansion + World Preset (2026-03-11)

**Author:** builder | **Resolved:** 2026-03-11 01:15

9 entertainment feeds added (Variety, Hollywood Reporter, Deadline, Rolling Stone, Billboard, Pitchfork, NME, Soompi, Bollywood Hungama). Entertainment world preset (purple). Total: 15 entertainment sources, 74 feeds overall. Deployed as v71.

---

## Archived 2026-03-10 (previous cleanup)

All threads below were 7+ days stale (last activity March 3).

---

## Thread: Latest Status (2026-03-03 02:17)

**builder**: Current state after 4 development rounds:

### Numbers
- **542 stories** from **16 sources** (6 news orgs, multiple section feeds)
- **331 geocoded** (61% rate, up from 48% after demonym/abbreviation NER)
- **47 concepts** across **8 domains**
- **17/17 tests passing**

### Round 4 Improvements
- **Trending concept detection** (`/api/trending`) - compares 3h vs 24h frequency, shows spiking concepts
- **Trending bar in sidebar** - red chips show trending concepts, clickable to filter
- **New story notification badge** - floating badge when polling finds new stories
- **Story freshness gradient** - newer stories are brighter/larger, older ones dimmer/smaller
- **New story highlight** - freshly arrived stories get white ring on map for 30s
- **Sidebar collapse toggle** - button to hide sidebar (keyboard: `s`)
- **Demonym NER** - "British" -> UK, "American" -> US, "French" -> France (50+ demonyms)
- **Abbreviation NER** - "UK", "US", "U.S.", "U.K.", "UAE" now resolve to countries
- **Geocode rate 48% -> 61%** after NER improvements (73 new geocoded stories)
- **SQLite busy timeout** - `PRAGMA busy_timeout=10000` prevents lock errors

### Features (cumulative)
- MapLibre GL JS 5.1.0 with **globe projection** + atmosphere/stars
- **Multi-label concept tagging** (47 concepts, 8 domains)
- **Concept chip toggles**: click = include, right-click = exclude
- **Trending concept bar** with spike detection
- **Heatmap mode** toggle (density visualization)
- **Text search** with debounced client-side filtering
- **Time filter** (1h, 6h, 24h, 7d)
- **Source filter** dropdown
- **Sidebar hover** highlights markers on map
- **Click story** to fly to location
- **Keyboard shortcuts**: / = search, Escape = close, m/h = marker/heatmap, s = sidebar
- **Story freshness gradient** - opacity and size based on age
- **New story badge** - notification when polling finds new stories
- **Shareable filter URLs** - filter state encoded in URL hash
- **Sidebar toggle** - collapsible for full-screen map
- Geocode cache with null result caching (>90% hit rate after warmup)
- NER with gazetteer + demonyms + abbreviations
- Background scheduler (scrapes every 15min)

### Architecture
```
16 RSS Feeds -> scraper.py -> ner.py (gazetteer + demonyms + abbreviations)
                                 -> geocoder.py (Nominatim + cache + hardcoded landmarks)
                                 -> categorizer.py (47 concepts, 8 domains)
                                 -> database.py (SQLite WAL + busy_timeout)
                                       |
                         app.py (FastAPI) -> /api/stories (GeoJSON)
                                          -> /api/concepts (domain-grouped with counts)
                                          -> /api/trending (spike detection)
                                          -> /api/sources, /api/stats
                                       |
                     index.html + app.js (MapLibre globe + trending + freshness + notifications)
```

---

## Thread: Strategist Round 3 — Anti-Curation Scorecard

**strategist**: Evaluation of the original vision of "contesting the curated front page".

### Anti-Curation Scorecard (Round 4)
| Feature | Status | Score |
|---------|--------|-------|
| User picks what to see (not editor) | Concept chips + exclude + presets | A+ |
| Spatial filtering (zoom = filter) | Globe/map zoom | A |
| Multi-source aggregation | 19 feeds, 8 orgs (BBC, Guardian, AJ, NPR, CNN, NYT, ABC AU) | A |
| No editorial hierarchy | All stories equal weight | A |
| Negative filtering ("not this") | Right-click to exclude, "No Sports" preset | A+ |
| Text search | Works, debounced | A |
| Time filtering | 4 presets | B+ |
| **Trending detection** | Spike ratio comparison, trending bar | A |
| **Filter presets** | 6 one-click presets (Conflict, Politics, Climate, etc.) | A |
| **Shareable filters** | URL hash encodes all filter state | A |
| Breaking detection | Not built (trending is close) | C |
| User-added feeds | Not built | F |
| Custom concepts | Not built | F |

**Overall: A-**

### What would make it an A+
1. **User-configurable feeds** — let users paste RSS URLs, store in localStorage
2. **Custom concepts** — let users define keyword groups, save as personal filters
3. **Offline mode** — service worker + cached data for offline viewing

---

## Thread: Technical Debt (originally posted by "verifier", a role that no longer exists)

Items noted:
1. Hardcoded concepts in JS (DOMAIN_COLORS) should come from API
2. No error handling for fetch failures in frontend
3. Source filter re-fetches from API while concept/search/time filter locally
4. Geocoder opens a new DB connection per call (should pool or pass connection)
5. Tests don't cover API endpoints (only unit tests)

**Note**: Items 2 and 5 have likely been addressed since this was posted (API tests and Playwright tests exist now). Items 1, 3, 4 may still be relevant — builder should verify.
