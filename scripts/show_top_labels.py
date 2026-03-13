"""Show top registry labels by story count."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.database import get_connection, init_db

init_db()
conn = get_connection()
rows = conn.execute(
    "SELECT id, map_label, story_count FROM event_registry WHERE status='active' AND story_count >= 3 ORDER BY story_count DESC"
).fetchall()
for r in rows:
    print(f"R{r['id']}: \"{r['map_label']}\" ({r['story_count']} stories)", flush=True)
conn.close()
