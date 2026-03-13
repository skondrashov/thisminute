"""Check why Washington events are geocoding to NC instead of DC."""
import sqlite3
import os

DB = os.environ.get("DB_PATH", "/opt/thisminute/data/thisminute.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# Check event 15634's story locations
rows = conn.execute(
    """SELECT s.location_name, s.lat, s.lon, COUNT(*) as cnt
    FROM stories s
    JOIN event_stories es ON s.id = es.story_id
    WHERE es.event_id = 15634 AND s.lat IS NOT NULL
    GROUP BY s.location_name, s.lat, s.lon
    ORDER BY cnt DESC LIMIT 10"""
).fetchall()
print("=== Event 15634 story locations ===")
for r in rows:
    print(f"  {r['cnt']:3d}x {r['location_name'][:30]:30s} ({r['lat']:.2f},{r['lon']:.2f})")

# Check what "Washington" geocodes to in the cache
print("\n=== All Washington geocode cache entries ===")
rows = conn.execute(
    "SELECT * FROM geocode_cache WHERE location_name LIKE '%ashington%'"
).fetchall()
for r in rows:
    lat = r["lat"]
    lon = r["lon"]
    print(f"  '{r['location_name']}' -> ({lat},{lon}) {(r['display_name'] or '')[:50]}")

# What location strings show (35.8, -77.0)?
print("\n=== Stories with lat ~35.8, lon ~-77.0 ===")
rows = conn.execute(
    """SELECT location_name, COUNT(*) as cnt FROM stories
    WHERE lat BETWEEN 35.5 AND 36.0 AND lon BETWEEN -77.5 AND -76.5
    GROUP BY location_name ORDER BY cnt DESC LIMIT 10"""
).fetchall()
for r in rows:
    print(f"  {r['cnt']:4d}x {r['location_name']}")

conn.close()
