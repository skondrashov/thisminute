# Strategy

## Vision

thisminute.org shows what's happening in the world right now, plotted on a map. Every news story gets a dot. The user decides what to see — not editors. The map IS the filter.

**North star**: Anti-curation. Reduce the gap between "everything happening" and "what the user can find."

## Current Priorities (updated 2026-05-14)

All original v1 priorities are complete. Current focus is UX polish and code quality for public launch readiness.

### Deprioritized

- **Custom topic/concept creation** — Moved to Phase 6. Power-user feature for a product that needs first-time users. Presets + search cover the major use cases.
- **Usage analytics per world** — Premature. No user base to measure yet.
- **Feedback-driven automation** — Feedback API is live. Manual triage for now.
- **Dot color theme selector** — Hidden due to interaction issues with country highlights. Tracked in BACKLOG.md.
- **Space/Internet tile scaling** — Nice-to-have. Backlog.
- **app.js module split** — The file (~5400 lines) is a build artifact edited directly. Should be re-split into ~10 source modules and restore the esbuild pipeline. Not blocking but improves maintainability.

## Completed

- [x] RSS scraping (tagged feeds, multi-language)
- [x] LLM extraction via Haiku (batches of 8)
- [x] Signature-based event clustering
- [x] Event registry with map labels
- [x] Situation synthesis via Sonnet (multi-domain passes)
- [x] Globe projection (MapLibre 5.x, always globe — no flat switch)
- [x] Orthogonal filter system (topic, source, time, sentiment, situation, location, search)
- [x] Light/dark mode
- [x] Trending concept detection
- [x] Shareable filter URLs
- [x] Deployed on GCP (thisminute.org live)
- [x] GDELT volume stabilized (SAMPLE_RATE + MAX_PER_CYCLE cap)
- [x] Structured data APIs (USGS, NOAA, EONET, GDACS, ReliefWeb, WHO, Launch Library, OpenAQ, Travel Advisories, FIRMS, Meteoalarm, ACLED, JMA)
- [x] Preset system with manage panel, drag-to-reorder, search-within-presets
- [x] Mobile UX (bottom sheet, reticle, stripped-down controls)
- [x] SEO/social (OG image, meta tags, robots.txt, sitemap.xml)

## Diverse Worlds (Human Directive)

thisminute should work for ANY interest, not just hard news. The next major effort is **worlds** — distinct lenses that transform the experience. See full directive in `reports/forum_archive.md` (archived 2026-03-13).

### Phase 1: Customizable Filter System + World Presets -- COMPLETE (v69)

- [x] Build the underlying "mixing board" — all filters composable and saveable
- [x] World presets are saved configurations on top of that system
- [x] Users can start from a preset, tweak it, save their own
- [x] Ship with default presets: News, Sports, Positive
- [x] One-click preset switching, visually distinct
- [x] Modified indicator (orange dot) when user tweaks filters
- [x] URL state integration (shareable `#world=X`)
- [x] Keyboard shortcut (`w` cycles worlds)
- [x] Skeptic review: saveWorlds try/catch, duplicate name guard, deferred sports matching
- [x] Playwright tests passing

### Phase 2: Feed Expansion by World -- COMPLETE (v71)

- [x] Sports feeds added (ESPN, ESPN Soccer, ESPNcricinfo, Sky Sports, Sportstar, Autosport, Rugby World)
- [x] Feed tagging system: all feeds tagged (news, sports, entertainment, positive, tech, science, business, health). `FEED_TAG_MAP` + `/api/feed-tags` endpoint
- [x] Sports world uses feed tags instead of keyword matching
- [x] Prompt caching implemented
- [x] Entertainment feeds added (Variety, Hollywood Reporter, Deadline, Rolling Stone, Billboard, Pitchfork, NME, Soompi, Bollywood Hungama)
- [x] Entertainment world preset (purple, `feedTags: ["entertainment"]`)

### Phase 3: World-Aware Extraction — COMPLETE

- [x] **World-aware situation synthesis** — Per-domain event queries + domain-specific Sonnet prompts. All 5 domains generating at cap (20 news, 10 sports, 10 entertainment, 10 positive, 10 curious = 60 total). Entertainment uses topic-signal + lowered source threshold. Positive uses relaxed bright_side + source signal.
- [x] Sports clustering (match/tournament, not just event_signature)
- [x] Entertainment clustering (person/production-centric)
- [x] "Human interest" scoring for trivial world (human_interest_score extraction + curious domain)
- [x] Curious world story-level filtering (`curiousMode` with `human_interest_score >= 6`, mirrors `brightSideMode` pattern)

### Phase 4: Deep Customizability — NEARLY COMPLETE

- [x] User-added RSS feeds backend (POST/GET/DELETE endpoints, SSRF protection with DNS pinning + redirect blocking, feed validation, pipeline integration with global volume cap, `user_feeds` table, `SOURCE_ENABLED["user_feeds"]` kill switch)
- [x] User-added RSS feeds frontend UI (modal dialog: add/list/remove feeds, status dots, tag selection, error display)
- [x] Shareable world presets via URL (share button per world, copy-to-clipboard)

### Phase 4.5: First-Use Experience — COMPLETE

- [x] Auto-cycling world presets for new visitors (6 worlds, 5s each, overlay with icon+name, stops on any interaction)
- [x] "Pick your worlds" first-visit selector — implemented as welcome questionnaire (6 personality cards, replaces world picker in first-visit flow)
- [x] Prominent world bar redesign (icon+label buttons, 12 unique domain-colored active states, hover lift, flex-wrap on desktop)
- [x] SEO/social shareability (OG image 1200x630, meta description, canonical link, twitter:card summary_large_image, dynamic OG for deep links, robots.txt, sitemap.xml)
- [x] Domain distribution endpoint (`/api/stats/domain-distribution`) — monitoring endpoint for content balance across domains, feed tags, source types
- [x] Dominance-tinted dot colors (white/gray base, tints toward dominant domain — replaces misleading HSL blending)
- [x] Full color overhaul (Tech=hot pink, Curious=orange, Markets=dark teal — no more collisions)
- [x] Map dot color themes (5 themes: domain, classic, mono, heat, neon — palette button + popup menu)
- [x] Replay tour menu item, filter status line below world bar

### Phase 5: Feedback Loop — STARTED

- [x] Explicit user feedback — `/api/feedback` endpoint live (v114), `user_feedback` table, rate limiting (5/min). Feedback triage owned by tester.
- Note: Usage analytics and feedback-driven automation deferred until user base exists.
- Note: ProMED RSS is dead (all URLs return 404, FeedBurner mirror empty since 2018). WHO DON partially covers disease outbreak space.

### Phase 6: Power User Features — NOT STARTED

- [ ] Custom topic/concept creation
- [ ] Usage analytics per world
- [ ] Feedback-driven improvements (suggest feeds, suggest categories)

### Ongoing (parallel)

- [x] Prompt caching (~$1.22/day savings)
- [x] Event dedup improvements: DB-indexed exact signature matching + full-DB merge pass (v80)
- [x] Mobile layout polish: smooth drag interpolation, swipe-to-close, auto-minimize (v84-85)
- [x] Search UX: keywords from LLM extraction now searchable (v81)
- [x] Story thumbnail images from RSS feeds (v82)
- [x] v83: Situation source counts, info panel context header, flyTo on situation select
- [x] Performance: nginx gzip + payload trim (2.3MB/20s → 477KB/0.7s = 29x faster initial load)
- [x] v86: Situation deep linking (shareable URLs), favicon, info panel slide transitions
- [x] v87-88: Story card images, favicons, data freshness indicator, search highlighting
- [x] Performance: batch N+1 queries (events 60→2, search 400→2, narratives 120→2), request-local geocode cache, concepts 7-day scan limit
- [x] UX: skeleton loading, keyboard shortcuts (o=open story, j/k=navigate), ARIA a11y, clickable map labels, developing badge, first-visit onboarding
- [x] v89: situation hover-highlight on map, search result count, view persistence in URL, tab title new-story count, situation delta badges, tab counts, a11y focus-visible
- [x] Performance: batch event stories query (eliminates N+1 in /api/events)
- [x] Performance: SQLite json_each() for topics (5.2s → 0.27s), narratives query split (3.5s → 0.28s), sources in-memory cache, Cache-Control headers on all endpoints
- [x] v90: smooth situation expand/collapse animation (CSS grid), chevron rotation, 'r' refresh shortcut, richer hover tooltips (source+time), shareable map position in URL, recency-based dot opacity, clickable concept tags and source names in info panel
- [x] v91: pulse animation on new story map dots, situation location labels, dynamic OpenGraph tags for deep links, copy-link on story cards, page title reflects active situation
- [x] v92: persistent map highlight for active situation, CSS grid event animation, ingestion velocity in stats bar
- [x] v93: "Map" button in info panel, event hover-highlight, story velocity display
- [x] Performance: in-memory caches for stories (30s), clouds (30s), events (60s), narratives (120s)
- [x] v94: visited story tracking (dimmed read stories), concepts cache (1.2s→0.08s), image placeholders, scroll preservation, mobile onboarding, "new" situation badge, trending indicators on concept chips
- [x] RSS feed: /api/feed.rss (global + per-situation via ?situation=N), autodiscovery link
- [x] Performance: in-memory caches for topics (30min) and concepts (30min)
- [x] UX: mobile sheet peek animation for first-time users
- [x] UX: source search filter in popup, excluded filter pills, situation event timestamps, 3h/12h time options, light-mode excluded chip style
- [x] v95: story detail image fade-in, hover tooltip fade animation, world button situation counts, stale data indicator, info panel time group headers (Today/Yesterday/Older)
- [x] UX: share view button, world overview domain-colored label, world-switch auto-deselects cross-domain situations
- [x] Fix: clearAllFilters closes info panel, narrative events include timestamps
- [x] UX: situation event progress bars (domain-colored), event locate buttons (flyTo)
- [x] UX: domain-colored map highlights (sports=green, entertainment=purple, positive=amber)
- [x] UX: light-mode map colors (heatmap, labels, dots, highlights all theme-aware)
- [x] UX: full timestamp tooltips on relative times, map label click selects parent situation
- [x] Testing: Playwright tests (root cause fix: parseInt on comma-formatted numbers)
- [x] v114: Feedback API (`/api/feedback`), proximity hover polish, mobile reticle, feed zoom scaling, crosshair cursor, WAL ownership fix, server-side rate limiting
- [x] Structured data sources: USGS earthquakes, NOAA weather alerts, EONET natural events, GDACS disasters, ReliefWeb humanitarian reports, WHO disease outbreaks, Launch Library space launches, OpenAQ air quality, US Travel Advisories, NASA FIRMS fire detection, Meteoalarm (European weather), ACLED (conflict data), JMA weather warnings (Japan)
- [x] SOURCE_ENABLED config toggles (env-var overridable per source)
- [x] Inference feed pattern (pre-built `_extraction` dicts, zero LLM cost for structured sources)
- [x] DRY refactor: `source_utils.py` shared helpers, data-driven pipeline SOURCES loop
- [x] FIRMS/NOAA volume caps: `FIRMS_MAX_BYTES` (10 MB) + `FIRMS_MAX_ROWS` (5000), `NOAA_MAX_ALERTS` (150) severity-sorted
- [x] Launch Library cache optimization: TTL increased from 30 to 45 min, reducing rate limit utilization from 53% to ~35%
- [x] World presets: All Stories, Bright Side, Sports, Entertainment, Curious, Science, Tech, Planet, Conflict, Travel, Power, Markets, Health
- [x] Multi-domain narrative analysis (news, sports, entertainment, positive, curious, science, business, health)
- [x] Domain-specific clustering: tournament-centric sports, production-centric entertainment
- [x] country_centroids.py helper for structured source geocoding
- [ ] Space/internet tile scaling at globe zoom

### Strategist Roadmap -- Remaining Items (not implemented)

- [x] **JMA** (Japan Meteorological Agency) -- Japanese weather alerts. `src/jma.py`. Fetches active warnings from JMA bosai API, aggregated at class10s regional level, 47 prefecture centroids. Added to Weather, Crisis, Travel presets.
- [x] **arXiv/bioRxiv/medRxiv RSS** -- Research preprint feeds added to FEEDS list (2026-03-14). arXiv AI, arXiv CS, bioRxiv, medRxiv. Also added IGN and Oddity Central.
- **ProMED** -- Disease alert RSS feed is dead (all URLs return 404, FeedBurner mirror empty since 2018). WHO DON partially covers this space. Would need a dedicated HTML scraper.
- **Global Forest Watch** -- Deforestation alert API. Not yet implemented.
- **SEC EDGAR** -- Financial filings API. Not yet implemented.

## Situation Architecture Decisions (2026-03-11)

### The Problem

`narrative_analyzer.py` runs every 1-2 hours, takes 50 events, and asks Sonnet to group them into situations. The prompt says "concrete, real-world developments" with examples like "2026 Iran war" and "Trump tariff escalation." It is entirely geopolitical. Three consequences:

1. **Sports/Entertainment worlds show zero situations.** The analyzer never creates "2026 IPL Season" or "Oscar Season 2026" because the prompt doesn't think in those terms. The events exist (ESPN stories cluster into events), but no situation synthesis happens for them.
2. **Positive world shows irrelevant situations.** It filters by `bright_side_count > 0`, which means "war situations that happen to contain a few positively-scored stories." Showing "US-Iran War" in the Positive world because 2 of its 47 stories got a bright_side_score >= 4 is wrong.
3. **The 50-event cap dilutes non-news events.** The analyzer gets the top 50 active events. If 45 are geopolitical and 5 are sports, Sonnet has no mass to synthesize sports situations from.

### Decision 1: Make the narrative analyzer world-aware

**Approach: Multiple analysis passes, one per domain.**

The narrative analyzer should run separate passes for different domains. Each pass filters events by the feed tags of their constituent stories and uses a domain-appropriate prompt. Concretely:

- **News pass** (current behavior, unchanged): Events where majority of stories come from news/business/tech/science feeds. Prompt stays as-is.
- **Sports pass**: Events where majority of stories come from sports-tagged feeds. Prompt rewritten for sports domain — a "situation" is an ongoing tournament, a transfer saga, a rivalry series, a doping scandal. Examples: "2026 IPL Season", "NFL Free Agency 2026", "FIFA World Cup Qualifying".
- **Entertainment pass**: Events where majority of stories come from entertainment-tagged feeds. Prompt rewritten for entertainment domain — a "situation" is an awards season, a franchise release wave, a celebrity scandal arc, a music tour. Examples: "Oscar Season 2026", "K-pop Group Disbandment Wave", "Marvel Phase 7 Rollout".

**Why not tag-and-filter on the frontend?** Because the problem is not filtering — the frontend already filters narratives by story overlap with the active world. The problem is that Sonnet never _creates_ the situations. You cannot filter for something that does not exist. The synthesis prompt must understand the domain to recognize what constitutes a "situation" in that domain.

**Cost impact:** 2-3 additional Sonnet calls per analysis cycle (every 1-2 hours). At ~$0.01-0.02 per call, this adds ~$0.50-1.00/day. Acceptable.

**Implementation:** Add a `domain` parameter to `analyze_narratives()`. The scheduler calls it once per domain. Each domain gets its own prompt preamble and examples but shares the same update/create/cleanup logic.

### Decision 2: Positive situations should be inherently positive narratives, not bright-side angles on war

The human's insight is correct: "positive feel-good cute and inspiring things are not really the same thing as medic actions during war." The current approach (filter by bright_side_count) shows war situations in the Positive world, which is philosophically wrong.

**New approach: A dedicated "positive" analysis pass.**

The positive pass should:

- Draw from ALL events (not just positive-feed stories), but with a filter: only include events where >= 30% of stories have `bright_side_score >= 4`
- Synthesize situations that are _inherently positive developments_: renewable energy milestones, peace processes, medical breakthroughs, conservation wins, community resilience
- Explicitly exclude "the bright side of a fundamentally negative situation" — those belong in the News world with their bright_side scores, not as Positive situations
- Use a prompt that says: "A positive situation is something you'd tell a friend about to make their day better. 'Progress on Middle East peace talks' qualifies. 'The Iran war' does not, even if some stories within it are positive."

**The bright_side_count filter stays** as a secondary signal on the frontend (it still helps rank), but it is no longer the sole mechanism for Positive world situations.

### Decision 3: Tag narratives with their domain

Each narrative should carry a `domain` field: "news", "sports", "entertainment", "positive". The frontend can then filter the Situations panel per-world natively, without relying solely on story_id overlap (which is indirect and fragile).

This is additive — the `story_ids` overlap filtering remains for cross-world edge cases (a cricket match that gets covered by a news outlet too). But the primary filter becomes the domain tag.

### Decision 4: Minimum viable implementation order

1. **Add `domain` column to `narratives` table** (migration, default "news")
2. **Refactor `analyze_narratives()` to accept a domain parameter** with domain-specific prompts
3. **Update scheduler to run one pass per domain** (news, sports, entertainment, positive)
4. **Expose `domain` in `/api/narratives` response**
5. **Frontend: filter situations by domain matching the active world**

Steps 1-3 are backend-only (no cache version bump). Step 4-5 need a version bump. The whole thing is one builder task, medium complexity.

### What This Does NOT Change

- Event clustering stays world-blind. Events are clustered by `event_signature` regardless of domain, which is correct — the same clustering algorithm works for "Iran airstrike" and "IPL match result."
- The event registry stays world-blind. Map labels are still derived from events, not situations.
- The 50-event cap is per-domain now (each pass gets its own 50), which actually increases total coverage.
- The `MAX_NARRATIVES` cap is per-domain. Lower-volume domains get fewer slots.

## Anti-Curation Scorecard

| Feature                                 | Score                                                       |
| --------------------------------------- | ----------------------------------------------------------- |
| User picks what to see                  | A+                                                          |
| Spatial filtering (map zoom)            | A                                                           |
| Multi-source aggregation                | A                                                           |
| No editorial hierarchy                  | A                                                           |
| Negative filtering                      | A+                                                          |
| Trending detection                      | A                                                           |
| World presets (saveable filter configs) | A+                                                          |
| Shareable filters                       | A                                                           |
| Custom worlds (user-created)            | A                                                           |
| World-aware situations                  | A- (all domains generating situations, domain-specific clustering shipped) |
| User-configurable feeds                 | A- (backend + frontend complete, add/list/remove with status, SSRF protection) |
| Custom concepts                         | F (deferred to Phase 6)                                     |
| First-use experience                    | A- (prominent icon+label preset bar with flex-wrap, manage panel with drag-to-reorder, filter status line) |
| Shareability                            | A- (URL state, OpenGraph with OG image, dynamic OG for situation deep links, robots.txt/sitemap.xml) |

**Overall: A-** (World-aware situations live for all domains. User feeds complete. Preset management with drag-to-reorder. Mobile UX streamlined. Main gap: custom concepts deferred to Phase 6.)
