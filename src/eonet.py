"""NASA EONET (Earth Observatory Natural Event Tracker) integration.

Fetches active natural events (wildfires, volcanoes, storms, etc.) from the
NASA EONET v3 API. These are satellite/sensor-derived events with precise
coordinates. They skip LLM extraction because all structured data is
available directly from the EONET API.
"""

import logging
from datetime import datetime, timezone

from .config import REQUEST_TIMEOUT, EONET_URL
from .source_utils import (
    fetch_json, build_extraction, attach_location,
    polygon_centroid as _shared_polygon_centroid, current_year,
)

logger = logging.getLogger(__name__)

# EONET category -> our category
_CATEGORY_MAP = {
    "wildfires": "disaster",
    "volcanoes": "disaster",
    "severeStorms": "disaster",
    "floods": "disaster",
    "landslides": "disaster",
    "seaLakeIce": "environment",
    "dustHaze": "environment",
    "drought": "environment",
    "tempExtremes": "environment",
    "earthquakes": "disaster",
    "manmade": "disaster",
    "waterColor": "environment",
    "snow": "environment",
}

# EONET category -> concepts list
_CONCEPT_MAP = {
    "wildfires": ["wildfire"],
    "volcanoes": ["volcano"],
    "severeStorms": ["storm"],
    "floods": ["flood"],
    "landslides": ["landslide"],
    "seaLakeIce": ["ice", "climate"],
    "dustHaze": ["dust", "air quality"],
    "drought": ["drought"],
    "tempExtremes": ["extreme temperature"],
    "earthquakes": ["earthquake"],
    "manmade": ["industrial"],
    "waterColor": ["water"],
    "snow": ["snow"],
}

# EONET category -> severity (most natural events start at 2-3)
_SEVERITY_MAP = {
    "wildfires": 3,
    "volcanoes": 4,
    "severeStorms": 3,
    "floods": 3,
    "landslides": 3,
    "seaLakeIce": 1,
    "dustHaze": 2,
    "drought": 2,
    "tempExtremes": 2,
    "earthquakes": 3,
    "manmade": 2,
    "waterColor": 1,
    "snow": 1,
}

# EONET category -> human interest score
_HUMAN_INTEREST_MAP = {
    "wildfires": 6,
    "volcanoes": 7,
    "severeStorms": 5,
    "floods": 5,
    "landslides": 5,
    "seaLakeIce": 2,
    "dustHaze": 3,
    "drought": 4,
    "tempExtremes": 4,
    "earthquakes": 6,
    "manmade": 4,
    "waterColor": 1,
    "snow": 2,
}


def _get_category_id(event):
    """Extract the primary category ID from an EONET event."""
    categories = event.get("categories", [])
    if categories:
        return categories[0].get("id", "")
    return ""


def _get_category_title(event):
    """Extract the primary category title from an EONET event."""
    categories = event.get("categories", [])
    if categories:
        return categories[0].get("title", "")
    return ""


def _get_latest_geometry(event):
    """Extract lat/lon from the most recent geometry entry.

    Handles both Point ([lon, lat]) and Polygon coordinates.
    Returns (lat, lon) or (None, None).
    """
    geometries = event.get("geometry", [])
    if not geometries:
        return None, None

    # Sort by date descending to get most recent
    sorted_geoms = sorted(
        geometries,
        key=lambda g: g.get("date", ""),
        reverse=True,
    )

    latest = sorted_geoms[0]
    geom_type = latest.get("type", "")
    coords = latest.get("coordinates")

    if not coords:
        return None, None

    if geom_type == "Point":
        if isinstance(coords, list) and len(coords) >= 2:
            return coords[1], coords[0]  # [lon, lat] -> (lat, lon)
    elif geom_type == "Polygon":
        # Use centroid of first ring
        result = _shared_polygon_centroid(coords)
        if result:
            return result["lat"], result["lon"]

    return None, None


def _get_latest_date(event):
    """Get the most recent geometry date as ISO string."""
    geometries = event.get("geometry", [])
    if not geometries:
        return None
    dates = [g.get("date") for g in geometries if g.get("date")]
    if dates:
        return sorted(dates, reverse=True)[0]
    return None


def _build_event_url(event):
    """Build a URL for the EONET event."""
    sources = event.get("sources", [])
    if sources and sources[0].get("url"):
        return sources[0]["url"]
    event_id = event.get("id", "")
    if event_id:
        return "https://eonet.gsfc.nasa.gov/api/v3/events/%s" % event_id
    return ""


def _build_summary(event):
    """Build a descriptive summary from the EONET event."""
    title = event.get("title", "")
    cat_title = _get_category_title(event)
    latest_date = _get_latest_date(event)

    parts = []
    if cat_title:
        parts.append("%s event" % cat_title)
    if title:
        parts.append(title)
    if latest_date:
        # Extract just the date portion
        date_str = latest_date[:10] if len(latest_date) >= 10 else latest_date
        parts.append("Last observed: %s" % date_str)

    return ". ".join(parts) + "." if parts else "Natural event detected by NASA EONET."


def _build_event_signature(event):
    """Build an event_signature for clustering."""
    title = event.get("title", "")
    year = current_year()
    cat_title = _get_category_title(event)

    # Try to use the event title directly since EONET titles are descriptive
    if title:
        # Truncate to reasonable length for signature
        sig = title if len(title) <= 60 else title[:57] + "..."
        return "%s %s" % (year, sig)
    return "%s %s Event" % (year, cat_title or "Natural")


def _fetch_events():
    """Fetch active events from EONET API."""
    return fetch_json(EONET_URL, key="events")


def scrape_eonet():
    """Fetch EONET events and return story dicts.

    Returns list of story dicts compatible with pipeline.process_story(),
    with pre-populated location, concept, and extraction data.
    EONET stories skip LLM extraction because all structured data is
    available directly from the EONET API.
    """
    now = datetime.now(timezone.utc).isoformat()
    events = _fetch_events()

    seen_ids = set()
    stories = []

    for event in events:
        try:
            event_id = event.get("id", "")
            if not event_id or event_id in seen_ids:
                continue
            seen_ids.add(event_id)

            title = event.get("title", "")
            if not title:
                continue

            url = _build_event_url(event)
            if not url:
                continue

            lat, lon = _get_latest_geometry(event)
            cat_id = _get_category_id(event)

            category = _CATEGORY_MAP.get(cat_id, "disaster")
            concepts = _CONCEPT_MAP.get(cat_id, ["natural event"])
            severity = _SEVERITY_MAP.get(cat_id, 2)
            hi_score = _HUMAN_INTEREST_MAP.get(cat_id, 3)

            summary = _build_summary(event)
            event_sig = _build_event_signature(event)
            published_at = _get_latest_date(event)

            # Location name from title
            location_name = title

            story = {
                "title": title,
                "url": url,
                "summary": summary,
                "source": "NASA EONET",
                "published_at": published_at,
                "scraped_at": now,
                "origin": "eonet",
                "source_type": "inferred",
                "category": category,
                "concepts": concepts,
                "location_name": location_name,
                "geocode_confidence": 0.8,
            }

            extraction_locations = attach_location(
                story, lat, lon, location_name)

            topics = list(concepts)  # copy
            if category == "disaster" and "disaster" not in topics:
                topics.append("disaster")

            story["_extraction"] = build_extraction(
                event_sig=event_sig,
                topics=topics,
                severity=severity,
                sentiment="negative",
                primary_action=cat_id or "natural event",
                hi_score=hi_score,
                locations=extraction_locations,
                search_keywords=[cat_id, title],
            )

            stories.append(story)
        except Exception as e:
            logger.error("Error processing EONET event: %s", e)
            continue

    logger.info("EONET: fetched %d natural events", len(stories))
    return stories
