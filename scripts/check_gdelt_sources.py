"""Check GDELT source distribution to identify junk sources."""
import sqlite3
import os

DB = os.environ.get("DB_PATH", "/opt/thisminute/data/thisminute.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# Top GDELT sources by volume
print("=== Top GDELT sources (last 24h) ===")
rows = conn.execute(
    """SELECT source, COUNT(*) as cnt FROM stories
    WHERE origin = 'gdelt' AND scraped_at > datetime('now', '-24 hours')
    GROUP BY source ORDER BY cnt DESC LIMIT 30"""
).fetchall()
for r in rows:
    print(f"  {r['cnt']:4d} {r['source']}")

# iHeart specifically
print("\n=== iHeart total ===")
iheart_total = conn.execute(
    "SELECT COUNT(*) as c FROM stories WHERE source LIKE '%Iheart%'"
).fetchone()["c"]
iheart_24h = conn.execute(
    "SELECT COUNT(*) as c FROM stories WHERE source LIKE '%Iheart%' AND scraped_at > datetime('now', '-24 hours')"
).fetchone()["c"]
print(f"  All time: {iheart_total}")
print(f"  Last 24h: {iheart_24h}")

# Other potentially junk GDELT sources
print("\n=== Sample stories from top GDELT source ===")
rows = conn.execute(
    """SELECT title, source FROM stories
    WHERE origin = 'gdelt' AND scraped_at > datetime('now', '-6 hours')
    AND source LIKE '%Iheart%'
    LIMIT 10"""
).fetchall()
for r in rows:
    print(f"  [{r['source']}] {r['title'][:60]}")

# Radio/podcast-like sources from GDELT
print("\n=== Potential radio/podcast GDELT sources ===")
rows = conn.execute(
    """SELECT source, COUNT(*) as cnt FROM stories
    WHERE origin = 'gdelt'
    AND (source LIKE '%radio%' OR source LIKE '%fm%' OR source LIKE '%am %'
         OR source LIKE '%iheart%' OR source LIKE '%podcast%'
         OR source LIKE '%wkjc%' OR source LIKE '%kiss%')
    GROUP BY source ORDER BY cnt DESC LIMIT 20"""
).fetchall()
for r in rows:
    print(f"  {r['cnt']:4d} {r['source']}")

conn.close()
