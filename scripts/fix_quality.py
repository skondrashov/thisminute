"""Targeted data quality fixes:
1. Resolve specific junk events (free their stories for re-clustering)
2. Fix miscategorized narratives (sports in news domain)
"""
import sqlite3
import os

DB = os.environ.get("DB_PATH", "/opt/thisminute/data/thisminute.db")

JUNK_EVENT_IDS = [
    31615,  # Radio Segment: Dating Preferences and Celebrity News
    26209,  # Multiple Stock Downgrades at Wall Street Zen
    23923,  # High-Performance SUV Launch Expected This Year
    35220,  # Daily Puzzle Solutions Published for March 11
    8350,   # Daily Herald Job Listings and Local News Updates
    29794,  # Best Alarm Clocks of 2026 - Product Review Roundup
    10642,  # Multiple Deaths Reported in UK and Oregon
    31838,  # Weekly Entertainment Reviews
]

# Narratives that are sports content but tagged as news domain
SPORTS_IN_NEWS = [17, 31]  # Sports Mega-Events, T20 World Cup


def resolve_junk_events(conn):
    """Resolve junk events and free their stories."""
    resolved = 0
    for eid in JUNK_EVENT_IDS:
        row = conn.execute(
            "SELECT id, title, story_count, status FROM events WHERE id = ?",
            (eid,),
        ).fetchone()
        if not row or row["status"] == "resolved":
            continue
        # Free stories
        conn.execute("DELETE FROM event_stories WHERE event_id = ?", (eid,))
        conn.execute("DELETE FROM narrative_events WHERE event_id = ?", (eid,))
        conn.execute(
            "UPDATE events SET status = 'resolved', merged_into = -1 WHERE id = ?",
            (eid,),
        )
        resolved += 1
        print(f"  Resolved [{eid}] ({row['story_count']} stories): {row['title'][:70]}")

    conn.commit()
    print(f"Resolved {resolved} junk events")
    return resolved


def fix_narrative_domains(conn):
    """Move sports-content narratives from news to sports domain."""
    fixed = 0
    for nid in SPORTS_IN_NEWS:
        row = conn.execute(
            "SELECT id, title, domain FROM narratives WHERE id = ?",
            (nid,),
        ).fetchone()
        if not row:
            continue
        if row["domain"] == "news":
            conn.execute(
                "UPDATE narratives SET domain = 'sports' WHERE id = ?",
                (nid,),
            )
            fixed += 1
            print(f"  [{nid}] news -> sports: {row['title'][:70]}")

    conn.commit()
    print(f"Fixed {fixed} narrative domains")
    return fixed


def deactivate_catchall_narrative(conn):
    """Deactivate catch-all narrative #35 (Entertainment/Sports/Culture in news)."""
    row = conn.execute(
        "SELECT id, title, domain, event_count FROM narratives WHERE id = 35",
    ).fetchone()
    if row and row["domain"] == "news":
        conn.execute(
            "UPDATE narratives SET status = 'inactive' WHERE id = 35",
        )
        conn.commit()
        print(f"  Deactivated catch-all [{row['id']}]: {row['title'][:70]}")
        return 1
    return 0


if __name__ == "__main__":
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000")

    print("=== RESOLVING JUNK EVENTS ===")
    resolve_junk_events(conn)

    print("\n=== FIXING NARRATIVE DOMAINS ===")
    fix_narrative_domains(conn)

    print("\n=== DEACTIVATING CATCH-ALL NARRATIVES ===")
    deactivate_catchall_narrative(conn)

    # Summary
    print("\n=== POST-FIX STATS ===")
    rows = conn.execute(
        """SELECT domain, COUNT(*) as cnt, SUM(story_count) as stories
           FROM narratives WHERE status = 'active'
           GROUP BY domain ORDER BY domain"""
    ).fetchall()
    for r in rows:
        print(f"  {r['domain']}: {r['cnt']} narratives, {r['stories']} stories")

    conn.close()
    print("\nDone!")
