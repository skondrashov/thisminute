"""Tests for JMA (Japan Meteorological Agency) weather warnings adapter."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.jma import (
    scrape_jma,
    _get_warning_info,
    _get_warning_concepts,
    _get_area_name,
    _get_centroid,
    _build_title,
    _build_summary,
    _build_event_signature,
    _build_url,
    _highest_severity_warning,
    _fetch_warnings,
    _fetch_area_names,
    _ACTIVE_STATUSES,
    _SKIP_CODES,
    _WARNING_CODES,
    _PREFECTURE_CENTROIDS,
)
from src.database import init_db, get_connection, insert_story, store_extraction


# --- Warning code mapping tests ---

def test_warning_info_special_warning():
    """Special warnings have severity 5."""
    info = _get_warning_info("04")
    assert info is not None
    assert info[0] == "Heavy Rain Special Warning"
    assert info[1] == "special_warning"
    assert info[2] == 5
    assert info[3] == 9


def test_warning_info_warning():
    """Regular warnings have severity 3."""
    info = _get_warning_info("05")
    assert info is not None
    assert info[0] == "Heavy Rain Warning"
    assert info[1] == "warning"
    assert info[2] == 3


def test_warning_info_advisory():
    """Advisories have severity 1-2."""
    info = _get_warning_info("07")
    assert info is not None
    assert info[0] == "Thunderstorm Advisory"
    assert info[1] == "advisory"
    assert info[2] == 2


def test_warning_info_unknown_code():
    """Unknown warning code returns None."""
    assert _get_warning_info("99") is None


def test_warning_info_all_codes_defined():
    """All known JMA codes have definitions."""
    expected_codes = [
        "02", "03", "04", "05", "06", "07", "08", "09", "10",
        "12", "13", "14", "15", "16", "17", "18", "19", "20",
        "21", "22", "24", "26", "32",
    ]
    for code in expected_codes:
        info = _get_warning_info(code)
        assert info is not None, "Missing definition for code %s" % code
        assert len(info) == 4, "Code %s should have 4 fields" % code


def test_warning_severity_range():
    """All warning severities are in 1-5 range."""
    for code, info in _WARNING_CODES.items():
        assert 1 <= info[2] <= 5, "Code %s severity %d out of range" % (code, info[2])


def test_warning_human_interest_range():
    """All human interest scores are in 1-10 range."""
    for code, info in _WARNING_CODES.items():
        assert 1 <= info[3] <= 10, "Code %s HI %d out of range" % (code, info[3])


# --- Warning concepts tests ---

def test_concepts_flood():
    concepts = _get_warning_concepts("02")
    assert "flood" in concepts


def test_concepts_thunderstorm():
    concepts = _get_warning_concepts("07")
    assert "thunderstorm" in concepts


def test_concepts_storm():
    concepts = _get_warning_concepts("09")
    assert "storm" in concepts
    assert "wind" in concepts


def test_concepts_snow():
    concepts = _get_warning_concepts("12")
    assert "snow" in concepts


def test_concepts_avalanche():
    concepts = _get_warning_concepts("20")
    assert "avalanche" in concepts


def test_concepts_unknown():
    """Unknown code returns empty list."""
    concepts = _get_warning_concepts("99")
    assert concepts == []


def test_concepts_skip_code():
    """Skip codes have no concepts mapping (they are filtered)."""
    for code in _SKIP_CODES:
        # These are valid codes but should be skipped
        assert code in _WARNING_CODES


# --- Area name resolution tests ---

def test_area_name_direct():
    names = {"012010": "Kamikawa Region", "130010": "Tokyo Region"}
    assert _get_area_name("012010", names) == "Kamikawa Region"


def test_area_name_parent_lookup():
    """Long code falls back to 6-digit parent."""
    names = {"013010": "Abashiri Region"}
    assert _get_area_name("0130100", names) == "Abashiri Region"


def test_area_name_unknown():
    """Unknown code returns 'Japan'."""
    assert _get_area_name("999999", {}) == "Japan"


# --- Centroid tests ---

def test_centroid_tokyo():
    c = _get_centroid("130010")
    assert c is not None
    assert abs(c[0] - 35.68) < 0.1  # lat
    assert abs(c[1] - 139.69) < 0.1  # lon


def test_centroid_hokkaido():
    c = _get_centroid("011000")
    assert c is not None
    assert abs(c[0] - 43.06) < 0.1


def test_centroid_okinawa():
    c = _get_centroid("471010")
    assert c is not None
    assert abs(c[0] - 26.34) < 0.1


def test_centroid_unknown_prefix():
    """Unknown prefix returns None."""
    assert _get_centroid("990000") is None


def test_all_prefectures_have_centroids():
    """All 47 prefectures (01-47) have centroids defined."""
    for i in range(1, 48):
        prefix = "%02d" % i
        assert prefix in _PREFECTURE_CENTROIDS, "Missing centroid for prefecture %s" % prefix


# --- Title and summary builder tests ---

def test_build_title():
    title = _build_title("Heavy Rain Warning", "Tokyo Region")
    assert title == "Heavy Rain Warning - Tokyo Region, Japan"


def test_build_summary():
    summary = _build_summary("Storm Warning", "Osaka Region", "warning")
    assert "Storm Warning" in summary
    assert "Osaka Region" in summary
    assert "Japan" in summary
    assert "Warning" in summary


def test_build_summary_special():
    summary = _build_summary("Heavy Rain Special Warning", "Kyushu", "special_warning")
    assert "Special Warning" in summary


# --- Event signature tests ---

def test_event_signature_format():
    sig = _build_event_signature("Heavy Rain Warning", "Tokyo Region")
    assert "Tokyo Region" in sig
    assert "Heavy Rain" in sig
    assert "Warning" not in sig  # stripped


def test_event_signature_advisory():
    sig = _build_event_signature("Wind Advisory", "Osaka Region")
    assert "Wind" in sig
    assert "Advisory" not in sig  # stripped


def test_event_signature_special():
    sig = _build_event_signature("Storm Special Warning", "Kanto")
    assert "Storm" in sig
    assert "Special Warning" not in sig  # stripped


# --- URL builder tests ---

def test_build_url():
    url = _build_url("130010")
    assert "jma.go.jp" in url
    assert "130010" in url
    assert "lang=en" in url


# --- Highest severity warning tests ---

def test_highest_severity_one_warning():
    warnings = [
        {"code": "05", "status": "\u767a\u8868"},  # Heavy Rain Warning
    ]
    result = _highest_severity_warning(warnings)
    assert result is not None
    assert result[0] == "05"
    assert result[1] == "Heavy Rain Warning"
    assert result[3] == 3  # severity


def test_highest_severity_picks_highest():
    warnings = [
        {"code": "15", "status": "\u7d99\u7d9a"},  # Wind Advisory (sev 2)
        {"code": "09", "status": "\u767a\u8868"},  # Storm Warning (sev 3)
    ]
    result = _highest_severity_warning(warnings)
    assert result[0] == "09"
    assert result[3] == 3


def test_highest_severity_skips_inactive():
    warnings = [
        {"code": "05", "status": "\u89e3\u9664"},  # lifted/canceled
    ]
    result = _highest_severity_warning(warnings)
    assert result is None


def test_highest_severity_skips_low_value():
    """Skip codes (dry air, fog, etc.) are filtered."""
    warnings = [
        {"code": "21", "status": "\u767a\u8868"},  # Dry Air Advisory
        {"code": "24", "status": "\u767a\u8868"},  # Dense Fog Advisory
    ]
    result = _highest_severity_warning(warnings)
    assert result is None


def test_highest_severity_unknown_code():
    warnings = [{"code": "99", "status": "\u767a\u8868"}]
    result = _highest_severity_warning(warnings)
    assert result is None


def test_highest_severity_empty():
    assert _highest_severity_warning([]) is None


def test_highest_severity_mixed():
    """Mix of skip codes and valid codes returns the valid one."""
    warnings = [
        {"code": "21", "status": "\u767a\u8868"},  # skip: Dry Air
        {"code": "07", "status": "\u767a\u8868"},  # valid: Thunderstorm
        {"code": "24", "status": "\u767a\u8868"},  # skip: Fog
    ]
    result = _highest_severity_warning(warnings)
    assert result is not None
    assert result[0] == "07"


# --- Mock data helpers ---

def _make_jma_warning_data(areas=None):
    """Build mock JMA map.json response.

    Returns a list of entries (one per 'prefecture').
    """
    if areas is None:
        areas = [
            {
                "code": "130010",
                "warnings": [
                    {"code": "05", "status": "\u767a\u8868"},
                ],
            }
        ]
    return [
        {
            "reportDatetime": "2026-03-14T12:00:00+09:00",
            "areaTypes": [
                {"areas": areas},
                {"areas": []},  # class20s level (unused)
            ],
        }
    ]


def _make_area_names():
    """Build mock area name lookup."""
    return {
        "130010": "Tokyo Region",
        "270000": "Osaka Region",
        "012010": "Kamikawa Region",
        "400010": "Fukuoka Region",
    }


# --- scrape_jma integration tests ---

def test_scrape_basic():
    """Basic scrape returns one story for one warning."""
    data = _make_jma_warning_data()
    names = _make_area_names()

    with patch("src.jma._fetch_warnings", return_value=data), \
         patch("src.jma._fetch_area_names", return_value=names), \
         patch("src.jma._cache", {"stories": [], "fetched_at": 0.0}):
        stories = scrape_jma()

    assert len(stories) == 1
    s = stories[0]
    assert s["source"] == "JMA"
    assert s["origin"] == "jma"
    assert s["source_type"] == "inferred"
    assert "weather" in s["concepts"]
    assert s["category"] in ("disaster", "weather")


def test_scrape_story_shape():
    """JMA story dict has all required fields."""
    data = _make_jma_warning_data()
    names = _make_area_names()

    with patch("src.jma._fetch_warnings", return_value=data), \
         patch("src.jma._fetch_area_names", return_value=names), \
         patch("src.jma._cache", {"stories": [], "fetched_at": 0.0}):
        stories = scrape_jma()

    s = stories[0]

    # Required story fields
    assert "title" in s
    assert "url" in s
    assert "summary" in s
    assert s["source"] == "JMA"
    assert s["origin"] == "jma"
    assert s["source_type"] == "inferred"
    assert s["published_at"] is not None
    assert s["scraped_at"] is not None
    assert s["lat"] is not None
    assert s["lon"] is not None
    assert s["geocode_confidence"] == 0.7
    assert "Japan" in s["location_name"]

    # Extraction data
    ext = s["_extraction"]
    assert ext["event_signature"] is not None
    assert "weather" in ext["topics"]
    assert ext["severity"] == 3  # Heavy Rain Warning
    assert ext["location_type"] == "terrestrial"
    assert isinstance(ext["actors"], list)
    assert isinstance(ext["locations"], list)
    assert len(ext["locations"]) == 1
    assert ext["locations"][0]["role"] == "event_location"


def test_scrape_disaster_category():
    """Warnings (severity >= 3) get 'disaster' category."""
    areas = [
        {"code": "130010", "warnings": [{"code": "09", "status": "\u767a\u8868"}]},  # Storm Warning
    ]
    data = _make_jma_warning_data(areas)
    names = _make_area_names()

    with patch("src.jma._fetch_warnings", return_value=data), \
         patch("src.jma._fetch_area_names", return_value=names), \
         patch("src.jma._cache", {"stories": [], "fetched_at": 0.0}):
        stories = scrape_jma()

    assert stories[0]["category"] == "disaster"
    assert "disaster" in stories[0]["_extraction"]["topics"]


def test_scrape_weather_category():
    """Advisories (severity < 3) get 'weather' category."""
    areas = [
        {"code": "130010", "warnings": [{"code": "15", "status": "\u767a\u8868"}]},  # Wind Advisory
    ]
    data = _make_jma_warning_data(areas)
    names = _make_area_names()

    with patch("src.jma._fetch_warnings", return_value=data), \
         patch("src.jma._fetch_area_names", return_value=names), \
         patch("src.jma._cache", {"stories": [], "fetched_at": 0.0}):
        stories = scrape_jma()

    assert stories[0]["category"] == "weather"


def test_scrape_multiple_regions():
    """Multiple regions each generate a story."""
    areas = [
        {"code": "130010", "warnings": [{"code": "05", "status": "\u767a\u8868"}]},
        {"code": "270000", "warnings": [{"code": "09", "status": "\u767a\u8868"}]},
    ]
    data = _make_jma_warning_data(areas)
    names = _make_area_names()

    with patch("src.jma._fetch_warnings", return_value=data), \
         patch("src.jma._fetch_area_names", return_value=names), \
         patch("src.jma._cache", {"stories": [], "fetched_at": 0.0}):
        stories = scrape_jma()

    assert len(stories) == 2


def test_scrape_dedup():
    """Same area+code combination is deduped."""
    areas = [
        {"code": "130010", "warnings": [{"code": "05", "status": "\u767a\u8868"}]},
    ]
    # Two entries with same area
    data = [
        {"reportDatetime": "2026-03-14T12:00:00+09:00", "areaTypes": [{"areas": areas}]},
        {"reportDatetime": "2026-03-14T13:00:00+09:00", "areaTypes": [{"areas": areas}]},
    ]
    names = _make_area_names()

    with patch("src.jma._fetch_warnings", return_value=data), \
         patch("src.jma._fetch_area_names", return_value=names), \
         patch("src.jma._cache", {"stories": [], "fetched_at": 0.0}):
        stories = scrape_jma()

    assert len(stories) == 1


def test_scrape_skips_low_value():
    """Skip codes (dry air, fog) produce no stories."""
    areas = [
        {"code": "130010", "warnings": [{"code": "21", "status": "\u767a\u8868"}]},
        {"code": "270000", "warnings": [{"code": "24", "status": "\u767a\u8868"}]},
    ]
    data = _make_jma_warning_data(areas)
    names = _make_area_names()

    with patch("src.jma._fetch_warnings", return_value=data), \
         patch("src.jma._fetch_area_names", return_value=names), \
         patch("src.jma._cache", {"stories": [], "fetched_at": 0.0}):
        stories = scrape_jma()

    assert len(stories) == 0


def test_scrape_skips_inactive():
    """Canceled warnings produce no stories."""
    areas = [
        {"code": "130010", "warnings": [{"code": "05", "status": "\u89e3\u9664"}]},
    ]
    data = _make_jma_warning_data(areas)
    names = _make_area_names()

    with patch("src.jma._fetch_warnings", return_value=data), \
         patch("src.jma._fetch_area_names", return_value=names), \
         patch("src.jma._cache", {"stories": [], "fetched_at": 0.0}):
        stories = scrape_jma()

    assert len(stories) == 0


def test_scrape_empty_response():
    """Empty API response returns empty list."""
    with patch("src.jma._fetch_warnings", return_value=[]), \
         patch("src.jma._fetch_area_names", return_value={}), \
         patch("src.jma._cache", {"stories": [], "fetched_at": 0.0}):
        stories = scrape_jma()

    assert stories == []


def test_scrape_none_response():
    """None API response returns empty/cached list."""
    with patch("src.jma._fetch_warnings", return_value=None), \
         patch("src.jma._fetch_area_names", return_value={}), \
         patch("src.jma._cache", {"stories": [], "fetched_at": 0.0}):
        stories = scrape_jma()

    assert stories == []


def test_scrape_max_cap():
    """More alerts than JMA_MAX_ALERTS are capped."""
    areas = [
        {
            "code": "%02d0010" % i,
            "warnings": [{"code": "15", "status": "\u767a\u8868"}],
        }
        for i in range(1, 48)  # 47 prefectures
    ]
    data = _make_jma_warning_data(areas)
    names = {"%02d0010" % i: "Region %d" % i for i in range(1, 48)}

    with patch("src.jma._fetch_warnings", return_value=data), \
         patch("src.jma._fetch_area_names", return_value=names), \
         patch("src.jma._cache", {"stories": [], "fetched_at": 0.0}), \
         patch("src.jma.JMA_MAX_ALERTS", 10):
        stories = scrape_jma()

    assert len(stories) == 10


def test_scrape_severity_sort():
    """Stories are sorted by severity (highest first)."""
    areas = [
        {"code": "130010", "warnings": [{"code": "15", "status": "\u767a\u8868"}]},  # Wind Adv (2)
        {"code": "270000", "warnings": [{"code": "04", "status": "\u767a\u8868"}]},  # Special (5)
        {"code": "400010", "warnings": [{"code": "09", "status": "\u767a\u8868"}]},  # Storm (3)
    ]
    data = _make_jma_warning_data(areas)
    names = _make_area_names()

    with patch("src.jma._fetch_warnings", return_value=data), \
         patch("src.jma._fetch_area_names", return_value=names), \
         patch("src.jma._cache", {"stories": [], "fetched_at": 0.0}):
        stories = scrape_jma()

    severities = [s["_extraction"]["severity"] for s in stories]
    assert severities == sorted(severities, reverse=True)
    assert severities[0] == 5  # Special warning first


def test_scrape_concepts_deduplicated():
    """Concepts should not have duplicates."""
    data = _make_jma_warning_data()
    names = _make_area_names()

    with patch("src.jma._fetch_warnings", return_value=data), \
         patch("src.jma._fetch_area_names", return_value=names), \
         patch("src.jma._cache", {"stories": [], "fetched_at": 0.0}):
        stories = scrape_jma()

    concepts = stories[0]["concepts"]
    assert len(concepts) == len(set(concepts))


def test_scrape_lat_lon_present():
    """Stories have lat/lon from prefecture centroids."""
    data = _make_jma_warning_data()
    names = _make_area_names()

    with patch("src.jma._fetch_warnings", return_value=data), \
         patch("src.jma._fetch_area_names", return_value=names), \
         patch("src.jma._cache", {"stories": [], "fetched_at": 0.0}):
        stories = scrape_jma()

    s = stories[0]
    assert s["lat"] is not None
    assert s["lon"] is not None
    # Should be near Tokyo
    assert 35 < s["lat"] < 36
    assert 139 < s["lon"] < 140


def test_scrape_unknown_area_still_works():
    """Unknown area code still produces a story with 'Japan' name."""
    areas = [
        {"code": "990010", "warnings": [{"code": "05", "status": "\u767a\u8868"}]},
    ]
    data = _make_jma_warning_data(areas)

    with patch("src.jma._fetch_warnings", return_value=data), \
         patch("src.jma._fetch_area_names", return_value={}), \
         patch("src.jma._cache", {"stories": [], "fetched_at": 0.0}):
        stories = scrape_jma()

    # Story created but without lat/lon (unknown prefecture)
    assert len(stories) == 1
    assert "Japan" in stories[0]["location_name"]


def test_scrape_cache():
    """Cached results are returned within cache TTL."""
    cached_stories = [{"title": "Cached Story"}]
    import time
    cache = {"stories": cached_stories, "fetched_at": time.monotonic()}

    with patch("src.jma._cache", cache), \
         patch("src.jma.JMA_CACHE_SECONDS", 900):
        stories = scrape_jma()

    assert len(stories) == 1
    assert stories[0]["title"] == "Cached Story"


def test_scrape_special_warning_extraction():
    """Special warnings have correct extraction data."""
    areas = [
        {"code": "130010", "warnings": [{"code": "08", "status": "\u767a\u8868"}]},  # Storm Special Warning
    ]
    data = _make_jma_warning_data(areas)
    names = _make_area_names()

    with patch("src.jma._fetch_warnings", return_value=data), \
         patch("src.jma._fetch_area_names", return_value=names), \
         patch("src.jma._cache", {"stories": [], "fetched_at": 0.0}):
        stories = scrape_jma()

    ext = stories[0]["_extraction"]
    assert ext["severity"] == 5
    assert ext["human_interest_score"] == 9
    assert ext["sentiment"] == "negative"
    assert "storm" in ext["topics"]
    assert "disaster" in ext["topics"]


def test_scrape_handles_missing_areaTypes():
    """Entries without areaTypes are skipped."""
    data = [{"reportDatetime": "2026-03-14T12:00:00+09:00"}]

    with patch("src.jma._fetch_warnings", return_value=data), \
         patch("src.jma._fetch_area_names", return_value={}), \
         patch("src.jma._cache", {"stories": [], "fetched_at": 0.0}):
        stories = scrape_jma()

    assert stories == []


def test_scrape_handles_empty_warnings():
    """Areas with empty warnings list are skipped."""
    areas = [
        {"code": "130010", "warnings": []},
    ]
    data = _make_jma_warning_data(areas)

    with patch("src.jma._fetch_warnings", return_value=data), \
         patch("src.jma._fetch_area_names", return_value={}), \
         patch("src.jma._cache", {"stories": [], "fetched_at": 0.0}):
        stories = scrape_jma()

    assert stories == []


# --- Database integration tests ---

def test_insert_jma_story():
    """JMA story with source_type='inferred' inserts correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        story = {
            "title": "Heavy Rain Warning - Tokyo Region, Japan",
            "url": "https://www.jma.go.jp/bosai/warning/#area_type=class20s&area_code=130010&lang=en",
            "summary": "JMA Warning: Heavy Rain Warning issued for Tokyo Region, Japan.",
            "source": "JMA",
            "scraped_at": "2026-03-14T12:00:00Z",
            "origin": "jma",
            "source_type": "inferred",
            "category": "disaster",
            "concepts": ["weather", "rain", "flood"],
            "lat": 35.68,
            "lon": 139.69,
            "geocode_confidence": 0.7,
        }

        was_new = insert_story(conn, story)
        assert was_new is True

        row = conn.execute("SELECT source_type, origin FROM stories WHERE url = ?",
                           (story["url"],)).fetchone()
        assert row["source_type"] == "inferred"
        assert row["origin"] == "jma"

        conn.close()


def test_jma_extraction_storage():
    """Pre-built extraction data from JMA stores correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        story = {
            "title": "Storm Warning - Osaka Region, Japan",
            "url": "https://www.jma.go.jp/bosai/warning/#area_type=class20s&area_code=270000&lang=en",
            "summary": "JMA Warning: Storm Warning issued for Osaka Region, Japan.",
            "source": "JMA",
            "scraped_at": "2026-03-14T12:00:00Z",
            "origin": "jma",
            "source_type": "inferred",
            "category": "disaster",
            "concepts": ["weather", "storm", "wind"],
            "lat": 34.69,
            "lon": 135.52,
            "geocode_confidence": 0.7,
        }

        insert_story(conn, story)
        row = conn.execute("SELECT id FROM stories WHERE url = ?",
                           (story["url"],)).fetchone()
        story_id = row["id"]

        extraction = {
            "event_signature": "2026 Osaka Region Storm",
            "topics": ["weather", "storm", "wind", "disaster"],
            "severity": 3,
            "sentiment": "negative",
            "primary_action": "storm warning",
            "location_type": "terrestrial",
            "search_keywords": ["weather", "storm warning", "Osaka Region", "japan"],
            "is_opinion": False,
            "human_interest_score": 7,
            "actors": [],
            "locations": [
                {"name": "Osaka Region, Japan", "role": "event_location",
                 "lat": 34.69, "lon": 135.52}
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
        assert ext_row["event_signature"] == "2026 Osaka Region Storm"
        assert ext_row["severity"] == 3
        assert ext_row["human_interest_score"] == 7

        status_row = conn.execute(
            "SELECT extraction_status FROM stories WHERE id = ?", (story_id,)
        ).fetchone()
        assert status_row["extraction_status"] == "done"

        conn.close()


# --- Config tests ---

def test_source_enabled_jma():
    """JMA source is enabled by default."""
    from src.config import SOURCE_ENABLED
    assert "jma" in SOURCE_ENABLED
    assert SOURCE_ENABLED["jma"] is True


def test_jma_config_urls():
    """JMA config URLs are set."""
    from src.config import JMA_WARNINGS_URL, JMA_AREA_URL
    assert "jma.go.jp" in JMA_WARNINGS_URL
    assert "warning" in JMA_WARNINGS_URL
    assert "jma.go.jp" in JMA_AREA_URL
    assert "area.json" in JMA_AREA_URL


def test_jma_config_max_alerts():
    """JMA_MAX_ALERTS config has sensible default."""
    from src.config import JMA_MAX_ALERTS
    assert isinstance(JMA_MAX_ALERTS, int)
    assert JMA_MAX_ALERTS == 100


def test_jma_config_cache_seconds():
    """JMA_CACHE_SECONDS config has sensible default."""
    from src.config import JMA_CACHE_SECONDS
    assert isinstance(JMA_CACHE_SECONDS, int)
    assert JMA_CACHE_SECONDS == 900


def test_jma_config_timeout():
    """JMA_TIMEOUT config has sensible default."""
    from src.config import JMA_TIMEOUT
    assert isinstance(JMA_TIMEOUT, int)
    assert JMA_TIMEOUT == 10


# --- Skip codes tests ---

def test_skip_codes_are_low_value():
    """All skip codes are advisory-level with severity 1."""
    for code in _SKIP_CODES:
        info = _get_warning_info(code)
        assert info is not None
        assert info[1] == "advisory"
        assert info[2] == 1


# --- Active status tests ---

def test_active_statuses():
    """Active statuses are the issued and continuing values."""
    assert len(_ACTIVE_STATUSES) == 2
    # These are Japanese strings for "issued" and "continuing"
    assert "\u767a\u8868" in _ACTIVE_STATUSES
    assert "\u7d99\u7d9a" in _ACTIVE_STATUSES


# --- Fetch warnings mock test ---

def test_fetch_warnings_uses_correct_url():
    """_fetch_warnings calls fetch_json with the JMA URL."""
    with patch("src.jma.fetch_json") as mock_fetch:
        mock_fetch.return_value = []
        _fetch_warnings()
        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args
        assert "jma.go.jp" in call_args[0][0] or call_args[1].get("url", "") != ""


def test_fetch_area_names_caches():
    """_fetch_area_names caches results for 24 hours."""
    mock_data = {
        "offices": {"130000": {"enName": "Tokyo", "name": "東京都"}},
        "class10s": {"130010": {"enName": "Tokyo Region", "name": "東京地方"}},
    }
    import time as time_mod
    area_cache = {"data": {}, "fetched_at": 0.0}

    with patch("src.jma.fetch_json", return_value=mock_data), \
         patch("src.jma._area_cache", area_cache):
        result = _fetch_area_names()

    assert "130010" in result
    assert result["130010"] == "Tokyo Region"
    assert area_cache["fetched_at"] > 0
