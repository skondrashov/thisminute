"""Fill in null event coordinates from geocode cache or story coordinates."""
import sqlite3
import os

DB = os.environ.get("DB_PATH", "/opt/thisminute/data/thisminute.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA journal_mode=WAL")

# Phase 1: Fill from geocode cache
events = conn.execute(
    """SELECT e.id, e.primary_location FROM events e
    WHERE e.merged_into IS NULL AND e.status != 'resolved'
    AND e.primary_location IS NOT NULL AND e.primary_location != ''
    AND (e.primary_lat IS NULL OR e.primary_lon IS NULL)"""
).fetchall()

print(f"Events with null coords: {len(events)}", flush=True)
fixed_cache = 0
remaining = []

for e in events:
    cached = conn.execute(
        "SELECT lat, lon FROM geocode_cache WHERE location_name = ?",
        (e["primary_location"],),
    ).fetchone()
    if cached and cached["lat"] is not None:
        conn.execute(
            "UPDATE events SET primary_lat=?, primary_lon=? WHERE id=?",
            (cached["lat"], cached["lon"], e["id"]),
        )
        fixed_cache += 1
    else:
        remaining.append(e)

conn.commit()
print(f"Fixed from geocode cache: {fixed_cache}", flush=True)

# Phase 2: Fill from story coordinates
fixed_stories = 0
for e in remaining:
    row = conn.execute(
        """SELECT s.lat, s.lon FROM stories s
        JOIN event_stories es ON s.id = es.story_id
        WHERE es.event_id = ? AND s.lat IS NOT NULL
        LIMIT 1""",
        (e["id"],),
    ).fetchone()
    if row:
        conn.execute(
            "UPDATE events SET primary_lat=?, primary_lon=? WHERE id=?",
            (row["lat"], row["lon"], e["id"]),
        )
        fixed_stories += 1

conn.commit()
print(f"Fixed from story coords: {fixed_stories}", flush=True)
print(f"Remaining null: {len(remaining) - fixed_stories}", flush=True)
conn.close()
