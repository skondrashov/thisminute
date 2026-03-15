"""Tests for ACLED (Armed Conflict Location & Event Data) adapter."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from src.acled import (
    scrape_acled,
    _severity_with_fatalities,
    _human_interest_with_fatalities,
    _get_concepts,
    _get_category,
    _build_event_signature,
    _build_title,
    _build_summary,
    _build_url,
    _fetch_acled,
)
from src.database import init_db, get_connection, insert_story, store_extraction


def _make_acled_event(data_id="12345", event_type="Battles",
                      sub_event_type="Armed clash", country="Syria",
                      admin1="Aleppo", actor1="Government forces",
                      actor2="Rebel group", fatalities=5,
                      lat="36.2", lon="37.15",
                      notes="Armed clash between forces.",
                      source="Local media",
                      event_date="2026-03-10"):
    """Build a mock ACLED event dict."""
    return {
        "data_id": data_id,
        "event_type": event_type,
        "sub_event_type": sub_event_type,
        "country": country,
        "admin1": admin1,
        "actor1": actor1,
        "actor2": actor2,
        "fatalities": fatalities,
        "latitude": lat,
        "longitude": lon,
        "notes": notes,
        "source": source,
        "event_date": event_date,
    }


# --- Severity mapping tests ---

def test_severity_battles_no_fatalities():
    assert _severity_with_fatalities("Battles", 0) == 3


def test_severity_battles_with_fatalities():
    assert _severity_with_fatalities("Battles", 5) == 4


def test_severity_battles_many_fatalities():
    assert _severity_with_fatalities("Battles", 20) == 5


def test_severity_battles_mass_fatalities():
    assert _severity_with_fatalities("Battles", 100) == 5


def test_severity_protests_no_fatalities():
    assert _severity_with_fatalities("Protests", 0) == 1


def test_severity_protests_with_fatalities():
    assert _severity_with_fatalities("Protests", 5) == 2


def test_severity_protests_many_fatalities():
    assert _severity_with_fatalities("Protests", 20) == 3


def test_severity_protests_mass_fatalities():
    assert _severity_with_fatalities("Protests", 100) == 5


def test_severity_riots_no_fatalities():
    assert _severity_with_fatalities("Riots", 0) == 2


def test_severity_riots_with_fatalities():
    assert _severity_with_fatalities("Riots", 5) == 3


def test_severity_explosions_no_fatalities():
    assert _severity_with_fatalities("Explosions/Remote violence", 0) == 3


def test_severity_explosions_with_fatalities():
    assert _severity_with_fatalities("Explosions/Remote violence", 1) == 3


def test_severity_explosions_many_fatalities():
    assert _severity_with_fatalities("Explosions/Remote violence", 20) == 5


def test_severity_vac_no_fatalities():
    assert _severity_with_fatalities("Violence against civilians", 0) == 3


def test_severity_vac_with_fatalities():
    assert _severity_with_fatalities("Violence against civilians", 1) == 3


def test_severity_strategic_no_fatalities():
    assert _severity_with_fatalities("Strategic developments", 0) == 1


def test_severity_strategic_mass_fatalities():
    assert _severity_with_fatalities("Strategic developments", 100) == 5


def test_severity_unknown_type():
    assert _severity_with_fatalities("Unknown type", 0) == 2


# --- Human interest mapping tests ---

def test_hi_battles_no_fatalities():
    assert _human_interest_with_fatalities("Battles", 0) == 5


def test_hi_battles_some_fatalities():
    assert _human_interest_with_fatalities("Battles", 1) == 6


def test_hi_battles_5_fatalities():
    assert _human_interest_with_fatalities("Battles", 5) == 7


def test_hi_battles_10_fatalities():
    assert _human_interest_with_fatalities("Battles", 10) == 7


def test_hi_battles_20_fatalities():
    assert _human_interest_with_fatalities("Battles", 20) == 8


def test_hi_battles_50_fatalities():
    assert _human_interest_with_fatalities("Battles", 50) == 9


def test_hi_battles_100_fatalities():
    assert _human_interest_with_fatalities("Battles", 100) == 10


def test_hi_protests_no_fatalities():
    assert _human_interest_with_fatalities("Protests", 0) == 4


def test_hi_vac_no_fatalities():
    assert _human_interest_with_fatalities("Violence against civilians", 0) == 6


def test_hi_strategic_no_fatalities():
    assert _human_interest_with_fatalities("Strategic developments", 0) == 3


def test_hi_unknown_type():
    assert _human_interest_with_fatalities("Unknown", 0) == 4


# --- Concept mapping tests ---

def test_concepts_battles():
    concepts = _get_concepts("Battles")
    assert "conflict" in concepts
    assert "violence" in concepts
    assert "battle" in concepts
    assert "military" in concepts


def test_concepts_explosions():
    concepts = _get_concepts("Explosions/Remote violence")
    assert "conflict" in concepts
    assert "explosion" in concepts
    assert "attack" in concepts


def test_concepts_vac():
    concepts = _get_concepts("Violence against civilians")
    assert "conflict" in concepts
    assert "civilian casualties" in concepts


def test_concepts_protests():
    concepts = _get_concepts("Protests")
    assert "conflict" in concepts
    assert "protest" in concepts
    assert "demonstration" in concepts


def test_concepts_riots():
    concepts = _get_concepts("Riots")
    assert "conflict" in concepts
    assert "riot" in concepts
    assert "unrest" in concepts


def test_concepts_strategic():
    concepts = _get_concepts("Strategic developments")
    assert "conflict" in concepts
    assert "political" in concepts
    assert "diplomacy" in concepts


def test_concepts_unknown():
    concepts = _get_concepts("Unknown")
    assert "conflict" in concepts
    assert "violence" in concepts


def test_concepts_no_duplicates():
    concepts = _get_concepts("Battles")
    assert len(concepts) == len(set(concepts))


# --- Category mapping tests ---

def test_category_battles():
    assert _get_category("Battles") == "conflict"


def test_category_explosions():
    assert _get_category("Explosions/Remote violence") == "conflict"


def test_category_vac():
    assert _get_category("Violence against civilians") == "conflict"


def test_category_protests():
    assert _get_category("Protests") == "politics"


def test_category_riots():
    assert _get_category("Riots") == "conflict"


def test_category_strategic():
    assert _get_category("Strategic developments") == "politics"


# --- Event signature tests ---

def test_event_signature_battles():
    sig = _build_event_signature("Syria", "Battles")
    assert "Syria" in sig
    assert "Battles" in sig


def test_event_signature_explosions():
    sig = _build_event_signature("Ukraine", "Explosions/Remote violence")
    assert "Ukraine" in sig
    assert "Explosions" in sig


def test_event_signature_protests():
    sig = _build_event_signature("France", "Protests")
    assert "France" in sig
    assert "Protests" in sig


def test_event_signature_has_year():
    sig = _build_event_signature("Nigeria", "Battles")
    assert "202" in sig  # year prefix


# --- Title tests ---

def test_title_with_admin():
    title = _build_title("Battles", "Armed clash", "Syria", "Aleppo")
    assert "Aleppo, Syria" in title
    assert "Armed clash" in title


def test_title_without_admin():
    title = _build_title("Protests", "Peaceful protest", "France", "")
    assert "France" in title
    assert "Peaceful protest" in title


def test_title_no_sub_event():
    title = _build_title("Battles", "", "Syria", "")
    assert "Battles" in title
    assert "Syria" in title


# --- Summary tests ---

def test_summary_with_notes():
    summary = _build_summary("Battles", "Armed clash", "Armed clash between forces.",
                             5, "Government", "Rebels", "Local media")
    assert "Armed clash between forces" in summary
    assert "Fatalities: 5" in summary
    assert "Government" in summary
    assert "Local media" in summary


def test_summary_no_notes():
    summary = _build_summary("Battles", "Armed clash", "", 0, "", "", "")
    assert "Armed clash" in summary


def test_summary_no_fatalities():
    summary = _build_summary("Protests", "Peaceful protest", "Large protest.",
                             0, "Protesters", "", "AP")
    assert "Fatalities" not in summary


def test_summary_long_notes_truncated():
    long_notes = "x" * 500
    summary = _build_summary("Battles", "", long_notes, 0, "", "", "")
    assert len(summary) < 600
    assert "..." in summary


def test_summary_no_actors():
    summary = _build_summary("Battles", "", "An event.", 0, "", "", "Source")
    assert "Actors" not in summary


# --- URL tests ---

def test_url_from_data_id():
    url = _build_url("12345")
    assert url == "https://acleddata.com/data/12345"


def test_url_different_id():
    url = _build_url("99999")
    assert "99999" in url


# --- Graceful skip when no API key ---

def test_skip_no_api_key():
    with patch("src.acled.ACLED_API_KEY", ""):
        with patch("src.acled.ACLED_EMAIL", "test@example.com"):
            stories = scrape_acled()
    assert stories == []


def test_skip_no_email():
    with patch("src.acled.ACLED_API_KEY", "test_key"):
        with patch("src.acled.ACLED_EMAIL", ""):
            stories = scrape_acled()
    assert stories == []


def test_skip_both_missing():
    with patch("src.acled.ACLED_API_KEY", ""):
        with patch("src.acled.ACLED_EMAIL", ""):
            stories = scrape_acled()
    assert stories == []


# --- Fetch returns empty ---

def test_fetch_no_credentials():
    with patch("src.acled.ACLED_API_KEY", ""):
        with patch("src.acled.ACLED_EMAIL", ""):
            result = _fetch_acled()
    assert result == []


# --- Full scrape tests ---

def test_scrape_basic():
    events = [_make_acled_event()]
    with patch("src.acled.ACLED_API_KEY", "test_key"):
        with patch("src.acled.ACLED_EMAIL", "test@example.com"):
            with patch("src.acled._fetch_acled", return_value=events):
                stories = scrape_acled()

    assert len(stories) == 1
    s = stories[0]
    assert s["origin"] == "acled"
    assert s["source_type"] == "inferred"
    assert s["category"] == "conflict"
    assert "conflict" in s["concepts"]


def test_scrape_multiple_events():
    events = [
        _make_acled_event(data_id="1", event_type="Battles", country="Syria"),
        _make_acled_event(data_id="2", event_type="Protests", country="France"),
        _make_acled_event(data_id="3", event_type="Riots", country="Nigeria"),
    ]
    with patch("src.acled.ACLED_API_KEY", "test_key"):
        with patch("src.acled.ACLED_EMAIL", "test@example.com"):
            with patch("src.acled._fetch_acled", return_value=events):
                stories = scrape_acled()

    assert len(stories) == 3


def test_scrape_empty_response():
    with patch("src.acled.ACLED_API_KEY", "test_key"):
        with patch("src.acled.ACLED_EMAIL", "test@example.com"):
            with patch("src.acled._fetch_acled", return_value=[]):
                stories = scrape_acled()

    assert stories == []


def test_scrape_skips_no_country():
    events = [_make_acled_event(country="")]
    with patch("src.acled.ACLED_API_KEY", "test_key"):
        with patch("src.acled.ACLED_EMAIL", "test@example.com"):
            with patch("src.acled._fetch_acled", return_value=events):
                stories = scrape_acled()

    assert len(stories) == 0


def test_scrape_skips_no_data_id():
    events = [_make_acled_event(data_id="")]
    with patch("src.acled.ACLED_API_KEY", "test_key"):
        with patch("src.acled.ACLED_EMAIL", "test@example.com"):
            with patch("src.acled._fetch_acled", return_value=events):
                stories = scrape_acled()

    assert len(stories) == 0


def test_scrape_skips_no_event_type():
    events = [_make_acled_event(event_type="")]
    with patch("src.acled.ACLED_API_KEY", "test_key"):
        with patch("src.acled.ACLED_EMAIL", "test@example.com"):
            with patch("src.acled._fetch_acled", return_value=events):
                stories = scrape_acled()

    assert len(stories) == 0


# --- Dedup tests ---

def test_dedup_same_data_id():
    events = [
        _make_acled_event(data_id="12345", country="Syria"),
        _make_acled_event(data_id="12345", country="Syria"),
    ]
    with patch("src.acled.ACLED_API_KEY", "test_key"):
        with patch("src.acled.ACLED_EMAIL", "test@example.com"):
            with patch("src.acled._fetch_acled", return_value=events):
                stories = scrape_acled()

    assert len(stories) == 1


def test_dedup_different_data_ids():
    events = [
        _make_acled_event(data_id="11111", country="Syria"),
        _make_acled_event(data_id="22222", country="Syria"),
    ]
    with patch("src.acled.ACLED_API_KEY", "test_key"):
        with patch("src.acled.ACLED_EMAIL", "test@example.com"):
            with patch("src.acled._fetch_acled", return_value=events):
                stories = scrape_acled()

    assert len(stories) == 2


# --- Story dict shape tests ---

def test_story_dict_shape():
    events = [_make_acled_event()]
    with patch("src.acled.ACLED_API_KEY", "test_key"):
        with patch("src.acled.ACLED_EMAIL", "test@example.com"):
            with patch("src.acled._fetch_acled", return_value=events):
                stories = scrape_acled()

    assert len(stories) == 1
    s = stories[0]

    # Required story fields
    assert "title" in s and len(s["title"]) > 0
    assert s["url"] == "https://acleddata.com/data/12345"
    assert "summary" in s
    assert s["source"] == "ACLED"
    assert s["origin"] == "acled"
    assert s["source_type"] == "inferred"
    assert s["category"] == "conflict"
    assert "conflict" in s["concepts"]
    assert "violence" in s["concepts"]
    assert s["lat"] == 36.2
    assert s["lon"] == 37.15
    assert s["geocode_confidence"] == 0.9
    assert s["published_at"] == "2026-03-10"

    # Extraction data
    ext = s["_extraction"]
    assert "event_signature" in ext
    assert "Syria" in ext["event_signature"]
    assert isinstance(ext["topics"], list)
    assert ext["severity"] == 4  # Battles with 5 fatalities
    assert ext["location_type"] == "terrestrial"
    assert isinstance(ext["human_interest_score"], int)
    assert ext["human_interest_score"] == 7  # Battles with 5 fatalities
    assert isinstance(ext["actors"], list)
    assert isinstance(ext["locations"], list)
    assert len(ext["locations"]) == 1
    assert ext["locations"][0]["role"] == "event_location"
    assert ext["locations"][0]["name"] == "Aleppo"


def test_story_dict_shape_protests():
    events = [_make_acled_event(
        data_id="99999", event_type="Protests",
        sub_event_type="Peaceful protest", country="France",
        admin1="Paris", fatalities=0,
        lat="48.86", lon="2.35")]
    with patch("src.acled.ACLED_API_KEY", "test_key"):
        with patch("src.acled.ACLED_EMAIL", "test@example.com"):
            with patch("src.acled._fetch_acled", return_value=events):
                stories = scrape_acled()

    assert len(stories) == 1
    s = stories[0]
    assert s["category"] == "politics"
    assert "protest" in s["concepts"]
    assert s["_extraction"]["severity"] == 1
    assert s["_extraction"]["sentiment"] == "mixed"


def test_story_dict_shape_strategic():
    events = [_make_acled_event(
        data_id="88888", event_type="Strategic developments",
        sub_event_type="Agreement", country="Colombia",
        admin1="", fatalities=0,
        lat="4.7", lon="-74.1")]
    with patch("src.acled.ACLED_API_KEY", "test_key"):
        with patch("src.acled.ACLED_EMAIL", "test@example.com"):
            with patch("src.acled._fetch_acled", return_value=events):
                stories = scrape_acled()

    assert len(stories) == 1
    s = stories[0]
    assert s["category"] == "politics"
    assert "political" in s["concepts"]
    assert s["_extraction"]["severity"] == 1
    assert s["_extraction"]["sentiment"] == "neutral"


# --- Coordinate handling tests ---

def test_no_coordinates():
    events = [_make_acled_event(lat="", lon="")]
    with patch("src.acled.ACLED_API_KEY", "test_key"):
        with patch("src.acled.ACLED_EMAIL", "test@example.com"):
            with patch("src.acled._fetch_acled", return_value=events):
                stories = scrape_acled()

    assert len(stories) == 1
    s = stories[0]
    assert "lat" not in s or s.get("lat") is None


def test_invalid_coordinates():
    events = [_make_acled_event(lat="abc", lon="xyz")]
    with patch("src.acled.ACLED_API_KEY", "test_key"):
        with patch("src.acled.ACLED_EMAIL", "test@example.com"):
            with patch("src.acled._fetch_acled", return_value=events):
                stories = scrape_acled()

    assert len(stories) == 1
    s = stories[0]
    # Story should still be created but without lat/lon
    assert s["_extraction"]["locations"] == []


# --- Sentiment mapping tests ---

def test_sentiment_battles():
    events = [_make_acled_event(event_type="Battles")]
    with patch("src.acled.ACLED_API_KEY", "test_key"):
        with patch("src.acled.ACLED_EMAIL", "test@example.com"):
            with patch("src.acled._fetch_acled", return_value=events):
                stories = scrape_acled()
    assert stories[0]["_extraction"]["sentiment"] == "negative"


def test_sentiment_protests():
    events = [_make_acled_event(event_type="Protests", fatalities=0)]
    with patch("src.acled.ACLED_API_KEY", "test_key"):
        with patch("src.acled.ACLED_EMAIL", "test@example.com"):
            with patch("src.acled._fetch_acled", return_value=events):
                stories = scrape_acled()
    assert stories[0]["_extraction"]["sentiment"] == "mixed"


def test_sentiment_strategic():
    events = [_make_acled_event(event_type="Strategic developments", fatalities=0)]
    with patch("src.acled.ACLED_API_KEY", "test_key"):
        with patch("src.acled.ACLED_EMAIL", "test@example.com"):
            with patch("src.acled._fetch_acled", return_value=events):
                stories = scrape_acled()
    assert stories[0]["_extraction"]["sentiment"] == "neutral"


# --- Location name handling ---

def test_location_name_with_admin():
    events = [_make_acled_event(country="Syria", admin1="Aleppo")]
    with patch("src.acled.ACLED_API_KEY", "test_key"):
        with patch("src.acled.ACLED_EMAIL", "test@example.com"):
            with patch("src.acled._fetch_acled", return_value=events):
                stories = scrape_acled()
    assert stories[0]["location_name"] == "Aleppo"


def test_location_name_no_admin():
    events = [_make_acled_event(country="Syria", admin1="")]
    with patch("src.acled.ACLED_API_KEY", "test_key"):
        with patch("src.acled.ACLED_EMAIL", "test@example.com"):
            with patch("src.acled._fetch_acled", return_value=events):
                stories = scrape_acled()
    assert stories[0]["location_name"] == "Syria"


# --- Search keywords ---

def test_search_keywords():
    events = [_make_acled_event(
        event_type="Battles", country="Syria", admin1="Aleppo")]
    with patch("src.acled.ACLED_API_KEY", "test_key"):
        with patch("src.acled.ACLED_EMAIL", "test@example.com"):
            with patch("src.acled._fetch_acled", return_value=events):
                stories = scrape_acled()
    kw = stories[0]["_extraction"]["search_keywords"]
    assert "battles" in kw
    assert "syria" in kw
    assert "aleppo" in kw


def test_search_keywords_no_admin():
    events = [_make_acled_event(
        event_type="Protests", country="France", admin1="")]
    with patch("src.acled.ACLED_API_KEY", "test_key"):
        with patch("src.acled.ACLED_EMAIL", "test@example.com"):
            with patch("src.acled._fetch_acled", return_value=events):
                stories = scrape_acled()
    kw = stories[0]["_extraction"]["search_keywords"]
    assert "protests" in kw
    assert "france" in kw


# --- Config integration tests ---

def test_config_acled_api_key():
    from src.config import ACLED_API_KEY as cfg_key
    assert isinstance(cfg_key, str)


def test_config_acled_email():
    from src.config import ACLED_EMAIL as cfg_email
    assert isinstance(cfg_email, str)


def test_config_acled_url():
    from src.config import ACLED_URL as cfg_url
    assert "acleddata.com" in cfg_url


def test_config_source_enabled():
    from src.config import SOURCE_ENABLED
    assert "acled" in SOURCE_ENABLED


# --- Database integration tests ---

def test_insert_acled_story():
    """ACLED story with source_type='inferred' inserts correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        story = {
            "title": "Armed clash in Aleppo, Syria",
            "url": "https://acleddata.com/data/12345",
            "summary": "Armed clash between forces.",
            "source": "ACLED",
            "scraped_at": "2026-03-14T00:00:00Z",
            "origin": "acled",
            "source_type": "inferred",
            "category": "conflict",
            "concepts": ["conflict", "violence", "battle", "military"],
            "lat": 36.2,
            "lon": 37.15,
            "geocode_confidence": 0.9,
        }

        was_new = insert_story(conn, story)
        assert was_new is True

        row = conn.execute("SELECT source_type, origin FROM stories WHERE url = ?",
                           (story["url"],)).fetchone()
        assert row["source_type"] == "inferred"
        assert row["origin"] == "acled"

        conn.close()


def test_acled_extraction_storage():
    """Pre-built extraction data from ACLED stores correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        story = {
            "title": "Armed clash in Aleppo, Syria",
            "url": "https://acleddata.com/data/12345",
            "summary": "Armed clash between forces.",
            "source": "ACLED",
            "scraped_at": "2026-03-14T00:00:00Z",
            "origin": "acled",
            "source_type": "inferred",
            "category": "conflict",
            "concepts": ["conflict", "violence", "battle", "military"],
            "lat": 36.2,
            "lon": 37.15,
            "geocode_confidence": 0.9,
        }

        insert_story(conn, story)
        row = conn.execute("SELECT id FROM stories WHERE url = ?",
                           (story["url"],)).fetchone()
        story_id = row["id"]

        extraction = {
            "event_signature": "2026 Syria Battles",
            "topics": ["conflict", "violence", "battle", "military"],
            "severity": 4,
            "sentiment": "negative",
            "primary_action": "battles",
            "location_type": "terrestrial",
            "search_keywords": ["battles", "syria", "aleppo"],
            "is_opinion": False,
            "human_interest_score": 7,
            "actors": [],
            "locations": [
                {"name": "Aleppo", "role": "event_location",
                 "lat": 36.2, "lon": 37.15}
            ],
        }

        store_extraction(conn, story_id, extraction)
        conn.execute(
            "UPDATE stories SET extraction_status = 'done' WHERE id = ?",
            (story_id,),
        )
        conn.commit()

        ext_row = conn.execute(
            "SELECT event_signature, severity, human_interest_score FROM story_extractions WHERE story_id = ?",
            (story_id,),
        ).fetchone()
        assert ext_row["event_signature"] == "2026 Syria Battles"
        assert ext_row["severity"] == 4
        assert ext_row["human_interest_score"] == 7

        status_row = conn.execute(
            "SELECT extraction_status FROM stories WHERE id = ?", (story_id,)
        ).fetchone()
        assert status_row["extraction_status"] == "done"

        conn.close()


# --- All event types produce valid stories ---

def test_all_event_types():
    """Each ACLED event type should produce a valid story."""
    event_types = [
        "Battles",
        "Explosions/Remote violence",
        "Violence against civilians",
        "Protests",
        "Riots",
        "Strategic developments",
    ]
    for et in event_types:
        events = [_make_acled_event(
            data_id=str(hash(et)), event_type=et,
            country="TestCountry", fatalities=0)]
        with patch("src.acled.ACLED_API_KEY", "test_key"):
            with patch("src.acled.ACLED_EMAIL", "test@example.com"):
                with patch("src.acled._fetch_acled", return_value=events):
                    stories = scrape_acled()
        assert len(stories) == 1, "Failed for event type: %s" % et
        s = stories[0]
        assert s["origin"] == "acled"
        assert s["source_type"] == "inferred"
        assert "conflict" in s["concepts"]


# --- Fatality escalation integration test ---

def test_fatality_escalation():
    """Higher fatalities should increase severity."""
    events_low = [_make_acled_event(data_id="1", fatalities=0)]
    events_high = [_make_acled_event(data_id="2", fatalities=50)]

    with patch("src.acled.ACLED_API_KEY", "test_key"):
        with patch("src.acled.ACLED_EMAIL", "test@example.com"):
            with patch("src.acled._fetch_acled", return_value=events_low):
                stories_low = scrape_acled()
            with patch("src.acled._fetch_acled", return_value=events_high):
                stories_high = scrape_acled()

    assert stories_high[0]["_extraction"]["severity"] > stories_low[0]["_extraction"]["severity"]
    assert stories_high[0]["_extraction"]["human_interest_score"] > stories_low[0]["_extraction"]["human_interest_score"]


# --- Error handling test ---

def test_malformed_event_skipped():
    """Events that cause exceptions should be skipped, not crash."""
    events = [
        {"data_id": "good", "event_type": "Battles", "country": "Syria",
         "admin1": "Aleppo", "latitude": "36.2", "longitude": "37.15",
         "fatalities": "5", "notes": "Good event.", "source": "Local",
         "event_date": "2026-03-10", "sub_event_type": "Armed clash",
         "actor1": "A", "actor2": "B"},
        # This one has no data_id so will be skipped
        {"event_type": "Battles", "country": "Syria"},
    ]
    with patch("src.acled.ACLED_API_KEY", "test_key"):
        with patch("src.acled.ACLED_EMAIL", "test@example.com"):
            with patch("src.acled._fetch_acled", return_value=events):
                stories = scrape_acled()
    assert len(stories) == 1


# --- Credential redaction tests ---

def test_fetch_acled_uses_log_url():
    """_fetch_acled passes a redacted log_url to fetch_json."""
    with patch("src.acled.ACLED_API_KEY", "secret_key_123"):
        with patch("src.acled.ACLED_EMAIL", "secret@example.com"):
            with patch("src.acled.fetch_json", return_value=[]) as mock_fj:
                _fetch_acled()
    mock_fj.assert_called_once()
    call_kwargs = mock_fj.call_args
    # The actual URL (positional arg) contains the key
    actual_url = call_kwargs[0][0]
    assert "secret_key_123" in actual_url
    # But log_url must NOT contain the key
    log_url = call_kwargs[1]["log_url"]
    assert "secret_key_123" not in log_url
    assert "secret@example.com" not in log_url
    assert "REDACTED" in log_url


def test_fetch_acled_log_url_has_base():
    """Redacted log_url still contains the base ACLED URL."""
    with patch("src.acled.ACLED_API_KEY", "mykey"):
        with patch("src.acled.ACLED_EMAIL", "me@test.com"):
            with patch("src.acled.fetch_json", return_value=[]) as mock_fj:
                _fetch_acled()
    log_url = mock_fj.call_args[1]["log_url"]
    assert "acleddata.com" in log_url


# --- ACLED_MAX_EVENTS config tests ---

def test_config_acled_max_events():
    """ACLED_MAX_EVENTS config var exists and has correct default."""
    from src.config import ACLED_MAX_EVENTS
    assert isinstance(ACLED_MAX_EVENTS, int)
    assert ACLED_MAX_EVENTS == 200


def test_fetch_acled_uses_max_events():
    """_fetch_acled passes ACLED_MAX_EVENTS as the limit parameter."""
    with patch("src.acled.ACLED_API_KEY", "test_key"):
        with patch("src.acled.ACLED_EMAIL", "test@example.com"):
            with patch("src.acled.ACLED_MAX_EVENTS", 50):
                with patch("src.acled.fetch_json", return_value=[]) as mock_fj:
                    _fetch_acled()
    actual_url = mock_fj.call_args[0][0]
    assert "limit=50" in actual_url
    log_url = mock_fj.call_args[1]["log_url"]
    assert "limit=50" in log_url


def test_fetch_acled_default_limit():
    """With default ACLED_MAX_EVENTS=200, URL contains limit=200."""
    with patch("src.acled.ACLED_API_KEY", "test_key"):
        with patch("src.acled.ACLED_EMAIL", "test@example.com"):
            with patch("src.acled.fetch_json", return_value=[]) as mock_fj:
                _fetch_acled()
    actual_url = mock_fj.call_args[0][0]
    assert "limit=200" in actual_url
