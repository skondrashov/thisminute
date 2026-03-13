"""Investigate multi-story events with no location at all."""
import sqlite3
import os
import json

DB = os.environ.get("DB_PATH", "/opt/thisminute/data/thisminute.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# Events with no location (multi-story)
rows = conn.execute(
    """SELECT e.id, e.title, e.story_count, e.event_type
    FROM events e
    WHERE e.merged_into IS NULL AND e.status != 'resolved'
    AND e.story_count >= 3
    AND (e.primary_location IS NULL OR e.primary_location = '')
    ORDER BY e.story_count DESC LIMIT 20"""
).fetchall()

print(f"=== Multi-story events (3+) with no location ===")
for r in rows:
    etype = r["event_type"] or "standard"
    print(f"\n  [{r['id']}] {r['story_count']} stories [{etype}]: {r['title'][:60]}")

    # Check if stories have locations
    story_locs = conn.execute(
        """SELECT s.location_name, s.lat, s.lon FROM stories s
        JOIN event_stories es ON s.id = es.story_id
        WHERE es.event_id = ?
        AND s.location_name IS NOT NULL AND s.location_name != ''
        LIMIT 5""",
        (r["id"],),
    ).fetchall()
    if story_locs:
        for sl in story_locs:
            coords = f"({sl['lat']:.2f},{sl['lon']:.2f})" if sl["lat"] else "(no coords)"
            print(f"    story loc: {sl['location_name'][:30]} {coords}")
    else:
        print(f"    NO story locations found")

    # Check story titles for location hints
    titles = conn.execute(
        """SELECT s.title FROM stories s
        JOIN event_stories es ON s.id = es.story_id
        WHERE es.event_id = ? LIMIT 3""",
        (r["id"],),
    ).fetchall()
    for t in titles:
        print(f"    story: {t['title'][:55]}")

# Check event_type distribution
print("\n\n=== Event type distribution (active, multi-story) ===")
types = conn.execute(
    """SELECT event_type, COUNT(*) as cnt FROM events
    WHERE merged_into IS NULL AND status != 'resolved' AND story_count >= 2
    GROUP BY event_type ORDER BY cnt DESC"""
).fetchall()
for t in types:
    print(f"  {t['event_type'] or 'NULL':15s}: {t['cnt']}")

conn.close()
