#!/usr/bin/env python3
"""One-time migration: add bbox columns to geocode_cache and backfill from Nominatim.

Run on the VM with the service stopped:
    sudo systemctl stop thisminute
    cd /opt/thisminute
    python3 -m deploy.migrate_geocache_bbox
    sudo systemctl start thisminute

Takes ~3-4 minutes (1 req/sec to Nominatim for ~200 entries).
"""

import sqlite3
import sys
import time

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

DB_PATH = "/opt/thisminute/data/thisminute.db"
USER_AGENT = "thisminute-news/1.0"
DELAY = 1.1  # seconds between Nominatim requests


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else DB_PATH
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row

    # Step 1: Add bbox columns if they don't exist
    for col in ("bbox_south", "bbox_north", "bbox_west", "bbox_east"):
        try:
            conn.execute(f"ALTER TABLE geocode_cache ADD COLUMN {col} REAL")
            print(f"  Added column {col}", flush=True)
        except sqlite3.OperationalError:
            print(f"  Column {col} already exists", flush=True)
    conn.commit()

    # Step 2: Find entries that need bbox backfill
    rows = conn.execute(
        "SELECT location_name, lat, lon FROM geocode_cache "
        "WHERE lat IS NOT NULL AND bbox_south IS NULL"
    ).fetchall()
    print(f"\n{len(rows)} entries need bbox backfill", flush=True)

    if not rows:
        # Step 3: Also find NER entities not yet in geocode_cache
        ner_rows = conn.execute("SELECT ner_entities FROM stories WHERE ner_entities IS NOT NULL").fetchall()
        import json
        all_names = set()
        for r in ner_rows:
            try:
                entities = json.loads(r["ner_entities"])
                for e in entities:
                    if isinstance(e, str):
                        all_names.add(e)
                    elif isinstance(e, dict) and "text" in e:
                        all_names.add(e["text"])
            except (json.JSONDecodeError, TypeError):
                pass

        cached = set(
            r["location_name"]
            for r in conn.execute("SELECT location_name FROM geocode_cache").fetchall()
        )
        missing = all_names - cached
        if missing:
            print(f"\n{len(missing)} NER entities not yet geocoded", flush=True)
        else:
            print("\nAll NER entities already geocoded. Nothing to do.", flush=True)
            conn.close()
            return

        rows = [{"location_name": n} for n in missing]

    geocoder = Nominatim(user_agent=USER_AGENT, timeout=10)
    success = 0
    failed = 0

    for i, row in enumerate(rows):
        name = row["location_name"] if isinstance(row, dict) else row["location_name"]
        print(f"  [{i+1}/{len(rows)}] {name} ... ", end="", flush=True)

        time.sleep(DELAY)
        try:
            result = geocoder.geocode(name, exactly_one=True, language="en")
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            print(f"ERROR: {e}", flush=True)
            failed += 1
            continue
        except Exception as e:
            print(f"ERROR: {e}", flush=True)
            failed += 1
            continue

        if result is None:
            print("not found", flush=True)
            failed += 1
            continue

        bbox_s = bbox_n = bbox_w = bbox_e = None
        if hasattr(result, "raw") and isinstance(result.raw, dict):
            bb = result.raw.get("boundingbox")
            if bb and len(bb) == 4:
                try:
                    bbox_s = float(bb[0])
                    bbox_n = float(bb[1])
                    bbox_w = float(bb[2])
                    bbox_e = float(bb[3])
                except (ValueError, TypeError):
                    pass

        importance = None
        if hasattr(result, "raw") and isinstance(result.raw, dict):
            importance = result.raw.get("importance")

        conn.execute(
            """INSERT OR REPLACE INTO geocode_cache
               (location_name, lat, lon, display_name, importance, cached_at,
                bbox_south, bbox_north, bbox_west, bbox_east)
               VALUES (?, ?, ?, ?, ?, datetime('now'), ?, ?, ?, ?)""",
            (name, result.latitude, result.longitude, result.address,
             importance, bbox_s, bbox_n, bbox_w, bbox_e),
        )
        conn.commit()

        bbox_info = f"bbox=[{bbox_s},{bbox_n},{bbox_w},{bbox_e}]" if bbox_s is not None else "no bbox"
        print(f"({result.latitude:.2f}, {result.longitude:.2f}) {bbox_info}", flush=True)
        success += 1

    print(f"\nDone: {success} succeeded, {failed} failed", flush=True)
    conn.close()


if __name__ == "__main__":
    main()
