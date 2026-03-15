"""Tests for the curious/human-interest domain in narrative_analyzer.

Validates that:
- _get_curious_events finds events with high human_interest_score
- _get_curious_events excludes events without high human_interest_score
- The curious domain prompt exists and has the right structure
- The scheduler includes "curious" in its domain list
- human_interest_score is properly stored in extraction
"""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from src.database import init_db, get_connection


def _setup_test_db():
    """Create a test database with sample events for curious domain testing."""
    tmpdir = tempfile.mkdtemp()
    db_path = Path(tmpdir) / "test.db"
    init_db(db_path)
    conn = get_connection(db_path)

    now = datetime.now(timezone.utc).isoformat()

    events = [
        # Event 1: Dog elected mayor - high human interest
        (1, "Dog Elected Mayor of Small Town", "A golden retriever wins mayoral election", "emerging", 6, now, now, now),
        # Event 2: New deep-sea species - high human interest
        (2, "New Deep-Sea Species Discovered", "Scientists find bioluminescent creature at 8000m", "emerging", 8, now, now, now),
        # Event 3: Senate budget vote - low human interest
        (3, "Senate Passes Budget Resolution", "Routine fiscal year budget approved", "emerging", 20, now, now, now),
        # Event 4: Man builds rollercoaster - high human interest
        (4, "Man Builds Rollercoaster in Garage", "Retired engineer creates backyard thrill ride", "emerging", 5, now, now, now),
        # Event 5: Quarterly earnings - no human interest scores at all
        (5, "Company Reports Q3 Earnings", "Revenue meets analyst expectations", "emerging", 10, now, now, now),
        # Event 6: Mixed event - some high, some low human interest
        (6, "Unusual Weather Patterns", "Strange weather phenomena across globe", "emerging", 12, now, now, now),
    ]
    for eid, title, desc, status, count, fs, lu, ca in events:
        conn.execute(
            """INSERT INTO events (id, title, description, status, story_count,
               first_seen, last_updated, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (eid, title, desc, status, count, fs, lu, ca),
        )

    story_id = 0

    # Event 1: Dog mayor - all stories have high human_interest_score (7-9)
    for i in range(6):
        story_id += 1
        _add_story(conn, story_id, 1, "BBC World",
                   f"Dog mayor story {i}", now,
                   human_interest_score=8 if i < 4 else 7)

    # Event 2: Deep-sea species - mostly high human_interest (6-8)
    for i in range(8):
        story_id += 1
        _add_story(conn, story_id, 2, "Guardian Science",
                   f"Deep sea creature {i}", now,
                   human_interest_score=7 if i < 5 else 5)

    # Event 3: Senate budget - all low human_interest (1-2)
    for i in range(20):
        story_id += 1
        _add_story(conn, story_id, 3, "CNN",
                   f"Budget vote {i}", now,
                   human_interest_score=2)

    # Event 4: Garage rollercoaster - all high human_interest (8-9)
    for i in range(5):
        story_id += 1
        _add_story(conn, story_id, 4, "NYT World",
                   f"Rollercoaster story {i}", now,
                   human_interest_score=9 if i < 3 else 8)

    # Event 5: Q3 earnings - no human_interest_score (NULL)
    for i in range(10):
        story_id += 1
        _add_story(conn, story_id, 5, "BBC World",
                   f"Earnings report {i}", now,
                   human_interest_score=None)

    # Event 6: Mixed weather - 3/12 stories with score >= 5 = 25%
    for i in range(12):
        story_id += 1
        score = 6 if i < 3 else 3
        _add_story(conn, story_id, 6, "Guardian World",
                   f"Weather story {i}", now,
                   human_interest_score=score)

    conn.commit()
    return conn, tmpdir


def _add_story(conn, story_id, event_id, source, title, now, human_interest_score):
    """Helper to insert a story, event_stories link, and story_extractions."""
    conn.execute(
        """INSERT INTO stories (id, title, url, source, scraped_at)
           VALUES (?, ?, ?, ?, ?)""",
        (story_id, title, f"https://example.com/{story_id}", source, now),
    )
    conn.execute(
        "INSERT INTO event_stories (event_id, story_id, added_at) VALUES (?, ?, ?)",
        (event_id, story_id, now),
    )
    conn.execute(
        """INSERT INTO story_extractions (story_id, extraction_json, topics,
           human_interest_score, extracted_at)
           VALUES (?, '{}', '[]', ?, ?)""",
        (story_id, human_interest_score, now),
    )


def test_curious_finds_high_interest_events():
    """Events with many high human_interest_score stories should be found."""
    conn, tmpdir = _setup_test_db()
    try:
        from src.narrative_analyzer import _get_curious_events
        events = _get_curious_events(conn, limit=50)
        event_ids = {e["id"] for e in events}

        # Event 1: Dog mayor - 100% of stories have score >= 5
        assert 1 in event_ids, f"Dog mayor event (100% hi >= 5) not found. Got IDs: {event_ids}"

        # Event 2: Deep-sea species - 100% of stories have score >= 5
        assert 2 in event_ids, f"Deep-sea species (100% hi >= 5) not found. Got IDs: {event_ids}"

        # Event 4: Garage rollercoaster - 100% have score >= 5
        assert 4 in event_ids, f"Rollercoaster event (100% hi >= 5) not found. Got IDs: {event_ids}"

        print(f"  High-interest events found: {sorted(event_ids)}")
    finally:
        conn.close()


def test_curious_excludes_low_interest_events():
    """Events with low human_interest_score should NOT be found."""
    conn, tmpdir = _setup_test_db()
    try:
        from src.narrative_analyzer import _get_curious_events
        events = _get_curious_events(conn, limit=50)
        event_ids = {e["id"] for e in events}

        # Event 3: Senate budget - 0% have score >= 5
        assert 3 not in event_ids, f"Senate budget (all score 2) incorrectly found as curious"

        print("  Low-interest events correctly excluded")
    finally:
        conn.close()


def test_curious_excludes_null_scores():
    """Events with NULL human_interest_score should NOT be found."""
    conn, tmpdir = _setup_test_db()
    try:
        from src.narrative_analyzer import _get_curious_events
        events = _get_curious_events(conn, limit=50)
        event_ids = {e["id"] for e in events}

        # Event 5: Q3 earnings - all NULL scores
        assert 5 not in event_ids, f"Q3 earnings (all NULL scores) incorrectly found as curious"

        print("  NULL-score events correctly excluded")
    finally:
        conn.close()


def test_curious_mixed_scores_threshold():
    """Events with mixed scores should pass if >= 15% have score >= 5."""
    conn, tmpdir = _setup_test_db()
    try:
        from src.narrative_analyzer import _get_curious_events
        events = _get_curious_events(conn, limit=50)
        event_ids = {e["id"] for e in events}

        # Event 6: Weather - 3/12 = 25% have score >= 5, should pass 15% threshold
        assert 6 in event_ids, f"Mixed weather (25% hi >= 5) not found. Got IDs: {event_ids}"

        print("  Mixed-score event at 25% correctly found")
    finally:
        conn.close()


def test_curious_domain_prompt_exists():
    """The curious domain should have a prompt in DOMAIN_PROMPTS."""
    from src.narrative_analyzer import DOMAIN_PROMPTS

    assert "curious" in DOMAIN_PROMPTS, "Missing 'curious' key in DOMAIN_PROMPTS"

    prompt = DOMAIN_PROMPTS["curious"]
    assert "intro" in prompt, "Missing 'intro' in curious prompt"
    assert "examples_good" in prompt, "Missing 'examples_good' in curious prompt"
    assert "examples_bad" in prompt, "Missing 'examples_bad' in curious prompt"
    assert "guidance" in prompt, "Missing 'guidance' in curious prompt"

    # Verify it's distinct from positive
    assert "you won't believe" in prompt["intro"].lower() or "curiosity" in prompt["intro"].lower(), \
        "Curious prompt intro doesn't emphasize curiosity/engagement"
    assert "human interest stories" in prompt["examples_bad"].lower(), \
        "Curious prompt should flag 'human interest stories' as bad (too vague)"

    print("  Curious domain prompt exists and has correct structure")


def test_curious_domain_config():
    """The curious domain should be properly configured in module-level dicts."""
    from src.narrative_analyzer import DOMAIN_MAX_NARRATIVES, DOMAIN_FEED_TAGS

    assert "curious" in DOMAIN_MAX_NARRATIVES, "Missing 'curious' in DOMAIN_MAX_NARRATIVES"
    assert DOMAIN_MAX_NARRATIVES["curious"] == 10, \
        f"Expected cap 10, got {DOMAIN_MAX_NARRATIVES['curious']}"

    assert "curious" in DOMAIN_FEED_TAGS, "Missing 'curious' in DOMAIN_FEED_TAGS"
    assert DOMAIN_FEED_TAGS["curious"] is None, \
        "curious should use None feed tags (score-based, not source-based)"

    print("  Curious domain config is correct")


def test_scheduler_includes_curious():
    """The scheduler's narrative loop should include 'curious' domain."""
    import inspect
    from src.scheduler import PipelineScheduler

    source = inspect.getsource(PipelineScheduler._narrative_loop)
    assert "curious" in source, \
        "PipelineScheduler._narrative_loop does not include 'curious' domain"

    print("  Scheduler includes 'curious' in domain list")


def test_human_interest_score_in_extraction_prompt():
    """The LLM extraction prompt should include human_interest_score field."""
    from src.llm_extractor import SYSTEM_PROMPT

    assert "human_interest_score" in SYSTEM_PROMPT, \
        "human_interest_score not found in extraction SYSTEM_PROMPT"
    assert "viral" in SYSTEM_PROMPT.lower() or "you won't believe" in SYSTEM_PROMPT.lower(), \
        "Extraction prompt should mention viral/engagement factor for human_interest_score"

    print("  human_interest_score field present in extraction prompt")


def test_human_interest_score_in_extraction_defaults():
    """The extraction parsing should default human_interest_score to None."""
    # Verify the setdefault is present in the extraction flow
    import inspect
    from src.llm_extractor import extract_stories_batch
    source = inspect.getsource(extract_stories_batch)
    assert 'human_interest_score' in source, \
        "extract_stories_batch does not handle human_interest_score"

    print("  human_interest_score handled in extraction defaults")


def test_human_interest_differs_from_bright_side():
    """Verify that human_interest_score and bright_side are conceptually different.

    The extraction prompt should make clear they serve different purposes.
    """
    from src.llm_extractor import SYSTEM_PROMPT

    # The prompt should explicitly state they're different
    assert "different from bright_side" in SYSTEM_PROMPT.lower() or \
           "different from bright side" in SYSTEM_PROMPT.lower(), \
        "Prompt should explicitly state human_interest_score differs from bright_side"

    print("  Prompt explicitly differentiates human_interest from bright_side")


def test_curious_domain_via_get_domain_events():
    """_get_domain_events should route 'curious' domain correctly."""
    conn, tmpdir = _setup_test_db()
    try:
        from src.narrative_analyzer import _get_domain_events
        events = _get_domain_events(conn, "curious", limit=50)
        event_ids = {e["id"] for e in events}

        # Should find high-interest events
        assert 1 in event_ids, f"Dog mayor not found via _get_domain_events('curious'). Got: {event_ids}"
        # Should exclude low-interest events
        assert 3 not in event_ids, f"Senate budget incorrectly found via _get_domain_events('curious')"

        print(f"  _get_domain_events('curious') returns correct events: {sorted(event_ids)}")
    finally:
        conn.close()


def test_database_stores_human_interest_score():
    """Verify that store_extraction persists human_interest_score."""
    tmpdir = tempfile.mkdtemp()
    db_path = Path(tmpdir) / "test_store.db"
    init_db(db_path)
    conn = get_connection(db_path)

    now = datetime.now(timezone.utc).isoformat()

    # Insert a story
    conn.execute(
        "INSERT INTO stories (id, title, url, source, scraped_at) VALUES (1, 'Test', 'http://test.com', 'Test', ?)",
        (now,),
    )
    conn.commit()

    # Store an extraction with human_interest_score
    from src.database import store_extraction
    extraction = {
        "topics": ["test"],
        "sentiment": "neutral",
        "severity": 3,
        "primary_action": "tested",
        "actors": [],
        "locations": [],
        "event_signature": "test event",
        "location_type": "terrestrial",
        "search_keywords": ["test"],
        "is_opinion": False,
        "bright_side": None,
        "human_interest_score": 7,
    }
    store_extraction(conn, 1, extraction)
    conn.commit()

    # Read it back
    row = conn.execute(
        "SELECT human_interest_score FROM story_extractions WHERE story_id = 1"
    ).fetchone()
    assert row is not None, "No extraction stored"
    assert row["human_interest_score"] == 7, \
        f"Expected human_interest_score=7, got {row['human_interest_score']}"

    print("  Database correctly stores and retrieves human_interest_score")
    conn.close()


if __name__ == "__main__":
    tests = [
        test_curious_finds_high_interest_events,
        test_curious_excludes_low_interest_events,
        test_curious_excludes_null_scores,
        test_curious_mixed_scores_threshold,
        test_curious_domain_prompt_exists,
        test_curious_domain_config,
        test_scheduler_includes_curious,
        test_human_interest_score_in_extraction_prompt,
        test_human_interest_score_in_extraction_defaults,
        test_human_interest_differs_from_bright_side,
        test_curious_domain_via_get_domain_events,
        test_database_stores_human_interest_score,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS: {test.__name__}", flush=True)
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {test.__name__}: {e}", flush=True)
            failed += 1
        except Exception as e:
            print(f"  ERROR: {test.__name__}: {type(e).__name__}: {e}", flush=True)
            failed += 1

    print(f"\n{passed}/{len(tests)} tests passed", flush=True)
    if failed:
        exit(1)
