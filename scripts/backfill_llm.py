"""Re-extract stories that got legacy-only extraction (no LLM).

Identifies stories where extraction_json contains "_legacy": true
or where bright_side_score is NULL, and re-runs them through the
LLM extractor in batches.

Usage:
    /opt/thisminute/venv/bin/python scripts/backfill_llm.py [--days N] [--limit N] [--dry-run]
"""
import argparse
import json
import logging
import sqlite3
import sys
import os

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.llm_extractor import extract_stories_batch
from src.llm_utils import get_anthropic_client, HAIKU_MODEL
from src.database import get_connection, store_extraction


def check_credits():
    """Verify API credits are available before running a long backfill."""
    client = get_anthropic_client()
    if not client:
        print("ERROR: No API client (missing ANTHROPIC_API_KEY?)", flush=True)
        return False
    try:
        response = client.messages.create(
            model=HAIKU_MODEL, max_tokens=5,
            messages=[{"role": "user", "content": "hi"}],
        )
        print(f"API credit check OK (model: {HAIKU_MODEL})", flush=True)
        return True
    except Exception as e:
        print(f"ERROR: API credit check failed: {e}", flush=True)
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7, help="Look back N days (default 7)")
    parser.add_argument("--limit", type=int, default=500, help="Max stories to re-extract (default 500)")
    parser.add_argument("--batch-size", type=int, default=8, help="Stories per LLM batch (default 8)")
    parser.add_argument("--dry-run", action="store_true", help="Just count, don't extract")
    parser.add_argument("--skip-credit-check", action="store_true", help="Skip API credit check")
    args = parser.parse_args()

    if not args.dry_run and not args.skip_credit_check:
        if not check_credits():
            sys.exit(1)

    conn = get_connection()

    # Find stories needing re-extraction: legacy flag OR null bright_side_score
    rows = conn.execute("""
        SELECT s.id, s.title, s.summary, s.url, s.source, s.published_at, s.scraped_at,
               s.lat, s.lon, s.location_name, s.concepts,
               se.extraction_json
        FROM stories s
        JOIN story_extractions se ON se.story_id = s.id
        WHERE (se.extraction_json LIKE '%"_legacy"%' OR se.bright_side_score IS NULL)
          AND se.extracted_at > datetime('now', ?)
        ORDER BY s.published_at DESC
        LIMIT ?
    """, (f"-{args.days} days", args.limit)).fetchall()

    print(f"Found {len(rows)} stories needing LLM re-extraction (last {args.days} days, limit {args.limit})", flush=True)

    if args.dry_run or len(rows) == 0:
        return

    # Build story dicts for the extractor
    stories = []
    for r in rows:
        stories.append({
            "id": r[0], "title": r[1], "summary": r[2], "url": r[3],
            "source": r[4], "published_at": r[5], "scraped_at": r[6],
            "lat": r[7], "lon": r[8], "location_name": r[9], "concepts": r[10],
        })

    # Load registry events for context
    registry_events = conn.execute("""
        SELECT id, registry_label, map_label, primary_lat, primary_lon, status
        FROM event_registry WHERE status != 'retired'
    """).fetchall()
    registry = [{"id": r[0], "registry_label": r[1], "map_label": r[2], "lat": r[3], "lon": r[4], "status": r[5]}
                for r in registry_events]

    # Load wiki events
    wiki_events = conn.execute("""
        SELECT we.id, we.article_title, COUNT(swe.story_id) as story_count
        FROM wiki_events we
        LEFT JOIN story_wiki_events swe ON swe.wiki_event_id = we.id
        WHERE we.status = 'active'
        GROUP BY we.id
    """).fetchall()
    wikis = [{"id": r[0], "article_title": r[1], "story_count": r[2]} for r in wiki_events]

    print(f"Re-extracting {len(stories)} stories via LLM...", flush=True)

    # Process in chunks with intermediate commits for visibility and resilience
    chunk_size = 100
    saved = 0
    still_legacy = 0
    for chunk_start in range(0, len(stories), chunk_size):
        chunk = stories[chunk_start:chunk_start + chunk_size]
        results = extract_stories_batch(chunk, batch_size=args.batch_size,
                                        registry_events=registry, wiki_events=wikis)
        chunk_saved = 0
        for story, extraction in results:
            if extraction.get("_legacy"):
                still_legacy += 1
                continue
            store_extraction(conn, story["id"], extraction)
            chunk_saved += 1
            saved += 1
        conn.commit()
        print(f"  chunk {chunk_start + 1}-{chunk_start + len(chunk)}: "
              f"{chunk_saved}/{len(chunk)} extracted ({saved} total, {still_legacy} legacy)",
              flush=True)

    print(f"Done: {saved} re-extracted via LLM, {still_legacy} still failed (API issue?)", flush=True)

    # Show bright_side stats after backfill
    bs = conn.execute("SELECT COUNT(*) FROM story_extractions WHERE bright_side_score IS NOT NULL").fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM story_extractions").fetchone()[0]
    print(f"Bright side coverage: {bs}/{total} ({100*bs//total}%)", flush=True)


if __name__ == "__main__":
    main()
