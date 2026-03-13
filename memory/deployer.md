# Deployer Memory

## Deploy procedure

- `scripts/deploy.py` is the standard deploy script. It now conditionally skips `npm run build` when `src/js/` is absent (fixed 2026-03-13).
- For backend-only deploys: the script handles everything automatically -- tarball, upload, CRLF fix, restart, health check.
- Pre-built `static/js/app.js` is in the repo and gets deployed as-is when `src/js/` is missing.

## Key deploy facts

- Tarball excludes: `node_modules`, `test-results`, `__pycache__`, `.git`, `data`, `e2e`, `src/js`, `*.db*`
- CRLF fix is mandatory -- Windows creates CRLF, VM needs LF
- WAL/SHM ownership fix runs twice: before restart and after (sleep 2)
- gcloud path has spaces -- must use Python subprocess with list args, not shell strings
- Health check via `https://thisminute.org/api/health` -- expects `{"status":"ok","stories":N}`

## Last deploy

- **Date**: 2026-03-13 05:53
- **What**: Backend-only deploy of skeptic warning fixes (tightened entertainment regex patterns, domain-gated fuzzy match boosts)
- **Result**: Success. Health: 120,960 stories. Service running, feeds scraping normally.
- **Tests**: 91/91 passed (47 entertainment + 20 sports + 7 domain + 17 core)
