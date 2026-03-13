"""Event registry maintenance: merge duplicates, retire stale events, refine labels.

Runs periodically (e.g., every hour) to keep the registry clean.
"""

import json
import logging
from datetime import datetime, timezone, timedelta

from .database import (
    get_active_registry_events,
    update_registry_event,
    merge_registry_events,
)
from .label_rules import MAP_LABEL_RULES
from .llm_utils import get_anthropic_client, parse_llm_json, HAIKU_MODEL

logger = logging.getLogger(__name__)

# Hours with no new stories before an event is retired
RETIRE_HOURS = 48

# Max active events in registry (oldest retired if exceeded)
MAX_ACTIVE_EVENTS = 200

# Max events to include in LLM maintenance call
MAINTENANCE_BATCH_SIZE = 60


def retire_stale_events(conn) -> int:
    """Retire events with no new stories for RETIRE_HOURS."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=RETIRE_HOURS)).isoformat()
    cursor = conn.execute(
        """UPDATE event_registry SET status = 'retired', retired_at = ?
           WHERE status = 'active' AND last_matched < ?""",
        (datetime.now(timezone.utc).isoformat(), cutoff),
    )
    conn.commit()
    retired = cursor.rowcount
    if retired:
        logger.info("Registry: retired %d stale events", retired)
    return retired


def cap_registry_size(conn) -> int:
    """If too many active events, retire the oldest ones."""
    events = get_active_registry_events(conn, limit=MAX_ACTIVE_EVENTS + 50)
    if len(events) <= MAX_ACTIVE_EVENTS:
        return 0
    to_retire = events[MAX_ACTIVE_EVENTS:]
    now = datetime.now(timezone.utc).isoformat()
    for ev in to_retire:
        conn.execute(
            "UPDATE event_registry SET status = 'retired', retired_at = ? WHERE id = ?",
            (now, ev["id"]),
        )
    conn.commit()
    logger.info("Registry: capped size, retired %d excess events", len(to_retire))
    return len(to_retire)


def llm_maintenance(conn) -> dict:
    """Use LLM to review the registry: merge duplicates and refine labels.

    Returns stats: {"merged": int, "relabeled": int}
    """
    client = get_anthropic_client()
    if not client:
        return {"merged": 0, "relabeled": 0}

    events = get_active_registry_events(conn, limit=MAINTENANCE_BATCH_SIZE)
    if len(events) < 2:
        return {"merged": 0, "relabeled": 0}

    event_lines = []
    for ev in events:
        event_lines.append(
            f"R{ev['id']}: registry_label=\"{ev['registry_label']}\" "
            f"map_label=\"{ev['map_label']}\" stories={ev['story_count']} "
            f"location=\"{ev.get('primary_location') or ''}\""
        )

    prompt = f"""Review this event registry for a real-time news map. Find issues and fix them.

{chr(10).join(event_lines)}

Tasks:
1. MERGE duplicates: events about the same real-world situation with different labels.
   Especially look for 3+ events in the same region that are really the same story.

2. FIX map_labels that violate any of these rules:

{MAP_LABEL_RULES}

Return a JSON object:
{{
  "merges": [{{"keep": R_ID, "merge": R_ID, "reason": "..."}}],
  "relabels": [{{"id": R_ID, "new_map_label": "...", "reason": "..."}}]
}}

Only include entries that need changes. Return empty arrays if everything looks good.
Return ONLY valid JSON, no other text."""

    try:
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        result = parse_llm_json(text, expected_type="dict")
        if result is None:
            return {"merged": 0, "relabeled": 0}

        # Apply merges
        merged = 0
        valid_ids = {ev["id"] for ev in events}
        for m in result.get("merges", []):
            keep_id = m.get("keep")
            merge_id = m.get("merge")
            if keep_id in valid_ids and merge_id in valid_ids and keep_id != merge_id:
                merge_registry_events(conn, keep_id, merge_id)
                valid_ids.discard(merge_id)
                merged += 1
                logger.info("Registry merge: R%d <- R%d (%s)", keep_id, merge_id, m.get("reason", ""))

        # Apply relabels
        relabeled = 0
        for r in result.get("relabels", []):
            rid = r.get("id")
            new_label = r.get("new_map_label")
            if rid in valid_ids and new_label:
                update_registry_event(conn, rid, map_label=new_label)
                relabeled += 1
                logger.info("Registry relabel: R%d -> \"%s\" (%s)", rid, new_label, r.get("reason", ""))

        return {"merged": merged, "relabeled": relabeled}

    except Exception as e:
        logger.warning("Registry LLM maintenance failed: %s", e)
        return {"merged": 0, "relabeled": 0}


def maintain_registry(conn) -> dict:
    """Main entry point for registry maintenance. Run periodically.

    Returns combined stats.
    """
    retired = retire_stale_events(conn)
    capped = cap_registry_size(conn)
    llm_stats = llm_maintenance(conn)

    stats = {
        "retired": retired,
        "capped": capped,
        "merged": llm_stats["merged"],
        "relabeled": llm_stats["relabeled"],
    }
    logger.info(
        "Registry maintenance: %d retired, %d capped, %d merged, %d relabeled",
        retired, capped, llm_stats["merged"], llm_stats["relabeled"],
    )
    return stats
