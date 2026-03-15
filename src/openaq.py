"""OpenAQ air quality integration for statistical inference events.

Fetches global air quality data from the OpenAQ API and creates stories
for locations exceeding WHO thresholds. Unlike news stories, these are
sensor-derived measurements with precise lat/lon, pollutant concentrations,
and timestamps. They skip LLM extraction because all structured data is
already available from the OpenAQ API.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from .config import REQUEST_TIMEOUT, OPENAQ_URL, OPENAQ_API_KEY
from .source_utils import fetch_json, dedup_list, build_extraction, attach_location, current_year

logger = logging.getLogger(__name__)

# WHO guideline thresholds (ug/m3, 24-hour mean unless noted)
# PM2.5 > 35 is US EPA "Unhealthy for Sensitive Groups" (WHO guideline = 15)
_THRESHOLDS = {
    "pm25": 35.0,
    "pm10": 45.0,     # WHO guideline = 45
    "o3": 100.0,      # WHO guideline = 100 (8-hour mean)
    "no2": 25.0,      # WHO guideline = 25
    "so2": 40.0,      # WHO guideline = 40 (24-hour)
}

# Canonical parameter name mapping (OpenAQ uses various forms)
_PARAM_ALIASES = {
    "pm25": "pm25",
    "pm2.5": "pm25",
    "pm10": "pm10",
    "o3": "o3",
    "ozone": "o3",
    "no2": "no2",
    "so2": "so2",
}

# Display names for pollutants
_PARAM_DISPLAY = {
    "pm25": "PM2.5",
    "pm10": "PM10",
    "o3": "O3",
    "no2": "NO2",
    "so2": "SO2",
}

# Pollutant-specific concepts
_PARAM_CONCEPTS = {
    "pm25": ["particulate-matter"],
    "pm10": ["particulate-matter"],
    "o3": ["ozone"],
    "no2": ["nitrogen-dioxide"],
    "so2": ["sulfur-dioxide"],
}


def _concentration_to_severity(param: str, value: float) -> int:
    """Map pollutant concentration to severity (1-5 scale).

    1 = above guideline, 2 = moderate, 3 = unhealthy for sensitive,
    4 = unhealthy, 5 = hazardous
    """
    threshold = _THRESHOLDS.get(param, 35.0)
    ratio = value / threshold
    if ratio >= 6.0:
        return 5
    elif ratio >= 4.0:
        return 4
    elif ratio >= 2.5:
        return 3
    elif ratio >= 1.5:
        return 2
    else:
        return 1


def _concentration_to_human_interest(param: str, value: float) -> int:
    """Map pollutant concentration to human interest score (1-10).

    Higher concentrations are more newsworthy.
    """
    threshold = _THRESHOLDS.get(param, 35.0)
    ratio = value / threshold
    if ratio >= 10.0:
        return 10
    elif ratio >= 7.0:
        return 9
    elif ratio >= 5.0:
        return 8
    elif ratio >= 4.0:
        return 7
    elif ratio >= 3.0:
        return 6
    elif ratio >= 2.0:
        return 5
    elif ratio >= 1.5:
        return 4
    else:
        return 3


def _build_summary(location_name: str, readings: list) -> str:
    """Build a descriptive summary from air quality readings.

    Args:
        location_name: Name of the monitoring location.
        readings: List of (param_display, value, unit) tuples.
    """
    parts = ["Air quality alert at %s." % location_name]
    for display, value, unit in readings:
        parts.append("%s: %.1f %s" % (display, value, unit))
    return " ".join(parts)


def _build_event_signature(location_name: str) -> str:
    """Build an event_signature for clustering.

    Uses year + location name for grouping.
    Example: '2026 Delhi Air Quality'
    """
    year = current_year()
    # Clean up location name for signature
    name = location_name.strip()
    if not name:
        name = "Unknown Location"
    return "%s %s Air Quality" % (year, name)


def _normalize_param(name: str) -> Optional[str]:
    """Normalize parameter name to canonical form."""
    return _PARAM_ALIASES.get(name.lower().strip().replace(" ", "").replace(".", ""))


def _exceeds_threshold(param: str, value: float) -> bool:
    """Check if a reading exceeds the WHO/EPA threshold."""
    threshold = _THRESHOLDS.get(param)
    if threshold is None:
        return False
    return value > threshold


def _extract_location_name(result: dict) -> str:
    """Extract a human-readable location name from an OpenAQ result.

    Tries various fields depending on API version.
    """
    # v2 format
    if "location" in result:
        return result["location"]
    # v3 format
    if "name" in result:
        return result["name"]
    # Fallback to city/country
    city = result.get("city", "")
    country = result.get("country", "")
    if city and country:
        return "%s, %s" % (city, country)
    return city or country or "Unknown"


def _extract_coordinates(result: dict) -> Optional[dict]:
    """Extract lat/lon from an OpenAQ result.

    Handles both v2 and v3 coordinate formats.
    """
    # v2 format: result.coordinates = {latitude, longitude}
    coords = result.get("coordinates")
    if coords:
        lat = coords.get("latitude")
        lon = coords.get("longitude")
        if lat is not None and lon is not None:
            return {"lat": float(lat), "lon": float(lon)}

    # v3 format: result.coordinates = {latitude, longitude} or
    # result.sensors[].latest.coordinates
    if "sensors" in result:
        for sensor in result.get("sensors", []):
            latest = sensor.get("latest", {})
            c = latest.get("coordinates")
            if c:
                lat = c.get("latitude")
                lon = c.get("longitude")
                if lat is not None and lon is not None:
                    return {"lat": float(lat), "lon": float(lon)}

    return None


def _extract_readings(result: dict) -> list:
    """Extract pollutant readings from an OpenAQ result.

    Returns list of (canonical_param, display_name, value, unit) tuples
    for readings that exceed thresholds.
    """
    readings = []

    # v2 format: result.measurements = [{parameter, value, unit, ...}, ...]
    measurements = result.get("measurements", [])
    for m in measurements:
        param_raw = m.get("parameter", "")
        param = _normalize_param(param_raw)
        if param is None:
            continue
        value = m.get("value")
        if value is None:
            continue
        try:
            value = float(value)
        except (ValueError, TypeError):
            continue
        if value <= 0:
            continue
        if _exceeds_threshold(param, value):
            unit = m.get("unit", "ug/m3")
            display = _PARAM_DISPLAY.get(param, param_raw)
            readings.append((param, display, value, unit))

    # v3 format: result.sensors = [{parameter: {name}, latest: {value, ...}}, ...]
    if not measurements and "sensors" in result:
        for sensor in result.get("sensors", []):
            param_info = sensor.get("parameter", {})
            param_raw = param_info.get("name", "") if isinstance(param_info, dict) else str(param_info)
            param = _normalize_param(param_raw)
            if param is None:
                continue
            latest = sensor.get("latest", {})
            value = latest.get("value")
            if value is None:
                continue
            try:
                value = float(value)
            except (ValueError, TypeError):
                continue
            if value <= 0:
                continue
            if _exceeds_threshold(param, value):
                unit = param_info.get("units", "ug/m3") if isinstance(param_info, dict) else "ug/m3"
                display = _PARAM_DISPLAY.get(param, param_raw)
                readings.append((param, display, value, unit))

    return readings


def _extract_location_id(result: dict) -> Optional[str]:
    """Extract a unique location identifier for dedup."""
    # v2 format
    loc_id = result.get("location")
    if loc_id:
        return "openaq:%s" % loc_id
    # v3 format
    loc_id = result.get("id")
    if loc_id:
        return "openaq:%s" % loc_id
    return None


def _extract_last_updated(result: dict) -> Optional[str]:
    """Extract last updated timestamp from an OpenAQ result."""
    # v2 format
    for m in result.get("measurements", []):
        ts = m.get("lastUpdated")
        if ts:
            return ts

    # v3 format
    ts = result.get("datetimeLast", {})
    if isinstance(ts, dict):
        return ts.get("utc") or ts.get("local")
    if isinstance(ts, str):
        return ts

    return None


def _fetch_openaq() -> list:
    """Fetch air quality data from OpenAQ API.

    Tries v2 endpoint (no auth required). Falls back gracefully if
    API is unavailable.
    """
    headers = {}
    url = OPENAQ_URL

    # If API key is available, use v3 endpoint with auth
    if OPENAQ_API_KEY:
        headers["X-API-Key"] = OPENAQ_API_KEY

    return fetch_json(
        url,
        key="results",
        headers=headers if headers else None,
    )


def scrape_openaq() -> list:
    """Fetch OpenAQ air quality data and return story dicts.

    Returns list of story dicts compatible with pipeline.process_story(),
    with pre-populated location, concept, and extraction data.
    OpenAQ stories skip LLM extraction because all structured data is
    available directly from the OpenAQ API.

    Only creates stories for locations exceeding WHO/EPA thresholds.
    """
    now = datetime.now(timezone.utc).isoformat()
    results = _fetch_openaq()

    if not results:
        logger.info("OpenAQ: no results returned")
        return []

    # Dedup by location ID
    seen_ids = set()
    stories = []

    for result in results:
        try:
            # Get location ID for dedup
            loc_id = _extract_location_id(result)
            if loc_id and loc_id in seen_ids:
                continue
            if loc_id:
                seen_ids.add(loc_id)

            # Extract readings that exceed thresholds
            readings = _extract_readings(result)
            if not readings:
                continue

            # Get location info
            location_name = _extract_location_name(result)
            coords = _extract_coordinates(result)

            # Use the worst (highest severity) reading for this location
            worst_reading = None
            worst_severity = 0
            for param, display, value, unit in readings:
                sev = _concentration_to_severity(param, value)
                if sev > worst_severity:
                    worst_severity = sev
                    worst_reading = (param, display, value, unit)

            # Build reading display for summary
            reading_tuples = [(display, value, unit) for _, display, value, unit in readings]
            summary = _build_summary(location_name, reading_tuples)
            event_sig = _build_event_signature(location_name)

            if not worst_reading:
                continue

            severity = worst_severity
            hi_score = _concentration_to_human_interest(worst_reading[0], worst_reading[2])

            # Concepts: base + pollutant-specific
            extra_concepts = []
            for param, _, _, _ in readings:
                extra_concepts.extend(_PARAM_CONCEPTS.get(param, []))
            concepts = dedup_list(["air-quality", "pollution", "health"] + extra_concepts)

            # Build URL from location ID
            loc_id_str = loc_id.replace("openaq:", "") if loc_id else "unknown"
            detail_url = "https://openaq.org/locations/%s" % loc_id_str

            # Published time
            published_at = _extract_last_updated(result)

            # Title
            pollutant_names = [display for _, display, _, _ in readings]
            title = "Air Quality Alert: %s (%s)" % (
                location_name,
                ", ".join(pollutant_names),
            )
            if len(title) > 200:
                title = title[:197] + "..."

            story = {
                "title": title,
                "url": detail_url,
                "summary": summary,
                "source": "OpenAQ",
                "published_at": published_at,
                "scraped_at": now,
                "origin": "openaq",
                "source_type": "inferred",
                "category": "health",
                "concepts": concepts,
                "location_name": location_name,
                "geocode_confidence": 0.9,
            }

            if coords:
                extraction_locations = attach_location(
                    story, coords["lat"], coords["lon"], location_name)
            else:
                extraction_locations = []

            # Pre-build extraction data so pipeline can store directly
            # without calling the LLM
            topics = dedup_list(["air-quality", "pollution", "health", "environment"] + extra_concepts)

            story["_extraction"] = build_extraction(
                event_sig=event_sig,
                topics=topics,
                severity=severity,
                sentiment="negative",
                primary_action="air quality alert",
                hi_score=hi_score,
                locations=extraction_locations,
                search_keywords=["air quality", "pollution"] + pollutant_names + [location_name],
            )

            stories.append(story)
        except Exception as e:
            logger.error("Error processing OpenAQ result: %s", e)
            continue

    logger.info("OpenAQ: fetched %d air quality alerts from %d results",
                len(stories), len(results))
    return stories
