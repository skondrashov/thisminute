"""Quick backlog and pipeline health check."""
import sqlite3
import os

DB = os.environ.get("DB_PATH", "/opt/thisminute/data/thisminute.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

unanalyzed = conn.execute(
    "SELECT COUNT(*) as c FROM events WHERE merged_into IS NULL AND status != 'resolved' AND story_count >= 2 AND last_analyzed IS NULL"
).fetchone()["c"]
analyzed_1h = conn.execute(
    "SELECT COUNT(*) as c FROM events WHERE last_analyzed > datetime('now', '-1 hour')"
).fetchone()["c"]
analyzed_4h = conn.execute(
    "SELECT COUNT(*) as c FROM events WHERE last_analyzed > datetime('now', '-4 hours')"
).fetchone()["c"]
total_multi = conn.execute(
    "SELECT COUNT(*) as c FROM events WHERE merged_into IS NULL AND status != 'resolved' AND story_count >= 2"
).fetchone()["c"]
total_active = conn.execute(
    "SELECT COUNT(*) as c FROM events WHERE merged_into IS NULL AND status != 'resolved'"
).fetchone()["c"]

print(f"Active events: {total_active} (multi-story: {total_multi})")
print(f"Unanalyzed multi-story: {unanalyzed}")
print(f"Analyzed last 1h: {analyzed_1h}")
print(f"Analyzed last 4h: {analyzed_4h}")

# Extraction backlog
pending = conn.execute(
    "SELECT COUNT(*) as c FROM stories WHERE extraction_status = 'pending'"
).fetchone()["c"]
print(f"\nPending extractions: {pending}")

# Recent pipeline activity
for table, col in [("stories", "scraped_at"), ("events", "last_updated")]:
    row = conn.execute(f"SELECT MAX({col}) as latest FROM {table}").fetchone()
    print(f"Latest {table}: {row['latest']}")

# Narrative freshness
narr = conn.execute(
    "SELECT MAX(last_analyzed) as latest, COUNT(*) as cnt FROM narratives WHERE status = 'active'"
).fetchone()
print(f"\nActive narratives: {narr['cnt']}, last analyzed: {narr['latest']}")

conn.close()
