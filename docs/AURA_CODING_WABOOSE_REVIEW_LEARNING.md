# Coding Waboose Review-Learning Architecture

## Purpose

This subsystem turns verified external review findings into typed, replayable review lessons for Coding Waboose. CodeRabbit, Codex, and manual reviews are teacher signals. They never become patch, commit, pull-request, merge, or production authority.

The implementation is the repository-native completion of the PR #164 post-merge handoff. It preserves the existing owners:

```text
exact repository source + tests
  → Agent Bridge / Coding Arena grounding
  → external reviewer adapter
  → NormalizedReviewFinding
  → duplicate and freshness disposition
  → invariant + detector + repair pattern + regression binding
  → durable review lesson registry
  → Capability Connectome declaration
  → DREAM-lite / QDKT advisory reuse
  → Coding Waboose deterministic/probable scan
  → Crucible adversarial replay
  → review-only finding or Forge repair request
  → verifier and human decision
```

## Canonical owners

| Concern | Owner | Authority |
|---|---|---|
| Exact code and line identity | Git/source, CODEMAP, Coding Arena | Exact evidence only |
| Typed review lesson facade/engine | `aura_coding_waboose_review_lessons.py` | Review learning only |
| Shared bounded contracts | `aura_review_lessons_contracts.py` | Validation only |
| Security/bounds detectors | `aura_review_lessons_security.py` | Review findings only |
| Determinism/source-shape detectors | `aura_review_lessons_determinism.py` | Review findings only |
| External-review normalization | `aura_review_lessons_external.py` | Typed evidence only |
| Durable PR #164 lesson fixtures | `.aura/review_lessons/pr164_spatial_review_lessons.json` | Versioned advisory evidence |
| External review ingestion | `ReviewLessonEngine.normalize_review()` / `ingest_review()` | No source truth upgrade |
| Waboose review orchestration | `aura_coding_waboose.py` + narrow subclass | Review only |
| Agent exposure | Agent Bridge/MCP adapters | Bounded tool projection |
| Capability relations | Affordance Directory and Connectome | Advisory discovery |
| Adversarial experience | `run_crucible_replay()` | Verification evidence only |
| Promotion | Existing Forge/Gate/human workflow | Separate authorization required |

## Lesson contract

Every durable lesson records:

```text
trigger
violated invariant
detector
repair pattern
required regression
generalization scope
false-positive guard
confidence
provenance
```

A comment alone is not a lesson. Review evidence must retain reviewer identity, PR/head identity, path/range, disposition, duplicate relationship, and provenance. A later source-grounding step is required before the finding can be treated as exact code evidence.

## PR #164 detector set

The initial registry implements thirteen deterministic detector families:

```text
detect_authority_aliases
detect_protected_metadata_overrides
detect_order_dependent_digesting
detect_truncate_before_sort
detect_count_without_byte_budget
detect_noncanonical_source_path
detect_uri_alias_encoding
detect_schema_runtime_drift
detect_unwired_regression
detect_stale_evidence_claim
detect_implicit_coordinate_basis_change
detect_nested_unit_double_application
detect_noncanonical_interchange_acceptance
```

These detectors generalize the defects found during the spatial S0-S2 review without hard-coding fixes to spatial files.

## External reviewer adapter

`normalize_external_review()` distinguishes top-level PR comments, inline review threads, review submissions, and current-head, historical, outdated, resolved, and duplicate findings.

The adapter byte-bounds the full payload and individual comment/path values. Boolean evidence flags are strict: strings such as `"false"` are rejected rather than coerced. The repository-bound engine independently reads Git HEAD and rejects a caller-supplied `current_head` that does not match it. A comment is never inferred to be source-grounded merely because it names a file and line.

## Coding Waboose integration

Coding Waboose receives two forms of evidence:

1. Typed registry lessons and Crucible receipts.
2. Conservative source-shape findings from `scan_source_for_review_lessons()`.

Source-shape findings are marked probable and carry no repair authority. They focus Codex, Hermes, or manual investigation on recurring review classes while exact tests and runtime verification decide whether a defect exists.

## Crucible replay

The PR #164 registry contains adversarial scenarios for authority aliases and protected overrides; order-dependent digesting and truncate-before-sort; count-only bounds; noncanonical source paths and encoded URI separators; schema/runtime drift; unwired regressions and stale evidence claims; implicit basis changes and nested-unit double application; and noncanonical interchange acceptance.

Each replay emits a typed receipt containing the invoked lesson, finding IDs, code slice/candidate, violated invariant, suggested repair, required regression, confidence, and provenance.

## Security and authority invariants

```yaml
external_reviewer_is_teacher_signal: true
external_reviewer_is_patch_authority: false
review_lesson_is_source_truth: false
crucible_receipt_is_merge_authority: false
automatic_fix: false
automatic_commit: false
automatic_push: false
automatic_pull_request: false
automatic_merge: false
human_review_required: true
patch_authority: exact_source_spans_and_hashes_only
```

Unknown detector IDs, malformed paths, symlink/path escapes, oversized payloads, non-boolean evidence flags, false current-head claims, duplicate lesson IDs, noncanonical registry ordering, registry digest drift, and schema/runtime contract violations fail closed.

## CLI

```bash
python -m aura_coding_waboose_review_lessons_cli summary
python -m aura_coding_waboose_review_lessons_cli crucible
python -m aura_coding_waboose_review_lessons_cli detect \
  detect_authority_aliases candidate.json
python -m aura_coding_waboose_review_lessons_cli normalize review.json --current-head <sha>
python -m aura_coding_waboose_review_lessons_cli scan-source aura_spatial_scene.py
```

`scan-source` validates a canonical repository-relative path and resolves it beneath the repository root before reading, so traversal and symlink escapes fail closed.

## Verification

Focused verification compiles and lints every new module, validates the Draft 2020-12 schema, compares schema/runtime acceptance, runs the new and retained Waboose tests, replays all Crucible scenarios, and runs an Aura-native harness over Agent Bridge, atomic inventory, Emergent Evidence, Council V3, proposal-only Surgeon controls, and Coding Waboose.

The focused workflow is `.github/workflows/aura-review-learning.yml`. A configured workflow is not a passed workflow; results must remain bound to the exact observed commit and run.
