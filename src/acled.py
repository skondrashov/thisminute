"""ACLED (Armed Conflict Location & Event Data) integration.

Fetches recent conflict events from the ACLED API. Covers battles,
explosions, violence against civilians, protests, riots, and strategic
developments worldwide. Pre-builds extraction dicts so zero LLM cost.

Requires ACLED_API_KEY and ACLED_EMAIL environment variables (free
registration at https://developer.acleddata.com/). Gracefully skips
if credentials are not set.
"""

import logging
from datetime import datetime, timezone, timedelta

from .config import REQUEST_TIMEOUT, ACLED_API_KEY, ACLED_EMAIL, ACLED_URL, ACLED_MAX_EVENTS
from .source_utils import fetch_json, build_extraction, attach_location, dedup_list, current_year

logger = logging.getLogger(__name__)

# Event type -> severity base (before fatality adjustment)
_EVENT_SEVERITY = {
    "Battles": 3,
    "Explosions/Remote violence": 3,
    "Violence against civilians": 3,
    "Protests": 1,
    "Riots": 2,
    "Strategic developments": 1,
}

# Event type -> human interest base (before fatality adjustment)
_EVENT_HUMAN_INTEREST = {
    "Battles": 5,
    "Explosions/Remote violence": 5,
    "Violence against civilians": 6,
    "Protests": 4,
    "Riots": 5,
    "Strategic developments": 3,
}

# Event type -> extra concepts
_EVENT_CONCEPTS = {
    "Battles": ["battle", "military"],
    "Explosions/Remote violence": ["explosion", "attack"],
    "Violence against civilians": ["civilian casualties", "atrocity"],
    "Protests": ["protest", "demonstration"],
    "Riots": ["riot", "unrest"],
    "Strategic developments": ["political", "diplomacy"],
}


def _severity_with_fatalities(event_type, fatalities):
    """Calculate severity (1-5) from event type and fatalities."""
    base = _EVENT_SEVERITY.get(event_type, 2)
    if fatalities >= 100:
        return 5
    elif fatalities >= 20:
        return min(base + 2, 5)
    elif fatalities >= 5:
        return min(base + 1, 5)
    elif fatalities >= 1:
        return max(base, 3) if event_type in ("Battles", "Explosions/Remote violence", "Violence against civilians") else base
    return base


def _human_interest_with_fatalities(event_type, fatalities):
    """Calculate human interest (1-10) from event type and fatalities."""
    base = _EVENT_HUMAN_INTEREST.get(event_type, 4)
    if fatalities >= 100:
        return 10
    elif fatalities >= 50:
        return 9
    elif fatalities >= 20:
        return 8
    elif fatalities >= 10:
        return 7
    elif fatalities >= 5:
        return min(base + 2, 10)
    elif fatalities >= 1:
        return min(base + 1, 10)
    return base


def _get_concepts(event_type):
    """Build concept list from event type."""
    base = ["conflict", "violence"]
    extra = _EVENT_CONCEPTS.get(event_type, [])
    return dedup_list(base + extra)


def _get_category(event_type):
    """Determine category from event type."""
    if event_type in ("Protests", "Strategic developments"):
        return "politics"
    return "conflict"


def _build_event_signature(country, event_type):
    """Build event signature for clustering."""
    year = current_year()
    # Clean event type for signature
    clean_type = event_type
    if "/" in clean_type:
        clean_type = clean_type.split("/")[0].strip()
    return "%s %s %s" % (year, country, clean_type)


def _build_title(event_type, sub_event_type, country, admin1):
    """Build human-readable title."""
    location = country
    if admin1:
        location = "%s, %s" % (admin1, country)
    label = sub_event_type if sub_event_type else event_type
    return "%s in %s" % (label, location)


def _build_summary(event_type, sub_event_type, notes, fatalities, actor1, actor2, source):
    """Build descriptive summary."""
    parts = []
    if notes:
        clean = notes.strip()
        if len(clean) > 400:
            clean = clean[:397] + "..."
        parts.append(clean)
    else:
        desc = sub_event_type if sub_event_type else event_type
        parts.append("%s event reported." % desc)

    if fatalities and fatalities > 0:
        parts.append("Fatalities: %d." % fatalities)

    actors = []
    if actor1:
        actors.append(actor1)
    if actor2:
        actors.append(actor2)
    if actors:
        parts.append("Actors: %s." % ", ".join(actors))

    if source:
        parts.append("Source: %s." % source)

    return " ".join(parts)


def _build_url(data_id):
    """Build a stable dedup URL from ACLED data_id."""
    return "https://acleddata.com/data/%s" % data_id


def _fetch_acled():
    """Fetch recent ACLED events. Returns list of event dicts or [].

    Fetches last 7 days of events, capped at ACLED_MAX_EVENTS (default 200).
    """
    if not ACLED_API_KEY or not ACLED_EMAIL:
        return []

    seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    url = "%s?key=%s&email=%s&limit=%d&event_date=%s&event_date_where=%%3E%%3D" % (
        ACLED_URL, ACLED_API_KEY, ACLED_EMAIL, ACLED_MAX_EVENTS, seven_days_ago)
    safe_url = "%s?key=REDACTED&email=REDACTED&limit=%d&event_date=%s" % (
        ACLED_URL, ACLED_MAX_EVENTS, seven_days_ago)

    return fetch_json(url, key="data", log_url=safe_url)


def scrape_acled():
    """Fetch ACLED conflict events and return story dicts.

    Returns list of story dicts compatible with pipeline.process_story(),
    with pre-populated location, concept, and extraction data.
    Gracefully returns empty list if ACLED_API_KEY or ACLED_EMAIL not set.
    """
    if not ACLED_API_KEY or not ACLED_EMAIL:
        logger.info("ACLED: skipping (no ACLED_API_KEY or ACLED_EMAIL set)")
        return []

    now = datetime.now(timezone.utc).isoformat()
    events = _fetch_acled()

    if not events:
        logger.info("ACLED: no events returned")
        return []

    seen_ids = set()
    stories = []

    for event in events:
        try:
            data_id = str(event.get("data_id", ""))
            if not data_id:
                continue
            if data_id in seen_ids:
                continue
            seen_ids.add(data_id)

            event_type = event.get("event_type", "")
            sub_event_type = event.get("sub_event_type", "")
            country = event.get("country", "")
            admin1 = event.get("admin1", "")
            actor1 = event.get("actor1", "")
            actor2 = event.get("actor2", "")
            notes = event.get("notes", "")
            source = event.get("source", "")
            event_date = event.get("event_date", "")

            if not country or not event_type:
                continue

            # Parse coordinates
            lat, lon = None, None
            try:
                lat_str = event.get("latitude", "")
                lon_str = event.get("longitude", "")
                if lat_str and lon_str:
                    lat = float(lat_str)
                    lon = float(lon_str)
            except (ValueError, TypeError):
                pass

            # Parse fatalities
            fatalities = 0
            try:
                fat_val = event.get("fatalities", 0)
                if fat_val:
                    fatalities = int(fat_val)
            except (ValueError, TypeError):
                pass

            title = _build_title(event_type, sub_event_type, country, admin1)
            summary = _build_summary(
                event_type, sub_event_type, notes, fatalities,
                actor1, actor2, source)
            url = _build_url(data_id)
            event_sig = _build_event_signature(country, event_type)
            severity = _severity_with_fatalities(event_type, fatalities)
            hi_score = _human_interest_with_fatalities(event_type, fatalities)
            concepts = _get_concepts(event_type)
            category = _get_category(event_type)

            location_name = admin1 if admin1 else country

            story = {
                "title": title,
                "url": url,
                "summary": summary,
                "source": "ACLED",
                "published_at": event_date,
                "scraped_at": now,
                "origin": "acled",
                "source_type": "inferred",
                "category": category,
                "concepts": concepts,
                "location_name": location_name,
                "geocode_confidence": 0.9,
            }

            extraction_locations = attach_location(
                story, lat, lon, location_name, confidence=0.9)

            topics = list(concepts)

            sentiment = "negative"
            if event_type == "Protests":
                sentiment = "mixed"
            elif event_type == "Strategic developments":
                sentiment = "neutral"

            primary_action = event_type.lower().split("/")[0].strip()

            story["_extraction"] = build_extraction(
                event_sig=event_sig,
                topics=topics,
                severity=severity,
                sentiment=sentiment,
                primary_action=primary_action,
                hi_score=hi_score,
                locations=extraction_locations,
                search_keywords=dedup_list(
                    [event_type.lower(), country.lower()] +
                    ([admin1.lower()] if admin1 else [])
                ),
            )

            stories.append(story)
        except Exception as e:
            logger.error("Error processing ACLED event: %s", e)
            continue

    logger.info("ACLED: fetched %d conflict events", len(stories))
    return stories
