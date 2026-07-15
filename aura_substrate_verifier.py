"""Independent P9 verifier for the cognitive-substrate manifest and release index."""
from __future__ import annotations

import ast
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

from aura_event_contracts import canonical_json
from aura_substrate_contracts import VerificationFinding, VerificationReport
from aura_substrate_manifest import (
    MANIFEST_PATH,
    RELEASE_INDEX_PATH,
    build_substrate_manifest,
)
from aura_substrate_release import build_release_index

MANIFEST_ARCHIVE_PATH = Path("docs/aura_substrate_manifest.v1.json.gz")


def _safe_file(root: Path, relative: str) -> Path:
    candidate = root / relative
    resolved_root = root.resolve()
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise ValueError("file unavailable") from exc
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError("file escapes repository") from exc
    if candidate.is_symlink() or not resolved.is_file():
        raise ValueError("path is not a regular non-symlink file")
    return resolved


def _git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def _module_facts(data: bytes) -> tuple[set[str], dict[str, str], set[str]]:
    text = data.decode("utf-8")
    tree = ast.parse(text)
    symbols: set[str] = set()
    literals: dict[str, str] = {}
    imports: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.add(node.name)
        elif isinstance(node, ast.Assign):
            if isinstance(node.value, ast.Constant) and type(node.value.value) is str:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        literals[target.id] = node.value.value
        elif isinstance(node, ast.AnnAssign):
            if (
                isinstance(node.target, ast.Name)
                and isinstance(node.value, ast.Constant)
                and type(node.value.value) is str
            ):
                literals[node.target.id] = node.value.value
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    return symbols, literals, imports


def _finding(
    findings: list[VerificationFinding],
    code: str,
    message: str,
    path: str | None = None,
) -> None:
    findings.append(VerificationFinding(code, message, path))


def _read_canonical_json(
    root: Path,
    relative: str,
    findings: list[VerificationFinding],
) -> dict[str, Any] | None:
    try:
        path = _safe_file(root, relative)
        text = path.read_text(encoding="utf-8")
        parsed = json.loads(text)
    except (ValueError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        _finding(findings, "JSON_ARTIFACT_UNAVAILABLE", f"{type(exc).__name__}: {exc}", relative)
        return None
    if not isinstance(parsed, dict):
        _finding(findings, "JSON_ARTIFACT_NOT_OBJECT", "artifact must contain a JSON object", relative)
        return None
    if text != canonical_json(parsed) + "\n":
        _finding(findings, "JSON_ARTIFACT_NONCANONICAL", "artifact bytes are not canonical JSON", relative)
    return parsed


def _manifest_artifacts(manifest: Any) -> tuple[bytes, bytes, dict[str, Any]]:
    full = (canonical_json(manifest.to_dict()) + "\n").encode("utf-8")
    archive = gzip.compress(full, mtime=0)
    receipt = {
        "version": manifest.version,
        "manifest_digest": manifest.digest,
        "archive_path": MANIFEST_ARCHIVE_PATH.as_posix(),
        "archive_sha256": hashlib.sha256(archive).hexdigest(),
        "uncompressed_bytes": len(full),
        "compressed_bytes": len(archive),
        "file_count": len(manifest.files),
        "phase_count": len(manifest.phases),
        "retained_external_surfaces": list(manifest.retained_external_surfaces),
    }
    return full, archive, receipt


def _verify_manifest_artifacts(
    root: Path,
    manifest: Any,
    receipt_path: str,
    archive_path: str,
    findings: list[VerificationFinding],
) -> None:
    expected_full, expected_archive, expected_receipt = _manifest_artifacts(manifest)
    parsed_receipt = _read_canonical_json(root, receipt_path, findings)
    if parsed_receipt is not None and parsed_receipt != expected_receipt:
        _finding(
            findings,
            "MANIFEST_RECEIPT_CONTENT_MISMATCH",
            "manifest receipt does not equal the deterministic ledger metadata",
            receipt_path,
        )
    try:
        archive = _safe_file(root, archive_path).read_bytes()
    except (ValueError, OSError) as exc:
        _finding(findings, "MANIFEST_ARCHIVE_UNAVAILABLE", str(exc), archive_path)
        return
    if archive != expected_archive:
        _finding(
            findings,
            "MANIFEST_ARCHIVE_CONTENT_MISMATCH",
            "manifest archive bytes are not the deterministic gzip encoding",
            archive_path,
        )
    try:
        expanded = gzip.decompress(archive)
    except (OSError, EOFError) as exc:
        _finding(
            findings,
            "MANIFEST_ARCHIVE_INVALID",
            f"{type(exc).__name__}: {exc}",
            archive_path,
        )
        return
    if expanded != expected_full:
        _finding(
            findings,
            "MANIFEST_ARCHIVE_LEDGER_MISMATCH",
            "decompressed manifest does not equal the deterministic phase ledger",
            archive_path,
        )


def _verify_git_history(root: Path, commits: tuple[str, ...], findings: list[VerificationFinding]) -> None:
    if not (root / ".git").exists():
        _finding(findings, "GIT_HISTORY_UNAVAILABLE", "repository metadata is unavailable")
        return
    for commit in commits:
        exists = subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
            cwd=root,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if exists.returncode != 0:
            _finding(findings, "PHASE_COMMIT_UNAVAILABLE", f"commit is absent: {commit}")
            continue
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
            cwd=root,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if ancestor.returncode != 0:
            _finding(findings, "PHASE_COMMIT_NOT_ANCESTOR", f"commit is not an ancestor of HEAD: {commit}")


def verify_substrate_release(
    root: str | Path = ".",
    manifest_path: str | Path = MANIFEST_PATH,
    manifest_archive_path: str | Path = MANIFEST_ARCHIVE_PATH,
    release_index_path: str | Path = RELEASE_INDEX_PATH,
) -> VerificationReport:
    base = Path(root)
    findings: list[VerificationFinding] = []
    manifest = build_substrate_manifest()
    _verify_manifest_artifacts(
        base,
        manifest,
        str(manifest_path),
        str(manifest_archive_path),
        findings,
    )

    release_modules = {
        Path(record.path).stem
        for record in manifest.files
        if record.path.endswith(".py")
    }
    retained_modules = {
        Path(path).stem
        for phase in manifest.phases
        for path in phase.retained_dependency_paths
        if path.endswith(".py")
    }
    retained_modules.update(
        Path(path).stem
        for path in manifest.retained_external_surfaces
        if path.endswith(".py")
    )
    checked_files = 0
    checked_symbols = 0
    checked_versions = 0

    for record in manifest.files:
        try:
            path = _safe_file(base, record.path)
            data = path.read_bytes()
        except (ValueError, OSError) as exc:
            _finding(findings, "RELEASE_FILE_UNAVAILABLE", str(exc), record.path)
            continue
        checked_files += 1
        if record.expected_git_blob_sha1 is not None:
            actual = _git_blob_sha1(data)
            if actual != record.expected_git_blob_sha1:
                _finding(
                    findings,
                    "PINNED_FILE_DIGEST_MISMATCH",
                    f"expected {record.expected_git_blob_sha1}, got {actual}",
                    record.path,
                )
        if record.path.endswith(".py"):
            try:
                symbols, literals, imports = _module_facts(data)
            except (UnicodeDecodeError, SyntaxError) as exc:
                _finding(findings, "PYTHON_AST_INVALID", f"{type(exc).__name__}: {exc}", record.path)
                continue
            for symbol in record.public_symbols:
                checked_symbols += 1
                if symbol not in symbols:
                    _finding(
                        findings,
                        "PUBLIC_SYMBOL_MISSING",
                        f"module-scope symbol is absent: {symbol}",
                        record.path,
                    )
            for name, expected in record.version_bindings:
                checked_versions += 1
                actual = literals.get(name)
                if actual != expected:
                    _finding(
                        findings,
                        "VERSION_BINDING_MISMATCH",
                        f"{name} expected {expected!r}, got {actual!r}",
                        record.path,
                    )
            for module in sorted(imports):
                if module.startswith("aura_") or module == "quantum_dag":
                    if module not in release_modules and module not in retained_modules:
                        _finding(
                            findings,
                            "UNDECLARED_AURA_DEPENDENCY",
                            f"repository dependency is neither released nor retained: {module}",
                            record.path,
                        )

    for relative in manifest.retained_external_surfaces:
        try:
            _safe_file(base, relative)
            checked_files += 1
        except ValueError as exc:
            _finding(findings, "RETAINED_SURFACE_UNAVAILABLE", str(exc), relative)

    evidence_paths = sorted(
        {
            path
            for phase in manifest.phases
            for path in (*phase.evidence_paths, *phase.retained_dependency_paths)
        }
    )
    for relative in evidence_paths:
        try:
            _safe_file(base, relative)
            checked_files += 1
        except ValueError as exc:
            _finding(findings, "EVIDENCE_FILE_UNAVAILABLE", str(exc), relative)

    file_by_path = {record.path: record for record in manifest.files}
    for phase in manifest.phases:
        for component in phase.component_paths:
            record = file_by_path.get(component)
            if record is None or phase.phase_id not in record.phase_ids:
                _finding(
                    findings,
                    "PHASE_FILE_BINDING_MISMATCH",
                    f"{phase.phase_id} is not bound by the component file record",
                    component,
                )

    _verify_git_history(base, tuple(phase.merge_commit for phase in manifest.phases), findings)

    expected_index: dict[str, Any] | None
    try:
        expected_index = build_release_index(base, manifest)
    except (ValueError, OSError, UnicodeDecodeError) as exc:
        expected_index = None
        _finding(findings, "RELEASE_INDEX_BUILD_FAILED", f"{type(exc).__name__}: {exc}")
    parsed_index = _read_canonical_json(base, str(release_index_path), findings)
    if expected_index is not None and parsed_index is not None and parsed_index != expected_index:
        _finding(
            findings,
            "RELEASE_INDEX_CONTENT_MISMATCH",
            "committed release index does not equal the approved current files",
            str(release_index_path),
        )

    findings.sort(key=lambda item: (item.code, item.path or "", item.message))
    release_digest = expected_index["index_digest"] if expected_index is not None else None
    return VerificationReport(
        manifest_digest=manifest.digest,
        release_index_digest=release_digest,
        checked_files=checked_files,
        checked_symbols=checked_symbols,
        checked_versions=checked_versions,
        findings=tuple(findings),
    )


def main() -> int:
    report = verify_substrate_release()
    print(canonical_json(report.to_dict()))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["MANIFEST_ARCHIVE_PATH", "verify_substrate_release"]
