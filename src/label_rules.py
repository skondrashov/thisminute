"""Shared label generation rules for map_label and registry_label.

Single source of truth — imported by llm_extractor, registry_manager, and seed_registry.
Edit these strings to change how all LLM prompts generate labels.
"""

MAP_LABEL_RULES = """MANDATORY RULES for map_label (violating any is an error):
- MUST contain a verb in present tense: "Tariffs escalate", "Dam collapses", "Nurses strike"
- NEVER include country/city/region names (the map already shows location)
- NEVER include proper nouns (no person/company/org names — those go in registry_label)
- NEVER use filler: crisis, situation, issues, developments, concerns, tensions, problems
- NEVER use passive/observational: "receives", "faces", "amid", "draws attention", "raises questions"
- MUST be specific: "Cholera outbreak" not "Health emergency", "Airstrikes intensify" not "Military operations"
- 2-4 words max. If you need 5+, you're saying too much.
- Each label must be distinct — avoid generic duplicates like 5 events all saying "Conflict escalates"
GOOD: "Tariffs escalate", "Ceasefire talks resume", "Nurses strike", "Earthquake rescue", "Factory fire kills 12"
BAD: "US China trade" (place names, no verb), "Political developments" (filler), "NHS crisis" (proper noun + filler), "Innovation advances amid debate" (observational), "Infrastructure and economic developments" (filler, too long)"""

REGISTRY_LABEL_RULES = """Rules for registry_label:
- 3-6 word canonical identifier with proper nouns + event type
- Format: "[Entity1] [Entity2] [event-type]"
- Must distinguish from similar events in the same region
- Stable over time — don't rename as story evolves
GOOD: "Trump China tariffs", "NHS nurses strike", "Boeing 737 MAX grounding"
BAD: "US politics" (too vague), "Trump announces 25% tariffs March 4" (too specific)"""
