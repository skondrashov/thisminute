# thisminute.org

For agent startup protocol, communication rules, and forum voting, see `PROTOCOL.md`.

## Overview

Real-time global news map. Scrapes 84 RSS feeds every 15 minutes, extracts structured data via LLM (Claude Haiku), clusters into events and registry events, identifies long-running situations (Claude Sonnet), and displays everything on an interactive globe.

**Philosophy**: Anti-curation. The user decides what to see, not editors. The map IS the filter. Events = "what is happening", not "here are headlines."

## Architecture

```
RSS Feeds (84) + GDELT (sampled, see config.py GDELT_SAMPLE_RATE)
    |
    v
scraper.py + gdelt.py --> pipeline.py
    |
    +--> ner.py --> geocoder.py --> categorizer.py --> database.py
    |
    +--> llm_extractor.py (Haiku: extraction)
    +--> semantic_clusterer.py (event grouping)
    +--> event_analyzer.py (Haiku: analysis)
    +--> registry_manager.py (event registry)
    |
    +--> narrative_analyzer.py (Sonnet, every 1-2h: situations)
    |
    v
app.py (FastAPI) --> static/index.html + app.js + style.css (MapLibre GL JS 5.x)
```

## Stack

- **Backend**: Python, FastAPI, uvicorn, SQLite
- **LLM**: Anthropic API (Haiku for extraction/analysis, Sonnet for situations)
- **Frontend**: Vanilla HTML/JS/CSS, MapLibre GL JS 5.x (no frameworks, esbuild bundler)
- **Deploy**: GCP e2-micro VM (`/opt/thisminute`), venv, nginx, systemd, Let's Encrypt
- **Data**: ~3,500 stories/day from 84 RSS feeds and GDELT

## DB Tables

| Table               | Purpose                                              |
| ------------------- | ---------------------------------------------------- |
| `stories`           | Raw scraped stories with NER/geocode data            |
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

## Key Design Decisions

- **LLM extraction replaces keyword categorization** — single Haiku call per 8-story batch
- **event_signature clustering** — LLM generates 3-6 word phrase identifying the real-world event
- **Dual event system**: `events` table (auto-clustered, ephemeral) + `event_registry` (LLM-tracked, long-lived)
- **location_type** — terrestrial/space/internet/abstract, routes to feed panels
- **Graceful degradation** — works without ANTHROPIC_API_KEY using keyword fallbacks
- **Bright Side system** — LLM scores stories 1-10 for positive framing, rewrites headlines

## Deploying

**Always use `python scripts/deploy.py`**. Never use raw tar/scp/ssh. See `agents/deployer.md` for full procedure.

**Every deploy MUST bump `?v=N`** in index.html for both CSS and JS links.

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
