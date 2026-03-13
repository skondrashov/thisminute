"""One-time script to re-merge events using improved signature matching."""
import sqlite3
import re
import sys
import json
from datetime import datetime, timezone

DB_PATH = sys.argv[1] if len(sys.argv) > 1 else "data/thisminute.db"
conn = sqlite3.connect(DB_PATH, timeout=30)
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA busy_timeout=30000")
conn.row_factory = sqlite3.Row

FUZZY_MATCH_THRESHOLD = 0.35

_STOPWORDS = frozenset({
    "the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "or", "is",
    "are", "was", "were", "be", "has", "have", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "over", "after",
    "before", "by", "with", "from", "up", "about", "into", "through", "new",
    "says", "said", "amid", "as", "its", "their", "his", "her", "but", "not",
})


def sig_words(sig):
    if not sig:
        return set()
    words = set(re.findall(r"[a-z]+", sig.lower()))
    return {w for w in words if w not in _STOPWORDS and len(w) > 1}


def sig_similarity(sig_a, sig_b):
    wa, wb = sig_words(sig_a), sig_words(sig_b)
    if not wa or not wb:
        return 0.0
    intersection = wa & wb
    return 2 * len(intersection) / (len(wa) + len(wb))


def get_event_signatures(event_id):
    rows = conn.execute(
        """SELECT se.event_signature FROM story_extractions se
           JOIN event_stories es ON se.story_id = es.story_id
           WHERE es.event_id = ?""",
        (event_id,),
    ).fetchall()
    return [r["event_signature"] for r in rows if r["event_signature"]]


# Get all active events
events = conn.execute(
    "SELECT * FROM events WHERE merged_into IS NULL ORDER BY id"
).fetchall()
events = [dict(e) for e in events]

print(f"Total events: {len(events)}", flush=True)
single = sum(1 for e in events if e["story_count"] == 1)
print(f"Single-story events: {single}", flush=True)

# Cache signatures
event_sigs = {}
for e in events:
    event_sigs[e["id"]] = get_event_signatures(e["id"])

# Try merging
total_merged = 0
for pass_num in range(10):
    merged = 0
    merged_ids = set()

    # Re-fetch active events
    events = conn.execute(
        "SELECT * FROM events WHERE merged_into IS NULL ORDER BY story_count DESC, id"
    ).fetchall()
    events = [dict(e) for e in events]

    # Refresh sig cache
    event_sigs = {}
    for e in events:
        event_sigs[e["id"]] = get_event_signatures(e["id"])

    small = [e for e in events if e["story_count"] <= 5]
    targets = events  # All events are potential merge targets

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
                    score = sig_similarity(s1, s2)
                    if score > best_score:
                        best_score = score
                        best_target = target

        if best_score >= FUZZY_MATCH_THRESHOLD and best_target:
            # Merge small_event into best_target
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
            merged_ids.add(small_event["id"])
            merged += 1

    if merged:
        conn.commit()
    total_merged += merged
    print(f"  Pass {pass_num+1}: merged {merged} events", flush=True)
    if merged == 0:
        break

print(f"\nTotal merged: {total_merged}", flush=True)

# Final stats
events = conn.execute(
    "SELECT * FROM events WHERE merged_into IS NULL"
).fetchall()
single = sum(1 for e in events if e["story_count"] == 1)
multi = sum(1 for e in events if e["story_count"] > 1)
print(f"After merge: {len(events)} events ({single} single, {multi} multi)", flush=True)

# Show top multi-story events
top = conn.execute(
    "SELECT id, title, story_count FROM events WHERE merged_into IS NULL ORDER BY story_count DESC LIMIT 10"
).fetchall()
print(f"\nTop events by story count:", flush=True)
for e in top:
    print(f"  #{e['id']}: [{e['story_count']} stories] {e['title'][:70]}", flush=True)

conn.close()
