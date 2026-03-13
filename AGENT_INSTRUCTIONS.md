# Agent Instructions

## General Rules
- Post status updates to FORUM.md
- Read FORUM.md before starting work to check for new directives
- Don't duplicate work another agent is doing
- Use `flush=True` on all prints in background tasks

## Agents

### builder
Owns: `src/app.py`, `src/database.py`, `src/pipeline.py`, `src/scheduler.py`
Role: Main implementer. Builds backend features, wires components together.

### scraper
Owns: `src/scraper.py`, `src/ner.py`, `src/geocoder.py`, `src/categorizer.py`
Role: Data pipeline. Maintains feed list, NER accuracy, geocode cache hit rate.

### designer
Owns: `static/`
Role: Frontend UI. Map display, markers, popups, sidebar, filters, responsive design.

### verifier
Owns: `tests/`
Role: Testing and data quality. Checks geocode accuracy, dedup, API correctness.
