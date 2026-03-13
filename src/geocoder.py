"""Geocoding with Nominatim, SQLite cache, and rate limiting."""

import logging
import math
import time
from typing import Optional

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from .config import NOMINATIM_USER_AGENT, GEOCODE_MIN_DELAY
from .database import get_connection, get_cached_geocode, cache_geocode

logger = logging.getLogger(__name__)

# Module-level rate limiter
_last_request_time = 0.0

# Lazy-load geocoder
_geocoder = None

# Vague region names that Nominatim can't geocode well
_SKIP_LOCATIONS = {
    "Middle East", "Southeast Asia", "Central Asia", "East Africa",
    "West Africa", "North Africa", "South America", "Central America",
    "Eastern Europe", "Western Europe", "Pacific Islands",
    "European Union", "African Union", "Arab League",
}

# Hardcoded coordinates for landmarks/regions Nominatim gets wrong
_HARDCODED = {
    # Contested territories — Nominatim often returns wrong results
    "West Bank": {"lat": 31.9474, "lon": 35.3026, "display_name": "West Bank, Palestinian Territories"},
    "Gaza": {"lat": 31.3547, "lon": 34.3088, "display_name": "Gaza, Palestinian Territories"},
    "Gaza Strip": {"lat": 31.3547, "lon": 34.3088, "display_name": "Gaza Strip, Palestinian Territories"},
    "Golan Heights": {"lat": 33.0057, "lon": 35.7542, "display_name": "Golan Heights"},
    "Crimea": {"lat": 44.9521, "lon": 34.1024, "display_name": "Crimea, Ukraine"},
    "Kashmir": {"lat": 34.0837, "lon": 74.7973, "display_name": "Kashmir"},
    "Taiwan": {"lat": 23.6978, "lon": 120.9605, "display_name": "Taiwan"},
    "Hong Kong": {"lat": 22.3193, "lon": 114.1694, "display_name": "Hong Kong"},
    "Macau": {"lat": 22.1987, "lon": 113.5439, "display_name": "Macau"},
    "Kosovo": {"lat": 42.6026, "lon": 20.9030, "display_name": "Kosovo"},
    "Donbas": {"lat": 48.0159, "lon": 37.8028, "display_name": "Donbas, Ukraine"},
    "Donetsk": {"lat": 48.0159, "lon": 37.8028, "display_name": "Donetsk, Ukraine"},
    "Luhansk": {"lat": 48.5740, "lon": 39.3078, "display_name": "Luhansk, Ukraine"},
    "Kherson": {"lat": 46.6354, "lon": 32.6169, "display_name": "Kherson, Ukraine"},
    "Zaporizhzhia": {"lat": 47.8388, "lon": 35.1396, "display_name": "Zaporizhzhia, Ukraine"},
    "Transnistria": {"lat": 46.8480, "lon": 29.6287, "display_name": "Transnistria, Moldova"},
    "Nagorno-Karabakh": {"lat": 39.8266, "lon": 46.7636, "display_name": "Nagorno-Karabakh"},
    "South Ossetia": {"lat": 42.3440, "lon": 43.9654, "display_name": "South Ossetia, Georgia"},
    "Abkhazia": {"lat": 43.0016, "lon": 41.0234, "display_name": "Abkhazia, Georgia"},
    "Somaliland": {"lat": 9.5600, "lon": 44.0650, "display_name": "Somaliland"},
    "Western Sahara": {"lat": 24.2155, "lon": -12.8858, "display_name": "Western Sahara"},
    "Xinjiang": {"lat": 41.1129, "lon": 85.2401, "display_name": "Xinjiang, China"},
    "Tibet": {"lat": 29.6465, "lon": 91.1145, "display_name": "Tibet, China"},
    # Landmarks and well-known places
    "Pentagon": {"lat": 38.8720, "lon": -77.0563, "display_name": "The Pentagon, Virginia, US"},
    "Capitol Hill": {"lat": 38.8899, "lon": -77.0091, "display_name": "Capitol Hill, Washington DC, US"},
    "White House": {"lat": 38.8977, "lon": -77.0365, "display_name": "The White House, Washington DC, US"},
    "Downing Street": {"lat": 51.5034, "lon": -0.1276, "display_name": "Downing Street, London, UK"},
    "Kremlin": {"lat": 55.7520, "lon": 37.6175, "display_name": "The Kremlin, Moscow, Russia"},
    "Wall Street": {"lat": 40.7069, "lon": -74.0089, "display_name": "Wall Street, New York, US"},
    "Silicon Valley": {"lat": 37.3875, "lon": -122.0575, "display_name": "Silicon Valley, California, US"},
    "Vatican": {"lat": 41.9029, "lon": 12.4534, "display_name": "Vatican City"},
    "Hollywood": {"lat": 34.0928, "lon": -118.3287, "display_name": "Hollywood, Los Angeles, US"},
    "Sahel": {"lat": 14.0, "lon": 0.0, "display_name": "Sahel Region, Africa"},
    "Arctic": {"lat": 71.0, "lon": 0.0, "display_name": "Arctic"},
    "Antarctic": {"lat": -75.0, "lon": 0.0, "display_name": "Antarctica"},
    "Guantanamo": {"lat": 20.0, "lon": -75.1, "display_name": "Guantanamo Bay, Cuba"},
    "Guantanamo Bay": {"lat": 20.0, "lon": -75.1, "display_name": "Guantanamo Bay, Cuba"},
    "Chernobyl": {"lat": 51.2763, "lon": 30.2219, "display_name": "Chernobyl, Ukraine"},
    "Fukushima": {"lat": 37.7608, "lon": 140.4748, "display_name": "Fukushima, Japan"},
    "Broadway": {"lat": 40.7590, "lon": -73.9845, "display_name": "Broadway, New York, US"},
    "Mar-a-Lago": {"lat": 26.6775, "lon": -80.0369, "display_name": "Mar-a-Lago, Palm Beach, US"},
    "Camp David": {"lat": 39.6481, "lon": -77.4650, "display_name": "Camp David, Maryland, US"},
    "Davos": {"lat": 46.8027, "lon": 9.8360, "display_name": "Davos, Switzerland"},
    "Strait of Hormuz": {"lat": 26.5667, "lon": 56.2500, "display_name": "Strait of Hormuz"},
    "Suez Canal": {"lat": 30.4580, "lon": 32.3498, "display_name": "Suez Canal, Egypt"},
    "Strait of Malacca": {"lat": 2.5000, "lon": 101.0000, "display_name": "Strait of Malacca"},
    "Marjayoun": {"lat": 33.3608, "lon": 35.5917, "display_name": "Marjayoun, Lebanon"},
    # US political / commonly misgeocoded
    "Washington D.C.": {"lat": 38.9072, "lon": -77.0369, "display_name": "Washington, D.C., US"},
    "Washington, D.C.": {"lat": 38.9072, "lon": -77.0369, "display_name": "Washington, D.C., US"},
    "Washington DC": {"lat": 38.9072, "lon": -77.0369, "display_name": "Washington, D.C., US"},
    "Beverly Hills": {"lat": 34.0736, "lon": -118.4004, "display_name": "Beverly Hills, California, US"},
    "Beverly Hills, California": {"lat": 34.0736, "lon": -118.4004, "display_name": "Beverly Hills, California, US"},
    "Rafah": {"lat": 31.2973, "lon": 34.2478, "display_name": "Rafah, Palestinian Territories"},
    "Khan Younis": {"lat": 31.3462, "lon": 34.3032, "display_name": "Khan Younis, Palestinian Territories"},
    "Jenin": {"lat": 32.4607, "lon": 35.3027, "display_name": "Jenin, Palestinian Territories"},
    "Nablus": {"lat": 32.2211, "lon": 35.2544, "display_name": "Nablus, Palestinian Territories"},
    "Ramallah": {"lat": 31.9038, "lon": 35.2034, "display_name": "Ramallah, Palestinian Territories"},
}


def bbox_to_radius_km(south: float, north: float, west: float, east: float) -> float:
    """Convert a bounding box to an approximate radius in km."""
    lat_km = (north - south) * 111.0
    lon_km = (east - west) * 111.0 * math.cos(math.radians((north + south) / 2.0))
    return max(lat_km, lon_km) / 2.0


def _get_geocoder() -> Nominatim:
    """Lazy-load the Nominatim geocoder."""
    global _geocoder
    if _geocoder is None:
        _geocoder = Nominatim(user_agent=NOMINATIM_USER_AGENT, timeout=10)
    return _geocoder


def _rate_limit():
    """Enforce minimum delay between Nominatim requests."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < GEOCODE_MIN_DELAY:
        time.sleep(GEOCODE_MIN_DELAY - elapsed)
    _last_request_time = time.time()


def geocode_location(location_name: str) -> Optional[dict]:
    """Geocode a location name, using cache first.

    Returns dict with lat, lon, display_name, importance or None if not found.
    Caches null results to avoid re-querying failures.
    """
    if not location_name or len(location_name.strip()) < 2:
        return None

    location_name = location_name.strip()

    if location_name in _SKIP_LOCATIONS:
        return None

    # Check hardcoded locations first
    if location_name in _HARDCODED:
        return _HARDCODED[location_name]

    # Check cache first
    conn = get_connection()
    cached = get_cached_geocode(conn, location_name)
    if cached is not None:
        conn.close()
        if cached["lat"] is None:
            return None  # Previously failed lookup
        return {
            "lat": cached["lat"],
            "lon": cached["lon"],
            "display_name": cached["display_name"],
            "importance": cached["importance"],
            "bbox_south": cached.get("bbox_south"),
            "bbox_north": cached.get("bbox_north"),
            "bbox_west": cached.get("bbox_west"),
            "bbox_east": cached.get("bbox_east"),
        }

    # Not cached — query Nominatim
    _rate_limit()
    geocoder = _get_geocoder()

    try:
        result = geocoder.geocode(
            location_name,
            exactly_one=True,
            language="en",
            addressdetails=False,
        )
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        logger.warning("Geocode error for '%s': %s", location_name, e)
        conn.close()
        return None
    except Exception as e:
        logger.error("Unexpected geocode error for '%s': %s", location_name, e)
        conn.close()
        return None

    if result is None:
        # Cache the null result so we don't re-query
        cache_geocode(conn, location_name, None, None)
        logger.debug("No geocode result for '%s'", location_name)
        conn.close()
        return None

    geo = {
        "lat": result.latitude,
        "lon": result.longitude,
        "display_name": result.address,
        "importance": None,
        "bbox_south": None,
        "bbox_north": None,
        "bbox_west": None,
        "bbox_east": None,
    }

    # Extract importance and bounding box from raw result
    if hasattr(result, "raw") and isinstance(result.raw, dict):
        geo["importance"] = result.raw.get("importance")
        # Nominatim returns boundingbox as [south, north, west, east] strings
        bb = result.raw.get("boundingbox")
        if bb and len(bb) == 4:
            try:
                geo["bbox_south"] = float(bb[0])
                geo["bbox_north"] = float(bb[1])
                geo["bbox_west"] = float(bb[2])
                geo["bbox_east"] = float(bb[3])
            except (ValueError, TypeError):
                pass

    # Cache the result
    cache_geocode(
        conn,
        location_name,
        geo["lat"],
        geo["lon"],
        geo["display_name"],
        geo["importance"],
        geo["bbox_south"],
        geo["bbox_north"],
        geo["bbox_west"],
        geo["bbox_east"],
    )
    conn.close()

    logger.info("Geocoded '%s' -> (%.4f, %.4f)", location_name, geo["lat"], geo["lon"])
    return geo
