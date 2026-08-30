# AWJ032-GLM53-05A — Pager Evidence Guard Repair Receipt

Status: DRAFT / NONPROMOTING / D0 ONLY

Source LASER: Drive `1M9yGx3C3NKpFvyMrOl3ZRMmtKRdzdEAG_VWagCMgTkQ`.
Work order: Drive `1ez7Z-n4On3nbmdltn-_JlZOHh4LpRoIFNX8tIz1iiIM`.
Base pager owner observed: PR #338 head `e41be7118431af56c865a1a5ec54d92e74e6a49e`.
Independent sibling used for reduction: PR #336 bounded-cache/logical-vs-physical evidence contract.

This child intentionally repairs only the packed-pager safety/evidence seam before any cache merger or real checkpoint effect.

Changes:
- copy/freeze caller-owned tensor/scale mappings after validation;
- reject a single call selecting the complete expert bank before backend reads;
- preserve all-expert addressability across repeated bounded calls;
- report physical bytes/read-operations/whole-tensor reads as `UNKNOWN` for an abstract backend unless it returns explicit read evidence;
- preserve explicit backend attestation as evidence rather than inferring physical behavior from `read_rows` API naming;
- add hostile-backend regression proving an internally whole-reading backend cannot yield a false zero;
- keep `g2_admitted=false` and synthetic-only claim ceiling.

Not closed by this child:
- bounded byte-budget LRU convergence from PR #336 into the single pager owner;
- telemetry parity for the per-expert pager;
- exact GLM-5.3 index/header/FP8 evidence;
- real model weights, native inference, host execution, G2, main merge, or Gate-10.

Exact-head CI is required before this child can be treated as a synthetic repair PASS.
