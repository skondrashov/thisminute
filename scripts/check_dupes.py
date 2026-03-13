"""Check duplicate event clusters and singleton age distribution."""
import sqlite3
import os

DB = os.environ.get("DB_PATH", "/opt/thisminute/data/thisminute.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# Check the duplicate signatures - why didn't they merge?
dupe_rows = conn.execute(
    """SELECT se.event_signature,
           GROUP_CONCAT(DISTINCT es.event_id) as event_ids,
           COUNT(DISTINCT es.event_id) as event_count
    FROM story_extractions se
    JOIN event_stories es ON se.story_id = es.story_id
    JOIN events e ON es.event_id = e.id
    WHERE e.merged_into IS NULL AND e.status != 'resolved'
    AND se.event_signature IS NOT NULL AND se.event_signature != ''
    GROUP BY se.event_signature
    HAVING COUNT(DISTINCT es.event_id) > 1
    ORDER BY event_count DESC"""
).fetchall()

print(f"=== {len(dupe_rows)} duplicate signatures ===")
for row in dupe_rows[:10]:
    sig = row["event_signature"][:40]
    eids = [int(x) for x in row["event_ids"].split(",")]
    counts = []
    for eid in eids[:6]:
        r = conn.execute("SELECT story_count FROM events WHERE id=?", (eid,)).fetchone()
        if r:
            counts.append(f"{eid}:{r['story_count']}")
    total = sum(int(c.split(":")[1]) for c in counts)
    print(f"  {sig}... events={row['event_count']} total_stories={total} [{', '.join(counts)}]")

# Singleton age distribution
print("\n=== Singleton age distribution ===")
for hours in [6, 12, 24, 48, 72, 168]:
    cnt = conn.execute(
        """SELECT COUNT(*) as c FROM events
        WHERE merged_into IS NULL AND status != 'resolved' AND story_count = 1
        AND first_seen > datetime('now', '-' || ? || ' hours')""",
        (hours,),
    ).fetchone()["c"]
    print(f"  < {hours}h: {cnt}")

old = conn.execute(
    """SELECT COUNT(*) as c FROM events
    WHERE merged_into IS NULL AND status != 'resolved' AND story_count = 1
    AND first_seen < datetime('now', '-48 hours')"""
).fetchone()["c"]
print(f"  > 48h (should be resolved): {old}")

# Multi-story events not analyzed
unanalyzed = conn.execute(
    """SELECT COUNT(*) as c FROM events
    WHERE merged_into IS NULL AND status != 'resolved'
    AND story_count >= 2 AND last_analyzed IS NULL"""
).fetchone()["c"]
print(f"\n=== Multi-story events not yet analyzed: {unanalyzed} ===")

# Events with vague titles
print("\n=== Events with vague/junk titles (active, multi-story) ===")
vague = conn.execute(
    """SELECT id, title, story_count FROM events
    WHERE merged_into IS NULL AND status != 'resolved' AND story_count >= 3
    AND (title LIKE '%Miscellaneous%' OR title LIKE '%Mixed%' OR title LIKE '%Various%'
         OR title LIKE '%Data Quality%' OR title LIKE '%Regional News%')
    ORDER BY story_count DESC LIMIT 15"""
).fetchall()
for r in vague:
    print(f"  [{r['id']}] {r['story_count']} stories: {r['title'][:60]}")
if not vague:
    print("  None found!")

# Singleton extraction and signature analysis
print("\n=== Singleton extraction status ===")
has_sig = conn.execute(
    """SELECT COUNT(DISTINCT e.id) as c FROM events e
    JOIN event_stories es ON e.id = es.event_id
    JOIN story_extractions se ON es.story_id = se.story_id
    WHERE e.merged_into IS NULL AND e.status != 'resolved' AND e.story_count = 1
    AND se.event_signature IS NOT NULL AND se.event_signature != '' """
).fetchone()["c"]
no_sig = conn.execute(
    """SELECT COUNT(DISTINCT e.id) as c FROM events e
    JOIN event_stories es ON e.id = es.event_id
    JOIN story_extractions se ON es.story_id = se.story_id
    WHERE e.merged_into IS NULL AND e.status != 'resolved' AND e.story_count = 1
    AND (se.event_signature IS NULL OR se.event_signature = '') """
).fetchone()["c"]
no_ext = conn.execute(
    """SELECT COUNT(*) as c FROM events e
    WHERE e.merged_into IS NULL AND e.status != 'resolved' AND e.story_count = 1
    AND NOT EXISTS (
        SELECT 1 FROM event_stories es
        JOIN story_extractions se ON es.story_id = se.story_id
        WHERE es.event_id = e.id
    )"""
).fetchone()["c"]
print(f"  With signature: {has_sig}")
print(f"  Without signature: {no_sig}")
print(f"  No extraction at all: {no_ext}")

# Sample recent singletons with their signatures
print("\n=== Recent singletons with signatures (20 sample) ===")
rows = conn.execute(
    """SELECT e.id, e.title,
        (SELECT se.event_signature FROM story_extractions se
         JOIN event_stories es ON se.story_id = es.story_id
         WHERE es.event_id = e.id LIMIT 1) as sig
    FROM events e
    WHERE e.merged_into IS NULL AND e.status != 'resolved' AND e.story_count = 1
    ORDER BY e.first_seen DESC LIMIT 20"""
).fetchall()
for r in rows:
    sig = (r["sig"] or "(none)")[:35]
    print(f"  [{r['id']}] sig={sig} | {r['title'][:45]}")

# Check if any singletons share signatures with multi-story events
print("\n=== Singletons whose sig matches a multi-story event (should have merged) ===")
missed = conn.execute(
    """SELECT e1.id as singleton_id, e1.title as s_title,
           se1.event_signature as sig,
           e2.id as multi_id, e2.story_count as multi_count
    FROM events e1
    JOIN event_stories es1 ON e1.id = es1.event_id
    JOIN story_extractions se1 ON es1.story_id = se1.story_id
    JOIN story_extractions se2 ON se1.event_signature = se2.event_signature AND se1.story_id != se2.story_id
    JOIN event_stories es2 ON se2.story_id = es2.story_id
    JOIN events e2 ON es2.event_id = e2.id
    WHERE e1.merged_into IS NULL AND e1.status != 'resolved' AND e1.story_count = 1
    AND e2.merged_into IS NULL AND e2.status != 'resolved' AND e2.story_count > 1
    AND se1.event_signature IS NOT NULL AND se1.event_signature != ''
    LIMIT 20"""
).fetchall()
if missed:
    for r in missed:
        print(f"  Singleton [{r['singleton_id']}] sig={r['sig'][:30]} -> Event [{r['multi_id']}] ({r['multi_count']} stories)")
else:
    print("  None found — exact match working correctly!")

conn.close()
