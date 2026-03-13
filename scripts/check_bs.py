import sqlite3
c = sqlite3.connect("/opt/thisminute/data/thisminute.db")

r = c.execute("SELECT bright_side_score, COUNT(*) FROM story_extractions GROUP BY bright_side_score ORDER BY COUNT(*) DESC LIMIT 15").fetchall()
print("bright_side_score distribution:")
for row in r:
    print(f"  {repr(row[0])}: {row[1]}")

r = c.execute("SELECT COUNT(*) FROM story_extractions WHERE CAST(bright_side_score AS INTEGER) >= 4").fetchone()
print(f"\nBright side (score>=4): {r[0]}")

r = c.execute("SELECT COUNT(*) FROM story_extractions WHERE bright_side_score IS NOT NULL").fetchone()
print(f"Non-null scores: {r[0]}")

# Check what the API would return
r = c.execute("""
    SELECT s.id, se.bright_side_score, se.bright_side_headline, s.title
    FROM stories s
    JOIN story_extractions se ON se.story_id = s.id
    WHERE CAST(se.bright_side_score AS INTEGER) >= 4
    AND s.lat IS NOT NULL
    ORDER BY s.published_at DESC
    LIMIT 5
""").fetchall()
print(f"\nSample bright side stories with location:")
for row in r:
    print(f"  id={row[0]} score={row[1]} headline={row[2][:60] if row[2] else 'N/A'}")
    print(f"    original: {row[3][:80]}")
