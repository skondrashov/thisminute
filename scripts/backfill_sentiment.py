"""Backfill sentiment for existing stories that don't have it yet."""
import sys
sys.path.insert(0, "/opt/thisminute")

from src.database import get_connection, init_db
from src.sentiment import classify_batch

init_db()
conn = get_connection()

# Get stories without sentiment, in batches of 50
total = 0
while True:
    rows = conn.execute(
        "SELECT id, title FROM stories WHERE sentiment IS NULL LIMIT 50"
    ).fetchall()
    if not rows:
        break
    stories = [{"id": r["id"], "title": r["title"]} for r in rows]
    sentiments = classify_batch(stories)
    for story_id, sentiment in sentiments.items():
        conn.execute("UPDATE stories SET sentiment = ? WHERE id = ?", (sentiment, story_id))
    conn.commit()
    total += len(sentiments)
    pos = sum(1 for v in sentiments.values() if v == "positive")
    neg = sum(1 for v in sentiments.values() if v == "negative")
    neu = sum(1 for v in sentiments.values() if v == "neutral")
    print(f"Batch: {len(sentiments)} classified (+{pos} ={neu} -{neg}), total: {total}", flush=True)

print(f"Done. {total} stories backfilled.", flush=True)
conn.close()
