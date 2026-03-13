"""Check events with location name but null coordinates."""
import sqlite3
import os

DB = os.environ.get("DB_PATH", "/opt/thisminute/data/thisminute.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

rows = conn.execute(
    """SELECT id, title, primary_location, story_count FROM events
    WHERE merged_into IS NULL AND status != 'resolved'
    AND story_count >= 2
    AND primary_location IS NOT NULL AND primary_location != ''
    AND (primary_lat IS NULL OR primary_lon IS NULL)
    ORDER BY story_count DESC LIMIT 30"""
).fetchall()

print(f"=== Events with location but no coords ({len(rows)} shown) ===")
for r in rows:
    loc = r["primary_location"]
    print(f"  [{r['id']}] {r['story_count']:3d} stories | loc='{loc[:40]}' | {r['title'][:40]}")

    # Check if any stories have coords
    has_coords = conn.execute(
        """SELECT COUNT(*) as c FROM stories s
        JOIN event_stories es ON s.id = es.story_id
        WHERE es.event_id = ? AND s.lat IS NOT NULL""",
        (r["id"],),
    ).fetchone()["c"]
    if has_coords > 0:
        print(f"    -> {has_coords} stories have coords (event should too!)")

# Check geocode cache for these locations
print("\n=== Checking geocode cache for null-coord locations ===")
for r in rows[:15]:
    loc = r["primary_location"]
    cached = conn.execute(
        "SELECT lat, lon FROM geocode_cache WHERE location_name = ?",
        (loc,),
    ).fetchone()
    if cached:
        if cached["lat"]:
            print(f"  '{loc[:35]}' -> ({cached['lat']:.2f},{cached['lon']:.2f}) CACHED OK (event is stale)")
        else:
            print(f"  '{loc[:35]}' -> NULL (failed geocode in cache)")
    else:
        print(f"  '{loc[:35]}' -> NOT IN CACHE")

conn.close()
