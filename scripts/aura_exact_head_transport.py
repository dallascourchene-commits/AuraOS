#!/usr/bin/env python3
"""Exact-head export and atomic publication-bundle preparation for AuraOS.

All generated state is written outside the source checkout.  This helper does not
publish, commit, push, open a pull request, or merge.  It prepares exact evidence
and whole-file payloads for Aura's existing Agent Bridge atomic publication lane.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
from typing import Any, Iterable
import zipfile

VERSION = "AURA_EXACT_HEAD_TRANSPORT_V1"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _run(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args), cwd=root, check=check, text=True, capture_output=True
    )


def _canonical_path(value: str) -> str:
    if not value or "\\" in value or "\x00" in value or re.match(r"^[A-Za-z]:", value):
        raise ValueError(f"unsafe repository path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe repository path: {value!r}")
    if path.as_posix() != value:
        raise ValueError(f"non-canonical repository path: {value!r}")
    return value


def _outside_checkout(root: Path, value: str | Path, *, create: bool = False) -> Path:
    root = root.resolve()
    path = Path(value).expanduser().resolve()
    if path == root or root in path.parents:
        raise ValueError(f"transport output must remain outside repository: {path}")
    if path.exists() and path.is_symlink():
        raise ValueError(f"transport output cannot be a symlink: {path}")
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def _status(root: Path) -> list[str]:
    result = _run(root, "git", "status", "--porcelain=v1", "--untracked-files=all")
    return [line for line in result.stdout.splitlines() if line]


def _head(root: Path) -> str:
    return _run(root, "git", "rev-parse", "HEAD").stdout.strip().lower()


def _blob_at(root: Path, revision: str, path: str) -> bytes | None:
    object_name = f"{revision}:{path}"
    exists = subprocess.run(
        ["git", "cat-file", "-e", object_name],
        cwd=root,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if exists.returncode:
        return None
    return subprocess.run(
        ["git", "cat-file", "blob", object_name],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def assert_exact_clean_head(
    root: Path,
    *,
    expected_head: str,
    diagnostics_dir: str | Path,
) -> dict[str, Any]:
    """Fail closed before creating any repository-local artifact."""
    root = root.resolve()
    if _SHA_RE.fullmatch(expected_head) is None:
        raise ValueError("expected_head must be a lowercase 40-character Git SHA-1")
    diagnostics = _outside_checkout(root, diagnostics_dir)
    observed_head = _head(root)
    dirty = _status(root)
    receipt = {
        "version": VERSION,
        "expected_head": expected_head,
        "observed_head": observed_head,
        "clean": not dirty,
        "dirty_paths": [row[3:] if len(row) > 3 else row for row in dirty],
        "status_rows": dirty,
        "repository": str(root),
        "production_mutation": False,
        "publication_authority": False,
        "merge_authority": False,
    }
    if observed_head != expected_head or dirty:
        diagnostics.mkdir(parents=True, exist_ok=True)
        _write_json_atomic(diagnostics / "exact_head_failure.json", receipt)
        if observed_head != expected_head:
            raise RuntimeError(
                f"exact HEAD mismatch: expected {expected_head}, observed {observed_head}"
            )
        paths = ", ".join(receipt["dirty_paths"][:20])
        raise RuntimeError(f"repository is dirty; refusing exact-head transport: {paths}")
    return receipt


def export_exact_head(
    root: Path,
    *,
    expected_head: str,
    output_dir: str | Path,
    diagnostics_dir: str | Path,
) -> dict[str, Any]:
    """Create a deterministic exact-head ZIP and checksum outside the checkout."""
    root = root.resolve()
    output = _outside_checkout(root, output_dir)
    if output.exists() and any(output.iterdir()):
        raise ValueError("exact-head output directory must be empty")
    initial = assert_exact_clean_head(
        root, expected_head=expected_head, diagnostics_dir=diagnostics_dir
    )
    output.mkdir(parents=True, exist_ok=True)
    archive = output / "AuraOS-full-repository.zip"
    temp_archive = output / ".AuraOS-full-repository.zip.tmp"
    _run(
        root,
        "git",
        "archive",
        "--format=zip",
        "--prefix=AuraOS/",
        f"--output={temp_archive}",
        expected_head,
    )
    os.replace(temp_archive, archive)
    digest = _sha256_file(archive)
    (output / "AuraOS-full-repository.zip.sha256").write_text(
        f"{digest}  {archive.name}\n", encoding="utf-8", newline="\n"
    )
    final = assert_exact_clean_head(
        root, expected_head=expected_head, diagnostics_dir=diagnostics_dir
    )
    receipt = {
        **initial,
        "final_clean": final["clean"],
        "archive": archive.name,
        "archive_sha256": digest,
        "archive_size_bytes": archive.stat().st_size,
        "content_source": "immutable_exact_head_git_archive",
    }
    _write_json_atomic(output / "exact_head_export_receipt.json", receipt)
    return receipt


def materialize_exact_head(
    root: Path,
    *,
    expected_head: str,
    destination: str | Path,
    diagnostics_dir: str | Path,
) -> dict[str, Any]:
    """Materialize exact HEAD outside the checkout without Git metadata."""
    root = root.resolve()
    destination_path = _outside_checkout(root, destination)
    if destination_path.exists() and any(destination_path.iterdir()):
        raise ValueError("materialization destination must be empty")
    assert_exact_clean_head(root, expected_head=expected_head, diagnostics_dir=diagnostics_dir)
    destination_path.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination_path.parent) as temporary:
        archive = Path(temporary) / "head.zip"
        _run(root, "git", "archive", "--format=zip", f"--output={archive}", expected_head)
        with zipfile.ZipFile(archive) as payload:
            payload.extractall(destination_path)
    assert_exact_clean_head(root, expected_head=expected_head, diagnostics_dir=diagnostics_dir)
    return {
        "version": VERSION,
        "expected_head": expected_head,
        "destination": str(destination_path),
        "source_checkout_clean": True,
        "production_mutation": False,
    }


def build_atomic_publication_bundle(
    root: Path,
    *,
    expected_head: str,
    candidate_root: str | Path,
    allowed_paths: Iterable[str],
    output_path: str | Path,
    diagnostics_dir: str | Path,
) -> dict[str, Any]:
    """Emit whole-file payloads only after every scope and identity check succeeds.

    Formatters may freely rewrite candidate files: publication uses the final complete
    bytes rather than brittle textual hunks.  Any validation failure leaves no bundle.
    """
    root = root.resolve()
    candidate = _outside_checkout(root, candidate_root)
    output = _outside_checkout(root, output_path)
    if not candidate.is_dir():
        raise FileNotFoundError(f"candidate root is missing: {candidate}")
    if output.exists():
        raise ValueError("publication bundle output must not already exist")
    assert_exact_clean_head(root, expected_head=expected_head, diagnostics_dir=diagnostics_dir)
    allowed = sorted({_canonical_path(path) for path in allowed_paths})
    if not allowed:
        raise ValueError("at least one allowed path is required")
    operations: list[dict[str, Any]] = []
    changed: list[str] = []
    for path in allowed:
        base_bytes = _blob_at(root, expected_head, path)
        target = candidate / Path(*PurePosixPath(path).parts)
        if base_bytes is None and not target.exists():
            continue
        if target.exists() and (not target.is_file() or target.is_symlink()):
            raise ValueError(f"candidate path must be a regular file: {path}")
        if not target.exists():
            operations.append({"path": path, "operation": "delete"})
            changed.append(path)
            continue
        candidate_bytes = target.read_bytes()
        if base_bytes == candidate_bytes:
            continue
        operations.append(
            {
                "path": path,
                "operation": "replace" if base_bytes is not None else "add",
                "byte_length": len(candidate_bytes),
                "sha256": hashlib.sha256(candidate_bytes).hexdigest(),
                "content_base64": base64.b64encode(candidate_bytes).decode("ascii"),
            }
        )
        changed.append(path)
    candidate_files = sorted(
        p.relative_to(candidate).as_posix()
        for p in candidate.rglob("*")
        if p.is_file() and not p.is_symlink()
    )
    for path in candidate_files:
        if path in allowed:
            continue
        base_bytes = _blob_at(root, expected_head, path)
        if base_bytes is None:
            raise RuntimeError(f"candidate contains out-of-scope addition: {path}")
        if base_bytes != (candidate / path).read_bytes():
            raise RuntimeError(f"candidate contains out-of-scope modification: {path}")
    if not operations:
        raise RuntimeError("candidate produced no bounded publication operations")
    bundle = {
        "version": VERSION,
        "base_head": expected_head,
        "changed_paths": changed,
        "operations": operations,
        "publication_mode": "existing_agent_bridge_atomic_compare_and_swap",
        "partial_publication_allowed": False,
        "formatting_drift_policy": "publish_verified_final_whole_file_bytes",
        "production_mutation": False,
        "automatic_publication": False,
        "merge_authority": False,
    }
    assert_exact_clean_head(root, expected_head=expected_head, diagnostics_dir=diagnostics_dir)
    _write_json_atomic(output, bundle)
    return bundle


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export")
    export.add_argument("--expected-head", required=True)
    export.add_argument("--output-dir", required=True)
    export.add_argument("--diagnostics-dir", required=True)
    materialize = sub.add_parser("materialize")
    materialize.add_argument("--expected-head", required=True)
    materialize.add_argument("--destination", required=True)
    materialize.add_argument("--diagnostics-dir", required=True)
    bundle = sub.add_parser("bundle")
    bundle.add_argument("--expected-head", required=True)
    bundle.add_argument("--candidate-root", required=True)
    bundle.add_argument("--allowed-path", action="append", required=True)
    bundle.add_argument("--output-path", required=True)
    bundle.add_argument("--diagnostics-dir", required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    root = Path(args.repo_root)
    if args.command == "export":
        result = export_exact_head(root, expected_head=args.expected_head, output_dir=args.output_dir, diagnostics_dir=args.diagnostics_dir)
    elif args.command == "materialize":
        result = materialize_exact_head(root, expected_head=args.expected_head, destination=args.destination, diagnostics_dir=args.diagnostics_dir)
    else:
        result = build_atomic_publication_bundle(root, expected_head=args.expected_head, candidate_root=args.candidate_root, allowed_paths=args.allowed_path, output_path=args.output_path, diagnostics_dir=args.diagnostics_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
