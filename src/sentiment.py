"""Batch sentiment classification for news stories using Claude Haiku."""

import json
import logging
import re

from .llm_utils import get_anthropic_client, strip_code_fences, HAIKU_MODEL

logger = logging.getLogger(__name__)

# Keyword fallback for when no API key is available
_POSITIVE_SIGNALS = {
    "breakthrough", "celebrates", "record-breaking", "wins", "award",
    "rescued", "saved", "recovered", "reunited", "cured", "milestone",
    "volunteers", "charity", "donation", "success", "triumph", "hero",
    "historic", "groundbreaking", "pioneering", "achievement", "peace",
    "freed", "exonerated", "survives", "comeback", "conservation",
    "renewable", "clean energy", "restored", "rebuild", "miracle",
    "discovery", "innovation", "launches", "partnership", "agreement",
    "medal", "championship", "festival", "concert", "celebrates",
}

_NEGATIVE_SIGNALS = {
    "killed", "dead", "death", "dies", "fatal", "murder", "shooting",
    "bomb", "attack", "war", "massacre", "crash", "disaster", "explosion",
    "suicide", "torture", "rape", "abuse", "famine", "crisis", "collapse",
    "terror", "hostage", "kidnap", "genocide", "execution", "stabbing",
    "drowning", "epidemic", "pandemic", "casualties", "victims", "threat",
    "fears", "warns", "alarming", "devastating", "catastroph", "brutal",
    "violent", "flee", "displaced", "destroyed", "toxic",
}


def _keyword_sentiment(title: str) -> str:
    """Fast keyword-based sentiment fallback."""
    words = set(re.findall(r"[a-z]+", title.lower()))
    pos = len(words & _POSITIVE_SIGNALS)
    neg = len(words & _NEGATIVE_SIGNALS)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


def classify_batch(stories: list[dict]) -> dict[int, str]:
    """Classify sentiment for a batch of stories.

    Returns {story_id: "positive"|"neutral"|"negative"}.
    Uses Claude Haiku for batch classification, falls back to keywords.
    """
    if not stories:
        return {}

    client = get_anthropic_client()
    if not client:
        return {s["id"]: _keyword_sentiment(s.get("title", "")) for s in stories}

    # Build numbered list of headlines for batch classification
    lines = []
    id_map = {}  # line_number -> story_id
    for i, story in enumerate(stories, 1):
        title = story.get("title", "")[:120]
        lines.append(f"{i}. {title}")
        id_map[i] = story["id"]

    headlines = "\n".join(lines)

    prompt = f"""Classify each news headline's emotional tone as positive, neutral, or negative.

positive = good news, achievements, progress, joy, hope, breakthroughs, recovery, celebration
neutral = factual reporting, policy changes, business updates, neither uplifting nor distressing
negative = death, violence, disaster, suffering, crisis, threat, loss, conflict, fear

Headlines:
{headlines}

Reply with ONLY a JSON array of strings, one per headline in order. Example: ["negative","positive","neutral"]"""

    try:
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=len(stories) * 15,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        text = strip_code_fences(text)
        sentiments = json.loads(text)

        result = {}
        for i, sent in enumerate(sentiments, 1):
            if i in id_map:
                s = sent.strip().lower()
                if s not in ("positive", "neutral", "negative"):
                    s = "neutral"
                result[id_map[i]] = s

        # Fill any missing with keyword fallback
        for story in stories:
            if story["id"] not in result:
                result[story["id"]] = _keyword_sentiment(story.get("title", ""))

        logger.info("LLM sentiment: %d classified (%d positive, %d neutral, %d negative)",
                     len(result),
                     sum(1 for v in result.values() if v == "positive"),
                     sum(1 for v in result.values() if v == "neutral"),
                     sum(1 for v in result.values() if v == "negative"))
        return result

    except Exception as e:
        logger.warning("LLM sentiment classification failed: %s", e)
        return {s["id"]: _keyword_sentiment(s.get("title", "")) for s in stories}
