"""Tests for WHO Disease Outbreak News (DON) adapter."""

import json
from unittest.mock import patch, MagicMock

import pytest

from src.who import (
    scrape_who,
    _parse_country_from_title,
    _extract_disease_concepts,
    _build_event_signature,
    _severity_from_title,
    _human_interest_from_title,
    _fetch_don_rss,
)


def _make_who_item(title="Avian Influenza A(H5N1) - United States of America",
                    url="https://www.who.int/emergencies/disease-outbreak-news/item/2026-DON-001",
                    description="An outbreak of avian influenza A(H5N1) has been reported.",
                    pub_date="2026-03-14T00:00:00Z"):
    """Build a mock WHO DON RSS item."""
    return {
        "title": title,
        "url": url,
        "description": description,
        "pubDate": pub_date,
    }


# --- Country parsing tests ---

def test_parse_country_with_parens():
    assert _parse_country_from_title("Cholera - Haiti (update)") == "Haiti"

def test_parse_country_no_delimiter():
    assert _parse_country_from_title("Global Polio Update") == ""

def test_parse_country_multi_dash():
    """Uses last segment after ' - '."""
    result = _parse_country_from_title("Middle East respiratory syndrome - Saudi Arabia")
    assert result == "Saudi Arabia"


# --- Disease concept tests ---

@pytest.mark.parametrize("title,expected_concept", [
    ("Avian Influenza A(H5N1)", "avian influenza"),
    ("Ebola virus disease - DRC", "ebola"),
    ("Cholera - Haiti", "cholera"),
    ("Mpox - Global update", "mpox"),
])
def test_concepts_parameterized(title, expected_concept):
    concepts = _extract_disease_concepts(title)
    assert expected_concept in concepts


def test_concepts_base_fields():
    """All disease titles include base concepts."""
    concepts = _extract_disease_concepts("Avian Influenza A(H5N1)")
    assert "disease" in concepts
    assert "outbreak" in concepts
    assert "health" in concepts


def test_concepts_generic():
    """Unknown disease still gets base concepts."""
    concepts = _extract_disease_concepts("Novel pathogen - Country X")
    assert "disease" in concepts
    assert "outbreak" in concepts
    assert "health" in concepts


# --- Severity mapping tests ---

@pytest.mark.parametrize("title,expected", [
    ("Ebola - DRC", 4),
    ("Cholera - Haiti", 3),
    ("Avian Influenza A(H5N1)", 3),
    ("Some disease update", 2),
])
def test_severity_parameterized(title, expected):
    assert _severity_from_title(title) == expected


# --- Human interest tests ---

@pytest.mark.parametrize("title,expected", [
    ("Ebola - DRC", 7),
    ("Avian Influenza", 6),
    ("Mpox - update", 5),
    ("Unknown disease", 4),
])
def test_human_interest_parameterized(title, expected):
    assert _human_interest_from_title(title) == expected


# --- Event signature tests ---

def test_event_sig_standard():
    sig = _build_event_signature("Avian Influenza A(H5N1) - United States")
    assert "Avian Influenza" in sig
    assert "United States" in sig

def test_event_sig_empty():
    sig = _build_event_signature("")
    assert "Disease Outbreak" in sig


# --- Dedup tests ---

def test_dedup_same_url():
    items = [
        _make_who_item(url="https://who.int/dup1"),
        _make_who_item(url="https://who.int/dup1"),
    ]
    with patch("src.who._fetch_don_rss", return_value=items):
        stories = scrape_who()
    assert len(stories) == 1


def test_dedup_different_urls():
    items = [
        _make_who_item(url="https://who.int/don1"),
        _make_who_item(url="https://who.int/don2",
                       title="Cholera - Haiti"),
    ]
    with patch("src.who._fetch_don_rss", return_value=items):
        stories = scrape_who()
    assert len(stories) == 2


# --- Story dict shape tests ---

def test_story_dict_shape():
    items = [_make_who_item()]
    with patch("src.who._fetch_don_rss", return_value=items):
        stories = scrape_who()

    assert len(stories) == 1
    s = stories[0]

    # Required story fields
    assert s["title"] == "Avian Influenza A(H5N1) - United States of America"
    assert "who.int" in s["url"]
    assert "avian influenza" in s["summary"].lower()
    assert s["source"] == "WHO"
    assert s["origin"] == "who"
    assert s["source_type"] == "reported"  # NOT inferred
    assert s["category"] == "health"
    assert "disease" in s["concepts"]
    assert "outbreak" in s["concepts"]
    assert "health" in s["concepts"]
    assert s["published_at"] is not None

    # Should have US centroid coordinates
    assert s.get("lat") is not None
    assert s.get("lon") is not None

    # Extraction data
    ext = s["_extraction"]
    assert "event_signature" in ext
    assert isinstance(ext["topics"], list)
    assert ext["severity"] == 3  # avian influenza
    assert ext["location_type"] == "terrestrial"
    assert ext["primary_action"] == "outbreak"
    assert isinstance(ext["actors"], list)
    assert isinstance(ext["locations"], list)
    assert len(ext["locations"]) == 1
    assert ext["locations"][0]["role"] == "event_location"


def test_story_dict_unknown_country():
    """Report with unknown country still works."""
    item = _make_who_item(title="Novel Virus - Atlantis")
    with patch("src.who._fetch_don_rss", return_value=[item]):
        stories = scrape_who()

    assert len(stories) == 1
    s = stories[0]
    assert s["origin"] == "who"
    assert s["location_name"] == "Atlantis"
    assert s.get("lat") is None


# --- Coordinate tests ---

def test_coordinates_from_country():
    """Known country should get centroid coordinates."""
    item = _make_who_item(title="Cholera - Bangladesh")
    with patch("src.who._fetch_don_rss", return_value=[item]):
        stories = scrape_who()
    s = stories[0]
    assert s.get("lat") is not None
    assert s.get("lon") is not None
    assert abs(s["lat"] - 24.0) < 1.0  # Bangladesh centroid


def test_coordinates_no_country():
    """No parseable country means no coordinates."""
    item = _make_who_item(title="Global Situation Update")
    with patch("src.who._fetch_don_rss", return_value=[item]):
        stories = scrape_who()
    s = stories[0]
    assert s.get("lat") is None or "lat" not in s


# --- HTML stripping test ---

def test_html_stripped():
    item = _make_who_item(description="<p>An <b>outbreak</b> of <i>H5N1</i> was reported.</p>")
    with patch("src.who._fetch_don_rss", return_value=[item]):
        stories = scrape_who()
    summary = stories[0]["summary"]
    assert "<p>" not in summary
    assert "<b>" not in summary
    assert "outbreak" in summary


# --- Fetch failure test ---

def test_fetch_failure_returns_empty():
    with patch("src.who._fetch_don_rss", return_value=[]):
        stories = scrape_who()
    assert stories == []
