"""Tests for JMA (Japan Meteorological Agency) weather warnings adapter."""

import pytest
from unittest.mock import patch

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


# --- Warning concepts tests ---

@pytest.mark.parametrize("code,expected_concepts", [
    ("02", ["flood"]),
    ("07", ["thunderstorm"]),
    ("09", ["storm", "wind"]),
    ("12", ["snow"]),
    ("20", ["avalanche"]),
])
def test_concepts(code, expected_concepts):
    concepts = _get_warning_concepts(code)
    for c in expected_concepts:
        assert c in concepts


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


@pytest.mark.parametrize("warnings_data,area_code", [
    ([], None),   # empty response
    (None, None), # none response
])
def test_scrape_empty_or_none_response(warnings_data, area_code):
    """Empty or None API response returns empty list."""
    with patch("src.jma._fetch_warnings", return_value=warnings_data), \
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
