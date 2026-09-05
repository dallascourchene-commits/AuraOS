# AGENT_07 — Workload-Qualified Cost Receipt V1

Exact foreign rebase parents:
1. F27 Exact Cumulative Energy O3 — exact cumulative state is integer transferred bytes; derive Decimal energy at admission/report boundaries, never float-round-trip cumulative spend.
2. AGENT_06 Workload Contamination Admission Gate V1 — exact-prefix collisions across distinct ranking categories invalidate cache-policy ranking; intentional shared-prefix controls must be explicit and non-ranking.

New keeper:

`EfficiencyCredit => ExactCumulativeCost ∧ WorkloadRankingEligible ∧ ExactSource/Envelope ∧ D0`

This worker binds workload qualification and transfer accounting into one tamper-evident receipt. It does not claim physical GLM/Qwen energy, model throughput, merge/deploy authority, native/private KV truth, or Gate10.
