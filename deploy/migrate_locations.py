#!/usr/bin/env python3
"""Re-geocode country-level stories to city-level using improved NER."""
import sqlite3
import sys
import time

sys.path.insert(0, "/opt/thisminute")
from src.ner import extract_locations, pick_primary_location, _COUNTRY_SET
from geopy.geocoders import Nominatim

geocoder = Nominatim(user_agent="thisminute-news-map/1.0", timeout=10)

conn = sqlite3.connect("/opt/thisminute/data/thisminute.db", timeout=30)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA busy_timeout=10000")

# Pre-load existing geocode cache
geo_cache = {}
for row in conn.execute(
    "SELECT location_name, lat, lon FROM geocode_cache WHERE lat IS NOT NULL"
).fetchall():
    geo_cache[row["location_name"]] = (row["lat"], row["lon"])

rows = conn.execute(
    "SELECT id, title, summary, location_name FROM stories WHERE lat IS NOT NULL"
).fetchall()

upgraded = 0
for row in rows:
    old_loc = row["location_name"]
    if old_loc not in _COUNTRY_SET:
        continue

    title = row["title"] or ""
    summary = row["summary"] or ""
    text = title + ". " + summary
    entities = extract_locations(text)
    new_loc = pick_primary_location(entities)

    if not new_loc or new_loc == old_loc or new_loc in _COUNTRY_SET:
        continue

    # Look up coordinates
    if new_loc in geo_cache:
        lat, lon = geo_cache[new_loc]
    else:
        time.sleep(1.1)  # Nominatim rate limit
        try:
            result = geocoder.geocode(new_loc, exactly_one=True, language="en")
        except Exception as e:
            print("  Geocode error for %s: %s" % (new_loc, e))
            continue
        if not result:
            continue
        lat, lon = result.latitude, result.longitude
        geo_cache[new_loc] = (lat, lon)

    conn.execute(
        "UPDATE stories SET location_name=?, lat=?, lon=? WHERE id=?",
        (new_loc, lat, lon, row["id"]),
    )
    upgraded += 1
    print("  %s -> %s (%.2f, %.2f)" % (old_loc, new_loc, lat, lon))

conn.commit()
conn.close()
print("")
print("Upgraded %d stories to city-level locations" % upgraded)
