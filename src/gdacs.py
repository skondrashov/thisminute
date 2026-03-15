"""GDACS (Global Disaster Alert and Coordination System) integration.

Fetches active disaster alerts from the GDACS GeoJSON API.
Events include earthquakes, floods, tropical cyclones, droughts, volcanoes,
and wildfires with alert levels and severity data. They skip LLM extraction
because all structured data is available from the GDACS API.
"""

import json
import logging
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from .config import REQUEST_TIMEOUT, GDACS_GEOJSON_URL, GDACS_RSS_URL
from .source_utils import fetch_json, build_extraction, attach_location, current_year

logger = logging.getLogger(__name__)

# GDACS alert level -> our severity (1-5)
_ALERT_SEVERITY = {
    "Green": 2,
    "Orange": 3,
    "Red": 4,
}

# GDACS alert level -> human interest score
_ALERT_HUMAN_INTEREST = {
    "Green": 3,
    "Orange": 5,
    "Red": 8,
}

# GDACS event type (lowercase) -> concepts
_EVENT_CONCEPTS = {
    "eq": ["earthquake"],
    "earthquake": ["earthquake"],
    "fl": ["flood"],
    "flood": ["flood"],
    "tc": ["cyclone", "hurricane"],
    "cyclone": ["cyclone", "hurricane"],
    "tropical cyclone": ["cyclone", "hurricane"],
    "dr": ["drought"],
    "drought": ["drought"],
    "vo": ["volcano"],
    "volcano": ["volcano"],
    "wf": ["wildfire"],
    "wildfire": ["wildfire"],
    "ts": ["tsunami"],
    "tsunami": ["tsunami"],
}


def _parse_event_type(event_type_str):
    """Normalize event type string to a standard key."""
    if not event_type_str:
        return ""
    lower = event_type_str.strip().lower()
    # Map short codes
    type_map = {
        "eq": "earthquake",
        "fl": "flood",
        "tc": "cyclone",
        "dr": "drought",
        "vo": "volcano",
        "wf": "wildfire",
        "ts": "tsunami",
    }
    return type_map.get(lower, lower)


def _get_concepts(event_type):
    """Get concepts list from event type."""
    normalized = _parse_event_type(event_type)
    for key, concepts in _EVENT_CONCEPTS.items():
        if key == normalized or normalized.startswith(key):
            return list(concepts)
    return [normalized] if normalized else ["disaster"]


def _build_event_signature(title, event_type):
    """Build an event_signature for clustering."""
    year = current_year()
    if title:
        # Truncate for signature
        sig = title if len(title) <= 60 else title[:57] + "..."
        return "%s %s" % (year, sig)
    etype = _parse_event_type(event_type)
    return "%s %s" % (year, etype.title() if etype else "Disaster")


def _build_summary(title, description, alert_level, population):
    """Build a summary from GDACS data."""
    parts = []
    if description:
        desc = description.strip()
        if len(desc) > 400:
            desc = desc[:397] + "..."
        parts.append(desc)
    elif title:
        parts.append(title)

    if alert_level:
        parts.append("Alert level: %s" % alert_level)
    if population:
        parts.append("Affected population: %s" % str(population))

    return " ".join(parts) if parts else "Disaster event reported by GDACS."


def _fetch_geojson():
    """Fetch active events from GDACS GeoJSON API.

    Returns list of features on success, None on failure (so caller can
    distinguish fetch failure from empty result set).
    """
    try:
        req = urllib.request.Request(
            GDACS_GEOJSON_URL,
            headers={"User-Agent": "thisminute-news-map/1.0"},
        )
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("features", [])
    except Exception as e:
        logger.error("GDACS GeoJSON fetch failed: %s", e)
        return None


def _fetch_rss():
    """Fetch active events from GDACS RSS feed as fallback."""
    try:
        req = urllib.request.Request(
            GDACS_RSS_URL,
            headers={"User-Agent": "thisminute-news-map/1.0"},
        )
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8")

        root = ET.fromstring(raw)
        items = []

        # RSS namespace handling
        ns = {
            "gdacs": "http://www.gdacs.org",
            "geo": "http://www.w3.org/2003/01/geo/wgs84_pos#",
        }

        for item in root.iter("item"):
            entry = {}
            title_el = item.find("title")
            entry["title"] = title_el.text.strip() if title_el is not None and title_el.text else ""

            link_el = item.find("link")
            entry["url"] = link_el.text.strip() if link_el is not None and link_el.text else ""

            desc_el = item.find("description")
            entry["description"] = desc_el.text.strip() if desc_el is not None and desc_el.text else ""

            pub_el = item.find("pubDate")
            entry["pubDate"] = pub_el.text.strip() if pub_el is not None and pub_el.text else ""

            # Try geo coordinates
            lat_el = item.find("geo:lat", ns)
            lon_el = item.find("geo:long", ns)
            if lat_el is not None and lat_el.text and lon_el is not None and lon_el.text:
                try:
                    entry["lat"] = float(lat_el.text)
                    entry["lon"] = float(lon_el.text)
                except (ValueError, TypeError):
                    pass

            # Try gdacs fields
            alert_el = item.find("gdacs:alertlevel", ns)
            entry["alertlevel"] = alert_el.text.strip() if alert_el is not None and alert_el.text else ""

            event_el = item.find("gdacs:eventtype", ns)
            entry["eventtype"] = event_el.text.strip() if event_el is not None and event_el.text else ""

            pop_el = item.find("gdacs:population", ns)
            entry["population"] = pop_el.text.strip() if pop_el is not None and pop_el.text else ""

            items.append(entry)

        return items
    except Exception as e:
        logger.error("GDACS RSS fetch failed: %s", e)
        return None


def _process_geojson_features(features):
    """Process GeoJSON features into story dicts."""
    now = datetime.now(timezone.utc).isoformat()
    seen_urls = set()
    stories = []

    for feature in features:
        try:
            props = feature.get("properties", {})
            geom = feature.get("geometry", {})

            title = props.get("name", "") or props.get("title", "")
            if not title:
                continue

            url = props.get("url", "") or props.get("link", "")
            if not url:
                continue

            if url in seen_urls:
                continue
            seen_urls.add(url)

            # Coordinates
            lat, lon = None, None
            if geom:
                coords = geom.get("coordinates")
                geom_type = geom.get("type", "")
                if coords and geom_type == "Point" and len(coords) >= 2:
                    lon, lat = coords[0], coords[1]

            # Event details
            event_type = props.get("eventtype", "") or props.get("type", "")
            alert_level = props.get("alertlevel", "") or props.get("alertLevel", "")
            description = props.get("description", "") or props.get("htmldescription", "")
            population = props.get("population", {})
            pop_str = ""
            if isinstance(population, dict):
                pop_str = str(population.get("value", ""))
            elif population:
                pop_str = str(population)

            concepts = _get_concepts(event_type)
            severity = _ALERT_SEVERITY.get(alert_level, 2)
            hi_score = _ALERT_HUMAN_INTEREST.get(alert_level, 3)

            # Adjust severity for Red alerts with context
            if alert_level == "Red":
                severity = 5 if "major" in title.lower() or "catastroph" in title.lower() else 4

            summary = _build_summary(title, description, alert_level, pop_str)
            event_sig = _build_event_signature(title, event_type)

            published_at = props.get("fromdate") or props.get("date")

            story = {
                "title": title,
                "url": url,
                "summary": summary,
                "source": "GDACS",
                "published_at": published_at,
                "scraped_at": now,
                "origin": "gdacs",
                "source_type": "inferred",
                "category": "disaster",
                "concepts": concepts,
                "location_name": title,
                "geocode_confidence": 0.8,
            }

            extraction_locations = attach_location(story, lat, lon, title)

            topics = list(concepts)
            if "disaster" not in topics:
                topics.append("disaster")

            story["_extraction"] = build_extraction(
                event_sig=event_sig,
                topics=topics,
                severity=severity,
                sentiment="negative",
                primary_action=_parse_event_type(event_type) or "disaster",
                hi_score=hi_score,
                locations=extraction_locations,
                search_keywords=[_parse_event_type(event_type), title],
            )

            stories.append(story)
        except Exception as e:
            logger.error("Error processing GDACS GeoJSON feature: %s", e)
            continue

    return stories


def _process_rss_items(items):
    """Process RSS items into story dicts."""
    now = datetime.now(timezone.utc).isoformat()
    seen_urls = set()
    stories = []

    for item in items:
        try:
            title = item.get("title", "")
            url = item.get("url", "")
            if not title or not url:
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)

            lat = item.get("lat")
            lon = item.get("lon")
            event_type = item.get("eventtype", "")
            alert_level = item.get("alertlevel", "")
            description = item.get("description", "")
            pop_str = item.get("population", "")

            concepts = _get_concepts(event_type)
            severity = _ALERT_SEVERITY.get(alert_level, 2)
            hi_score = _ALERT_HUMAN_INTEREST.get(alert_level, 3)

            if alert_level == "Red":
                severity = 5 if "major" in title.lower() or "catastroph" in title.lower() else 4

            summary = _build_summary(title, description, alert_level, pop_str)
            event_sig = _build_event_signature(title, event_type)

            story = {
                "title": title,
                "url": url,
                "summary": summary,
                "source": "GDACS",
                "published_at": item.get("pubDate"),
                "scraped_at": now,
                "origin": "gdacs",
                "source_type": "inferred",
                "category": "disaster",
                "concepts": concepts,
                "location_name": title,
                "geocode_confidence": 0.8,
            }

            extraction_locations = attach_location(story, lat, lon, title)

            topics = list(concepts)
            if "disaster" not in topics:
                topics.append("disaster")

            story["_extraction"] = build_extraction(
                event_sig=event_sig,
                topics=topics,
                severity=severity,
                sentiment="negative",
                primary_action=_parse_event_type(event_type) or "disaster",
                hi_score=hi_score,
                locations=extraction_locations,
                search_keywords=[_parse_event_type(event_type), title],
            )

            stories.append(story)
        except Exception as e:
            logger.error("Error processing GDACS RSS item: %s", e)
            continue

    return stories


def scrape_gdacs():
    """Fetch GDACS events and return story dicts.

    Tries GeoJSON API first, falls back to RSS feed.
    Returns list of story dicts compatible with pipeline.process_story(),
    with pre-populated location, concept, and extraction data.
    """
    # Try GeoJSON first
    features = _fetch_geojson()
    if features is not None:
        stories = _process_geojson_features(features)
        logger.info("GDACS: fetched %d events via GeoJSON", len(stories))
        return stories

    # Fall back to RSS
    items = _fetch_rss()
    if items is not None:
        stories = _process_rss_items(items)
        logger.info("GDACS: fetched %d events via RSS", len(stories))
        return stories

    logger.error("GDACS: both GeoJSON and RSS failed, returning empty")
    return []
