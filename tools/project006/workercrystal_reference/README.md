# Project006 Lane-C WorkerCrystal G6 acceptance reference

This directory is a **reference-only repository realization** of the exact reviewed Drive-local Lane-C G6 acceptance-identity delta for `PROJECT006-RESIDENT-DEEPSEEK-WORKERCRYSTAL-BB-POC-001`.

## Exact design inputs

- G6 contract: Drive `1L2Qot2bJKXgqiQVW_riVQ2rOkoiqHhAByVzYJFLxQ18` at revision `AIroW35jBJ2FOK5Ul59fjy19ftAKhjf_p-R6d9itQyy0ZEblcQPd4nTplirpeJed_PkHgP-pnWn9Yi5_pZhsz32nE7jI6Ji7sdWVl4PHbaM`.
- Different-J G6 technical review: Drive `1J99GzWe0HpfP59uBHO02VHP_Y1bB86qYOHbEAqer7dA` at revision `AIroW35_gLK1rd-MwnpgBaca0L6VS8EPKSu3qt73WkZx37iD4F2eYBAG5J1N7YgWtcP_0jrmFbCfUqybRLB0JVVdC0uoxrM4DJ0VFk2A8pQ`.
- Repository implementation claim: Drive `1pgKV0lT3FZ1zXg6VLwr9AGulp-rU2AXltOYyJQmaGYg`.

## Implemented bounded surface

`workercrystal_acceptance_g6.py` realizes the reviewed one-way identity graph:

1. derive the preserved G5 `accepted_result_identity` from the exact closed accepted-result body;
2. derive one immutable G6 attempt/result binding per exact required contribution, with `acceptance_operation_digest` **absent** from the binding schema and identity preimage;
3. canonicalize the exact G6 binding-identity set;
4. derive the closed G6 acceptance-operation body and digest downstream;
5. on restart, independently rebuild accepted-result identity, binding records/identities, binding set and operation digest in that order, then compare to stored state;
6. fail closed on missing/extra/substituted bindings, noncanonical sets, profile aliasing, digest transplantation, malformed protected facts or stored/recomputed mismatch.

The reference deliberately does not implement or infer the upstream source-graph/currentness/authority verifier or the full durable transaction engine. `AcceptanceFacts` and terminal-attempt inputs are the already-resolved protected inputs to this identity/reconstruction layer. A caller must not treat constructing those inputs as proof that upstream admission was lawful.

## Canonicalization ceiling

The reviewed contract requires Unicode NFC + RFC8785 JCS + SHA-256. This reference uses deterministic JSON over the contract's restricted type domain: fixed ASCII object keys, NFC strings, non-negative integers, booleans, arrays and objects. Floats and null are rejected. Canonical member sets are duplicate-rejecting and ordered exactly where the G6 contract requires byte ordering.

## Author-side checks

`test_workercrystal_acceptance_g6.py` covers:

- accepted-result identity permutation invariance;
- duplicate verifier/contribution rejection;
- normative absence of operation digest from the G6 binding schema;
- G5 profile-alias rejection;
- G6 operation binding-set permutation invariance;
- rejection of noncanonical stored set order;
- transplanted operation-digest rejection;
- binding-identity tamper rejection;
- exact required-attempt set equality;
- empty-required-set failure when external contribution is required;
- multiple AcceptedResult relations without mutable attempt backlink state;
- unknown operation-field rejection;
- exact restart reconstruction.

The constructor executed these fixtures before staging and observed **15/15 PASS**. That is author-side evidence only and is not an independent review or repository-wide CI result.

## Explicit nonclaims

This directory does **not** establish:

- a complete WorkerCrystal scheduler/runtime;
- live workers, DeepSeek calls, provider connectivity or credential authority;
- Lane-A Resident or Lane-B Sidecar integration;
- durable database transaction atomicity or crash recovery beyond the pure reconstruction contract;
- complete RequiredContributingAttemptSet/source-graph derivation;
- deployment, systemd state, benchmark superiority or production performance;
- bug-bounty eligibility/finding/submission/acceptance/reward;
- repository merge/canonical adoption;
- Human Stage-9 disposition or Stage-10/Gate-10 closure.

Logical WorkerCrystal scale remains distinct from live worker count, and this reference contains no provider/network/credential path.

## Review law

J163/V02 authored this repository generation and must not independently review or certify it. A fresh Different-J reviewer must bind the exact PR head, execute/inspect the tests and attack the G6 schema, identity direction, canonicalization, restart/transplant behavior, version aliases and the claim ceiling before any adoption consequence.
