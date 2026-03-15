"""Tests for sports-aware event clustering.

Tests the tournament/competition pattern extraction, sports event detection,
and the sports merge logic in semantic_clusterer.py.
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.semantic_clusterer import (
    _extract_tournament_key,
    _signature_similarity,
    _signature_words,
    SPORTS_MERGE_THRESHOLD,
)
from src.database import init_db, get_connection


# --- Tournament key extraction tests ---

@pytest.mark.parametrize("title,expected_fragment", [
    ("2026 Premier League", "premier league"),
    ("2026 Indian Wells Tennis", "indian wells"),
    ("Champions League Quarterfinals", "champions league"),
    ("2026 IPL Cricket Season", "ipl"),
    ("UFC 315", "ufc"),
    ("2026 World Cup Qualifying", "world cup"),
    ("Tour de France Stage 12", "tour de france"),
    ("2028 Olympics Track Events", "olympic"),
])
def test_tournament_key_parameterized(title, expected_fragment):
    key = _extract_tournament_key(title)
    assert key is not None
    assert expected_fragment in key.lower()


def test_tournament_key_premier_league_variants():
    assert _extract_tournament_key("2026 Premier League") == "2026 premier league"
    assert _extract_tournament_key("Premier League Week 28") == "premier league"
    assert _extract_tournament_key("2025/26 Premier League") is not None


def test_tournament_key_f1():
    key = _extract_tournament_key("2026 F1 Australian GP")
    assert key is not None
    assert "f1" in key.lower() or "formula" in key.lower()
    assert "gp" in key.lower() or "grand prix" in key.lower()


def test_tournament_key_none_for_news():
    """News events should NOT match tournament patterns."""
    assert _extract_tournament_key("Iran Nuclear Talks") is None
    assert _extract_tournament_key("Trump Tariff Escalation") is None
    assert _extract_tournament_key("Gaza Ceasefire Negotiations") is None
    assert _extract_tournament_key("UK Election Campaign") is None


def test_tournament_key_none_for_empty():
    assert _extract_tournament_key("") is None
    assert _extract_tournament_key(None) is None


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

def test_sports_and_non_sports_event_detection_with_db():
    """Test _is_sports_event detects sports events and rejects news events."""
    from src.semantic_clusterer import _is_sports_event

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        # Insert sports stories
        for i, source in enumerate(["ESPN", "BBC Sport", "Sky Sports"]):
            conn.execute(
                """INSERT INTO stories (title, url, source, scraped_at)
                   VALUES (?, ?, ?, datetime('now'))""",
                (f"Sports story {i}", f"https://example.com/sports-{i}", source),
            )
        conn.commit()

        conn.execute(
            """INSERT INTO events (title, status, story_count, created_at, first_seen, last_updated)
               VALUES ('Test Sports Event', 'active', 3, datetime('now'), datetime('now'), datetime('now'))"""
        )
        sports_event_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        story_ids = [r[0] for r in conn.execute("SELECT id FROM stories").fetchall()]
        for sid in story_ids:
            conn.execute(
                "INSERT INTO event_stories (event_id, story_id, added_at) VALUES (?, ?, datetime('now'))",
                (sports_event_id, sid),
            )
        conn.commit()

        assert _is_sports_event(conn, sports_event_id) is True

        # Insert news stories
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
        news_event_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        news_story_ids = [
            r[0] for r in conn.execute(
                "SELECT id FROM stories WHERE source IN ('BBC World','CNN','Al Jazeera')"
            ).fetchall()
        ]
        for sid in news_story_ids:
            conn.execute(
                "INSERT INTO event_stories (event_id, story_id, added_at) VALUES (?, ?, datetime('now'))",
                (news_event_id, sid),
            )
        conn.commit()

        assert _is_sports_event(conn, news_event_id) is False

        conn.close()


if __name__ == "__main__":
    tests = [
        test_tournament_key_parameterized,
        test_tournament_key_premier_league_variants,
        test_tournament_key_f1,
        test_tournament_key_none_for_news,
        test_tournament_key_none_for_empty,
        test_similar_tournament_signatures,
        test_different_tournament_signatures,
        test_f1_gp_variations,
        test_sports_and_non_sports_event_detection_with_db,
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
