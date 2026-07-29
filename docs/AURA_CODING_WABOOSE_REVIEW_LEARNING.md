# Aura Coding Waboose Review Learning

**Architecture version:** `AURA_CODING_WABOOSE_REVIEW_LEARNING_V1`  
**Source lesson set:** PR #164 — Aura Spatial S0–S2  
**Authority:** Review learning only. No patch, commit, push, pull-request, merge, promotion, or production-mutation authority.

## Purpose

PR #164 exposed a recurring gap between finding a defect once and converting that defect into a reusable review skill. CodeRabbit, Codex, and manual review found valuable classes of errors, but raw comments are not a durable detector, regression, or architectural capability.

This subsystem converts successful review evidence into a typed, replayable learning path:

```text
external review comment or thread
  → typed reviewer finding
  → current / historical / resolved / outdated / duplicate disposition
  → invariant + repair pattern + required regression
  → deterministic lesson detector
  → Crucible adversarial replay
  → Coding Waboose hypothesis
  → exact-source and test corroboration
  → human-reviewed repair handoff
```

External reviewers remain teacher signals. A reviewer comment cannot prove itself, mutate source, or authorize promotion.

## Retained owners

The implementation extends retained Aura owners rather than creating a parallel review system:

- `aura_coding_waboose.py` remains the public Coding Waboose review owner.
- `aura_waboose_learning.py` remains the existing CodeRabbit/DREAM-lite/QDKT memory owner.
- `aura_coding_waboose_review_lessons.py` owns the typed lesson registry, normalizers, deterministic detectors, bounds, and Crucible receipts.
- `aura_coding_waboose_review_learning.py` is the narrow Coding Waboose integration layer that runs lesson detectors during a normal review scan.
- `aura_agent_arena_review_learning_bridge.py` extends the persistent Agent Bridge with four review-only tools.
- `aura_agent_arena_review_learning_mcp.py` projects those four tools through MCP while delegating every retained base tool unchanged.
- `.aura/review_lessons/pr164_spatial_review_lessons.json` is the canonical PR #164 lesson and adversarial-scenario registry.
- `schemas/aura_review_lesson.schema.json` is its strict Draft 2020-12 interchange schema.

## Aura-native planning harness

`scripts/aura_review_learning_architect_harness.py` exercises the architecture requested for long refactors:

1. **Coding Arena / Agent Bridge** — prepares bounded arena context and ACT capsules.
2. **Capability Connectome / atomic inventory** — finds existing owners and callable atomic functions before new code is introduced.
3. **Emergent Properties evidence** — searches for reusable compositions and review focus directives.
4. **Council V3** — selects critic lanes from plan length, dependencies, risks, rollback, and cost evidence.
5. **Surgeon control** — prepares proposal-only exact file/symbol slices under a bounded control profile.
6. **Coding Waboose** — reviews the exact branch range and applies learned detectors as hypotheses.
7. **Crucible** — replays every registered adversarial lesson and emits proof-oriented receipts.

The harness never claims that a configured workflow passed. Its receipt distinguishes current-head execution from workflow configuration and historical evidence.

## PR #164 executable lessons

The initial registry contains 13 defect classes:

| Lesson | Invariant |
|---|---|
| Authority aliases | Case, separators, and camel-case must not bypass protected authority metadata. |
| Protected metadata overrides | Untrusted metadata cannot contradict immutable false authority fields. |
| Order-dependent digesting | Canonicalize and deduplicate before identity, digest, cache, or interchange. |
| Truncate before sort | Stable sort and deduplicate before applying a cap. |
| Count-only bounds | Attacker-controlled retained evidence needs count and byte ceilings. |
| Noncanonical source paths | Evidence paths must be canonical repository-relative POSIX paths. |
| URI alias encoding | Validation must reject encoded/repeated separators and ambiguous URI forms. |
| Schema/runtime drift | Schema and runtime must expose the same acceptance boundary. |
| Unwired regression | A regression is evidence only when the intended workflow executes it. |
| Stale evidence claim | Every verification claim binds to an exact commit, run, and observed status. |
| Implicit coordinate basis change | Handedness or axis changes require an explicit tested conversion. |
| Nested unit double application | Unit conversion is applied exactly once and remains separate from geometric scale. |
| Noncanonical interchange acceptance | Canonical ordering and uniqueness are checked before accepting an external digest. |

Each lesson declares:

- trigger;
- invariant;
- repair pattern;
- required regression;
- generalization scope;
- false-positive guard;
- provenance;
- confidence;
- one adversarial Crucible scenario.

## Agent Bridge tools

The review-learning bridge exposes:

### `aura_waboose_ingest_external_review`

Normalizes bounded CodeRabbit, Codex, or manual review payloads. It preserves reviewer identity, exact repository head, PR number, file and line anchors, and disposition. Duplicate findings are not stored twice.

### `aura_waboose_review_lesson_summary`

Returns registry digest, lesson count, scenario count, detector IDs, stored finding count, and authority boundaries.

### `aura_waboose_run_review_detector`

Runs one deterministic detector against a bounded candidate object. The result is a review finding, not a repair or patch command.

### `aura_waboose_crucible_replay`

Replays all or selected adversarial scenarios and emits receipts containing:

- lesson invoked;
- detector invoked;
- finding produced;
- code slice or candidate shape;
- violated invariant;
- suggested repair;
- required regression;
- confidence;
- provenance;
- immutable non-authority fields.

## Coding Waboose integration

`ReviewLessonAwareCodingWaboose` subclasses the retained `CodingWaboose` façade. During `prepare()` it attaches the lesson registry context. During `scan()` it:

- reads only changed files in the review contract;
- parses Python with the declared source encoding;
- runs precision-first AST and lexical lesson detectors;
- checks changed test/workflow wiring when both are in scope;
- deduplicates lesson findings before normal Waboose ranking;
- runs the complete Crucible replay;
- preserves the existing diagnostic breadboard and review-only authority envelope.

Static lesson findings remain hypotheses until exact source, dependency, and regression evidence corroborate them. The integration deliberately favors high-confidence patterns over broad speculative linting.

## Reviewer evidence semantics

Normalized reviewer findings use explicit dispositions:

- `current_head` — reviewer evidence is bound to the exact current repository head;
- `historical` — evidence belongs to another commit and may still teach a general lesson;
- `resolved` — the review thread was marked resolved;
- `outdated` — GitHub marked the thread outdated after source movement;
- `duplicate` — the same reviewer/path/range/message identity was already present.

None of these statuses means that the current source is defective. Current source must be inspected and tested again.

## Bounds and fail-closed behavior

The implementation applies explicit ceilings to:

- complete reviewer payload canonical bytes;
- individual comment bytes;
- stored finding count per payload;
- repository path bytes;
- detector/scenario canonical bytes;
- registry canonical bytes;
- harness receipt canonical bytes.

Repository paths reject absolute paths, traversal, dot segments, repeated separators, backslashes, controls, and noncanonical POSIX forms. URI detectors reject encoded separator changes, credentials, queries, fragments, repeated separators, backslashes, and dot segments where those forms would create ambiguous evidence or resolver behavior.

## Verification workflow

`.github/workflows/aura-review-learning.yml` runs on Python 3.10 and 3.12 and includes:

1. focused Python compilation;
2. focused Ruff checks;
3. Draft 2020-12 schema meta-validation;
4. registry schema validation;
5. runtime registry semantic and digest validation;
6. new detector, Waboose, and Agent Bridge tests;
7. retained Coding Waboose and Waboose-learning regressions;
8. the Aura-native Architect/Council/Surgeon/Connectome/Emergent/Waboose harness on Python 3.12;
9. direct assertions that mutation and promotion authority remain false;
10. upload of an exact-head harness receipt.

A workflow file existing in the repository is only configured evidence. It becomes execution evidence only after GitHub reports the run and its conclusion for the exact PR head SHA.

## B11–B15 final Foundry harness binding

The final bilateral live-repair and Spatial Foundry refactor binds its scoped review request at:

```text
.aura/waboose_requests/bilateral_intent_guardrail_foundry_final.v2.json
```

The request covers the bounded incident-capture, durable replay, Runtime Profile V2 equivalence, persistent repair, isolated preview/rollback, canonical U7 delegation, Showcase composition, and projection-only Spatial Foundry files and tests. It also admits the final objective, plan-revision delta, definition-of-done receipt, architecture addendum, and generated navigation paths while keeping generated maps out of targeted external review.

For this final phase, the Review Learning workflow is intentionally part of the exact-head acceptance bundle because it executes the retained Aura-native harness over the complete branch range. A passing receipt must show:

- exact current PR head and base ancestry;
- Connectome and owner reuse rather than duplicate planes;
- Council V3 scope, tests, sequence, continuity, rollback, and cost lanes;
- Surgeon proposal-only control;
- Coding Waboose review over the exact changed range;
- Crucible adversarial replay with no unresolved failed lesson;
- `production_mutation`, `automatic_fix`, `automatic_commit`, `automatic_push`, `automatic_pull_request`, and `automatic_merge` all false;
- `human_review_required` true.

This binding does not make the review-learning subsystem a B11–B15 truth, persistence, verifier, rollback, or learning owner. It is an exact-head internal review gate before the separately authorized final Codex and CodeRabbit reviews.

## CodeRabbit and Codex review scope

Target reviewer scope is restricted to permanent source and tests:

```text
aura_coding_waboose_review_lessons.py
aura_coding_waboose_review_learning.py
aura_agent_arena_review_learning_bridge.py
aura_agent_arena_review_learning_mcp.py
schemas/aura_review_lesson.schema.json
.aura/review_lessons/pr164_spatial_review_lessons.json
scripts/aura_review_learning_architect_harness.py
tests/test_aura_coding_waboose_review_lessons.py
tests/test_aura_coding_waboose_review_learning.py
tests/test_aura_agent_arena_review_learning.py
.github/workflows/aura-review-learning.yml
docs/AURA_CODING_WABOOSE_REVIEW_LEARNING.md
```

Generated navigation files are excluded from targeted review until source verification is complete:

```text
.aura/CODEMAP.md
.aura/CODEMAP.json
topology_map.json
Aura_Memory/live_topology_ast.json
```

## Authority contract

Every public packet must preserve:

```json
{
  "production_mutation": false,
  "automatic_fix": false,
  "automatic_commit": false,
  "automatic_push": false,
  "automatic_pull_request": false,
  "automatic_merge": false,
  "human_review_required": true,
  "patch_authority": "exact_source_spans_and_hashes_only",
  "vsa_patch_authority": false
}
```

Learning improves what Coding Waboose notices. It does not expand what Coding Waboose is authorized to do.
