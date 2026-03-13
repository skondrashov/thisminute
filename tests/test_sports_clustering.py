"""Tests for sports-aware event clustering.

Tests the tournament/competition pattern extraction, sports event detection,
and the sports merge logic in semantic_clusterer.py.
"""

import json
import tempfile
from pathlib import Path

from src.semantic_clusterer import (
    _extract_tournament_key,
    _signature_similarity,
    _signature_words,
    SPORTS_MERGE_THRESHOLD,
)
from src.database import init_db, get_connection


# --- Tournament key extraction tests ---

def test_tournament_key_premier_league():
    assert _extract_tournament_key("2026 Premier League") == "2026 premier league"
    assert _extract_tournament_key("Premier League Week 28") == "premier league"
    assert _extract_tournament_key("2025/26 Premier League") is not None


def test_tournament_key_tennis():
    key = _extract_tournament_key("2026 Indian Wells Tennis")
    assert key is not None
    assert "indian wells" in key


def test_tournament_key_f1():
    key = _extract_tournament_key("2026 F1 Australian GP")
    assert key is not None
    assert "f1" in key.lower() or "formula" in key.lower()
    assert "gp" in key.lower() or "grand prix" in key.lower()


def test_tournament_key_champions_league():
    key = _extract_tournament_key("Champions League Quarterfinals")
    assert key is not None
    assert "champions league" in key


def test_tournament_key_six_nations():
    key = _extract_tournament_key("2026 Six Nations Rugby")
    assert key is not None
    assert "six nations" in key


def test_tournament_key_ipl():
    key = _extract_tournament_key("2026 IPL Cricket Season")
    assert key is not None
    assert "ipl" in key


def test_tournament_key_nfl():
    key = _extract_tournament_key("2026 NFL Free Agency")
    assert key is not None
    assert "nfl" in key.lower()


def test_tournament_key_ufc():
    key = _extract_tournament_key("UFC 315")
    assert key is not None
    assert "ufc" in key.lower()


def test_tournament_key_march_madness():
    key = _extract_tournament_key("2026 March Madness")
    assert key is not None
    assert "march madness" in key


def test_tournament_key_none_for_news():
    """News events should NOT match tournament patterns."""
    assert _extract_tournament_key("Iran Nuclear Talks") is None
    assert _extract_tournament_key("Trump Tariff Escalation") is None
    assert _extract_tournament_key("Gaza Ceasefire Negotiations") is None
    assert _extract_tournament_key("UK Election Campaign") is None


def test_tournament_key_none_for_empty():
    assert _extract_tournament_key("") is None
    assert _extract_tournament_key(None) is None


def test_tournament_key_world_cup():
    key = _extract_tournament_key("2026 World Cup Qualifying")
    assert key is not None
    assert "world cup" in key


def test_tournament_key_tour_de_france():
    key = _extract_tournament_key("Tour de France Stage 12")
    assert key is not None
    assert "tour de france" in key


def test_tournament_key_olympics():
    key = _extract_tournament_key("2028 Olympics Track Events")
    assert key is not None
    assert "olympic" in key.lower()


# --- Signature similarity tests for sports ---

def test_similar_tournament_signatures():
    """Signatures from same tournament should have decent similarity."""
    score = _signature_similarity(
        "2026 Indian Wells Tennis",
        "2026 Indian Wells Semifinals"
    )
    assert score >= SPORTS_MERGE_THRESHOLD, f"Score {score} below threshold {SPORTS_MERGE_THRESHOLD}"


def test_different_tournament_signatures():
    """Signatures from different tournaments should have low similarity."""
    score = _signature_similarity(
        "2026 Indian Wells Tennis",
        "2026 Premier League"
    )
    assert score < SPORTS_MERGE_THRESHOLD, f"Score {score} should be below threshold"


def test_same_league_different_wording():
    """Different wordings of the same league should still share words."""
    words_a = _signature_words("2026 Premier League")
    words_b = _signature_words("Premier League Week 28")
    overlap = words_a & words_b
    assert "premier" in overlap
    assert "league" in overlap


def test_f1_gp_variations():
    """Various F1 GP signature formats should extract tournament keys."""
    sigs = [
        "F1 Australian Grand Prix",
        "2026 F1 Australian GP",
        "Formula 1 Australian Grand Prix",
    ]
    keys = [_extract_tournament_key(s) for s in sigs]
    assert all(k is not None for k in keys), f"Some F1 signatures failed: {list(zip(sigs, keys))}"


# --- Integration test with DB ---

def test_sports_event_detection_with_db():
    """Test that _is_sports_event correctly detects sports events from sources."""
    from src.semantic_clusterer import _is_sports_event

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        # Insert stories from sports sources
        for i, source in enumerate(["ESPN", "BBC Sport", "Sky Sports"]):
            conn.execute(
                """INSERT INTO stories (title, url, source, scraped_at)
                   VALUES (?, ?, ?, datetime('now'))""",
                (f"Sports story {i}", f"https://example.com/sports-{i}", source),
            )
        conn.commit()

        # Create an event and assign the stories
        conn.execute(
            """INSERT INTO events (title, status, story_count, created_at, first_seen, last_updated)
               VALUES ('Test Sports Event', 'active', 3, datetime('now'), datetime('now'), datetime('now'))"""
        )
        event_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        story_ids = [r[0] for r in conn.execute("SELECT id FROM stories").fetchall()]
        for sid in story_ids:
            conn.execute(
                "INSERT INTO event_stories (event_id, story_id, added_at) VALUES (?, ?, datetime('now'))",
                (event_id, sid),
            )
        conn.commit()

        assert _is_sports_event(conn, event_id) is True
        conn.close()


def test_non_sports_event_detection_with_db():
    """Test that news events are NOT detected as sports."""
    from src.semantic_clusterer import _is_sports_event

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        # Insert stories from news sources
        for i, source in enumerate(["BBC World", "CNN", "Al Jazeera"]):
            conn.execute(
                """INSERT INTO stories (title, url, source, scraped_at)
                   VALUES (?, ?, ?, datetime('now'))""",
                (f"News story {i}", f"https://example.com/news-{i}", source),
            )
        conn.commit()

        conn.execute(
            """INSERT INTO events (title, status, story_count, created_at, first_seen, last_updated)
               VALUES ('Test News Event', 'active', 3, datetime('now'), datetime('now'), datetime('now'))"""
        )
        event_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        story_ids = [r[0] for r in conn.execute("SELECT id FROM stories").fetchall()]
        for sid in story_ids:
            conn.execute(
                "INSERT INTO event_stories (event_id, story_id, added_at) VALUES (?, ?, datetime('now'))",
                (event_id, sid),
            )
        conn.commit()

        assert _is_sports_event(conn, event_id) is False
        conn.close()


if __name__ == "__main__":
    tests = [
        test_tournament_key_premier_league,
        test_tournament_key_tennis,
        test_tournament_key_f1,
        test_tournament_key_champions_league,
        test_tournament_key_six_nations,
        test_tournament_key_ipl,
        test_tournament_key_nfl,
        test_tournament_key_ufc,
        test_tournament_key_march_madness,
        test_tournament_key_none_for_news,
        test_tournament_key_none_for_empty,
        test_tournament_key_world_cup,
        test_tournament_key_tour_de_france,
        test_tournament_key_olympics,
        test_similar_tournament_signatures,
        test_different_tournament_signatures,
        test_same_league_different_wording,
        test_f1_gp_variations,
        test_sports_event_detection_with_db,
        test_non_sports_event_detection_with_db,
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
            print(f"  ERROR: {test.__name__}: {e}", flush=True)
            failed += 1
    print(f"\n{passed}/{passed + failed} tests passed", flush=True)
