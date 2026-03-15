# Strategic Analysis: Audience Growth Through Data Source Expansion

**Author:** strategist | **Date:** 2026-03-14 | **Revised:** 2026-03-14 (post-skeptic review)

**Revision note:** This is a corrected version incorporating the skeptic's review (FORUM.md, 2026-03-14 04:20). Items marked [CORRECTED] were wrong in the original. Items marked [UNCHANGED] survived scrutiny. Items marked [NEW] were added based on the review.

---

## 1. Audience Segments

[CORRECTED] Audience sizes below are now stated as *realistic addressable users* (people who might plausibly try a new free tool), not total community sizes. The original version used subreddit subscriber counts and total addressable markets, which inflated numbers by 10-100x.

### 1A. News Junkies / Current Events Obsessives
- **Who:** 25-55, politically engaged, check news 10+ times/day. Journalists, policy wonks, informed citizens.
- **Currently use:** Google News, Apple News, Twitter/X trending, Reuters, AP News app.
- **What we'd need:** We already serve this well. Improve: faster ingestion cycle (sub-15min), more wire services (AP, Reuters RSS), breaking news alerts.
- **Realistic addressable audience:** ~500K-2M (power users dissatisfied with algorithmic curation who actively seek alternatives).
- **Our pitch:** "Every source, one map. No algorithm choosing what you see."

### 1B. Finance / Markets Watchers
- **Who:** 25-60, traders, investors, finance professionals, crypto enthusiasts.
- **Currently use:** Bloomberg Terminal, TradingView, Finviz, Yahoo Finance, r/wallstreetbets, r/investing, FinTwit.
- **What we'd need:** Market-moving event feeds. Central bank announcements, SEC filings, earnings calendars, commodity prices, crypto price alerts. A "Markets" world preset.
- **Realistic addressable audience:** ~100K-500K (retail investors interested in geographic event mapping; professionals already have Bloomberg).
- **Our pitch:** "See market-moving events on a map before they hit your feed." [CORRECTED: removed Bloomberg comparison -- see Section 5 note]

### 1C. Weather Enthusiasts / Storm Chasers
- **Who:** 18-65, hobbyist meteorologists, emergency managers, agriculture workers, outdoor recreation planners.
- **Currently use:** Weather.gov, Windy.com, Weather Underground, r/weather, r/TropicalWeather, Ventusky.
- **What we'd need:** Global weather data (not just US/NOAA). ECMWF severe weather, JMA typhoon tracking, tropical cyclone advisories, global temperature anomalies. A "Weather" world preset.
- **Realistic addressable audience:** ~200K-1M (weather power users; r/weather and r/TropicalWeather active communities total ~50K daily active, plus weather Twitter).
- **Our pitch:** "Every active weather alert and natural event on Earth, one globe, right now."

### 1D. Emergency / Disaster Responders
- **Who:** 30-60, NGO workers, FEMA/emergency managers, military, insurance adjusters, supply chain managers.
- **Currently use:** ReliefWeb, GDACS, Pacific Disaster Center (PDC), OCHA dashboards, FEMA app.
- **What we'd need:** We're building this (GDACS, ReliefWeb, WHO). Add: IFRC appeals, UN OCHA Flash Updates. A "Crisis" world preset.
- **Realistic addressable audience:** ~50K-200K (niche but extremely high engagement and sharing; professionals in emergency management).
- **Our pitch:** "Global crisis situational awareness in one view. Beats checking 6 dashboards."

### 1E. Science / Space Enthusiasts
- **Who:** 18-45, STEM-educated, follow space launches, climate research, physics breakthroughs.
- **Currently use:** r/space, r/science, NASA.gov, SpaceFlightNow, Phys.org, ArsTechnica.
- **What we'd need:** ~~Space launch calendar~~ Launch Library 2 (DONE). ISS position, asteroid close approaches (NASA NeoWs), solar weather (NOAA SWPC). A "Science" world preset.
- **Realistic addressable audience:** ~100K-500K (active science news consumers who engage daily; r/space has ~50-100K DAU, not the 25M subscriber count).
- **Our pitch:** "Every launch, discovery, and breakthrough happening right now, on a globe."

### 1F. Sports Fans (Hardcore)
- **Who:** 18-45, follow multiple leagues, care about scores, transfers, injury reports.
- **Currently use:** ESPN, The Athletic, FotMob, SofaScore, r/soccer, r/nba, fantasy sports apps.
- **What we'd need:** Live scores API (not just news). We have good RSS coverage. Add: transfer rumors feeds, injury report APIs, fantasy-relevant data. Improve Sports world situations.
- **Realistic addressable audience:** ~200K-1M (sports fans who want multi-league geographic coverage; niche within the massive sports audience).
- **Our pitch:** "Every game, transfer, and injury from every league on one map. No app switching."

### 1G. Entertainment / Pop Culture Followers
- **Who:** 16-35, follow celebrity news, movie releases, music drops, streaming content.
- **Currently use:** TMZ, Twitter/X, TikTok, r/movies, r/music, r/television, Letterboxd, social feeds.
- **What we'd need:** Better entertainment data: box office numbers (BoxOfficeMojo), streaming charts, gaming news (IGN, Kotaku RSS). Expand Entertainment world.
- **Realistic addressable audience:** ~100K-500K (pop culture consumers interested in geographic/global view of entertainment events).
- **Our pitch:** "Every premiere, chart-topper, and award show from around the world. Not just Hollywood."

### 1H. Travel / Expat / Digital Nomad Community
- **Who:** 25-45, frequent travelers, expats, remote workers.
- **Currently use:** Google Flights, Rome2Rio, travel advisories (State Dept), r/digitalnomad, r/travel, Nomad List.
- **What we'd need:** Travel advisories (State Dept RSS, UK FCDO, Australia Smartraveller), airline disruption data, disease outbreak maps (CDC, WHO). A "Travel" world preset.
- **Realistic addressable audience:** ~100K-500K (active international travelers seeking risk assessment tools).
- **Our pitch:** "Before you book, see what's happening there. Conflicts, weather, outbreaks, all live."

### 1I. Environmental / Climate Activists
- **Who:** 18-40, passionate about climate change, deforestation, ocean health, renewable energy.
- **Currently use:** Climate.gov, Carbon Brief, r/environment, r/climate, Guardian Environment, Grist.
- **What we'd need:** Climate data feeds: NOAA global temperature anomalies, NASA FIRMS (fire data), Global Forest Watch deforestation alerts, air quality (OpenAQ API), sea level data. A "Climate" world preset.
- **Realistic addressable audience:** ~100K-500K (environmentally engaged users who check data regularly).
- **Our pitch:** "Watch the planet in real time. Every fire, flood, air quality alert, and climate milestone."

### 1J. Geopolitical / OSINT Analysts
- **Who:** 25-55, defense analysts, intelligence professionals, think tank researchers, OSINT hobbyists.
- **Currently use:** Janes, ACLED conflict data, Bellingcat, Liveuamap, Twitter/X OSINT accounts, r/geopolitics.
- **What we'd need:** ACLED conflict event data (API available, free for non-commercial), armed conflict location mapping, sanctions/embargo feeds. A "Geopolitics" world preset.
- **Realistic addressable audience:** ~20K-100K (niche, high engagement, strong word-of-mouth).
- **Our pitch:** "Global conflict and security events, all sources, one map." [CORRECTED: removed Liveuamap comparison -- we don't match their curation/verification quality]

### 1K. Public Health / Epidemiology Watchers
- **Who:** 25-55, health professionals, researchers, pandemic-aware general public.
- **Currently use:** WHO Disease Outbreak News, ProMED, HealthMap, CDC, Johns Hopkins dashboards.
- **What we'd need:** WHO DON (DONE), ProMED RSS, Global.health data. A "Health" or integrated into Crisis world.
- **Realistic addressable audience:** ~50K-200K (heightened since COVID; subset of JHU dashboard's former audience).
- **Our pitch:** "Disease outbreaks and health emergencies worldwide, live."

### 1L. Academic / Research Community
- **Who:** 22-65, university researchers, grad students, science journalists.
- **Currently use:** Google Scholar alerts, PubMed, arXiv, Nature/Science RSS, Altmetric, r/academia.
- **What we'd need:** Research preprint feeds (arXiv RSS, bioRxiv RSS, medRxiv RSS), retraction notices, funding announcements.
- **Realistic addressable audience:** ~20K-100K (researchers and science journalists interested in geographic distribution of research).
- **Our pitch:** "Where in the world is groundbreaking research happening right now?"

### 1M. Crypto / Web3 Community
- **Who:** 18-40, crypto traders, DeFi users, blockchain developers.
- **Currently use:** CoinDesk, The Block, CoinTelegraph, Crypto Twitter, r/cryptocurrency, Dextools.
- **What we'd need:** ~~Crypto news RSS~~ CoinDesk and Decrypt already added (DONE). On-chain alert feeds, regulatory action feeds. Could be part of a "Markets" world.
- **Realistic addressable audience:** ~50K-200K (crypto-engaged users interested in geographic regulatory/event mapping).
- **Our pitch:** "Every regulation, hack, launch, and market move, mapped to where it's happening."

---

## 2. Feed Gap Analysis

[CORRECTED] Removed Launch Library 2 and RSS feeds (HN, TechCrunch, The Verge, Atlas Obscura, CoinDesk, Decrypt) from the gap analysis -- these are already implemented. Updated priorities to reflect actual remaining gaps.

### Tier 1: High Priority (large audience x easy implementation)

| Audience | Data Source Needed | Free API? | World Preset | Priority |
|---|---|---|---|---|
| Weather (1C) | Meteoalarm (European severe weather) | Yes, XML feed | Weather | **HIGH** |
| Weather (1C) | JMA (Japan Meteorological Agency) | Yes, XML/JSON | Weather | **HIGH** |
| Climate (1I) | OpenAQ (global air quality) | Yes, free API | Climate | **HIGH** |
| Climate (1I) | NASA FIRMS (active fire data) | Yes, free API | Climate | **HIGH** |
| Travel (1H) | US State Dept travel advisories | Yes, RSS feed | Travel | **HIGH** |
| Health (1K) | ProMED disease alerts | Yes, RSS feed | Crisis | **HIGH** |
| Science (1E) | NASA NeoWs (asteroid approaches) | Yes, free API key | Science | **HIGH** |
| Entertainment (1G) | IGN / Kotaku RSS (gaming) | Yes, RSS | Entertainment | **HIGH** |

### Tier 2: Medium Priority (good audience, moderate implementation)

| Audience | Data Source Needed | Free API? | World Preset | Priority |
|---|---|---|---|---|
| Finance (1B) | FRED (Federal Reserve economic data) | Yes, free API key | Markets | **MEDIUM** |
| Geopolitics (1J) | ACLED conflict events | Yes, free for non-commercial | Geopolitics | **MEDIUM** |
| Science (1E) | arXiv RSS (preprint papers) | Yes, RSS | Science | **MEDIUM** |
| Sports (1F) | Transfer rumor aggregator RSS | Partial, some RSS | Sports | **MEDIUM** |
| Weather (1C) | NOAA SWPC (space weather / solar) | Yes, JSON | Science | **MEDIUM** |
| Climate (1I) | Global Forest Watch (deforestation) | Yes, API | Climate | **MEDIUM** |
| Health (1K) | Global.health (disease tracking) | Yes, API | Crisis | **MEDIUM** |
| Travel (1H) | UK FCDO travel advisories | Yes, RSS/API | Travel | **MEDIUM** |
| Academic (1L) | bioRxiv / medRxiv RSS | Yes, RSS | Science | **MEDIUM** |
| Entertainment (1G) | Spotify Charts (scrape or RSS) | No official API for charts | Entertainment | **MEDIUM** |

### Tier 3: Lower Priority (niche audience or hard implementation)

| Audience | Data Source Needed | Free API? | World Preset | Priority |
|---|---|---|---|---|
| Finance (1B) | SEC EDGAR (filings) | Yes, free | Markets | **LOW** |
| Geopolitics (1J) | UN Security Council resolutions | Partial (UN News RSS) | Geopolitics | **LOW** |
| Sports (1F) | Live scores API | No free options at scale | Sports | **LOW** |
| Crypto (1M) | On-chain alerts | Complex, multiple APIs | Markets | **LOW** |
| Academic (1L) | Retraction Watch | RSS available | Science | **LOW** |

---

## 3. "Killer Presets"

[CORRECTED] Added dependency analysis for each preset. Noted which need new backend infrastructure vs. config-only changes.

### 3A. "Weather" World
- **Description:** Every active weather alert, storm, and natural event on the planet.
- **Filters/feeds:** NOAA (US, DONE) + EONET (DONE) + Meteoalarm (Europe, NEW) + JMA (Japan/Pacific, NEW) + weather-tagged RSS stories.
- **New data sources needed:** Meteoalarm XML feed, JMA severe weather.
- **Implementation dependencies:** [NEW] This preset needs ORIGIN filtering (showing NOAA/EONET origin stories) combined with feedTags (weather RSS). The current preset system supports `activeOrigins` in config, so this is a composite filter: restrict `activeOrigins` to `["rss", "noaa", "eonet"]` and use `feedTags: ["science"]` for the RSS component. Feasible with current infrastructure but needs careful config.
- **Competitive landscape:** [CORRECTED] Windy.com integrates news alongside weather data. Weather.gov links press coverage to alerts. Our differentiation is combining multiple authoritative alert APIs (NOAA + EONET + eventually Meteoalarm/JMA) into one view with RSS news context. This is incrementally better, not categorically unique.

### 3B. "Science" World
- **Description:** Space launches, asteroid flybys, physics breakthroughs, biology discoveries. The "I love science" feed, but real-time and mapped.
- **Filters/feeds:** Science-tagged RSS (DONE: ScienceDaily, Phys.org, Space.com, Guardian Science) + Launch Library 2 (DONE) + NASA NeoWs (NEW) + arXiv/bioRxiv RSS (NEW) + NOAA SWPC (NEW).
- **New data sources needed:** NASA NeoWs API, arXiv RSS.
- **Implementation dependencies:** [NEW] Needs `feedTags: ["science"]` entry in `WORLD_PRESETS` (trivial config addition). Also needs `activeOrigins` to include `launches` to show Launch Library data. `WORLD_DOMAIN_MAP` needs a `science` entry for situation filtering -- but there is no "science" narrative domain in the backend. Options: (a) add a "science" domain to `narrative_analyzer.py` (significant work), or (b) show all domains' situations in Science world (simple, use existing `news` domain map). Recommend (b) for now.
- **Why defensible:** The spatial dimension for science is genuinely novel. Most science news tools are lists. Plotting launches from Cape Canaveral, particle physics from CERN, marine biology from Galapagos on one globe adds real value. [CORRECTED] However, many science stories map poorly to geography -- a multi-university collaboration doesn't have a single event location. Our NER/geocoding will default to institutional addresses, which is adequate but not always meaningful.

### 3C. "Markets" World
- **Description:** Market-moving events, central bank decisions, earnings surprises, crypto regulation, trade policy -- all mapped to where they originate.
- **Filters/feeds:** Business-tagged RSS (DONE: BBC Business, Guardian Business, NYT Business, CoinDesk, Decrypt) + FRED API (NEW).
- **New data sources needed:** FRED API (moderate).
- **Implementation dependencies:** [NEW] Needs `feedTags: ["business"]` in `WORLD_PRESETS`. Straightforward config addition.
- **Why defensible:** [CORRECTED] Geographic view of market-moving events is a useful niche tool for retail investors. **Removed Bloomberg comparison** -- Bloomberg Terminal provides institutional-grade real-time data feeds with sub-second latency. We show RSS headlines geocoded with 15-minute refresh. These are categorically different products. Our value is "free geographic context for news events," not "Bloomberg alternative."

### 3D. "Crisis" World
- **Description:** Active disasters, humanitarian emergencies, disease outbreaks. For people who need situational awareness.
- **Filters/feeds:** USGS (DONE) + NOAA (DONE) + EONET (DONE) + GDACS (DONE) + ReliefWeb (DONE) + WHO (DONE) + ProMED RSS (NEW) + ACLED (NEW).
- **New data sources needed:** ProMED RSS (trivial), ACLED API (moderate).
- **Implementation dependencies:** [NEW] This is the most natural composite preset. Restrict `activeOrigins` to `["usgs", "noaa", "eonet", "gdacs", "reliefweb", "who"]` plus any crisis-tagged RSS. Most infrastructure already exists.

### 3E. "Climate" World
- **Description:** Environmental change in real time. Wildfires, air quality, deforestation, conservation.
- **Filters/feeds:** EONET wildfires (DONE) + NASA FIRMS (NEW) + OpenAQ (NEW) + Global Forest Watch (NEW) + science/environment RSS (DONE).
- **New data sources needed:** OpenAQ API, NASA FIRMS API, Global Forest Watch API.
- **Implementation dependencies:** [NEW] Requires new API adapter modules. Each follows the existing pattern (200-400 lines). See risk analysis in Section 7.

### 3F. "Travel" World
- **Description:** What's happening where you're going? Travel advisories, disease outbreaks, weather alerts, political instability.
- **Filters/feeds:** State Dept travel advisories (NEW) + UK FCDO (NEW) + WHO outbreak alerts (DONE) + NOAA weather (DONE).
- **New data sources needed:** State Dept RSS, UK FCDO RSS/API.
- **Implementation dependencies:** [NEW] Travel advisories are country-level data geocoded to centroids. Pairs well with zoom-filter.

### 3G. "Tech" World
- **Description:** AI breakthroughs, cybersecurity incidents, product launches, startup funding, regulatory actions -- mapped globally.
- **Filters/feeds:** Tech-tagged RSS (DONE: BBC Tech, Ars Technica, Wired, Guardian Tech, HN, TechCrunch, The Verge).
- **New data sources needed:** None -- all feeds are already live.
- **Implementation dependencies:** [NEW] Needs `feedTags: ["tech"]` in `WORLD_PRESETS`. The feeds ARE tagged "tech" in config.py. This is a config-only change -- the simplest possible preset to ship. No new domain mapping needed if we show all situations.

### 3H. "Curious" World
- **Description:** The most interesting, unusual, and surprising things happening right now.
- **Filters/feeds:** Atlas Obscura (DONE) + stories with high human_interest_score + curious domain situations.
- **New data sources needed:** None for feeds. But:
- **Implementation dependencies:** [CORRECTED -- this is NOT trivial] The curious domain exists in the backend (`narrative_analyzer.py` lines 26, 35, 91-96) and generates situations. However:
  1. There is NO "curious" entry in `WORLD_PRESETS` in the frontend.
  2. There is NO "curious" entry in `WORLD_DOMAIN_MAP` (line 320-325 of app.js only maps news, sports, entertainment, positive).
  3. `computeFilteredState()` (line 1302) does NOT filter by `human_interest_score`. The frontend has no awareness of this field.
  4. To make a "Curious" preset that shows high-human-interest stories, we need **new frontend filter infrastructure** -- either adding `human_interest_score` to the filter system, or using a different mechanism (e.g., a new feedTag or origin type).
  5. The simplest viable approach: add a "curious" world preset that uses `brightSideMode: false` and shows all stories, with situations filtered to the curious domain only (via `WORLD_DOMAIN_MAP`). This doesn't filter stories by human_interest_score but does show curious situations. Full curious filtering would require frontend work.

---

## 4. Remaining Quick Wins

[CORRECTED] Removed items that are already done. Updated time estimates based on the skeptic's analysis and the actual complexity observed in existing adapter code.

### Already Done (not quick wins -- these shipped)
- **6 RSS feeds** (HN, TechCrunch, The Verge, Atlas Obscura, CoinDesk, Decrypt): Live in `src/config.py` lines 83-95, 143.
- **Launch Library 2**: Complete 423-line adapter at `src/launches.py` with caching, provider detection, severity mapping, event signatures. Integrated into pipeline, config, and SOURCE_ENABLED.

### 4A. "Science" and "Tech" World Presets -- CONFIG ONLY
- **Effort:** 1-2 hours total. Add entries to `WORLD_PRESETS` and `WORLD_ICONS` in `static/js/app.js`.
- **Risk:** Near zero. Config changes only. No new backend code.
- **Why now:** Validates the preset system with the least effort. All data sources are already live.

### 4B. OpenAQ -- Global Air Quality
- **API:** `https://api.openaq.org/v3/locations?limit=100&order_by=lastUpdated&sort=desc`
- **Auth:** Free API key (instant registration).
- **Data:** City name, lat/lon, PM2.5/PM10/O3/NO2/SO2 readings, last updated time.
- **Realistic addressable audience:** Climate-concerned, health-conscious users (~100K-500K).
- **Implementation:** [CORRECTED] ~8-12 hours. Based on existing adapters (USGS ~230 lines, NOAA ~360, launches 423), a production-quality adapter with tests, pipeline integration, and config runs 200-300 lines plus test coverage. The 4-hour original estimate assumed trivial integration.
- **Risk considerations:** [NEW] Need to verify API rate limits. Volume control needed -- OpenAQ could return hundreds of cities exceeding thresholds. Filter to worst offenders (PM2.5 > 50 or AQI "unhealthy") to keep volume manageable.

### 4C. NASA FIRMS -- Active Fires Worldwide
- **API:** `https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/VIIRS_SNPP_NRT/world/1`
- **Auth:** Free API key (NASA Earthdata, instant).
- **Data:** Lat/lon, brightness, confidence, date, satellite. Thousands of active fire detections daily.
- **Realistic addressable audience:** Climate activists, wildfire-affected communities (~100K-500K).
- **Implementation:** [CORRECTED] ~12-16 hours. CSV format adds parsing complexity. Must cluster nearby fire points (a single wildfire produces hundreds of satellite detections). Clustering logic is non-trivial and quality-sensitive.
- **Risk considerations:** [NEW] **Volume is the biggest concern.** FIRMS detects thousands of fires daily worldwide. Without aggressive filtering (confidence > 80%, cluster radius, min brightness), this could flood the pipeline with thousands of stories per cycle. Each story costs Haiku tokens unless we skip LLM extraction (which we should, as a structured data source). Memory impact on e2-micro VM needs benchmarking.

### 4D. US State Dept Travel Advisories
- **API:** RSS feed at `https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories.xml`
- **Auth:** None.
- **Data:** Country, advisory level (1-4), date, description.
- **Realistic addressable audience:** Travelers, expats (~100K-500K).
- **Implementation:** [CORRECTED] ~6-8 hours. RSS-parseable, geocode to country centroids (existing `country_centroids.py`). Needs severity mapping from advisory levels. Lower total line count than API adapters but still needs tests and pipeline integration.
- **Risk:** Low volume (advisory changes are infrequent). Low risk.

### 4E. ProMED Disease Alerts
- **API:** RSS feed.
- **Auth:** None.
- **Effort:** [CORRECTED] ~4-6 hours. RSS adapter following existing pattern.
- **Risk:** Low volume, low risk.

---

## 5. The "Marketing Moat"

### What makes thisminute genuinely different

[UNCHANGED -- these core differentiators survived scrutiny]

1. **Spatial first.** Google News, Apple News, Feedly -- they're all lists. We're a map. This isn't a gimmick; it changes how you process information. You see patterns (conflict spreading, storms moving, fires clustering) that no list reveals.

2. **Anti-curation.** Every other news product employs editors or algorithms to decide what you see. We show everything and give you the knobs. This is philosophically different from every competitor.

3. **Source diversity.** We mix RSS news, government sensor data (USGS, NOAA), satellite observations (EONET), and global event databases (GDELT). No other free tool combines journalistic sources with scientific/sensor data.

4. **Worlds, not feeds.** Feedly gives you folders of RSS feeds. We give you worlds -- composable filter presets that transform the entire experience. Sports world isn't "sports feeds in a folder." It's the globe showing only sports events, with sports-specific situations, sports-colored dots.

5. **Free and open.** Government data tools (ReliefWeb, GDACS) require navigating clunky UIs. We make that data beautiful and instant.

### [CORRECTED] Competitive positioning -- honest assessment

| Claim (original) | Reality | Revised position |
|---|---|---|
| "Bloomberg-lite for maps" | Bloomberg Terminal is institutional-grade real-time data with sub-second latency. We're RSS headlines with 15-min refresh. Categorically different. | **Dropped.** Do not compare to Bloomberg. |
| "Liveuamap for the whole world" | Liveuamap has dedicated regional analysts curating and verifying each data point with sourced OSINT. We auto-ingest RSS with LLM extraction. Different quality level. | **Dropped.** Position as "global event map" without claiming to match Liveuamap's verification. |
| "Nobody maps where science is happening" | Defensible as a differentiator. Science news on a geographic map is novel. Limitation: many science stories don't have clean event locations. | **Keep with caveat.** Geographic science mapping adds genuine value for launches, discoveries, field research. Less useful for multi-institution collaborations. |
| "No other tool combines alerts with news context" | Windy.com integrates news. Weather.gov links press releases. Our combination of multiple alert APIs (USGS + NOAA + EONET + GDACS) with news RSS is incrementally better. | **Soften.** "Most comprehensive free combination of alert APIs with news context." |

### The one-sentence pitch per audience

| Audience | Pitch |
|---|---|
| News Junkies | "Every news source on Earth, no algorithm. You decide." |
| Finance | "See market-moving events on a map, for free." |
| Weather | "Every weather alert on the planet, one globe." |
| Emergency/Crisis | "Global crisis awareness without checking 6 dashboards." |
| Science/Space | "Watch discoveries and launches happen in real time." |
| Sports | "Every league, every match, every transfer, one map." |
| Entertainment | "Global pop culture, not just Hollywood." |
| Travel | "What's really happening where you're going." |
| Climate | "The state of the planet, live." |
| OSINT/Geopolitics | "Global conflict and security events, all sources, one map." |
| Public Health | "Disease outbreaks and health emergencies worldwide." |
| Tech | "Global tech news. Not just Silicon Valley." |
| Curious | "The most interesting things happening right now." |

---

## 6. Priority Recommendations

[CORRECTED] Updated to reflect what's actually done, realistic time estimates, and dependency ordering.

### Immediate (this week)
1. **Ship "Science" and "Tech" world presets** (1-2 hours, config changes only, zero risk). These validate the preset system and serve the science/tech audiences with zero new backend work. All data sources are already live.
2. **Wire "curious" domain into frontend** (2-3 hours). Add `curious` to `WORLD_DOMAIN_MAP` and `WORLD_PRESETS`. Even without `human_interest_score` filtering, curious situations from the backend will display in this world.

### Next sprint (2 weeks)
3. **OpenAQ air quality** (8-12 hours, unlocks climate audience)
4. **State Dept travel advisories** (6-8 hours, unlocks travel audience)
5. **ProMED disease alerts** (4-6 hours, strengthens crisis preset)
6. **Ship "Weather" and "Crisis" composite presets** (2-3 hours each, config + origin filtering)

### Following sprint
7. **NASA FIRMS fire data** (12-16 hours, requires clustering logic and volume control)
8. **Meteoalarm** (8-12 hours, European severe weather, makes Weather world truly global)
9. **Ship "Climate", "Travel", "Markets" world presets**

### Deferred (needs further analysis)
10. ACLED conflict data (makes Geopolitics preset possible, but need to assess data licensing terms)
11. NASA NeoWs (asteroid approaches, cool but low story volume)
12. Full "Curious" preset with `human_interest_score` frontend filtering (needs new filter infrastructure)

---

## 7. Risk Analysis [NEW]

This section was missing from the original analysis. The skeptic correctly identified significant gaps.

### 7A. API Rate Limits
- **Launch Library 2:** Free tier is 15 req/hr. Pipeline runs every 15 min = 4 cycles/hr x 2 endpoints = 8 req/hr. Current caching (30 min) keeps us under the limit, but any retry logic or cache miss could exceed it. **Status: Close to limit. Monitor.**
- **OpenAQ:** Free tier has generous limits but needs verification before implementation.
- **NASA FIRMS:** Rate limits unknown. Need to check before building adapter.
- **Aggregate budget:** [NEW] Before adding any new API source, document its rate limit and calculate per-cycle API call count. Maintain a running total. Current: USGS (2 endpoints/cycle), NOAA (1), EONET (1), GDACS (2), ReliefWeb (1), WHO (1), Launches (2 with cache). Total: ~10 API calls/cycle, ~40/hr.

### 7B. Cost Impact
- Structured data sources (USGS, NOAA, EONET, GDACS, ReliefWeb, WHO, Launches) skip LLM extraction, so they add zero Haiku cost.
- RSS feeds DO go through LLM extraction. The 6 new feeds add ~50-100 stories/day, which is ~$0.10-0.20/day additional Haiku cost. Manageable.
- **NASA FIRMS risk:** If FIRMS adds 1000+ fire stories/day and they go through LLM extraction, cost could spike. Must use the inference feed pattern (skip LLM, pre-build extraction) for all structured data sources.
- **OpenAQ risk:** Similar volume concern. Must use inference feed pattern.

### 7C. VM Resource Limits
- **Platform:** GCP e2-micro (1 vCPU, 1 GB RAM).
- **Current pipeline:** Scraping + NER + geocoding + LLM extraction + clustering + analysis in a 15-minute cycle.
- **Risk:** Adding sources that return thousands of data points per cycle (FIRMS, OpenAQ) could push pipeline over memory/time limits.
- **Mitigation:** (a) All new structured data sources must use the inference feed pattern (skip LLM extraction). (b) Implement aggressive filtering at ingestion (only ingest events above severity thresholds). (c) Monitor pipeline cycle time after each new source. (d) Consider increasing to e2-small if needed (~$10/mo additional).

### 7D. Maintenance Burden
- 9 data source modules already exist. Each is a point of failure -- APIs change, rate limits change, formats change.
- **Mitigation:** (a) The DRY refactor (source_utils.py) reduces per-module maintenance burden. (b) The SOURCE_ENABLED toggle system allows disabling broken sources without code changes. (c) Each new source should be added one at a time with monitoring, not all at once.

### 7E. Data Quality
- Structured data sources skip LLM extraction and use hand-coded event_signature heuristics. These heuristics can produce bad clustering.
- **Risk:** More sources = more hand-tuned heuristics = more potential for clustering errors.
- **Mitigation:** (a) Each new adapter needs comprehensive test coverage for event_signature generation. (b) Monitor clustering quality per-source. (c) Consider adding a "source quality" metric to track clustering accuracy.

---

## 8. The Bias Correction Principle [CORRECTED]

### Original (wrong)
"For every disaster source added, add at least one non-disaster source."

### Why it was wrong
The skeptic correctly identified that **source count is the wrong metric -- story volume is what matters.** NOAA alone generates hundreds of alerts per cycle. USGS generates dozens of earthquakes per day. Adding one CoinDesk RSS feed (20 stories/day) does not "balance" NOAA (200+ alerts/day).

### Revised principle
**"Monitor the story domain distribution in the default 'All' world. If any single category exceeds 40% of visible stories, raise ingestion thresholds for that category's sources or adjust severity filters."**

This is measurable and actionable. Concrete implementation:
1. Add a `/api/stats/domain-distribution` endpoint that reports story counts by domain/origin in the current cycle.
2. Dashboard the distribution so we can see skew in real time.
3. Use severity thresholds as the lever: e.g., only ingest NOAA alerts of severity "Extreme" or "Severe" (not "Moderate" or "Minor") if weather stories exceed 40% of volume.
4. The world presets themselves solve the user-facing problem -- each preset shows the right content for that audience. The "doom map" concern only applies to the default "All" world.

### What the original got right
The underlying observation IS correct: if we keep adding disaster sources without any non-disaster sources, the default experience gets grimmer. The fix is just different from what I proposed -- it's volume thresholds and severity filters, not source counting.
