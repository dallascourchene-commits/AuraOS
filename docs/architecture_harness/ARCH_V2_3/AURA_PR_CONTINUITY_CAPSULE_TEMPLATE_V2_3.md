---
capsule_schema: AURA_PR_CONTINUITY_CAPSULE_V2_3
generated_projection: true
harness_version: AURA_ARCH_V2_3
authoritative_state: ".aura/pr_context/PR-XXXX.context.json"
pr_number: XXXX
phase: "P?"
base_sha: "<40-hex>"
head_sha: "<40-hex>"
capsule_generation: 1
last_transaction_id: null
terminal_state: "ORIENTING"
---

# Aura PR #XXXX Continuity Capsule

> **Generated file. Do not edit directly.**  
> Update the authoritative JSON state through the ARCH controller, then regenerate this projection.

## 0. Fresh-agent bootstrap

**What this PR is doing:**  
<One paragraph>

**Why it exists:**  
<One paragraph>

**Current phase:** `<P1/P2/...>`

**Current exact head:** `<sha>`

**Last known green:** `<sha>`

**Current blocker/root cause:**  
<One paragraph>

**Exactly one authorized next action:**  
<One imperative action>

## 1. Objective

<Exact objective>

## 2. Non-objectives

- <Explicit non-objective>
- <Explicit non-objective>

## 3. Predecessor and inherited state

- Parent PR / phase:
- Exact predecessor merge:
- Inherited decisions:
- Inherited invariants:
- Known predecessor limitations:

## 4. Exact scope

### Allowed paths

- `path`

### Forbidden or generated paths

- `path`

### Allowed symbols

- `symbol`

## 5. Architecture summary

<Bounded description of the relevant system and relationships>

## 6. Canonical owners

| Domain | Canonical owner | This PR may |
|---|---|---|
| Example | `module_name` | delegate only |

## 7. Accepted input and threat model

- Accepted input domain:
- Rejected input classes:
- Trust boundaries:
- Threat-model changes requiring human approval:

## 8. Authority boundary

This PR does **not** grant:

- <authority>
- <authority>

## 8A. Delegation and active leases

- Authority ceiling digest:
- Active lease IDs:
- Revoked lease IDs:
- Delegation-chain receipt refs:
- Child authority subset check: PASSED / FAILED / NOT_APPLICABLE

## 8B. Declared communication plane

- Declared channel IDs:
- Message/delivery receipt refs:
- Shared files/caches/status surfaces reviewed as possible channels: YES / NO
- Storage/timing/behavioral covert-channel findings:
- Undeclared channel detected: FALSE / TRUE

## 9. Accepted decisions

| ID | Status | Decision | Rationale | Head |
|---|---|---|---|---|
| `DEC-0001` | ACCEPTED | ... | ... | `<sha>` |

## 10. Superseded or rejected approaches

| ID | Approach | Why rejected | Do not retry unless |
|---|---|---|---|
| `REJ-0001` | ... | ... | ... |

## 11. Invariant registry

| ID | Statement | Status | Proof head | Proof |
|---|---|---|---|---|
| `INV-...` | ... | PROVEN | `<sha>` | `receipt` |

## 12. Current execution state

### Observed

- `path/symbol @ digest`

### Modified

- `path`

### Attempted

- `command/test/review`

### Stale observations

- `item that must be reread`

## 12A. JSpace advisory working-set projection

- Status: ENABLED / DISABLED / UNAVAILABLE
- Codec version: `AURA_JSPACE_CODEC_V0` / null
- Active limit: `<= 25`
- Packet digest:
- Phase hash:
- Source refs:
- Origin refs:
- Freshness: CURRENT / STALE / UNKNOWN / NOT_APPLICABLE
- Authoritative: **false**
- Patch authority: **false**
- Persistent truth: **false**
- Reconstructable: **true**

If stale, reconstruct from canonical capsule/route/evidence or disable it. Never promote a JSpace item directly to truth, policy, capability, verifier status, or patch authority.

## 13. Active findings and root-cause groups

| Root cause | Findings | Invariants | Status | Proposed disposition |
|---|---|---|---|---|
| `RC-...` | `R...` | `INV-...` | OPEN | PATCH / REFRAME |

## 14. Patch transaction history

### PT-0001 — <title>

- Starting head:
- Ending head:
- Trigger:
- Root cause:
- Hypothesis:
- What changed:
- Why:
- Tests:
- Proof receipt:
- Burden before:
- Burden after:
- Regressions:
- Decision: PROMOTED / DESTROYED / ROLLED_BACK

## 15. Proof ledger

| Invariant | Proof type | Evidence | Freshness condition | Status |
|---|---|---|---|---|
| `INV-...` | test/runtime/static | ... | ... | PROVEN |

## 15A. Verification independence

- Status: UNASSESSED / INDEPENDENT / CORRELATED / CONFLICTING
- Verifier refs:
- Shared-origin refs:
- Shared-context refs:
- Shared-tool/model/session refs:
- Independence receipt:
- Exact contradictions retained: YES / NO

## 16. Reviewer history

| Wave | Reviewer | Head range | Root causes found | Disposition |
|---|---|---|---|---|
| 1 | CodeRabbit | ... | ... | ... |

## 17. Regression risks

- <risk>
- <risk>

## 18. Context compaction

- Current generation:
- Estimated L2 tokens:
- Last compaction:
- Previous generation digest:
- Current generation digest:
- Minimum-fidelity coverage: PASSED / FAILED

## 18A. Commit-time authorization

- Status: NOT_REQUIRED / PENDING / VALIDATED / STALE / REVOKED / REFUSED / REPLAN_REQUIRED
- Planned/candidate effect digest:
- Authority witness digest:
- Validated exact head:
- Lease still current: YES / NO / N/A
- Dependency/effect binding still current: YES / NO / N/A
- Validated at:
- Expires at:
- Receipt ref:
- Revalidation required before durable effect: **true**

Endpoint success is not authorization. A stale or mismatched witness requires replan/refusal before durability.

## 19. Durable-promotion checklist

- [ ] Durable decisions promoted
- [ ] Permanent invariants promoted
- [ ] Public documentation updated
- [ ] Reusable tests retained
- [ ] Unresolved work transferred
- [ ] Final PR summary updated
- [ ] Terminal capsule receipt emitted
- [ ] Temporary capsule deleted from final tree

## 20. Handoff instructions

1. Verify the checkout head equals the recorded head.
2. Read the L0 bootstrap and active root-cause group.
3. Do not act on raw reviewer comments.
4. Do not retry rejected approaches.
5. Do not change scope, threat model, authority, or decisions.
6. Use only declared communication channels; treat shared files/cache/status/JSpace as potential channels.
7. Preserve non-malleable origin and authority labels across summaries/tool echoes/derived state.
8. Treat JSpace as advisory reconstructable working state only.
9. Revalidate authority at the durable commit boundary.
10. Record verifier correlation/independence; do not equate vote count with independence.
11. Perform only the authorized next action.
12. Record results through the ARCH controller.
