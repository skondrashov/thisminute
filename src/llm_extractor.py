"""LLM-powered story extraction using Claude Haiku.

Replaces categorizer + NER + sentiment in a single batched API call.
Extracts: topics, sentiment, severity, actors, locations, event_signature.
Falls back to legacy pipeline if no API key or on failure.
"""

import copy
import json
import logging
import os
import re
import time
from typing import Optional

from .label_rules import MAP_LABEL_RULES, REGISTRY_LABEL_RULES
from .llm_utils import get_anthropic_client, strip_code_fences, HAIKU_MODEL

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 8

SYSTEM_PROMPT = """You are the structured-data extraction engine for thisminute.org, a real-time global news map. Your extractions power search, filtering, map placement, and narrative threading. Accuracy matters — a miscategorized location_type hides a story from users; a bad event_signature breaks clustering.

Return a JSON array with one object per story, in the same order as input.

═══════════════════════════════════════════
FIELD SPECIFICATIONS
═══════════════════════════════════════════

1. "topics" (array of 1-5 strings)
   Lowercase hyphenated slugs. Be specific enough to be useful, generic enough to cluster.
   GOOD: "gaza-conflict", "us-tariffs", "ai-regulation", "climate-wildfires", "nhs-funding"
   BAD: "news", "world", "update", "breaking" (too vague)
   BAD: "trump-says-tariffs-on-canada-march-4" (too specific — won't match other stories)
   Reuse existing slugs when the topic matches. Prefer compound forms: "police-shooting", "election-fraud", "drug-trafficking".

2. "sentiment" — one of: "positive", "neutral", "negative"
   - positive: achievements, breakthroughs, rescues, peace deals, recoveries, celebrations
   - neutral: announcements, routine politics, reports without clear valence, scheduled events
   - negative: violence, disasters, corruption, failures, deaths, crises, threats

3. "severity" — integer 1-5
   1 = routine (local news, product launches, sports results, minor policy)
   2 = notable (significant policy changes, notable arrests, regional weather events)
   3 = significant (major political developments, mass protests, large accidents, significant scientific discoveries)
   4 = major (wars, terrorist attacks, natural disasters with casualties, constitutional crises, pandemics)
   5 = crisis (existential threats, massive death tolls, nuclear incidents, civilization-scale events)

4. "primary_action" — 1-3 word verb phrase describing what happened
   Examples: "airstrike", "arrested", "elected", "discovered", "collapsed", "data breach",
   "mass shooting", "signed treaty", "launched rocket", "went bankrupt", "passed legislation"

5. "actors" — array of key people/organizations/groups involved
   Each actor object:
   - "name": full name or commonly known name (not pronouns or vague references)
   - "role": MUST be one of these six values:
     * "perpetrator" — caused harm, committed a crime, launched an attack, violated rules
     * "victim" — was harmed, killed, injured, discriminated against, targeted
     * "authority" — police, government, judge, regulator, international body responding/overseeing
     * "witness" — reported, testified, observed (journalists covering the story are NOT witnesses)
     * "participant" — involved but not clearly perpetrator/victim (athletes, negotiators, researchers)
     * "target" — intended target of an action that may not have succeeded yet
   - "type": "person", "organization", "government", "group", "company", or null
   - "description": 2-8 word description for context, or null
     GOOD: "36-year-old former Marine", "Palestinian aid organization", "tech startup CEO"
     BAD: null when a description would help users understand the story
   - "demographic": demographic info ONLY when relevant to the story, or null
     Include when: the story is ABOUT race/gender/age/religion/ethnicity, or when it's central to understanding (hate crimes, discrimination, demographic patterns)
     Do NOT include: routine mentions where demographic is incidental
     Format: "Black", "Latino", "Muslim", "women", "elderly", "LGBTQ", "Indigenous", "children"

6. "affected_parties" — array of strings naming groups impacted
   Examples: "civilians", "refugees", "healthcare workers", "students", "small businesses",
   "indigenous communities", "tech workers", "consumers", "taxpayers"

7. "locations" — array of geographic locations mentioned
   Each location object:
   - "name": standard geographic name (use the most common English name)
     GOOD: "Gaza Strip", "Washington D.C.", "South China Sea"
     BAD: "the region", "overseas", "here"
   - "role": one of:
     * "event_location" — where the event primarily took place
     * "origin" — where something/someone came from
     * "destination" — where something/someone is going
     * "mentioned" — referenced but not the event location
   - "context": 3-10 word explanation, or null
   Every terrestrial story MUST have at least one location with role "event_location".
   If the location is ambiguous, use the most specific location you can confidently identify.

8. "registry_event_id" — integer or null
   If an ACTIVE EVENTS REGISTRY is provided in the prompt, match this story to the most
   appropriate registry event by its ID. Return the integer ID.
   - Only match if the story is genuinely about that event (not just tangentially related)
   - If no registry event fits, return null (and provide new_event below)
   - If the registry is empty or not provided, return null

9. "new_event" — object or null
   If registry_event_id is null (no existing event matches), propose a new event:
   - "registry_label": see LABEL RULES below
   - "map_label": see LABEL RULES below
   If registry_event_id is set, this MUST be null.

10. "event_signature" — 3-6 word CANONICAL phrase identifying the real-world event
   If a KNOWN EVENT SIGNATURES list is provided, REUSE an existing signature
   verbatim when the story matches that event. Only create a new signature if
   no existing one fits. This is critical for clustering stories about the same event.
   If you set registry_event_id, still provide event_signature for redundancy.
   NEVER use vague catch-all signatures like "Miscellaneous News", "Mixed Updates",
   "Various Regional Stories", "Data Quality Issues", or "Global News Roundup".
   Every story is about ONE specific event — name that event precisely.

   SPORTS EVENT SIGNATURES — use tournament/competition-centric signatures, NOT match results:
   - Individual match results within a tournament should use the TOURNAMENT name as signature
     BAD: "Wolves Beat Liverpool 2-1", "Liverpool Lose Wolves" (match-result-centric, fragments)
     GOOD: "2026 Premier League" (all Premier League match stories cluster together)
   - Include the year/season and competition name:
     GOOD: "2026 Indian Wells Tennis", "2026 Six Nations Rugby", "2026 F1 Australian GP"
     GOOD: "2026 IPL Cricket Season", "2026 March Madness", "2026 Champions League"
     BAD: "Medvedev Beats Sinner", "Russell Wins Australian GP" (too specific, won't cluster)
   - For transfer/trade news, use the league + window: "2026 NFL Free Agency", "2026 Premier League Transfers"
   - For standalone sporting events (boxing match, UFC fight), name the event: "UFC 315", "Tyson Fury Joshua Fight"
   - Multi-day events (Grand Prix weekends, tennis tournaments, golf majors) = ONE signature for the whole event
   - League/competition stories about standings, playoffs, relegation = use the league signature

   ENTERTAINMENT EVENT SIGNATURES — use person/production/franchise-centric signatures, NOT individual news items:
   - Movie franchise stories should cluster around the FRANCHISE or PRODUCTION name:
     BAD: "Tom Holland Spider-Man 4 Casting", "Spider-Man 4 Filming Begins" (fragments by news item)
     GOOD: "Spider-Man 4 Production" (all Spider-Man 4 stories cluster together)
     GOOD: "Marvel Phase 7 Lineup", "2026 Barbie Sequel", "Dune Part Three"
   - Music tours and albums should cluster around the TOUR or ALBUM name:
     BAD: "Taylor Swift Eras Tour Paris", "Taylor Swift Eras Tour London" (fragments by city)
     GOOD: "Taylor Swift Eras Tour" (all Eras Tour stories cluster together)
     GOOD: "Beyonce 2026 World Tour", "Kendrick Lamar New Album"
   - Awards shows and ceremonies should cluster around the AWARD EVENT:
     BAD: "Oscar Nominations Announced", "Oscar Ceremony Results" (fragments by phase)
     GOOD: "2026 Academy Awards" (all Oscars stories cluster together)
     GOOD: "2026 Grammy Awards", "2026 Emmy Awards", "2026 BAFTA Awards"
     GOOD: "2026 Golden Globe Awards", "2026 Tony Awards"
   - Film festivals should cluster around the FESTIVAL:
     GOOD: "2026 Cannes Film Festival", "2026 Sundance Festival", "2026 Venice Film Festival"
     GOOD: "2026 SXSW Festival", "2026 Toronto Film Festival", "2026 Berlin Film Festival"
   - TV show stories should cluster around the SHOW NAME:
     GOOD: "Stranger Things Season 5", "House of the Dragon Season 3", "The Bear Season 4"
     BAD: "Stranger Things Trailer Released", "Stranger Things Premiere Date" (fragments by news item)
   - Celebrity/personality stories should cluster around the PERSON + context:
     GOOD: "Taylor Swift 2026", "Drake Kendrick Feud", "BTS Military Service"
     BAD: "Taylor Swift Seen In Paris" (too specific, won't cluster)
   - K-pop, Bollywood, and international entertainment follow the same rules:
     GOOD: "BLACKPINK 2026 Comeback", "Shah Rukh Khan New Film", "2026 K-pop Awards"

11. "location_type" — MUST be exactly one of: "terrestrial", "space", "internet", "abstract"

   This determines WHERE the story appears on the map. Getting this wrong hides stories from users.

   ┌─────────────┬──────────────────────────────────────────────────────────────────────────┐
   │ terrestrial  │ DEFAULT. Any event that happens at a place on Earth.                     │
   │              │ Includes: wars, politics, weather, sports, crime, protests, economy,     │
   │              │ health, science done at a lab, court cases, elections, infrastructure     │
   │              │ Even if the story MENTIONS space or internet, it's terrestrial if the     │
   │              │ event HAPPENS on Earth.                                                   │
   │              │ "NASA announces Mars mission" = terrestrial (announcement at NASA HQ)     │
   │              │ "Company hacked" = terrestrial (company has a location)                   │
   │              │ "Parliament debates internet regulation" = terrestrial                    │
   ├─────────────┼──────────────────────────────────────────────────────────────────────────┤
   │ space        │ The event OCCURS in space or on another celestial body.                   │
   │              │ "Satellite collision in orbit" = space                                    │
   │              │ "Mars rover discovers water" = space                                     │
   │              │ "ISS crew conducts spacewalk" = space                                    │
   │              │ "Asteroid passes near Earth" = space                                     │
   │              │ "SpaceX launches rocket" = terrestrial (launch happens on Earth)          │
   │              │ "James Webb telescope images" = space (telescope is in space)             │
   │              │ "Astronaut returns to Earth" = terrestrial (the return is on Earth)       │
   ├─────────────┼──────────────────────────────────────────────────────────────────────────┤
   │ internet     │ The event exists PRIMARILY in digital/cyber space with no single          │
   │              │ physical location.                                                       │
   │              │ "Global ransomware attack" = internet (distributed, no single location)   │
   │              │ "Social media platform outage" = internet                                │
   │              │ "Viral misinformation campaign" = internet                               │
   │              │ "New AI model released" = internet (exists online, no physical event)     │
   │              │ "Cryptocurrency crash" = internet (digital-native event)                  │
   │              │ "Company hacked, data leaked" = terrestrial (company has HQ location)     │
   │              │ "TikTok banned in US" = terrestrial (US government action)                │
   ├─────────────┼──────────────────────────────────────────────────────────────────────────┤
   │ abstract     │ No meaningful physical, space, or internet location.                     │
   │              │ "Anniversary of World War I" = abstract                                  │
   │              │ "New study on human happiness" = abstract (meta-study, no lab location)   │
   │              │ "Global poverty statistics released" = abstract                          │
   │              │ "Philosophy of AI consciousness debated" = abstract                      │
   │              │ Historical retrospectives, opinion pieces about concepts,                │
   │              │ global statistical reports, theoretical discussions                      │
   │              │ NOTE: If you can identify WHERE the report was released or the study      │
   │              │ was conducted, prefer "terrestrial" with that location.                  │
   └─────────────┴──────────────────────────────────────────────────────────────────────────┘

12. "is_opinion" — boolean (true/false)
    true if the piece is an opinion column, editorial, op-ed, commentary, analysis, review, or letter.
    false if it is straight news reporting, even if it contains quotes with opinions.
    Clues: byline says "Opinion", "Editorial", "Commentary", "Analysis", "Review";
    title starts with "Opinion:", "Editorial:", or is a question/rhetorical framing;
    text uses first person ("I think", "we should"), argues a position, or makes recommendations.
    When uncertain, default to false.

13. "search_keywords" — array of 3-10 strings
    Words/short phrases a user might type to find this story. Include terms NOT already in the title.
    Think: what would someone search for if they vaguely remembered this story?
    Include: related concepts, colloquial terms, consequences, category terms.
    Example for "Israeli airstrike kills 47 in Gaza":
      ["war crimes", "civilian casualties", "bombing", "middle east", "IDF", "Palestine", "conflict"]
    Example for "New CRISPR treatment cures sickle cell":
      ["gene editing", "genetic therapy", "blood disease", "medical breakthrough", "biotech"]

14. "bright_side" — object or null
    Evaluate whether this story belongs in a "bright side" / good news feed.
    Return null if the story is not uplifting at all.
    If the story has ANY positive/hopeful/inspiring angle, return an object:
    - "score": integer 1-10 rating how uplifting/hopeful the story is:
      1-2 = mildly positive (routine sports win, minor good quarter, celebrity fluff)
      3-4 = genuinely nice (local hero, modest scientific advance, community event)
      5-6 = meaningfully uplifting (medical breakthrough, successful rescue, peace progress, environmental recovery)
      7-8 = powerfully inspiring (against-the-odds triumph, transformative discovery, major justice served, lives saved at scale)
      9-10 = extraordinarily bright (war ends, disease eradicated, historic human achievement)
    - "category": one of:
      * "breakthrough" — scientific/medical/tech discovery or advance
      * "kindness" — human compassion, volunteering, community support, generosity
      * "solution" — practical fix to a real problem, policy that works, innovation deployed
      * "recovery" — healing, rebuilding, comeback, restoration after hardship
      * "justice" — accountability, rights won, wrongs righted, fairness achieved
      * "progress" — measurable improvement in human/environmental conditions over time
      * "celebration" — cultural achievement, sporting triumph, milestone, festival
      * "nature" — wildlife success, conservation win, natural wonder, environmental good news
    - "headline": 5-15 word rewrite of the title emphasizing the bright angle
      (this is for display in the bright side feed — make it genuinely feel good to read)
      GOOD: "New gene therapy gives sight to 12 children born blind"
      GOOD: "Community raises $2M overnight to rebuild school after tornado"
      BAD: "Gene therapy advances" (too vague)
      BAD: same as original title (add the bright angle)

    IMPORTANT: Be generous but honest. A war story about civilian casualties is NOT bright side
    even if it mentions "hope for peace." But a story about refugees finding safety IS bright side.
    Sports results are bright side only if there's a compelling human story (comeback, underdog, milestone).
    Science stories are bright side when there's a real-world impact, not just "paper published."

15. "human_interest_score" — integer 1-10 or null
    How QUIRKY, SURPRISING, or DELIGHTFUL is this story? This powers a "Curious" feed of
    lighthearted, offbeat, and genuinely unusual stories. Think "you won't believe this" in
    a FUN way — not in a tragic or horrifying way.

    IMPORTANT: This is NOT "how engaging/dramatic is this story." War, violence, tragedy,
    conflict, death, disaster, and political drama should score LOW (1-3) even if they are
    gripping or emotionally intense. The Oscars, major sporting events, and mainstream
    celebrity news should also score LOW (2-4) — they are entertainment, not curiosities.

    What scores HIGH: unusual, weird, heartwarming, scientifically surprising, "wait really?",
    quirky human achievements, odd animal behavior, unexpected discoveries, wholesome surprises.

    1-2 = routine hard news, politics, conflict, tragedy, standard business/sports/entertainment
    3-4 = mildly unusual angle, but fundamentally a normal news story
    5-6 = genuinely surprising or quirky (odd science finding, unusual achievement, weird event)
    7-8 = highly unusual (bizarre event, remarkable coincidence, "wait really?", delightful oddity)
    9-10 = extraordinary (once-in-a-decade oddity, jaw-dropping wholesome discovery)

    Stories that score HIGH: "Dog elected mayor of small town" (9), "New deep-sea species discovered
    in backyard pond" (8), "Man builds working rollercoaster in garage" (8), "92-year-old graduates
    college" (7), "New island appears after underwater volcano" (8), "Twins reunited after 60 years
    via DNA test" (7), "Scientists discover New Zealand-sized continent" (9)

    Stories that score LOW: "Senate passes budget resolution" (2), "Israeli soldiers kill family" (1),
    "Oscar winners announced" (3), "Harry Styles hosts SNL" (3), "Earthquake kills dozens" (1),
    "Company reports Q3 earnings" (1), "War escalates in region" (1), "Celebrity divorce" (2)

    Return null if you cannot assess. Most news scores 1-4. Reserve 6+ for genuinely
    quirky or delightful stories that would make someone smile or say "huh, neat."

16. "translated_title" — string or null
    If the story title is NOT in English, provide a natural English translation.
    If the title IS already in English, return null.
    The translation should read like a native English headline — not a word-for-word translation.
    Examples:
      "Terremoto de magnitud 6.2 sacude el sur de México" → "Magnitude 6.2 earthquake strikes southern Mexico"
      "Macron annonce un plan de relance pour l'Afrique" → "Macron announces recovery plan for Africa"
      "President Biden signs new bill" → null (already English)

17. "wikipedia_events" — array of 0-3 strings (Wikipedia article titles)
    Map this story to Wikipedia articles about the EVENT or TOPIC it covers.
    Use the exact Wikipedia article title (as it appears in the URL/page title).
    - Prefer specific event articles: "2025-2026 Israel-Hamas war", "2025 Turkish invasion of Syria"
    - Also include broader context articles if relevant: "Russia-Ukraine war", "European migrant crisis"
    - For ongoing situations, use the article title as Wikipedia has it (check the KNOWN WIKIPEDIA EVENTS list if provided)
    - If no Wikipedia article plausibly exists for this event, return an empty array
    - Do NOT invent articles — only propose titles you believe actually exist on Wikipedia
    - Routine local news, minor stories, and opinion pieces typically have NO Wikipedia article: return []
    GOOD: ["2025-2026 Israel-Hamas war", "Gaza Strip"]
    GOOD: ["United States-China trade war", "Presidency of Donald Trump"]
    GOOD: ["2026 Iranian revolution"]
    BAD: ["News about Gaza"] (not a real article title)
    BAD: ["Trump tariffs March 2026"] (too specific, not how Wikipedia titles work)

═══════════════════════════════════════════
LABEL RULES (for new_event field)
═══════════════════════════════════════════

""" + REGISTRY_LABEL_RULES + "\n\n" + MAP_LABEL_RULES + """

═══════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════

Return ONLY a JSON array. No markdown, no explanation, no preamble. One object per story, same order as input.

If you cannot confidently extract a field, use reasonable defaults:
- topics: at least ["general"]
- sentiment: "neutral"
- severity: 2
- actors: [] (empty is OK if genuinely no named actors)
- locations: [] (only if truly no location — but try hard to find one)
- location_type: "terrestrial" (when in doubt, default to this)
- search_keywords: at least 3 keywords
- bright_side: null (when in doubt, null is safer than a low score)
- human_interest_score: null (when in doubt, null is safer than a low score)
- translated_title: null (only provide when the original title is NOT in English)"""


def _repair_json_array(text: str) -> Optional[list[dict]]:
    """Try to extract valid JSON objects from a malformed JSON array.

    When the LLM produces mostly-valid JSON with a syntax error in one object,
    this extracts the objects that are individually valid.
    """
    if not text or not text.strip().startswith("["):
        return None

    # Strategy: find top-level object boundaries and parse each individually
    results = []
    depth = 0
    obj_start = None
    in_string = False
    escape = False

    for i, ch in enumerate(text):
        if escape:
            escape = False
            continue
        if ch == '\\' and in_string:
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue

        if ch == '{':
            if depth == 0:
                obj_start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and obj_start is not None:
                obj_text = text[obj_start:i + 1]
                try:
                    obj = json.loads(obj_text)
                    if isinstance(obj, dict):
                        results.append(obj)
                except json.JSONDecodeError:
                    pass
                obj_start = None

    return results if results else None


def _build_story_text(story: dict) -> str:
    """Build compact text representation of a story for the prompt."""
    title = story.get("title", "")
    summary = (story.get("summary") or "")[:300]
    source = story.get("source", "")
    return f"[{source}] {title}: {summary}" if summary else f"[{source}] {title}"


def _build_registry_block(registry_events: list[dict]) -> str:
    """Build the registry block for the user prompt."""
    if not registry_events:
        return ""
    lines = ["ACTIVE EVENTS REGISTRY (match stories to these by ID when appropriate):"]
    for ev in registry_events:
        lines.append(f"  R{ev['id']}: {ev['registry_label']} | map: {ev['map_label']}")
    return "\n".join(lines) + "\n\n"


def _build_wiki_events_block(wiki_events: list[dict]) -> str:
    """Build the known Wikipedia events block for the user prompt."""
    if not wiki_events:
        return ""
    lines = ["KNOWN WIKIPEDIA EVENTS (reuse these exact titles when they match):"]
    for ev in wiki_events:
        lines.append(f"  - {ev['article_title']} ({ev['story_count']} stories)")
    return "\n".join(lines) + "\n\n"


def _build_signatures_block(signatures: list[dict]) -> str:
    """Build a block of known event signatures for the LLM to reuse."""
    if not signatures:
        return ""
    lines = ["KNOWN EVENT SIGNATURES (reuse these exact phrases when a story matches):"]
    for sig in signatures:
        lines.append(f"  - \"{sig['event_signature']}\" ({sig['story_count']} stories)")
    return "\n".join(lines) + "\n\n"


def _extract_batch_llm(
    client,
    stories: list[dict],
    registry_events: Optional[list[dict]] = None,
    wiki_events: Optional[list[dict]] = None,
    known_signatures: Optional[list[dict]] = None,
) -> Optional[list[dict]]:
    """Call Claude Haiku to extract structured data from a batch of stories."""
    numbered = []
    for i, story in enumerate(stories, 1):
        numbered.append(f"{i}. {_build_story_text(story)}")

    # Stories go first — they MUST NOT be truncated
    stories_block = f"Extract structured data from these {len(stories)} stories:\n\n" + "\n".join(numbered)

    # Context blocks get remaining budget (stories typically ~3-4k chars)
    context_budget = 14000 - len(stories_block) - 100  # leave margin
    registry_block = _build_registry_block(registry_events or [])
    wiki_block = _build_wiki_events_block(wiki_events or [])
    sigs_block = _build_signatures_block(known_signatures or [])

    context = ""
    if context_budget > 0 and registry_block:
        context += registry_block[:context_budget] + "\n\n"
        context_budget -= len(registry_block)
    if context_budget > 500 and wiki_block:
        context += wiki_block[:context_budget] + "\n\n"
        context_budget -= len(wiki_block)
    if context_budget > 500 and sigs_block:
        context += sigs_block[:context_budget] + "\n\n"

    user_prompt = stories_block + "\n\n" + context

    try:
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=len(stories) * 1500,
            system=[{
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": user_prompt}],
        )

        stop = response.stop_reason
        usage = response.usage

        text = response.content[0].text.strip()
        text = strip_code_fences(text)

        if stop == "max_tokens":
            logger.warning("LLM extraction hit max_tokens (%d stories, limit=%d, used=%d output tokens)",
                           len(stories), len(stories) * 1500, usage.output_tokens)

        extractions = json.loads(text)
        if not isinstance(extractions, list):
            logger.warning("LLM returned non-array: %s", type(extractions))
            return None

        return extractions

    except json.JSONDecodeError as e:
        # Try to repair: extract complete JSON objects from the response
        repaired = _repair_json_array(text)
        if repaired:
            logger.warning("LLM JSON repaired: %d objects recovered from invalid response (stop=%s, tokens=%s)",
                           len(repaired), stop, getattr(usage, 'output_tokens', '?'))
            return repaired
        logger.warning("LLM JSON parse failed (stop=%s, output_tokens=%s): %s — around error: %.200s",
                       stop, getattr(usage, 'output_tokens', '?'), e,
                       text[max(0, e.pos - 50):e.pos + 100] if text and hasattr(e, 'pos') else '')
        return None
    except Exception as e:
        logger.warning("LLM extraction API call failed: %s", e, exc_info=True)
        return None


def _generate_title_signature(title: str) -> str:
    """Generate a basic event signature from a title by extracting key content words."""
    import re as _re
    _SIG_STOPWORDS = frozenset(
        "a an the and or but in on at to for of is it its by from with as be was "
        "were are been has had have will would could should may might shall this "
        "that these those he she they his her their our your my me we us you what "
        "which who whom how when where why than not no nor so if do does did can "
        "about after all also any been before being between both each few into just "
        "more most new now only other out over own same some still such then there "
        "through too under up very says said say here get got way go going "
        "news live video watch read make made first year years old much many well "
        "back take takes set sets hit hits come comes keep keeps".split()
    )
    words = _re.findall(r"[A-Za-z]{3,}", title.lower())
    key = [w for w in words if w not in _SIG_STOPWORDS][:6]
    return " ".join(key) if len(key) >= 2 else ""


def _legacy_extract(story: dict) -> dict:
    """Fallback extraction using existing categorizer + NER + keyword sentiment."""
    from .categorizer import tag_concepts, get_primary_category
    from .ner import extract_story_location
    from .sentiment import _keyword_sentiment

    title = story.get("title", "")
    summary = story.get("summary", "")

    # Concepts
    concepts = tag_concepts(title, summary)
    topic_names = [c["name"] for c in concepts[:5]]

    # Location
    _, entities = extract_story_location(story)
    locations = []
    for e in entities:
        if isinstance(e, dict):
            locations.append({
                "name": e.get("text", ""),
                "role": e.get("role", "mentioned"),
                "context": None,
            })

    # Sentiment
    sentiment = _keyword_sentiment(title)

    return {
        "topics": topic_names,
        "sentiment": sentiment,
        "severity": 2 if sentiment == "negative" else 1,
        "primary_action": None,
        "actors": [],
        "affected_parties": [],
        "locations": locations,
        "event_signature": _generate_title_signature(title),
        "location_type": "terrestrial",
    }


# Stopwords for title dedup
_DEDUP_STOPWORDS = {"the", "a", "an", "in", "on", "at", "to", "for", "of", "is",
                    "are", "was", "were", "and", "or", "but", "with", "by", "as",
                    "from", "has", "have", "had", "be", "been", "will", "would",
                    "could", "should", "may", "might", "can", "do", "does", "did",
                    "not", "no", "its", "it", "this", "that", "their", "they",
                    "he", "she", "his", "her", "him", "we", "our", "you", "your",
                    "s", "t", "re", "ve", "ll", "d", "m"}


def _normalize_title(title: str) -> set:
    """Normalize a story title into a set of content words for comparison."""
    words = re.sub(r"[^\w\s]", " ", title.lower()).split()
    return {w for w in words if w not in _DEDUP_STOPWORDS and len(w) > 1}


def _jaccard(a: set, b: set) -> float:
    """Jaccard similarity between two word sets."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _dedup_stories_by_title(stories: list[dict], threshold: float = 0.5) -> tuple:
    """Group stories with similar titles to avoid redundant LLM extraction.

    Returns (unique_stories, duplicates_map) where duplicates_map maps
    a representative story index to list of duplicate story indices.
    """
    if len(stories) <= 1:
        return stories, {}

    title_words = [_normalize_title(s.get("title", "")) for s in stories]
    assigned = [False] * len(stories)
    groups = []  # list of (representative_idx, [duplicate_idxs])

    for i in range(len(stories)):
        if assigned[i]:
            continue
        group_dupes = []
        assigned[i] = True
        for j in range(i + 1, len(stories)):
            if assigned[j]:
                continue
            if _jaccard(title_words[i], title_words[j]) >= threshold:
                group_dupes.append(j)
                assigned[j] = True
        groups.append((i, group_dupes))

    unique = [stories[g[0]] for g in groups]
    dupe_map = {}
    for rep_idx_in_unique, (orig_idx, dupes) in enumerate(groups):
        if dupes:
            dupe_map[rep_idx_in_unique] = [(stories[d], d) for d in dupes]

    saved = sum(len(v) for v in dupe_map.values())
    if saved > 0:
        logger.info("Pre-LLM dedup: %d stories → %d unique (%d duplicates will share extraction)",
                    len(stories), len(unique), saved)

    return unique, dupe_map


def extract_stories_batch(
    stories: list[dict],
    batch_size: int = DEFAULT_BATCH_SIZE,
    registry_events: Optional[list[dict]] = None,
    wiki_events: Optional[list[dict]] = None,
    known_signatures: Optional[list[dict]] = None,
) -> list[tuple[dict, dict]]:
    """Extract structured data from stories in batches.

    Returns list of (story, extraction) tuples.
    Uses LLM if available, falls back to legacy per-story extraction.
    registry_events: active event registry for story-to-event matching.
    wiki_events: known Wikipedia event articles for consistent tagging.
    Pre-deduplicates similar titles to save LLM calls.
    """
    if not stories:
        return []

    client = get_anthropic_client()
    results = []

    if not client:
        logger.info("No API key, using legacy extraction for %d stories", len(stories))
        for story in stories:
            extraction = _legacy_extract(story)
            results.append((story, extraction))
        return results

    # Pre-LLM dedup: group stories with similar titles
    unique_stories, dupe_map = _dedup_stories_by_title(stories)

    # Process unique stories in batches with delay to avoid rate limits
    unique_results = []
    total_batches = (len(unique_stories) + batch_size - 1) // batch_size
    for batch_num, i in enumerate(range(0, len(unique_stories), batch_size), 1):
        if i > 0:
            time.sleep(0.5)  # Small delay between batches
        batch = unique_stories[i:i + batch_size]
        if batch_num % 25 == 1 or batch_num == total_batches:
            logger.info("Processing batch %d/%d (stories %d-%d)", batch_num, total_batches, i + 1, i + len(batch))
        extractions = _extract_batch_llm(client, batch, registry_events, wiki_events, known_signatures)

        if extractions and len(extractions) >= 1:
            # Use what the LLM returned; fallback remaining stories if partial
            matched = min(len(extractions), len(batch))
            if matched < len(batch):
                logger.warning("LLM returned %d/%d extractions, using partial batch", matched, len(batch))
            for story, extraction in zip(batch[:matched], extractions[:matched]):
                # Validate and fill defaults
                extraction.setdefault("topics", [])
                extraction.setdefault("sentiment", "neutral")
                extraction.setdefault("severity", 2)
                extraction.setdefault("primary_action", None)
                extraction.setdefault("actors", [])
                extraction.setdefault("affected_parties", [])
                extraction.setdefault("locations", [])
                extraction.setdefault("event_signature", "")
                extraction.setdefault("location_type", "terrestrial")
                extraction.setdefault("is_opinion", False)
                extraction.setdefault("search_keywords", [])
                extraction.setdefault("registry_event_id", None)
                extraction.setdefault("new_event", None)
                extraction.setdefault("wikipedia_events", [])
                extraction.setdefault("bright_side", None)
                extraction.setdefault("human_interest_score", None)
                extraction.setdefault("translated_title", None)
                # Normalize registry_event_id: strip "R" prefix if present
                reg_id = extraction.get("registry_event_id")
                if isinstance(reg_id, str) and reg_id.startswith("R"):
                    try:
                        extraction["registry_event_id"] = int(reg_id[1:])
                    except ValueError:
                        extraction["registry_event_id"] = None
                unique_results.append((story, extraction))
            # Fallback for unmatched remainder
            for story in batch[matched:]:
                extraction = _legacy_extract(story)
                extraction["_legacy"] = True
                unique_results.append((story, extraction))
        else:
            # Fallback for this batch — mark as legacy so they can be re-extracted later
            logger.warning("LLM batch failed, falling back to legacy for %d stories", len(batch))
            for story in batch:
                extraction = _legacy_extract(story)
                extraction["_legacy"] = True
                unique_results.append((story, extraction))

    # Expand results: add duplicate stories with shared extraction from their representative
    results = []
    for idx, (story, extraction) in enumerate(unique_results):
        results.append((story, extraction))
        if idx in dupe_map:
            for dupe_story, _ in dupe_map[idx]:
                dupe_extraction = copy.deepcopy(extraction)
                dupe_extraction["_dedup_shared"] = True
                results.append((dupe_story, dupe_extraction))

    logger.info("Extracted %d stories (%d via LLM, %d shared via dedup)", len(results),
                sum(1 for _, e in results if e.get("actors") and not e.get("_dedup_shared")),
                sum(1 for _, e in results if e.get("_dedup_shared")))
    return results


def enrich_stories(conn, story_ids: Optional[list[int]] = None) -> int:
    """Main entry point: extract and store structured data for pending stories.

    If story_ids provided, only process those. Otherwise process all pending.
    Loads the active event registry so the LLM can assign stories to known events.
    Returns number of stories enriched.
    """
    from .database import (
        get_pending_extraction_stories, store_extraction,
        get_active_registry_events, create_registry_event,
        assign_story_to_registry,
        get_active_wiki_events, get_or_create_wiki_event,
        assign_story_to_wiki_event,
        get_recent_event_signatures,
    )

    if story_ids:
        # Fetch specific stories
        placeholders = ",".join("?" * len(story_ids))
        rows = conn.execute(
            f"""SELECT id, title, summary, source, location_name, lat, lon, scraped_at
               FROM stories WHERE id IN ({placeholders})""",
            story_ids,
        ).fetchall()
        stories = [dict(r) for r in rows]
    else:
        stories = get_pending_extraction_stories(conn, limit=256)

    if not stories:
        return 0

    # Load registry, wiki events, and known signatures for LLM matching
    registry_events = get_active_registry_events(conn, limit=150)
    wiki_events = get_active_wiki_events(conn, limit=200)
    known_signatures = get_recent_event_signatures(conn, limit=200)

    results = extract_stories_batch(
        stories, registry_events=registry_events, wiki_events=wiki_events,
        known_signatures=known_signatures,
    )

    # Build a lookup of valid registry IDs for validation
    valid_reg_ids = {ev["id"] for ev in registry_events}
    # Track known wiki article titles to avoid re-querying
    known_wiki_titles = {ev["article_title"]: ev["id"] for ev in wiki_events}

    assigned_count = 0
    new_event_count = 0
    wiki_link_count = 0

    for story, extraction in results:
        try:
            store_extraction(conn, story["id"], extraction)

            # Handle registry assignment
            reg_id = extraction.get("registry_event_id")
            new_event = extraction.get("new_event")

            if reg_id and reg_id in valid_reg_ids:
                assign_story_to_registry(conn, reg_id, story["id"])
                assigned_count += 1
            elif new_event and isinstance(new_event, dict):
                reg_label = new_event.get("registry_label", "")
                map_lbl = new_event.get("map_label", "")
                if reg_label and map_lbl:
                    new_id = create_registry_event(
                        conn, reg_label, map_lbl,
                        location=story.get("location_name"),
                        lat=story.get("lat"),
                        lon=story.get("lon"),
                    )
                    assign_story_to_registry(conn, new_id, story["id"])
                    # Add to valid set so subsequent stories can match
                    valid_reg_ids.add(new_id)
                    registry_events.append({
                        "id": new_id,
                        "registry_label": reg_label,
                        "map_label": map_lbl,
                    })
                    new_event_count += 1

            # Handle Wikipedia event links
            wiki_articles = extraction.get("wikipedia_events", [])
            if isinstance(wiki_articles, list):
                for title in wiki_articles[:3]:
                    if not isinstance(title, str) or not title.strip():
                        continue
                    title = title.strip()
                    # Get or create, using cache to avoid repeated DB lookups
                    if title in known_wiki_titles:
                        wiki_id = known_wiki_titles[title]
                    else:
                        wiki_id = get_or_create_wiki_event(conn, title)
                        known_wiki_titles[title] = wiki_id
                    assign_story_to_wiki_event(conn, story["id"], wiki_id)
                    wiki_link_count += 1

        except Exception as e:
            logger.error("Failed to store extraction for story %d: %s", story["id"], e)

    logger.info(
        "Registry: %d assigned to existing, %d new events created, %d wiki links",
        assigned_count, new_event_count, wiki_link_count,
    )
    return len(results)
