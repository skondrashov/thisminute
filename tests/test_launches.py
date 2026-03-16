"""Tests for Launch Library 2 adapter."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.launches import (
    scrape_launches,
    _status_to_severity,
    _status_to_human_interest,
    _build_summary,
    _build_event_signature,
    _get_provider_concepts,
    _parse_launch,
    _fetch_json,
)
from src.database import init_db, get_connection, insert_story, store_extraction


# --- Helper to build mock launch objects ---

def _make_launch(
    url="https://ll.thespacedevs.com/2.3.0/launch/1/",
    name="Falcon 9 Block 5 | Starlink Group 12-3",
    status_abbrev="Go",
    mission_desc="A batch of Starlink satellites for SpaceX's broadband network.",
    pad_name="SLC-40",
    pad_lat="28.5618",
    pad_lon="-80.5772",
    loc_name="Cape Canaveral, FL, USA",
    net="2026-03-15T14:30:00Z",
    rocket_name="Falcon 9 Block 5",
    image=None,
):
    """Build a mock Launch Library 2 launch object."""
    return {
        "id": "test-id-1",
        "name": name,
        "url": url,
        "net": net,
        "status": {"abbrev": status_abbrev},
        "rocket": {"configuration": {"name": rocket_name}},
        "mission": {"description": mission_desc},
        "pad": {
            "name": pad_name,
            "latitude": pad_lat,
            "longitude": pad_lon,
            "location": {"name": loc_name},
        },
        "image": image,
    }


# --- Severity mapping tests ---

def test_severity_routine_commercial():
    assert _status_to_severity("Go", "A batch of Starlink satellites.") == 2

def test_severity_government():
    assert _status_to_severity("Go", "Military reconnaissance satellite.") == 3

def test_severity_crew_mission():
    assert _status_to_severity("Go", "Crew Dragon carrying astronauts to ISS.") == 4

def test_severity_iss():
    assert _status_to_severity("Go", "Resupply mission to the International Space Station.") == 4

def test_severity_maiden_flight():
    assert _status_to_severity("Go", "Maiden flight of the new rocket.") == 5

def test_severity_default():
    assert _status_to_severity("TBD", "") == 2


# --- Human interest score tests ---

def test_human_interest_routine_starlink():
    assert _status_to_human_interest("Go", "Starlink satellites.", "Falcon 9 | Starlink Group 12-3") == 6

def test_human_interest_crew():
    assert _status_to_human_interest("Go", "Carrying astronauts to ISS.", "Crew Dragon") == 8

def test_human_interest_historic():
    assert _status_to_human_interest("Go", "Maiden flight of Starship.", "Starship") == 9

def test_human_interest_deep_space():
    assert _status_to_human_interest("Go", "Mission to Mars.", "Falcon Heavy | Mars Probe") == 8

def test_human_interest_moon():
    assert _status_to_human_interest("Go", "Lunar landing mission.", "SLS | Artemis") == 8

def test_human_interest_default():
    assert _status_to_human_interest("Go", "Weather satellite.", "Atlas V | GOES-T") == 7


# --- Provider concepts tests ---

def test_provider_spacex():
    concepts = _get_provider_concepts("Falcon 9 Block 5 | Starlink")
    assert "spacex" in concepts

def test_provider_nasa():
    concepts = _get_provider_concepts("SLS | Artemis - NASA mission")
    assert "nasa" in concepts

def test_provider_ula():
    concepts = _get_provider_concepts("Atlas V | ULA payload")
    assert "ula" in concepts

def test_provider_rocket_lab():
    concepts = _get_provider_concepts("Electron | Rocket Lab mission")
    assert "rocketlab" in concepts

def test_provider_unknown():
    concepts = _get_provider_concepts("Unknown Rocket | Payload")
    assert concepts == []

def test_provider_multiple():
    concepts = _get_provider_concepts("Falcon 9 | NASA SpaceX mission")
    assert "spacex" in concepts
    assert "nasa" in concepts


# --- Summary builder tests ---

def test_summary_combined():
    """Summary includes rocket name, pad, status, and date."""
    launch = _make_launch(status_abbrev="Go", net="2026-03-15T14:30:00Z")
    summary = _build_summary(launch)
    assert "Falcon 9" in summary
    assert "Starlink" in summary
    assert "SLC-40" in summary or "Cape Canaveral" in summary
    assert "Go" in summary
    assert "2026-03-15" in summary


def test_summary_long_mission_desc():
    long_desc = "A" * 400
    launch = _make_launch(mission_desc=long_desc)
    summary = _build_summary(launch)
    assert "..." in summary


# --- Event signature tests ---

def test_event_signature_spacex():
    launch = _make_launch(name="Falcon 9 Block 5 | Starlink Group 12-3")
    sig = _build_event_signature(launch)
    assert "SpaceX" in sig
    assert "Starlink Group 12-3" in sig

def test_event_signature_ula():
    launch = _make_launch(name="Vulcan Centaur | NROL-106")
    sig = _build_event_signature(launch)
    assert "ULA" in sig
    assert "NROL-106" in sig

def test_event_signature_no_pipe():
    launch = _make_launch(name="Soyuz 2.1b")
    sig = _build_event_signature(launch)
    assert "Soyuz 2.1b" in sig

def test_event_signature_has_date():
    launch = _make_launch(net="2026-03-15T14:30:00Z")
    sig = _build_event_signature(launch)
    assert "March 2026" in sig or "2026" in sig


# --- Coordinate extraction tests ---

def test_coordinate_extraction():
    launch = _make_launch(pad_lat="28.5618", pad_lon="-80.5772")
    now = "2026-03-14T00:00:00Z"
    story = _parse_launch(launch, now)
    assert story is not None
    assert story["lat"] == 28.5618
    assert story["lon"] == -80.5772

def test_coordinate_missing_lat():
    launch = _make_launch(pad_lat=None, pad_lon="-80.5772")
    now = "2026-03-14T00:00:00Z"
    story = _parse_launch(launch, now)
    assert story is None

def test_coordinate_invalid():
    launch = _make_launch(pad_lat="not_a_number", pad_lon="-80.5772")
    now = "2026-03-14T00:00:00Z"
    story = _parse_launch(launch, now)
    assert story is None


# --- Dedup tests ---

def test_dedup_same_url():
    """Same launch in both feeds should be deduped."""
    launch = _make_launch(url="https://ll.thespacedevs.com/2.3.0/launch/1/")
    mock_upcoming = {"results": [launch]}
    mock_previous = {"results": [launch]}
    with patch("src.launches._fetch_json") as mock_fetch:
        mock_fetch.side_effect = [mock_upcoming, mock_previous]
        with patch("src.launches._cache", {"stories": [], "fetched_at": 0.0}):
            stories = scrape_launches()
    assert len(stories) == 1

def test_dedup_different_urls():
    """Different launches should both appear."""
    launch1 = _make_launch(url="https://ll.thespacedevs.com/2.3.0/launch/1/")
    launch2 = _make_launch(
        url="https://ll.thespacedevs.com/2.3.0/launch/2/",
        name="Ariane 6 | ESA Satellite",
    )
    mock_upcoming = {"results": [launch1]}
    mock_previous = {"results": [launch2]}
    with patch("src.launches._fetch_json") as mock_fetch:
        mock_fetch.side_effect = [mock_upcoming, mock_previous]
        with patch("src.launches._cache", {"stories": [], "fetched_at": 0.0}):
            stories = scrape_launches()
    assert len(stories) == 2


# --- Story dict shape tests ---

def test_story_dict_shape():
    """Launch story dict has all required fields."""
    launch = _make_launch()
    mock_data = {"results": [launch]}
    with patch("src.launches._fetch_json") as mock_fetch:
        mock_fetch.side_effect = [mock_data, {"results": []}]
        with patch("src.launches._cache", {"stories": [], "fetched_at": 0.0}):
            stories = scrape_launches()

    assert len(stories) == 1
    s = stories[0]

    # Required story fields
    assert s["title"] == "Starlink Group 12-3 (Falcon 9 Block 5)"
    assert s["url"] == "https://ll.thespacedevs.com/2.3.0/launch/1/"
    assert len(s["summary"]) > 0
    assert s["source"] == "Launch Library"
    assert s["origin"] == "launches"
    assert s["source_type"] == "inferred"
    assert s["category"] == "science"
    assert "space" in s["concepts"]
    assert "science" in s["concepts"]
    assert "launch" in s["concepts"]
    assert "spacex" in s["concepts"]
    assert s["lat"] == 28.5618
    assert s["lon"] == -80.5772
    assert s["geocode_confidence"] == 1.0
    assert s["published_at"] is not None
    assert s["location_name"] == "Cape Canaveral, FL, USA"

    # Extraction data
    ext = s["_extraction"]
    assert "SpaceX" in ext["event_signature"]
    assert "Starlink" in ext["event_signature"]
    assert ext["topics"] == ["space", "launch"]
    assert ext["severity"] == 2  # routine commercial
    assert ext["location_type"] == "terrestrial"
    assert ext["human_interest_score"] == 6  # Starlink
    assert isinstance(ext["actors"], list)
    assert isinstance(ext["locations"], list)
    assert len(ext["locations"]) == 1
    assert ext["locations"][0]["role"] == "event_location"
    assert ext["locations"][0]["lat"] == 28.5618
    assert ext["locations"][0]["lon"] == -80.5772
    assert ext["sentiment"] == "neutral"  # Go status


@pytest.mark.parametrize("status_abbrev,expected_sentiment", [
    ("Success", "positive"),
    ("Failure", "negative"),
])
def test_story_dict_status_sentiment(status_abbrev, expected_sentiment):
    launch = _make_launch(status_abbrev=status_abbrev)
    now = "2026-03-14T00:00:00Z"
    story = _parse_launch(launch, now)
    assert story["_extraction"]["sentiment"] == expected_sentiment


# --- Cache tests ---

def test_cache_returns_cached():
    """Cache returns stored results within cache window."""
    import time as time_mod
    cached_stories = [{"title": "Cached Launch", "url": "https://cached"}]
    cache_state = {"stories": cached_stories, "fetched_at": time_mod.monotonic()}
    with patch("src.launches._cache", cache_state):
        stories = scrape_launches()
    assert len(stories) == 1
    assert stories[0]["title"] == "Cached Launch"


# --- Missing field handling tests ---

def test_missing_name():
    launch = _make_launch(name="")
    now = "2026-03-14T00:00:00Z"
    story = _parse_launch(launch, now)
    assert story is None

def test_missing_url():
    launch = _make_launch(url="")
    now = "2026-03-14T00:00:00Z"
    story = _parse_launch(launch, now)
    assert story is None

def test_missing_pad():
    launch = _make_launch()
    launch["pad"] = None
    now = "2026-03-14T00:00:00Z"
    story = _parse_launch(launch, now)
    assert story is None

def test_missing_mission():
    """Launch without mission description still works."""
    launch = _make_launch(mission_desc="")
    launch["mission"] = None
    now = "2026-03-14T00:00:00Z"
    story = _parse_launch(launch, now)
    assert story is not None
    assert len(story["summary"]) > 0

def test_missing_status():
    """Launch without status still works."""
    launch = _make_launch()
    launch["status"] = None
    now = "2026-03-14T00:00:00Z"
    story = _parse_launch(launch, now)
    assert story is not None


# --- Concepts dedup test ---

def test_concepts_no_duplicates():
    """Concepts list should have no duplicates."""
    launch = _make_launch(name="Falcon 9 | NASA SpaceX mission")
    now = "2026-03-14T00:00:00Z"
    story = _parse_launch(launch, now)
    assert len(story["concepts"]) == len(set(story["concepts"]))


# --- Database integration tests ---

def test_launch_extraction_storage():
    """Pre-built extraction data from launches stores correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        story = {
            "title": "Falcon 9 Block 5 | Starlink Group 12-3",
            "url": "https://ll.thespacedevs.com/2.3.0/launch/test_ext/",
            "summary": "Falcon 9 launch.",
            "source": "Launch Library",
            "scraped_at": "2026-03-14T00:00:00Z",
            "origin": "launches",
            "source_type": "inferred",
            "category": "science",
            "concepts": ["space", "science", "launch"],
            "lat": 28.5618,
            "lon": -80.5772,
            "geocode_confidence": 1.0,
        }

        insert_story(conn, story)
        row = conn.execute("SELECT id FROM stories WHERE url = ?",
                           (story["url"],)).fetchone()
        story_id = row["id"]

        extraction = {
            "event_signature": "SpaceX Starlink Group 12-3 March 2026",
            "topics": ["space", "launch"],
            "severity": 2,
            "sentiment": "neutral",
            "primary_action": "launch",
            "location_type": "terrestrial",
            "search_keywords": ["space", "launch", "rocket", "Cape Canaveral"],
            "is_opinion": False,
            "human_interest_score": 6,
            "actors": [],
            "locations": [
                {"name": "Cape Canaveral, FL, USA", "role": "event_location",
                 "lat": 28.5618, "lon": -80.5772}
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
        assert ext_row["event_signature"] == "SpaceX Starlink Group 12-3 March 2026"
        assert ext_row["severity"] == 2
        assert ext_row["human_interest_score"] == 6

        # Verify extraction_status
        status_row = conn.execute(
            "SELECT extraction_status FROM stories WHERE id = ?", (story_id,)
        ).fetchone()
        assert status_row["extraction_status"] == "done"

        conn.close()
