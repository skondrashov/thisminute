# Skeptic Memory

## Last Review: 2026-03-14 18:45

### Security Review -- User-Added RSS Feeds Backend (2026-03-14 18:45)

Reviewed `src/app.py` (user-feeds endpoints, SSRF protection, rate limiting), `src/database.py` (user_feeds table), `src/pipeline.py` (user feed integration), `src/config.py` (USER_FEED_MAX configs), `tests/test_user_feeds.py` (66 tests).

| # | Finding | Severity | Status |
|---|---------|----------|--------|
| 1 | DNS rebinding TOCTOU: `_is_private_ip()` resolves DNS, then `requests.get()` resolves again later. Attacker DNS can flip between checks. | WARNING | RESOLVED -- builder extracted `_resolve_host()`, fetch connects to resolved IP directly (2026-03-14 18:50) |
| 2 | HTTP redirect to internal: `requests.get()` follows 302 redirects by default. Attacker can redirect to 127.0.0.1 or 169.254.169.254. 1-line fix: `allow_redirects=False`. | WARNING | RESOLVED -- builder added `allow_redirects=False` + redirect rejection (2026-03-14 18:50) |
| 3 | No global cap on user-feed stories across all users in pipeline. 100 users * 20 feeds * 50 stories = 100K stories/cycle. LLM cost: ~$600/day. | WARNING | RESOLVED -- builder added `USER_FEED_TOTAL_MAX_STORIES=500` + kill switch (2026-03-14 18:50) |
| 4 | Rate limit keyed on client-supplied browser_hash, trivially bypassable. | NOTE | Acceptable for v1 |
| 5 | browser_hash is weak identifier, not a security credential. | NOTE | Document limitation |
| 6 | No `SOURCE_ENABLED["user_feeds"]` toggle to disable globally. | NOTE | RESOLVED -- builder added toggle (2026-03-14 18:50) |
| 7 | Tests missing SSRF edge cases (redirects, IPv4-mapped IPv6, hex IPs). | NOTE | Backlog |
| 8 | Input validation thorough (lengths, scheme, allowlists, parameterized SQL). | OK | Ship |
| 9 | Database schema correct (constraints, indexes, defaults). | OK | Ship |
| 10 | Config reasonable defaults, env-overridable. | OK | Ship |

Key insight: The SSRF protection is conceptually correct (resolve hostname, check against private ranges) but has a TOCTOU gap because DNS resolution happens twice -- once for the check, once for the actual fetch. This is a well-known class of vulnerability. The redirect bypass is even easier to exploit and has a trivial fix.

### Targeted Review -- Curious Filtering + Backlog Fixes (2026-03-14 18:30)

Reviewed 5 changes. All rated OK or NOTE. No warnings. Safe to deploy.

| # | Change | Rating | Details |
|---|--------|--------|---------|
| 1 | Curious world filtering (`app.py`, `app.js`) | OK | Null handling correct, pattern mirrors brightSideMode in all 13 integration points, SQL change is additive-only |
| 2 | HTTPS feed URLs (`config.py`) | OK | 4 URLs fixed. CNN HTTP remains (their endpoint) |
| 3 | ACLED_MAX_EVENTS config | OK | Follows NOAA/FIRMS pattern exactly, 3 tests added |
| 4 | Meteoalarm test fix (monotonic clock) | OK | Line 549 fixed correctly |
| 5 | Remaining `0.0` cache values | NOTE | 11 instances in meteoalarm tests still use `_cache["fetched_at"] = 0.0`. Same latent bug. Backlog. |

Key verification: `curiousMode` null handling chain is correct: DB NULL -> Python None -> JSON null -> JS `!hiScore` catches null. Stories without `human_interest_score` are excluded from Curious world, which is the right behavior.

Key difference from `brightSideMode` (intentional, not a bug): `brightSideMode` has a standalone narrative filter (line 1534 of app.js: `if (state.brightSideMode && !worldDomain)`). `curiousMode` does not need this because the Curious preset always has a world domain ("curious" in WORLD_DOMAIN_MAP), so narratives are filtered by domain instead.

### Frontend Quality Review (2026-03-14 06:13)

Reviewed `static/index.html` and `static/js/app.js`. Focused on 12 presets, 14 origin toggles, WORLD_DOMAIN_MAP, size checks, colors.

| # | Finding | Severity | Status |
|---|---------|----------|--------|
| 1 | Missing ACLED origin button in HTML (13 buttons, not 14) | Warning | FIXED 06:16 -- button added |
| 2 | Stale fallback activeOrigins in applyWorldConfig (12 origins, missing meteoalarm + acled) | Warning | FIXED 06:16 -- fallback updated |
| 3 | Sports (#2ea043) vs Markets (#16a34a) color proximity | Note | Both green, marginal distinguishability |
| 4 | Curious preset filters nothing at story level (only narrative domain filter) | Note | RESOLVED 18:20 -- curiousMode added |
| 5 | All 12 presets structurally consistent, WORLD_DOMAIN_MAP correct, size < 14 checks consistent | Positive | Verified |
| 6 | _configToParams handles all 14 origins, no dead origin count checks | Positive | Verified |

Both warnings fixed by builder (06:16). Frontend now has 15 origin buttons (with JMA added at 06:19).

### ACLED + Meteoalarm Adapter Review (2026-03-14 06:05)

Reviewed `src/acled.py` (90 tests), `src/meteoalarm.py` (57 tests), 6 new RSS feeds, Geopolitics + Markets presets. 147 tests pass.

| # | Finding | Severity | Status |
|---|---------|----------|--------|
| 1 | ACLED API key leaked in fetch_json error logs (key in URL query string) | Warning | FIXED 06:08 -- log_url redaction |
| 2 | Meteoalarm 20 sequential HTTP requests (worst case 600s) | Warning | FIXED 06:08 -- time budget (60s) |
| 3 | arXiv/bioRxiv/medRxiv feeds use HTTP not HTTPS | Note | RESOLVED 18:15 |
| 4 | ACLED has no configurable volume cap (hard-codes limit=200) | Note | RESOLVED 18:15 |
| 5 | bioRxiv/medRxiv subject=all adds LLM cost (~$0.50/day) | Note | Monitor |
| 6 | Severity/HI calibration correct in both adapters | Positive | Verified |
| 7 | Edge case handling solid (empty, missing, invalid, dupes) | Positive | Verified |
| 8 | RSS feed tags correct, presets consistent | Positive | Verified |

### Previous: Source Adapter + DRY Refactor Review (2026-03-14 05:25)

Reviewed 4 new source modules (source_utils.py, openaq.py, travel_advisories.py, firms.py), spot-checked DRY refactoring of 7 existing adapters, reviewed pipeline SOURCES loop, checked 10 frontend world presets. Full test suite: 518 passed, 0 failed.

| # | Finding | Severity | Status |
|---|---------|----------|--------|
| 1 | FIRMS CSV unbounded memory (50 MB worst case) | Warning | FIXED -- FIRMS_MAX_BYTES cap |
| 2 | `_nearest_country` brute-force distance | Note | Acceptable |
| 3 | No `test_source_utils.py` | Note | Now has 4 tests |
| 4 | Ambiguous ternary in search_keywords (3 modules) | Note | Correct behavior, cosmetic |
| 5 | OpenAQ limit=100 misses worst stations | Note | Acceptable design tradeoff |
| 6 | NOAA alerts unbounded volume | Warning | FIXED -- NOAA_MAX_ALERTS=150 |
| 7-11 | DRY refactor, pipeline loop, presets, XXE, API keys | Positive | All verified correct |

### Architecture Notes (updated 2026-03-14 18:30)

- 16 source types in SOURCE_ENABLED: rss, gdelt, usgs, noaa, eonet, gdacs, reliefweb, who, launches, openaq, travel, firms, meteoalarm, acled, jma, user_feeds
- 95 RSS feeds in config.py FEEDS list (95 active, 1 commented out)
- 13 structured data API adapters (USGS through JMA), all use pre-built _extraction dicts (zero LLM cost)
- source_utils.py: 6 shared helpers (fetch_json, dedup_list, build_extraction, attach_location, strip_html, polygon_centroid)
- Pipeline SOURCES loop: data-driven, 15 entries replacing ~75 lines of boilerplate
- Frontend: 12 world presets, 15 origin toggle buttons in HTML, 15 origins in JS state, `< 15` checks in 3 locations
- FIRMS: downloads world VIIRS CSV (potentially 50 MB), clusters by 0.5-deg grid cells, conf >= 80 filter
- OpenAQ: limit=100, order_by=lastUpdated, optional API key via X-API-Key header
- Travel advisories: RSS/XML parsing, Level 2+ only, country centroid geocoding
- Launch Library cache: 45 min TTL (updated from 30 min), free tier 15 req/hr (~35% utilization)
- NOAA: NOAA_MAX_ALERTS=150, severity-sorted (Extreme > Severe > Moderate > Minor)
- ACLED: ACLED_MAX_EVENTS=200 (configurable), log_url redaction for credentials
- JMA: single JSON endpoint, 47 prefecture centroids, class10s aggregation, 15-min cache, max 100 alerts
- `RESOLVE_HOURS = 48` in `src/semantic_clusterer.py`
- `MAX_ACTIVE_EVENTS = 200` in `src/registry_manager.py`
- Backfill limit: 256 stories per cycle in `llm_extractor.py`
- `MAX_GDELT_PER_CYCLE = 50` in `src/gdelt.py`
- Narrative caps: 20 news, 10 sports, 10 entertainment, 10 positive, 10 curious
- WORLD_DOMAIN_MAP maps: news, sports, entertainment, positive, curious
- curiousMode: filters stories by human_interest_score >= 6 (CURIOUS_MIN_SCORE), mirrors brightSideMode pattern
- brightSideMode: filters stories by bright_side_score >= 4 (BRIGHT_SIDE_MIN_SCORE)

### What To Check Next Time

- ~~USER FEEDS: 3 warnings fixed~~ -- YES (2026-03-14 18:50): allow_redirects=False, _resolve_host() DNS pinning, USER_FEED_TOTAL_MAX_STORIES=500
- **USER FEEDS: SSRF edge case tests still missing** -- redirect to private IP, IPv4-mapped IPv6 (::ffff:127.0.0.1), hex IP (0x7f000001). Backlog item #14.
- ~~USER FEEDS: SOURCE_ENABLED toggle added~~ -- YES (2026-03-14 18:50): SOURCE_ENABLED["user_feeds"]
- **Sports vs Markets color** -- has Markets green been changed to avoid confusion with Sports green? (backlog)
- **bioRxiv/medRxiv volume** -- how many stories/day are these actually generating? LLM cost impact?
- **Curious world density** -- does CURIOUS_MIN_SCORE=6 produce enough stories to be useful? Monitor post-deploy.
- **Meteoalarm test cleanup** -- have the 11 remaining `_cache["fetched_at"] = 0.0` instances been fixed?
- Are FIRMS fire stories showing up correctly in production? (needs API key)
- Are OpenAQ stories showing up? (needs API key for v3 endpoint)
- Are travel advisory stories clustering correctly? (same country should cluster)
- Check pipeline cycle time with all 15 sources active on e2-micro VM
- Is Launch Library rate limit still at safe utilization? (was 53%, now ~35% with 45-min TTL)
- Has the curious domain produced quality narratives? (5th domain added 2026-03-13)
- Monitor NOAA volume during severe weather season (spring tornado season starting)

### Recurring Patterns to Watch

- **Stale documentation** -- targets, cost estimates, architecture descriptions lag behind code changes
- **Claims without verification** -- always check deployed behavior, not just code
- **Unbounded resource usage** -- FIRMS CSV download and NOAA alerts are both capped now; new sources should always have volume caps
- **Misleading readability** -- the ternary pattern in search_keywords is correct but easy to misread
- **Credential safety** -- log_url pattern now exists for URL-based auth; any new source with URL credentials should use it
- **Convergence works** -- the strategist review/revision cycle produced a materially better document
- **monotonic() != epoch** -- tests that set `fetched_at = 0.0` assume epoch semantics but monotonic() measures uptime. Always use `time.monotonic() - TTL - 1` for cache invalidation in tests.
- **SSRF TOCTOU** -- any feature that validates a URL then fetches it has a DNS rebinding window. The check and the fetch resolve DNS independently. Must either resolve once and pin the IP, or validate post-fetch.
- **HTTP redirects bypass URL validation** -- `requests.get()` follows 30 redirects by default. Always use `allow_redirects=False` when fetching user-supplied URLs, or validate each redirect target.
- **Client-supplied identifiers are not auth** -- browser_hash is a convenience identifier, not a secret. Any rate limiting or access control keyed on client-supplied values is bypassable.
