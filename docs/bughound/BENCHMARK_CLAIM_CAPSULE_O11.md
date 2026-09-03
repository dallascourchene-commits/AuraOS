# BugHound O11 — Benchmark Claim Capsule / Superiority Gate

A performance claim is an evidence object, not prose.

O11 binds challenger and baseline results to the same corpus generation, benchmark semantic root, historical cut, split, exact case set, evaluator generation, tool policy and resource budget. Every run must be contamination-free, repository-group-disjoint, historical-blind, completed, and exact-head provider verified.

Quality axes are kept separate: precision, recall, localization F1, causal-trace coverage, reproduction rate, patched specificity and repeatability. Resource axes are tool calls, tokens and elapsed time.

A scoped superiority receipt is conservative: the challenger's lower interval bound must exceed every baseline upper bound on every declared quality axis, and its resource upper bound must be no worse than every baseline on each resource axis. Otherwise the claim remains HOLD. The receipt always fixes `generalized_real_world_superiority=false`; benchmark superiority never self-promotes into live-world superiority or bounty authority.

Keeper laws:
- `BenchmarkScore != BenchmarkClaim`.
- `MatchedCaseSet + DifferentBudget != FairComparison`.
- `HistoricalBlind != RepositoryGeneralization` unless group separation is also proven.
- `ProviderGreenOldHead != CurrentRunProof`.
- `PointEstimateDominance != IntervalDominance`.
- `ScopedBenchmarkSuperiority != GeneralizedRealWorldSuperiority`.
- `ComparisonReceipt != LiveTargetAuthority != SubmissionAuthority != CashPaid`.
