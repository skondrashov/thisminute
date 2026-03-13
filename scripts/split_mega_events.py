#!/usr/bin/env python3
"""Split mega-events and delete garbage events.

Mega-events (100+ stories) absorbed unrelated stories because the old
clustering threshold was too low and matched against all accumulated sigs.

This script:
1. Unassigns all stories from events with 100+ stories
2. Deletes garbage events (like "News Clustering Error")
3. Lets the improved clusterer re-assign them properly
"""
import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "thisminute.db")

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Find mega-events (100+ stories)
    mega = conn.execute(
        "SELECT id, title, story_count FROM events WHERE merged_into IS NULL AND story_count >= 100"
    ).fetchall()

    print(f"Found {len(mega)} mega-events:", flush=True)
    total_freed = 0
    for e in mega:
        print(f"  #{e['id']} ({e['story_count']} stories): {e['title'][:80]}", flush=True)
        # Unassign all stories from this event
        conn.execute("DELETE FROM event_stories WHERE event_id = ?", (e["id"],))
        conn.execute("UPDATE events SET story_count = 0, merged_into = -1 WHERE id = ?", (e["id"],))
        total_freed += e["story_count"]

    # Find and delete garbage events (title contains "Error" or "Mismatch")
    garbage = conn.execute(
        """SELECT id, title, story_count FROM events
           WHERE merged_into IS NULL
           AND (title LIKE '%Clustering Error%' OR title LIKE '%Clustering System Error%'
                OR title LIKE '%Mismatch%' OR title LIKE '%Incorrectly Grouped%')"""
    ).fetchall()

    print(f"\nFound {len(garbage)} garbage events:", flush=True)
    for e in garbage:
        print(f"  #{e['id']} ({e['story_count']} stories): {e['title'][:80]}", flush=True)
        conn.execute("DELETE FROM event_stories WHERE event_id = ?", (e["id"],))
        conn.execute("UPDATE events SET story_count = 0, merged_into = -1 WHERE id = ?", (e["id"],))
        total_freed += e["story_count"]

    # Also find events with very mixed signatures (high diversity = bad clustering)
    mixed = conn.execute(
        """SELECT es2.event_id, COUNT(DISTINCT se.event_signature) as sig_count,
                  e.story_count, e.title
           FROM event_stories es2
           JOIN story_extractions se ON es2.story_id = se.story_id
           JOIN events e ON es2.event_id = e.id
           WHERE e.merged_into IS NULL AND e.story_count >= 20
           GROUP BY es2.event_id
           HAVING sig_count > story_count * 0.8"""
    ).fetchall()

    print(f"\nFound {len(mixed)} events with very high signature diversity:", flush=True)
    for e in mixed:
        print(f"  #{e['event_id']} ({e['story_count']} stories, {e['sig_count']} unique sigs): {e['title'][:60]}", flush=True)
        conn.execute("DELETE FROM event_stories WHERE event_id = ?", (e["event_id"],))
        conn.execute("UPDATE events SET story_count = 0, merged_into = -1 WHERE id = ?", (e["event_id"],))
        total_freed += e["story_count"]

    conn.commit()

    # Count unassigned stories now
    unassigned = conn.execute(
        "SELECT COUNT(*) as c FROM stories WHERE id NOT IN (SELECT story_id FROM event_stories)"
    ).fetchone()["c"]

    print(f"\nTotal stories freed: {total_freed}", flush=True)
    print(f"Total unassigned stories now: {unassigned}", flush=True)
    print("These will be re-clustered by the improved semantic clusterer.", flush=True)

    conn.close()

if __name__ == "__main__":
    main()
