"""Curious scoring benchmark: Compare human_interest_score across models.

Two modes:
  python scripts/test_curious_scoring.py          # Random sample from DB, all 3 models
  python scripts/test_curious_scoring.py --golden  # Fixed golden set, haiku only (for drift detection)

The golden set has Opus-scored reference values. Run --golden periodically to check
if haiku scoring has drifted (e.g., after model updates or prompt changes).
"""
import sqlite3
import json
import os
import sys

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

MODELS = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-6",
}

# Golden set: fixed titles with Opus reference scores (from 2026-03-16 benchmark).
# Used for drift detection — run with --golden to check if haiku still agrees.
GOLDEN_SET = [
    ("Israeli soldiers kill family of four, including two children, in occupied West Bank", 1),
    ("Severe Thunderstorm Warning issued March 15 at 3:54PM EDT until March 15 at 4:30PM EDT", 1),
    ("Iran war: Trump dials up the pressure to secure Hormuz", 2),
    ("Zelensky plotting suspending elections for years - media", 2),
    ("Wind Advisory issued March 16 at 1:45AM EDT until March 16 at 7:00PM EDT", 1),
    ("Oscar winners announced at 97th Academy Awards ceremony", 3),
    ("Harry Styles hosts SNL, performs new album tracks", 3),
    ("Venus again exits in first round at Indian Wells", 2),
    ("Senate passes budget resolution after marathon session", 2),
    ("Company reports Q3 earnings beat expectations", 1),
    ("Hedgehogs Could Avoid Extinction by Silent Ultrasound Installed on Cars", 8),
    ("Dog elected honorary mayor of small Vermont town for third term", 9),
    ("Scientists discover New Zealand-sized continent hidden under the Pacific", 9),
    ("92-year-old grandmother graduates college alongside her granddaughter", 8),
    ("Man builds working rollercoaster in his garage using salvaged parts", 8),
    ("New deep-sea species discovered living in backyard pond in Devon", 8),
    ("Twins reunited after 60 years via DNA test at the same grocery store", 7),
    ("AI helps create personalized cancer vaccine for dying dog, now in remission", 8),
    ("Verstappen to enter Nurburgring 24 Hours with Mercedes team", 6),
    ("Scientists discover AI can make humans more creative in controlled study", 5),
    ("Lebanese Family Members of Synagogue Attacker Died in Airstrike", 1),
    ("Two students die in university meningitis outbreak", 1),
    ("Funeral arrangements announced of Noah Sikora (3), killed in shopping centre car park", 1),
    ("Pope Leo decries 'atrocious violence' in Iran war, urges ceasefire", 2),
    ("THOR AI solves a 100-year-old physics problem in seconds", 7),
    ("Fortnite-maker raising in-game currency prices 'to help pay the bills'", 4),
    ("Steven Spielberg Issues Timothee Chalamet Dig, Teases Western In Development", 4),
    ("The Jewish Cemeteries Giving Life to Morocco's Muslim Communities", 6),
    ("Hawaii University Hauls 84 Tons of Derelict Fishing Gear from Pacific Ocean Garbage Patch", 5),
    ("The women bringing chess into the 21st Century - with 'bullet' matches and viral videos", 6),
]


def score_with_model(client, model_id, titles):
    numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(titles))
    resp = client.messages.create(
        model=model_id,
        max_tokens=500,
        messages=[{"role": "user", "content": f"{SCORING_PROMPT}\n\n{numbered}"}],
    )
    text = resp.content[0].text.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print(f"  Failed to parse {model_id} response: {text[:200]}", flush=True)
        return None


def run_golden():
    """Run haiku against the fixed golden set and check for drift."""
    client = Anthropic()
    titles = [g[0] for g in GOLDEN_SET]
    opus_ref = [g[1] for g in GOLDEN_SET]

    print(f"Golden set benchmark: {len(titles)} stories, haiku vs opus reference\n", flush=True)
    print("Scoring with haiku...", flush=True)
    haiku_scores = score_with_model(client, MODELS["haiku"], titles)

    if not haiku_scores or len(haiku_scores) != len(titles):
        print("ERROR: haiku returned wrong number of scores", flush=True)
        return

    print(f"\n{'#':>3} {'Opus':>5} {'Haiku':>6} {'Diff':>5}  Title", flush=True)
    print("-" * 100, flush=True)

    diffs = []
    for i, (title, ref) in enumerate(GOLDEN_SET):
        h = haiku_scores[i]
        d = h - ref
        diffs.append(abs(d))
        flag = " ***" if abs(d) >= 3 else " **" if abs(d) >= 2 else ""
        safe = title[:65].encode('ascii', 'replace').decode()
        print(f"{i+1:>3} {ref:>5} {h:>6} {d:>+5}  {safe}{flag}", flush=True)

    avg = sum(diffs) / len(diffs)
    exact = sum(1 for d in diffs if d == 0)
    close = sum(1 for d in diffs if d <= 1)

    print(f"\n{'='*80}", flush=True)
    print(f"Avg diff: {avg:.1f}  |  Exact: {exact}/{len(titles)}  |  Within 1: {close}/{len(titles)}", flush=True)

    # Regression checks
    tragedy_titles = [i for i, (t, _) in enumerate(GOLDEN_SET) if any(w in t.lower() for w in ["kill", "die", "dead", "war", "attack"])]
    quirky_titles = [i for i, (_, s) in enumerate(GOLDEN_SET) if s >= 7]

    tragedy_scores = [haiku_scores[i] for i in tragedy_titles]
    quirky_scores = [haiku_scores[i] for i in quirky_titles]

    tragedy_ok = all(s <= 3 for s in tragedy_scores)
    quirky_ok = all(s >= 5 for s in quirky_scores)

    print(f"\nTragedy stories (should be <=3): {'PASS' if tragedy_ok else 'FAIL'} {tragedy_scores}", flush=True)
    print(f"Quirky stories (should be >=5):  {'PASS' if quirky_ok else 'FAIL'} {quirky_scores}", flush=True)

    if avg > 1.5 or not tragedy_ok:
        print("\n*** DRIFT DETECTED — haiku scoring may have regressed ***", flush=True)
        sys.exit(1)
    else:
        print("\nAll good — haiku scoring is consistent with opus reference.", flush=True)


def run_abc():
    """Full ABC comparison with random stories from the DB."""
    client = Anthropic()
    conn = sqlite3.connect("data/thisminute.db")
    stories = conn.execute("""
        SELECT s.id, s.title, se.human_interest_score
        FROM stories s JOIN story_extractions se ON se.story_id = s.id
        WHERE s.title IS NOT NULL AND length(s.title) > 20
        ORDER BY RANDOM() LIMIT 30
    """).fetchall()
    conn.close()
    titles = [s[1] for s in stories]

    print(f"ABC test: {len(titles)} random stories across 3 models\n", flush=True)

    results = {}
    for name, model_id in MODELS.items():
        print(f"Scoring with {name} ({model_id})...", flush=True)
        scores = score_with_model(client, model_id, titles)
        if scores and len(scores) == len(titles):
            results[name] = scores
            print(f"  Got {len(scores)} scores", flush=True)
        else:
            print(f"  ERROR: got {len(scores) if scores else 0} scores", flush=True)

    if len(results) < 2:
        print("Not enough models returned valid results.", flush=True)
        return

    print(f"\n{'#':>3} {'Old':>4} ", end="", flush=True)
    for name in results:
        print(f"{name:>7} ", end="")
    print("  Title")
    print("-" * 120, flush=True)

    for i, (sid, title, old_score) in enumerate(stories):
        old = str(old_score) if old_score is not None else "-"
        print(f"{i+1:>3} {old:>4} ", end="", flush=True)
        for name in results:
            print(f"{results[name][i]:>7} ", end="")
        vals = [results[name][i] for name in results]
        spread = max(vals) - min(vals)
        flag = " ***" if spread >= 4 else " *" if spread >= 3 else ""
        safe = title[:70].encode('ascii', 'replace').decode()
        print(f"  {safe}{flag}", flush=True)

    print(f"\n{'='*80}", flush=True)
    if "opus" in results:
        for name in results:
            if name == "opus":
                continue
            diffs = [abs(results[name][i] - results["opus"][i]) for i in range(len(titles))]
            avg_diff = sum(diffs) / len(diffs)
            exact = sum(1 for d in diffs if d == 0)
            close = sum(1 for d in diffs if d <= 1)
            print(f"{name} vs opus: avg diff={avg_diff:.1f}, exact={exact}/{len(titles)}, within 1={close}/{len(titles)}", flush=True)


if __name__ == "__main__":
    if "--golden" in sys.argv:
        run_golden()
    else:
        run_abc()
