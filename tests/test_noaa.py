"""Tests for NOAA weather alerts adapter."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.noaa import (
    scrape_noaa,
    _severity_to_score,
    _severity_to_human_interest,
    _severity_sort_key,
    _get_event_concepts,
    _polygon_centroid,
    _geometry_to_point,
    _build_title,
    _build_summary,
    _build_event_signature,
    _extract_region_name,
    _fetch_alerts,
)


# --- Severity mapping tests ---

@pytest.mark.parametrize("severity,expected", [
    ("Minor", 1),
    ("Moderate", 2),
    ("Severe", 3),
    ("Extreme", 4),
    ("Unknown", 2),
])
def test_severity_score(severity, expected):
    assert _severity_to_score(severity) == expected


# --- Human interest score tests ---

@pytest.mark.parametrize("severity,expected", [
    ("Minor", 2),
    ("Moderate", 4),
    ("Severe", 6),
    ("Extreme", 8),
])
def test_human_interest(severity, expected):
    assert _severity_to_human_interest(severity) == expected


# --- Event concepts tests ---

@pytest.mark.parametrize("event,expected_concept", [
    ("Tornado Warning", "tornado"),
    ("Flash Flood Watch", "flood"),
    ("Hurricane Warning", "hurricane"),
    ("Winter Storm Warning", "winter storm"),
    ("Red Flag Warning", "wildfire"),
    ("Excessive Heat Warning", "heat wave"),
])
def test_concepts(event, expected_concept):
    assert expected_concept in _get_event_concepts(event)


def test_concepts_unknown():
    """Unknown event type returns empty list."""
    assert _get_event_concepts("Special Weather Statement") == []


# --- Centroid calculation tests ---

def test_polygon_centroid_triangle():
    """Centroid of a triangle."""
    coords = [[[0.0, 0.0], [10.0, 0.0], [5.0, 10.0], [0.0, 0.0]]]
    result = _polygon_centroid(coords)
    assert result is not None
    assert abs(result["lon"] - 3.75) < 0.01
    assert abs(result["lat"] - 2.5) < 0.01


def test_polygon_centroid_empty():
    """Empty coordinates return None."""
    assert _polygon_centroid([]) is None
    assert _polygon_centroid([[]]) is None


def test_polygon_centroid_too_few_points():
    """Fewer than 3 points returns None."""
    assert _polygon_centroid([[[0.0, 0.0], [1.0, 1.0]]]) is None


# --- Geometry to point tests ---

def test_geometry_point():
    """Point geometry extracts directly."""
    geom = {"type": "Point", "coordinates": [-95.5, 32.5]}
    result = _geometry_to_point(geom)
    assert result is not None
    assert result["lat"] == 32.5
    assert result["lon"] == -95.5


def test_geometry_polygon():
    """Polygon geometry returns centroid."""
    geom = {
        "type": "Polygon",
        "coordinates": [[[-100.0, 30.0], [-90.0, 30.0], [-90.0, 40.0], [-100.0, 40.0], [-100.0, 30.0]]],
    }
    result = _geometry_to_point(geom)
    assert result is not None
    assert abs(result["lat"] - 34.0) < 0.01
    assert abs(result["lon"] - (-96.0)) < 0.01


def test_geometry_multipolygon():
    """MultiPolygon uses centroid of first polygon."""
    geom = {
        "type": "MultiPolygon",
        "coordinates": [
            [[[-100.0, 30.0], [-90.0, 30.0], [-90.0, 40.0], [-100.0, 40.0], [-100.0, 30.0]]],
            [[[-80.0, 20.0], [-70.0, 20.0], [-70.0, 30.0], [-80.0, 30.0], [-80.0, 20.0]]],
        ],
    }
    result = _geometry_to_point(geom)
    assert result is not None
    assert abs(result["lat"] - 34.0) < 0.01


def test_geometry_none():
    """None geometry returns None."""
    assert _geometry_to_point(None) is None


def test_geometry_no_coordinates():
    """Geometry without coordinates returns None."""
    assert _geometry_to_point({"type": "Polygon"}) is None


# --- Title builder tests ---

def test_title_from_headline():
    props = {"headline": "Tornado Warning issued for Dallas County"}
    assert _build_title(props) == "Tornado Warning issued for Dallas County"


def test_title_from_event_and_area():
    props = {"event": "Flood Warning", "areaDesc": "Harris County, TX"}
    assert _build_title(props) == "Flood Warning - Harris County, TX"


def test_title_long_area_truncated():
    long_area = "A" * 200
    props = {"event": "Winter Storm", "areaDesc": long_area}
    title = _build_title(props)
    assert len(title) < 200


def test_title_event_only():
    props = {"event": "Tornado Watch"}
    assert _build_title(props) == "Tornado Watch"


# --- Summary builder tests ---

def test_summary_from_description():
    props = {"description": "A tornado warning has been issued for the area."}
    summary = _build_summary(props)
    assert "tornado warning" in summary.lower()


def test_summary_truncated():
    long_desc = "X" * 600
    props = {"description": long_desc}
    summary = _build_summary(props)
    assert len(summary) <= 500


def test_summary_fallback():
    props = {"event": "Flood Watch", "areaDesc": "Travis County", "severity": "Moderate"}
    summary = _build_summary(props)
    assert "Flood Watch" in summary
    assert "Travis County" in summary


# --- Event signature tests ---

def test_event_signature_tornado():
    props = {"event": "Tornado Warning", "areaDesc": "Dallas County, TX; Tarrant County, TX"}
    sig = _build_event_signature(props)
    assert "Tornado" in sig
    assert "TX" in sig or "Dallas County" in sig


def test_event_signature_no_area():
    props = {"event": "Winter Storm Watch", "areaDesc": ""}
    sig = _build_event_signature(props)
    assert "Winter Storm" in sig
    assert "US" in sig


def test_event_signature_strips_warning():
    props = {"event": "Flood Warning", "areaDesc": "Harris County, TX"}
    sig = _build_event_signature(props)
    assert "Warning" not in sig
    assert "Flood" in sig


# --- Region name extraction tests ---

def test_region_name_with_area():
    assert _extract_region_name("Dallas County, TX; Tarrant County, TX") == "Dallas County, TX"


def test_region_name_empty():
    assert _extract_region_name("") == "United States"


# --- Dedup tests ---

def _make_noaa_feature(alert_id="https://api.weather.gov/alerts/test1",
                       event="Tornado Warning",
                       headline="Tornado Warning for Dallas",
                       severity="Severe",
                       area="Dallas County, TX"):
    """Build a mock NOAA GeoJSON feature."""
    return {
        "type": "Feature",
        "properties": {
            "id": alert_id,
            "event": event,
            "headline": headline,
            "description": "A tornado warning has been issued.",
            "severity": severity,
            "areaDesc": area,
            "onset": "2026-03-14T00:00:00Z",
            "sent": "2026-03-14T00:00:00Z",
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[-97.0, 32.0], [-96.0, 32.0], [-96.0, 33.0], [-97.0, 33.0], [-97.0, 32.0]]],
        },
    }


def test_dedup_same_id():
    """Same alert ID should be deduped."""
    features = [
        _make_noaa_feature(alert_id="https://api.weather.gov/alerts/dup1"),
        _make_noaa_feature(alert_id="https://api.weather.gov/alerts/dup1"),
    ]
    with patch("src.noaa._fetch_alerts", return_value=features):
        stories = scrape_noaa()
    assert len(stories) == 1


# --- Story dict shape tests ---

def test_story_dict_shape():
    """NOAA story dict has all required fields."""
    features = [_make_noaa_feature()]
    with patch("src.noaa._fetch_alerts", return_value=features):
        stories = scrape_noaa()

    assert len(stories) == 1
    s = stories[0]

    # Required story fields
    assert s["title"] == "Tornado Warning for Dallas"
    assert s["url"] == "https://api.weather.gov/alerts/test1"
    assert "tornado" in s["summary"].lower()
    assert s["source"] == "NOAA Weather"
    assert s["origin"] == "noaa"
    assert s["source_type"] == "inferred"
    assert s["category"] in ("disaster", "weather")
    assert "weather" in s["concepts"]
    assert "disaster" in s["concepts"]
    assert s["lat"] is not None
    assert s["lon"] is not None
    assert s["geocode_confidence"] == 1.0
    assert s["published_at"] is not None

    # Extraction data
    ext = s["_extraction"]
    assert "Tornado" in ext["event_signature"]
    assert "weather" in ext["topics"]
    assert ext["severity"] == 3  # Severe
    assert ext["location_type"] == "terrestrial"
    assert ext["human_interest_score"] == 6  # Severe
    assert isinstance(ext["actors"], list)
    assert isinstance(ext["locations"], list)
    assert len(ext["locations"]) == 1
    assert ext["locations"][0]["role"] == "event_location"


def test_story_dict_no_geometry():
    """NOAA story with no geometry still has a valid dict."""
    feature = _make_noaa_feature()
    feature["geometry"] = None
    with patch("src.noaa._fetch_alerts", return_value=[feature]):
        stories = scrape_noaa()

    assert len(stories) == 1
    s = stories[0]
    assert "lat" not in s or s.get("lat") is None
    assert s["geocode_confidence"] == 0.8  # Lower confidence without geometry


def test_category_disaster_for_severe():
    """Severe/Extreme alerts get category 'disaster'."""
    features = [_make_noaa_feature(severity="Severe")]
    with patch("src.noaa._fetch_alerts", return_value=features):
        stories = scrape_noaa()
    assert stories[0]["category"] == "disaster"


def test_category_weather_for_minor():
    """Minor/Moderate alerts get category 'weather'."""
    features = [_make_noaa_feature(severity="Minor")]
    with patch("src.noaa._fetch_alerts", return_value=features):
        stories = scrape_noaa()
    assert stories[0]["category"] == "weather"


# --- NOAA_MAX_ALERTS cap tests ---

def test_max_alerts_caps_volume():
    """Alerts exceeding NOAA_MAX_ALERTS should be capped."""
    features = [
        _make_noaa_feature(
            alert_id="https://api.weather.gov/alerts/a%d" % i,
            headline="Alert %d" % i,
            severity="Minor",
        )
        for i in range(200)
    ]
    with patch("src.noaa._fetch_alerts", return_value=features):
        with patch("src.noaa.NOAA_MAX_ALERTS", 50):
            stories = scrape_noaa()
    assert len(stories) == 50


def test_max_alerts_prioritizes_severe():
    """When capped, severe/extreme alerts should be kept over minor ones."""
    features = []
    # 3 Extreme alerts
    for i in range(3):
        features.append(_make_noaa_feature(
            alert_id="https://api.weather.gov/alerts/ext%d" % i,
            headline="Extreme Alert %d" % i,
            severity="Extreme",
            event="Tornado Warning",
        ))
    # 3 Minor alerts
    for i in range(3):
        features.append(_make_noaa_feature(
            alert_id="https://api.weather.gov/alerts/min%d" % i,
            headline="Minor Alert %d" % i,
            severity="Minor",
            event="Frost Advisory",
        ))

    with patch("src.noaa._fetch_alerts", return_value=features):
        with patch("src.noaa.NOAA_MAX_ALERTS", 4):
            stories = scrape_noaa()

    assert len(stories) == 4
    # All 3 extreme alerts should be present
    extreme_count = sum(1 for s in stories if s["_extraction"]["severity"] == 4)
    assert extreme_count == 3
    # Only 1 minor alert kept
    minor_count = sum(1 for s in stories if s["_extraction"]["severity"] == 1)
    assert minor_count == 1


def test_max_alerts_severity_sort_order():
    """Alerts should be sorted: Extreme > Severe > Moderate > Minor."""
    from src.noaa import _severity_sort_key
    extreme = _make_noaa_feature(severity="Extreme")
    severe = _make_noaa_feature(severity="Severe")
    moderate = _make_noaa_feature(severity="Moderate")
    minor = _make_noaa_feature(severity="Minor")

    assert _severity_sort_key(extreme) < _severity_sort_key(severe)
    assert _severity_sort_key(severe) < _severity_sort_key(moderate)
    assert _severity_sort_key(moderate) < _severity_sort_key(minor)
