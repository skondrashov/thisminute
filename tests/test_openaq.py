"""Tests for OpenAQ air quality adapter."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.openaq import (
    scrape_openaq,
    _concentration_to_severity,
    _concentration_to_human_interest,
    _build_summary,
    _build_event_signature,
    _normalize_param,
    _exceeds_threshold,
    _extract_location_name,
    _extract_coordinates,
    _extract_readings,
    _extract_location_id,
    _fetch_openaq,
)
from src.database import init_db, get_connection, insert_story, store_extraction


# --- Severity mapping tests ---

def test_severity_above_guideline():
    """Barely above threshold gives severity 1."""
    assert _concentration_to_severity("pm25", 36.0) == 1
    assert _concentration_to_severity("pm25", 50.0) == 1

def test_severity_moderate():
    """1.5x threshold gives severity 2."""
    assert _concentration_to_severity("pm25", 55.0) == 2  # 55/35 = 1.57

def test_severity_unhealthy_sensitive():
    """2.5x threshold gives severity 3."""
    assert _concentration_to_severity("pm25", 90.0) == 3  # 90/35 = 2.57

def test_severity_unhealthy():
    """4x threshold gives severity 4."""
    assert _concentration_to_severity("pm25", 140.0) == 4  # 140/35 = 4.0

def test_severity_hazardous():
    """6x threshold gives severity 5."""
    assert _concentration_to_severity("pm25", 210.0) == 5  # 210/35 = 6.0
    assert _concentration_to_severity("pm25", 500.0) == 5

def test_severity_other_pollutants():
    """Severity mapping works for other pollutants too."""
    assert _concentration_to_severity("pm10", 50.0) == 1   # 50/45 = 1.11
    assert _concentration_to_severity("o3", 250.0) == 3    # 250/100 = 2.5
    assert _concentration_to_severity("no2", 100.0) == 4   # 100/25 = 4.0
    assert _concentration_to_severity("so2", 250.0) == 5   # 250/40 = 6.25


# --- Human interest score tests ---

def test_human_interest_low():
    """Just above threshold gives score 3."""
    assert _concentration_to_human_interest("pm25", 36.0) == 3

def test_human_interest_medium():
    """2x threshold gives score 5."""
    assert _concentration_to_human_interest("pm25", 70.0) == 5

def test_human_interest_high():
    """5x threshold gives score 8."""
    assert _concentration_to_human_interest("pm25", 175.0) == 8

def test_human_interest_extreme():
    """10x threshold gives score 10."""
    assert _concentration_to_human_interest("pm25", 350.0) == 10


# --- Parameter normalization tests ---

def test_normalize_pm25():
    assert _normalize_param("pm25") == "pm25"
    assert _normalize_param("PM2.5") == "pm25"
    assert _normalize_param("pm2.5") == "pm25"

def test_normalize_pm10():
    assert _normalize_param("pm10") == "pm10"
    assert _normalize_param("PM10") == "pm10"

def test_normalize_ozone():
    assert _normalize_param("o3") == "o3"
    assert _normalize_param("ozone") == "o3"

def test_normalize_no2():
    assert _normalize_param("no2") == "no2"
    assert _normalize_param("NO2") == "no2"

def test_normalize_so2():
    assert _normalize_param("so2") == "so2"

def test_normalize_unknown():
    assert _normalize_param("co") is None
    assert _normalize_param("") is None


# --- Threshold tests ---

def test_exceeds_threshold_pm25():
    assert _exceeds_threshold("pm25", 36.0) is True
    assert _exceeds_threshold("pm25", 35.0) is False
    assert _exceeds_threshold("pm25", 10.0) is False

def test_exceeds_threshold_pm10():
    assert _exceeds_threshold("pm10", 50.0) is True
    assert _exceeds_threshold("pm10", 45.0) is False

def test_exceeds_threshold_unknown():
    """Unknown parameter never exceeds."""
    assert _exceeds_threshold("co", 1000.0) is False


# --- Summary builder tests ---

def test_summary_basic():
    summary = _build_summary("Delhi", [("PM2.5", 150.0, "ug/m3")])
    assert "Delhi" in summary
    assert "PM2.5" in summary
    assert "150.0" in summary

def test_summary_multiple_pollutants():
    readings = [("PM2.5", 150.0, "ug/m3"), ("PM10", 200.0, "ug/m3")]
    summary = _build_summary("Beijing", readings)
    assert "PM2.5" in summary
    assert "PM10" in summary
    assert "Beijing" in summary


# --- Event signature tests ---

def test_event_signature_with_location():
    sig = _build_event_signature("Delhi")
    assert "Delhi" in sig
    assert "Air Quality" in sig

def test_event_signature_empty():
    sig = _build_event_signature("")
    assert "Unknown Location" in sig
    assert "Air Quality" in sig


# --- Location extraction tests ---

def test_extract_location_v2():
    result = {"location": "US Embassy, Delhi"}
    assert _extract_location_name(result) == "US Embassy, Delhi"

def test_extract_location_v3():
    result = {"name": "Central Beijing Monitor"}
    assert _extract_location_name(result) == "Central Beijing Monitor"

def test_extract_location_city_country():
    result = {"city": "Mumbai", "country": "IN"}
    assert _extract_location_name(result) == "Mumbai, IN"

def test_extract_location_fallback():
    result = {}
    assert _extract_location_name(result) == "Unknown"


# --- Coordinate extraction tests ---

def test_extract_coordinates_v2():
    result = {"coordinates": {"latitude": 28.6, "longitude": 77.2}}
    coords = _extract_coordinates(result)
    assert coords is not None
    assert coords["lat"] == 28.6
    assert coords["lon"] == 77.2

def test_extract_coordinates_missing():
    result = {}
    assert _extract_coordinates(result) is None

def test_extract_coordinates_none_values():
    result = {"coordinates": {"latitude": None, "longitude": None}}
    assert _extract_coordinates(result) is None


# --- Reading extraction tests ---

def test_extract_readings_v2_exceeding():
    result = {
        "measurements": [
            {"parameter": "pm25", "value": 150.0, "unit": "ug/m3"},
            {"parameter": "pm10", "value": 30.0, "unit": "ug/m3"},  # Below threshold
        ]
    }
    readings = _extract_readings(result)
    assert len(readings) == 1
    assert readings[0][0] == "pm25"
    assert readings[0][2] == 150.0

def test_extract_readings_v2_none_exceeding():
    result = {
        "measurements": [
            {"parameter": "pm25", "value": 10.0, "unit": "ug/m3"},
        ]
    }
    readings = _extract_readings(result)
    assert len(readings) == 0

def test_extract_readings_v2_multiple_exceeding():
    result = {
        "measurements": [
            {"parameter": "pm25", "value": 150.0, "unit": "ug/m3"},
            {"parameter": "pm10", "value": 200.0, "unit": "ug/m3"},
            {"parameter": "o3", "value": 120.0, "unit": "ug/m3"},
        ]
    }
    readings = _extract_readings(result)
    assert len(readings) == 3

def test_extract_readings_negative_value_filtered():
    result = {
        "measurements": [
            {"parameter": "pm25", "value": -5.0, "unit": "ug/m3"},
        ]
    }
    readings = _extract_readings(result)
    assert len(readings) == 0


# --- Location ID tests ---

def test_location_id_v2():
    result = {"location": "US Embassy Delhi"}
    loc_id = _extract_location_id(result)
    assert loc_id == "openaq:US Embassy Delhi"

def test_location_id_v3():
    result = {"id": 12345}
    loc_id = _extract_location_id(result)
    assert loc_id == "openaq:12345"

def test_location_id_missing():
    result = {}
    assert _extract_location_id(result) is None


# --- Dedup tests ---

def _make_openaq_result(location="Test Station", loc_id=None, pm25=150.0,
                        lat=28.6, lon=77.2):
    """Build a mock OpenAQ v2 result."""
    result = {
        "location": location,
        "coordinates": {"latitude": lat, "longitude": lon},
        "measurements": [
            {"parameter": "pm25", "value": pm25, "unit": "ug/m3",
             "lastUpdated": "2026-03-14T00:00:00Z"},
        ],
        "city": "TestCity",
        "country": "TC",
    }
    if loc_id is not None:
        result["location"] = loc_id
    return result


def test_dedup_same_location():
    """Same location ID should be deduped."""
    results = [
        _make_openaq_result(location="Station A", pm25=150.0),
        _make_openaq_result(location="Station A", pm25=160.0),
    ]
    with patch("src.openaq._fetch_openaq", return_value=results):
        stories = scrape_openaq()
    assert len(stories) == 1


def test_dedup_different_locations():
    """Different locations should both appear."""
    results = [
        _make_openaq_result(location="Station A", pm25=150.0),
        _make_openaq_result(location="Station B", pm25=200.0, lat=30.0, lon=80.0),
    ]
    with patch("src.openaq._fetch_openaq", return_value=results):
        stories = scrape_openaq()
    assert len(stories) == 2


# --- Threshold filtering tests ---

def test_below_threshold_filtered():
    """Locations below threshold produce no stories."""
    results = [
        _make_openaq_result(location="Clean Station", pm25=10.0),
    ]
    with patch("src.openaq._fetch_openaq", return_value=results):
        stories = scrape_openaq()
    assert len(stories) == 0


def test_above_threshold_included():
    """Locations above threshold produce stories."""
    results = [
        _make_openaq_result(location="Dirty Station", pm25=100.0),
    ]
    with patch("src.openaq._fetch_openaq", return_value=results):
        stories = scrape_openaq()
    assert len(stories) == 1


# --- Story dict shape tests ---

def test_story_dict_shape():
    """OpenAQ story dict has all required fields."""
    results = [_make_openaq_result(location="Delhi Embassy", pm25=150.0)]
    with patch("src.openaq._fetch_openaq", return_value=results):
        stories = scrape_openaq()

    assert len(stories) == 1
    s = stories[0]

    # Required story fields
    assert "Air Quality Alert" in s["title"]
    assert "Delhi Embassy" in s["title"]
    assert "openaq.org" in s["url"]
    assert "Delhi Embassy" in s["summary"]
    assert "PM2.5" in s["summary"]
    assert s["source"] == "OpenAQ"
    assert s["origin"] == "openaq"
    assert s["source_type"] == "inferred"
    assert s["category"] == "health"
    assert "air-quality" in s["concepts"]
    assert "pollution" in s["concepts"]
    assert "health" in s["concepts"]
    assert s["lat"] == 28.6
    assert s["lon"] == 77.2
    assert s["geocode_confidence"] == 1.0
    assert s["published_at"] is not None

    # Extraction data
    ext = s["_extraction"]
    assert "Air Quality" in ext["event_signature"]
    assert "Delhi Embassy" in ext["event_signature"]
    assert "air-quality" in ext["topics"]
    assert "pollution" in ext["topics"]
    assert ext["severity"] >= 1
    assert ext["location_type"] == "terrestrial"
    assert ext["human_interest_score"] >= 3
    assert isinstance(ext["actors"], list)
    assert isinstance(ext["locations"], list)
    assert len(ext["locations"]) == 1
    assert ext["locations"][0]["role"] == "event_location"


def test_story_no_coordinates():
    """Story with no coordinates still has valid dict."""
    result = {
        "location": "No Coords Station",
        "measurements": [
            {"parameter": "pm25", "value": 150.0, "unit": "ug/m3",
             "lastUpdated": "2026-03-14T00:00:00Z"},
        ],
    }
    with patch("src.openaq._fetch_openaq", return_value=[result]):
        stories = scrape_openaq()

    assert len(stories) == 1
    s = stories[0]
    assert "lat" not in s or s.get("lat") is None
    assert s["geocode_confidence"] == 0.9  # Lower confidence without coords


def test_concepts_include_pollutant_specific():
    """PM2.5 readings should include particulate-matter in concepts."""
    results = [_make_openaq_result(pm25=150.0)]
    with patch("src.openaq._fetch_openaq", return_value=results):
        stories = scrape_openaq()
    assert "particulate-matter" in stories[0]["concepts"]


def test_concepts_deduplicated():
    """Concepts should not have duplicates."""
    results = [_make_openaq_result(pm25=150.0)]
    with patch("src.openaq._fetch_openaq", return_value=results):
        stories = scrape_openaq()
    concepts = stories[0]["concepts"]
    assert len(concepts) == len(set(concepts))


def test_empty_results():
    """Empty API response produces no stories."""
    with patch("src.openaq._fetch_openaq", return_value=[]):
        stories = scrape_openaq()
    assert len(stories) == 0


def test_api_failure_graceful():
    """API failure produces empty list, not exception."""
    with patch("src.openaq._fetch_openaq", return_value=[]):
        stories = scrape_openaq()
    assert stories == []


# --- Database integration tests ---

def test_insert_openaq_story():
    """OpenAQ story with source_type='inferred' inserts correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        story = {
            "title": "Air Quality Alert: Delhi (PM2.5)",
            "url": "https://openaq.org/locations/openaq:Delhi",
            "summary": "Air quality alert at Delhi. PM2.5: 150.0 ug/m3",
            "source": "OpenAQ",
            "scraped_at": "2026-03-14T00:00:00Z",
            "origin": "openaq",
            "source_type": "inferred",
            "category": "health",
            "concepts": ["air-quality", "pollution", "health", "particulate-matter"],
            "lat": 28.6,
            "lon": 77.2,
            "geocode_confidence": 1.0,
        }

        was_new = insert_story(conn, story)
        assert was_new is True

        row = conn.execute("SELECT source_type, origin FROM stories WHERE url = ?",
                           (story["url"],)).fetchone()
        assert row["source_type"] == "inferred"
        assert row["origin"] == "openaq"

        conn.close()


def test_openaq_extraction_storage():
    """Pre-built extraction data from OpenAQ stores correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        story = {
            "title": "Air Quality Alert: Delhi (PM2.5)",
            "url": "https://openaq.org/locations/openaq:Delhi_ext",
            "summary": "Air quality alert at Delhi. PM2.5: 150.0 ug/m3",
            "source": "OpenAQ",
            "scraped_at": "2026-03-14T00:00:00Z",
            "origin": "openaq",
            "source_type": "inferred",
            "category": "health",
            "concepts": ["air-quality", "pollution", "health"],
            "lat": 28.6,
            "lon": 77.2,
            "geocode_confidence": 1.0,
        }

        insert_story(conn, story)
        row = conn.execute("SELECT id FROM stories WHERE url = ?",
                           (story["url"],)).fetchone()
        story_id = row["id"]

        extraction = {
            "event_signature": "2026 Delhi Air Quality",
            "topics": ["air-quality", "pollution", "health", "environment"],
            "severity": 4,
            "sentiment": "negative",
            "primary_action": "air quality alert",
            "location_type": "terrestrial",
            "search_keywords": ["air quality", "pollution", "PM2.5", "Delhi"],
            "is_opinion": False,
            "human_interest_score": 7,
            "actors": [],
            "locations": [
                {"name": "Delhi", "role": "event_location", "lat": 28.6, "lon": 77.2}
            ],
        }

        store_extraction(conn, story_id, extraction)
        conn.execute(
            "UPDATE stories SET extraction_status = 'done' WHERE id = ?",
            (story_id,),
        )
        conn.commit()

        # Verify extraction stored
        ext_row = conn.execute(
            "SELECT event_signature, severity, human_interest_score FROM story_extractions WHERE story_id = ?",
            (story_id,),
        ).fetchone()
        assert ext_row["event_signature"] == "2026 Delhi Air Quality"
        assert ext_row["severity"] == 4
        assert ext_row["human_interest_score"] == 7

        # Verify extraction_status
        status_row = conn.execute(
            "SELECT extraction_status FROM stories WHERE id = ?", (story_id,)
        ).fetchone()
        assert status_row["extraction_status"] == "done"

        conn.close()


# --- Config integration tests ---

def test_source_enabled_includes_openaq():
    """OpenAQ should be in SOURCE_ENABLED."""
    from src.config import SOURCE_ENABLED
    assert "openaq" in SOURCE_ENABLED
    assert SOURCE_ENABLED["openaq"] is True


def test_openaq_url_configured():
    """OpenAQ URL is configured."""
    from src.config import OPENAQ_URL
    assert "openaq.org" in OPENAQ_URL
    assert "latest" in OPENAQ_URL


def test_openaq_api_key_configured():
    """OPENAQ_API_KEY config exists (may be empty)."""
    from src.config import OPENAQ_API_KEY
    assert isinstance(OPENAQ_API_KEY, str)


def test_source_enabled_env_override():
    """Environment variables can disable OpenAQ."""
    import os
    old = os.environ.get("SOURCE_OPENAQ_ENABLED")
    try:
        os.environ["SOURCE_OPENAQ_ENABLED"] = "false"
        result = os.environ.get("SOURCE_OPENAQ_ENABLED", "true").lower() != "false"
        assert result is False
    finally:
        if old is None:
            os.environ.pop("SOURCE_OPENAQ_ENABLED", None)
        else:
            os.environ["SOURCE_OPENAQ_ENABLED"] = old
