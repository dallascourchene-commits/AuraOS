#!/usr/bin/env python3
"""Bounded runtime reproduction and end-to-end verification for AuraOS.

The harness creates an isolated Python environment, starts one loopback-only
application server from a repository-owned profile, runs a bounded probe and
verification commands without a shell, captures exact evidence, and terminates
the server. It never edits source, applies a patch, commits, pushes, opens a
pull request, or merges.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping, Sequence
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from typing import Any
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
import venv

VERSION = "AURA_RUNTIME_REFACTOR_HARNESS_V1"
PROFILE_VERSION = "AURA_RUNTIME_PROFILE_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
MAX_PROFILE_BYTES = 256 * 1024
MAX_RECEIPT_BYTES = 2 * 1024 * 1024
MAX_COMMANDS = 32
MAX_COMMAND_ARGS = 96
MAX_ARG_BYTES = 16 * 1024
MAX_OUTPUT_BYTES = 64 * 1024
MAX_ARTIFACT_BYTES = 32 * 1024 * 1024
MAX_REQUIRED_ARTIFACTS = 32
DEFAULT_COMMAND_TIMEOUT_SECONDS = 180
DEFAULT_READINESS_TIMEOUT_SECONDS = 60
SAFE_ENV_KEYS = frozenset(
    {
        "PATH",
        "HOME",
        "USERPROFILE",
        "SYSTEMROOT",
        "COMSPEC",
        "PATHEXT",
        "TMPDIR",
        "TMP",
        "TEMP",
        "LANG",
        "LC_ALL",
        "NODE_PATH",
        "LD_LIBRARY_PATH",
        "PLAYWRIGHT_BROWSERS_PATH",
        "XDG_RUNTIME_DIR",
    }
)
SENSITIVE_ENV_FRAGMENT = re.compile(r"TOKEN|SECRET|PASSWORD|CREDENTIAL|PRIVATE|API_KEY", re.IGNORECASE)
AUTHORITY_CONTRACT = {
    "production_mutation": False,
    "automatic_fix": False,
    "automatic_commit": False,
    "automatic_push": False,
    "automatic_pull_request": False,
    "automatic_merge": False,
    "runtime_evidence_authority": False,
    "human_review_required": True,
    "patch_authority": PATCH_AUTHORITY,
}
AXIOM_BINDINGS = (
    "observe_runtime_before_mutation",
    "preserve_source_truth_separate_from_presentation_truth",
    "classify_performance_evidence_separately_from_integrity_evidence",
    "bind every conclusion to exact profile source and runtime artifacts",
    "retain only independently verified repairs",
    "keep patch and merge authority outside the harness",
)


class RuntimeHarnessError(RuntimeError):
    """Raised when a runtime profile or execution violates a hard boundary."""


def _json_digest(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=32).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


class _BoundedStreamCapture:
    """Drain one child stream while retaining only a fixed-size evidence tail."""

    def __init__(self, maximum: int = MAX_OUTPUT_BYTES) -> None:
        self.maximum = maximum
        self.total_bytes = 0
        self.tail = bytearray()
        self.digest = hashlib.sha256()

    def consume(self, stream: Any) -> None:
        try:
            while True:
                chunk = stream.read(8192)
                if not chunk:
                    break
                self.total_bytes += len(chunk)
                self.digest.update(chunk)
                self.tail.extend(chunk)
                overflow = len(self.tail) - self.maximum
                if overflow > 0:
                    del self.tail[:overflow]
        finally:
            stream.close()

    def receipt(self) -> dict[str, Any]:
        retained = bytes(self.tail)
        return {
            "text": retained.decode("utf-8", errors="replace"),
            "truncated": self.total_bytes > len(retained),
            "total_bytes": self.total_bytes,
            "retained_bytes": len(retained),
            "retention": "TAIL",
            "sha256": self.digest.hexdigest(),
        }

    def write_log(self, path: Path) -> None:
        path.write_bytes(bytes(self.tail))


def _start_bounded_capture(
    process: subprocess.Popen[Any],
) -> tuple[_BoundedStreamCapture, _BoundedStreamCapture, tuple[threading.Thread, ...]]:
    if process.stdout is None or process.stderr is None:
        raise RuntimeHarnessError("child process pipes were not allocated")
    stdout = _BoundedStreamCapture()
    stderr = _BoundedStreamCapture()
    threads = (
        threading.Thread(target=stdout.consume, args=(process.stdout,), daemon=True),
        threading.Thread(target=stderr.consume, args=(process.stderr,), daemon=True),
    )
    for thread in threads:
        thread.start()
    return stdout, stderr, threads


def _finish_bounded_capture(
    stdout: _BoundedStreamCapture,
    stderr: _BoundedStreamCapture,
    threads: Sequence[threading.Thread],
    *,
    output: Path,
    label: str,
) -> dict[str, Any]:
    for thread in threads:
        thread.join(timeout=10)
    complete = not any(thread.is_alive() for thread in threads)
    stdout.write_log(output / f"{label}.stdout.log")
    stderr.write_log(output / f"{label}.stderr.log")
    return {
        "capture_complete": complete,
        "stdout": stdout.receipt(),
        "stderr": stderr.receipt(),
    }


def _safe_repo_path(root: Path, value: str, label: str) -> Path:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise RuntimeHarnessError(f"{label} must be a non-empty POSIX repository path")
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts:
        raise RuntimeHarnessError(f"{label} escapes the repository")
    candidate = root
    for part in pure.parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise RuntimeHarnessError(f"{label} contains a symbolic link")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise RuntimeHarnessError(f"{label} escapes the repository") from exc
    return resolved


def _external_output_path(root: Path, value: str | Path) -> Path:
    output = Path(value).expanduser().resolve()
    try:
        output.relative_to(root)
    except ValueError:
        return output
    raise RuntimeHarnessError("runtime evidence output must be outside the repository checkout")


def _positive_number(value: Any, label: str, *, maximum: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0 or value > maximum:
        raise RuntimeHarnessError(f"{label} must be in (0, {maximum}]")
    return float(value)


_MISSING = object()


def _strict_bool(value: Any, label: str, *, default: bool) -> bool:
    if value is _MISSING:
        return default
    if not isinstance(value, bool):
        raise RuntimeHarnessError(f"{label} must be a boolean")
    return value


def _validate_loopback_url(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise RuntimeHarnessError(f"{label} must be a URL string")
    parsed = urlparse(value)
    if parsed.scheme != "http" or parsed.hostname not in {
        "127.0.0.1",
        "::1",
    }:
        raise RuntimeHarnessError(f"{label} must use loopback HTTP")
    if parsed.username or parsed.password or not parsed.port:
        raise RuntimeHarnessError(f"{label} must include a port and no credentials")
    return value


def _validate_command(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or len(value) > MAX_COMMAND_ARGS:
        raise RuntimeHarnessError(f"{label} must be a non-empty bounded argument array")
    output: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item or "\x00" in item:
            raise RuntimeHarnessError(f"{label} contains an invalid argument")
        if len(item.encode("utf-8")) > MAX_ARG_BYTES:
            raise RuntimeHarnessError(f"{label} contains an oversized argument")
        output.append(item)
    return tuple(output)


def _validate_env(value: Any, label: str) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict) or len(value) > 64:
        raise RuntimeHarnessError(f"{label} must be a bounded object")
    output: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", key):
            raise RuntimeHarnessError(f"{label} contains an invalid environment key")
        if SENSITIVE_ENV_FRAGMENT.search(key):
            raise RuntimeHarnessError(f"{label} may not declare secret-bearing environment keys")
        if not isinstance(item, str) or "\x00" in item or len(item.encode("utf-8")) > MAX_ARG_BYTES:
            raise RuntimeHarnessError(f"{label}.{key} must be a bounded string")
        output[key] = item
    return output


def load_runtime_profile(root: Path, profile_path: str | Path) -> dict[str, Any]:
    root = root.resolve()
    path = _safe_repo_path(root, str(profile_path), "runtime profile")
    if not path.is_file() or path.is_symlink():
        raise RuntimeHarnessError(f"runtime profile is missing or unsafe: {path}")
    if path.stat().st_size > MAX_PROFILE_BYTES:
        raise RuntimeHarnessError("runtime profile exceeds the size boundary")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeHarnessError(f"runtime profile is not canonical UTF-8 JSON: {exc}") from exc
    if not isinstance(raw, dict) or raw.get("version") != PROFILE_VERSION:
        raise RuntimeHarnessError(f"runtime profile version must be {PROFILE_VERSION}")
    profile_id = raw.get("profile_id")
    if not isinstance(profile_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", profile_id):
        raise RuntimeHarnessError("runtime profile_id is invalid")
    objective = raw.get("objective")
    if not isinstance(objective, str) or not objective.strip() or len(objective) > 1000:
        raise RuntimeHarnessError("runtime profile objective is invalid")

    environment = raw.get("environment") or {}
    if not isinstance(environment, dict):
        raise RuntimeHarnessError("runtime profile environment must be an object")
    requirements = environment.get("requirements") or []
    if not isinstance(requirements, list) or len(requirements) > 8:
        raise RuntimeHarnessError("runtime requirements must be a bounded array")
    requirement_paths: list[str] = []
    for index, requirement in enumerate(requirements):
        target = _safe_repo_path(root, requirement, f"requirements[{index}]")
        if not target.is_file() or target.is_symlink():
            raise RuntimeHarnessError(f"requirements file is missing or unsafe: {requirement}")
        requirement_paths.append(requirement)

    server = raw.get("server")
    probe = raw.get("probe")
    if not isinstance(server, dict) or not isinstance(probe, dict):
        raise RuntimeHarnessError("runtime profile requires server and probe objects")
    server_command = _validate_command(server.get("command"), "server.command")
    readiness_url = _validate_loopback_url(server.get("readiness_url"), "server.readiness_url")
    server_timeout = _positive_number(
        server.get("readiness_timeout_seconds", DEFAULT_READINESS_TIMEOUT_SECONDS),
        "server.readiness_timeout_seconds",
        maximum=900,
    )
    probe_command = _validate_command(probe.get("command"), "probe.command")
    probe_timeout = _positive_number(
        probe.get("timeout_seconds", DEFAULT_COMMAND_TIMEOUT_SECONDS),
        "probe.timeout_seconds",
        maximum=3600,
    )
    probe_env = _validate_env(probe.get("env"), "probe.env")
    required_artifacts = probe.get("required_artifacts") or []
    if not isinstance(required_artifacts, list) or len(required_artifacts) > MAX_REQUIRED_ARTIFACTS:
        raise RuntimeHarnessError("probe.required_artifacts must be a bounded array")
    canonical_artifacts: list[str] = []
    for index, item in enumerate(required_artifacts):
        if not isinstance(item, str) or not item or "\\" in item or "\x00" in item:
            raise RuntimeHarnessError(f"probe.required_artifacts[{index}] is invalid")
        pure = PurePosixPath(item)
        if pure.is_absolute() or ".." in pure.parts:
            raise RuntimeHarnessError("probe artifact path escapes the output directory")
        canonical_artifacts.append(item)
    success_json = probe.get("success_json")
    if success_json is not None and success_json not in canonical_artifacts:
        raise RuntimeHarnessError("probe.success_json must be one of the required artifacts")
    success_field = probe.get("success_field", "ok")
    if not isinstance(success_field, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]{0,127}", success_field):
        raise RuntimeHarnessError("probe.success_field is invalid")

    verification_raw = raw.get("verification_commands") or []
    if not isinstance(verification_raw, list) or len(verification_raw) > MAX_COMMANDS:
        raise RuntimeHarnessError("verification_commands must be a bounded array")
    verification: list[dict[str, Any]] = []
    for index, row in enumerate(verification_raw):
        if isinstance(row, list):
            command = _validate_command(row, f"verification_commands[{index}]")
            timeout = DEFAULT_COMMAND_TIMEOUT_SECONDS
        elif isinstance(row, dict):
            command = _validate_command(
                row.get("command"),
                f"verification_commands[{index}].command",
            )
            timeout = _positive_number(
                row.get("timeout_seconds", DEFAULT_COMMAND_TIMEOUT_SECONDS),
                f"verification_commands[{index}].timeout_seconds",
                maximum=3600,
            )
        else:
            raise RuntimeHarnessError(f"verification_commands[{index}] is invalid")
        verification.append({"command": command, "timeout_seconds": timeout})

    return {
        "version": PROFILE_VERSION,
        "profile_id": profile_id,
        "objective": objective.strip(),
        "profile_path": str(path.relative_to(root).as_posix()),
        "profile_sha256": _sha256(path),
        "environment": {
            "create_venv": _strict_bool(
                environment.get("create_venv", _MISSING),
                "environment.create_venv",
                default=True,
            ),
            "requirements": tuple(requirement_paths),
        },
        "server": {
            "command": server_command,
            "readiness_url": readiness_url,
            "readiness_timeout_seconds": server_timeout,
        },
        "probe": {
            "command": probe_command,
            "timeout_seconds": probe_timeout,
            "env": probe_env,
            "required_artifacts": tuple(canonical_artifacts),
            "success_json": success_json,
            "success_field": success_field,
        },
        "verification_commands": tuple(verification),
        "axiom_bindings": tuple(raw.get("axiom_bindings") or AXIOM_BINDINGS),
    }


def _venv_python(venv_path: Path) -> Path:
    return venv_path / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _git_identity(root: Path) -> dict[str, Any]:
    if shutil.which("git") is None or not (root / ".git").exists():
        return {
            "available": False,
            "head": "",
            "branch": "",
            "status": [],
        }

    def call(*args: str) -> str:
        process = subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        return process.stdout.strip() if process.returncode == 0 else ""

    status_text = call("status", "--porcelain=v1", "-z")
    status = [item for item in status_text.split("\x00") if item][:10_000]
    return {
        "available": True,
        "head": call("rev-parse", "HEAD"),
        "branch": call("branch", "--show-current"),
        "status": status,
        "clean": not status,
    }


def _safe_environment(root: Path, additions: Mapping[str, str] | None = None) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key in SAFE_ENV_KEYS}
    env["PYTHONPATH"] = str(root)
    for key, value in (additions or {}).items():
        env[key] = value
    return env


def _substitute(value: str, *, root: Path, output: Path, python: Path) -> str:
    return value.replace("{repo}", str(root)).replace("{output}", str(output)).replace("{python}", str(python))


def _resolve_command(command: Sequence[str], *, root: Path, output: Path, python: Path) -> tuple[str, ...]:
    values = tuple(_substitute(item, root=root, output=output, python=python) for item in command)
    executable = values[0]
    if executable == str(python):
        resolved = python
    elif "/" in executable or "\\" in executable:
        candidate = Path(executable)
        resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
        if not candidate.is_absolute():
            try:
                resolved.relative_to(root)
            except ValueError as exc:
                raise RuntimeHarnessError("command executable escapes the repository") from exc
    else:
        found = shutil.which(executable, path=os.environ.get("PATH"))
        if not found:
            raise RuntimeHarnessError(f"runtime executable is unavailable: {executable}")
        resolved = Path(found).resolve()
    if not resolved.is_file():
        raise RuntimeHarnessError(f"runtime executable is not a file: {resolved}")
    return (str(resolved), *values[1:])


def _run_command(
    command: Sequence[str],
    *,
    root: Path,
    output: Path,
    python: Path,
    env: Mapping[str, str],
    timeout_seconds: float,
    label: str,
) -> dict[str, Any]:
    resolved = _resolve_command(command, root=root, output=output, python=python)
    started = time.monotonic()
    process = subprocess.Popen(
        resolved,
        cwd=root,
        env=dict(env),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
        start_new_session=(os.name != "nt"),
    )
    stdout, stderr, threads = _start_bounded_capture(process)
    timed_out = False
    try:
        returncode = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_process(process)
        returncode = 124
    capture = _finish_bounded_capture(
        stdout,
        stderr,
        threads,
        output=output,
        label=label,
    )
    receipt = {
        "label": label,
        "command": list(resolved),
        "returncode": returncode,
        "timed_out": timed_out,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        **capture,
    }
    _write_json(output / f"{label}.receipt.json", receipt)
    return receipt


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


def _readiness(url: str, timeout_seconds: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    attempts = 0
    last_error = ""
    started = time.monotonic()
    opener = build_opener(_NoRedirectHandler())
    while time.monotonic() < deadline:
        attempts += 1
        try:
            request = Request(url, headers={"Cache-Control": "no-cache"})
            with opener.open(
                request,
                timeout=min(3.0, max(0.1, deadline - time.monotonic())),
            ) as response:
                status = int(response.status)
                body = response.read(1024)
            if 200 <= status < 300:
                return {
                    "ok": True,
                    "url": url,
                    "status": status,
                    "attempts": attempts,
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                    "body_prefix_sha256": hashlib.sha256(body).hexdigest(),
                }
            last_error = f"HTTP {status}"
        except (URLError, TimeoutError, OSError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        time.sleep(0.25)
    return {
        "ok": False,
        "url": url,
        "attempts": attempts,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "error": last_error or "readiness timeout",
    }


def _terminate_process(
    process: subprocess.Popen[Any],
) -> dict[str, Any]:
    if process.poll() is not None:
        return {
            "already_exited": True,
            "returncode": process.returncode,
        }
    try:
        if os.name == "nt":
            process.terminate()
        else:
            os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=5)
        return {
            "already_exited": False,
            "forced": False,
            "returncode": process.returncode,
        }
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            if os.name == "nt":
                process.kill()
            else:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            pass
        return {
            "already_exited": False,
            "forced": True,
            "returncode": process.poll(),
        }


def _read_success_field(path: Path, field: str) -> tuple[bool, Any]:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_RECEIPT_BYTES:
        return False, None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, OSError):
        return False, None
    current: Any = value
    for part in field.split("."):
        if not isinstance(current, dict) or part not in current:
            return False, None
        current = current[part]
    return current is True, current


def _artifact_inventory(output: Path, paths: Sequence[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in paths:
        path = (output / Path(*PurePosixPath(item).parts)).resolve()
        try:
            path.relative_to(output)
        except ValueError as exc:
            raise RuntimeHarnessError("runtime artifact escaped the output directory") from exc
        candidate = output / Path(*PurePosixPath(item).parts)
        symlinked = candidate.is_symlink()
        size = candidate.stat().st_size if candidate.is_file() and not symlinked else 0
        within_size_limit = size <= MAX_ARTIFACT_BYTES
        row: dict[str, Any] = {
            "path": item,
            "present": candidate.is_file() and not symlinked,
            "symlinked": symlinked,
            "size_bytes": size,
            "within_size_limit": within_size_limit,
        }
        if row["present"] and within_size_limit:
            row["sha256"] = _sha256(candidate)
        rows.append(row)
    return rows


def _load_baseline(
    path: str | Path | None,
) -> dict[str, Any] | None:
    if path is None:
        return None
    target = Path(path).expanduser().resolve()
    if not target.is_file() or target.is_symlink() or target.stat().st_size > MAX_RECEIPT_BYTES:
        raise RuntimeHarnessError("baseline receipt is missing or unsafe")
    value = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("version") != VERSION or not value.get("run_digest"):
        raise RuntimeHarnessError("baseline receipt is not an Aura runtime harness receipt")
    return {
        "path": str(target),
        "sha256": _sha256(target),
        "run_digest": value["run_digest"],
        "ok": bool(value.get("ok")),
        "profile_id": value.get("profile_id"),
    }


def run_runtime_profile(
    root: Path,
    *,
    profile_path: str | Path,
    output_dir: str | Path,
    venv_path: str | Path | None = None,
    install_requirements: bool = False,
    allow_dirty: bool = False,
    baseline_receipt: str | Path | None = None,
    nested_replay_context: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise RuntimeHarnessError("repository root is missing")
    # Reject externally supplied nested replay mode — it must come from
    # the internal nested_replay_context parameter, not from the environment.
    if os.environ.get("AURA_NESTED_REPLAY_MODE") and nested_replay_context is None:
        raise RuntimeHarnessError(
            "AURA_NESTED_REPLAY_MODE is set in the external environment — "
            "this variable is internal-only; unset it before running a top-level proof"
        )
    profile = load_runtime_profile(root, profile_path)
    output = _external_output_path(root, output_dir)
    # Reject non-empty output directories to prevent stale artifact reuse.
    if output.exists() and any(output.iterdir()):
        raise RuntimeHarnessError(
            f"runtime output directory is not empty: {output} — "
            "use a fresh directory for each run"
        )
    output.mkdir(parents=True, exist_ok=True)
    before = _git_identity(root)
    if before.get("available") and before.get("status") and not allow_dirty:
        raise RuntimeHarnessError("repository is dirty; runtime evidence must bind a clean tree")

    default_venv = root.parent / f".{root.name}-runtime-harness-venv"
    venv_dir = Path(venv_path).expanduser().resolve() if venv_path else default_venv.resolve()
    try:
        venv_dir.relative_to(root)
    except ValueError:
        pass
    else:
        raise RuntimeHarnessError("runtime venv must be outside the repository checkout")

    environment_receipts: list[dict[str, Any]] = []
    if profile["environment"]["create_venv"]:
        if not _venv_python(venv_dir).is_file():
            venv.EnvBuilder(with_pip=True).create(venv_dir)
        python = _venv_python(venv_dir)
    else:
        python = Path(sys.executable).resolve()

    base_env = _safe_environment(root)
    # Propagate nested replay context to child processes when provided
    # internally. This is NOT inherited from the external environment —
    # it comes from the nested_replay_context parameter set by
    # execute_exact_runtime_replay in the P4 server.
    if nested_replay_context:
        for _key, _val in nested_replay_context.items():
            base_env[_key] = _val
    if install_requirements:
        for index, requirement in enumerate(profile["environment"]["requirements"]):
            result = _run_command(
                [
                    "{python}",
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    str(_safe_repo_path(root, requirement, "requirement")),
                ],
                root=root,
                output=output,
                python=python,
                env=base_env,
                timeout_seconds=1800,
                label=f"environment-{index:02d}",
            )
            environment_receipts.append(result)
            if result["returncode"] != 0:
                raise RuntimeHarnessError(f"requirements installation failed: {requirement}")

    server_command = _resolve_command(
        profile["server"]["command"],
        root=root,
        output=output,
        python=python,
    )
    # Allow port override via environment variable for nested runtime proofs.
    # When the V2 adapter re-runs the V1 profile inside an already-running
    # P4 server, the nested server must use a different port.
    _port_override = os.environ.get("AURA_RUNTIME_SERVER_PORT")
    if _port_override:
        server_command = [
            arg if arg != "8768" else _port_override
            for arg in server_command
        ]
        # Also update the readiness URL if it references the old port.
        readiness_url = profile["server"].get("readiness_url", "")
        if "8768" in readiness_url:
            profile["server"]["readiness_url"] = readiness_url.replace("8768", _port_override)
        # Update probe environment to point at the nested server port.
        probe_env = profile.get("probe", {}).get("env", {})
        if "AURA_CONSTRUCTION_PASCAL_FOUNDRY_URL" in probe_env:
            probe_env["AURA_CONSTRUCTION_PASCAL_FOUNDRY_URL"] = (
                probe_env["AURA_CONSTRUCTION_PASCAL_FOUNDRY_URL"].replace("8768", _port_override)
            )
    process: subprocess.Popen[Any] | None = None
    server_capture: (
        tuple[
            _BoundedStreamCapture,
            _BoundedStreamCapture,
            tuple[threading.Thread, ...],
        ]
        | None
    ) = None
    server_output: dict[str, Any] = {"capture_complete": False}
    readiness: dict[str, Any] = {
        "ok": False,
        "error": "server not started",
    }
    probe_receipt: dict[str, Any] = {
        "returncode": 125,
        "error": "probe not run",
    }
    verification_receipts: list[dict[str, Any]] = []
    termination: dict[str, Any] = {"not_started": True}
    started_at = time.time()
    try:
        process = subprocess.Popen(
            server_command,
            cwd=root,
            env=base_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            start_new_session=(os.name != "nt"),
        )
        server_capture = _start_bounded_capture(process)
        readiness = _readiness(
            profile["server"]["readiness_url"],
            profile["server"]["readiness_timeout_seconds"],
        )
        _write_json(output / "readiness.receipt.json", readiness)
        if readiness["ok"]:
            probe_env_values = {
                key: _substitute(value, root=root, output=output, python=python)
                for key, value in profile["probe"]["env"].items()
            }
            # Also propagate nested replay context to the browser probe.
            if nested_replay_context:
                for _key, _val in nested_replay_context.items():
                    probe_env_values[_key] = _val
            probe_env = _safe_environment(root, probe_env_values)
            probe_receipt = _run_command(
                profile["probe"]["command"],
                root=root,
                output=output,
                python=python,
                env=probe_env,
                timeout_seconds=profile["probe"]["timeout_seconds"],
                label="probe",
            )
    finally:
        if process is not None:
            termination = _terminate_process(process)
        if server_capture is not None:
            server_output = _finish_bounded_capture(
                server_capture[0],
                server_capture[1],
                server_capture[2],
                output=output,
                label="server",
            )
        _write_json(output / "server-output.receipt.json", server_output)
        _write_json(output / "server-termination.receipt.json", termination)

    for index, row in enumerate(profile["verification_commands"]):
        receipt = _run_command(
            row["command"],
            root=root,
            output=output,
            python=python,
            env=base_env,
            timeout_seconds=row["timeout_seconds"],
            label=f"verify-{index:02d}",
        )
        verification_receipts.append(receipt)

    artifacts = _artifact_inventory(output, profile["probe"]["required_artifacts"])
    success_ok = True
    success_value: Any = None
    if profile["probe"]["success_json"]:
        success_path = output / Path(*PurePosixPath(profile["probe"]["success_json"]).parts)
        success_ok, success_value = _read_success_field(success_path, profile["probe"]["success_field"])
    after = _git_identity(root)
    tree_unchanged = before.get("head") == after.get("head") and before.get("status") == after.get("status")
    verification_ok = all(item["returncode"] == 0 for item in verification_receipts)
    command_capture_ok = (
        probe_receipt.get("capture_complete") is True
        and all(item.get("capture_complete") is True for item in environment_receipts)
        and all(item.get("capture_complete") is True for item in verification_receipts)
    )
    server_capture_ok = server_output.get("capture_complete") is True
    artifacts_ok = all(item["present"] and item["within_size_limit"] for item in artifacts)
    ok = (
        readiness.get("ok") is True
        and probe_receipt.get("returncode") == 0
        and success_ok
        and artifacts_ok
        and verification_ok
        and command_capture_ok
        and server_capture_ok
        and tree_unchanged
    )
    baseline = _load_baseline(baseline_receipt)
    if baseline and baseline.get("profile_id") != profile["profile_id"]:
        raise RuntimeHarnessError("baseline receipt profile does not match current runtime profile")
    cycle_state = (
        "REPAIRED_AND_VERIFIED"
        if baseline and not baseline["ok"] and ok
        else "REGRESSION_DETECTED"
        if baseline and baseline["ok"] and not ok
        else "RUNTIME_VERIFIED"
        if ok
        else "RUNTIME_FAILURE_REPRODUCED"
    )
    receipt = {
        "version": VERSION,
        "profile_version": PROFILE_VERSION,
        "profile_id": profile["profile_id"],
        "objective": profile["objective"],
        "profile_path": profile["profile_path"],
        "profile_sha256": profile["profile_sha256"],
        "ok": ok,
        "cycle_state": cycle_state,
        "baseline": baseline,
        "repo_identity_before": before,
        "repo_identity_after": after,
        "repository_unchanged": tree_unchanged,
        "venv_path": (str(venv_dir) if profile["environment"]["create_venv"] else None),
        "python": str(python),
        "requirements_install": environment_receipts,
        "server_command": list(server_command),
        "readiness": readiness,
        "probe": probe_receipt,
        "probe_success_field": {
            "path": profile["probe"]["success_json"],
            "field": profile["probe"]["success_field"],
            "value": success_value,
            "ok": success_ok,
        },
        "verification": verification_receipts,
        "command_capture_complete": command_capture_ok,
        "server_capture_complete": server_capture_ok,
        "artifacts": artifacts,
        "server_output": server_output,
        "server_termination": termination,
        "elapsed_seconds": round(time.time() - started_at, 3),
        "axiom_bindings": list(profile["axiom_bindings"]),
        **AUTHORITY_CONTRACT,
    }
    receipt["run_digest"] = _json_digest(receipt)
    receipt_path = output / "runtime_harness_receipt.json"
    _write_json(receipt_path, receipt)
    return {
        **receipt,
        "receipt_path": str(receipt_path),
        "output_dir": str(output),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--venv")
    parser.add_argument("--install-requirements", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--baseline-receipt")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    try:
        result = run_runtime_profile(
            Path(args.repo_root),
            profile_path=args.profile,
            output_dir=args.output_dir,
            venv_path=args.venv,
            install_requirements=args.install_requirements,
            allow_dirty=args.allow_dirty,
            baseline_receipt=args.baseline_receipt,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ok"] else 1
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "version": VERSION,
                    "error": f"{type(exc).__name__}: {exc}",
                    **AUTHORITY_CONTRACT,
                },
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
