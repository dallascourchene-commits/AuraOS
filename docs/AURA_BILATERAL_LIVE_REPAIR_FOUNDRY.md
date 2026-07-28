# Aura Bilateral Live Repair Foundry — B11–B15

## Status

This document describes the final B11–B15 implementation over the merged B0–B10 bilateral-intent foundation. The implementation is deliberately a **thin orchestration and projection adapter**. It does not introduce another intent owner, archive, runtime harness, verifier, Crucible, current-reproof path, rollback authority, Construction truth store, or learning plane.

The implementation base is the exact merged B10 head:

```text
f1b9d786c4ff30d1ff5b984f5859db80f33446cc
```

## Canonical owners reused

| Responsibility | Canonical owner | B11–B15 use |
|---|---|---|
| Privacy-safe payload sanitization | `aura_arena_experience.sanitize_experience_payload` | Sanitizes every incident event, marker, hypothesis, counterexample, projection, and receipt payload. |
| Durable attempt evidence | `aura_arena_attempt_archive.ArenaAttemptArchive` | Retains full incident replay packets, runtime replays, failed/successful repair attempts, and preview/rollback receipts. |
| Runtime execution and proof | `scripts.aura_runtime_profile_v2_adapter.run_runtime_profile_v2` | Replays the incident against the exact confirmation, profile, source tree, allowed paths, and independent verifier. |
| P0, P1, current reproof, disposition, Relationship Experience, QDKT | `aura_unified_memory_continuity_learning` | Receives unchanged contracts through `commit_bridge_prediction`, `observe_bridge_prediction`, and `finalize_bridge_learning`. |
| Existing web application and API | `aura_showcase_server` | All existing routes and static assets are delegated unchanged. |
| Presentation | `aura_showcase_live_repair_server` | Adds one projection-only Foundry surface without creating visual truth or domain authority. |

## B11 — “Aura, watch this” bounded incident capture

`BoundedIncidentCapture` requires explicit human authorization and then records only a bounded session:

- exact bilateral identity;
- exact release and environment identity;
- bounded UI/runtime events;
- one explicit human incident marker;
- exact positive, negative, and preservation obligations;
- required assets;
- canonical privacy redactions;
- retention and dissolution receipts.

The explicit incident marker is retained separately from the rolling event window. Later events therefore cannot evict replay identity. Sets and nested mappings are normalized deterministically before hashing, so replay identities do not depend on process hash order.

Finalization:

1. rejects an absent marker;
2. rejects missing positive, negative, or preservation obligations;
3. resolves current bilateral identity through a trusted in-process owner and rejects stale identity;
4. computes one deterministic replay digest;
5. clears the active event buffer;
6. stores the complete sanitized packet in the canonical Attempt Archive.

No background or unrestricted recording is enabled.
The default Showcase server therefore fails capture finalization closed until its
embedding owner supplies `current_identity_resolver`; a request body cannot
declare its own identity current.

## B12 — persistent bounded repair Foundry

`BilateralLiveRepairService` composes the existing Runtime Profile V2 and Attempt Archive owners.

```text
archived incident replay
→ exact Runtime Profile V2 replay
→ positive + negative + preservation + fault proof
→ independent verifier identity check
→ adjacent regression result
→ persistent Attempt Archive record
→ Surgeon-local or Council-structural route
```

A candidate is never marked ready unless all of these are true:

- the Runtime V2 proof itself passed;
- every positive assertion passed;
- every negative assertion passed;
- every preservation assertion passed;
- every required fault injection passed;
- adjacent regressions passed;
- repository identity remained unchanged;
- the independent verifier ID and source digest match the confirmed contract.

Runtime proof is referenced by the digest of a Runtime Profile V2 result already retained in the canonical Attempt Archive. The public API cannot submit an arbitrary proof packet or regression boolean. Adjacent-regression status is derived from the retained base Runtime Harness receipt. Failed hypothesis digests are read back from the canonical Attempt Archive. The same failed hypothesis cannot be retried after a service restart, and the total attempt budget is eight. Local classes route to the Surgeon; interface, dependency, invariant, scope, authority, prohibition, and sequence failures route to Council V3.

## B13 — isolated preview and exact rollback

AuraOS does not currently expose a separate canonical production hot-swap owner. The approved plan refinement therefore implements an evidence-only preview adapter rather than inventing one.

The preview contract admits only:

- `LOCAL_EPHEMERAL`; or
- `CANARY_ISOLATED`.

It binds the candidate to the incident replay digest, bilateral identity digest, and last verified digest. If health degrades, a technical rollback may run only when it was pre-authorized for that isolated environment and an explicit restore adapter returns the exact last verified digest. The receipt is retained in the Attempt Archive.

The browser route cannot supply a simulated restore digest or manufacture a rollback adapter. Technical rollback is available only to a trusted in-process isolated preview owner. This does **not** authorize production mutation, deployment, or human promotion.

## B14 — canonical U7 current-reproof delegation

The Foundry does not implement its own learning decision. `run_governed_u7` delegates in order:

```text
commit_bridge_prediction
→ observe_bridge_prediction
→ finalize_bridge_learning
```

The existing owner remains responsible for:

- proposal-only Crucible storage and binding;
- immutable P0;
- independent P1;
- continuity receipt;
- current source reproof;
- human/community disposition;
- Relationship Experience;
- governed QDKT consequential observation;
- no automatic crystallization or promotion.

## B15 — Spatial Foundry presentation

`aura_showcase_live_repair_server.py` subclasses the established Showcase state, reuses the same Attempt Archive object, delegates all old API/static behavior, and injects one Foundry tab.

The projection displays:

- confirmed human intent;
- negative intent;
- preservation guardrails;
- live runtime identity and event window;
- failed attempts and counterexamples;
- P0/P1/current-reproof status;
- human/community disposition;
- exact source and receipt drill-down;
- an always-visible authority rail.

The projection is digest-bound but never authoritative. Visual state cannot mutate Construction truth, approve a patch, authorize professional or physical work, deploy, merge, or promote learning.

## API surface

```text
GET  /api/showcase/live-repair/status
POST /api/showcase/live-repair/capture/start
POST /api/showcase/live-repair/capture/{capture_id}/event/v1
POST /api/showcase/live-repair/capture/{capture_id}/mark/v1
POST /api/showcase/live-repair/capture/{capture_id}/finalize/v1
POST /api/showcase/live-repair/replay/run
POST /api/showcase/live-repair/attempt        # retained Runtime V2 proof reference only
POST /api/showcase/live-repair/preview        # browser cannot execute rollback
POST /api/showcase/live-repair/projection
```

The U7 call remains an internal Python integration because it requires the canonical in-process Bridge/session object; it is not exposed as a body-supplied authority endpoint.

## Run the composed Showcase

```bash
python aura_showcase_live_repair_server.py \
  --repo-root . \
  --host 127.0.0.1 \
  --port 8091
```

## Focused verification

```bash
python -m py_compile \
  aura_bilateral_live_repair_foundry.py \
  aura_bilateral_live_repair_foundry_contracts.py \
  aura_bilateral_live_repair_foundry_capture.py \
  aura_bilateral_live_repair_foundry_service.py \
  aura_showcase_live_repair_server.py \
  tests/test_aura_bilateral_live_repair_foundry.py \
  tests/test_aura_showcase_live_repair_server.py

pytest -q \
  tests/test_aura_bilateral_live_repair_foundry.py \
  tests/test_aura_showcase_live_repair_server.py

node --check aura_showcase/live-repair-foundry.js
```

The focused suite currently contains 19 tests and covers:

- canonical confirmation-reference identity;
- explicit capture authorization;
- marker survival after rolling-buffer eviction;
- deterministic set and mapping serialization;
- secret redaction and bounded dissolution;
- durable packet rehydration after restart;
- tamper rejection;
- exact Runtime V2 profile binding and durable proof references;
- rejection of caller-supplied proof and browser-manufactured rollback;
- negative-proof omission;
- persistent no-repeat and attempt budgets;
- Surgeon/Council routing;
- isolated rollback and exact restoration;
- canonical U7 delegation;
- stale projection rejection;
- Showcase route and static composition.

## Authority summary

Planning proposes. Runtime and independent verification prove. Human/community governance authorizes.

This implementation grants no automatic patch, commit, push, pull request, merge, deployment, production mutation, professional decision, physical-work authorization, crystallization, or learning promotion authority.
