# AWJ032 GLM-5.3 G5 — Recompute Progress / Version-Currentness Admission

Date: 2026-08-31  
Status: DRAFT / D0 / HS1 / NONPROMOTING  
Coordinate: `K27:AWJ032:G5:RECOMPUTE_PROGRESS_VERSION_ADMISSION`

## Objective

Close the control-plane gap between G4's lawful `HOLD_RECOMPUTE_G3` result and an actual bounded attempt to recompute G3.

Residual:

`G4HOLD_RECOMPUTE_G3 + RetrievalActivity + SourceVersionTransition != LawfulG3RecomputeAttemptUntil IndependentProgressWitness + ExplicitSourceVersionEdge + FutureReadCurrentnessDebt Commute`.

G5 does not execute recomputation. It decides only whether one bounded G3 recompute attempt may be handed to its downstream owner.

## Earned two-parent Diamond

### Parent A — PR #754 Retrieval Progress Guard
Semantic owner head: `412e683b8a3d28bd57e4dc39059283cc823e2fb3`.

Semantic blobs:
- source `5e20a51af1bbafa17c56b3a80125bcf003cc6b62`;
- tests `fd70a6a2ba38220f633c7becf421fbe472bd6b6b`.

The owner PR's provider run was approval-blocked, so proof came through the proof-only mirror `f85135562a5975cd7ea1892ab1c221d9004d3e0d`. Git history shows the mirror changed only workflow plumbing; the semantic source/test blobs are identical. `Aura Retrieval Progress Guard` run `33435590114`, job `99631099474`, finished SUCCESS and executed compile, focused adversarials and the Different-J finite proof.

Reusable consequence: repeated activity with identical retrieval fingerprint, provider state and evidence is not progress. The first no-progress repeat requires a true axis change; further identical no-progress repetition collapses the cone.

### Parent B — PR #755 EKI-4 Version Transition Envelope
Exact semantic/proof head: `162fdb9c69f288090845453a67d1f41da28e8a53`.

Semantic blobs:
- source `7ac33764ee238098a2887af96344ed642565ac48`;
- tests `10c83c2432636908b237fe171eebd0714a10788f`.

`Aura External Version Transition Envelope V1` run `33435683382`, job `99631408076`, finished SUCCESS on the exact head.

Reusable consequence: distinct versioned representation and an explicit predecessor -> successor edge solve representation only. They do not satisfy future read-time source-currentness debt.

## G4 substrate

G4 terminal proof generation: `68d76cb7d08366d085be13ad68871ab3c9cf00e1`.

Dedicated run/job: `33436142388` / `99632931053`, SUCCESS.

G4 establishes `PlanValidAtCompile != PlanValidAtUse` and returns `HOLD_RECOMPUTE_G3` for any identity-bearing planning/runtime generation drift.

## Collision quotient

Active adjacent work is intentionally not absorbed:
- PR #758 owns scheme-serializable hydration transactions across route/epoch/retrieval novelty.
- PR #759 owns preservation of retrieval no-progress debt across K27 route-projection aliases.
- G5 owns only GLM G3 recompute-attempt admission after G4 invalidation, joining #754 progress semantics with #755 source-version/read-currentness debt.

Repository search found no existing GLM owner for this exact relation.

## Typed outcomes

1. `NOT_APPLICABLE_RECOMPUTE` — G4 still says the plan is unchanged.
2. `HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED` — #754 says the first identical no-progress retry must change a real axis.
3. `COLLAPSE_RECOMPUTE_CONE` — #754 says repeated identical no-progress retry must stop.
4. `HOLD_VERSION_TRANSITION_REQUIRED` — G4 source-binding drift exists but no explicit #755-compatible source generation transition is supplied.
5. `HOLD_SOURCE_READ_CURRENTNESS_REQUIRED` — the source version transitioned, but a current read witness for the successor generation is absent, stale or unknown.
6. `ADMIT_BOUNDED_G3_RECOMPUTE_ATTEMPT` — G4 requires recomputation, #754 proves independent progress, and any source-binding drift has both an explicit version edge and a use-time current-read witness.

Admission is not execution, retrieval authority, provider authority, transfer authority or source-currentness minting.

## Triadic Process

**Thesis:** G4 correctly detects stale GLM prefetch plans and requires G3 recomputation.

**Counterplane A:** repeating the same retrieval/recompute activity without any independent state/evidence delta is not progress and can create an infinite control loop.

**Counterplane B:** when the changed G4 axis is `source_binding_generation`, a new version edge still does not prove that the successor source is current at read time.

**Synthesis:** consume #754's progress disposition first; if the retry cone remains open, bind source drift to #755's explicit version-transition semantics and preserve the carried read-currentness obligation. Only then may one bounded G3 recompute attempt be admitted.

## Creation Process

1. Freeze G4 exact terminal proof generation.
2. Freeze #754 semantic owner blobs and proof-only mirror coordinates.
3. Freeze #755 exact semantic/proof head and blobs.
4. Collision-scan current GLM/Navigator/retrieval owners.
5. Type G4, progress, version-transition and current-read projections separately.
6. Implement explicit decision-tree precedence.
7. Implement independently shaped ordered-rule classifier.
8. Attack no-progress, source-version and stale-read substitutions.
9. Exhaust all 90 valid finite control combinations and reexecute G4 tests.
10. Require exact-head hosted SUCCESS before closure or successor credit.

## Eight crystalline validation lenses

1. **Ordered:** G4 revalidation -> progress gate -> version edge -> read-currentness debt -> bounded attempt admission.
2. **Adversarial:** swap progress, source generation, version edge and read state independently.
3. **Contradiction:** `HOLD_RECOMPUTE_G3` cannot imply permission to retry forever; `VersionTransition` cannot imply `CurrentAtRead`.
4. **Factorization:** plan currentness, retrieval progress, version representation, read currentness, recompute admission, execution, effects and K27 remain distinct leaves.
5. **Synthesis:** #754 no-progress law × #755 version/read-debt law under G4's GLM-specific reopen trigger.
6. **Quotient:** decision tree and ordered rule table must collapse to the same typed disposition.
7. **Temporal:** currentness is bound to the successor generation at use time; past persisted labels do not pay future read debt.
8. **Effect ceiling:** bounded admission never executes GLM, retrieval, transfer, routing or provider effects.

## HyperScale

HS1 is sufficient. The valid state space is finite and exhaustible: 90 combinations. Increasing worker count would duplicate proof mass rather than add falsification coverage.

`ScaleUntilProofClosed; DoNotFanOutPastFiniteExhaustion`.

## External Different-J pressure

External work grants no Aura authority; it is falsification and methodology pressure only.

- `Is Agent Memory a Database? Rethinking Data Foundations for Long-Term AI Agent Memory` (arXiv `2605.26252`) argues that long-term memory correctness is a property of the state trajectory rather than an individual stored record. This pressures G5 to distinguish persisted transition artifacts from current use-time state.
- `Risk-Constrained Freshness-Aware Semantic Caching for Open-Web Retrieval-Augmented LLMs` / FreshCache (arXiv `2607.04281`) treats cache reuse as temporal freshness/risk inference rather than similarity-only reuse. This pressures fail-closed future-read currentness rather than assuming a prior cache/version is still valid.
- Current LocalLLaMA GLM-5.3 TensorSharp/llama.cpp measurements (`reddit:1w0wgad`) report a shape-keyed LRU graph cache, warm-cache behavior, CPU-MoE offload and materially different decode behavior across runtime choices. This reinforces that runtime/cache state transitions are real operational axes, not timeless labels.
- A current LocalLLaMA GLM-5.3 local-inference report (`reddit:1w1qp10`) shows strong hardware/runtime sensitivity and very different time-to-first-token from other large models, adding negative pressure against universalizing one cached admission decision.
- Direct task-specific Google-Scholar-native discovery yielded no stable stronger result in this pass. Record `SCHOLAR_DIRECT_GAP`; do not fabricate Scholar provenance.

## External-world K27 coordinate-memory delta

Namespace: `K27-B3MOD27-XYZ-v1`. Coordinates use successive four-byte SHA-256 limbs reduced mod 27. They are deterministic routing/reopen indices only.

| Canonical source ID | K27 XYZ | SHA-256 prefix | Role |
| --- | --- | --- | --- |
| `arxiv:2605.26252` | `(18,21,12)` | `5d33d3e3e0827eae` | state-trajectory memory correctness |
| `arxiv:2607.04281` | `(6,23,11)` | `bbac51fda43f378f` | temporal freshness/risk gate |
| `reddit:1w0wgad` | `(0,1,4)` | `f7c80321e8d34d75` | GLM runtime/cache falsification pressure |
| `reddit:1w1qp10` | `(21,4,26)` | `5e6e5853c06ee18c` | hardware/runtime sensitivity falsifier |
| `scholar:direct-gap:glm53-g5:2026-08-31` | `(11,16,24)` | `4135fa72bb9207f6` | explicit Scholar discovery gap |

`K27Coordinate != SemanticIdentity != Currentness != RuntimeTruth != Authority`.

`CoordinateMemory != MODEL_PREFIX_KV`.

No native/private transformer KV state is read, written, inferred or represented by G5.

## Laws under proof

`G4Hold != RecomputeExecutionAuthority`.

`RepeatedRecomputeActivityWithoutIndependentDelta != Progress`.

`FirstNoProgressRepeat => HOLD_CHANGE_AXIS`.

`RepeatedNoProgressRepeat => COLLAPSE_RECOMPUTE_CONE`.

`SourceBindingGenerationDrift => ExplicitVersionTransitionRequired`.

`VersionTransition != CurrentAtRead`.

`PersistedCurrentness != FutureReadCurrentnessWitness`.

`ProgressWitness + VersionEdge != SourceTruth`.

`BoundedRecomputeAdmission != ModelExecution != ProviderEffect`.

`K27Coordinate != RecomputeAdmission != NativeRoutingAuthority`.

`CoordinateMemory != MODEL_PREFIX_KV`.

## Claim ceiling

No GLM/model/provider execution, retrieval execution, network/provider effect, transfer effect, physical NVMe observation, native-route mutation, source-currentness minting, semantic truth, causal speedup/output-quality claim, G2/Gate-10 promotion, semantic K27 authority, native/private transformer KV access, merge/deploy/spend, or public/financial/human effect is granted.

Closure requires dedicated `Aura GLM53 G5 Recompute Admission` exact-head hosted SUCCESS.