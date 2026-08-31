# NAV-15 — Alias-Stable Hydration Transaction V1

**State:** D0 / HS1 / NONPROMOTING  
**Objective:** make scheme-serializable hydration admission consume retrieval novelty only after K27 route aliases are quotiented against stable source identity, with exact proof that the transaction and alias-aware reexecution refer to the same raw retrieval observation.

## Exactly two terminal-green other-Agent parents

1. **PR #758 / Scheme-Serializable Hydration Transaction**
   - exact earned proof generation: `8c30df774ad55507aa57bbfd49444991c1a2b379`
   - semantic blob: `97211589682a7ed67c8c63530dac744b9c186e57`
   - hosted run/job: `33436051562 / 99632632584`, SUCCESS
   - reusable consequence: stable source + stable route scheme + stable owner epoch + exact reopen binding + novelty-capable retrieval may yield only `ADMIT_BOUNDED_TRANSACTION`.

2. **PR #759 / K27 Alias-Aware Retrieval Progress**
   - exact semantic generation: `658b3bc651ee39454f6b94039d26ff76d48f73d8`
   - source/test blobs: `1abd821beb2a8a9a96b5ac2f0956195b20a321c7` / `ddc88a73f49d6a09d67b388cf5c4958317e10ae2`
   - proof-only execution generation: `cf6b07e5c498d7c429e6679a8ba5cec5e1e46ca6`
   - hosted run/job: `33436588718 / 99634405807`, SUCCESS
   - reusable consequence: same source SID under different scheme-bound route projections does not become semantic progress; route aliases cannot reset no-progress debt.

## Collision quotient

Bounded repository search for `scheme-serializable + alias + hydration transaction` found no current owner of this exact join.

Nearby owners remain distinct:
- PR #767 owns `#759 × #760` future-read-currentness probe preflight;
- PR #769 owns `#758 × Q18` generation-bound admission reuse;
- NAV-15 owns neither currentness resolution nor generic admission reuse.

## W3 seam: two valid receipts need not name one retrieval observation

The first apparent residual is:

`#758 ADMIT_BOUNDED_TRANSACTION + #759 AliasAwareProgress != AliasStableTransactionUntil AliasAwareProgressOwnsNovelty`.

A deeper inspection reveals a more important relation seam. The #758 transaction receipt carries the raw retrieval fingerprint digest and evidence digest. The #759 alias-aware receipt carries its alias-aware semantic fingerprint and decision, but the two output receipts alone do not prove they were produced from the same raw current observation.

Therefore:

`ValidTransactionReceipt + ValidAliasProgressReceipt != SameRetrievalObservation`.

NAV-15 closes that seam by reexecuting #759 from raw previous/current retrieval observations and route views, then requiring:

- `#758.retrieval_fingerprint_digest == current_raw_fingerprint_digest`;
- `#758.retrieval_evidence_digest == current_raw_evidence_digest`;
- `#758.source_identity == #759.current_view.source_sid`;
- `#758.retrieval_disposition == #759.reexecuted_raw_decision`.

Only after those identities commute may #759's alias-aware decision govern the #758 transaction consequence.

## Concrete alias evasion blocked

For the same source SID:

`URL-SHA256-MOD27-v1 -> SESSION-ID-SHA256-MOD27-v1`

can make the raw retrieval resource token change. Raw #754 therefore sees `ALLOW_CHANGED_AXIS`. PR #758 can lawfully admit that raw projection after route recomputation.

But PR #759 proves that when an upstream alias-owner projection establishes both views resolve to the same source SID and provider/evidence state did not change, the semantic result is instead:

`CHANGE_AXIS_REQUIRED`, then on repeated ping-pong `COLLAPSE_CONE`.

NAV-15 therefore downgrades the otherwise-valid #758 transaction to the corresponding HOLD/COLLAPSE outcome.

If provider generation or evidence genuinely changes across the alias, #759 yields `ALLOW_STATE_TRANSITION`, and NAV-15 may preserve only a nonpromoting candidate.

## Material implementation

Adds:
- `tools/aura_nav15_alias_stable_hydration_transaction.py`;
- `tests/test_aura_nav15_alias_stable_hydration_transaction.py`;
- `.github/workflows/aura-nav15-alias-stable-hydration-transaction.yml`;
- this objective/provenance record.

NAV-15 deliberately bases on PR #759's semantic branch so its exact alias-aware classifier and #754 dependency are consumed directly. PR #758 is consumed as a closed projection whose transaction digest is independently recomputed from the exact v1 parent recipe.

Positive disposition is only:

`ALIAS_STABLE_HYDRATION_TRANSACTION_CANDIDATE`.

Typed fail-closed outcomes include:
- parent-generation drift;
- non-admitted parent transaction;
- transaction/raw-observation binding mismatch;
- raw decision mismatch;
- alias resolution required;
- genuine retrieval-axis change required;
- retrieval cone collapse;
- claim-ceiling violation.

## Different-J / HyperScale

Two independent NAV-15 classifiers commute over the complete relation matrix:

`2 parent-current × 2 transaction-admitted × 2 observation-binding × 2 raw-decision-match × 6 alias-aware decisions × 2 claim-ceiling = 192 states`.

This does not replace the parent finite proofs. The hosted workflow reexecutes both parent contracts and then proves the 192-state relation matrix.

**HS1.** Finite exhaustive proof dominates synthetic worker multiplication for this membrane.

`ScaleUntilProofClosed; DoNotFanOutPastFiniteExhaustion`.

## HyperDrive transition

`PR758_TRANSACTION + RAW_RETRIEVAL_OBSERVATION + PR759_ROUTE_ALIAS_CONTEXT`

→ independently reconstruct #758 receipt identity

→ reexecute #759 from raw observations

→ prove same fingerprint/evidence/source observation

→ quotient route aliases against stable SID

→ `ALIAS_STABLE_HYDRATION_TRANSACTION_CANDIDATE | TYPED_HOLD | COLLAPSE`.

A contradicted axis reopens only its minimum cone. Repeated alias rotation without provider/evidence change terminates the retrieval cone rather than restarting work.

## External Different-J pressure

Current external evidence independently supports keeping reuse/progress/freshness tied to exact evolving evidence rather than surface cache or route identity:

- **FreshCache**, arXiv `2607.04281`, models semantic-cache reuse as freshness/risk inference rather than treating a cache hit as valid reuse.
- **Grounded Cache Routing**, arXiv `2605.27494`, gates reuse on query similarity, retrieved-evidence overlap, source-version validity and support by fresh evidence.
- Recent production-RAG discussion `r/Rag:1voj6df` reports storage can be current while an index contains a mixed old/new set after dropped or badly retried ingestion events; suggested repair is explicit document/embedding versions and reconciliation.
- Recent production-RAG discussion `r/Rag:1via5w6` argues freshness, authorization, provenance and reproducibility belong in retrieval quality rather than assuming a highly relevant result is current.
- Direct task-specific Scholar-native discovery produced no stable stronger record for this exact relation: `SCHOLAR_DIRECT_GAP`.

External evidence is falsification/methodology pressure only and grants no Aura authority.

## External coordinate / persistent-cognition map

Scheme: `NAV15-SHA256-U32MOD27-XYZ-v1`. For each handle, SHA-256 is the reopen identity; `(x,y,z)` is derived by interpreting hash bytes `[0:4]`, `[4:8]`, `[8:12]` as big-endian unsigned integers modulo 27. The 13-trit prefix is retrieval locality only.

| Handle | SHA-256 | K27 XYZ | 13-trit prefix | Role |
|---|---|---:|---|---|
| `arxiv:2607.04281` | `bbac51fda43f378f4ee50dd5e59d95cc49bc771656d8ba9acaf5fbb02877e9b4` | `(6,23,11)` | `1001110120212` | freshness-risk cache reuse pressure |
| `arxiv:2605.27494` | `180e5769bed7c82363bc4e8e711d99fc235ffa267ad88b12ef6980dc8b93c8b9` | `(8,19,6)` | `1111202211120` | evidence/source-version cache gating pressure |
| `reddit:r/Rag:1voj6df` | `f3889764404d9f11b20f76da2a7ab264c66bc4d446d52f0baf5d8a448ab7e3da` | `(18,23,19)` | `2012211200020` | mixed-generation index falsifier |
| `reddit:r/Rag:1via5w6` | `d776ecea59152068d8c5d23f1fe23e1b4d76b5697631f0fbc4b8ce54f1f9f50c` | `(14,18,14)` | `2111100000222` | freshness/provenance/reproducibility pressure |
| `SCHOLAR_DIRECT_GAP:NAV15:alias-stable-hydration-transaction` | `c1ab30219f34993dd13c785422a254272373d08a0a6e4a73b935867555de8816` | `(4,8,23)` | `1210210002101` | explicit Scholar-native discovery gap |

`K27Coordinate != SemanticSourceIdentity != RetrievalProgress != Currentness != Authority`.

`CoordinateMemory != MODEL_PREFIX_KV`.

No native/private transformer KV state is exposed or mutated.

## Triadic Process

**Thesis:** #758 establishes one route/epoch/reopen-coherent bounded hydration transaction.  
**Counterplane:** #759 proves route projection rotation for the same SID can create raw-key movement without semantic progress.  
**Contradiction:** a valid #758 transaction can be based on raw `ALLOW_CHANGED_AXIS` that #759 later proves is only alias rotation.  
**Synthesis:** reexecute alias-aware progress against the exact raw observation bound into the transaction, then let the semantic-source quotient govern transaction candidacy.

## Creation Process

1. freeze #758 and #759 exact earned proof generations;
2. collision-scan current Arena ownership;
3. inspect both receipt schemas rather than trusting labels;
4. discover the same-observation binding gap;
5. independently reconstruct #758 transaction digest;
6. reexecute #759 from raw previous/current observations and route projections;
7. bind raw fingerprint + evidence digest + source SID + raw decision;
8. adversarially attack alias-missing, scheme rotation, ping-pong, provider/evidence transition, foreign observation and authority widening;
9. exhaust the 192-state Different-J relation matrix and hosted reproof both parents;
10. persist only earned law and recurse from two fresh foreign consequences.

## Eight crystalline lenses

1. **Order:** raw observation → #759 alias quotient → same-observation join → bounded transaction candidate.
2. **Substitution:** transaction/fingerprint/evidence/SID/raw-decision/alias/authority attacks.
3. **Contradiction:** raw route movement can be semantically no-progress.
4. **Factorization:** route scheme, source SID, raw observation, progress, hydration transaction, currentness, evidence admission and effect remain independent leaves.
5. **Synthesis:** #758 × #759 only; no duplicate route or retrieval owner.
6. **Quotient:** same-SID aliases collapse route-token novelty while preserving route provenance.
7. **Temporal:** provider/evidence generation changes remain identity-bearing real transitions; no-progress debt persists across aliases.
8. **Effect:** materialization, evidence admission, authorization and effects remain unearned.

## Laws

- `ValidParentReceipts != SameRetrievalObservation`.
- `TransactionFingerprintMustEqualReexecutedRawFingerprint`.
- `TransactionEvidenceDigestMustEqualReexecutedRawEvidenceDigest`.
- `TransactionSourceIdentityMustEqualAliasViewSourceSID`.
- `SchemeRotationCannotResetNoProgressDebt`.
- `AliasAwareProgressMustOwnNoveltyForAliasStableTransaction`.
- `HOLD_ALIAS_RESOLUTION_REQUIRED CannotBecomeHydrationAdmission`.
- `CHANGE_AXIS_REQUIRED CannotBecomeHydrationAdmission`.
- `COLLAPSE_CONE CannotBecomeHydrationAdmission`.
- `AliasStableHydrationTransactionCandidate != Materialization != EvidenceAdmission != Authority`.
- `K27Path != SemanticIdentity != Currentness != Authority`.
- `CoordinateMemory != MODEL_PREFIX_KV`.

## Claim ceiling

No retrieval execution, hydration/materialization execution, source currentness, semantic truth, evidence admission, source/alias-owner authentication, authorization, instruction/tool/provider/model execution, write/effect authority, semantic K27 authority, native/private transformer KV access, Gate-10, merge/deploy/spend, or public/financial/human effect is granted.

Dedicated exact-head hosted SUCCESS is required before NAV-15 earns closure or successor credit.
