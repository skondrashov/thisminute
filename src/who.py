"""WHO Disease Outbreak News (DON) integration.

Fetches disease outbreak reports from the WHO DON RSS feed.
Low volume source (~2-5 items/week) providing global disease outbreak alerts.
These are authored by WHO epidemiologists, so source_type='reported'.
"""

import logging
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from .config import REQUEST_TIMEOUT, WHO_DON_URL
from .country_centroids import get_centroid
from .source_utils import build_extraction, attach_location, strip_html, current_year

logger = logging.getLogger(__name__)

# Disease keywords for concept enrichment
_DISEASE_KEYWORDS = {
    "avian influenza": ["avian influenza", "influenza"],
    "h5n1": ["avian influenza", "h5n1"],
    "h7n9": ["avian influenza", "h7n9"],
    "influenza": ["influenza"],
    "ebola": ["ebola"],
    "marburg": ["marburg"],
    "cholera": ["cholera"],
    "plague": ["plague"],
    "yellow fever": ["yellow fever"],
    "dengue": ["dengue"],
    "zika": ["zika"],
    "mpox": ["mpox"],
    "monkeypox": ["mpox"],
    "mers": ["mers", "coronavirus"],
    "sars": ["sars", "coronavirus"],
    "covid": ["covid-19", "coronavirus"],
    "measles": ["measles"],
    "polio": ["polio"],
    "diphtheria": ["diphtheria"],
    "meningitis": ["meningitis"],
    "lassa fever": ["lassa fever"],
    "rift valley fever": ["rift valley fever"],
    "nipah": ["nipah"],
    "hantavirus": ["hantavirus"],
    "anthrax": ["anthrax"],
    "hepatitis": ["hepatitis"],
    "typhoid": ["typhoid"],
    "malaria": ["malaria"],
    "chikungunya": ["chikungunya"],
    "oropouche": ["oropouche"],
}


def _parse_country_from_title(title):
    """Parse country name from WHO DON title format.

    Titles are typically: "Disease Name - Country Name"
    or "Disease Name - Country Name (extra info)"
    """
    if not title:
        return ""

    # Split on " - " (the standard delimiter)
    parts = title.split(" - ")
    if len(parts) >= 2:
        country_part = parts[-1].strip()
        # Remove parenthetical info
        if "(" in country_part:
            country_part = country_part[:country_part.index("(")].strip()
        return country_part

    return ""


def _extract_disease_concepts(title):
    """Extract disease-specific concepts from the title."""
    from .source_utils import dedup_list
    raw = ["disease", "outbreak", "health"]
    title_lower = title.lower()

    for keyword, disease_concepts in _DISEASE_KEYWORDS.items():
        if keyword in title_lower:
            raw.extend(disease_concepts)

    return dedup_list(raw)


def _build_event_signature(title):
    """Build event signature from DON title.

    Example: "2026 H5N1 Avian Influenza United States"
    """
    year = current_year()
    if title:
        sig = title if len(title) <= 60 else title[:57] + "..."
        return "%s %s" % (year, sig)
    return "%s Disease Outbreak" % year


def _severity_from_title(title):
    """Estimate severity from title context."""
    title_lower = title.lower()
    # High-threat diseases
    if any(d in title_lower for d in ["ebola", "marburg", "plague", "anthrax", "nipah"]):
        return 4
    if any(d in title_lower for d in ["cholera", "mers", "avian influenza", "h5n1"]):
        return 3
    return 2


def _human_interest_from_title(title):
    """Estimate human interest from title context."""
    title_lower = title.lower()
    if any(d in title_lower for d in ["ebola", "marburg", "plague"]):
        return 7
    if any(d in title_lower for d in ["avian influenza", "cholera", "mers"]):
        return 6
    if any(d in title_lower for d in ["mpox", "measles", "dengue"]):
        return 5
    return 4


def _fetch_don_rss():
    """Fetch WHO Disease Outbreak News RSS feed."""
    try:
        req = urllib.request.Request(
            WHO_DON_URL,
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
        logger.error("Failed to fetch WHO DON RSS: %s", e)
        return []


def scrape_who():
    """Fetch WHO Disease Outbreak News and return story dicts.

    Returns list of story dicts compatible with pipeline.process_story(),
    with pre-populated location, concept, and extraction data.
    source_type is 'reported' since these are authored by WHO epidemiologists.
    """
    now = datetime.now(timezone.utc).isoformat()
    items = _fetch_don_rss()

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

            # Summary from description
            description = item.get("description", "")
            if description:
                clean = strip_html(description)
                summary = clean[:500].strip()
                if len(clean) > 500:
                    summary += "..."
            else:
                summary = title

            # Parse country from title
            country_name = _parse_country_from_title(title)
            lat, lon = None, None
            if country_name:
                centroid = get_centroid(country_name)
                if centroid:
                    lat, lon = centroid

            concepts = _extract_disease_concepts(title)
            event_sig = _build_event_signature(title)
            severity = _severity_from_title(title)
            hi_score = _human_interest_from_title(title)

            location_name = country_name or "Global"

            story = {
                "title": title,
                "url": url,
                "summary": summary,
                "source": "WHO",
                "published_at": item.get("pubDate"),
                "scraped_at": now,
                "origin": "who",
                "source_type": "reported",
                "category": "health",
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
                primary_action="outbreak",
                hi_score=hi_score,
                locations=extraction_locations,
                search_keywords=concepts[:3] + [country_name] if country_name else concepts[:3],
            )

            stories.append(story)
        except Exception as e:
            logger.error("Error processing WHO DON item: %s", e)
            continue

    logger.info("WHO DON: fetched %d outbreak reports", len(stories))
    return stories
