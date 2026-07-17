# AuraOS Architecture

> Canonical compact architecture anchor for humans and AI agents

**Architecture audit:** through merged PR #133 and the canonical Human Agent, Observatory, and Crucible documentation sync.  
**CODEMAP rule:** regenerate from the current tree with `python3 aura_codebase_navigator.py` after source or architecture changes.  
**Topology source:** `compiled_deep_topology`.

## 1. Architectural identity

AuraOS is a sovereign, local-first, Arena-based cognitive operating substrate.

It is not a single model, conventional chatbot, monolithic autonomous agent, visual wrapper around an LLM, or a system where semantic similarity may authorize changes.

```text
OBJECTIVE
  → structured IntentPacket
  → semantic and machine FST routing
  → capability discovery and reuse
  → exact grounded micro-context
  → bounded Arena
  → temporary capability leases / ephemeral organs
  → optional external workers
  → exact verification
  → human or community approval
  → governed memory, telemetry, and dissolution receipts
```

> **Meaning may guide retrieval. Only grounded evidence and authorized governance may grant authority.**

## 2. Truth and authority

### Advisory cognition

These layers may discover, rank, compress, remember, or visualize:

- VSA / HDC resonance;
- semantic similarity;
- DREAM and DREAM-lite;
- QDKT and JSpace state;
- ST3GG recall handles;
- MUSIC and MITOSIS;
- visual topology;
- summaries and screenshots;
- emergent-capability hypotheses;
- inferred or ghost edges;
- external research sidecars.

They may not authorize production mutation, policy activation, civic decisions, restricted-data access, or cultural-profile activation.

### Authoritative evidence

Authority is grounded in:

- exact repository-relative paths;
- exact symbols and semantic IDs;
- source line ranges;
- content and signature hashes;
- current CODEMAP and compiled topology facts;
- tests and verifier outputs;
- exact source snapshots and sidecars;
- manifests and boundary contracts;
- capability leases and consent records;
- human, teacher, speaker, or community approval;
- applicable legal and governance authority.

```yaml
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
```

Unknown, ungrounded, expired, ambiguous, or unauthorized actions fail closed.

## 3. Architectural planes

AuraOS is organized into eight cooperating planes:

1. human and community intent;
2. intent compilation and FST routing;
3. self-model, capability discovery, and grounding;
4. advisory cognition and compression;
5. Arenas and ephemeral organs;
6. external workers and controlled egress;
7. verification, approval, memory, and observability;
8. domain deployments such as language, civic, research, mesh, and AR.

Presentation is never authority. A route may constrain or reject work, but it cannot create permission that was never granted.

## 4. Human Agent, Observatory, Experience, and Crucible

Four surfaces are connected but must not collapse into one another:

```text
OBSERVATORY
  explain and bound
    → HUMAN AGENT ARENA
      admit and execute
        → EXPERIENCE LEDGER
          record verified outcome
            → CRUCIBLE
              test empirical uncertainty and propose
```

### Aura Observatory

The Observatory explains how an intention was parsed, routed, localized, compressed, and bounded. It is review-only.

It may carry objective, exact files and symbols, source spans and hashes, focused tests, route decisions, compressed context, and selected topology identifiers into a Human Agent handoff.

It does not:

- stage changes;
- execute workers;
- mutate production;
- create leases;
- grant authority;
- make evidence eligible for learning by itself.

Primary handoff implementation:

- `aura_showcase_observatory_handoff.py`

### Human Agent Arena

The Human Agent Arena is the governed command centre:

```text
FRAME → GROUND → PLAN → ACT → PROVE → DECIDE
```

Actions pass WFST admission and lifecycle checks. Exact grounding, granted capabilities, verifier requirements, and human approval remain authoritative.

Context may be constructed before admission, but active workflow evidence is committed only after the guarded operation succeeds. Denied operations must leave workflow evidence unchanged.

Primary implementation:

- `aura_human_agent_arena.py`
- `aura_human_agent_arena_server.py`
- `aura_human_agent_wfst_adapter.py`
- `aura_arena_wfst_runtime.py`
- `aura_arena_tool_runtime.py`

### Experience Ledger

Governed actions may produce sanitized `ArenaExperience V3` records after execution and verification. Experience records preserve objective, route, action, evidence, outcome, costs, and lifecycle context without granting automatic learning authority.

Primary implementation:

- `aura_arena_experience.py`
- `aura_arena_experience_ledger.py`

### Learning Arena / Crucible

The Crucible mines only complete verified experience records.

```text
ArenaExperience V3
  → TRAIN
  → VALIDATION
  → SHADOW
  → CRYSTALLIZATION_PROPOSED
  → verifier and human review
```

The pre-experience learning handoff is explicitly:

```yaml
status: AWAITING_VERIFIED_EXPERIENCE
eligible_for_crucible: false
```

The allowed learned surface is limited to `soft_weight_profile.empirical_uncertainty`.

The Crucible cannot alter hard guards, states, transitions, capabilities, risk classes, verifier requirements, source code, active grammar manifests, or consent rules. It cannot automatically commit, push, open a pull request, or merge.

Primary implementation:

- `aura_arena_crucible.py`
- `aura_crucible_validation.py`
- `aura_arena_experience.py`
- `aura_arena_experience_ledger.py`

## 5. Emergent Refactor Workspace

Merged PR #133 adds a governed Human Agent evidence workspace for Aura's emergent-property reports.

```text
stored emergent run
  → exact provenance validation
  → objective-aware finding search
  → optional bounded public research
  → selected finding and evidence IDs
  → content-addressed refactor packet
  → guarded Human Agent admission
  → workflow evidence
```

Implementation properties:

- run, finding, research, and packet identities are content-addressed from stable content;
- exact seed byte sizes and SHA-256 hashes are verified;
- stored files are authoritative over secondary JSONL indexes;
- malformed indexes are reconciled without duplicating records;
- missing selected IDs fail closed;
- malformed identifiers return structured errors;
- network research has bounded total deadlines and result limits;
- PDF and README sidecars are untrusted text;
- external links are restricted to HTTP and HTTPS;
- special research and workspace executions use normalized tool-run records;
- workflow state is not mutated before admission.

Primary implementation:

- `aura_emergent_refactor_workspace.py`
- `aura_arena_research_bridge.py`
- `aura_human_agent_arena_server.py`
- `aura_human_agent_arena/emergent.js`
- `aura_human_agent_arena/emergent.css`
- `tests/test_aura_emergent_refactor_workspace.py`

Seed evidence:

```text
Aura_Memory/emergent_results/seed_runs/2026-07-16/
```

Emergent findings and research are advisory evidence. They become actionable only after exact local grounding, admission, bounded execution, and verification.

## 6. Council–Surgeon architecture

Aura separates architectural deliberation from bounded implementation.

```text
Selective Council V3
  → architecture
  → dependencies and interfaces
  → invariants and sequence
  → rollback and cost when justified

Sliced Surgeon
  → exact-file patch
  → focused tests
  → bounded repair
```

Scope and tests are universal critic lanes. Sequence, continuity, rollback, and cost lanes are admitted from measured plan structure and risk rather than called uniformly.

Escalation occurs when an interface, dependency, or invariant is invalidated, downstream scope expands materially, or the local repair budget is exhausted.

Primary contracts:

- `aura_architect_council_v3.py`
- `aura_refactor_output_record.py`
- `aura_refactor_patch_evaluator.py`
- `aura_refactor_patch_evaluator_v2.py`
- `aura_code_quality_registry.py`
- `schemas/aura_refactor_output_record.schema.json`

`AURA_REFACTOR_OUTPUT_RECORD_V1` preserves prompt and patch identity, estimated and provider-reported usage separately, exact tests and gates, failed gates, working status, disposition, and measurement completeness.

## 7. Evidence and observability

Aura distinguishes:

1. executable gate evidence;
2. deterministic comparative token proxies;
3. estimated structural projections;
4. discovery and capacity scans.

Current evidence includes:

- context localization: **89.04% lower** total-token proxy with quality `+0.0057`;
- Selective Council V3: **32.83% lower** total proxy and **33.33% fewer calls** than Council V2 with the same accepted plan, patch, and quality;
- executable fixture: visible `3/3`, hidden `3/3`, regression `2/2`, `WORKING`, `ACCEPTED`;
- real AuraOS refactor trial: `32/32`, `35/35`, and `21/21` passing groups;
- State Ledger continuity: **96.19% less** step-7 context with preservation `1.0000` and drift `0.0000`;
- emergent scan: `708` Python files, `10,815` nodes, `20,764` edges, `15` probes, `0` failures;
- grounded capacity projections: `7` probes, all still `NEEDS_GROUNDING`;
- shared grounding projection: **53.1936% projected savings**, classified `ESTIMATED` and not provider billing.

Unknown cost stays unknown. Estimated structural projections cannot be relabelled as measured provider savings. Discovery recurrence cannot be relabelled as implementation correctness.

## 8. Source-of-truth order

When sources conflict:

1. exact source and schemas;
2. tests and verifier artifacts;
3. healthy current CODEMAP and compiled topology;
4. exact snapshots, sidecars, and ledgers;
5. manifests, leases, consent, and boundary contracts;
6. current subsystem documentation;
7. README and architecture summaries;
8. historical reports and extracted text.

## 9. Navigation protocol

1. Read `README.md`.
2. Read `.aura/ARCHITECTURE.md`.
3. Read `.aura/CODEMAP.md`.
4. Query only the relevant files and symbols.
5. Open exact source slices plus immediate topology neighbours.
6. Verify hashes, tests, and contracts before changing code.
7. Regenerate CODEMAP after successful source or architecture changes.

```bash
python3 aura_codebase_navigator.py --query "human agent emergent research"
python3 -m aura_agent_arena_cli read-slice \
  --file aura_emergent_refactor_workspace.py \
  --symbol EmergentRefactorWorkspace
```

Never load the entire repository or `aura_node.py` for ordinary agent work.

## 10. Architectural invariants

- Humans and communities retain consequential authority.
- External models are workers, not governors.
- Intent is a request, not permission.
- Grammar and routes constrain work but do not create authority.
- Semantic and VSA layers are advisory.
- Patch authority requires exact spans and hashes.
- Tools receive minimum capabilities through temporary leases.
- Failed or denied actions do not mutate governed state.
- Observatory output is review evidence, not execution authority.
- Emergent findings are hypotheses until grounded and verified.
- Crucible proposals never self-promote.
- Cost classes and claim boundaries remain explicit.
- Restricted cultural and personal data remain inside consent and governance boundaries.
- Temporary organs and Arenas produce lifecycle and dissolution receipts.
