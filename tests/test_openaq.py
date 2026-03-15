"""Tests for OpenAQ air quality adapter."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

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


# --- Severity mapping tests ---

@pytest.mark.parametrize("value,expected", [
    (36.0, 1),
    (55.0, 2),
    (90.0, 3),
    (140.0, 4),
    (210.0, 5),
])
def test_severity(value, expected):
    assert _concentration_to_severity("pm25", value) == expected


def test_severity_other_pollutants():
    """Severity mapping works for other pollutants too."""
    assert _concentration_to_severity("pm10", 50.0) == 1
    assert _concentration_to_severity("o3", 250.0) == 3
    assert _concentration_to_severity("no2", 100.0) == 4
    assert _concentration_to_severity("so2", 250.0) == 5


# --- Human interest score tests ---

@pytest.mark.parametrize("value,expected", [
    (36.0, 3),
    (70.0, 5),
    (175.0, 8),
    (350.0, 10),
])
def test_human_interest(value, expected):
    assert _concentration_to_human_interest("pm25", value) == expected


# --- Parameter normalization tests ---

@pytest.mark.parametrize("raw,expected", [
    ("pm25", "pm25"),
    ("PM2.5", "pm25"),
    ("pm2.5", "pm25"),
    ("pm10", "pm10"),
    ("PM10", "pm10"),
    ("o3", "o3"),
    ("ozone", "o3"),
    ("no2", "no2"),
    ("NO2", "no2"),
    ("so2", "so2"),
])
def test_normalize(raw, expected):
    assert _normalize_param(raw) == expected


def test_normalize_unknown():
    assert _normalize_param("co") is None
    assert _normalize_param("") is None


# --- Threshold tests ---

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


# --- Threshold filtering tests ---

def test_below_threshold_filtered():
    """Locations below threshold produce no stories."""
    results = [
        _make_openaq_result(location="Clean Station", pm25=10.0),
    ]
    with patch("src.openaq._fetch_openaq", return_value=results):
        stories = scrape_openaq()
    assert len(stories) == 0


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


def test_empty_results():
    """Empty API response produces no stories."""
    with patch("src.openaq._fetch_openaq", return_value=[]):
        stories = scrape_openaq()
    assert len(stories) == 0
