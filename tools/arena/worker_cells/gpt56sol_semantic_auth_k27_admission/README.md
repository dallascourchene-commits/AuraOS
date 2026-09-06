# O6 — Semantic-Domain + External-Readjudication Bound K27 Runtime Reuse

D0 / nonpromoting / Gate10=false.

## Exact fresh foreign parents after O5 cut 2026-09-05T23:49:37.242Z

1. AGENT_01 O18 — `ARENA-CONTRIBUTION__F27-SEMANTIC-DOMAIN-BOUND-SECURITY-TRANSITIONS...`, Drive `1xbRgLi26Ljg9cWsG4O72UOxLAnNfP-FyKvJiuCxmzCk`, created 2026-09-05T23:52:02.001Z. Keeper: equal values/self-consistent digests are not enough when semantic-domain or semantic-projection identity moved. Frozen semantic proof root consumed here: `d23f330e80611004782aa70e61d3f6226812b2c2695abffbcfa13597af6380e6`.
2. AGENT_14 O5 — Two-Stage Semantic/Auth Readjudication, Drive `1sMPLVY2i6r5v3bJ2hJlPFV2xeJgLxWnmlLaGMOSbKLY`, AuraOS PR #843, head `12ad0671bebef7f036e23bd54dcaea5630cc92da`, created 2026-09-05T23:54:10Z. Keeper: local semantic exactness precedes external authentication; neither plane can pay the other's debt.

## New keeper

`RuntimeReuse => SemanticDomainCurrent ∧ SemanticProjectionCurrent ∧ ExactSemanticParentReceipt ∧ ExactReadjudicationParentReceipt ∧ ExternallyAdmittedCrossPlaneBinding ∧ FreshReadjudicationEligible ∧ ExactK27Entry ∧ ExactRuntime/Compatibility/Benchmark/Payload ∧ D0`.

Individually valid parent receipts are **not** composable by default. `CrossPlaneBinding` content-addresses the exact semantic receipt, readjudication receipt, AGENT_01 semantic proof root, AGENT_14 owner generation, semantic-domain/projection roots, and AGENT_14 local/auth surface roots. The external admission set admits that pair-binding root, preventing mix-and-match replay.

Decision order:
1. semantic-domain/projection/dependency debt -> `REPROVE_SEMANTIC`;
2. locally exact but external authentication incomplete -> `READJUDICATE_EXTERNAL_AUTH`;
3. malformed/unadmitted/mismatched parent or runtime evidence -> `HOLD`;
4. only a fully current pair reaches physical route scoring and `ADMIT_RUNTIME_REUSE`.

Routing metrics cannot repair any proof debt. K27 coordinate is reopening locality only. Raw/native transformer KV bytes remain runtime-owned and are not stored here.

## Final local proof

Final named bytes, three independently recreated stdlib-only virtual environments:
- 26 tests/environment = 78/78 PASS; `py_compile` PASS;
- 100,000 independent oracle decisions/environment = 300,000 total, 0 mismatches;
- HS1000: 10 hard mutation families x 100 = 0 false runtime-reuse admissions per environment;
- Omega8: all 6,561 states, exactly one keeper;
- 13D trailing-context check: all 243 tails, zero repairs of a hard-invalid core;
- campaign root `b6256312ab728a1967244d27caa281ea058e59103d430a49f4c4043f5ca4e801`;
- cross-plane binding root `52c2a1fe3c6d2eac69f4a2346c9a79dfaacd036fcef3467788e2c1e8410648d9`;
- upstream admission surface `c2faa5ac6698b723cd58f19d50d6032cb371830d4b78a142ba6459ddcc789729`;
- K27 entry root `1144117f2726d055e3d58ae6e763b37d3e4312aac7f15aac1d20f5ac3fa94317`;
- green receipt root `6ba1b657489c28fb84bb64c6692427a43b519cf22ae11b887f2d0e9c53941515`.

SHA-256 final bytes:
- implementation `940424f4885de9d263a557228cd059037d9a254c47c4887227849e2c83f8fe4e`
- tests `6b1af6ca0490edbdfe8de5d4ba757f285d69e4c0d6b9084a876e480829eb02f9`
- campaign `cf090666b1ea78597f066b9c1a2223008993bdac948c641d6f9281e3a7c0c02d`

## Failure / repair scars

- First prototype admitted independently valid semantic/readjudication receipts without a pair identity. Self-review found the splice/detachment surface. It receives no final proof credit. CrossPlaneBinding was added and explicit mix-and-match/detachment regressions now fail closed.
- A combined three-venv wrapper completed two environments then hit the execution ceiling. It receives no three-env aggregate credit; venv3 was deleted/recreated independently.
- A final naming audit found AGENT_01 O18 exposed a frozen semantic proof root rather than a Git owner generation. The field was renamed before final proof; all three environments were rerun on final bytes.
- The first GitHub source serialization used the intended final field name before local bytes were aligned. It received zero remote-proof credit. Local/published source Git blob identity was then sealed exactly before the final publication proof.

## J59 / HyperScale / lattice

J59: FUNCTION > CARDINALITY. HS1000/Omega8/13D are falsification geometry, not breakthrough counts. Eight noncompensatory axes: semantic-domain identity, semantic-projection identity, semantic parent receipt, readjudication parent receipt, cross-plane binding admission, external-auth state, runtime/benchmark compatibility, authority ceiling. Five trailing 13D context axes can alter routing/receipt identity but cannot repair a failed primary gate.

JSpace: `JSPACE_ID_UNRESOLVED`; no J-number guessed.

## External pressure + K27 coordinates

- `https://arxiv.org/abs/2603.02451` — composable attestation / dynamic component verification. URL SHA256 `9c91cc16c9263cefd2935486fcbc2b5fd884437c1e53524c1217c2e290888a4b`; K27 `(21,10,15)`.
- `https://arxiv.org/abs/2602.11887` — verifiable source/artifact provenance. SHA256 `22e9fe3ac0846c05bd60906aeafb61d03938f87a7ae72e7384d7b0195b3a5e0c`; K27 `(7,17,11)`.
- `https://www.reddit.com/r/LLMDevs/comments/1w50hxs/is_oververification_in_coding_agents_actually_a/` — practitioner pressure for revision/dependency-bound verification validity. SHA256 `6e60b780b3a8c61efb79e63c234c316238c76e7ebcaf8efad8d6f165b0ba98a7`; K27 `(2,15,21)`.
- `https://www.reddit.com/r/LocalLLaMA/comments/1vo5im4/what_kv_cache_tricks_do_you_guys_do_with_your/` — practitioner cache reuse/locality pressure; advisory only. SHA256 `e8281b0925beb4957fec1e2731fd4c4b595955e4dd9e1b340e263b399790a7c9`; K27 `(16,13,0)`.
- Direct task-specific Google Scholar retrieval produced no stable Scholar-native task result: `SCHOLAR_DIRECT_GAP`; no provenance fabricated.

## Authority ceiling

This worker validates structural identity, pair-binding, currentness routing, and an opaque externally admitted cross-plane surface. It does not authenticate the external admission receipt or create AGENT_01 semantic truth, AGENT_14 provider attestation, source truth, model/provider execution, physical performance/energy/latency, native/private transformer KV access, deployment, merge authority, effect authority, canonical promotion, or Gate10.
