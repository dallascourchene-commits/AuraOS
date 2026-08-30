"""AWJ-032 G1 deterministic AirLLM source admission gate.

Runs before importing AirLLM or model code. The default Aura policy is a hard
remote-code refusal: any explicit True or dynamic value for trust_remote_code in
AirLLM source blocks admission. Exact remote-code allowlisting, if ever granted,
must be implemented as a separate authority-bound gate and is intentionally not
hidden in this module.
"""
from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Iterable

SCHEMA = "AuraAirLLMSourceAdmissionV1"
DEFAULT_EXPECTED_VERSION = "3.3.0"
_VERSION_RE = re.compile(r"\bversion\s*=\s*['\"]([^'\"]+)['\"]")
_PIP_MUTATION_RE = re.compile(
    r"(?:python(?:3)?\s+-m\s+pip|\bpip(?:3)?\s+install)\b", re.IGNORECASE
)
_LOADER_BOUNDARIES = frozenset({"from_pretrained", "from_config", "get_module_class"})


@dataclass(frozen=True)
class Finding:
    code: str
    path: str
    line: int
    detail: str


@dataclass(frozen=True)
class SourceAdmissionReceipt:
    schema: str
    status: str
    expected_version: str
    observed_version: str | None
    source_digest: str
    inspected_files: tuple[str, ...]
    findings: tuple[Finding, ...]
    remote_code_policy: str = "HARD_FALSE"
    claim_ceiling: str = "SOURCE_STATIC_GATE_ONLY_NOT_INSTALL_OR_RUNTIME_PROOF"

    def to_dict(self) -> dict:
        out = asdict(self)
        out["findings"] = [asdict(f) for f in self.findings]
        return out


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _file_digest(paths: Iterable[Path], root: Path) -> str:
    h = sha256()
    for path in sorted(paths, key=lambda p: _rel(p, root)):
        rel = _rel(path, root).encode("utf-8")
        data = path.read_bytes()
        h.update(len(rel).to_bytes(4, "big"))
        h.update(rel)
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    return h.hexdigest()


def _trust_value(node: ast.AST | None) -> str:
    if isinstance(node, ast.Constant) and node.value is False:
        return "FALSE"
    if isinstance(node, ast.Constant) and node.value is True:
        return "TRUE"
    return "DYNAMIC"


def _trust_finding(state: str, rel: str, line: int, detail: str) -> Finding | None:
    if state == "TRUE":
        return Finding("REMOTE_CODE_TRUE", rel, line, detail)
    if state == "DYNAMIC":
        return Finding("REMOTE_CODE_DYNAMIC", rel, line, detail)
    return None


def _static_bindings(tree: ast.AST) -> dict[str, ast.AST]:
    """Collect simple name bindings used only for conservative static folding."""
    bindings: dict[str, ast.AST] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                bindings[target.id] = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.value is not None:
                bindings[node.target.id] = node.value
    return bindings


def _const_string(
    node: ast.AST | None,
    bindings: dict[str, ast.AST],
    seen: frozenset[str] = frozenset(),
) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in seen:
            return None
        value = bindings.get(node.id)
        if value is None:
            return None
        return _const_string(value, bindings, seen | {node.id})
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _const_string(node.left, bindings, seen)
        right = _const_string(node.right, bindings, seen)
        if left is not None and right is not None:
            return left + right
        return None
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            elif isinstance(value, ast.FormattedValue):
                part = _const_string(value.value, bindings, seen)
                if part is None:
                    return None
                parts.append(part)
            else:
                return None
        return "".join(parts)
    return None


def _mapping_trust_state(
    node: ast.AST | None,
    bindings: dict[str, ast.AST],
    opaque_names: frozenset[str] = frozenset(),
    seen: frozenset[str] = frozenset(),
) -> tuple[str, bool]:
    """Return (trust state, mapping_known) for one expanded mapping."""
    if isinstance(node, ast.Name):
        if node.id in opaque_names or node.id in seen:
            return "UNKNOWN", False
        value = bindings.get(node.id)
        if value is None:
            return "UNKNOWN", False
        return _mapping_trust_state(
            value,
            bindings,
            opaque_names,
            seen | {node.id},
        )

    if isinstance(node, ast.Dict):
        state = "ABSENT"
        for key, value in zip(node.keys, node.values):
            if key is None:
                nested_state, known = _mapping_trust_state(
                    value,
                    bindings,
                    opaque_names,
                    seen,
                )
                if not known:
                    return "UNKNOWN", False
                if nested_state != "ABSENT":
                    state = nested_state
                continue
            resolved_key = _const_string(key, bindings)
            if resolved_key is None:
                return "UNKNOWN", False
            if resolved_key == "trust_remote_code":
                state = _trust_value(value)
        return state, True

    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "dict":
        state = "ABSENT"
        for kw in node.keywords:
            if kw.arg == "trust_remote_code":
                state = _trust_value(kw.value)
            elif kw.arg is None:
                nested_state, known = _mapping_trust_state(
                    kw.value,
                    bindings,
                    opaque_names,
                    seen,
                )
                if not known:
                    return "UNKNOWN", False
                if nested_state != "ABSENT":
                    state = nested_state
        if len(node.args) > 1:
            return "UNKNOWN", False
        if node.args:
            arg = node.args[0]
            if not isinstance(arg, (ast.List, ast.Tuple)):
                return "UNKNOWN", False
            for pair in arg.elts:
                if not isinstance(pair, (ast.List, ast.Tuple)) or len(pair.elts) != 2:
                    return "UNKNOWN", False
                key, value = pair.elts
                resolved_key = _const_string(key, bindings)
                if resolved_key is None:
                    return "UNKNOWN", False
                if resolved_key == "trust_remote_code":
                    state = _trust_value(value)
        return state, True

    return "UNKNOWN", False


def _mapping_opaque_mutation_names(
    tree: ast.AST,
    bindings: dict[str, ast.AST],
) -> frozenset[str]:
    """Track aliases of mappings whose later mutation cannot be statically bounded.

    This is intentionally conservative only for mappings that may later cross a
    protected loader boundary. Merely mutating an opaque dictionary is not itself
    a finding; the boundary expansion decides whether it is security-relevant.
    """
    opaque: set[str] = set()
    aliases: set[tuple[str, str]] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and isinstance(node.value, ast.Name):
                aliases.add((target.id, node.value.id))
            if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name):
                resolved_key = _const_string(target.slice, bindings)
                if resolved_key is None and _trust_value(node.value) != "FALSE":
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
                resolved_key = _const_string(target.slice, bindings)
                if resolved_key is None and _trust_value(node.value) != "FALSE":
                    opaque.add(target.value.id)
        elif (
            isinstance(node, ast.AugAssign)
            and isinstance(node.target, ast.Name)
            and isinstance(node.op, ast.BitOr)
        ):
            _, known = _mapping_trust_state(node.value, bindings)
            if not known:
                opaque.add(node.target.id)

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            owner = node.func.value
            if not isinstance(owner, ast.Name):
                continue
            if node.func.attr == "update":
                unsafe = len(node.args) > 1
                for arg in node.args:
                    _, known = _mapping_trust_state(arg, bindings)
                    unsafe = unsafe or not known
                for kw in node.keywords:
                    if kw.arg is None:
                        _, known = _mapping_trust_state(kw.value, bindings)
                        unsafe = unsafe or not known
                if unsafe:
                    opaque.add(owner.id)
            elif node.func.attr == "setdefault":
                if not node.args or _const_string(node.args[0], bindings) is None:
                    value = node.args[1] if len(node.args) >= 2 else None
                    if _trust_value(value) != "FALSE":
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


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _scan_trust_remote_code(tree: ast.AST, rel: str) -> list[Finding]:
    """Reject direct, mapping-mediated, and loader-boundary remote-code widening."""
    findings: list[Finding] = []
    bindings = _static_bindings(tree)
    opaque_names = _mapping_opaque_mutation_names(tree, bindings)

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_name = _call_name(node)
            explicit_state: str | None = None
            opaque_expansions: list[ast.AST] = []

            for kw in node.keywords:
                if kw.arg == "trust_remote_code":
                    explicit_state = _trust_value(kw.value)
                    finding = _trust_finding(
                        explicit_state,
                        rel,
                        int(getattr(node, "lineno", 0)),
                        "trust_remote_code keyword is not literal False",
                    )
                    if finding is not None:
                        findings.append(finding)
                elif kw.arg is None:
                    state, known = _mapping_trust_state(
                        kw.value,
                        bindings,
                        opaque_names,
                    )
                    if state in {"TRUE", "DYNAMIC"}:
                        finding = _trust_finding(
                            state,
                            rel,
                            int(getattr(node, "lineno", 0)),
                            "expanded trust_remote_code mapping is not literal False",
                        )
                        if finding is not None:
                            findings.append(finding)
                    elif not known:
                        opaque_expansions.append(kw.value)

            if (
                call_name in _LOADER_BOUNDARIES
                and opaque_expansions
                and explicit_state != "FALSE"
            ):
                findings.append(
                    Finding(
                        "REMOTE_CODE_OPAQUE_LOADER_KWARGS",
                        rel,
                        int(getattr(node, "lineno", 0)),
                        f"{call_name} receives opaque **kwargs without explicit trust_remote_code=False",
                    )
                )

            if isinstance(node.func, ast.Attribute) and node.func.attr == "setdefault":
                if node.args and _const_string(node.args[0], bindings) == "trust_remote_code":
                    value = node.args[1] if len(node.args) >= 2 else None
                    finding = _trust_finding(
                        _trust_value(value),
                        rel,
                        int(getattr(node, "lineno", 0)),
                        "trust_remote_code setdefault value is not literal False",
                    )
                    if finding is not None:
                        findings.append(finding)

            if (
                isinstance(node.func, ast.Name)
                and node.func.id == "setattr"
                and len(node.args) >= 3
                and _const_string(node.args[1], bindings) == "trust_remote_code"
            ):
                finding = _trust_finding(
                    _trust_value(node.args[2]),
                    rel,
                    int(getattr(node, "lineno", 0)),
                    "trust_remote_code setattr value is not literal False",
                )
                if finding is not None:
                    findings.append(finding)

        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if key is None or _const_string(key, bindings) != "trust_remote_code":
                    continue
                finding = _trust_finding(
                    _trust_value(value),
                    rel,
                    int(getattr(node, "lineno", 0)),
                    "trust_remote_code mapping value is not literal False",
                )
                if finding is not None:
                    findings.append(finding)

        value_node: ast.AST | None = None
        target: ast.AST | None = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            value_node = node.value
        elif isinstance(node, ast.AnnAssign):
            target = node.target
            value_node = node.value

        if value_node is not None and isinstance(target, ast.Subscript):
            if _const_string(target.slice, bindings) == "trust_remote_code":
                finding = _trust_finding(
                    _trust_value(value_node),
                    rel,
                    int(getattr(node, "lineno", 0)),
                    "trust_remote_code subscript assignment is not literal False",
                )
                if finding is not None:
                    findings.append(finding)

        if (
            value_node is not None
            and isinstance(target, ast.Attribute)
            and target.attr == "trust_remote_code"
        ):
            finding = _trust_finding(
                _trust_value(value_node),
                rel,
                int(getattr(node, "lineno", 0)),
                "trust_remote_code attribute assignment is not literal False",
            )
            if finding is not None:
                findings.append(finding)

    return findings


def _safe_source_file(path: Path, root: Path, findings: list[Finding]) -> bool:
    """Keep the audited source set physically inside the pinned materialization."""
    try:
        rel_hint = _rel(path, root)
    except ValueError:
        rel_hint = path.as_posix()
    if path.is_symlink():
        findings.append(
            Finding(
                "SOURCE_SYMLINK_FORBIDDEN",
                rel_hint,
                0,
                "audited AirLLM source must not be supplied through a symlink",
            )
        )
        return False
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError):
        findings.append(
            Finding(
                "SOURCE_PATH_ESCAPE_OR_UNRESOLVED",
                rel_hint,
                0,
                "source path does not resolve strictly inside the pinned root",
            )
        )
        return False
    return resolved.is_file()


def audit_airllm_source(
    root: str | Path, expected_version: str = DEFAULT_EXPECTED_VERSION
) -> SourceAdmissionReceipt:
    root = Path(root).resolve()
    findings: list[Finding] = []
    if not root.is_dir():
        return SourceAdmissionReceipt(
            SCHEMA,
            "BLOCKED",
            expected_version,
            None,
            "",
            (),
            (Finding("SOURCE_ROOT_MISSING", ".", 0, "source root is not a directory"),),
        )

    setup = root / "air_llm" / "setup.py"
    package = root / "air_llm" / "airllm"
    files: list[Path] = []
    if setup.exists():
        if _safe_source_file(setup, root, findings):
            files.append(setup)
    else:
        findings.append(
            Finding("SETUP_MISSING", "air_llm/setup.py", 0, "pinned package metadata missing")
        )
    if package.is_dir():
        for path in package.rglob("*.py"):
            if _safe_source_file(path, root, findings):
                files.append(path)
    else:
        findings.append(
            Finding("PACKAGE_MISSING", "air_llm/airllm", 0, "AirLLM package directory missing")
        )

    observed_version = None
    if setup in files:
        try:
            setup_text = setup.read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeError) as exc:
            findings.append(
                Finding("SOURCE_READ_ERROR", _rel(setup, root), 0, type(exc).__name__)
            )
        else:
            match = _VERSION_RE.search(setup_text)
            if match:
                observed_version = match.group(1)
            else:
                findings.append(
                    Finding(
                        "VERSION_UNRESOLVED",
                        _rel(setup, root),
                        0,
                        "literal package version not found",
                    )
                )
            if observed_version != expected_version:
                findings.append(
                    Finding(
                        "VERSION_MISMATCH",
                        _rel(setup, root),
                        0,
                        f"expected {expected_version!r}, observed {observed_version!r}",
                    )
                )

    readable_files: list[Path] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeError) as exc:
            findings.append(
                Finding("SOURCE_READ_ERROR", _rel(path, root), 0, type(exc).__name__)
            )
            continue
        readable_files.append(path)
        rel = _rel(path, root)
        for match in _PIP_MUTATION_RE.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            findings.append(Finding("NESTED_PIP_MUTATION", rel, line, match.group(0)))
        if path.suffix != ".py":
            continue
        try:
            tree = ast.parse(text, filename=rel)
        except SyntaxError as exc:
            findings.append(
                Finding("PYTHON_PARSE_ERROR", rel, int(exc.lineno or 0), str(exc.msg))
            )
            continue
        findings.extend(_scan_trust_remote_code(tree, rel))

    inspected = tuple(sorted(_rel(p, root) for p in files))
    digest = _file_digest(readable_files, root) if readable_files else ""
    status = "PASS" if not findings else "BLOCKED"
    return SourceAdmissionReceipt(
        schema=SCHEMA,
        status=status,
        expected_version=expected_version,
        observed_version=observed_version,
        source_digest=digest,
        inspected_files=inspected,
        findings=tuple(findings),
    )


def require_admitted(
    root: str | Path, expected_version: str = DEFAULT_EXPECTED_VERSION
) -> SourceAdmissionReceipt:
    receipt = audit_airllm_source(root, expected_version)
    if receipt.status != "PASS":
        codes = ",".join(sorted({f.code for f in receipt.findings}))
        raise RuntimeError(f"AIRLLM_BLOCKED_DEPENDENCY_SECURITY:{codes}")
    return receipt


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("source_root")
    parser.add_argument("--expected-version", default=DEFAULT_EXPECTED_VERSION)
    args = parser.parse_args()
    receipt = audit_airllm_source(args.source_root, args.expected_version)
    print(json.dumps(receipt.to_dict(), sort_keys=True, separators=(",", ":")))
    return 0 if receipt.status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())