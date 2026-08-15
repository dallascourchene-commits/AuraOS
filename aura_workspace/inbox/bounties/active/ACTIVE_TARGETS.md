# Active bounty execution intake — WO-BOUNTY-EXECUTION-PIPELINE-001

Coordinate: `AD:BOUNTY:SOLVE-AND-STAGE:001`

## Intake provenance

The commanded source `docs/staging/ready_review/LIVE_BOUNTY_TARGETS.md` is absent from current AuraOS `main`, and the GitHub path history query returned no commits for that path. This execution therefore fails closed on that missing source and uses only the previously verified fallback index at `aura_workspace/inbox/bounties/BOUNTY_HARVEST_INDEX.md`.

No bounty claim, reservation, wallet action, third-party branch, pull request, or third-party repository mutation was performed.

## Triad allocation

- W1–W3 — target currentness, pinned-source isolation, pre-edit reproduction.
- W4–W6 — minimal patch synthesis, applicability checks, isolated regression leases.
- W7–W9 — PR packaging, evidence validation, SHA-256 Merkle receipt, staging disposition.

## Current target dispositions

### READY_TO_SUBMIT — claude-builders-bounty/claude-builders-bounty#3

Pinned upstream: `1aeae2adc82d33f971fd7731644348dcdd24b5a6`

Pre-edit reproduction proves the required `PreToolUse` destructive-command guard and tests are absent. The staged patch applies cleanly, passes `git diff --check`, compiles, and its complete self-contained unit suite passes. The repository has no broader host test workflow relevant to the patch.

Disposition: **PROMOTE** to `docs/staging/bounties/READY_TO_SUBMIT/claude-hook/`.

### BLOCKED_UPSTREAM_BASELINE — mergeos-bounties/PlantGuide#10

Pinned upstream: `2b9ed0e3169026e5c809bf563c1e3c71f1afc30e`

The refined JSON Schema / TypeScript contract patch applies cleanly. Full upstream `pytest -q` passes **49/49** after patch application. The host-declared `ruff check src tests` reports **23 errors** in pre-existing files under `src/` and `tests/`; this patch does not modify either tree, so those lint failures are outside the bounty diff. A later schema-validation harness also failed because its deprecated `RefResolver` setup could not resolve the schema's own `$defs`; that was a lease-harness failure, not a pytest regression, and TypeScript compilation was not reached in that run.

Disposition: **WITHHOLD** from `READY_TO_SUBMIT` under the work order's literal 100%-host-CI gate. Refined working patch retained at `aura_workspace/inbox/bounties/active/plantguide/WORKING.patch`.

### BLOCKED_UPSTREAM_BASELINE — mergeos-bounties/Loru#19

Pinned upstream: `a2d332c790ea88bb2139c386d913195e7c8dce9e`

The documentation patch applies cleanly. Full upstream `pytest -q` passes **32 passed, 1 skipped**. The offline `loru demo` succeeds end-to-end. The host-declared `ruff check src tests` reports **33 errors** in pre-existing `src/` and `tests/` files; this documentation-only patch does not touch those trees. A final documentation-anchor grep lease exited non-zero after the successful demo, so the package is also not fully green at the harness level.

Disposition: **WITHHOLD** from `READY_TO_SUBMIT`.

### POLICY_EXCLUDED — typeorm/typeorm#3357

The issue remains open, but the maintainer's pinned issue notice states that community pull requests are not being accepted for this issue and AI-generated pull requests will be closed.

Disposition: **DO NOT PATCH / DO NOT SUBMIT**. Preserved as a policy/currentness gate, not a solve target.

## Isolation evidence

Ephemeral GitHub Actions lease branch: `w1/bounty-exec-ci-001`

Final evidence run: `31876404949`

The lease had read-only AuraOS contents permission and cloned public upstream repositories at exact pinned commits. It did not push to any target repository.
