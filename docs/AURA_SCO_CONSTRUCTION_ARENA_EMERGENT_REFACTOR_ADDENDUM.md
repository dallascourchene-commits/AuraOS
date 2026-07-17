# AuraOS SCO Construction Arena — Emergent Refactor Addendum

```yaml
document_status: PHASE_ONE_IMPLEMENTED_PENDING_FINAL_GATES
document_version: 1.1.0
prepared_date: 2026-07-16
repository: dallascourchene-commits/AuraOS
baseline_main: 52f07f3b8bc5f932b6a1c950f0c3081500f189db
branch: refactor/sco-construction-arena
phase: E0_E3
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
construction_authority: authorized_human_professional_contractual_legal_and_regulatory_roles_only
cross_arena_handoff: docs/AURA_CROSS_ARENA_CHANGE_HANDOFF_LOG.md
```

## Decision

The SCO Construction Arena should be built as a narrow domain layer over Aura's existing governed spine. The original proposed module list remains a responsibility inventory, not permission to create a parallel planner, evidence store, bridge, experience system, quality system, or autonomous construction controller.

```text
human objective
  -> Human Agent emergent evidence
  -> Capability Connectome / Resolver
  -> CODEMAP and exact topology
  -> existing owner | narrow adapter | true capability gap
  -> revisioned refactor skeleton
  -> exact-span-and-hash Action Capsules
  -> staged patch and verifier
  -> digest-bound human decision
```

## Construction authority boundary

Aura may represent claims, evidence, conflicts, dependencies, missing approvals, and coordination options. It may not:

- authorize physical work;
- certify safety, engineering, inspection, or professional conclusions;
- release payment or transfer funds;
- control physical access;
- operate equipment;
- discipline workers;
- treat sensor or location data as dispositive proof;
- replace contractual, legal, regulatory, owner, consultant, or community authority.

## Original ten emergent properties adapted

| # | Emergent property | Phase 1 adaptation |
|---:|---|---|
| 1 | Grounded intent -> Action Capsules | Only `READY_FOR_ACT` nodes with verified repository bytes, SHA-256 hashes, and exact line spans compile |
| 2 | Topology -> route | Future work may select zero-model, Surgeon, Council, or human specialist from grounded task structure |
| 3 | Localization before broad prompts | Capability Resolver and exact requested owner symbols precede invention |
| 4 | Verified memory -> compact context | Revisioned skeletons replace conversation replay as the continuity object |
| 5 | Plans -> persistent live skeletons | Content-addressed, immutable, revisioned skeleton and node records |
| 6 | Gate failure -> bounded repair | Repairs append to responsible-node history; revision forks and gaps fail closed |
| 7 | Attempts -> governed procedures | Deferred until complete verified ArenaExperience records exist |
| 8 | Finding -> ghost plan | Human Agent emergent evidence remains proposal-only and strict at packet admission |
| 9 | Reuse before invention | Every proposed capability receives an exact owner/reuse decision |
| 10 | Verified component -> hotswap proposal | Deferred to exact-head staging, verification, approval, rollback, and post-merge checks |

## Phase 1 implementation

### General canonical owner

`aura_refactor_skeleton.py` provides:

- `SourceSpan`;
- `IntegrationDisposition`;
- `RefactorSkeletonNode`;
- `RefactorSkeleton`;
- `RefactorSkeletonStore`;
- exact repository file verification and SHA-256 helpers.

The implementation preserves:

- stable semantic identity;
- recursive immutability of digest-covered content;
- canonical node and skeleton digests;
- exact source hashes and line spans;
- revision and prior-digest chains;
- repair history;
- cross-Arena integration dispositions;
- proposal-only authority;
- content-addressed, atomically written persistence.

A node cannot become `READY_FOR_ACT` without exactly one valid SHA-256 hash per target file, at least one exact span per target, required tests, normalized repository-relative paths, and verified current file bytes.

### Construction planning adapter

`aura_construction_refactor_plan.py` provides:

- construction capability requirements;
- Capability Resolver-backed reuse inventory;
- exact requested-symbol owner proof;
- rejection of file placeholders, unrelated symbols, and generic capability paths;
- the E0-E14 Construction skeleton;
- fail-closed exact-grounded Action Capsule compilation;
- construction authority validation.

### Phase sequence

```text
E0 — evidence and baseline lock
E1 — capability reuse matrix
E2 — persistent refactor skeleton
E3 — exact-grounded capsule compiler boundary
E4-E14 — deferred runtime, evidence, benchmark, documentation, review, and merge work
```

## Human Agent Emergent integration

Reuse `aura_emergent_refactor_workspace.py`; do not create another evidence store.

```text
EMR-* complete report
EMF-* finding
ERP-* strict refactor packet
ERE-* external research evidence
```

Complete files remain authoritative; indexes are repairable. Semantic IDs exclude timestamps. Evidence capture may be permissive, but packet admission is strict and unresolved selected IDs fail closed. External research remains non-authoritative.

## Cross-Arena discoverability

Every new capability must classify every relevant structure as one of:

```text
INTEGRATED
INTENTIONALLY_LOCAL
ADAPTER_REQUIRED
DEFERRED
BLOCKED
NOT_APPLICABLE
DEPRECATED
SUPERSEDED
```

Anything not integrated must be recorded in `docs/AURA_CROSS_ARENA_CHANGE_HANDOFF_LOG.md` with its canonical owner, missing wire, exact next grounding task, and retirement criterion.

## Manual equivalent review

CodeRabbit was unavailable within the phase window, so an equivalent manual review was completed. The exact evidence is recorded in `docs/AURA_SCO_PHASE1_REVIEW_EVIDENCE.md`.

```yaml
py_compile: PASS
focused_adversarial_tests: 33_passed
automated_review_findings_repaired: 5
additional_manual_findings_repaired: 16
```

## Generated topology policy

The topology artifacts are regenerated, never hand-merged:

```text
.aura/CODEMAP.json
.aura/CODEMAP.md
topology_map.json
```

They must reflect the exact final source, tests, and documentation tree.

## Next phase

After Phase 1 is merged and current `main` is regrounded, execute E4-E6 only:

```text
E4 — minimal Construction domain contracts
E5 — deterministic state, supersession, conflict, and queries
E6 — authority, attestation, and receipt adapter
```

Money, hazard, live connectors, physical control, Human Agent runtime integration, Experience projection, and Crucible proposal mining remain deferred until E4-E6 are independently verified.

> Build the Construction Arena by extending Aura's governed spine, not by creating another monolith. Preserve unknowns, conflicts, and missing authority; return consequential decisions to authorized people.
