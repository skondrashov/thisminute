"""Meteoalarm European severe weather alerts integration.

Fetches active weather warnings from the Meteoalarm API for major
European countries. Unlike news stories, these are government-issued
CAP alerts with structured severity, event type, and region data.
They skip LLM extraction because all structured data is pre-built.

Meteoalarm API returns JSON with CAP-format warnings. No authentication
required. Geographic data uses area names + EMMA_ID codes (no lat/lon),
so we use country-level centroids for map placement.

API docs: https://feeds.meteoalarm.org
"""

import logging
import time
from datetime import datetime, timezone

from .config import (
    REQUEST_TIMEOUT,
    METEOALARM_COUNTRIES,
    METEOALARM_BASE_URL,
    METEOALARM_CACHE_SECONDS,
    METEOALARM_MAX_ALERTS,
    METEOALARM_TIMEOUT,
    METEOALARM_TOTAL_BUDGET,
)
from .country_centroids import get_centroid
from .source_utils import fetch_json, dedup_list, build_extraction, attach_location, current_year

logger = logging.getLogger(__name__)

# Module-level cache to avoid hammering the API
_cache = {
    "stories": [],
    "fetched_at": 0.0,
}

# Meteoalarm awareness_level -> our 1-5 severity scale
# Format: "N; color; Level" e.g. "2; yellow; Moderate"
_AWARENESS_SEVERITY_MAP = {
    "1": 1,   # green / Minor
    "2": 2,   # yellow / Moderate
    "3": 3,   # orange / Severe
    "4": 4,   # red / Extreme
}

# Meteoalarm awareness_level -> human interest score (1-10)
_AWARENESS_HI_MAP = {
    "1": 2,   # green / Minor
    "2": 4,   # yellow / Moderate
    "3": 7,   # orange / Severe
    "4": 9,   # red / Extreme
}

# Meteoalarm severity string -> our 1-5 scale (fallback)
_SEVERITY_MAP = {
    "Minor": 1,
    "Moderate": 2,
    "Severe": 3,
    "Extreme": 4,
}

_HUMAN_INTEREST_MAP = {
    "Minor": 2,
    "Moderate": 4,
    "Severe": 7,
    "Extreme": 9,
}

# awareness_type number -> event concept mapping
# Format: "N; EventType" e.g. "1; Wind"
_AWARENESS_TYPE_CONCEPTS = {
    "1": ["wind", "storm"],
    "2": ["snow", "ice", "winter storm"],
    "3": ["thunderstorm", "lightning"],
    "4": ["fog"],
    "5": ["heat wave"],
    "6": ["cold wave"],
    "7": ["avalanche"],
    "8": ["flood"],
    "9": ["wildfire"],
    "10": ["rain"],
    "11": ["storm surge", "flood"],
    "12": ["coastal event"],
    "13": ["forest fire", "wildfire"],
}

# Event name keywords -> concepts (fallback for text-based matching)
_EVENT_CONCEPTS = {
    "wind": ["wind", "storm"],
    "storm": ["storm"],
    "thunder": ["thunderstorm"],
    "rain": ["rain", "flood"],
    "snow": ["snow", "winter storm"],
    "ice": ["ice", "winter storm"],
    "frost": ["frost", "cold wave"],
    "fog": ["fog"],
    "heat": ["heat wave"],
    "cold": ["cold wave"],
    "flood": ["flood"],
    "avalanche": ["avalanche"],
    "fire": ["wildfire"],
    "tornado": ["tornado"],
    "hail": ["thunderstorm", "hail"],
    "coastal": ["coastal event"],
    "wave": ["storm surge"],
}


def _parse_awareness_level(params):
    """Extract awareness level number from parameter list.

    Looks for parameter with valueName 'awareness_level'.
    Value format: "N; color; Level" e.g. "2; yellow; Moderate"
    Returns the numeric level as a string, or None.
    """
    if not params:
        return None
    for p in params:
        if p.get("valueName") == "awareness_level":
            val = p.get("value", "")
            parts = val.split(";")
            if parts:
                return parts[0].strip()
    return None


def _parse_awareness_type(params):
    """Extract awareness type number from parameter list.

    Looks for parameter with valueName 'awareness_type'.
    Value format: "N; TypeName" e.g. "1; Wind"
    Returns the numeric type as a string, or None.
    """
    if not params:
        return None
    for p in params:
        if p.get("valueName") == "awareness_type":
            val = p.get("value", "")
            parts = val.split(";")
            if parts:
                return parts[0].strip()
    return None


def _get_severity(info, awareness_level):
    """Map alert to our 1-5 severity scale."""
    if awareness_level and awareness_level in _AWARENESS_SEVERITY_MAP:
        return _AWARENESS_SEVERITY_MAP[awareness_level]
    # Fallback to CAP severity field
    sev_str = info.get("severity", "Moderate")
    return _SEVERITY_MAP.get(sev_str, 2)


def _get_human_interest(info, awareness_level):
    """Map alert to human interest score (1-10)."""
    if awareness_level and awareness_level in _AWARENESS_HI_MAP:
        return _AWARENESS_HI_MAP[awareness_level]
    sev_str = info.get("severity", "Moderate")
    return _HUMAN_INTEREST_MAP.get(sev_str, 3)


def _get_event_concepts(awareness_type_num, event_text):
    """Get weather concepts from awareness type or event text."""
    concepts = []
    # Try awareness_type number first
    if awareness_type_num and awareness_type_num in _AWARENESS_TYPE_CONCEPTS:
        concepts = list(_AWARENESS_TYPE_CONCEPTS[awareness_type_num])
    else:
        # Fallback: keyword match on event text
        event_lower = (event_text or "").lower()
        for key, vals in _EVENT_CONCEPTS.items():
            if key in event_lower:
                concepts.extend(vals)
                break
    return concepts


def _get_english_info(info_list):
    """Find the English-language info block from the info array.

    Meteoalarm provides alerts in multiple languages. We prefer
    English (en, en-GB, en-US) and fall back to the first info block.
    """
    if not info_list:
        return None
    for info in info_list:
        lang = (info.get("language") or "").lower()
        if lang.startswith("en"):
            return info
    # Fallback: return first info block
    return info_list[0]


def _build_title(info, country_name):
    """Build a title from alert info."""
    headline = (info.get("headline") or "").strip()
    if headline:
        return headline

    event = info.get("event", "Weather Alert")
    areas = info.get("area", [])
    if areas:
        area_name = areas[0].get("areaDesc", "")
        if area_name:
            return "%s - %s" % (event, area_name)
    return "%s - %s" % (event, country_name.replace("-", " ").title())


def _build_summary(info):
    """Build a summary from alert description."""
    desc = (info.get("description") or "").strip()
    if desc:
        if len(desc) > 500:
            desc = desc[:497] + "..."
        return desc
    instruction = (info.get("instruction") or "").strip()
    if instruction:
        if len(instruction) > 500:
            instruction = instruction[:497] + "..."
        return instruction
    event = info.get("event", "Weather alert")
    severity = info.get("severity", "")
    return "%s. Severity: %s." % (event, severity)


def _build_event_signature(info, country_name):
    """Build event signature for clustering.

    Format: "2026 Country EventType"
    """
    event = info.get("event", "Weather Alert")
    year = current_year()

    # Clean up event name: remove color prefix (e.g. "Yellow Wind Warning")
    event_clean = event
    for color in ("Green ", "Yellow ", "Orange ", "Red "):
        if event_clean.startswith(color):
            event_clean = event_clean[len(color):]
    # Remove "Warning" / "Watch" suffixes for cleaner grouping
    for suffix in (" Warning", " Watch", " Advisory", " Alert"):
        event_clean = event_clean.replace(suffix, "")

    country_display = country_name.replace("-", " ").title()

    # Extract region from first area if available
    areas = info.get("area", [])
    if areas:
        region = areas[0].get("areaDesc", country_display)
    else:
        region = country_display

    return "%s %s %s" % (year, region, event_clean)


def _extract_location_name(info, country_name):
    """Extract a location name from alert areas."""
    areas = info.get("area", [])
    if areas:
        area_desc = areas[0].get("areaDesc", "")
        if area_desc:
            return area_desc
    return country_name.replace("-", " ").title()


def _build_url(info, alert_identifier):
    """Build a URL for the alert."""
    # Prefer the web link from alert info
    web = (info.get("web") or "").strip()
    if web:
        return web
    # Fall back to alert identifier (which is a URN-style ID)
    return "https://meteoalarm.org/alert/%s" % alert_identifier


def _fetch_country_warnings(country, timeout=None):
    """Fetch warnings for a single country from Meteoalarm API."""
    url = METEOALARM_BASE_URL.replace("{country}", country)
    return fetch_json(url, key="warnings", timeout=timeout)


def _parse_warning(warning, country, now):
    """Parse a single Meteoalarm warning into a story dict.

    Returns None if the warning is invalid or should be skipped.
    """
    alert = warning.get("alert")
    if not alert:
        return None

    uuid = warning.get("uuid", "")
    identifier = alert.get("identifier", "")

    info_list = alert.get("info", [])
    info = _get_english_info(info_list)
    if not info:
        return None

    event = info.get("event", "")
    if not event:
        return None

    # Parse awareness parameters
    params = info.get("parameter", [])
    awareness_level = _parse_awareness_level(params)
    awareness_type = _parse_awareness_type(params)

    # Skip green/minor alerts (awareness level 1) to reduce volume
    if awareness_level == "1":
        return None

    # Get severity and human interest
    severity = _get_severity(info, awareness_level)
    hi_score = _get_human_interest(info, awareness_level)

    # Build story fields
    title = _build_title(info, country)
    url = _build_url(info, identifier)
    summary = _build_summary(info)
    location_name = _extract_location_name(info, country)
    event_sig = _build_event_signature(info, country)

    # Get concepts
    extra_concepts = _get_event_concepts(awareness_type, event)
    concepts = dedup_list(["weather"] + extra_concepts)

    # Category based on severity
    category = "disaster" if severity >= 3 else "weather"

    # Published time
    published_at = info.get("onset") or info.get("effective") or alert.get("sent")

    # Get country centroid for map placement
    centroid = get_centroid(country.replace("-", " "))
    lat = centroid[0] if centroid else None
    lon = centroid[1] if centroid else None

    story = {
        "title": title,
        "url": url,
        "summary": summary,
        "source": "Meteoalarm",
        "published_at": published_at,
        "scraped_at": now,
        "origin": "meteoalarm",
        "source_type": "inferred",
        "category": category,
        "concepts": concepts,
        "location_name": location_name,
        "geocode_confidence": 0.6,  # country centroid, not precise
    }

    if lat is not None and lon is not None:
        extraction_locations = attach_location(
            story, lat, lon, location_name, confidence=0.6)
    else:
        extraction_locations = []

    # Pre-build extraction data
    topics = ["weather"] + extra_concepts
    if severity >= 3:
        topics.append("disaster")
    topics = dedup_list(topics)

    story["_extraction"] = build_extraction(
        event_sig=event_sig,
        topics=topics,
        severity=severity,
        sentiment="negative",
        primary_action=event.lower(),
        hi_score=hi_score,
        locations=extraction_locations,
        search_keywords=["weather", event.lower(), location_name],
    )

    return story


def scrape_meteoalarm():
    """Fetch European weather alerts from Meteoalarm and return story dicts.

    Returns list of story dicts compatible with pipeline.process_story(),
    with pre-populated location, concept, and extraction data.
    Meteoalarm stories skip LLM extraction because all structured data
    is available directly from the API.

    Results are cached for METEOALARM_CACHE_SECONDS to be polite to the API.
    Green/minor alerts (awareness level 1) are filtered out.
    """
    # Check cache
    elapsed = time.monotonic() - _cache["fetched_at"]
    if _cache["stories"] and elapsed < METEOALARM_CACHE_SECONDS:
        logger.info("Meteoalarm: returning %d cached stories (%.0fs old)",
                     len(_cache["stories"]), elapsed)
        return list(_cache["stories"])

    now = datetime.now(timezone.utc).isoformat()
    all_stories = []
    seen_ids = set()
    budget_start = time.monotonic()
    countries_fetched = 0
    countries_skipped = 0

    for country in METEOALARM_COUNTRIES:
        # Check total time budget before each request
        elapsed_budget = time.monotonic() - budget_start
        if elapsed_budget >= METEOALARM_TOTAL_BUDGET:
            countries_skipped = len(METEOALARM_COUNTRIES) - countries_fetched
            logger.warning(
                "Meteoalarm: time budget exhausted (%.0fs >= %ds), "
                "skipping %d remaining countries",
                elapsed_budget, METEOALARM_TOTAL_BUDGET, countries_skipped)
            break

        try:
            warnings = _fetch_country_warnings(country, timeout=METEOALARM_TIMEOUT)
            countries_fetched += 1
            if not warnings:
                continue

            for warning in warnings:
                try:
                    # Dedup by uuid
                    uuid = warning.get("uuid", "")
                    alert_id = ""
                    alert = warning.get("alert")
                    if alert:
                        alert_id = alert.get("identifier", "")
                    dedup_key = uuid or alert_id
                    if not dedup_key or dedup_key in seen_ids:
                        continue
                    seen_ids.add(dedup_key)

                    story = _parse_warning(warning, country, now)
                    if story:
                        all_stories.append(story)
                except Exception as e:
                    logger.error("Error processing Meteoalarm warning: %s", e)
                    continue

        except Exception as e:
            countries_fetched += 1
            logger.error("Error fetching Meteoalarm %s: %s", country, e)
            continue

    # Sort by severity (most severe first) and cap
    all_stories.sort(key=lambda s: s["_extraction"]["severity"], reverse=True)
    if len(all_stories) > METEOALARM_MAX_ALERTS:
        logger.warning(
            "Meteoalarm: %d alerts exceed cap of %d, keeping most severe",
            len(all_stories), METEOALARM_MAX_ALERTS)
        all_stories = all_stories[:METEOALARM_MAX_ALERTS]

    # Update cache
    _cache["stories"] = list(all_stories)
    _cache["fetched_at"] = time.monotonic()

    logger.info("Meteoalarm: fetched %d alerts from %d/%d countries (%.1fs)",
                len(all_stories), countries_fetched, len(METEOALARM_COUNTRIES),
                time.monotonic() - budget_start)
    return all_stories
