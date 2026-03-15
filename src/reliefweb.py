"""ReliefWeb (UN OCHA) humanitarian reports integration.

Fetches recent humanitarian reports from the ReliefWeb API.
These are authored reports from UN/NGO sources about disasters, conflicts,
epidemics, and other humanitarian situations. Unlike sensor data sources,
these are human-written reports with source_type='reported'.
"""

import logging
from datetime import datetime, timezone

from .config import REQUEST_TIMEOUT, RELIEFWEB_URL
from .country_centroids import get_centroid
from .source_utils import (
    fetch_json, build_extraction, attach_location, strip_html, current_year,
)

logger = logging.getLogger(__name__)

# Disaster type keywords -> concepts
_DISASTER_CONCEPTS = {
    "flood": ["flood"],
    "earthquake": ["earthquake"],
    "epidemic": ["epidemic", "health"],
    "cyclone": ["cyclone", "hurricane"],
    "hurricane": ["hurricane"],
    "typhoon": ["cyclone", "hurricane"],
    "tornado": ["tornado"],
    "tsunami": ["tsunami"],
    "drought": ["drought"],
    "volcano": ["volcano"],
    "conflict": ["conflict", "war"],
    "displacement": ["displacement", "refugee"],
    "food": ["food crisis", "hunger"],
    "famine": ["famine", "hunger"],
    "fire": ["wildfire"],
    "wildfire": ["wildfire"],
    "landslide": ["landslide"],
    "cold wave": ["cold wave"],
    "heat wave": ["heat wave"],
    "storm": ["storm"],
    "insecurity": ["conflict"],
    "violence": ["conflict", "violence"],
    "cholera": ["cholera", "epidemic"],
    "malaria": ["malaria", "epidemic"],
    "ebola": ["ebola", "epidemic"],
    "measles": ["measles", "epidemic"],
    "covid": ["covid-19", "epidemic"],
    "mpox": ["mpox", "epidemic"],
    "avian influenza": ["avian influenza", "epidemic"],
}

# Disaster type keywords -> category
_DISASTER_CATEGORIES = {
    "flood": "disaster",
    "earthquake": "disaster",
    "cyclone": "disaster",
    "hurricane": "disaster",
    "typhoon": "disaster",
    "tornado": "disaster",
    "tsunami": "disaster",
    "volcano": "disaster",
    "fire": "disaster",
    "wildfire": "disaster",
    "landslide": "disaster",
    "drought": "environment",
    "epidemic": "health",
    "cholera": "health",
    "malaria": "health",
    "ebola": "health",
    "measles": "health",
    "covid": "health",
    "mpox": "health",
    "avian influenza": "health",
    "conflict": "crisis",
    "displacement": "crisis",
    "food": "crisis",
    "famine": "crisis",
    "violence": "crisis",
    "insecurity": "crisis",
}


def _extract_concepts(title, disaster_types):
    """Extract concepts from disaster type names and title."""
    from .source_utils import dedup_list
    raw = []

    # From disaster types
    for dt in disaster_types:
        dt_lower = dt.lower()
        for key, vals in _DISASTER_CONCEPTS.items():
            if key in dt_lower:
                raw.extend(vals)

    # From title
    title_lower = title.lower()
    for key, vals in _DISASTER_CONCEPTS.items():
        if key in title_lower:
            raw.extend(vals)

    concepts = dedup_list(raw)
    if not concepts:
        concepts = ["humanitarian"]

    return concepts


def _extract_category(title, disaster_types):
    """Determine category from disaster type names and title."""
    # Check disaster types first
    for dt in disaster_types:
        dt_lower = dt.lower()
        for key, cat in _DISASTER_CATEGORIES.items():
            if key in dt_lower:
                return cat

    # Check title
    title_lower = title.lower()
    for key, cat in _DISASTER_CATEGORIES.items():
        if key in title_lower:
            return cat

    return "crisis"


def _extract_country_name(report):
    """Extract primary country name from a ReliefWeb report."""
    # Try primary_country first
    pc = report.get("primary_country")
    if isinstance(pc, dict) and pc.get("name"):
        return pc["name"]
    if isinstance(pc, list) and pc:
        if isinstance(pc[0], dict):
            return pc[0].get("name", "")
        return str(pc[0])

    # Fall back to country list
    countries = report.get("country", [])
    if isinstance(countries, list) and countries:
        if isinstance(countries[0], dict):
            return countries[0].get("name", "")
        return str(countries[0])

    return ""


def _build_event_signature(title, disaster_types, country):
    """Build event signature from disaster name or country + type."""
    year = current_year()

    # Use disaster name if available
    if disaster_types:
        dt = disaster_types[0]
        if len(dt) <= 60:
            return "%s %s" % (year, dt)

    # Fall back to country + general type
    if country:
        category = _extract_category(title, disaster_types)
        return "%s %s %s" % (year, country, category.title())

    # Fall back to title
    sig = title if len(title) <= 60 else title[:57] + "..."
    return "%s %s" % (year, sig)


def _severity_from_title(title):
    """Estimate severity from title keywords."""
    title_lower = title.lower()
    if any(w in title_lower for w in ["emergency", "catastroph", "crisis", "famine"]):
        return 4
    if any(w in title_lower for w in ["severe", "major", "deadly", "fatal"]):
        return 3
    if any(w in title_lower for w in ["warning", "alert", "update"]):
        return 2
    return 2


def _human_interest_from_title(title):
    """Estimate human interest from title keywords."""
    title_lower = title.lower()
    if any(w in title_lower for w in ["emergency", "catastroph", "crisis", "death"]):
        return 7
    if any(w in title_lower for w in ["severe", "major", "deadly", "conflict"]):
        return 6
    if any(w in title_lower for w in ["flood", "earthquake", "cyclone", "epidemic"]):
        return 5
    return 4


def _fetch_reports():
    """Fetch recent reports from ReliefWeb API."""
    return fetch_json(RELIEFWEB_URL, key="data")


def scrape_reliefweb():
    """Fetch ReliefWeb reports and return story dicts.

    Returns list of story dicts compatible with pipeline.process_story(),
    with pre-populated location, concept, and extraction data.
    source_type is 'reported' since these are authored humanitarian reports.
    """
    now = datetime.now(timezone.utc).isoformat()
    reports = _fetch_reports()

    seen_urls = set()
    stories = []

    for report in reports:
        try:
            fields = report.get("fields", {})
            if not fields:
                continue

            title = fields.get("title", "")
            if not title:
                continue

            url = fields.get("url", "")
            if not url:
                # Construct from report ID
                report_id = report.get("id")
                if report_id:
                    url = "https://reliefweb.int/node/%s" % report_id
                else:
                    continue

            if url in seen_urls:
                continue
            seen_urls.add(url)

            # Summary from body text
            body = fields.get("body", "") or ""
            if body:
                clean = strip_html(body)
                summary = clean[:500].strip()
                if len(clean) > 500:
                    summary += "..."
            else:
                summary = title

            # Country and geolocation
            country_name = _extract_country_name(fields)
            lat, lon = None, None
            if country_name:
                centroid = get_centroid(country_name)
                if centroid:
                    lat, lon = centroid

            # Source organization
            source_orgs = fields.get("source", [])
            source_name = "ReliefWeb"
            if isinstance(source_orgs, list) and source_orgs:
                if isinstance(source_orgs[0], dict):
                    source_name = source_orgs[0].get("name", "ReliefWeb")
                elif isinstance(source_orgs[0], str):
                    source_name = source_orgs[0]

            # Disaster types
            disaster_list = fields.get("disaster", [])
            disaster_types = []
            if isinstance(disaster_list, list):
                for d in disaster_list:
                    if isinstance(d, dict) and d.get("name"):
                        disaster_types.append(d["name"])
                    elif isinstance(d, str):
                        disaster_types.append(d)

            concepts = _extract_concepts(title, disaster_types)
            category = _extract_category(title, disaster_types)
            severity = _severity_from_title(title)
            hi_score = _human_interest_from_title(title)
            event_sig = _build_event_signature(title, disaster_types, country_name)

            # Published date
            date_info = fields.get("date", {})
            published_at = None
            if isinstance(date_info, dict):
                published_at = date_info.get("created") or date_info.get("original")
            elif isinstance(date_info, str):
                published_at = date_info

            location_name = country_name or title

            story = {
                "title": title,
                "url": url,
                "summary": summary,
                "source": source_name,
                "published_at": published_at,
                "scraped_at": now,
                "origin": "reliefweb",
                "source_type": "reported",
                "category": category,
                "concepts": concepts,
                "location_name": location_name,
                "geocode_confidence": 0.6,
            }

            extraction_locations = attach_location(
                story, lat, lon, location_name, confidence=0.7)

            topics = list(concepts)

            story["_extraction"] = build_extraction(
                event_sig=event_sig,
                topics=topics,
                severity=severity,
                sentiment="negative",
                primary_action=concepts[0] if concepts else "humanitarian",
                hi_score=hi_score,
                locations=extraction_locations,
                search_keywords=concepts[:3] + [country_name] if country_name else concepts[:3],
            )

            stories.append(story)
        except Exception as e:
            logger.error("Error processing ReliefWeb report: %s", e)
            continue

    logger.info("ReliefWeb: fetched %d reports", len(stories))
    return stories
