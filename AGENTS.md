# thisminute.org

If told to go, start, or begin — you are the **orchestrator**. See `agents/orchestrator.md`.

For agent startup protocol, communication rules, and forum voting, see `PROTOCOL.md`.

## Overview

Real-time global news map. Ingests 95 RSS feeds + 13 structured data APIs (USGS, NOAA, EONET, GDACS, ReliefWeb, WHO, Launch Library, OpenAQ, Travel Advisories, FIRMS, Meteoalarm, ACLED, JMA) every 15 minutes, extracts structured data via LLM (Claude Haiku), clusters into events and registry events, identifies long-running situations across 5 narrative domains (Claude Sonnet), and displays everything on an interactive globe. 12 world presets (News, Sports, Entertainment, Positive, Science, Tech, Curious, Weather, Crisis, Travel, Geopolitics, Markets).

**Philosophy**: Anti-curation. The user decides what to see, not editors. The map IS the filter. Events = "what is happening", not "here are headlines."

## Architecture

```
RSS Feeds (95)          Structured data APIs (13):
    |                   usgs.py, noaa.py, eonet.py, gdacs.py,
    v                   reliefweb.py, who.py, launches.py,
scraper.py              openaq.py, travel_advisories.py, firms.py,
    |                   meteoalarm.py, acled.py, jma.py
    +--- gdelt.py ---+      |   country_centroids.py (helper)
                     |      |   source_utils.py (shared helpers)
                     v      v
                   pipeline.py  <-- also scrapes user_feeds (user-added RSS)
                       |
    +--> ner.py --> geocoder.py --> categorizer.py --> database.py
    |
    +--> llm_extractor.py (Haiku: extraction)
    +--> semantic_clusterer.py (event grouping)
    +--> event_analyzer.py (Haiku: analysis)
    +--> registry_manager.py (event registry)
    |
    +--> narrative_analyzer.py (Sonnet, every 1-2h: 5 domain passes)
    |
    v
app.py (FastAPI) --> static/index.html + app.js + style.css (MapLibre GL JS 5.x)
```

## Stack

- **Backend**: Python, FastAPI, uvicorn, SQLite
- **LLM**: Anthropic API (Haiku for extraction/analysis, Sonnet for situations)
- **Frontend**: Vanilla HTML/JS/CSS, MapLibre GL JS 5.x (no frameworks, esbuild bundler)
- **Deploy**: GCP e2-micro VM (`/opt/thisminute`), venv, nginx, systemd, Let's Encrypt
- **Data**: ~4,000+ stories/day from 95 RSS feeds, GDELT, and 13 structured data APIs

## DB Tables

| Table               | Purpose                                              |
| ------------------- | ---------------------------------------------------- |
| `stories`           | Raw scraped stories with NER/geocode data. `source_type`: 'reported' (RSS/GDELT) or 'inferred' (structured APIs) |
| `story_extractions` | LLM-extracted structured data per story              |
| `story_actors`      | Actors with roles (perpetrator/victim/authority/etc) |
| `story_locations`   | Enriched location data from LLM (with roles)         |
| `events`            | Clustered groups of related stories                  |
| `event_stories`     | Event-story join table                               |
| `event_registry`    | Long-lived tracked events with map labels            |
| `registry_stories`  | Registry-story join table                            |
| `narratives`        | Situations spanning multiple events                  |
| `narrative_events`  | Narrative-event join table                           |
| `world_overview`    | Current global summary text                          |
| `geocode_cache`     | Nominatim results cache (including null results)     |
| `feed_state`        | Per-feed last-scraped timestamps                     |
| `user_feedback`     | User-submitted feedback (type, target, message, status) |
| `user_feeds`        | User-added RSS feeds (URL, tag, browser_hash, active, errors) |

## Key Design Decisions

- **LLM extraction replaces keyword categorization** — single Haiku call per 8-story batch
- **event_signature clustering** — LLM generates 3-6 word phrase identifying the real-world event
- **Dual event system**: `events` table (auto-clustered, ephemeral) + `event_registry` (LLM-tracked, long-lived)
- **location_type** — terrestrial/space/internet/abstract, routes to feed panels
- **Graceful degradation** — works without ANTHROPIC_API_KEY using keyword fallbacks
- **Bright Side system** — LLM scores stories 1-10 for positive framing, rewrites headlines
- **Inference feed pattern** — Structured data APIs (USGS, NOAA, etc.) pre-build `_extraction` dicts, skipping LLM entirely (zero Haiku cost)
- **SOURCE_ENABLED toggles** — Config-driven enable/disable per 16 source types (including user_feeds), overridable via env vars
- **curiousMode filtering** — Frontend filters stories by `human_interest_score >= 6` in the Curious world preset, mirroring the `brightSideMode` pattern
- **User-added RSS feeds** — Backend API for user-configurable feeds with SSRF protection (DNS pinning, redirect blocking), rate limiting, per-user/global volume caps, and pipeline integration
- **5 narrative domains** — news, sports, entertainment, positive, curious. Per-domain Sonnet passes with domain-specific prompts
- **12 world presets** — News, Sports, Entertainment, Positive, Science, Tech, Curious, Weather, Crisis, Travel, Geopolitics, Markets. Composite presets use subset `activeOrigins` arrays.
- **DRY source adapter pattern** — `source_utils.py` shared helpers (fetch_json, build_extraction, attach_location, dedup_list, strip_html, polygon_centroid)
- **Dominance-tinted dot colors** — Map dots use RGB lerp from a theme-aware base (white dark, gray light) toward the dominant domain color. Ratio = dominant_count / total_stories. Replaced earlier HSL circular averaging which produced misleading intermediate colors.
- **World bar** — Icon+label buttons with 12 unique domain-colored active states (all pass WCAG AA 4.5:1). Share button copies current URL to clipboard.
- **Auto-cycling world tour** — First-time visitors see a 6-world tour (5s per world) that stops on any interaction. Suppresses other onboarding until tour ends.
- **SEO/social** — OG image (1200x630), meta description, canonical link, twitter:card summary_large_image, dynamic OG for situation deep links. `robots.txt` and `sitemap.xml` served via FastAPI routes.
- **Security hardening** — Two-tier rate limiting (per-hash + per-IP), global write budgets, 64KB body size middleware, SSRF protection with DNS pinning, security response headers (nosniff, DENY, strict-origin). Application-layer ready for public launch.

## Deploying & Pushing

**Deploys and git pushes are handled by the ops steward** (see `../ops/agents/steward.md`). Do not deploy or push directly.

To request a deploy: add an entry to `../ops/DEPLOY_QUEUE.md` with scope (push/deploy/both), changed files, and any notes. The steward runs tests, pushes to GitHub, deploys via `python scripts/deploy.py`, cache-busts `?v=` params, and verifies health — on a 60-minute cycle.

The deployer agent (`agents/deployer.md`) retains its role for pre-deploy preparation and verification checklists, but does not execute deploys or pushes itself.

## Cost Model

Cost scales linearly with story volume. The main lever is `GDELT_SAMPLE_RATE` in `src/config.py`. See `agents/economist.md` for the full breakdown.

## Reference Docs

Not every agent needs all the details. Read the ones relevant to your task:

| Doc | Who should read it | What's in it |
|---|---|---|
| `ref/frontend.md` | builder (UI tasks), designer, tester | UI layout, filter system, frontend pitfalls, quality signals |
| `ref/backend.md` | builder (backend tasks), tester, skeptic | Pipeline flow, geocoding, data quality, extraction signals |
| `agents/deployer.md` | deployer | VM procedures, gcloud commands, verification |
| `agents/economist.md` | economist | Cost model, pricing landscape, optimization levers |
| `agents/feedback.md` | feedback | User feedback triage, DB queries, adversarial awareness |
