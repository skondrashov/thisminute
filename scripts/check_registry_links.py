"""Check how many stories are linked to registry events."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.database import get_connection, init_db

init_db()
conn = get_connection()

r1 = conn.execute("SELECT COUNT(*) as c FROM story_extractions WHERE registry_event_id IS NOT NULL").fetchone()
print(f"Stories with registry_event_id in extractions: {r1['c']}", flush=True)

r2 = conn.execute("SELECT COUNT(*) as c FROM registry_stories").fetchone()
print(f"Rows in registry_stories table: {r2['c']}", flush=True)

r3 = conn.execute("SELECT COUNT(*) as c FROM story_extractions").fetchone()
print(f"Total extractions: {r3['c']}", flush=True)

# Show top registry events by linked stories
rows = conn.execute("""
    SELECT rs.registry_event_id, er.map_label, COUNT(*) as cnt
    FROM registry_stories rs
    JOIN event_registry er ON rs.registry_event_id = er.id
    GROUP BY rs.registry_event_id
    ORDER BY cnt DESC LIMIT 10
""").fetchall()
print("\nTop 10 registry events by linked stories:", flush=True)
for r in rows:
    print(f"  R{r['registry_event_id']}: \"{r['map_label']}\" ({r['cnt']} stories)", flush=True)

conn.close()
