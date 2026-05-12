"""Compare Haiku vs Gemini Flash extraction quality on real stories.

Pulls stories that already have Haiku extractions from the DB, re-runs
them through Gemini 2.5 Flash with the same prompt, and compares results.

Usage:
    python scripts/model_comparison.py --gemini-key YOUR_KEY [--count 100] [--batch-size 8]

Set GEMINI_API_KEY env var as alternative to --gemini-key flag.
"""

import argparse
import json
import logging
import os
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path
from textwrap import dedent

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.llm_extractor import (
    SYSTEM_PROMPT,
    _build_story_text,
    _build_registry_block,
    _build_wiki_events_block,
    _build_signatures_block,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DB_PATH = PROJECT_ROOT / "data" / "thisminute.db"

# Fields to compare and how
EXACT_FIELDS = ["sentiment", "location_type", "is_opinion"]
NUMERIC_FIELDS = ["severity", "human_interest_score"]
LIST_FIELDS = ["topics", "search_keywords", "affected_parties"]
STRUCT_FIELDS = ["actors", "locations", "bright_side"]
TEXT_FIELDS = ["event_signature", "primary_action", "translated_title"]


def get_stories_with_extractions(db_path: Path, count: int) -> list[dict]:
    """Pull recent stories that have Haiku extractions from DB."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT s.id, s.title, s.summary, s.source, s.location_name, s.lat, s.lon,
                  s.scraped_at, se.extraction_json
           FROM stories s
           JOIN story_extractions se ON se.story_id = s.id
           WHERE s.source_type = 'reported'
             AND se.extraction_json IS NOT NULL
           ORDER BY s.id DESC
           LIMIT ?""",
        (count,),
    ).fetchall()
    conn.close()

    results = []
    for r in rows:
        try:
            extraction = json.loads(r["extraction_json"])
        except (json.JSONDecodeError, TypeError):
            continue
        results.append({
            "story": {
                "id": r["id"],
                "title": r["title"],
                "summary": r["summary"],
                "source": r["source"],
                "location_name": r["location_name"],
                "lat": r["lat"],
                "lon": r["lon"],
                "scraped_at": r["scraped_at"],
            },
            "haiku_extraction": extraction,
        })
    return results


def call_gemini_batch(client, stories: list[dict], model: str = "gemini-2.5-flash") -> list[dict] | None:
    """Call Gemini Flash with the same prompt format as Haiku."""
    numbered = []
    for i, story in enumerate(stories, 1):
        numbered.append(f"{i}. {_build_story_text(story)}")

    user_prompt = f"Extract structured data from these {len(stories)} stories:\n\n" + "\n".join(numbered)

    try:
        response = client.models.generate_content(
            model=model,
            contents=user_prompt,
            config={
                "system_instruction": SYSTEM_PROMPT,
                "temperature": 0.0,
                "max_output_tokens": len(stories) * 1500,
            },
        )

        text = response.text.strip()
        # Strip code fences
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        extractions = json.loads(text)
        if isinstance(extractions, list):
            return extractions
        logger.warning("Gemini returned non-array: %s", type(extractions))
        return None

    except json.JSONDecodeError as e:
        logger.warning("Gemini JSON parse failed: %s", e)
        # Try extracting objects
        try:
            # Find the array
            start = text.index("[")
            end = text.rindex("]") + 1
            extractions = json.loads(text[start:end])
            if isinstance(extractions, list):
                return extractions
        except (ValueError, json.JSONDecodeError):
            pass
        return None
    except Exception as e:
        logger.warning("Gemini API call failed: %s", e)
        return None


def compare_exact(haiku_val, gemini_val) -> dict:
    """Compare exact-match fields."""
    match = haiku_val == gemini_val
    return {"match": match, "haiku": haiku_val, "gemini": gemini_val}


def compare_numeric(haiku_val, gemini_val) -> dict:
    """Compare numeric fields — allow ±1 tolerance."""
    if haiku_val is None and gemini_val is None:
        return {"match": True, "exact": True, "diff": 0}
    if haiku_val is None or gemini_val is None:
        return {"match": False, "exact": False, "diff": None, "haiku": haiku_val, "gemini": gemini_val}
    diff = abs(haiku_val - gemini_val)
    return {"match": diff <= 1, "exact": diff == 0, "diff": diff}


def compare_list_overlap(haiku_list, gemini_list) -> dict:
    """Compare list fields by Jaccard similarity."""
    h = set(haiku_list or [])
    g = set(gemini_list or [])
    if not h and not g:
        return {"jaccard": 1.0, "overlap": 0, "haiku_only": 0, "gemini_only": 0}
    union = h | g
    inter = h & g
    return {
        "jaccard": len(inter) / len(union) if union else 1.0,
        "overlap": len(inter),
        "haiku_only": len(h - g),
        "gemini_only": len(g - h),
    }


def compare_event_signature(haiku_sig: str, gemini_sig: str) -> dict:
    """Compare event signatures — word overlap since exact match is unlikely."""
    h_words = set((haiku_sig or "").lower().split())
    g_words = set((gemini_sig or "").lower().split())
    if not h_words and not g_words:
        return {"word_overlap": 1.0, "exact": True}
    inter = h_words & g_words
    union = h_words | g_words
    return {
        "word_overlap": len(inter) / len(union) if union else 0.0,
        "exact": haiku_sig == gemini_sig,
        "haiku": haiku_sig,
        "gemini": gemini_sig,
    }


def compare_actors(haiku_actors: list, gemini_actors: list) -> dict:
    """Compare actor extraction — names found, roles assigned."""
    h_names = {a.get("name", "").lower().strip() for a in (haiku_actors or []) if a.get("name")}
    g_names = {a.get("name", "").lower().strip() for a in (gemini_actors or []) if a.get("name")}

    name_inter = h_names & g_names
    name_union = h_names | g_names

    # Role agreement for shared actors
    role_matches = 0
    role_total = 0
    for h_actor in (haiku_actors or []):
        h_name = (h_actor.get("name") or "").lower().strip()
        if h_name in name_inter:
            for g_actor in (gemini_actors or []):
                if (g_actor.get("name") or "").lower().strip() == h_name:
                    role_total += 1
                    if h_actor.get("role") == g_actor.get("role"):
                        role_matches += 1
                    break

    return {
        "name_jaccard": len(name_inter) / len(name_union) if name_union else 1.0,
        "haiku_count": len(h_names),
        "gemini_count": len(g_names),
        "shared_names": len(name_inter),
        "role_agreement": role_matches / role_total if role_total else None,
        "role_matches": role_matches,
        "role_total": role_total,
    }


def compare_locations(haiku_locs: list, gemini_locs: list) -> dict:
    """Compare location extraction."""
    h_names = {loc.get("name", "").lower().strip() for loc in (haiku_locs or []) if loc.get("name")}
    g_names = {loc.get("name", "").lower().strip() for loc in (gemini_locs or []) if loc.get("name")}
    inter = h_names & g_names
    union = h_names | g_names
    return {
        "name_jaccard": len(inter) / len(union) if union else 1.0,
        "haiku_count": len(h_names),
        "gemini_count": len(g_names),
        "shared": len(inter),
    }


def compare_bright_side(haiku_bs, gemini_bs) -> dict:
    """Compare bright_side — presence agreement + score diff."""
    h_present = haiku_bs is not None
    g_present = gemini_bs is not None
    presence_match = h_present == g_present

    if h_present and g_present:
        h_score = haiku_bs.get("score", 0)
        g_score = gemini_bs.get("score", 0)
        cat_match = haiku_bs.get("category") == gemini_bs.get("category")
        return {
            "presence_match": True,
            "score_diff": abs(h_score - g_score),
            "category_match": cat_match,
            "both_present": True,
        }
    return {
        "presence_match": presence_match,
        "both_present": False,
        "haiku_present": h_present,
        "gemini_present": g_present,
    }


def run_comparison(stories_data: list[dict], gemini_client, batch_size: int = 8,
                   gemini_model: str = "gemini-2.5-flash") -> dict:
    """Run full comparison and return aggregate stats."""
    all_comparisons = []
    failures = 0
    json_failures = 0

    total_batches = (len(stories_data) + batch_size - 1) // batch_size

    for batch_num, i in enumerate(range(0, len(stories_data), batch_size), 1):
        batch = stories_data[i:i + batch_size]
        stories_for_gemini = [item["story"] for item in batch]

        logger.info("Batch %d/%d (%d stories)...", batch_num, total_batches, len(batch))

        gemini_extractions = call_gemini_batch(gemini_client, stories_for_gemini, model=gemini_model)

        if gemini_extractions is None:
            json_failures += len(batch)
            logger.warning("  Batch %d: Gemini returned unparseable response", batch_num)
            continue

        if len(gemini_extractions) < len(batch):
            logger.warning("  Batch %d: Gemini returned %d/%d extractions",
                           batch_num, len(gemini_extractions), len(batch))

        matched = min(len(gemini_extractions), len(batch))
        for j in range(matched):
            haiku_ext = batch[j]["haiku_extraction"]
            gemini_ext = gemini_extractions[j]

            comp = {
                "story_id": batch[j]["story"]["id"],
                "title": batch[j]["story"]["title"][:80],
                "source": batch[j]["story"]["source"],
            }

            # Exact fields
            for field in EXACT_FIELDS:
                comp[field] = compare_exact(haiku_ext.get(field), gemini_ext.get(field))

            # Numeric fields
            for field in NUMERIC_FIELDS:
                comp[field] = compare_numeric(haiku_ext.get(field), gemini_ext.get(field))

            # Event signature (the critical one)
            comp["event_signature"] = compare_event_signature(
                haiku_ext.get("event_signature"), gemini_ext.get("event_signature")
            )

            # Topics overlap
            comp["topics"] = compare_list_overlap(haiku_ext.get("topics"), gemini_ext.get("topics"))

            # Actors
            comp["actors"] = compare_actors(haiku_ext.get("actors"), gemini_ext.get("actors"))

            # Locations
            comp["locations"] = compare_locations(haiku_ext.get("locations"), gemini_ext.get("locations"))

            # Bright side
            comp["bright_side"] = compare_bright_side(haiku_ext.get("bright_side"), gemini_ext.get("bright_side"))

            # Human interest score
            comp["human_interest_score"] = compare_numeric(
                haiku_ext.get("human_interest_score"), gemini_ext.get("human_interest_score")
            )

            # Search keywords overlap
            comp["search_keywords"] = compare_list_overlap(
                haiku_ext.get("search_keywords"), gemini_ext.get("search_keywords")
            )

            all_comparisons.append(comp)

        failures += len(batch) - matched

        # Rate limit courtesy
        if batch_num < total_batches:
            time.sleep(1.0)

    return aggregate_stats(all_comparisons, failures, json_failures)


def aggregate_stats(comparisons: list[dict], failures: int, json_failures: int) -> dict:
    """Compute aggregate quality metrics from per-story comparisons."""
    n = len(comparisons)
    if n == 0:
        return {"error": "No successful comparisons", "failures": failures, "json_failures": json_failures}

    stats = {
        "total_compared": n,
        "api_failures": failures,
        "json_parse_failures": json_failures,
    }

    # Exact match rates
    for field in EXACT_FIELDS:
        matches = sum(1 for c in comparisons if c[field]["match"])
        stats[f"{field}_agreement"] = f"{matches}/{n} ({100 * matches / n:.1f}%)"

    # Severity agreement
    sev_exact = sum(1 for c in comparisons if c["severity"]["exact"])
    sev_close = sum(1 for c in comparisons if c["severity"]["match"])
    diffs = [c["severity"]["diff"] for c in comparisons if c["severity"]["diff"] is not None]
    stats["severity_exact"] = f"{sev_exact}/{n} ({100 * sev_exact / n:.1f}%)"
    stats["severity_within_1"] = f"{sev_close}/{n} ({100 * sev_close / n:.1f}%)"
    stats["severity_avg_diff"] = f"{sum(diffs) / len(diffs):.2f}" if diffs else "N/A"

    # Event signature — the critical metric
    sig_exact = sum(1 for c in comparisons if c["event_signature"]["exact"])
    sig_overlaps = [c["event_signature"]["word_overlap"] for c in comparisons]
    stats["event_signature_exact_match"] = f"{sig_exact}/{n} ({100 * sig_exact / n:.1f}%)"
    stats["event_signature_avg_word_overlap"] = f"{sum(sig_overlaps) / len(sig_overlaps):.2f}"

    # Topics overlap
    topic_jaccards = [c["topics"]["jaccard"] for c in comparisons]
    stats["topics_avg_jaccard"] = f"{sum(topic_jaccards) / len(topic_jaccards):.2f}"

    # Actors
    actor_jaccards = [c["actors"]["name_jaccard"] for c in comparisons]
    role_agreements = [c["actors"]["role_agreement"] for c in comparisons if c["actors"]["role_agreement"] is not None]
    stats["actors_avg_name_jaccard"] = f"{sum(actor_jaccards) / len(actor_jaccards):.2f}"
    stats["actors_role_agreement"] = (
        f"{sum(role_agreements) / len(role_agreements):.2f} ({len(role_agreements)} stories with shared actors)"
        if role_agreements else "N/A (no shared actors)"
    )

    # Locations
    loc_jaccards = [c["locations"]["name_jaccard"] for c in comparisons]
    stats["locations_avg_name_jaccard"] = f"{sum(loc_jaccards) / len(loc_jaccards):.2f}"

    # Bright side
    bs_presence = sum(1 for c in comparisons if c["bright_side"]["presence_match"])
    stats["bright_side_presence_agreement"] = f"{bs_presence}/{n} ({100 * bs_presence / n:.1f}%)"
    bs_both = [c["bright_side"] for c in comparisons if c["bright_side"].get("both_present")]
    if bs_both:
        cat_matches = sum(1 for b in bs_both if b.get("category_match"))
        score_diffs = [b["score_diff"] for b in bs_both]
        stats["bright_side_category_agreement"] = f"{cat_matches}/{len(bs_both)} ({100 * cat_matches / len(bs_both):.1f}%)"
        stats["bright_side_avg_score_diff"] = f"{sum(score_diffs) / len(score_diffs):.2f}"

    # Human interest score
    hi_close = sum(1 for c in comparisons if c["human_interest_score"]["match"])
    hi_exact = sum(1 for c in comparisons if c["human_interest_score"]["exact"])
    stats["human_interest_within_1"] = f"{hi_close}/{n} ({100 * hi_close / n:.1f}%)"
    stats["human_interest_exact"] = f"{hi_exact}/{n} ({100 * hi_exact / n:.1f}%)"

    # Search keywords
    kw_jaccards = [c["search_keywords"]["jaccard"] for c in comparisons]
    stats["search_keywords_avg_jaccard"] = f"{sum(kw_jaccards) / len(kw_jaccards):.2f}"

    # Find worst event_signature mismatches for manual review
    sig_mismatches = sorted(
        [c for c in comparisons if not c["event_signature"]["exact"]],
        key=lambda c: c["event_signature"]["word_overlap"],
    )[:10]

    stats["worst_signature_mismatches"] = [
        {
            "title": c["title"],
            "haiku": c["event_signature"]["haiku"],
            "gemini": c["event_signature"]["gemini"],
            "word_overlap": f"{c['event_signature']['word_overlap']:.2f}",
        }
        for c in sig_mismatches
    ]

    return stats


def print_report(stats: dict):
    """Print a human-readable comparison report."""
    print("\n" + "=" * 70)
    print("MODEL COMPARISON: Haiku 4.5 vs Gemini 2.5 Flash")
    print("=" * 70)

    print(f"\nStories compared: {stats['total_compared']}")
    print(f"API failures: {stats['api_failures']}")
    print(f"JSON parse failures: {stats['json_parse_failures']}")

    print("\n--- CLASSIFICATION AGREEMENT ---")
    for field in EXACT_FIELDS:
        key = f"{field}_agreement"
        if key in stats:
            print(f"  {field:20s} {stats[key]}")

    print("\n--- NUMERIC FIELDS ---")
    print(f"  severity exact:       {stats.get('severity_exact', 'N/A')}")
    print(f"  severity ±1:          {stats.get('severity_within_1', 'N/A')}")
    print(f"  severity avg diff:    {stats.get('severity_avg_diff', 'N/A')}")
    print(f"  human_interest exact: {stats.get('human_interest_exact', 'N/A')}")
    print(f"  human_interest ±1:    {stats.get('human_interest_within_1', 'N/A')}")

    print("\n--- EVENT SIGNATURE (CRITICAL) ---")
    print(f"  exact match:          {stats.get('event_signature_exact_match', 'N/A')}")
    print(f"  avg word overlap:     {stats.get('event_signature_avg_word_overlap', 'N/A')}")

    print("\n--- ENTITY EXTRACTION ---")
    print(f"  topics jaccard:       {stats.get('topics_avg_jaccard', 'N/A')}")
    print(f"  actors name jaccard:  {stats.get('actors_avg_name_jaccard', 'N/A')}")
    print(f"  actors role agree:    {stats.get('actors_role_agreement', 'N/A')}")
    print(f"  locations jaccard:    {stats.get('locations_avg_name_jaccard', 'N/A')}")
    print(f"  keywords jaccard:     {stats.get('search_keywords_avg_jaccard', 'N/A')}")

    print("\n--- BRIGHT SIDE ---")
    print(f"  presence agreement:   {stats.get('bright_side_presence_agreement', 'N/A')}")
    if "bright_side_category_agreement" in stats:
        print(f"  category agreement:   {stats['bright_side_category_agreement']}")
        print(f"  avg score diff:       {stats['bright_side_avg_score_diff']}")

    # Worst signature mismatches
    mismatches = stats.get("worst_signature_mismatches", [])
    if mismatches:
        print(f"\n--- WORST EVENT SIGNATURE MISMATCHES (top {len(mismatches)}) ---")
        for m in mismatches:
            print(f"\n  \"{m['title']}\"")
            print(f"    Haiku:  \"{m['haiku']}\"")
            print(f"    Gemini: \"{m['gemini']}\"")
            print(f"    Word overlap: {m['word_overlap']}")

    print("\n" + "=" * 70)

    # Verdict
    sig_overlap = float(stats.get("event_signature_avg_word_overlap", "0"))
    sentiment_pct = _extract_pct(stats.get("sentiment_agreement", "0/0 (0%)"))
    loc_type_pct = _extract_pct(stats.get("location_type_agreement", "0/0 (0%)"))

    print("\nVERDICT:")
    if sig_overlap >= 0.6 and sentiment_pct >= 85 and loc_type_pct >= 90:
        print("  [PASS] Gemini Flash looks VIABLE for extraction.")
        print("     Signature overlap is strong enough for clustering.")
        print("     Consider running in shadow mode for a week before switching.")
    elif sig_overlap >= 0.4 and sentiment_pct >= 75:
        print("  [MARGINAL] Gemini Flash is MARGINAL.")
        print("     Signature overlap may cause clustering fragmentation.")
        print("     Consider the split-prompt approach (cheap model for classification, Haiku for signatures).")
    else:
        print("  [FAIL] Gemini Flash is NOT READY for this prompt.")
        print("     Significant divergence in critical fields.")
        print("     Keep Haiku or try a different model.")

    print()


def _extract_pct(s: str) -> float:
    """Extract percentage from a formatted string like '85/100 (85.0%)'."""
    try:
        return float(s.split("(")[1].rstrip("%)"))
    except (IndexError, ValueError):
        return 0.0


def main():
    parser = argparse.ArgumentParser(description="Compare Haiku vs Gemini Flash extraction quality")
    parser.add_argument("--gemini-key", help="Google AI API key (or set GEMINI_API_KEY env var)")
    parser.add_argument("--count", type=int, default=100, help="Number of stories to compare (default: 100)")
    parser.add_argument("--batch-size", type=int, default=8, help="Batch size for Gemini calls (default: 8)")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Gemini model to test (default: gemini-2.5-flash)")
    parser.add_argument("--output", help="Save raw comparison data to JSON file")
    parser.add_argument("--db", help="Path to DB file (default: data/thisminute.db)")
    args = parser.parse_args()

    # Get API key
    api_key = args.gemini_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: No Gemini API key. Use --gemini-key or set GEMINI_API_KEY env var.")
        print("Get one free at: https://aistudio.google.com/apikey")
        sys.exit(1)

    db_path = Path(args.db) if args.db else DB_PATH
    if not db_path.exists():
        print(f"ERROR: Database not found at {db_path}")
        print("Copy it from the VM: gcloud compute scp thisminute:/opt/thisminute/data/thisminute.db data/")
        sys.exit(1)

    # Load stories
    logger.info("Loading %d stories with Haiku extractions from %s...", args.count, db_path)
    stories_data = get_stories_with_extractions(db_path, args.count)
    logger.info("Loaded %d stories with existing Haiku extractions", len(stories_data))

    if not stories_data:
        print("ERROR: No stories with extractions found in database.")
        sys.exit(1)

    # Initialize Gemini client
    from google import genai
    client = genai.Client(api_key=api_key)

    # Run comparison
    logger.info("Running %d stories through %s...", len(stories_data), args.model)
    stats = run_comparison(stories_data, client, batch_size=args.batch_size, gemini_model=args.model)

    # Print report
    print_report(stats)

    # Optionally save raw data
    if args.output:
        with open(args.output, "w") as f:
            json.dump(stats, f, indent=2)
        logger.info("Raw stats saved to %s", args.output)

    # Cost estimate
    print("--- COST COMPARISON ---")
    print(f"  Stories compared: {stats['total_compared']}")
    est_daily = 2800  # typical daily volume
    batches_per_day = est_daily / args.batch_size
    haiku_daily = batches_per_day * (7000 * 1.0 + 2000 * 5.0) / 1_000_000
    gemini_daily = batches_per_day * (7000 * 0.30 + 2000 * 2.50) / 1_000_000
    print(f"  Estimated daily cost (Haiku):        ${haiku_daily:.2f}")
    print(f"  Estimated daily cost (Gemini Flash):  ${gemini_daily:.2f}")
    print(f"  Savings:                              ${haiku_daily - gemini_daily:.2f}/day ({100 * (1 - gemini_daily / haiku_daily):.0f}%)")
    print()


if __name__ == "__main__":
    main()
