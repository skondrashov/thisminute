"""NOAA Severe Weather Alerts integration for statistical inference events.

Fetches active severe weather alerts from the NOAA Weather API (US-only).
Unlike news stories, these are government-issued alerts with structured data
(severity, affected area, event type). They skip LLM extraction because all
structured data is already available from the NOAA API.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from .config import REQUEST_TIMEOUT, NOAA_ALERTS_URL, NOAA_MAX_ALERTS
from .source_utils import (
    fetch_json, dedup_list, build_extraction, attach_location,
    polygon_centroid as _shared_polygon_centroid, current_year,
)

logger = logging.getLogger(__name__)

# NOAA severity -> our 1-5 severity scale
_SEVERITY_MAP = {
    "Minor": 1,
    "Moderate": 2,
    "Severe": 3,
    "Extreme": 4,
}

# NOAA severity -> human interest score (1-10)
_HUMAN_INTEREST_MAP = {
    "Minor": 2,
    "Moderate": 4,
    "Severe": 6,
    "Extreme": 8,
}

# NOAA event type -> additional concepts
_EVENT_CONCEPTS = {
    "tornado": ["tornado"],
    "flood": ["flood"],
    "hurricane": ["hurricane"],
    "tropical storm": ["hurricane"],
    "typhoon": ["hurricane"],
    "winter storm": ["winter storm"],
    "blizzard": ["winter storm"],
    "ice storm": ["winter storm"],
    "thunderstorm": ["thunderstorm"],
    "hail": ["thunderstorm"],
    "fire": ["wildfire"],
    "wildfire": ["wildfire"],
    "red flag": ["wildfire"],
    "tsunami": ["tsunami"],
    "volcano": ["volcano"],
    "avalanche": ["avalanche"],
    "dust storm": ["dust storm"],
    "heat": ["heat wave"],
    "excessive heat": ["heat wave"],
    "cold": ["cold wave"],
    "wind chill": ["cold wave"],
    "freeze": ["cold wave"],
    "wind": ["wind"],
    "high wind": ["wind"],
    "dense fog": ["fog"],
}


def _severity_to_score(severity: str) -> int:
    """Map NOAA severity string to our 1-5 scale."""
    return _SEVERITY_MAP.get(severity, 2)


def _severity_to_human_interest(severity: str) -> int:
    """Map NOAA severity string to human interest score (1-10)."""
    return _HUMAN_INTEREST_MAP.get(severity, 3)


def _get_event_concepts(event_type: str) -> list:
    """Get additional concepts based on NOAA event type."""
    event_lower = event_type.lower()
    for key, concepts in _EVENT_CONCEPTS.items():
        if key in event_lower:
            return concepts
    return []


def _polygon_centroid(coordinates: list) -> Optional[dict]:
    """Calculate the centroid of a polygon from GeoJSON coordinates.

    Delegates to source_utils.polygon_centroid.
    """
    return _shared_polygon_centroid(coordinates)


def _geometry_to_point(geometry: dict) -> Optional[dict]:
    """Extract a lat/lon point from NOAA geometry.

    NOAA returns polygons (affected area). We calculate the centroid.
    Also handles Point and MultiPolygon geometries.
    """
    if not geometry:
        return None

    geom_type = geometry.get("type", "")
    coords = geometry.get("coordinates")

    if not coords:
        return None

    if geom_type == "Point":
        if len(coords) >= 2:
            return {"lat": coords[1], "lon": coords[0]}

    elif geom_type == "Polygon":
        return _polygon_centroid(coords)

    elif geom_type == "MultiPolygon":
        # Use centroid of the first polygon
        if coords and coords[0]:
            return _polygon_centroid(coords[0])

    return None


def _build_title(props: dict) -> str:
    """Build a title from NOAA alert properties.

    Prefers headline; falls back to event + areaDesc.
    """
    headline = props.get("headline", "").strip()
    if headline:
        return headline

    event = props.get("event", "Weather Alert")
    area = props.get("areaDesc", "")
    if area:
        # Truncate long area descriptions
        if len(area) > 100:
            area = area[:97] + "..."
        return "%s - %s" % (event, area)
    return event


def _build_summary(props: dict) -> str:
    """Build a summary from NOAA alert description.

    Uses first 500 chars of the description field.
    """
    desc = props.get("description", "").strip()
    if not desc:
        # Fall back to instruction field
        desc = props.get("instruction", "").strip()
    if not desc:
        event = props.get("event", "Weather alert")
        area = props.get("areaDesc", "unknown area")
        severity = props.get("severity", "")
        return "%s for %s. Severity: %s." % (event, area, severity)

    if len(desc) > 500:
        desc = desc[:497] + "..."
    return desc


def _build_event_signature(props: dict) -> str:
    """Build an event_signature for clustering.

    Groups by event type + region for broader clustering.
    Example: '2026 US Tornado Season' or '2026 Texas Winter Storm'
    """
    event = props.get("event", "Weather Alert")
    area = props.get("areaDesc", "")
    year = current_year()

    # Extract a region from areaDesc (typically "County, ST" or "Area; Area")
    # Use the state abbreviation or first meaningful region name
    region = "US"
    if area:
        # Try to find a US state abbreviation (2 uppercase letters after comma/semicolon)
        parts = area.replace(";", ",").split(",")
        for part in parts:
            stripped = part.strip()
            if len(stripped) == 2 and stripped.isupper():
                region = stripped
                break
            elif len(stripped) > 2:
                region = stripped
                break

    # Simplify event type for signature
    event_simple = event.replace(" Warning", "").replace(" Watch", "").replace(" Advisory", "")

    return "%s %s %s" % (year, region, event_simple)


def _extract_region_name(area_desc: str) -> str:
    """Extract a location name from NOAA areaDesc for geocoding."""
    if not area_desc:
        return "United States"
    # areaDesc is typically "County, ST; County2, ST"
    # Take the first entry
    first = area_desc.split(";")[0].strip()
    return first if first else "United States"


def _fetch_alerts() -> list:
    """Fetch active NOAA weather alerts and return GeoJSON features."""
    return fetch_json(
        NOAA_ALERTS_URL,
        key="features",
        user_agent="(thisminute.org, contact@thisminute.org)",
        headers={"Accept": "application/geo+json"},
    )


def _severity_sort_key(feature):
    """Sort key for NOAA features: Extreme first, then Severe, Moderate, Minor.

    Returns a numeric value where lower = higher priority.
    """
    sev = feature.get("properties", {}).get("severity", "Moderate")
    order = {"Extreme": 0, "Severe": 1, "Moderate": 2, "Minor": 3}
    return order.get(sev, 4)


def scrape_noaa() -> list:
    """Fetch NOAA weather alerts and return story dicts.

    Returns list of story dicts compatible with pipeline.process_story(),
    with pre-populated location, concept, and extraction data.
    NOAA stories skip LLM extraction because all structured data is
    available directly from the NOAA API.

    Alerts are sorted by severity (Extreme/Severe first) and capped at
    NOAA_MAX_ALERTS to prevent unbounded volume during severe weather
    outbreaks.
    """
    now = datetime.now(timezone.utc).isoformat()
    features = _fetch_alerts()

    # Sort by severity (most severe first) and cap
    features = sorted(features, key=_severity_sort_key)
    if len(features) > NOAA_MAX_ALERTS:
        logger.warning(
            "NOAA: %d alerts exceed cap of %d, keeping most severe",
            len(features), NOAA_MAX_ALERTS)
        features = features[:NOAA_MAX_ALERTS]

    # Dedup by alert ID (properties.id)
    seen_ids = set()
    stories = []

    for feature in features:
        try:
            props = feature.get("properties", {})
            alert_id = props.get("id", "")
            if not alert_id or alert_id in seen_ids:
                continue
            seen_ids.add(alert_id)

            # Build title
            title = _build_title(props)
            if not title:
                continue

            # Use the alert ID as the URL (it's a full URL)
            url = alert_id

            # Get lat/lon from geometry
            geometry = feature.get("geometry")
            point = _geometry_to_point(geometry) if geometry else None

            # Build other fields
            summary = _build_summary(props)
            severity_str = props.get("severity", "Moderate")
            severity = _severity_to_score(severity_str)
            hi_score = _severity_to_human_interest(severity_str)
            event_type = props.get("event", "Weather Alert")
            area_desc = props.get("areaDesc", "")

            # Published time from onset or sent
            published_at = props.get("onset") or props.get("sent")

            # Location
            location_name = _extract_region_name(area_desc)

            # Concepts
            extra_concepts = _get_event_concepts(event_type)
            concepts = dedup_list(["weather", "disaster"] + extra_concepts)

            # Determine category based on severity
            category = "disaster" if severity >= 3 else "weather"

            story = {
                "title": title,
                "url": url,
                "summary": summary,
                "source": "NOAA Weather",
                "published_at": published_at,
                "scraped_at": now,
                "origin": "noaa",
                "source_type": "inferred",
                "category": category,
                "concepts": concepts,
                "location_name": location_name,
                "geocode_confidence": 0.8,
            }

            if point:
                extraction_locations = attach_location(
                    story, point["lat"], point["lon"], location_name)
            else:
                extraction_locations = []

            # Pre-build extraction data so pipeline can store directly
            # without calling the LLM
            event_sig = _build_event_signature(props)
            topics = ["weather"] + extra_concepts
            if severity >= 3:
                topics.append("disaster")
            topics = dedup_list(topics)

            story["_extraction"] = build_extraction(
                event_sig=event_sig,
                topics=topics,
                severity=severity,
                sentiment="negative",
                primary_action=event_type.lower(),
                hi_score=hi_score,
                locations=extraction_locations,
                search_keywords=["weather", event_type.lower(), location_name],
            )

            stories.append(story)
        except Exception as e:
            logger.error("Error processing NOAA alert: %s", e)
            continue

    logger.info("NOAA: fetched %d weather alerts", len(stories))
    return stories
