"""Tests for the domain distribution endpoint and database function."""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from src.database import init_db, get_connection, get_domain_distribution


def _setup_test_db():
    """Create a test database with sample stories, extractions, events, and narratives."""
    tmpdir = tempfile.mkdtemp()
    db_path = Path(tmpdir) / "test.db"
    init_db(db_path)
    conn = get_connection(db_path)

    now = datetime.now(timezone.utc).isoformat()

    # --- Stories from various sources ---
    stories = [
        # News sources
        (1, "War update", "https://example.com/1", "BBC World", now, "reported"),
        (2, "Election results", "https://example.com/2", "CNN", now, "reported"),
        (3, "Trade deal", "https://example.com/3", "NYT World", now, "reported"),
        # Sports sources
        (4, "Match result", "https://example.com/4", "BBC Sport", now, "reported"),
        (5, "Transfer news", "https://example.com/5", "ESPN", now, "reported"),
        # Entertainment sources
        (6, "Film premiere", "https://example.com/6", "Variety", now, "reported"),
        (7, "Album release", "https://example.com/7", "Billboard", now, "reported"),
        # Science sources
        (8, "Discovery", "https://example.com/8", "ScienceDaily", now, "reported"),
        # Tech sources
        (9, "AI update", "https://example.com/9", "Ars Technica", now, "reported"),
        # Positive sources
        (10, "Good deed", "https://example.com/10", "Good News Network", now, "reported"),
        # Inferred (structured API) sources -- no feed tag
        (11, "Earthquake", "https://example.com/11", "USGS", now, "inferred"),
        (12, "Weather alert", "https://example.com/12", "NOAA", now, "inferred"),
        # Health source
        (13, "Health update", "https://example.com/13", "BBC Health", now, "reported"),
        # Business source
        (14, "Market news", "https://example.com/14", "BBC Business", now, "reported"),
    ]

    for sid, title, url, source, scraped_at, source_type in stories:
        conn.execute(
            """INSERT INTO stories (id, title, url, source, scraped_at, source_type)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (sid, title, url, source, scraped_at, source_type),
        )

    # --- Extractions with bright_side_score and human_interest_score ---
    extractions = [
        # (story_id, bright_side_score, human_interest_score)
        (1, 1, 2),    # news, low scores
        (2, 2, 3),    # news
        (3, 2, 4),    # news
        (4, 3, 3),    # sports
        (5, 2, 5),    # sports
        (6, 3, 7),    # entertainment, curious proxy (hi >= 6)
        (7, 5, 8),    # entertainment, positive proxy (bs >= 4), curious proxy
        (8, 4, 9),    # science, positive proxy, curious proxy
        (9, 3, 6),    # tech, curious proxy
        (10, 8, 5),   # positive, positive proxy
        (11, 1, 2),   # inferred
        (12, 1, 1),   # inferred
        (13, 3, 4),   # health
        (14, 2, 3),   # business
    ]

    for story_id, bs_score, hi_score in extractions:
        conn.execute(
            """INSERT INTO story_extractions
               (story_id, extraction_json, bright_side_score, human_interest_score, extracted_at)
               VALUES (?, '{}', ?, ?, ?)""",
            (story_id, bs_score, hi_score, now),
        )

    # --- Events with linked stories ---
    conn.execute(
        """INSERT INTO events (id, title, status, story_count, first_seen, last_updated, created_at)
           VALUES (1, 'War Event', 'emerging', 3, ?, ?, ?)""",
        (now, now, now),
    )
    for sid in [1, 2, 3]:
        conn.execute(
            "INSERT INTO event_stories (event_id, story_id, added_at) VALUES (1, ?, ?)",
            (sid, now),
        )

    conn.execute(
        """INSERT INTO events (id, title, status, story_count, first_seen, last_updated, created_at)
           VALUES (2, 'Sports Event', 'emerging', 2, ?, ?, ?)""",
        (now, now, now),
    )
    for sid in [4, 5]:
        conn.execute(
            "INSERT INTO event_stories (event_id, story_id, added_at) VALUES (2, ?, ?)",
            (sid, now),
        )

    conn.execute(
        """INSERT INTO events (id, title, status, story_count, first_seen, last_updated, created_at)
           VALUES (3, 'Mixed Event', 'emerging', 3, ?, ?, ?)""",
        (now, now, now),
    )
    for sid in [6, 8, 10]:
        conn.execute(
            "INSERT INTO event_stories (event_id, story_id, added_at) VALUES (3, ?, ?)",
            (sid, now),
        )

    # --- Narratives with domains ---
    for nid, title, domain in [
        (1, "Global Conflict", "news"),
        (2, "Sports Season", "sports"),
        (3, "Film Awards", "entertainment"),
        (4, "Climate Progress", "positive"),
        (5, "Tech Breakthroughs", "curious"),
    ]:
        conn.execute(
            """INSERT INTO narratives
               (id, title, status, domain, first_seen, last_updated, created_at, last_analyzed)
               VALUES (?, ?, 'active', ?, ?, ?, ?, ?)""",
            (nid, title, domain, now, now, now, now),
        )

    conn.commit()
    return conn, tmpdir


def test_total_stories():
    """Total story count should match inserted stories."""
    conn, tmpdir = _setup_test_db()
    try:
        result = get_domain_distribution(conn, hours=24)
        assert result["total_stories"] == 14, f"Expected 14, got {result['total_stories']}"
    finally:
        conn.close()


def test_by_feed_tag():
    """Feed tag counts should reflect source-to-tag mapping."""
    conn, tmpdir = _setup_test_db()
    try:
        result = get_domain_distribution(conn, hours=24)
        tags = result["by_feed_tag"]
        # BBC World, CNN, NYT World are all "news" tagged
        assert tags.get("news", 0) == 3, f"Expected 3 news, got {tags.get('news', 0)}"
        # BBC Sport, ESPN are "sports" tagged
        assert tags.get("sports", 0) == 2, f"Expected 2 sports, got {tags.get('sports', 0)}"
        # Variety, Billboard are "entertainment" tagged
        assert tags.get("entertainment", 0) == 2, f"Expected 2 entertainment, got {tags.get('entertainment', 0)}"
        # ScienceDaily is "science" tagged
        assert tags.get("science", 0) == 1, f"Expected 1 science, got {tags.get('science', 0)}"
        # Ars Technica is "tech" tagged
        assert tags.get("tech", 0) == 1, f"Expected 1 tech, got {tags.get('tech', 0)}"
        # Good News Network is "positive" tagged
        assert tags.get("positive", 0) == 1, f"Expected 1 positive, got {tags.get('positive', 0)}"
        # BBC Health is "health" tagged
        assert tags.get("health", 0) == 1, f"Expected 1 health, got {tags.get('health', 0)}"
        # BBC Business is "business" tagged
        assert tags.get("business", 0) == 1, f"Expected 1 business, got {tags.get('business', 0)}"
    finally:
        conn.close()


def test_untagged_stories():
    """Stories from sources not in FEED_TAG_MAP should be counted as untagged."""
    conn, tmpdir = _setup_test_db()
    try:
        result = get_domain_distribution(conn, hours=24)
        # USGS and NOAA are not in FEED_TAG_MAP (they are structured APIs)
        assert result["untagged_stories"] == 2, f"Expected 2 untagged, got {result['untagged_stories']}"
    finally:
        conn.close()


def test_by_source_type():
    """Source type breakdown should separate reported from inferred."""
    conn, tmpdir = _setup_test_db()
    try:
        result = get_domain_distribution(conn, hours=24)
        st = result["by_source_type"]
        assert st.get("reported", 0) == 12, f"Expected 12 reported, got {st.get('reported', 0)}"
        assert st.get("inferred", 0) == 2, f"Expected 2 inferred, got {st.get('inferred', 0)}"
    finally:
        conn.close()


def test_positive_proxy():
    """Positive proxy should count stories with bright_side_score >= 4."""
    conn, tmpdir = _setup_test_db()
    try:
        result = get_domain_distribution(conn, hours=24)
        # Stories 7 (bs=5), 8 (bs=4), 10 (bs=8) have bright_side_score >= 4
        assert result["positive_proxy"] == 3, f"Expected 3 positive proxy, got {result['positive_proxy']}"
    finally:
        conn.close()


def test_curious_proxy():
    """Curious proxy should count stories with human_interest_score >= 6."""
    conn, tmpdir = _setup_test_db()
    try:
        result = get_domain_distribution(conn, hours=24)
        # Stories 6 (hi=7), 7 (hi=8), 8 (hi=9), 9 (hi=6) have human_interest >= 6
        assert result["curious_proxy"] == 4, f"Expected 4 curious proxy, got {result['curious_proxy']}"
    finally:
        conn.close()


def test_extracted_stories():
    """Extracted story count should match stories with extractions."""
    conn, tmpdir = _setup_test_db()
    try:
        result = get_domain_distribution(conn, hours=24)
        assert result["extracted_stories"] == 14, f"Expected 14 extracted, got {result['extracted_stories']}"
    finally:
        conn.close()


def test_narratives_by_domain():
    """Narrative domain counts should match active narratives."""
    conn, tmpdir = _setup_test_db()
    try:
        result = get_domain_distribution(conn, hours=24)
        nd = result["narratives_by_domain"]
        assert nd.get("news") == 1
        assert nd.get("sports") == 1
        assert nd.get("entertainment") == 1
        assert nd.get("positive") == 1
        assert nd.get("curious") == 1
    finally:
        conn.close()


def test_events_total_and_tags():
    """Event counts and tag breakdown should be correct."""
    conn, tmpdir = _setup_test_db()
    try:
        result = get_domain_distribution(conn, hours=24)
        assert result["total_events"] == 3, f"Expected 3 events, got {result['total_events']}"
        et = result["events_by_tag"]
        # Event 1 has stories from BBC World, CNN, NYT World -> all "news"
        assert et.get("news", 0) >= 1, "Expected at least 1 news event"
        # Event 2 has stories from BBC Sport, ESPN -> "sports"
        assert et.get("sports", 0) >= 1, "Expected at least 1 sports event"
    finally:
        conn.close()


def test_hours_parameter():
    """The hours parameter should be included in the response."""
    conn, tmpdir = _setup_test_db()
    try:
        result = get_domain_distribution(conn, hours=48)
        assert result["hours"] == 48, f"Expected hours=48, got {result['hours']}"
    finally:
        conn.close()


def test_empty_database():
    """Should return zeroes for an empty database."""
    tmpdir = tempfile.mkdtemp()
    db_path = Path(tmpdir) / "empty.db"
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        result = get_domain_distribution(conn, hours=24)
        assert result["total_stories"] == 0
        assert result["extracted_stories"] == 0
        assert result["positive_proxy"] == 0
        assert result["curious_proxy"] == 0
        assert result["untagged_stories"] == 0
        assert result["total_events"] == 0
        assert result["by_feed_tag"] == {}
        assert result["by_source_type"] == {}
        assert result["narratives_by_domain"] == {}
        assert result["events_by_tag"] == {}
    finally:
        conn.close()
