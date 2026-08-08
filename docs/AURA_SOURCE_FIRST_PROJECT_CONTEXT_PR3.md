# AuraOS PR3 — Source-First Project Reconstruction and Task-Conditioned Relational Graph

## Status

`IMPLEMENTING`

**Program:** AuraOS Intent-Native Spatial Computing / Ephemeral Arenas foundation
**Master unit:** PR3 — Source-first project reconstruction and task-conditioned relational graph
**Exact starting `main`:** `bf0c65a9e6ae1dfcbb575401d51a9d22f343d804`
**Branch:** `refactor/source-first-project-context-pr3`
**Harness:** ARCH v2.3
**Default terminal state:** `READY_FOR_HUMAN_REVIEW`
**Automatic merge:** forbidden

## 1. Objective

PR3 compiles the smallest sufficient, explainable, correction-capable project context from existing canonical Aura owners and answer-determining sources. Omission, staleness, conflicts, unavailable adapters, and missing mandatory evidence are first-class outputs rather than hidden side effects of context reduction.

The compiler is deliberately **read-only**. It does not create a universal project database, replace Aura's continuity owner, mutate source, execute code, grant patch authority, render a spatial scene, or start PR4 work.

## 2. Inherited architecture

PR3 preserves the already-merged PR1 `ProjectContextProjection` contract in `aura_ephemeral_workspace_contracts.py`. That contract remains the immutable minimum-sufficient projection consumed by downstream workspace recipes.

PR3 adds a compiler and selection/provenance companion around that contract. It consumes exact records emitted by existing public canonical APIs such as:

- Unified Memory / Continuity for accepted decisions, rejected alternatives, blockers, next actions, and project continuity;
- Coding Relationship Compass / Relational Index / Relationship Atlas for exact objective-scoped relationships;
- Emergent Evidence Spine and repository-owned source/test/schema evidence producers for exact source identities and proof obligations;
- Gate/policy owners for authority and policy dependencies;
- Attempt Archive / review evidence owners for failed or rejected evidence.

These adapters remain owners of their records. `aura_project_context_compiler.py` owns only the deterministic task-conditioned selection result, its omission receipt, its bounded graph projection, and freshness/provenance validation.

## 3. No second plane

PR3 must not become a second:

- truth or project-memory store;
- source repository;
- router/planner;
- policy or authority owner;
- verifier;
- mutation path;
- renderer/scene truth store.

Every compilation is disposable and reconstructable from canonical sources. A changed answer-determining source requires a new compilation; PR3 never repairs freshness by mutating a long-lived project graph.

## 4. Source-first candidate contract

Every candidate carries:

- a stable task-local candidate ID;
- category and source adapter;
- origin reference;
- fixed authority class;
- truth class;
- availability state;
- exact `CanonicalReference` when authoritative source material is available;
- relevance score;
- explicit dependencies;
- optional conflict key, which is always a string and is canonically validated when non-empty;
- temporal bindings.

Truth classes are structurally distinct:

- `EXACT_CURRENT`
- `DERIVED_VERIFIED`
- `ADVISORY`
- `HYPOTHESIS`
- `STALE`
- `UNAVAILABLE`

Graph edges independently preserve:

- `EXACT`
- `DERIVED_VERIFIED`
- `ADVISORY`
- `HYPOTHESIS`
- `STALE`
- `UNAVAILABLE`

For an authority-bearing `EXACT_CURRENT` or `DERIVED_VERIFIED` candidate, `origin_ref` must equal the exact `CanonicalReference.canonical_ref`. This structurally binds the candidate's claimed origin to the canonical reference that also carries owner, digest, truth, and freshness identity. An authority-bearing candidate with a different claimed origin is rejected at construction. Advisory/hypothesis/stale/unavailable material cannot acquire authority through an origin claim; if its origin differs from its reference, `origin_bound` is false rather than self-asserted true.

A summary, model conclusion, shadow ranker, trusted-tool echo, or repeated/corroborated advisory statement cannot upgrade its origin or authority class.

## 5. Hard inclusion and graph reduction

The compiler receives an already task-conditioned candidate set from public canonical adapters. It then uses deterministic dependency closure and budget-aware selection rather than arbitrary node clipping.

Within that task-conditioned set, these classes are mandatory and cannot be silently dropped for budget reasons:

- direct tests;
- direct schemas;
- authority dependencies;
- policy dependencies;
- known blockers;
- failed-attempt evidence;
- proof obligations.

Answer-determining source candidates are also mandatory. Explicitly required candidates remain mandatory regardless of category.

Selection eligibility and **source admission are deliberately different predicates**. `DERIVED_VERIFIED` evidence may be selected and may support reconstruction, but a `COMPLETE` source-first compilation requires at least one selected `SOURCE` candidate whose truth class is `EXACT_CURRENT` **and whose `answer_determining` flag is true for the current objective**. A derived answer source cannot impersonate that anchor, and an unrelated exact source cannot launder a derived answer source into completeness.

If the complete mandatory dependency closure cannot fit the declared node budget, PR3 does **not** choose an arbitrary subset. The receipt becomes `INCOMPLETE`, records the budget omission, and denies admission.

Optional candidates are ranked deterministically by declared relevance, then fixed category priority, then candidate ID. A candidate and its dependency closure are selected as a unit only when they fit.

## 6. `ProjectionSelectionReceipt`

Every compilation emits `AURA_PROJECTION_SELECTION_RECEIPT_V1`, recording:

- `selected`
- `omitted_irrelevant`
- `omitted_by_budget`
- `stale`
- `unavailable`
- `conflicting`
- `source_adapter_missing`
- `mandatory_evidence_missing`
- `COMPLETE` or `INCOMPLETE`
- the exact selection budget and digest

The receipt is bound to the objective digest, exact repository identity digest, and canonical project owner.

A `COMPLETE` receipt cannot contain missing mandatory evidence. An `INCOMPLETE` receipt must expose at least one missing mandatory item.

## 7. Existing PR1 projection remains canonical

**Projection emission is a consequence of a complete receipt, not merely of having selected references.** When—and only when—the receipt is `COMPLETE` and the exact-current answer-determining source admission anchor is satisfied, PR3 emits the existing PR1 `ProjectContextProjection` with:

- canonical owner fixed to `aura_unified_memory_continuity`;
- exact repository identity;
- exact references grouped into the existing PR1 fields;
- `MINIMUM_SUFFICIENT` privacy class;
- `LOCAL_ONLY` egress class;
- false mutation/execution/persistence/merge authority inherited from the PR1 authority envelope.

An `INCOMPLETE` compilation has `projection: null`; the same is true through `headless_projection()`. PR3's compilation record independently owns `project_ref`; that value is included in the compilation digest and the nested PR1 projection must match it, so a hand-built projection cannot silently substitute a different project identity. The public `ProjectContextCompilation` constructor also rejects a hand-assembled `INCOMPLETE` record that attempts to smuggle in a PR1 projection, independently re-proves the exact-current answer-determining source anchor for a hand-assembled `COMPLETE` record, revalidates every selected candidate against the same truth/availability/freshness eligibility boundary used by the compiler, and independently rejects the reserved `source:selected` missing-source marker. Selected unresolved conflicts are rejected as well. This prevents a caller from placing advisory, stale, unavailable, adapter-missing, conflicting, or reserved-sentinel material into a canonical projection by bypassing `compile_project_context_projection()`.

PR3 does not change the PR1 serialized contract or PR2 runtime contract.

## 8. Temporal invalidation

Selected candidates may bind any of the following validity dependencies:

- `REPOSITORY_HEAD`
- `SOURCE_HASH`
- `EVIDENCE`
- `POLICY`
- `LEASE`
- `OWNER_RECORD`
- `DEPENDENCY_VERSION`

Freshness validation compares the complete compiled repository identity and every selected temporal binding against current canonical observations. Every authoritative selected canonical reference is automatically represented by a drift-sensitive temporal binding over its exact canonical-reference digest, using the existing SOURCE_HASH, EVIDENCE, POLICY, or OWNER_RECORD binding classes according to evidence category. Cross-candidate binding definitions with the same key must agree; conflicting mandatory evidence is receipt-visible and prevents admission. A binding already expired at the compilation freshness timestamp is classified as stale before selection and prevents mandatory admission. Missing, changed, or expired bindings require recompilation. Freshness validation is read-only and never mutates the projection in place.

## 9. Bounded backward provenance

PR3 can trace incoming project-context edges backward from a selected result, failure, proof obligation, or operation. The trace is explicitly bounded by hop and node ceilings and reports any truncated frontier.

`source_reached` means only that at least one node categorized as `SOURCE` was encountered. It is intentionally weaker than proof completeness.

A trace is `source_complete` only when every requested start's complete backward component terminates at `EXACT_CURRENT` `SOURCE` nodes through only `EXACT` or `DERIVED_VERIFIED` edges, no rootless or cyclic component remains unproved, and no predecessor frontier was truncated. `DERIVED_VERIFIED` source roots may support a trace but cannot make it source-complete. Bounded output may never imply completeness it did not prove.

## 10. Memory lifecycle governance

Every retained candidate records the full lifecycle:

1. `WRITE_INGEST`
2. `STORE`
3. `RETRIEVE`
4. `EXECUTE_USE`
5. `SHARE_PROPAGATE`
6. `FORGET_ROLLBACK`

This is governance metadata, not a new memory owner. For authority-bearing candidates, origin is structurally rebound to the candidate's canonical reference at creation. Authority is fixed by truth class (`EXACT_CURRENT` → canonical read, `DERIVED_VERIFIED` → derived read); advisory/hypothesis/stale/unavailable material carries no read authority and cannot increase authority by transformation. The serialized `authority_non_increasing` field is computed from that enforced truth/authority mapping rather than emitted as an unconditional assertion.

## 11. Headless / client projection

`headless_projection()` returns only selected nodes and selected bounded edges plus the explicit selection receipt. It always states:

`full_project_graph_included: false`

The complete repository/project topology is not sent to the client by default. The headless payload includes `project_ref` and `compilation_digest`, and exact canonical references survive the headless path. If selection is `INCOMPLETE`, the headless payload retains the receipt and selected diagnostic context but exposes no canonical PR1 projection.

Spatial representation, asset streaming, scene deltas, WebXR, and renderer work are PR4 or later and are out of scope here.

## 12. VSA/HDC boundary

PR3 does not grant VSA/HDC ranking any authority. A future PR3 transaction may add an optional shadow comparison against exact traversal if justified, but disagreement must remain visible and exact traversal remains authoritative. The initial implementation does not require that optional ranker.

## 13. Security properties

PR3 fails closed when:

- mandatory evidence is stale, unavailable, conflicting, adapter-missing, dependency-missing, or budget-blocked;
- no selected `EXACT_CURRENT`, answer-determining source anchors admission, even if `DERIVED_VERIFIED` source material or unrelated exact source material is present;
- an `INCOMPLETE` compilation attempts to emit or expose a canonical PR1 projection;
- a hand-assembled `COMPLETE` compilation cannot independently prove its exact-current answer-determining source anchor;
- a hand-assembled compilation attempts to mark compiler-ineligible advisory, stale, unavailable, adapter-missing, or conflicting candidates as selected canonical evidence;
- caller-supplied candidate IDs collide with the reserved `source:selected` missing-source receipt marker, including through hand-assembled public compilation records;
- selected candidates exceed signed node/edge budgets, have incomplete dependency closure, or graph edges reference candidates outside the task-conditioned set;
- projection references differ in full canonical identity or category placement from selected candidates;
- one canonical reference is aliased into multiple candidate roles;
- an authority-bearing candidate claims an `origin_ref` different from its canonical reference origin;
- advisory/hypothesis/stale/unavailable material attempts to carry canonical/derived read authority;
- repository identity or selected temporal bindings drift, or caller binding keys collide after canonical normalization;
- a provenance trace is truncated, follows non-authoritative edges, or terminates at non-exact source roots but is presented as source-complete.

PR3 never grants patch, execution, persistence, publication, deployment, payment, professional, or merge authority.

## 14. Focused verification

The focused PR3 suite must prove at minimum:

- deterministic selection/digest under reordered equivalent inputs;
- `INCOMPLETE` never emits or exposes the canonical PR1 projection, including hand-assembled public records;
- `DERIVED_VERIFIED` answer source cannot satisfy the exact-current answer-source admission anchor;
- an unrelated exact source cannot launder a derived answer source into a `COMPLETE` compilation;
- the public compilation object independently re-proves the exact-current answer-determining source anchor;
- the public compilation object rejects compiler-ineligible selected candidates even when a forged receipt and PR1 projection contain matching reference IDs;
- the public compilation object rejects the reserved `source:selected` marker independently of the normal compiler entry path;
- authority-bearing origin claims are structurally bound to `CanonicalReference.canonical_ref` and forged origin claims fail closed;
- serialized authority non-increase is computed from enforced truth/authority class mapping;
- provenance rooted only in derived source cannot claim `source_complete`;
- answer-determining source changes invalidate identity/freshness;
- mandatory evidence survives context pressure;
- mandatory closure is never arbitrarily clipped;
- missing source adapters produce `INCOMPLETE`;
- stale and conflicting evidence remain visible;
- exact and hypothesis edges remain distinct;
- bounded provenance exposes truncation and proves source-completeness only when warranted;
- all temporal binding classes fail closed on change/expiry;
- memory lifecycle and origin/authority monotonicity are explicit;
- full project topology is absent from default headless output;
- Draft 2020-12 schema validation passes for the selection receipt;
- retained PR1/PR2 compatibility suites remain green or any pre-existing baseline failure is exact-base reproduced and dispositioned without being silently attributed to PR3.

## 15. PR3 exit boundary

PR3 is complete only when:

- focused compiler/schema tests are green;
- retained PR1 and PR2 tests are green, with any unrelated pre-existing repository failure separately baseline-proven and dispositioned;
- compile/static/schema/diff checks are green;
- exact changed-file scope is intentional;
- available external reviewer findings are reproduced and dispositioned against PR3 invariants;
- no generated CODEMAP/topology artifact is committed before source stabilization;
- temporary ARCH continuity state is promoted/deleted according to ARCH v2.3;
- the exact PR head reaches `READY_FOR_HUMAN_REVIEW`.

PR4 must not begin automatically, and PR3 must not merge automatically.
