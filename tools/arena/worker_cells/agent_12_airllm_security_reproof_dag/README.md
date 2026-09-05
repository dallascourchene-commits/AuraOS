# AGENT_12 — AirLLM Security Reproof DAG

D0-only composition worker. It combines the AirLLM fail-closed security lane (PR #835) with dependency-scoped evidence recomputation (PR #836) without reimplementing either owner.

Keeper law:

`SecurityReproof(changed) = smallest dependency-closed cone over the fixed AirLLM security graph`.

`ReusableSecurityWitness => OutsideCone AND ExactCurrentOutput AND ExactDependencyInputBinding AND ExpectedVerifierRoot AND ExactParentGenerations AND CanonicalGraph AND D0`.

The fixed graph prevents a caller from deleting a hard dependency to make a plan look smaller. Changes to model bytes reopen model allowlisting + Safetensors structure + secure entrypoint + receipts. Package-source changes reopen remote-code policy and the secure entrypoint. Trace/workload changes reopen only the reuse lane when the underlying security receipt remains exact.

Final local proof on final bytes: 26 tests × 3 fresh stdlib-only virtual environments = 78/78 PASS; 300,000 randomized dependency-closure oracle decisions with 0 mismatches; HS1000 0/3,000 false admissions; Ω8 all 6,561 states with exactly one keeper; 300,000 unique sampled 13D states with 0 hard-invalid repairs. Stable campaign root `64a7fd367e5b75dfa17aeab9164932e1bf68d48aba04a631931b1cd0fb7f5a0f`. Random one/two-root changes averaged 36.7733846154% of full 13-node security-graph recomputation.

Failed-first scars receive zero proof credit: the first unit oracle expected eight nodes for a seven-node union closure; the first HS1000 definition treated a tampered witness inside its own recomputation cone as a false admission. Both test/campaign definitions were corrected without changing production semantics, and all credited virtual environments were recreated afterward.

No physical model execution, provider truth, hosted PASS, deployment, effect authority, private/native transformer KV, or Gate10 is claimed.
