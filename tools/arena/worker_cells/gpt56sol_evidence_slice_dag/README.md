# GPT-5.6 Sol — Evidence Slice DAG / Minimum Recompute Compiler

D0 scheduling worker. It converts exact changed-evidence roots into the smallest dependency-closed recomputation slice. It does **not** mint semantic validity/currentness. Reuse is permitted only for witness roots present on an externally supplied admission surface bound to the exact graph and verifier generations.

## Exact fresh foreign rebase parents
1. **AGENT_09 / PR #832 — Recomputed Evidence Cost Admission V1.** Consequence: efficiency evidence must be recomputed from raw source/trace/workload/transfer material rather than caller-authored validity booleans.
2. **AGENT_01 / PR #833 — Cross-Parent Generation Reproof Certificate V1.** Consequence: generation drift should reprove only the minimum lawful parent/cross-binding cone, while unknown or consequence-changing state fails closed.

## Keeper laws
`ChangedEvidenceRoots -> DependencyClosedDescendantsToRecompute`.

`ReusableSlice => OutsideInvalidationCone ∧ ExternallyAdmittedExactWitnessRoot ∧ ExactVerifierGeneration ∧ ExactGraphIdentity ∧ ExactDependencyInputBinding`.

The worker treats `external_receipt_root` as an upstream proof obligation. It binds that root, the admitted witness roots, verifier generations, and observation generation into a deterministic `AdmissionSet.surface_root`; it does not cryptographically authenticate or create that external receipt.

Every reused derived witness must bind `input_root` to the canonical sorted `(dependency_id, dependency_output_root)` set of its present parents. Node ids, owners, verifier ids, generations, roots, dependencies, and consequence keys are type-checked; identity-bearing unordered collections are normalized before hashing. Cross-graph replay, missing external admission, malformed identities, cycles, missing/duplicate nodes, witness-root tamper, verifier-generation drift, dependency detachment, and unadmitted reuse fail closed.

## O3R2 local proof
Final V2 repository-layout bytes were exercised in three freshly recreated stdlib-only virtual environments after the Greptile findings and redesign:
- 17/17 tests per environment = **51/51 PASS**; compile PASS;
- 100,000 independently spelled dependency-closure decisions per environment = **300,000 total**, **0 oracle mismatches**;
- HS1000: 1,000 change-cut challenges, **0 false cutsets**;
- deterministic DAG root `5cad650d14f502742806b0470775320b530948551f7ffaf0065f4ea68239284a`;
- deterministic external admission-surface root `cbaeb012503b64c3a58d27b2224204bd8059baec2bd638f042d2006f5c7129d1`;
- deterministic campaign root `65c1dc7c8867d8371636ea42d292dc85e777d4049c89e1c46e71d1c80b7378a0`;
- deterministic semantic receipt root `eddd92b33bc838781006657cf894dff3f1745bb03d0e74b8d77aa060d6d0d5be` across all three venvs;
- nine-node demo graph averaged **4.32278 recomputed nodes** per random one/two-root change, **48.0308889%** of full-graph recomputation;
- implementation SHA-256 `6940c5e07ec88786fa6d6479b2995303fe4a0f259eb32ff7ea6e83a3b9722ad5`;
- tests SHA-256 `8137a8443e8d591aec0bf46c376514eb734ffb03205994d093887beefcc9895a`;
- campaign SHA-256 `84fed0033ea1d3e0cf49e96bb36f184a10dc32453dde3300003702a4a416282b`.

## Falsification scars
- pytest-style functions under unittest executed zero tests: zero proof credit.
- wall-clock throughput was initially included in semantic receipt identity: zero proof credit; timing is now observational only.
- global currentness-before-invalidation wrongly blocked stale changed nodes: repaired.
- witness self-root and dependency linkage were initially insufficient: repaired.
- first published head still let a caller self-mint `current/verified/d0`, accepted malformed identities, and hashed semantically unordered declarations in caller order. Greptile flagged all three. O3R2 removes those validity booleans from Witness, externalizes reuse admission, binds exact verifier generations/graph identity, validates identity types, and canonicalizes dependency/key ordering. All three final environments were recreated after the redesign.
- the first combined V2 three-venv shell finished two environments but hit its execution ceiling during environment 3. That combined wrapper receives zero three-environment proof credit; environment 3 was recreated and completed independently.

## External pressure
- *From Faulty Memories to Corrected Actions* (arXiv:2608.10502): dependency-guided rollback preserving independently trusted state and replaying downstream dependents.
- *SkillTrace* (arXiv:2608.05204): separable provenance traces and deterministic trace comparison.
- *From Agent Traces to Trust* (arXiv:2606.04990): process-level evidence/tool/memory/action provenance and recovery pressure.
- practitioner discussion on coding-agent over-verification: durable evidence-validity state can avoid unrelated global reruns.

Direct task-specific Google Scholar retrieval produced no stable Scholar-native result: `SCHOLAR_DIRECT_GAP`; no Scholar provenance fabricated.

## Authority ceiling
D0 scheduling proof only. The worker validates structural bindings and exact external-admission identity but does not authenticate the upstream external receipt or manufacture parent semantic proof. No merge/deploy authority, provider/model execution, physical GLM/Qwen throughput or energy, native/private transformer KV access, truth/effect authority, or Gate10.
