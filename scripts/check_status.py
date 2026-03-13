"""Check narrative, overview, and extraction status."""
import sqlite3
import subprocess
import sys

DB_PATH = sys.argv[1] if len(sys.argv) > 1 else "data/thisminute.db"
conn = sqlite3.connect("file:///" + DB_PATH + "?mode=ro", uri=True)
conn.row_factory = sqlite3.Row

# Narratives
narrs = conn.execute("SELECT * FROM narratives").fetchall()
print("Narratives: %d" % len(narrs), flush=True)
for n in narrs:
    n = dict(n)
    print("  #%d: [%s] %s" % (n["id"], n["status"], n["title"]), flush=True)

# World overview
try:
    wo = conn.execute("SELECT * FROM world_overviews ORDER BY created_at DESC LIMIT 3").fetchall()
    print("\nWorld overviews: %d" % len(wo), flush=True)
    for w in wo:
        w = dict(w)
        text = str(w.get("overview_text", ""))[:120]
        print("  [%s] %s" % (w.get("created_at", ""), text), flush=True)
except Exception as e:
    print("\nWorld overviews table: %s" % e, flush=True)

# DB tables
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("\nTables:", flush=True)
for t in tables:
    print("  %s" % t[0], flush=True)

# Extraction
extracted = conn.execute("SELECT COUNT(*) FROM story_extractions").fetchone()[0]
pending = conn.execute("SELECT COUNT(*) FROM stories WHERE extraction_status='pending'").fetchone()[0]
print("\nExtraction: %d done, %d pending" % (extracted, pending), flush=True)

# Events
events = conn.execute("SELECT COUNT(*) FROM events WHERE merged_into IS NULL").fetchone()[0]
single = conn.execute("SELECT COUNT(*) FROM events WHERE merged_into IS NULL AND story_count=1").fetchone()[0]
multi = conn.execute("SELECT COUNT(*) FROM events WHERE merged_into IS NULL AND story_count>1").fetchone()[0]
print("Events: %d total (%d single, %d multi)" % (events, single, multi), flush=True)

# Recent logs
r = subprocess.run(["journalctl", "-u", "thisminute", "-n", "50", "--no-pager"],
                    capture_output=True, text=True)
lines = r.stdout.split("\n")
relevant = [l for l in lines if any(k in l.lower() for k in ["narrative", "overview", "extract", "cluster", "error"])]
print("\nRecent relevant logs:", flush=True)
for l in relevant[-15:]:
    print("  %s" % l.strip(), flush=True)

conn.close()
