"""Semantic event clustering using LLM-extracted event signatures.

Replaces rule-based Jaccard clustering with signature-based matching.
Falls back to the original event_clusterer if no extractions exist.
"""

import json
import logging
import re
from collections import Counter
from datetime import datetime, timezone, timedelta

from .database import (
    get_active_events,
    get_unassigned_stories,
    get_event_stories,
)
from .llm_utils import parse_json_field

logger = logging.getLogger(__name__)

# Threshold for fuzzy signature matching (Dice coefficient)
FUZZY_MATCH_THRESHOLD = 0.40

# Minimum overlapping content words required for a match
MIN_OVERLAP_WORDS = 2

# Max stories per event before we stop adding more (prevents mega-events)
MAX_EVENT_STORIES = 50

# Max canonical signatures to use per event for matching
MAX_CANONICAL_SIGS = 10

# Max key_actors per event
MAX_KEY_ACTORS = 8

# Hours after which an event with no new stories is resolved
RESOLVE_HOURS = 48


def _get_event_signature(conn, story_id: int) -> str:
    """Get the event_signature from story_extractions for a story."""
    row = conn.execute(
        "SELECT event_signature FROM story_extractions WHERE story_id = ?",
        (story_id,),
    ).fetchone()
    return row["event_signature"] if row else ""


def _get_event_signatures(conn, event_id: int) -> list[str]:
    """Get canonical event signatures (most common, deduplicated).

    Uses GROUP BY to return only the top N most frequent signatures,
    preventing mega-events from accumulating hundreds of diverse sigs.
    """
    rows = conn.execute(
        """SELECT se.event_signature, COUNT(*) as cnt
           FROM story_extractions se
           JOIN event_stories es ON se.story_id = es.story_id
           WHERE es.event_id = ? AND se.event_signature IS NOT NULL
           AND se.event_signature != ''
           GROUP BY se.event_signature
           ORDER BY cnt DESC
           LIMIT ?""",
        (event_id, MAX_CANONICAL_SIGS),
    ).fetchall()
    return [r["event_signature"] for r in rows]


def _batch_get_event_signatures(conn, event_ids: list[int]) -> dict[int, list[str]]:
    """Batch-fetch signatures for multiple events in a single query.

    Returns {event_id: [sig1, sig2, ...]} with at most MAX_CANONICAL_SIGS per event.
    Much more efficient than calling _get_event_signatures N times.
    """
    if not event_ids:
        return {}
    ph = ",".join("?" * len(event_ids))
    rows = conn.execute(
        f"""SELECT es.event_id, se.event_signature, COUNT(*) as cnt
            FROM story_extractions se
            JOIN event_stories es ON se.story_id = es.story_id
            WHERE es.event_id IN ({ph})
            AND se.event_signature IS NOT NULL AND se.event_signature != ''
            GROUP BY es.event_id, se.event_signature
            ORDER BY es.event_id, cnt DESC""",
        event_ids,
    ).fetchall()

    result = {}
    for r in rows:
        eid = r["event_id"]
        if eid not in result:
            result[eid] = []
        if len(result[eid]) < MAX_CANONICAL_SIGS:
            result[eid].append(r["event_signature"])
    return result


# Stopwords to ignore in signature comparison
_STOPWORDS = frozenset({
    "the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "or", "is",
    "are", "was", "were", "be", "has", "have", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "over", "after",
    "before", "by", "with", "from", "up", "about", "into", "through", "new",
    "says", "said", "amid", "as", "its", "their", "his", "her", "but", "not",
})


def _signature_words(sig: str) -> set:
    """Extract significant words from a signature, filtering noise."""
    if not sig:
        return set()
    words = set(re.findall(r"[a-z]+", sig.lower()))
    # Remove stopwords and very short words
    return {w for w in words if w not in _STOPWORDS and len(w) > 1}


def _signature_similarity(sig_a: str, sig_b: str) -> float:
    """Compute Dice coefficient between significant words of two signatures.

    Requires at least MIN_OVERLAP_WORDS common content words.
    When only 2 words overlap, penalizes the score to avoid false positives
    from generic word pairs (e.g., "credit risks" matching unrelated events).
    """
    words_a = _signature_words(sig_a)
    words_b = _signature_words(sig_b)
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    if len(intersection) < MIN_OVERLAP_WORDS:
        return 0.0
    # Dice coefficient: 2*|intersection| / (|A| + |B|)
    score = 2 * len(intersection) / (len(words_a) + len(words_b))
    # Penalize 2-word overlap: require higher raw score to prevent
    # false positives from generic word pairs
    if len(intersection) == 2:
        score *= 0.7
    return score


def _best_event_match(signature: str, events: list[dict], event_sigs: dict) -> tuple:
    """Find the best matching event for a signature.

    Skips events that already have MAX_EVENT_STORIES stories to prevent
    mega-events from absorbing everything.

    Returns (event_id, score) or (None, 0).
    """
    best_id = None
    best_score = 0.0

    for event in events:
        # Don't add to already-large events
        if event.get("story_count", 0) >= MAX_EVENT_STORIES:
            continue
        sigs = event_sigs.get(event["id"], [])
        for esig in sigs:
            score = _signature_similarity(signature, esig)
            if score > best_score:
                best_score = score
                best_id = event["id"]

    return best_id, best_score




def _create_event(conn, story: dict) -> int:
    """Create a new event from a single story."""
    now = datetime.now(timezone.utc).isoformat()
    story_time = story.get("scraped_at", now)
    concepts = parse_json_field(story.get("concepts"))

    # Get extraction data if available
    extraction = conn.execute(
        "SELECT * FROM story_extractions WHERE story_id = ?", (story["id"],)
    ).fetchone()

    severity = None
    primary_action = None
    event_type = None
    affected_parties = "[]"
    location_name = story.get("location_name")
    lat = story.get("lat")
    lon = story.get("lon")

    if extraction:
        extraction = dict(extraction)
        severity = extraction.get("severity")
        primary_action = extraction.get("primary_action")
        topics = parse_json_field(extraction.get("topics"))
        if topics:
            concepts = topics
        try:
            ext_json = json.loads(extraction.get("extraction_json", "{}"))
            affected_parties = json.dumps(ext_json.get("affected_parties", []))
            event_type = ext_json.get("location_type", "terrestrial")
        except (json.JSONDecodeError, TypeError):
            pass

        # Use LLM-extracted event_location if available (more accurate)
        loc_row = conn.execute(
            """SELECT sl.name FROM story_locations sl
               WHERE sl.story_id = ? AND sl.role = 'event_location'
               LIMIT 1""",
            (story["id"],),
        ).fetchone()
        if loc_row:
            location_name = loc_row["name"]

    cursor = conn.execute(
        """INSERT INTO events
           (title, description, status, key_actors, primary_location,
            primary_lat, primary_lon, concepts, story_count,
            first_seen, last_updated, created_at,
            severity, primary_action, affected_parties, event_type)
           VALUES (?, ?, 'emerging', '[]', ?, ?, ?, ?, 1, ?, ?, ?,
                   ?, ?, ?, ?)""",
        (
            story.get("title", "Unnamed event"),
            story.get("summary", ""),
            location_name,
            lat,
            lon,
            json.dumps(concepts),
            story_time, story_time, now,
            severity, primary_action, affected_parties, event_type,
        ),
    )
    event_id = cursor.lastrowid

    conn.execute(
        "INSERT INTO event_stories (event_id, story_id, added_at) VALUES (?, ?, ?)",
        (event_id, story["id"], now),
    )
    conn.commit()
    return event_id


def _assign_story_to_event(conn, story: dict, event_id: int) -> None:
    """Add a story to an existing event and update aggregates."""
    now = datetime.now(timezone.utc).isoformat()
    story_time = story.get("scraped_at", now)

    conn.execute(
        "INSERT OR IGNORE INTO event_stories (event_id, story_id, added_at) VALUES (?, ?, ?)",
        (event_id, story["id"], now),
    )

    # Merge concepts
    story_concepts = parse_json_field(story.get("concepts"))
    event = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if event:
        event = dict(event)
        existing_concepts = parse_json_field(event.get("concepts"))
        merged_concepts = list(set(existing_concepts + story_concepts))

        # Recompute actors from story_actors table
        actor_rows = conn.execute(
            """SELECT sa.name, COUNT(*) as cnt FROM story_actors sa
               JOIN event_stories es ON sa.story_id = es.story_id
               WHERE es.event_id = ?
               GROUP BY sa.name ORDER BY cnt DESC LIMIT ?""",
            (event_id, MAX_KEY_ACTORS),
        ).fetchall()
        actors = [r["name"] for r in actor_rows] if actor_rows else parse_json_field(event.get("key_actors"))

        # Aggregate severity (use max)
        extraction = conn.execute(
            "SELECT severity, primary_action FROM story_extractions WHERE story_id = ?",
            (story["id"],),
        ).fetchone()
        new_severity = event.get("severity")
        new_action = event.get("primary_action")
        if extraction:
            try:
                ext_sev = int(extraction["severity"]) if extraction["severity"] else None
            except (ValueError, TypeError):
                ext_sev = None
            try:
                new_severity = int(new_severity) if new_severity else None
            except (ValueError, TypeError):
                new_severity = None
            if ext_sev and (new_severity is None or ext_sev > new_severity):
                new_severity = ext_sev
            if not new_action and extraction["primary_action"]:
                new_action = extraction["primary_action"]

        # Update location if story has coordinates and event doesn't,
        # or every 10 stories recalculate from median
        new_lat = event.get("primary_lat")
        new_lon = event.get("primary_lon")
        new_location = None  # Only update location name on recalculation
        story_lat = story.get("lat")
        story_lon = story.get("lon")
        story_count = event.get("story_count", 0) + 1

        if story_lat and story_lon:
            if new_lat is None or new_lon is None:
                new_lat, new_lon = story_lat, story_lon
                new_location = story.get("location_name")
            elif story_count % 10 == 0:
                # Recalculate from most common location's coordinates
                # (independent median of lat/lon produces nonsense when
                # stories span multiple regions, e.g. Iran + Washington)
                coord_rows = conn.execute(
                    """SELECT s.lat, s.lon, s.location_name FROM stories s
                       JOIN event_stories es ON s.id = es.story_id
                       WHERE es.event_id = ? AND s.lat IS NOT NULL""",
                    (event_id,),
                ).fetchall()
                if len(coord_rows) >= 3:
                    # Find most common location name
                    loc_counts = {}
                    for r in coord_rows:
                        name = r["location_name"]
                        if name:
                            loc_counts[name] = loc_counts.get(name, 0) + 1
                    if loc_counts:
                        new_location = max(loc_counts, key=loc_counts.get)
                        # Use median coords from stories with that location
                        loc_rows = [r for r in coord_rows
                                    if r["location_name"] == new_location]
                        if loc_rows:
                            lats = sorted(r["lat"] for r in loc_rows)
                            lons = sorted(r["lon"] for r in loc_rows)
                            new_lat = lats[len(lats) // 2]
                            new_lon = lons[len(lons) // 2]

        conn.execute(
            """UPDATE events SET
               story_count = story_count + 1,
               last_updated = ?,
               concepts = ?,
               key_actors = ?,
               severity = ?,
               primary_action = ?,
               primary_location = COALESCE(?, primary_location),
               primary_lat = COALESCE(?, primary_lat),
               primary_lon = COALESCE(?, primary_lon)
               WHERE id = ?""",
            (story_time, json.dumps(merged_concepts), json.dumps(actors),
             new_severity, new_action, new_location, new_lat, new_lon, event_id),
        )
    conn.commit()


def _update_event_statuses(conn) -> None:
    """Auto-update event statuses."""
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(hours=RESOLVE_HOURS)).isoformat()

    conn.execute(
        """UPDATE events SET status = 'resolved'
           WHERE merged_into IS NULL
           AND status NOT IN ('resolved')
           AND last_updated < ?""",
        (cutoff,),
    )
    conn.execute(
        """UPDATE events SET status = 'ongoing'
           WHERE merged_into IS NULL
           AND status = 'emerging'
           AND story_count >= 3""",
    )
    conn.commit()


def _merge_threshold(story_count: int) -> float:
    """Dynamic merge threshold based on event size.

    Smaller events merge more aggressively to reduce singletons;
    larger events require higher similarity to avoid contamination.
    """
    if story_count <= 2:
        return 0.35
    elif story_count <= 5:
        return 0.40
    else:
        return 0.45


def _try_merge_events(conn, events: list[dict]) -> int:
    """Merge small events with similar signatures.

    Uses dynamic thresholds: singletons (1-2 stories) merge at 0.35,
    small events (3-5) at 0.40, larger events (6+) at 0.45.
    """
    merged = 0
    small = [e for e in events if e["story_count"] <= 5]
    large = [e for e in events if e["story_count"] > 5]
    targets = large + small

    # Batch-fetch signatures (single query instead of N queries)
    event_sigs = _batch_get_event_signatures(conn, [e["id"] for e in events])

    merged_ids = set()
    for small_event in small:
        if small_event["id"] in merged_ids:
            continue
        sigs = event_sigs.get(small_event["id"], [])
        if not sigs:
            continue

        best_score = 0
        best_target = None
        for target in targets:
            if target["id"] == small_event["id"] or target["id"] in merged_ids:
                continue
            target_sigs = event_sigs.get(target["id"], [])
            for s1 in sigs:
                for s2 in target_sigs:
                    score = _signature_similarity(s1, s2)
                    if score > best_score:
                        best_score = score
                        best_target = target

        # Use dynamic threshold: stricter for larger source events
        merge_thresh = _merge_threshold(small_event.get("story_count", 1))
        if best_score >= merge_thresh and best_target:
            # Check if merge would exceed cap
            combined = best_target.get("story_count", 0) + small_event.get("story_count", 0)
            if combined > MAX_EVENT_STORIES:
                continue
            conn.execute(
                "UPDATE event_stories SET event_id = ? WHERE event_id = ?",
                (best_target["id"], small_event["id"]),
            )
            count = conn.execute(
                "SELECT COUNT(*) as c FROM event_stories WHERE event_id = ?",
                (best_target["id"],),
            ).fetchone()["c"]
            conn.execute(
                "UPDATE events SET story_count = ? WHERE id = ?",
                (count, best_target["id"]),
            )
            conn.execute(
                "UPDATE events SET merged_into = ? WHERE id = ?",
                (best_target["id"], small_event["id"]),
            )
            # Update in-memory count for subsequent checks
            best_target["story_count"] = count
            merged_ids.add(small_event["id"])
            merged += 1

    if merged:
        conn.commit()
    return merged


def _find_event_by_exact_signature(conn, signature: str) -> int | None:
    """Find an active event that already has a story with this exact signature.

    Uses the idx_extractions_event_signature index for O(1) lookup instead
    of loading all events into memory. Returns the largest matching event
    that isn't full (< MAX_EVENT_STORIES).
    """
    row = conn.execute(
        """SELECT es.event_id, e.story_count
           FROM story_extractions se
           JOIN event_stories es ON se.story_id = es.story_id
           JOIN events e ON es.event_id = e.id
           WHERE se.event_signature = ?
           AND e.merged_into IS NULL AND e.status != 'resolved'
           AND e.story_count < ?
           ORDER BY e.story_count DESC
           LIMIT 1""",
        (signature, MAX_EVENT_STORIES),
    ).fetchone()
    return row["event_id"] if row else None


def _merge_exact_duplicates(conn) -> int:
    """Merge events that share exact signatures across the full database.

    Uses SQL GROUP BY to find signatures assigned to multiple active events,
    then merges smaller events into the largest one in each group.
    """
    # Find signatures shared across multiple active events
    dupe_rows = conn.execute(
        """SELECT se.event_signature,
                  GROUP_CONCAT(DISTINCT es.event_id) as event_ids
           FROM story_extractions se
           JOIN event_stories es ON se.story_id = es.story_id
           JOIN events e ON es.event_id = e.id
           WHERE e.merged_into IS NULL AND e.status != 'resolved'
           AND se.event_signature IS NOT NULL AND se.event_signature != ''
           GROUP BY se.event_signature
           HAVING COUNT(DISTINCT es.event_id) > 1
           LIMIT 500"""
    ).fetchall()

    merged = 0
    for row in dupe_rows:
        event_ids = [int(x) for x in row["event_ids"].split(",")]
        # Get story counts to find the largest
        events_info = conn.execute(
            f"""SELECT id, story_count FROM events
                WHERE id IN ({','.join('?' * len(event_ids))})
                ORDER BY story_count DESC""",
            event_ids,
        ).fetchall()
        if len(events_info) < 2:
            continue

        target = events_info[0]
        target_id = target["id"]
        target_count = target["story_count"]

        for source in events_info[1:]:
            source_id = source["id"]
            combined = target_count + source["story_count"]
            if combined > MAX_EVENT_STORIES:
                continue
            # Move stories from source to target
            conn.execute(
                "UPDATE OR IGNORE event_stories SET event_id = ? WHERE event_id = ?",
                (target_id, source_id),
            )
            # Clean up any stories that couldn't move (duplicates)
            conn.execute(
                "DELETE FROM event_stories WHERE event_id = ?",
                (source_id,),
            )
            conn.execute(
                "UPDATE events SET merged_into = ? WHERE id = ?",
                (target_id, source_id),
            )
            # Recount
            count = conn.execute(
                "SELECT COUNT(*) as c FROM event_stories WHERE event_id = ?",
                (target_id,),
            ).fetchone()["c"]
            conn.execute(
                "UPDATE events SET story_count = ? WHERE id = ?",
                (count, target_id),
            )
            target_count = count
            merged += 1

    if merged:
        conn.commit()
    return merged


def cluster_new_stories(conn) -> dict:
    """Main semantic clustering entry point.

    Two-phase matching:
    1. Exact signature match via DB index (catches most cases)
    2. Fuzzy signature match against recent events (catches near-matches)
    """
    stories = get_unassigned_stories(conn, limit=500)
    if not stories:
        return {"assigned": 0, "new_events": 0, "merged": 0}

    assigned = 0
    new_events = 0

    # Group stories by signature for efficient matching
    sig_groups = {}  # signature -> [stories]
    no_sig_stories = []

    for story in stories:
        sig = _get_event_signature(conn, story["id"])
        if sig:
            sig_groups.setdefault(sig, []).append(story)
        else:
            no_sig_stories.append(story)

    # Track newly created events for fuzzy matching fallback
    new_event_sigs = {}  # event_id -> [signatures]

    # Phase 1: Exact signature match via DB query
    unmatched_groups = {}  # sig -> [stories] that didn't find exact match
    for sig, group in sig_groups.items():
        event_id = _find_event_by_exact_signature(conn, sig)
        if event_id is not None:
            # Check available slots
            current = conn.execute(
                "SELECT story_count FROM events WHERE id = ?", (event_id,)
            ).fetchone()
            available = MAX_EVENT_STORIES - (current[0] if current else 0)
            to_assign = group[:max(available, 0)]
            overflow = group[max(available, 0):]

            for story in to_assign:
                _assign_story_to_event(conn, story, event_id)
                assigned += 1

            if overflow:
                first = overflow[0]
                new_id = _create_event(conn, first)
                new_events += 1
                new_event_sigs[new_id] = [sig]
                for story in overflow[1:MAX_EVENT_STORIES]:
                    _assign_story_to_event(conn, story, new_id)
                    assigned += 1
        else:
            unmatched_groups[sig] = group

    # Phase 2: Fuzzy match unmatched signatures against recent events
    if unmatched_groups:
        recent_events = get_active_events(conn, limit=500)
        event_ids = [e["id"] for e in recent_events]
        event_sigs = _batch_get_event_signatures(conn, event_ids)
        # Also include newly created events from phase 1
        for eid, sigs in new_event_sigs.items():
            event_sigs[eid] = sigs
            ev = conn.execute("SELECT * FROM events WHERE id = ?", (eid,)).fetchone()
            if ev:
                recent_events.append(dict(ev))

        for sig, group in unmatched_groups.items():
            best_event_id, best_score = _best_event_match(
                sig, recent_events, event_sigs
            )

            if best_score >= FUZZY_MATCH_THRESHOLD and best_event_id is not None:
                current = conn.execute(
                    "SELECT story_count FROM events WHERE id = ?", (best_event_id,)
                ).fetchone()
                available = MAX_EVENT_STORIES - (current[0] if current else 0)
                to_assign = group[:max(available, 0)]
                overflow = group[max(available, 0):]

                for story in to_assign:
                    _assign_story_to_event(conn, story, best_event_id)
                    assigned += 1
                event_sigs.setdefault(best_event_id, []).append(sig)

                if overflow:
                    first = overflow[0]
                    new_id = _create_event(conn, first)
                    new_events += 1
                    new_event = conn.execute(
                        "SELECT * FROM events WHERE id = ?", (new_id,)
                    ).fetchone()
                    if new_event:
                        recent_events.append(dict(new_event))
                        event_sigs[new_id] = [sig]
                    for story in overflow[1:MAX_EVENT_STORIES]:
                        _assign_story_to_event(conn, story, new_id)
                        assigned += 1
            else:
                # No match — create new event
                first = group[0]
                new_id = _create_event(conn, first)
                new_events += 1
                new_event = conn.execute(
                    "SELECT * FROM events WHERE id = ?", (new_id,)
                ).fetchone()
                if new_event:
                    recent_events.append(dict(new_event))
                    event_sigs[new_id] = [sig]
                for story in group[1:MAX_EVENT_STORIES]:
                    _assign_story_to_event(conn, story, new_id)
                    assigned += 1

    # Stories without extractions are skipped — they'll be clustered once extracted.
    if no_sig_stories:
        logger.info("Skipping %d stories without event signatures (awaiting extraction)",
                     len(no_sig_stories))

    # Update statuses
    _update_event_statuses(conn)

    # Merge exact-duplicate events across the full database
    merged = _merge_exact_duplicates(conn)

    # Also try fuzzy merging on recent small events
    recent = get_active_events(conn, limit=500)
    merged += _try_merge_events(conn, recent)

    logger.info(
        "Semantic clustering: %d assigned, %d new events, %d merged",
        assigned, new_events, merged,
    )
    return {"assigned": assigned, "new_events": new_events, "merged": merged}
