"""Seed the event registry from existing analyzed events.

One-time migration: converts existing events (with LLM titles) into registry
events with proper map_labels. Run on production after deploying the registry.

Usage: python -m scripts.seed_registry [--dry-run]
"""

import json
import logging
import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import (
    get_connection, init_db, get_active_events,
    create_registry_event, assign_story_to_registry,
    get_active_registry_events,
)
from src.label_rules import MAP_LABEL_RULES, REGISTRY_LABEL_RULES
from src.llm_utils import get_anthropic_client, strip_code_fences, HAIKU_MODEL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
)
logger = logging.getLogger(__name__)

# Batch size for LLM label generation
LABEL_BATCH_SIZE = 20


def _get_client():
    return get_anthropic_client()


def _generate_map_labels(client, events: list[dict]) -> dict:
    """Ask LLM to generate map_labels for a batch of events.

    Returns {event_id: {"registry_label": ..., "map_label": ...}}
    """
    lines = []
    for ev in events:
        loc = ev.get("primary_location") or ""
        lines.append(f"E{ev['id']}: \"{ev['title']}\" (location: {loc}, {ev.get('story_count', 0)} stories)")

    prompt = f"""Convert these news event titles into two labels each:

{chr(10).join(lines)}

For each event, return:
- "registry_label":
{REGISTRY_LABEL_RULES}

- "map_label":
{MAP_LABEL_RULES}

Return a JSON object mapping event ID to labels:
{{"E1": {{"registry_label": "...", "map_label": "..."}}, ...}}

Return ONLY valid JSON."""

    try:
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=200 * len(events),
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        text = strip_code_fences(text)
        result = json.loads(text)
        # Normalize keys: "E123" -> 123
        normalized = {}
        for k, v in result.items():
            eid = int(k.replace("E", ""))
            normalized[eid] = v
        return normalized
    except Exception as e:
        logger.error("LLM label generation failed: %s", e)
        return {}


def _fallback_labels(event: dict) -> dict:
    """Generate labels without LLM — use event title as registry_label,
    derive a rough map_label by stripping common location words."""
    title = event.get("title", "Unknown")
    # Use title as registry label (already decent from event_analyzer)
    registry_label = title[:60]

    # Crude map_label: take first few words, skip location-ish ones
    # This will be refined by registry maintenance later
    map_label = title[:40]

    return {"registry_label": registry_label, "map_label": map_label}


def seed_registry(dry_run=False):
    init_db()
    conn = get_connection()

    # Check if registry already has many events (skip if already seeded)
    existing = get_active_registry_events(conn, limit=200)
    if len(existing) >= 50:
        logger.info("Registry already has %d events. Skipping seed.", len(existing))
        conn.close()
        return
    # Track existing registry labels to avoid duplicates
    existing_labels = {e["registry_label"].lower() for e in existing}

    # Get analyzed events with 2+ stories
    events = conn.execute(
        """SELECT * FROM events
           WHERE merged_into IS NULL
           AND story_count >= 2
           AND last_analyzed IS NOT NULL
           ORDER BY story_count DESC
           LIMIT 200""",
    ).fetchall()
    events = [dict(e) for e in events]
    logger.info("Found %d analyzed events to seed registry from", len(events))

    if not events:
        conn.close()
        return

    client = _get_client()
    all_labels = {}

    if client:
        # Generate labels in batches
        for i in range(0, len(events), LABEL_BATCH_SIZE):
            batch = events[i:i + LABEL_BATCH_SIZE]
            logger.info("Generating labels for batch %d-%d...", i, i + len(batch))
            labels = _generate_map_labels(client, batch)
            all_labels.update(labels)
            if i + LABEL_BATCH_SIZE < len(events):
                time.sleep(0.5)
        logger.info("LLM generated labels for %d/%d events", len(all_labels), len(events))
    else:
        logger.warning("No API key — using fallback labels (will need refinement)")

    # Create registry events and link stories
    created = 0
    linked = 0

    for event in events:
        labels = all_labels.get(event["id"]) or _fallback_labels(event)
        reg_label = labels.get("registry_label", event["title"][:60])
        map_label = labels.get("map_label", event["title"][:40])

        # Skip if we already have a registry event with this label
        if reg_label.lower() in existing_labels:
            continue

        if dry_run:
            logger.info(
                "  [DRY RUN] E%d (%d stories): registry=\"%s\" map=\"%s\"",
                event["id"], event["story_count"], reg_label, map_label,
            )
            continue

        existing_labels.add(reg_label.lower())
        reg_id = create_registry_event(
            conn, reg_label, map_label,
            location=event.get("primary_location"),
            lat=event.get("primary_lat"),
            lon=event.get("primary_lon"),
        )
        created += 1

        # Link existing stories from this event
        story_rows = conn.execute(
            "SELECT story_id FROM event_stories WHERE event_id = ?",
            (event["id"],),
        ).fetchall()
        for row in story_rows:
            assign_story_to_registry(conn, reg_id, row["story_id"])
            linked += 1

    conn.close()

    if dry_run:
        logger.info("Dry run complete. Would create %d registry events.", len(events))
    else:
        logger.info("Seeded registry: %d events created, %d stories linked", created, linked)


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    seed_registry(dry_run=dry_run)
