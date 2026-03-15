"""USGS Earthquake feed integration for statistical inference events.

Fetches significant and M4.5+ earthquakes from the USGS GeoJSON feeds.
Unlike news stories, these are sensor-derived events with precise lat/lon,
magnitude, depth, and other seismological data. They skip LLM extraction
because all structured data is already available from the USGS API.
"""

import logging
from datetime import datetime, timezone

from .config import REQUEST_TIMEOUT, USGS_SIGNIFICANT_URL, USGS_4_5_URL, USGS_MIN_MAGNITUDE
from .source_utils import fetch_json, build_extraction, current_year

logger = logging.getLogger(__name__)


def _mag_to_severity(mag: float) -> int:
    """Map earthquake magnitude to extraction severity (1-5 scale).

    1 = minor (M4.5-4.9), 2 = moderate (M5.0-5.4), 3 = strong (M5.5-5.9),
    4 = major (M6.0-6.9), 5 = severe (M7.0+)
    """
    if mag >= 7.0:
        return 5
    elif mag >= 6.0:
        return 4
    elif mag >= 5.5:
        return 3
    elif mag >= 5.0:
        return 2
    else:
        return 1


def _mag_to_human_interest(mag: float) -> int:
    """Map earthquake magnitude to human interest score (1-10).

    Larger earthquakes are more inherently newsworthy/engaging.
    """
    if mag >= 8.0:
        return 10
    elif mag >= 7.5:
        return 9
    elif mag >= 7.0:
        return 8
    elif mag >= 6.5:
        return 7
    elif mag >= 6.0:
        return 6
    elif mag >= 5.5:
        return 5
    elif mag >= 5.0:
        return 4
    else:
        return 3


def _build_summary(props: dict) -> str:
    """Build a descriptive summary from USGS feature properties."""
    parts = []
    mag = props.get("mag")
    place = props.get("place", "unknown location")
    if mag is not None:
        parts.append("M%.1f earthquake near %s" % (mag, place))
    else:
        parts.append("Earthquake near %s" % place)

    depth_km = None
    # depth comes from geometry coordinates[2], passed in via props for convenience
    if "depth_km" in props and props["depth_km"] is not None:
        depth_km = props["depth_km"]
        parts.append("Depth: %.1f km" % depth_km)

    felt = props.get("felt")
    if felt is not None and felt > 0:
        parts.append("Felt by %d people" % felt)

    tsunami = props.get("tsunami")
    if tsunami and tsunami > 0:
        parts.append("Tsunami warning issued")

    return ". ".join(parts) + "."


def _build_event_signature(props: dict) -> str:
    """Build an event_signature for clustering.

    Uses year + approximate location to group related quakes.
    Example: '2026 Taiwan Earthquake'
    """
    place = props.get("place", "")
    # USGS place is like "52 km SSE of Hualien City, Taiwan"
    # Extract the region (after last comma) for the signature
    region = place.split(",")[-1].strip() if "," in place else place
    if not region:
        region = "Unknown Region"
    year = current_year()
    return "%s %s Earthquake" % (year, region)


def _fetch_feed(url: str) -> list[dict]:
    """Fetch a USGS GeoJSON feed and return its features."""
    return fetch_json(url)


def scrape_usgs() -> list[dict]:
    """Fetch USGS earthquake feeds and return story dicts.

    Returns list of story dicts compatible with pipeline.process_story(),
    with pre-populated location, concept, and extraction data.
    USGS stories skip LLM extraction because all structured data is
    available directly from the USGS API.
    """
    now = datetime.now(timezone.utc).isoformat()

    # Fetch both feeds
    sig_features = _fetch_feed(USGS_SIGNIFICANT_URL)
    m45_features = _fetch_feed(USGS_4_5_URL)

    # Dedup by USGS detail URL
    seen_urls = set()
    all_features = []
    for f in sig_features + m45_features:
        url = f.get("properties", {}).get("url")
        if url and url not in seen_urls:
            seen_urls.add(url)
            all_features.append(f)

    stories = []
    for feature in all_features:
        try:
            props = feature.get("properties", {})
            geom = feature.get("geometry", {})
            coords = geom.get("coordinates", [])

            if len(coords) < 2:
                continue

            lon, lat = coords[0], coords[1]
            depth_km = coords[2] if len(coords) > 2 else None

            mag = props.get("mag")
            if mag is None:
                continue

            # Apply minimum magnitude filter
            if mag < USGS_MIN_MAGNITUDE:
                continue

            title = props.get("title", "")
            detail_url = props.get("url", "")
            if not title or not detail_url:
                continue

            # Pass depth into props for summary builder
            props_with_depth = dict(props)
            props_with_depth["depth_km"] = depth_km

            summary = _build_summary(props_with_depth)
            event_sig = _build_event_signature(props)
            severity = _mag_to_severity(mag)
            hi_score = _mag_to_human_interest(mag)

            # Convert USGS epoch ms to ISO timestamp
            time_ms = props.get("time")
            published_at = None
            if time_ms is not None:
                try:
                    published_at = datetime.fromtimestamp(
                        time_ms / 1000, tz=timezone.utc
                    ).isoformat()
                except (ValueError, OSError):
                    pass

            place = props.get("place", "")
            # Extract location name from place string
            location_name = place.split(",")[-1].strip() if "," in place else place

            story = {
                "title": title,
                "url": detail_url,
                "summary": summary,
                "source": "USGS Earthquakes",
                "published_at": published_at,
                "scraped_at": now,
                "origin": "usgs",
                "source_type": "inferred",
                "category": "disaster",
                "concepts": ["disaster", "earthquake"],
                "location_name": location_name,
                "lat": lat,
                "lon": lon,
                "geocode_confidence": 1.0,
            }

            # Pre-build extraction data so pipeline can store directly
            # without calling the LLM
            extraction_locations = [
                {
                    "name": location_name,
                    "role": "event_location",
                    "lat": lat,
                    "lon": lon,
                }
            ]
            story["_extraction"] = build_extraction(
                event_sig=event_sig,
                topics=["earthquake", "disaster"],
                severity=severity,
                sentiment="negative",
                primary_action="earthquake",
                hi_score=hi_score,
                locations=extraction_locations,
                search_keywords=["earthquake", "seismic", location_name],
            )

            stories.append(story)
        except Exception as e:
            logger.error("Error processing USGS feature: %s", e)
            continue

    logger.info("USGS: fetched %d earthquakes (%d significant, %d M4.5+)",
                len(stories), len(sig_features), len(m45_features))
    return stories
