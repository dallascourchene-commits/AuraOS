# CS-HARNESS-001 Different-J Integration Repairs

Status: sibling repair support; non-merging; no authority widening.

Base reviewed: PR #312 head `c03bd4b2b673aa5956b081493388600e87beca77`.

H-A reference: branch `cs-harness-h-a-arena-admission`, module commit `10d10e006c7f5c6469cd49b06e52aaf13b7cca40`, tests commit `81c4f332297b94cc2114c7faef41771044279a27` (14/14 local PASS).

## Blocking/important repairs before H-F

1. **Mission return must be one-shot.** In `claim_best_available`, restore the canonical mission only when `gate >= 10 and temporary_mission is True`. Once restored, a later scheduler pass must be able to claim canonical Creator Studio/PUBG work instead of returning `MISSION_RETURN` forever.

2. **One ordinary worker = one active claim.** Add a `worker_active_claims(state, worker_id)` check. A worker with exactly one claim should continue that claim rather than receive another. More than one active claim is a typed fail-closed corruption state. Explicit reducer/coordinator/verifier exceptions belong to the H-A/live admission layer.

3. **Finish/residual compilation must be atomic at the semantic boundary.** Validate the entire material residual batch before marking the parent COMPLETE or releasing its claim. A malformed later residual must not leave a completed parent plus partially-created successor work.

4. **Wake scans must not over-assign workers.** Exclude workers that already own an active claim and reserve a worker after targeting one work item in a scan.

5. **Do not durably retarget the same work/version to multiple workers.** Before emitting, check the wake ledger for an existing `(mission,event_type,work_id,work_version)` eligibility event. Actual execution must still acquire the authoritative WorkGraph lease; wake intent is not execution authority.

6. **Replace permissive literal `v1` work versions.** Live integration should supply the authoritative WorkGraph/source/currentness digest. A deterministic WorkItem-content digest is a safer reference fallback so changed work semantics naturally produce a new wake version.

7. **H-A admission precedes substantive ACT.** ORIENT/REPAIR_ADMISSION may run while incomplete; substantive work requires the ArenaAdmissionV1 contract. Caller-supplied booleans/strings are not currentness or authority proof.

8. **Gate8/Gate10 evidence must be semantic, not merely nonempty strings.** Resolve evidence refs to typed durable receipts/currentness and bind allowed terminal reasons to actual predicates before live Gate-10 credit.

## Regression battery

`test_creator_studio_differentj_integration.py` encodes the cross-lane failures above. On the unmodified reviewed PR head these tests are expected to expose the missing invariants. A local repair candidate implementing items 1–6 passed `9/9` focused regressions in 0.06s. The candidate was not written onto the sibling-owned PR branch; the active owner should integrate/cherry-pick equivalent logic and rerun the full original + Different-J suites.

## Claim ceiling

This support branch is evidence and a repair contract, not a production/live continual-work claim. H-F still requires a genuinely fresh independent ChatGPT window; G8/G9/G10 still require runtime/Arena receipts rather than document or unit-test presence alone.
