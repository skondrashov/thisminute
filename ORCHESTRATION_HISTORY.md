# How thisminute.org Organized Its Agents

The agentic orchestration of thisminute.org went through six distinct phases over three months (March–May 2026). Each phase was a response to something breaking or outgrowing the previous model. None were planned in advance.

## Phase 0: Solo Build (early March)

No agents. One human, one Claude session at a time, four rounds of iterative development. Globe projection, keyword categorization, geocoding, trending detection.

```
542 stories · 16 RSS sources · 17 tests
```

The project worked but had outgrown what one context window could hold. The codebase had enough surface area — backend pipeline, frontend map, geocoding, LLM integration, deployment — that a single session couldn't maintain awareness of all of it simultaneously.

## Phase 1: Inherited Structure (March, week 1)

**Model: Protocol + Forum**

The agent system was bootstrapped by taking the [agi project](https://llms.thisminute.org/orchestration/evolution#evo-agi)'s post-consolidation roster and saying "model a new project after this." Five roles, directly inherited:

```
orchestrator · builder · tester · strategist · skeptic
```

The coordination infrastructure came with them:
- **PROTOCOL.md** — startup sequence: read your role file, get the timestamp, read the forum, do your work, post results, update memory, reflect on shutdown.
- **FORUM.md** — threaded discussion file. Agents post proposals, findings, and reviews. Others vote `+1`/`-1`. The forum is the shared memory between agent spawns.
- **memory/{agent}.md** — per-agent persistent learnings across sessions.
- **reports/{agent}.md** — verification logs and archived history.

The agi project had learned the hard way that starting with 10 agents (including police, coach, editor, and curator) produced noise, not output. Its forum hit 8,753 lines in a single day, mostly oversight roles talking to each other. The consolidation to 7 agents happened within hours. thisminute started with 5 because of that lesson.

LLM extraction via Claude Haiku replaced keyword categorization. Event clustering and narrative synthesis via Sonnet were added. The skeptic's value was established immediately — inherited from agi, where it had invalidated all Go evaluation results by questioning the oracle itself rather than just testing outputs.

## Phase 2: Crisis-Driven Growth (March, week 1–2)

**Model: Protocol + Forum (growing)**

GDELT was sampled at 7%. The underlying dataset grew 10x without anyone noticing, producing 45,000 stories/day instead of the expected few hundred. Events bloated to 25,000. Three new domains of work appeared overnight:

- **deployer** — getting code onto the VM reliably
- **economist** — tracking LLM spend as volume scaled
- **designer** — making the UI work for multiple data types

```
orchestrator · builder · tester · strategist · skeptic · deployer · economist · designer
```

Each role was added because the work genuinely split into a new domain — not because someone planned a roster. The GDELT sample rate was cut from 7% to 0.3%. After the fix, the orchestrator ran 20+ cycles overnight and shipped 4 versions.

```
45K→4.2K stories/day · 60%→98% extraction rate · 74 RSS feeds
```

## Phase 3: Forum Maintenance & Adversarial Dynamics (March, week 2)

**Model: Protocol + Forum (peak complexity)**

The forum hit 1,008 lines in a single session. A 9th agent was added specifically to manage it:

- **librarian** — archives resolved threads, keeps the forum around 400 lines, updates documentation.

```
orchestrator · builder · tester · strategist · skeptic
deployer · economist · designer · librarian
```

The strategist proposed 13 audience segments and 8 presets. The skeptic flagged that the numbers were inflated 10–100x, 2 of 3 "immediate" items were already built, and time estimates were 2–3x too low. Without the adversarial check, the team would have sprinted against fabricated numbers. The strategist wasn't lying — it was doing its job (proposing ambitious plans). The skeptic's job was to pressure-test them. This proposal + challenge dynamic proved more reliable than having any single agent try to be both creative and critical.

By mid-March the system hit its stride:

```
10–11 agents · 95 RSS feeds · 13 structured APIs · 710 tests
Forum: ~400 lines (librarian-maintained) · $10.92/day LLM cost
```

Two more roles were added:
- **feedback** (10th) — triage user feedback from the `user_feedback` table
- **security** (11th) — app-layer security audit (XSS, SSRF, rate limiting), distinct from ops' infra-layer security

The forum at steady state contained proposals, findings, skeptic reviews, backlog items, and session summaries. The post format was structured: `**Author:** name | **Timestamp:** YYYY-MM-DD HH:MM | **Votes:** +N/-M`. The voting system allowed agents to signal agreement or disagreement across sessions.

### What the forum looked like at its peak

A typical 400-line FORUM.md contained:
- **Skeptic backlog** — 30 items across 5 review sessions, severity-tagged (Critical/Warning/Note), with resolution tracking
- **Tester pre-deploy verification** — 18-check table with PASS/FAIL/BUG results, specific line numbers, code snippets
- **Builder session summaries** — files modified, tests added, decisions made
- **Orchestrator session summary** — which agents were spawned, in what order, what they found
- **Cross-agent references** — tester confirming skeptic findings with `+1` votes, builder referencing skeptic items by number

The forum was the evidence ledger. The protocol was the startup sequence. Together they gave each fresh agent spawn enough context to pick up where the last one left off — without requiring persistent processes.

### Field note: Stigmergy has a hard ceiling

> Forum-based coordination (agents read/write a shared file) is the most natural pattern that emerges. But it fails via unbounded growth — one project's forum went from 51 to 621 lines in a single session, another hit 904 across 7 cycles. Every shared-context pattern needs a maintenance agent. The pattern and its maintenance cost are inseparable.

## Phase 4: The Stall (late March – mid April)

**Model: Protocol + Forum (frozen)**

The VM's `ANTHROPIC_API_KEY` was set to `disabled` during a credits-exhausted period and never restored. For approximately one month:
- Every Haiku/Sonnet call returned HTTP 401
- Pipeline kept ingesting but LLM-derived fields stayed NULL
- Default preset (Bright Side, filtering on `bright_side_score >= 4`) showed nothing
- Narratives froze at their March 28 state
- No agent work happened
- The forum went stale

The site appeared blank to users. API tests would have passed — the APIs were fine, the frontend was rendering nothing because the data it depended on was all NULL.

## Phase 5: Revival (April 15)

**Model: Protocol + Forum (one last session)**

A deployer + tester diagnostic session identified the root cause (key set to "disabled"), restored the key, ran a backfill, and fixed the `uvicorn --workers 2` → `1` SQLite lock contention. This was the last session that used the forum — agents posted findings, the orchestrator posted a summary, tester posted a health check. The forum grew to ~1,000 lines with these threads, none of which would ever be read again.

```
235K stories · 739 tests · workers 2→1 · LLM extraction restored
```

## Phase 6: The Pruning (May 2026)

**Model: Direct Dispatch (current)**

The forge (from [llms.thisminute.org](https://llms.thisminute.org)) audited the project's agent system and executed a major cleanup. The result was a net deletion of 1,672 lines across 15 files:

**Deleted entirely:**
- `FORUM.md` (998 lines) — stale since April, never to be read again
- `PROTOCOL.md` (30 lines) — described forum-based coordination that nobody followed
- `CLAUDE.md` (1 line) — was just a redirect to `AGENTS.md`

**Roles eliminated (4):**
- **feedback** → merged into tester (feedback triage section)
- **security** → merged into skeptic (security audit section)
- **librarian** → eliminated (no forum to maintain)
- **strategist** → eliminated (proposals now come from the human or orchestrator)

**Roles consolidated (6 → 6, leaner):**
- builder, tester, deployer, designer, economist, skeptic — each role file rewritten to be focused and self-contained

**New coordination model:**

```bash
claude --system-prompt "$(cat agents/builder.md)" -p "fix the geocoder cache bug"
```

Spawn a fresh Claude with the role file as system prompt. Get the result. Move on. No forum read/write step. No startup protocol. No session timestamps. No mandatory voting. The orchestrator captures output directly.

```
6 agents · 0 forum lines · 0 protocol steps · memory/ files for persistence
```

### Why it changed

The Protocol + Forum model served its purpose during the intensive March development sprint. But by May, the costs outweighed the benefits:

1. **The forum was write-only.** Agents posted to it, but subsequent agents rarely read historical threads. The useful information was in the most recent post, not in the accumulated history.

2. **The librarian was treating a symptom.** Forum maintenance (archiving resolved threads, updating backlog items) was work created by the coordination model itself, not by the project.

3. **Four roles had narrow scope.** Feedback triage is a checklist the tester can follow. Security audit is a review the skeptic can do. Strategy proposals come from the human. Forum maintenance is unnecessary without a forum. Each role file was 60–130 lines of instructions for work that fits in a section of another role.

4. **The forum's value was evidence, not discussion.** In practice, agents didn't discuss or vote. They posted findings. The orchestrator read the most recent findings and made decisions. This is just "return your output" — which is what direct dispatch does without the file I/O.

5. **Startup protocol was ceremony.** "Read your role file, get the timestamp, read the forum, read memory" — by Phase 6, every agent was spawned with a specific task and the role file as system prompt. The protocol steps that mattered (understanding the project, having persistent learnings) were handled by `AGENTS.md` and `memory/` files.

## Summary: The Arc

| Phase | When | Agents | Model | Trigger |
|-------|------|--------|-------|---------|
| 0 | Early Mar | 0 | Solo | — |
| 1 | Mar wk 1 | 5 | Protocol + Forum | Inherited from agi project |
| 2 | Mar wk 1–2 | 8 | Protocol + Forum | GDELT crisis, 3 new domains |
| 3 | Mar wk 2–3 | 11 | Protocol + Forum | Forum explosion, security needs |
| 4 | Late Mar–Apr | 11 (frozen) | Protocol + Forum | API key disabled, month-long stall |
| 5 | Apr 15 | 11 | Protocol + Forum | Revival, last forum session |
| 6 | May | 6 | Direct Dispatch | Forge cleanup, role consolidation |

## Lessons Specific to thisminute.org

**Grow into complexity, don't start with it.** Starting with 5 agents and growing to 11 worked better than agi's approach of starting with 10 and consolidating. Each addition was triggered by a real domain split.

**The skeptic was the most important role.** It caught inflated numbers from the strategist, spec/code drift, false claims about data quality, and security gaps. The adversarial dynamic (proposal + challenge) was more reliable than expecting any single agent to self-critique.

**Forums are write-heavy, read-light.** Agents wrote detailed posts. Subsequent agents rarely read historical threads beyond the most recent. The forum accumulated as a record but functioned as a one-way channel.

**Maintenance roles create their own work.** The librarian existed to manage forum growth. The forum grew because agents posted to it. Removing the forum removed the need for the librarian.

**Role files are the real coordination mechanism.** The protocol and forum were overhead. The role file — which defines what an agent is, what it owns, and how it reports — is the only artifact that consistently improved agent output across all phases.

**Direct dispatch is sufficient for solo-dev projects.** With one human making all decisions, the orchestrator doesn't need a forum to coordinate with other agents. It spawns them, reads their output, and decides what to do next. The forum's value (asynchronous coordination between independently-scheduled agents) was never realized because agents were always spawned sequentially by one human.

## Context: Four Models Across the Ecosystem

thisminute's evolution is one instance of a broader pattern observed across 12 projects:

| Model | Projects | When It Fits |
|-------|----------|-------------|
| **Protocol + Forum** | thisminute, tools, rts, agi | Steady-state products with multiple domains. Needs a librarian or the forum grows without bound. |
| **Checkpoint** | balatro, sts2 | Rapid build-test-fix iteration. Agents are disposable — they spawn, read the checkpoint, work, update it, shut down. |
| **Steward** | orchestration, ops | Small scope or bootstrap. One agent owns everything, knows when to split. |
| **Forge** | thisminute-forge, singularity-forge | Scan-evaluate-act over a registry of projects. Audit quality or fill gaps. |

thisminute moved from Protocol + Forum → Direct Dispatch, which is closest to a simplified Steward model with specialist dispatch. The forum overhead was eliminated, the roles consolidated, and coordination simplified to: spawn → work → done.

The full ecosystem evolution is documented at [llms.thisminute.org/orchestration/evolution](https://llms.thisminute.org/orchestration/evolution).
