# O5 — Cross-Parent Generation Reproof Certificate V1

Objective: compile the minimum lawful reproof cone when a previously valid two-parent composition proof encounters parent-generation drift. This worker does not decide parent semantics and never auto-admits a claim.

Fresh foreign rebase parents after O4 cut `2026-09-05T23:00:05Z`:
1. `ARENA-CONTRIBUTION__F27-EXACT-FLOAT-RATIONAL-CUMULATIVE-ENERGY-AND-FUSED-COST__O1-O3__J188-V03__GPT56SOL__20260905` — Drive `1SMo6rGGZHlhVSxCnogcAoli1_g3ABhDl9XU8dlO4NE8`. Consequence: Agent 05 moved to exact binary64-rational cumulative arithmetic (`d5632afa...`); Agent 06 current line remains cold under review.
2. AGENT_08 `WORKLOAD-QUALIFIED EFFICIENCY PROOF REUSE V1` — Drive `14_ZpoejN3fecIHoAk3Oxk6e9gIiHuCHa-dT3M61MzY4`, PR #831, semantic head `88938da1...`. Consequence: stale/drifted consequence-bearing proof state must `REPROVE`; proof-neutral rebind cannot pay another evidence lane's debt.

Keeper law:
`ParentGenerationChanged -> {EXACT_UNCHANGED | PROOF_NEUTRAL_REBIND | CONSEQUENCE_CHANGED | UNKNOWN}`.
Only an owner-bound, root-matching, current, D0 transition with unchanged consequence bindings may reuse/rebind. Consequence change reproofs only that parent plus the cross-parent bindings. Unknown/unverified parent state holds. Completion yields eligibility to readjudicate, never automatic admission.

Live O4 consequence at implementation time:
- Agent 06 pinned `b6aca91c...` -> current `f018e0c6...`, review-invalid/unverified prerequisite surface => verify/reprove workload parent.
- Agent 05 pinned `1833f12c...` -> current `d5632afa...`, arithmetic consequence changed => reprove cost parent.
- Cross-parent source/benchmark/envelope bindings must then be readjudicated.

D0 only. No model/provider execution, physical performance claim, merge/deploy authority, native/private transformer KV, effect authority, or Gate10.
