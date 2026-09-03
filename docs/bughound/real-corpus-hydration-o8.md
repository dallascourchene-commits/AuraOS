# BugHound Real-Corpus Hydration & Blind Benchmark Registry — O8

Status: D0 / local benchmark infrastructure / nonpromoting / no live-target authority.

This package closes the `AUTHORIZED_REAL_CORPUS` reopening seam from the BugHound Cash-Fidelity O1–O7 decommission. It does **not** run against deployed bounty targets. It creates a source-bound corpus registry and contamination firewall so established disclosed-vulnerability datasets can be hydrated progressively from L0 to L4 without leaking evaluator truth into the BugHound solver.

## L0 → L4

- **L0 Source identity:** canonical dataset URL, source generation, license/provenance handle, SHA-256, K27 lookup coordinate.
- **L1 Case index:** opaque case ID, repository/language/CVE/GHSA/CWE/severity metadata.
- **L2 Semantic representation:** vulnerable snapshot handle, root-cause abstraction, changed file/function metadata. Training corpora may expose patch-derived semantics; blind evaluators do not expose them to the solver.
- **L3 Causal representation:** entrypoint/critical-operation/dependency-trace schema. Gold trace annotations remain evaluator-only on blind corpora.
- **L4 Executable oracle:** local isolated reproduction handle plus vulnerable/fixed counterfactual and independent replay. Raw PoC/trigger/oracle internals stay outside reusable solver memory.

## Corpus roles

Training/hydration: NIST Juliet C/C++, CVEfixes, PrimeVul.

Blind real-world evaluation: ARVO, VulnGym, Cisco Vulnerability Localization Benchmark, Magma, Vul4J, SEC-bench (repository-only/local-isolated detection profile).

Different-J diagnostic: Snyk VulnBench JS for repeatability/reference agreement. It is intentionally *not* treated as independent universal ground truth.

## Benchmark score vector

Do not collapse the result into one flattering accuracy number. Preserve:
- independently supported discovery precision/recall/F1;
- patched/clean false positives;
- repository file-localization F1;
- causal-trace coverage;
- L4 reproduction + patched-counterfactual specificity;
- repeated-run stability;
- tool calls, tokens and elapsed time.

`KnownBugLabel != CandidatePerformance`. A case counts as an L4 verified discovery only when BugHound independently identifies it, local reproduction succeeds, the patched/negative counterfactual is clean, and the evaluator evidence is independently bound.

## City/tool routing

- Athens / Research Archives: corpus source identity, indexing, dedupe, currentness.
- Geneva / Embassy: source/license/schema/provenance customs.
- San Francisco / Engineering: AST/CFG/call/dataflow/localization and patch-diff tools (patch hidden during blind evaluation).
- Detroit / Workshop: isolated local build/test/fuzz/reproduction only for benchmark-owned public artifacts.
- Federal Capital: benchmark policy, split integrity, sealed evaluator truth, scoring.
- New York / Commerce: repeatability/resource economics only; no private bounty-duplicate or payout inference.

## Keeper laws

`TrainingHydration != BlindEvaluationTruth`.
`PatchOrPoCVisibleToSolver => EvaluationContaminated`.
`Localization != CausalTrace != Reproduction`.
`ReproductionOnVulnerable != CounterfactualSpecificityUntilPatchedNegativeIsClean`.
`ReferenceAgreement != IndependentGroundTruth`.
`SyntheticCoverage != RealWorldGeneralization`.
`K27Coordinate != SourceIdentity != Truth != Currentness != Authority`.
`BenchmarkPass != LiveTargetAuthorization != SubmissionAuthority != Payout`.
`ReusableMemory != TargetSpecificUndisclosedExploitInstructions`.
