"""Backfill is_opinion column from extraction_json.

The is_opinion column was added via ALTER TABLE as TEXT DEFAULT 0,
so old rows have 0 even if the LLM extraction JSON says true.
This script reads the JSON blob and sets the column correctly.
"""
import json
import sqlite3
import sys

db_path = sys.argv[1] if len(sys.argv) > 1 else "data/thisminute.db"
conn = sqlite3.connect(db_path)

rows = conn.execute(
    "SELECT story_id, extraction_json, is_opinion FROM story_extractions"
).fetchall()

fixed = 0
for story_id, ext_json, current_val in rows:
    if not ext_json:
        continue
    try:
        ext = json.loads(ext_json)
    except (json.JSONDecodeError, TypeError):
        continue
    correct = 1 if ext.get("is_opinion") in (True, 1, "true", "True") else 0
    # Fix if current value doesn't match (handles string "0"/"1", None, etc.)
    if current_val != correct:
        conn.execute(
            "UPDATE story_extractions SET is_opinion = ? WHERE story_id = ?",
            (correct, story_id),
        )
        fixed += 1

conn.commit()
total = len(rows)
print(f"Checked {total} rows, fixed {fixed} is_opinion values", flush=True)

# Show distribution after fix
dist = conn.execute(
    "SELECT is_opinion, typeof(is_opinion), COUNT(*) FROM story_extractions GROUP BY is_opinion, typeof(is_opinion)"
).fetchall()
print("Distribution after fix:")
for val, typ, count in dist:
    print(f"  {repr(val)} ({typ}): {count}")

conn.close()
