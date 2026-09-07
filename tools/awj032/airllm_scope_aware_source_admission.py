"""Lexical-scope refinement for the AWJ032 AirLLM HARD_FALSE source gate.

The v1 gate is intentionally conservative, but its static binding table is
module-wide. Python names are not module-wide: a ``**kwargs`` parameter in one
function must not erase a mutation-bounded local ``kwargs = {...}`` mapping in a
different function. This refinement keeps every v1 finding unless the exact
opaque-loader finding can be discharged structurally inside the lexical scope
that contains the call.

This module is part of the same source-admission owner surface. It grants no
runtime, model, provider, checkpoint, deployment, or Gate10 authority.
"""
from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Iterable

from tools.awj032 import airllm_source_admission as base

SCHEMA = "AuraAirLLMSourceAdmissionLexicalScopeV2"
_SCOPE_BOUNDARIES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)


@dataclass(frozen=True)
class ScopeAwareSourceAdmissionReceipt:
    schema: str
    status: str
    expected_version: str
    observed_version: str | None
    source_digest: str
    inspected_files: tuple[str, ...]
    findings: tuple[base.Finding, ...]
    discharged_findings: tuple[base.Finding, ...]
    remote_code_policy: str = "HARD_FALSE"
    scope_policy: str = "LEXICAL_SCOPE_MUTATION_BOUNDED"
    claim_ceiling: str = "SOURCE_STATIC_GATE_ONLY_NOT_INSTALL_OR_RUNTIME_PROOF"

    def to_dict(self) -> dict:
        out = asdict(self)
        out["findings"] = [asdict(f) for f in self.findings]
        out["discharged_findings"] = [asdict(f) for f in self.discharged_findings]
        return out


def _direct_scope_nodes(scope: ast.AST) -> tuple[ast.AST, ...]:
    """Return nodes owned by one lexical scope, never descendants of nested scopes."""
    out: list[ast.AST] = []
    stack = list(reversed(list(ast.iter_child_nodes(scope))))
    while stack:
        node = stack.pop()
        out.append(node)
        if isinstance(node, _SCOPE_BOUNDARIES):
            continue
        stack.extend(reversed(list(ast.iter_child_nodes(node))))
    return tuple(out)


def _lexical_scopes(tree: ast.AST) -> tuple[ast.AST, ...]:
    scopes: list[ast.AST] = [tree]
    scopes.extend(
        node for node in ast.walk(tree)
        if isinstance(node, _SCOPE_BOUNDARIES)
    )
    return tuple(scopes)


def _static_bindings(nodes: Iterable[ast.AST]) -> dict[str, ast.AST]:
    """V1 folding semantics, restricted to one lexical scope."""
    nodes = tuple(nodes)
    candidates: dict[str, list[ast.AST]] = {}
    modeled_targets: set[int] = set()
    for node in nodes:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                candidates.setdefault(target.id, []).append(node.value)
                modeled_targets.add(id(target))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.value is not None:
                candidates.setdefault(node.target.id, []).append(node.value)
                modeled_targets.add(id(node.target))

    invalidated: set[str] = set()
    for node in nodes:
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            if id(node) not in modeled_targets:
                invalidated.add(node.id)
        elif isinstance(node, ast.arg):
            invalidated.add(node.arg)
        elif isinstance(node, ast.alias):
            invalidated.add(node.asname or node.name.split(".", 1)[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            invalidated.add(node.name)
        elif isinstance(node, ast.ExceptHandler) and isinstance(node.name, str):
            invalidated.add(node.name)
        elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and isinstance(
            getattr(node, "name", None), str
        ):
            invalidated.add(node.name)
        elif isinstance(node, ast.MatchMapping) and isinstance(
            getattr(node, "rest", None), str
        ):
            invalidated.add(node.rest)

    bindings: dict[str, ast.AST] = {}
    for name, values in candidates.items():
        if name in invalidated:
            continue
        shapes = {
            ast.dump(value, annotate_fields=True, include_attributes=False)
            for value in values
        }
        if len(shapes) == 1:
            bindings[name] = values[0]
    return bindings


def _opaque_mutation_names(
    nodes: Iterable[ast.AST], bindings: dict[str, ast.AST]
) -> frozenset[str]:
    """Track mutation uncertainty only inside the lexical scope that owns a call."""
    nodes = tuple(nodes)
    opaque: set[str] = set()
    aliases: set[tuple[str, str]] = set()

    for node in nodes:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and isinstance(node.value, ast.Name):
                aliases.add((target.id, node.value.id))
            if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name):
                key = base._const_string(target.slice, bindings)
                if key is None and base._trust_value(node.value) != "FALSE":
                    opaque.add(target.value.id)
        elif isinstance(node, ast.AnnAssign):
            target = node.target
            if isinstance(target, ast.Name) and isinstance(node.value, ast.Name):
                aliases.add((target.id, node.value.id))
            if (
                node.value is not None
                and isinstance(target, ast.Subscript)
                and isinstance(target.value, ast.Name)
            ):
                key = base._const_string(target.slice, bindings)
                if key is None and base._trust_value(node.value) != "FALSE":
                    opaque.add(target.value.id)
        elif (
            isinstance(node, ast.AugAssign)
            and isinstance(node.target, ast.Name)
            and isinstance(node.op, ast.BitOr)
        ):
            _, known = base._mapping_trust_state(node.value, bindings)
            if not known:
                opaque.add(node.target.id)

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            owner = node.func.value
            if not isinstance(owner, ast.Name):
                continue
            if node.func.attr == "update":
                unsafe = len(node.args) > 1
                for arg in node.args:
                    _, known = base._mapping_trust_state(arg, bindings)
                    unsafe = unsafe or not known
                for kw in node.keywords:
                    if kw.arg is None:
                        _, known = base._mapping_trust_state(kw.value, bindings)
                        unsafe = unsafe or not known
                if unsafe:
                    opaque.add(owner.id)
            elif node.func.attr == "setdefault":
                if not node.args or base._const_string(node.args[0], bindings) is None:
                    value = node.args[1] if len(node.args) >= 2 else None
                    if base._trust_value(value) != "FALSE":
                        opaque.add(owner.id)

    changed = True
    while changed:
        changed = False
        for left, right in aliases:
            if left in opaque and right not in opaque:
                opaque.add(right)
                changed = True
            if right in opaque and left not in opaque:
                opaque.add(left)
                changed = True
    return frozenset(opaque)


def _safe_opaque_loader_keys(tree: ast.AST) -> frozenset[tuple[int, str]]:
    """Identify v1 opaque-loader findings discharged by same-scope static proof.

    A call is dischargeable only when every ``**mapping`` expansion at that
    loader boundary is statically known in the call's lexical scope and any
    ``trust_remote_code`` entry is literal False. Unknown or mutation-opaque
    mappings remain HOLD. An explicit non-False keyword is never discharged.
    """
    safe: set[tuple[int, str]] = set()
    for scope in _lexical_scopes(tree):
        nodes = _direct_scope_nodes(scope)
        bindings = _static_bindings(nodes)
        opaque_names = _opaque_mutation_names(nodes, bindings)
        for node in nodes:
            if not isinstance(node, ast.Call):
                continue
            call_name = base._call_name(node)
            if call_name not in base._LOADER_BOUNDARIES:
                continue
            explicit_state: str | None = None
            expansions: list[ast.AST] = []
            for kw in node.keywords:
                if kw.arg == "trust_remote_code":
                    explicit_state = base._trust_value(kw.value)
                elif kw.arg is None:
                    expansions.append(kw.value)
            if not expansions or explicit_state not in (None, "FALSE"):
                continue
            proven = True
            for expansion in expansions:
                state, known = base._mapping_trust_state(
                    expansion, bindings, opaque_names
                )
                if not known or state not in {"ABSENT", "FALSE"}:
                    proven = False
                    break
            if proven:
                line = int(getattr(node, "lineno", 0))
                detail = (
                    f"{call_name} receives opaque **kwargs without explicit "
                    "trust_remote_code=False"
                )
                safe.add((line, detail))
    return frozenset(safe)


def _dischargeable_findings(path: Path) -> frozenset[tuple[int, str]]:
    try:
        text = path.read_text(encoding="utf-8", errors="strict")
        tree = ast.parse(text, filename=path.as_posix())
    except (OSError, UnicodeError, SyntaxError):
        return frozenset()
    return _safe_opaque_loader_keys(tree)


def audit_airllm_source(
    root: str | Path,
    expected_version: str = base.DEFAULT_EXPECTED_VERSION,
) -> ScopeAwareSourceAdmissionReceipt:
    """Run v1, then structurally discharge only proven cross-scope false positives."""
    root_path = Path(root).resolve()
    original = base.audit_airllm_source(root_path, expected_version)
    safe_by_path: dict[str, frozenset[tuple[int, str]]] = {}
    for rel in original.inspected_files:
        if not rel.endswith(".py"):
            continue
        safe_by_path[rel] = _dischargeable_findings(root_path / rel)

    kept: list[base.Finding] = []
    discharged: list[base.Finding] = []
    for finding in original.findings:
        key = (finding.line, finding.detail)
        if (
            finding.code == "REMOTE_CODE_OPAQUE_LOADER_KWARGS"
            and key in safe_by_path.get(finding.path, frozenset())
        ):
            discharged.append(finding)
        else:
            kept.append(finding)

    return ScopeAwareSourceAdmissionReceipt(
        schema=SCHEMA,
        status="PASS" if not kept else "BLOCKED",
        expected_version=original.expected_version,
        observed_version=original.observed_version,
        source_digest=original.source_digest,
        inspected_files=original.inspected_files,
        findings=tuple(kept),
        discharged_findings=tuple(discharged),
    )


def require_admitted(
    root: str | Path,
    expected_version: str = base.DEFAULT_EXPECTED_VERSION,
) -> ScopeAwareSourceAdmissionReceipt:
    receipt = audit_airllm_source(root, expected_version)
    if receipt.status != "PASS":
        codes = ",".join(sorted({f.code for f in receipt.findings}))
        raise RuntimeError(f"AIRLLM_BLOCKED_DEPENDENCY_SECURITY:{codes}")
    return receipt


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root")
    parser.add_argument("--expected-version", default=base.DEFAULT_EXPECTED_VERSION)
    args = parser.parse_args()
    receipt = audit_airllm_source(args.source_root, args.expected_version)
    print(json.dumps(receipt.to_dict(), sort_keys=True, separators=(",", ":")))
    return 0 if receipt.status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
