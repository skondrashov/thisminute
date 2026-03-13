"""Find junk/low-quality events that should be cleaned up."""
import sqlite3
import os

DB = os.environ.get("DB_PATH", "/opt/thisminute/data/thisminute.db")

JUNK_PATTERNS = [
    "Radio Segment", "Wall Street Zen", "SUV Launch", "Puzzle Solutions",
    "Dating Preferences", "Stock Downgrade", "Horoscope", "Daily Quiz",
    "Crossword", "Wordle", "Celebrity News", "Entertainment Roundup",
]

def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    # Find events matching junk patterns
    print("=== JUNK PATTERN MATCHES ===")
    for pattern in JUNK_PATTERNS:
        rows = conn.execute(
            """SELECT id, title, story_count FROM events
               WHERE merged_into IS NULL AND status != 'resolved'
               AND title LIKE ?
               ORDER BY story_count DESC""",
            (f"%{pattern}%",),
        ).fetchall()
        for r in rows:
            print(f"  [{r['id']}] ({r['story_count']} stories) {r['title'][:80]}")

    # Find events with very generic titles
    print("\n=== GENERIC/VAGUE TITLES (active, 2+ stories) ===")
    generic_words = [
        "Multiple %", "Various %", "Several %", "Daily %", "Weekly %",
        "% Roundup", "% Digest", "% Updates", "% Summary",
    ]
    for pattern in generic_words:
        rows = conn.execute(
            """SELECT id, title, story_count FROM events
               WHERE merged_into IS NULL AND status != 'resolved'
               AND story_count >= 2
               AND title LIKE ?
               ORDER BY story_count DESC LIMIT 5""",
            (pattern,),
        ).fetchall()
        for r in rows:
            print(f"  [{r['id']}] ({r['story_count']} stories) {r['title'][:80]}")

    # Check for narrative #17 and #35 (sports/entertainment in news domain)
    print("\n=== MISCATEGORIZED NARRATIVES ===")
    rows = conn.execute(
        """SELECT id, domain, title, story_count, event_count FROM narratives
           WHERE status = 'active'
           AND domain = 'news'
           AND (title LIKE '%Sports%' OR title LIKE '%Entertainment%'
                OR title LIKE '%Culture%' OR title LIKE '%Baseball%'
                OR title LIKE '%Rugby%' OR title LIKE '%NBA%'
                OR title LIKE '%NFL%' OR title LIKE '%Cricket%'
                OR title LIKE '%Film%' OR title LIKE '%Music%')
           ORDER BY story_count DESC"""
    ).fetchall()
    for r in rows:
        print(f"  [{r['id']}] domain={r['domain']} ({r['story_count']} stories, {r['event_count']} events) {r['title'][:80]}")

    # Find top singleton events (1 story, recent)
    print("\n=== RECENT SINGLETONS (last 24h, could be clustered) ===")
    rows = conn.execute(
        """SELECT id, title, story_count, last_updated FROM events
           WHERE merged_into IS NULL AND status != 'resolved'
           AND story_count = 1
           AND last_updated > datetime('now', '-1 day')
           ORDER BY last_updated DESC
           LIMIT 20"""
    ).fetchall()
    print(f"  Total recent singletons: {len(rows)}")
    for r in rows[:10]:
        print(f"  [{r['id']}] {r['title'][:70]} ({r['last_updated'][:16]})")

    # Overall stats
    print("\n=== OVERALL STATS ===")
    total = conn.execute("SELECT COUNT(*) as c FROM events WHERE merged_into IS NULL AND status != 'resolved'").fetchone()['c']
    singles = conn.execute("SELECT COUNT(*) as c FROM events WHERE merged_into IS NULL AND status != 'resolved' AND story_count = 1").fetchone()['c']
    multi = total - singles
    print(f"  Total active events: {total}")
    print(f"  Singletons: {singles} ({100*singles/max(total,1):.1f}%)")
    print(f"  Multi-story: {multi} ({100*multi/max(total,1):.1f}%)")

    conn.close()

if __name__ == "__main__":
    main()
