"""Check narrative quality across all domains."""
import sqlite3
import os

DB = os.environ.get("DB_PATH", "/opt/thisminute/data/thisminute.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

for domain in ["news", "sports", "entertainment", "positive"]:
    print(f"\n=== {domain.upper()} NARRATIVES ===")
    narrs = conn.execute(
        """SELECT id, title, story_count, event_count, description
        FROM narratives WHERE status = 'active' AND domain = ?
        ORDER BY story_count DESC""",
        (domain,),
    ).fetchall()
    for n in narrs:
        desc = (n["description"] or "")[:80]
        print(f"  [{n['id']}] {n['story_count']:4d} stories, {n['event_count']:3d} events | {n['title']}")
        if desc:
            print(f"    {desc}")

# Check for stale narratives (no events or very low story count)
print("\n\n=== POTENTIAL QUALITY ISSUES ===")
# Narratives with <5 events
low_event = conn.execute(
    "SELECT id, title, domain, story_count, event_count FROM narratives WHERE status='active' AND event_count < 3 ORDER BY event_count"
).fetchall()
if low_event:
    print("Narratives with <3 events:")
    for n in low_event:
        print(f"  [{n['id']}] {n['domain']:15s} {n['event_count']} events | {n['title'][:50]}")

# Overlapping narratives (same domain, similar story counts)
print("\nAll active narrative titles by domain:")
for domain in ["news", "sports", "entertainment", "positive"]:
    narrs = conn.execute(
        "SELECT title FROM narratives WHERE status='active' AND domain=? ORDER BY story_count DESC",
        (domain,),
    ).fetchall()
    print(f"  {domain}: {len(narrs)} narratives")

conn.close()
