"""Second pass: fix events with smaller coordinate mismatches (200km+)."""
import sqlite3
import os
import math

DB = os.environ.get("DB_PATH", "/opt/thisminute/data/thisminute.db")

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    events = conn.execute(
        """SELECT id, title, primary_location, primary_lat, primary_lon, story_count
        FROM events
        WHERE merged_into IS NULL AND status != 'resolved'
        AND story_count >= 2
        AND primary_lat IS NOT NULL AND primary_lon IS NOT NULL"""
    ).fetchall()

    print(f"Checking {len(events)} events (200km threshold)...", flush=True)
    fixed = 0

    for event in events:
        eid = event["id"]
        coord_rows = conn.execute(
            """SELECT s.lat, s.lon, s.location_name FROM stories s
            JOIN event_stories es ON s.id = es.story_id
            WHERE es.event_id = ? AND s.lat IS NOT NULL AND s.location_name IS NOT NULL""",
            (eid,),
        ).fetchall()

        if len(coord_rows) < 3:
            continue

        loc_counts = {}
        for r in coord_rows:
            name = r["location_name"]
            if name:
                loc_counts[name] = loc_counts.get(name, 0) + 1

        if not loc_counts:
            continue

        best_loc = max(loc_counts, key=loc_counts.get)
        loc_rows = [r for r in coord_rows if r["location_name"] == best_loc]
        if not loc_rows:
            continue

        lats = sorted(r["lat"] for r in loc_rows)
        lons = sorted(r["lon"] for r in loc_rows)
        correct_lat = lats[len(lats) // 2]
        correct_lon = lons[len(lons) // 2]

        dist = haversine_km(event["primary_lat"], event["primary_lon"], correct_lat, correct_lon)

        if dist > 200:
            print(f"  [{eid}] {event['title'][:50]}", flush=True)
            print(f"    Was: ({event['primary_lat']:.2f},{event['primary_lon']:.2f}) {event['primary_location'][:35]}", flush=True)
            print(f"    Now: ({correct_lat:.2f},{correct_lon:.2f}) {best_loc[:35]}  [{dist:.0f}km]", flush=True)
            conn.execute(
                "UPDATE events SET primary_location=?, primary_lat=?, primary_lon=? WHERE id=?",
                (best_loc, correct_lat, correct_lon, eid),
            )
            fixed += 1

    conn.commit()
    print(f"\nFixed {fixed} events", flush=True)
    conn.close()


if __name__ == "__main__":
    main()
