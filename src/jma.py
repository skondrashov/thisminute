"""JMA (Japan Meteorological Agency) weather warnings integration.

Fetches active weather warnings from JMA's bosai API for Japan.
This gives the Weather preset Asia-Pacific coverage alongside NOAA
(Americas) and Meteoalarm (Europe).

JMA's bosai API returns JSON with warning codes and area codes.
Area names are resolved via a separate area.json endpoint (cached).
No authentication required.

API:
  - Warnings: https://www.jma.go.jp/bosai/warning/data/warning/map.json
  - Area codes: https://www.jma.go.jp/bosai/common/const/area.json
"""

import logging
import time
from datetime import datetime, timezone

from .config import (
    REQUEST_TIMEOUT,
    JMA_WARNINGS_URL,
    JMA_AREA_URL,
    JMA_CACHE_SECONDS,
    JMA_MAX_ALERTS,
    JMA_TIMEOUT,
)
from .source_utils import fetch_json, dedup_list, build_extraction, attach_location, current_year

logger = logging.getLogger(__name__)

# Module-level cache for warnings and area data
_cache = {
    "stories": [],
    "fetched_at": 0.0,
}

_area_cache = {
    "data": {},
    "fetched_at": 0.0,
}

# JMA warning code -> (English name, level, severity, human_interest)
# level: "special_warning" (highest), "warning", "advisory" (lowest)
# Codes from JMA VPWW54 specification
_WARNING_CODES = {
    # Special warnings (tokubetsu keihoo) -- severity 4-5, very rare
    "04": ("Heavy Rain Special Warning", "special_warning", 5, 9),
    "08": ("Storm Special Warning", "special_warning", 5, 9),
    "17": ("Storm Surge Special Warning", "special_warning", 5, 9),
    # Warnings (keihoo) -- severity 3
    "03": ("Flood Warning", "warning", 3, 6),
    "05": ("Heavy Rain Warning", "warning", 3, 7),
    "06": ("Snowstorm Warning", "warning", 3, 6),
    "09": ("Storm Warning", "warning", 3, 7),
    "12": ("Heavy Snow Warning", "warning", 3, 6),
    "16": ("High Wave Warning", "warning", 3, 5),
    "18": ("Storm Surge Warning", "warning", 3, 6),
    # Advisories (chuuihoo) -- severity 1-2
    "02": ("Flood Advisory", "advisory", 2, 3),
    "07": ("Thunderstorm Advisory", "advisory", 2, 4),
    "10": ("Heavy Rain Advisory", "advisory", 2, 3),
    "13": ("Snowstorm Advisory", "advisory", 2, 3),
    "14": ("Wave Advisory", "advisory", 1, 2),
    "15": ("Wind Advisory", "advisory", 2, 3),
    "19": ("Storm Surge Advisory", "advisory", 2, 3),
    "20": ("Avalanche Advisory", "advisory", 2, 4),
    "22": ("Heavy Snow Advisory", "advisory", 2, 3),
    # Low-value advisories (filtered by default)
    "21": ("Dry Air Advisory", "advisory", 1, 1),
    "24": ("Dense Fog Advisory", "advisory", 1, 2),
    "26": ("Low Temperature Advisory", "advisory", 1, 2),
    "32": ("Frost Advisory", "advisory", 1, 1),
}

# Warning codes to skip (low meteorological interest)
_SKIP_CODES = {"21", "24", "26", "32"}

# Warning code -> weather concepts for extraction
_WARNING_CONCEPTS = {
    "02": ["flood"],
    "03": ["flood"],
    "04": ["rain", "flood"],
    "05": ["rain", "flood"],
    "06": ["winter storm", "snow"],
    "07": ["thunderstorm"],
    "08": ["storm", "wind"],
    "09": ["storm", "wind"],
    "10": ["rain"],
    "12": ["snow", "winter storm"],
    "13": ["snow", "wind"],
    "14": ["wave"],
    "15": ["wind"],
    "16": ["wave"],
    "17": ["storm surge"],
    "18": ["storm surge"],
    "19": ["storm surge"],
    "20": ["avalanche"],
    "22": ["snow"],
}

# Japan prefecture centroids (lat, lon) keyed by first 2 digits of area code
# 01=Hokkaido through 47=Okinawa
_PREFECTURE_CENTROIDS = {
    "01": (43.06, 141.35),   # Hokkaido
    "02": (40.82, 140.74),   # Aomori
    "03": (39.70, 141.15),   # Iwate
    "04": (38.27, 140.87),   # Miyagi
    "05": (39.72, 140.10),   # Akita
    "06": (38.24, 140.34),   # Yamagata
    "07": (37.75, 140.47),   # Fukushima
    "08": (36.34, 140.45),   # Ibaraki
    "09": (36.57, 139.88),   # Tochigi
    "10": (36.39, 139.06),   # Gunma
    "11": (35.86, 139.65),   # Saitama
    "12": (35.60, 140.12),   # Chiba
    "13": (35.68, 139.69),   # Tokyo
    "14": (35.45, 139.64),   # Kanagawa
    "15": (37.90, 139.02),   # Niigata
    "16": (36.70, 137.21),   # Toyama
    "17": (36.59, 136.63),   # Ishikawa
    "18": (36.07, 136.22),   # Fukui
    "19": (35.66, 138.57),   # Yamanashi
    "20": (36.23, 138.18),   # Nagano
    "21": (35.39, 136.72),   # Gifu
    "22": (34.98, 138.38),   # Shizuoka
    "23": (35.18, 136.91),   # Aichi
    "24": (34.73, 136.51),   # Mie
    "25": (35.00, 135.87),   # Shiga
    "26": (35.02, 135.76),   # Kyoto
    "27": (34.69, 135.52),   # Osaka
    "28": (34.69, 135.18),   # Hyogo
    "29": (34.69, 135.83),   # Nara
    "30": (34.23, 135.17),   # Wakayama
    "31": (35.50, 134.24),   # Tottori
    "32": (35.47, 133.05),   # Shimane
    "33": (34.66, 133.93),   # Okayama
    "34": (34.40, 132.46),   # Hiroshima
    "35": (34.19, 131.47),   # Yamaguchi
    "36": (34.07, 134.56),   # Tokushima
    "37": (34.34, 134.04),   # Kagawa
    "38": (33.84, 132.77),   # Ehime
    "39": (33.56, 133.53),   # Kochi
    "40": (33.61, 130.42),   # Fukuoka
    "41": (33.25, 130.30),   # Saga
    "42": (32.74, 129.87),   # Nagasaki
    "43": (32.79, 130.74),   # Kumamoto
    "44": (33.24, 131.61),   # Oita
    "45": (31.91, 131.42),   # Miyazaki
    "46": (31.56, 130.56),   # Kagoshima
    "47": (26.34, 127.80),   # Okinawa
}

# Status values: issued / continuing (active states)
_ACTIVE_STATUSES = ("\u767a\u8868", "\u7d99\u7d9a")  # hatsu-hyou, keizoku


def _fetch_warnings():
    """Fetch the JMA warning map data (all prefectures)."""
    return fetch_json(
        JMA_WARNINGS_URL,
        key=None,
        timeout=JMA_TIMEOUT,
    )


def _fetch_area_names():
    """Fetch and cache the JMA area code -> English name mapping.

    Returns a dict mapping area code strings to English names.
    Cached for 24 hours since area codes rarely change.
    """
    elapsed = time.monotonic() - _area_cache["fetched_at"]
    if _area_cache["data"] and elapsed < 86400:  # 24 hour cache
        return _area_cache["data"]

    data = fetch_json(JMA_AREA_URL, key=None, timeout=JMA_TIMEOUT)
    if not data:
        return _area_cache["data"]  # return stale cache on failure

    lookup = {}
    for level in ("centers", "offices", "class10s", "class15s", "class20s"):
        for code, info in data.get(level, {}).items():
            en_name = info.get("enName", "")
            if en_name:
                lookup[code] = en_name

    _area_cache["data"] = lookup
    _area_cache["fetched_at"] = time.monotonic()
    logger.info("JMA: cached %d area names", len(lookup))
    return lookup


def _get_area_name(code, area_names):
    """Resolve an area code to an English name."""
    name = area_names.get(code, "")
    if name:
        return name
    # Try parent prefectures by truncating code
    if len(code) >= 6:
        parent = code[:6]
        name = area_names.get(parent, "")
        if name:
            return name
    return "Japan"


def _get_centroid(area_code):
    """Get approximate lat/lon for an area code.

    Uses the first 2 digits (prefecture code) to look up centroids.
    """
    prefix = area_code[:2]
    return _PREFECTURE_CENTROIDS.get(prefix)


def _get_warning_info(code):
    """Look up warning code metadata.

    Returns (name, level, severity, human_interest) or None if unknown.
    """
    return _WARNING_CODES.get(code)


def _get_warning_concepts(code):
    """Get weather concepts for a warning code."""
    return list(_WARNING_CONCEPTS.get(code, []))


def _build_title(warning_name, area_name):
    """Build a title from warning name and area."""
    return "%s - %s, Japan" % (warning_name, area_name)


def _build_summary(warning_name, area_name, level):
    """Build a summary for the warning."""
    level_label = level.replace("_", " ").title()
    return ("JMA %s: %s issued for %s, Japan." %
            (level_label, warning_name, area_name))


def _build_event_signature(warning_name, area_name):
    """Build event signature for clustering.

    Groups by warning type + region.
    Format: "2026 AreaName WarningType"
    """
    year = current_year()
    # Simplify warning name for signature
    simple = warning_name
    for suffix in (" Warning", " Advisory", " Special Warning"):
        simple = simple.replace(suffix, "")
    return "%s %s %s" % (year, area_name, simple)


def _build_url(area_code):
    """Build a URL for the warning (links to JMA bosai page)."""
    return "https://www.jma.go.jp/bosai/warning/#area_type=class20s&area_code=%s&lang=en" % area_code


def _highest_severity_warning(warnings):
    """From a list of active warning dicts, return the most severe one.

    Returns (code, name, level, severity, human_interest) or None.
    """
    best = None
    for w in warnings:
        code = w.get("code")
        if not code or code in _SKIP_CODES:
            continue
        status = w.get("status", "")
        if status not in _ACTIVE_STATUSES:
            continue
        info = _get_warning_info(code)
        if not info:
            continue
        name, level, severity, hi = info
        if best is None or severity > best[3]:
            best = (code, name, level, severity, hi)
    return best


def scrape_jma():
    """Fetch JMA weather warnings and return story dicts.

    Returns list of story dicts compatible with pipeline.process_story(),
    with pre-populated location, concept, and extraction data.
    JMA stories skip LLM extraction because all structured data is
    pre-built from the API.

    Warnings are aggregated at the class10s (regional) level to avoid
    generating thousands of city-level stories. Only the highest-severity
    warning per region is reported.

    Results are cached for JMA_CACHE_SECONDS.
    """
    # Check cache
    elapsed = time.monotonic() - _cache["fetched_at"]
    if _cache["stories"] and elapsed < JMA_CACHE_SECONDS:
        logger.info("JMA: returning %d cached stories (%.0fs old)",
                     len(_cache["stories"]), elapsed)
        return list(_cache["stories"])

    now = datetime.now(timezone.utc).isoformat()

    # Fetch area names (cached for 24h)
    area_names = _fetch_area_names()

    # Fetch warnings
    raw = _fetch_warnings()
    if not raw:
        logger.warning("JMA: no warning data returned")
        return list(_cache["stories"])  # return stale cache

    if not isinstance(raw, list):
        logger.error("JMA: unexpected response type %s", type(raw).__name__)
        return []

    # Parse warnings at the regional level (areaTypes[0] = class10s)
    stories = []
    seen_ids = set()

    for entry in raw:
        area_types = entry.get("areaTypes", [])
        if not area_types:
            continue

        # Use first areaType (class10s = regional level)
        regions = area_types[0].get("areas", [])

        for region in regions:
            try:
                area_code = region.get("code", "")
                if not area_code:
                    continue

                warnings = region.get("warnings", [])
                if not warnings:
                    continue

                # Find highest-severity active warning in this region
                best = _highest_severity_warning(warnings)
                if not best:
                    continue

                code, warning_name, level, severity, hi_score = best

                # Dedup by area + warning code
                dedup_key = "%s:%s" % (area_code, code)
                if dedup_key in seen_ids:
                    continue
                seen_ids.add(dedup_key)

                # Resolve area name
                area_name = _get_area_name(area_code, area_names)

                # Get centroid
                centroid = _get_centroid(area_code)
                lat = centroid[0] if centroid else None
                lon = centroid[1] if centroid else None

                # Build story fields
                title = _build_title(warning_name, area_name)
                url = _build_url(area_code)
                summary = _build_summary(warning_name, area_name, level)
                event_sig = _build_event_signature(warning_name, area_name)

                # Concepts
                extra_concepts = _get_warning_concepts(code)
                concepts = dedup_list(["weather"] + extra_concepts)

                # Category
                category = "disaster" if severity >= 3 else "weather"

                # Published time from entry report datetime
                published_at = entry.get("reportDatetime")

                location_name = "%s, Japan" % area_name

                story = {
                    "title": title,
                    "url": url,
                    "summary": summary,
                    "source": "JMA",
                    "published_at": published_at,
                    "scraped_at": now,
                    "origin": "jma",
                    "source_type": "inferred",
                    "category": category,
                    "concepts": concepts,
                    "location_name": location_name,
                    "geocode_confidence": 0.7,
                }

                if lat is not None and lon is not None:
                    extraction_locations = attach_location(
                        story, lat, lon, location_name, confidence=0.7)
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
                    primary_action=warning_name.lower(),
                    hi_score=hi_score,
                    locations=extraction_locations,
                    search_keywords=["weather", warning_name.lower(),
                                     area_name, "japan"],
                )

                stories.append(story)
            except Exception as e:
                logger.error("Error processing JMA warning: %s", e)
                continue

    # Sort by severity (most severe first) and cap
    stories.sort(key=lambda s: s["_extraction"]["severity"], reverse=True)
    if len(stories) > JMA_MAX_ALERTS:
        logger.warning(
            "JMA: %d alerts exceed cap of %d, keeping most severe",
            len(stories), JMA_MAX_ALERTS)
        stories = stories[:JMA_MAX_ALERTS]

    # Update cache
    _cache["stories"] = list(stories)
    _cache["fetched_at"] = time.monotonic()

    logger.info("JMA: fetched %d weather warnings", len(stories))
    return stories
