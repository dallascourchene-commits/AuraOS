# Aura Arena Guarded-WFST — Phase A2 Live Integration

Status: `DRAFT_REVIEW_REQUIRED`

Phase A2 connects the Phase A guarded-WFST foundation to Aura's live Human Agent and
Coding Workbench surfaces. It does not implement the background Crucible and it does
not promote learned routes.

## Human Agent default path

The Human Agent workflow now routes typed, voice, button, and API actions through
`HumanAgentWFSTController` before invoking the existing `_do_*` action methods.
The old keyword chain is removed from `ingest_command()`.

Free-form text at `FRAME` becomes an objective only after exact state-local and Meta
routing has failed. Therefore `help`, `status`, `what next`, and `why blocked` remain
Meta self-loops and cannot accidentally become objectives.

Direct `execute()` remains for backwards compatibility and internal post-admission
execution. User-facing HTTP routes use `execute_guarded()`.

## Contextual route projection

The server exposes:

```text
GET  /api/human-agent/routes
POST /api/human-agent/workflow/action
POST /api/human-agent/workflow/command
```

Responses include admitted, recommended, blocked, and Meta transitions plus the J1
state packet. The local frontend projects its primary contextual buttons from those
admitted transitions. Blocked transitions show failed guards and missing evidence.

## Coding Workbench integration

`CodingWorkbenchWFSTSession` wraps the existing 18-state state machine and action
functions. `.aura/arena_routes/coding.v1.json` contains one state-local transition for
each legacy `allowed_action`.

The adapter persists only local session state and structured experience. It does not:

- commit;
- push;
- merge;
- open a pull request;
- run an external coding agent automatically;
- mutate the active grammar.

`open_pr` and `generate_pr_command` only create an unexecuted draft PR command packet.
`send_to_agent` only records a returned staged-patch reference after explicit human
approval.

Server routes:

```text
GET  /api/coding-workbench/state
GET  /api/coding-workbench/routes
POST /api/coding-workbench/action
POST /api/coding-workbench/command
```

## Authority remains unchanged

```yaml
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
learned_weight_patch_authority: false
crystallization_patch_authority: false
automatic_grammar_promotion: false
automatic_commit: false
automatic_push: false
automatic_merge: false
```

The WFST admits and ranks transitions. Existing leases, tools, sandboxes, tests,
verifiers, and human review remain the authority for consequential work.
