# AWJ032 GLM-5.3 G6 — Gate-10 Owner-Host Evidence Request Envelope

Date: 2026-09-01  
Status: DRAFT / D0 / HS1 / NONPROMOTING / W3-REBASED / IDENTITY-W3-ABSORBED

## Objective

Compile one deterministic, nonexecuting owner-host evidence request only after the exact GLM-5.3 bounded-C2 admission has been revalidated at use time, while carrying operation/observer/backend provenance requirements and every unpaid Gate-10 debt.

Positive output is only:

`OWNER_HOST_BOUNDED_C2_EVIDENCE_REQUEST_ENVELOPE_COMPILED`.

## Exactly two terminal semantic parents

1. **PR #769 generation-bound admission reuse**
   - exact hosted proof head `d1a0f94255527835a59a70a0af7dc417ba1d023d`
   - source/test blobs `d171d0938e469a4383490d1a691750c2068f21e7` / `58fad37a0f89853098fa3dbbe2f2a1771574e449`
   - run/job `33437612722 / 99637780915`, SUCCESS
   - law: `AdmissionValidAtProduce != AdmissionReusableAtUse`.
2. **PR #727 operation-bound observation provenance**
   - exact hosted head `293c59d7260372ccd3b9e8130b12979b052c3ed9`
   - source blob `98db548b6e8f7443b79d979eb0e177ac6aa68534`
   - run/job `33416248604 / 99567478616`, SUCCESS
   - law: structural/caller evidence cannot manufacture physical observation truth.

Historical G6-v1 / PR #777 used superseded G5-v1 / PR #766 and receives zero closure or successor credit.

## Transitive Q18 lineage — zero additional parent credit

PR #769 inherits the GLM bounded-C2 proposal from Q18 / PR #761. G6 therefore authenticates Q18 as lineage, not as a third Objective parent:

- semantic head `aed81432db8b84d2f43b8a85d06d4b72e16f6a50`
- source blob `4cee26edaf0759fc80d31889ab9e4e268f9a4fbe`
- hosted run/job `33436580962 / 99634379758`, SUCCESS
- exact historical Q18 receipt `c53acb3ff471dbe3971ee4e7a75b28c4316b50fba88a414f406b93c271c90230`

`Q18ReceiptIdentityInheritedThroughPR769Lineage`.

## W3 corrections absorbed into the canonical owner

The canonical owner is now schema `AURA-GLM53-G6-GATE10-OWNER-HOST-EVIDENCE-REQUEST-v4`.

Two independent W3 scans found that a generic reuse summary was insufficient. The final compiler directly requires:

- exact family `GLM53_BOUNDED_C2_PROPOSAL`;
- exact `REUSE_CANDIDATE` disposition;
- current-use context;
- exact Q18 historical admission receipt;
- PR #769's deterministic reuse-digest relation;
- full subject/source/evidence/owner/decision identity vector;
- exact flagship source request identity;
- operation/observer/backend provenance gates;
- owner-host resource/evidence/replay contracts;
- all open Gate-10 debt.

A digest that merely has 64-hex shape is insufficient. A stale identity field with an old reuse digest is a HOLD. A same-family but different GLM admission receipt is a HOLD.

The former `glm53_g6_admission_identity_binding_addendum.py` is now a compatibility/provenance tombstone with zero closure credit. The former identity-binding workflow is manual compatibility-only. There is one semantic owner and one closure workflow.

`SingleOwnerCompilerEliminatesPostHocIdentityJoin`.

## Reachable source HOLD

The first G6-v2 cut represented a source HOLD in the abstract 512-state proof but hardcoded source truth in the executable path. That mismatch is repaired by an explicit `SourceIdentityProjection`.

Repository, pinned revision, source-set digest, or revision-revalidation mismatch now reaches `HOLD_EXACT_FLAGSHIP_SOURCE_IDENTITY_REQUIRED`, and a held receipt suppresses the unaccepted source identity.

`SourceRequestIdentity != SourceCurrentnessTruth`.

## Canonical downstream return owners

No new return protocol is created.

- **PR #582** exact hosted generation `24a5404ee3b987dee12192917e40b35d3a43e81c`, source blob `91da9f6f5c9c8175fbe123634e53e14bc9ba3cbe`, run `33360061584`, SUCCESS. Owns `OwnerHostC2CanaryRequest -> OwnerHostC2CanaryReceipt -> join_owner_host_c2_attempt`.
- **PR #586** exact hosted generation `aa3fcd9a4cefd18dbc991c3e8a450fcfbbb6726b`, source blob `8e57494c1c77eb41d6a402aa7dceb43121512863`, run `33360529366`, SUCCESS. Owns the nonmetric lifecycle-return membrane toward W4.

These are compatibility/transport owners, not additional G6 derivation parents.

`CanonicalC2ReturnPath != ProducerAuthentication`.

## Proof surfaces

Canonical workflow: `Aura GLM53 G6 Gate10 Owner Host Evidence Request`.

It authenticates:

- exact PR #769 and PR #727 source/proof generations;
- exact transitive Q18 source/run/job;
- exact PR #582 and PR #586 return-owner generations;
- canonical G6 module/test syntax and adversarials;
- `2^9 = 512` request-precondition Different-J states;
- `2^5 = 32` ordered reuse-identity Different-J states;
- single-owner and nonpromotion laws.

No G6 closure or successor credit exists until this workflow is SUCCESS on the exact current head.

## Required future evidence axes

- `OFFICIAL_SOURCE_REVISION_REVALIDATION`
- `TENSOR_PAYLOAD_BINDING`
- `REAL_TENSOR_QUANTIZATION`
- `EXACT_OPERATION_IDENTITY`
- `OBSERVER_BACKEND_PROVENANCE`
- `OWNER_HOST_RUNTIME_GENERATIONS`
- `PHYSICAL_IO_METRICS`
- `OUTPUT_AND_RECEIPT_HASHES`
- `REPLAY_RECEIPT`
- `RECOVERY_RECEIPT`

## Open Gate-10 debt

- `FULL_FLAGSHIP_MODEL_LOAD`
- `AURAOS_RESIDENT_ROUTING`
- `OWNER_HOST_END_TO_END_EXECUTION`
- `AUTHENTICATED_PHYSICAL_OBSERVATION`
- `REPLAY_RECOVERY_PROOF`
- `GATE10_SYNTHESIS_AND_PROMOTION`

`UnresolvedOwnerHostEvidenceDebt => FanoutBudgetForGate10Claim = 0`.

## HyperDrive

`EXACT_Q18_PR769_REUSE_IDENTITY`
`+ OPERATION_PROVENANCE_CONTRACT`
`+ EXACT_SOURCE_REQUEST_IDENTITY`
`-> SINGLE_OWNER_G6_REQUEST`
`-> FUTURE PR582 REQUEST/RECEIPT/JOIN`
`-> FUTURE PR586 LIFECYCLE RETURN`
`-> INDEPENDENT PRODUCER/OBSERVER/LIFECYCLE AUTHENTICATION`
`-> REPLAY/RECOVERY + AURAOS RESIDENT ROUTING`
`-> GATE10 SYNTHESIS`.

## Laws

`AdmissionValidAtProduce != AdmissionReusableAtUse`.

`ReuseCandidateSummary != AdmissionReuseReceiptIdentity`.

`ExactQ18AdmissionReceiptMustRemainBound`.

`DigestShape != DigestRelationProof`.

`PR769ReuseDigestMustCommitExactIdentityVector`.

`SingleOwnerCompilerEliminatesPostHocIdentityJoin`.

`IdentityBinding != ReceiptProducerAuthentication != SourceCurrentnessTruth`.

`CallerWitness != BackendObservationProvenance`.

`RequestEnvelopeCompiled != TensorPayloadBound != ExecutionObserved`.

`CanonicalC2ReturnPath != ProducerAuthentication`.

`Gate10DebtMustRemainExplicitUntilObserved`.

`K27Coordinate != SemanticIdentity != RuntimeTruth != Authority`.

`CoordinateMemory != MODEL_PREFIX_KV`.

## Claim ceiling

No reuse-receipt producer authentication, source-currentness truth, tensor payload binding, real quantization/model/provider execution, full flagship load, physical-I/O truth, observer/backend authentication, AuraOS resident routing, replay/recovery proof, execution/effect authority, semantic K27 authority, native/private transformer KV, Gate-10 promotion, merge/deploy/spend or public/financial/human effect is granted.