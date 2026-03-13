"""Test LLM extraction to debug bright_side output."""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.llm_extractor import extract_stories_batch, SYSTEM_PROMPT
from src.llm_utils import get_anthropic_client, strip_code_fences, HAIKU_MODEL

client = get_anthropic_client()
if not client:
    print("NO API CLIENT")
    sys.exit(1)

print(f"Model: {HAIKU_MODEL}", flush=True)
print(f"System prompt length: {len(SYSTEM_PROMPT)} chars", flush=True)

# Test with extract_stories_batch
test_stories = [
    {
        "id": 999999,
        "title": "Scientists develop new vaccine that could eliminate malaria",
        "summary": "Researchers at Oxford University have developed a vaccine showing 80% efficacy against malaria in clinical trials involving 5,000 children in Africa.",
        "source": "BBC News",
        "url": "https://example.com",
        "published_at": "2026-03-09",
        "scraped_at": "2026-03-09",
        "lat": 51.75,
        "lon": -1.25,
        "location_name": "Oxford",
        "concepts": "health,science",
    }
]

results = extract_stories_batch(test_stories)
for story, extraction in results:
    print(f"\nExtraction keys: {list(extraction.keys())}", flush=True)
    print(f"Has bright_side: {'bright_side' in extraction}", flush=True)
    print(f"bright_side value: {extraction.get('bright_side')}", flush=True)
    print(f"is_opinion: {extraction.get('is_opinion')}", flush=True)
    print(f"search_keywords: {extraction.get('search_keywords')}", flush=True)
    print(f"_legacy: {extraction.get('_legacy')}", flush=True)

# Also test raw API call with max_tokens to check stop_reason
print("\n--- RAW API TEST ---", flush=True)
response = client.messages.create(
    model=HAIKU_MODEL,
    max_tokens=1500,
    system=SYSTEM_PROMPT,
    messages=[{"role": "user", "content": "Extract structured data from this 1 story:\n\n1. [BBC News] Scientists develop new vaccine that could eliminate malaria: Researchers at Oxford University have developed a vaccine showing 80% efficacy against malaria in clinical trials involving 5,000 children in Africa."}],
)
print(f"Stop reason: {response.stop_reason}", flush=True)
print(f"Usage: input={response.usage.input_tokens} output={response.usage.output_tokens}", flush=True)
text = response.content[0].text.strip()
text = strip_code_fences(text)
data = json.loads(text)
if isinstance(data, list) and len(data) > 0:
    print(f"Keys from raw API: {list(data[0].keys())}", flush=True)
    print(f"bright_side: {data[0].get('bright_side')}", flush=True)
