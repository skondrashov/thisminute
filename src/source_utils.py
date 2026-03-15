"""Shared utilities for source adapter modules.

Extracts common boilerplate: HTTP fetching, concept deduplication,
extraction dict assembly, location attachment, HTML stripping,
polygon centroid calculation, and date helpers.
"""

import json
import logging
import re
import urllib.request
from datetime import datetime, timezone

from .config import REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


def fetch_json(url, key="features", user_agent="thisminute-news-map/1.0",
               timeout=None, headers=None, log_url=None):
    """Fetch JSON from a URL and return data at the given key.

    Args:
        url: The URL to fetch.
        key: The dict key to extract from the response. If None, returns
             the full parsed dict.
        user_agent: User-Agent header value.
        timeout: Request timeout in seconds. Defaults to REQUEST_TIMEOUT.
        headers: Optional dict of additional headers (merged with User-Agent).
        log_url: If provided, this URL is logged instead of the real URL.
                 Use this when the real URL contains credentials.

    Returns:
        The list/dict at data[key], or the full data dict if key is None,
        or [] on error (or {} if key is None).
    """
    if timeout is None:
        timeout = REQUEST_TIMEOUT

    safe_url = log_url if log_url is not None else url

    req_headers = {"User-Agent": user_agent}
    if headers:
        req_headers.update(headers)

    try:
        req = urllib.request.Request(url, headers=req_headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if key is None:
            return data
        return data.get(key, [])
    except Exception as e:
        logger.error("Failed to fetch %s: %s", safe_url, e)
        if key is None:
            return {}
        return []


def dedup_list(items):
    """Order-preserving deduplication of a list."""
    return list(dict.fromkeys(items))


def build_extraction(event_sig, topics, severity, sentiment, primary_action,
                     hi_score, locations, search_keywords=None,
                     location_type="terrestrial"):
    """Build the standard 11-key extraction dict.

    Returns a dict ready to be assigned to story["_extraction"].
    """
    return {
        "event_signature": event_sig,
        "topics": topics,
        "severity": severity,
        "sentiment": sentiment,
        "primary_action": primary_action,
        "location_type": location_type,
        "search_keywords": search_keywords or [],
        "is_opinion": False,
        "human_interest_score": hi_score,
        "actors": [],
        "locations": locations,
    }


def attach_location(story, lat, lon, location_name, confidence=1.0):
    """Set lat/lon/geocode_confidence on story and return extraction_locations.

    If lat or lon is None, the story is not modified and an empty list
    is returned.
    """
    extraction_locations = []
    if lat is not None and lon is not None:
        story["lat"] = lat
        story["lon"] = lon
        story["geocode_confidence"] = confidence
        extraction_locations.append({
            "name": location_name,
            "role": "event_location",
            "lat": lat,
            "lon": lon,
        })
    return extraction_locations


def strip_html(text):
    """Remove HTML tags from text."""
    return re.sub(r'<[^>]+>', '', text)


def current_year():
    """Return the current UTC year as a 4-digit string (e.g. '2026')."""
    return datetime.now(timezone.utc).strftime("%Y")


def polygon_centroid(coordinates):
    """Calculate the centroid of a polygon from GeoJSON coordinates.

    GeoJSON polygons have coordinates as [[[lon, lat], [lon, lat], ...]].
    Returns {"lat": float, "lon": float} or None if invalid.
    """
    if not coordinates or not coordinates[0]:
        return None

    ring = coordinates[0]  # outer ring
    if len(ring) < 3:
        return None

    total_lon = 0.0
    total_lat = 0.0
    count = 0
    for point in ring:
        if len(point) >= 2:
            total_lon += point[0]
            total_lat += point[1]
            count += 1

    if count == 0:
        return None

    return {"lat": total_lat / count, "lon": total_lon / count}
