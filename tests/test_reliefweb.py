"""Tests for ReliefWeb (UN OCHA) humanitarian reports adapter."""

import json
from unittest.mock import patch, MagicMock

import pytest

from src.reliefweb import (
    scrape_reliefweb,
    _extract_concepts,
    _extract_category,
    _extract_country_name,
    _build_event_signature,
    _severity_from_title,
    _human_interest_from_title,
    _fetch_reports,
)


def _make_reliefweb_report(report_id=12345, title="Bangladesh: Floods - Emergency Update",
                            url="https://reliefweb.int/report/bangladesh/floods-update",
                            country="Bangladesh", disaster_name="Bangladesh Floods 2026",
                            body="Heavy monsoon rains have caused widespread flooding."):
    """Build a mock ReliefWeb API report."""
    return {
        "id": report_id,
        "fields": {
            "title": title,
            "url": url,
            "body": body,
            "primary_country": {"name": country},
            "country": [{"name": country}],
            "disaster": [{"name": disaster_name}] if disaster_name else [],
            "date": {"created": "2026-03-14T00:00:00Z"},
            "source": [{"name": "UN OCHA"}],
        },
    }


# --- Concept extraction tests ---

@pytest.mark.parametrize("title,disaster_names,expected", [
    ("Flood situation report", ["Bangladesh Floods"], "flood"),
    ("Earthquake response", ["Turkey Earthquake"], "earthquake"),
    ("Armed conflict update", ["Sudan Conflict"], "conflict"),
    ("IDP displacement report", [], "displacement"),
])
def test_concepts_parameterized(title, disaster_names, expected):
    concepts = _extract_concepts(title, disaster_names)
    assert expected in concepts


def test_concepts_epidemic():
    concepts = _extract_concepts("Cholera outbreak", ["Cholera Epidemic"])
    assert "cholera" in concepts
    assert "epidemic" in concepts


def test_concepts_default():
    """Unknown topics default to 'humanitarian'."""
    concepts = _extract_concepts("General update", [])
    assert "humanitarian" in concepts


# --- Category extraction tests ---

@pytest.mark.parametrize("title,disaster_names,expected", [
    ("Flood update", ["Floods"], "disaster"),
    ("Earthquake", ["Earthquake"], "disaster"),
    ("Cholera outbreak", ["Epidemic"], "health"),
    ("Conflict update", ["Armed Conflict"], "crisis"),
    ("General report", [], "crisis"),
])
def test_category_parameterized(title, disaster_names, expected):
    assert _extract_category(title, disaster_names) == expected


# --- Country extraction tests ---

def test_country_primary_dict():
    report = {"primary_country": {"name": "Bangladesh"}, "country": []}
    assert _extract_country_name(report) == "Bangladesh"

def test_country_from_list():
    report = {"country": [{"name": "Somalia"}]}
    assert _extract_country_name(report) == "Somalia"

def test_country_empty():
    report = {}
    assert _extract_country_name(report) == ""

def test_country_primary_list():
    report = {"primary_country": [{"name": "Yemen"}], "country": []}
    assert _extract_country_name(report) == "Yemen"


# --- Severity mapping tests ---

@pytest.mark.parametrize("title,min_val", [
    ("Emergency response", 4),
    ("Crisis situation update", 4),
    ("Severe flooding", 3),
    ("Situation update", 2),
])
def test_severity_parameterized(title, min_val):
    assert _severity_from_title(title) >= min_val


# --- Human interest tests ---

@pytest.mark.parametrize("title,min_val", [
    ("Emergency crisis", 7),
    ("Flood situation", 5),
    ("General update", 4),
])
def test_human_interest_parameterized(title, min_val):
    assert _human_interest_from_title(title) >= min_val


# --- Event signature tests ---

def test_event_sig_with_disaster():
    sig = _build_event_signature("Flood update", ["Bangladesh Floods 2026"], "Bangladesh")
    assert "Bangladesh Floods 2026" in sig

def test_event_sig_country_fallback():
    sig = _build_event_signature("Update report", [], "Somalia")
    assert "Somalia" in sig

def test_event_sig_title_fallback():
    sig = _build_event_signature("Special report on climate", [], "")
    assert "Special report" in sig


# --- Dedup tests ---

def test_dedup_same_url():
    reports = [
        _make_reliefweb_report(url="https://reliefweb.int/dup1"),
        _make_reliefweb_report(url="https://reliefweb.int/dup1"),
    ]
    with patch("src.reliefweb._fetch_reports", return_value=reports):
        stories = scrape_reliefweb()
    assert len(stories) == 1


def test_dedup_different_urls():
    reports = [
        _make_reliefweb_report(report_id=1, url="https://reliefweb.int/r1"),
        _make_reliefweb_report(report_id=2, url="https://reliefweb.int/r2",
                               title="Somalia: Drought Update"),
    ]
    with patch("src.reliefweb._fetch_reports", return_value=reports):
        stories = scrape_reliefweb()
    assert len(stories) == 2


# --- Story dict shape tests ---

def test_story_dict_shape():
    reports = [_make_reliefweb_report()]
    with patch("src.reliefweb._fetch_reports", return_value=reports):
        stories = scrape_reliefweb()

    assert len(stories) == 1
    s = stories[0]

    # Required story fields
    assert s["title"] == "Bangladesh: Floods - Emergency Update"
    assert s["url"] == "https://reliefweb.int/report/bangladesh/floods-update"
    assert "Heavy monsoon" in s["summary"]
    assert s["source"] == "UN OCHA"
    assert s["origin"] == "reliefweb"
    assert s["source_type"] == "reported"  # NOT inferred
    assert s["category"] in ("disaster", "crisis")
    assert isinstance(s["concepts"], list)
    assert len(s["concepts"]) > 0
    assert s["published_at"] is not None

    # Should have country centroid coordinates
    assert s.get("lat") is not None
    assert s.get("lon") is not None

    # Extraction data
    ext = s["_extraction"]
    assert "event_signature" in ext
    assert isinstance(ext["topics"], list)
    assert ext["location_type"] == "terrestrial"
    assert isinstance(ext["actors"], list)
    assert isinstance(ext["locations"], list)


def test_story_dict_unknown_country():
    """Report for unknown country still produces valid story."""
    report = _make_reliefweb_report(country="Atlantis")
    with patch("src.reliefweb._fetch_reports", return_value=[report]):
        stories = scrape_reliefweb()

    assert len(stories) == 1
    s = stories[0]
    # Should still have a story, just without geo coordinates
    assert s["origin"] == "reliefweb"


# --- HTML stripping test ---

def test_html_stripped_from_body():
    report = _make_reliefweb_report(
        body="<p>Heavy <b>monsoon</b> rains have caused <a href='#'>flooding</a>.</p>"
    )
    with patch("src.reliefweb._fetch_reports", return_value=[report]):
        stories = scrape_reliefweb()
    summary = stories[0]["summary"]
    assert "<p>" not in summary
    assert "<b>" not in summary
    assert "monsoon" in summary


# --- Fetch failure test ---

def test_fetch_failure_returns_empty():
    with patch("src.reliefweb._fetch_reports", return_value=[]):
        stories = scrape_reliefweb()
    assert stories == []
