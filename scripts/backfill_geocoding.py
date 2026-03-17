#!/usr/bin/env python3
"""Backfill geocoding for stories that have LLM-extracted locations but no lat/lon.

Uses the same logic as the pipeline's _geocode_from_extractions() but runs
as a one-time batch over all historical ungeolocated stories.

Usage:
    python scripts/backfill_geocoding.py              # dry run (report only)
    python scripts/backfill_geocoding.py --apply       # actually geocode
    python scripts/backfill_geocoding.py --apply -n 500  # limit to 500 stories
"""

import json
import sqlite3
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.geocoder import geocode_location

# Role priority for LLM-extracted locations
_ROLE_PRIORITY = {"event_location": 0, "origin": 1, "destination": 2, "mentioned": 3}


def backfill(db_path: str = "data/thisminute.db", dry_run: bool = True, limit: int = 5000):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """SELECT s.id, s.title, se.extraction_json
           FROM stories s
           JOIN story_extractions se ON se.story_id = s.id
           WHERE s.lat IS NULL
             AND se.location_type = 'terrestrial'
           ORDER BY s.id DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()

    print(f"Found {len(rows)} ungeolocated terrestrial stories")
    if not rows:
        conn.close()
        return

    geocoded = 0
    skipped_no_locs = 0
    failed = 0

    for i, row in enumerate(rows):
        try:
            extraction = json.loads(row["extraction_json"])
        except (json.JSONDecodeError, TypeError):
            continue

        locations = extraction.get("locations") or []
        if not locations:
            skipped_no_locs += 1
            continue

        locations.sort(key=lambda loc: _ROLE_PRIORITY.get(loc.get("role", "mentioned"), 3))

        found = False
        for loc in locations:
            name = loc.get("name", "").strip()
            if not name or len(name) < 2:
                continue

            if dry_run:
                title = row['title'][:60].encode('ascii', 'replace').decode()
                print(f"  [{row['id']}] Would try: {name} (role={loc.get('role')}) for: {title}")
                found = True
                break
            else:
                geo = geocode_location(name)
                if geo:
                    conn.execute(
                        """UPDATE stories
                           SET lat = ?, lon = ?, location_name = ?, geocode_confidence = ?
                           WHERE id = ?""",
                        (geo["lat"], geo["lon"], name, geo.get("importance", 0.5), row["id"]),
                    )
                    geocoded += 1
                    found = True
                    if geocoded % 50 == 0:
                        conn.commit()
                        print(f"  ... {geocoded} geocoded so far ({i+1}/{len(rows)} processed)")
                    break

        if not found and not dry_run:
            failed += 1

    if not dry_run and geocoded > 0:
        conn.commit()

    conn.close()

    print(f"\nResults:")
    print(f"  Processed: {len(rows)}")
    print(f"  No locations in extraction: {skipped_no_locs}")
    if dry_run:
        print(f"  Would attempt geocoding: {len(rows) - skipped_no_locs}")
    else:
        print(f"  Geocoded: {geocoded}")
        print(f"  Failed: {failed}")


if __name__ == "__main__":
    dry = "--apply" not in sys.argv
    limit = 5000
    if "-n" in sys.argv:
        idx = sys.argv.index("-n")
        if idx + 1 < len(sys.argv):
            limit = int(sys.argv[idx + 1])

    if dry:
        print("DRY RUN (pass --apply to commit changes)\n")
    else:
        print(f"APPLYING geocoding (limit={limit})\n")

    backfill(dry_run=dry, limit=limit)
