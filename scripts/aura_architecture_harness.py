#!/usr/bin/env python3
"""Reproducible full-repository harness for Aura architecture analysis.

Runs Aura's Connectome, Relational Index, Relationship Atlas, Emergent
Properties, and proposal-only Architect surfaces. It never applies patches or
grants execution authority.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, BinaryIO, Iterable, Iterator
import venv
import zipfile

VERSION = "AURA_ARCHITECTURE_HARNESS_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
MAX_REFERENCE_FILES = 8
MAX_REFERENCE_BYTES = 2_000_000
AI_HANDOFF_VERSION = "AURA_ARCHITECTURE_HARNESS_AI_HANDOFF_V1"
DEFAULT_INLINE_MAX_BYTES = 256 * 1024
HARD_INLINE_MAX_BYTES = 1024 * 1024
BINARY_PROBE_BYTES = 8192
DIGEST_CHUNK_BYTES = 1024 * 1024
COMMAND_OUTPUT_MAX_BYTES = 64 * 1024
COMMAND_OUTPUT_MAX_LINES = 400
TASK_WATCHDOG_VERSION = "AURA_ARCHITECTURE_HARNESS_TASK_WATCHDOG_V1"
DEFAULT_WATCHDOG_CHECKIN_SECONDS = 10 * 60
DEFAULT_WATCHDOG_PAUSE_SECONDS = 20 * 60
WATCHDOG_POLL_SECONDS = 0.25
WATCHDOG_TERMINATE_GRACE_SECONDS = 5
WATCHDOG_STATUS_FILE = "watchdog_status.json"
WATCHDOG_EVENTS_FILE = "watchdog_events.jsonl"
WATCHDOG_PAUSE_FILE = "watchdog_pause_receipt.json"
WATCHDOG_LATEST_CHECKIN_FILE = "watchdog_latest_checkin.json"
WATCHDOG_STATUS_MAX_BYTES = 64 * 1024
WATCHDOG_ARTIFACT_NAMES = (
    "harness_request.json",
    "connectome.json",
    "relational_index.json",
    "relational_index_summary.json",
    "relationship_atlas.json",
    "relationship_atlas_receipt.json",
    "emergent_properties.json",
    "architect_preparation.json",
    "harness_summary.json",
)
MAX_GIT_STATUS_ENTRIES = 10_000
MAX_GIT_TREE_ENTRIES = 100_000
MAX_GIT_RECORD_BYTES = 16 * 1024
SOURCE_REVIEW = "SOURCE_REVIEW"
DIGEST_ONLY = "DIGEST_ONLY"
REGENERATE_FROM_FINAL_TREE = "REGENERATE_FROM_FINAL_TREE"
GENERATED_REPRODUCIBLE_PATHS = frozenset({
    ".aura/CODEMAP.json",
    ".aura/CODEMAP.md",
    "topology_map.json",
    "Aura_Memory/live_topology_ast.json",
    "docs/aura_substrate_manifest.v1.json",
    "docs/aura_substrate_release_index.v1.json",
})
GENERATED_REPRODUCIBLE_PATTERNS = (
    "docs/aura_substrate_manifest.files.*.json",
    "docs/aura_substrate_manifest.phases.*.json",
)
SENSITIVE_OR_RUNTIME_PARTS = frozenset({
    ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "node_modules", "Aura_Sandbox",
})
SENSITIVE_BASENAME_PATTERNS = (
    ".env", ".env.*", "*.pem", "*.key", "id_rsa", "id_ed25519",
    "credentials.json", "service-account*.json",
)
AUTHORITY_CONTRACT = {
    "production_mutation": False,
    "automatic_fix": False,
    "automatic_commit": False,
    "automatic_push": False,
    "automatic_pull_request": False,
    "automatic_merge": False,
    "provider_execution_authorized": False,
    "human_review_required": True,
    "patch_authority": PATCH_AUTHORITY,
    "vsa_patch_authority": False,
}
DEFAULT_OBJECTIVE = (
    "make a new function that combines the properties of Connectome, "
    "Relational Synthesis, and Atlas to code better"
)
REQUIRED_REPOSITORY_FILES = (
    "aura_capability_connectome.py",
    "aura_capability_connectome_v2.py",
    "aura_relational_index.py",
    "aura_relationship_atlas.py",
    "aura_relational_synthesis.py",
    "aura_emergent_potential_repl.py",
    "aura_architect_loop.py",
    "aura_live_architect.py",
    ".aura/CODEMAP.json",
)
TARGET_IMPORTS = tuple(path.removesuffix(".py") for path in REQUIRED_REPOSITORY_FILES[:-1])


def _digest(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode(), digest_size=16).hexdigest()


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")
    tmp.replace(path)


def _stream_sha256(path: Path, *, chunk_bytes: int = DIGEST_CHUNK_BYTES) -> str:
    """Hash a regular file without loading it into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_bytes)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _symlink_sha256(path: Path) -> str:
    return hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest()


def _reference_manifest(values: Iterable[str | Path]) -> list[dict[str, Any]]:
    paths = [Path(value).expanduser().resolve() for value in values]
    if len(paths) > MAX_REFERENCE_FILES:
        raise ValueError(f"at most {MAX_REFERENCE_FILES} reference files are allowed")
    manifest: list[dict[str, Any]] = []
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(f"reference file is missing: {path}")
        size = path.stat().st_size
        if size > MAX_REFERENCE_BYTES:
            raise ValueError(
                f"reference file exceeds {MAX_REFERENCE_BYTES} bytes: {path}"
            )
        manifest.append(
            {
                "name": path.name,
                "path": str(path),
                "size_bytes": size,
                "sha256": _stream_sha256(path),
            }
        )
    return manifest


@dataclass(frozen=True)
class _BoundedExcerpt:
    text: str
    truncated: bool
    total_bytes: int
    total_lines: int
    omitted_bytes: int
    omitted_lines: int


@dataclass(frozen=True)
class _CommandResult:
    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    stdout_truncation: dict[str, Any]
    stderr_truncation: dict[str, Any]


@dataclass(frozen=True)
class _WatchdogCommandResult:
    command: _CommandResult
    paused: bool
    pause_receipt: dict[str, Any] | None
    checkins: tuple[dict[str, Any], ...]


def _utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _append_json_line(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise RuntimeError(f"refusing watchdog event symlink: {path}")
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")


def _task_watchdog_policy(
    *,
    checkin_seconds: float = DEFAULT_WATCHDOG_CHECKIN_SECONDS,
    pause_seconds: float = DEFAULT_WATCHDOG_PAUSE_SECONDS,
) -> dict[str, Any]:
    if checkin_seconds <= 0:
        raise ValueError("watchdog check-in interval must be positive")
    if pause_seconds < checkin_seconds:
        raise ValueError("watchdog pause threshold must be at least the check-in interval")
    return {
        "version": TASK_WATCHDOG_VERSION,
        "harness_version": VERSION,
        "enabled": True,
        "checkin_seconds": checkin_seconds,
        "pause_seconds": pause_seconds,
        "checkin_assessments": [
            "HEALTHY_CONTINUE",
            "SLOW_BUT_PROGRESSING",
            "STALLED_REASSESS",
            "UNKNOWN_REASSESS",
        ],
        "pause_assessment": "PAUSED_FOR_REASSESSMENT",
        "resume_supported": True,
        "resume_required": True,
        "production_mutation": False,
        "human_review_required": True,
        "status_file": WATCHDOG_STATUS_FILE,
        "events_file": WATCHDOG_EVENTS_FILE,
        "pause_receipt_file": WATCHDOG_PAUSE_FILE,
    }


def _watchdog_resume_command(output_dir: Path) -> str:
    explicit = os.environ.get("AURA_WATCHDOG_RESUME_COMMAND", "").strip()
    if explicit:
        return explicit
    return (
        "rerun the original harness command with "
        f"--output-dir {json.dumps(str(output_dir))} --resume"
    )


def _watchdog_artifact_inventory(output_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name in WATCHDOG_ARTIFACT_NAMES:
        path = output_dir / name
        try:
            if path.is_file() and not path.is_symlink():
                rows.append({"path": name, "size_bytes": path.stat().st_size})
        except OSError:
            continue
    return rows


def _read_watchdog_progress(output_dir: Path) -> dict[str, Any]:
    path = output_dir / WATCHDOG_STATUS_FILE
    try:
        if not path.is_file() or path.is_symlink():
            return {}
        if path.stat().st_size > WATCHDOG_STATUS_MAX_BYTES:
            return {}
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _write_watchdog_progress(
    output_dir: Path,
    *,
    phase: str,
    state: str,
    started_monotonic: float,
    detail: str = "",
) -> dict[str, Any]:
    previous = _read_watchdog_progress(output_dir)
    try:
        sequence = int(previous.get("progress_sequence") or 0) + 1
    except (TypeError, ValueError):
        sequence = 1
    payload = {
        "version": TASK_WATCHDOG_VERSION,
        "harness_version": VERSION,
        "event": "phase_progress",
        "progress_sequence": sequence,
        "phase": phase,
        "state": state,
        "detail": detail,
        "updated_at_utc": _utc_timestamp(),
        "elapsed_seconds": round(max(0.0, time.monotonic() - started_monotonic), 3),
        "completed_artifacts": _watchdog_artifact_inventory(output_dir),
        "resume_supported": True,
        "resume_command": _watchdog_resume_command(output_dir),
        "production_mutation": False,
        "patch_authority": PATCH_AUTHORITY,
    }
    _write(output_dir / WATCHDOG_STATUS_FILE, payload)
    _append_json_line(output_dir / WATCHDOG_EVENTS_FILE, payload)
    return payload


def _assess_watchdog_progress(
    *,
    elapsed_seconds: float,
    progress_age_seconds: float,
    checkin_seconds: float,
    last_phase: str = "",
    last_state: str = "",
    progress_changed: bool | None = None,
    status_present: bool = True,
    completed_artifacts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not status_present:
        assessment = "UNKNOWN_REASSESS"
        action = "inspect_child_and_output_state"
    elif progress_changed is True:
        assessment = "HEALTHY_CONTINUE"
        action = "continue"
    elif progress_age_seconds <= checkin_seconds * 1.5:
        assessment = "SLOW_BUT_PROGRESSING"
        action = "continue_until_next_checkin"
    else:
        assessment = "STALLED_REASSESS"
        action = "prepare_for_hard_pause"
    progress_healthy = assessment in {"HEALTHY_CONTINUE", "SLOW_BUT_PROGRESSING"}
    return {
        "version": TASK_WATCHDOG_VERSION,
        "harness_version": VERSION,
        "event": "watchdog_checkin",
        "checked_at_utc": _utc_timestamp(),
        "elapsed_seconds": round(elapsed_seconds, 3),
        "last_progress_age_seconds": round(progress_age_seconds, 3),
        "last_phase": last_phase or "unknown",
        "last_state": last_state or "unknown",
        "assessment": assessment,
        "action": action,
        "progress_healthy": progress_healthy,
        "needs_reassessment_now": not progress_healthy,
        "completed_artifacts": completed_artifacts or [],
        "production_mutation": False,
    }


def _watchdog_progress_token(
    output_dir: Path, progress: dict[str, Any]
) -> tuple[int | None, int | None] | None:
    try:
        sequence = int(progress.get("progress_sequence"))
    except (TypeError, ValueError):
        sequence = None
    try:
        mtime_ns = (output_dir / WATCHDOG_STATUS_FILE).stat().st_mtime_ns
    except OSError:
        mtime_ns = None
    if sequence is None and mtime_ns is None:
        return None
    return (sequence, mtime_ns)


def _run_with_watchdog(
    cmd: list[str],
    root: Path,
    *,
    output_dir: Path,
    checkin_seconds: float = DEFAULT_WATCHDOG_CHECKIN_SECONDS,
    pause_seconds: float = DEFAULT_WATCHDOG_PAUSE_SECONDS,
    env: dict[str, str] | None = None,
    resume_command: str | None = None,
    max_output_bytes: int = COMMAND_OUTPUT_MAX_BYTES,
    max_output_lines: int = COMMAND_OUTPUT_MAX_LINES,
) -> _WatchdogCommandResult:
    """Supervise a command with periodic health checks and a resumable hard pause."""
    _task_watchdog_policy(
        checkin_seconds=checkin_seconds,
        pause_seconds=pause_seconds,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    merged = os.environ.copy()
    merged.update(env or {})
    if resume_command:
        merged["AURA_WATCHDOG_RESUME_COMMAND"] = resume_command
    started = time.monotonic()
    next_checkin = checkin_seconds
    last_progress_seen = started
    progress = _read_watchdog_progress(output_dir)
    observed_progress_token = _watchdog_progress_token(output_dir, progress)
    last_checkin_progress_token = observed_progress_token
    checkins: list[dict[str, Any]] = []
    paused = False
    pause_receipt: dict[str, Any] | None = None
    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        process = subprocess.Popen(
            cmd,
            cwd=root,
            stdout=stdout_file,
            stderr=stderr_file,
            env=merged,
        )
        while process.poll() is None:
            now = time.monotonic()
            elapsed = now - started
            progress = _read_watchdog_progress(output_dir)
            progress_token = _watchdog_progress_token(output_dir, progress)
            if progress_token is not None and progress_token != observed_progress_token:
                observed_progress_token = progress_token
                last_progress_seen = now
            if elapsed >= next_checkin:
                progress_changed = (
                    observed_progress_token is not None
                    and observed_progress_token != last_checkin_progress_token
                )
                event = _assess_watchdog_progress(
                    elapsed_seconds=elapsed,
                    progress_age_seconds=max(0.0, now - last_progress_seen),
                    checkin_seconds=checkin_seconds,
                    progress_changed=progress_changed,
                    status_present=bool(progress),
                    last_phase=str(progress.get("phase") or ""),
                    last_state=str(progress.get("state") or ""),
                    completed_artifacts=_watchdog_artifact_inventory(output_dir),
                )
                event["hard_pause_after_seconds"] = round(pause_seconds, 3)
                checkins.append(event)
                _append_json_line(output_dir / WATCHDOG_EVENTS_FILE, event)
                _write(output_dir / WATCHDOG_LATEST_CHECKIN_FILE, event)
                print(json.dumps(event, sort_keys=True), file=sys.stderr, flush=True)
                last_checkin_progress_token = observed_progress_token
                next_checkin += checkin_seconds
            if elapsed >= pause_seconds:
                paused = True
                progress = _read_watchdog_progress(output_dir)
                latest = checkins[-1] if checkins else {}
                pause_receipt = {
                    "version": TASK_WATCHDOG_VERSION,
                    "harness_version": VERSION,
                    "event": "watchdog_hard_pause",
                    "assessment": "PAUSED_FOR_REASSESSMENT",
                    "paused_at_utc": _utc_timestamp(),
                    "elapsed_seconds": round(elapsed, 3),
                    "reason": "maximum_continuous_runtime_reached",
                    "latest_checkin_assessment": latest.get(
                        "assessment", "NO_SCHEDULED_CHECKIN_COMPLETED"
                    ),
                    "recommended_next_action": (
                        "review_then_resume_same_plan"
                        if latest.get("progress_healthy")
                        else "reassess_scope_or_strategy_before_resume"
                    ),
                    "last_phase": str(progress.get("phase") or "unknown"),
                    "last_state": str(progress.get("state") or "unknown"),
                    "checkin_count": len(checkins),
                    "completed_artifacts": _watchdog_artifact_inventory(output_dir),
                    "resume_required": True,
                    "resume_command": resume_command or _watchdog_resume_command(output_dir),
                    "safe_checkpoint_directory": str(output_dir),
                    "production_mutation": False,
                    "patch_authority": PATCH_AUTHORITY,
                }
                process.terminate()
                try:
                    process.wait(timeout=WATCHDOG_TERMINATE_GRACE_SECONDS)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=WATCHDOG_TERMINATE_GRACE_SECONDS)
                break
            time.sleep(WATCHDOG_POLL_SECONDS)
        if process.poll() is None:
            process.wait()
        stdout = _bounded_excerpt(
            stdout_file, max_bytes=max_output_bytes, max_lines=max_output_lines
        )
        stderr = _bounded_excerpt(
            stderr_file, max_bytes=max_output_bytes, max_lines=max_output_lines
        )
    command = _CommandResult(
        args=tuple(cmd),
        returncode=int(process.returncode or 0),
        stdout=stdout.text,
        stderr=stderr.text,
        stdout_truncation=_truncation_dict(stdout),
        stderr_truncation=_truncation_dict(stderr),
    )
    if pause_receipt is not None:
        pause_receipt = {
            **pause_receipt,
            "terminated_returncode": command.returncode,
            "stdout_truncation": command.stdout_truncation,
            "stderr_truncation": command.stderr_truncation,
        }
        _write(output_dir / WATCHDOG_PAUSE_FILE, pause_receipt)
        _append_json_line(output_dir / WATCHDOG_EVENTS_FILE, pause_receipt)
        print(json.dumps(pause_receipt, sort_keys=True), file=sys.stderr, flush=True)
    return _WatchdogCommandResult(
        command=command,
        paused=paused,
        pause_receipt=pause_receipt,
        checkins=tuple(checkins),
    )


def _bounded_excerpt(
    handle: BinaryIO,
    *,
    max_bytes: int = COMMAND_OUTPUT_MAX_BYTES,
    max_lines: int = COMMAND_OUTPUT_MAX_LINES,
) -> _BoundedExcerpt:
    """Return a deterministic tail excerpt and explicit truncation receipt."""
    handle.seek(0)
    retained = bytearray()
    total_bytes = 0
    newline_count = 0
    last_byte = b""
    while True:
        chunk = handle.read(64 * 1024)
        if not chunk:
            break
        total_bytes += len(chunk)
        newline_count += chunk.count(b"\n")
        last_byte = chunk[-1:]
        retained.extend(chunk)
        if len(retained) > max_bytes:
            del retained[: len(retained) - max_bytes]
    total_lines = newline_count + (1 if total_bytes and last_byte != b"\n" else 0)
    byte_omitted = max(0, total_bytes - len(retained))
    retained_lines = retained.splitlines(keepends=True)
    if max_lines >= 0 and len(retained_lines) > max_lines:
        removed = retained_lines[:-max_lines] if max_lines else retained_lines
        byte_omitted += sum(len(row) for row in removed)
        retained_lines = retained_lines[-max_lines:] if max_lines else []
    payload = b"".join(retained_lines)
    kept_line_count = payload.count(b"\n") + (
        1 if payload and not payload.endswith(b"\n") else 0
    )
    omitted_lines = max(0, total_lines - kept_line_count)
    return _BoundedExcerpt(
        text=payload.decode("utf-8", errors="replace"),
        truncated=bool(byte_omitted or omitted_lines),
        total_bytes=total_bytes,
        total_lines=total_lines,
        omitted_bytes=byte_omitted,
        omitted_lines=omitted_lines,
    )


def _truncation_dict(value: _BoundedExcerpt) -> dict[str, Any]:
    return {
        "truncated": value.truncated,
        "total_bytes": value.total_bytes,
        "total_lines": value.total_lines,
        "omitted_bytes": value.omitted_bytes,
        "omitted_lines": value.omitted_lines,
    }


def _run(
    cmd: list[str],
    root: Path,
    *,
    check: bool = True,
    timeout: int = 300,
    env: dict[str, str] | None = None,
    max_output_bytes: int = COMMAND_OUTPUT_MAX_BYTES,
    max_output_lines: int = COMMAND_OUTPUT_MAX_LINES,
) -> _CommandResult:
    """Run a command without retaining unbounded stdout or stderr in memory."""
    merged = os.environ.copy()
    merged.update(env or {})
    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        try:
            completed = subprocess.run(
                cmd,
                cwd=root,
                check=False,
                stdout=stdout_file,
                stderr=stderr_file,
                timeout=timeout,
                env=merged,
            )
        except subprocess.TimeoutExpired:
            raise
        stdout = _bounded_excerpt(
            stdout_file, max_bytes=max_output_bytes, max_lines=max_output_lines
        )
        stderr = _bounded_excerpt(
            stderr_file, max_bytes=max_output_bytes, max_lines=max_output_lines
        )
    result = _CommandResult(
        args=tuple(cmd),
        returncode=completed.returncode,
        stdout=stdout.text,
        stderr=stderr.text,
        stdout_truncation=_truncation_dict(stdout),
        stderr_truncation=_truncation_dict(stderr),
    )
    if check and result.returncode:
        raise subprocess.CalledProcessError(
            result.returncode,
            cmd,
            output=result.stdout,
            stderr=result.stderr,
        )
    return result


def _root(value: str | Path) -> Path:
    root = Path(value).expanduser().resolve()
    missing = [name for name in REQUIRED_REPOSITORY_FILES if not (root / name).is_file()]
    if missing:
        raise FileNotFoundError("incomplete AuraOS repository; missing: " + ", ".join(missing))
    return root


def _iter_nul_records(stream: BinaryIO) -> Iterator[bytes]:
    pending = bytearray()
    while True:
        chunk = stream.read(64 * 1024)
        if not chunk:
            break
        pending.extend(chunk)
        while True:
            marker = pending.find(0)
            if marker < 0:
                if len(pending) > MAX_GIT_RECORD_BYTES:
                    raise RuntimeError("oversized unterminated Git record")
                break
            if marker > MAX_GIT_RECORD_BYTES:
                raise RuntimeError("oversized Git record")
            yield bytes(pending[:marker])
            del pending[: marker + 1]
    if pending:
        raise RuntimeError("unterminated NUL-delimited Git output")


def _git_nul_records(
    root: Path,
    args: list[str],
    *,
    max_records: int,
) -> list[bytes]:
    process = subprocess.Popen(
        ["git", *args],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdout is not None
    rows: list[bytes] = []
    try:
        for row in _iter_nul_records(process.stdout):
            if len(row) > MAX_GIT_RECORD_BYTES:
                process.kill()
                raise RuntimeError(f"git {' '.join(args)} emitted an oversized record")
            rows.append(row)
            if len(rows) > max_records:
                process.kill()
                raise RuntimeError(f"git {' '.join(args)} exceeded {max_records} records")
    finally:
        process.stdout.close()
    stderr = process.stderr.read(COMMAND_OUTPUT_MAX_BYTES + 1) if process.stderr else b""
    returncode = process.wait()
    if returncode:
        raise RuntimeError(
            f"git {' '.join(args)} failed: "
            + stderr[:COMMAND_OUTPUT_MAX_BYTES].decode("utf-8", errors="replace")
        )
    if len(stderr) > COMMAND_OUTPUT_MAX_BYTES:
        raise RuntimeError(f"git {' '.join(args)} emitted excessive stderr")
    return rows


def _git_status(root: Path) -> list[str]:
    return [
        row.decode("utf-8", errors="replace")
        for row in _git_nul_records(
            root,
            ["status", "--porcelain=v1", "-z"],
            max_records=MAX_GIT_STATUS_ENTRIES,
        )
        if row
    ]


def _git_value(root: Path, *args: str) -> str:
    return _run(["git", *args], root, check=False).stdout.strip()


def _validate_repo_path(value: str) -> str:
    if not value or "\\" in value or "\x00" in value:
        raise ValueError(f"unsafe repository path: {value!r}")
    if re.match(r"^[A-Za-z]:", value):
        raise ValueError(f"Windows drive path is not allowed: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe repository path: {value!r}")
    normalized = path.as_posix()
    if normalized != value:
        raise ValueError(f"non-canonical repository path: {value!r}")
    return normalized


def _git_tree_entries(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in _git_nul_records(
        root,
        ["ls-tree", "-rz", "-l", "HEAD"],
        max_records=MAX_GIT_TREE_ENTRIES,
    ):
        header, separator, raw_path = record.partition(b"\t")
        if not separator:
            raise RuntimeError("unexpected git ls-tree record")
        fields = header.decode("ascii").split()
        if len(fields) != 4:
            raise RuntimeError("unexpected git ls-tree metadata")
        mode, object_type, oid, size_text = fields
        if object_type != "blob":
            continue
        path = _validate_repo_path(raw_path.decode("utf-8", errors="strict"))
        rows.append(
            {
                "path": path,
                "mode": mode,
                "git_blob_oid": oid,
                "git_blob_size_bytes": int(size_text),
            }
        )
    return sorted(rows, key=lambda row: row["path"])


def _read_git_blob(root: Path, oid: str, *, max_bytes: int) -> bytes:
    process = subprocess.Popen(
        ["git", "cat-file", "blob", oid],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdout is not None
    payload = process.stdout.read(max_bytes + 1)
    stderr = process.stderr.read(COMMAND_OUTPUT_MAX_BYTES + 1) if process.stderr else b""
    returncode = process.wait()
    if returncode:
        raise RuntimeError(
            "git cat-file failed: "
            + stderr[:COMMAND_OUTPUT_MAX_BYTES].decode("utf-8", errors="replace")
        )
    if len(payload) > max_bytes:
        raise RuntimeError("Git blob exceeded its admitted source-review ceiling")
    return payload


def _binary_bytes(prefix: bytes) -> bool:
    if b"\x00" in prefix:
        return True
    try:
        prefix.decode("utf-8")
    except UnicodeDecodeError:
        return True
    return False


def _binary_probe(path: Path, *, max_bytes: int = BINARY_PROBE_BYTES) -> tuple[bool, int]:
    with path.open("rb") as handle:
        prefix = handle.read(max_bytes)
    return _binary_bytes(prefix), len(prefix)


def _git_blob_sha256(root: Path, oid: str) -> str:
    process = subprocess.Popen(
        ["git", "cat-file", "blob", oid],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdout is not None
    digest = hashlib.sha256()
    while True:
        chunk = process.stdout.read(DIGEST_CHUNK_BYTES)
        if not chunk:
            break
        digest.update(chunk)
    stderr = process.stderr.read(COMMAND_OUTPUT_MAX_BYTES + 1) if process.stderr else b""
    returncode = process.wait()
    if returncode:
        raise RuntimeError(
            "git cat-file digest failed: "
            + stderr[:COMMAND_OUTPUT_MAX_BYTES].decode("utf-8", errors="replace")
        )
    if len(stderr) > COMMAND_OUTPUT_MAX_BYTES:
        raise RuntimeError("git cat-file digest emitted excessive stderr")
    return digest.hexdigest()


def _is_generated_reproducible(path: str) -> bool:
    return path in GENERATED_REPRODUCIBLE_PATHS or any(
        fnmatch.fnmatchcase(path, pattern)
        for pattern in GENERATED_REPRODUCIBLE_PATTERNS
    )


def _is_sensitive_or_runtime(path: str) -> bool:
    parts = PurePosixPath(path).parts
    if any(part in SENSITIVE_OR_RUNTIME_PARTS for part in parts):
        return True
    basename = parts[-1]
    return any(
        fnmatch.fnmatchcase(basename, pattern)
        for pattern in SENSITIVE_BASENAME_PATTERNS
    )


def _classify_tracked_file(
    path: str,
    *,
    size_bytes: int,
    binary: bool,
    symlink: bool,
    inline_max_bytes: int,
) -> tuple[str, str]:
    path = _validate_repo_path(path)
    if _is_generated_reproducible(path):
        return REGENERATE_FROM_FINAL_TREE, "generated_reproducible_artifact"
    if symlink:
        return DIGEST_ONLY, "symlink_not_archived"
    if _is_sensitive_or_runtime(path):
        return DIGEST_ONLY, "sensitive_or_runtime_path"
    if size_bytes > inline_max_bytes:
        return DIGEST_ONLY, "exceeds_inline_max_bytes"
    if binary:
        return DIGEST_ONLY, "binary_content"
    return SOURCE_REVIEW, "bounded_tracked_text_source"


def _working_tree_metadata(root: Path, path: str, *, symlink: bool) -> dict[str, Any]:
    target = root / Path(*PurePosixPath(path).parts)
    try:
        if symlink:
            if not target.is_symlink():
                return {"working_tree_present": False}
            return {
                "working_tree_present": True,
                "working_tree_size_bytes": target.lstat().st_size,
                "working_tree_sha256": _symlink_sha256(target),
            }
        if not target.is_file() or target.is_symlink():
            return {"working_tree_present": False}
        return {
            "working_tree_present": True,
            "working_tree_size_bytes": target.stat().st_size,
            "working_tree_sha256": _stream_sha256(target),
        }
    except OSError as exc:
        return {
            "working_tree_present": False,
            "working_tree_error": type(exc).__name__,
        }


def _safe_output_dir(root: Path, value: str | Path | None) -> Path:
    output = (
        Path(value).expanduser()
        if value is not None
        else root.parent / f"{root.name}-ai-handoff"
    ).resolve()
    if output == root or root in output.parents:
        raise ValueError("AI handoff output must be outside the repository")
    if output.exists() and output.is_symlink():
        raise ValueError("AI handoff output cannot be a symlink")
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError("AI handoff output directory must be empty")
    return output


def _zip_info(path: str, mode: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    permission = 0o755 if mode == "100755" else 0o644
    info.external_attr = permission << 16
    return info


def _regeneration_policy() -> list[dict[str, Any]]:
    return [
        {
            "timing": "after_source_and_tests_stabilize_in_canonical_linux_lf_checkout",
            "commands": [
                "python aura_codebase_navigator.py",
                "python -m aura_codemap_verify --compare-json .aura/CODEMAP.json",
            ],
            "paths": sorted(
                path for path in GENERATED_REPRODUCIBLE_PATHS
                if path.startswith(".aura/") or path.startswith("Aura_Memory/")
                or path == "topology_map.json"
            ),
        },
        {
            "timing": "after_source_and_tests_stabilize_from_canonical_linux_lf_content",
            "commands": [
                "python aura_substrate_release.py --root . "
                "--manifest-output-root <temporary-output-root> "
                "--output <temporary-output-root>/docs/"
                "aura_substrate_release_index.v1.json"
            ],
            "patterns": [
                "docs/aura_substrate_manifest.v1.json",
                *GENERATED_REPRODUCIBLE_PATTERNS,
                "docs/aura_substrate_release_index.v1.json",
            ],
        },
    ]


def _ai_handoff_summary(root: Path) -> dict[str, Any]:
    default_manifest = root.parent / f"{root.name}-ai-handoff" / "ai_handoff_manifest.json"
    result = {
        "version": AI_HANDOFF_VERSION,
        "default_inline_max_bytes": DEFAULT_INLINE_MAX_BYTES,
        "hard_inline_max_bytes": HARD_INLINE_MAX_BYTES,
        "generated_artifact_disposition": REGENERATE_FROM_FINAL_TREE,
        "recommended_command": (
            "python scripts/aura_architecture_harness.py --repo-root . "
            "handoff --output-dir ../AuraOS-ai-handoff"
        ),
        "review_authority": "exact_source_files_and_tests_only",
    }
    if default_manifest.is_file():
        result["manifest_path"] = str(default_manifest)
    return result


def _canonical_source_commit(identity: dict[str, Any]) -> str:
    source_commit = (
        identity.get("source_sha")
        if identity.get("synthetic_local_identity")
        else identity.get("head")
    )
    if not isinstance(source_commit, str) or not re.fullmatch(
        r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", source_commit
    ):
        raise RuntimeError("ambiguous or missing canonical source commit identity")
    return source_commit.lower()


def create_ai_handoff(
    root: Path,
    *,
    output_dir: str | Path | None,
    inline_max_bytes: int = DEFAULT_INLINE_MAX_BYTES,
    allow_dirty: bool = False,
    create_archive: bool = True,
) -> dict[str, Any]:
    if inline_max_bytes <= 0 or inline_max_bytes > HARD_INLINE_MAX_BYTES:
        raise ValueError(
            f"inline_max_bytes must be between 1 and {HARD_INLINE_MAX_BYTES}"
        )
    initial_identity = _git_info(root)
    if not initial_identity.get("available"):
        raise RuntimeError("Git metadata is required for an AI handoff")
    if not initial_identity.get("clean") and not allow_dirty:
        raise RuntimeError("repository is dirty; use a clean checkout or --allow-dirty")
    source_commit = _canonical_source_commit(initial_identity)
    output = _safe_output_dir(root, output_dir)
    entries = _git_tree_entries(root)
    object_format = _git_value(root, "rev-parse", "--show-object-format") or "unknown"
    review_rows: list[dict[str, Any]] = []
    digest_only_rows: list[dict[str, Any]] = []
    omission_counts: dict[str, int] = {}
    warnings: list[str] = []
    if not initial_identity.get("clean"):
        warnings.append(
            "dirty_repository_allowed; archive bytes remain pinned to HEAD Git blobs"
        )

    for entry in entries:
        repo_path = entry["path"]
        symlink = entry["mode"] == "120000"
        disposition, reason = _classify_tracked_file(
            repo_path,
            size_bytes=entry["git_blob_size_bytes"],
            binary=False,
            symlink=symlink,
            inline_max_bytes=inline_max_bytes,
        )
        inspected_bytes = 0
        if disposition == SOURCE_REVIEW:
            blob = _read_git_blob(
                root, entry["git_blob_oid"], max_bytes=inline_max_bytes
            )
            prefix = blob[:BINARY_PROBE_BYTES]
            inspected_bytes = len(prefix)
            if _binary_bytes(prefix):
                disposition, reason = DIGEST_ONLY, "binary_content"
        working = _working_tree_metadata(root, repo_path, symlink=symlink)
        row = {
            "path": repo_path,
            "size_bytes": entry["git_blob_size_bytes"],
            "git_blob_oid": entry["git_blob_oid"],
            "git_object_format": object_format,
            "disposition": disposition,
            "reason": reason,
            **working,
        }
        if not symlink:
            row["binary_probe_bytes"] = inspected_bytes
        if disposition == SOURCE_REVIEW:
            review_rows.append({**entry, **working})
        else:
            row["git_blob_sha256"] = _git_blob_sha256(
                root, entry["git_blob_oid"]
            )
            digest_only_rows.append(row)
            omission_counts[reason] = omission_counts.get(reason, 0) + 1

    review_rows.sort(key=lambda row: row["path"])
    digest_only_rows.sort(key=lambda row: row["path"])
    review_list = output / "ai_review_files.txt"
    review_list.write_text(
        "".join(f"{row['path']}\n" for row in review_rows), encoding="utf-8", newline="\n"
    )

    archive_meta: dict[str, Any] | None = None
    working_tree_variances: list[dict[str, Any]] = []
    archive = output / "ai_source_review.zip"
    archive_context = (
        zipfile.ZipFile(
            archive, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        )
        if create_archive
        else None
    )
    try:
        for row in review_rows:
            blob = _read_git_blob(
                root,
                row["git_blob_oid"],
                max_bytes=inline_max_bytes,
            )
            if len(blob) != row["git_blob_size_bytes"]:
                raise RuntimeError(f"Git blob size changed for {row['path']}")
            canonical_sha256 = hashlib.sha256(blob).hexdigest()
            working_sha256 = row.get("working_tree_sha256")
            if working_sha256 and working_sha256 != canonical_sha256:
                working_tree_variances.append(
                    {
                        "path": row["path"],
                        "git_blob_oid": row["git_blob_oid"],
                        "git_blob_sha256": canonical_sha256,
                        "working_tree_sha256": working_sha256,
                        "working_tree_size_bytes": row.get("working_tree_size_bytes"),
                        "git_blob_size_bytes": row["git_blob_size_bytes"],
                    }
                )
            if archive_context is not None:
                archive_context.writestr(_zip_info(row["path"], row["mode"]), blob)
    finally:
        if archive_context is not None:
            archive_context.close()
    if create_archive:
        archive_meta = {
            "path": archive.name,
            "size_bytes": archive.stat().st_size,
            "sha256": _stream_sha256(archive),
            "uncompressed_size_bytes": sum(
                row["git_blob_size_bytes"] for row in review_rows
            ),
            "content_source": "immutable_HEAD_git_blobs",
            "classification_basis": "uncompressed_git_blob_size_and_bounded_prefix",
        }

    final_identity = _git_info(root)
    if final_identity.get("head") != initial_identity.get("head"):
        raise RuntimeError("repository HEAD changed during AI handoff generation")
    if final_identity.get("status") != initial_identity.get("status"):
        raise RuntimeError("repository status changed during AI handoff generation")
    if not allow_dirty and not final_identity.get("clean"):
        raise RuntimeError("repository became dirty during AI handoff generation")

    manifest: dict[str, Any] = {
        "version": AI_HANDOFF_VERSION,
        "source": {
            "source_commit": source_commit,
            "local_head": initial_identity.get("head"),
            "branch": initial_identity.get("branch"),
            "clean": initial_identity.get("clean"),
            "synthetic_local_identity": initial_identity.get("synthetic_local_identity"),
            "dirty_entry_count": len(initial_identity.get("status", [])),
            "status_digest": _digest(initial_identity.get("status", [])),
            "git_object_format": object_format,
        },
        "inline_max_bytes": inline_max_bytes,
        "review_file_count": len(review_rows),
        "digest_only_file_count": len(digest_only_rows),
        "digest_only_files": digest_only_rows,
        "omission_counts": dict(sorted(omission_counts.items())),
        "review_file_list": review_list.name,
        "review_archive": archive_meta,
        "working_tree_variances": sorted(
            working_tree_variances, key=lambda row: row["path"]
        ),
        "regeneration": _regeneration_policy(),
        "safe_review_diff": [
            "git diff -- . "
            "':(exclude).aura/CODEMAP.json' "
            "':(exclude).aura/CODEMAP.md' "
            "':(exclude)topology_map.json' "
            "':(exclude)Aura_Memory/live_topology_ast.json'"
        ],
        "warnings": warnings,
        "authority": dict(AUTHORITY_CONTRACT),
    }
    manifest_path = output / "ai_handoff_manifest.json"
    _write(manifest_path, manifest)
    return {
        "ok": True,
        "version": VERSION,
        "ai_handoff": AI_HANDOFF_VERSION,
        "output_dir": str(output),
        "manifest_path": str(manifest_path),
        "review_file_list_path": str(review_list),
        "review_archive_path": str(output / archive_meta["path"]) if archive_meta else None,
        "review_file_count": len(review_rows),
        "digest_only_file_count": len(digest_only_rows),
        "source_commit": source_commit,
        "checkout_clean_after_run": final_identity.get("clean"),
        **AUTHORITY_CONTRACT,
    }

def _venv_python(path: Path) -> Path:
    return path / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _git_info(root: Path) -> dict[str, Any]:
    if shutil.which("git") is None or not (root / ".git").exists():
        return {"available": False, "clean": False, "head": "", "status": []}
    status = _git_status(root)
    return {
        "available": True,
        "head": _git_value(root, "rev-parse", "HEAD"),
        "branch": _git_value(root, "branch", "--show-current"),
        "clean": not status,
        "status": status,
        "synthetic_local_identity": (
            _git_value(root, "config", "--get", "aura.harnessSyntheticIdentity")
            == "true"
        ),
        "source_sha": _git_value(root, "config", "--get", "aura.harnessSourceSha"),
    }


def _init_git(root: Path, source_sha: str) -> dict[str, Any]:
    if (root / ".git").exists():
        return _git_info(root)
    if shutil.which("git") is None:
        raise RuntimeError("git is required for Aura's repository identity")
    for cmd in (
        ["git", "init"],
        ["git", "config", "user.name", "Aura Architecture Harness"],
        ["git", "config", "user.email", "aura-harness@local.invalid"],
        ["git", "config", "aura.harnessSyntheticIdentity", "true"],
        ["git", "config", "aura.harnessSourceSha", source_sha or "UNSPECIFIED"],
        ["git", "add", "-f", "-A"],
    ):
        _run(cmd, root, timeout=600)
    message = "chore: establish local Aura harness snapshot"
    if source_sha:
        message += f"\n\nSource-GitHub-SHA: {source_sha}"
    _run(["git", "commit", "-m", message], root, timeout=600)
    return _git_info(root)

def _probe(python: Path, root: Path) -> dict[str, Any]:
    code = (
        "import importlib,json\n"
        f"mods={list(TARGET_IMPORTS)!r}\n"
        "out={}\n"
        "for name in mods:\n"
        " try:\n"
        "  m=importlib.import_module(name);out[name]={'ok':True,'file':getattr(m,'__file__','')}\n"
        " except Exception as e: out[name]={'ok':False,'error':f'{type(e).__name__}: {e}'}\n"
        "print(json.dumps(out,sort_keys=True))\n"
    )
    process = _run([str(python), "-c", code], root, check=False,
                   env={"PYTHONPATH": str(root)})
    if process.returncode:
        return {"ok": False, "error": process.stderr or process.stdout, "modules": {}}
    modules = json.loads(process.stdout)
    return {"ok": all(row["ok"] for row in modules.values()), "modules": modules}


def prepare(root: Path, venv_path: Path, *, system_packages: bool,
            install_requirements: bool, initialize_git: bool,
            source_sha: str) -> dict[str, Any]:
    identity = _init_git(root, source_sha) if initialize_git else _git_info(root)
    if not venv_path.exists():
        venv.EnvBuilder(with_pip=True, system_site_packages=system_packages).create(venv_path)
    python = _venv_python(venv_path)
    install: dict[str, Any] = {"requested": install_requirements, "ran": False}
    if install_requirements:
        result = _run([str(python), "-m", "pip", "install", "-r", "requirements.txt"],
                      root, check=False, timeout=1800)
        install = {
            "requested": True,
            "ran": True,
            "returncode": result.returncode,
            "stdout_tail": result.stdout[-2000:],
            "stderr_tail": result.stderr[-2000:],
            "stdout_truncation": result.stdout_truncation,
            "stderr_truncation": result.stderr_truncation,
        }
    imports = _probe(python, root)
    output = {
        "ok": imports["ok"], "version": VERSION, "repo_root": str(root),
        "venv_path": str(venv_path), "python": str(python),
        "python_version": _run([str(python), "--version"], root).stdout.strip(),
        "system_site_packages": system_packages, "git_identity": identity,
        "requirements_install": install, "target_imports": imports,
        "safe_to_patch": False, "production_mutation": False,
        "patch_authority": PATCH_AUTHORITY,
    }
    manifest = venv_path / "aura_harness_environment.json"
    _write(manifest, output)
    output["manifest_path"] = str(manifest)
    return output


def _stream_json_integer_metadata(
    path: Path,
    fields: Iterable[str],
) -> dict[str, Any]:
    patterns = {
        field: re.compile(rb'"' + re.escape(field.encode("ascii")) + rb'"\s*:\s*(\d+)')
        for field in fields
    }
    found: dict[str, int] = {}
    digest = hashlib.sha256()
    overlap = b""
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(DIGEST_CHUNK_BYTES)
            if not chunk:
                break
            digest.update(chunk)
            window = overlap + chunk
            for field, pattern in patterns.items():
                if field in found:
                    continue
                match = pattern.search(window)
                if match:
                    found[field] = int(match.group(1))
            overlap = window[-512:]
    return {
        **found,
        "size_bytes": path.stat().st_size,
        "sha256": digest.hexdigest(),
    }


def doctor(root: Path, python: Path | None) -> dict[str, Any]:
    codemap = _stream_json_integer_metadata(
        root / ".aura/CODEMAP.json", ("file_count", "symbol_count")
    )
    output = {
        "ok": True, "version": VERSION, "repo_root": str(root),
        "git_identity": _git_info(root),
        "codemap": codemap,
        "ai_handoff": _ai_handoff_summary(root),
        "task_watchdog": _task_watchdog_policy(),
        "safe_to_patch": False, "production_mutation": False,
        "patch_authority": PATCH_AUTHORITY,
    }
    if python and python.is_file():
        output["target_imports"] = _probe(python, root)
        output["ok"] = output["target_imports"]["ok"]
    return output

def run_architecture(root: Path, *, objective: str, combine_with: list[str],
                     profile: str, top: int, pair_limit: int,
                     allow_expansive: bool, output_dir: str | Path,
                     resume: bool, enforce_clean: bool,
                     reference_files: list[str] | None = None,
                     watchdog_checkin_seconds: float = DEFAULT_WATCHDOG_CHECKIN_SECONDS,
                     watchdog_pause_seconds: float = DEFAULT_WATCHDOG_PAUSE_SECONDS) -> dict[str, Any]:
    sys.path.insert(0, str(root))
    from aura_architect_loop import ArchitectFusionLoop
    from aura_capability_connectome import build_capability_connectome
    from aura_capability_connectome_v2 import enrich_connectome
    from aura_emergent_potential_repl import audit_emergent_potential
    from aura_relational_index import build_relational_index
    from aura_relationship_atlas import build_relationship_atlas

    started = time.time()
    started_monotonic = time.monotonic()
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    watchdog_policy = _task_watchdog_policy(
        checkin_seconds=watchdog_checkin_seconds,
        pause_seconds=watchdog_pause_seconds,
    )
    _write_watchdog_progress(
        output_dir, phase="initialization", state="running",
        started_monotonic=started_monotonic,
    )
    reference_manifest = _reference_manifest(reference_files or [])
    request = {
        "version": VERSION, "repo_identity": _git_info(root),
        "objective": objective, "combine_with": combine_with,
        "atlas_profile": profile.upper(), "top": top,
        "pair_limit": pair_limit, "allow_expansive": allow_expansive,
        "reference_files": reference_manifest,
        "task_watchdog": watchdog_policy,
    }
    request["digest"] = _digest(request)
    request_path = output_dir / "harness_request.json"
    if resume and request_path.exists():
        if json.loads(request_path.read_text()).get("digest") != request["digest"]:
            raise RuntimeError("resume request does not match retained artifacts")
    else:
        _write(request_path, request)

    _write_watchdog_progress(
        output_dir, phase="connectome", state="starting",
        started_monotonic=started_monotonic,
    )
    connectome_path = output_dir / "connectome.json"
    if resume and connectome_path.exists():
        connectome = json.loads(connectome_path.read_text())
    else:
        connectome = enrich_connectome(build_capability_connectome(root))
        _write(connectome_path, connectome)
    _write_watchdog_progress(
        output_dir, phase="connectome", state="completed",
        started_monotonic=started_monotonic,
    )

    _write_watchdog_progress(
        output_dir, phase="relational_index", state="starting",
        started_monotonic=started_monotonic,
    )
    index_path = output_dir / "relational_index.json"
    index_summary_path = output_dir / "relational_index_summary.json"
    if resume and index_path.exists() and index_summary_path.exists():
        index_data = json.loads(index_path.read_text())
        index_summary = json.loads(index_summary_path.read_text())
    else:
        built = build_relational_index(root, profile="STANDARD", persist=False, include_index=True)
        index_data = built.pop("index")
        index_summary = built
        _write(index_path, index_data)
        _write(index_summary_path, index_summary)
    _write_watchdog_progress(
        output_dir, phase="relational_index", state="completed",
        started_monotonic=started_monotonic,
    )

    participants = int(index_summary.get("participant_count") or 0)
    pairs = participants * max(0, participants - 1) // 2
    profile = profile.upper()
    if profile not in {"MINIMAL", "STANDARD", "DEEP"}:
        raise ValueError("atlas profile must be MINIMAL, STANDARD, or DEEP")
    if profile != "MINIMAL" and pairs > pair_limit and not allow_expansive:
        raise RuntimeError(
            f"refusing {profile} scan over {pairs:,} participant pairs; "
            "use MINIMAL or explicitly allow the expansive scan"
        )

    _write_watchdog_progress(
        output_dir, phase="relationship_atlas", state="starting",
        started_monotonic=started_monotonic,
    )
    atlas_path = output_dir / "relationship_atlas.json"
    receipt_path = output_dir / "relationship_atlas_receipt.json"
    if resume and atlas_path.exists():
        atlas = json.loads(atlas_path.read_text())
    else:
        snapshot = build_relationship_atlas(
            repo_root=root,
            profile=profile,
            relational_index_data=index_data,
            persist=False,
        )
        atlas = snapshot.to_dict()
        _write(atlas_path, atlas)
        _write(
            receipt_path,
            {
                "snapshot_digest": snapshot.snapshot_digest,
                "assessments_count": len(snapshot.assessments),
                "prohibitions_count": len(snapshot.prohibitions),
                "missing_configurations_count": len(snapshot.missing_configurations),
                "operational_profile": profile,
                "freshness": "CURRENT",
                "persistence": "external_harness_artifact_only",
            },
        )
    _write_watchdog_progress(
        output_dir, phase="relationship_atlas", state="completed",
        started_monotonic=started_monotonic,
    )

    _write_watchdog_progress(
        output_dir, phase="emergent_properties", state="starting",
        started_monotonic=started_monotonic,
    )
    emergent_path = output_dir / "emergent_properties.json"
    if resume and emergent_path.exists():
        emergent = json.loads(emergent_path.read_text())
    else:
        report = audit_emergent_potential(
            root, top=top, focus=objective,
            new_function_description=objective, combine_with=combine_with,
        )
        emergent = report.to_dict()
        _write(emergent_path, emergent)
    _write_watchdog_progress(
        output_dir, phase="emergent_properties", state="completed",
        started_monotonic=started_monotonic,
    )

    _write_watchdog_progress(
        output_dir, phase="architect_preparation", state="starting",
        started_monotonic=started_monotonic,
    )
    architect_path = output_dir / "architect_preparation.json"
    if resume and architect_path.exists():
        architect = json.loads(architect_path.read_text())
    else:
        prepared = ArchitectFusionLoop(repo_root=root).prepare(
            objective,
            architecture_decision=(
                "Compile an objective-scoped, evidence-bound coding relationship "
                "capsule from Connectome anatomy, Atlas meaning, and Relational "
                "Synthesis composition; remain proposal-only."
            ),
            act_tasks=[
                {"objective": "Resolve the smallest capability path.",
                 "target_file": "aura_capability_connectome.py",
                 "target_symbol": "build_capability_connectome"},
                {"objective": "Classify required, missing, candidate, and prohibited relations.",
                 "target_file": "aura_relationship_atlas.py",
                 "target_symbol": "build_relationship_atlas"},
                {"objective": "Compile the objective-specific synthesis capsule.",
                 "target_file": "aura_relational_synthesis.py"},
                {"objective": "Ground combinations with Emergent Properties.",
                 "target_file": "aura_emergent_potential_repl.py",
                 "target_symbol": "audit_emergent_potential"},
            ],
            acceptance_criteria=[
                "Do not duplicate canonical ownership.",
                "Retain evidence and truth class.",
                "Apply prohibitions before ranking.",
                "Remain proposal-only and source-bounded.",
            ],
            rollback_conditions=["stale identity", "prohibited coupling", "unbounded scope"],
            constraints=["no production mutation", "no VSA patch authority",
                         "human review required", "independent verification required"],
            refresh_codemap=False,
        )
        architect = prepared.to_dict()
        _write(architect_path, architect)
    _write_watchdog_progress(
        output_dir, phase="architect_preparation", state="completed",
        started_monotonic=started_monotonic,
    )

    output = {
        "ok": True, "version": VERSION, "objective": objective,
        "repo_identity": _git_info(root), "request_digest": request["digest"],
        "reference_files": reference_manifest,
        "resumed": resume,
        "ai_handoff": _ai_handoff_summary(root),
        "task_watchdog": watchdog_policy,
        "connectome": {
            "node_count": connectome.get("node_count"),
            "edge_count": connectome.get("edge_count"),
            "graph_digest": connectome.get("graph_digest"),
        },
        "relational_index": index_summary,
        "atlas": {
            "profile": profile, "estimated_full_pair_count": pairs,
            "snapshot_digest": atlas.get("snapshot_digest"),
            "assessment_count": len(atlas.get("assessments") or []),
            "missing_configuration_count": len(atlas.get("missing_configurations") or []),
            "prohibition_count": len(atlas.get("prohibitions") or []),
        },
        "emergent": {
            "summary": emergent.get("summary", {}),
            "verifier_summary": emergent.get("verifier_summary", ""),
            "top_connection_ids": [row.get("connection_id") for row in (emergent.get("connections") or [])[:top]],
        },
        "architect": {
            "phase_hash": architect.get("plan", {}).get("phase_hash"),
            "intensity": architect.get("intensity"),
            "shadow_gate": architect.get("shadow_report", {}).get("gate"),
            "ready_for_incubator": architect.get("arena", {}).get("ready_for_incubator"),
        },
        "elapsed_seconds": round(time.time() - started, 3),
        "safe_to_patch": False, "production_mutation": False,
        "human_review_required": True, "patch_authority": PATCH_AUTHORITY,
    }
    post = _git_info(root)
    output["post_run_repo_identity"] = post
    if enforce_clean and post.get("available") and not post.get("clean"):
        output["ok"] = False
        output["tracked_repository_changes_detected"] = post.get("status", [])
    output["run_digest"] = _digest(output)
    _write(output_dir / "harness_summary.json", output)
    _write_watchdog_progress(
        output_dir, phase="complete", state="completed",
        started_monotonic=started_monotonic,
    )
    return output


def _default_venv(root: Path) -> Path:
    return root.parent / f".{root.name}-architecture-harness-venv"


def _run_resume_command(
    root: Path,
    venv_path: Path,
    output_dir: Path,
    args: argparse.Namespace,
) -> str:
    command = [
        sys.executable,
        "scripts/aura_architecture_harness.py",
        "--repo-root",
        str(root),
        "run",
        "--venv",
        str(venv_path),
        "--objective",
        args.objective,
        "--combine-with",
        *args.combine_with,
        "--atlas-profile",
        args.atlas_profile,
        "--top",
        str(args.top),
        "--pair-limit",
        str(args.pair_limit),
        "--output-dir",
        str(output_dir),
        "--watchdog-checkin-seconds",
        str(args.watchdog_checkin_seconds),
        "--watchdog-pause-seconds",
        str(args.watchdog_pause_seconds),
        "--resume",
    ]
    if args.allow_expansive_atlas:
        command.append("--allow-expansive-atlas")
    if args.allow_dirty:
        command.append("--allow-dirty")
    for reference in args.reference_file:
        command.extend(["--reference-file", reference])
    return subprocess.list2cmdline(command) if os.name == "nt" else shlex.join(command)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--venv")
    prep.add_argument("--system-site-packages", action="store_true")
    prep.add_argument("--install-requirements", action="store_true")
    prep.add_argument("--initialize-local-git", action="store_true")
    prep.add_argument("--source-sha", default="")
    doc = sub.add_parser("doctor")
    doc.add_argument("--venv")
    handoff = sub.add_parser("handoff")
    handoff.add_argument("--output-dir")
    handoff.add_argument(
        "--inline-max-bytes", type=int, default=DEFAULT_INLINE_MAX_BYTES
    )
    handoff.add_argument("--allow-dirty", action="store_true")
    handoff.add_argument("--no-archive", action="store_true")
    run = sub.add_parser("run")
    run.add_argument("--venv")
    run.add_argument("--objective", default=DEFAULT_OBJECTIVE)
    run.add_argument("--combine-with", nargs="*", default=["Connectome", "Relational Synthesis", "Atlas"])
    run.add_argument("--atlas-profile", default="MINIMAL")
    run.add_argument("--top", type=int, default=12)
    run.add_argument("--pair-limit", type=int, default=5_000_000)
    run.add_argument("--allow-expansive-atlas", action="store_true")
    run.add_argument("--allow-dirty", action="store_true")
    run.add_argument("--output-dir")
    run.add_argument(
        "--reference-file",
        action="append",
        default=[],
        help="Bind an external specification or evidence file by name, size, and SHA-256.",
    )
    run.add_argument("--resume", action="store_true")
    run.add_argument(
        "--watchdog-checkin-seconds",
        type=float,
        default=DEFAULT_WATCHDOG_CHECKIN_SECONDS,
        help="Emit a progress reassessment at this interval (default: 600 seconds).",
    )
    run.add_argument(
        "--watchdog-pause-seconds",
        type=float,
        default=DEFAULT_WATCHDOG_PAUSE_SECONDS,
        help="Pause safely and require --resume after this runtime (default: 1200 seconds).",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    try:
        root = _root(args.repo_root)
        venv_path = Path(args.venv).expanduser().resolve() if getattr(args, "venv", None) else _default_venv(root)
        python = _venv_python(venv_path)
        if args.command == "prepare":
            result = prepare(root, venv_path,
                             system_packages=args.system_site_packages,
                             install_requirements=args.install_requirements,
                             initialize_git=args.initialize_local_git,
                             source_sha=args.source_sha)
        elif args.command == "doctor":
            result = doctor(root, python if python.is_file() else None)
        elif args.command == "handoff":
            result = create_ai_handoff(
                root,
                output_dir=args.output_dir,
                inline_max_bytes=args.inline_max_bytes,
                allow_dirty=args.allow_dirty,
                create_archive=not args.no_archive,
            )
        else:
            identity = _git_info(root)
            if not identity.get("available"):
                raise RuntimeError("run prepare with --initialize-local-git first")
            if not identity.get("clean") and not args.allow_dirty:
                raise RuntimeError("repository is dirty; use a clean checkout")
            if not python.is_file():
                raise RuntimeError("harness venv missing; run prepare first")
            output_dir = Path(args.output_dir).resolve() if args.output_dir else (
                root.parent / f"{root.name}-architecture-harness-runs" /
                time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
            )
            payload = {
                "root": str(root), "objective": args.objective,
                "combine_with": args.combine_with, "profile": args.atlas_profile,
                "top": args.top, "pair_limit": args.pair_limit,
                "allow_expansive": args.allow_expansive_atlas,
                "output_dir": str(output_dir), "resume": args.resume,
                "enforce_clean": not args.allow_dirty,
                "reference_files": args.reference_file,
                "watchdog_checkin_seconds": args.watchdog_checkin_seconds,
                "watchdog_pause_seconds": args.watchdog_pause_seconds,
            }
            code = (
                "import json,sys;from pathlib import Path;"
                "sys.path.insert(0,sys.argv[1]);"
                "from scripts.aura_architecture_harness import run_architecture;"
                "p=json.loads(sys.argv[2]);"
                "r=run_architecture(Path(p.pop('root')),**p);"
                "print(json.dumps(r,indent=2,sort_keys=True))"
            )
            monitored = _run_with_watchdog(
                [str(python), "-c", code, str(root), json.dumps(payload)],
                root,
                output_dir=output_dir,
                checkin_seconds=args.watchdog_checkin_seconds,
                pause_seconds=args.watchdog_pause_seconds,
                env={"PYTHONPATH": str(root)},
                resume_command=_run_resume_command(root, venv_path, output_dir, args),
            )
            process = monitored.command
            if monitored.paused:
                result = {
                    "ok": False,
                    "paused": True,
                    "version": VERSION,
                    "reason": "watchdog_hard_pause",
                    "watchdog": monitored.pause_receipt,
                    "checkins": list(monitored.checkins),
                    "safe_to_patch": False,
                    "production_mutation": False,
                    "human_review_required": True,
                    "patch_authority": PATCH_AUTHORITY,
                }
            else:
                if process.returncode:
                    raise RuntimeError(process.stderr.strip() or process.stdout.strip())
                result = json.loads(process.stdout)
                result["watchdog"] = {
                    "checkin_seconds": args.watchdog_checkin_seconds,
                    "pause_seconds": args.watchdog_pause_seconds,
                    "checkin_count": len(monitored.checkins),
                    "checkins": list(monitored.checkins),
                    "paused": False,
                    "status_path": str(output_dir / WATCHDOG_STATUS_FILE),
                    "events_path": str(output_dir / WATCHDOG_EVENTS_FILE),
                }
                _write(output_dir / "harness_summary.json", result)
        print(json.dumps(result, indent=2, sort_keys=True))
        if result.get("paused"):
            return 2
        return 0 if result.get("ok") else 1
    except Exception as exc:
        print(json.dumps({"ok": False, "version": VERSION,
                          "error": f"{type(exc).__name__}: {exc}",
                          "safe_to_patch": False, "production_mutation": False},
                         indent=2, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
