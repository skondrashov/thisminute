"""NASA FIRMS (Fire Information for Resource Management System) integration.

Fetches active fire detections worldwide from NASA's FIRMS VIIRS satellite data.
Individual fire detections (~375m pixels) are clustered into fire events by
rounding lat/lon to 0.5-degree grid cells. This reduces thousands of raw
detections down to ~20-100 fire event stories per cycle.

Requires FIRMS_API_KEY environment variable (free from NASA Earthdata).
Gracefully skips if no API key is set.
"""

import csv
import io
import logging
import math
import urllib.request
from datetime import datetime, timezone

from .config import REQUEST_TIMEOUT, FIRMS_API_KEY, FIRMS_URL, FIRMS_MAX_ROWS, FIRMS_MAX_BYTES
from .country_centroids import CENTROIDS
from .source_utils import build_extraction, attach_location, current_year

logger = logging.getLogger(__name__)

# Grid cell size for clustering (degrees). 0.5 deg ~ 55 km at equator.
_GRID_RESOLUTION = 0.5


def _cluster_severity(count):
    """Map number of fire detections in a cluster to severity (1-5).

    1-2 detections: severity 1 (small fire)
    3-10: severity 2
    11-50: severity 3
    51-200: severity 4
    200+: severity 5 (major wildfire)
    """
    if count > 200:
        return 5
    elif count > 50:
        return 4
    elif count > 10:
        return 3
    elif count > 2:
        return 2
    else:
        return 1


def _cluster_human_interest(count):
    """Map cluster size to human interest score (1-10)."""
    if count > 500:
        return 10
    elif count > 200:
        return 9
    elif count > 100:
        return 8
    elif count > 50:
        return 7
    elif count > 20:
        return 6
    elif count > 10:
        return 5
    elif count > 5:
        return 4
    elif count > 2:
        return 3
    else:
        return 2


def _grid_key(lat, lon):
    """Round lat/lon to grid cell key for clustering.

    Returns (grid_lat, grid_lon) as floats rounded to _GRID_RESOLUTION.
    """
    grid_lat = round(math.floor(lat / _GRID_RESOLUTION) * _GRID_RESOLUTION, 1)
    grid_lon = round(math.floor(lon / _GRID_RESOLUTION) * _GRID_RESOLUTION, 1)
    return (grid_lat, grid_lon)


def _nearest_country(lat, lon):
    """Find the nearest country to a lat/lon from centroids.

    Returns the country name (title-cased) or None if no country within
    a reasonable distance (~30 degrees).
    """
    best_name = None
    best_dist = 900.0  # impossibly large
    for name, (clat, clon) in CENTROIDS.items():
        # Skip alternate names (short keys that duplicate longer entries)
        if len(name) <= 3:
            continue
        dist = math.sqrt((lat - clat) ** 2 + (lon - clon) ** 2)
        if dist < best_dist:
            best_dist = dist
            best_name = name
    if best_dist < 30.0 and best_name:
        return best_name.title()
    return None


def _parse_confidence(value):
    """Parse FIRMS confidence value. Returns numeric confidence or None.

    VIIRS confidence can be 'low', 'nominal', 'high' or numeric 0-100.
    """
    if not value:
        return None
    v = value.strip().lower()
    if v == "high":
        return 95
    elif v == "nominal":
        return 80
    elif v == "low":
        return 30
    else:
        try:
            return int(v)
        except (ValueError, TypeError):
            return None


def _fetch_firms_csv():
    """Fetch FIRMS CSV data. Returns raw text or empty string on error.

    Enforces FIRMS_MAX_BYTES size cap to prevent unbounded memory usage
    on the 1 GB VM. If the response exceeds the limit, it is truncated
    to the last complete line within the limit and a warning is logged.
    """
    if not FIRMS_API_KEY:
        return ""
    url = FIRMS_URL.format(MAP_KEY=FIRMS_API_KEY)
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "thisminute-news-map/1.0"},
        )
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            raw = resp.read(FIRMS_MAX_BYTES + 1)
            if len(raw) > FIRMS_MAX_BYTES:
                logger.warning(
                    "FIRMS CSV response exceeded %d bytes, truncating",
                    FIRMS_MAX_BYTES)
                raw = raw[:FIRMS_MAX_BYTES]
                # Trim to last complete line
                last_nl = raw.rfind(b"\n")
                if last_nl > 0:
                    raw = raw[:last_nl]
            return raw.decode("utf-8")
    except Exception as e:
        logger.error("Failed to fetch FIRMS data: %s", e)
        return ""


def _parse_detections(csv_text):
    """Parse FIRMS CSV text into list of detection dicts.

    Filters by confidence >= 80. Stops after FIRMS_MAX_ROWS high-confidence
    detections to bound memory usage. Returns list of dicts with keys:
    lat, lon, confidence, frp, acq_date, acq_time, brightness.
    """
    if not csv_text or not csv_text.strip():
        return []

    detections = []
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        try:
            conf = _parse_confidence(row.get("confidence", ""))
            if conf is None or conf < 80:
                continue

            lat = float(row.get("latitude", 0))
            lon = float(row.get("longitude", 0))
            if lat == 0 and lon == 0:
                continue

            frp = 0.0
            try:
                frp = float(row.get("frp", 0))
            except (ValueError, TypeError):
                pass

            detections.append({
                "lat": lat,
                "lon": lon,
                "confidence": conf,
                "frp": frp,
                "acq_date": row.get("acq_date", ""),
                "acq_time": row.get("acq_time", ""),
                "brightness": row.get("brightness", ""),
            })

            if len(detections) >= FIRMS_MAX_ROWS:
                logger.warning(
                    "FIRMS: hit %d row cap, stopping parse early",
                    FIRMS_MAX_ROWS)
                break
        except (ValueError, TypeError, KeyError) as e:
            logger.debug("Skipping FIRMS row: %s", e)
            continue

    return detections


def _cluster_detections(detections):
    """Cluster fire detections by grid cell.

    Returns dict of grid_key -> {detections: list, count: int,
    avg_lat: float, avg_lon: float, max_frp: float, date: str}.
    """
    clusters = {}
    for det in detections:
        key = _grid_key(det["lat"], det["lon"])
        if key not in clusters:
            clusters[key] = {
                "detections": [],
                "sum_lat": 0.0,
                "sum_lon": 0.0,
                "max_frp": 0.0,
                "date": det.get("acq_date", ""),
            }
        c = clusters[key]
        c["detections"].append(det)
        c["sum_lat"] += det["lat"]
        c["sum_lon"] += det["lon"]
        if det["frp"] > c["max_frp"]:
            c["max_frp"] = det["frp"]
        # Keep latest date
        if det.get("acq_date", "") > c["date"]:
            c["date"] = det["acq_date"]

    # Compute averages
    result = {}
    for key, c in clusters.items():
        count = len(c["detections"])
        result[key] = {
            "count": count,
            "avg_lat": c["sum_lat"] / count,
            "avg_lon": c["sum_lon"] / count,
            "max_frp": c["max_frp"],
            "date": c["date"],
        }

    return result


def _build_event_signature(lat, lon, country):
    """Build event signature for a fire cluster."""
    year = current_year()
    if country:
        return "%s %s Wildfire" % (year, country)
    # Fall back to grid coordinates
    lat_dir = "N" if lat >= 0 else "S"
    lon_dir = "E" if lon >= 0 else "W"
    return "%s Fire %s%d%s%d" % (year, lat_dir, abs(int(lat)), lon_dir, abs(int(lon)))


def _build_title(count, country, lat, lon):
    """Build a human-readable title for a fire cluster."""
    if country:
        if count > 50:
            return "Major wildfire activity in %s" % country
        elif count > 10:
            return "Active fires in %s" % country
        else:
            return "Fire detected in %s" % country
    lat_dir = "N" if lat >= 0 else "S"
    lon_dir = "E" if lon >= 0 else "W"
    return "Fire detected at %s%.1f %s%.1f" % (lat_dir, abs(lat), lon_dir, abs(lon))


def _build_summary(count, max_frp, country, date):
    """Build a descriptive summary for a fire cluster."""
    parts = []
    parts.append("%d fire detection%s from VIIRS satellite" % (count, "s" if count != 1 else ""))
    if country:
        parts.append("Location: %s" % country)
    if max_frp > 0:
        parts.append("Max fire radiative power: %.1f MW" % max_frp)
    if date:
        parts.append("Date: %s" % date)
    return ". ".join(parts) + "."


def scrape_firms():
    """Fetch FIRMS fire detections and return clustered story dicts.

    Returns list of story dicts compatible with pipeline.process_story(),
    with pre-populated location, concept, and extraction data.
    Gracefully returns empty list if FIRMS_API_KEY is not set.
    """
    if not FIRMS_API_KEY:
        logger.info("FIRMS: skipping (no FIRMS_API_KEY set)")
        return []

    now = datetime.now(timezone.utc).isoformat()

    # Fetch and parse CSV
    csv_text = _fetch_firms_csv()
    detections = _parse_detections(csv_text)

    if not detections:
        logger.info("FIRMS: no high-confidence detections found")
        return []

    # Cluster nearby detections
    clusters = _cluster_detections(detections)

    stories = []
    for grid_key, cluster in clusters.items():
        try:
            lat = cluster["avg_lat"]
            lon = cluster["avg_lon"]
            count = cluster["count"]
            max_frp = cluster["max_frp"]
            date = cluster["date"]

            country = _nearest_country(lat, lon)
            title = _build_title(count, country, lat, lon)
            summary = _build_summary(count, max_frp, country, date)
            event_sig = _build_event_signature(lat, lon, country)
            severity = _cluster_severity(count)
            hi_score = _cluster_human_interest(count)

            # Dedup URL uses grid cell coordinates per day
            dedup_url = "https://firms.modaps.eosdis.nasa.gov/fire/%s/%.1f/%.1f" % (
                date or "unknown", grid_key[0], grid_key[1])

            location_name = country or ("%.1f, %.1f" % (lat, lon))

            story = {
                "title": title,
                "url": dedup_url,
                "summary": summary,
                "source": "NASA FIRMS",
                "published_at": now,
                "scraped_at": now,
                "origin": "firms",
                "source_type": "inferred",
                "category": "disaster",
                "concepts": ["wildfire", "fire", "environment", "climate"],
                "location_name": location_name,
                "geocode_confidence": 0.8,
            }

            extraction_locations = attach_location(
                story, lat, lon, location_name)

            story["_extraction"] = build_extraction(
                event_sig=event_sig,
                topics=["wildfire", "fire", "environment"],
                severity=severity,
                sentiment="negative",
                primary_action="wildfire",
                hi_score=hi_score,
                locations=extraction_locations,
                search_keywords=["wildfire", "fire", "FIRMS", location_name],
            )

            stories.append(story)
        except Exception as e:
            logger.error("Error processing FIRMS cluster: %s", e)
            continue

    logger.info("FIRMS: %d detections clustered into %d fire events",
                len(detections), len(stories))
    return stories
