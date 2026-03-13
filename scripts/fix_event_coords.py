"""Fix events where location name and coordinates are inconsistent.

Uses the most common location name among event stories, then takes
the median coords only from stories with that location name.

Run on VM:
    sudo -u thisminute /opt/thisminute/venv/bin/python /opt/thisminute/scripts/fix_event_coords.py
"""
import sqlite3
import os
import math

DB = os.environ.get("DB_PATH", "/opt/thisminute/data/thisminute.db")

def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    # Get all active multi-story events with coordinates
    events = conn.execute(
        """SELECT id, title, primary_location, primary_lat, primary_lon, story_count
        FROM events
        WHERE merged_into IS NULL AND status != 'resolved'
        AND story_count >= 2
        AND primary_lat IS NOT NULL AND primary_lon IS NOT NULL"""
    ).fetchall()

    print(f"Checking {len(events)} multi-story events with coordinates...", flush=True)
    fixed = 0

    for event in events:
        eid = event["id"]
        # Get all story locations for this event
        coord_rows = conn.execute(
            """SELECT s.lat, s.lon, s.location_name FROM stories s
            JOIN event_stories es ON s.id = es.story_id
            WHERE es.event_id = ? AND s.lat IS NOT NULL AND s.location_name IS NOT NULL""",
            (eid,),
        ).fetchall()

        if len(coord_rows) < 3:
            continue

        # Find most common location name
        loc_counts = {}
        for r in coord_rows:
            name = r["location_name"]
            if name:
                loc_counts[name] = loc_counts.get(name, 0) + 1

        if not loc_counts:
            continue

        best_loc = max(loc_counts, key=loc_counts.get)

        # Get median coords from stories with that location
        loc_rows = [r for r in coord_rows if r["location_name"] == best_loc]
        if not loc_rows:
            continue

        lats = sorted(r["lat"] for r in loc_rows)
        lons = sorted(r["lon"] for r in loc_rows)
        correct_lat = lats[len(lats) // 2]
        correct_lon = lons[len(lons) // 2]

        # Check if current coords are far from correct coords
        dist = haversine_km(event["primary_lat"], event["primary_lon"], correct_lat, correct_lon)

        if dist > 500:  # More than 500km off
            print(f"  [{eid}] {event['title'][:50]}", flush=True)
            print(f"    Was: ({event['primary_lat']:.2f},{event['primary_lon']:.2f}) {event['primary_location'][:40]}", flush=True)
            print(f"    Now: ({correct_lat:.2f},{correct_lon:.2f}) {best_loc[:40]}  [dist={dist:.0f}km]", flush=True)
            conn.execute(
                "UPDATE events SET primary_location=?, primary_lat=?, primary_lon=? WHERE id=?",
                (best_loc, correct_lat, correct_lon, eid),
            )
            fixed += 1

    conn.commit()
    print(f"\nFixed {fixed} events with mismatched coordinates", flush=True)

    # Also fix events with null coordinates but a location name
    null_coords = conn.execute(
        """SELECT id, title, primary_location FROM events
        WHERE merged_into IS NULL AND status != 'resolved'
        AND story_count >= 2
        AND primary_location IS NOT NULL AND primary_location != ''
        AND (primary_lat IS NULL OR primary_lon IS NULL)"""
    ).fetchall()

    if null_coords:
        print(f"\n{len(null_coords)} events with location name but no coords — fixing from stories...", flush=True)
        fixed_null = 0
        for event in null_coords:
            eid = event["id"]
            # Try to get coords from stories
            row = conn.execute(
                """SELECT s.lat, s.lon, s.location_name FROM stories s
                JOIN event_stories es ON s.id = es.story_id
                WHERE es.event_id = ? AND s.lat IS NOT NULL
                LIMIT 1""",
                (eid,),
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE events SET primary_lat=?, primary_lon=? WHERE id=?",
                    (row["lat"], row["lon"], eid),
                )
                fixed_null += 1
        conn.commit()
        print(f"Fixed {fixed_null} events with null coordinates", flush=True)

    conn.close()


if __name__ == "__main__":
    main()
