"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9c2-[Q-SYS:HOTSWAP_REFACTOR]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Stateless Software Update / Hotswap Safety)
DEPENDENCIES: ast, dataclasses, pathlib, typing
FUNCTIONS: HotswapSafetyReport, classify_hotswap_safety_from_sources, classify_hotswap_safety, suggest_hotswap_refactoring
SYNOPSIS: Classifies code changes using AST source comparison to determine if a patch can be
safely reloaded at runtime or if it requires refactoring or a full system restart.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any


@dataclass
class HotswapSafetyReport:
    classification: str
    reasons: list[str]
    changed_public_symbols: list[str]
    changed_class_signatures: list[str]
    module_state_findings: list[str]


def _parse_source(source: str, file_path: str = "") -> tuple[ast.Module | None, str | None]:
    try:
        return ast.parse(source or "", filename=file_path or "<hotswap>"), None
    except Exception as exc:
        return None, str(exc)


def _safe_unparse(node: ast.AST | None) -> str:
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:
        return ast.dump(node, include_attributes=False)


def _public_function_signatures(tree: ast.Module) -> dict[str, str]:
    signatures: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            returns = _safe_unparse(node.returns)
            signatures[node.name] = f"{type(node).__name__}:{ast.dump(node.args, include_attributes=False)}->{returns}"
    return signatures


def _class_bases(tree: ast.Module) -> dict[str, str]:
    classes: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            bases = [_safe_unparse(base) for base in node.bases]
            keywords = [f"{kw.arg}={_safe_unparse(kw.value)}" for kw in node.keywords]
            classes[node.name] = ",".join([*bases, *keywords])
    return classes


def _all_exports(tree: ast.Module) -> tuple[str, ...] | None:
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets):
            continue
        if not isinstance(node.value, (ast.List, ast.Tuple)):
            return None
        values: list[str] = []
        for item in node.value.elts:
            try:
                values.append(str(ast.literal_eval(item)))
            except Exception:
                return None
        return tuple(values)
    return None


def _module_mutable_assignments(tree: ast.Module) -> dict[str, str]:
    findings: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value = node.value
        if isinstance(value, (ast.List, ast.Dict, ast.Set)):
            for target in targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    findings[target.id] = type(value).__name__
        elif isinstance(value, ast.Call):
            call_name = _call_name(value)
            if call_name in {"list", "dict", "set", "defaultdict", "deque"}:
                for target in targets:
                    if isinstance(target, ast.Name) and not target.id.startswith("_"):
                        findings[target.id] = call_name
    return findings


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _call_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Call):
        return _call_name(node.func)
    return ""


def _top_level_runtime_starts(tree: ast.Module) -> list[str]:
    findings: list[str] = []
    for node in tree.body:
        calls: list[ast.Call] = []
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            calls.append(node.value)
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            calls.append(node.value)
        for call in calls:
            call_name = _call_name(call.func)
            receiver_name = _call_name(call.func.value) if isinstance(call.func, ast.Attribute) else ""
            if call_name.endswith(".start") and any(token in receiver_name for token in {"Thread", "Process"}):
                findings.append(f"top_level_start:{call_name}")
            if call_name in {"Thread", "threading.Thread", "Process", "multiprocessing.Process"}:
                findings.append(f"top_level_runtime_factory:{call_name}")
            if call_name.endswith(".run_forever") or call_name in {"asyncio.run", "run_forever"}:
                findings.append(f"top_level_event_loop:{call_name}")
    return findings


def _import_side_effect_findings(before: ast.Module, after: ast.Module) -> list[str]:
    def imports(tree: ast.Module) -> set[str]:
        names: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.Import):
                names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module)
        return names

    added = imports(after) - imports(before)
    risky = {
        name
        for name in added
        if name.split(".", 1)[0] in {"threading", "multiprocessing", "asyncio", "subprocess"}
    }
    return [f"new_runtime_import:{name}" for name in sorted(risky)]


def classify_hotswap_safety_from_sources(
    before_source: str,
    after_source: str,
    *,
    file_path: str = "",
) -> HotswapSafetyReport:
    before_tree, before_error = _parse_source(before_source, file_path)
    after_tree, after_error = _parse_source(after_source, file_path)
    if before_error or after_error or before_tree is None or after_tree is None:
        error = after_error or before_error or "unknown parse failure"
        return HotswapSafetyReport(
            classification="restart_required",
            reasons=[f"AST parse failure: {error}"],
            changed_public_symbols=[],
            changed_class_signatures=[],
            module_state_findings=[],
        )

    reasons: list[str] = []
    changed_public_symbols: list[str] = []
    changed_class_signatures: list[str] = []
    module_state_findings: list[str] = []

    before_signatures = _public_function_signatures(before_tree)
    after_signatures = _public_function_signatures(after_tree)
    for name in sorted(set(before_signatures) | set(after_signatures)):
        if before_signatures.get(name) != after_signatures.get(name):
            changed_public_symbols.append(name)
            reasons.append(f"public_signature_changed:{name}")

    before_classes = _class_bases(before_tree)
    after_classes = _class_bases(after_tree)
    for name in sorted(set(before_classes) & set(after_classes)):
        if before_classes[name] != after_classes[name]:
            changed_class_signatures.append(name)
            reasons.append(f"class_base_changed:{name}")

    before_all = _all_exports(before_tree)
    after_all = _all_exports(after_tree)
    if before_all != after_all:
        changed_public_symbols.append("__all__")
        reasons.append("public_exports_changed:__all__")

    before_mutables = _module_mutable_assignments(before_tree)
    after_mutables = _module_mutable_assignments(after_tree)
    for name, kind in sorted(after_mutables.items()):
        if before_mutables.get(name) != kind:
            module_state_findings.append(f"module_mutable_assignment:{name}:{kind}")

    before_runtime = set(_top_level_runtime_starts(before_tree))
    after_runtime = set(_top_level_runtime_starts(after_tree))
    for finding in sorted(after_runtime - before_runtime):
        module_state_findings.append(finding)
        reasons.append(finding)

    for finding in _import_side_effect_findings(before_tree, after_tree):
        module_state_findings.append(finding)

    if any(item.startswith(("top_level_start", "top_level_event_loop", "top_level_runtime_factory")) for item in module_state_findings):
        classification = "restart_required"
    elif changed_public_symbols or changed_class_signatures or module_state_findings:
        classification = "reload_requires_refactor"
    else:
        classification = "hotswap_safe"

    return HotswapSafetyReport(
        classification=classification,
        reasons=reasons or module_state_findings,
        changed_public_symbols=sorted(set(changed_public_symbols)),
        changed_class_signatures=changed_class_signatures,
        module_state_findings=module_state_findings,
    )


def _apply_unified_diff(before_source: str, diff: str) -> str | None:
    before_lines = before_source.splitlines()
    result: list[str] = []
    source_index = 0
    diff_lines = diff.splitlines()
    hunk_re = re.compile(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")
    i = 0
    applied = False
    while i < len(diff_lines):
        match = hunk_re.match(diff_lines[i])
        if not match:
            i += 1
            continue
        applied = True
        old_start = int(match.group(1)) - 1
        if old_start < source_index:
            return None
        result.extend(before_lines[source_index:old_start])
        source_index = old_start
        i += 1
        while i < len(diff_lines) and not diff_lines[i].startswith("@@ "):
            line = diff_lines[i]
            if line.startswith("\\ No newline"):
                i += 1
                continue
            prefix = line[:1]
            body = line[1:]
            if prefix == " ":
                result.append(body)
                source_index += 1
            elif prefix == "-":
                source_index += 1
            elif prefix == "+":
                result.append(body)
            elif prefix in {"-", "+"}:
                pass
            i += 1
    if not applied:
        return None
    result.extend(before_lines[source_index:])
    return "\n".join(result) + ("\n" if before_source.endswith("\n") else "")


def _classify_diff_fallback(diff: str) -> HotswapSafetyReport:
    added_lines = "\n".join(line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++"))
    if re.search(r"(Thread|Process)\s*\(.*\)\.start\s*\(", added_lines) or "run_forever(" in added_lines:
        return HotswapSafetyReport(
            classification="restart_required",
            reasons=["diff_adds_top_level_runtime_start"],
            changed_public_symbols=[],
            changed_class_signatures=[],
            module_state_findings=["diff_adds_top_level_runtime_start"],
        )
    if re.search(r"^\s*def\s+[A-Za-z_]\w*\s*\(", added_lines, re.MULTILINE):
        return HotswapSafetyReport(
            classification="reload_requires_refactor",
            reasons=["diff_may_change_public_signature"],
            changed_public_symbols=[],
            changed_class_signatures=[],
            module_state_findings=[],
        )
    return HotswapSafetyReport(
        classification="hotswap_safe",
        reasons=[],
        changed_public_symbols=[],
        changed_class_signatures=[],
        module_state_findings=[],
    )


def classify_hotswap_safety(file_path: str | Path, diff: str) -> tuple[str, list[str]]:
    """
    Analyze the current file and proposed unified diff for reload safety.

    Returns a compatibility tuple of ``(classification, reasons)``.
    """
    path = Path(file_path)
    if not path.exists():
        return "hotswap_safe", ["New file creation is hotswap safe when scoped and verifier-gated."]
    try:
        before_source = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return "restart_required", [f"Could not read source: {exc}"]

    after_source = _apply_unified_diff(before_source, diff)
    report = (
        classify_hotswap_safety_from_sources(before_source, after_source, file_path=str(path))
        if after_source is not None
        else _classify_diff_fallback(diff)
    )
    return report.classification, report.reasons


def suggest_hotswap_refactoring(file_path: str | Path, reasons: list[str]) -> str:
    """Generate refactoring instructions to turn a non-hotswappable module into a reloadable one."""
    instructions = [
        "Your proposed patch was flagged as reload-unsafe for hot-swapping due to the following:",
        *[f"- {reason}" for reason in reasons],
        "",
        "To support hot-swapping without restarting the system, refactor the code to:",
        "1. Avoid module-level mutable global variables. Wrap them in a registry or class instance getter.",
        "2. Do not start threads or run event loops directly on module load. Create start/stop functions.",
        "3. Keep public function signatures and class bases stable, or include an explicit migration plan.",
        "Please refactor the targets and resubmit the transaction.",
    ]
    return "\n".join(instructions)
