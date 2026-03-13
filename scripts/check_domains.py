#!/usr/bin/env python3
"""Quick diagnostic: check narrative domain health."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import get_connection

conn = get_connection()

print("=== Active narratives by domain ===")
for d in ["news", "sports", "entertainment", "positive"]:
    row = conn.execute(
        "SELECT count(*) as c, max(last_analyzed) as la FROM narratives WHERE status='active' AND domain=?",
        (d,)
    ).fetchone()
    print(f"  {d}: count={row['c']}, last_analyzed={row['la']}")

print("\n=== All narratives by domain (any status) ===")
rows = conn.execute(
    "SELECT domain, status, count(*) as c FROM narratives GROUP BY domain, status ORDER BY domain, status"
).fetchall()
for r in rows:
    print(f"  {r['domain']} / {r['status']}: {r['c']}")

print("\n=== News narratives last_analyzed timestamps ===")
rows = conn.execute(
    "SELECT id, title, last_analyzed FROM narratives WHERE status='active' AND domain='news' ORDER BY last_analyzed DESC LIMIT 5"
).fetchall()
for r in rows:
    print(f"  [{r['id']}] {r['last_analyzed']} - {r['title'][:60]}")

conn.close()
