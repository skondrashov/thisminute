"""US State Department Travel Advisories integration.

Fetches travel advisories from the State Department RSS feed.
Creates stories for countries with active Level 2+ advisories.
Level 1 (Exercise Normal Precautions) is filtered out to reduce noise.
source_type is 'inferred' since these are advisory classifications.
"""

import logging
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from .config import REQUEST_TIMEOUT, TRAVEL_ADVISORY_URL
from .country_centroids import get_centroid
from .source_utils import build_extraction, attach_location, dedup_list, strip_html, current_year

logger = logging.getLogger(__name__)

# Advisory level -> severity mapping
# Level 4 maps to 5 (skipping 4) to emphasize "Do Not Travel"
_LEVEL_SEVERITY = {1: 1, 2: 2, 3: 3, 4: 5}

# Advisory level -> human_interest mapping
_LEVEL_HUMAN_INTEREST = {1: 2, 2: 4, 3: 6, 4: 9}

# Advisory level labels
_LEVEL_LABELS = {
    1: "Exercise Normal Precautions",
    2: "Exercise Increased Caution",
    3: "Reconsider Travel",
    4: "Do Not Travel",
}

# Keywords in descriptions that suggest specific threat concepts
_THREAT_KEYWORDS = {
    "terrorism": ["terrorism"],
    "terrorist": ["terrorism"],
    "conflict": ["conflict"],
    "civil unrest": ["civil unrest", "protest"],
    "crime": ["crime"],
    "kidnapping": ["kidnapping", "crime"],
    "armed conflict": ["conflict", "war"],
    "war": ["war", "conflict"],
    "health": ["health"],
    "disease": ["health", "disease"],
    "natural disaster": ["natural disaster"],
    "piracy": ["piracy"],
    "wrongful detention": ["detention"],
    "nuclear": ["nuclear"],
}


def _parse_advisory_level(title):
    """Extract advisory level (1-4) from title.

    Titles are typically: "CountryName - Travel Advisory (Level N: Label)"
    or "CountryName Travel Advisory - Level N: Label"
    """
    if not title:
        return None

    # Look for "Level N" pattern
    match = re.search(r'Level\s+(\d)', title, re.IGNORECASE)
    if match:
        level = int(match.group(1))
        if 1 <= level <= 4:
            return level

    return None


def _parse_country_from_title(title):
    """Extract country name from advisory title.

    Titles are typically:
    "CountryName - Travel Advisory"
    "CountryName Travel Advisory"
    """
    if not title:
        return ""

    # Try "Country - Travel Advisory" pattern first
    parts = title.split(" - ")
    if len(parts) >= 2:
        country = parts[0].strip()
        # Remove "Travel Advisory" and level info if present
        country = re.sub(r'\s*Travel Advisory.*', '', country, flags=re.IGNORECASE)
        if country:
            return country

    # Try "Country Travel Advisory" pattern
    match = re.match(r'^(.+?)\s+Travel Advisory', title, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return ""


def _extract_threat_concepts(description):
    """Extract threat-specific concepts from advisory description."""
    raw = ["travel", "safety"]
    if not description:
        return raw

    desc_lower = description.lower()
    for keyword, concepts in _THREAT_KEYWORDS.items():
        if keyword in desc_lower:
            raw.extend(concepts)

    return dedup_list(raw)


def _build_event_signature(country_name):
    """Build event signature for clustering.

    Format: "2026 CountryName Travel Advisory"
    """
    year = current_year()
    if country_name:
        return "%s %s Travel Advisory" % (year, country_name)
    return "%s Travel Advisory" % year


def _fetch_advisory_rss():
    """Fetch US State Department travel advisory RSS feed."""
    try:
        req = urllib.request.Request(
            TRAVEL_ADVISORY_URL,
            headers={"User-Agent": "thisminute-news-map/1.0"},
        )
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8")

        root = ET.fromstring(raw)
        items = []

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

            items.append(entry)

        return items
    except Exception as e:
        logger.error("Failed to fetch travel advisory RSS: %s", e)
        return []


def scrape_travel_advisories():
    """Fetch US State Department travel advisories and return story dicts.

    Returns list of story dicts compatible with pipeline.process_story(),
    with pre-populated location, concept, and extraction data.
    Only Level 2+ advisories are included (Level 1 = normal precautions).
    source_type is 'inferred' since these are advisory classifications.
    """
    now = datetime.now(timezone.utc).isoformat()
    items = _fetch_advisory_rss()

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

            # Parse advisory level
            level = _parse_advisory_level(title)
            if level is None:
                # Try to infer from description
                description = item.get("description", "")
                if description:
                    level = _parse_advisory_level(description)
            if level is None:
                level = 2  # Default to Level 2 if unparseable

            # Filter out Level 1 (Exercise Normal Precautions)
            if level < 2:
                continue

            # Parse country name
            country_name = _parse_country_from_title(title)

            # Summary from description
            description = item.get("description", "")
            if description:
                clean = strip_html(description)
                summary = clean[:500].strip()
                if len(clean) > 500:
                    summary += "..."
            else:
                level_label = _LEVEL_LABELS.get(level, "")
                summary = "%s: %s" % (title, level_label) if level_label else title

            # Geocode country
            lat, lon = None, None
            if country_name:
                centroid = get_centroid(country_name)
                if centroid:
                    lat, lon = centroid

            concepts = _extract_threat_concepts(description)
            event_sig = _build_event_signature(country_name)
            severity = _LEVEL_SEVERITY.get(level, 2)
            hi_score = _LEVEL_HUMAN_INTEREST.get(level, 4)

            location_name = country_name or "Global"

            story = {
                "title": title,
                "url": url,
                "summary": summary,
                "source": "US State Dept",
                "published_at": item.get("pubDate"),
                "scraped_at": now,
                "origin": "travel",
                "source_type": "inferred",
                "category": "politics",
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
                primary_action="advisory",
                hi_score=hi_score,
                locations=extraction_locations,
                search_keywords=concepts[:3] + [country_name] if country_name else concepts[:3],
            )

            stories.append(story)
        except Exception as e:
            logger.error("Error processing travel advisory item: %s", e)
            continue

    logger.info("Travel Advisories: fetched %d advisories", len(stories))
    return stories
