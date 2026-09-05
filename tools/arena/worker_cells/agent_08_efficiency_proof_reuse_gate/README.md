# AGENT_08 — Workload-Qualified Efficiency Proof Reuse V2

Independent D0 verifier/composition membrane over AGENT_27 trace/resource proof-reuse semantics and AGENT_07 workload-qualified exact-cost semantics.

This version removes caller-authored `verified/current/receipt_valid` booleans from the admission basis. It independently recomputes the consequence-bearing parent projections from raw evidence, pins the exact parent semantic commits and verifier source blobs, pins the current base source generation, recomputes contamination/cost/transfer/budget invariants, and compares current projection roots to the proof-time roots. Any mismatch returns `REPROVE`.

Keeper: `ReusableEfficiencyProof => IndependentlyRecomputedTraceProofProjectionExact AND IndependentlyRecomputedQualifiedCostProjectionExact AND RecordedProjectionRootsCurrent AND D0`.

The 13D context is now hashed into each decision receipt; different tails produce different context roots while remaining unable to repair a failed hard axis.

No model/provider execution, physical performance, hosted PASS, truth/effect authority, merge/deploy, private/native transformer KV, or Gate10.
