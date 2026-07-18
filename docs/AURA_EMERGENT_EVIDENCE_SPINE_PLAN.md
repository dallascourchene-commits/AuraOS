# Aura Emergent Evidence Spine — Architecture Plan

Status: implementation plan for post-Waboose item 2

## Purpose

Turn Aura's existing read-only emergent-capability discovery into one canonical, evidence-bound spine usable by:

- Coding Arena and Aura Forge planning;
- Coding Waboose review focus;
- Human Agent and Observatory review surfaces;
- Agent Bridge / MCP clients such as Codex and Hermes;
- the arXiv and repository research lanes.

The spine is not another planner, truth store, patch engine, verifier, or learned-memory owner. It composes existing canonical owners.

## Canonical owner sequence

```text
Capability Connectome V2
  → Capability Resolver V2
  → complete atomic-function inventory
  → exact CodeTopo dependency closure
  → bounded Emergent Capability Auditor
  → Coding Research Lane / arXiv query plan
  → Arena-specific evidence projections
  → Coding Waboose + verifier + human decision
```

### Capability Connectome

The Capability Connectome decides which Aura-native capabilities belong in the requested circuit. Connectome V2 pins nodes and paths with stable digests and execution traits. It remains advisory and never grants patch authority.

### Atomic functions

The complete repository inventory is computed from `CodeTopoAnchor`, which already indexes functions, async functions, methods, async methods, and nested functions with:

- exact repository-relative file;
- exact line span;
- source and file hashes;
- parent/qualified symbol identity;
- calls, imports, and decorators.

The spine exposes this as `build_atomic_function_inventory()`. The complete set is always computed first; external packets may emit only a bounded subset while retaining the full count and inventory digest.

### Automatic focus

Every spine invocation follows this order:

```text
objective / explicit targets
  → resolve the Connectome capability path
  → enumerate every atomic callable
  → bind exact target and implementation symbols
  → expand only bounded callers, callees, imports, tests, and related functions
  → extract exact code-block slices and hashes
  → run emergent-property reasoning only over that closure
  → identify evidence and research gaps
  → create Coding Waboose review directives
  → project the same evidence packet to the requested Arena
```

Aura must never ask an LLM to invent the atomic inventory, source spans, call graph, dependency graph, or proof status.

## Arena projections

### Coding Arena

- exact target files and symbols;
- acceptance criteria;
- risk map and authority constraints;
- related tests;
- Waboose focus directives.

### Coding Waboose

- atomic-closure integrity review;
- emergent-finding verification questions;
- authority and research-truth invariants;
- bounded graph depth and node budgets.

### Human Agent

- grounded findings and future potentials;
- evidence/research gaps;
- questions requiring judgment;
- no automatic acceptance or implementation.

### Agent Bridge

- compact capability path;
- selected atomic functions;
- exact source slices and hashes;
- dependency edges and tests;
- bounded token estimate.

### Research lane

- objective and capability-derived arXiv query plans;
- offline manifest evidence when available;
- explicit advisory-only truth class;
- `ArenaResearchBridge.search_arxiv` as the bounded online executor.

## Authority invariants

```yaml
connectome_is_advisory: true
atomic_source_spans_are_exact_evidence: true
emergent_findings_are_patch_authority: false
external_research_is_patch_authority: false
coding_waboose_reviews: true
verification_proves: true
human_authorizes: true
production_mutation: false
automatic_fix: false
automatic_commit: false
automatic_push: false
automatic_pull_request: false
automatic_merge: false
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
```

## Implementation capsules

1. **Core spine** — Connectome routing, full atomic inventory, exact dependency closure, bounded source slices, emergent audit, research projection, and Waboose directives.
2. **Coding and Agent Bridge wiring** — explicit MCP tools plus optional emergent enrichment during Coding Arena preparation.
3. **Human Agent and research wiring** — local HTTP endpoint, existing emergent-results persistence, workflow evidence projection, and arXiv research execution handoff.
4. **Canonical documentation and regression closure** — README, USER_GUIDE, ARCHITECTURE, CODEMAP/topology regeneration, full manual audit, final Coding Waboose pass, and CodeRabbit attempt.

A Coding Waboose review is required after every capsule and once more over the complete PR before merge.
