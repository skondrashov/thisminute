"""Investigate junk events that have accumulated many stories."""
import sqlite3
import os

DB = os.environ.get("DB_PATH", "/opt/thisminute/data/thisminute.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# Check the two known junk events
for eid in [26158, 13383]:
    event = conn.execute("SELECT * FROM events WHERE id=?", (eid,)).fetchone()
    if not event:
        continue
    print(f"=== Event [{eid}] ===")
    print(f"  Title: {event['title']}")
    print(f"  Stories: {event['story_count']}, Status: {event['status']}")
    print(f"  Location: {event['primary_location']}")

    # Check story sources
    stories = conn.execute(
        """SELECT s.source, s.title, s.origin FROM stories s
        JOIN event_stories es ON s.id = es.story_id
        WHERE es.event_id = ?
        ORDER BY s.scraped_at DESC LIMIT 10""",
        (eid,),
    ).fetchall()
    sources = {}
    for s in stories:
        src = s["source"] or "unknown"
        sources[src] = sources.get(src, 0) + 1
        if len(sources) <= 5:
            print(f"    [{s['origin']}] {src}: {s['title'][:55]}")

    source_counts = conn.execute(
        """SELECT s.source, COUNT(*) as cnt FROM stories s
        JOIN event_stories es ON s.id = es.story_id
        WHERE es.event_id = ?
        GROUP BY s.source ORDER BY cnt DESC""",
        (eid,),
    ).fetchall()
    print(f"  Source breakdown:")
    for sc in source_counts:
        print(f"    {sc['source']}: {sc['cnt']}")

# Find other potential junk events (high story count, suspicious patterns)
print("\n\n=== Potential junk events (high story count, non-news patterns) ===")
rows = conn.execute(
    """SELECT e.id, e.title, e.story_count, e.primary_location FROM events e
    WHERE e.merged_into IS NULL AND e.status != 'resolved'
    AND e.story_count >= 10
    ORDER BY e.story_count DESC LIMIT 50"""
).fetchall()

junk_keywords = ["report", "flash", "podcast", "radio", "programming",
                 "newsletter", "bulletin", "briefing", "roundup",
                 "recap", "podcast", "audio"]
for r in rows:
    title_lower = r["title"].lower()
    is_suspicious = any(kw in title_lower for kw in junk_keywords)
    if is_suspicious:
        print(f"  [{r['id']}] {r['story_count']:3d} stories | {r['title'][:55]}")

conn.close()
