---
name: statistical inference feeds
description: User wants to show real-world events inferred from statistics (deaths, births, outbreaks), not just news stories — making the map show reality, not just media coverage
type: user
---

The user has a long-standing desire to show events on the map that don't have news articles — things inferred from statistical data sources like Worldometer. Example: "5 people died here in the last hour" based on mortality statistics, even when no news story covers it.

This is a natural extension of the anti-curation philosophy: the gap between "what's happening" and "what's being reported" is the biggest blind spot. Statistical feeds would fill that gap.

The user described this as "captivating" — it's clearly a passion feature, not a backlog item.

**Settings philosophy**: Visual distinction options and theming choices that affect the "feel" of the app should be exposed as user settings, at least short-term, so the user can try all combinations and converge on what works. Don't hardcode aesthetic decisions — make them toggleable. This applies broadly, not just to statistical feeds.

**Unbiased ingestion principle**: You cannot present the world in an unbiased way if you only ingest biased data. Ingestion must be maximally broad and balanced across ALL domains — disasters AND good news, conflicts AND academic breakthroughs, crises AND celebrity/entertainment, health scares AND scientific discoveries. Every bit of real-time data we can squeeze from the internet. The toggles let users filter; the ingestion must be comprehensive. If the data sources skew toward doom (disaster APIs are easy to find), that itself is a bias that must be actively counterbalanced with equal emphasis on positive, cultural, academic, and entertainment sources.
