"""Incremental story-to-event clustering (rule-based, always works)."""

import hashlib
import json
import logging
import re
from datetime import datetime, timezone, timedelta

from .database import (
    get_active_events,
    get_unassigned_stories,
    get_event_stories,
)

logger = logging.getLogger(__name__)

# Words to ignore in title similarity
STOP_WORDS = frozenset(
    "a an the and or but in on at to for of is it its by from with as be was "
    "were are been has had have will would could should may might shall this "
    "that these those he she they his her their our your my me we us you what "
    "which who whom how when where why than not no nor so if do does did can "
    "about after all also any been before being between both each few into just "
    "more most new now only other out over own same some still such then there "
    "through too under up very says said say".split()
)

# Threshold for assigning a story to an existing event
ASSIGN_THRESHOLD = 0.30

# Minimum title similarity required (prevents location-only matches)
MIN_TITLE_SIM = 0.05

# Max key_actors per event (prevents snowball contamination)
MAX_KEY_ACTORS = 8

# Thresholds for merging small events
MERGE_TITLE_THRESHOLD = 0.35
MERGE_LOCATION_THRESHOLD = 0.40

# Hours after which an event with no new stories is resolved
RESOLVE_HOURS = 48

# Weights for similarity components
W_TITLE = 0.35
W_LOCATION = 0.30
W_CONCEPT = 0.25
W_TEMPORAL = 0.10


def _significant_words(text: str) -> set[str]:
    """Extract significant words from text, lowercased, stop words removed."""
    if not text:
        return set()
    words = set(re.findall(r"[a-z0-9]+", text.lower()))
    return words - STOP_WORDS


def title_similarity(a: str, b: str) -> float:
    """Jaccard similarity on significant words of two titles."""
    words_a = _significant_words(a)
    words_b = _significant_words(b)
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def location_overlap(locs_a: list[str], locs_b: list[str]) -> float:
    """Jaccard overlap between two lists of location names."""
    if not locs_a or not locs_b:
        return 0.0
    set_a = {loc.lower() for loc in locs_a}
    set_b = {loc.lower() for loc in locs_b}
    intersection = set_a & set_b
    if not intersection:
        return 0.0
    return len(intersection) / len(set_a | set_b)


def concept_overlap(a: list[str], b: list[str]) -> float:
    """Jaccard overlap of concept lists."""
    if not a or not b:
        return 0.0
    set_a = set(a)
    set_b = set(b)
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def temporal_proximity(time_a: str, time_b: str) -> float:
    """Score 0-1 based on time difference, decaying over 48h."""
    try:
        t_a = datetime.fromisoformat(time_a)
        t_b = datetime.fromisoformat(time_b)
        diff_hours = abs((t_a - t_b).total_seconds()) / 3600
        if diff_hours > RESOLVE_HOURS:
            return 0.0
        return 1.0 - (diff_hours / RESOLVE_HOURS)
    except (ValueError, TypeError):
        return 0.5  # unknown, neutral


def _parse_json_field(val, default=None):
    """Safely parse a JSON string field."""
    if default is None:
        default = []
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            pass
    return default


def _extract_locations(story: dict, event_only: bool = True) -> list[str]:
    """Extract location names from a story's NER entities.

    If event_only=True, only return locations with role 'event_location'
    (where it happened), not origins or passing mentions. This prevents
    clustering contamination from contextual country references.
    """
    entities = _parse_json_field(story.get("ner_entities"))
    locations = []
    for e in entities:
        if isinstance(e, dict):
            text = e.get("text", "")
            role = e.get("role", "mentioned")
            if event_only and role not in ("event_location",):
                continue
        elif isinstance(e, str):
            text = e
        else:
            continue
        if text:
            locations.append(text)
    if not locations and story.get("location_name"):
        locations.append(story["location_name"])
    return locations


def _event_titles(conn, event: dict) -> list[str]:
    """Get recent story titles for an event (for matching)."""
    stories = get_event_stories(conn, event["id"], limit=10)
    return [s["title"] for s in stories if s.get("title")]


def story_event_score(story: dict, event: dict, event_story_titles: list[str]) -> float:
    """Score how well a story matches an existing event (0-1)."""
    # Title similarity: compare against event title + recent story titles
    best_title_sim = title_similarity(story.get("title", ""), event.get("title", ""))
    for et in event_story_titles:
        sim = title_similarity(story.get("title", ""), et)
        if sim > best_title_sim:
            best_title_sim = sim

    # Location overlap
    story_locs = _extract_locations(story)
    event_locs = []
    if event.get("primary_location"):
        event_locs.append(event["primary_location"])
    event_actors = _parse_json_field(event.get("key_actors"))
    event_locs.extend(event_actors)
    loc_score = location_overlap(story_locs, event_locs)

    # Concept overlap
    story_concepts = _parse_json_field(story.get("concepts"))
    event_concepts = _parse_json_field(event.get("concepts"))
    concept_score = concept_overlap(story_concepts, event_concepts)

    # Temporal proximity
    time_score = temporal_proximity(
        story.get("scraped_at", ""),
        event.get("last_updated", ""),
    )

    # Gate: if no title word overlap at all, location/concept matches alone
    # are unreliable (prevents snowball contamination via shared country names)
    if best_title_sim < MIN_TITLE_SIM:
        return 0.0

    return (
        W_TITLE * best_title_sim
        + W_LOCATION * loc_score
        + W_CONCEPT * concept_score
        + W_TEMPORAL * time_score
    )


def _create_event(conn, story: dict) -> int:
    """Create a new event seeded from a single story."""
    now = datetime.now(timezone.utc).isoformat()
    story_time = story.get("scraped_at", now)
    concepts = _parse_json_field(story.get("concepts"))
    locations = _extract_locations(story)

    cursor = conn.execute(
        """INSERT INTO events
           (title, description, status, key_actors, primary_location,
            primary_lat, primary_lon, concepts, story_count,
            first_seen, last_updated, created_at)
           VALUES (?, ?, 'emerging', ?, ?, ?, ?, ?, 1, ?, ?, ?)""",
        (
            story.get("title", "Unnamed event"),
            story.get("summary", ""),
            json.dumps(locations),
            story.get("location_name"),
            story.get("lat"),
            story.get("lon"),
            json.dumps(concepts),
            story_time,
            story_time,
            now,
        ),
    )
    event_id = cursor.lastrowid

    conn.execute(
        "INSERT INTO event_stories (event_id, story_id, added_at) VALUES (?, ?, ?)",
        (event_id, story["id"], now),
    )
    conn.commit()
    return event_id


def _recompute_event_actors(conn, event_id: int) -> list[str]:
    """Recompute key_actors from all stories in the event, keeping only frequent ones."""
    from collections import Counter
    stories = get_event_stories(conn, event_id, limit=50)
    loc_counts = Counter()
    for s in stories:
        for loc in _extract_locations(s):
            loc_counts[loc.lower()] += 1
    # Keep locations mentioned by 2+ stories, or all if event is small
    story_count = len(stories)
    if story_count <= 2:
        top_locs = [loc for loc, _ in loc_counts.most_common(MAX_KEY_ACTORS)]
    else:
        # Only keep locations mentioned by at least 2 stories
        top_locs = [loc for loc, cnt in loc_counts.most_common(MAX_KEY_ACTORS) if cnt >= 2]
        if not top_locs:
            # Fallback: keep the most common one
            top_locs = [loc for loc, _ in loc_counts.most_common(1)]
    return top_locs


def _assign_story_to_event(conn, story: dict, event_id: int) -> None:
    """Add a story to an existing event and update aggregates."""
    now = datetime.now(timezone.utc).isoformat()
    story_time = story.get("scraped_at", now)

    conn.execute(
        "INSERT OR IGNORE INTO event_stories (event_id, story_id, added_at) VALUES (?, ?, ?)",
        (event_id, story["id"], now),
    )

    # Update event aggregates
    story_concepts = _parse_json_field(story.get("concepts"))
    event = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if event:
        event = dict(event)
        existing_concepts = _parse_json_field(event.get("concepts"))
        merged_concepts = list(set(existing_concepts + story_concepts))

        # Recompute actors from all stories (frequency-weighted, capped)
        merged_actors = _recompute_event_actors(conn, event_id)

        conn.execute(
            """UPDATE events SET
               story_count = story_count + 1,
               last_updated = ?,
               concepts = ?,
               key_actors = ?
               WHERE id = ?""",
            (story_time, json.dumps(merged_concepts), json.dumps(merged_actors), event_id),
        )
    conn.commit()


def _update_event_statuses(conn) -> None:
    """Auto-update event statuses based on story count and age."""
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(hours=RESOLVE_HOURS)).isoformat()

    # Resolve events with no stories in 48h
    conn.execute(
        """UPDATE events SET status = 'resolved'
           WHERE merged_into IS NULL
           AND status NOT IN ('resolved')
           AND last_updated < ?""",
        (cutoff,),
    )

    # Promote emerging -> ongoing when 3+ stories
    conn.execute(
        """UPDATE events SET status = 'ongoing'
           WHERE merged_into IS NULL
           AND status = 'emerging'
           AND story_count >= 3""",
    )

    conn.commit()


def _try_merge_events(conn, events: list[dict]) -> int:
    """Try to merge small similar events. Returns merge count."""
    merged = 0
    # Only consider small events for merging
    small = [e for e in events if e["story_count"] <= 5]
    large = [e for e in events if e["story_count"] > 5]
    targets = large + small  # prefer merging into larger events

    merged_ids = set()
    for small_event in small:
        if small_event["id"] in merged_ids:
            continue

        best_score = 0
        best_target = None
        for target in targets:
            if target["id"] == small_event["id"]:
                continue
            if target["id"] in merged_ids:
                continue

            t_sim = title_similarity(
                small_event.get("title", ""),
                target.get("title", ""),
            )
            small_locs = _parse_json_field(small_event.get("key_actors"))
            target_locs = _parse_json_field(target.get("key_actors"))
            l_sim = location_overlap(small_locs, target_locs)

            # Either strong title match alone, or both moderate
            can_merge = (t_sim >= MERGE_TITLE_THRESHOLD) or (
                t_sim >= 0.25 and l_sim >= MERGE_LOCATION_THRESHOLD
            )
            if can_merge:
                score = t_sim + l_sim
                if score > best_score:
                    best_score = score
                    best_target = target

        if best_target:
            # Merge small_event into best_target
            conn.execute(
                "UPDATE event_stories SET event_id = ? WHERE event_id = ?",
                (best_target["id"], small_event["id"]),
            )
            # Update target story count
            count = conn.execute(
                "SELECT COUNT(*) as c FROM event_stories WHERE event_id = ?",
                (best_target["id"],),
            ).fetchone()["c"]
            conn.execute(
                "UPDATE events SET story_count = ? WHERE id = ?",
                (count, best_target["id"]),
            )
            # Mark small as merged
            conn.execute(
                "UPDATE events SET merged_into = ? WHERE id = ?",
                (best_target["id"], small_event["id"]),
            )
            merged_ids.add(small_event["id"])
            merged += 1

    if merged:
        conn.commit()
    return merged


def _compute_analysis_hash(conn, event_id: int) -> str:
    """Compute a hash of story IDs for change detection."""
    rows = conn.execute(
        "SELECT story_id FROM event_stories WHERE event_id = ? ORDER BY story_id",
        (event_id,),
    ).fetchall()
    ids_str = ",".join(str(r["story_id"]) for r in rows)
    return hashlib.md5(ids_str.encode()).hexdigest()


def cluster_new_stories(conn) -> dict:
    """Main clustering entry point. Process unassigned stories.

    Returns stats dict: {"assigned": int, "new_events": int, "merged": int}
    """
    stories = get_unassigned_stories(conn, limit=200)
    if not stories:
        return {"assigned": 0, "new_events": 0, "merged": 0}

    events = get_active_events(conn, limit=100)

    # Pre-fetch recent titles for each event
    event_titles_cache = {}
    for event in events:
        event_titles_cache[event["id"]] = _event_titles(conn, event)

    assigned = 0
    new_events = 0

    for story in stories:
        best_score = 0
        best_event_id = None

        for event in events:
            score = story_event_score(
                story, event, event_titles_cache.get(event["id"], [])
            )
            if score > best_score:
                best_score = score
                best_event_id = event["id"]

        if best_score >= ASSIGN_THRESHOLD and best_event_id is not None:
            _assign_story_to_event(conn, story, best_event_id)
            assigned += 1
        else:
            new_id = _create_event(conn, story)
            new_events += 1
            # Add to active events list for subsequent stories in this batch
            new_event = conn.execute(
                "SELECT * FROM events WHERE id = ?", (new_id,)
            ).fetchone()
            if new_event:
                new_event = dict(new_event)
                events.append(new_event)
                event_titles_cache[new_id] = [story.get("title", "")]

    # Update statuses (emerging -> ongoing, stale -> resolved)
    _update_event_statuses(conn)

    # Try merging small similar events
    events = get_active_events(conn, limit=100)
    merged = _try_merge_events(conn, events)

    # Update analysis hashes
    for event in get_active_events(conn, limit=100):
        new_hash = _compute_analysis_hash(conn, event["id"])
        conn.execute(
            "UPDATE events SET analysis_hash = ? WHERE id = ? AND (analysis_hash IS NULL OR analysis_hash != ?)",
            (new_hash, event["id"], new_hash),
        )
    conn.commit()

    logger.info(
        "Clustering: %d assigned, %d new events, %d merged",
        assigned, new_events, merged,
    )
    return {"assigned": assigned, "new_events": new_events, "merged": merged}
