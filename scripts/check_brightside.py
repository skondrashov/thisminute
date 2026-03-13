"""Check bright side scoring quality and positive content coverage."""
import sqlite3
import os
import json

DB = os.environ.get("DB_PATH", "/opt/thisminute/data/thisminute.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# Bright side score distribution
print("=== Bright side score distribution (recent extractions) ===")
rows = conn.execute(
    """SELECT bright_side_score, COUNT(*) as cnt FROM story_extractions
    WHERE bright_side_score IS NOT NULL
    GROUP BY bright_side_score ORDER BY bright_side_score DESC"""
).fetchall()
for r in rows:
    print(f"  Score {r['bright_side_score']}: {r['cnt']}")

# High bright-side stories (positive world)
print("\n=== Top bright-side stories (last 24h) ===")
rows = conn.execute(
    """SELECT s.title, s.source, se.bright_side_score, se.bright_side_category, se.bright_side_headline
    FROM stories s
    JOIN story_extractions se ON s.id = se.story_id
    WHERE se.bright_side_score >= 4 AND s.scraped_at > datetime('now', '-24 hours')
    ORDER BY se.bright_side_score DESC, s.scraped_at DESC LIMIT 15"""
).fetchall()
for r in rows:
    cat = r["bright_side_category"] or "none"
    headline = r["bright_side_headline"] or ""
    print(f"  [{r['bright_side_score']}] {r['source']}: {r['title'][:50]}")
    if headline:
        print(f"    Headline: {headline[:55]}")

# Positive narratives
print("\n=== Positive domain narratives ===")
rows = conn.execute(
    """SELECT id, title, story_count, event_count FROM narratives
    WHERE status = 'active' AND domain = 'positive'
    ORDER BY story_count DESC"""
).fetchall()
for r in rows:
    print(f"  [{r['id']}] {r['story_count']:4d} stories | {r['title'][:50]}")

# Event type distribution
print("\n=== Event type distribution (active, 2+ stories) ===")
rows = conn.execute(
    """SELECT event_type, COUNT(*) as cnt,
       SUM(story_count) as total_stories
    FROM events
    WHERE merged_into IS NULL AND status != 'resolved' AND story_count >= 2
    GROUP BY event_type ORDER BY cnt DESC"""
).fetchall()
for r in rows:
    etype = r["event_type"] or "NULL"
    print(f"  {etype:15s}: {r['cnt']:4d} events, {r['total_stories']:5d} stories")

conn.close()
