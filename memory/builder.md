# Builder Memory

## Domain Event Filtering (2026-03-13)

- Entertainment events get heavy cross-coverage from general news sources (BBC, CNN, NYT all cover Oscars). A 50% entertainment-source threshold is too strict. Current threshold: 15% source ratio + topic-keyword secondary signal.
- Positive events: `bright_side_score >= 3` at 15% ratio works better than the original >= 4 at 30%. Also added source-based signal for positive-tagged feeds.
- Sports at 50% threshold works fine because sports sources dominate sports events (ESPN, BBC Sport, etc. are the primary reporters).
- The LLM prompt is the final quality gate -- it rejects junk/vague situations even if the event filter is permissive. Better to be too permissive on event filtering and let Sonnet decide quality.
- Topic-based matching uses LIKE against the JSON topics string. Requires >= 2 matching stories to avoid false positives.

## Deploy Script Notes

- `src/js/` is excluded from repo (filtered in `make_tarball()` and not committed). The pre-built `static/js/app.js` is what gets deployed.
- `deploy()` now conditionally runs `npm run build` only if `src/js/` exists. If missing, it skips the build and uses the pre-built bundle.
- `make_tarball()` explicitly excludes `src/js` from the tarball via the `dirs[:]` filter.

## Sports Clustering (2026-03-13)

- Sports event_signatures fragment badly when match-result-centric ("Wolves Beat Liverpool"). Fixed by adding sports-specific prompt guidance to generate tournament-centric signatures ("2026 Premier League").
- Three-part fix: (1) LLM prompt guidance, (2) post-clustering tournament merge pass, (3) fuzzy match boost for shared tournaments.
- Tournament detection uses 25+ regex patterns in `_SPORTS_TOURNAMENT_PATTERNS` covering all major sports.
- Sports events detected via feed source tags (>= 50% from `_SPORTS_SOURCES`). News events are never touched by sports merge logic.
- Key thresholds: `SPORTS_MERGE_THRESHOLD = 0.28` (lower than normal 0.35-0.45), tournament boost = +0.15 on fuzzy score.
- The prompt change is the most impactful: it changes how NEW signatures are generated. The merge pass fixes existing fragmented events.
- Tournament patterns may need expansion as new sports/competitions appear. Easy to add new patterns to the list.

## Entertainment Clustering (2026-03-13)

- Entertainment event_signatures fragment by individual news item ("Spider-Man 4 Casting" vs "Spider-Man 4 Filming"). Fixed by adding entertainment-specific prompt guidance to generate production/franchise-centric signatures ("Spider-Man 4 Production").
- Three-part fix (mirrors sports): (1) LLM prompt guidance, (2) post-clustering entertainment merge pass, (3) fuzzy match boost for shared entertainment keys.
- Entertainment detection uses 30% source ratio (lower than sports' 50%) because entertainment events get heavy cross-coverage from general news outlets (BBC, CNN, NYT all cover Oscars).
- Entertainment patterns cover: award shows (12 types), film festivals (10 types), movie franchises (12+), TV shows (6+), music tours (pattern-based), K-pop groups (4+), Broadway/West End, Bollywood.
- Key thresholds: `ENTERTAINMENT_MERGE_THRESHOLD = 0.28`, `ENTERTAINMENT_SOURCE_RATIO = 0.3`, entertainment boost = +0.15 on fuzzy score.
- The prompt change is most impactful: it changes how NEW signatures are generated. The merge pass fixes existing fragmented events.
- Cross-domain isolation verified: entertainment patterns don't match sports signatures and vice versa.

## Entertainment Pattern Disambiguation (2026-03-13)

- Patterns for common English words (succession, batman, wednesday, the bear) MUST require franchise/show-specific context words. Bare word matching causes false positives on news signatures.
- Greedy capture groups like `\w[\w\s]*?` after franchise names (star wars, harry potter) match nonsense -- use explicit word lists instead.
- Allow one optional intervening word between franchise name and context word (e.g., "Star Wars New Trilogy" needs `(?:\w+\s+)?` before `trilogy`).
- The `_best_event_match()` boost is domain-gated: sports boost only for confirmed sports events, entertainment boost only for confirmed entertainment events. Pre-compute domain sets in the caller via batch queries.

## Sports Narrative Prompt -- Cross-Sport Contamination (2026-03-13)

- The clustering layer (semantic_clusterer.py) correctly separates events by sport -- rugby events are separate from cricket events. But the Sonnet narrative prompt was too loose, grouping events from different sports into one situation.
- Root cause: the sports prompt said "a tournament, a season, a transfer saga" but never said "ONE sport per situation." Sonnet interpreted this as "group big sports events together" and created a cricket situation containing rugby, football, tennis, MMA, and motorsport events.
- Fix: added explicit "CRITICAL -- ONE SPORT PER SITUATION" guidance to `DOMAIN_PROMPTS["sports"]["guidance"]`. Also added cross-sport contamination to `examples_bad`.
- Key lesson: domain-specific prompts need EXPLICIT exclusion rules, not just good examples. Sonnet follows examples but generalizes liberally -- if you don't say "don't mix sports," it will mix them when the events seem related (e.g., both are "big international competitions").
- The fix takes effect on the next narrative analysis cycle (every 1-2 hours). Existing contaminated narratives should self-correct as Sonnet reassigns events.

## Curious/Human Interest Domain (2026-03-13)

- human_interest_score (1-10) is DIFFERENT from bright_side_score. Human interest = "this is fascinating/engaging." Bright side = "this is good news." A gripping war crime investigation is high human-interest but low bright-side. A routine charity donation is high bright-side but low human-interest.
- Curious domain uses human_interest_score >= 5 at 15% ratio (same architecture as positive domain's bright_side_score approach).
- Score 5 cutoff is appropriate: 5-6 in the rubric is "engaging -- surprising twist, dramatic confrontation, compelling human drama, odd science." Reserve 7+ for genuinely remarkable stories.
- The curious domain is source-agnostic (DOMAIN_FEED_TAGS = None). Human interest stories come from any source.
- The Sonnet prompt emphasizes "you won't believe this" factor and explicitly differentiates from positive domain. Rejects vague buckets like "human interest stories" and "viral content."
- Cap: 10 situations (same as sports/entertainment/positive).
- Phase 3 is now COMPLETE: all 5 domains generating (news, sports, entertainment, positive, curious).

## Key Thresholds (Updated)

| Domain | Source ratio | Extra signal |
|--------|-------------|--------------|
| News | 0.5 | None |
| Sports | 0.5 | None |
| Entertainment | 0.15 | Topic keywords (film, oscars, broadway, etc.) |
| Positive | N/A | bright_side_score >= 3 at 15% ratio OR 30% positive-source ratio |
| Curious | N/A | human_interest_score >= 5 at 15% ratio |

## USGS Earthquake Integration (2026-03-14)

- First "statistical inference feed" -- sensor-derived events, not news articles.
- `source_type` column distinguishes 'reported' (news) from 'inferred' (sensor data like USGS). Default is 'reported' for backward compatibility.
- USGS stories skip LLM extraction entirely. All structured data (event_signature, severity, topics, location) comes from the USGS API. Pre-built `_extraction` dict is attached to the story dict and stored directly by pipeline.
- The `_extraction` key is popped from the story dict before `insert_story()` and stored via `store_extraction()` after the story is inserted. Then `extraction_status` is set to 'done'.
- Two feeds: significant earthquakes (hourly, typically 0-2 events) and M4.5+ (daily, typically 5-15 events). Very low volume compared to RSS (~3,500/day) and GDELT (~1,700/day).
- USGS stories get up to 50 slots in `get_stories()` alongside the RSS/GDELT 50/50 balance. Since volume is tiny, this doesn't affect the balance.
- Frontend origin buttons now include RSS, GDELT, USGS, NOAA (and potentially more as new adapters ship). Origin filtering logic updated accordingly.
- `_mag_to_severity()` maps magnitude to 1-5 scale. `_mag_to_human_interest()` maps to 1-10 scale.
- Event signatures use "YEAR Region Earthquake" format for clustering.
- Config: `USGS_SIGNIFICANT_URL`, `USGS_4_5_URL`, `USGS_MIN_MAGNITUDE` (default 4.5).
- Pattern for adding new inference feeds: create adapter module, add `_extraction` dict to skip LLM, add origin button, update origin filtering constants.

## NOAA Weather Alerts Integration (2026-03-14)

- Second "statistical inference feed" -- government-issued weather alerts, US-only.
- NOAA API at `https://api.weather.gov/alerts/active` returns GeoJSON. No API key needed, just User-Agent header: `(thisminute.org, contact@thisminute.org)`.
- NOAA returns polygon geometries (affected areas), not points. We calculate the centroid (average of all coordinates in the outer ring) for the story's lat/lon.
- Severity mapping: Minor=1, Moderate=2, Severe=3, Extreme=4. Human interest: Minor=2, Moderate=4, Severe=6, Extreme=8.
- Category: "disaster" for severity >= 3, "weather" for severity < 3.
- Event signatures use "YEAR Region EventType" format (e.g., "2026 TX Tornado"). Strips "Warning"/"Watch"/"Advisory" from event type for cleaner signatures.
- `properties.id` is the dedup key (it's a full URL like `https://api.weather.gov/alerts/...`).
- Event-specific concepts mapped from event type: tornado, flood, hurricane, winter storm, wildfire, heat wave, etc.
- Follows exact same patterns as USGS: stdlib only, pre-built `_extraction` dict, skips LLM extraction.

## Config-Driven Source Toggle System (2026-03-14)

- `SOURCE_ENABLED` dict in `src/config.py` with boolean for each source: rss, gdelt, usgs, noaa.
- All default to True. Can be disabled via environment variables: `SOURCE_RSS_ENABLED=false`, etc.
- Pipeline checks `SOURCE_ENABLED[source]` before calling each scraper. Disabled sources log a skip message and continue.
- This replaces hard-coded source calls in pipeline.py with a config-driven approach.

## World Presets (2026-03-14)

- 12 built-in presets: news, sports, entertainment, positive, science, tech, curious, weather, crisis, travel, geopolitics, markets
- Science: `feedTags: ["science"]`, color `#00b4d8`, icon microscope. Shows science-tagged RSS + all inference sources. No narrative domain mapping (science feeds grouped under "news" domain in backend).
- Tech: `feedTags: ["tech"]`, color `#e63946`, icon laptop. Shows tech-tagged RSS + all inference sources. No narrative domain mapping (same as science).
- Curious: No feedTags (curious uses ALL feeds). Color `#ff6f61`, icon puzzle. HAS narrative domain mapping (`WORLD_DOMAIN_MAP.curious = "curious"`). Situations panel shows only curious-domain narratives. Known UX limitation: map shows ALL stories but sidebar shows only curious situations.
- Backend narrative domains (5): news, sports, entertainment, positive, curious. There are NO science or tech narrative domains.
- `WORLD_DOMAIN_MAP` controls situation filtering: when a world has a domain mapping, `computeFilteredState()` filters narratives to only that domain. Worlds without mapping show all-domain situations.
- Composite presets (weather, crisis, travel, geopolitics, markets) use SUBSET activeOrigins arrays to filter to relevant data sources. Weather: rss + noaa + eonet + usgs + gdacs + firms + meteoalarm. Crisis: rss + usgs + noaa + eonet + gdacs + reliefweb + who + travel + firms + meteoalarm + acled. Travel: rss + travel + noaa + gdacs + who + meteoalarm + acled. Geopolitics: rss + gdelt + acled + travel. Markets: rss + gdelt (with feedTags: business). These subsets trigger origin filtering automatically (size < 14).
- Colors/icons must be updated in at least 3 places: `WORLD_PRESETS`, `WORLD_ICONS`, and HTML world-btn elements in index.html. Also `_DOMAIN_HIGHLIGHT_COLORS` if the preset has a narrative domain mapping.
- Cache-bust version must be bumped in index.html on every change (both CSS and JS links).

## ProMED Disease Alerts (2026-03-14)

- ProMED (promedmail.org) does NOT have a working public RSS feed as of 2026-03-14. Tried: /feed/, /feed, /promed-posts/feed/, /rss/. All return 404. The FeedBurner mirror (feeds.feedburner.com/ProMED) exists but has 0 items since 2018.
- Cannot add to FEEDS list without a working RSS URL. Would need a dedicated HTML scraper to parse their web interface, which is a larger effort.
- WHO DON feed (already integrated) partially covers the same disease outbreak space.

## Volume Caps on Data Source Adapters (2026-03-14)

- FIRMS has two caps: `FIRMS_MAX_BYTES` (10 MB) limits HTTP response size in `_fetch_firms_csv()`, and `FIRMS_MAX_ROWS` (5000) limits high-confidence detections in `_parse_detections()`. Both env-overridable.
- NOAA has `NOAA_MAX_ALERTS` (150) cap. Alerts are sorted by severity (Extreme > Severe > Moderate > Minor) before capping so the most critical alerts are always processed.
- Pattern: volume caps should be config-driven with env-var overrides, and should log warnings when triggered. Default values should be generous enough for normal operation but prevent worst-case spikes.

## Project Conventions

- `flush=True` on all prints (Windows subprocess buffers stdout)
- Avoid unicode in print statements (cp1252 encoding on Windows)
- SQLite with WAL mode and busy_timeout=10000
- Always add columns with DEFAULT values in migrations
- Bump `?v=N` in index.html on every deploy
- 16 data source types in SOURCE_ENABLED: rss, gdelt, usgs, noaa, eonet, gdacs, reliefweb, who, launches, openaq, travel, firms, meteoalarm, acled, jma, user_feeds
- 15 DB tables (added user_feeds for user-configurable RSS)
- Pattern for adding new inference feeds: create adapter module in `src/`, add config URL, add `_extraction` dict to skip LLM, add origin button in index.html, update origin filtering constants in app.js, add to SOURCE_ENABLED in config.py, gate in pipeline.py
- Shared source adapter utilities live in `src/source_utils.py`: `fetch_json()`, `dedup_list()`, `build_extraction()`, `attach_location()`, `strip_html()`, `polygon_centroid()`. All 8 adapter modules use these helpers.
- Pipeline source scraping uses a data-driven `SOURCES` list + loop instead of per-source if/try/except blocks. To add a new source: add entry to `SOURCES` list in `pipeline.py`, add to `SOURCE_ENABLED` in `config.py`, create adapter module using `source_utils` helpers.
- Adapter modules keep their `_fetch_*` function names as thin wrappers around `source_utils.fetch_json()` -- this preserves test mock targets. Tests mock `src.usgs._fetch_feed`, `src.noaa._fetch_alerts`, etc.
- RSS/XML fetchers (GDACS RSS, WHO DON RSS) keep their own fetch since XML parsing differs from JSON. GDACS `_fetch_geojson` also kept since it returns None (not []) on failure.

## OpenAQ Air Quality Integration (2026-03-14)

- 10th data source adapter. Uses OpenAQ v2 API (`/v2/latest`) -- no auth required, optional API key via `OPENAQ_API_KEY`.
- Threshold-based ingestion: only creates stories for locations exceeding WHO/EPA thresholds (PM2.5 > 35, PM10 > 45, O3 > 100, NO2 > 25, SO2 > 40 ug/m3).
- Severity uses ratio-based mapping (concentration / threshold). Human interest also ratio-based 1-10.
- Handles both v2 and v3 API response formats in parsing logic. Currently uses v2 (no auth, `key="results"`).
- Event signatures: "YEAR LocationName Air Quality". Category: "health". origin: "openaq".
- Dedup by location ID ("openaq:{location}"). Mock target: `src.openaq._fetch_openaq`.
- Frontend: origin count now 10 (was 9). `size < 10` in origin filtering checks. All world preset activeOrigins arrays include "openaq".
- Cache-bust version bumped to `?v=132`.
- 53 tests in `tests/test_openaq.py`.

## US State Dept Travel Advisories Integration (2026-03-14)

- 11th data source adapter. Uses State Department RSS feed at `travel.state.gov/content/travel/en/traveladvisories/traveladvisories.xml` -- no auth.
- RSS/XML parsing using `xml.etree.ElementTree` (same pattern as `src/who.py`).
- Level filtering: Only Level 2+ advisories ingested. Level 1 (Exercise Normal Precautions) excluded to reduce noise.
- Severity mapping: Level 1=1, Level 2=2, Level 3=3, Level 4=5 (skips 4 to emphasize "Do Not Travel").
- Human interest: Level 1=2, Level 2=4, Level 3=6, Level 4=9.
- Country parsing from title format "CountryName - Travel Advisory (Level N: Label)".
- Geocoding via `country_centroids.py`. Threat concepts extracted from description keywords.
- Event signatures: "YEAR CountryName Travel Advisory". Category: "politics". origin: "travel".
- Dedup by advisory URL. Mock target: `src.travel_advisories._fetch_advisory_rss`.
- Frontend: origin count now 11 (was 10). `size < 11` in origin filtering checks. All world preset activeOrigins arrays include "travel".
- Cache-bust version bumped to `?v=133`.
- 52 tests in `tests/test_travel_advisories.py`.

## NASA FIRMS Fire Detection Integration (2026-03-14)

- 12th data source adapter. Uses NASA FIRMS API for satellite-derived active fire detection data (VIIRS instrument).
- CSV-based API at `https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/VIIRS_SNPP_NRT/world/1`. Requires free `FIRMS_API_KEY` from NASA Earthdata.
- Parsed with stdlib `csv.DictReader` + `io.StringIO`. No JSON endpoint used.
- Confidence filtering: only detections with confidence >= 80 (or "high"/"nominal" string values). Maps string confidence to numeric: high=95, nominal=80, low=30.
- Grid-based clustering: rounds lat/lon to 0.5-degree cells (~55km). Reduces thousands of raw detections to ~20-100 fire event stories per cycle.
- Severity mapping from cluster size: 1-2=1, 3-10=2, 11-50=3, 51-200=4, 200+=5.
- Human interest mapping from cluster size: 1-2=2, 3-5=3, 6-10=4, 11-20=5, 21-50=6, 51-100=7, 101-200=8, 201-500=9, 500+=10.
- Country mapping via `country_centroids.py` `_nearest_country()` function. Finds nearest country within 30 degrees. Falls back to coordinate-based names.
- Event signatures: "YEAR CountryName Wildfire" or "YEAR Fire N34W118" (coordinate-based fallback).
- Category: "disaster". Concepts: ["wildfire", "fire", "environment", "climate"]. origin: "firms". source_type: "inferred".
- Dedup URL: `https://firms.modaps.eosdis.nasa.gov/fire/{date}/{grid_lat}/{grid_lon}` -- daily + grid cell uniqueness.
- Mock target: `src.firms._fetch_firms_csv`. Gracefully returns [] if no API key.
- Frontend: origin count now 12 (was 11). `size < 12` in origin filtering checks. All world preset activeOrigins arrays include "firms". Weather and Crisis composite presets include "firms".
- Cache-bust version bumped to `?v=135`.
- 62 tests in `tests/test_firms.py`.

## Meteoalarm European Weather Alerts Integration (2026-03-14)

- 13th data source adapter. Uses Meteoalarm API for European severe weather alerts.
- Public JSON API at `https://feeds.meteoalarm.org/api/v1/warnings/feeds-{country}` -- no auth required.
- Returns CAP-format warnings. Key fields: `alert.info[].severity`, `alert.info[].parameter[].awareness_level` (1-4 scale with color), `alert.info[].parameter[].awareness_type` (event category number), `alert.info[].area[].areaDesc` (region name).
- No lat/lon coordinates in API response -- only area names and EMMA_ID/geocode identifiers. Uses country-level centroids for map placement (`geocode_confidence=0.6`).
- Multilingual: alerts come in multiple languages. Adapter selects English (`en*`) info blocks, falls back to first info block.
- Green alerts filtered: awareness_level=1 (green/minor) alerts are skipped to reduce volume. Only yellow (2), orange (3), and red (4) alerts ingested.
- 20 high-population European countries fetched: DE, FR, IT, ES, UK, PL, NL, BE, AT, CH, SE, NO, FI, DK, PT, CZ, RO, HU, GR, IE.
- 15-minute cache (`METEOALARM_CACHE_SECONDS=900`). 200 alert cap (`METEOALARM_MAX_ALERTS`), sorted by severity (most severe kept).
- awareness_type maps to weather concepts: 1=wind/storm, 2=snow/ice, 3=thunderstorm, 4=fog, 5=heat wave, 6=cold wave, 7=avalanche, 8=flood, 9=wildfire, 10=rain.
- Event signatures: "YEAR Region EventType". Strips color prefix (Yellow/Orange/Red) and Warning/Watch/Advisory suffixes.
- Category: "weather" for severity < 3, "disaster" for severity >= 3. origin: "meteoalarm". source_type: "inferred".
- Dedup by alert uuid (primary) or alert identifier (fallback). Mock target: `src.meteoalarm._fetch_country_warnings`.
- Frontend: origin count now 13 (was 12). `size < 13` in origin filtering checks. All world preset activeOrigins arrays include "meteoalarm". Weather, Crisis, and Travel composite presets include "meteoalarm".
- Cache-bust version bumped to `?v=136`.
- 57 tests in `tests/test_meteoalarm.py`.

## Launch Library Cache TTL (2026-03-14)

- `LAUNCHES_CACHE_SECONDS` default changed from 1800 (30 min) to 2700 (45 min). Reduces free-tier rate limit utilization from 53% to ~35%. Already env-overridable.

## ACLED Conflict Data Integration (2026-03-14)

- 14th data source adapter. Uses ACLED API for armed conflict events (battles, explosions, violence against civilians, protests, riots, strategic developments).
- API at `https://api.acleddata.com/acled/read`. Requires `ACLED_API_KEY` + `ACLED_EMAIL` env vars (free registration at developer.acleddata.com).
- Fetches last 7 days of events, limit 200 per cycle. Uses `event_date_where=>=` parameter.
- Severity mapping combines event_type base + fatality escalation: Battles base=3, fatalities>=20 -> severity 5. Protests base=1. 100+ fatalities always = severity 5.
- Human interest: fatality-based escalation 1-10. 100+ fatalities = 10.
- Categories: "conflict" for Battles/Explosions/Violence against civilians/Riots. "politics" for Protests/Strategic developments.
- Sentiment varies: "negative" (violence), "mixed" (protests), "neutral" (strategic developments).
- Event signatures: "YEAR Country EventType" format. Slashes cleaned from event types (e.g., "Explosions" not "Explosions/Remote violence").
- Concepts: ["conflict", "violence"] base + event-type-specific extras (battle, explosion, protest, riot, political, etc.).
- Dedup by ACLED `data_id` field. URL: `https://acleddata.com/data/{data_id}`.
- Graceful skip if ACLED_API_KEY or ACLED_EMAIL not set (same pattern as FIRMS).
- Mock target: `src.acled._fetch_acled`. origin: "acled". source_type: "inferred".
- Frontend: origin count now 14 (was 13). `size < 14` in origin filtering checks. All full-origin preset arrays include "acled". Crisis and Travel composite presets include "acled".
- Cache-bust version bumped to `?v=137`.
- 90 tests in `tests/test_acled.py`.

## Geopolitics + Markets World Presets (2026-03-14)

- Geopolitics preset: color `#6b7280` (military grey), icon globe. Composite origins: rss + gdelt + acled + travel. Shows conflict, political, and geopolitical news.
- Markets preset: color `#16a34a` (finance green), icon chart. Composite origins: rss + gdelt. feedTags: `["business"]`. Shows business/finance RSS stories.
- 15 SOURCE_ENABLED entries: rss, gdelt, usgs, noaa, eonet, gdacs, reliefweb, who, launches, openaq, travel, firms, meteoalarm, acled, jma.
- 12 built-in world presets: news, sports, entertainment, positive, science, tech, curious, weather, crisis, travel, geopolitics, markets.

## RSS Feed Additions (2026-03-14)

- Added 6 feeds (90 -> 95 active): arXiv AI, arXiv CS, bioRxiv, medRxiv, IGN, Oddity Central.
- arXiv feeds use `http://arxiv.org/rss/{category}` -- valid RSS 2.0 with arxiv namespace.
- bioRxiv/medRxiv use `http://connect.{bio|med}rxiv.org/{bio|med}rxiv_xml.php?subject=all` -- RDF/RSS 1.0 format. medRxiv has UTF-8 BOM but feedparser handles it.
- IGN at `https://feeds.ign.com/ign/all` -- standard RSS 2.0.
- Oddity Central at `https://www.odditycentral.com/feed` -- standard WordPress RSS 2.0.
- FEED_TAG_MAP auto-builds from FEEDS list, no manual updates needed for tag mapping.
- These are pure config additions -- no new adapter code, no pipeline changes, no frontend changes.

## Credential Redaction in fetch_json (2026-03-14)

- `source_utils.fetch_json()` has a `log_url` parameter. When provided, this URL is logged instead of the real URL on errors. Use this when the real URL contains credentials (API keys, emails, etc.).
- ACLED is the first adapter to use this -- it passes `log_url` with `key=REDACTED&email=REDACTED`.
- Pattern: if an API requires credentials in query params and uses `fetch_json()`, always pass a `log_url` to avoid leaking secrets to logs.

## JMA Weather Warnings Integration (2026-03-14)

- 15th data source adapter. Uses JMA bosai API for Japanese weather warnings.
- Single JSON endpoint `https://www.jma.go.jp/bosai/warning/data/warning/map.json` returns all active warnings nationwide. No per-prefecture loop needed (unlike Meteoalarm's per-country approach).
- Area name resolution via `https://www.jma.go.jp/bosai/common/const/area.json` -- has English names (`enName` field), cached 24 hours.
- Warning codes are JMA-standard numeric codes (02-32). Three levels: special_warning (codes 04,08,17; severity 5), warning (codes 03,05,06,09,12,16,18; severity 3), advisory (remaining; severity 1-2).
- Low-value advisories filtered: codes 21 (Dry Air), 24 (Dense Fog), 26 (Low Temperature), 32 (Frost).
- No lat/lon in API response. Uses 47 hardcoded prefecture centroids keyed by first 2 digits of area code. geocode_confidence=0.7.
- Aggregated at class10s (regional) level, not class20s (city) level. The map.json areaTypes[0] is class10s, areaTypes[1] is class20s. Only highest-severity warning per region reported.
- Japanese status strings: "\u767a\u8868" (hatsu-hyou = issued/active), "\u7d99\u7d9a" (keizoku = continuing). "\u89e3\u9664" (kaijo = lifted/canceled) is inactive.
- 15-minute cache (same as Meteoalarm). Max 100 alerts, sorted by severity.
- Event signatures: "YEAR AreaName WarningType" (strips Warning/Advisory/Special Warning suffixes).
- Category: "disaster" for severity >= 3, "weather" for severity < 3. origin: "jma". source_type: "inferred".
- Dedup by area_code:warning_code combination. Mock target: `src.jma._fetch_warnings`.
- Frontend: origin count now 15 (was 14). `size < 15` in origin filtering checks. All full-origin preset arrays include "jma". Weather, Crisis, and Travel composite presets include "jma".
- Cache-bust version bumped to `?v=139`.
- 66 tests in `tests/test_jma.py`.

## Meteoalarm Cache Test Fix (2026-03-14)

- `time.monotonic()` starts from 0 at boot. Setting `_cache["fetched_at"] = 0.0` to simulate "expired" is wrong on freshly booted machines where `monotonic()` < cache TTL.
- Correct pattern: `_cache["fetched_at"] = time.monotonic() - (TTL + buffer)` to guarantee expiry regardless of uptime.
- General lesson: never use absolute values (0.0, epoch timestamps) with `time.monotonic()`. Always use relative offsets from the current monotonic time.

## User Feeds SSRF Security Fixes (2026-03-14)

- **Redirect SSRF bypass:** `requests.get()` follows redirects by default. Added `allow_redirects=False` and reject 3xx responses. This prevents attackers from 302-redirecting to internal IPs (127.0.0.1, 169.254.169.254).
- **DNS rebinding TOCTOU:** Extracted `_resolve_host()` that returns `(is_private, resolved_ip)`. The HTTP fetch connects to the resolved IP directly with a `Host` header, eliminating the TOCTOU gap where DNS could rebind between validation and fetch.
- **Global volume cap:** `USER_FEED_TOTAL_MAX_STORIES=500` caps aggregate user-feed stories per pipeline cycle. `SOURCE_ENABLED["user_feeds"]` provides a kill switch. Without these, 100 users * 20 feeds * 50 stories = 100K stories/cycle = ~$600/day in LLM costs.
- `_validate_feed_url()` now returns a tuple `(error, resolved_ip, hostname)` instead of just `error`. Callers must destructure.
- Pattern: always resolve DNS once and reuse the result for both validation and the HTTP fetch. Never validate a hostname and then let a library re-resolve it.

## Meteoalarm Time Budget (2026-03-14)

- `METEOALARM_TIMEOUT=5` (per-request, was using global 30s). `METEOALARM_TOTAL_BUDGET=60` (total for all 20 countries). Both env-overridable.
- Worst case reduced from 600s to 60s. Normal operation: <10s total.
- Pattern for sequential multi-request adapters: always set a per-request timeout lower than the global default, and add a total time budget with early exit. Log which resources were skipped.

## User Feeds Frontend UI (2026-03-15)

- Frontend uses modal dialog pattern (same as feedback-dialog and world-save-dialog). Modal overlay with `.visible` class toggle.
- `_getBrowserHash()` reused from feedback system for user identity. Hash is based on user agent + screen dimensions.
- Three API endpoints consumed: `POST /api/user-feeds` (add), `GET /api/user-feeds?hash=X` (list), `DELETE /api/user-feeds/{id}?hash=X` (remove).
- Feed status shown via colored dots: green (active/fetched), yellow (pending first fetch), red (error with `last_error`).
- Tag dropdown matches `_VALID_FEED_TAGS` in `app.py`: news, sports, entertainment, positive, tech, science, business, health.
- Feed count badge shows "N/20" matching `USER_FEED_MAX=20` config. API enforces this limit server-side.
- `_escHtml()` helper uses DOM text node for safe HTML escaping (no regex). Used for feed titles and URLs.
- All CSS uses CSS variables (--bg-primary, --text-primary, etc.) for theme compatibility. Light mode overrides added for buttons and tag badges.
- Mobile responsive: add form wraps (URL input full-width, select and button below), panel width constrained to 90%/380px.
- Cache-bust version bumped to `?v=140`.

## WCAG AA Contrast Compliance (2026-03-15)

- All 12 world button active-state CSS colors pass WCAG AA (4.5:1) with white text in both dark and light mode.
- The WORLD_PRESETS color values in app.js (e.g., positive `#f5a623`) are the BRIGHT brand colors used for dots, highlights, and tour labels. These are NOT the button background colors.
- The CSS active-state backgrounds (style.css lines 443-502) use independently darkened variants (e.g., positive `#a06800`, science `#0077a8`).
- When adding new world presets: always verify the CSS active-state background has >= 4.5:1 contrast with white. Use the WCAG relative luminance formula: max luminance for 4.5:1 = 0.1833.
- Minimum contrast in current set: sports `#218838` at 4.52:1.

## Onboarding Sequencing Pattern (2026-03-15)

- First-time visitors: `startWorldTour()` fires first, sets `_worldTourActive = true` synchronously.
- The `if (!_worldTourActive)` guard in init prevents `showOnboardingHint()` and mobile sheet peek from firing during tour.
- `stopWorldTour()` fires deferred onboarding: `showOnboardingHint()` immediately + mobile sheet peek with 2s delay.
- Three conditions for tour: no `tm_world_tour_seen`, no `tm_last_visit`, no `tm_default_world`, no URL hash.
- `captureFirstVisitFlag()` must be called BEFORE `loadStateFromURL()` (which sets `tm_last_visit`).

## Dominance-Tinted Dot Colors (2026-03-15)

- Replaced circular HSL averaging with dominance-ratio RGB lerp in `_blendLocationColors()`.
- Old approach: weighted circular average of hue values across all domains at a location. Produced misleading intermediate colors (e.g., violence red + power blue = purple).
- New approach: find dominant domain (highest story count), calculate ratio = dominant_count / total, lerp from base color to domain color.
- Theme-aware base colors: dark mode = white (#ffffff, dots look like city lights), light mode = medium gray (#6e7681, avoids vanishing on light backgrounds).
- Replaced HSL infrastructure (_hexToHSL, _hslToHex, _domainHSL, _fallbackHSL) with RGB equivalents (_hexToRGB, _rgbToHex, _domainRGB, _fallbackRGB).
- Added re-blend call in `toggleTheme()` so dot colors update with the correct base on theme switch.
- Country polygon fills (updateCountryPolygons) were already dominant-domain based -- unchanged.
- `blended_color` property name preserved -- no MapLibre layer changes needed.
- Light mode gray value (#6e7681) may need visual tuning.
- Cache-bust version bumped to ?v=144.

## SEO/Social Shareability (2026-03-15)

- Meta description (137 chars): "Real-time global news map. Every story gets a dot. 95 sources, 12 world views. You decide what matters."
- OG image at `/static/og-image.png` (1200x630). Generated via Pillow -- dark theme with colored dots, branding, stats subtitle.
- Twitter card upgraded from `summary` to `summary_large_image` for large preview on Twitter/X.
- `<link rel="canonical" href="https://thisminute.org">` added.
- `og:image`, `og:image:width`, `og:image:height`, `og:locale`, `twitter:image` all added.
- Dynamic OG in `app.py` now replaces `og:url` with situation-specific URL for `/?sit=N` deep links.
- `robots.txt` served at `/robots.txt` via dedicated FastAPI route (not via `/static/` mount).
- `sitemap.xml` served at `/sitemap.xml` -- minimal single-entry for SPA homepage.
- String replacements in `app.py` index() must match the exact text in `index.html`. If description text changes, update BOTH files.
- Cache-bust version bumped to `?v=145`.

## Map Dot Color Theme System (2026-03-15)

- 5 switchable dot color themes: domain (default), classic, mono, heat, neon.
- State: `state.dotColorTheme` persisted as `tm_dot_theme` in localStorage.
- `_blendLocationColors()` expanded with switch on theme. Domain = existing dominance tinting. Classic = uniform blue. Mono = white/gray. Heat = story-count gradient. Neon = pure domain colors.
- Heat gradient: 5 color stops via `_HEAT_STOPS` array + `_heatColor()` linear interpolation. Uses max group size across all coords as upper bound.
- UI: palette button (`#dot-theme-btn`) + popup menu (`#dot-theme-menu`) near legend area. 5 items with checkmark, label, description.
- Legend adaptation: domain/neon show domain legend, classic/mono hide it, heat shows gradient legend (`#heat-legend`).
- Escape key closes menu. Outside click closes menu.
- Dark/light mode CSS for all new elements. Mobile responsive (repositioned to top area). Sidebar-collapsed positioning. Map-hidden hiding.
- Cache-bust version bumped to ?v=147.

## World Bar Share Button (2026-03-15)

- Share button (`#world-share-btn`) added to the world bar between world preset buttons and gear button.
- Uses link icon (&#x1F517;), same pattern as `#share-view-btn` and `.situation-share-btn`.
- Copies `window.location.href` to clipboard (hash already contains full world + filter state).
- Visual feedback: checkmark + green border for 1.5s, title changes to "Copied!".
- Fallback for older browsers: hidden textarea + `document.execCommand("copy")`.
- `renderWorldsBar()` inserts world buttons before `#world-share-btn` (not `#worlds-more-btn`) to maintain correct DOM order after dynamic re-renders.
- Overflow fade `::after` offset increased from 36px to 68px to account for the extra button.
- Cache-bust version bumped to `?v=143`.
