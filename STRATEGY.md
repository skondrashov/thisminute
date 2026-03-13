# Strategy

## Vision

thisminute.org shows what's happening in the world right now, plotted on a map. Every news story gets a dot. The user decides what to see — not editors. The map IS the filter.

**North star**: Anti-curation. Reduce the gap between "everything happening" and "what the user can find."

## Current Priorities

1. ~~**Event clustering improvements**~~ — DONE (v80). Root cause: clusterer only loaded 500 events into memory, missing 29k+ small events. Fixed with DB-indexed exact signature matching + full-database merge pass. Merged 2,011 duplicate events. Multi-story events went from 6% to 8.8%.
2. **Domain-specific clustering** — Sports/entertainment event_signatures may need domain-aware patterns (match-centric vs person-centric clustering). Clustering already works passably because feed-tag filtering surfaces the right stories, but quality can improve.
3. ~~**Narrative cap enforcement**~~ — DONE. Per-domain caps enforced: news=20, sports/entertainment/positive=10 each. Lowest-ranked excess deactivated after each analysis pass.

### Deprioritized

- **Cheaper model evaluation** — At ~$10.92/day total (verified 2026-03-13), cost is manageable. Prompt caching + pre-LLM dedup are higher ROI with zero risk.
- ~~**Mobile layout polish**~~ — DONE (v84-85). Smooth drag interpolation with velocity snapping, info panel swipe-to-close, auto-minimize on situation select, filter indicator, prefers-reduced-motion support.
- **Space/Internet tile scaling** — Nice-to-have. Does not serve the directive's diversity goal. Backlog.

## Completed

- [x] RSS scraping (74 feeds, 8 categories, tagged)
- [x] LLM extraction via Haiku (15 fields, batches of 8)
- [x] Signature-based event clustering
- [x] Event registry with map labels
- [x] Situation synthesis via Sonnet
- [x] Globe projection (MapLibre 5.x)
- [x] Orthogonal filter system (topic, source, time, sentiment, situation, location)
- [x] Light/dark mode
- [x] Trending concept detection
- [x] Shareable filter URLs
- [x] Deployed on GCP (thisminute.org live)
- [x] GDELT volume stabilized (SAMPLE_RATE=0.003, MAX_PER_CYCLE=50 cap)
- [x] Cost model recalculated (~$10.92/day verified 2026-03-13, down from $14-16 estimate)

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
- [x] 61 Playwright tests passing

### Phase 2: Feed Expansion by World -- COMPLETE (v71)

- [x] Sports feeds: 7 new dedicated feeds (ESPN, ESPN Soccer, ESPNcricinfo, Sky Sports, Sportstar, Autosport, Rugby World). Total: 10 sports sources.
- [x] Feed tagging system: all 74 feeds tagged (news, sports, entertainment, positive, tech, science, business, health). `FEED_TAG_MAP` + `/api/feed-tags` endpoint.
- [x] Sports world uses feed tags instead of keyword matching (skeptic Issue 7 resolved)
- [x] Prompt caching implemented (~$1.22/day savings)
- [x] Entertainment feeds: 9 new feeds (Variety, Hollywood Reporter, Deadline, Rolling Stone, Billboard, Pitchfork, NME, Soompi, Bollywood Hungama). Total: 15 entertainment sources.
- [x] Entertainment world preset (purple, `feedTags: ["entertainment"]`)
- [x] Economist cost check after feeds are live for 24h — verified 2026-03-13: ~$10.92/day

### Phase 3: World-Aware Extraction — IN PROGRESS

- [x] **World-aware situation synthesis** — Per-domain event queries + domain-specific Sonnet prompts. Sports, entertainment, and positive situations now generated. API limit raised to 60.
- [ ] Sports clustering (match/tournament, not just event_signature)
- [ ] Entertainment clustering (person/production-centric)
- [ ] "Human interest" scoring for trivial world

### Phase 4: Deep Customizability

- [ ] User-added RSS feeds (paste URL -> source)
- [ ] Custom topic/concept creation
- [ ] Shareable world presets via URL

### Phase 5: Feedback Loop — STARTED

- [ ] Usage analytics per world
- [x] Explicit user feedback — `/api/feedback` endpoint live (v114), `user_feedback` table, feedback agent (`agents/feedback.md`), rate limiting (5/min)
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
- [x] Testing: fixed all 63 Playwright tests (root cause: parseInt on comma-formatted numbers)
- [x] v114: Feedback API (`/api/feedback`), proximity hover polish, mobile reticle, feed zoom scaling, crosshair cursor, WAL ownership fix, server-side rate limiting
- [ ] Space/internet tile scaling at globe zoom

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
- The `MAX_NARRATIVES = 20` cap becomes per-domain (20 news + 10 sports + 10 entertainment + 10 positive = 50 max total). Sports/entertainment/positive get fewer because they'll have lower volume.

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
| World-aware situations                  | B+ (all 4 domains generating situations, quality improving) |
| User-configurable feeds                 | F                                                           |
| Custom concepts                         | F                                                           |

**Overall: A-** (World-aware situations now live for all 4 domains. Main gaps: user-configurable feeds and custom concepts.)
