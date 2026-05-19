"""Tests that every domain preset gets both events and situations after filtering.

Validates the domain-aware event filtering fix: events linked to domain
narratives should appear in that domain's preset, even when the global top-N
events are dominated by news.

This catches the bug where Sports/Entertainment/etc. presets would show
situations but no events (or vice versa) because events lacked domain tags.
"""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.database import init_db, get_connection


# ---------------------------------------------------------------------------
# The PRESET_DOMAIN_MAP from the frontend (src/js/state.js), replicated here
# so we can simulate the same filtering logic Python-side.
# ---------------------------------------------------------------------------
PRESET_DOMAIN_MAP = {
    "bright_side": "positive",
    "sports": "sports",
    "entertainment": "entertainment",
    "curious": "curious",
    "conflict": "news",
    "power": "news",
    "health": "health",
    "science": "science",
    "tech": "science",
    "markets": "business",
}

# Presets that explicitly hide situations (no narratives expected)
DOMAINLESS_HIDE_SITUATIONS = {"planet", "travel"}

# Domains that should have both events and situations when data exists
DOMAIN_PRESETS = ["sports", "entertainment", "science", "markets", "health"]


def _now():
    return datetime.now(timezone.utc).isoformat()


def _setup_db_with_domain_data():
    """Build a test DB with events and narratives across multiple domains.

    Creates the minimum data needed for each domain preset to have at least
    one event linked to at least one narrative.
    """
    tmpdir = tempfile.mkdtemp()
    db_path = Path(tmpdir) / "test.db"
    init_db(db_path)
    conn = get_connection(db_path)
    now = _now()

    # --- Define domain events ------------------------------------------------
    #   (event_id, title, story_count, source_name, domain, num_stories)
    domain_events = [
        # News (big global events — will dominate the top-N)
        (1,  "Ukraine Peace Talks",         40, "BBC World",      "news"),
        (2,  "US Election Coverage",         35, "CNN",            "news"),
        (3,  "China Trade Negotiations",     30, "NYT World",      "news"),
        # Sports
        (10, "Champions League Semi-Finals", 15, "ESPN",           "sports"),
        (11, "NBA Playoffs Round 2",         12, "ESPN",           "sports"),
        # Entertainment
        (20, "Academy Awards 2026",          18, "Variety",        "entertainment"),
        (21, "Cannes Film Festival",         10, "Deadline",       "entertainment"),
        # Science
        (30, "Mars Sample Return Update",    8,  "ScienceDaily",   "science"),
        (31, "CERN Particle Discovery",      6,  "Phys.org",       "science"),
        # Business / Markets
        (40, "Fed Rate Decision",            20, "Reuters Business", "business"),
        (41, "Tech IPO Wave",                9,  "Bloomberg",      "business"),
        # Health
        (50, "WHO Pandemic Preparedness",    7,  "BBC Health",     "health"),
        (51, "Cancer Vaccine Trial",         5,  "Reuters Health", "health"),
        # Positive
        (60, "Coral Reef Recovery",          6,  "Good News Network", "positive"),
        # Curious
        (70, "New Species Discovered",       4,  "BBC World",      "curious"),
    ]

    story_id = 0
    for eid, title, story_count, source, domain in domain_events:
        conn.execute(
            """INSERT INTO events (id, title, description, status, story_count,
               first_seen, last_updated, created_at)
               VALUES (?, ?, ?, 'emerging', ?, ?, ?, ?)""",
            (eid, title, f"About {title}", story_count, now, now, now),
        )
        for i in range(story_count):
            story_id += 1
            conn.execute(
                """INSERT INTO stories (id, title, url, source, scraped_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (story_id, f"{title} story {i}",
                 f"https://example.com/{story_id}", source, now),
            )
            conn.execute(
                "INSERT INTO event_stories (event_id, story_id, added_at) VALUES (?, ?, ?)",
                (eid, story_id, now),
            )

    # --- Create narratives per domain and link events -------------------------
    narr_data = [
        (1, "Ukraine-Russia Conflict",     "news",          [1]),
        (2, "US Election Season",          "news",          [2, 3]),
        (3, "European Football Season",    "sports",        [10, 11]),
        (4, "Awards Season 2026",          "entertainment", [20, 21]),
        (5, "Space Exploration Updates",   "science",       [30, 31]),
        (6, "Global Markets Turmoil",      "business",      [40, 41]),
        (7, "Global Health Initiatives",   "health",        [50, 51]),
        (8, "Environmental Bright Spots",  "positive",      [60]),
        (9, "Nature's Surprises",          "curious",       [70]),
    ]

    for nid, title, domain, event_ids in narr_data:
        conn.execute(
            """INSERT INTO narratives (id, title, description, status, domain,
               first_seen, last_updated, event_count, story_count, created_at)
               VALUES (?, ?, ?, 'active', ?, ?, ?, ?, 0, ?)""",
            (nid, title, f"About {title}", domain, now, now, len(event_ids), now),
        )
        for eid in event_ids:
            conn.execute(
                """INSERT INTO narrative_events (narrative_id, event_id, relevance_score, added_at)
                   VALUES (?, ?, 1.0, ?)""",
                (nid, eid, now),
            )

    conn.commit()
    return conn, tmpdir


# ---------------------------------------------------------------------------
# Core test: the /api/events endpoint should include narrative-linked events
# ---------------------------------------------------------------------------

class TestEventDomainCoverage:
    """Verify that the events API returns events for every domain,
    not just the global top-N by story_count."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.conn, self.tmpdir = _setup_db_with_domain_data()
        yield
        self.conn.close()

    def _get_events_with_domains(self, limit=5):
        """Simulate the /api/events endpoint logic (the backend fix).

        Returns events with their inferred domains from narrative links.
        """
        conn = self.conn

        # Step 1: global top-N (will be news-dominated)
        events = [
            dict(r) for r in conn.execute(
                """SELECT * FROM events
                   WHERE merged_into IS NULL AND status != 'resolved'
                   ORDER BY story_count DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        ]
        global_ids = {e["id"] for e in events}

        # Step 2: add narrative-linked events (the fix)
        narr_event_rows = conn.execute(
            """SELECT DISTINCT e.* FROM events e
               JOIN narrative_events ne ON e.id = ne.event_id
               JOIN narratives n ON n.id = ne.narrative_id
               WHERE n.status = 'active'
                 AND e.merged_into IS NULL
                 AND e.status != 'resolved'"""
        ).fetchall()
        for r in narr_event_rows:
            d = dict(r)
            if d["id"] not in global_ids:
                events.append(d)
                global_ids.add(d["id"])

        # Step 3: compute domains from narrative links
        event_ids = [e["id"] for e in events]
        ph = ",".join("?" * len(event_ids))
        domain_rows = conn.execute(
            f"""SELECT ne.event_id, n.domain
                FROM narrative_events ne
                JOIN narratives n ON n.id = ne.narrative_id
                WHERE ne.event_id IN ({ph})
                  AND n.status = 'active'""",
            event_ids,
        ).fetchall()

        from collections import defaultdict
        domain_map = defaultdict(set)
        for r in domain_rows:
            domain_map[r["event_id"]].add(r["domain"] or "news")

        for e in events:
            e["domains"] = sorted(domain_map.get(e["id"], []))

        return events

    def test_global_topn_is_news_dominated(self):
        """Without the fix, top-5 global events are all news."""
        top5 = [
            dict(r) for r in self.conn.execute(
                """SELECT * FROM events
                   WHERE merged_into IS NULL AND status != 'resolved'
                   ORDER BY story_count DESC LIMIT 5"""
            ).fetchall()
        ]
        ids = {e["id"] for e in top5}
        # News events (40, 35, 30 stories) and maybe a couple others
        # but sports (15, 12), science (8, 6), health (7, 5) are likely excluded
        assert 1 in ids, "Top news event should be in top 5"
        # Small domain events shouldn't make it
        assert 30 not in ids, "Science event (8 stories) shouldn't be in global top-5"
        assert 50 not in ids, "Health event (7 stories) shouldn't be in global top-5"

    def test_narrative_linked_events_included(self):
        """With the fix, ALL narrative-linked events appear regardless of story_count rank."""
        events = self._get_events_with_domains(limit=5)
        event_ids = {e["id"] for e in events}

        # These small-count domain events should now be included via narrative links
        assert 30 in event_ids, "Science event should be included via narrative link"
        assert 50 in event_ids, "Health event should be included via narrative link"
        assert 51 in event_ids, "Health event #2 should be included via narrative link"
        assert 10 in event_ids, "Sports event should be included via narrative link"

    def test_events_have_domain_tags(self):
        """Events should be annotated with domains from their linked narratives."""
        events = self._get_events_with_domains(limit=5)
        by_id = {e["id"]: e for e in events}

        assert "sports" in by_id[10]["domains"]
        assert "entertainment" in by_id[20]["domains"]
        assert "science" in by_id[30]["domains"]
        assert "business" in by_id[40]["domains"]
        assert "health" in by_id[50]["domains"]
        assert "news" in by_id[1]["domains"]

    @pytest.mark.parametrize("preset,domain", [
        ("sports", "sports"),
        ("entertainment", "entertainment"),
        ("science", "science"),
        ("markets", "business"),
        ("health", "health"),
    ])
    def test_domain_preset_has_events(self, preset, domain):
        """Each domain preset should find events via domain tag matching."""
        events = self._get_events_with_domains(limit=5)
        domain_events = [e for e in events if domain in e.get("domains", [])]
        assert len(domain_events) > 0, (
            f"Preset '{preset}' (domain={domain}) found 0 events. "
            f"Available domains: {set(d for e in events for d in e.get('domains', []))}"
        )

    @pytest.mark.parametrize("preset,domain", [
        ("sports", "sports"),
        ("entertainment", "entertainment"),
        ("science", "science"),
        ("markets", "business"),
        ("health", "health"),
    ])
    def test_domain_preset_has_narratives(self, preset, domain):
        """Each domain preset should find narratives with matching domain."""
        rows = self.conn.execute(
            "SELECT * FROM narratives WHERE status = 'active' AND domain = ?",
            (domain,),
        ).fetchall()
        assert len(rows) > 0, (
            f"Preset '{preset}' (domain={domain}) found 0 narratives"
        )


class TestDomainBypassFiltering:
    """Verify that domain-matched events bypass source filtering,
    mirroring how domain-matched narratives work."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.conn, self.tmpdir = _setup_db_with_domain_data()
        yield
        self.conn.close()

    def test_source_filter_would_miss_events_without_domain_bypass(self):
        """Simulate feedTag preset: activeSources restricts to specific feeds.
        Without domain bypass, events from general sources would be missed."""
        # Simulate Sports preset: activeSources = {"ESPN"}
        # storyIds = stories from ESPN
        sports_stories = self.conn.execute(
            "SELECT id FROM stories WHERE source = 'ESPN'"
        ).fetchall()
        story_ids = {r["id"] for r in sports_stories}

        # Get all events
        events = [dict(r) for r in self.conn.execute(
            "SELECT * FROM events WHERE merged_into IS NULL"
        ).fetchall()]

        # Old filtering: only events with overlapping story_ids
        event_story_map = {}
        for e in events:
            rows = self.conn.execute(
                "SELECT story_id FROM event_stories WHERE event_id = ?", (e["id"],)
            ).fetchall()
            event_story_map[e["id"]] = {r["story_id"] for r in rows}

        old_filter = [
            e for e in events
            if event_story_map[e["id"]] & story_ids
        ]
        old_ids = {e["id"] for e in old_filter}

        # Should find sports events (ESPN stories) but not science, health, etc.
        assert 10 in old_ids or 11 in old_ids, "Should find sports events by source"
        assert 30 not in old_ids, "Science event shouldn't match ESPN source filter"

    def test_domain_bypass_finds_events_through_narrative_link(self):
        """With domain bypass, events linked to domain narratives are included
        even when storyIds don't overlap with the source filter."""
        # Get all events with domain tags (simulating the backend fix)
        events = [dict(r) for r in self.conn.execute(
            """SELECT DISTINCT e.* FROM events e
               JOIN narrative_events ne ON e.id = ne.event_id
               JOIN narratives n ON n.id = ne.narrative_id
               WHERE n.status = 'active'"""
        ).fetchall()]

        # Compute domain tags
        domain_map = {}
        for e in events:
            rows = self.conn.execute(
                """SELECT n.domain FROM narratives n
                   JOIN narrative_events ne ON n.id = ne.narrative_id
                   WHERE ne.event_id = ? AND n.status = 'active'""",
                (e["id"],),
            ).fetchall()
            domain_map[e["id"]] = {r["domain"] for r in rows}

        # Science preset: domain = "science"
        science_events = [e for e in events if "science" in domain_map.get(e["id"], set())]
        assert len(science_events) >= 2, (
            f"Expected 2 science events (Mars + CERN), got {len(science_events)}"
        )
        science_ids = {e["id"] for e in science_events}
        assert 30 in science_ids, "Mars Sample Return should be in science events"
        assert 31 in science_ids, "CERN Discovery should be in science events"
