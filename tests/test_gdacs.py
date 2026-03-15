"""Tests for GDACS (Global Disaster Alert and Coordination System) adapter."""

import json
from unittest.mock import patch, MagicMock

import pytest

from src.gdacs import (
    scrape_gdacs,
    _parse_event_type,
    _get_concepts,
    _build_event_signature,
    _build_summary,
    _fetch_geojson,
    _fetch_rss,
    _process_geojson_features,
    _process_rss_items,
)


def _make_gdacs_geojson_feature(url="https://www.gdacs.org/report.aspx?eventid=1001",
                                 title="M 6.2 Earthquake - Turkey",
                                 event_type="EQ", alert_level="Orange",
                                 lat=38.0, lon=37.5):
    """Build a mock GDACS GeoJSON feature."""
    return {
        "type": "Feature",
        "properties": {
            "name": title,
            "url": url,
            "eventtype": event_type,
            "alertlevel": alert_level,
            "description": "Earthquake of magnitude 6.2 near Turkey.",
            "population": {"value": 500000},
            "fromdate": "2026-03-14T00:00:00Z",
        },
        "geometry": {
            "type": "Point",
            "coordinates": [lon, lat],
        },
    }


def _make_gdacs_rss_item(url="https://www.gdacs.org/report.aspx?eventid=2001",
                          title="Tropical Cyclone - Mozambique",
                          event_type="TC", alert_level="Red",
                          lat=-15.0, lon=40.0):
    """Build a mock GDACS RSS item dict."""
    return {
        "title": title,
        "url": url,
        "description": "Category 4 tropical cyclone approaching Mozambique.",
        "pubDate": "2026-03-14T00:00:00Z",
        "eventtype": event_type,
        "alertlevel": alert_level,
        "population": "1000000",
        "lat": lat,
        "lon": lon,
    }


# --- Event type parsing tests ---

@pytest.mark.parametrize("code,expected", [
    ("EQ", "earthquake"),
    ("FL", "flood"),
    ("TC", "cyclone"),
    ("DR", "drought"),
    ("VO", "volcano"),
    ("WF", "wildfire"),
    ("something", "something"),
    ("", ""),
])
def test_parse_event_type(code, expected):
    assert _parse_event_type(code) == expected


# --- Concept mapping tests ---

@pytest.mark.parametrize("code,expected_concept", [
    ("EQ", "earthquake"),
    ("FL", "flood"),
    ("TC", "cyclone"),
    ("DR", "drought"),
])
def test_concepts_parameterized(code, expected_concept):
    concepts = _get_concepts(code)
    assert expected_concept in concepts


def test_concepts_cyclone_includes_hurricane():
    concepts = _get_concepts("TC")
    assert "hurricane" in concepts


# --- Severity mapping tests ---

@pytest.mark.parametrize("alert_level,expected_min", [
    ("Green", 2),
    ("Orange", 3),
    ("Red", 4),
])
def test_severity_parameterized(alert_level, expected_min):
    features = [_make_gdacs_geojson_feature(alert_level=alert_level)]
    stories = _process_geojson_features(features)
    assert stories[0]["_extraction"]["severity"] >= expected_min


def test_severity_green_exact():
    features = [_make_gdacs_geojson_feature(alert_level="Green")]
    stories = _process_geojson_features(features)
    assert stories[0]["_extraction"]["severity"] == 2


# --- Summary builder tests ---

def test_build_summary_with_all():
    summary = _build_summary("Earthquake", "Strong earthquake hit region.", "Orange", "50000")
    assert "earthquake" in summary.lower()
    assert "Orange" in summary
    assert "50000" in summary

def test_build_summary_no_description():
    summary = _build_summary("Flood Warning", "", "Green", "")
    assert "Flood Warning" in summary

def test_build_summary_empty():
    summary = _build_summary("", "", "", "")
    assert len(summary) > 0


# --- Event signature tests ---

def test_event_signature_with_title():
    sig = _build_event_signature("Turkey Earthquake", "EQ")
    assert "Turkey Earthquake" in sig

def test_event_signature_no_title():
    sig = _build_event_signature("", "FL")
    assert "Flood" in sig


# --- Dedup tests ---

def test_geojson_dedup_same_url():
    features = [
        _make_gdacs_geojson_feature(url="https://gdacs.org/dup1"),
        _make_gdacs_geojson_feature(url="https://gdacs.org/dup1"),
    ]
    stories = _process_geojson_features(features)
    assert len(stories) == 1


def test_rss_dedup_same_url():
    items = [
        _make_gdacs_rss_item(url="https://gdacs.org/rss_dup1"),
        _make_gdacs_rss_item(url="https://gdacs.org/rss_dup1"),
    ]
    stories = _process_rss_items(items)
    assert len(stories) == 1


# --- Story dict shape tests (GeoJSON) ---

def test_geojson_story_dict_shape():
    features = [_make_gdacs_geojson_feature()]
    stories = _process_geojson_features(features)

    assert len(stories) == 1
    s = stories[0]

    assert s["title"] == "M 6.2 Earthquake - Turkey"
    assert s["url"] == "https://www.gdacs.org/report.aspx?eventid=1001"
    assert s["source"] == "GDACS"
    assert s["origin"] == "gdacs"
    assert s["source_type"] == "inferred"
    assert s["category"] == "disaster"
    assert "earthquake" in s["concepts"]
    assert s["lat"] == 38.0
    assert s["lon"] == 37.5
    assert s["geocode_confidence"] == 1.0

    ext = s["_extraction"]
    assert "event_signature" in ext
    assert isinstance(ext["topics"], list)
    assert "disaster" in ext["topics"]
    assert ext["location_type"] == "terrestrial"
    assert isinstance(ext["actors"], list)
    assert isinstance(ext["locations"], list)
    assert len(ext["locations"]) == 1
    assert ext["locations"][0]["role"] == "event_location"


# --- Fallback behavior tests ---

def test_scrape_gdacs_geojson_first():
    """GeoJSON is preferred over RSS."""
    geojson_features = [_make_gdacs_geojson_feature()]
    with patch("src.gdacs._fetch_geojson", return_value=geojson_features):
        with patch("src.gdacs._fetch_rss") as mock_rss:
            stories = scrape_gdacs()
    assert len(stories) == 1
    mock_rss.assert_not_called()


def test_scrape_gdacs_rss_fallback():
    """Falls back to RSS when GeoJSON fails."""
    rss_items = [_make_gdacs_rss_item()]
    with patch("src.gdacs._fetch_geojson", return_value=None):
        with patch("src.gdacs._fetch_rss", return_value=rss_items):
            stories = scrape_gdacs()
    assert len(stories) == 1


def test_scrape_gdacs_both_fail():
    """Returns empty when both sources fail."""
    with patch("src.gdacs._fetch_geojson", return_value=None):
        with patch("src.gdacs._fetch_rss", return_value=None):
            stories = scrape_gdacs()
    assert stories == []
