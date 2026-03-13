"""Check event analysis coverage."""
import sqlite3
import os

DB = os.environ.get("DB_PATH", "/opt/thisminute/data/thisminute.db")

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# Unanalyzed events
row = conn.execute(
    """SELECT COUNT(*) as total,
              SUM(CASE WHEN last_analyzed IS NULL THEN 1 ELSE 0 END) as unanalyzed,
              SUM(CASE WHEN story_count >= 2 AND last_analyzed IS NULL THEN 1 ELSE 0 END) as multi_unanalyzed
       FROM events WHERE merged_into IS NULL AND status != 'resolved'"""
).fetchone()
print(f"Active events: {row['total']}")
print(f"  Never analyzed: {row['unanalyzed']}")
print(f"  Multi-story, never analyzed: {row['multi_unanalyzed']}")

# Top unanalyzed multi-story events
rows = conn.execute(
    """SELECT id, title, story_count FROM events
       WHERE merged_into IS NULL AND status != 'resolved'
       AND story_count >= 2 AND last_analyzed IS NULL
       ORDER BY story_count DESC LIMIT 10"""
).fetchall()
if rows:
    print("\nTop unanalyzed multi-story events:")
    for r in rows:
        print(f"  [{r['id']}] ({r['story_count']} stories) {r['title'][:70]}")

# Check stale analyses (content changed since last analysis)
stale = conn.execute(
    """SELECT COUNT(*) as c FROM events
       WHERE merged_into IS NULL AND status != 'resolved'
       AND last_analyzed IS NOT NULL
       AND last_analyzed < last_updated"""
).fetchone()['c']
print(f"\nStale analyses (last_updated > last_analyzed): {stale}")

# Event analyzer rate
from datetime import datetime
analyzed_24h = conn.execute(
    """SELECT COUNT(*) as c FROM events
       WHERE last_analyzed > datetime('now', '-1 day')"""
).fetchone()['c']
analyzed_1h = conn.execute(
    """SELECT COUNT(*) as c FROM events
       WHERE last_analyzed > datetime('now', '-1 hour')"""
).fetchone()['c']
print(f"\nAnalyzed in last hour: {analyzed_1h}")
print(f"Analyzed in last 24h: {analyzed_24h}")

conn.close()
