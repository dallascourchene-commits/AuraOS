# AGENT_01 — Contamination-Bound Fused Cost Adjudicator V1

O4 composition membrane over exactly two foreign parent proof surfaces:

- AGENT_06 Workload Contamination Gate (`b6aca91ce25589cf581c46e4582194529ed90dda`)
- AGENT_05 Fused Route Cost Receipt (`1833f12c31e89c498235f3a6b5806b8e08036224`)

The cell does **not** reimplement either parent verifier. It accepts root-bound parent attestations produced after parent verification and grants only D0 comparative cost-ranking eligibility when both parents are verified/current/ready and the cross-parent source identity, benchmark generation, and envelope identity are exact matches.

Integrated benchmark construction must bind the Agent 06 `WorkloadBatch.envelope_root` to the canonical Agent 05 `envelope_id`; the adapter treats a mismatch as non-comparable rather than creating a third envelope authority.

No policy winner, physical performance truth, effect authority, merge/deploy authority, provider/model execution, native/private transformer KV access, or Gate10 is granted.

## Re-entry requirement

The standalone AGENT_06 fixture uses symbolic `source_generation` / opaque envelope labels, while AGENT_05 binds a concrete Git `source_head` and canonical `envelope_id`. Those historical O1 receipts are valid rebase parents but are **not** directly promoted into comparative ranking. An integrated run must re-issue the workload-contamination proof with `source_generation == cost.source_head`, `benchmark_generation == cost.benchmark_generation`, and `WorkloadBatch.envelope_root == cost.envelope_id`.
