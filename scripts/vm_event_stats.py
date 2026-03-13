#!/usr/bin/env python3
"""Query event statistics from the thisminute database."""
import sqlite3
import sys

DB_PATH = "/opt/thisminute/data/thisminute.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    print("=" * 70)
    print("QUERY 1: Events by story_count (active, not merged)")
    print("=" * 70)
    c.execute("""
        SELECT story_count, COUNT(*) as num_events
        FROM events
        WHERE merged_into IS NULL AND status != 'resolved'
        GROUP BY story_count
        ORDER BY story_count
        LIMIT 20
    """)
    print(f"{'story_count':>12} | {'num_events':>10}")
    print("-" * 26)
    for row in c.fetchall():
        print(f"{row[0]:>12} | {row[1]:>10}")

    print()
    print("=" * 70)
    print("QUERY 2: Total active events, single-story count and percentage")
    print("=" * 70)
    c.execute("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN story_count = 1 THEN 1 ELSE 0 END) as single_story,
               ROUND(100.0 * SUM(CASE WHEN story_count = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) as pct_single
        FROM events
        WHERE merged_into IS NULL AND status != 'resolved'
    """)
    row = c.fetchone()
    print(f"Total active events:  {row[0]}")
    print(f"Single-story events:  {row[1]}")
    print(f"Percentage single:    {row[2]}%")

    print()
    print("=" * 70)
    print("QUERY 3: Example single-story event signatures (15 most recent)")
    print("=" * 70)
    c.execute("""
        SELECT e.id, e.title, e.story_count, se.event_signature
        FROM events e
        JOIN event_stories es ON e.id = es.event_id
        JOIN story_extractions se ON es.story_id = se.story_id
        WHERE e.merged_into IS NULL AND e.status != 'resolved' AND e.story_count = 1
        ORDER BY e.id DESC
        LIMIT 15
    """)
    for row in c.fetchall():
        title = (row[1] or "")[:60]
        sig = (row[3] or "")[:50]
        print(f"  Event {row[0]:>5}: {title}")
        print(f"           sig: {sig}")
        print()

    print("=" * 70)
    print("QUERY 4: Signatures assigned to multiple events (potential merges)")
    print("=" * 70)
    c.execute("""
        SELECT se.event_signature,
               COUNT(DISTINCT es.event_id) as event_count,
               GROUP_CONCAT(DISTINCT es.event_id) as event_ids
        FROM story_extractions se
        JOIN event_stories es ON se.story_id = es.story_id
        JOIN events e ON es.event_id = e.id
        WHERE e.merged_into IS NULL AND e.status != 'resolved'
        GROUP BY se.event_signature
        HAVING event_count > 1
        ORDER BY event_count DESC
        LIMIT 15
    """)
    for row in c.fetchall():
        sig = (row[0] or "")[:70]
        print(f"  Signature: {sig}")
        print(f"  Events ({row[1]}): {row[2]}")
        print()

    conn.close()

if __name__ == "__main__":
    main()
