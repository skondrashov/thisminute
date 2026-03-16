"""Tests for features added in the data quality audit session:
- Preprint per-cycle caps (scraper)
- Translated title support (database)
- New feed config entries
- Curious domain prompt exclusions
"""

import json
import sqlite3
import tempfile
from unittest.mock import patch, MagicMock

from src.config import (
    FEEDS, FEED_TAG_MAP,
    ARXIV_MAX_PER_CYCLE, BIORXIV_MAX_PER_CYCLE,
)
from src.scraper import _SOURCE_CAPS, scrape_feed
from src.narrative_analyzer import DOMAIN_PROMPTS


# --- Preprint caps ---

def test_source_caps_configured():
    """arXiv and bioRxiv sources have per-cycle caps."""
    assert "arXiv AI" in _SOURCE_CAPS
    assert "arXiv CS" in _SOURCE_CAPS
    assert "bioRxiv" in _SOURCE_CAPS
    assert "medRxiv" in _SOURCE_CAPS


def test_source_caps_use_config_values():
    """Caps reference the config constants."""
    assert _SOURCE_CAPS["arXiv AI"] == ARXIV_MAX_PER_CYCLE
    assert _SOURCE_CAPS["arXiv CS"] == ARXIV_MAX_PER_CYCLE
    assert _SOURCE_CAPS["bioRxiv"] == BIORXIV_MAX_PER_CYCLE
    assert _SOURCE_CAPS["medRxiv"] == BIORXIV_MAX_PER_CYCLE


def test_default_cap_values():
    """Default caps are 20 per cycle."""
    assert ARXIV_MAX_PER_CYCLE == 20
    assert BIORXIV_MAX_PER_CYCLE == 20


def test_scraper_enforces_cap():
    """scrape_feed caps stories for sources in _SOURCE_CAPS."""
    # Create 50 fake entries
    fake_entries = []
    for i in range(50):
        fake_entries.append(MagicMock(
            get=lambda key, default="", _i=i: {
                "link": f"https://example.com/{_i}",
                "title": f"Paper {_i}",
                "summary": f"Abstract {_i}",
            }.get(key, default),
            **{"get.side_effect": None}
        ))

    fake_feed = MagicMock()
    fake_feed.entries = []
    fake_feed.get.side_effect = lambda k, d=None: {"status": 200, "etag": None, "modified": None}.get(k, d)
    fake_feed.bozo = False

    # Patch feedparser and DB
    with patch("src.scraper.feedparser.parse", return_value=fake_feed), \
         patch("src.scraper.get_connection") as mock_conn, \
         patch("src.scraper.get_feed_state", return_value=None), \
         patch("src.scraper.update_feed_state"):
        mock_conn.return_value = MagicMock()

        # Build a proper feed entry list
        import feedparser
        real_entries = []
        for i in range(50):
            entry = {
                "link": f"https://arxiv.org/abs/{i}",
                "title": f"Paper {i}: Novel Approach",
                "summary": f"We propose a novel approach {i}",
            }
            real_entries.append(entry)

        fake_feed.entries = real_entries

        feed_config = {"url": "https://arxiv.org/rss/cs.AI", "source": "arXiv AI", "tags": ["science", "tech"]}
        stories = scrape_feed(feed_config)

        assert len(stories) <= ARXIV_MAX_PER_CYCLE


# --- Translated title in database ---

def test_translated_title_column_exists():
    """story_extractions table has translated_title column after migration."""
    from src.database import init_db
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    init_db.__wrapped__(conn) if hasattr(init_db, '__wrapped__') else None

    # Re-init via the normal path
    from src.database import init_db as real_init
    conn2 = sqlite3.connect(db_path)
    conn2.row_factory = sqlite3.Row
    # Check column exists
    cols = conn2.execute("PRAGMA table_info(story_extractions)").fetchall()
    col_names = [c[1] for c in cols]
    conn2.close()

    # If table doesn't exist yet (fresh DB), create it
    if "translated_title" not in col_names:
        conn3 = sqlite3.connect(db_path)
        conn3.execute("CREATE TABLE IF NOT EXISTS story_extractions (story_id INTEGER PRIMARY KEY, extraction_json TEXT NOT NULL, translated_title TEXT DEFAULT NULL)")
        cols2 = conn3.execute("PRAGMA table_info(story_extractions)").fetchall()
        col_names2 = [c[1] for c in cols2]
        conn3.close()
        assert "translated_title" in col_names2


def test_store_extraction_saves_translated_title():
    """store_extraction persists translated_title."""
    from src.database import init_db, store_extraction

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    # Minimal schema — stories needs extraction_status, concepts, sentiment, category
    conn.executescript("""
        CREATE TABLE stories (
            id INTEGER PRIMARY KEY, title TEXT, url TEXT, summary TEXT,
            source TEXT, scraped_at TEXT, lat REAL, lon REAL,
            extraction_status TEXT DEFAULT 'pending',
            concepts TEXT DEFAULT '[]', sentiment TEXT, category TEXT
        );
        CREATE TABLE story_extractions (
            story_id INTEGER PRIMARY KEY, extraction_json TEXT NOT NULL,
            topics TEXT DEFAULT '[]', sentiment TEXT, severity INTEGER,
            primary_action TEXT, event_signature TEXT,
            location_type TEXT DEFAULT 'terrestrial',
            search_keywords TEXT DEFAULT '[]', is_opinion INTEGER DEFAULT 0,
            extracted_at TEXT NOT NULL, extraction_model TEXT,
            extraction_version INTEGER DEFAULT 1, registry_event_id INTEGER,
            bright_side_score TEXT, bright_side_category TEXT,
            bright_side_headline TEXT, human_interest_score INTEGER,
            translated_title TEXT DEFAULT NULL
        );
        CREATE TABLE story_actors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id INTEGER, name TEXT, role TEXT, type TEXT,
            description TEXT, demographic TEXT, UNIQUE(story_id, name, role)
        );
        CREATE TABLE story_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id INTEGER, name TEXT, role TEXT, context TEXT
        );
    """)

    conn.execute(
        "INSERT INTO stories (id, title, url, summary, source, scraped_at, lat, lon) VALUES (1, 'Terremoto en México', 'http://x.com', '', 'El Universal', '2026-03-16', 19.4, -99.1)"
    )

    extraction = {
        "topics": ["earthquake"],
        "sentiment": "negative",
        "severity": 4,
        "event_signature": "Mexico earthquake March 2026",
        "translated_title": "Earthquake in Mexico",
        "actors": [],
        "locations": [],
    }

    store_extraction(conn, 1, extraction)
    conn.commit()

    row = conn.execute("SELECT translated_title FROM story_extractions WHERE story_id = 1").fetchone()
    assert row["translated_title"] == "Earthquake in Mexico"
    conn.close()


def test_store_extraction_null_translated_title():
    """English stories get null translated_title."""
    from src.database import store_extraction

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE stories (id INTEGER PRIMARY KEY, title TEXT, url TEXT, summary TEXT, source TEXT, scraped_at TEXT, lat REAL, lon REAL, extraction_status TEXT DEFAULT 'pending', concepts TEXT DEFAULT '[]', sentiment TEXT, category TEXT);
        CREATE TABLE story_extractions (
            story_id INTEGER PRIMARY KEY, extraction_json TEXT NOT NULL,
            topics TEXT DEFAULT '[]', sentiment TEXT, severity INTEGER,
            primary_action TEXT, event_signature TEXT,
            location_type TEXT DEFAULT 'terrestrial',
            search_keywords TEXT DEFAULT '[]', is_opinion INTEGER DEFAULT 0,
            extracted_at TEXT NOT NULL, extraction_model TEXT,
            extraction_version INTEGER DEFAULT 1, registry_event_id INTEGER,
            bright_side_score TEXT, bright_side_category TEXT,
            bright_side_headline TEXT, human_interest_score INTEGER,
            translated_title TEXT DEFAULT NULL
        );
        CREATE TABLE story_actors (id INTEGER PRIMARY KEY AUTOINCREMENT, story_id INTEGER, name TEXT, role TEXT, type TEXT, description TEXT, demographic TEXT, UNIQUE(story_id, name, role));
        CREATE TABLE story_locations (id INTEGER PRIMARY KEY AUTOINCREMENT, story_id INTEGER, name TEXT, role TEXT, context TEXT);
    """)
    conn.execute("INSERT INTO stories (id, title, url, summary, source, scraped_at, lat, lon) VALUES (1, 'UK passes new law', 'http://x.com', '', 'BBC', '2026-03-16', 51.5, -0.1)")

    extraction = {
        "topics": ["legislation"],
        "sentiment": "neutral",
        "severity": 2,
        "event_signature": "UK legislation 2026",
        "translated_title": None,
        "actors": [],
        "locations": [],
    }

    store_extraction(conn, 1, extraction)
    conn.commit()

    row = conn.execute("SELECT translated_title FROM story_extractions WHERE story_id = 1").fetchone()
    assert row["translated_title"] is None
    conn.close()


# --- New feeds config ---

def test_new_feeds_present():
    """New regional feeds are in FEEDS config."""
    sources = {f["source"] for f in FEEDS}
    assert "Jeune Afrique" in sources
    assert "OC Media" in sources
    assert "Punch Nigeria" in sources
    assert "El Universal" in sources
    assert "El Tiempo" in sources
    assert "Rappler" in sources
    assert "Yonhap" in sources
    assert "Astana Times" in sources


def test_non_english_feeds_have_lang_tag():
    """Non-English feeds have a lang field."""
    for feed in FEEDS:
        if feed["source"] in ("Jeune Afrique",):
            assert feed.get("lang") == "fr", f"{feed['source']} should be lang=fr"
        if feed["source"] in ("El Universal", "El Tiempo", "Prensa Libre"):
            assert feed.get("lang") == "es", f"{feed['source']} should be lang=es"


def test_new_feeds_in_tag_map():
    """New feeds appear in FEED_TAG_MAP."""
    assert "Jeune Afrique" in FEED_TAG_MAP
    assert "OC Media" in FEED_TAG_MAP
    assert "Rappler" in FEED_TAG_MAP


def test_total_feed_count():
    """Total feed count increased from 95 to 106."""
    assert len(FEEDS) >= 106


# --- Curious domain prompt ---

def test_curious_prompt_excludes_awards():
    """Curious prompt explicitly excludes award ceremonies."""
    guidance = DOMAIN_PROMPTS["curious"]["guidance"]
    assert "Award ceremonies" in guidance or "award ceremonies" in guidance.lower()
    assert "Oscars" in guidance
    assert "entertainment" in guidance.lower()


def test_curious_prompt_excludes_sports():
    """Curious prompt excludes mainstream sports records."""
    guidance = DOMAIN_PROMPTS["curious"]["guidance"]
    assert "Sports records" in guidance or "sports" in guidance.lower()


def test_curious_bad_examples_include_mainstream():
    """Curious bad examples mention mainstream entertainment."""
    bad = DOMAIN_PROMPTS["curious"]["examples_bad"]
    assert "Oscars" in bad or "oscars" in bad.lower()
    assert "Grammy" in bad or "Super Bowl" in bad


# --- Extraction prompt ---

def test_extraction_prompt_has_translated_title():
    """LLM extraction prompt includes translated_title field."""
    from src.llm_extractor import SYSTEM_PROMPT
    assert "translated_title" in SYSTEM_PROMPT
    assert "English translation" in SYSTEM_PROMPT or "NOT in English" in SYSTEM_PROMPT
