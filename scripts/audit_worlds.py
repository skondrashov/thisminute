"""Comprehensive data quality audit across all world presets.

Checks stories, situations, events, geocoding, and cross-contamination
for each of the 13 world presets.
"""
import sqlite3
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import FEED_TAG_MAP, FEEDS

# World preset definitions (mirrors frontend WORLD_PRESETS)
WORLDS = {
    "bright_side": {"feedTags": [], "brightSideMode": True, "origins": None, "domain": "positive"},
    "sports": {"feedTags": ["sports"], "origins": ["rss", "gdelt"], "domain": "sports"},
    "entertainment": {"feedTags": ["entertainment"], "origins": ["rss", "gdelt"], "domain": "entertainment"},
    "curious": {"feedTags": [], "curiousMode": True, "origins": None, "domain": "curious"},
    "science": {"feedTags": ["science", "tech"], "origins": ["rss", "gdelt"], "domain": "science"},
    "tech": {"feedTags": ["tech"], "origins": ["rss", "gdelt"], "domain": "science"},
    "planet": {"feedTags": [], "origins": ["noaa", "usgs", "eonet", "gdacs", "firms", "meteoalarm", "jma"], "domain": None},
    "conflict": {"feedTags": [], "origins": ["rss", "gdelt", "acled"], "domain": "news"},
    "travel": {"feedTags": [], "origins": ["rss", "travel", "noaa", "gdacs", "who", "meteoalarm", "acled", "jma"], "domain": None},
    "power": {"feedTags": [], "origins": ["rss", "gdelt"], "domain": "news"},
    "markets": {"feedTags": ["business"], "origins": ["rss", "gdelt"], "domain": "business"},
    "health": {"feedTags": ["health"], "origins": ["rss", "who", "reliefweb"], "domain": "health"},
    "all": {"feedTags": [], "origins": None, "domain": None},
}

# War/conflict/tragedy keywords for cross-contamination check
WAR_KEYWORDS = {"war", "kill", "killed", "dead", "death", "attack", "bomb", "strike", "troops",
                "military", "soldier", "airstrike", "missile", "casualties", "invasion"}
TRAGEDY_KEYWORDS = {"die", "dies", "died", "fatal", "crash", "disaster", "earthquake", "tsunami",
                    "flood", "shooting", "massacre", "explosion"}


def get_sources_for_tags(tags):
    """Get source names that have any of the given tags."""
    return [src for src, src_tags in FEED_TAG_MAP.items() if any(t in tags for t in src_tags)]


def audit_world(conn, world_id, config):
    """Audit a single world preset."""
    print(f"\n{'='*80}", flush=True)
    print(f"  WORLD: {world_id.upper()}", flush=True)
    print(f"{'='*80}", flush=True)

    # Get stories matching this world's filters
    if config.get("brightSideMode"):
        stories = conn.execute("""
            SELECT s.id, s.title, s.lat, s.lon, s.source, s.location_name,
                   se.bright_side_score, se.human_interest_score, se.topics
            FROM stories s
            JOIN story_extractions se ON se.story_id = s.id
            WHERE CAST(se.bright_side_score AS INTEGER) >= 4
            ORDER BY s.id DESC LIMIT 200
        """).fetchall()
    elif config.get("curiousMode"):
        stories = conn.execute("""
            SELECT s.id, s.title, s.lat, s.lon, s.source, s.location_name,
                   se.bright_side_score, se.human_interest_score, se.topics
            FROM stories s
            JOIN story_extractions se ON se.story_id = s.id
            WHERE se.human_interest_score >= 7
            ORDER BY s.id DESC LIMIT 200
        """).fetchall()
    elif config.get("feedTags"):
        sources = get_sources_for_tags(config["feedTags"])
        if not sources:
            print(f"  WARNING: No sources found for tags {config['feedTags']}", flush=True)
            return
        placeholders = ",".join("?" * len(sources))
        stories = conn.execute(f"""
            SELECT s.id, s.title, s.lat, s.lon, s.source, s.location_name,
                   se.bright_side_score, se.human_interest_score, se.topics
            FROM stories s
            JOIN story_extractions se ON se.story_id = s.id
            WHERE s.source IN ({placeholders})
            ORDER BY s.id DESC LIMIT 200
        """, sources).fetchall()
    elif config.get("origins"):
        # Origin-filtered presets (planet, conflict, travel, power)
        # Map origin names to actual source names or origin column values
        origin_list = config["origins"]
        rss_sources = []
        api_origins = []
        for origin in origin_list:
            if origin == "rss":
                rss_sources.extend(src for src in FEED_TAG_MAP.keys())
            elif origin == "gdelt":
                api_origins.append("gdelt")
            else:
                api_origins.append(origin)

        # Build query: match by source name (RSS) OR by origin column (API)
        conditions = []
        params = []
        if rss_sources:
            ph = ",".join("?" * len(rss_sources))
            conditions.append(f"s.source IN ({ph})")
            params.extend(rss_sources)
        if api_origins:
            ph = ",".join("?" * len(api_origins))
            conditions.append(f"s.origin IN ({ph})")
            params.extend(api_origins)

        where = " OR ".join(conditions) if conditions else "1=1"
        stories = conn.execute(f"""
            SELECT s.id, s.title, s.lat, s.lon, s.source, s.location_name,
                   se.bright_side_score, se.human_interest_score, se.topics
            FROM stories s
            JOIN story_extractions se ON se.story_id = s.id
            WHERE {where}
            ORDER BY s.id DESC LIMIT 200
        """, params).fetchall()
    else:
        stories = conn.execute("""
            SELECT s.id, s.title, s.lat, s.lon, s.source, s.location_name,
                   se.bright_side_score, se.human_interest_score, se.topics
            FROM stories s
            JOIN story_extractions se ON se.story_id = s.id
            ORDER BY s.id DESC LIMIT 200
        """).fetchall()

    total = len(stories)
    geocoded = sum(1 for s in stories if s["lat"] is not None)
    geo_pct = (geocoded * 100 // total) if total else 0

    print(f"\n  Stories: {total} (recent 200 cap)", flush=True)
    print(f"  Geocoded: {geocoded}/{total} ({geo_pct}%)", flush=True)

    # Source distribution
    source_counts = {}
    for s in stories:
        src = s["source"] or "unknown"
        source_counts[src] = source_counts.get(src, 0) + 1
    top_sources = sorted(source_counts.items(), key=lambda x: -x[1])[:8]
    print(f"  Top sources: {', '.join(f'{s}({c})' for s, c in top_sources)}", flush=True)

    # Cross-contamination check
    if world_id not in ("all", "conflict", "power", "planet"):
        war_stories = []
        for s in stories:
            title = (s["title"] or "").lower()
            if any(w in title.split() for w in WAR_KEYWORDS):
                war_stories.append(s)
        if war_stories:
            pct = len(war_stories) * 100 // total if total else 0
            print(f"\n  *** WAR/CONFLICT CONTAMINATION: {len(war_stories)}/{total} ({pct}%) ***", flush=True)
            for s in war_stories[:5]:
                t = (s["title"] or "").encode("ascii", "replace").decode()[:80]
                print(f"    - {t}", flush=True)

    # Tragedy check for bright_side and curious
    if world_id in ("bright_side", "curious"):
        tragedy_stories = []
        for s in stories:
            title = (s["title"] or "").lower()
            if any(w in title.split() for w in TRAGEDY_KEYWORDS | WAR_KEYWORDS):
                tragedy_stories.append(s)
        if tragedy_stories:
            pct = len(tragedy_stories) * 100 // total if total else 0
            print(f"\n  *** TRAGEDY/VIOLENCE in {world_id}: {len(tragedy_stories)}/{total} ({pct}%) ***", flush=True)
            for s in tragedy_stories[:5]:
                t = (s["title"] or "").encode("ascii", "replace").decode()[:80]
                score_field = "bright_side_score" if world_id == "bright_side" else "human_interest_score"
                score = s[score_field]
                print(f"    - [{score}] {t}", flush=True)

    # Sample stories (first 10)
    print(f"\n  Sample stories:", flush=True)
    for s in stories[:10]:
        t = (s["title"] or "").encode("ascii", "replace").decode()[:75]
        loc = s["location_name"] or "no-loc"
        src = s["source"] or "?"
        print(f"    [{src:>15}] {loc:>20}: {t}", flush=True)

    # Situations for this domain
    domain = config.get("domain")
    if domain:
        narrs = conn.execute(
            "SELECT id, title, story_count, domain FROM narratives WHERE domain = ? AND status = 'active' ORDER BY story_count DESC",
            (domain,)
        ).fetchall()
        print(f"\n  Situations ({domain} domain): {len(narrs)}", flush=True)
        for n in narrs[:10]:
            t = (n["title"] or "").encode("ascii", "replace").decode()[:65]
            print(f"    [{n['story_count']:>3} stories] {t}", flush=True)

        # Check if situations have war contamination (for non-news domains)
        if domain not in ("news",):
            for n in narrs:
                title = (n["title"] or "").lower()
                if any(w in title.split() for w in WAR_KEYWORDS):
                    print(f"    *** WAR IN {domain.upper()} SITUATION: {n['title']}", flush=True)
    else:
        # Presets without domain mapping — planet/travel hide situations in frontend
        narrs = conn.execute(
            "SELECT id, title, story_count, domain FROM narratives WHERE status = 'active' ORDER BY story_count DESC LIMIT 10"
        ).fetchall()
        hidden_note = " (hidden in frontend)" if world_id in ("planet", "travel") else ""
        print(f"\n  Situations (no domain filter - shows all{hidden_note}): {len(narrs)}", flush=True)
        for n in narrs[:10]:
            t = (n["title"] or "").encode("ascii", "replace").decode()[:55]
            print(f"    [{n['domain']:>14} | {n['story_count']:>3} stories] {t}", flush=True)


def main():
    conn = sqlite3.connect("data/thisminute.db")
    conn.row_factory = sqlite3.Row

    # Overall stats
    total_stories = conn.execute("SELECT COUNT(*) FROM stories").fetchone()[0]
    total_extracted = conn.execute("SELECT COUNT(*) FROM story_extractions").fetchone()[0]
    total_geocoded = conn.execute("SELECT COUNT(*) FROM stories WHERE lat IS NOT NULL").fetchone()[0]
    total_narrs = conn.execute("SELECT COUNT(*) FROM narratives WHERE status='active'").fetchone()[0]
    total_events = conn.execute("SELECT COUNT(*) FROM events WHERE merged_into IS NULL").fetchone()[0]

    print("THISMINUTE DATA QUALITY AUDIT", flush=True)
    print(f"{'='*80}", flush=True)
    print(f"Total stories: {total_stories}", flush=True)
    print(f"Extracted: {total_extracted}", flush=True)
    print(f"Geocoded: {total_geocoded} ({total_geocoded*100//total_stories}%)", flush=True)
    print(f"Active situations: {total_narrs}", flush=True)
    print(f"Active events: {total_events}", flush=True)

    # Domain distribution
    print(f"\nSituations by domain:", flush=True)
    for row in conn.execute("SELECT domain, COUNT(*) as c FROM narratives WHERE status='active' GROUP BY domain ORDER BY c DESC"):
        print(f"  {row['domain']:>15}: {row['c']}", flush=True)

    # Audit each world
    for world_id, config in WORLDS.items():
        try:
            audit_world(conn, world_id, config)
        except Exception as e:
            print(f"\n  ERROR auditing {world_id}: {e}", flush=True)

    conn.close()


if __name__ == "__main__":
    main()
