# AWJ032 GLM-5.3 G4 — Structural Generation Revalidation + Owner-Currentness Gate

Date: 2026-08-31  
Status: DRAFT / D0 / HS1 / NONPROMOTING  
Coordinate: `K27:AWJ032:G4:PREFETCH_PLAN_REVALIDATION`

## Objective

Prevent a previously lawful G3 speculative transfer plan from being treated as current after consequence-relevant runtime state changes, while preventing caller-shaped generation labels from impersonating authenticated owner currentness.

G3 terminal semantic/proof generation is frozen at `bdcd92c25308a70f263439c23a73d0240b511d86`:
- G3 dedicated run `33428379023`, job `99607453967`, SUCCESS;
- descendant-safe G2-W3 run `33428378932`, job `99607453756`, SUCCESS.

## W3 falsifier and repair

Initial G4 semantics returned `REVALIDATED_UNCHANGED` / reusable when all eight caller-supplied generation strings matched. Independent audit found that `CurrentReuseContext` carried only caller-constructible labels; exact equality therefore proved structural agreement but not that predictor/calibration/policy/source/runtime/cache/storage/host owners authenticated those labels.

This mirrors the existing GLM observation boundary in PR #736:

`MatchingCallerWitness + UnauthenticatedReceipt != AuthenticatedObservation`.

G4 correction:

`MatchingGenerationLabels != AuthenticatedOwnerCurrentness != ReuseAuthority`.

The one zero-drift state now returns `STRUCTURAL_MATCH_OWNER_AUTH_REQUIRED`. It is explicitly non-executable and cannot authorize reuse. Any of the eight axes drifting returns `HOLD_RECOMPUTE_G3`.

`CurrentReuseContext.owner_currentness_authenticated` is hard-false and rejects caller self-minting. `G4RevalidationReceipt` keeps `owner_currentness_authentication_required=true`, `owner_currentness_authenticated_by_this_contract=false`, and `reuse_authorized_by_this_contract=false`.

## Eight identity-bearing axes

1. prediction generation
2. calibration generation
3. policy generation
4. source-binding generation
5. runtime generation
6. cache generation
7. storage-geometry generation
8. host-profile generation

Two differently shaped classifiers—the explicit tree and ordered axis table—must commute on the same canonical changed-axis tuple.

## Finite proof

The complete `2^8 = 256` lattice is exhaustible at HS1:
- exactly 1 structural match requiring external owner authentication;
- exactly 255 `HOLD_RECOMPUTE_G3` states;
- exactly 0 authenticated reuse authorizations minted by G4.

Manual receipt construction is hardened as well: the G3 receipt digest and G4 plan identity digest must remain lowercase SHA-256 values, and changed-axis tuples reject duplicates, unknown axes, and noncanonical ordering.

## Triadic / Creation / crystalline pass

- **W0:** freeze exact terminal-green G3 coordinates.
- **W1:** plan -> use-time projection -> structural comparison -> owner-auth gate / HOLD.
- **W2:** mutate each generation independently; attempt caller-authentication and digest substitution.
- **W3:** contradiction `matching labels = authenticated currentness` discovered and repaired.
- **W4:** prediction/calibration/policy/source/runtime/cache/storage/host/physical/effect remain separate leaves.
- **W5:** combine G3 temporal currentness with the PR #736 provenance lesson without borrowing PR #736 terminal-parent credit.
- **W6:** tree/table Different-J classifiers collapse to one canonical drift quotient.
- **W7:** any identity-bearing generation drift reopens the smallest G3 currentness cone.
- **W8:** reuse/execution/physical/G2/Gate10/effect authority remains unearned.

Creation sequence: freeze -> collision scan -> enumerate axes -> build two classifiers -> adversarial substitutions -> W3 provenance challenge -> downgrade equality to structural-only -> exhaust 256 states -> reexecute G3 -> exact-host proof -> independent review -> persist/recurse.

## External Different-J pressure

External sources are falsification/methodology pressure only; they grant no Aura authority.

- SpecPrefetch, arXiv `2607.24787`, separates speculative transfer scheduling from the frozen native router under cache/bandwidth constraints.
- SPICE, arXiv `2608.21240`, makes speculative-expert handling confidence/runtime dependent and introduces approximation-on-miss; that approximation remains outside Aura's exact-demand cone.
- SP-MoE, arXiv `2510.10302`, reports deployment-sensitive expert-prefetch policies and latency modeling.
- Current public GLM-5.3 DFlash2/SGLang DGX Spark evidence reports large configuration-dependent changes across speculation, KV format, concurrency and host/runtime choices.
- LocalLLaMA GLM-5.3 benchmark reports similarly vary with graph caching and CPU-MoE offload; community evidence is advisory only.
- Direct Google-Scholar-native task-specific discovery yielded no stable stronger primary result: `SCHOLAR_DIRECT_GAP`.

## External-world K27 coordinate-memory delta

Scheme: canonical URL -> SHA-256 -> first three digest bytes modulo 27. These are deterministic retrieval/reopen coordinates only.

| Source | K27 XYZ | SHA-256 |
| --- | --- | --- |
| `https://arxiv.org/abs/2607.24787` | `(5,7,6)` | `05fa720414a31c670d7eef9f7bf1707bf7259c3419fb76248225a6e832064cca` |
| `https://arxiv.org/abs/2608.21240` | `(22,26,16)` | `4c6bcdf0bd5102999a43413afb16d57e0fb353f557fabe54e6a6e24a06ba07e8` |
| `https://arxiv.org/abs/2510.10302` | `(12,16,21)` | `27cd81f880c901aae9581493ed69aa91a5ed5695f4eef0b681e3e0b18cf7a73f` |
| NVIDIA GLM-5.3 DFlash2/SGLang DGX Spark thread | `(9,20,5)` | `9014ddc272d568c2e72257f98d63c5690657da2d222761bac0c971b6617476e3` |
| LocalLLaMA GLM-5.3 TensorSharp/llama.cpp benchmark | `(11,22,9)` | `5ceefcc4b3486a573ca145fdb12399dc30f1a4052e8b043008958a68c8673d69` |
| LocalLLaMA disk-MoE/offload discussion | `(9,9,22)` | `3ffcb8044618c2e530dc05bf8750ffe10f658f7c01c975a73c5c514e97d2b162` |

`K27Coordinate != SemanticIdentity != Currentness != RuntimeTruth != Authority`.

`CoordinateMemory != MODEL_PREFIX_KV`.

No native/private transformer KV state is read, stored, or mutated by G4.

## Core laws

`PlanValidAtCompile != PlanValidAtUse`.

`AnyIdentityBearingAxisDrift => HOLD_RECOMPUTE_G3`.

`EmptySpeculativePlan != TimelessPlan`.

`MatchingGenerationLabels != AuthenticatedOwnerCurrentness`.

`AuthenticatedOwnerCurrentness != ReuseExecutionAuthority`.

`StructuralMatch != PhysicalIOObservation`.

`SameReceiptDigest + DifferentRuntimeGeneration => Recompute`.

`K27Coordinate != PlanValidity != NativeRoutingAuthority`.

## Claim ceiling

G4 proves structural generation comparison only. It does not authenticate the generation owners, authorize plan reuse or transfer execution, observe physical NVMe bytes, mutate the native route, prove causal speedup/output quality, admit G2/Gate10, access native/private transformer KV, mint semantic K27 authority, merge/deploy/spend, or create public/financial/human effects.

Closure requires the dedicated exact-head hosted workflow to succeed on the repaired semantic generation and independent review to reveal no unresolved consequence-changing defect.
