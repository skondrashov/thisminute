"""Re-score human_interest_score for all existing stories using the updated prompt.

Sends story titles in batches to Haiku with the new quirky/delightful rubric
and updates the DB in place. Only touches human_interest_score — no other fields.
"""
import sqlite3
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from anthropic import Anthropic

SCORING_PROMPT = """Score each story title on "human_interest_score" (1-10):

How QUIRKY, SURPRISING, or DELIGHTFUL is this story? This powers a "Curious" feed of
lighthearted, offbeat, and genuinely unusual stories.

IMPORTANT: War, violence, tragedy, conflict, death, disaster, and political drama = LOW (1-3).
Mainstream entertainment (Oscars, celebrity news, major sports) = LOW (2-4).
Routine news, business, politics = LOW (1-3).

What scores HIGH: unusual, weird, heartwarming, scientifically surprising, "wait really?",
quirky achievements, odd animal behavior, unexpected discoveries, wholesome surprises.

1-2 = routine hard news, politics, conflict, tragedy, standard business/sports/entertainment
3-4 = mildly unusual but fundamentally normal news
5-6 = genuinely surprising or quirky
7-8 = highly unusual, bizarre, "wait really?", delightful oddity
9-10 = extraordinary once-in-a-decade oddity

Return ONLY a JSON array of integers, one per story, same order. No explanation."""

BATCH_SIZE = 20  # titles are short, can fit more per call
MODEL = "claude-haiku-4-5-20251001"


def score_batch(client, titles):
    numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(titles))
    resp = client.messages.create(
        model=MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": f"{SCORING_PROMPT}\n\n{numbered}"}],
    )
    text = resp.content[0].text.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        scores = json.loads(text)
        if isinstance(scores, list) and len(scores) == len(titles):
            return scores
        print(f"  Length mismatch: got {len(scores)}, expected {len(titles)}", flush=True)
        return None
    except json.JSONDecodeError:
        print(f"  Parse error: {text[:100]}", flush=True)
        return None


def main():
    client = Anthropic()
    conn = sqlite3.connect("data/thisminute.db")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")

    # Get all stories with extractions
    rows = conn.execute("""
        SELECT se.story_id, s.title, se.human_interest_score
        FROM story_extractions se
        JOIN stories s ON s.id = se.story_id
        WHERE s.title IS NOT NULL AND length(s.title) > 10
        ORDER BY se.story_id
    """).fetchall()

    total = len(rows)
    print(f"Re-scoring {total} stories in batches of {BATCH_SIZE}", flush=True)
    print(f"Estimated API calls: {(total + BATCH_SIZE - 1) // BATCH_SIZE}", flush=True)

    updated = 0
    errors = 0
    changed = 0
    start = time.time()

    for i in range(0, total, BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        ids = [r[0] for r in batch]
        titles = [r[1] for r in batch]
        old_scores = [r[2] for r in batch]

        scores = score_batch(client, titles)
        if scores is None:
            # Retry once
            time.sleep(1)
            scores = score_batch(client, titles)

        if scores is None:
            errors += len(batch)
            print(f"  Batch {i//BATCH_SIZE + 1}: FAILED (skipping {len(batch)} stories)", flush=True)
            continue

        # Update DB
        for j, (story_id, score) in enumerate(zip(ids, scores)):
            score = max(1, min(10, int(score)))  # clamp
            conn.execute(
                "UPDATE story_extractions SET human_interest_score = ? WHERE story_id = ?",
                (score, story_id)
            )
            if old_scores[j] != score:
                changed += 1
            updated += 1

        conn.commit()

        batch_num = i // BATCH_SIZE + 1
        total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
        elapsed = time.time() - start
        rate = updated / elapsed if elapsed > 0 else 0
        eta = (total - updated) / rate if rate > 0 else 0

        if batch_num % 10 == 0 or batch_num == total_batches:
            print(f"  Batch {batch_num}/{total_batches}: {updated}/{total} done, "
                  f"{changed} changed, {errors} errors, "
                  f"{rate:.0f}/s, ETA {eta:.0f}s", flush=True)

    conn.close()
    elapsed = time.time() - start

    print(f"\nDone in {elapsed:.1f}s", flush=True)
    print(f"  Updated: {updated}/{total}", flush=True)
    print(f"  Changed: {changed} ({changed*100//max(updated,1)}%)", flush=True)
    print(f"  Errors:  {errors}", flush=True)


if __name__ == "__main__":
    main()
