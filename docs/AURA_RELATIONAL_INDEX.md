# Aura Relational Anatomy Index

## Status

Phase 2 of Aura Relational Synthesis implements the generated, deterministic Ahead-of-Time relational anatomy cache.

Canonical module:

```text
aura_relational_index.py
```

Schema:

```text
schemas/aura_relational_index.schema.json
```

Generated runtime artifacts:

```text
.aura/RELATIONAL_INDEX.json
.aura/RELATIONAL_INDEX_RECEIPT.json
.aura/RELATIONAL_INDEX.md
```

The generated artifacts are navigation/cache outputs. They are not source truth and are excluded from their own scan.

## Aura-native implementation evidence

Phase 2 was planned against the current repository by executing Aura inside an isolated Python virtual environment. The run used:

- `AuraAgentArenaBridge.aura_repo_digest()`;
- `AuraAgentArenaBridge.aura_prepare_arena()` and the Coding Arena preparation path;
- `build_capability_connectome()` plus `enrich_connectome()`;
- `find_capability_path()` plus `enrich_path()`;
- `build_atomic_function_inventory()`;
- `AuraEmergentEvidenceSpine.run()`;
- `audit_emergent_capabilities()`.

The execution established:

```text
Agent Bridge CODEMAP files:     1,113
Agent Bridge symbols:           8,557
Connectome capabilities:           20
Connectome edges:                  55
current Python source files:       779
current CodeTopo nodes:         12,341
current CodeTopo edges:         24,452
complete atomic callables:      10,244
materialized index participants:12,361
materialized index relations:   24,518
materialized index groups:          22
Evidence Spine source slices:      180
Evidence Spine linked tests:         91
bounded emergent-audit symbols:    327
bounded emergent-audit edges:      953
advisory audit findings:            50
future-potential findings:           2
```

Coding Arena grounded the implementation seam to:

```text
aura_relational_synthesis.py#RelationalSynthesisShadowCompiler
```

The final isolated-venv materialization completed in about 11 seconds; loading, receipt linkage, and full Draft 2020-12 schema validation completed in about 8 seconds. The emergent audit was deliberately bounded to the ten Phase 2 architecture files and returned advisory candidate pairs only. Phase 2 therefore does not promote audit similarity into exact group membership or motifs. It materializes only exact CodeTopo relations and explicitly declared capability bundles. Higher-order motif evaluation remains Phase 3.

## Architecture

```text
current source
  → CodeTopoAnchor exact nodes and edges
  → canonical atomic inventory digest
  → Capability Connectome V2 advisory declarations
  → Phase 1 relational participants/relations/groups
  → deterministic macro domains and explicit surgical bundles
  → reverse indexes
  → freshness tuple
  → generated relational index + empirical build receipt
```

The index stores reusable anatomy. It does not store the current human objective, current diff, leases, consent, proof disposition, patch readiness, or objective-specific Relational Synthesis Capsule.

## Truth boundaries

Exact structural relations are admitted only from current `CodeTopoAnchor` edges:

- `call` → `CALLS`;
- `import` → `IMPORTS`;
- `test` → `TESTS`.

Capability implementation declarations become `IMPLEMENTS_CAPABILITY` relations with `ADVISORY_CONNECTOME` truth. Exact source endpoints are preserved, but the declaration itself remains advisory.

Qualified identities are required for same-named methods. An unqualified symbol is admitted only when it resolves uniquely inside the capability's declared implementation files. Ambiguous or missing mappings remain explicit boundary records.

## Freshness

A current index is pinned to:

- repository HEAD;
- working-tree digest;
- CODEMAP digest;
- topology digest, version, and health;
- Capability Connectome graph digest and version;
- atomic inventory digest and version;
- relation ontology digest;
- profile digest;
- index schema digest.

A missing freshness identity is never fabricated. A stale, corrupt, or unsupported index cannot claim exact relational grounding.

## Profiles

```text
MINIMAL
STANDARD
DEEP
```

Profiles bound group materialization only. Relations are selected jointly under relation and participant limits; a relation is omitted when its mandatory endpoints would exceed the participant budget. Selected endpoints are never dropped, and omission counts remain in relation units with the causal budget recorded explicitly.

## Macro domains and surgical bundles

The index uses explicit architecture registries. It does not infer exact domain membership from filenames or keywords.

All 16 macro-domain definitions and six initial surgical-bundle definitions are represented. Domains for which the current Connectome has no declared capability remain explicit unresolved groups rather than disappearing.

## Reverse indexes

The V1 index provides deterministic lookup by:

- participant;
- CodeTopo node ID;
- qualified symbol;
- file path;
- capability;
- group kind;
- relation type;
- test path;
- schema, authority family, and Arena when exact supported evidence exists.

Every reverse-index value must resolve to a participant, relation, or group in the same index. Participant lookup returns the participant itself, all incident relations, and any groups that include it, including for participants that belong to no materialized group.

## Persistence

Writes use a thread and cross-process lock, sibling temporary file, flush, `fsync`, atomic `os.replace`, and reload validation. Post-write reload and linked index/receipt reads remain under the same store lock. Store targets reject absolute, parent-traversal, Windows drive-qualified, and resolved symlink-escape paths. The empirical receipt is separate from deterministic index identity so timestamps and wall time cannot make equal repository states produce different indexes.

The initial incremental builder intentionally performs a conservative canonical full rebuild after validating changed paths. This proves incremental/full equivalence without introducing a fragile partial AST engine. Later optimization may replace affected groups while preserving byte-equivalent canonical output.

## Commands

```bash
python -m aura_relational_index build
python -m aura_relational_index refresh --changed aura_relational_index.py
python -m aura_relational_index status
python -m aura_relational_index validate
python -m aura_relational_index query --capability aura.relational.index
python -m aura_relational_index query --file aura_relational_index.py
python -m aura_relational_index query --relation CALLS
```

The CLI writes only generated index artifacts and never patches, commits, pushes, opens pull requests, or merges.

`build` and `refresh` print bounded summaries rather than serializing the full generated index to stdout. `status` and `validate` load the stored profile, release the expanded stored graph before current-state work, and compute only the current repository identity instead of constructing a second full relational index.


## Final validation

The permanent implementation was validated in the canonical excluded `.venv` with:

- 48 focused Phase 1/Phase 2 contract tests after manual CodeRabbit/Codex review hardening;
- 38 Affordance Directory and Capability Connectome tests;
- 16 Evidence Spine and CodeTopoAnchor tests;
- module compilation;
- deterministic repeated full builds;
- Draft 2020-12 schema validation with local references;
- atomic write, exact reload, and receipt linkage;
- current/stale freshness comparison;
- zero-valued topology-health preservation and comparison;
- runtime/schema exact-key and canonical-profile parity;
- Windows-drive and symlink-parent containment;
- lock-scoped post-write and linked-state verification;
- exact/advisory evidence separation;
- coupled relation/participant budget enforcement;
- participant self and incident-relation reverse lookup;
- stored-profile identity-only validation;
- bounded CLI result serialization;
- conservative incremental/full equivalence;
- exact query lookup over the generated reverse indexes.

The Agent Bridge, Coding Arena, Connectome, Evidence Spine, and Emergent Capability Auditor remained read-only throughout these runs.

## Authority invariants

```yaml
generated_only: true
safe_to_patch: false
production_mutation: false
automatic_fix: false
automatic_commit: false
automatic_push: false
automatic_pull_request: false
automatic_merge: false
human_review_required: true
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
```

No index lookup may override current exact source revalidation or human review.
