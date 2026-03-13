"""Check what's in the geocode cache for commonly misgeocoded locations."""
import sqlite3
import os

DB = os.environ.get("DB_PATH", "/opt/thisminute/data/thisminute.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# Check cache entries for Washington variants
print("=== Geocode cache: Washington variants ===")
rows = conn.execute(
    """SELECT location_name, lat, lon, display_name
    FROM geocode_cache WHERE location_name LIKE '%Washington%'
    ORDER BY location_name"""
).fetchall()
for r in rows:
    lat = r["lat"]
    lon = r["lon"]
    coords = f"({lat:.2f},{lon:.2f})" if lat else "(null)"
    print(f"  '{r['location_name']}' -> {coords} {(r['display_name'] or '')[:60]}")

# Check Beverly Hills
print("\n=== Geocode cache: Beverly Hills ===")
rows = conn.execute(
    """SELECT location_name, lat, lon, display_name
    FROM geocode_cache WHERE location_name LIKE '%Beverly Hills%'"""
).fetchall()
for r in rows:
    lat = r["lat"]
    lon = r["lon"]
    coords = f"({lat:.2f},{lon:.2f})" if lat else "(null)"
    print(f"  '{r['location_name']}' -> {coords} {(r['display_name'] or '')[:60]}")

# Check what primary_location strings events are using for Washington
print("\n=== Events with 'Washington' in primary_location ===")
rows = conn.execute(
    """SELECT primary_location, primary_lat, primary_lon, COUNT(*) as cnt
    FROM events
    WHERE merged_into IS NULL AND status != 'resolved'
    AND primary_location LIKE '%Washington%'
    GROUP BY primary_location, primary_lat, primary_lon
    ORDER BY cnt DESC LIMIT 15"""
).fetchall()
for r in rows:
    lat = r["primary_lat"]
    lon = r["primary_lon"]
    coords = f"({lat:.2f},{lon:.2f})" if lat else "(null)"
    print(f"  [{r['cnt']:3d}x] {r['primary_location'][:55]} -> {coords}")

# What location strings does the LLM extract for political events?
print("\n=== Story extractions: top location strings (political) ===")
rows = conn.execute(
    """SELECT se.locations, COUNT(*) as cnt
    FROM story_extractions se
    WHERE se.locations LIKE '%Washington%'
    GROUP BY se.locations
    ORDER BY cnt DESC LIMIT 10"""
).fetchall()
for r in rows:
    print(f"  [{r['cnt']:4d}x] {(r['locations'] or '')[:70]}")

# Events with no location (multi-story)
print("\n=== Multi-story events without location (sample) ===")
rows = conn.execute(
    """SELECT id, title, story_count FROM events
    WHERE merged_into IS NULL AND status != 'resolved' AND story_count >= 3
    AND (primary_location IS NULL OR primary_location = '')
    ORDER BY story_count DESC LIMIT 15"""
).fetchall()
for r in rows:
    print(f"  [{r['id']}] {r['story_count']} stories: {r['title'][:55]}")

conn.close()
