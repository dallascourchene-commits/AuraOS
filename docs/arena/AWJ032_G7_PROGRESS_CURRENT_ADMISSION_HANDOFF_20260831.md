# AWJ032 GLM-5.3 G7 v2 — Structural Progress/Admission Handoff

**Status:** D0 / HS1 / NONPROMOTING / HOSTED-PROOF-PENDING  
**Date:** 2026-08-31

## Objective

Structurally bind a terminal NAV-14 progress-bearing hydrated-version handoff projection to a terminal generation-bound GLM-5.3 admission-reuse projection while preserving two external trust debts that this pure module cannot pay:

1. parent receipt **producer authentication**;
2. presented use-time **currentness authentication**.

G7 must not launder matching caller-presented fields into source truth, currentness, tensor provenance, reuse authority, execution authority, or Gate-10 evidence.

## Exactly two terminal-green other-Agent parents

1. **NAV-14 / PR #768**
   - proof generation `6cdd1be40428250bffba20e924f664c7be585469`
   - semantic source blob `b1bdfb4c65281c314e658a6fb6fc8727a4b54245`
   - hosted run/job `33437542974 / 99637538062`, SUCCESS
   - earned consequence: exact hydrated material + purpose + independent retrieval progress may produce only `PROGRESS_BOUND_HANDOFF_CANDIDATE`; future read-currentness remains unpaid.

2. **Generation-Bound Admission Reuse / PR #769**
   - proof generation `d1a0f94255527835a59a70a0af7dc417ba1d023d`
   - semantic source blob `d171d0938e469a4383490d1a691750c2068f21e7`
   - hosted run/job `33437612722 / 99637780915`, SUCCESS
   - earned consequence: `AdmissionValidAtProduce != AdmissionReusableAtUse`; exact presented producer/subject/source/evidence/owner/decision axes are required for `REUSE_CANDIDATE`, but that pure projection does not itself authenticate the observer/producer.

## True Git convergence

`afadf96392b2a1fb0f32c488f1b240853b46462c`

Ordered parents: #769 proof generation, then #768 proof generation. The convergence tree carries both exact semantic/test surfaces.

## W3 falsifier and repair

Initial G7-v1 used a caller-constructible `CurrentHandoffUseContextV1` and could label an all-equal presentation `CURRENT_PROGRESS_BOUND_ADMISSION_HANDOFF_CANDIDATE`.

That overclaimed what equality proves:

`MatchingPresentedUseContext != AuthenticatedCurrentness`.

A second inspection found that the parent projections were also caller-constructible and G7-v1 did not recompute the positive parent receipt digests. It also weakened NAV-14's digest-shaped `subject_key` and `evidence_generation_key` into arbitrary text.

Repair:
- rename the positive disposition to `STRUCTURAL_PROGRESS_ADMISSION_MATCH_EXTERNAL_AUTH_REQUIRED`;
- rename use-time input to `PresentedHandoffUseContextV2`;
- preserve NAV-14 subject/evidence digest shapes;
- project NAV-14 `handoff_digest`, `retrieval_receipt_digest`, and `retrieval_decision` and recompute the exact positive NAV-14 receipt digest;
- recompute the exact positive #769 admission-reuse receipt digest;
- only NAV-14 positive retrieval decisions `ALLOW_INITIAL` and `ALLOW_STATE_TRANSITION` are accepted;
- carry explicit permanent debts:
  - `parent_projection_authentication_required=true`;
  - `parent_projection_authenticated_by_this_contract=false`;
  - `presented_currentness_authentication_required=true`;
  - `presented_currentness_authenticated_by_this_contract=false`;
  - `reuse_authorized_by_this_contract=false`.

`SelfConsistentParentProjection != AuthenticatedParentReceipt`.

## Residual

`SelfConsistentParentProjections + MatchingPresentedHandoff != AuthenticatedCurrentReuseUntil ExternalProducerAuthentication + ExternalCurrentnessAuthentication + FutureReadCurrentness + TensorBinding + OwnerHostEffectEvidence`.

## Material implementation

- `tools/awj032/glm53_g7_progress_current_admission_handoff.py`
- `tools/awj032/test_glm53_g7_progress_current_admission_handoff.py`
- `.github/workflows/aura-glm53-g7-progress-current-admission-handoff.yml`
- this objective/provenance record

The positive structural state requires:
- exact terminal parent generations;
- self-consistent positive parent receipt digests;
- NAV-14 positive retrieval semantics;
- GLM-5.3 bounded C2 admission family;
- unchanged nonpromotion ceilings;
- cross-parent subject/evidence-generation equality;
- exact presented progress-handoff receipt/material/source-view continuity.

Any mismatch HOLDs. HOLD receipts suppress identity-bearing fields rather than echoing stale values as current.

## Deliberate non-binding

G7 does not assert:
- that self-consistent parent bytes authenticate their producer;
- that presented use-time fields were read from their owners or are current;
- that #769 `source_generation_key` is proven by NAV-14 source URI/material;
- that material/source-view continuity proves source truth or tensor payload identity.

The fixture URI is only a deterministic source-view identifier, not a source attestation.

## Different-J / HyperScale

Two differently shaped classifiers commute over a complete 512-state bounded structural lattice:

`2 progress-ready × 2 reuse-ready × 2 family × 2 subject-match × 2 evidence-generation-match × 2 presented-progress-receipt-match × 2 material-match × 2 source-view-match × 2 ceiling = 512`.

The v2 focused adversarial suite adds positive-parent receipt self-integrity, NAV-14 positive-decision validation, parent-shape preservation, and explicit external-auth ceilings. Local v2 result before hosted submission: **22 tests green; 512/512 states commute**.

HS1 remains sufficient. The next unresolved dimension is external trust/currentness, not more same-boundary fanout.

## External Different-J pressure

- PLACEMEM (`arXiv:2607.04089`) treats persistent agent state as correction-aware/versioned provenance + validity and does not equate reusable runtime state with timeless truth.
- Memory Provenance Laundering (`arXiv:2607.29167`) independently formalizes source-authority non-amplification through persistent memory.
- Current practitioner reports independently describe stale/superseded memories being retrieved as if current.
- Direct task-specific Scholar-native discovery still yields `SCHOLAR_DIRECT_GAP` for this exact seam.

External evidence is falsification/methodology pressure only.

## K27 / HyperDrive

K27 is deterministic retrieval/reopen metadata only.

`K27Placement != SemanticIdentity != Currentness != Authority`  
`CoordinateMemory != MODEL_PREFIX_KV`

HyperDrive transition:

`SELF_CONSISTENT_NAV14_PROJECTION + SELF_CONSISTENT_ADMISSION_REUSE_PROJECTION + PRESENTED_STRUCTURAL_MATCH -> STRUCTURAL_PROGRESS_ADMISSION_MATCH_EXTERNAL_AUTH_REQUIRED | TYPED_HOLD`.

## Triadic / Creation / Ω8

- W0 exact two-parent hosted provenance + true convergence.
- W1 ordered structural membrane.
- W2 parent/projection/currentness substitutions.
- W3 caller-currentness and parent-producer-auth contradiction; repaired in v2.
- W4 separate producer authentication, structural equality, currentness, future reads, tensor binding, execution/effects.
- W5 exact #768 × #769 synthesis.
- W6 self-consistent/same-looking projection quotient.
- W7 any parent/presented/material/source-view drift reopens the owner.
- W8 effect plane remains unearned.

## Claim ceiling

Even the positive structural state permanently carries:
- `candidate_only=true`;
- `parent_projection_authentication_required=true`;
- `parent_projection_authenticated_by_this_contract=false`;
- `presented_currentness_authentication_required=true`;
- `presented_currentness_authenticated_by_this_contract=false`;
- `future_read_currentness_required=true`;
- `future_read_currentness_proven=false`;
- `reuse_authorized_by_this_contract=false`;
- `tensor_payload_bound=false`;
- `source_truth_proven=false`;
- `evidence_admitted=false`;
- `persistent_write_authorized=false`;
- `execution_authorized=false`;
- `provider_effect_authorized=false`;
- `owner_host_execution_observed=false`;
- `gate10_promoted=false`;
- `semantic_k27_authority=false`;
- `native_private_transformer_kv_accessed=false`.

No model/provider execution, source/currentness truth, physical I/O, tensor provenance, AuraOS-resident routing, replay/recovery proof, Gate-10 promotion, merge/deploy/spend, or public/financial/human effect is claimed.

## Closure rule

The queued v1 workflow generation is superseded and cannot close G7. Closure requires a dedicated hosted SUCCESS on the repaired v2 semantic generation (or a proven semantic-identical descendant) plus review/currentness checks with no unresolved consequence-changing defect.
