"""Aura Review Arena — graph-guided, evidence-bound automated code review.

The Review Arena is a deterministic-engineering plus replaceable-agent hybrid.
Aura computes the diff, changed symbols, dependency impact slice, static/tool
findings, source anchors, and evidence strength.  A coding agent may add
run-specific hypotheses and semantic findings, but cannot invent authoritative
graph edges, prove its own findings, mutate production code, or promote fixes.

The reviewer is intentionally separate from Forge.  Confirmed findings are
compiled into bounded Forge repair requests; implementation and promotion remain
separate, verifier-bound, human-authorized decisions.
"""
from __future__ import annotations

import ast
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Callable, Iterable, Mapping, Sequence
import uuid

REVIEW_ARENA_VERSION = "AURA_REVIEW_ARENA_V1"
REVIEW_CONTRACT_VERSION = "AURA_REVIEW_CONTRACT_V1"
REVIEW_PACKET_VERSION = "AURA_REVIEW_PACKET_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

_ALLOWED_PROFILES = frozenset({"precision", "balanced", "exhaustive"})
_ALLOWED_MODES = frozenset({"range", "workspace", "files"})
_ALLOWED_DIRECTIONS = frozenset({"callers", "callees", "both", "shared_resources"})
_ALLOWED_SEVERITIES = frozenset({"blocker", "high", "medium", "low", "info"})
_ALLOWED_CATEGORIES = frozenset({
    "syntax",
    "correctness",
    "logic",
    "security",
    "concurrency",
    "compatibility",
    "contract",
    "test_gap",
    "performance",
    "maintainability",
    "authority",
    "dependency_impact",
    "tool_failure",
})
_SEVERITY_SCORE = {"blocker": 5, "high": 4, "medium": 3, "low": 2, "info": 1}
_STATUS_SCORE = {"confirmed": 4, "corroborated": 3, "probable": 2, "advisory": 1}

_SECRET_KEYS = frozenset({
    "api_key",
    "password",
    "private_key",
    "secret",
    "credential",
    "credentials",
    "access_token",
    "auth_token",
    "bearer_token",
    "refresh_token",
    "authorization",
    "client_secret",
    "passphrase",
    "signing_key",
})
_SECRET_SUFFIXES = ("_api_key", "_password", "_private_key", "_secret", "_credential")
_TOKEN_USAGE_KEYS = frozenset({
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "prompt_tokens",
    "completion_tokens",
    "cached_tokens",
    "reasoning_tokens",
    "max_context_tokens",
    "max_output_tokens",
})

_GUIDELINE_NAMES = frozenset({
    "AGENTS.md",
    "AGENT.md",
    "CLAUDE.md",
    "GEMINI.md",
    ".cursorrules",
    ".windsurfrules",
})

CommandRunner = Callable[[Sequence[str], Path, int], subprocess.CompletedProcess[str]]


def _digest(value: Any, *, size: int = 16) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8", errors="replace"), digest_size=size).hexdigest()


def _sanitize(value: Any) -> Any:
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            lowered = key_text.lower()
            secret_token = (
                (lowered == "token" or lowered.endswith("_token"))
                and lowered not in _TOKEN_USAGE_KEYS
            )
            if lowered in _SECRET_KEYS or lowered.endswith(_SECRET_SUFFIXES) or secret_token:
                continue
            result[key_text] = _sanitize(item)
        return result
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    return value


def _clean_strings(values: Sequence[Any] | None, *, field_name: str) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)) or not isinstance(values, (list, tuple)):
        raise ValueError(f"{field_name} must be an array of strings")
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return tuple(result)


def _safe_repo_path(value: Any, *, field_name: str = "file") -> str | None:
    text = str(value or "").replace("\\", "/").strip()
    if not text:
        return None
    path = PurePosixPath(text)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{field_name} must be a repository-relative path")
    normalized = path.as_posix()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized or normalized == ".":
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _safe_ref(value: Any, *, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    if text.startswith("-") or not re.fullmatch(r"[A-Za-z0-9._/@{}~^:+-]+", text):
        raise ValueError(f"{field_name} contains unsafe characters")
    return text


def _default_command_runner(
    command: Sequence[str], cwd: Path, timeout_seconds: int
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        timeout=max(1, timeout_seconds),
    )


def _file_digest(path: Path) -> str:
    try:
        return hashlib.blake2b(path.read_bytes(), digest_size=16).hexdigest()
    except OSError:
        return "UNAVAILABLE"


def _truncate(text: str, limit: int = 12000) -> str:
    value = str(text or "")
    return value if len(value) <= limit else value[:limit] + "\n...[truncated]..."


def _normalize_tool_path(value: Any, repo_root: Path) -> str:
    text = str(value or "").replace("\\", "/").strip()
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


@dataclass(frozen=True)
class ReviewFocusDirective:
    """One agent- or Aura-selected investigative question."""

    directive_id: str
    name: str
    question: str
    risk: str = "correctness"
    direction: str = "both"
    target_patterns: tuple[str, ...] = ()
    required_evidence: tuple[str, ...] = ("exact_source",)
    suggested_tools: tuple[str, ...] = ()
    max_depth: int = 1
    max_nodes: int = 40
    origin: str = "agent"

    @classmethod
    def from_value(cls, value: str | Mapping[str, Any], *, origin: str = "agent") -> "ReviewFocusDirective":
        if isinstance(value, str):
            raw: Mapping[str, Any] = {"name": value[:80], "question": value}
        elif isinstance(value, Mapping):
            raw = value
        else:
            raise ValueError("focus directives must be strings or objects")
        name = str(raw.get("name") or raw.get("question") or "review_focus").strip()[:120]
        question = str(raw.get("question") or raw.get("name") or "").strip()
        if not question:
            raise ValueError("focus directive question is required")
        risk = str(raw.get("risk") or "correctness").strip().lower()
        direction = str(raw.get("direction") or "both").strip().lower()
        if direction not in _ALLOWED_DIRECTIONS:
            raise ValueError(f"unsupported focus direction: {direction}")
        max_depth = int(raw.get("max_depth", 1))
        max_nodes = int(raw.get("max_nodes", 40))
        if max_depth < 0 or max_depth > 4:
            raise ValueError("focus max_depth must be between 0 and 4")
        if max_nodes < 1 or max_nodes > 250:
            raise ValueError("focus max_nodes must be between 1 and 250")
        patterns = _clean_strings(raw.get("target_patterns"), field_name="target_patterns")
        evidence = _clean_strings(raw.get("required_evidence"), field_name="required_evidence") or ("exact_source",)
        tools = _clean_strings(raw.get("suggested_tools"), field_name="suggested_tools")
        identity = {
            "name": name,
            "question": question,
            "risk": risk,
            "direction": direction,
            "patterns": patterns,
            "evidence": evidence,
            "tools": tools,
            "depth": max_depth,
            "nodes": max_nodes,
            "origin": origin,
        }
        return cls(
            directive_id=f"FOCUS-{_digest(identity, size=10)}",
            name=name,
            question=question,
            risk=risk,
            direction=direction,
            target_patterns=patterns,
            required_evidence=evidence,
            suggested_tools=tools,
            max_depth=max_depth,
            max_nodes=max_nodes,
            origin=origin,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for name in ("target_patterns", "required_evidence", "suggested_tools"):
            payload[name] = list(payload[name])
        return payload


@dataclass(frozen=True)
class AuraReviewRequest:
    objective: str
    mode: str = "range"
    base_ref: str = "HEAD~1"
    head_ref: str = "HEAD"
    changed_files: tuple[str, ...] = ()
    diff_text: str = ""
    profile: str = "precision"
    focus_directives: tuple[ReviewFocusDirective, ...] = ()
    invariants: tuple[str, ...] = ()
    risk_map: tuple[str, ...] = ()
    agent_name: str = "external_agent"
    graph_depth: int = 2
    graph_node_budget: int = 120
    run_tests: bool = True
    run_optional_tools: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_value(cls, value: "AuraReviewRequest | Mapping[str, Any]") -> "AuraReviewRequest":
        if isinstance(value, cls):
            return value
        if not isinstance(value, Mapping):
            raise ValueError("review request must be an object")
        objective = str(value.get("objective") or "").strip()
        if not objective:
            raise ValueError("objective is required")
        mode = str(value.get("mode") or "range").strip().lower()
        if mode not in _ALLOWED_MODES:
            raise ValueError(f"unsupported review mode: {mode}")
        profile = str(value.get("profile") or "precision").strip().lower()
        if profile not in _ALLOWED_PROFILES:
            raise ValueError(f"unsupported review profile: {profile}")
        base_ref = _safe_ref(value.get("base_ref", "HEAD~1"), field_name="base_ref")
        head_ref = _safe_ref(value.get("head_ref", "HEAD"), field_name="head_ref")
        raw_files = _clean_strings(value.get("changed_files"), field_name="changed_files")
        files: list[str] = []
        for raw in raw_files:
            safe = _safe_repo_path(raw, field_name="changed_file")
            if safe and safe not in files:
                files.append(safe)
        raw_directives = value.get("focus_directives") or []
        if isinstance(raw_directives, (str, bytes)) or not isinstance(raw_directives, (list, tuple)):
            raise ValueError("focus_directives must be an array")
        directives = tuple(ReviewFocusDirective.from_value(item, origin="agent") for item in raw_directives)
        graph_depth = int(value.get("graph_depth", 2))
        graph_node_budget = int(value.get("graph_node_budget", 120))
        if graph_depth < 0 or graph_depth > 4:
            raise ValueError("graph_depth must be between 0 and 4")
        if graph_node_budget < 1 or graph_node_budget > 500:
            raise ValueError("graph_node_budget must be between 1 and 500")
        metadata_value = value.get("metadata")
        if metadata_value is None:
            metadata: dict[str, Any] = {}
        elif isinstance(metadata_value, Mapping):
            metadata = _sanitize(dict(metadata_value))
        else:
            raise ValueError("metadata must be an object")
        diff_text = str(value.get("diff_text") or "")
        if len(diff_text) > 2_000_000:
            raise ValueError("diff_text exceeds the 2 MB review boundary")
        return cls(
            objective=objective,
            mode=mode,
            base_ref=base_ref,
            head_ref=head_ref,
            changed_files=tuple(files),
            diff_text=diff_text,
            profile=profile,
            focus_directives=directives,
            invariants=_clean_strings(value.get("invariants"), field_name="invariants"),
            risk_map=_clean_strings(value.get("risk_map"), field_name="risk_map"),
            agent_name=str(value.get("agent_name") or "external_agent").strip()[:120] or "external_agent",
            graph_depth=graph_depth,
            graph_node_budget=graph_node_budget,
            run_tests=bool(value.get("run_tests", True)),
            run_optional_tools=bool(value.get("run_optional_tools", True)),
            metadata=metadata,
        )

    def identity_dict(self) -> dict[str, Any]:
        return {
            "objective": self.objective,
            "mode": self.mode,
            "base_ref": self.base_ref,
            "head_ref": self.head_ref,
            "changed_files": list(self.changed_files),
            "diff_digest": _digest(self.diff_text) if self.diff_text else "",
            "profile": self.profile,
            "focus_directives": [item.to_dict() for item in self.focus_directives],
            "invariants": list(self.invariants),
            "risk_map": list(self.risk_map),
            "agent_name": self.agent_name,
            "graph_depth": self.graph_depth,
            "graph_node_budget": self.graph_node_budget,
            "run_tests": self.run_tests,
            "run_optional_tools": self.run_optional_tools,
            "metadata": _sanitize(self.metadata),
        }


@dataclass(frozen=True)
class AuraReviewContract:
    contract_id: str
    request_digest: str
    repository_head: str
    diff_digest: str
    changed_files: tuple[str, ...]
    changed_symbols: tuple[Mapping[str, Any], ...]
    impact_slice: tuple[Mapping[str, Any], ...]
    focus_directives: tuple[ReviewFocusDirective, ...]
    invariants: tuple[str, ...]
    risk_map: tuple[str, ...]
    routing_frame: Mapping[str, Any]
    guideline_files: tuple[Mapping[str, Any], ...]
    profile: str
    authority: Mapping[str, Any]
    lifecycle: tuple[str, ...] = (
        "FRAME",
        "DIFF",
        "SLICE",
        "SCAN",
        "INVESTIGATE",
        "CORROBORATE",
        "RANK",
        "DECIDE",
        "REPAIR_HANDOFF",
        "DISSOLVE",
    )
    version: str = REVIEW_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["changed_files"] = list(self.changed_files)
        payload["changed_symbols"] = [_sanitize(dict(item)) for item in self.changed_symbols]
        payload["impact_slice"] = [_sanitize(dict(item)) for item in self.impact_slice]
        payload["focus_directives"] = [item.to_dict() for item in self.focus_directives]
        payload["invariants"] = list(self.invariants)
        payload["risk_map"] = list(self.risk_map)
        payload["guideline_files"] = [_sanitize(dict(item)) for item in self.guideline_files]
        payload["lifecycle"] = list(self.lifecycle)
        return _sanitize(payload)


class _ASTReviewVisitor(ast.NodeVisitor):
    def __init__(self, *, file: str) -> None:
        self.file = file
        self.findings: list[dict[str, Any]] = []
        self._async_depth = 0

    def _finding(
        self,
        node: ast.AST,
        *,
        rule: str,
        category: str,
        severity: str,
        title: str,
        message: str,
        suggested_fix: str,
        confidence: float = 0.82,
    ) -> None:
        line = int(getattr(node, "lineno", 1) or 1)
        self.findings.append({
            "origin": "builtin_ast",
            "rule": rule,
            "category": category,
            "severity": severity,
            "confidence": confidence,
            "title": title,
            "message": message,
            "file": self.file,
            "line_start": line,
            "line_end": int(getattr(node, "end_lineno", line) or line),
            "suggested_fix": suggested_fix,
            "evidence": [{"kind": "ast", "source": rule, "line": line}],
            "status": "probable",
        })

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_mutable_defaults(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_mutable_defaults(node)
        self._async_depth += 1
        self.generic_visit(node)
        self._async_depth -= 1

    def _check_mutable_defaults(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        defaults = [*node.args.defaults, *[item for item in node.args.kw_defaults if item is not None]]
        for default in defaults:
            mutable = isinstance(default, (ast.List, ast.Dict, ast.Set))
            mutable = mutable or (
                isinstance(default, ast.Call)
                and isinstance(default.func, ast.Name)
                and default.func.id in {"list", "dict", "set", "defaultdict"}
            )
            if mutable:
                self._finding(
                    default,
                    rule="mutable-default-argument",
                    category="logic",
                    severity="medium",
                    title="Mutable default argument persists across calls",
                    message="This default object is allocated once and shared by every call, which can leak state between review or execution sessions.",
                    suggested_fix="Use None as the default and allocate the collection inside the function.",
                )

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        broad = node.type is None or (
            isinstance(node.type, ast.Name) and node.type.id in {"Exception", "BaseException"}
        )
        swallowed = not node.body or all(
            isinstance(item, ast.Pass)
            or (
                isinstance(item, ast.Expr)
                and isinstance(item.value, ast.Constant)
                and isinstance(item.value.value, str)
            )
            for item in node.body
        )
        if node.type is None:
            self._finding(
                node,
                rule="bare-except",
                category="correctness",
                severity="medium",
                title="Bare except catches control-flow and system exceptions",
                message="A bare except can hide KeyboardInterrupt, SystemExit, and unexpected programming failures.",
                suggested_fix="Catch the narrow exception types that are expected at this boundary.",
            )
        if broad and swallowed:
            self._finding(
                node,
                rule="broad-exception-swallow",
                category="logic",
                severity="high",
                title="Broad exception is swallowed without fail-closed evidence",
                message="This handler can convert an unexpected failure into apparent success or missing evidence.",
                suggested_fix="Return a structured failure, preserve the exception type, and add a regression test for the malformed dependency packet.",
                confidence=0.88,
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        call_name = ""
        if isinstance(node.func, ast.Name):
            call_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            root = node.func.value.id if isinstance(node.func.value, ast.Name) else ""
            call_name = f"{root}.{node.func.attr}" if root else node.func.attr

        if call_name in {"eval", "exec"}:
            self._finding(
                node,
                rule="dynamic-code-execution",
                category="security",
                severity="high",
                title="Dynamic code execution requires an explicit trust boundary",
                message=f"{call_name} executes data as code and can become a code-injection path.",
                suggested_fix="Replace dynamic execution with a constrained parser or an explicit allowlisted dispatcher.",
                confidence=0.94,
            )

        if call_name.endswith("subprocess.run") or call_name.endswith("subprocess.call") or call_name in {
            "subprocess.run", "subprocess.call", "subprocess.check_call", "subprocess.check_output"
        }:
            shell_true = any(
                keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True
                for keyword in node.keywords
            )
            if shell_true:
                self._finding(
                    node,
                    rule="subprocess-shell-true",
                    category="security",
                    severity="high",
                    title="Shell command execution expands the injection surface",
                    message="shell=True delegates parsing to a shell; user- or repository-controlled fragments can become commands.",
                    suggested_fix="Pass an argument vector with shell=False and validate every repository/ref/path input separately.",
                    confidence=0.96,
                )
            if self._async_depth:
                self._finding(
                    node,
                    rule="blocking-subprocess-in-async",
                    category="concurrency",
                    severity="medium",
                    title="Blocking subprocess call runs inside an async function",
                    message="A synchronous subprocess can stall the event loop and delay unrelated sessions.",
                    suggested_fix="Use asyncio subprocess APIs or move the blocking operation to a bounded executor.",
                )

        if call_name.endswith("yaml.load") or call_name == "yaml.load":
            has_loader = any(keyword.arg == "Loader" for keyword in node.keywords)
            if not has_loader:
                self._finding(
                    node,
                    rule="unsafe-yaml-load",
                    category="security",
                    severity="high",
                    title="YAML load has no explicit safe loader",
                    message="Untrusted YAML may construct arbitrary Python objects when a safe loader is not selected.",
                    suggested_fix="Use yaml.safe_load or an explicitly safe Loader.",
                    confidence=0.9,
                )
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        self.generic_visit(node)


class AuraReviewArena:
    """Canonical graph-guided review surface for native and external coding agents."""

    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        command_runner: CommandRunner | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self._run_command_impl = command_runner or _default_command_runner
        self._reviews: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _error(code: str, *, stage: str, details: Any = None) -> dict[str, Any]:
        result = {
            "ok": False,
            "version": REVIEW_ARENA_VERSION,
            "error": str(code),
            "stage": stage,
            "production_mutation": False,
            "automatic_fix": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_pull_request": False,
            "automatic_merge": False,
            "human_review_required": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        if details is not None:
            result["details"] = _sanitize(details)
        return result

    def prepare(self, value: AuraReviewRequest | Mapping[str, Any]) -> dict[str, Any]:
        try:
            request = AuraReviewRequest.from_value(value)
            repository_head = self._materialized_review_head(request)
            diff_text, changed_files = self._resolve_diff(request)
        except (ValueError, OSError, subprocess.SubprocessError) as exc:
            return self._error(str(exc), stage="DIFF")
        if not changed_files:
            return self._error("review_has_no_changed_files", stage="DIFF")

        changed_ranges = self._parse_diff_ranges(diff_text)
        deleted_files = self._deleted_files_from_diff(diff_text)
        changed_symbols = self._changed_symbols(changed_files, changed_ranges)
        changed_symbols.extend(self._deleted_symbols(request, deleted_files))
        changed_symbols = sorted(
            changed_symbols,
            key=lambda item: (
                str(item.get("file") or ""),
                int(item.get("line_start") or 0),
                str(item.get("symbol") or ""),
            ),
        )
        topology = self._load_topology()
        impact_slice = self._impact_slice(
            changed_files,
            changed_symbols,
            topology,
            max_depth=request.graph_depth,
            max_nodes=request.graph_node_budget,
        )
        impact_slice = self._augment_deleted_impacts(
            request,
            deleted_files,
            changed_symbols,
            impact_slice,
            max_nodes=request.graph_node_budget,
        )
        inferred = self._infer_focus_directives(request, diff_text, changed_files, changed_symbols)
        directives = self._dedupe_directives([*request.focus_directives, *inferred])
        guidelines = self._guidelines_for_files(changed_files)
        routing_frame = self._routing_frame(request, changed_files, guidelines)
        diff_digest = _digest(diff_text)
        request_digest = _digest(request.identity_dict())
        identity = {
            "request_digest": request_digest,
            "repository_head": repository_head,
            "diff_digest": diff_digest,
            "changed_files": changed_files,
            "changed_symbols": changed_symbols,
            "impact_slice": impact_slice,
            "focus": [item.to_dict() for item in directives],
        }
        contract = AuraReviewContract(
            contract_id=_digest(identity),
            request_digest=request_digest,
            repository_head=repository_head,
            diff_digest=diff_digest,
            changed_files=tuple(changed_files),
            changed_symbols=tuple(changed_symbols),
            impact_slice=tuple(impact_slice),
            focus_directives=tuple(directives),
            invariants=request.invariants,
            risk_map=request.risk_map,
            routing_frame=routing_frame,
            guideline_files=tuple(guidelines),
            profile=request.profile,
            authority={
                "aura_computes_diff_and_graph": True,
                "agent_supplies_hypotheses": True,
                "agent_may_not_self_confirm": True,
                "planning_proposes": True,
                "verification_proves": True,
                "human_authorizes": True,
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": False,
                "production_mutation": False,
                "automatic_fix": False,
                "automatic_commit": False,
                "automatic_push": False,
                "automatic_pull_request": False,
                "automatic_merge": False,
            },
        )
        review_id = f"REVIEW-{contract.contract_id[:16]}-{uuid.uuid4().hex[:12]}"
        self._reviews[review_id] = {
            "request": request,
            "contract": contract,
            "diff_text": diff_text,
            "changed_ranges": changed_ranges,
            "deleted_files": tuple(deleted_files),
            "topology": topology,
            "deterministic_findings": [],
            "agent_findings": [],
            "agent_finding_inputs": [],
            "tool_results": [],
            "status": "PREPARED",
            "created_at": time.time(),
        }
        return {
            "ok": True,
            "version": REVIEW_ARENA_VERSION,
            "review_id": review_id,
            "status": "PREPARED",
            "contract": contract.to_dict(),
            "agent_packet": self._agent_packet_from_state(review_id, include_source=False),
            "production_mutation": False,
            "automatic_fix": False,
            "human_review_required": True,
        }

    def scan(self, review_id: str) -> dict[str, Any]:
        state = self._reviews.get(str(review_id))
        if state is None:
            return self._error("review_not_found", stage="SCAN")
        request: AuraReviewRequest = state["request"]
        contract: AuraReviewContract = state["contract"]
        findings: list[dict[str, Any]] = []
        deleted_files = set(state.get("deleted_files", ()))
        for file in contract.changed_files:
            if file.endswith(".py") and file not in deleted_files:
                findings.extend(self._scan_python_file(file))
        findings.extend(self._scan_signature_impacts(state))
        tool_results, tool_findings = self._run_tools(state)
        findings.extend(tool_findings)
        normalized = self._normalize_findings(findings, origin_default="deterministic")
        state["deterministic_findings"] = normalized
        state["tool_results"] = tool_results
        state["status"] = "WAITING_FOR_AGENT" if request.agent_name != "none" else "SCANNED"
        return {
            "ok": True,
            "version": REVIEW_ARENA_VERSION,
            "review_id": review_id,
            "status": state["status"],
            "deterministic_findings": normalized,
            "tool_results": _sanitize(tool_results),
            "agent_packet": self._agent_packet_from_state(review_id, include_source=False),
            "production_mutation": False,
            "automatic_fix": False,
            "human_review_required": True,
        }

    def agent_packet(
        self,
        review_id: str,
        *,
        include_source: bool = False,
        max_files: int = 24,
        max_lines_per_file: int = 120,
    ) -> dict[str, Any]:
        if review_id not in self._reviews:
            return self._error("review_not_found", stage="INVESTIGATE")
        if max_files < 1 or max_files > 80:
            return self._error("max_files must be between 1 and 80", stage="INVESTIGATE")
        if max_lines_per_file < 8 or max_lines_per_file > 240:
            return self._error("max_lines_per_file must be between 8 and 240", stage="INVESTIGATE")
        return self._agent_packet_from_state(
            review_id,
            include_source=bool(include_source),
            max_files=max_files,
            max_lines_per_file=max_lines_per_file,
        )

    def submit_findings(
        self,
        review_id: str,
        findings: Sequence[Mapping[str, Any]],
        *,
        agent_name: str = "external_agent",
    ) -> dict[str, Any]:
        state = self._reviews.get(str(review_id))
        if state is None:
            return self._error("review_not_found", stage="CORROBORATE")
        if isinstance(findings, (str, bytes)) or not isinstance(findings, (list, tuple)):
            return self._error("findings must be an array of objects", stage="CORROBORATE")
        accepted: list[dict[str, Any]] = []
        accepted_inputs: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        scope = self._review_scope_files(state["contract"])
        for index, raw in enumerate(findings):
            if not isinstance(raw, Mapping):
                rejected.append({"index": index, "reason": "finding_must_be_object"})
                continue
            try:
                finding = self._validate_agent_finding(raw, scope=scope, agent_name=agent_name)
            except ValueError as exc:
                rejected.append({"index": index, "reason": str(exc)})
                continue
            accepted.append(finding)
            accepted_inputs.append({
                "agent_name": str(agent_name or "external_agent")[:120],
                "finding": _sanitize(dict(raw)),
            })
        state["agent_finding_inputs"] = [
            *state.get("agent_finding_inputs", []),
            *accepted_inputs,
        ]
        state["agent_findings"] = self._normalize_findings(
            [*state.get("agent_findings", []), *accepted], origin_default="agent"
        )
        state["status"] = "AGENT_FINDINGS_RECEIVED"
        return {
            "ok": True,
            "version": REVIEW_ARENA_VERSION,
            "review_id": review_id,
            "accepted_count": len(accepted),
            "rejected": rejected,
            "status": state["status"],
            "production_mutation": False,
            "automatic_fix": False,
            "human_review_required": True,
        }

    def finalize(self, review_id: str) -> dict[str, Any]:
        state = self._reviews.get(str(review_id))
        if state is None:
            return self._error("review_not_found", stage="RANK")
        request: AuraReviewRequest = state["request"]
        all_findings = self._normalize_findings(
            [*state.get("deterministic_findings", []), *state.get("agent_findings", [])],
            origin_default="review",
        )
        if request.profile == "precision":
            visible = [
                item for item in all_findings
                if item.get("status") in {"confirmed", "corroborated"}
                or (
                    item.get("status") == "probable"
                    and float(item.get("confidence", 0.0)) >= 0.85
                    and item.get("severity") in {"blocker", "high", "medium"}
                )
            ]
        elif request.profile == "balanced":
            visible = [item for item in all_findings if float(item.get("confidence", 0.0)) >= 0.65]
        else:
            visible = all_findings
        ranked = sorted(
            visible,
            key=lambda item: (
                -_SEVERITY_SCORE.get(str(item.get("severity")), 0),
                -_STATUS_SCORE.get(str(item.get("status")), 0),
                -float(item.get("confidence", 0.0)),
                str(item.get("file") or ""),
                int(item.get("line_start") or 0),
            ),
        )
        repairs = [self._forge_repair_request(item, state["contract"]) for item in ranked if self._repair_eligible(item)]
        counts = defaultdict(int)
        for item in ranked:
            counts[str(item.get("severity") or "info")] += 1
        state["status"] = "READY_FOR_HUMAN_REVIEW"
        packet = {
            "ok": True,
            "version": REVIEW_ARENA_VERSION,
            "packet_version": REVIEW_PACKET_VERSION,
            "review_id": review_id,
            "contract_id": state["contract"].contract_id,
            "status": state["status"],
            "profile": request.profile,
            "summary": {
                "visible_findings": len(ranked),
                "all_findings_before_profile_filter": len(all_findings),
                "severity_counts": dict(counts),
                "blocking": any(item.get("severity") in {"blocker", "high"} for item in ranked),
                "tool_runs": len(state.get("tool_results", [])),
            },
            "findings": ranked,
            "suppressed_advisories": max(0, len(all_findings) - len(ranked)),
            "forge_repair_requests": repairs,
            "decision_options": [
                "REQUEST_FORGE_REPAIR",
                "ACCEPT_RISK_WITH_RATIONALE",
                "REJECT_FINDING",
                "REQUEST_DEEPER_REVIEW",
            ],
            "production_mutation": False,
            "automatic_fix": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_pull_request": False,
            "automatic_merge": False,
            "human_review_required": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        state["final_packet"] = packet
        return packet

    def status(self, review_id: str) -> dict[str, Any]:
        state = self._reviews.get(str(review_id))
        if state is None:
            return self._error("review_not_found", stage="STATUS")
        return {
            "ok": True,
            "version": REVIEW_ARENA_VERSION,
            "review_id": review_id,
            "status": state["status"],
            "contract_id": state["contract"].contract_id,
            "deterministic_findings": len(state.get("deterministic_findings", [])),
            "agent_findings": len(state.get("agent_findings", [])),
            "tool_runs": len(state.get("tool_results", [])),
            "production_mutation": False,
            "automatic_fix": False,
            "human_review_required": True,
        }

    def run_once(self, value: AuraReviewRequest | Mapping[str, Any]) -> dict[str, Any]:
        prepared = self.prepare(value)
        if not prepared.get("ok"):
            return prepared
        review_id = str(prepared["review_id"])
        scanned = self.scan(review_id)
        if not scanned.get("ok"):
            return scanned
        return self.finalize(review_id)

    @staticmethod
    def _request_state_payload(request: AuraReviewRequest) -> dict[str, Any]:
        return {
            "objective": request.objective,
            "mode": request.mode,
            "base_ref": request.base_ref,
            "head_ref": request.head_ref,
            "changed_files": list(request.changed_files),
            "diff_text": request.diff_text,
            "profile": request.profile,
            "focus_directives": [item.to_dict() for item in request.focus_directives],
            "invariants": list(request.invariants),
            "risk_map": list(request.risk_map),
            "agent_name": request.agent_name,
            "graph_depth": request.graph_depth,
            "graph_node_budget": request.graph_node_budget,
            "run_tests": request.run_tests,
            "run_optional_tools": request.run_optional_tools,
            "metadata": _sanitize(request.metadata),
        }

    def export_review_state(self, review_id: str) -> dict[str, Any]:
        state = self._reviews.get(str(review_id))
        if state is None:
            return self._error("review_not_found", stage="STATE_EXPORT")
        contract: AuraReviewContract = state["contract"]
        return {
            "ok": True,
            "version": REVIEW_ARENA_VERSION,
            "review_id": str(review_id),
            "contract_id": contract.contract_id,
            "request": self._request_state_payload(state["request"]),
            "target_status": str(state.get("status") or "PREPARED"),
            "created_at": float(state.get("created_at") or time.time()),
            # Persist only the agent's original bounded claims. Deterministic
            # findings, evidence status, tool results, Waboose receipts, and
            # repair eligibility are recomputed from the exact reviewed head.
            "agent_finding_inputs": _sanitize(
                state.get("agent_finding_inputs", [])
            ),
            "derived_evidence_persisted_as_authority": False,
            "production_mutation": False,
            "automatic_fix": False,
            "human_review_required": True,
        }

    def import_review_state(self, value: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(value, Mapping):
            return self._error("review_state_must_be_object", stage="STATE_IMPORT")
        review_id = str(value.get("review_id") or "").strip()
        contract_id = str(value.get("contract_id") or "").strip()
        request_payload = value.get("request")
        if not review_id or not contract_id or not isinstance(request_payload, Mapping):
            return self._error(
                "review_state_requires_review_id_contract_id_and_request",
                stage="STATE_IMPORT",
            )
        if review_id in self._reviews:
            return self._error("review_state_already_loaded", stage="STATE_IMPORT")
        prepared = self.prepare(request_payload)
        if not prepared.get("ok"):
            return self._error(
                "review_state_revalidation_failed",
                stage="STATE_IMPORT",
                details=prepared,
            )
        generated_id = str(prepared["review_id"])
        state = self._reviews.pop(generated_id)
        generated_contract: AuraReviewContract = state["contract"]
        if generated_contract.contract_id != contract_id:
            return self._error(
                "review_state_contract_mismatch",
                stage="STATE_IMPORT",
                details={
                    "expected_contract_id": contract_id,
                    "current_contract_id": generated_contract.contract_id,
                },
            )
        try:
            state["created_at"] = float(value.get("created_at") or time.time())
        except (TypeError, ValueError, OverflowError):
            state["created_at"] = time.time()
        self._reviews[review_id] = state

        allowed_targets = {
            "PREPARED",
            "WAITING_FOR_AGENT",
            "SCANNED",
            "AGENT_FINDINGS_RECEIVED",
            "READY_FOR_HUMAN_REVIEW",
        }
        target_status = str(
            value.get("target_status") or value.get("status") or "PREPARED"
        )
        if target_status not in allowed_targets:
            self._reviews.pop(review_id, None)
            return self._error("invalid_review_state_target_status", stage="STATE_IMPORT")

        if target_status != "PREPARED":
            scanned = self.scan(review_id)
            if not scanned.get("ok"):
                self._reviews.pop(review_id, None)
                return self._error(
                    "review_state_scan_replay_failed",
                    stage="STATE_IMPORT",
                    details=scanned,
                )

        raw_inputs = value.get("agent_finding_inputs", [])
        if isinstance(raw_inputs, (str, bytes)) or not isinstance(raw_inputs, (list, tuple)):
            self._reviews.pop(review_id, None)
            return self._error(
                "agent_finding_inputs_must_be_an_array",
                stage="STATE_IMPORT",
            )
        for index, item in enumerate(raw_inputs):
            if not isinstance(item, Mapping) or not isinstance(item.get("finding"), Mapping):
                self._reviews.pop(review_id, None)
                return self._error(
                    "invalid_persisted_agent_finding_input",
                    stage="STATE_IMPORT",
                    details={"index": index},
                )
            replayed = self.submit_findings(
                review_id,
                [dict(item["finding"])],
                agent_name=str(item.get("agent_name") or "external_agent"),
            )
            if (
                not replayed.get("ok")
                or int(replayed.get("accepted_count") or 0) != 1
                or replayed.get("rejected")
            ):
                self._reviews.pop(review_id, None)
                return self._error(
                    "persisted_agent_finding_revalidation_failed",
                    stage="STATE_IMPORT",
                    details={"index": index, "result": replayed},
                )

        if target_status == "READY_FOR_HUMAN_REVIEW":
            finalized = self.finalize(review_id)
            if not finalized.get("ok"):
                self._reviews.pop(review_id, None)
                return self._error(
                    "review_state_finalize_replay_failed",
                    stage="STATE_IMPORT",
                    details=finalized,
                )

        loaded = self._reviews[review_id]
        return {
            "ok": True,
            "version": REVIEW_ARENA_VERSION,
            "review_id": review_id,
            "contract_id": contract_id,
            "status": loaded["status"],
            "derived_evidence_recomputed": True,
            "production_mutation": False,
            "automatic_fix": False,
            "human_review_required": True,
        }

    def _resolve_diff(self, request: AuraReviewRequest) -> tuple[str, list[str]]:
        if request.diff_text:
            diff = request.diff_text
            files = list(request.changed_files) or self._files_from_diff(diff)
            return diff, files
        if request.mode == "files":
            if not request.changed_files:
                raise ValueError("changed_files are required in files mode")
            return "", list(request.changed_files)
        if request.mode == "workspace":
            unstaged = self._git(["git", "diff", "--no-ext-diff", "--unified=0", "HEAD", "--"], timeout=20)
            staged = self._git(["git", "diff", "--cached", "--no-ext-diff", "--unified=0", "--"], timeout=20)
            diff = "\n".join(part for part in (staged, unstaged) if part)
            files = self._files_from_diff(diff)
            untracked = self._git(["git", "ls-files", "--others", "--exclude-standard"], timeout=10)
            for line in untracked.splitlines():
                safe = _safe_repo_path(line, field_name="untracked_file")
                if safe and safe not in files:
                    files.append(safe)
            for file in request.changed_files:
                if file not in files:
                    files.append(file)
            return diff, files
        diff = self._git([
            "git", "diff", "--no-ext-diff", "--unified=0", request.base_ref, request.head_ref, "--"
        ], timeout=30)
        files = self._files_from_diff(diff)
        for file in request.changed_files:
            if file not in files:
                files.append(file)
        return diff, files

    def _git(self, command: Sequence[str], *, timeout: int) -> str:
        result = self._run_command_impl(command, self.repo_root, timeout)
        if result.returncode != 0:
            raise ValueError(_truncate(result.stderr or result.stdout, 1200) or "git command failed")
        return str(result.stdout or "")

    def _git_head(self) -> str:
        try:
            return self._git(["git", "rev-parse", "HEAD"], timeout=5).strip() or "UNAVAILABLE"
        except (ValueError, OSError, subprocess.SubprocessError):
            return "UNAVAILABLE"

    def _materialized_review_head(self, request: AuraReviewRequest) -> str:
        current = self._git_head()
        if request.mode != "range":
            return current
        requested = self._git(
            ["git", "rev-parse", "--verify", f"{request.head_ref}^{{commit}}"],
            timeout=8,
        ).strip()
        if not requested or current == "UNAVAILABLE" or requested != current:
            raise ValueError("range_head_ref_not_checked_out")
        worktree_status = self._git(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            timeout=10,
        )
        if worktree_status.strip():
            raise ValueError("range_review_requires_clean_worktree")
        return requested

    @staticmethod
    def _files_from_diff(diff_text: str) -> list[str]:
        result: list[str] = []
        old_path = ""
        for line in diff_text.splitlines():
            if line.startswith("--- a/"):
                old_path = str(
                    _safe_repo_path(line[6:], field_name="diff_file") or ""
                )
                continue
            if line.startswith("+++ b/"):
                path = _safe_repo_path(line[6:], field_name="diff_file")
                if path and path not in result:
                    result.append(path)
                old_path = ""
                continue
            if line == "+++ /dev/null":
                if old_path and old_path not in result:
                    result.append(old_path)
                old_path = ""
        return result

    @staticmethod
    def _deleted_files_from_diff(diff_text: str) -> list[str]:
        result: list[str] = []
        old_path = ""
        for line in diff_text.splitlines():
            if line.startswith("--- a/"):
                old_path = str(
                    _safe_repo_path(line[6:], field_name="diff_file") or ""
                )
            elif line == "+++ /dev/null":
                if old_path and old_path not in result:
                    result.append(old_path)
                old_path = ""
            elif line.startswith("+++ b/"):
                old_path = ""
        return result

    @staticmethod
    def _parse_diff_ranges(diff_text: str) -> dict[str, list[tuple[int, int]]]:
        ranges: dict[str, list[tuple[int, int]]] = defaultdict(list)
        current = ""
        for line in diff_text.splitlines():
            if line.startswith("+++ b/"):
                current = str(_safe_repo_path(line[6:], field_name="diff_file") or "")
                continue
            if current and line.startswith("@@"):
                match = re.search(r"\+(\d+)(?:,(\d+))?", line)
                if not match:
                    continue
                start = int(match.group(1))
                count = int(match.group(2) or "1")
                end = start if count == 0 else start + count - 1
                ranges[current].append((start, end))
        return dict(ranges)

    def _changed_symbols(
        self,
        changed_files: Sequence[str],
        changed_ranges: Mapping[str, Sequence[tuple[int, int]]],
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for file in changed_files:
            if not file.endswith(".py"):
                continue
            path = self._resolve_file(file)
            if path is None or not path.exists():
                continue
            try:
                source = path.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source, filename=file)
            except (OSError, SyntaxError):
                continue
            file_ranges = list(changed_ranges.get(file) or [])
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue
                start = int(node.lineno)
                end = int(getattr(node, "end_lineno", start) or start)
                if file_ranges and not any(not (end < lo or start > hi) for lo, hi in file_ranges):
                    continue
                result.append({
                    "file": file,
                    "symbol": node.name,
                    "kind": type(node).__name__,
                    "line_start": start,
                    "line_end": end,
                    "signature": self._node_signature(node),
                    "source_digest": _digest(ast.get_source_segment(source, node) or ""),
                })
        return sorted(result, key=lambda item: (item["file"], item["line_start"], item["symbol"]))

    def _deleted_symbols(
        self,
        request: AuraReviewRequest,
        deleted_files: Sequence[str],
    ) -> list[dict[str, Any]]:
        if request.mode != "range":
            return []
        result: list[dict[str, Any]] = []
        for file in deleted_files:
            if not file.endswith(".py"):
                continue
            try:
                source = self._git(
                    ["git", "show", f"{request.base_ref}:{file}"],
                    timeout=10,
                )
                tree = ast.parse(source, filename=file)
            except (ValueError, OSError, SyntaxError, subprocess.SubprocessError):
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue
                start = int(node.lineno)
                end = int(getattr(node, "end_lineno", start) or start)
                result.append({
                    "file": file,
                    "symbol": node.name,
                    "kind": type(node).__name__,
                    "line_start": start,
                    "line_end": end,
                    "signature": self._node_signature(node),
                    "source_digest": _digest(ast.get_source_segment(source, node) or ""),
                    "change_kind": "deleted",
                    "source_ref": request.base_ref,
                })
        return result

    @staticmethod
    def _node_signature(node: ast.AST) -> str:
        if isinstance(node, ast.ClassDef):
            return f"class {node.name}({','.join(ast.unparse(base) for base in node.bases)})"
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
            return f"{prefix} {node.name}{ast.unparse(node.args)}"
        return type(node).__name__

    def _load_topology(self) -> dict[str, Any]:
        candidates = [
            self.repo_root / "Aura_Memory" / "live_topology_ast.json",
            self.repo_root / "topology_map.json",
        ]
        for path in candidates:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, Mapping):
                return dict(payload)
        return {"nodes": [], "edges": [], "meta": {"source": "missing"}}

    @staticmethod
    def _graph_node_file(node: Mapping[str, Any]) -> str:
        raw = str(node.get("file") or "").replace("\\", "/")
        if not raw:
            raw = str(node.get("id") or "").split("::", 1)[0].replace("\\", "/")
        while raw.startswith("./"):
            raw = raw[2:]
        return raw

    def _impact_slice(
        self,
        changed_files: Sequence[str],
        changed_symbols: Sequence[Mapping[str, Any]],
        topology: Mapping[str, Any],
        *,
        max_depth: int,
        max_nodes: int,
    ) -> list[dict[str, Any]]:
        nodes = [item for item in topology.get("nodes", []) if isinstance(item, Mapping)]
        edges = [item for item in topology.get("edges", []) if isinstance(item, Mapping)]
        node_by_id = {str(item.get("id") or ""): item for item in nodes if str(item.get("id") or "")}
        file_to_nodes: dict[str, list[str]] = defaultdict(list)
        basename_to_files: dict[str, set[str]] = defaultdict(set)
        for node_id, node in node_by_id.items():
            file = self._graph_node_file(node)
            if not file:
                continue
            file_to_nodes[file].append(node_id)
            basename_to_files[Path(file).name].add(file)
        symbol_keys = {(str(item.get("file")), str(item.get("symbol"))) for item in changed_symbols}
        anchors: list[str] = []
        for changed in changed_files:
            candidates = file_to_nodes.get(changed, [])
            if not candidates and len(basename_to_files.get(Path(changed).name, set())) == 1:
                only = next(iter(basename_to_files[Path(changed).name]))
                candidates = file_to_nodes.get(only, [])
            symbol_candidates = [
                node_id for node_id in candidates
                if (changed, str(node_by_id[node_id].get("label") or node_id.rsplit("::", 1)[-1])) in symbol_keys
            ]
            for node_id in (symbol_candidates or candidates):
                if node_id not in anchors:
                    anchors.append(node_id)
        outgoing: dict[str, list[tuple[str, str]]] = defaultdict(list)
        incoming: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for edge in edges:
            source = str(edge.get("source") or "")
            target = str(edge.get("target") or "")
            if source not in node_by_id or target not in node_by_id:
                continue
            kind = str(edge.get("kind") or edge.get("type") or "relation")
            outgoing[source].append((target, kind))
            incoming[target].append((source, kind))
        records: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        queue: deque[tuple[str, int, str, str, str]] = deque()
        for anchor in anchors:
            queue.append((anchor, 0, "changed", "changed", ""))
        while queue and len(records) < max_nodes:
            node_id, depth, direction, edge_kind, parent = queue.popleft()
            key = (node_id, direction)
            if key in seen:
                continue
            seen.add(key)
            node = node_by_id.get(node_id, {})
            file = self._graph_node_file(node)
            records.append({
                "node_id": node_id,
                "file": file,
                "symbol": str(node.get("label") or node_id.rsplit("::", 1)[-1]),
                "kind": str(node.get("kind") or node.get("shape") or "unknown"),
                "line": int(node.get("line") or 0),
                "direction": direction,
                "depth": depth,
                "edge_kind": edge_kind,
                "parent_node": parent,
                "authority": "advisory_navigation_exact_source_required",
            })
            if depth >= max_depth:
                continue
            for target, kind in outgoing.get(node_id, []):
                queue.append((target, depth + 1, "callee_or_dependency", kind, node_id))
            for source, kind in incoming.get(node_id, []):
                queue.append((source, depth + 1, "caller_or_dependent", kind, node_id))
        return records

    def _augment_deleted_impacts(
        self,
        request: AuraReviewRequest,
        deleted_files: Sequence[str],
        changed_symbols: Sequence[Mapping[str, Any]],
        impact_slice: Sequence[Mapping[str, Any]],
        *,
        max_nodes: int,
    ) -> list[dict[str, Any]]:
        records = [dict(item) for item in impact_slice]
        seen = {
            (
                str(item.get("file") or ""),
                str(item.get("symbol") or ""),
                int(item.get("line") or 0),
                str(item.get("direction") or ""),
            )
            for item in records
        }
        deleted = set(deleted_files)
        for item in changed_symbols:
            file = str(item.get("file") or "")
            symbol = str(item.get("symbol") or "")
            if file not in deleted or not symbol:
                continue
            changed_key = (file, symbol, int(item.get("line_start") or 1), "changed")
            if changed_key not in seen and len(records) < max_nodes:
                records.append({
                    "node_id": f"{file}::{symbol}",
                    "file": file,
                    "symbol": symbol,
                    "kind": str(item.get("kind") or "deleted_symbol"),
                    "line": int(item.get("line_start") or 1),
                    "direction": "changed",
                    "depth": 0,
                    "edge_kind": "deleted",
                    "parent_node": "",
                    "change_kind": "deleted",
                    "authority": "exact_base_source_deleted_at_review_head",
                })
                seen.add(changed_key)
            candidate_files = self._candidate_callsite_files(
                request,
                symbol,
                [str(row.get("file") or "") for row in records],
            )
            for callsite in self._find_callsites(
                symbol,
                candidate_files,
                target_file=file,
            ):
                if not callsite.get("target_resolved"):
                    continue
                key = (
                    str(callsite["file"]),
                    symbol,
                    int(callsite["line"]),
                    "caller_or_dependent",
                )
                if key in seen:
                    continue
                records.append({
                    "node_id": f"{callsite['file']}::line:{callsite['line']}",
                    "file": callsite["file"],
                    "symbol": symbol,
                    "kind": "resolved_callsite",
                    "line": int(callsite["line"]),
                    "direction": "caller_or_dependent",
                    "depth": 1,
                    "edge_kind": "deleted_symbol_call",
                    "parent_node": f"{file}::{symbol}",
                    "authority": "exact_import_resolution_and_head_source",
                })
                seen.add(key)
                if len(records) >= max_nodes:
                    return records
        return records

    def _infer_focus_directives(
        self,
        request: AuraReviewRequest,
        diff_text: str,
        changed_files: Sequence[str],
        changed_symbols: Sequence[Mapping[str, Any]],
    ) -> list[ReviewFocusDirective]:
        corpus = "\n".join([
            request.objective,
            *request.invariants,
            *request.risk_map,
            *changed_files,
            *[str(item.get("signature") or "") for item in changed_symbols],
            diff_text[:250_000],
        ]).lower()
        specs: list[dict[str, Any]] = [
            {
                "name": "standard_correctness",
                "question": "Can the changed code fail at runtime, return the wrong state, or silently convert a dependency failure into success?",
                "risk": "correctness",
                "direction": "both",
                "required_evidence": ["exact_source", "changed_line", "reproduction_or_control_flow"],
                "suggested_tools": ["py_compile", "ruff", "focused_tests"],
                "max_depth": min(2, request.graph_depth),
                "max_nodes": min(80, request.graph_node_budget),
            },
            {
                "name": "dependency_impact",
                "question": "Do callers, callees, schemas, tests, or shared resources depend on behavior changed by this run?",
                "risk": "dependency_impact",
                "direction": "both",
                "required_evidence": ["topology_edge", "exact_source"],
                "suggested_tools": ["aura_topology", "focused_tests"],
                "max_depth": request.graph_depth,
                "max_nodes": request.graph_node_budget,
            },
            {
                "name": "test_adequacy",
                "question": "Do tests exercise the changed success path, malformed inputs, dependency failures, and authority boundaries?",
                "risk": "test_gap",
                "direction": "callers",
                "target_patterns": ["test_", "tests/"],
                "required_evidence": ["test_file", "uncovered_branch_or_missing_case"],
                "suggested_tools": ["pytest"],
                "max_depth": 1,
                "max_nodes": 40,
            },
        ]
        conditional = [
            (
                ("secret", "token", "authorization", "api_key", "sanitize", "redact"),
                {
                    "name": "credential_boundary",
                    "question": "Can credentials leak through metadata, logs, exported packets, exceptions, or suffix-based key handling while legitimate usage counters remain visible?",
                    "risk": "security",
                    "direction": "both",
                    "target_patterns": ["token", "secret", "authorization", "sanitize", "redact"],
                    "required_evidence": ["exact_source", "malformed_or_adversarial_input"],
                    "suggested_tools": ["bandit", "focused_tests"],
                },
            ),
            (
                ("except", "exception", "error", "fail closed", "blocked", "isinstance", "mapping"),
                {
                    "name": "fail_closed_dependency_packets",
                    "question": "Can a malformed return packet or unexpected dependency exception escape the facade, preserve a stale success status, or leak internals?",
                    "risk": "correctness",
                    "direction": "callees",
                    "target_patterns": ["except", "get(", "status", "ok"],
                    "required_evidence": ["exact_source", "malformed_dependency_packet", "regression_test"],
                    "suggested_tools": ["pytest"],
                },
            ),
            (
                ("schema", "contract", "dataclass", "json", "typeddict", "required_gates"),
                {
                    "name": "schema_runtime_parity",
                    "question": "Does the runtime accept, reject, serialize, and validate exactly the shapes promised by the schema and documentation?",
                    "risk": "contract",
                    "direction": "both",
                    "target_patterns": ["schema", "from_value", "to_dict", "validate"],
                    "required_evidence": ["runtime_path", "schema_path", "round_trip_test"],
                    "suggested_tools": ["focused_tests"],
                },
            ),
            (
                ("async", "await", "thread", "lock", "session", "run_id", "status"),
                {
                    "name": "state_and_concurrency",
                    "question": "Can two runs collide, overwrite state, observe stale status, block the event loop, or cross session boundaries?",
                    "risk": "concurrency",
                    "direction": "both",
                    "target_patterns": ["session", "run_id", "status", "async", "lock"],
                    "required_evidence": ["state_transition", "interleaving_or_duplicate_run_test"],
                    "suggested_tools": ["pytest"],
                },
            ),
            (
                ("subprocess", "path", "resolve", "relative_to", "export", "workspace", "ref"),
                {
                    "name": "filesystem_and_command_boundary",
                    "question": "Can a repository path, ref, symlink, export path, or command argument escape the review workspace or become command injection?",
                    "risk": "security",
                    "direction": "callees",
                    "target_patterns": ["Path", "resolve", "relative_to", "subprocess", "git"],
                    "required_evidence": ["boundary_check", "adversarial_path_or_ref"],
                    "suggested_tools": ["bandit", "focused_tests"],
                },
            ),
            (
                ("automatic_commit", "automatic_merge", "production_mutation", "human_review", "authority"),
                {
                    "name": "authority_non_mutation",
                    "question": "Can any request, delegated result, metadata field, or error path weaken the non-mutation and human-authorization invariants?",
                    "risk": "authority",
                    "direction": "both",
                    "target_patterns": ["production_mutation", "automatic_", "human_review", "authority"],
                    "required_evidence": ["contract_invariant", "tamper_test"],
                    "suggested_tools": ["focused_tests"],
                },
            ),
            (
                ("codemap", "topology", "generated", "architecture.md", "user_guide"),
                {
                    "name": "generated_artifact_consistency",
                    "question": "Do generated maps and canonical documentation match the permanent source tree after temporary tooling is removed?",
                    "risk": "compatibility",
                    "direction": "shared_resources",
                    "target_patterns": ["CODEMAP", "topology", "ARCHITECTURE", "USER_GUIDE"],
                    "required_evidence": ["regeneration", "verification"],
                    "suggested_tools": ["aura_codemap_verify"],
                },
            ),
        ]
        for needles, spec in conditional:
            if any(needle in corpus for needle in needles):
                specs.append(spec)
        return [ReviewFocusDirective.from_value(spec, origin="aura_inferred") for spec in specs]

    @staticmethod
    def _dedupe_directives(values: Iterable[ReviewFocusDirective]) -> list[ReviewFocusDirective]:
        result: list[ReviewFocusDirective] = []
        seen: set[str] = set()
        for item in values:
            key = item.directive_id
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result

    def _guidelines_for_files(self, changed_files: Sequence[str]) -> list[dict[str, Any]]:
        candidates: set[Path] = set()
        for changed in changed_files:
            current = (self.repo_root / changed).parent
            while True:
                for name in _GUIDELINE_NAMES:
                    candidates.add(current / name)
                candidates.add(current / ".github" / "copilot-instructions.md")
                candidates.add(current / ".aura" / "ARCHITECTURE.md")
                if current == self.repo_root or self.repo_root not in current.parents:
                    break
                current = current.parent
        results: list[dict[str, Any]] = []
        for path in sorted(candidates):
            if not path.is_file():
                continue
            try:
                rel = path.relative_to(self.repo_root).as_posix()
            except ValueError:
                continue
            results.append({
                "file": rel,
                "digest": _file_digest(path),
                "scope": path.parent.relative_to(self.repo_root).as_posix() if path.parent != self.repo_root else ".",
            })
        return results

    def _routing_frame(
        self,
        request: AuraReviewRequest,
        changed_files: Sequence[str],
        guidelines: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        artifact = "python_module" if all(file.endswith(".py") for file in changed_files) else "patch"
        scope = "file" if len(changed_files) == 1 else ("subsystem" if len(changed_files) <= 12 else "repo")
        risk_text = " ".join([*request.risk_map, *request.invariants]).lower()
        risk = "high" if any(word in risk_text for word in ("security", "authority", "production", "credential")) else "medium"
        quality = "accuracy_first" if request.profile in {"precision", "exhaustive"} else "balanced"
        grounding = ["file_exists", "codemap_grounded"]
        if guidelines:
            grounding.append("manifest_owner")
        if self._select_test_files(changed_files, []):
            grounding.append("tests_exist")
        try:
            from aura_fst_routing import RoutingFrame

            return RoutingFrame(
                intent="verify",
                artifact=artifact,
                action="inspect",
                scope=scope,
                risk=risk,
                grounding=tuple(grounding),
                tests="required" if request.run_tests else "existing",
                quality=quality,
                cost="local_first",
            ).to_dict()
        except Exception:  # noqa: BLE001
            return {
                "intent": "verify",
                "artifact": artifact,
                "action": "inspect",
                "scope": scope,
                "risk": risk,
                "grounding": grounding,
                "tests": "required" if request.run_tests else "existing",
                "quality": quality,
                "cost": "local_first",
            }

    def _scan_python_file(self, file: str) -> list[dict[str, Any]]:
        path = self._resolve_file(file)
        if path is None or not path.exists():
            return [{
                "origin": "builtin_ast",
                "rule": "changed-file-missing",
                "category": "correctness",
                "severity": "high",
                "confidence": 1.0,
                "title": "Changed file is missing from the working tree",
                "message": "The diff references a file that cannot be read at the reviewed head.",
                "file": file,
                "line_start": 1,
                "line_end": 1,
                "suggested_fix": "Verify the reviewed head/ref and deletion semantics before relying on this review.",
                "evidence": [{"kind": "filesystem", "source": "review_head"}],
                "status": "confirmed",
            }]
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=file)
        except SyntaxError as exc:
            return [{
                "origin": "builtin_ast",
                "rule": "python-syntax-error",
                "category": "syntax",
                "severity": "blocker",
                "confidence": 1.0,
                "title": "Python syntax error",
                "message": str(exc.msg),
                "file": file,
                "line_start": int(exc.lineno or 1),
                "line_end": int(exc.lineno or 1),
                "suggested_fix": "Repair the syntax error before semantic review.",
                "evidence": [{"kind": "parser", "source": "ast.parse", "offset": exc.offset}],
                "status": "confirmed",
            }]
        except OSError:
            return []
        visitor = _ASTReviewVisitor(file=file)
        visitor.visit(tree)
        return visitor.findings

    def _scan_signature_impacts(self, state: Mapping[str, Any]) -> list[dict[str, Any]]:
        request: AuraReviewRequest = state["request"]
        if request.mode != "range":
            return []
        contract: AuraReviewContract = state["contract"]
        impact_files = sorted({
            str(item.get("file") or "")
            for item in contract.impact_slice
            if str(item.get("file") or "").endswith(".py")
        })[:160]
        findings: list[dict[str, Any]] = []
        for changed in contract.changed_files:
            if not changed.endswith(".py"):
                continue
            current_path = self._resolve_file(changed)
            try:
                current = (
                    current_path.read_text(encoding="utf-8", errors="replace")
                    if current_path is not None and current_path.is_file()
                    else ""
                )
                base = self._git(
                    ["git", "show", f"{request.base_ref}:{changed}"],
                    timeout=10,
                )
            except (OSError, ValueError, subprocess.SubprocessError):
                base = ""
            if not current and not base:
                continue
            old_signatures = self._function_signatures(base)
            new_signatures = self._function_signatures(current)
            changed_names = {
                name
                for name in set(old_signatures) | set(new_signatures)
                if old_signatures.get(name) != new_signatures.get(name)
            }
            for name in sorted(changed_names):
                old = old_signatures.get(name)
                new = new_signatures.get(name)
                callsites = self._find_callsites(
                    name,
                    self._candidate_callsite_files(request, name, impact_files),
                    target_file=changed,
                )
                if old and not new:
                    for callsite in callsites:
                        resolved = bool(callsite.get("target_resolved"))
                        findings.append({
                            "origin": "signature_impact",
                            "rule": "removed-symbol-callsite",
                            "category": "compatibility",
                            "severity": "high",
                            "confidence": 0.97 if resolved else 0.68,
                            "title": (
                                f"Resolved call site still references removed symbol {name}"
                                if resolved
                                else f"Same-named call may reference removed symbol {name}"
                            ),
                            "message": (
                                f"The import-resolved call targets {changed}, where {name} "
                                "is absent at the reviewed head."
                                if resolved
                                else f"A graph-related file calls {name}, but import resolution "
                                f"could not prove that it targets {changed}."
                            ),
                            "file": callsite["file"],
                            "line_start": callsite["line"],
                            "line_end": callsite["line"],
                            "related_files": [changed],
                            "related_symbols": [name],
                            "suggested_fix": (
                                "Update or remove the resolved call site, or restore a "
                                "compatibility facade."
                                if resolved
                                else "Resolve the call target before changing code."
                            ),
                            "evidence": [
                                {
                                    "kind": "signature_diff",
                                    "source": changed,
                                    "old": old,
                                    "new": None,
                                },
                                {"kind": "callsite", **callsite},
                            ],
                            "status": "corroborated" if resolved else "probable",
                        })
                elif (
                    old
                    and new
                    and int(new["required_positional"])
                    > int(old["required_positional"])
                ):
                    for callsite in callsites:
                        if callsite["starred"]:
                            continue
                        if int(callsite["positional_args"]) >= int(new["required_positional"]):
                            continue
                        resolved = bool(callsite.get("target_resolved"))
                        findings.append({
                            "origin": "signature_impact",
                            "rule": "callsite-arity-mismatch",
                            "category": "compatibility",
                            "severity": "high",
                            "confidence": 0.97 if resolved else 0.72,
                            "title": (
                                f"Resolved call site does not satisfy the new {name} signature"
                                if resolved
                                else f"Same-named call may not satisfy the new {name} signature"
                            ),
                            "message": (
                                "The import-resolved call targets the reviewed function and "
                                "supplies fewer positional arguments than its new signature requires."
                                if resolved
                                else "The call has too few arguments for the reviewed signature, "
                                "but the target remains ambiguous."
                            ),
                            "file": callsite["file"],
                            "line_start": callsite["line"],
                            "line_end": callsite["line"],
                            "related_files": [changed],
                            "related_symbols": [name],
                            "suggested_fix": (
                                "Update the resolved call site or provide a backwards-compatible default."
                                if resolved
                                else "Resolve the call target before proposing a repair."
                            ),
                            "evidence": [
                                {
                                    "kind": "signature_diff",
                                    "source": changed,
                                    "old": old,
                                    "new": new,
                                },
                                {"kind": "callsite", **callsite},
                            ],
                            "status": "corroborated" if resolved else "probable",
                        })
        return findings

    def _candidate_callsite_files(
        self,
        request: AuraReviewRequest,
        symbol: str,
        impact_files: Sequence[str],
    ) -> list[str]:
        result: list[str] = []
        for file in impact_files:
            try:
                safe = _safe_repo_path(file, field_name="impact_file")
            except ValueError:
                continue
            if safe and safe.endswith(".py") and safe not in result:
                result.append(safe)
        completed = self._run_command_impl(
            ["git", "grep", "-l", "--fixed-strings", "-e", symbol, "--", "*.py"],
            self.repo_root,
            20,
        )
        if completed.returncode in {0, 1}:
            for line in str(completed.stdout or "").splitlines():
                try:
                    safe = _safe_repo_path(line, field_name="grep_file")
                except ValueError:
                    continue
                if safe and safe.endswith(".py") and safe not in result:
                    result.append(safe)
                if len(result) >= 200:
                    break
        return result

    @staticmethod
    def _function_signatures(source: str) -> dict[str, dict[str, Any]]:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return {}
        result: dict[str, dict[str, Any]] = {}
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            positional = [*node.args.posonlyargs, *node.args.args]
            if positional and positional[0].arg in {"self", "cls"}:
                positional = positional[1:]
            required = max(0, len(positional) - len(node.args.defaults))
            result[node.name] = {
                "required_positional": required,
                "max_positional": None if node.args.vararg else len(positional),
                "required_kwonly": sorted(
                    arg.arg for arg, default in zip(node.args.kwonlyargs, node.args.kw_defaults) if default is None
                ),
                "has_vararg": node.args.vararg is not None,
                "has_varkw": node.args.kwarg is not None,
                "line": int(node.lineno),
                "signature": AuraReviewArena._node_signature(node),
            }
        return result

    @staticmethod
    def _module_candidates_for_file(file: str) -> set[str]:
        path = PurePosixPath(file)
        parts = list(path.with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            parts.pop()
        candidates: set[str] = set()
        if parts:
            candidates.add(".".join(parts))
            if parts[0] in {"src", "lib"} and len(parts) > 1:
                candidates.add(".".join(parts[1:]))
        return {item for item in candidates if item}

    @staticmethod
    def _resolve_import_module(
        caller_file: str,
        module: str | None,
        level: int,
    ) -> str:
        module_parts = [part for part in str(module or "").split(".") if part]
        if level <= 0:
            return ".".join(module_parts)
        package_parts = list(PurePosixPath(caller_file).parent.parts)
        trim = max(0, level - 1)
        if trim:
            package_parts = package_parts[: max(0, len(package_parts) - trim)]
        return ".".join([*package_parts, *module_parts])

    @staticmethod
    def _dotted_name(node: ast.AST) -> str:
        parts: list[str] = []
        current: ast.AST | None = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
            return ".".join(reversed(parts))
        return ""

    def _find_callsites(
        self,
        symbol: str,
        files: Sequence[str],
        *,
        target_file: str,
    ) -> list[dict[str, Any]]:
        target_modules = self._module_candidates_for_file(target_file)
        result: list[dict[str, Any]] = []
        for file in files:
            path = self._resolve_file(file)
            if path is None or not path.is_file():
                continue
            try:
                tree = ast.parse(
                    path.read_text(encoding="utf-8", errors="replace"),
                    filename=file,
                )
            except (OSError, SyntaxError):
                continue

            direct_aliases: dict[str, tuple[str, str]] = {}
            module_aliases: dict[str, str] = {}
            imported_modules: set[str] = set()
            for import_node in ast.walk(tree):
                if isinstance(import_node, ast.Import):
                    for alias in import_node.names:
                        imported_modules.add(alias.name)
                        local = alias.asname or alias.name.split(".", 1)[0]
                        module_aliases[local] = (
                            alias.name if alias.asname else alias.name.split(".", 1)[0]
                        )
                elif isinstance(import_node, ast.ImportFrom):
                    resolved_module = self._resolve_import_module(
                        file,
                        import_node.module,
                        import_node.level,
                    )
                    if resolved_module:
                        imported_modules.add(resolved_module)
                    for alias in import_node.names:
                        if alias.name == "*":
                            continue
                        local = alias.asname or alias.name
                        direct_aliases[local] = (resolved_module, alias.name)
                        imported_child = ".".join(
                            item for item in (resolved_module, alias.name) if item
                        )
                        if imported_child:
                            module_aliases[local] = imported_child

            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                resolution = ""
                target_resolved = False
                target_module = ""
                call_name = ""
                matches_symbol = False

                if isinstance(node.func, ast.Name):
                    call_name = node.func.id
                    imported = direct_aliases.get(call_name)
                    if imported and imported[1] == symbol:
                        matches_symbol = True
                        if imported[0] in target_modules:
                            target_resolved = True
                            resolution = "from_import"
                            target_module = imported[0]
                        else:
                            resolution = "imported_from_other_module"
                    elif call_name == symbol:
                        matches_symbol = True
                        if file == target_file:
                            target_resolved = True
                            resolution = "same_file"
                            target_module = next(iter(sorted(target_modules)), "")
                        else:
                            resolution = "ambiguous_name"
                elif isinstance(node.func, ast.Attribute):
                    dotted = self._dotted_name(node.func)
                    if not dotted or node.func.attr != symbol:
                        continue
                    call_name = symbol
                    matches_symbol = True
                    prefix = dotted.rsplit(".", 1)[0]
                    parts = prefix.split(".")
                    root = parts[0]
                    resolved_prefix = prefix
                    if root in module_aliases:
                        resolved_prefix = ".".join(
                            [module_aliases[root], *parts[1:]]
                        )
                    if resolved_prefix in target_modules and (
                        resolved_prefix in imported_modules
                        or root in module_aliases
                    ):
                        target_resolved = True
                        resolution = "module_attribute"
                        target_module = resolved_prefix
                    else:
                        resolution = "ambiguous_attribute"
                else:
                    continue

                if not matches_symbol:
                    continue
                result.append({
                    "file": file,
                    "line": int(node.lineno),
                    "local_call_name": call_name,
                    "original_symbol": symbol,
                    "positional_args": len(node.args),
                    "keyword_args": sorted(
                        keyword.arg for keyword in node.keywords if keyword.arg
                    ),
                    "starred": any(
                        isinstance(arg, ast.Starred) for arg in node.args
                    ) or any(keyword.arg is None for keyword in node.keywords),
                    "target_file": target_file,
                    "target_modules": sorted(target_modules),
                    "target_module": target_module,
                    "target_resolved": target_resolved,
                    "resolution": resolution,
                })
        return result

    def _run_tools(self, state: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        request: AuraReviewRequest = state["request"]
        contract: AuraReviewContract = state["contract"]
        changed = list(contract.changed_files)
        py_files = [file for file in changed if file.endswith(".py") and (self.repo_root / file).is_file()]
        tests = self._select_test_files(changed, contract.impact_slice)
        plans: list[tuple[str, list[str], int]] = []
        if request.mode == "range":
            plans.append(("git_diff_check", ["git", "diff", "--check", request.base_ref, request.head_ref, "--"], 20))
        # Syntax is checked in-process with ast.parse so review does not write
        # __pycache__ artifacts into the reviewed tree.
        if request.run_optional_tools and py_files and shutil.which("ruff"):
            plans.append(("ruff", ["ruff", "check", "--output-format", "json", *py_files[:80]], 60))
        if request.run_optional_tools and py_files and shutil.which("bandit"):
            plans.append(("bandit", ["bandit", "-q", "-f", "json", *py_files[:80]], 90))
        if request.run_tests and tests:
            plans.append(
                (
                    "pytest",
                    [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *tests[:16]],
                    180,
                )
            )
        # Semgrep/CodeQL/Joern adapters must be explicit local capabilities with
        # pinned configuration. V1 never invokes network-backed auto rules.
        results: list[dict[str, Any]] = []
        findings: list[dict[str, Any]] = []
        for name, command, timeout in plans:
            started = time.monotonic()
            try:
                completed = self._run_command_impl(command, self.repo_root, timeout)
                result = {
                    "tool": name,
                    "command": command[:4] + (["..."] if len(command) > 4 else []),
                    "returncode": completed.returncode,
                    "duration_ms": int((time.monotonic() - started) * 1000),
                    "stdout": _truncate(completed.stdout, 12000),
                    "stderr": _truncate(completed.stderr, 12000),
                    "timed_out": False,
                }
            except subprocess.TimeoutExpired:
                result = {
                    "tool": name,
                    "returncode": 124,
                    "duration_ms": int((time.monotonic() - started) * 1000),
                    "stdout": "",
                    "stderr": "tool timed out",
                    "timed_out": True,
                }
            except OSError as exc:
                result = {
                    "tool": name,
                    "returncode": 127,
                    "duration_ms": int((time.monotonic() - started) * 1000),
                    "stdout": "",
                    "stderr": type(exc).__name__,
                    "timed_out": False,
                }
            results.append(result)
            findings.extend(self._tool_findings(name, result))
        return results, findings

    def _tool_findings(self, name: str, result: Mapping[str, Any]) -> list[dict[str, Any]]:
        stdout = str(result.get("stdout") or "")
        stderr = str(result.get("stderr") or "")
        returncode = int(result.get("returncode") or 0)
        findings: list[dict[str, Any]] = []
        if name == "ruff" and stdout:
            try:
                payload = json.loads(stdout)
            except json.JSONDecodeError:
                payload = []
            if isinstance(payload, list):
                for item in payload:
                    if not isinstance(item, Mapping):
                        continue
                    location = item.get("location") if isinstance(item.get("location"), Mapping) else {}
                    end_location = item.get("end_location") if isinstance(item.get("end_location"), Mapping) else {}
                    findings.append({
                        "origin": "tool",
                        "rule": str(item.get("code") or "ruff"),
                        "category": "correctness",
                        "severity": "medium",
                        "confidence": 0.98,
                        "title": str(item.get("message") or "Ruff finding"),
                        "message": str(item.get("message") or "Ruff reported a code-quality issue."),
                        "file": _normalize_tool_path(item.get("filename"), self.repo_root),
                        "line_start": int(location.get("row") or 1),
                        "line_end": int(end_location.get("row") or location.get("row") or 1),
                        "suggested_fix": "Apply the Ruff rule's recommended correction and rerun the focused checks.",
                        "evidence": [{"kind": "tool", "source": "ruff", "code": item.get("code")}],
                        "status": "confirmed",
                    })
        elif name == "bandit" and stdout:
            try:
                payload = json.loads(stdout)
            except json.JSONDecodeError:
                payload = {}
            for item in payload.get("results", []) if isinstance(payload, Mapping) else []:
                if not isinstance(item, Mapping):
                    continue
                severity = str(item.get("issue_severity") or "MEDIUM").lower()
                findings.append({
                    "origin": "tool",
                    "rule": str(item.get("test_id") or "bandit"),
                    "category": "security",
                    "severity": severity if severity in _ALLOWED_SEVERITIES else "medium",
                    "confidence": 0.97,
                    "title": str(item.get("issue_text") or "Bandit security finding"),
                    "message": str(item.get("issue_text") or "Bandit identified a security-sensitive pattern."),
                    "file": str(item.get("filename") or ""),
                    "line_start": int(item.get("line_number") or 1),
                    "line_end": int(item.get("line_number") or 1),
                    "suggested_fix": "Apply the Bandit guidance and add a regression test for the security boundary.",
                    "evidence": [{"kind": "tool", "source": "bandit", "test_id": item.get("test_id")}],
                    "status": "confirmed",
                })
        elif name == "semgrep" and stdout:
            try:
                payload = json.loads(stdout)
            except json.JSONDecodeError:
                payload = {}
            for item in payload.get("results", []) if isinstance(payload, Mapping) else []:
                if not isinstance(item, Mapping):
                    continue
                start = item.get("start") if isinstance(item.get("start"), Mapping) else {}
                end = item.get("end") if isinstance(item.get("end"), Mapping) else {}
                extra = item.get("extra") if isinstance(item.get("extra"), Mapping) else {}
                findings.append({
                    "origin": "tool",
                    "rule": str(item.get("check_id") or "semgrep"),
                    "category": "security",
                    "severity": "high" if str(extra.get("severity") or "").upper() == "ERROR" else "medium",
                    "confidence": 0.96,
                    "title": str(extra.get("message") or "Semgrep finding"),
                    "message": str(extra.get("message") or "Semgrep identified a semantic pattern."),
                    "file": str(item.get("path") or ""),
                    "line_start": int(start.get("line") or 1),
                    "line_end": int(end.get("line") or start.get("line") or 1),
                    "suggested_fix": "Review the matched data/control flow and apply a bounded fix.",
                    "evidence": [{"kind": "tool", "source": "semgrep", "check_id": item.get("check_id")}],
                    "status": "confirmed",
                })
        elif name == "git_diff_check" and returncode != 0:
            for line in (stdout + "\n" + stderr).splitlines()[:30]:
                match = re.match(r"(.+?):(\d+):", line)
                findings.append({
                    "origin": "tool",
                    "rule": "git-diff-check",
                    "category": "correctness",
                    "severity": "medium",
                    "confidence": 1.0,
                    "title": "Git diff integrity check failed",
                    "message": line.strip() or "git diff --check reported malformed whitespace or conflict markers.",
                    "file": match.group(1) if match else "",
                    "line_start": int(match.group(2)) if match else 1,
                    "line_end": int(match.group(2)) if match else 1,
                    "suggested_fix": "Remove conflict markers or whitespace errors and rerun git diff --check.",
                    "evidence": [{"kind": "tool", "source": "git diff --check"}],
                    "status": "confirmed",
                })
        elif name == "py_compile" and returncode != 0:
            match = re.search(r'File "([^"]+)", line (\d+)', stderr)
            findings.append({
                "origin": "tool",
                "rule": "py-compile",
                "category": "syntax",
                "severity": "blocker",
                "confidence": 1.0,
                "title": "Python compilation failed",
                "message": _truncate(stderr or stdout, 1200),
                "file": match.group(1) if match else "",
                "line_start": int(match.group(2)) if match else 1,
                "line_end": int(match.group(2)) if match else 1,
                "suggested_fix": "Repair the compilation error before semantic review.",
                "evidence": [{"kind": "tool", "source": "py_compile"}],
                "status": "confirmed",
            })
        elif name == "pytest" and returncode != 0:
            findings.append({
                "origin": "tool",
                "rule": "focused-pytest-failure",
                "category": "correctness",
                "severity": "high",
                "confidence": 1.0,
                "title": "Focused regression tests failed",
                "message": _truncate(stdout + "\n" + stderr, 4000),
                "file": "",
                "line_start": 1,
                "line_end": 1,
                "suggested_fix": "Use the failing test and traceback as the primary repair evidence.",
                "evidence": [{"kind": "test", "source": "pytest", "returncode": returncode}],
                "status": "confirmed",
            })
        elif result.get("timed_out"):
            findings.append({
                "origin": "tool",
                "rule": f"{name}-timeout",
                "category": "tool_failure",
                "severity": "low",
                "confidence": 1.0,
                "title": f"{name} exceeded the bounded review timeout",
                "message": "The scan is incomplete because this tool did not finish within its lease.",
                "file": "",
                "line_start": 1,
                "line_end": 1,
                "suggested_fix": "Run a narrower target or grant a separately approved larger tool budget.",
                "evidence": [{"kind": "tool", "source": name, "timeout": True}],
                "status": "confirmed",
            })
        return findings

    def _select_test_files(
        self,
        changed_files: Sequence[str],
        impact_slice: Sequence[Mapping[str, Any]],
    ) -> list[str]:
        candidates: list[str] = []
        source_files = [file for file in changed_files if file.endswith(".py") and "test" not in Path(file).name]
        for file in changed_files:
            if file.endswith(".py") and (Path(file).name.startswith("test_") or "/tests/" in f"/{file}"):
                candidates.append(file)
        for item in impact_slice:
            file = str(item.get("file") or "")
            if file.endswith(".py") and (Path(file).name.startswith("test_") or "/tests/" in f"/{file}"):
                candidates.append(file)
        for source in source_files:
            stem = Path(source).stem
            likely = [
                f"tests/test_{stem}.py",
                f"test_{stem}.py",
            ]
            for file in likely:
                if (self.repo_root / file).is_file():
                    candidates.append(file)
        return list(dict.fromkeys(candidates))[:24]

    def _agent_packet_from_state(
        self,
        review_id: str,
        *,
        include_source: bool,
        max_files: int = 24,
        max_lines_per_file: int = 120,
    ) -> dict[str, Any]:
        state = self._reviews[review_id]
        contract: AuraReviewContract = state["contract"]
        files: list[str] = list(contract.changed_files)
        for item in contract.impact_slice:
            file = str(item.get("file") or "")
            if file and file not in files:
                files.append(file)
            if len(files) >= max_files:
                break
        manifest: list[dict[str, Any]] = []
        ranges = state.get("changed_ranges", {})
        symbols_by_file: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in contract.changed_symbols:
            symbols_by_file[str(item.get("file") or "")].append(dict(item))
        for file in files[:max_files]:
            path = self._resolve_file(file)
            deleted_files = set(state.get("deleted_files", ()))
            entry: dict[str, Any] = {
                "file": file,
                "exists": bool(path and path.is_file()),
                "exists_at_review_head": bool(path and path.is_file()),
                "change_kind": "deleted" if file in deleted_files else (
                    "changed" if file in contract.changed_files else "impact"
                ),
                "digest": _file_digest(path) if path else "UNAVAILABLE",
                "changed_ranges": [list(item) for item in ranges.get(file, [])],
                "changed_symbols": symbols_by_file.get(file, []),
                "role": "changed" if file in contract.changed_files else "impact",
            }
            if include_source and path and path.is_file():
                try:
                    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
                    if entry["changed_ranges"]:
                        start = max(1, min(item[0] for item in entry["changed_ranges"]) - 20)
                    else:
                        start = 1
                    end = min(len(lines), start + max_lines_per_file - 1)
                    entry["source_slice"] = {
                        "line_start": start,
                        "line_end": end,
                        "content": "\n".join(f"{index:>6}: {lines[index - 1]}" for index in range(start, end + 1)),
                    }
                except OSError:
                    pass
            manifest.append(entry)
        return {
            "ok": True,
            "version": REVIEW_ARENA_VERSION,
            "packet_type": "AURA_REVIEW_AGENT_PACKET_V1",
            "review_id": review_id,
            "contract_id": contract.contract_id,
            "objective": state["request"].objective,
            "profile": contract.profile,
            "routing_frame": _sanitize(contract.routing_frame),
            "focus_directives": [item.to_dict() for item in contract.focus_directives],
            "invariants": list(contract.invariants),
            "risk_map": list(contract.risk_map),
            "changed_files": list(contract.changed_files),
            "changed_symbols": [_sanitize(dict(item)) for item in contract.changed_symbols],
            "impact_slice": [_sanitize(dict(item)) for item in contract.impact_slice[: state["request"].graph_node_budget]],
            "guideline_files": [_sanitize(dict(item)) for item in contract.guideline_files],
            "deterministic_findings": _sanitize(state.get("deterministic_findings", [])),
            "context_manifest": manifest,
            "agent_instructions": [
                "Treat Aura topology as navigation evidence; confirm every issue against exact source.",
                "Review every changed file or explicitly record why a file is excluded.",
                "Use focus directives to inspect callers, callees, tests, schemas, and shared resources.",
                "Return only actionable defects, not generic style preferences.",
                "Each finding must include file, line, category, severity, confidence, exact evidence, impact, and fix direction.",
                "Do not mark findings confirmed; Aura assigns evidence status.",
                "Do not edit, commit, push, open, or merge through the Review Arena.",
            ],
            "finding_schema": {
                "required": ["category", "severity", "title", "message", "file", "line_start", "evidence_excerpt", "impact", "suggested_fix"],
                "severity": sorted(_ALLOWED_SEVERITIES),
                "category": sorted(_ALLOWED_CATEGORIES),
            },
            "production_mutation": False,
            "automatic_fix": False,
            "human_review_required": True,
        }

    def _validate_agent_finding(
        self,
        value: Mapping[str, Any],
        *,
        scope: set[str],
        agent_name: str,
    ) -> dict[str, Any]:
        category = str(value.get("category") or "").strip().lower()
        severity = str(value.get("severity") or "").strip().lower()
        if category not in _ALLOWED_CATEGORIES:
            raise ValueError(f"unsupported_category:{category}")
        if severity not in _ALLOWED_SEVERITIES:
            raise ValueError(f"unsupported_severity:{severity}")
        title = str(value.get("title") or "").strip()
        message = str(value.get("message") or "").strip()
        impact = str(value.get("impact") or "").strip()
        suggested_fix = str(value.get("suggested_fix") or "").strip()
        if not all((title, message, impact, suggested_fix)):
            raise ValueError("finding_requires_title_message_impact_and_suggested_fix")
        file = _safe_repo_path(value.get("file"), field_name="finding_file")
        if not file or file not in scope:
            raise ValueError("finding_file_outside_review_scope")
        path = self._resolve_file(file)
        if path is None or not path.is_file():
            raise ValueError("finding_file_missing")
        try:
            line_start = int(value.get("line_start") or 0)
            line_end = int(value.get("line_end") or line_start)
            confidence = float(value.get("confidence", 0.7))
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("invalid_finding_numeric_field") from exc
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line_start < 1 or line_end < line_start or line_start > max(1, len(lines)):
            raise ValueError("finding_line_out_of_range")
        confidence = min(0.95, max(0.0, confidence))
        excerpt = str(value.get("evidence_excerpt") or "").strip()
        window_start = max(1, line_start - 3)
        window_end = min(len(lines), max(line_end, line_start) + 3)
        window = "\n".join(lines[window_start - 1 : window_end])
        exact = bool(excerpt and excerpt in window)
        evidence = value.get("evidence")
        if isinstance(evidence, Mapping):
            evidence_items = [dict(evidence)]
        elif isinstance(evidence, (list, tuple)):
            evidence_items = [dict(item) for item in evidence if isinstance(item, Mapping)]
        else:
            evidence_items = []
        evidence_items.append({
            "kind": "exact_source_excerpt" if exact else "source_anchor_only",
            "source": file,
            "line_start": line_start,
            "line_end": line_end,
            "excerpt_digest": _digest(excerpt) if excerpt else "",
            "source_digest": _file_digest(path),
        })
        status = "corroborated" if exact else "advisory"
        if not exact:
            confidence = min(confidence, 0.6)
        return {
            "origin": "agent",
            "agent_name": str(agent_name or "external_agent")[:120],
            "rule": str(value.get("rule") or "agent-semantic-review")[:120],
            "category": category,
            "severity": severity,
            "confidence": round(confidence, 4),
            "title": title[:300],
            "message": message[:4000],
            "impact": impact[:2000],
            "file": file,
            "line_start": line_start,
            "line_end": line_end,
            "suggested_fix": suggested_fix[:2000],
            "reproduction": str(value.get("reproduction") or "")[:2000],
            "related_files": list(_clean_strings(value.get("related_files"), field_name="related_files")),
            "related_symbols": list(_clean_strings(value.get("related_symbols"), field_name="related_symbols")),
            "focus_directive_ids": list(_clean_strings(value.get("focus_directive_ids"), field_name="focus_directive_ids")),
            "evidence": _sanitize(evidence_items),
            "status": status,
            "agent_claimed_confirmation_ignored": bool(value.get("confirmed") or value.get("status") == "confirmed"),
        }

    def _normalize_findings(
        self,
        findings: Sequence[Mapping[str, Any]],
        *,
        origin_default: str,
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        fingerprints: set[str] = set()
        for raw in findings:
            if not isinstance(raw, Mapping):
                continue
            item = _sanitize(dict(raw))
            item.setdefault("origin", origin_default)
            severity = str(item.get("severity") or "medium").lower()
            category = str(item.get("category") or "correctness").lower()
            item["severity"] = severity if severity in _ALLOWED_SEVERITIES else "medium"
            item["category"] = category if category in _ALLOWED_CATEGORIES else "correctness"
            try:
                item["confidence"] = round(min(1.0, max(0.0, float(item.get("confidence", 0.7)))), 4)
            except (TypeError, ValueError, OverflowError):
                item["confidence"] = 0.5
            item.setdefault("status", "advisory" if item["origin"] == "agent" else "probable")
            file = str(item.get("file") or "")
            if file:
                try:
                    item["file"] = _safe_repo_path(file, field_name="finding_file") or ""
                except ValueError:
                    continue
            try:
                item["line_start"] = max(1, int(item.get("line_start") or 1))
                item["line_end"] = max(
                    item["line_start"], int(item.get("line_end") or item["line_start"])
                )
            except (TypeError, ValueError, OverflowError):
                continue
            fingerprint_payload = {
                "file": item.get("file"),
                "line": item.get("line_start"),
                "category": item.get("category"),
                "rule": item.get("rule"),
                "title": re.sub(r"\s+", " ", str(item.get("title") or "").lower()).strip(),
            }
            fingerprint = _digest(fingerprint_payload, size=12)
            if fingerprint in fingerprints:
                continue
            fingerprints.add(fingerprint)
            item["finding_id"] = f"FIND-{fingerprint}"
            result.append(item)
        return result

    def _review_scope_files(self, contract: AuraReviewContract) -> set[str]:
        scope = set(contract.changed_files)
        scope.update(str(item.get("file") or "") for item in contract.impact_slice if item.get("file"))
        return {item for item in scope if item}

    @staticmethod
    def _repair_eligible(finding: Mapping[str, Any]) -> bool:
        return (
            str(finding.get("status")) in {"confirmed", "corroborated"}
            and str(finding.get("severity")) in {"blocker", "high", "medium"}
            and bool(finding.get("file"))
        )

    @staticmethod
    def _forge_repair_request(
        finding: Mapping[str, Any],
        contract: AuraReviewContract,
    ) -> dict[str, Any]:
        return {
            "objective": f"Repair review finding {finding.get('finding_id')}: {finding.get('title')}",
            "target_file": finding.get("file"),
            "acceptance_criteria": [
                f"Resolve: {finding.get('message')}",
                "Preserve every unaffected caller and contract in the Aura impact slice.",
                "Add or update a focused regression test that fails before the repair and passes after it.",
                "Pass canonical Arena verification and hotswap readiness before human review.",
            ],
            "risk_map": [
                str(finding.get("category") or "correctness"),
                str(finding.get("severity") or "medium"),
                *list(contract.risk_map),
            ],
            "constraints": [
                "review_finding_is_evidence_not_patch_authority",
                "reuse_canonical_coding_arena_and_forge_owners",
                "no_automatic_commit_push_pr_or_merge",
                "human_review_required",
            ],
            "metadata": {
                "review_contract_id": contract.contract_id,
                "review_finding_id": finding.get("finding_id"),
                "review_evidence": finding.get("evidence", []),
            },
        }

    def _resolve_file(self, file: str) -> Path | None:
        try:
            safe = _safe_repo_path(file, field_name="file")
            if not safe:
                return None
            target = (self.repo_root / safe).resolve()
            target.relative_to(self.repo_root)
            return target
        except (ValueError, OSError):
            return None


def validate_review_contract(value: Any) -> list[str]:
    """Return structural/tamper errors without granting review or patch authority."""
    if not isinstance(value, Mapping):
        return ["contract_must_be_object"]
    errors: list[str] = []
    required = {
        "version",
        "contract_id",
        "request_digest",
        "repository_head",
        "diff_digest",
        "changed_files",
        "changed_symbols",
        "impact_slice",
        "focus_directives",
        "routing_frame",
        "profile",
        "authority",
        "lifecycle",
    }
    errors.extend(f"missing:{name}" for name in sorted(required - set(value)))
    if value.get("version") != REVIEW_CONTRACT_VERSION:
        errors.append("unsupported_version")
    for name in ("contract_id", "request_digest", "diff_digest"):
        if not str(value.get(name) or "").strip():
            errors.append(f"{name}_must_not_be_empty")
    if value.get("profile") not in _ALLOWED_PROFILES:
        errors.append("invalid_profile")
    for name in ("changed_files", "changed_symbols", "impact_slice", "focus_directives", "lifecycle"):
        if not isinstance(value.get(name), (list, tuple)):
            errors.append(f"{name}_must_be_array")
    if not list(value.get("changed_files") or []):
        errors.append("changed_files_must_not_be_empty")
    for file in value.get("changed_files", []) if isinstance(value.get("changed_files"), (list, tuple)) else []:
        try:
            _safe_repo_path(file, field_name="changed_file")
        except ValueError:
            errors.append(f"invalid_changed_file:{file}")
    expected_lifecycle = [
        "FRAME", "DIFF", "SLICE", "SCAN", "INVESTIGATE", "CORROBORATE",
        "RANK", "DECIDE", "REPAIR_HANDOFF", "DISSOLVE",
    ]
    if isinstance(value.get("lifecycle"), (list, tuple)) and list(value.get("lifecycle")) != expected_lifecycle:
        errors.append("invalid_lifecycle")
    authority = value.get("authority")
    expected_authority = {
        "aura_computes_diff_and_graph": True,
        "agent_supplies_hypotheses": True,
        "agent_may_not_self_confirm": True,
        "planning_proposes": True,
        "verification_proves": True,
        "human_authorizes": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": False,
        "production_mutation": False,
        "automatic_fix": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_pull_request": False,
        "automatic_merge": False,
    }
    if not isinstance(authority, Mapping):
        errors.append("authority_must_be_object")
    else:
        for name, expected in expected_authority.items():
            if authority.get(name) != expected:
                errors.append(f"invalid_authority:{name}")
    return errors


__all__ = [
    "AuraReviewArena",
    "AuraReviewContract",
    "AuraReviewRequest",
    "PATCH_AUTHORITY",
    "REVIEW_ARENA_VERSION",
    "REVIEW_CONTRACT_VERSION",
    "REVIEW_PACKET_VERSION",
    "ReviewFocusDirective",
    "VSA_PATCH_AUTHORITY",
    "validate_review_contract",
]
