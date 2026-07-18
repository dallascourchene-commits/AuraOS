# Coding Waboose V1

**Coding Waboose** is Aura's graph-guided, evidence-bound, breadboarded code-review organ for Aura-native workers and external coding agents such as Codex, Hermes, Claude Code, Gemini CLI, or any MCP client.

The project name uses the founder-selected spelling **Waboose**. The widely documented Ojibwe/Anishinaabemowin dictionary spelling for rabbit or snowshoe hare is **waabooz**; the product spelling is retained as a named Aura surface rather than presented as a standardized dictionary form.

Coding Waboose is not a second patch executor. It reviews a change, computes its cascading impact, turns run-specific review concerns into temporary diagnostic circuits, allows a replaceable coding agent to investigate those circuits, corroborates findings against exact evidence, and compiles eligible findings into bounded Aura Forge repair requests.

## Core principle

```text
Aura computes exact evidence and graph slices.
The coding agent supplies investigative focus.
The Coding Breadboard simulates diagnostic circuits.
Verification proves.
A human authorizes repair or risk acceptance.
```

A coding agent does not author the authoritative call graph, mark its own finding proven, edit production files through Waboose, or merge a repair.

## End-to-end pipeline

```text
objective + diff/range/workspace
  → exact changed files and changed symbols
  → bidirectional topology impact slice
  → standard deterministic scans
  → run-specific focus directives
  → diagnostic Coding Breadboard
  → bounded coding-agent investigation
  → exact-source corroboration
  → precision-first ranking and deduplication
  → human review packet
  → optional Aura Forge repair request
  → separate staged implementation and verification
```

Lifecycle:

```text
FRAME
→ DIFF
→ SLICE
→ SCAN
→ INVESTIGATE
→ CORROBORATE
→ RANK
→ DECIDE
→ REPAIR_HANDOFF
→ DISSOLVE
```

## Why the Coding Breadboard matters

The recently introduced Planning Board/Coding Breadboard architecture is not merely a visualization. It gives Coding Waboose a typed, out-of-order, mockable, bidirectionally planned, evidence-grounded, governance-aware intermediate representation for review.

Each `ReviewFocusDirective` becomes one temporary diagnostic component with:

- typed inputs for the changed source, impact graph, and review hypothesis;
- explicit connected evidence references;
- explicit mocks when a dependency or proof input is unavailable;
- forward paths from changed code to possible consequences;
- backward proof requirements from a proposed finding to the evidence needed to justify repair;
- required capabilities and verifier receipts;
- proposal-only authority and reversible/idempotent semantics.

The diagnostic circuit uses Aura's Board Continuity levels:

```text
BC0 STRUCTURAL   components and fallback paths are valid
BC1 TYPED        ports, effects, and verifier contracts are declared
BC2 CONSTRAINED  review-only policy and resource constraints are resolved
BC3 GROUNDED     exact source and topology references are bound
BC4 AUTHORIZED   the component is explicitly classified as review-only/no-execution
BC5 VERIFIED     the declared diagnostic inspections have bound receipts
```

A component can be useful before it is powered:

```yaml
status: CONNECTED_GROUNDED_UNPOWERED
continuity: BC4_AUTHORIZED
execution_authority: false
```

If a target suggested by the agent cannot be resolved, Waboose records an explicit mock:

```yaml
status: MOCKED_GROUNDED_UNPOWERED
mocked_input: unresolved_impact_target
invented_graph_edge: false
```

An energized component means the declared inspection was performed and its receipts were bound. It does **not** mean a defect exists, the finding is confirmed, or a repair is authorized.

Circuit states:

- `GROUNDED_DIAGNOSTIC_CIRCUIT_UNPOWERED`
- `PARTIALLY_ENERGIZED_DIAGNOSTIC_CIRCUIT`
- `VERIFIED_DIAGNOSTIC_CIRCUIT`

## What Aura computes

Coding Waboose uses repository facts rather than asking a language model to reconstruct them:

- exact changed files and zero-context diff ranges;
- changed Python classes/functions and stable source digests;
- forward callees/dependencies and reverse callers/dependents;
- import, call, and shared-resource edges already present in Aura topology;
- bounded related-file and test manifests;
- repository-local coding and architecture instructions;
- deterministic parser, static-tool, and test evidence;
- evidence status, deduplication, ranking, and repair eligibility;
- diagnostic breadboard connectivity, mocks, continuity, and receipts.

Topology remains navigation evidence. Exact source, hashes, tool results, tests, runtime traces, and verifier output remain authority.

## What a coding agent contributes

An agent can supply a focus directive such as:

```json
{
  "name": "fail_closed_dependency_packets",
  "question": "Can a malformed bridge or session packet escape the facade or preserve stale success state?",
  "risk": "correctness",
  "direction": "callees",
  "target_patterns": ["get(", "status", "ok", "Mapping"],
  "required_evidence": [
    "exact_source",
    "malformed_dependency_packet",
    "regression_test"
  ],
  "suggested_tools": ["pytest"],
  "max_depth": 2,
  "max_nodes": 80
}
```

Aura also infers focus directives from the objective, diff, changed symbols, invariants, and risk map. V1 includes focused review families for:

- general correctness and control flow;
- callers, callees, tests, schemas, and shared-resource impact;
- test adequacy and malformed input boundaries;
- credential redaction and usage-token preservation;
- fail-closed dependency packets and exception behavior;
- schema/runtime/documentation parity;
- duplicate-run identity and session-state isolation;
- filesystem, ref, command, and export boundaries;
- non-mutation and human-authorization invariants;
- generated CODEMAP/topology/document consistency.

## Standard deterministic scans

V1 has local, bounded checks for:

- Python syntax errors;
- mutable default arguments;
- bare or silently swallowed broad exceptions;
- `eval`/`exec` use;
- `subprocess` with `shell=True`;
- blocking subprocess calls inside async functions;
- unsafe `yaml.load` use;
- removed-symbol call sites;
- changed function signatures that direct dependent calls no longer satisfy;
- `git diff --check` failures;
- Ruff diagnostics when Ruff is locally installed;
- Bandit diagnostics when Bandit is locally installed;
- focused pytest regressions selected from changed and topology-related files.

Coding Waboose does not silently download rule packs or invoke a cloud scanner. Semgrep, CodeQL, Joern, tree-sitter, ast-grep, code-property-graph, dynamic-slicing, and runtime-trace analyzers belong behind explicit local capability adapters with pinned configuration, recorded versions, and separate budgets.

## Evidence ladder and false-positive control

Findings are ranked by evidence rather than model confidence alone:

1. failing test, runtime reproduction, or bounded trace — `confirmed`;
2. deterministic parser/static-tool result — `confirmed`;
3. exact signature/call-site or graph/source combination — `probable` or `corroborated`;
4. coding-agent finding whose excerpt matches the exact source anchor — `corroborated`;
5. uncorroborated agent hypothesis — `advisory`.

In `precision` profile, low-confidence or advisory findings are suppressed from the primary packet but remain countable for audit.

## Profiles

- `precision`: high signal; confirmed/corroborated findings and strong probable defects only.
- `balanced`: broader findings with a minimum confidence threshold.
- `exhaustive`: all retained findings and the broadest locally configured adapters.

## Request modes

### Git range

```json
{
  "objective": "Review Forge input hardening for malformed dependency packets and authority leakage",
  "mode": "range",
  "base_ref": "main",
  "head_ref": "feature/my-change",
  "profile": "precision",
  "risk_map": ["security", "contract", "concurrency"],
  "invariants": [
    "production_mutation remains false",
    "agent findings cannot self-confirm",
    "all delegated packets fail closed"
  ]
}
```

### Workspace

```json
{
  "objective": "Review my current staged, unstaged, and untracked changes",
  "mode": "workspace",
  "profile": "balanced"
}
```

### Explicit files

```json
{
  "objective": "Review these modules without a Git range",
  "mode": "files",
  "changed_files": [
    "aura_coding_waboose.py",
    "aura_coding_waboose_breadboard.py"
  ],
  "run_tests": false
}
```

## CLI

One-shot deterministic review:

```bash
python aura_coding_waboose_cli.py run --request waboose_request.json
```

Compile only:

```bash
python aura_coding_waboose_cli.py prepare --request waboose_request.json
```

Long-lived external agents should use MCP so review state and breadboard receipts remain in one server process.

## MCP tools

The Agent Arena MCP server exposes:

- `aura_waboose_prepare`
- `aura_waboose_scan`
- `aura_waboose_agent_packet`
- `aura_waboose_submit_findings`
- `aura_waboose_finalize`
- `aura_waboose_status`

Typical agent loop:

```text
1. aura_waboose_prepare(request)
2. aura_waboose_scan(review_id)
3. aura_waboose_agent_packet(review_id, include_source=true)
4. inspect the bounded source, impact graph, and diagnostic breadboard
5. aura_waboose_submit_findings(review_id, findings)
6. aura_waboose_finalize(review_id)
7. a human selects a Forge repair request or rejects/accepts the risk
```

## Finding contract

An agent finding must contain:

- category and severity;
- concise title and defect explanation;
- exact repository-relative file and line;
- an evidence excerpt near that line;
- concrete impact;
- bounded fix direction;
- optional reproduction, related files/symbols, and focus-directive IDs.

When a finding lists `focus_directive_ids`, an exact-source-corroborated finding may energize those breadboard components. Waboose still ignores attempts to set `confirmed=true` or `status=confirmed`; Aura assigns evidence status.

## Forge handoff

The final packet can include `forge_repair_requests`. Each request contains:

- a finding-specific objective;
- exact target file;
- acceptance criteria;
- risk map;
- non-mutation/human-review constraints;
- Waboose contract/finding lineage and evidence.

A handoff is not a patch. Forge must prepare its own Coding Arena evidence contract, stage a candidate in the canonical boundary, run verification, and stop for human review.

## Authority boundary

Every result preserves:

```yaml
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

## Canonical owners

- `aura_coding_waboose.py` — public product owner and review lifecycle;
- `aura_coding_waboose_breadboard.py` — Planning Board diagnostic-circuit compiler;
- `aura_review_arena.py` — internal reusable diff, topology, scan, corroboration, and ranking engine;
- `aura_coding_waboose_cli.py` — one-shot CLI;
- `schemas/aura_coding_waboose_contract.schema.json` — public product envelope;
- `schemas/aura_review_contract.schema.json` — internal review-engine contract;
- Agent Bridge persistence/MCP tools — long-lived external-agent access.

## Research and future adapters

The design basis and source survey are recorded in:

```text
.aura/research/AURA_CODING_WABOOSE_RESEARCH_2026-07-17.md
```

Planned extensions include polyglot tree-sitter/ast-grep analysis, local SARIF/RDFormat ingestion, CodeQL/Joern code-property-graph tools, dynamic and causal slicing, specialist Waboose Council roles, an independent false-positive judge, mutation-seeded hidden defects, and AACR-Bench-compatible precision/recall/token-cost evaluation.
