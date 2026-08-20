# Project006 Lane-C WorkerCrystal G6 acceptance reference

This directory is a **reference-only repository realization** of the exact reviewed Drive-local Lane-C G6 acceptance-identity delta for `PROJECT006-RESIDENT-DEEPSEEK-WORKERCRYSTAL-BB-POC-001`.

## Exact design inputs

- G6 contract: Drive `1L2Qot2bJKXgqiQVW_riVQ2rOkoiqHhAByVzYJFLxQ18` at revision `AIroW35jBJ2FOK5Ul59fjy19ftAKhjf_p-R6d9itQyy0ZEblcQPd4nTplirpeJed_PkHgP-pnWn9Yi5_pZhsz32nE7jI6Ji7sdWVl4PHbaM`.
- Different-J G6 technical review: Drive `1J99GzWe0HpfP59uBHO02VHP_Y1bB86qYOHbEAqer7dA` at revision `AIroW35_gLK1rd-MwnpgBaca0L6VS8EPKSu3qt73WkZx37iD4F2eYBAG5J1N7YgWtcP_0jrmFbCfUqybRLB0JVVdC0uoxrM4DJ0VFk2A8pQ`.
- Repository implementation claim: Drive `1pgKV0lT3FZ1zXg6VLwr9AGulp-rU2AXltOYyJQmaGYg`.

## Implemented bounded surface

`workercrystal_acceptance_g6.py` realizes the reviewed one-way identity graph:

1. derive the preserved G5 `accepted_result_identity` from the exact closed accepted-result body;
2. require every public G6 binding/operation builder to match that independently recomputed accepted-result identity, preventing identity transplantation;
3. derive one immutable G6 attempt/result binding per exact required contribution, with `acceptance_operation_digest` **absent** from the binding schema and identity preimage;
4. make public `validate_g6_binding_record` semantic: it requires independently resolved `AcceptanceFacts` plus the exact `AttemptTerminalFacts`, reconstructs the expected record, and canonical-byte-compares it; the self-hash-only checker is private/internal and is not an authority path;
5. canonicalize the exact G6 binding-identity set;
6. derive the closed G6 acceptance-operation body and digest downstream;
7. on restart, independently rebuild accepted-result identity, binding records/identities, binding set and operation digest in that order, then compare to stored state;
8. reject generation integers outside the interoperable RFC8785/ECMAScript safe-integer range `0..9007199254740991`, avoiding cross-validator JCS numeric divergence;
9. fail closed on missing/extra/substituted bindings, rehashed protected-fact transplantation, noncanonical sets, profile aliasing, identity/digest transplantation, malformed protected facts, non-COMPLETE lifecycle, unsafe generation integers, or stored/recomputed mismatch.

The reference deliberately does not implement or infer the upstream source-graph/currentness/authority verifier or the full durable transaction engine. `AcceptanceFacts` and terminal-attempt inputs are the already-resolved protected inputs to this identity/reconstruction layer. A caller must not treat constructing those inputs as proof that upstream admission was lawful.

## Canonicalization ceiling

The reviewed contract requires Unicode NFC + RFC8785 JCS + SHA-256. This reference uses deterministic JSON over the contract's restricted type domain: fixed ASCII object keys, NFC strings, non-negative JCS-safe integers, booleans, arrays and objects. Floats, null and integers above `2^53-1` are rejected. Canonical member sets are duplicate-rejecting and ordered exactly where the G6 contract requires byte ordering.

## Author-side checks

The reference now contains **24 unittest regression methods** across `test_workercrystal_acceptance_g6.py` and `test_workercrystal_jcs_safe_integer.py`, covering:

- accepted-result identity permutation invariance;
- duplicate verifier/contribution rejection;
- normative absence of operation digest from the G6 binding schema;
- G5 profile-alias rejection;
- binding- and operation-builder accepted-result identity transplant rejection;
- public semantic binding validation requiring protected facts and accepting an exact reconstructed record;
- rehashed protected-fact transplant rejection across accepted-result identity/digest, terminal reconciliation generation, capsule identity/digest/incarnation, lease identity/generation and fencing-token digest;
- G6 operation binding-set permutation invariance;
- rejection of noncanonical stored set order;
- transplanted operation-digest rejection;
- binding-identity tamper rejection;
- exact required-attempt set equality;
- empty-required-set failure when external contribution is required;
- multiple AcceptedResult relations without mutable attempt backlink state;
- unknown operation-field and malformed protected-digest rejection;
- non-COMPLETE restart rejection;
- exact restart reconstruction;
- acceptance of the maximum interoperable JCS-safe generation integer;
- fail-closed rejection of `2^53` and larger generation integers.

The original constructor scratch suite observed **15/15 PASS** before repository staging. After the independent Greptile transplant finding, Sourcery lifecycle-test suggestion, and Codex JCS-safe-integer finding were incorporated, the earlier constructor reconstructed the then-exact three committed functional/test blobs, verified their Git blob SHA-1 identities against GitHub (`2be837b4fc6ae6c7cef4e1228257b8b4fe7da8aa`, `75be58e5a7ab253bdf8df75e1b9b6e99ca25f9c0`, `9f677e50985affa890b5a355c14bb68c0645cdad`), and executed that earlier suite with **21/21 PASS**. That evidence belongs to those earlier blobs only and remains author-side evidence. The later semantic-validator repair and its new regressions require exact-head workflow evidence plus fresh Different-J review; no pass is inferred from the historical 21/21 run.

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

J163/V02 authored the original repository generation and must not independently review or certify it. The current semantic-validator repair is also constructor-authored work and must receive fresh Different-J review. That reviewer must bind the exact PR head, execute/inspect the tests and attack the G6 schema, protected-fact crossbinding, identity direction, canonicalization including the JCS safe-integer ceiling, restart/transplant behavior, version aliases and the claim ceiling before any adoption consequence.