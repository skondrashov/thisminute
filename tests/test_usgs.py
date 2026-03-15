"""Tests for USGS earthquake adapter."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.usgs import (
    scrape_usgs,
    _mag_to_severity,
    _mag_to_human_interest,
    _build_summary,
    _build_event_signature,
    _fetch_feed,
)
from src.database import init_db, get_connection, insert_story, store_extraction


# --- Severity mapping tests ---

def test_severity_minor():
    assert _mag_to_severity(4.5) == 1
    assert _mag_to_severity(4.9) == 1

def test_severity_moderate():
    assert _mag_to_severity(5.0) == 2
    assert _mag_to_severity(5.4) == 2

def test_severity_strong():
    assert _mag_to_severity(5.5) == 3
    assert _mag_to_severity(5.9) == 3

def test_severity_major():
    assert _mag_to_severity(6.0) == 4
    assert _mag_to_severity(6.9) == 4

def test_severity_severe():
    assert _mag_to_severity(7.0) == 5
    assert _mag_to_severity(8.5) == 5


# --- Human interest score tests ---

def test_human_interest_small():
    assert _mag_to_human_interest(4.5) == 3

def test_human_interest_medium():
    assert _mag_to_human_interest(5.5) == 5

def test_human_interest_large():
    assert _mag_to_human_interest(7.0) == 8

def test_human_interest_great():
    assert _mag_to_human_interest(8.0) == 10


# --- Summary builder tests ---

def test_summary_basic():
    props = {"mag": 5.2, "place": "52 km SSE of Hualien City, Taiwan"}
    summary = _build_summary(props)
    assert "M5.2" in summary
    assert "Hualien City, Taiwan" in summary

def test_summary_with_depth():
    props = {"mag": 6.1, "place": "Tokyo, Japan", "depth_km": 35.2}
    summary = _build_summary(props)
    assert "Depth: 35.2 km" in summary

def test_summary_with_felt():
    props = {"mag": 5.0, "place": "California", "felt": 1500}
    summary = _build_summary(props)
    assert "Felt by 1500 people" in summary

def test_summary_with_tsunami():
    props = {"mag": 7.8, "place": "Chile", "tsunami": 1}
    summary = _build_summary(props)
    assert "Tsunami warning issued" in summary

def test_summary_no_mag():
    props = {"place": "Unknown"}
    summary = _build_summary(props)
    assert "Earthquake near Unknown" in summary


# --- Event signature tests ---

def test_event_signature_with_country():
    props = {"place": "52 km SSE of Hualien City, Taiwan"}
    sig = _build_event_signature(props)
    assert "Taiwan" in sig
    assert "Earthquake" in sig

def test_event_signature_no_comma():
    props = {"place": "Central Alaska"}
    sig = _build_event_signature(props)
    assert "Central Alaska" in sig
    assert "Earthquake" in sig

def test_event_signature_empty():
    props = {"place": ""}
    sig = _build_event_signature(props)
    assert "Unknown Region" in sig


# --- Dedup tests ---

def _make_usgs_feature(url="https://earthquake.usgs.gov/eq1", mag=5.5, lat=25.0, lon=121.5, title="M 5.5 - Taiwan"):
    """Build a mock USGS GeoJSON feature."""
    return {
        "type": "Feature",
        "properties": {
            "mag": mag,
            "place": "52 km SSE of Hualien City, Taiwan",
            "time": 1710400000000,
            "url": url,
            "title": title,
            "felt": 100,
            "tsunami": 0,
        },
        "geometry": {
            "type": "Point",
            "coordinates": [lon, lat, 10.0],
        },
    }


def test_dedup_same_url():
    """Same earthquake in both feeds should be deduped."""
    features = [
        _make_usgs_feature(url="https://earthquake.usgs.gov/eq1"),
        _make_usgs_feature(url="https://earthquake.usgs.gov/eq1"),
    ]
    with patch("src.usgs._fetch_feed") as mock_fetch:
        mock_fetch.side_effect = [features[:1], features[1:]]
        stories = scrape_usgs()
    assert len(stories) == 1


def test_dedup_different_urls():
    """Different earthquakes should both appear."""
    with patch("src.usgs._fetch_feed") as mock_fetch:
        mock_fetch.side_effect = [
            [_make_usgs_feature(url="https://earthquake.usgs.gov/eq1")],
            [_make_usgs_feature(url="https://earthquake.usgs.gov/eq2", title="M 6.0 - Japan")],
        ]
        stories = scrape_usgs()
    assert len(stories) == 2


# --- Story dict shape tests ---

def test_story_dict_shape():
    """USGS story dict has all required fields."""
    with patch("src.usgs._fetch_feed") as mock_fetch:
        mock_fetch.side_effect = [
            [_make_usgs_feature()],
            [],
        ]
        stories = scrape_usgs()

    assert len(stories) == 1
    s = stories[0]

    # Required story fields
    assert s["title"] == "M 5.5 - Taiwan"
    assert s["url"] == "https://earthquake.usgs.gov/eq1"
    assert "M5.5" in s["summary"]
    assert s["source"] == "USGS Earthquakes"
    assert s["origin"] == "usgs"
    assert s["source_type"] == "inferred"
    assert s["category"] == "disaster"
    assert s["concepts"] == ["disaster", "earthquake"]
    assert s["lat"] == 25.0
    assert s["lon"] == 121.5
    assert s["geocode_confidence"] == 1.0
    assert s["published_at"] is not None

    # Extraction data
    ext = s["_extraction"]
    assert "Earthquake" in ext["event_signature"]
    assert ext["topics"] == ["earthquake", "disaster"]
    assert ext["severity"] == 3  # M5.5 = strong
    assert ext["location_type"] == "terrestrial"
    assert ext["human_interest_score"] == 5  # M5.5
    assert isinstance(ext["actors"], list)
    assert isinstance(ext["locations"], list)
    assert len(ext["locations"]) == 1
    assert ext["locations"][0]["role"] == "event_location"


def test_min_magnitude_filter():
    """Stories below min magnitude are filtered out."""
    with patch("src.usgs._fetch_feed") as mock_fetch:
        mock_fetch.side_effect = [
            [_make_usgs_feature(mag=3.0, url="https://earthquake.usgs.gov/small")],
            [],
        ]
        with patch("src.usgs.USGS_MIN_MAGNITUDE", 4.5):
            stories = scrape_usgs()
    assert len(stories) == 0


# --- Database integration tests ---

def test_insert_usgs_story():
    """USGS story with source_type='inferred' inserts correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        story = {
            "title": "M 5.5 - Taiwan Earthquake",
            "url": "https://earthquake.usgs.gov/test1",
            "summary": "M5.5 earthquake near Taiwan.",
            "source": "USGS Earthquakes",
            "scraped_at": "2026-03-14T00:00:00Z",
            "origin": "usgs",
            "source_type": "inferred",
            "category": "disaster",
            "concepts": ["disaster", "earthquake"],
            "lat": 25.0,
            "lon": 121.5,
            "geocode_confidence": 1.0,
        }

        was_new = insert_story(conn, story)
        assert was_new is True

        row = conn.execute("SELECT source_type, origin FROM stories WHERE url = ?",
                           (story["url"],)).fetchone()
        assert row["source_type"] == "inferred"
        assert row["origin"] == "usgs"

        conn.close()


def test_source_type_default_reported():
    """Regular RSS stories default to source_type='reported'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        story = {
            "title": "Some news headline",
            "url": "https://example.com/news1",
            "summary": "A news story.",
            "source": "BBC World",
            "scraped_at": "2026-03-14T00:00:00Z",
        }

        was_new = insert_story(conn, story)
        assert was_new is True

        row = conn.execute("SELECT source_type FROM stories WHERE url = ?",
                           (story["url"],)).fetchone()
        assert row["source_type"] == "reported"

        conn.close()


def test_usgs_extraction_storage():
    """Pre-built extraction data from USGS stores correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        story = {
            "title": "M 6.0 - Japan",
            "url": "https://earthquake.usgs.gov/test_ext",
            "summary": "M6.0 earthquake near Japan.",
            "source": "USGS Earthquakes",
            "scraped_at": "2026-03-14T00:00:00Z",
            "origin": "usgs",
            "source_type": "inferred",
            "category": "disaster",
            "concepts": ["disaster", "earthquake"],
            "lat": 35.0,
            "lon": 139.0,
            "geocode_confidence": 1.0,
        }

        insert_story(conn, story)
        row = conn.execute("SELECT id FROM stories WHERE url = ?",
                           (story["url"],)).fetchone()
        story_id = row["id"]

        extraction = {
            "event_signature": "2026 Japan Earthquake",
            "topics": ["earthquake", "disaster"],
            "severity": 4,
            "sentiment": "negative",
            "primary_action": "earthquake",
            "location_type": "terrestrial",
            "search_keywords": ["earthquake", "seismic", "Japan"],
            "is_opinion": False,
            "human_interest_score": 6,
            "actors": [],
            "locations": [
                {"name": "Japan", "role": "event_location", "lat": 35.0, "lon": 139.0}
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
        assert ext_row["event_signature"] == "2026 Japan Earthquake"
        assert ext_row["severity"] == 4
        assert ext_row["human_interest_score"] == 6

        # Verify extraction_status
        status_row = conn.execute(
            "SELECT extraction_status FROM stories WHERE id = ?", (story_id,)
        ).fetchone()
        assert status_row["extraction_status"] == "done"

        conn.close()
