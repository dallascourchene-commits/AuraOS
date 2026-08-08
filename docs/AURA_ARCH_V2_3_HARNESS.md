# Aura ARCH v2.3 Harness — Repository Orientation

**Current governance standard:** `AURA_ARCH_V2_3`  
**Core bundle:** `docs/architecture_harness/ARCH_V2_3/`  
**Authority:** human-governed; no automatic merge or production authority

Aura uses the word **harness** for several related but different things. This file is the orientation point that prevents those layers from being conflated.

## 1. The four-file ARCH v2.3 bundle

| File | Role |
|---|---|
| `AURA_UNIVERSAL_REFACTOR_CONVERGENCE_HARNESS_V2_3.md` | Human-readable architecture, state machine, threat model, recursive-work rules, learning/evolution rules, security tests, and implementation handoff. |
| `aura_arch_v2_3_default_policy.json` | Machine-readable default policy: authority, communication, JSpace, convergence, rollback, verifier-independence, and commit-time authorization defaults. |
| `aura_pr_continuity_capsule.v2_3.schema.json` | Machine-readable contract for the authoritative per-PR continuity state. |
| `AURA_PR_CONTINUITY_CAPSULE_TEMPLATE_V2_3.md` | Generated/readable projection template for humans and fresh AI workers. The JSON capsule remains authoritative. |

These four files are one versioned contract. Do not mix the v2.3 Markdown with a stale v2/v2.2 policy or capsule schema.

## 2. How this relates to Aura's other harnesses

### ARCH v2.3 — governance and convergence standard

ARCH governs long-horizon AI-assisted refactors: exact-head continuity, scope, authority, recursive workers, patch transactions, proof, review, learning, convergence, communications, and stopping.

### `scripts/aura_architecture_harness.py` — repository orientation/execution companion

The Architecture Harness CLI produces bounded AI-safe repository handoffs and runs Aura's own Connectome/Relational Index/Atlas/Emergent/Architect analysis. It is a source-orientation and proposal surface. It does not replace ARCH v2.3's governance state.

### `scripts/aura_runtime_refactor_harness.py` — runtime observation/proof

The Runtime Refactor Harness reproduces declared runtime profiles, probes them, retains verification evidence, and emits cleanup/proof receipts. It observes and verifies; it does not authorize patches, commits, publication, or merge.

They compose as follows:

```text
ARCH v2.3 policy + continuity capsule
              ↓
exact-head Architecture Harness orientation / bounded source handoff
              ↓
Arena / Council / Surgeon / external worker under leases
              ↓
Runtime Refactor Harness and other exact verifiers
              ↓
verifier-independence check
              ↓
commit-time authorization revalidation
              ↓
READY_FOR_HUMAN_REVIEW
              ↓
human disposition
```

## 3. Fresh-agent startup sequence

1. Read `README.md` and `.aura/ARCHITECTURE.md`.
2. Read this orientation file.
3. Load the v2.3 default policy JSON.
4. Validate/create the current PR capsule against the v2.3 schema; render the Markdown projection from that JSON state.
5. Re-establish exact repository/base/head identity and current CODEMAP/topology health.
6. Discover canonical owners before adding modules or stores.
7. Admit only the minimum task-conditioned capabilities and declared coordination channels.
8. Use AuraJSpace only as bounded advisory working state when useful.
9. Preserve exact evidence, rejected approaches, proof receipts, origin labels, and authority ceilings through compaction/handoff.
10. Before any durable effect, revalidate commit-time authority against the exact effect and current head/lease/dependency state.
11. Record verifier independence/correlation, not just reviewer count.
12. Stop at `READY_FOR_HUMAN_REVIEW`; no autonomous merge.

## 4. What v2.3 adds over v2.2

ARCH v2.3 preserves the complete v2.2 recursive/provenance-governed continual harness and adds:

- a **declared communication plane** and threat model for storage, timing, and behavioral covert channels;
- explicit prohibition on a second communications/control/shared-workspace plane;
- **non-malleable origin-bound authority** across summaries, tool echoes, derived state, and worker consensus;
- **commit-time authorization** for durable effects;
- verifier **independence/correlation receipts** and Sybil/manufactured-corroboration resistance;
- a governed **AuraJSpace bounded deliberative working set**;
- deterministic enforcement below prompt-only/model-monitor policy.

## 5. AuraJSpace in ARCH v2.3

Aura already implements a deterministic JSpace codec in `aura_jspace_codec.py`. The repository implementation is explicit:

- codec: `AURA_JSPACE_CODEC_V0`;
- packet family: `J0`;
- default active limit: `25`;
- purpose: compact active route/workspace state;
- patch authority: none; exact source spans, hashes, tests, and verifier gates remain authoritative.

ARCH v2.3 uses it as a **reconstructable advisory deliberative working set** for the live refactor capsule. A v2.3 JSpace projection is bound to workspace/head/phase and carries only digests/source/origin references needed to reconstruct its state. It is not a second memory database and cannot mint route, policy, verifier, patch, or merge authority.

### Anthropic J-space is related by design lesson, not implementation

Anthropic's July 2026 interpretability work describes an emergent neural activation subspace found with a Jacobian-based lens. Their researchers report a small selectively populated workspace and typically use a sparsity parameter no greater than about 25 meaningfully active J-lens vectors. Aura's JSpace is **not that neural mechanism**: it is explicit software, deterministic, inspectable, and policy-bounded.

The useful engineering correspondence is the bounded-working-set pattern: keep a small, current set of deliberatively relevant concepts available while exact evidence and canonical owners remain elsewhere.

The default v2.3 profile therefore keeps Aura's existing `25` active-item ceiling. It is configurable downward and should be re-evaluated empirically; it is not treated as a universal law.

## 6. Non-negotiable v2.3 invariants

```yaml
no_second_truth_plane: true
no_second_memory_plane: true
no_second_routing_plane: true
no_second_verification_plane: true
no_second_policy_plane: true
no_second_authority_plane: true
no_second_governance_plane: true
no_second_merge_plane: true
no_second_communications_or_control_plane: true
no_second_shared_workspace_plane: true
child_authority_subset_of_parent: true
derived_state_may_increase_authority: false
origin_binding_non_malleable: true
declared_channels_only: true
commit_time_authorization_for_durable_effects: true
jspace_authoritative: false
jspace_patch_authority: false
jspace_persistent_truth: false
verifier_vote_count_is_independence: false
endpoint_success_is_authorization: false
automatic_merge: false
human_review_required: true
```

## 7. Research basis for the v2.3 delta

The v2.3 additions were informed by current external work on covert event channels in agent systems, commit-time authorization, non-malleable origin-bound memory authority, runtime/institutional multi-agent governance, task-conditioned least privilege, and Anthropic's J-space/global-workspace findings. These are external precedent, not Aura benchmark claims. See the provenance appendix in the main v2.3 harness document for exact references.

## 8. Migration rule

Do not silently rewrite an in-flight capsule from an older schema. A human may explicitly migrate a PR to v2.3 by re-establishing exact head, preserving all accepted decisions/invariants/rejected approaches/proofs, initializing the new communication/JSpace/commit-authorization/independence fields, and validating the result against the v2.3 schema.
