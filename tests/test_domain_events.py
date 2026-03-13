"""Tests for domain event filtering in narrative_analyzer.

Validates that entertainment and positive domain events are correctly
found with the updated multi-signal filtering logic.
"""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from src.database import init_db, get_connection


def _setup_test_db():
    """Create a test database with sample events, stories, and extractions."""
    tmpdir = tempfile.mkdtemp()
    db_path = Path(tmpdir) / "test.db"
    init_db(db_path)
    conn = get_connection(db_path)

    now = datetime.now(timezone.utc).isoformat()

    # --- Create events ---
    events = [
        # Event 1: Academy Awards - mixed sources (entertainment + news)
        (1, "Academy Awards 2026", "The 98th Academy Awards ceremony", "emerging", 23, now, now, now),
        # Event 2: SXSW Festival - mostly entertainment sources
        (2, "SXSW 2026 Festival", "South by Southwest music and film festival", "emerging", 14, now, now, now),
        # Event 3: Broadway Shows - mixed sources
        (3, "Broadway Season 2026", "New Broadway shows and revivals", "emerging", 22, now, now, now),
        # Event 4: A news event (should NOT match entertainment)
        (4, "Iran Nuclear Talks", "Diplomatic negotiations on nuclear deal", "emerging", 45, now, now, now),
        # Event 5: Positive event - high bright_side_score
        (5, "Coral Reef Recovery", "Great Barrier Reef shows recovery signs", "emerging", 8, now, now, now),
        # Event 6: Positive event from positive-tagged source
        (6, "Community Garden Movement", "Urban gardens spreading worldwide", "emerging", 5, now, now, now),
        # Event 7: Sports event (should NOT match entertainment)
        (7, "FIFA World Cup 2026", "World Cup qualifying matches", "emerging", 30, now, now, now),
        # Event 8: Film Reviews - topic signal only (no entertainment sources)
        (8, "Film Review Roundup", "New movie releases and reviews", "emerging", 17, now, now, now),
    ]
    for eid, title, desc, status, count, fs, lu, ca in events:
        conn.execute(
            """INSERT INTO events (id, title, description, status, story_count,
               first_seen, last_updated, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (eid, title, desc, status, count, fs, lu, ca),
        )

    # --- Create stories and link to events ---
    story_id = 0

    # Event 1: Academy Awards - 8 entertainment, 15 news sources = 35% entertainment
    for i in range(8):
        story_id += 1
        _add_story(conn, story_id, 1, "Variety" if i < 4 else "Hollywood Reporter",
                    f"Oscar nominee {i}", now,
                    topics=["oscars", "film", "awards"], bright_side_score=2)
    for i in range(15):
        story_id += 1
        source = ["BBC World", "CNN", "NYT World", "Guardian World", "NPR"][i % 5]
        _add_story(conn, story_id, 1, source,
                    f"Oscar coverage {i}", now,
                    topics=["oscars", "entertainment"], bright_side_score=2)

    # Event 2: SXSW - 10 entertainment, 4 news = 71% entertainment
    for i in range(10):
        story_id += 1
        _add_story(conn, story_id, 2, "Rolling Stone" if i < 5 else "Billboard",
                    f"SXSW music {i}", now,
                    topics=["sxsw", "music", "festival"], bright_side_score=3)
    for i in range(4):
        story_id += 1
        _add_story(conn, story_id, 2, "BBC World",
                    f"SXSW news {i}", now,
                    topics=["sxsw", "festival"], bright_side_score=2)

    # Event 3: Broadway - 5 entertainment, 17 news = 23% entertainment
    for i in range(5):
        story_id += 1
        _add_story(conn, story_id, 3, "Deadline" if i < 3 else "NME",
                    f"Broadway show {i}", now,
                    topics=["broadway", "theater", "entertainment"], bright_side_score=3)
    for i in range(17):
        story_id += 1
        source = ["NYT World", "BBC World", "Guardian World", "CNN"][i % 4]
        _add_story(conn, story_id, 3, source,
                    f"Broadway review {i}", now,
                    topics=["broadway", "theater"], bright_side_score=2)

    # Event 4: Iran Nuclear Talks - all news sources
    for i in range(45):
        story_id += 1
        source = ["BBC World", "CNN", "Al Jazeera", "NYT World", "Guardian World"][i % 5]
        _add_story(conn, story_id, 4, source,
                    f"Iran talks {i}", now,
                    topics=["iran", "nuclear", "diplomacy"], bright_side_score=1)

    # Event 5: Coral Reef Recovery - mixed sources, high bright_side
    for i in range(8):
        story_id += 1
        source = "Good News Network" if i < 3 else ["Guardian Science", "BBC World", "ScienceDaily", "Phys.org", "BBC World"][i - 3]
        _add_story(conn, story_id, 5, source,
                    f"Reef recovery {i}", now,
                    topics=["environment", "reef", "conservation"],
                    bright_side_score=6 if i < 5 else 3)

    # Event 6: Community Garden - all from positive sources
    for i in range(5):
        story_id += 1
        source = ["Good News Network", "Positive News", "Reasons to be Cheerful",
                   "Happy Broadcast", "Vox Future Perfect"][i]
        _add_story(conn, story_id, 6, source,
                    f"Garden story {i}", now,
                    topics=["community", "urban-farming", "sustainability"],
                    bright_side_score=7)

    # Event 7: FIFA World Cup - all sports sources
    for i in range(30):
        story_id += 1
        source = ["BBC Sport", "ESPN", "Sky Sports", "ESPN Soccer", "Guardian Sport", "Sportstar"][i % 6]
        _add_story(conn, story_id, 7, source,
                    f"World Cup {i}", now,
                    topics=["football", "world-cup", "fifa"], bright_side_score=2)

    # Event 8: Film Reviews - NO entertainment sources, but entertainment topics
    for i in range(17):
        story_id += 1
        source = ["BBC World", "NYT World", "Guardian World", "NPR"][i % 4]
        _add_story(conn, story_id, 8, source,
                    f"Film review {i}", now,
                    topics=["film", "movie", "cinema", "box-office"], bright_side_score=2)

    conn.commit()
    return conn, tmpdir


def _add_story(conn, story_id, event_id, source, title, now, topics, bright_side_score):
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
    topics_json = json.dumps(topics)
    conn.execute(
        """INSERT INTO story_extractions (story_id, extraction_json, topics,
           bright_side_score, extracted_at)
           VALUES (?, '{}', ?, ?, ?)""",
        (story_id, topics_json, bright_side_score, now),
    )


def test_entertainment_source_ratio():
    """Entertainment events should be found even with < 50% entertainment sources."""
    conn, tmpdir = _setup_test_db()
    try:
        from src.narrative_analyzer import _get_domain_events
        events = _get_domain_events(conn, "entertainment", limit=50)
        event_ids = {e["id"] for e in events}

        # Event 1: Academy Awards at 35% entertainment sources - should pass with 0.15 threshold
        assert 1 in event_ids, f"Academy Awards (35% ent sources) not found. Got IDs: {event_ids}"

        # Event 2: SXSW at 71% entertainment sources - should definitely pass
        assert 2 in event_ids, f"SXSW (71% ent sources) not found. Got IDs: {event_ids}"

        # Event 3: Broadway at 23% entertainment sources - should pass with 0.15 threshold
        assert 3 in event_ids, f"Broadway (23% ent sources) not found. Got IDs: {event_ids}"

        # Event 4: Iran Nuclear Talks - should NOT be in entertainment
        assert 4 not in event_ids, f"Iran Nuclear Talks incorrectly matched as entertainment"

        # Event 7: FIFA World Cup - should NOT be in entertainment
        assert 7 not in event_ids, f"FIFA World Cup incorrectly matched as entertainment"

        print(f"  Entertainment events found: {len(events)} (IDs: {sorted(event_ids)})")
    finally:
        conn.close()


def test_entertainment_topic_signal():
    """Events with entertainment topics should be found even without entertainment sources."""
    conn, tmpdir = _setup_test_db()
    try:
        from src.narrative_analyzer import _get_domain_events
        events = _get_domain_events(conn, "entertainment", limit=50)
        event_ids = {e["id"] for e in events}

        # Event 8: Film Reviews - 0% entertainment sources, but topics are film/movie/cinema
        assert 8 in event_ids, (
            f"Film Reviews (0% ent sources, film/movie topics) not found via topic signal. "
            f"Got IDs: {event_ids}"
        )

        print(f"  Topic-signal entertainment events: Event 8 correctly found")
    finally:
        conn.close()


def test_positive_bright_side():
    """Positive events should be found via bright_side_score."""
    conn, tmpdir = _setup_test_db()
    try:
        from src.narrative_analyzer import _get_domain_events
        events = _get_domain_events(conn, "positive", limit=50)
        event_ids = {e["id"] for e in events}

        # Event 5: Coral Reef Recovery - 5/8 stories have bright_side >= 3 = 63%
        assert 5 in event_ids, f"Coral Reef Recovery not found as positive. Got IDs: {event_ids}"

        # Event 6: Community Garden - all bright_side >= 7
        assert 6 in event_ids, f"Community Garden not found as positive. Got IDs: {event_ids}"

        # Event 4: Iran Nuclear Talks - all bright_side = 1, should NOT match
        assert 4 not in event_ids, f"Iran Nuclear Talks incorrectly matched as positive"

        print(f"  Positive events found: {len(events)} (IDs: {sorted(event_ids)})")
    finally:
        conn.close()


def test_positive_source_signal():
    """Events from positive-tagged sources should be found."""
    conn, tmpdir = _setup_test_db()
    try:
        from src.narrative_analyzer import _get_positive_events
        events = _get_positive_events(conn, limit=50)
        event_ids = {e["id"] for e in events}

        # Event 6: Community Garden - 100% from positive-tagged sources
        assert 6 in event_ids, f"Community Garden (positive sources) not found. Got IDs: {event_ids}"

        print(f"  Positive source-signal events: Event 6 correctly found")
    finally:
        conn.close()


def test_sports_unchanged():
    """Sports filtering should still work (threshold 0.5)."""
    conn, tmpdir = _setup_test_db()
    try:
        from src.narrative_analyzer import _get_domain_events
        events = _get_domain_events(conn, "sports", limit=50)
        event_ids = {e["id"] for e in events}

        # Event 7: FIFA World Cup - 100% sports sources
        assert 7 in event_ids, f"FIFA World Cup not found in sports. Got IDs: {event_ids}"

        # Entertainment events should NOT appear in sports
        assert 1 not in event_ids, "Academy Awards incorrectly in sports"
        assert 2 not in event_ids, "SXSW incorrectly in sports"

        print(f"  Sports events found: {len(events)} (IDs: {sorted(event_ids)})")
    finally:
        conn.close()


def test_news_unchanged():
    """News filtering should still work at 0.5 threshold."""
    conn, tmpdir = _setup_test_db()
    try:
        from src.narrative_analyzer import _get_domain_events
        events = _get_domain_events(conn, "news", limit=50)
        event_ids = {e["id"] for e in events}

        # Event 4: Iran Nuclear Talks - 100% news sources
        assert 4 in event_ids, f"Iran Nuclear Talks not found in news. Got IDs: {event_ids}"

        # Sports event should NOT appear in news
        assert 7 not in event_ids, "FIFA World Cup incorrectly in news"

        print(f"  News events found: {len(events)} (IDs: {sorted(event_ids)})")
    finally:
        conn.close()


def test_no_junk_entertainment():
    """Entertainment should not include unrelated events just because of loose matching."""
    conn, tmpdir = _setup_test_db()
    try:
        from src.narrative_analyzer import _get_domain_events
        events = _get_domain_events(conn, "entertainment", limit=50)
        event_ids = {e["id"] for e in events}

        # Verify no news-only or sports-only events leaked in
        assert 4 not in event_ids, "Iran Nuclear Talks leaked into entertainment"
        assert 7 not in event_ids, "FIFA World Cup leaked into entertainment"

        print(f"  No junk in entertainment: PASS (only {sorted(event_ids)})")
    finally:
        conn.close()


if __name__ == "__main__":
    tests = [
        test_entertainment_source_ratio,
        test_entertainment_topic_signal,
        test_positive_bright_side,
        test_positive_source_signal,
        test_sports_unchanged,
        test_news_unchanged,
        test_no_junk_entertainment,
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
