# Coding Waboose W2 — Continual Review Intelligence Refactor Plan

**Status:** Future bounded refactor plan
**Teacher episode:** AuraOS PR #162, Relational Synthesis R2
**Reviewed head:** Exact PR #162 reviewed head
**External teacher signals:** CodeRabbit and the independent Codex review on the same exact PR head
**Authority:** Proposal and learning only; exact current-source reproof and human authorization remain mandatory

## 1. Executive decision

Coding Waboose V1.1 correctly covered local AST and topology defect classes, but PR #162 exposed a broader review gap: many important defects do not live inside a single syntax tree or line-local pattern. They arise from **relationships among runtime contracts, schemas, persistence boundaries, scale characteristics, truth classes, query behavior, and profile budgets**.

The next refactor should therefore become:

```text
Coding Waboose W2: Continual Review Intelligence
  = deterministic rule packages
  + relational contract comparison
  + bounded operational probes
  + exact-head CodeRabbit teacher episodes
  + DREAM-lite/QDKT retrieval
  + current-source reproof
```

W2 must not copy CodeRabbit's conclusions blindly. CodeRabbit remains an external teacher signal. Waboose must convert repeated, exact-head-grounded lessons into deterministic candidate rules, test them against positive and false-positive fixtures, promote them through a governed lifecycle, and reprove every future finding against current source.

## 2. Why CodeRabbit found issues Waboose missed

### 2.1 Waboose's deterministic packs were too narrow

V1.1 primarily executes five semantic packs:

- `strict_input_types`;
- `symbol_identity`;
- `source_integrity`;
- `bounded_graph_integrity`;
- `test_evidence_preservation`.

Those packs are useful, but none owns runtime/schema parity, resource scaling, cross-file persistence atomicity, truth-class contamination, coupled budget selection, reverse-index behavioral completeness, or platform-specific path containment.

### 2.2 The review was mostly source-static, not operationally scaled

The implementation passed unit tests and deterministic serialization checks, but the default CLI path attempted to serialize a 35 MB index again. The defect emerged only when the command was exercised at Aura's real repository scale. Waboose did not run a bounded memory/RSS probe or assert that CLI output remained summary-sized.

### 2.3 Contract checks were one-directional

The JSON Schema used `additionalProperties: false`, but runtime `from_dict()` accepted extra nested fields. Waboose checked that schemas existed and tests passed; it did not compare schema object keys against runtime exact-key validators in both directions.

### 2.4 Concurrency was represented as code, not interleavings

The store used a lock for writes, but released it before post-write reload and read the linked index/receipt pair without a shared lock. A line-local review sees locking code; an interleaving-aware review asks whether the **entire invariant window** is protected.

### 2.5 Truth classes were validated individually, not relationally

Exact relations were correctly labelled `EXACT_SOURCE`, and Connectome relations were correctly labelled advisory. Yet exact relation evidence still included a Connectome digest, and advisory implementations received an `exact_implementation` role. Waboose lacked a rule that checks whether exact and advisory evidence or vocabulary contaminate one another across a full construction path.

### 2.6 Independent limits were tested independently

Relation count and participant count were each bounded, but relation selection could force more mandatory endpoints than the participant budget. Waboose lacked a coupled-invariant detector that evaluates limits jointly rather than one field at a time.

### 2.7 Reverse-index shape was validated, but behavior was not

Every reverse-index ID was valid, sorted, and non-dangling. However, participant lookup returned only group IDs, not the participant or incident relations. Waboose checked structural validity but did not execute a behavioral round-trip for each advertised query surface.

### 2.8 Platform and filesystem semantics were under-modelled

`PurePosixPath` correctly rejected absolute and parent-traversal paths on POSIX, but it did not reject Windows drive-qualified paths, and lexical containment did not protect against symlinked parents. Waboose lacked cross-platform path and resolved-filesystem containment probes.

## 3. PR #162 lesson matrix

| External finding | Root defect family | W2 candidate rule |
|---|---|---|
| CLI build duplicated the full index in JSON output | Operational scale / bounded output | `cli_operational_boundedness` |
| Status/validate retained stored and rebuilt full indexes | Resource lifetime / identity-only validation | `scale_resource_safety` |
| Participant lookup omitted self and incident relations | Behavioral reverse-index incompleteness | `reverse_index_completeness` |
| `topology_health` omitted from runtime freshness and `0.0` lost | Runtime/schema parity and falsy-value preservation | `runtime_schema_parity` |
| Windows drives and symlink parents could escape | Resolved workspace containment | `workspace_path_containment` |
| Nested extra keys accepted despite schema prohibition | Runtime/schema parity | `runtime_schema_parity` |
| Profile name, budgets, and digest could disagree | Compound identity contract | `profile_identity_integrity` |
| Post-write and linked reads escaped the lock window | Persistence interleaving | `persistence_atomicity` |
| Exact evidence included advisory Connectome context; advisory role said exact | Truth-class contamination | `truth_class_integrity` |
| Relation selection violated participant budget | Coupled limits and accounting | `coupled_budget_integrity` |
| CLI validate forced STANDARD instead of stored profile | Persisted-state/profile mismatch | `profile_identity_integrity` |

The two participant-lookup comments from Codex and CodeRabbit are one shared lesson, not two separate rules.

## 4. Proposed W2 rule package structure

```text
aura_waboose_rules/
  contract.py
  registry.py
  construction_paths.py
  schema_parity.py
  identity_integrity.py
  graph_boundaries.py
  authority_integrity.py
  persistence_atomicity.py
  operational_scale.py
  query_completeness.py
  patch_effectiveness.py
  test_adequacy.py
  generated_artifacts.py
```

### 4.1 `schema_parity.py`

Deterministic checks:

- compare JSON Schema required keys and `additionalProperties` policy with runtime `from_dict()` and `__post_init__` exact-key checks;
- identify schema-required fields omitted from freshness or equality comparisons;
- flag truthiness chains that can erase valid schema values such as `0`, `0.0`, `false`, or empty-but-valid collections;
- verify schema conditionals for discriminated contracts such as profile name → budgets → digest.

Required fixtures:

- extra nested field rejected in runtime and schema;
- missing required field rejected in both;
- valid `0.0` preserved;
- profile budget mismatch rejected;
- false-positive fixtures for optional open-ended metadata objects.

### 4.2 `identity_integrity.py`

Deterministic checks:

- bind discriminant, payload, and digest into one indivisible contract;
- compare persisted profile/variant with the profile used during validation;
- detect default-argument substitution that changes the meaning of persisted state;
- require all freshness identities, including nullable numeric identities, to participate in comparison.

### 4.3 `persistence_atomicity.py`

Deterministic construction-path checks:

- build a lock-scope graph from lock acquisition through all writes, post-write verification, and linked reads;
- flag verification that occurs after lock release;
- flag multi-file linked reads performed under separate lock windows;
- require atomic temporary-file replacement and parent-directory durability where supported;
- run a bounded two-writer/two-reader interleaving fixture.

### 4.4 `authority_integrity.py`

Deterministic truth-flow checks:

- exact relations may reference only exact canonical evidence owners;
- advisory evidence may provide context but must not mutate exact relation identity or payload;
- role names, predicates, and metadata must agree with the relation truth class;
- no `exact_*` vocabulary is allowed on advisory-only bindings unless an explicit exact owner proves it;
- Connectome, VSA, learned motifs, and model outputs remain non-authoritative.

### 4.5 `operational_scale.py`

Bounded probes:

- execute documented CLI paths on a generated large fixture or sampled real index;
- assert stdout/result payload is bounded independently of artifact size;
- track peak RSS or a deterministic allocation proxy;
- prohibit retaining a stored full graph while building a second full graph for freshness-only operations;
- distinguish build artifacts from CLI summaries.

W2 must use explicit budgets and skip rather than exhaust constrained runners.

### 4.6 `query_completeness.py`

Behavioral contract tests:

- for every reverse-index selector, select a known object and require the advertised object to be returned;
- participant lookup must return the participant and all incident relations;
- file/capability/group lookups must preserve all documented result classes;
- ungrouped participants remain inspectable;
- structural validity alone is not sufficient.

### 4.7 `workspace_path_containment.py`

Cross-platform deterministic checks:

- reject POSIX absolute paths;
- reject parent traversal;
- reject Windows drive and UNC paths even on POSIX hosts;
- resolve existing parent components and reject symlink escapes;
- revalidate containment immediately before lock and write operations;
- include Linux and Windows path fixtures.

### 4.8 `coupled_budget_integrity.py`

Relational selection checks:

- evaluate relation and participant budgets jointly;
- every selected relation must have both endpoints included;
- selecting a relation may not push participant count over budget;
- omitted relation count remains in relation units;
- omission reasons preserve the causal budget without adding participant counts to relation totals;
- deterministic ordering remains stable under input reorder.

### 4.9 `cli_operational_boundedness.py`

CLI contract checks:

- build/refresh commands print bounded summaries, never full generated indexes;
- validate/status use stored profile and freshness-only computation;
- exit code remains meaningful after artifacts are written;
- command documentation and implementation remain synchronized.

## 5. Rule lifecycle

Every new rule moves through:

```text
candidate → probation → verified → retired
```

### Candidate

Created from one or more exact-head-grounded external findings. It may produce advisory diagnostics only.

### Probation

Requires:

- at least one positive fixture;
- at least two false-positive fixtures;
- exact source-span grounding;
- deterministic output;
- no new authority.

### Verified

Requires repeated confirmation across independent PRs or an approved architecture invariant plus regression coverage. Only verified deterministic packs may satisfy a matching Waboose focus directive.

### Retired

Used when the architecture removes the defect class, the detector becomes noisy, or a stronger canonical rule supersedes it. Historical teacher episodes remain append-only.

## 6. Teacher-signal ingestion

The existing CodeRabbit learning path should remain:

```text
successful CodeRabbit review
  → exact reviewed HEAD
  → exact source span and digest
  → Capability Resolver / Connectome path
  → AST and relational signature
  → DREAM-lite similarity
  → QDKT observation
  → candidate rule family
  → probation fixtures
  → repeated confirmation
  → verified deterministic pack
```

For PR #162, the learning episode should record the following higher-order signatures in addition to the AST signature:

- schema path + runtime validator path;
- lock acquisition/release + linked read/write path;
- truth-class owner + evidence-reference owner;
- profile discriminant + budget mapping + digest;
- reverse-index producer + query consumer;
- documented CLI command + returned payload size class;
- relation selector + mandatory endpoint cardinality.

These are relational cause chains, not merely lexical token patterns.

## 7. Waboose review pipeline changes

Proposed review order:

```text
exact changed-file and range identity
  → canonical source decoding
  → schema/runtime parity
  → construction-path and truth-flow analysis
  → reverse-index behavioral probes
  → persistence interleaving probes
  → bounded scale/CLI probes
  → focused tests and linters
  → learned teacher-signal retrieval
  → current-source reproof
  → advisory findings
```

Hard guards precede learned ranking. A DREAM/QDKT similarity score cannot rescue a detector that lacks current evidence.

## 8. Workflows

Recommended workflows:

- `waboose-pr-review.yml` — bounded deterministic PR review;
- `waboose-daily-observatory.yml` — daily code-health proposals, maximum ten new findings and minimum zero;
- `waboose-weekly-deep-scan.yml` — scale and cross-contract probes;
- `waboose-rule-probation.yml` — positive/false-positive fixture gate;
- `coderabbit-waboose-learning.yml` — exact-head teacher dispatch;
- `coderabbit-waboose-learning-persist.yml` — non-authoritative DREAM/QDKT persistence.

No workflow may automatically fix, commit, push, open a PR, or merge production changes.

## 9. Implementation sequence

### W2.0 — Lesson normalization

- normalize PR #162 CodeRabbit and Codex comments into one deduplicated lesson set;
- bind each lesson to reviewed head and exact source span;
- record Connectome paths and relational signatures;
- produce a learning receipt.

### W2.1 — Contract and identity packs

Implement:

- `runtime_schema_parity`;
- `profile_identity_integrity`;
- `truth_class_integrity`;
- `reverse_index_completeness`.

### W2.2 — Persistence and containment packs

Implement:

- `persistence_atomicity`;
- `workspace_path_containment`.

### W2.3 — Coupled budgets and scale packs

Implement:

- `coupled_budget_integrity`;
- `scale_resource_safety`;
- `cli_operational_boundedness`.

### W2.4 — Governed promotion

- run positive and false-positive suites;
- compare against at least two future external reviews;
- promote only confirmed packs;
- keep novel motifs advisory until reproof.

## 10. Acceptance gates

W2 is complete only when:

- all nine PR #162 defect families are detected by deterministic fixtures;
- each pack has false-positive protection;
- runtime/schema key parity is checked in both directions;
- stored-profile validation never silently substitutes a default;
- exact/advisory evidence contamination is rejected;
- persistence linked-state reads are lock-scoped;
- Windows and symlink containment fixtures pass;
- participant queries return self and incident relations;
- coupled budgets cannot exceed either limit;
- large CLI builds emit bounded summaries;
- learned findings remain proposal-only;
- current-source reproof is mandatory;
- `safe_to_patch`, `production_mutation`, `automatic_fix`, `automatic_commit`, `automatic_push`, `automatic_pull_request`, and `automatic_merge` remain false;
- human review remains required.

## 11. Immediate lesson for future Aura refactors

Before requesting CodeRabbit, Coding Waboose should ask nine explicit questions:

1. Does runtime validation reject everything the schema forbids?
2. Are discriminants, budgets, and digests one canonical identity?
3. Are nullable and falsy-but-valid values preserved and compared?
4. Are exact and advisory evidence owners kept completely separate?
5. Do locks protect the full multi-file invariant window?
6. Are all path checks resolved and cross-platform?
7. Are multiple budgets enforced jointly?
8. Does every reverse index satisfy its advertised query behavior?
9. Do documented CLI paths remain bounded at Aura's real repository scale?

That checklist should become the first W2 probation pack and the default pre-CodeRabbit manual audit for generated indexes, registries, persistence stores, and Arena projection caches.
