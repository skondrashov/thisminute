"""FastAPI application for thisminute."""

import colorsys
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import FastAPI, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import STATIC_DIR, FEED_TAG_MAP
from .database import (
    get_connection, get_stories, get_sources, get_source_counts, get_categories, get_stats,
    get_cached_geocode, init_db, get_all_events, get_event_by_id,
    get_event_stories, get_world_overview,
    search_stories_multi, get_story_extraction, get_story_actors,
    get_active_narratives, get_narrative_by_id, get_narrative_events,
    get_active_registry_events,
)
from .categorizer import get_all_concept_names, CONCEPT_DOMAINS
from .geocoder import bbox_to_radius_km
from .ner import classify_location, _COUNTRY_SET
from .scheduler import PipelineScheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

scheduler = PipelineScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start scheduler on startup, stop on shutdown."""
    init_db()
    scheduler.start()
    yield
    scheduler.stop()


app = FastAPI(title="thisminute", lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index(sit: Optional[int] = Query(None)):
    """Serve the main page, with dynamic OG tags for situation deep links."""
    if sit is None:
        return FileResponse(str(STATIC_DIR / "index.html"))

    # Dynamic OG: look up situation for social preview
    conn = get_connection()
    narrative = get_narrative_by_id(conn, sit)
    conn.close()

    html_path = STATIC_DIR / "index.html"
    html = html_path.read_text(encoding="utf-8")

    if narrative:
        title = f"{narrative['title']} — thisminute"
        desc = narrative.get("description") or "Follow this developing situation on thisminute.org"
        # Escape for HTML attributes
        title_safe = title.replace('"', "&quot;").replace("<", "&lt;")
        desc_safe = desc.replace('"', "&quot;").replace("<", "&lt;")
        html = html.replace(
            '<meta property="og:title" content="thisminute — global news, live">',
            f'<meta property="og:title" content="{title_safe}">',
        ).replace(
            '<meta property="og:description" content="Real-time global news on an interactive map. Filter by topic, search by actor or action, track evolving narratives across 50+ sources.">',
            f'<meta property="og:description" content="{desc_safe}">',
        ).replace(
            '<meta name="twitter:title" content="thisminute — global news, live">',
            f'<meta name="twitter:title" content="{title_safe}">',
        ).replace(
            '<meta name="twitter:description" content="Real-time global news on an interactive map. Filter by topic, search by actor, track narratives.">',
            f'<meta name="twitter:description" content="{desc_safe}">',
        ).replace(
            "<title>thisminute — global news, live</title>",
            f"<title>{title_safe}</title>",
        )

    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)


@app.get("/api/health")
async def api_health():
    """Health check endpoint for nginx and monitoring."""
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) as c FROM stories").fetchone()["c"]
    conn.close()
    return {"status": "ok", "stories": total}


@app.get("/api/diagnostics")
async def api_diagnostics():
    """Diagnostics endpoint for monitoring system health."""
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) as c FROM stories").fetchone()["c"]
    rss = conn.execute("SELECT COUNT(*) as c FROM stories WHERE origin='rss'").fetchone()["c"]
    gdelt = conn.execute("SELECT COUNT(*) as c FROM stories WHERE origin='gdelt'").fetchone()["c"]
    recent_1h = conn.execute(
        "SELECT COUNT(*) as c FROM stories WHERE scraped_at > datetime('now', '-1 hour')"
    ).fetchone()["c"]
    recent_24h = conn.execute(
        "SELECT COUNT(*) as c FROM stories WHERE scraped_at > datetime('now', '-1 day')"
    ).fetchone()["c"]
    events_active = conn.execute(
        "SELECT COUNT(*) as c FROM events WHERE merged_into IS NULL AND status != 'resolved'"
    ).fetchone()["c"]
    narr_rows = conn.execute(
        "SELECT domain, COUNT(*) as c FROM narratives WHERE status='active' GROUP BY domain"
    ).fetchall()
    narr_by_domain = {r["domain"]: r["c"] for r in narr_rows}
    registry_active = conn.execute(
        "SELECT COUNT(*) as c FROM event_registry WHERE status='active'"
    ).fetchone()["c"]
    conn.close()
    return {
        "stories": {"total": total, "rss": rss, "gdelt": gdelt, "last_1h": recent_1h, "last_24h": recent_24h},
        "events": {"active": events_active},
        "narratives": narr_by_domain,
        "registry": {"active": registry_active},
    }


_stories_cache = {"data": None, "expires": 0}  # in-memory cache for default stories query
_narratives_cache = {"data": None, "expires": 0}  # in-memory cache for default narratives query
_events_cache = {"data": None, "expires": 0}  # in-memory cache for default events query
_clouds_cache = {"data": None, "expires": 0}  # in-memory cache for default clouds query


@app.get("/api/stories")
async def api_stories(
    since: Optional[str] = Query(None, description="ISO timestamp filter"),
    source: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    concepts: Optional[str] = Query(None, description="Comma-separated concept names to include"),
    exclude: Optional[str] = Query(None, description="Comma-separated concept names to exclude"),
    search: Optional[str] = Query(None, description="Text search in title/summary"),
    limit: int = Query(2000, ge=1, le=5000),
):
    """Return stories as GeoJSON FeatureCollection."""
    import time as _time

    # Serve cached response for the default (no-filter) query
    is_default = not since and not source and not category and not concepts and not exclude and not search and limit == 2000
    now = _time.time()
    if is_default and _stories_cache["data"] and now < _stories_cache["expires"]:
        return JSONResponse(
            content=_stories_cache["data"],
            headers={"Cache-Control": "public, max-age=15"},
        )

    concept_list = [c.strip() for c in concepts.split(",")] if concepts else None
    exclude_list = [c.strip() for c in exclude.split(",")] if exclude else None

    conn = get_connection()
    stories = get_stories(
        conn, since=since, source=source, category=category,
        concepts=concept_list, exclude_concepts=exclude_list,
        search=search, limit=limit,
    )

    # Bulk-fetch extraction data for location_type and search_keywords
    story_ids = [s["id"] for s in stories]
    extraction_map = {}
    registry_link_map = {}
    narrative_link_map = {}
    if story_ids:
        placeholders = ",".join("?" * len(story_ids))
        rows = conn.execute(
            f"""SELECT se.story_id, se.location_type, se.search_keywords, se.severity,
                       se.primary_action, se.topics, se.is_opinion, se.registry_event_id,
                       se.bright_side_score, se.bright_side_category, se.bright_side_headline
                FROM story_extractions se WHERE se.story_id IN ({placeholders})""",
            story_ids,
        ).fetchall()
        for r in rows:
            extraction_map[r[0]] = dict(r)
        # Also get registry links from registry_stories (covers seeded events)
        reg_rows = conn.execute(
            f"SELECT story_id, registry_event_id FROM registry_stories WHERE story_id IN ({placeholders})",
            story_ids,
        ).fetchall()
        for r in reg_rows:
            registry_link_map[r["story_id"]] = r["registry_event_id"]
        # Get narrative IDs per story (story → event_stories → narrative_events)
        narrative_link_map = {}  # story_id -> [narrative_id, ...]
        try:
            narr_rows = conn.execute(
                f"""SELECT DISTINCT es.story_id, ne.narrative_id
                    FROM event_stories es
                    JOIN narrative_events ne ON ne.event_id = es.event_id
                    JOIN narratives n ON n.id = ne.narrative_id AND n.status = 'active'
                    WHERE es.story_id IN ({placeholders})""",
                story_ids,
            ).fetchall()
            for r in narr_rows:
                narrative_link_map.setdefault(r["story_id"], []).append(r["narrative_id"])
        except Exception:
            pass
    conn.close()

    features = []
    for s in stories:
        story_concepts = s.get("concepts", "[]")
        if isinstance(story_concepts, str):
            try:
                story_concepts = json.loads(story_concepts)
            except (json.JSONDecodeError, TypeError):
                story_concepts = []

        ext = extraction_map.get(s["id"], {})

        # Use LLM-extracted topics if available (override categorizer)
        ext_topics = ext.get("topics")
        if ext_topics:
            try:
                parsed = json.loads(ext_topics) if isinstance(ext_topics, str) else ext_topics
                if parsed:
                    story_concepts = parsed
            except (json.JSONDecodeError, TypeError):
                pass

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [s["lon"], s["lat"]],
            },
            "properties": {
                "id": s["id"],
                "title": s["title"],
                "url": s["url"],
                "summary": s["summary"],
                "source": s["source"],
                "origin": s.get("origin", "rss"),
                "category": s.get("category", "general"),
                "concepts": story_concepts,
                "location_name": s.get("location_name"),
                "published_at": s.get("published_at"),
                "scraped_at": s["scraped_at"],
                "location_type": ext.get("location_type", "terrestrial"),
                "severity": ext.get("severity"),
                "primary_action": ext.get("primary_action"),
                "is_opinion": ext.get("is_opinion") in (1, "1", True),
                "registry_event_id": ext.get("registry_event_id") or registry_link_map.get(s["id"]),
                "bright_side_score": int(ext["bright_side_score"]) if ext.get("bright_side_score") is not None else None,
                "bright_side_category": ext.get("bright_side_category"),
                "bright_side_headline": ext.get("bright_side_headline"),
                "narrative_ids": narrative_link_map.get(s["id"], []),
                "search_keywords": _parse_keywords(ext.get("search_keywords")),
                "image_url": s.get("image_url"),
            },
        })

    result = {"type": "FeatureCollection", "features": features}
    if is_default:
        _stories_cache["data"] = result
        _stories_cache["expires"] = now + 30  # 30s cache
    return JSONResponse(
        content=result,
        headers={"Cache-Control": "public, max-age=15"},
    )


def _parse_keywords(raw) -> list[str]:
    """Parse search_keywords JSON field into a list of strings."""
    if not raw:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []
    return raw if isinstance(raw, list) else []


def _parse_ner_entities(raw) -> list[dict]:
    """Parse ner_entities field into a list of {"name": ..., "role": ...} dicts.

    Handles both ["string", ...] and [{"text": ..., "role": ...}, ...] formats.
    """
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []
    if not isinstance(raw, list):
        return []
    results = []
    for item in raw:
        if isinstance(item, str):
            results.append({"name": item, "role": "mentioned"})
        elif isinstance(item, dict):
            text = item.get("text")
            if text:
                results.append({"name": text, "role": item.get("role", "mentioned")})
    return results


@app.get("/api/stories/clouds")
async def api_stories_clouds(
    since: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    concepts: Optional[str] = Query(None),
    exclude: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=2000),
):
    """Return multi-point GeoJSON for confidence cloud rendering.

    Each story is expanded into one Point per NER entity, with radius_km
    reflecting location specificity (city=tight, country=wide).
    """
    import time as _time
    is_default = not since and not source and not category and not concepts and not exclude and not search and limit == 500
    now = _time.time()
    if is_default and _clouds_cache["data"] and now < _clouds_cache["expires"]:
        return JSONResponse(
            content=_clouds_cache["data"],
            headers={"Cache-Control": "public, max-age=30"},
        )

    concept_list = [c.strip() for c in concepts.split(",")] if concepts else None
    exclude_list = [c.strip() for c in exclude.split(",")] if exclude else None

    conn = get_connection()
    stories = get_stories(
        conn, since=since, source=source, category=category,
        concepts=concept_list, exclude_concepts=exclude_list,
        search=search, limit=limit,
    )

    features = []
    _geocode_cache = {}  # Request-local cache for repeated entity names
    for s in stories:
        parsed_entities = _parse_ner_entities(s.get("ner_entities", "[]"))

        story_concepts = s.get("concepts", "[]")
        if isinstance(story_concepts, str):
            try:
                story_concepts = json.loads(story_concepts)
            except (json.JSONDecodeError, TypeError):
                story_concepts = []

        primary_loc = s.get("location_name")

        if not parsed_entities:
            # Fallback: use the story's primary geocoded location
            if s.get("lat") is not None and s.get("lon") is not None:
                tier, radius_km = classify_location(primary_loc or "")
                country_name = primary_loc if primary_loc in _COUNTRY_SET else None
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [s["lon"], s["lat"]]},
                    "properties": {
                        "story_id": s["id"],
                        "title": s["title"],
                        "url": s["url"],
                        "summary": s.get("summary"),
                        "source": s["source"],
                        "category": s.get("category", "general"),
                        "concepts": story_concepts,
                        "location_name": primary_loc,
                        "country_name": country_name,
                        "role": "mentioned",
                        "radius_km": radius_km,
                        "tier": tier,
                        "is_primary": True,
                        "scraped_at": s["scraped_at"],
                    },
                })
            continue

        for entity in parsed_entities:
            entity_name = entity["name"]
            entity_role = entity["role"]

            if entity_name not in _geocode_cache:
                _geocode_cache[entity_name] = get_cached_geocode(conn, entity_name)
            cached = _geocode_cache[entity_name]
            if not cached or cached.get("lat") is None:
                continue

            tier, default_radius = classify_location(entity_name)

            # Use bbox-derived radius if available, else tier default
            bbox_s = cached.get("bbox_south")
            bbox_n = cached.get("bbox_north")
            bbox_w = cached.get("bbox_west")
            bbox_e = cached.get("bbox_east")
            if bbox_s is not None and bbox_n is not None and bbox_w is not None and bbox_e is not None:
                radius_km = max(bbox_to_radius_km(bbox_s, bbox_n, bbox_w, bbox_e), 5)
            else:
                radius_km = default_radius

            country_name = entity_name if entity_name in _COUNTRY_SET else None

            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [cached["lon"], cached["lat"]]},
                "properties": {
                    "story_id": s["id"],
                    "title": s["title"],
                    "url": s["url"],
                    "summary": s.get("summary"),
                    "source": s["source"],
                    "category": s.get("category", "general"),
                    "concepts": story_concepts,
                    "location_name": entity_name,
                    "country_name": country_name,
                    "role": entity_role,
                    "radius_km": round(radius_km, 1),
                    "tier": tier,
                    "is_primary": (entity_name == primary_loc),
                    "scraped_at": s["scraped_at"],
                },
            })

    conn.close()
    response_data = {"type": "FeatureCollection", "features": features}
    if is_default:
        _clouds_cache["data"] = response_data
        _clouds_cache["expires"] = now + 30  # 30s cache
    return JSONResponse(
        content=response_data,
        headers={"Cache-Control": "public, max-age=30"},
    )


_sources_cache = {"data": None, "expires": 0}

@app.get("/api/sources")
async def api_sources():
    """Return list of source names with counts (cached in memory for 30 min)."""
    import time as _time
    now = _time.time()
    if _sources_cache["data"] and now < _sources_cache["expires"]:
        return JSONResponse(
            content=_sources_cache["data"],
            headers={"Cache-Control": "public, max-age=1800"},
        )

    conn = get_connection()
    rows = conn.execute(
        """SELECT source, COUNT(*) as count FROM stories
           WHERE scraped_at > datetime('now', '-3 days')
           GROUP BY source ORDER BY count DESC"""
    ).fetchall()
    sources = [r["source"] for r in rows]
    counts = [{"source": r["source"], "count": r["count"]} for r in rows]
    conn.close()

    result = {"sources": sources, "counts": counts}
    _sources_cache["data"] = result
    _sources_cache["expires"] = now + 1800  # 30 min
    return JSONResponse(
        content=result,
        headers={"Cache-Control": "public, max-age=1800"},
    )


@app.get("/api/feed-tags")
async def api_feed_tags():
    """Return mapping of source names to their feed tags.

    Used by the frontend to filter stories by feed category (e.g. sports, tech).
    Also returns a reverse mapping of tag -> source names for convenience.
    """
    # tag -> [source_name, ...]
    tag_sources = {}
    for source, tags in FEED_TAG_MAP.items():
        for tag in tags:
            tag_sources.setdefault(tag, []).append(source)
    return JSONResponse(
        content={"source_tags": FEED_TAG_MAP, "tag_sources": tag_sources},
        headers={"Cache-Control": "public, max-age=86400"},  # 24h — config-derived
    )


@app.get("/api/categories")
async def api_categories():
    """Return list of categories with colors."""
    conn = get_connection()
    cats = get_categories(conn)
    conn.close()
    return JSONResponse(
        content={"categories": [
            {"name": c, "color": CONCEPT_DOMAINS.get(c, {}).get("color", "#95a5a6")}
            for c in cats
        ]},
        headers={"Cache-Control": "public, max-age=21600"},  # 6h
    )


_concepts_cache = {"data": None, "expires": 0}

@app.get("/api/concepts")
async def api_concepts():
    """Return all known concepts grouped by domain."""
    import time as _time
    now = _time.time()
    if _concepts_cache["data"] and now < _concepts_cache["expires"]:
        return JSONResponse(
            content=_concepts_cache["data"],
            headers={"Cache-Control": "public, max-age=1800"},
        )

    # Count concepts using json_each() in SQL (avoids loading all stories into Python)
    conn = get_connection()
    rows = conn.execute(
        """SELECT jc.value AS concept, COUNT(*) AS cnt
           FROM stories s, json_each(s.concepts) jc
           WHERE s.scraped_at > datetime('now', '-7 days')
             AND s.concepts IS NOT NULL AND s.concepts != '[]'
           GROUP BY jc.value"""
    ).fetchall()
    conn.close()

    counts = {r["concept"]: r["cnt"] for r in rows}

    result = {}
    for domain_name, domain_info in CONCEPT_DOMAINS.items():
        concepts = []
        for concept_name in domain_info["concepts"]:
            concepts.append({
                "name": concept_name,
                "count": counts.get(concept_name, 0),
            })
        result[domain_name] = {
            "color": domain_info["color"],
            "concepts": concepts,
        }

    _concepts_cache["data"] = result
    _concepts_cache["expires"] = now + 1800  # 30 min
    return JSONResponse(
        content=result,
        headers={"Cache-Control": "public, max-age=1800"},  # 30 min
    )


# Topic color mapping for LLM-generated topics
_TOPIC_COLORS = {
    # conflict / military
    "war": "#e74c3c", "military": "#e74c3c", "strike": "#e74c3c", "attack": "#e74c3c",
    "conflict": "#e74c3c", "weapon": "#e74c3c", "bomb": "#e74c3c", "missile": "#e74c3c",
    "combat": "#e74c3c", "airstrike": "#e74c3c", "naval": "#e74c3c", "defense": "#e74c3c",
    # politics / governance
    "politic": "#3498db", "election": "#3498db", "govern": "#3498db", "democra": "#3498db",
    "vote": "#3498db", "parliament": "#3498db", "congress": "#3498db", "senate": "#3498db",
    "legislation": "#3498db", "cabinet": "#3498db", "trump": "#3498db", "biden": "#3498db",
    "policy": "#3498db",
    # economy / trade / business
    "econom": "#f39c12", "trade": "#f39c12", "market": "#f39c12", "financ": "#f39c12",
    "business": "#f39c12", "oil": "#f39c12", "tariff": "#f39c12", "supply": "#f39c12",
    "price": "#f39c12", "invest": "#f39c12", "bank": "#f39c12", "stock": "#f39c12",
    # tech / AI / science
    "tech": "#9b59b6", "ai": "#9b59b6", "cyber": "#9b59b6", "digital": "#9b59b6",
    "robot": "#9b59b6", "space": "#9b59b6", "scien": "#9b59b6", "nasa": "#9b59b6",
    "quantum": "#9b59b6", "gravi": "#9b59b6",
    # climate / environment
    "climate": "#27ae60", "environ": "#27ae60", "emission": "#27ae60", "flood": "#27ae60",
    "wildfire": "#27ae60", "drought": "#27ae60", "carbon": "#27ae60", "sustain": "#27ae60",
    "energy": "#27ae60", "renew": "#27ae60",
    # health
    "health": "#1abc9c", "medic": "#1abc9c", "disease": "#1abc9c", "vaccin": "#1abc9c",
    "hospital": "#1abc9c", "pandem": "#1abc9c", "drug": "#1abc9c",
    # sports
    "sport": "#e67e22", "football": "#e67e22", "cricket": "#e67e22", "olympic": "#e67e22",
    "premier": "#e67e22", "league": "#e67e22", "rugby": "#e67e22", "tennis": "#e67e22",
    "cup": "#e67e22", "match": "#e67e22",
    # culture / entertainment
    "film": "#e91e63", "music": "#e91e63", "art": "#e91e63", "culture": "#e91e63",
    "award": "#e91e63", "entertain": "#e91e63", "book": "#e91e63", "festival": "#e91e63",
    # security / espionage
    "espio": "#795548", "spy": "#795548", "intellig": "#795548", "secur": "#795548",
    "surveil": "#795548", "hack": "#795548",
    # human rights / social
    "human": "#e74c3c", "rights": "#c0392b", "protest": "#c0392b", "refugee": "#c0392b",
    "crisis": "#c0392b", "humanitarian": "#c0392b",
    # regions (for country-specific topics)
    "china": "#ff5722", "india": "#ff9800", "iran": "#d32f2f", "russia": "#b71c1c",
    "uk": "#2196f3", "us": "#1565c0", "eu": "#1a237e", "africa": "#4caf50",
    "asia": "#ff7043", "middle": "#bf360c", "latin": "#558b2f",
    "hong": "#ff5722", "japan": "#ff7043", "korea": "#ff7043",
}


def _topic_color(topic: str) -> str:
    """Get a color for an LLM-generated topic by keyword matching."""
    lower = topic.lower().replace("-", " ")
    for keyword, color in _TOPIC_COLORS.items():
        if keyword in lower:
            return color
    # Fallback: deterministic hex color from hash (must be hex for frontend alpha suffixes)
    h = (hash(topic) % 360) / 360.0
    r, g, b = colorsys.hls_to_rgb(h, 0.45, 0.55)
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"


@app.get("/api/trending")
async def api_trending():
    """Detect trending concepts by comparing recent vs baseline frequency.

    Compares concept frequency in last 3h vs last 24h.
    Returns concepts sorted by spike ratio.
    """
    conn = get_connection()
    now = datetime.now(timezone.utc)
    recent_cutoff = (now - timedelta(hours=3)).isoformat()
    baseline_cutoff = (now - timedelta(hours=24)).isoformat()

    recent_rows = conn.execute(
        "SELECT concepts FROM stories WHERE scraped_at > ?", (recent_cutoff,)
    ).fetchall()
    baseline_rows = conn.execute(
        "SELECT concepts FROM stories WHERE scraped_at > ? AND scraped_at <= ?",
        (baseline_cutoff, recent_cutoff),
    ).fetchall()
    conn.close()

    def count_concepts(rows):
        counts = {}
        total = len(rows)
        for row in rows:
            try:
                concepts = json.loads(row["concepts"] or "[]")
                for c in concepts:
                    counts[c] = counts.get(c, 0) + 1
            except (json.JSONDecodeError, TypeError):
                pass
        return counts, max(total, 1)

    recent_counts, recent_total = count_concepts(recent_rows)
    baseline_counts, baseline_total = count_concepts(baseline_rows)

    # Merge near-duplicate concept names (e.g. "china-economy" and "chinese-economy")
    def _normalize_concept(name):
        """Normalize concept for dedup: strip common suffixes, singular forms."""
        n = name.lower().replace("-", " ").strip()
        # Common prefix normalizations
        for old, new in [("chinese ", "china "), ("american ", "us "),
                         ("british ", "uk "), ("european ", "eu "),
                         ("indian ", "india "), ("russian ", "russia ")]:
            if n.startswith(old):
                n = new + n[len(old):]
        return n

    # Group by normalized name, sum counts
    norm_map = {}  # normalized -> (best_name, total_recent, total_baseline)
    for concept, recent_n in recent_counts.items():
        norm = _normalize_concept(concept)
        baseline_n = baseline_counts.get(concept, 0)
        if norm in norm_map:
            prev_name, prev_r, prev_b = norm_map[norm]
            # Keep the name with higher count
            best = concept if recent_n > prev_r else prev_name
            norm_map[norm] = (best, prev_r + recent_n, prev_b + baseline_n)
        else:
            norm_map[norm] = (concept, recent_n, baseline_n)

    trending = []
    for norm, (concept, recent_n, baseline_n) in norm_map.items():
        recent_rate = recent_n / recent_total
        baseline_rate = baseline_n / baseline_total if baseline_total > 0 else 0

        # Spike ratio: how much higher is the recent rate vs baseline
        if baseline_rate > 0:
            spike = recent_rate / baseline_rate
        elif recent_n >= 2:
            spike = 5.0  # New concept appearing multiple times
        else:
            spike = 1.0

        if spike >= 1.3 or (baseline_rate == 0 and recent_n >= 2):
            trending.append({
                "name": concept,
                "spike": round(spike, 2),
                "recent_count": recent_n,
                "baseline_count": baseline_n,
                "color": _topic_color(concept),
            })

    trending.sort(key=lambda x: x["spike"], reverse=True)
    return {"trending": trending[:15], "recent_stories": recent_total}


@app.get("/api/stats")
async def api_stats():
    """Return database statistics."""
    conn = get_connection()
    stats = get_stats(conn)
    conn.close()
    return JSONResponse(
        content=stats,
        headers={"Cache-Control": "public, max-age=60"},
    )


@app.get("/api/feed.rss")
async def api_rss_feed(situation: Optional[int] = Query(None)):
    """RSS 2.0 feed of recent stories, optionally filtered to a situation."""
    from xml.sax.saxutils import escape as xml_escape
    conn = get_connection()

    feed_title = "thisminute — global news, live"
    feed_desc = "Real-time global news from 80+ sources, aggregated and mapped."
    feed_link = "https://thisminute.org"

    if situation:
        narr = get_narrative_by_id(conn, situation)
        if narr:
            # Get story IDs via narrative → events → event_stories
            story_ids = conn.execute(
                """SELECT DISTINCT es.story_id FROM narrative_events ne
                   JOIN event_stories es ON ne.event_id = es.event_id
                   WHERE ne.narrative_id = ?""",
                (situation,),
            ).fetchall()
            sids = [r["story_id"] for r in story_ids]
            if sids:
                placeholders = ",".join("?" for _ in sids)
                rows = conn.execute(
                    f"""SELECT title, url, source, summary, scraped_at, location_name
                        FROM stories WHERE id IN ({placeholders})
                        ORDER BY scraped_at DESC LIMIT 50""",
                    sids,
                ).fetchall()
            else:
                rows = []
            feed_title = f"{narr['title']} — thisminute"
            feed_desc = narr.get("description") or feed_desc
            feed_link = f"https://thisminute.org/?sit={situation}"
        else:
            rows = []
    else:
        rows = conn.execute(
            """SELECT title, url, source, summary, scraped_at, location_name
               FROM stories WHERE scraped_at > datetime('now', '-1 day')
               ORDER BY scraped_at DESC LIMIT 50"""
        ).fetchall()
    conn.close()

    items = []
    for r in rows:
        title = xml_escape(r["title"] or "Untitled")
        link = xml_escape(r["url"] or "")
        source = xml_escape(r["source"] or "")
        desc = xml_escape(r["summary"] or "")[:500]
        pub = r["scraped_at"] or ""
        loc = xml_escape(r["location_name"] or "")
        loc_tag = f"<category>{loc}</category>" if loc else ""
        items.append(f"""<item>
  <title>{title}</title>
  <link>{link}</link>
  <description>{desc}</description>
  <source>{source}</source>
  <pubDate>{pub}</pubDate>
  {loc_tag}
  <guid isPermaLink="true">{link}</guid>
</item>""")

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>{xml_escape(feed_title)}</title>
  <link>{xml_escape(feed_link)}</link>
  <description>{xml_escape(feed_desc)}</description>
  <language>en</language>
  <lastBuildDate>{datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")}</lastBuildDate>
  {"".join(items)}
</channel>
</rss>"""

    return Response(content=rss, media_type="application/rss+xml",
                    headers={"Cache-Control": "public, max-age=300"})


import re

_STOP_WORDS = frozenset(
    "a an the and or but in on at to for of is it its by from with as be was "
    "were are been has had have will would could should may might shall this "
    "that these those he she they his her their our your my me we us you what "
    "which who whom how when where why than not no nor so if do does did can "
    "about after all also any been before being between both each few into just "
    "more most new now only other out over own same some still such then there "
    "through too under up very says said say over here why get got way go going "
    "news live video watch read make made first year years old much many well "
    "back take takes set sets hit hits come comes keep keeps".split()
)


def _extract_keywords(titles: list[str], max_phrases: int = 12) -> list[dict]:
    """Extract meaningful phrases from story titles, preferring bigrams.

    Extracts 2-word phrases first (e.g. "World Cup", "Israeli strikes"),
    then fills with standalone words not already covered by a phrase.
    """
    bigram_counts = {}
    unigram_counts = {}

    for title in titles:
        # Tokenize preserving original positions
        tokens = re.findall(r"[A-Za-z'\-]{3,}", title)

        seen_bi = set()
        seen_uni = set()

        # Bigrams from ORIGINALLY adjacent words where BOTH are significant
        for j in range(len(tokens) - 1):
            w1, w2 = tokens[j], tokens[j + 1]
            if w1.lower().rstrip("'s") in _STOP_WORDS:
                continue
            if w2.lower().rstrip("'s") in _STOP_WORDS:
                continue
            phrase = f"{w1} {w2}"
            key = phrase.lower()
            if key not in seen_bi:
                seen_bi.add(key)
                if key not in bigram_counts:
                    bigram_counts[key] = {"phrase": phrase, "count": 0}
                bigram_counts[key]["count"] += 1

        # Unigrams
        for w in tokens:
            if w.lower().rstrip("'s") in _STOP_WORDS:
                continue
            key = w.lower()
            if key not in seen_uni:
                seen_uni.add(key)
                if key not in unigram_counts:
                    unigram_counts[key] = {"phrase": w, "count": 0}
                unigram_counts[key]["count"] += 1

    # Rank bigrams: keep those appearing 2+ times
    good_bigrams = sorted(
        [b for b in bigram_counts.values() if b["count"] >= 2],
        key=lambda x: x["count"], reverse=True,
    )

    results = []
    covered_words = set()  # words already represented by a bigram

    for b in good_bigrams:
        if len(results) >= max_phrases:
            break
        results.append({"word": b["phrase"], "count": b["count"]})
        for w in b["phrase"].lower().split():
            covered_words.add(w)

    # Fill remaining slots with unigrams not covered by bigrams
    remaining_unis = sorted(
        [u for u in unigram_counts.values()
         if u["phrase"].lower() not in covered_words and u["count"] >= 2],
        key=lambda x: x["count"], reverse=True,
    )
    for u in remaining_unis:
        if len(results) >= max_phrases:
            break
        results.append({"word": u["phrase"], "count": u["count"]})

    return results


@app.get("/api/events")
async def api_events(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100),
    min_stories: int = Query(2, ge=1, le=100, description="Minimum stories per event"),
):
    """Return active events with sample stories and keywords."""
    import time as _time
    is_default = (status is None and limit == 20 and min_stories == 2)
    now = _time.time()
    if is_default and _events_cache["data"] and now < _events_cache["expires"]:
        return JSONResponse(
            content=_events_cache["data"],
            headers={"Cache-Control": "public, max-age=60"},
        )
    conn = get_connection()
    events = get_all_events(conn, status=status, limit=limit, min_stories=min_stories)

    from collections import Counter, defaultdict

    event_ids = [e["id"] for e in events]
    if not event_ids:
        conn.close()
        return JSONResponse(
            content={"events": []},
            headers={"Cache-Control": "public, max-age=60"},
        )

    placeholders = ",".join("?" * len(event_ids))

    # Batch: narrative links for all events
    narr_rows = conn.execute(
        f"SELECT event_id, narrative_id FROM narrative_events WHERE event_id IN ({placeholders})",
        event_ids,
    ).fetchall()
    narr_map = defaultdict(list)
    for r in narr_rows:
        narr_map[r["event_id"]].append(r["narrative_id"])

    # Batch: all story_ids for all events
    es_rows = conn.execute(
        f"SELECT event_id, story_id FROM event_stories WHERE event_id IN ({placeholders})",
        event_ids,
    ).fetchall()
    es_map = defaultdict(list)
    for r in es_rows:
        es_map[r["event_id"]].append(r["story_id"])

    # Batch: fetch all stories for all events in one query (replaces N+1 get_event_stories calls)
    story_rows = conn.execute(
        f"""SELECT es.event_id, s.id, s.title, s.url, s.source, s.scraped_at, s.sentiment
            FROM event_stories es
            JOIN stories s ON s.id = es.story_id
            WHERE es.event_id IN ({placeholders})
            ORDER BY s.scraped_at DESC""",
        event_ids,
    ).fetchall()
    stories_by_event = defaultdict(list)
    for r in story_rows:
        stories_by_event[r["event_id"]].append(dict(r))

    result = []
    for event in events:
        eid = event["id"]
        # Parse JSON fields
        for field in ("key_actors", "concepts", "related_events", "affected_parties"):
            val = event.get(field, "[]")
            if isinstance(val, str):
                try:
                    event[field] = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    event[field] = []

        all_stories = stories_by_event.get(eid, [])
        all_titles = [s["title"] for s in all_stories if s.get("title")]
        event["keywords"] = _extract_keywords(all_titles)
        event["source_count"] = len({s["source"] for s in all_stories if s.get("source")})

        # Aggregate sentiment from stories
        sentiments = [s.get("sentiment") for s in all_stories if s.get("sentiment")]
        if sentiments:
            sent_counts = Counter(sentiments)
            event["sentiment"] = sent_counts.most_common(1)[0][0]
            event["sentiment_counts"] = dict(sent_counts)
        else:
            event["sentiment"] = None
            event["sentiment_counts"] = {}

        event["narrative_ids"] = narr_map.get(eid, [])
        event["story_ids"] = es_map.get(eid, [])
        event["sample_stories"] = [
            {
                "id": s["id"],
                "title": s["title"],
                "url": s["url"],
                "source": s["source"],
                "scraped_at": s["scraped_at"],
            }
            for s in all_stories[:5]
        ]
        result.append(event)

    conn.close()
    response_data = {"events": result}
    if is_default:
        _events_cache["data"] = response_data
        _events_cache["expires"] = now + 60  # 1 min cache
    return JSONResponse(
        content=response_data,
        headers={"Cache-Control": "public, max-age=60"},
    )


@app.get("/api/events/{event_id}")
async def api_event_detail(event_id: int):
    """Return full event detail with all stories."""
    conn = get_connection()
    event = get_event_by_id(conn, event_id)
    if not event:
        conn.close()
        return {"error": "Event not found"}

    # Parse JSON fields
    for field in ("key_actors", "concepts", "related_events"):
        val = event.get(field, "[]")
        if isinstance(val, str):
            try:
                event[field] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                event[field] = []

    stories = get_event_stories(conn, event_id, limit=50)
    # Bulk fetch bright_side data for these stories
    story_ids_list = [s["id"] for s in stories]
    bs_map = {}
    if story_ids_list:
        ph = ",".join("?" * len(story_ids_list))
        bs_rows = conn.execute(
            f"SELECT story_id, bright_side_score, bright_side_category, bright_side_headline FROM story_extractions WHERE story_id IN ({ph})",
            story_ids_list,
        ).fetchall()
        for r in bs_rows:
            bs_map[r["story_id"]] = dict(r)

    event["stories"] = []
    for s in stories:
        story_concepts = s.get("concepts", "[]")
        if isinstance(story_concepts, str):
            try:
                story_concepts = json.loads(story_concepts)
            except (json.JSONDecodeError, TypeError):
                story_concepts = []
        bs = bs_map.get(s["id"], {})
        event["stories"].append({
            "id": s["id"],
            "title": s["title"],
            "url": s["url"],
            "summary": s.get("summary"),
            "source": s["source"],
            "location_name": s.get("location_name"),
            "lat": s.get("lat"),
            "lon": s.get("lon"),
            "concepts": story_concepts,
            "scraped_at": s["scraped_at"],
            "published_at": s.get("published_at"),
            "image_url": s.get("image_url"),
            "bright_side_score": bs.get("bright_side_score"),
            "bright_side_category": bs.get("bright_side_category"),
            "bright_side_headline": bs.get("bright_side_headline"),
        })

    conn.close()
    return event


@app.get("/api/registry")
async def api_registry(
    limit: int = Query(100, ge=1, le=500),
):
    """Return active event registry with map labels for map display."""
    conn = get_connection()
    events = get_active_registry_events(conn, limit=limit)
    conn.close()
    return {"registry": events}


@app.get("/api/wiki-events")
async def api_wiki_events(
    limit: int = Query(100, ge=1, le=500),
):
    """Return active Wikipedia event articles with story counts."""
    conn = get_connection()
    try:
        from .database import get_active_wiki_events
        events = get_active_wiki_events(conn, limit=limit)
    except Exception:
        events = []
    conn.close()
    return {"wiki_events": events}


@app.get("/api/world-overview")
async def api_world_overview():
    """Return the current world overview."""
    conn = get_connection()
    overview = get_world_overview(conn)
    conn.close()
    if not overview:
        return {"summary": None, "generated_at": None, "top_events": []}

    top = overview.get("top_events", "[]")
    if isinstance(top, str):
        try:
            top = json.loads(top)
        except (json.JSONDecodeError, TypeError):
            top = []

    return {
        "summary": overview.get("summary"),
        "generated_at": overview.get("generated_at"),
        "top_events": top,
    }


# ==================== SEARCH ====================

@app.get("/api/search")
async def api_search(
    actor_role: Optional[str] = Query(None, description="Actor role: perpetrator/victim/authority/witness/participant/target"),
    actor_name: Optional[str] = Query(None, description="Actor name (partial match)"),
    actor_demographic: Optional[str] = Query(None, description="Actor demographic (partial match)"),
    action: Optional[str] = Query(None, description="Primary action (e.g. 'airstrike', 'arrested')"),
    topic: Optional[str] = Query(None, description="Topic tag"),
    severity_min: Optional[int] = Query(None, ge=1, le=5, description="Minimum severity (1-5)"),
    location_type: Optional[str] = Query(None, description="Location type: terrestrial/space/internet/abstract"),
    search: Optional[str] = Query(None, description="Free text search"),
    limit: int = Query(200, ge=1, le=1000),
):
    """Multi-dimensional search across stories, actors, and extractions."""
    conn = get_connection()
    stories = search_stories_multi(
        conn,
        actor_role=actor_role,
        actor_name=actor_name,
        actor_demographic=actor_demographic,
        action=action,
        topic=topic,
        severity_min=severity_min,
        location_type=location_type,
        search=search,
        limit=limit,
    )

    # Batch fetch extractions and actors for all story IDs
    story_ids = [s["id"] for s in stories]
    extraction_map = {}
    actor_map = {}
    if story_ids:
        placeholders = ",".join("?" * len(story_ids))
        ext_rows = conn.execute(
            f"SELECT * FROM story_extractions WHERE story_id IN ({placeholders})", story_ids
        ).fetchall()
        for r in ext_rows:
            extraction_map[r["story_id"]] = dict(r)
        act_rows = conn.execute(
            f"SELECT * FROM story_actors WHERE story_id IN ({placeholders})", story_ids
        ).fetchall()
        for r in act_rows:
            actor_map.setdefault(r["story_id"], []).append(dict(r))

    features = []
    for s in stories:
        story_concepts = s.get("concepts", "[]")
        if isinstance(story_concepts, str):
            try:
                story_concepts = json.loads(story_concepts)
            except (json.JSONDecodeError, TypeError):
                story_concepts = []

        extraction = extraction_map.get(s["id"])
        actors = actor_map.get(s["id"], [])

        props = {
            "id": s["id"],
            "title": s["title"],
            "url": s["url"],
            "summary": s["summary"],
            "source": s["source"],
            "category": s.get("category", "general"),
            "concepts": story_concepts,
            "location_name": s.get("location_name"),
            "published_at": s.get("published_at"),
            "scraped_at": s["scraped_at"],
            "sentiment": s.get("sentiment"),
            "actors": [{"name": a["name"], "role": a["role"], "type": a.get("type"), "demographic": a.get("demographic")} for a in actors],
        }

        if extraction:
            props["severity"] = extraction.get("severity")
            props["primary_action"] = extraction.get("primary_action")
            props["topics"] = json.loads(extraction.get("topics", "[]")) if isinstance(extraction.get("topics"), str) else extraction.get("topics", [])

        if s.get("lat") is not None and s.get("lon") is not None:
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [s["lon"], s["lat"]]},
                "properties": props,
            })
        else:
            features.append({
                "type": "Feature",
                "geometry": None,
                "properties": props,
            })

    conn.close()
    return {"type": "FeatureCollection", "features": features, "total": len(features)}


# ==================== NARRATIVES ====================

@app.get("/api/narratives")
async def api_narratives(
    limit: int = Query(60, ge=1, le=200),
):
    """Return active narratives with linked event counts."""
    import time as _time
    is_default = (limit == 60)
    now = _time.time()
    if is_default and _narratives_cache["data"] and now < _narratives_cache["expires"]:
        return JSONResponse(
            content=_narratives_cache["data"],
            headers={"Cache-Control": "public, max-age=120"},
        )
    conn = get_connection()
    narratives = get_active_narratives(conn, limit=limit)

    from collections import defaultdict

    narr_ids = [n["id"] for n in narratives]
    if not narr_ids:
        conn.close()
        return JSONResponse(
            content={"narratives": []},
            headers={"Cache-Control": "public, max-age=120"},
        )

    placeholders = ",".join("?" * len(narr_ids))

    # Batch: get all linked events for all narratives
    event_rows = conn.execute(
        f"""SELECT ne.narrative_id, ne.relevance_score, e.*
            FROM narrative_events ne
            JOIN events e ON e.id = ne.event_id
            WHERE ne.narrative_id IN ({placeholders})
            ORDER BY ne.relevance_score DESC""",
        narr_ids,
    ).fetchall()
    events_map = defaultdict(list)
    for r in event_rows:
        events_map[r["narrative_id"]].append(dict(r))

    # Batch: get story IDs and sources for all narratives (2 joins instead of 4)
    story_rows = conn.execute(
        f"""SELECT DISTINCT ne.narrative_id, es.story_id, s.source
            FROM narrative_events ne
            JOIN event_stories es ON es.event_id = ne.event_id
            JOIN stories s ON s.id = es.story_id
            WHERE ne.narrative_id IN ({placeholders})""",
        narr_ids,
    ).fetchall()
    story_data_map = defaultdict(list)
    all_story_ids_set = set()
    for r in story_rows:
        story_data_map[r["narrative_id"]].append(r)
        all_story_ids_set.add(r["story_id"])

    # Batch: get bright_side scores separately (lighter query)
    bs_map = {}
    if all_story_ids_set:
        bs_ph = ",".join("?" * len(all_story_ids_set))
        bs_rows = conn.execute(
            f"SELECT story_id, bright_side_score FROM story_extractions WHERE story_id IN ({bs_ph}) AND bright_side_score IS NOT NULL",
            list(all_story_ids_set),
        ).fetchall()
        for r in bs_rows:
            bs_map[r["story_id"]] = r["bright_side_score"]

    result = []
    for n in narratives:
        theme_tags = n.get("theme_tags", "[]")
        if isinstance(theme_tags, str):
            try:
                theme_tags = json.loads(theme_tags)
            except (json.JSONDecodeError, TypeError):
                theme_tags = []

        events = events_map.get(n["id"], [])
        narr_story_rows = story_data_map.get(n["id"], [])
        narr_story_ids = list({r["story_id"] for r in narr_story_rows})
        bright_count = sum(1 for sid in narr_story_ids
                          if bs_map.get(sid) and int(bs_map[sid]) >= 4)
        source_count = len({r["source"] for r in narr_story_rows if r["source"]})

        result.append({
            "id": n["id"],
            "title": n["title"],
            "description": n.get("description"),
            "status": n.get("status", "active"),
            "theme_tags": theme_tags,
            "domain": n.get("domain", "news"),
            "event_count": n.get("event_count", 0),
            "story_count": len(narr_story_ids),
            "source_count": source_count,
            "bright_side_count": bright_count,
            "story_ids": narr_story_ids,
            "first_seen": n.get("first_seen"),
            "last_updated": n.get("last_updated"),
            "events": [
                {
                    "id": e["id"],
                    "title": e["title"],
                    "status": e.get("status"),
                    "story_count": e.get("story_count", 0),
                    "primary_location": e.get("primary_location"),
                    "primary_lat": e.get("primary_lat"),
                    "primary_lon": e.get("primary_lon"),
                    "relevance_score": e.get("relevance_score", 1.0),
                    "last_updated": e.get("last_updated"),
                }
                for e in events[:10]
            ],
        })

    conn.close()
    response_data = {"narratives": result}
    if is_default:
        _narratives_cache["data"] = response_data
        _narratives_cache["expires"] = now + 120  # 2 min cache
    return JSONResponse(
        content=response_data,
        headers={"Cache-Control": "public, max-age=120"},
    )


@app.get("/api/narratives/{narrative_id}")
async def api_narrative_detail(narrative_id: int):
    """Return full narrative detail with events and their stories."""
    conn = get_connection()
    narrative = get_narrative_by_id(conn, narrative_id)
    if not narrative:
        conn.close()
        return {"error": "Narrative not found"}

    theme_tags = narrative.get("theme_tags", "[]")
    if isinstance(theme_tags, str):
        try:
            theme_tags = json.loads(theme_tags)
        except (json.JSONDecodeError, TypeError):
            theme_tags = []

    events = get_narrative_events(conn, narrative_id)
    event_ids = [e["id"] for e in events]
    events_with_stories = []
    for e in events:
        events_with_stories.append({
            "id": e["id"],
            "title": e["title"],
            "description": e.get("description"),
            "status": e.get("status"),
            "story_count": e.get("story_count", 0),
            "primary_location": e.get("primary_location"),
            "primary_lat": e.get("primary_lat"),
            "primary_lon": e.get("primary_lon"),
            "severity": e.get("severity"),
            "relevance_score": e.get("relevance_score", 1.0),
        })
    # Batch-fetch all stories for all events in one query (replaces N+1)
    all_stories = []
    seen_story_ids = set()
    if event_ids:
        ph = ",".join("?" * len(event_ids))
        rows = conn.execute(
            f"""SELECT DISTINCT s.* FROM stories s
                JOIN event_stories es ON s.id = es.story_id
                WHERE es.event_id IN ({ph})
                ORDER BY s.scraped_at DESC""",
            event_ids,
        ).fetchall()
        for r in rows:
            s = dict(r)
            if s["id"] not in seen_story_ids:
                seen_story_ids.add(s["id"])
                all_stories.append(s)
    # Sort by recency
    all_stories.sort(key=lambda s: s.get("scraped_at") or "", reverse=True)
    # Bulk fetch bright_side data
    narr_story_ids = [s["id"] for s in all_stories]
    bs_map = {}
    if narr_story_ids:
        ph = ",".join("?" * len(narr_story_ids))
        bs_rows = conn.execute(
            f"SELECT story_id, bright_side_score, bright_side_category, bright_side_headline FROM story_extractions WHERE story_id IN ({ph})",
            narr_story_ids,
        ).fetchall()
        for r in bs_rows:
            bs_map[r["story_id"]] = dict(r)
    all_stories = [{
        "id": s["id"], "title": s["title"], "url": s["url"],
        "source": s["source"], "summary": s.get("summary"),
        "location_name": s.get("location_name"),
        "lat": s.get("lat"), "lon": s.get("lon"),
        "scraped_at": s["scraped_at"],
        "published_at": s.get("published_at"),
        "image_url": s.get("image_url"),
        "bright_side_score": bs_map.get(s["id"], {}).get("bright_side_score"),
        "bright_side_category": bs_map.get(s["id"], {}).get("bright_side_category"),
        "bright_side_headline": bs_map.get(s["id"], {}).get("bright_side_headline"),
    } for s in all_stories]

    conn.close()
    return {
        "id": narrative["id"],
        "title": narrative["title"],
        "description": narrative.get("description"),
        "status": narrative.get("status"),
        "theme_tags": theme_tags,
        "event_count": narrative.get("event_count", 0),
        "story_count": len(all_stories),
        "first_seen": narrative.get("first_seen"),
        "last_updated": narrative.get("last_updated"),
        "events": events_with_stories,
        "stories": all_stories,
    }


# ==================== TOPICS & ACTORS ====================

_topics_cache = {"data": None, "expires": 0}

@app.get("/api/topics")
async def api_topics():
    """Return emergent topics from LLM extraction with counts."""
    import time as _time
    now = _time.time()
    if _topics_cache["data"] and now < _topics_cache["expires"]:
        return JSONResponse(
            content=_topics_cache["data"],
            headers={"Cache-Control": "public, max-age=1800"},
        )

    conn = get_connection()
    try:
        # Use SQLite JSON functions to extract and count topics in SQL
        rows = conn.execute(
            """SELECT j.value as topic, COUNT(*) as count
               FROM stories, json_each(stories.concepts) j
               WHERE stories.scraped_at > datetime('now', '-3 days')
               AND stories.concepts IS NOT NULL AND stories.concepts != '[]'
               GROUP BY j.value
               ORDER BY count DESC
               LIMIT 100"""
        ).fetchall()
        result = [{"name": r["topic"], "count": r["count"]} for r in rows]
    except Exception:
        # Fallback: parse JSON in Python if json_each not available
        raw = conn.execute(
            """SELECT concepts FROM stories
               WHERE scraped_at > datetime('now', '-3 days')
               AND concepts IS NOT NULL AND concepts != '[]'"""
        ).fetchall()
        counts = {}
        for row in raw:
            try:
                for t in json.loads(row["concepts"] or "[]"):
                    counts[t] = counts.get(t, 0) + 1
            except (json.JSONDecodeError, TypeError):
                pass
        sorted_topics = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        result = [{"name": name, "count": count} for name, count in sorted_topics[:100]]
    conn.close()
    response_data = {"topics": result}
    _topics_cache["data"] = response_data
    _topics_cache["expires"] = now + 1800  # 30 min
    return JSONResponse(
        content=response_data,
        headers={"Cache-Control": "public, max-age=1800"},  # 30 min
    )


@app.get("/api/actors")
async def api_actors(
    role: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    """Browse/search actors by role, type, demographic."""
    conn = get_connection()
    query = """
        SELECT name, role, type, demographic, COUNT(*) as story_count
        FROM story_actors
        WHERE 1=1
    """
    params = []
    if role:
        query += " AND role = ?"
        params.append(role)
    if type:
        query += " AND type = ?"
        params.append(type)
    if search:
        query += " AND name LIKE ?"
        params.append(f"%{search}%")
    query += " GROUP BY name, role ORDER BY story_count DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return {
        "actors": [
            {
                "name": r["name"],
                "role": r["role"],
                "type": r["type"],
                "demographic": r["demographic"],
                "story_count": r["story_count"],
            }
            for r in rows
        ],
    }


class FeedbackPayload(BaseModel):
    feedback_type: str
    target_type: str | None = None
    target_id: int | None = None
    target_title: str | None = None
    message: str = ""
    context: dict = {}
    browser_hash: str = ""


# In-memory rate limiter for feedback: max 5 per minute per browser_hash
_feedback_rate: dict[str, list[float]] = {}

@app.post("/api/feedback")
async def submit_feedback(payload: FeedbackPayload, request: Request):
    valid_types = {"doesnt_belong", "should_merge", "wrong_category", "general"}
    if payload.feedback_type not in valid_types:
        return JSONResponse({"error": "invalid type"}, status_code=400)
    # Rate limit: 5 per minute per browser_hash (or IP if no hash)
    import time
    key = payload.browser_hash[:64] or (request.client.host if request.client else "unknown")
    now = time.time()
    window = _feedback_rate.setdefault(key, [])
    window[:] = [t for t in window if now - t < 60]
    if len(window) >= 5:
        return JSONResponse({"error": "rate limited"}, status_code=429)
    window.append(now)
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO user_feedback
               (feedback_type, target_type, target_id, target_title,
                message, context_json, browser_hash, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)""",
            (payload.feedback_type, payload.target_type, payload.target_id,
             payload.target_title, payload.message[:1000],
             json.dumps(payload.context), payload.browser_hash[:64],
             datetime.now(timezone.utc).isoformat()))
        conn.commit()
    finally:
        conn.close()
    return {"status": "ok"}
