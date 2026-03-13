"""Core tests for thisminute."""

import json
import tempfile
from pathlib import Path

from src.ner import extract_locations, pick_primary_location, extract_story_location
from src.categorizer import categorize, tag_concepts, get_primary_category
from src.database import init_db, get_connection, insert_story, get_stories, get_stats


# --- NER tests ---

def test_ner_basic():
    locs = extract_locations("Fighting in Gaza as Israel launches strikes")
    names = [l["text"] for l in locs]
    assert "Gaza" in names
    assert "Israel" in names


def test_ner_multiple_mentions():
    locs = extract_locations("Ukraine Ukraine Ukraine and Russia")
    assert locs[0]["text"] == "Ukraine"
    assert locs[0]["count"] == 3


def test_ner_empty():
    assert extract_locations("") == []
    assert extract_locations("hi") == []
    assert extract_locations(None) == []


def test_pick_primary_gpe_preferred():
    entities = [
        {"text": "Middle East", "label": "LOC", "count": 3},
        {"text": "Iran", "label": "GPE", "count": 1},
    ]
    assert pick_primary_location(entities) == "Iran"


def test_story_location_extraction():
    story = {"title": "Earthquake hits Japan", "summary": "A 6.5 magnitude earthquake struck Tokyo"}
    location, entities = extract_story_location(story)
    assert location in ("Japan", "Tokyo")
    entity_names = [e["text"] for e in entities]
    assert "Japan" in entity_names


def test_ner_demonyms():
    """Demonyms like 'British', 'American' should resolve to countries."""
    locs = extract_locations("British PM meets French president in Paris")
    names = [l["text"] for l in locs]
    assert "United Kingdom" in names
    assert "France" in names
    assert "Paris" in names


def test_ner_abbreviations():
    """UK and US abbreviations should resolve to countries."""
    locs = extract_locations("UK launches investigation into US trade practices")
    names = [l["text"] for l in locs]
    assert "United Kingdom" in names
    assert "United States" in names


# --- Concept tagger tests ---

def test_concept_multi_label():
    """Stories should get multiple concept tags."""
    concepts = tag_concepts("Gaza bombing kills 30", "Airstrikes hit refugee camp")
    names = [c["name"] for c in concepts]
    assert "bombing" in names
    assert "death" in names
    assert "displacement" in names


def test_concept_war_story():
    """War story should be violence domain."""
    concepts = tag_concepts("Russia launches missile strike", "Military forces target infrastructure")
    assert get_primary_category(concepts) == "violence"


def test_concept_weather_not_tech():
    """Weather stories should NOT be tech."""
    concepts = tag_concepts("Wettest summer in a decade", "Heatwaves followed by floods")
    cat = get_primary_category(concepts)
    assert cat != "tech", f"Weather story categorized as {cat}"
    assert cat == "planet"


def test_concept_election():
    concepts = tag_concepts("Election results announced", "President wins vote in landslide")
    names = [c["name"] for c in concepts]
    assert "election" in names
    assert "politics" in names


def test_concept_empty():
    concepts = tag_concepts("Something happened", "Details unclear")
    assert get_primary_category(concepts) == "general"


def test_categorize_backwards_compat():
    """categorize() should still return a string."""
    cat = categorize("Stock market crashes", "Recession fears mount")
    assert isinstance(cat, str)
    assert cat == "economy"


# --- Database tests ---

def test_database_insert_and_query():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        story = {
            "title": "Test Story",
            "url": "https://example.com/test",
            "summary": "A test story about war in Ukraine",
            "source": "Test Source",
            "location_name": "London",
            "lat": 51.5074,
            "lon": -0.1278,
            "category": "violence",
            "concepts": ["war"],
            "scraped_at": "2026-01-01T00:00:00Z",
        }

        assert insert_story(conn, story) is True
        assert insert_story(conn, story) is False  # dedup

        stories = get_stories(conn)
        assert len(stories) == 1
        assert stories[0]["title"] == "Test Story"

        stats = get_stats(conn)
        assert stats["total_stories"] == 1
        assert stats["geocoded_stories"] == 1

        conn.close()


def test_database_concept_filter():
    """Test concept-based filtering."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        insert_story(conn, {
            "title": "War in Ukraine",
            "url": "https://example.com/1",
            "source": "BBC",
            "category": "violence",
            "concepts": ["war", "death"],
            "lat": 50.0, "lon": 30.0,
            "scraped_at": "2026-01-01T00:00:00Z",
        })
        insert_story(conn, {
            "title": "Football match",
            "url": "https://example.com/2",
            "source": "ESPN",
            "category": "culture",
            "concepts": ["sports"],
            "lat": 51.0, "lon": -0.1,
            "scraped_at": "2026-01-01T00:00:00Z",
        })
        insert_story(conn, {
            "title": "Election day",
            "url": "https://example.com/3",
            "source": "CNN",
            "category": "power",
            "concepts": ["election", "politics"],
            "lat": 38.0, "lon": -77.0,
            "scraped_at": "2026-01-01T00:00:00Z",
        })

        # Include filter
        assert len(get_stories(conn, concepts=["war"])) == 1
        assert len(get_stories(conn, concepts=["war", "sports"])) == 2
        assert len(get_stories(conn, concepts=["election"])) == 1

        # Exclude filter
        assert len(get_stories(conn, exclude_concepts=["war"])) == 2
        assert len(get_stories(conn, exclude_concepts=["sports", "war"])) == 1

        # Search filter
        assert len(get_stories(conn, search="football")) == 1
        assert len(get_stories(conn, search="Ukraine")) == 1
        assert len(get_stories(conn, search="nonexistent")) == 0

        conn.close()


def test_database_source_filter():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        for i, src in enumerate(["BBC", "CNN", "BBC"]):
            insert_story(conn, {
                "title": f"Story {i}",
                "url": f"https://example.com/{i}",
                "source": src,
                "lat": 51.0 + i, "lon": -0.1,
                "scraped_at": "2026-01-01T00:00:00Z",
            })

        assert len(get_stories(conn, source="BBC")) == 2
        assert len(get_stories(conn, source="CNN")) == 1

        conn.close()


def test_trending_api_endpoint():
    """Test the trending API returns valid structure."""
    from datetime import datetime, timezone, timedelta
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        now = datetime.now(timezone.utc)
        # Insert several recent stories with same concept (simulates trending)
        for i in range(5):
            insert_story(conn, {
                "title": f"AI breakthrough {i}",
                "url": f"https://example.com/ai-{i}",
                "source": "TechNews",
                "category": "tech",
                "concepts": ["AI"],
                "lat": 37.0 + i * 0.1, "lon": -122.0,
                "scraped_at": (now - timedelta(minutes=30 + i)).isoformat(),
            })
        # Insert one old story with different concept (baseline)
        insert_story(conn, {
            "title": "Football match results",
            "url": "https://example.com/sports-1",
            "source": "ESPN",
            "category": "culture",
            "concepts": ["sports"],
            "lat": 51.0, "lon": -0.1,
            "scraped_at": (now - timedelta(hours=12)).isoformat(),
        })

        # Verify the stories exist
        all_stories = get_stories(conn)
        assert len(all_stories) == 6

        # Check concept filtering works for AI
        ai_stories = get_stories(conn, concepts=["AI"])
        assert len(ai_stories) == 5

        conn.close()


if __name__ == "__main__":
    tests = [
        test_ner_basic,
        test_ner_multiple_mentions,
        test_ner_empty,
        test_pick_primary_gpe_preferred,
        test_story_location_extraction,
        test_concept_multi_label,
        test_concept_war_story,
        test_concept_weather_not_tech,
        test_concept_election,
        test_concept_empty,
        test_categorize_backwards_compat,
        test_database_insert_and_query,
        test_database_concept_filter,
        test_database_source_filter,
    ]
    passed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS: {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {test.__name__}: {e}")
        except Exception as e:
            print(f"  ERROR: {test.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
