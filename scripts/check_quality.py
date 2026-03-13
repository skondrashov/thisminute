"""Comprehensive data quality check: narratives, locations, extractions."""
import sqlite3
import os
import json

DB = os.environ.get("DB_PATH", "/opt/thisminute/data/thisminute.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# === NARRATIVES ===
print("=== NARRATIVE QUALITY ===")
narrs = conn.execute(
    """SELECT id, title, domain, status, story_count, event_count,
           LENGTH(title) as title_len
    FROM narratives WHERE status = 'active'
    ORDER BY story_count DESC"""
).fetchall()
print(f"Active narratives: {len(narrs)}")

# Title length distribution
long_titles = [n for n in narrs if n["title_len"] > 60]
print(f"  Titles > 60 chars: {len(long_titles)}")
for n in long_titles[:5]:
    print(f"    [{n['id']}] ({n['title_len']} chars) {n['title'][:80]}")

# Domain distribution
domains = {}
for n in narrs:
    d = n["domain"] or "none"
    domains[d] = domains.get(d, 0) + 1
print(f"  By domain: {domains}")

# Low story count narratives (might be stale)
low = [n for n in narrs if n["story_count"] <= 2]
print(f"  Low-story narratives (<=2): {len(low)}")

# Narratives with 0 events
zero_events = [n for n in narrs if n["event_count"] == 0]
print(f"  0-event narratives: {len(zero_events)}")

# === LOCATIONS ===
print("\n=== LOCATION QUALITY ===")

# Events with location but no coordinates
no_coords = conn.execute(
    """SELECT COUNT(*) as c FROM events
    WHERE merged_into IS NULL AND status != 'resolved' AND story_count >= 2
    AND primary_location IS NOT NULL AND primary_location != ''
    AND (primary_lat IS NULL OR primary_lon IS NULL)"""
).fetchone()["c"]
total_multi = conn.execute(
    """SELECT COUNT(*) as c FROM events
    WHERE merged_into IS NULL AND status != 'resolved' AND story_count >= 2"""
).fetchone()["c"]
no_loc = conn.execute(
    """SELECT COUNT(*) as c FROM events
    WHERE merged_into IS NULL AND status != 'resolved' AND story_count >= 2
    AND (primary_location IS NULL OR primary_location = '')"""
).fetchone()["c"]
print(f"Multi-story events: {total_multi}")
print(f"  Without location: {no_loc} ({100*no_loc/max(total_multi,1):.0f}%)")
print(f"  Location but no coords: {no_coords}")

# Location accuracy spot check
print("\n  Top 20 events - location check:")
top = conn.execute(
    """SELECT id, title, primary_location, primary_lat, primary_lon, story_count
    FROM events
    WHERE merged_into IS NULL AND status != 'resolved' AND story_count >= 5
    ORDER BY story_count DESC LIMIT 20"""
).fetchall()
for e in top:
    loc = e["primary_location"] or "(none)"
    lat = e["primary_lat"]
    lon = e["primary_lon"]
    coords = f"({lat:.1f},{lon:.1f})" if lat and lon else "(no coords)"
    print(f"  [{e['id']}] {e['story_count']:3d} stories | {loc[:25]:25s} {coords:15s} | {e['title'][:40]}")

# === EXTRACTION QUALITY ===
print("\n=== EXTRACTION QUALITY ===")

# Pending extractions
pending = conn.execute(
    "SELECT COUNT(*) as c FROM stories WHERE extraction_status = 'pending'"
).fetchone()["c"]
failed = conn.execute(
    "SELECT COUNT(*) as c FROM stories WHERE extraction_status = 'failed'"
).fetchone()["c"]
completed = conn.execute(
    "SELECT COUNT(*) as c FROM stories WHERE extraction_status = 'completed'"
).fetchone()["c"]
legacy = conn.execute(
    "SELECT COUNT(*) as c FROM stories WHERE extraction_status = 'legacy'"
).fetchone()["c"]
print(f"  Completed: {completed}")
print(f"  Pending: {pending}")
print(f"  Failed: {failed}")
print(f"  Legacy: {legacy}")

# Stories with extraction but no topics
no_topics = conn.execute(
    """SELECT COUNT(*) as c FROM story_extractions
    WHERE topics IS NULL OR topics = '' OR topics = '[]'"""
).fetchone()["c"]
total_ext = conn.execute("SELECT COUNT(*) as c FROM story_extractions").fetchone()["c"]
print(f"\n  Extractions total: {total_ext}")
print(f"  Without topics: {no_topics} ({100*no_topics/max(total_ext,1):.1f}%)")

# Stories with no event_signature
no_sig = conn.execute(
    """SELECT COUNT(*) as c FROM story_extractions
    WHERE event_signature IS NULL OR event_signature = ''"""
).fetchone()["c"]
print(f"  Without event_signature: {no_sig} ({100*no_sig/max(total_ext,1):.1f}%)")

# === PIPELINE HEALTH ===
print("\n=== PIPELINE HEALTH ===")

# Recent pipeline runs
print("  Stories scraped in last hour:")
for origin in ["rss", "gdelt"]:
    cnt = conn.execute(
        """SELECT COUNT(*) as c FROM stories
        WHERE origin = ? AND scraped_at > datetime('now', '-1 hour')""",
        (origin,),
    ).fetchone()["c"]
    print(f"    {origin}: {cnt}")

# Events analyzed in last hour
analyzed_1h = conn.execute(
    "SELECT COUNT(*) as c FROM events WHERE last_analyzed > datetime('now', '-1 hour')"
).fetchone()["c"]
analyzed_4h = conn.execute(
    "SELECT COUNT(*) as c FROM events WHERE last_analyzed > datetime('now', '-4 hours')"
).fetchone()["c"]
print(f"  Events analyzed last 1h: {analyzed_1h}")
print(f"  Events analyzed last 4h: {analyzed_4h}")

# World overview age
overview = conn.execute("SELECT generated_at FROM world_overview LIMIT 1").fetchone()
if overview:
    print(f"  World overview generated: {overview['generated_at']}")

conn.close()
