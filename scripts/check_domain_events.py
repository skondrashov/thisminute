"""Diagnostic: check how many events each domain gets from _get_domain_events."""
import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import FEED_TAG_MAP

DB = os.environ.get("DB_PATH", "/opt/thisminute/data/thisminute.db")

DOMAIN_FEED_TAGS = {
    "news": {"news", "business", "tech", "science", "health"},
    "sports": {"sports"},
    "entertainment": {"entertainment"},
    "positive": None,
}

def check_domain(conn, domain, limit=50):
    if domain == "positive":
        rows = conn.execute(
            """SELECT e.id, e.title, e.story_count,
                      CAST(SUM(CASE WHEN se.bright_side_score >= 4 THEN 1 ELSE 0 END) AS REAL)
                          / COUNT(*) as bright_ratio
               FROM events e
               JOIN event_stories es ON e.id = es.event_id
               LEFT JOIN story_extractions se ON es.story_id = se.story_id
               WHERE e.merged_into IS NULL AND e.status != 'resolved'
               GROUP BY e.id
               HAVING bright_ratio >= 0.3
               ORDER BY e.story_count DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        print(f"\n=== POSITIVE domain: {len(rows)} events (bright_ratio >= 0.3) ===")
        for r in rows[:10]:
            print(f"  [{r['id']}] ({r['story_count']} stories, bright={r['bright_ratio']:.2f}) {r['title'][:80]}")
        return len(rows)

    domain_tags = DOMAIN_FEED_TAGS.get(domain, {"news"})
    domain_sources = [
        src for src, tags in FEED_TAG_MAP.items()
        if any(t in domain_tags for t in tags)
    ]
    print(f"\n=== {domain.upper()} domain: {len(domain_sources)} sources ===")
    for s in domain_sources[:20]:
        print(f"  - {s}")

    if not domain_sources:
        print("  NO SOURCES FOUND!")
        return 0

    placeholders = ",".join("?" * len(domain_sources))
    rows = conn.execute(
        f"""SELECT e.id, e.title, e.story_count,
                   SUM(CASE WHEN s.source IN ({placeholders}) THEN 1 ELSE 0 END) as domain_count,
                   COUNT(*) as total_count,
                   CAST(SUM(CASE WHEN s.source IN ({placeholders}) THEN 1 ELSE 0 END) AS REAL) / COUNT(*) as domain_ratio
            FROM events e
            JOIN event_stories es ON e.id = es.event_id
            JOIN stories s ON es.story_id = s.id
            WHERE e.merged_into IS NULL AND e.status != 'resolved'
            GROUP BY e.id
            HAVING domain_ratio >= 0.5
            ORDER BY e.story_count DESC
            LIMIT ?""",
        (*domain_sources, *domain_sources, limit),
    ).fetchall()
    print(f"  Events with >= 50% domain stories: {len(rows)}")
    for r in rows[:10]:
        print(f"  [{r['id']}] ({r['story_count']} stories, {r['domain_count']}/{r['total_count']} domain) {r['title'][:80]}")

    # Also check events with ANY domain stories (even below 50%)
    rows2 = conn.execute(
        f"""SELECT e.id, e.title, e.story_count,
                   SUM(CASE WHEN s.source IN ({placeholders}) THEN 1 ELSE 0 END) as domain_count,
                   COUNT(*) as total_count,
                   CAST(SUM(CASE WHEN s.source IN ({placeholders}) THEN 1 ELSE 0 END) AS REAL) / COUNT(*) as domain_ratio
            FROM events e
            JOIN event_stories es ON e.id = es.event_id
            JOIN stories s ON es.story_id = s.id
            WHERE e.merged_into IS NULL AND e.status != 'resolved'
            GROUP BY e.id
            HAVING domain_count >= 1
            ORDER BY domain_count DESC
            LIMIT 20""",
        (*domain_sources, *domain_sources,),
    ).fetchall()
    print(f"\n  Events with ANY domain stories: {len(rows2)}")
    for r in rows2[:15]:
        pct = r['domain_ratio'] * 100
        marker = " <<<" if pct >= 50 else ""
        print(f"  [{r['id']}] ({r['domain_count']}/{r['total_count']} = {pct:.0f}%) {r['title'][:70]}{marker}")

    return len(rows)


def check_narratives(conn):
    print("\n=== ACTIVE NARRATIVES BY DOMAIN ===")
    rows = conn.execute(
        """SELECT domain, COUNT(*) as cnt, SUM(event_count) as events, SUM(story_count) as stories
           FROM narratives WHERE status = 'active'
           GROUP BY domain ORDER BY domain"""
    ).fetchall()
    for r in rows:
        print(f"  {r['domain']}: {r['cnt']} narratives, {r['events']} events, {r['stories']} stories")

    # Check inactive
    rows2 = conn.execute(
        """SELECT domain, COUNT(*) as cnt FROM narratives
           WHERE status = 'inactive' GROUP BY domain"""
    ).fetchall()
    if rows2:
        print("\n  Inactive narratives:")
        for r in rows2:
            print(f"    {r['domain']}: {r['cnt']}")


def check_story_sources(conn):
    """Check how many stories each entertainment source actually has."""
    ent_sources = [
        src for src, tags in FEED_TAG_MAP.items()
        if "entertainment" in tags
    ]
    print("\n=== ENTERTAINMENT SOURCE STORY COUNTS (last 7 days) ===")
    for src in sorted(ent_sources):
        row = conn.execute(
            """SELECT COUNT(*) as cnt FROM stories
               WHERE source = ? AND scraped_at > datetime('now', '-7 days')""",
            (src,),
        ).fetchone()
        total = conn.execute(
            "SELECT COUNT(*) as cnt FROM stories WHERE source = ?", (src,)
        ).fetchone()
        print(f"  {src}: {row['cnt']} (7d), {total['cnt']} (all time)")


if __name__ == "__main__":
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    check_narratives(conn)
    for domain in ["news", "sports", "entertainment", "positive"]:
        check_domain(conn, domain)
    check_story_sources(conn)

    conn.close()
