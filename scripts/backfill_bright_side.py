"""Backfill bright_side scores for existing stories.

Sends story titles+summaries to Haiku in batches, asking ONLY for bright_side scoring.
Much cheaper than full re-extraction.

Usage: python -m scripts.backfill_bright_side [--hours 72] [--batch-size 20] [--dry-run]
"""

import argparse
import json
import logging
import os
import sqlite3
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

# Add parent to path so we can import src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BRIGHT_SIDE_PROMPT = """Score each news story for a "bright side" / good news feed.

For EACH story, return a JSON object with:
- "bright_side": null if not uplifting at all, OR an object with:
  - "score": 1-10 (1-2=mildly positive, 3-4=genuinely nice, 5-6=meaningfully uplifting, 7-8=powerfully inspiring, 9-10=extraordinary)
  - "category": one of: "breakthrough", "kindness", "solution", "recovery", "justice", "progress", "celebration", "nature"
  - "headline": 5-15 word rewrite emphasizing the bright angle

Be generous but honest. War/violence/disaster = null. Sports only if compelling human story.
Science only if real-world impact. Routine business = null.

Return ONLY a JSON array, one object per story, same order as input."""


def get_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def backfill(db_path, hours=72, batch_size=20, dry_run=False):
    try:
        import anthropic
    except ImportError:
        logger.error("anthropic package not installed")
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        return

    client = anthropic.Anthropic(api_key=api_key)
    conn = get_connection(db_path)

    # Ensure columns exist
    for col in ("bright_side_score", "bright_side_category", "bright_side_headline"):
        try:
            conn.execute(f"ALTER TABLE story_extractions ADD COLUMN {col} TEXT DEFAULT NULL")
        except sqlite3.OperationalError:
            pass

    # Get stories that need bright_side scoring
    rows = conn.execute(
        """SELECT s.id, s.title, s.summary, s.source
           FROM stories s
           JOIN story_extractions se ON se.story_id = s.id
           WHERE se.bright_side_score IS NULL
             AND s.scraped_at > datetime('now', ? || ' hours')
           ORDER BY s.scraped_at DESC""",
        (f"-{hours}",),
    ).fetchall()

    stories = [dict(r) for r in rows]
    logger.info("Found %d stories to score (last %d hours)", len(stories), hours)

    if dry_run:
        logger.info("Dry run, exiting")
        return

    scored = 0
    bright_count = 0
    total_batches = (len(stories) + batch_size - 1) // batch_size

    for batch_idx in range(0, len(stories), batch_size):
        batch = stories[batch_idx:batch_idx + batch_size]
        batch_num = batch_idx // batch_size + 1

        # Build prompt
        numbered = []
        for i, s in enumerate(batch, 1):
            summary = (s["summary"] or "")[:200]
            text = f"[{s['source']}] {s['title']}"
            if summary:
                text += f": {summary}"
            numbered.append(f"{i}. {text}")

        user_msg = "Score these stories:\n\n" + "\n".join(numbered)

        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=len(batch) * 100,
                system=BRIGHT_SIDE_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
            text = response.content[0].text.strip()
            # Strip code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            results = json.loads(text)
            if not isinstance(results, list):
                logger.warning("Batch %d/%d: non-array response", batch_num, total_batches)
                continue

            for s, result in zip(batch, results):
                bs = result.get("bright_side") if isinstance(result, dict) else None
                if bs and isinstance(bs, dict) and bs.get("score"):
                    conn.execute(
                        """UPDATE story_extractions
                           SET bright_side_score = ?, bright_side_category = ?, bright_side_headline = ?
                           WHERE story_id = ?""",
                        (bs["score"], bs.get("category"), bs.get("headline"), s["id"]),
                    )
                    bright_count += 1
                scored += 1

            conn.commit()
            logger.info(
                "Batch %d/%d: scored %d stories (%d bright so far)",
                batch_num, total_batches, len(batch), bright_count,
            )

        except json.JSONDecodeError as e:
            logger.warning("Batch %d/%d: JSON parse failed: %s", batch_num, total_batches, e)
        except Exception as e:
            logger.warning("Batch %d/%d: API error: %s", batch_num, total_batches, e)

        # Small delay between batches
        if batch_idx + batch_size < len(stories):
            time.sleep(0.3)

    logger.info("Done: %d scored, %d bright side (%.1f%%)", scored, bright_count,
                100 * bright_count / max(scored, 1))
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=int, default=72, help="How many hours back to go")
    parser.add_argument("--batch-size", type=int, default=20, help="Stories per API call")
    parser.add_argument("--db", default=None, help="DB path (default: auto-detect)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db = args.db or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "thisminute.db")
    backfill(db, hours=args.hours, batch_size=args.batch_size, dry_run=args.dry_run)
