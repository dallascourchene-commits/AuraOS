# BugHound O10 — Historical Blind Cut

D0 benchmark infrastructure only. No live target testing or external-effect authority.

## Purpose
Evaluate whether BugHound can rediscover already-known vulnerabilities using only evidence that was public/available at a declared historical `as_of` cut. Knowledge recorded after the cut remains evaluator-only and cannot retroactively become solver evidence.

## Foreign rebase parents
1. Aura World / Memory City Bitemporal Civic Provenance Projector O4: `ValidTime != ObservationTime`; later-recorded history must not rewrite an earlier as-known state.
2. J67/V01 Counterfactual Consequence Separability: source-resolvable states may be compressed together only while no lawful future perturbation can distinguish their consequence sets; vulnerable and fixed/history states remain separable when they change evaluation consequences.

## Real calibration case
VulnGym v0.1.4 example `entry-00057` identifies Open WebUI vulnerable commit `9942de8011d4b5a141ac507c974c061c0cdad59a`. GitHub records that commit at 2025-10-21T21:03:04Z. The corresponding advisory is treated as published at 2025-11-07T15:25:23Z. Therefore an as-of cut such as 2025-11-01 may expose the vulnerable source while sealing later advisory/label/trace/fix/oracle truth.

The solver packet never includes GHSA/CVE IDs, vulnerability title/category, entry-point gold, critical-operation gold, trace gold, fix, patch, PoC, oracle, or expected-finding truth. The evaluator seal binds those classes by digest only.

## Split law
A chronological cut is necessary but not sufficient. Training/validation and test sets must also be repository/group-disjoint. This addresses project-distribution leakage and false transfer confidence.

## Core laws
- `SourceCommitTime != AdvisoryObservationTime`.
- `LaterPublishedAdvisory != EarlierAsOfKnowledge`.
- `KnownToday != SolverVisibleAtHistoricalCut`.
- `VulnerableSnapshotVisible != VulnerabilityLabelVisible`.
- `EvaluatorGoldAfterCut != SolverEvidence`.
- `TemporalSplit != RepositoryGeneralization`.
- `HistoricalBlindPass != ZeroDayDiscovery`.
- `HistoricalBlindBenchmark != LiveTargetAuthorization`.
