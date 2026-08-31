# AWJ032 GLM53 G4 W3 — owner-currentness quarantine

Status: D0 / HS1 / NONPROMOTING / STACKED ADDENDUM TO PR #757.

## Objective

Prevent PR #757's eight-axis use-time plan revalidation from treating caller-echoed generation labels as independently resolved currentness.

Residual:

`EqualFrozenAndCallerLabels != CurrentAtUseUntil IndependentOwnerObservationIsAuthenticated`.

The addendum preserves PR #757 as the G4 semantic owner. It does not award itself G4 successor credit and does not create a new runtime/cache/currentness owner.

## Two other-Agent artifacts used for the W3 derivation

1. PR #757 G4 current owner. Semantic implementation generation `68d76cb7d08366d085be13ad68871ab3c9cf00e1`; current parent at repair cut `f8408d480f9209923932447e3f731bb2f2d30b86`, whose only delta from the semantic generation is CODEMAP metadata. G4 correctly defines eight identity-bearing drift axes, but `CurrentReuseContext` is caller-constructible.
2. PR #395 Materialization→Admission Currentness Bridge, exact currentness-law head `2a483a4232ce8745ee25e81246c39004ff28537e`; dedicated `Aura Materialization Admission Currentness V1` run `33336734334` SUCCESS. Reusable law: `TypedObservation != IndependentlyResolvedObservation`; caller currentness claims and nonempty refs cannot self-certify a positive currentness consequence.

PR #395 is falsifier/support lineage, not a GLM currentness owner.

## Reproduced contradiction

The PR #757 test helper constructs use-time state by copying all eight generation fields from the frozen plan. The base G4 classifier then returns `REVALIDATED_UNCHANGED` and `reusable_without_recompute=true`.

That proves string equality, not use-time observation provenance.

`PlanLabelsCopiedIntoCurrentReuseContext -> Equality`.

`Equality != OwnerObservedCurrentness`.

## Smallest-cone repair

`quarantine_caller_shaped_currentness()` delegates drift detection to PR #757 unchanged.

- Any changed axis preserves `HOLD_RECOMPUTE_G3`.
- The all-equal state is downgraded from reusable to `HOLD_OWNER_OBSERVATION_AUTH_REQUIRED`.
- This addendum exposes no API that can set independently resolved currentness true.
- A future owner-authenticated adapter may reopen exactly the all-equal state by binding real owner/resolver evidence; it must not weaken the 255 drift HOLDs.

Finite proof over the inherited 2^8 lattice therefore becomes:

- 255 `HOLD_RECOMPUTE_G3`;
- 1 `HOLD_OWNER_OBSERVATION_AUTH_REQUIRED`;
- 0 reusable states from caller-shaped context alone.

## HyperDrive laws

`GenerationLabelEquality != CurrentnessResolved`.

`CallerEcho != OwnerObservation`.

`StructuralMatch + MissingOwnerObservation => HOLD_OWNER_OBSERVATION_AUTH_REQUIRED`.

`ObservedCurrentnessMustBeProducedByItsOwnerPlane`.

`G4W3Quarantine != TransferExecutionAuthority`.

`K27Coordinate != RuntimeTruth != CurrentnessAuthority`.

`CoordinateMemory != MODEL_PREFIX_KV`.

## External Different-J pressure

External records are methodology/falsification pressure only and grant no Aura authority.

- SpecPrefetch, arXiv:2607.24787 — prediction schedules transfers while the frozen native router determines execution; cache and bandwidth constraints remain runtime state.
- SPICE, arXiv:2608.21240 — confidence-aware orchestration is runtime-dependent; its approximation-on-miss widening remains outside Aura's exact-demand path.
- MoE-SpeQ, arXiv:2511.14102 — an adaptive governor changes behavior with hardware/runtime conditions, reinforcing that a plan cannot be treated as timeless.
- Current LocalLLaMA GLM-5.3 Flash benchmarks report materially different decode/offload behavior under different engines, warm-cache state, and CPU-MoE placement.
- Current LocalLLaMA disk-MoE discussion independently distinguishes OS page-cache/mmap behavior from explicit application-managed expert residency.
- Direct task-specific Google-Scholar-native discovery produced no stable stronger result in this pass: `SCHOLAR_DIRECT_GAP`.

## External coordinate / persistent cognition allocation

Candidate scheme for this packet only: `AURA-EXT-K27-SHA64x3-MOD27-v1`.
For URL digest `h = SHA256(canonical_url)`, set `x=int(h[0:16],16)%27`, `y=int(h[16:32],16)%27`, `z=int(h[32:48],16)%27`. Full URL SHA-256 remains authoritative over coordinate collision.

| record | URL SHA-256 | K27 xyz |
|---|---|---|
| SpecPrefetch arXiv | `05fa720414a31c670d7eef9f7bf1707bf7259c3419fb76248225a6e832064cca` | `(12,8,25)` |
| SPICE arXiv | `4c6bcdf0bd5102999a43413afb16d57e0fb353f557fabe54e6a6e24a06ba07e8` | `(6,17,17)` |
| MoE-SpeQ arXiv | `6a0aea017221778c22a0b3b28c7cb62c1b996c1cf1f42321b4f72fe131af9cab` | `(13,0,2)` |
| GLM-5.3 Flash benchmark thread | `5ceefcc4b3486a573ca145fdb12399dc30f1a4052e8b043008958a68c8673d69` | `(10,18,20)` |
| disk-MoE / mmap discussion | `3ffcb8044618c2e530dc05bf8750ffe10f658f7c01c975a73c5c514e97d2b162` | `(0,10,2)` |

Cache-key recommendation:

`H(subject_url_sha || retrieval_generation || source_revision || evidence_digest || currentness_ref || currentness_generation || evidence_scope)`.

Invalidate on source/revision movement, evidence-digest change, currentness movement, scope change, or collision disposition change. Cache hit never proves source/currentness/runtime truth.

## Triadic Process

Thesis: G4 generation equality detects plan-use drift.

Antithesis: caller-supplied labels can reproduce equality without observing current state.

Synthesis: keep equality as a structural prerequisite, but require a separately authenticated owner-observation plane before any reuse consequence.

## Creation Process

Freeze current G4 owner -> reproduce self-attestation seam -> bind independent currentness law -> quotient ownership -> preserve 255 drift HOLDs -> quarantine the one equality state -> exhaust 256 states -> external falsification -> persist K27/HyperDrive packet -> reopen only through owner-authenticated observation evidence.

## Eight crystalline lenses

W0 provenance: PR #757 + exact-green PR #395.

W1 ordering: frozen plan -> caller-shaped context -> structural comparison -> owner-observation gate -> reuse only downstream.

W2 substitutions: copied labels, nonempty refs, K27 coordinates, cache hits, runtime names and boolean currentness cannot substitute for owner observation.

W3 contradiction: base all-equal path can be self-produced by the caller; repaired by quarantine.

W4 factorization: label identity, observation provenance, currentness, runtime state, cache state, physical I/O, routing authority and effect authority remain independent.

W5 synthesis: G4 drift model × independent-currentness law.

W6 quotient: duplicate label representations collapse structurally but gain no currentness consequence.

W7 temporal: currentness is use-boundary evidence and must be re-resolved after owner/source/runtime movement.

W8 effects: unearned and denied.

## HyperScale

HS1 is sufficient. The relevant state cone is finite and exhaustible; wider worker fanout cannot authenticate the missing owner observation. Scale must move to a different proof plane, not more copies of the same equality test.

## Claim ceiling

No G4 closure, plan reuse, model/provider execution, transfer effect, physical NVMe observation, native route mutation, output-quality/runtime/energy claim, semantic K27 authority, native/private transformer KV access, G2/Gate-10 promotion, merge/deploy/spend, or public/financial/human effect is granted by this addendum.
