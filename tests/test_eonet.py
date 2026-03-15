"""Tests for EONET (NASA Earth Observatory Natural Event Tracker) adapter."""

import json
from unittest.mock import patch, MagicMock

import pytest

from src.eonet import (
    scrape_eonet,
    _get_category_id,
    _get_category_title,
    _get_latest_geometry,
    _get_latest_date,
    _build_event_url,
    _build_summary,
    _build_event_signature,
    _fetch_events,
)


def _make_eonet_event(event_id="EONET_1234", title="Wildfire - S of Lubbock, Texas, US",
                       cat_id="wildfires", cat_title="Wildfires",
                       lat=33.3, lon=-101.8, source_url="https://firms.modaps.eosdis.nasa.gov"):
    """Build a mock EONET event."""
    return {
        "id": event_id,
        "title": title,
        "categories": [{"id": cat_id, "title": cat_title}],
        "sources": [{"id": "InciWeb", "url": source_url}],
        "geometry": [
            {
                "magnitudeValue": None,
                "magnitudeUnit": None,
                "date": "2026-03-14T00:00:00Z",
                "type": "Point",
                "coordinates": [lon, lat],
            }
        ],
    }


# --- Coordinate extraction tests ---

def test_geometry_point():
    event = _make_eonet_event(lat=33.3, lon=-101.8)
    lat, lon = _get_latest_geometry(event)
    assert abs(lat - 33.3) < 0.01
    assert abs(lon - (-101.8)) < 0.01


def test_geometry_polygon():
    event = {
        "id": "EONET_5678",
        "title": "Iceberg",
        "categories": [{"id": "seaLakeIce", "title": "Sea and Lake Ice"}],
        "geometry": [
            {
                "date": "2026-03-14T00:00:00Z",
                "type": "Polygon",
                "coordinates": [
                    [[-50.0, -60.0], [-40.0, -60.0], [-40.0, -50.0], [-50.0, -50.0], [-50.0, -60.0]]
                ],
            }
        ],
        "sources": [],
    }
    lat, lon = _get_latest_geometry(event)
    assert lat is not None
    assert lon is not None
    assert abs(lat - (-56.0)) < 1.0
    assert abs(lon - (-46.0)) < 1.0


def test_geometry_empty():
    event = {"geometry": []}
    lat, lon = _get_latest_geometry(event)
    assert lat is None
    assert lon is None


def test_geometry_most_recent():
    """Should use the most recent geometry entry."""
    event = {
        "geometry": [
            {"date": "2026-03-10T00:00:00Z", "type": "Point", "coordinates": [10.0, 20.0]},
            {"date": "2026-03-14T00:00:00Z", "type": "Point", "coordinates": [30.0, 40.0]},
            {"date": "2026-03-12T00:00:00Z", "type": "Point", "coordinates": [50.0, 60.0]},
        ],
    }
    lat, lon = _get_latest_geometry(event)
    assert lat == 40.0  # Most recent (March 14)
    assert lon == 30.0


# --- URL builder tests ---

def test_build_url_fallback():
    event = {"id": "EONET_9999", "sources": []}
    url = _build_event_url(event)
    assert "EONET_9999" in url


# --- Event signature tests ---

def test_event_signature():
    event = _make_eonet_event(title="Wildfire - S of Lubbock, Texas, US")
    sig = _build_event_signature(event)
    assert "Wildfire" in sig
    assert "Lubbock" in sig


# --- Category/concept mapping tests ---

@pytest.mark.parametrize("cat_id,cat_title,title,expected_category,expected_concept", [
    ("wildfires", "Wildfires", "Wildfire - S of Lubbock, Texas, US", "disaster", "wildfire"),
    ("volcanoes", "Volcanoes", "Kilauea Volcano, Hawaii", "disaster", "volcano"),
    ("seaLakeIce", "Sea and Lake Ice", "Iceberg B-42", "environment", "ice"),
])
def test_category_parameterized(cat_id, cat_title, title, expected_category, expected_concept):
    event = _make_eonet_event(cat_id=cat_id, cat_title=cat_title, title=title)
    with patch("src.eonet._fetch_events", return_value=[event]):
        stories = scrape_eonet()
    assert len(stories) == 1
    assert stories[0]["category"] == expected_category
    assert expected_concept in stories[0]["concepts"]


# --- Severity tests (via scrape_eonet) ---

@pytest.mark.parametrize("cat_id,expected_severity", [
    ("volcanoes", 4),
    ("seaLakeIce", 1),
])
def test_severity_parameterized(cat_id, expected_severity):
    event = _make_eonet_event(cat_id=cat_id)
    with patch("src.eonet._fetch_events", return_value=[event]):
        stories = scrape_eonet()
    assert stories[0]["_extraction"]["severity"] == expected_severity


# --- Dedup tests ---

def test_dedup_same_id():
    events = [
        _make_eonet_event(event_id="EONET_DUP1"),
        _make_eonet_event(event_id="EONET_DUP1"),
    ]
    with patch("src.eonet._fetch_events", return_value=events):
        stories = scrape_eonet()
    assert len(stories) == 1


# --- Story dict shape tests ---

def test_story_dict_shape():
    events = [_make_eonet_event()]
    with patch("src.eonet._fetch_events", return_value=events):
        stories = scrape_eonet()

    assert len(stories) == 1
    s = stories[0]

    # Required story fields
    assert s["title"] == "Wildfire - S of Lubbock, Texas, US"
    assert s["url"] == "https://firms.modaps.eosdis.nasa.gov"
    assert s["source"] == "NASA EONET"
    assert s["origin"] == "eonet"
    assert s["source_type"] == "inferred"
    assert s["category"] == "disaster"
    assert "wildfire" in s["concepts"]
    assert abs(s["lat"] - 33.3) < 0.01
    assert abs(s["lon"] - (-101.8)) < 0.01
    assert s["geocode_confidence"] == 1.0
    assert s["published_at"] is not None

    # Extraction data
    ext = s["_extraction"]
    assert "event_signature" in ext
    assert isinstance(ext["topics"], list)
    assert ext["severity"] == 3  # wildfires default
    assert ext["location_type"] == "terrestrial"
    assert ext["human_interest_score"] == 6  # wildfires default
    assert isinstance(ext["actors"], list)
    assert isinstance(ext["locations"], list)
    assert len(ext["locations"]) == 1
    assert ext["locations"][0]["role"] == "event_location"


def test_story_dict_no_geometry():
    """Story with no usable geometry still works."""
    event = _make_eonet_event()
    event["geometry"] = []
    with patch("src.eonet._fetch_events", return_value=[event]):
        stories = scrape_eonet()

    assert len(stories) == 1
    s = stories[0]
    assert s["geocode_confidence"] == 0.8
    assert s["_extraction"]["locations"] == []


# --- Fetch error handling tests ---

def test_fetch_failure_returns_empty():
    with patch("src.eonet._fetch_events", return_value=[]):
        stories = scrape_eonet()
    assert stories == []
