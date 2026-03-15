"""Launch Library 2 integration for space launch events.

Fetches upcoming and recent launches from the Launch Library 2 API.
Unlike news stories, these are tracked/scheduled events with precise
launch pad coordinates, rocket details, and mission data. They skip LLM
extraction because all structured data is already available from the API.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Optional

from .config import (
    REQUEST_TIMEOUT,
    LAUNCHES_UPCOMING_URL,
    LAUNCHES_PREVIOUS_URL,
    LAUNCHES_CACHE_SECONDS,
)
from .source_utils import fetch_json as _shared_fetch_json, dedup_list, build_extraction

logger = logging.getLogger(__name__)

# Module-level cache to respect rate limits (15 req/hour free tier)
_cache = {
    "stories": [],
    "fetched_at": 0.0,
}

# Known launch providers -> additional concepts
_PROVIDER_CONCEPTS = {
    "spacex": ["spacex"],
    "space exploration technologies": ["spacex"],
    "falcon": ["spacex"],
    "starship": ["spacex"],
    "nasa": ["nasa"],
    "national aeronautics": ["nasa"],
    "sls": ["nasa"],
    "roscosmos": ["roscosmos"],
    "soyuz": ["roscosmos"],
    "esa": ["esa"],
    "european space agency": ["esa"],
    "ariane": ["arianespace"],
    "vega": ["arianespace"],
    "jaxa": ["jaxa"],
    "isro": ["isro"],
    "cnsa": ["cnsa"],
    "long march": ["cnsa"],
    "chang zheng": ["cnsa"],
    "casc": ["cnsa"],
    "ula": ["ula"],
    "united launch alliance": ["ula"],
    "atlas": ["ula"],
    "vulcan": ["ula"],
    "rocket lab": ["rocketlab"],
    "electron": ["rocketlab"],
    "blue origin": ["blueorigin"],
    "new glenn": ["blueorigin"],
    "arianespace": ["arianespace"],
    "northrop grumman": ["northropgrumman"],
    "antares": ["northropgrumman"],
    "relativity": ["relativity"],
    "astra": ["astra"],
    "virgin orbit": ["virginorbit"],
    "firefly": ["firefly"],
}


def _status_to_severity(status_abbrev: str, mission_desc: str) -> int:
    """Map launch status and mission to severity (1-5 scale).

    1 = minor, 2 = routine commercial, 3 = government/military,
    4 = ISS/crew mission, 5 = historic/maiden flight
    """
    desc_lower = (mission_desc or "").lower()
    name_lower = status_abbrev.lower() if status_abbrev else ""

    # Historic/maiden flights
    if "maiden" in desc_lower or "first" in desc_lower or "inaugural" in desc_lower:
        return 5

    # Crew missions / ISS
    if "crew" in desc_lower or "astronaut" in desc_lower or "cosmonaut" in desc_lower:
        return 4
    if " iss " in desc_lower or desc_lower.startswith("iss ") or desc_lower.endswith(" iss"):
        return 4
    if "international space station" in desc_lower:
        return 4

    # Government/military
    if "military" in desc_lower or "reconnaissance" in desc_lower or "spy" in desc_lower:
        return 3
    if "government" in desc_lower or "national security" in desc_lower:
        return 3

    # Default: routine commercial
    return 2


def _status_to_human_interest(status_abbrev: str, mission_desc: str, name: str) -> int:
    """Map launch details to human interest score (1-10).

    Historic launches get 9, crew missions get 8, routine Starlink gets 6.
    """
    desc_lower = (mission_desc or "").lower()
    name_lower = (name or "").lower()

    # Historic/maiden flights
    if "maiden" in desc_lower or "first" in desc_lower or "inaugural" in desc_lower:
        return 9

    # Crew missions
    if "crew" in desc_lower or "astronaut" in desc_lower or "cosmonaut" in desc_lower:
        return 8
    if " iss " in desc_lower or desc_lower.startswith("iss ") or desc_lower.endswith(" iss"):
        return 8
    if "international space station" in desc_lower:
        return 8

    # Deep space / planetary
    if "mars" in desc_lower or "moon" in desc_lower or "lunar" in desc_lower:
        return 8
    if "jupiter" in desc_lower or "saturn" in desc_lower or "asteroid" in desc_lower:
        return 8

    # Military/national security
    if "military" in desc_lower or "national security" in desc_lower:
        return 7

    # Routine Starlink
    if "starlink" in name_lower:
        return 6

    # Default
    return 7


def _get_provider_concepts(name: str) -> list:
    """Extract provider-specific concepts from launch name."""
    name_lower = (name or "").lower()
    concepts = []
    seen = set()
    for key, vals in _PROVIDER_CONCEPTS.items():
        if key in name_lower:
            for v in vals:
                if v not in seen:
                    seen.add(v)
                    concepts.append(v)
    return concepts


def _build_summary(launch: dict) -> str:
    """Build a descriptive summary from launch data."""
    parts = []

    name = launch.get("name", "")
    if name:
        parts.append(name)

    # Rocket info
    rocket = launch.get("rocket") or {}
    config = rocket.get("configuration") or {}
    rocket_name = config.get("name", "")
    if rocket_name and rocket_name not in name:
        parts.append("Rocket: %s" % rocket_name)

    # Mission description
    mission = launch.get("mission") or {}
    mission_desc = mission.get("description", "")
    if mission_desc:
        if len(mission_desc) > 300:
            mission_desc = mission_desc[:297] + "..."
        parts.append(mission_desc)

    # Pad location
    pad = launch.get("pad") or {}
    pad_name = pad.get("name", "")
    loc = pad.get("location") or {}
    loc_name = loc.get("name", "")
    if pad_name and loc_name:
        parts.append("Launch pad: %s, %s" % (pad_name, loc_name))
    elif loc_name:
        parts.append("Location: %s" % loc_name)

    # Status
    status = launch.get("status") or {}
    status_abbrev = status.get("abbrev", "")
    if status_abbrev:
        parts.append("Status: %s" % status_abbrev)

    # NET date
    net = launch.get("net", "")
    if net:
        parts.append("NET: %s" % net)

    return ". ".join(parts) + "." if parts else "Space launch."


def _build_event_signature(launch: dict) -> str:
    """Build an event_signature for clustering.

    Example: 'SpaceX Starlink Launch March 2026'
    """
    name = launch.get("name", "")

    # Try to extract a meaningful short name
    # Launch names are like "Falcon 9 Block 5 | Starlink Group 12-3"
    # Use the payload part (after |) if available
    if "|" in name:
        payload = name.split("|", 1)[1].strip()
    else:
        payload = name

    # Add month/year for temporal grouping
    net = launch.get("net", "")
    if net:
        try:
            dt = datetime.fromisoformat(net.replace("Z", "+00:00"))
            date_part = dt.strftime("%B %Y")
        except (ValueError, AttributeError):
            date_part = datetime.now(timezone.utc).strftime("%Y")
    else:
        date_part = datetime.now(timezone.utc).strftime("%Y")

    # Extract provider from name (before |)
    if "|" in name:
        rocket_part = name.split("|", 1)[0].strip()
        # Simplify: "Falcon 9 Block 5" -> "SpaceX" if known
        rocket_lower = rocket_part.lower()
        if "falcon" in rocket_lower or "starship" in rocket_lower:
            provider = "SpaceX"
        elif "atlas" in rocket_lower or "vulcan" in rocket_lower:
            provider = "ULA"
        elif "electron" in rocket_lower:
            provider = "Rocket Lab"
        elif "ariane" in rocket_lower:
            provider = "Arianespace"
        elif "soyuz" in rocket_lower:
            provider = "Roscosmos"
        elif "long march" in rocket_lower or "chang zheng" in rocket_lower:
            provider = "CNSA"
        else:
            provider = rocket_part.split()[0] if rocket_part else "Launch"
    else:
        provider = "Launch"

    return "%s %s %s" % (provider, payload, date_part)


def _fetch_json(url: str) -> dict:
    """Fetch JSON from a URL and return parsed data."""
    return _shared_fetch_json(url, key=None)


def _parse_launch(launch: dict, now: str) -> Optional[dict]:
    """Parse a single launch object into a story dict.

    Returns None if the launch is invalid or missing required fields.
    """
    name = launch.get("name", "")
    if not name:
        return None

    # URL (detail page)
    url = launch.get("url", "")
    if not url:
        return None

    # Coordinates from pad
    pad = launch.get("pad") or {}
    lat_str = pad.get("latitude")
    lon_str = pad.get("longitude")
    if lat_str is None or lon_str is None:
        return None

    try:
        lat = float(lat_str)
        lon = float(lon_str)
    except (ValueError, TypeError):
        return None

    # Status
    status = launch.get("status") or {}
    status_abbrev = status.get("abbrev", "TBD")

    # Mission
    mission = launch.get("mission") or {}
    mission_desc = mission.get("description", "")

    # Build fields
    summary = _build_summary(launch)
    event_sig = _build_event_signature(launch)
    severity = _status_to_severity(status_abbrev, mission_desc)
    hi_score = _status_to_human_interest(status_abbrev, mission_desc, name)

    # Provider concepts
    provider_concepts = _get_provider_concepts(name)
    concepts = dedup_list(["space", "science", "launch"] + provider_concepts)

    # Published time from NET
    net = launch.get("net", "")
    published_at = None
    if net:
        try:
            dt = datetime.fromisoformat(net.replace("Z", "+00:00"))
            published_at = dt.isoformat()
        except (ValueError, AttributeError):
            pass

    # Location name from pad
    loc = pad.get("location") or {}
    location_name = loc.get("name", "")
    if not location_name:
        location_name = pad.get("name", "Launch Pad")

    # Sentiment based on status
    sentiment = "neutral"
    if status_abbrev == "Success":
        sentiment = "positive"
    elif status_abbrev == "Failure":
        sentiment = "negative"

    story = {
        "title": name,
        "url": url,
        "summary": summary,
        "source": "Launch Library",
        "published_at": published_at,
        "scraped_at": now,
        "origin": "launches",
        "source_type": "inferred",
        "category": "science",
        "concepts": concepts,
        "location_name": location_name,
        "lat": lat,
        "lon": lon,
        "geocode_confidence": 1.0,
    }

    # Pre-build extraction data
    topics = ["space", "launch"]
    search_keywords = ["space", "launch", "rocket", location_name]
    for pc in provider_concepts:
        if pc not in search_keywords:
            search_keywords.append(pc)

    story["_extraction"] = build_extraction(
        event_sig=event_sig,
        topics=topics,
        severity=severity,
        sentiment=sentiment,
        primary_action="launch",
        hi_score=hi_score,
        locations=[
            {
                "name": location_name,
                "role": "event_location",
                "lat": lat,
                "lon": lon,
            }
        ],
        search_keywords=search_keywords,
    )

    return story


def scrape_launches() -> list:
    """Fetch upcoming and recent launches and return story dicts.

    Returns list of story dicts compatible with pipeline.process_story(),
    with pre-populated location, concept, and extraction data.
    Launch stories skip LLM extraction because all structured data is
    available directly from the Launch Library 2 API.

    Results are cached for LAUNCHES_CACHE_SECONDS to respect rate limits
    (free tier: 15 requests/hour).
    """
    # Check cache
    elapsed = time.monotonic() - _cache["fetched_at"]
    if _cache["stories"] and elapsed < LAUNCHES_CACHE_SECONDS:
        logger.info("Launches: returning %d cached stories (%.0fs old)",
                     len(_cache["stories"]), elapsed)
        return list(_cache["stories"])

    now = datetime.now(timezone.utc).isoformat()

    # Fetch both feeds
    upcoming_data = _fetch_json(LAUNCHES_UPCOMING_URL)
    previous_data = _fetch_json(LAUNCHES_PREVIOUS_URL)

    upcoming_results = upcoming_data.get("results", [])
    previous_results = previous_data.get("results", [])

    # Dedup by URL
    seen_urls = set()
    all_launches = []
    for launch in upcoming_results + previous_results:
        url = launch.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            all_launches.append(launch)

    stories = []
    for launch in all_launches:
        try:
            story = _parse_launch(launch, now)
            if story:
                stories.append(story)
        except Exception as e:
            logger.error("Error processing launch: %s", e)
            continue

    # Update cache
    _cache["stories"] = list(stories)
    _cache["fetched_at"] = time.monotonic()

    logger.info("Launches: fetched %d launches (%d upcoming, %d previous)",
                len(stories), len(upcoming_results), len(previous_results))
    return stories
