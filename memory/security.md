# Security Agent Memory

## Final State (after Session 3, 2026-03-15)

### Security posture: READY FOR PUBLIC LAUNCH

All application-layer security hardening is complete. 710/710 tests passing. No regressions. Three sessions of audit and hardening with no remaining critical or warning-level issues.

### What is protected

**Write abuse resistance (3 layers):**
1. Per-browser_hash rate limits (5/min) on all write endpoints
2. Per-IP rate limits (20/min) as fallback against hash rotation
3. Global write budgets: 10K feedback rows (90-day rolling window), 5K user_feeds rows

**Payload limits:**
- 64 KB request body size middleware (handles both Content-Length and chunked transfers)
- Field-level caps: browser_hash (64), target_title (500), message (1000), context JSON (4 KB), URL (2048)

**SSRF protection (feed validation):**
- DNS resolution with private IP check on ALL addresses
- IP pinning (connect to resolved IP, eliminating DNS rebinding TOCTOU)
- Redirect blocking (no 302 following)
- Streaming response with 2 MB size limit
- Connection properly closed via try/finally in all code paths

**Query protection:**
- All read endpoints have LIMIT clauses
- Expensive endpoints cached (stories 30s, events 30s, narratives 30s, concepts 30min, trending 5min, topics 30min, clouds 30min)
- json_each() SQL for concept counting (concepts, trending, topics endpoints) — avoids loading thousands of rows into Python
- Narrative detail stories query limited to 200 rows

**Response security:**
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- Referrer-Policy: strict-origin-when-cross-origin
- Permissions-Policy: camera=(), microphone=(), geolocation=()
- Error messages sanitized (no exception strings leaked to client)

**Input validation:**
- All SQL uses parameterized queries
- `_BUDGET_TABLES` whitelist prevents SQL injection via f-string table names
- feedback_type validated against allowlist
- feed_tag validated against allowlist

### Rate limit architecture
- `_check_rate_limit(store, key, max_calls, window_seconds, record=True)` — sliding window, per-key, with optional dry-run
- `_record_rate_limit(store, key)` — explicitly record a request
- `_check_write_rate(request, store, browser_hash)` — checks both tiers without recording, then records if both pass (check-then-record pattern)
- Separate stores per endpoint: `_feedback_rate`, `_user_feed_rate`, `_delete_feed_rate`, `_list_feeds_rate`
- Sweep at 500 keys prunes fully-expired entries

### Middleware execution order
1. `add_security_headers` (outer) — adds security headers to all responses
2. `limit_request_body` (inner) — rejects oversized bodies before route handlers run

### Key architecture facts
- No auth system — all identity via `browser_hash` (client fingerprint)
- SQLite WAL mode, busy_timeout=10s, connection timeout=30s
- WAL mode means reads never block writes and vice versa — budget check queries always succeed even during pipeline writes
- nginx reverse proxy (sets X-Forwarded-For)
- 3 write endpoints: POST /api/feedback, POST /api/user-feeds, DELETE /api/user-feeds/{id}
- 1 rate-limited read endpoint: GET /api/user-feeds (30/min per IP, anti-enumeration)

### What remains (ops steward scope)
- nginx rate limiting (coarse: ~10 req/s per IP globally)
- fail2ban for repeated 429 responses
- nginx client_max_body_size 64k
- X-Forwarded-For header: nginx must `proxy_set_header X-Forwarded-For $remote_addr` (not append)
- Backlog item #14: SSRF edge case tests (IPv4-mapped IPv6, hex IP notation) — defense code already handles these, just missing test coverage

### Edge case analysis (Session 3)
- **SQLite busy during budget check**: Not an issue — WAL mode allows concurrent reads during writes
- **Rate limiter memory under sustained attack**: Bounded. 500-key sweep trigger, ~80 KB per store at capacity. 4 stores = ~320 KB worst case. Botnet scale (10K+ IPs) could reach ~3 MB temporarily — acceptable for 1 GB VM. Real mitigation is nginx rate limiting.
- **Legitimate user hitting budget cap**: Gets HTTP 503. Feedback budget now uses 90-day rolling window so old rows naturally age out. User_feeds budget counts all rows (users actively manage feeds).
- **Old feedback row cleanup**: 90-day rolling window on feedback budget means the 10K cap applies to recent rows only. Old rows stay for admin review but don't block new submissions.

### Session 3 changes (2026-03-15)
- Added 90-day rolling window to feedback global budget (prevents permanent budget exhaustion)
- Fixed streaming feed fetch connection leak (resp.close() now in try/finally, not scattered across code paths)
- Aligned feedback message validator with DB truncation (both 1000 chars, user gets clear error instead of silent truncation)
- Full verification of session 2 fixes: all correct (check-then-record, chunked body handling, streaming fetch, security headers, json_each SQL)

### Test count
710 tests passing after session 3 changes.
