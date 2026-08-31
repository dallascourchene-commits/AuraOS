# AWJ032 GLM-5.3 G6 W3 — Admission-Reuse Identity Binding

Date: 2026-08-31  
Status: DRAFT / D0 / HS1 / NONPROMOTING / STACKED ON PR #782

## Objective

Close the smallest consequence-bearing projection gap in the current G6 owner-host Gate-10 request:

`CurrentReuseCandidateSummary != ExactAdmissionReuseReceiptIdentity`.

PR #782 correctly consumes exactly two terminal other-Agent parents and compiles only a nonexecuting owner-host evidence request. Its base `AdmissionReuseProjection`, however, retains a generic family/disposition/current-context summary while PR #769's actual reuse receipt preserves a stronger consequence-bearing identity vector.

This W3 addendum binds the complete vector to the G6 request without authenticating the caller-supplied receipt or widening any execution/effect authority.

## Exactly two other-Agent parents

1. **PR #769 — generation-bound admission reuse**
   - semantic owner head: `2b7d313bfbf4664ea4008b32c2cdbf79e957b298`
   - exact hosted proof generation: `d1a0f94255527835a59a70a0af7dc417ba1d023d`
   - source/test blobs: `d171d0938e469a4383490d1a691750c2068f21e7` / `58fad37a0f89853098fa3dbbe2f2a1771574e449`
   - run/job: `33437612722 / 99637780915`, SUCCESS
   - reusable law: `AdmissionValidAtProduce != AdmissionReusableAtUse`; positive reuse is only `REUSE_CANDIDATE`.

2. **PR #727 — secure operation-bound observation envelope**
   - exact hosted proof head: `293c59d7260372ccd3b9e8130b12979b052c3ed9`
   - source blob: `98db548b6e8f7443b79d979eb0e177ac6aa68534`
   - run/job: `33416248604 / 99567478616`, SUCCESS
   - reusable law: caller/structural evidence cannot manufacture physical truth; exact operation/workload/source plus observer/backend provenance remain explicit.

No self-authored artifact is counted as an Objective parent.

## W3 contradiction

PR #769's `AdmissionReuseReceiptV1` carries:

- `admission_receipt_digest`
- `subject_identity`
- `source_generation_key`
- `evidence_generation_key`
- `owner_context_key`
- `decision_context_key`
- `reuse_digest`

and its exact GLM family is `GLM53_BOUNDED_C2_PROPOSAL`.

The original G6-v2 projection reduced that to `BOUNDED_C2_PROPOSAL` + `REUSE_CANDIDATE` + `current_context_exact`.

That reduction could admit a structurally current but unrelated bounded-C2 admission into a GLM-5.3 Gate-10 request.

Therefore:

`ReuseCandidateSummary != AdmissionReuseReceiptIdentity`.

`GenericBoundedC2Family != GLM53BoundedC2ProposalIdentity`.

## Repair

Adds:

- `tools/awj032/glm53_g6_admission_identity_binding_addendum.py`
- `tools/awj032/test_glm53_g6_admission_identity_binding_addendum.py`
- `.github/workflows/aura-glm53-g6-admission-identity-binding-w3.yml`

The addendum consumes an already-compiled G6 request and a lossless PR #769 identity projection. A positive result is only:

`IDENTITY_BOUND_EXTERNAL_AUTH_REQUIRED`.

It binds the base G6 request digest to all seven consequence-bearing PR #769 identity fields. Each identity-axis substitution changes the binding/receipt digest; omissions and malformed digests fail closed.

The pure contract does **not** authenticate the producer of the reuse receipt, prove source currentness, authenticate the future owner, execute GLM/provider work, observe physical I/O, or grant Gate-10 authority.

## Hosted proof

Dedicated workflow `Aura GLM53 G6 Admission Identity Binding W3`:

- checks out the exact candidate head;
- pins #782's base G6 source/test blobs (`d92f6115120431082ed43a3023729654d8a4cdb7` / `e1f905b04b6daea9119fa6e6f751cd0cc721819e`);
- authenticates exact #769/#727 parent blobs;
- revalidates exact successful parent run/job coordinates;
- reruns G6 base adversarials;
- runs identity-binding W3 adversarials;
- exhausts the existing 512-state G6 Different-J surface plus a 16-state W3 summary lattice;
- enforces the anti-collapse/nonpromotion laws.

Current candidate generation: `5984198d7a935e6c6969da7961ba9b2ebb05e041`. Exact hosted W3 closure remains pending until the dedicated workflow returns SUCCESS.

## Triadic Process

**Thesis:** generation-bound admission reuse makes a bounded C2 proposal eligible for later use only when its consequence-bearing generations remain exact.

**Counterplane:** summarizing that result as a generic current boolean discards the very subject/source/evidence/owner/decision identity that PR #769 proved must remain exact.

**Second counterplane:** operation provenance from PR #727 prevents a structurally matching request/witness from becoming physical truth.

**Synthesis:** exact GLM family + complete PR #769 reuse identity vector + G6 request digest + PR #727 provenance debt -> deterministic identity-bound request candidate with external authentication still required.

## Creation Process

1. Freeze terminal #769 and #727 proof coordinates.
2. Collision-scan active G6 ownership; #782 is canonical and #777 is closed/superseded.
3. Compare #782's reuse projection to #769's actual receipt shape.
4. Identify the seven-field consequence-bearing projection loss.
5. Add a smallest stacked identity membrane rather than revive or fork G6.
6. Reject generic family cross-casting.
7. Attack every identity axis independently.
8. Bind identity and base-request digests deterministically.
9. Reexecute base 512-state proof and add 16-state W3 summary proof.
10. Require exact hosted SUCCESS before closure/successor credit.

## Omega-8 crystalline lenses

- **W0 provenance:** exact #769 + #727 terminal proofs only.
- **W1 ordered:** admission -> use-time revalidation -> exact reuse identity -> G6 request -> future owner-host evidence.
- **W2 substitution:** family, admission digest, reuse digest, subject, source, evidence, owner, decision, parent proof coordinates.
- **W3 contradiction:** summary currentness does not preserve consequence-bearing identity.
- **W4 factorization:** reuse identity, producer authentication, source currentness, owner authentication, execution, physical observation, replay/recovery and Gate-10 remain independent leaves.
- **W5 synthesis:** generation-bound reuse × operation provenance.
- **W6 quotient:** closed #777 receives zero active-owner credit; repair lives only on #782.
- **W7 temporal:** any consequence-bearing identity/generation change invalidates reuse binding.
- **W8 effect:** unearned.

## HyperScale

HS1 remains sufficient. The base G6 precondition cone is finite (`2^9 = 512`); the added W3 summary cone is finite (`2^4 = 16`). Same-boundary agent fanout cannot manufacture receipt authentication, source currentness, owner authentication or physical truth.

`UnresolvedExternalAuthentication => Gate10FanoutCredit = 0`.

## HyperDrive / K27

HyperDrive edge:

`PR769_REUSE_CANDIDATE + PR727_PROVENANCE -> G6_BASE_REQUEST -> EXACT_REUSE_IDENTITY_BINDING -> IDENTITY_BOUND_EXTERNAL_AUTH_REQUIRED | TYPED_HOLD`.

K27 remains deterministic retrieval/reopen metadata only:

`K27Coordinate != SemanticIdentity != Currentness != RuntimeTruth != Authority`.

`CoordinateMemory != MODEL_PREFIX_KV`.

No native/private transformer KV state is accessed or inferred.

## Official-source currentness refinement

Current public `zai-org/GLM-5.3` repository head observed in this Arena pass is `187fb9fff6319062325ff825627ef6db084d9bc6`, but the latest head movement is evaluation-metadata-only. The consequence-bearing Q18 tensor source remains at initial revision `7cda81930d6e4cef42f48555de830aa32ecdde28`:

- shard `model-00038-of-00141.safetensors`: Xet `a79bfbc0b0a8dc79a2d26497e7954d0d473c34b1f275dc5333aead4352e6e53a`, SHA-256 `e97f6e12233173645263c8cb25ae809c8393c19545669dd0f116a27282c781d1`;
- `model.safetensors.index.json`: Xet `cc559a187bc99b20039b572a3161f394c51ad19eb2c8eed41371f54740af5f94`, SHA-256 `e0fe7f28c1f853d4824e4d796374e3dacf1fe470988773952c79b063768134bf`.

Law:

`RepoHeadChanged != TensorSourceGenerationChanged`.

Revalidate consequence-bearing source-set content, while keeping unrelated repository-metadata currentness as a separate axis.

## Objective-1 closure provenance

The preceding G4 W3 objective closed at exact #764 head `d2169ecfc9a5c7278b0a5e0a0c359f15ab2d31c9`; dedicated run/job `33439280871 / 99643250720` completed SUCCESS. That closure proved only the non-reusable owner-resolved/currentness candidate membrane and external resolver/epoch trust debt. It grants no parent credit to this Objective-2 derivation.

## Claim ceiling

No reuse-receipt producer authentication, source currentness truth, tensor binding, real quantization/model/provider execution, full flagship load, physical-I/O truth, observer/backend authentication, AuraOS resident routing, replay/recovery proof, execution/effect authority, semantic K27 authority, native/private transformer KV access, Gate-10 promotion, merge/deploy/spend, or public/financial/human effect is granted.
