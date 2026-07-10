# Aura Coding Workbench Orchestrator

## What This Is

The Coding Workbench Orchestrator turns the Native Cockpit into a coding-native workbench for human-agent software engineering. It uses practical coding language: open workspace, scope task, filter context, localize code, rank regions, slice context, build change graph, detect refactor candidates, split work, create act capsules, stage patch, run tests, verify patch, review, prepare PR.

## Workflow

```
OPEN_WORKSPACE → SCOPE_TASK → FILTER_CONTEXT → LOCALIZE_CODE →
RANK_CODE_REGIONS → SLICE_CONTEXT → BUILD_CHANGE_GRAPH →
DETECT_REFACTOR_CANDIDATES → SPLIT_WORK → CREATE_ACT_CAPSULES →
PREPARE_AGENT_HANDOFF → STAGE_PATCH → RUN_TESTS → VERIFY_PATCH →
HUMAN_REVIEW → PR_READY
```

Plus: NEED_TOPOLOGY_REPAIR, BLOCKED_SECURITY_RISK

## Topology Health

The workbench validates CODEMAP topology before any graph operation. If topology has 0 nodes, it routes to NEED_TOPOLOGY_REPAIR and blocks change graph generation.

## Invariants

- `patch_authority: "exact_source_spans_and_hashes_only"`
- `vsa_patch_authority: false`
- All advisory layers (MUSIC, DREAM, QDKT, JSpace, VSA, ST3GG) remain non-authoritative
- Human approval required before patch, commit, push, or PR
