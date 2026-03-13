import sqlite3
c = sqlite3.connect("/opt/thisminute/data/thisminute.db")

# GDELT extraction status breakdown
r = c.execute("SELECT extraction_status, COUNT(*) FROM stories WHERE origin = 'gdelt' GROUP BY extraction_status").fetchall()
print("GDELT extraction status:")
for row in r:
    print("  %s: %d" % (row[0], row[1]))

# RSS extraction status breakdown
r = c.execute("SELECT extraction_status, COUNT(*) FROM stories WHERE origin = 'rss' GROUP BY extraction_status").fetchall()
print("\nRSS extraction status:")
for row in r:
    print("  %s: %d" % (row[0], row[1]))

# How many GDELT stories have bright_side_score?
r = c.execute("SELECT COUNT(*) FROM stories s JOIN story_extractions se ON se.story_id = s.id WHERE s.origin = 'gdelt' AND se.bright_side_score IS NOT NULL").fetchone()
print("\nGDELT with bright_side_score: %d" % r[0])

r = c.execute("SELECT COUNT(*) FROM stories s JOIN story_extractions se ON se.story_id = s.id WHERE s.origin = 'rss' AND se.bright_side_score IS NOT NULL").fetchone()
print("RSS with bright_side_score: %d" % r[0])

# How many pending extraction?
r = c.execute("SELECT COUNT(*) FROM stories WHERE extraction_status = 'pending'").fetchone()
print("\nPending extraction: %d" % r[0])

# Service logs
import subprocess
r2 = subprocess.run(["sudo", "journalctl", "-u", "thisminute", "-n", "20", "--no-pager"], capture_output=True, text=True)
print("\nRecent service logs:")
print(r2.stdout[-2000:] if len(r2.stdout) > 2000 else r2.stdout)
