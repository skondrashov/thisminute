"""Fix misgeocoded locations in cache, stories, events, and registry.

Clears geocode cache entries for locations that are now hardcoded,
then updates all stories/events/registry that used the wrong coordinates.

Safe to run multiple times (idempotent).
"""

import sqlite3
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.geocoder import _HARDCODED


def fix_geocode_cache(conn):
    """Remove cached entries for locations we now have hardcoded."""
    deleted = 0
    for name, coords in _HARDCODED.items():
        row = conn.execute(
            "SELECT lat, lon FROM geocode_cache WHERE location_name = ?",
            (name,),
        ).fetchone()
        if row is None:
            continue
        # Check if cached lat/lon differs significantly from hardcoded
        if row[0] is not None:
            lat_diff = abs(row[0] - coords["lat"])
            lon_diff = abs(row[1] - coords["lon"])
            if lat_diff > 1.0 or lon_diff > 1.0:
                print(f"  FIXING cache: {name}: ({row[0]:.2f}, {row[1]:.2f}) -> ({coords['lat']:.2f}, {coords['lon']:.2f})", flush=True)
                conn.execute("DELETE FROM geocode_cache WHERE location_name = ?", (name,))
                deleted += 1
    conn.commit()
    print(f"Cleared {deleted} bad geocode cache entries", flush=True)


def fix_stories(conn):
    """Fix story coordinates for hardcoded locations."""
    fixed = 0
    for name, coords in _HARDCODED.items():
        rows = conn.execute(
            "SELECT id, lat, lon FROM stories WHERE location_name = ? AND lat IS NOT NULL",
            (name,),
        ).fetchall()
        for row in rows:
            lat_diff = abs(row[1] - coords["lat"])
            lon_diff = abs(row[2] - coords["lon"])
            if lat_diff > 1.0 or lon_diff > 1.0:
                conn.execute(
                    "UPDATE stories SET lat = ?, lon = ? WHERE id = ?",
                    (coords["lat"], coords["lon"], row[0]),
                )
                fixed += 1
    conn.commit()
    print(f"Fixed {fixed} story coordinates", flush=True)


def fix_events(conn):
    """Fix event coordinates for hardcoded locations."""
    fixed = 0
    for name, coords in _HARDCODED.items():
        rows = conn.execute(
            "SELECT id, primary_lat, primary_lon FROM events WHERE primary_location = ? AND primary_lat IS NOT NULL",
            (name,),
        ).fetchall()
        for row in rows:
            lat_diff = abs(row[1] - coords["lat"])
            lon_diff = abs(row[2] - coords["lon"])
            if lat_diff > 1.0 or lon_diff > 1.0:
                conn.execute(
                    "UPDATE events SET primary_lat = ?, primary_lon = ? WHERE id = ?",
                    (coords["lat"], coords["lon"], row[0]),
                )
                fixed += 1
    conn.commit()
    print(f"Fixed {fixed} event coordinates", flush=True)


def fix_registry(conn):
    """Fix registry event coordinates for hardcoded locations."""
    fixed = 0
    for name, coords in _HARDCODED.items():
        rows = conn.execute(
            "SELECT id, primary_lat, primary_lon FROM event_registry WHERE primary_location = ? AND primary_lat IS NOT NULL",
            (name,),
        ).fetchall()
        for row in rows:
            lat_diff = abs(row[1] - coords["lat"])
            lon_diff = abs(row[2] - coords["lon"])
            if lat_diff > 1.0 or lon_diff > 1.0:
                conn.execute(
                    "UPDATE event_registry SET primary_lat = ?, primary_lon = ? WHERE id = ?",
                    (coords["lat"], coords["lon"], row[0]),
                )
                fixed += 1
    conn.commit()
    print(f"Fixed {fixed} registry event coordinates", flush=True)


if __name__ == "__main__":
    db_path = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "..", "data", "thisminute.db"))
    print(f"Fixing geocode data in {db_path}", flush=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    fix_geocode_cache(conn)
    fix_stories(conn)
    fix_events(conn)
    fix_registry(conn)
    conn.close()
    print("Done!", flush=True)
