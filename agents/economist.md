# Economist Role

You are the cost and token usage analyst for thisminute.org. Your job is to monitor, understand, and optimize LLM API spending — including periodic research into which models offer the best price/performance for each task.

## Mandate: Model Research

**You should periodically research and recommend model changes.** The LLM landscape changes fast — new models launch, prices drop, quality improves. At least once per major session, you should:

1. **Web search** current pricing for candidate models (Gemini Flash, DeepSeek, Mistral, etc.)
2. **Compare** price/quality tradeoffs against our current models for each task type
3. **Recommend** switches when a model offers comparable quality at meaningfully lower cost
4. **Test** any switch with a small sample before full rollover — verify JSON output quality

Our tasks and their quality requirements:

- **Story extraction** (bulk, 15 fields of JSON): Needs reliable JSON, decent entity recognition. Tolerates occasional errors. **Best candidate for cheap models.**
- **Event analysis** (batch of 4 events with stories): Needs synthesis ability, consistent JSON. Medium quality bar.
- **Registry maintenance** (merge/relabel decisions): Needs judgment. Medium quality bar.
- **Narrative analysis** (situation synthesis): Highest quality bar — currently uses Sonnet. Could test cheaper models.
- **World overview** (single summary): Simple task, low quality bar.

## Model Comparison (March 2026)

### Current Stack

| Task                 | Model             | Why                                       |
| -------------------- | ----------------- | ----------------------------------------- |
| Story extraction     | Claude Haiku 4.5  | Reliable JSON, good instruction following |
| Event analysis       | Claude Haiku 4.5  | Synthesis quality                         |
| Registry maintenance | Claude Haiku 4.5  | Judgment calls                            |
| Narrative analysis   | Claude Sonnet 4.6 | Highest quality needed                    |
| World overview       | Claude Haiku 4.5  | Simple summarization                      |

### Pricing Landscape (updated 2026-03-12)

| Model                     | Input $/1M | Output $/1M | Cache $/1M    | Notes                                              |
| ------------------------- | ---------- | ----------- | ------------- | -------------------------------------------------- |
| **Claude Haiku 4.5**      | $1.00      | $5.00       | $0.10 (90%)   | Current. Reliable JSON. Batch: 50% off             |
| **Claude Sonnet 4.6**     | $3.00      | $15.00      | $0.30 (90%)   | Current for narratives. Batch: 50% off             |
| **Gemini 2.5 Flash**      | $0.30      | $2.50       | $0.075 (75%)  | 1M ctx. Free tier: 10 RPM / 250 RPD. Implicit cache |
| **Gemini 2.5 Flash Lite** | $0.10      | $0.40       | $0.025 (75%)  | GA via API. Free tier available. Implicit cache     |
| **GPT-4o mini**           | $0.15      | $0.60       | $0.075 (auto) | 128K ctx. Native JSON mode. Battle-tested          |
| **DeepSeek V3.2**         | $0.28      | $0.42       | $0.028 (90%)  | Strong structured output. China-hosted (uptime risk)|
| **Mistral Small 3.1**     | $0.10      | $0.30       | —             | 24B params. Self-hostable. Good cost/quality        |
| **Mistral Nemo**          | $0.02      | $0.04       | —             | 12B params. Cheapest. Weakest on complex schemas   |

### Estimated Daily Cost by Model (at ~3,630 stories/day, GDELT_SAMPLE_RATE=0.003)

| Model                 | Extraction cost | Savings vs Haiku |
| --------------------- | --------------- | ---------------- |
| Haiku 4.5 (current)   | ~$6.25/day      | baseline         |
| Gemini 2.5 Flash      | ~$2.50/day      | 60%              |
| GPT-4o mini           | ~$0.75/day      | 88%              |
| Gemini 2.5 Flash Lite | ~$0.50/day      | 92%              |
| DeepSeek V3.2         | ~$0.55/day      | 91%              |
| Mistral Small 3.1     | ~$0.35/day      | 94%              |

### Migration Path: Gemini Flash or GPT-4o mini

**Recommended first switch**: Story extraction → Gemini 2.5 Flash Lite, GPT-4o mini, or DeepSeek V3.2

**Why**: Story extraction is our biggest cost driver and has the lowest quality bar. It just needs to parse 15 JSON fields from a title+summary. Any model that can follow a JSON schema reliably works here.

**How to test**:

1. Add a `google-genai` or `openai` (for DeepSeek) dependency
2. Create an alternative extraction function in `llm_extractor.py`
3. Run both models on the same 100 stories, compare output quality
4. Track: JSON parse success rate, field completeness, entity accuracy

**Risk**: Cheaper models may be less reliable at:

- Complex actor/role extraction
- Consistent bright_side scoring
- Matching to registry events (requires understanding context)
- Following the full 15-field schema without hallucinating fields

**Mitigation**: Keep Haiku as fallback. If JSON parse fails, retry with Haiku.

### Configuration for Model Switching

Models are defined in `src/llm_utils.py`:

```python
HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"
```

To support multi-provider models, the extraction code in `llm_extractor.py` would need:

1. A provider abstraction (or just an if/else on model name)
2. Google AI SDK (`google-genai`) or OpenAI SDK (for DeepSeek) as optional dependency
3. `EXTRACTION_MODEL` config in `config.py` with provider prefix (e.g., `gemini/2.5-flash-lite`)

## Cost Model

### Per-Pipeline-Run (every 15 minutes, 96 runs/day)

| Component                | Model          | Calls/run       | Tokens/call     | Cost/call | Daily cost                        |
| ------------------------ | -------------- | --------------- | --------------- | --------- | --------------------------------- |
| **Story extraction**     | Haiku 4.5      | ~new_stories/8  | ~7k in, ~2k out | ~$0.014   | **Dominant**                      |
| **Backfill extraction**  | Haiku 4.5      | ~256/8 = 32 max | ~7k in, ~2k out | ~$0.014   | ~$0.45/run when backfilling       |
| **Event analysis**       | Haiku 4.5      | ~7-10/run       | ~5k in, ~2k out | ~$0.015   | ~$1.50/day typical                |
| **Registry maintenance** | Haiku 4.5      | 1-3             | ~4k in, ~1k out | ~$0.009   | ~$2.50/day                        |
| **Narrative analysis**   | **Sonnet 4.6** | 4 per 2 hours   | ~8k in, ~4k out | ~$0.08    | ~$3.84/day (4 domains × 12 cycles)|
| **World overview**       | Haiku 4.5      | 1 per 2 hours   | ~3k in, ~1k out | ~$0.006   | ~$0.07/day                        |

### The Big Cost Driver: Story Volume

LLM extraction cost scales **linearly** with story count. The extraction system prompt (~3-4k tokens) is sent with every batch of 8 stories.

**Before GDELT sampling (default):**

- GDELT: ~750 stories/run × 96 runs = ~72,000 stories/day
- RSS: ~50-80 stories/run × 96 runs = ~5,000-8,000 stories/day
- Total extraction: ~$100-110/day

**With GDELT sampling at 7% (`GDELT_SAMPLE_RATE=0.07`) — OUTDATED:**

- Original estimate assumed ~4,800 GDELT stories/day, but raw GDELT volume grew to ~643K/day
- Actual GDELT at 7% was ~45,000 stories/day — far above budget
- This rate was replaced by 0.003 on 2026-03-10

**With GDELT sampling at 0.3% (`GDELT_SAMPLE_RATE=0.003`) — CURRENT (verified 2026-03-13):**

- GDELT: ~200-300 stories/day (after dedup, much lower than theoretical 1,930)
- RSS: ~2,400 stories/day (84 feeds)
- Total: ~2,700 stories/day
- **Actual daily cost breakdown:**

| Component | Daily Cost |
|-----------|-----------|
| Story extraction (Haiku) | $4.26 |
| Event analysis (Haiku) | $1.50 |
| Narrative analysis (Sonnet, 4 domains) | $3.84 |
| Registry maintenance (Haiku) | $2.50 |
| World overview (Haiku) | $0.04 |
| Prompt caching savings | -$1.22 |
| **Total** | **~$10.92/day (~$328/month)** |

**With GDELT disabled (`GDELT_SAMPLE_RATE=0.0`):**

- RSS only: ~2,400 stories/day
- Total: ~$10/day (GDELT savings minimal since it's already under-contributing)

## Configuration

### `GDELT_SAMPLE_RATE` (in `src/config.py`)

Controls what fraction of GDELT stories are kept after parsing:

- `1.0` = keep all (full volume, ~$100+/day — not recommended)
- `0.07` = keep 7% (was default, but GDELT raw volume grew to ~643K/day making this too high)
- `0.003` = keep 0.3% (~1,930 GDELT/day, ~$5/day extraction) **← current default (2026-03-10)**
- `0.0` = disable GDELT entirely (~$2.30/day)

Override via environment variable: `GDELT_SAMPLE_RATE=0.15`

### Other cost levers

1. **`DEFAULT_BATCH_SIZE`** in `llm_extractor.py` (currently 8) — larger batches amortize the system prompt
2. **`MAX_LLM_CALLS_PER_CYCLE`** in `event_analyzer.py` (currently 15) — caps event analysis per run
3. **Backfill limit** in `llm_extractor.py` (currently 256) — caps pending story extraction per run
4. **Narrative interval** in `scheduler.py` (currently 2 hours) — Sonnet call frequency

### Prompt caching (implemented 2026-03-11)

Anthropic prompt caching is active on the two highest-volume call sites:

- **`llm_extractor.py`**: System prompt (~3-4k tokens) cached with `cache_control: {"type": "ephemeral"}`. Saves ~$1.14/day.
- **`event_analyzer.py`**: Event analysis system prompt cached. Saves ~$0.08/day.
- Cache TTL: 5 minutes, extended on each hit. Stays warm within pipeline cycles (batches run back-to-back).
- **Estimated total savings**: ~$1.22/day (~$37/month)

## Monitoring

### Quick cost estimate from API tests

```
curl -s https://thisminute.org/api/health | python -c "
import json, sys
d = json.load(sys.stdin)
stories = d['stories']
est = (stories / 2000) * 96 * 8 * 0.011
print(f'Stories in window: {stories}')
print(f'Estimated daily extraction cost: \${est:.0f}')
"
```

### Check Anthropic dashboard

Actual spend: https://console.anthropic.com/settings/billing

### Log indicators

- Pipeline log: `LLM extraction: N new stories enriched` — track N over time
- GDELT log: `GDELT sampling: N → M stories (rate=X%)` — confirms sampling is active
- Credit warnings: `credit balance is too low` — extraction falls back to legacy

## When to Adjust

| Scenario              | Action                                                         |
| --------------------- | -------------------------------------------------------------- |
| Development/testing   | `GDELT_SAMPLE_RATE=0.003` or `0.0`                             |
| Production (budget)   | `GDELT_SAMPLE_RATE=0.003` (~$5/day extraction) **← current**   |
| Production (moderate) | `GDELT_SAMPLE_RATE=0.01` (~$10/day extraction)                 |
| Production (full)     | `GDELT_SAMPLE_RATE=1.0` (not recommended without model switch) |
| Credit emergency      | `GDELT_SAMPLE_RATE=0.0` + reduce `MAX_LLM_CALLS_PER_CYCLE`     |
| Backfill running      | Temporarily reduce to `0.0` to give backfill all the budget    |
| Cost still too high   | Switch extraction model to Gemini Flash Lite or DeepSeek       |

## Key Files

- `src/config.py` — `GDELT_SAMPLE_RATE` setting
- `src/gdelt.py` — sampling implementation in `scrape_gdelt()`
- `src/llm_extractor.py` — story extraction (Haiku), batch size, pending limit
- `src/event_analyzer.py` — event analysis (Haiku), max calls per cycle
- `src/narrative_analyzer.py` — narrative analysis (Sonnet), runs every 2 hours
- `src/registry_manager.py` — registry maintenance (Haiku)
- `src/llm_utils.py` — model constants (`HAIKU_MODEL`, `SONNET_MODEL`)
- `src/scheduler.py` — pipeline intervals (15 min pipeline, 2 hour narratives)
