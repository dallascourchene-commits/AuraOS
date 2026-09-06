# GPT-5.6 Sol — Transition-Aware K27 Cache Admission

D0 worker cell binding Transition/Reproof semantics to K27 persistent coordinate memory without treating coordinates or cache hits as truth.

Keeper:

`RuntimeReuse => TransitionReusable ∧ ExactSubject ∧ ExactSemanticRoot ∧ ExactProviderAnchor ∧ ExactDependencyRoot ∧ RuntimeOwnerGeneration ∧ CompatibilityProfile ∧ BenchmarkGeneration ∧ PayloadHash ∧ D0`.

Physical routing signals (recompute cost, dependency fanout, invocation frequency, locality, queue depth) are evaluated **only after** semantic admission. They can rank already-valid cache entries but cannot repair stale provenance/currentness.

K27 coordinates are deterministic reopening geometry derived from full identity SHA-256. The full digest remains identity; `(x,y,z)` is not truth, currentness, semantic authority, or native transformer KV.

## Local proof
Final repository-layout bytes were exercised in three freshly recreated Python stdlib-only virtual environments after fail-closed routing hardening:
- 20/20 tests per environment = **60/60 PASS**; compile PASS;
- 100,000 independently spelled admission decisions per environment = **300,000 total**, **0 oracle mismatches**;
- HS1000 = ten mutation families × 100 cases, **0 false runtime-reuse admissions**;
- Ω8 exhaustive `3^8 = 6,561`, exactly one fully valid keeper;
- all `3^5 = 243` trailing 13D contexts fail to repair a hard-invalid core;
- deterministic campaign root `ddb249496b9245866d3d73a582883e1d5575cba5905fd9f64b8e03e770c8650f`;
- deterministic transition root `ade7c12a10080f51e354d12edcdadc112aa5f6c2effaa76c6bcd14e34c6abf01`;
- deterministic entry root `ea1213bd72727008e86d7a2418f5a6575537f86c1216cf5a2621819d3740ede9`;
- deterministic semantic receipt root `16bd8528c0f50e302611fb8d732cc14be62398799af5d6e530a868eee9de85e5` across all three environments.

Final SHA-256:
- implementation `19e7fc2724f50fc580d45c2fdc35497ee8906099694187f134abec0575fe8d4f`;
- tests `0e2eb3192e334a1d6c0936d3ac7ad34b2bb60043f0aecc71a1f3008b268764dd`;
- campaign `067313fa1f93bd3b45c71b909bcac374905697070d6d20a82442e6e0d9e7c20a`.

Failed-first scar: an otherwise semantically valid request with malformed/overflowing routing signals initially escaped via an exception. Routing validation/overflow is now fail-closed as HOLD, and all final virtual environments were recreated after the repair.

## External pressure
- arXiv:2608.10502 motivates dependency-guided rollback that selectively replays only affected dependents while preserving independently trusted state.
- arXiv:2609.00243 motivates fine-grained invalidation contracts rather than coarse cache flushing.
- arXiv:2607.20495 and arXiv:2608.14624 motivate workload/DAG/execution-aware physical cache retention and prefetching after correctness/currentness is established.
- Recent practitioner discussion on coding-agent over-verification independently argues that revision/dependency-bound runtime evidence is safer than model-memory guesses about whether an old verification result remains valid.
- Direct task-specific Google Scholar retrieval returned no stable Scholar-native result in this run: `SCHOLAR_DIRECT_GAP`.

## Authority ceiling
D0 control-plane admission/routing proof only. No raw KV bytes are persisted by this worker; only an opaque runtime-owned handle and payload identity are bound. No native/private transformer KV access, provider/model execution, physical throughput/latency/energy claim, hosted PASS, merge/deploy authority, truth/effect authority, canonical K27 semantic authority, or Gate10.
