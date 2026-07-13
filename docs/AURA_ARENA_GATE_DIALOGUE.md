# Aura Arena Gate Dialogue

## Purpose

The Human Agent Arena now supports ordinary-language human intervention at every guided gate.

A human may:

1. select a bounded topology node;
2. inspect its exact file, symbol, source range, dependencies, callers, tests, and visible risks;
3. enter a new intention, concern, correction, or question;
4. ask Aura to address it from the current workflow gate;
5. review Aura's proposed interpretation;
6. approve or reject that proposal;
7. allow only the existing guarded workflow to attempt the next gate.

This makes the Arena collaborative rather than a fixed wizard while preserving explicit authority boundaries.

## Interaction model

```text
current guarded gate
+ selected topology node
+ bounded neighbours and tests
+ human's new ordinary-language intent
                    |
                    v
      deterministic local intent compiler
                    |
                    v
     six-slot packet + machine route + gate state
                    |
                    v
 optional Fireworks-first external voice when configured
                    |
                    v
         PENDING_HUMAN_APPROVAL proposal
                    |
          human approves or rejects
                    |
                    v
 existing guarded WFST may attempt the next action
```

The external model never chooses the authoritative action. The deterministic Human Agent WFST remains authoritative.

## Selected-node anchoring

The dialogue packet contains presenter-safe topology metadata only:

- exact node identifier;
- label;
- repository path;
- symbol;
- node type;
- exact line range where available;
- projection truth class;
- bounded dependencies;
- bounded callers;
- connected tests;
- bounded graph relations;
- candidate risk labels.

Source contents are not copied into the dialogue packet merely because a node is selected.

The topology visualization remains an orientation and selection surface. It has no patch authority.

## Gate stages

The same comment and approval surface follows the user through:

```text
INTAKE -> FRAME -> GROUND -> PLAN -> ACT -> PROVE -> DECIDE
```

### INTAKE

The user can ask how a selected node or task should enter the investigation.

Approval may load or continue with a bounded task. It grants no workflow or patch authority by itself.

### FRAME

The user can correct or refine the objective around the selected evidence.

Approval allows the existing `set_objective` guard to attempt framing.

### GROUND

The user can ask Aura to inspect a file, symbol, dependency, caller, test, or uncertainty.

Approval allows the existing `ground_context` action to run its topology inspector.

### PLAN

The user can specify constraints, acceptance criteria, exclusions, or concerns about the selected node.

Approval allows `prepare_capsule` to compile the bounded Arena handoff.

### ACT

The user can comment on how a candidate change should interact with the selected node and dependencies.

A valid candidate unified diff is still required. Approval cannot fabricate the missing diff or bypass the staging gate.

### PROVE

The user can ask which focused tests or verifier evidence are required for the selected topology evidence.

Approval allows the existing sequence:

```text
run_tests -> verify_patch
```

A failed test or verifier remains a denial.

### DECIDE

The user can request a final evidence and risk summary for the selected node.

Approval may attempt:

```text
check_hotswap -> record review-only decision -> export review packet
```

The demonstration decision explicitly does not approve production promotion or merging.

## Proposal identity and stale-context protection

Every Aura response receives a proposal identifier and binds to:

- workflow identifier;
- current guarded phase;
- workflow phase/evidence digest;
- guided-stage name;
- selected-node digest;
- human-comment digest;
- deterministic intent trace;
- recommended guarded action.

Approval fails closed when:

- the workflow instance changes;
- the workflow phase changes;
- the evidence/phase digest changes;
- the guided stage changes;
- the selected topology node or bounded context changes;
- no current node is supplied for a node-anchored proposal.

This prevents an approval given for one file or gate from being reused for another.

## Model behavior

When an external provider is configured, Aura uses the established egress priority.

Fireworks AI is first. The `cheap` role resolves to:

```text
accounts/fireworks/models/deepseek-v4-flash
```

The external model is used only as Aura's explanatory voice. Its response is advisory and must remain grounded in the deterministic packet.

When no external provider is configured or an egress call fails, Aura produces a deterministic local response from:

- the current gate guidance;
- admitted and blocked actions;
- the selected node and bounded neighbours;
- the locally compiled six-slot intent;
- the machine route.

The feature therefore remains usable without an LLM.

## Approval meanings

Two different approvals must never be conflated.

### Gate-dialogue approval

```yaml
meaning: allow the existing guarded workflow to attempt the next gate
patch_authority: false
production_approval: false
merge_approval: false
```

### Final production or merge approval

This is outside the gate-dialogue approval and remains blocked in the showcase.

```yaml
production_mutation: false
automatic_commit: false
automatic_push: false
automatic_pull_request: false
automatic_merge: false
automatic_grammar_promotion: false
```

## APIs

```text
GET  /api/showcase/human/gate/status
POST /api/showcase/human/gate/address
POST /api/showcase/human/gate/approve
```

### Address packet

```json
{
  "comment": "Check whether this selected renderer can use stale state.",
  "stage_hint": "GROUND",
  "node_context": {
    "selected_node": {
      "id": "node-id",
      "file_path": "aura_showcase/civic.js",
      "symbol": "refreshMap",
      "line_range": [120, 180]
    },
    "dependencies": ["project_map_manifest"],
    "callers": ["renderCivicGuide"],
    "tests": ["tests/test_aura_showcase_guided_interface.py"]
  },
  "prefer_model": true
}
```

### Approval packet

```json
{
  "proposal_id": "GDP-...",
  "approved": true,
  "stage_hint": "GROUND",
  "current_node_context": {},
  "reviewer": "human_operator",
  "note": "Proceed to the existing guarded action only."
}
```

## Authority invariants

```yaml
selected_topology_patch_authority: false
external_model_action_authority: false
gate_dialogue_patch_authority: false
approval_scope: existing_guarded_workflow_only
exact_source_authority: source_spans_and_hashes
human_approval_required: true
production_mutation: false
automatic_commit: false
automatic_push: false
automatic_merge: false
```
