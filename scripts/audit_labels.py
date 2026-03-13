"""Audit registry labels and fix bad ones.

Finds labels that violate the rules and runs LLM maintenance
with a larger batch size to fix them.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import get_connection, init_db, get_active_registry_events, update_registry_event
from src.llm_utils import get_anthropic_client, parse_llm_json, HAIKU_MODEL
from src.label_rules import MAP_LABEL_RULES

BANNED_WORDS = {
    "crisis", "situation", "issues", "developments", "concerns", "tensions",
    "problems", "unrest", "turmoil", "upheaval", "challenges", "dynamics",
    "matters", "affairs", "conditions", "circumstances", "implications",
    "ramifications", "aspects", "factors", "elements", "dramatically",
}

PASSIVE_WORDS = {"receives", "publishes", "faces", "amid", "draws", "raises", "sparks"}


def audit():
    init_db()
    conn = get_connection()
    events = get_active_registry_events(conn, limit=200)
    print(f"Total active registry events: {len(events)}", flush=True)

    bad = []
    for ev in events:
        label = ev["map_label"]
        words = label.lower().split()
        reasons = []

        if len(words) > 4:
            reasons.append(f"too long ({len(words)} words)")
        if any(w in BANNED_WORDS for w in words):
            reasons.append("banned filler word")
        if any(w in PASSIVE_WORDS for w in words):
            reasons.append("passive/observational")
        if label == "Events reported":
            reasons.append("completely generic")

        if reasons:
            bad.append(ev)
            print(f"  BAD R{ev['id']}: \"{label}\" ({ev['story_count']} stories) - {', '.join(reasons)}", flush=True)

    print(f"\n{len(bad)} bad labels out of {len(events)} total", flush=True)

    if not bad:
        conn.close()
        return

    # Fix bad labels with LLM
    client = get_anthropic_client()
    if not client:
        print("No API key - can't fix labels", flush=True)
        conn.close()
        return

    # Process in batches of 30
    fixed = 0
    for i in range(0, len(bad), 30):
        batch = bad[i:i+30]
        lines = []
        for ev in batch:
            lines.append(
                f"R{ev['id']}: registry_label=\"{ev['registry_label']}\" "
                f"map_label=\"{ev['map_label']}\" stories={ev['story_count']}"
            )

        prompt = f"""Fix these map_labels for a news map. Each label is currently BAD.

{chr(10).join(lines)}

{MAP_LABEL_RULES}

Return a JSON array of fixes:
[{{"id": R_ID, "new_map_label": "..."}}]

Fix EVERY label listed. Return ONLY valid JSON."""

        try:
            response = client.messages.create(
                model=HAIKU_MODEL,
                max_tokens=50 * len(batch),
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            print(f"  Batch {i}: raw response ({len(text)} chars): {text[:200]}...", flush=True)
            fixes = parse_llm_json(text, expected_type="list")
            if not fixes:
                print(f"  Batch {i}: LLM returned unparseable response", flush=True)
                continue
            print(f"  Batch {i}: got {len(fixes)} fixes", flush=True)

            valid_ids = {ev["id"] for ev in batch}
            for fix in fixes:
                rid = fix.get("id")
                # Normalize: "R1108" -> 1108
                if isinstance(rid, str) and rid.startswith("R"):
                    try:
                        rid = int(rid[1:])
                    except ValueError:
                        continue
                elif isinstance(rid, str):
                    try:
                        rid = int(rid)
                    except ValueError:
                        continue
                new_label = fix.get("new_map_label", "")
                if rid in valid_ids and new_label:
                    update_registry_event(conn, rid, map_label=new_label)
                    fixed += 1
                    print(f"  Fixed R{rid}: \"{new_label}\"", flush=True)
        except Exception as e:
            print(f"  Batch {i} failed: {e}", flush=True)

    conn.close()
    print(f"\nFixed {fixed} labels", flush=True)


if __name__ == "__main__":
    audit()
