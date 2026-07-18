# Coding Waboose V1.1

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

### Semantic integrity rule packs

V1.1 adds deterministic semantic review packs for defect classes that ordinary
syntax checks and linters often miss:

- `strict_input_types` — catches truthiness-based parsing of declared boolean options;
- `symbol_identity` — preserves qualified identities such as `Worker.run` at every exact target boundary;
- `source_integrity` — requires exact Python decoding and fail-closed repository inventories;
- `bounded_graph_integrity` — prevents dependency edges from escaping bounded node closures;
- `test_evidence_preservation` — keeps test callable nodes and their call/test edges in bounded audit evidence.

Each pack has positive and false-positive regression tests. A detector receipt
means the pack actually executed over exact source; it is not a claim that a
defect exists.

### Semantic completeness gate

`aura_coding_waboose_cli.py run` is a deterministic-only path. It may complete a
custom focus directive only when a registered deterministic semantic pack truly
implements that directive. Any unsupported agent-origin directive remains
unverified and blocks finalization:

```yaml
ok: false
error: semantic_review_incomplete
status: BLOCKED_INCOMPLETE_SEMANTIC_REVIEW
forge_repair_requests: []
automatic_merge: false
```

A custom semantic question can otherwise be completed only by an actual coding
agent submission that Aura corroborates against exact current source. Passing
tests or linters alone can no longer masquerade as completion of an unrelated
semantic question.

Coding Waboose does not silently download rule packs or invoke a cloud scanner. Semgrep, CodeQL, Joern, tree-sitter, ast-grep, code-property-graph, dynamic-slicing, and runtime-trace analyzers belong behind explicit local capability adapters with pinned configuration, recorded versions, and separate budgets.

## Learning from successful CodeRabbit reviews

CodeRabbit is treated as an external **teacher signal**, never as patch,
verification, or merge authority. A lesson enters Waboose memory only when:

1. the CodeRabbit review completed successfully;
2. its review is bound to the exact pull-request head SHA;
3. its repository-relative file and line range still exist at that head;
4. any supplied evidence excerpt matches the exact source window;
5. Python source is decoded exactly with its declared encoding;
6. the lesson is deduplicated against prior grounded episodes.

The learning path composes Aura's existing organs:

```text
successful CodeRabbit finding
  → exact reviewed-head/source grounding
  → AST/source signature
  → Capability Resolver + Capability Connectome path
  → DREAM-lite similarity ranking against prior review lessons
  → QDKT observation and causal-update event
  → repeated-confirmation confidence update
  → QDKT crystal after the governed threshold
  → retrieval before a future Waboose review
  → current-source reproof before any repair handoff
```

Known recurring defect families reinforce deterministic semantic rule packs.
Unknown recurring patterns may surface only as `probable` advisory findings;
they cannot generate a Forge repair request without fresh current-source
corroboration.

### Cross-PR persistence and trust boundary

The GitHub integration uses two workflows:

- `coderabbit-waboose-learning.yml` receives a CodeRabbit review event and
  dispatches a trusted learning run on the repository's default branch;
- `coderabbit-waboose-learning-persist.yml` serializes updates to shared
  DREAM/QDKT memory, verifies the exact reviewed SHA, and materializes that head
  as read-only source data.

The trusted default-branch runtime performs the learning. Python from the
reviewed pull request is **never executed**, installed, sourced, or tested by the
learning workflow. The persistent memory is stored outside the repository and
is shared across later pull requests.

CLI:

```bash
python aura_coderabbit_learning_cli.py ingest --review coderabbit_review.json
python aura_coderabbit_learning_cli.py summary
```

Every learning result preserves:

```yaml
teacher: CodeRabbit
teacher_is_patch_authority: false
connectome_is_advisory: true
dream_lite_is_ranking_only: true
qdkt_crystals_are_patch_authority: false
production_mutation: false
automatic_merge: false
human_review_required: true
```

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
- `aura_waboose_learn_coderabbit`
- `aura_waboose_learning_summary`

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
- `aura_coding_waboose_cli.py` — one-shot review CLI;
- `aura_waboose_semantic_rules.py` — deterministic semantic-integrity packs;
- `aura_waboose_learning.py` — exact grounding, Connectome routing, DREAM-lite retrieval, and QDKT learning;
- `aura_coderabbit_learning_cli.py` — external-review lesson ingestion and memory summary;
- `schemas/aura_coding_waboose_contract.schema.json` — public product envelope;
- `schemas/aura_review_contract.schema.json` — internal review-engine contract;
- Agent Bridge persistence/MCP tools — long-lived external-agent access.

## Research and future adapters

The design basis and source survey are recorded in:

```text
.aura/research/AURA_CODING_WABOOSE_RESEARCH_2026-07-17.md
```

Planned extensions include polyglot tree-sitter/ast-grep analysis, local SARIF/RDFormat ingestion, CodeQL/Joern code-property-graph tools, dynamic and causal slicing, specialist Waboose Council roles, an independent false-positive judge, mutation-seeded hidden defects, AACR-Bench-compatible precision/recall/token-cost evaluation, and governed promotion of repeatedly grounded learned patterns into new deterministic rule packs.
