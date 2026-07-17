# Aura Review Arena V1

Aura Review Arena is a graph-guided, evidence-bound code-review surface for Aura-native workers and external coding agents such as Codex, Hermes, Claude Code, Gemini CLI, or any MCP client.

It is not a second patch executor. It reviews a change, computes its cascading impact, allows a replaceable coding agent to investigate run-specific risks, corroborates every finding against exact source or deterministic evidence, and compiles confirmed findings into bounded Aura Forge repair requests.

## Core principle

```text
Aura computes exact evidence.
The coding agent supplies investigative focus.
Verification proves.
A human authorizes repair or acceptance.
```

The coding agent does not author the authoritative call graph, mark its own findings proven, edit production files through the reviewer, or merge a repair.

## Review pipeline

```text
objective + diff/range/workspace
  → exact changed files and changed symbols
  → bidirectional topology impact slice
  → standard deterministic scans
  → run-specific focus directives
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

## What Aura computes

Aura Review Arena uses repository facts rather than asking a language model to reconstruct them:

- exact changed files and zero-context diff ranges;
- changed Python classes/functions and stable source digests;
- forward callees/dependencies and reverse callers/dependents;
- import, call, and shared-resource edges already present in Aura topology;
- bounded related-file and test manifests;
- repository-local coding/architecture instructions;
- deterministic parser, static-tool, and test evidence;
- evidence status, deduplication, ranking, and repair eligibility.

Topology remains navigation evidence. Exact source, hashes, tool results, tests, and verifier output remain authority.

## What a coding agent contributes

An agent can supply a `focus_directive` such as:

```json
{
  "name": "fail_closed_dependency_packets",
  "question": "Can a malformed bridge or session packet escape the facade or preserve stale success state?",
  "risk": "correctness",
  "direction": "callees",
  "target_patterns": ["get(", "status", "ok", "Mapping"],
  "required_evidence": ["exact_source", "malformed_dependency_packet", "regression_test"],
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

The Arena does not silently download rule packs or invoke a cloud scanner. Semgrep, CodeQL, Joern, tree-sitter, ast-grep, and other analyzers belong behind explicit local capability adapters with recorded tool versions and separate budgets.

## Precision-first evidence ladder

Findings are ranked by evidence rather than model confidence alone:

1. failing test or runtime reproduction — `confirmed`;
2. deterministic parser/static-tool result — `confirmed`;
3. exact signature/call-site or graph/source combination — `probable` or `corroborated`;
4. coding-agent finding whose excerpt matches the exact source anchor — `corroborated`;
5. uncorroborated agent hypothesis — `advisory`.

In `precision` profile, low-confidence or advisory findings are suppressed from the primary review packet but remain countable for audit.

## Profiles

- `precision`: high signal; confirmed/corroborated findings and strong probable defects only.
- `balanced`: broader findings with a minimum confidence threshold.
- `exhaustive`: all retained findings and the broadest locally configured adapters.

## Request modes

### Git range

```json
{
  "objective": "Review the Forge input hardening for malformed dependency packets and authority leakage",
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

Use staged, unstaged, and untracked files:

```json
{
  "objective": "Review my current local changes",
  "mode": "workspace",
  "profile": "balanced"
}
```

### Explicit files

Useful for a synthetic or pre-materialized review:

```json
{
  "objective": "Review these modules without a Git range",
  "mode": "files",
  "changed_files": ["aura_review_arena.py", "tests/test_aura_review_arena.py"],
  "run_tests": false
}
```

## CLI

One-shot deterministic review:

```bash
python aura_review_arena_cli.py run --request review_request.json
```

Compile only:

```bash
python aura_review_arena_cli.py prepare --request review_request.json
```

The in-process CLI subcommands for `agent-packet`, `submit-findings`, `finalize`, and `status` are primarily useful to embedded callers. Long-lived external agents should use the MCP tools so review state remains in one server process.

## MCP tools

The Agent Arena MCP server exposes:

- `aura_review_prepare`
- `aura_review_scan`
- `aura_review_agent_packet`
- `aura_review_submit_findings`
- `aura_review_finalize`
- `aura_review_status`

Typical coding-agent loop:

```text
1. aura_review_prepare(request)
2. aura_review_scan(review_id)
3. aura_review_agent_packet(review_id, include_source=true)
4. inspect only the bounded exact-source/impact packet
5. aura_review_submit_findings(review_id, findings)
6. aura_review_finalize(review_id)
7. human selects a Forge repair request or rejects/accepts the risk
```

## Finding contract

An agent finding must contain:

- category and severity;
- concise title and defect explanation;
- exact repository-relative file and line;
- an evidence excerpt near that line;
- concrete impact;
- bounded fix direction;
- optional reproduction, related files/symbols, and focus directive IDs.

The Arena ignores an agent's attempt to set `confirmed=true` or `status=confirmed`. Evidence status is assigned by Aura.

## Forge handoff

The final packet can include `forge_repair_requests`. Each request contains:

- a finding-specific objective;
- exact target file;
- acceptance criteria;
- risk map;
- non-mutation/human-review constraints;
- review contract/finding lineage and evidence.

A handoff is not a patch. Forge must still prepare its own Coding Arena evidence contract, stage a candidate in the canonical boundary, run verification, and stop for human review.

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

## Research and future adapters

The design basis and source survey are recorded in:

```text
.aura/research/AURA_REVIEW_ARENA_RESEARCH_2026-07-17.md
```

Planned extensions include polyglot tree-sitter/ast-grep analysis, local SARIF/RDFormat ingestion, CodeQL/Joern code-property-graph tools, specialist Review Council roles, a false-positive judge, mutation-seeded hidden defects, and AACR-Bench-compatible precision/recall/token-cost evaluation.
