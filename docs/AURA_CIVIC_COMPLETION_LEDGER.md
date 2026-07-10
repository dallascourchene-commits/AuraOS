# Aura Civic Commons Arena — Completion Ledger

## Base
- **Base SHA:** `298c3737ebfeb9f272b813e78effe063f6c4a6ea`
- **Branch:** `feature/aura-civic-commons-completion`
- **Merged PR #63:** Civic Commons Arena scaffolding

## Status Summary
| Status | Count |
|--------|-------|
| PASS | 29 |
| PARTIAL | 10 |
| MISSING | 5 |
| BLOCKED_EXTERNAL | 0 |

## Key Integration Gaps (from audit)
1. **Civic organs don't use real ephemeral runtime** — they call dispatcher directly, no manifests/leases/lifecycle/dissolution
2. **Civic sessions are in-memory** — `_sessions` dict, no SQLite persistence
3. **No Human Agent Arena UI** — CLI-only, no civic endpoints in server
4. **No functioning map** — GeoJSON validation exists but no MapLibre rendering
5. **No official snapshots** — source definitions only, no curated records
6. **No real provider broker** — fixture mode only, no schema validation/redaction/budgeting
7. **No Cost Observatory connection** — civic stages not recorded
8. **No persistent Community Memory** — in-memory archive only
9. **Story dataflow not story-specific** — organs hardcode hairstylist fixtures internally
10. **Named organs aliased** — SystemicContextOrgan aliases ConsentArc, LegalBylaw aliases Evidence

## Milestone Plan
1. Integrate persistent lifecycle + manifest hardening into real ephemeral runtime
2. Add persistent Civic session store + atomic state projection
3. Make Civic organs story-aware + ephemeral-runtime governed
4. Integrate CivicArenaAdapter + Arena contracts + WorldStateDelta
5. Implement real deliberation, systemic context, What-If, pilot, decision packet assembly
6. Add official snapshots + source-backed legal/Council evidence
7. Add Human Agent Arena Civic API + frontend
8. Add MapLibre map + accessible table/list parity
9. Connect AMD/Fireworks broker + Cost Observatory
10. Complete tests, docs, manifests, CODEMAP, completion ledger
