"""Tests for Meteoalarm European severe weather alerts adapter."""

import time
import pytest
from unittest.mock import patch

from src.meteoalarm import (
    scrape_meteoalarm,
    _parse_awareness_level,
    _parse_awareness_type,
    _get_severity,
    _get_human_interest,
    _get_event_concepts,
    _get_english_info,
    _build_title,
    _build_summary,
    _build_event_signature,
    _extract_location_name,
    _build_url,
    _parse_warning,
    _fetch_country_warnings,
    _cache,
)
from src.country_centroids import get_centroid


# --- Helper to build mock warnings ---

def _make_warning(uuid="abc-123",
                  identifier="2.49.0.0.276.0.DE.20260314.001",
                  event="Yellow Wind Warning",
                  headline="Yellow Wind Warning for Germany - Bavaria",
                  severity="Moderate",
                  awareness_level="2; yellow; Moderate",
                  awareness_type="1; Wind",
                  area_desc="Bavaria",
                  language="en-GB",
                  description="Strong winds expected in Bavaria.",
                  onset="2026-03-14T06:00:00+01:00",
                  web="https://meteoalarm.org/en/live/region/DE"):
    """Build a mock Meteoalarm warning dict."""
    return {
        "uuid": uuid,
        "alert": {
            "identifier": identifier,
            "status": "Actual",
            "msgType": "Alert",
            "scope": "Public",
            "sender": "dwd@dwd.de",
            "sent": "2026-03-14T05:00:00+01:00",
            "info": [
                {
                    "language": language,
                    "category": ["Met"],
                    "event": event,
                    "headline": headline,
                    "description": description,
                    "severity": severity,
                    "urgency": "Immediate",
                    "certainty": "Likely",
                    "onset": onset,
                    "effective": onset,
                    "expires": "2026-03-15T06:00:00+01:00",
                    "web": web,
                    "area": [
                        {
                            "areaDesc": area_desc,
                            "geocode": [
                                {"valueName": "EMMA_ID", "value": "DE009"}
                            ],
                        }
                    ],
                    "parameter": [
                        {"valueName": "awareness_level", "value": awareness_level},
                        {"valueName": "awareness_type", "value": awareness_type},
                    ],
                }
            ],
        },
    }


# --- Awareness level parsing tests ---

@pytest.mark.parametrize("value,expected", [
    ("2; yellow; Moderate", "2"),
    ("4; red; Extreme", "4"),
])
def test_parse_awareness_level(value, expected):
    params = [{"valueName": "awareness_level", "value": value}]
    assert _parse_awareness_level(params) == expected


def test_parse_awareness_level_missing():
    assert _parse_awareness_level([]) is None
    assert _parse_awareness_level(None) is None


def test_parse_awareness_level_no_match():
    params = [{"valueName": "other_param", "value": "something"}]
    assert _parse_awareness_level(params) is None


# --- Awareness type parsing tests ---

@pytest.mark.parametrize("value,expected", [
    ("1; Wind", "1"),
    ("8; Flood", "8"),
])
def test_parse_awareness_type(value, expected):
    params = [{"valueName": "awareness_type", "value": value}]
    assert _parse_awareness_type(params) == expected


def test_parse_awareness_type_missing():
    assert _parse_awareness_type([]) is None
    assert _parse_awareness_type(None) is None


# --- Severity mapping tests ---

@pytest.mark.parametrize("sev_str,level,expected", [
    ("Moderate", "2", 2),
    ("Severe",   "3", 3),
    ("Extreme",  "4", 4),
])
def test_severity_from_awareness_level(sev_str, level, expected):
    assert _get_severity({"severity": sev_str}, level) == expected


def test_severity_fallback():
    """When no awareness_level, falls back to severity string."""
    assert _get_severity({"severity": "Severe"}, None) == 3


def test_severity_unknown():
    assert _get_severity({"severity": "Unknown"}, None) == 2


# --- Human interest score tests ---

@pytest.mark.parametrize("sev_str,level,expected", [
    ("Moderate", "2", 4),
    ("Extreme",  "4", 9),
])
def test_hi_from_awareness_level(sev_str, level, expected):
    assert _get_human_interest({"severity": sev_str}, level) == expected


def test_hi_fallback():
    assert _get_human_interest({"severity": "Severe"}, None) == 7


# --- Event concepts tests ---

def test_concepts_wind():
    concepts = _get_event_concepts("1", "Wind Warning")
    assert "wind" in concepts
    assert "storm" in concepts


def test_concepts_flood():
    concepts = _get_event_concepts("8", "Flood Warning")
    assert "flood" in concepts


def test_concepts_snow():
    concepts = _get_event_concepts("2", "Snow/Ice Warning")
    assert "snow" in concepts


def test_concepts_heat():
    concepts = _get_event_concepts("5", "Heat Warning")
    assert "heat wave" in concepts


def test_concepts_thunderstorm():
    concepts = _get_event_concepts("3", "Thunderstorm Warning")
    assert "thunderstorm" in concepts


def test_concepts_fallback_text():
    """When no awareness_type match, falls back to event text."""
    concepts = _get_event_concepts(None, "Tornado Warning")
    assert "tornado" in concepts


def test_concepts_unknown():
    """Unknown type and text returns empty list."""
    concepts = _get_event_concepts(None, "Special Statement")
    assert concepts == []


# --- English info selection tests ---

def test_get_english_info():
    info_list = [
        {"language": "de-DE", "event": "Windwarnung"},
        {"language": "en-GB", "event": "Wind Warning"},
        {"language": "fr", "event": "Avertissement de vent"},
    ]
    result = _get_english_info(info_list)
    assert result["event"] == "Wind Warning"


def test_get_english_info_fallback():
    """Falls back to first info if no English."""
    info_list = [
        {"language": "de-DE", "event": "Windwarnung"},
        {"language": "fr", "event": "Avertissement de vent"},
    ]
    result = _get_english_info(info_list)
    assert result["event"] == "Windwarnung"


def test_get_english_info_empty():
    assert _get_english_info([]) is None
    assert _get_english_info(None) is None


# --- Title builder tests ---

def test_title_from_headline():
    info = {"headline": "Yellow Wind Warning for Germany - Bavaria"}
    assert _build_title(info, "germany") == "Yellow Wind Warning for Germany - Bavaria"


def test_title_from_event_and_area():
    info = {"event": "Flood Warning", "area": [{"areaDesc": "Rheinland-Pfalz"}]}
    title = _build_title(info, "germany")
    assert "Flood Warning" in title
    assert "Rheinland-Pfalz" in title


def test_title_fallback_country():
    info = {"event": "Storm Warning", "area": []}
    title = _build_title(info, "germany")
    assert "Storm Warning" in title
    assert "Germany" in title


# --- Summary builder tests ---

def test_summary_from_description():
    info = {"description": "Strong winds expected across Bavaria."}
    summary = _build_summary(info)
    assert "Strong winds" in summary


def test_summary_truncated():
    info = {"description": "X" * 600}
    summary = _build_summary(info)
    assert len(summary) <= 500


def test_summary_fallback():
    info = {"event": "Heat Warning", "severity": "Severe"}
    summary = _build_summary(info)
    assert "Heat Warning" in summary


# --- Event signature tests ---

def test_event_signature_wind():
    info = {
        "event": "Yellow Wind Warning",
        "area": [{"areaDesc": "Bavaria"}],
    }
    sig = _build_event_signature(info, "germany")
    assert "Wind" in sig
    assert "Bavaria" in sig


def test_event_signature_strips_color():
    info = {
        "event": "Red Thunderstorm Warning",
        "area": [{"areaDesc": "Lombardy"}],
    }
    sig = _build_event_signature(info, "italy")
    assert "Thunderstorm" in sig
    assert "Red" not in sig


def test_event_signature_strips_warning():
    info = {
        "event": "Orange Flood Warning",
        "area": [],
    }
    sig = _build_event_signature(info, "france")
    assert "Flood" in sig
    assert "Warning" not in sig


# --- Location name tests ---

def test_location_name_from_area():
    info = {"area": [{"areaDesc": "Nordrhein-Westfalen"}]}
    assert _extract_location_name(info, "germany") == "Nordrhein-Westfalen"


def test_location_name_fallback():
    info = {"area": []}
    assert _extract_location_name(info, "united-kingdom") == "United Kingdom"


# --- URL builder tests ---

def test_url_from_web():
    info = {"web": "https://meteoalarm.org/en/live/region/DE"}
    assert _build_url(info, "test-id") == "https://meteoalarm.org/en/live/region/DE"


def test_url_fallback():
    info = {}
    url = _build_url(info, "2.49.0.0.276.0.DE.20260314.001")
    assert "meteoalarm.org" in url
    assert "2.49.0.0.276.0.DE.20260314.001" in url


# --- Green alert filtering ---

def test_green_alerts_filtered():
    """Green/minor alerts (awareness level 1) are skipped."""
    warning = _make_warning(awareness_level="1; green; Minor")
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    result = _parse_warning(warning, "germany", now)
    assert result is None


# --- Country centroids ---

def test_centroids_exist_for_default_countries():
    """All default countries should have centroids via country_centroids."""
    from src.config import METEOALARM_COUNTRIES
    for country in METEOALARM_COUNTRIES:
        centroid = get_centroid(country.replace("-", " "))
        assert centroid is not None, "Missing centroid for %s" % country


# --- Story dict shape tests ---

def test_story_dict_shape():
    """Meteoalarm story dict has all required fields."""
    warning = _make_warning()
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    story = _parse_warning(warning, "germany", now)

    assert story is not None
    assert story["title"] == "Yellow Wind Warning for Germany - Bavaria"
    assert "meteoalarm.org" in story["url"]
    assert "wind" in story["summary"].lower() or "Strong" in story["summary"]
    assert story["source"] == "Meteoalarm"
    assert story["origin"] == "meteoalarm"
    assert story["source_type"] == "inferred"
    assert story["category"] in ("disaster", "weather")
    assert "weather" in story["concepts"]
    assert story["lat"] is not None
    assert story["lon"] is not None
    assert story["geocode_confidence"] == 0.6
    assert story["published_at"] is not None

    # Extraction data
    ext = story["_extraction"]
    assert "Wind" in ext["event_signature"]
    assert "weather" in ext["topics"]
    assert ext["severity"] == 2  # Yellow/Moderate
    assert ext["location_type"] == "terrestrial"
    assert ext["human_interest_score"] == 4
    assert isinstance(ext["actors"], list)
    assert isinstance(ext["locations"], list)
    assert len(ext["locations"]) == 1
    assert ext["locations"][0]["role"] == "event_location"


# --- Dedup tests ---

def test_dedup_same_uuid():
    """Same UUID should be deduped."""
    warnings = [
        _make_warning(uuid="dup-1", identifier="id-a"),
        _make_warning(uuid="dup-1", identifier="id-b"),
    ]
    with patch("src.meteoalarm._fetch_country_warnings", return_value=warnings):
        with patch("src.meteoalarm.METEOALARM_COUNTRIES", ["germany"]):
            _cache["stories"] = []
            _cache["fetched_at"] = 0.0
            stories = scrape_meteoalarm()
    assert len(stories) == 1


# --- Max alerts cap tests ---

def test_max_alerts_caps_volume():
    """Alerts exceeding METEOALARM_MAX_ALERTS should be capped."""
    warnings = [
        _make_warning(
            uuid="uuid-%d" % i,
            identifier="id-%d" % i,
            headline="Alert %d" % i,
            awareness_level="2; yellow; Moderate",
        )
        for i in range(50)
    ]
    with patch("src.meteoalarm._fetch_country_warnings", return_value=warnings):
        with patch("src.meteoalarm.METEOALARM_COUNTRIES", ["germany"]):
            with patch("src.meteoalarm.METEOALARM_MAX_ALERTS", 20):
                _cache["stories"] = []
                _cache["fetched_at"] = 0.0
                stories = scrape_meteoalarm()
    assert len(stories) == 20


def test_max_alerts_prioritizes_severe():
    """When capped, severe alerts should be kept over moderate ones."""
    warnings = []
    # 3 red/extreme alerts
    for i in range(3):
        warnings.append(_make_warning(
            uuid="ext-%d" % i,
            identifier="ext-id-%d" % i,
            headline="Extreme Alert %d" % i,
            awareness_level="4; red; Extreme",
            severity="Extreme",
        ))
    # 5 yellow/moderate alerts
    for i in range(5):
        warnings.append(_make_warning(
            uuid="mod-%d" % i,
            identifier="mod-id-%d" % i,
            headline="Moderate Alert %d" % i,
            awareness_level="2; yellow; Moderate",
            severity="Moderate",
        ))

    with patch("src.meteoalarm._fetch_country_warnings", return_value=warnings):
        with patch("src.meteoalarm.METEOALARM_COUNTRIES", ["germany"]):
            with patch("src.meteoalarm.METEOALARM_MAX_ALERTS", 5):
                _cache["stories"] = []
                _cache["fetched_at"] = 0.0
                stories = scrape_meteoalarm()

    assert len(stories) == 5
    # All 3 extreme alerts should be present
    extreme_count = sum(1 for s in stories if s["_extraction"]["severity"] == 4)
    assert extreme_count == 3


# --- Cache tests ---

def test_cache_returns_cached():
    """Cached results should be returned without fetching."""
    import time
    _cache["stories"] = [{"title": "Cached"}]
    _cache["fetched_at"] = time.monotonic()  # just now
    with patch("src.meteoalarm._fetch_country_warnings") as mock_fetch:
        stories = scrape_meteoalarm()
    mock_fetch.assert_not_called()
    assert len(stories) == 1
    assert stories[0]["title"] == "Cached"
    # Clean up
    _cache["stories"] = []
    _cache["fetched_at"] = 0.0


def test_cache_expired():
    """Expired cache should trigger new fetch."""
    _cache["stories"] = [{"title": "Old"}]
    _cache["fetched_at"] = time.monotonic() - 1000  # always expired
    warnings = [_make_warning()]
    with patch("src.meteoalarm._fetch_country_warnings", return_value=warnings):
        with patch("src.meteoalarm.METEOALARM_COUNTRIES", ["germany"]):
            stories = scrape_meteoalarm()
    assert len(stories) >= 1
    assert stories[0]["title"] != "Old"
    # Clean up
    _cache["stories"] = []
    _cache["fetched_at"] = 0.0


# --- Time budget tests ---

def test_per_request_timeout():
    """_fetch_country_warnings passes per-request timeout."""
    with patch("src.meteoalarm.fetch_json", return_value=[]) as mock_fj:
        _fetch_country_warnings("germany", timeout=5)
    mock_fj.assert_called_once()
    assert mock_fj.call_args[1]["timeout"] == 5


def test_time_budget_stops_fetching():
    """When time budget is exhausted, remaining countries are skipped."""
    import time as time_mod

    call_count = [0]
    original_monotonic = time_mod.monotonic

    def slow_fetch(country, timeout=None):
        call_count[0] += 1
        return [_make_warning(uuid="uuid-%s" % country)]

    # Simulate time passing: each call to monotonic advances by 20s
    mono_calls = [0]
    start_time = original_monotonic()

    def fake_monotonic():
        mono_calls[0] += 1
        # First call is budget_start, then each loop iteration checks budget
        # Make it so after 3 countries, budget (60s) is exceeded
        return start_time + (mono_calls[0] * 20)

    with patch("src.meteoalarm._fetch_country_warnings", side_effect=slow_fetch):
        with patch("src.meteoalarm.METEOALARM_COUNTRIES",
                   ["germany", "france", "italy", "spain", "poland"]):
            with patch("src.meteoalarm.METEOALARM_TOTAL_BUDGET", 60):
                with patch("src.meteoalarm.time.monotonic", side_effect=fake_monotonic):
                    _cache["stories"] = []
                    _cache["fetched_at"] = 0.0
                    stories = scrape_meteoalarm()

    # Should have fetched fewer than 5 countries due to budget
    assert call_count[0] < 5
    # But should have some stories from the countries that were fetched
    assert len(stories) > 0
    # Clean up
    _cache["stories"] = []
    _cache["fetched_at"] = 0.0


def test_scrape_uses_meteoalarm_timeout_config():
    """scrape_meteoalarm passes METEOALARM_TIMEOUT to _fetch_country_warnings."""
    with patch("src.meteoalarm._fetch_country_warnings",
               return_value=[]) as mock_fetch:
        with patch("src.meteoalarm.METEOALARM_COUNTRIES", ["germany"]):
            with patch("src.meteoalarm.METEOALARM_TIMEOUT", 7):
                _cache["stories"] = []
                _cache["fetched_at"] = 0.0
                scrape_meteoalarm()

    mock_fetch.assert_called_once_with("germany", timeout=7)
    # Clean up
    _cache["stories"] = []
    _cache["fetched_at"] = 0.0


