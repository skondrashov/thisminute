"""Tests for US State Department Travel Advisories adapter."""

from unittest.mock import patch

from src.travel_advisories import (
    scrape_travel_advisories,
    _parse_advisory_level,
    _parse_country_from_title,
    _extract_threat_concepts,
    _build_event_signature,
    _fetch_advisory_rss,
    _LEVEL_SEVERITY,
    _LEVEL_HUMAN_INTEREST,
)


def _make_advisory_item(title="Afghanistan - Travel Advisory (Level 4: Do Not Travel)",
                         url="https://travel.state.gov/content/travel/en/traveladvisories/item1.html",
                         description="Do not travel to Afghanistan due to civil unrest, armed conflict, crime, terrorism, and kidnapping.",
                         pub_date="2026-03-14T00:00:00Z"):
    """Build a mock travel advisory RSS item."""
    return {
        "title": title,
        "url": url,
        "description": description,
        "pubDate": pub_date,
    }


# --- Advisory level parsing tests ---

def test_parse_level_4():
    assert _parse_advisory_level("Afghanistan - Travel Advisory (Level 4: Do Not Travel)") == 4

def test_parse_level_3():
    assert _parse_advisory_level("Pakistan - Travel Advisory (Level 3: Reconsider Travel)") == 3

def test_parse_level_2():
    assert _parse_advisory_level("Mexico - Travel Advisory (Level 2: Exercise Increased Caution)") == 2

def test_parse_level_1():
    assert _parse_advisory_level("Canada - Travel Advisory (Level 1: Exercise Normal Precautions)") == 1

def test_parse_level_none():
    assert _parse_advisory_level("Some Random Title") is None

def test_parse_level_empty():
    assert _parse_advisory_level("") is None

def test_parse_level_case_insensitive():
    assert _parse_advisory_level("Country - Travel Advisory (level 3: Reconsider)") == 3


# --- Country name extraction tests ---

def test_parse_country_standard():
    assert _parse_country_from_title("Afghanistan - Travel Advisory (Level 4: Do Not Travel)") == "Afghanistan"

def test_parse_country_multi_word():
    assert _parse_country_from_title("South Sudan - Travel Advisory (Level 4: Do Not Travel)") == "South Sudan"

def test_parse_country_no_dash():
    result = _parse_country_from_title("Mexico Travel Advisory")
    assert result == "Mexico"

def test_parse_country_empty():
    assert _parse_country_from_title("") == ""

def test_parse_country_level_info():
    """Country name should not include level information."""
    result = _parse_country_from_title("Iraq - Travel Advisory (Level 4: Do Not Travel)")
    assert "Level" not in result
    assert result == "Iraq"


# --- Severity mapping tests ---

def test_severity_level_1():
    assert _LEVEL_SEVERITY[1] == 1

def test_severity_level_2():
    assert _LEVEL_SEVERITY[2] == 2

def test_severity_level_3():
    assert _LEVEL_SEVERITY[3] == 3

def test_severity_level_4():
    """Level 4 maps to severity 5, skipping 4."""
    assert _LEVEL_SEVERITY[4] == 5


# --- Human interest mapping tests ---

def test_human_interest_level_1():
    assert _LEVEL_HUMAN_INTEREST[1] == 2

def test_human_interest_level_2():
    assert _LEVEL_HUMAN_INTEREST[2] == 4

def test_human_interest_level_3():
    assert _LEVEL_HUMAN_INTEREST[3] == 6

def test_human_interest_level_4():
    assert _LEVEL_HUMAN_INTEREST[4] == 9


# --- Threat concept extraction tests ---

def test_concepts_terrorism():
    concepts = _extract_threat_concepts("Due to terrorism and conflict")
    assert "travel" in concepts
    assert "safety" in concepts
    assert "terrorism" in concepts
    assert "conflict" in concepts

def test_concepts_crime():
    concepts = _extract_threat_concepts("Due to crime and kidnapping")
    assert "crime" in concepts
    assert "kidnapping" in concepts

def test_concepts_civil_unrest():
    concepts = _extract_threat_concepts("Due to civil unrest")
    assert "civil unrest" in concepts

def test_concepts_base_only():
    """No special keywords still gets base concepts."""
    concepts = _extract_threat_concepts("General advisory for travelers")
    assert "travel" in concepts
    assert "safety" in concepts

def test_concepts_empty():
    concepts = _extract_threat_concepts("")
    assert concepts == ["travel", "safety"]

def test_concepts_deduped():
    """Repeated keywords should not produce duplicate concepts."""
    concepts = _extract_threat_concepts("terrorism and terrorist activities, terrorism warning")
    assert concepts.count("terrorism") == 1


# --- Event signature tests ---

def test_event_sig_standard():
    sig = _build_event_signature("Afghanistan")
    assert "Afghanistan" in sig
    assert "Travel Advisory" in sig

def test_event_sig_empty():
    sig = _build_event_signature("")
    assert "Travel Advisory" in sig

def test_event_sig_has_year():
    sig = _build_event_signature("Iraq")
    # Should contain the current year
    assert "202" in sig  # works for 2020s


# --- Level filtering tests ---

def test_level_1_excluded():
    """Level 1 advisories should be filtered out."""
    items = [_make_advisory_item(
        title="Canada - Travel Advisory (Level 1: Exercise Normal Precautions)",
        url="https://travel.state.gov/canada",
    )]
    with patch("src.travel_advisories._fetch_advisory_rss", return_value=items):
        stories = scrape_travel_advisories()
    assert len(stories) == 0

def test_level_2_included():
    """Level 2 advisories should be included."""
    items = [_make_advisory_item(
        title="Mexico - Travel Advisory (Level 2: Exercise Increased Caution)",
        url="https://travel.state.gov/mexico",
    )]
    with patch("src.travel_advisories._fetch_advisory_rss", return_value=items):
        stories = scrape_travel_advisories()
    assert len(stories) == 1

def test_level_3_included():
    """Level 3 advisories should be included."""
    items = [_make_advisory_item(
        title="Pakistan - Travel Advisory (Level 3: Reconsider Travel)",
        url="https://travel.state.gov/pakistan",
    )]
    with patch("src.travel_advisories._fetch_advisory_rss", return_value=items):
        stories = scrape_travel_advisories()
    assert len(stories) == 1

def test_level_4_included():
    """Level 4 advisories should be included."""
    items = [_make_advisory_item()]
    with patch("src.travel_advisories._fetch_advisory_rss", return_value=items):
        stories = scrape_travel_advisories()
    assert len(stories) == 1

def test_mixed_levels_filtering():
    """Only Level 2+ should survive filtering."""
    items = [
        _make_advisory_item(title="Canada - Travel Advisory (Level 1: Exercise Normal Precautions)", url="https://travel.state.gov/1"),
        _make_advisory_item(title="Mexico - Travel Advisory (Level 2: Exercise Increased Caution)", url="https://travel.state.gov/2"),
        _make_advisory_item(title="Pakistan - Travel Advisory (Level 3: Reconsider Travel)", url="https://travel.state.gov/3"),
        _make_advisory_item(title="Afghanistan - Travel Advisory (Level 4: Do Not Travel)", url="https://travel.state.gov/4"),
    ]
    with patch("src.travel_advisories._fetch_advisory_rss", return_value=items):
        stories = scrape_travel_advisories()
    assert len(stories) == 3


# --- Dedup tests ---

def test_dedup_same_url():
    items = [
        _make_advisory_item(url="https://travel.state.gov/dup1"),
        _make_advisory_item(url="https://travel.state.gov/dup1"),
    ]
    with patch("src.travel_advisories._fetch_advisory_rss", return_value=items):
        stories = scrape_travel_advisories()
    assert len(stories) == 1

def test_dedup_different_urls():
    items = [
        _make_advisory_item(url="https://travel.state.gov/adv1"),
        _make_advisory_item(url="https://travel.state.gov/adv2",
                            title="Iraq - Travel Advisory (Level 4: Do Not Travel)"),
    ]
    with patch("src.travel_advisories._fetch_advisory_rss", return_value=items):
        stories = scrape_travel_advisories()
    assert len(stories) == 2


# --- Story dict shape tests ---

def test_story_dict_shape():
    items = [_make_advisory_item()]
    with patch("src.travel_advisories._fetch_advisory_rss", return_value=items):
        stories = scrape_travel_advisories()

    assert len(stories) == 1
    s = stories[0]

    # Required story fields
    assert "Afghanistan" in s["title"]
    assert "travel.state.gov" in s["url"]
    assert s["source"] == "US State Dept"
    assert s["origin"] == "travel"
    assert s["source_type"] == "inferred"
    assert s["category"] == "politics"
    assert "travel" in s["concepts"]
    assert "safety" in s["concepts"]
    assert s["published_at"] is not None

    # Should have Afghanistan centroid coordinates
    assert s.get("lat") is not None
    assert s.get("lon") is not None

    # Extraction data
    ext = s["_extraction"]
    assert "event_signature" in ext
    assert isinstance(ext["topics"], list)
    assert ext["severity"] == 5  # Level 4 -> severity 5
    assert ext["human_interest_score"] == 9  # Level 4 -> HI 9
    assert ext["location_type"] == "terrestrial"
    assert ext["primary_action"] == "advisory"
    assert ext["sentiment"] == "negative"
    assert isinstance(ext["actors"], list)
    assert isinstance(ext["locations"], list)
    assert len(ext["locations"]) == 1
    assert ext["locations"][0]["role"] == "event_location"


def test_story_dict_level_2_severity():
    """Level 2 advisory should have correct severity and human interest."""
    items = [_make_advisory_item(
        title="Mexico - Travel Advisory (Level 2: Exercise Increased Caution)",
        url="https://travel.state.gov/mexico",
        description="Exercise increased caution in Mexico due to crime.",
    )]
    with patch("src.travel_advisories._fetch_advisory_rss", return_value=items):
        stories = scrape_travel_advisories()

    assert len(stories) == 1
    ext = stories[0]["_extraction"]
    assert ext["severity"] == 2
    assert ext["human_interest_score"] == 4


def test_story_dict_level_3_severity():
    """Level 3 advisory should have correct severity and human interest."""
    items = [_make_advisory_item(
        title="Pakistan - Travel Advisory (Level 3: Reconsider Travel)",
        url="https://travel.state.gov/pakistan",
    )]
    with patch("src.travel_advisories._fetch_advisory_rss", return_value=items):
        stories = scrape_travel_advisories()

    assert len(stories) == 1
    ext = stories[0]["_extraction"]
    assert ext["severity"] == 3
    assert ext["human_interest_score"] == 6


def test_story_unknown_country():
    """Advisory for unknown country still works, just no coordinates."""
    item = _make_advisory_item(
        title="Atlantis - Travel Advisory (Level 3: Reconsider Travel)",
        url="https://travel.state.gov/atlantis",
    )
    with patch("src.travel_advisories._fetch_advisory_rss", return_value=[item]):
        stories = scrape_travel_advisories()

    assert len(stories) == 1
    s = stories[0]
    assert s["origin"] == "travel"
    assert s["location_name"] == "Atlantis"
    assert s.get("lat") is None


# --- Geocoding tests ---

def test_coordinates_from_country():
    """Known country should get centroid coordinates."""
    item = _make_advisory_item(
        title="Iraq - Travel Advisory (Level 4: Do Not Travel)",
        url="https://travel.state.gov/iraq",
    )
    with patch("src.travel_advisories._fetch_advisory_rss", return_value=[item]):
        stories = scrape_travel_advisories()
    s = stories[0]
    assert s.get("lat") is not None
    assert s.get("lon") is not None
    assert abs(s["lat"] - 33.0) < 1.0  # Iraq centroid


def test_coordinates_afghanistan():
    """Afghanistan should get centroid coordinates."""
    items = [_make_advisory_item()]
    with patch("src.travel_advisories._fetch_advisory_rss", return_value=items):
        stories = scrape_travel_advisories()
    s = stories[0]
    assert s.get("lat") is not None
    assert abs(s["lat"] - 33.0) < 1.0  # Afghanistan centroid


# --- HTML stripping test ---

def test_html_stripped():
    item = _make_advisory_item(description="<p>Do <b>not</b> travel due to <i>terrorism</i>.</p>")
    with patch("src.travel_advisories._fetch_advisory_rss", return_value=[item]):
        stories = scrape_travel_advisories()
    summary = stories[0]["summary"]
    assert "<p>" not in summary
    assert "<b>" not in summary
    assert "terrorism" in summary


# --- Fetch failure test ---

def test_fetch_failure_returns_empty():
    with patch("src.travel_advisories._fetch_advisory_rss", return_value=[]):
        stories = scrape_travel_advisories()
    assert stories == []


# --- Config integration tests ---

def test_travel_config_url():
    from src.config import TRAVEL_ADVISORY_URL
    assert "travel.state.gov" in TRAVEL_ADVISORY_URL

def test_source_enabled_includes_travel():
    from src.config import SOURCE_ENABLED
    assert "travel" in SOURCE_ENABLED
    assert SOURCE_ENABLED["travel"] is True


# --- Database integration tests ---

def test_story_insertable():
    """Story dict should be compatible with database.insert_story()."""
    items = [_make_advisory_item()]
    with patch("src.travel_advisories._fetch_advisory_rss", return_value=items):
        stories = scrape_travel_advisories()

    s = stories[0]
    # Must have all fields expected by insert_story
    assert "title" in s
    assert "url" in s
    assert "summary" in s
    assert "source" in s
    assert "origin" in s
    assert "source_type" in s
    assert "category" in s
    assert "concepts" in s
    assert "scraped_at" in s
    assert "_extraction" in s


def test_extraction_dict_shape():
    """Extraction dict should have all 11 required keys."""
    items = [_make_advisory_item()]
    with patch("src.travel_advisories._fetch_advisory_rss", return_value=items):
        stories = scrape_travel_advisories()

    ext = stories[0]["_extraction"]
    required_keys = [
        "event_signature", "topics", "severity", "sentiment",
        "primary_action", "location_type", "search_keywords",
        "is_opinion", "human_interest_score", "actors", "locations",
    ]
    for key in required_keys:
        assert key in ext, "Missing key: %s" % key


# --- Edge case tests ---

def test_no_title_skipped():
    """Items with no title should be skipped."""
    items = [_make_advisory_item(title="")]
    with patch("src.travel_advisories._fetch_advisory_rss", return_value=items):
        stories = scrape_travel_advisories()
    assert len(stories) == 0

def test_no_url_skipped():
    """Items with no URL should be skipped."""
    items = [_make_advisory_item(url="")]
    with patch("src.travel_advisories._fetch_advisory_rss", return_value=items):
        stories = scrape_travel_advisories()
    assert len(stories) == 0

def test_unparseable_level_defaults_to_2():
    """If level cannot be parsed, default to Level 2 (included)."""
    items = [_make_advisory_item(
        title="Somewhere - Travel Advisory",
        url="https://travel.state.gov/somewhere",
        description="Exercise caution due to crime.",
    )]
    with patch("src.travel_advisories._fetch_advisory_rss", return_value=items):
        stories = scrape_travel_advisories()
    assert len(stories) == 1
    assert stories[0]["_extraction"]["severity"] == 2


def test_summary_fallback_no_description():
    """If no description, summary should be derived from title."""
    items = [_make_advisory_item(
        title="Syria - Travel Advisory (Level 4: Do Not Travel)",
        url="https://travel.state.gov/syria",
        description="",
    )]
    with patch("src.travel_advisories._fetch_advisory_rss", return_value=items):
        stories = scrape_travel_advisories()
    assert len(stories) == 1
    assert "Syria" in stories[0]["summary"] or "Do Not Travel" in stories[0]["summary"]
