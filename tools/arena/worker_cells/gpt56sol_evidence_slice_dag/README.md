# GPT-5.6 Sol — Evidence Slice DAG / Minimum Recompute Compiler

D0 worker cell. It converts exact raw-evidence changes into the smallest dependency-closed recomputation slice while preserving only unaffected, current, verified, dependency-bound witnesses.

## Exact fresh foreign rebase parents
1. **AGENT_09 / PR #832 — Recomputed Evidence Cost Admission V1.** Consequence: efficiency evidence must be recomputed from raw source/trace/workload/transfer material rather than caller-authored validity booleans.
2. **AGENT_01 / PR #833 — Cross-Parent Generation Reproof Certificate V1.** Consequence: generation drift should reprove only the minimum lawful parent/cross-binding cone, while unknown or consequence-changing state fails closed.

## New keeper law

`ChangedEvidenceRoots -> DependencyClosedDescendantsToRecompute`.

`ReusableSlice => OutsideInvalidationCone ∧ Current ∧ Verified ∧ ValidWitnessRoot ∧ ExactDependencyInputBinding ∧ D0`.

A stale witness is allowed only when that node is inside the recomputation cone. Every reused derived witness must bind its `input_root` to the canonical ordered output roots of its declared current dependencies. A self-consistent witness detached from its current parent outputs is not reusable proof. Cycles, missing dependencies, duplicate nodes, unknown changed nodes, incomplete witness sets, stale reusable witnesses, witness-root tamper, dependency detachment, malformed boolean state, or malformed identity fail closed. Timing is observational and excluded from semantic receipt identity.

## Local proof
Final O3R1 repository-layout bytes were exercised in three freshly recreated stdlib-only virtual environments after the dependency-binding repair:
- 15/15 tests per environment = **45/45 PASS**; compile PASS;
- 100,000 independently spelled dependency-closure decisions per environment = **300,000 total**, **0 oracle mismatches**;
- HS1000: 1,000 change-cut challenges, **0 false cutsets**;
- deterministic DAG root `b531d12ff544b804102d86c642599063f0f03bc4358d3fc9af8cb1e933e814f9`;
- deterministic campaign root `44368ed5791e267dc86d477575426c5383aef4e8ffe1ca576af4ee331c45ed2c`;
- deterministic semantic receipt root `37d7a34edaaa84eafbb23cf5b8f4036a44b28b6cdb11819ed164ed7f4c9b2f09` across all three venvs;
- nine-node demo graph averaged **4.32278 recomputed nodes** per random one/two-root change, **48.0308889%** of full-graph recomputation;
- final implementation SHA-256 `2e02a95cefa45cae1b80e110c686de1edb6de7c4a68679b0b26ab4d8475d77c7`;
- final test SHA-256 `ad8dafd52da1ba79addc11dc9afec7361a9173867bc721605e3ad2c28524c3dc`;
- campaign SHA-256 `437f880417ca9560458125793e3fb9e042e1fbc1c1e1614fabf666094ac7c4e5`.

Failed-first runs receive zero proof credit: the first harness used pytest-style functions under unittest and executed zero tests; a second scar included wall-clock throughput in receipt identity. Both were repaired before credited runs. Subsequent review found stale-changed/currentness semantics, witness self-root integrity, generator-safe duplicate detection, and—after the first PR publication—dependency detachment on the reusable side. The latter allowed a witness to be individually current/root-valid while no longer binding the present outputs of its declared parents. O3R1 recomputes that dependency-input root for every reused derived witness, rejects mismatches, adds a regression, and recreates all three proof environments.

## External pressure
- *From Faulty Memories to Corrected Actions* (arXiv:2608.10502) motivates dependency-guided rollback that preserves unaffected trusted state and selectively replays affected computation.
- *SkillTrace* (arXiv:2608.05204) motivates multiple provenance traces and deterministic cached trace comparison rather than monolithic reuse identity.
- Recent practitioner discussion on coding-agent over-verification frames durable evidence-validity state as a way to avoid unnecessary reruns after unrelated repository changes.

Direct task-specific Google Scholar retrieval produced no stable Scholar-native result in this run: `SCHOLAR_DIRECT_GAP`.

## Authority ceiling
D0 software/control-plane scheduling proof only. No parent semantic proof is manufactured here; no merge/deploy authority, provider/model execution, physical GLM/Qwen throughput or energy, native/private transformer KV access, truth/effect authority, or Gate10.
