# AWJ032 GLM-5.3 G6 W3 — Internal Identity Join Correction

Date: 2026-08-31  
Status: DRAFT / D0 / HS1 / NONPROMOTING / SUPERSEDES POST-HOC BINDING SHAPE

## Correction

The first identity-binding addendum correctly preserved PR #769's seven consequence-bearing identity fields, but its API still accepted:

`base_request + reuse_identity`.

That is insufficient because the base G6 receipt does not carry the reuse identity needed to prove that the two independently supplied objects belong together.

Therefore:

`CallerSuppliedBaseRequest + IndependentExactIdentity != JoinedRequestIdentity`.

A later binding hash cannot manufacture a relation that the inputs did not establish.

## Current W3 API

The only public construction path is:

`compile_identity_bound_g6_request(reuse_identity, provenance, owner, evidence)`.

Order:

1. validate exact PR #769 proof coordinates;
2. require exact family `GLM53_BOUNDED_C2_PROPOSAL`;
3. require `REUSE_CANDIDATE` and candidate-only claim ceiling;
4. validate the full identity vector:
   - admission receipt digest;
   - reuse digest;
   - subject identity;
   - source generation;
   - evidence generation;
   - owner context;
   - decision context;
5. construct the weaker PR #782 base reuse projection **inside** the membrane;
6. compile the base G6 request internally from provenance/owner/evidence inputs;
7. require the base request to be compiled and nonpromoting;
8. bind the internally constructed base request digest to the exact PR #769 identity vector;
9. return only `IDENTITY_BOUND_EXTERNAL_AUTH_REQUIRED`.

There is no public `base_request` parameter and no public `bind_g6_request_to_admission_identity` function.

## Hosted invariant

`Aura GLM53 G6 Admission Identity Binding W3` now asserts:

- public parameters are exactly `reuse_identity, provenance, owner, evidence`;
- `base_request` is absent;
- the unsafe public precompiled binder is absent;
- #782 base G6 source/test blobs remain pinned;
- #769/#727 exact terminal proofs and blobs revalidate;
- base G6 adversarials and W3 adversarials pass;
- 512-state base + 16-state W3 summary lattices pass;
- anti-cross-cast and nonpromotion laws remain present.

Current correction commits:

- module: `b9c84d3e9c8f90655c7814a79355b72e81d00caa`
- tests: `b0162fb19b68f4b07e9bd0f4afbfedee5c543e57`
- workflow: `87ddd289f6d4fe996ef61bce4c1667b87e9dfa4e`

Exact hosted SUCCESS on the current head is still required before Objective-2 closure.

## Triadic / Omega-8 refinement

- **Thesis:** exact PR #769 identity can disambiguate the G6 reuse candidate.
- **Counterplane:** post-hoc pairing of two caller-supplied objects does not prove their join.
- **Synthesis:** validate exact identity first, construct base request internally, then bind one internally generated request to that identity.
- **W3 contradiction:** `IndependentTruths != ProvenRelation`.
- **W4 factorization:** identity preservation, producer authentication, source currentness, request construction, execution and physical observation remain distinct.
- **W7:** any identity/generation change requires reconstruction; an old base request cannot be relabeled current by attaching a new identity.
- **W8:** effect authority remains unearned.

## Laws

`ReuseCandidateSummary != AdmissionReuseReceiptIdentity`.

`CallerSuppliedBaseRequest + IndependentIdentity != JoinedRequestIdentity`.

`IdentityBoundWrapperMustConstructBaseRequest`.

`IdentityBinding != ReceiptProducerAuthentication != SourceCurrentnessTruth`.

`RequestEnvelopeCompiled != TensorPayloadBound != ExecutionObserved`.

`CoordinateMemory != MODEL_PREFIX_KV`.

## Claim ceiling

No reuse-receipt producer authentication, source-currentness truth, owner authentication, tensor binding, model/provider execution, physical I/O, observer/backend authentication, AuraOS resident routing, replay/recovery proof, execution/effect authority, semantic K27 authority, native/private transformer KV state, Gate-10 promotion, merge/deploy/spend or public/financial/human effect is granted.
