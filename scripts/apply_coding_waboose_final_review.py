from __future__ import annotations

from pathlib import Path


REPO = Path('.')


def replace_once(path: str, old: str, new: str) -> None:
    target = REPO / path
    text = target.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'missing fragment in {path}: {old[:140]!r}')
    target.write_text(text.replace(old, new, 1), encoding='utf-8')


def replace_between(path: str, start: str, end: str, replacement: str) -> None:
    target = REPO / path
    text = target.read_text(encoding='utf-8')
    start_at = text.find(start)
    if start_at < 0:
        raise SystemExit(f'missing start marker in {path}: {start!r}')
    end_at = text.find(end, start_at)
    if end_at < 0:
        raise SystemExit(f'missing end marker in {path}: {end!r}')
    target.write_text(text[:start_at] + replacement + text[end_at:], encoding='utf-8')


def patch_review_engine() -> None:
    replace_once(
        'aura_review_arena.py',
        '''        try:
            request = AuraReviewRequest.from_value(value)
            diff_text, changed_files = self._resolve_diff(request)
''',
        '''        try:
            request = AuraReviewRequest.from_value(value)
            repository_head = self._materialized_review_head(request)
            diff_text, changed_files = self._resolve_diff(request)
''',
    )
    replace_once(
        'aura_review_arena.py',
        '''        changed_ranges = self._parse_diff_ranges(diff_text)
        changed_symbols = self._changed_symbols(changed_files, changed_ranges)
        topology = self._load_topology()
''',
        '''        changed_ranges = self._parse_diff_ranges(diff_text)
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
''',
    )
    replace_once(
        'aura_review_arena.py',
        '''        impact_slice = self._impact_slice(
            changed_files,
            changed_symbols,
            topology,
            max_depth=request.graph_depth,
            max_nodes=request.graph_node_budget,
        )
        inferred = self._infer_focus_directives(request, diff_text, changed_files, changed_symbols)
''',
        '''        impact_slice = self._impact_slice(
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
''',
    )
    replace_once(
        'aura_review_arena.py',
        '''        repository_head = self._git_head()
        diff_digest = _digest(diff_text)
''',
        '''        diff_digest = _digest(diff_text)
''',
    )
    replace_once(
        'aura_review_arena.py',
        '''            "diff_text": diff_text,
            "changed_ranges": changed_ranges,
            "topology": topology,
''',
        '''            "diff_text": diff_text,
            "changed_ranges": changed_ranges,
            "deleted_files": tuple(deleted_files),
            "topology": topology,
''',
    )
    replace_once(
        'aura_review_arena.py',
        '''        findings: list[dict[str, Any]] = []
        for file in contract.changed_files:
            if file.endswith(".py"):
                findings.extend(self._scan_python_file(file))
''',
        '''        findings: list[dict[str, Any]] = []
        deleted_files = set(state.get("deleted_files", ()))
        for file in contract.changed_files:
            if file.endswith(".py") and file not in deleted_files:
                findings.extend(self._scan_python_file(file))
''',
    )

    state_methods = '''    @staticmethod
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
        energized = state.get("waboose_energized_focus_ids", set())
        if not isinstance(energized, (set, list, tuple)):
            energized = ()
        return {
            "ok": True,
            "version": REVIEW_ARENA_VERSION,
            "review_id": str(review_id),
            "contract_id": contract.contract_id,
            "request": self._request_state_payload(state["request"]),
            "status": str(state.get("status") or "PREPARED"),
            "created_at": float(state.get("created_at") or time.time()),
            "deterministic_findings": _sanitize(state.get("deterministic_findings", [])),
            "agent_findings": _sanitize(state.get("agent_findings", [])),
            "tool_results": _sanitize(state.get("tool_results", [])),
            "waboose_energized_focus_ids": sorted(str(item) for item in energized),
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

        def _finding_rows(name: str) -> list[Mapping[str, Any]]:
            raw = value.get(name, [])
            if isinstance(raw, (str, bytes)) or not isinstance(raw, (list, tuple)):
                return []
            return [dict(item) for item in raw if isinstance(item, Mapping)]

        state["deterministic_findings"] = self._normalize_findings(
            _finding_rows("deterministic_findings"),
            origin_default="deterministic",
        )
        state["agent_findings"] = self._normalize_findings(
            _finding_rows("agent_findings"),
            origin_default="agent",
        )
        raw_tools = value.get("tool_results", [])
        state["tool_results"] = (
            [dict(item) for item in raw_tools if isinstance(item, Mapping)]
            if isinstance(raw_tools, (list, tuple))
            else []
        )
        allowed_statuses = {
            "PREPARED",
            "WAITING_FOR_AGENT",
            "SCANNED",
            "AGENT_FINDINGS_RECEIVED",
            "READY_FOR_HUMAN_REVIEW",
        }
        status = str(value.get("status") or "PREPARED")
        state["status"] = status if status in allowed_statuses else "PREPARED"
        try:
            state["created_at"] = float(value.get("created_at") or time.time())
        except (TypeError, ValueError, OverflowError):
            state["created_at"] = time.time()
        raw_energized = value.get("waboose_energized_focus_ids", [])
        state["waboose_energized_focus_ids"] = {
            str(item)
            for item in raw_energized
            if str(item).strip()
        } if isinstance(raw_energized, (list, tuple, set)) else set()
        state.pop("waboose_breadboard", None)
        state.pop("final_packet", None)
        self._reviews[review_id] = state
        return {
            "ok": True,
            "version": REVIEW_ARENA_VERSION,
            "review_id": review_id,
            "contract_id": contract_id,
            "status": state["status"],
            "production_mutation": False,
            "automatic_fix": False,
            "human_review_required": True,
        }

'''
    replace_once(
        'aura_review_arena.py',
        '    def _resolve_diff(self, request: AuraReviewRequest) -> tuple[str, list[str]]:\n',
        state_methods + '    def _resolve_diff(self, request: AuraReviewRequest) -> tuple[str, list[str]]:\n',
    )

    replace_once(
        'aura_review_arena.py',
        '''    def _git_head(self) -> str:
        try:
            return self._git(["git", "rev-parse", "HEAD"], timeout=5).strip() or "UNAVAILABLE"
        except (ValueError, OSError, subprocess.SubprocessError):
            return "UNAVAILABLE"

''',
        '''    def _git_head(self) -> str:
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
        tracked_status = self._git(
            ["git", "status", "--porcelain=v1", "--untracked-files=no"],
            timeout=10,
        )
        if tracked_status.strip():
            raise ValueError("range_review_requires_clean_tracked_worktree")
        return requested

''',
    )

    replace_between(
        'aura_review_arena.py',
        '    @staticmethod\n    def _files_from_diff',
        '    @staticmethod\n    def _parse_diff_ranges',
        '''    @staticmethod
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

''',
    )

    replace_once(
        'aura_review_arena.py',
        '    @staticmethod\n    def _node_signature(node: ast.AST) -> str:\n',
        '''    def _deleted_symbols(
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
''',
    )

    replace_once(
        'aura_review_arena.py',
        '''        return records

    def _infer_focus_directives(
''',
        '''        return records

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
''',
    )

    replace_between(
        'aura_review_arena.py',
        '    def _scan_signature_impacts(',
        '    @staticmethod\n    def _function_signatures',
        '''    def _scan_signature_impacts(self, state: Mapping[str, Any]) -> list[dict[str, Any]]:
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

''',
    )

    replace_once(
        'aura_review_arena.py',
        '''            entry: dict[str, Any] = {
                "file": file,
                "exists": bool(path and path.is_file()),
                "digest": _file_digest(path) if path else "UNAVAILABLE",
''',
        '''            deleted_files = set(state.get("deleted_files", ()))
            entry: dict[str, Any] = {
                "file": file,
                "exists": bool(path and path.is_file()),
                "exists_at_review_head": bool(path and path.is_file()),
                "change_kind": "deleted" if file in deleted_files else (
                    "changed" if file in contract.changed_files else "impact"
                ),
                "digest": _file_digest(path) if path else "UNAVAILABLE",
''',
    )


def patch_cli() -> None:
    Path('aura_coding_waboose_cli.py').write_text('''"""Command-line interface for Coding Waboose V1."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Mapping
import uuid

from aura_coding_waboose import CodingWaboose

STATE_VERSION = "AURA_CODING_WABOOSE_CLI_STATE_V1"


def _load_json(value: str) -> Any:
    path = Path(value)
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)


def _state_path(repo_root: str, value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = Path(repo_root).resolve() / path
    return path.resolve()


def _load_state_store(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": STATE_VERSION, "reviews": {}}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping) or payload.get("version") != STATE_VERSION:
        raise ValueError("invalid Coding Waboose CLI state file")
    reviews = payload.get("reviews")
    if not isinstance(reviews, Mapping):
        raise ValueError("Coding Waboose CLI state file has no review map")
    return {"version": STATE_VERSION, "reviews": dict(reviews)}


def _restore_review(arena: CodingWaboose, state_path: Path, review_id: str) -> None:
    store = _load_state_store(state_path)
    payload = store["reviews"].get(review_id)
    if not isinstance(payload, Mapping):
        raise ValueError(f"review state not found: {review_id}")
    restored = arena.import_review_state(payload)
    if not restored.get("ok"):
        raise ValueError(
            f"review state could not be revalidated: {restored.get('error', 'unknown')}"
        )


def _save_review(arena: CodingWaboose, state_path: Path, review_id: str) -> None:
    exported = arena.export_review_state(review_id)
    if not exported.get("ok"):
        raise ValueError(str(exported.get("error") or "review state export failed"))
    store = _load_state_store(state_path)
    store["reviews"][review_id] = exported
    state_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = state_path.with_name(
        f".{state_path.name}.{uuid.uuid4().hex}.tmp"
    )
    temporary.write_text(
        json.dumps(store, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary.replace(state_path)
    try:
        state_path.chmod(0o600)
    except OSError:
        pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Coding Waboose, Aura's graph-guided diagnostic code-review organ."
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--state-file",
        default=".aura/waboose_cli_state.json",
        help="Persistent review-state file used across separate CLI invocations",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="Compile a review contract and agent packet")
    prepare.add_argument("--request", required=True, help="JSON object or path to JSON file")

    run = sub.add_parser("run", help="Run deterministic scan and finalize without agent findings")
    run.add_argument("--request", required=True, help="JSON object or path to JSON file")

    scan = sub.add_parser("scan", help="Run deterministic scans for a prepared review")
    scan.add_argument("--review-id", required=True)

    packet = sub.add_parser("agent-packet", help="Emit a bounded packet for a coding agent")
    packet.add_argument("--review-id", required=True)
    packet.add_argument("--include-source", action="store_true")
    packet.add_argument("--max-files", type=int, default=24)
    packet.add_argument("--max-lines-per-file", type=int, default=120)

    submit = sub.add_parser("submit-findings", help="Submit structured coding-agent findings")
    submit.add_argument("--review-id", required=True)
    submit.add_argument("--findings", required=True, help="JSON array or path to JSON file")
    submit.add_argument("--agent-name", default="external_agent")

    finalize = sub.add_parser("finalize", help="Rank findings and compile Forge repair requests")
    finalize.add_argument("--review-id", required=True)

    status = sub.add_parser("status", help="Show persisted review status")
    status.add_argument("--review-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    arena = CodingWaboose(args.repo_root)
    state_path = _state_path(args.repo_root, args.state_file)
    lifecycle_commands = {
        "scan",
        "agent-packet",
        "submit-findings",
        "finalize",
        "status",
    }

    try:
        if args.command in lifecycle_commands:
            _restore_review(arena, state_path, args.review_id)

        if args.command == "prepare":
            result = arena.prepare(_load_json(args.request))
        elif args.command == "run":
            result = arena.run_once(_load_json(args.request))
        elif args.command == "scan":
            result = arena.scan(args.review_id)
        elif args.command == "agent-packet":
            result = arena.agent_packet(
                args.review_id,
                include_source=args.include_source,
                max_files=args.max_files,
                max_lines_per_file=args.max_lines_per_file,
            )
        elif args.command == "submit-findings":
            result = arena.submit_findings(
                args.review_id,
                _load_json(args.findings),
                agent_name=args.agent_name,
            )
        elif args.command == "finalize":
            result = arena.finalize(args.review_id)
        else:
            result = arena.status(args.review_id)

        review_id = str(result.get("review_id") or "")
        if result.get("ok") and review_id:
            _save_review(arena, state_path, review_id)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        result = {
            "ok": False,
            "version": "AURA_CODING_WABOOSE_V1",
            "error": str(exc),
            "production_mutation": False,
            "automatic_fix": False,
            "human_review_required": True,
        }

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True, default=str) + "\\n")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
''', encoding='utf-8')


def patch_tests() -> None:
    path = Path('tests/test_aura_review_arena.py')
    text = path.read_text(encoding='utf-8')
    addition = r'''


def test_range_review_requires_requested_head_to_be_checked_out_and_clean(
    tmp_path: Path,
) -> None:
    repo = build_review_repo(tmp_path)
    reviewed_head = _git(repo, "rev-parse", "HEAD")
    base = _git(repo, "rev-parse", "HEAD~1")
    _git(repo, "checkout", "--detach", base)

    wrong_head = AuraReviewArena(repo).prepare(
        {
            "objective": "Review an exact branch head",
            "base_ref": base,
            "head_ref": reviewed_head,
            "run_tests": False,
            "run_optional_tools": False,
        }
    )
    assert wrong_head["ok"] is False
    assert wrong_head["error"] == "range_head_ref_not_checked_out"

    _git(repo, "checkout", "main")
    _write(repo, "core.py", (repo / "core.py").read_text(encoding="utf-8") + "\n# dirty\n")
    dirty = AuraReviewArena(repo).prepare(
        {
            "objective": "Review an exact clean head",
            "base_ref": base,
            "head_ref": reviewed_head,
            "run_tests": False,
            "run_optional_tools": False,
        }
    )
    assert dirty["ok"] is False
    assert dirty["error"] == "range_review_requires_clean_tracked_worktree"

    _git(repo, "checkout", "--", "core.py")
    prepared = AuraReviewArena(repo).prepare(
        {
            "objective": "Review materialized head source",
            "base_ref": base,
            "head_ref": reviewed_head,
            "run_tests": False,
            "run_optional_tools": False,
        }
    )
    assert prepared["ok"] is True
    assert prepared["contract"]["repository_head"] == reviewed_head
    compute = next(
        item
        for item in prepared["contract"]["changed_symbols"]
        if item["symbol"] == "compute"
    )
    assert "increment" in compute["signature"]


def test_deletion_only_range_tracks_removed_symbols_and_surviving_callers(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "deletion-review"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "review@example.test")
    _git(repo, "config", "user.name", "Aura Review Test")
    _write(repo, "core.py", "def compute(value):\n    return value + 1\n")
    _write(
        repo,
        "caller.py",
        "from core import compute\n\ndef use():\n    return compute(1)\n",
    )
    _write(
        repo,
        "Aura_Memory/live_topology_ast.json",
        json.dumps(
            {
                "nodes": [
                    {
                        "id": "caller.py::use",
                        "file": "caller.py",
                        "label": "use",
                        "kind": "function",
                        "line": 3,
                    }
                ],
                "edges": [],
            }
        ),
    )
    _commit(repo, "base")
    (repo / "core.py").unlink()
    _commit(repo, "delete core")

    arena = AuraReviewArena(repo)
    prepared = arena.prepare(
        {
            "objective": "Review deleted API callers",
            "base_ref": "HEAD~1",
            "head_ref": "HEAD",
            "run_tests": False,
            "run_optional_tools": False,
        }
    )
    assert prepared["ok"] is True
    assert prepared["contract"]["changed_files"] == ["core.py"]
    removed = next(
        item
        for item in prepared["contract"]["changed_symbols"]
        if item["symbol"] == "compute"
    )
    assert removed["change_kind"] == "deleted"
    assert any(
        item["file"] == "caller.py"
        and item["edge_kind"] == "deleted_symbol_call"
        for item in prepared["contract"]["impact_slice"]
    )

    scanned = arena.scan(prepared["review_id"])
    finding = next(
        item
        for item in scanned["deterministic_findings"]
        if item["rule"] == "removed-symbol-callsite"
    )
    assert finding["file"] == "caller.py"
    assert finding["status"] == "corroborated"
    final = arena.finalize(prepared["review_id"])
    assert any(
        item["target_file"] == "caller.py"
        for item in final["forge_repair_requests"]
    )
'''
    if 'test_range_review_requires_requested_head_to_be_checked_out_and_clean' in text:
        raise SystemExit('review hardening tests already present')
    path.write_text(text + addition, encoding='utf-8')

    Path('tests/test_aura_coding_waboose_cli.py').write_text(r'''from __future__ import annotations

import json
from pathlib import Path

from aura_coding_waboose_cli import main
from test_aura_review_arena import build_review_repo


def _result(capsys) -> dict:
    output = capsys.readouterr().out
    return json.loads(output)


def test_cli_persists_review_across_separate_invocations(
    tmp_path: Path,
    capsys,
) -> None:
    repo = build_review_repo(tmp_path)
    state_file = tmp_path / "waboose-state.json"
    request_file = tmp_path / "request.json"
    request_file.write_text(
        json.dumps(
            {
                "objective": "Review caller compatibility",
                "base_ref": "HEAD~1",
                "head_ref": "HEAD",
                "run_tests": False,
                "run_optional_tools": False,
            }
        ),
        encoding="utf-8",
    )

    assert main(
        [
            "--repo-root",
            str(repo),
            "--state-file",
            str(state_file),
            "prepare",
            "--request",
            str(request_file),
        ]
    ) == 0
    prepared = _result(capsys)
    review_id = prepared["review_id"]
    assert state_file.is_file()

    assert main(
        [
            "--repo-root",
            str(repo),
            "--state-file",
            str(state_file),
            "scan",
            "--review-id",
            review_id,
        ]
    ) == 0
    scanned = _result(capsys)
    assert scanned["review_id"] == review_id
    assert any(
        item["rule"] == "callsite-arity-mismatch"
        for item in scanned["deterministic_findings"]
    )

    assert main(
        [
            "--repo-root",
            str(repo),
            "--state-file",
            str(state_file),
            "status",
            "--review-id",
            review_id,
        ]
    ) == 0
    status = _result(capsys)
    assert status["review_id"] == review_id
    assert status["deterministic_findings"] >= 1

    assert main(
        [
            "--repo-root",
            str(repo),
            "--state-file",
            str(state_file),
            "finalize",
            "--review-id",
            review_id,
        ]
    ) == 0
    final = _result(capsys)
    assert final["review_id"] == review_id
    assert final["forge_repair_requests"]


def test_cli_state_revalidation_fails_after_reviewed_contract_changes(
    tmp_path: Path,
    capsys,
) -> None:
    repo = build_review_repo(tmp_path)
    state_file = tmp_path / "waboose-state.json"
    request = json.dumps(
        {
            "objective": "Review exact state",
            "base_ref": "HEAD~1",
            "head_ref": "HEAD",
            "run_tests": False,
            "run_optional_tools": False,
        }
    )
    assert main(
        [
            "--repo-root",
            str(repo),
            "--state-file",
            str(state_file),
            "prepare",
            "--request",
            request,
        ]
    ) == 0
    prepared = _result(capsys)
    review_id = prepared["review_id"]

    core = repo / "core.py"
    core.write_text(core.read_text(encoding="utf-8") + "\n# tracked drift\n", encoding="utf-8")
    assert main(
        [
            "--repo-root",
            str(repo),
            "--state-file",
            str(state_file),
            "status",
            "--review-id",
            review_id,
        ]
    ) == 1
    failed = _result(capsys)
    assert failed["ok"] is False
    assert "revalidated" in failed["error"]
''', encoding='utf-8')


def main() -> None:
    patch_review_engine()
    patch_cli()
    patch_tests()


if __name__ == '__main__':
    main()
