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
_PIP_MUTATION_RE = re.compile(r"(?:python(?:3)?\s+-m\s+pip|\bpip(?:3)?\s+install)\b", re.IGNORECASE)


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


def _trust_value(node: ast.AST) -> str:
    if isinstance(node, ast.Constant) and node.value is False:
        return "FALSE"
    if isinstance(node, ast.Constant) and node.value is True:
        return "TRUE"
    return "DYNAMIC"


def audit_airllm_source(root: str | Path, expected_version: str = DEFAULT_EXPECTED_VERSION) -> SourceAdmissionReceipt:
    root = Path(root).resolve()
    findings: list[Finding] = []
    if not root.is_dir():
        return SourceAdmissionReceipt(SCHEMA, "BLOCKED", expected_version, None, "", (), (
            Finding("SOURCE_ROOT_MISSING", ".", 0, "source root is not a directory"),
        ))

    setup = root / "air_llm" / "setup.py"
    package = root / "air_llm" / "airllm"
    files: list[Path] = []
    if setup.is_file():
        files.append(setup)
    else:
        findings.append(Finding("SETUP_MISSING", "air_llm/setup.py", 0, "pinned package metadata missing"))
    if package.is_dir():
        files.extend(p for p in package.rglob("*.py") if p.is_file())
    else:
        findings.append(Finding("PACKAGE_MISSING", "air_llm/airllm", 0, "AirLLM package directory missing"))

    observed_version = None
    if setup.is_file():
        setup_text = setup.read_text(encoding="utf-8", errors="strict")
        match = _VERSION_RE.search(setup_text)
        if match:
            observed_version = match.group(1)
        else:
            findings.append(Finding("VERSION_UNRESOLVED", _rel(setup, root), 0, "literal package version not found"))
        if observed_version != expected_version:
            findings.append(Finding("VERSION_MISMATCH", _rel(setup, root), 0, f"expected {expected_version!r}, observed {observed_version!r}"))

    for path in files:
        text = path.read_text(encoding="utf-8", errors="strict")
        rel = _rel(path, root)
        for match in _PIP_MUTATION_RE.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            findings.append(Finding("NESTED_PIP_MUTATION", rel, line, match.group(0)))
        if path.suffix != ".py":
            continue
        try:
            tree = ast.parse(text, filename=rel)
        except SyntaxError as exc:
            findings.append(Finding("PYTHON_PARSE_ERROR", rel, int(exc.lineno or 0), str(exc.msg)))
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for kw in node.keywords:
                if kw.arg != "trust_remote_code":
                    continue
                state = _trust_value(kw.value)
                if state == "TRUE":
                    findings.append(Finding("REMOTE_CODE_TRUE", rel, int(getattr(node, "lineno", 0)), "trust_remote_code=True"))
                elif state == "DYNAMIC":
                    findings.append(Finding("REMOTE_CODE_DYNAMIC", rel, int(getattr(node, "lineno", 0)), "trust_remote_code is not literal False"))

    inspected = tuple(sorted(_rel(p, root) for p in files))
    digest = _file_digest(files, root) if files else ""
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


def require_admitted(root: str | Path, expected_version: str = DEFAULT_EXPECTED_VERSION) -> SourceAdmissionReceipt:
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
