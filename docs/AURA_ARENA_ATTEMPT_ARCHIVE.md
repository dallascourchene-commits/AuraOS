# Aura Arena Attempt Archive

## Purpose

A failed coding attempt is still useful evidence.

The Arena now preserves successful, denied, blocked, and failed attempts so a human can:

- inspect exactly what was attempted;
- review a candidate diff even when it did not stage;
- copy the complete artifact into another conversation or agent;
- copy only the diff for manual editing;
- compare multiple approaches;
- identify recurring verifier or test failures;
- use an earlier attempt as input to a later bounded refactor.

The archive complements the `ArenaExperience` ledger. It does not replace it.

```text
ArenaExperience ledger
  -> machine-observable outcomes for the Crucible and governed learning

Arena Attempt Archive
  -> human-inspectable outputs, diffs, failures, and copy/paste artifacts
```

## What is archived

For each Human Agent or Coding Workbench action, the unified Arena records:

- artifact ID and digest;
- timestamp;
- Arena and workflow IDs;
- current phase;
- requested route and action;
- current objective;
- selected topology node;
- bounded gate-dialogue context;
- sanitized request packet;
- sanitized result packet;
- candidate unified diff when present;
- observable stdout, stderr, logs, test output, verifier output, and diagnostics;
- denial or failure summary;
- missing evidence and remediation;
- whether the attempt completed or failed.

This includes failures such as:

```text
patch rejected
-> archived

tests failed
-> archived

verifier denied
-> archived

worker produced unusable output
-> archived

hard guard blocked the action
-> archived
```

## Human interface

The Human Agent Arena displays an **Arena Attempt Archive** below the gate dialogue.

Each artifact supports:

- **Inspect** — show the complete sanitized record;
- **Copy full artifact** — copy a Markdown packet with objective, topology anchor, human intent, Aura response, failure summary, diff, outputs, request, and result;
- **Copy diff** — copy only the candidate unified diff;
- **Show failed only** — filter the archive to denied and failed work;
- **Refresh archive** — reload persistent records.

## Topology and gate lineage

When the user selected a topology node before the coding attempt, the archive preserves:

- file;
- symbol;
- line range;
- dependencies;
- callers;
- connected tests;
- the human's gate comment;
- Aura's response;
- the approval proposal ID and decision state.

This makes the artifact understandable later, even after the live topology selection has changed.

## Persistence

The default archive is a SQLite database in WAL mode:

```text
Aura_Memory/arena_attempt_artifacts.db
```

The schema supports filtering by:

- Arena;
- workflow;
- action;
- status;
- success or failure;
- creation time.

## Sanitization

Before persistence, the archive uses Aura's existing Arena experience sanitizer.

It removes or redacts:

- API keys;
- access tokens;
- authorization headers;
- passwords;
- private keys;
- cookies;
- hidden chain-of-thought;
- private reasoning;
- scratchpads and internal monologues.

The archive stores observable output, not private model reasoning.

## Reuse contract

An archived attempt may be reused as input to a future refactor, but it remains unverified.

```yaml
reusable_for_refactoring: true
copyable: true
human_inspection: true
verified: false
archived_output_authority: false
patch_authority: false
production_authority: false
learning_authority: false
human_review_required_before_reuse: true
```

A future Arena must re-ground and re-verify the artifact against the current repository state.

Storage never means:

- the patch is correct;
- the patch still applies;
- the tests pass;
- the selected files are current;
- the artifact may bypass a gate;
- the artifact may be committed or merged.

## APIs

```text
GET /api/showcase/human/attempts/status
GET /api/showcase/human/attempts?limit=12
GET /api/showcase/human/attempts?failures_only=true
GET /api/showcase/human/attempts/{artifact_id}
```

Every Human Agent and Coding Workbench POST action routed through the unified showcase returns an `attempt_artifact` summary.

Example:

```json
{
  "attempt_artifact": {
    "ok": true,
    "artifact_id": "ATT-...",
    "status": "DENIED",
    "attempt_ok": false,
    "has_candidate_diff": true,
    "failure_preserved": true,
    "copyable": true,
    "reusable_for_refactoring": true,
    "verified": false,
    "production_authority": false
  }
}
```

## Relationship to the Learning Arena

Failed attempts may eventually inform learning, but the Attempt Archive does not send them directly into the Crucible as trusted knowledge.

```text
failed attempt artifact
-> human inspection
-> possible corrected refactor
-> new governed Arena execution
-> verifier evidence
-> OutcomeVector
-> ArenaExperience record
-> TRAIN / VALIDATION / SHADOW
-> CRYSTALLIZATION_PROPOSED
-> verifier and human review
```

The failed output is preserved immediately, while learning remains evidence-gated.
