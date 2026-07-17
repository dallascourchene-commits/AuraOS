from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"missing fragment in {path}: {old[:160]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_review_core() -> None:
    replace_once(
        "aura_review_arena.py",
        '''def _truncate(text: str, limit: int = 12000) -> str:
    value = str(text or "")
    return value if len(value) <= limit else value[:limit] + "\\n...[truncated]..."
''',
        '''def _truncate(text: str, limit: int = 12000) -> str:
    value = str(text or "")
    return value if len(value) <= limit else value[:limit] + "\\n...[truncated]..."


def _normalize_tool_path(value: Any, repo_root: Path) -> str:
    text = str(value or "").replace("\\\\", "/").strip()
    if not text:
        return ""
    path = Path(text)
    if path.is_absolute():
        try:
            return path.resolve().relative_to(repo_root).as_posix()
        except (OSError, ValueError):
            return ""
    try:
        return _safe_repo_path(text, field_name="tool_file") or ""
    except ValueError:
        return ""
''',
    )
    replace_once(
        "aura_review_arena.py",
        '''        swallowed = not node.body or all(isinstance(item, (ast.Pass, ast.Expr)) for item in node.body)
''',
        '''        swallowed = not node.body or all(
            isinstance(item, ast.Pass)
            or (
                isinstance(item, ast.Expr)
                and isinstance(item.value, ast.Constant)
                and isinstance(item.value.value, str)
            )
            for item in node.body
        )
''',
    )
    replace_once(
        "aura_review_arena.py",
        '''                            "status": "corroborated",
                        })
                elif old and new and int(new["required_positional"]) > int(old["required_positional"]):
''',
        '''                            "status": "probable",
                        })
                elif old and new and int(new["required_positional"]) > int(old["required_positional"]):
''',
    )
    replace_once(
        "aura_review_arena.py",
        '''                                "status": "corroborated",
                            })
        return findings
''',
        '''                                "status": "probable",
                            })
        return findings
''',
    )
    replace_once(
        "aura_review_arena.py",
        '''        if py_files:
            plans.append(("py_compile", [sys.executable, "-m", "py_compile", *py_files[:80]], 40))
''',
        '''        # Syntax is checked in-process with ast.parse so review does not write
        # __pycache__ artifacts into the reviewed tree.
''',
    )
    replace_once(
        "aura_review_arena.py",
        '''        if request.run_tests and tests:
            plans.append(("pytest", [sys.executable, "-m", "pytest", "-q", *tests[:16]], 180))
        if request.profile == "exhaustive" and request.run_optional_tools and py_files and shutil.which("semgrep"):
            plans.append(("semgrep", ["semgrep", "--json", "--config", "auto", *py_files[:60]], 180))
''',
        '''        if request.run_tests and tests:
            plans.append(
                (
                    "pytest",
                    [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *tests[:16]],
                    180,
                )
            )
        # Semgrep/CodeQL/Joern adapters must be explicit local capabilities with
        # pinned configuration. V1 never invokes network-backed auto rules.
''',
    )
    replace_once(
        "aura_review_arena.py",
        '''                        "file": str(item.get("filename") or ""),
''',
        '''                        "file": _normalize_tool_path(item.get("filename"), self.repo_root),
''',
    )
    replace_once(
        "aura_review_arena.py",
        '''                    "file": str(item.get("filename") or ""),
''',
        '''                    "file": _normalize_tool_path(item.get("filename"), self.repo_root),
''',
    )
    replace_once(
        "aura_review_arena.py",
        '''            item["line_start"] = max(1, int(item.get("line_start") or 1))
            item["line_end"] = max(item["line_start"], int(item.get("line_end") or item["line_start"]))
''',
        '''            try:
                item["line_start"] = max(1, int(item.get("line_start") or 1))
                item["line_end"] = max(
                    item["line_start"], int(item.get("line_end") or item["line_start"])
                )
            except (TypeError, ValueError, OverflowError):
                continue
''',
    )


def patch_persistence_bridge() -> None:
    replace_once(
        "aura_agent_arena_persistence_bridge.py",
        '''from aura_temporal_persistence import PATCH_AUTHORITY, VSA_PATCH_AUTHORITY
''',
        '''from aura_temporal_persistence import PATCH_AUTHORITY, VSA_PATCH_AUTHORITY
from aura_review_arena import AuraReviewArena
''',
    )
    replace_once(
        "aura_agent_arena_persistence_bridge.py",
        '''        self.persistence = ArenaPersistenceCoordinator(str(self.repo_root))
''',
        '''        self.persistence = ArenaPersistenceCoordinator(str(self.repo_root))
        self.review_arena = AuraReviewArena(self.repo_root)
''',
    )
    replace_once(
        "aura_agent_arena_persistence_bridge.py",
        '''    @staticmethod
    def list_tools() -> list[dict[str, Any]]:
''',
        '''    def aura_review_prepare(self, request: Mapping[str, Any]) -> dict[str, Any]:
        return self.review_arena.prepare(request)

    def aura_review_scan(self, review_id: str) -> dict[str, Any]:
        return self.review_arena.scan(review_id)

    def aura_review_agent_packet(
        self,
        review_id: str,
        *,
        include_source: bool = False,
        max_files: int = 24,
        max_lines_per_file: int = 120,
    ) -> dict[str, Any]:
        return self.review_arena.agent_packet(
            review_id,
            include_source=include_source,
            max_files=max_files,
            max_lines_per_file=max_lines_per_file,
        )

    def aura_review_submit_findings(
        self,
        review_id: str,
        findings: list[Mapping[str, Any]],
        *,
        agent_name: str = "external_agent",
    ) -> dict[str, Any]:
        return self.review_arena.submit_findings(
            review_id,
            findings,
            agent_name=agent_name,
        )

    def aura_review_finalize(self, review_id: str) -> dict[str, Any]:
        return self.review_arena.finalize(review_id)

    def aura_review_status(self, review_id: str) -> dict[str, Any]:
        return self.review_arena.status(review_id)

    @staticmethod
    def list_tools() -> list[dict[str, Any]]:
''',
    )
    replace_once(
        "aura_agent_arena_persistence_bridge.py",
        '''            {
                "name": "aura_handoff_checkpoint",
                "description": "Create a payload-free digital baton for another Aura arena.",
                "required_inputs": ["checkpoint_id", "target_arena_id", "current_repo_head"],
            },
        ]
''',
        '''            {
                "name": "aura_handoff_checkpoint",
                "description": "Create a payload-free digital baton for another Aura arena.",
                "required_inputs": ["checkpoint_id", "target_arena_id", "current_repo_head"],
            },
            {
                "name": "aura_review_prepare",
                "description": "Compile an evidence-bound graph-guided code-review contract.",
                "required_inputs": ["objective"],
            },
            {
                "name": "aura_review_scan",
                "description": "Run deterministic review scans for a prepared review.",
                "required_inputs": ["review_id"],
            },
            {
                "name": "aura_review_agent_packet",
                "description": "Return a bounded impact packet for a replaceable coding agent.",
                "required_inputs": ["review_id"],
            },
            {
                "name": "aura_review_submit_findings",
                "description": "Submit structured agent findings for exact-source corroboration.",
                "required_inputs": ["review_id", "findings"],
            },
            {
                "name": "aura_review_finalize",
                "description": "Rank review findings and compile Forge repair requests.",
                "required_inputs": ["review_id"],
            },
            {
                "name": "aura_review_status",
                "description": "Return bounded in-process review status.",
                "required_inputs": ["review_id"],
            },
        ]
''',
    )


def patch_mcp() -> None:
    replace_once(
        "aura_agent_arena_mcp.py",
        '''from typing import Any
''',
        '''from typing import Any, Mapping
''',
    )
    replace_once(
        "aura_agent_arena_mcp.py",
        '''    {
        "name": "aura_handoff_checkpoint",
        "description": "Create a payload-free digital baton for another Aura arena.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "checkpoint_id": {"type": "string"},
                "target_arena_id": {"type": "string"},
                "current_repo_head": {"type": "string"},
                "current_invariant_values": {"type": "object"},
            },
            "required": ["checkpoint_id", "target_arena_id", "current_repo_head"],
        },
    },
]
''',
        '''    {
        "name": "aura_handoff_checkpoint",
        "description": "Create a payload-free digital baton for another Aura arena.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "checkpoint_id": {"type": "string"},
                "target_arena_id": {"type": "string"},
                "current_repo_head": {"type": "string"},
                "current_invariant_values": {"type": "object"},
            },
            "required": ["checkpoint_id", "target_arena_id", "current_repo_head"],
        },
    },
    {
        "name": "aura_review_prepare",
        "description": "Compile an evidence-bound review contract from a Git range, workspace, or explicit files.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "objective": {"type": "string"},
                "mode": {"type": "string", "enum": ["range", "workspace", "files"], "default": "range"},
                "base_ref": {"type": "string", "default": "HEAD~1"},
                "head_ref": {"type": "string", "default": "HEAD"},
                "changed_files": {"type": "array", "items": {"type": "string"}},
                "diff_text": {"type": "string"},
                "profile": {"type": "string", "enum": ["precision", "balanced", "exhaustive"], "default": "precision"},
                "focus_directives": {"type": "array", "items": {"type": ["string", "object"]}},
                "invariants": {"type": "array", "items": {"type": "string"}},
                "risk_map": {"type": "array", "items": {"type": "string"}},
                "agent_name": {"type": "string", "default": "external_agent"},
                "graph_depth": {"type": "integer", "minimum": 0, "maximum": 4, "default": 2},
                "graph_node_budget": {"type": "integer", "minimum": 1, "maximum": 500, "default": 120},
                "run_tests": {"type": "boolean", "default": true},
                "run_optional_tools": {"type": "boolean", "default": true},
                "metadata": {"type": "object"},
            },
            "required": ["objective"],
        },
    },
    {
        "name": "aura_review_scan",
        "description": "Run local deterministic scans and dependency-impact checks for a prepared review.",
        "inputSchema": {
            "type": "object",
            "properties": {"review_id": {"type": "string"}},
            "required": ["review_id"],
        },
    },
    {
        "name": "aura_review_agent_packet",
        "description": "Return the bounded focus, topology, evidence, and optional exact-source packet for a coding agent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "review_id": {"type": "string"},
                "include_source": {"type": "boolean", "default": false},
                "max_files": {"type": "integer", "minimum": 1, "maximum": 80, "default": 24},
                "max_lines_per_file": {"type": "integer", "minimum": 8, "maximum": 240, "default": 120},
            },
            "required": ["review_id"],
        },
    },
    {
        "name": "aura_review_submit_findings",
        "description": "Submit structured coding-agent findings for exact-source corroboration; agent confirmation claims are ignored.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "review_id": {"type": "string"},
                "findings": {"type": "array", "items": {"type": "object"}},
                "agent_name": {"type": "string", "default": "external_agent"},
            },
            "required": ["review_id", "findings"],
        },
    },
    {
        "name": "aura_review_finalize",
        "description": "Deduplicate and rank findings, then compile review-only Forge repair requests.",
        "inputSchema": {
            "type": "object",
            "properties": {"review_id": {"type": "string"}},
            "required": ["review_id"],
        },
    },
    {
        "name": "aura_review_status",
        "description": "Return the bounded status and finding counts for an in-process review.",
        "inputSchema": {
            "type": "object",
            "properties": {"review_id": {"type": "string"}},
            "required": ["review_id"],
        },
    },
]
''',
    )
    replace_once(
        "aura_agent_arena_mcp.py",
        '''@_register_tool("aura_handoff_checkpoint")
def _handle_handoff_checkpoint(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_handoff_checkpoint(
        checkpoint_id=str(args.get("checkpoint_id", "")),
        target_arena_id=str(args.get("target_arena_id", "")),
        current_repo_head=str(args.get("current_repo_head", "")),
        current_invariant_values=dict(args.get("current_invariant_values") or {}),
    )


# ---------------------------------------------------------------------------
# JSON-RPC server
''',
        '''@_register_tool("aura_handoff_checkpoint")
def _handle_handoff_checkpoint(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_handoff_checkpoint(
        checkpoint_id=str(args.get("checkpoint_id", "")),
        target_arena_id=str(args.get("target_arena_id", "")),
        current_repo_head=str(args.get("current_repo_head", "")),
        current_invariant_values=dict(args.get("current_invariant_values") or {}),
    )


@_register_tool("aura_review_prepare")
def _handle_review_prepare(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    request = {
        "objective": str(args.get("objective", "")),
        "mode": str(args.get("mode", "range")),
        "base_ref": str(args.get("base_ref", "HEAD~1")),
        "head_ref": str(args.get("head_ref", "HEAD")),
        "changed_files": list(args.get("changed_files", []) or []),
        "diff_text": str(args.get("diff_text", "")),
        "profile": str(args.get("profile", "precision")),
        "focus_directives": list(args.get("focus_directives", []) or []),
        "invariants": list(args.get("invariants", []) or []),
        "risk_map": list(args.get("risk_map", []) or []),
        "agent_name": str(args.get("agent_name", "external_agent")),
        "graph_depth": int(args.get("graph_depth", 2)),
        "graph_node_budget": int(args.get("graph_node_budget", 120)),
        "run_tests": bool(args.get("run_tests", True)),
        "run_optional_tools": bool(args.get("run_optional_tools", True)),
        "metadata": dict(args.get("metadata") or {}),
    }
    return bridge.aura_review_prepare(request)


@_register_tool("aura_review_scan")
def _handle_review_scan(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_review_scan(str(args.get("review_id", "")))


@_register_tool("aura_review_agent_packet")
def _handle_review_agent_packet(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_review_agent_packet(
        str(args.get("review_id", "")),
        include_source=bool(args.get("include_source", False)),
        max_files=int(args.get("max_files", 24)),
        max_lines_per_file=int(args.get("max_lines_per_file", 120)),
    )


@_register_tool("aura_review_submit_findings")
def _handle_review_submit_findings(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    raw_findings = args.get("findings", []) or []
    findings = [dict(item) for item in raw_findings if isinstance(item, Mapping)]
    return bridge.aura_review_submit_findings(
        str(args.get("review_id", "")),
        findings,
        agent_name=str(args.get("agent_name", "external_agent")),
    )


@_register_tool("aura_review_finalize")
def _handle_review_finalize(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_review_finalize(str(args.get("review_id", "")))


@_register_tool("aura_review_status")
def _handle_review_status(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
    return bridge.aura_review_status(str(args.get("review_id", "")))


# ---------------------------------------------------------------------------
# JSON-RPC server
''',
    )
    replace_once(
        "aura_agent_arena_mcp.py",
        '''                "isError": is_error_packet(result),
''',
        '''                "isError": is_error_packet(result)
                or (isinstance(result, Mapping) and result.get("ok") is False),
''',
    )


def patch_docs() -> None:
    replace_once(
        "README.md",
        '''| **Aura Forge** | Compiles a frozen Coding Arena plan and Arena Evidence Contract, then runs bounded Council–Surgeon slice sessions | Stops at verifier-backed human review; no automatic commit, PR, merge, or production mutation |
| **Agent Arena Bridge** | Exposes bounded CLI/MCP workflows and external-agent handoffs | External agents remain workers, not authorities |
''',
        '''| **Aura Forge** | Compiles a frozen Coding Arena plan and Arena Evidence Contract, then runs bounded Council–Surgeon slice sessions | Stops at verifier-backed human review; no automatic commit, PR, merge, or production mutation |
| **Aura Review Arena** | Computes exact diff/symbol/dependency impact, runs deterministic scans, and lets coding agents steer run-specific evidence review | Review only; agent findings cannot self-confirm or mutate, commit, push, open, or merge |
| **Agent Arena Bridge** | Exposes bounded CLI/MCP workflows and external-agent handoffs | External agents remain workers, not authorities |
''',
    )
    replace_once(
        "README.md",
        '''<!-- AURA_FORGE_V1:END -->

## Canonical architecture
''',
        '''<!-- AURA_FORGE_V1:END -->

<!-- AURA_REVIEW_ARENA_V1:START -->
## Aura Review Arena — graph-guided code review

Aura Review Arena combines deterministic program analysis with replaceable coding-agent
investigation. Aura computes changed symbols, callers, callees, tests, schemas, shared-resource
neighbors, exact source anchors, and tool evidence. Codex, Hermes, or another MCP client may
supply run-specific review questions and semantic findings, but cannot invent authoritative
edges, mark its own findings proven, or apply a fix.

```text
change or workspace
  → exact diff and changed symbols
  → bidirectional dependency-impact slice
  → syntax/static/test scans
  → run-specific focus directives
  → bounded coding-agent investigation
  → exact-source corroboration and precision-first ranking
  → human review packet
  → optional Aura Forge repair handoff
```

See [`docs/AURA_REVIEW_ARENA.md`](docs/AURA_REVIEW_ARENA.md).
<!-- AURA_REVIEW_ARENA_V1:END -->

## Canonical architecture
''',
    )
    replace_once(
        "USER_GUIDE.md",
        '''| **Aura Forge API** | Frozen-plan verified engineering runs with an exact Arena Evidence Contract and bounded worker sessions | `from aura_forge import AuraForgeRuntime` |
| **Coding Arena** | Visual code topology, exact source regions, route simulation, and capsule review | `python3 aura_coding_arena_server.py --demo` |
''',
        '''| **Aura Forge API** | Frozen-plan verified engineering runs with an exact Arena Evidence Contract and bounded worker sessions | `from aura_forge import AuraForgeRuntime` |
| **Aura Review Arena** | Graph-guided diff review, deterministic scans, coding-agent focus, exact-source corroboration, and Forge repair handoff | `python3 aura_review_arena_cli.py run --request review_request.json` |
| **Coding Arena** | Visual code topology, exact source regions, route simulation, and capsule review | `python3 aura_coding_arena_server.py --demo` |
''',
    )
    replace_once(
        "USER_GUIDE.md",
        '''The browser surfaces are not authority. A button, chart, ranking, dialogue, or visual node does not approve a consequential action.

## 4. Orient yourself before changing code
''',
        '''The browser surfaces are not authority. A button, chart, ranking, dialogue, or visual node does not approve a consequential action.

### Review a coding run before repair

Use Aura Review Arena when the question is not only "does it compile?" but also "what exact
callers, callees, schemas, tests, state transitions, authority boundaries, or shared resources
could this change affect?"

```bash
python3 aura_review_arena_cli.py run --request review_request.json
```

For Codex, Hermes, or another MCP client, keep the MCP server alive and call:

```text
aura_review_prepare
→ aura_review_scan
→ aura_review_agent_packet
→ aura_review_submit_findings
→ aura_review_finalize
```

A review finding is not patch authority. Select a generated Forge repair request only after
examining the exact evidence, then let Forge stage and verify the separate repair.

## 4. Orient yourself before changing code
''',
    )
    replace_once(
        ".aura/ARCHITECTURE.md",
        '''automatic_grammar_promotion: false
automatic_commit: false
''',
        '''automatic_grammar_promotion: false
automatic_fix: false
automatic_commit: false
''',
    )
    replace_once(
        ".aura/ARCHITECTURE.md",
        '''<!-- AURA_FORGE_V1:END -->

### Plane 8 — Observatory and glass-box explanation
''',
        '''<!-- AURA_FORGE_V1:END -->

<!-- AURA_REVIEW_ARENA_V1:START -->
#### Aura Review Arena

Aura Review Arena is the canonical pre-repair review surface over CODEMAP, compiled topology,
exact source slices, deterministic tools, external-agent MCP handoffs, and Forge repair intake.
It has a separate lifecycle:

```text
FRAME → DIFF → SLICE → SCAN → INVESTIGATE
  → CORROBORATE → RANK → DECIDE → REPAIR_HANDOFF → DISSOLVE
```

Aura owns exact changed-file/symbol extraction, callers/callees/shared-resource impact,
source anchors, deterministic findings, evidence status, deduplication, and ranking. A
replaceable coding agent may propose focus directives and semantic findings. Agent-generated
call graphs, confidence, or self-declared confirmation are not authority.

The Review Arena cannot edit production files, apply a fix, commit, push, open a pull request,
or merge. Confirmed findings can become bounded Aura Forge repair requests; Forge must still
compile a separate evidence contract, stage the candidate, verify it, and stop for human review.

Primary owners include:

- `aura_review_arena.py`;
- `aura_review_arena_cli.py`;
- `schemas/aura_review_contract.schema.json`;
- Review Arena tools on `aura_agent_arena_persistence_bridge.py` and `aura_agent_arena_mcp.py`;
- `docs/AURA_REVIEW_ARENA.md`.
<!-- AURA_REVIEW_ARENA_V1:END -->

### Plane 8 — Observatory and glass-box explanation
''',
    )


def main() -> None:
    patch_review_core()
    patch_persistence_bridge()
    patch_mcp()
    patch_docs()


if __name__ == "__main__":
    main()
