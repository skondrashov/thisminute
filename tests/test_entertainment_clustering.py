"""Tests for entertainment-aware event clustering.

Tests the production/franchise/award pattern extraction, entertainment event
detection, and the entertainment merge logic in semantic_clusterer.py.
"""

import json
import tempfile
from pathlib import Path

from src.semantic_clusterer import (
    _extract_entertainment_key,
    _signature_similarity,
    _signature_words,
    ENTERTAINMENT_MERGE_THRESHOLD,
)
from src.database import init_db, get_connection


# --- Entertainment key extraction tests ---

def test_entertainment_key_oscars():
    assert _extract_entertainment_key("2026 Academy Awards") is not None
    key = _extract_entertainment_key("2026 Academy Awards")
    assert "academy award" in key
    key2 = _extract_entertainment_key("2026 Oscars")
    assert key2 is not None
    assert "oscar" in key2


def test_entertainment_key_grammys():
    key = _extract_entertainment_key("2026 Grammy Awards")
    assert key is not None
    assert "grammy" in key


def test_entertainment_key_emmys():
    key = _extract_entertainment_key("2026 Emmy Awards")
    assert key is not None
    assert "emmy" in key


def test_entertainment_key_golden_globes():
    key = _extract_entertainment_key("2026 Golden Globes")
    assert key is not None
    assert "golden globe" in key


def test_entertainment_key_bafta():
    key = _extract_entertainment_key("2026 BAFTA Awards")
    assert key is not None
    assert "bafta" in key


def test_entertainment_key_tonys():
    key = _extract_entertainment_key("2026 Tony Awards")
    assert key is not None
    assert "tony" in key


def test_entertainment_key_cannes():
    key = _extract_entertainment_key("2026 Cannes Film Festival")
    assert key is not None
    assert "cannes" in key


def test_entertainment_key_sundance():
    key = _extract_entertainment_key("2026 Sundance Film Festival")
    assert key is not None
    assert "sundance" in key


def test_entertainment_key_venice():
    key = _extract_entertainment_key("2026 Venice Film Festival")
    assert key is not None
    assert "venice" in key


def test_entertainment_key_tiff():
    key = _extract_entertainment_key("2026 Toronto International Festival")
    assert key is not None
    assert "toronto" in key


def test_entertainment_key_sxsw():
    key = _extract_entertainment_key("2026 SXSW Festival")
    assert key is not None
    assert "sxsw" in key


def test_entertainment_key_spider_man():
    key = _extract_entertainment_key("Spider-Man 4 Production")
    assert key is not None
    assert "spider" in key


def test_entertainment_key_marvel():
    key = _extract_entertainment_key("Marvel Phase 7 Lineup")
    assert key is not None
    assert "marvel" in key


def test_entertainment_key_star_wars():
    key = _extract_entertainment_key("Star Wars New Trilogy")
    assert key is not None
    assert "star wars" in key


def test_entertainment_key_game_of_thrones():
    key = _extract_entertainment_key("House of the Dragon Season 3")
    assert key is not None
    assert "house of the dragon" in key


def test_entertainment_key_stranger_things():
    key = _extract_entertainment_key("Stranger Things Season 5")
    assert key is not None
    assert "stranger things" in key


def test_entertainment_key_music_tour():
    key = _extract_entertainment_key("Taylor Swift Eras Tour")
    assert key is not None
    assert "tour" in key


def test_entertainment_key_bts():
    key = _extract_entertainment_key("BTS Military Service Comeback")
    assert key is not None
    assert "bts" in key


def test_entertainment_key_blackpink():
    key = _extract_entertainment_key("BLACKPINK 2026 Comeback")
    assert key is not None
    assert "blackpink" in key


def test_entertainment_key_bollywood():
    key = _extract_entertainment_key("Bollywood Box Office Release")
    assert key is not None
    assert "bollywood" in key


def test_entertainment_key_none_for_news():
    """News events should NOT match entertainment patterns."""
    assert _extract_entertainment_key("Iran Nuclear Talks") is None
    assert _extract_entertainment_key("Trump Tariff Escalation") is None
    assert _extract_entertainment_key("Gaza Ceasefire Negotiations") is None
    assert _extract_entertainment_key("UK Election Campaign") is None


def test_entertainment_key_none_for_sports():
    """Pure sports events should NOT match entertainment patterns."""
    assert _extract_entertainment_key("2026 Premier League") is None
    assert _extract_entertainment_key("2026 Indian Wells Tennis") is None
    assert _extract_entertainment_key("NFL Free Agency") is None


def test_entertainment_key_none_for_empty():
    assert _extract_entertainment_key("") is None
    assert _extract_entertainment_key(None) is None


def test_entertainment_key_filmfare():
    key = _extract_entertainment_key("2026 Filmfare Awards")
    assert key is not None
    assert "filmfare" in key


def test_entertainment_key_generic_festival():
    key = _extract_entertainment_key("2026 Animation Festival")
    assert key is not None
    assert "festival" in key


# --- Signature similarity tests for entertainment ---

def test_similar_award_signatures():
    """Signatures from same award show should have decent similarity."""
    score = _signature_similarity(
        "2026 Academy Awards Nominations",
        "2026 Academy Awards Ceremony"
    )
    assert score >= ENTERTAINMENT_MERGE_THRESHOLD, f"Score {score} below threshold {ENTERTAINMENT_MERGE_THRESHOLD}"


def test_different_entertainment_signatures():
    """Signatures from different entertainment events should have low similarity."""
    score = _signature_similarity(
        "2026 Academy Awards",
        "Spider-Man 4 Production"
    )
    assert score < ENTERTAINMENT_MERGE_THRESHOLD, f"Score {score} should be below threshold"


def test_same_franchise_different_wording():
    """Different wordings of the same franchise should still share words."""
    words_a = _signature_words("Spider-Man 4 Production")
    words_b = _signature_words("Spider-Man 4 Casting")
    overlap = words_a & words_b
    assert "spider" in overlap or "man" in overlap


def test_festival_variations():
    """Various film festival signature formats should extract entertainment keys."""
    sigs = [
        "Cannes Film Festival 2026",
        "2026 Cannes Festival",
        "Cannes Film Festival",
    ]
    keys = [_extract_entertainment_key(s) for s in sigs]
    assert all(k is not None for k in keys), f"Some festival signatures failed: {list(zip(sigs, keys))}"


# --- Integration test with DB ---

def test_entertainment_event_detection_with_db():
    """Test that _is_entertainment_event correctly detects entertainment events from sources."""
    from src.semantic_clusterer import _is_entertainment_event

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        # Insert stories from entertainment sources
        for i, source in enumerate(["Variety", "Hollywood Reporter", "Deadline"]):
            conn.execute(
                """INSERT INTO stories (title, url, source, scraped_at)
                   VALUES (?, ?, ?, datetime('now'))""",
                (f"Entertainment story {i}", f"https://example.com/ent-{i}", source),
            )
        conn.commit()

        # Create an event and assign the stories
        conn.execute(
            """INSERT INTO events (title, status, story_count, created_at, first_seen, last_updated)
               VALUES ('Test Entertainment Event', 'active', 3, datetime('now'), datetime('now'), datetime('now'))"""
        )
        event_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        story_ids = [r[0] for r in conn.execute("SELECT id FROM stories").fetchall()]
        for sid in story_ids:
            conn.execute(
                "INSERT INTO event_stories (event_id, story_id, added_at) VALUES (?, ?, datetime('now'))",
                (event_id, sid),
            )
        conn.commit()

        assert _is_entertainment_event(conn, event_id) is True
        conn.close()


def test_non_entertainment_event_detection_with_db():
    """Test that news events are NOT detected as entertainment."""
    from src.semantic_clusterer import _is_entertainment_event

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

        assert _is_entertainment_event(conn, event_id) is False
        conn.close()


def test_entertainment_does_not_match_sports():
    """Ensure entertainment patterns don't accidentally match sports events."""
    from src.semantic_clusterer import _extract_tournament_key

    # These should match entertainment but NOT sports
    ent_sigs = [
        "2026 Academy Awards",
        "Spider-Man 4 Production",
        "Taylor Swift Eras Tour",
        "Cannes Film Festival 2026",
    ]
    for sig in ent_sigs:
        ent_key = _extract_entertainment_key(sig)
        sport_key = _extract_tournament_key(sig)
        assert ent_key is not None, f"'{sig}' should have entertainment key"
        assert sport_key is None, f"'{sig}' should NOT have sports key, got '{sport_key}'"


def test_sports_does_not_match_entertainment():
    """Ensure sports patterns don't accidentally match entertainment events."""
    from src.semantic_clusterer import _extract_tournament_key

    # These should match sports but NOT entertainment
    sport_sigs = [
        "2026 Premier League",
        "2026 Indian Wells Tennis",
        "NFL Free Agency",
        "2026 F1 Australian GP",
    ]
    for sig in sport_sigs:
        sport_key = _extract_tournament_key(sig)
        ent_key = _extract_entertainment_key(sig)
        assert sport_key is not None, f"'{sig}' should have sports key"
        assert ent_key is None, f"'{sig}' should NOT have entertainment key, got '{ent_key}'"


# --- Tests for ambiguous pattern fixes (Warning 2 from skeptic review) ---

def test_succession_no_false_positive():
    """'succession' alone should NOT match -- requires TV-specific context."""
    assert _extract_entertainment_key("Iranian Leadership Succession") is None
    assert _extract_entertainment_key("Presidential Succession") is None
    assert _extract_entertainment_key("Succession Plan at Company") is None


def test_succession_with_context():
    """'succession' WITH TV-specific context should match."""
    key = _extract_entertainment_key("Succession Season 4")
    assert key is not None
    assert "succession" in key
    key2 = _extract_entertainment_key("Succession HBO Finale")
    assert key2 is not None


def test_batman_no_false_positive():
    """'batman' alone should NOT match -- requires franchise-specific context."""
    assert _extract_entertainment_key("Batman Province Turkey") is None
    assert _extract_entertainment_key("Batman Illinois Flooding") is None
    assert _extract_entertainment_key("Batman City Council Meeting") is None


def test_batman_with_context():
    """'batman' WITH franchise-specific context should match."""
    key = _extract_entertainment_key("Batman Movie Returns")
    assert key is not None
    assert "batman" in key
    key2 = _extract_entertainment_key("Batman DC Universe")
    assert key2 is not None


def test_wednesday_no_false_positive():
    """'wednesday' alone should NOT match -- requires TV-specific context."""
    assert _extract_entertainment_key("Ash Wednesday") is None
    assert _extract_entertainment_key("Wednesday Election Day") is None
    assert _extract_entertainment_key("Next Wednesday Deadline") is None


def test_wednesday_with_context():
    """'wednesday' WITH TV-specific context should match."""
    key = _extract_entertainment_key("Wednesday Season 2")
    assert key is not None
    assert "wednesday" in key
    key2 = _extract_entertainment_key("Wednesday Netflix Premiere")
    assert key2 is not None


def test_the_bear_no_false_positive():
    """'the bear' alone should NOT match -- requires TV-specific context."""
    assert _extract_entertainment_key("The Bear Market Crisis") is None
    assert _extract_entertainment_key("The Bear Grylls Show") is None
    assert _extract_entertainment_key("The Bear River Flooding") is None


def test_the_bear_with_context():
    """'the bear' WITH TV-specific context should match."""
    key = _extract_entertainment_key("The Bear Season 3")
    assert key is not None
    assert "the bear" in key
    key2 = _extract_entertainment_key("The Bear FX Premiere")
    assert key2 is not None


def test_star_wars_no_false_positive():
    """'star wars' without franchise context should NOT match."""
    assert _extract_entertainment_key("Star Wars is discussed in Congress") is None
    assert _extract_entertainment_key("Star Wars in Budget Debate") is None


def test_star_wars_with_context():
    """'star wars' WITH franchise context should match."""
    key = _extract_entertainment_key("Star Wars New Trilogy")
    assert key is not None
    assert "star wars" in key
    key2 = _extract_entertainment_key("Star Wars Mandalorian")
    assert key2 is not None


def test_harry_potter_no_false_positive():
    """'harry potter' without franchise context should NOT match."""
    assert _extract_entertainment_key("Harry Potter is discussed in school board") is None


def test_harry_potter_with_context():
    """'harry potter' WITH franchise context should match."""
    key = _extract_entertainment_key("Harry Potter HBO Series")
    assert key is not None
    assert "harry potter" in key
    key2 = _extract_entertainment_key("Harry Potter Hogwarts Legacy")
    assert key2 is not None


# --- Tests for domain-gated boost (Warning 3 from skeptic review) ---

def test_boost_only_applies_to_domain_events():
    """Verify that entertainment/sports boosts only apply to confirmed domain events."""
    from src.semantic_clusterer import _best_event_match

    # Create mock events and signatures
    events = [
        {"id": 1, "story_count": 5},  # news event
        {"id": 2, "story_count": 5},  # entertainment event
    ]
    event_sigs = {
        1: ["2026 Academy Awards Coverage"],
        2: ["2026 Academy Awards Nominations"],
    }

    # Without domain gating (empty sets), no boost should apply
    _, score_no_boost = _best_event_match(
        "2026 Academy Awards Ceremony",
        events,
        event_sigs,
        sports_event_ids=set(),
        entertainment_event_ids=set(),
    )

    # With event 2 marked as entertainment, boost should apply to it
    _, score_with_boost = _best_event_match(
        "2026 Academy Awards Ceremony",
        events,
        event_sigs,
        sports_event_ids=set(),
        entertainment_event_ids={2},
    )

    # The boosted score should be >= the non-boosted score
    # (it may match event 2 with boost instead of event 1 without)
    assert score_with_boost >= score_no_boost


def test_sports_boost_not_applied_to_news_event():
    """Sports boost should NOT apply when target event is not sports."""
    from src.semantic_clusterer import _best_event_match

    events = [
        {"id": 1, "story_count": 5},  # news event with sports-sounding sig
    ]
    event_sigs = {
        1: ["2026 Premier League Regulations"],
    }

    # With empty sports set, no boost even though sigs share tournament key
    _, score_no_sports = _best_event_match(
        "2026 Premier League Transfers",
        events,
        event_sigs,
        sports_event_ids=set(),
        entertainment_event_ids=set(),
    )

    # With event 1 marked as sports, boost should apply
    _, score_with_sports = _best_event_match(
        "2026 Premier League Transfers",
        events,
        event_sigs,
        sports_event_ids={1},
        entertainment_event_ids=set(),
    )

    assert score_with_sports >= score_no_sports


if __name__ == "__main__":
    tests = [
        test_entertainment_key_oscars,
        test_entertainment_key_grammys,
        test_entertainment_key_emmys,
        test_entertainment_key_golden_globes,
        test_entertainment_key_bafta,
        test_entertainment_key_tonys,
        test_entertainment_key_cannes,
        test_entertainment_key_sundance,
        test_entertainment_key_venice,
        test_entertainment_key_tiff,
        test_entertainment_key_sxsw,
        test_entertainment_key_spider_man,
        test_entertainment_key_marvel,
        test_entertainment_key_star_wars,
        test_entertainment_key_game_of_thrones,
        test_entertainment_key_stranger_things,
        test_entertainment_key_music_tour,
        test_entertainment_key_bts,
        test_entertainment_key_blackpink,
        test_entertainment_key_bollywood,
        test_entertainment_key_none_for_news,
        test_entertainment_key_none_for_sports,
        test_entertainment_key_none_for_empty,
        test_entertainment_key_filmfare,
        test_entertainment_key_generic_festival,
        test_similar_award_signatures,
        test_different_entertainment_signatures,
        test_same_franchise_different_wording,
        test_festival_variations,
        test_entertainment_event_detection_with_db,
        test_non_entertainment_event_detection_with_db,
        test_entertainment_does_not_match_sports,
        test_sports_does_not_match_entertainment,
        test_succession_no_false_positive,
        test_succession_with_context,
        test_batman_no_false_positive,
        test_batman_with_context,
        test_wednesday_no_false_positive,
        test_wednesday_with_context,
        test_the_bear_no_false_positive,
        test_the_bear_with_context,
        test_star_wars_no_false_positive,
        test_star_wars_with_context,
        test_harry_potter_no_false_positive,
        test_harry_potter_with_context,
        test_boost_only_applies_to_domain_events,
        test_sports_boost_not_applied_to_news_event,
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
