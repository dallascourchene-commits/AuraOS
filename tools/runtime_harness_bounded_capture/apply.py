from __future__ import annotations

from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"hardening anchor missing: {label}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    harness = Path("scripts/aura_runtime_refactor_harness.py")
    replace_once(
        harness,
        "import subprocess\nimport sys\n",
        "import subprocess\nimport sys\nimport threading\n",
        "threading import",
    )
    replace_once(
        harness,
        "from urllib.request import Request, urlopen\n",
        "from urllib.request import HTTPRedirectHandler, Request, build_opener\n",
        "bounded readiness imports",
    )
    replace_once(
        harness,
        "MAX_OUTPUT_BYTES = 64 * 1024\nMAX_REQUIRED_ARTIFACTS = 32\n",
        "MAX_OUTPUT_BYTES = 64 * 1024\nMAX_ARTIFACT_BYTES = 32 * 1024 * 1024\nMAX_REQUIRED_ARTIFACTS = 32\n",
        "artifact size constant",
    )
    replace_once(
        harness,
        '''def _bounded_text(value: str, maximum: int = MAX_OUTPUT_BYTES) -> dict[str, Any]:
    encoded = value.encode("utf-8", errors="replace")
    if len(encoded) <= maximum:
        return {"text": value, "truncated": False, "total_bytes": len(encoded)}
    tail = encoded[-maximum:].decode("utf-8", errors="replace")
    return {"text": tail, "truncated": True, "total_bytes": len(encoded)}
''',
        '''class _BoundedStreamCapture:
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
''',
        "bounded stream capture",
    )
    replace_once(
        harness,
        '''    resolved = (root / Path(*pure.parts)).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise RuntimeHarnessError(f"{label} escapes the repository") from exc
    return resolved
''',
        '''    candidate = root
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
''',
        "symlink-safe repository path",
    )
    replace_once(
        harness,
        '''    if parsed.scheme != "http" or parsed.hostname not in {
        "127.0.0.1",
        "localhost",
        "::1",
    }:
''',
        '''    if parsed.scheme != "http" or parsed.hostname not in {
        "127.0.0.1",
        "::1",
    }:
''',
        "literal loopback readiness",
    )
    replace_once(
        harness,
        '''def _run_command(
    command: Sequence[str],
    *,
    root: Path,
    output: Path,
    python: Path,
    env: Mapping[str, str],
    timeout_seconds: float,
    label: str,
) -> dict[str, Any]:
    resolved = _resolve_command(
        command, root=root, output=output, python=python
    )
    started = time.monotonic()
    try:
        process = subprocess.run(
            resolved,
            cwd=root,
            env=dict(env),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        timed_out = False
        returncode = process.returncode
        stdout = process.stdout
        stderr = process.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        returncode = 124
        stdout = (
            exc.stdout.decode(errors="replace")
            if isinstance(exc.stdout, bytes)
            else (exc.stdout or "")
        )
        stderr = (
            exc.stderr.decode(errors="replace")
            if isinstance(exc.stderr, bytes)
            else (exc.stderr or "")
        )
    receipt = {
        "label": label,
        "command": list(resolved),
        "returncode": returncode,
        "timed_out": timed_out,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "stdout": _bounded_text(stdout),
        "stderr": _bounded_text(stderr),
    }
    _write_json(output / f"{label}.receipt.json", receipt)
    (output / f"{label}.stdout.log").write_text(
        stdout, encoding="utf-8", errors="replace"
    )
    (output / f"{label}.stderr.log").write_text(
        stderr, encoding="utf-8", errors="replace"
    )
    return receipt


def _readiness(url: str, timeout_seconds: float) -> dict[str, Any]:
''',
        '''def _run_command(
    command: Sequence[str],
    *,
    root: Path,
    output: Path,
    python: Path,
    env: Mapping[str, str],
    timeout_seconds: float,
    label: str,
) -> dict[str, Any]:
    resolved = _resolve_command(
        command, root=root, output=output, python=python
    )
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
''',
        "bounded command runner",
    )
    replace_once(
        harness,
        '''    deadline = time.monotonic() + timeout_seconds
    attempts = 0
    last_error = ""
    started = time.monotonic()
    while time.monotonic() < deadline:
''',
        '''    deadline = time.monotonic() + timeout_seconds
    attempts = 0
    last_error = ""
    started = time.monotonic()
    opener = build_opener(_NoRedirectHandler())
    while time.monotonic() < deadline:
''',
        "non-redirecting readiness opener",
    )
    replace_once(
        harness,
        '''            with urlopen(
                request,
                timeout=min(
                    3.0, max(0.1, deadline - time.monotonic())
                ),
            ) as response:
''',
        '''            with opener.open(
                request,
                timeout=min(
                    3.0, max(0.1, deadline - time.monotonic())
                ),
            ) as response:
''',
        "non-redirecting readiness request",
    )
    replace_once(
        harness,
        '''        row: dict[str, Any] = {
            "path": item,
            "present": path.is_file() and not path.is_symlink(),
        }
        if row["present"]:
            row.update(
                {
                    "size_bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                }
            )
''',
        '''        candidate = output / Path(*PurePosixPath(item).parts)
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
''',
        "bounded artifact inventory",
    )
    replace_once(
        harness,
        '''    server_stdout = (output / "server.stdout.log").open(
        "w", encoding="utf-8"
    )
    server_stderr = (output / "server.stderr.log").open(
        "w", encoding="utf-8"
    )
    process: subprocess.Popen[Any] | None = None
''',
        '''    process: subprocess.Popen[Any] | None = None
    server_capture: tuple[
        _BoundedStreamCapture,
        _BoundedStreamCapture,
        tuple[threading.Thread, ...],
    ] | None = None
    server_output: dict[str, Any] = {"capture_complete": False}
''',
        "bounded server capture state",
    )
    replace_once(
        harness,
        '''        process = subprocess.Popen(
            server_command,
            cwd=root,
            env=base_env,
            stdout=server_stdout,
            stderr=server_stderr,
            text=True,
            start_new_session=(os.name != "nt"),
        )
        readiness = _readiness(
''',
        '''        process = subprocess.Popen(
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
''',
        "bounded server process",
    )
    replace_once(
        harness,
        '''    finally:
        if process is not None:
            termination = _terminate_process(process)
        server_stdout.close()
        server_stderr.close()
        _write_json(
            output / "server-termination.receipt.json", termination
        )
''',
        '''    finally:
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
        _write_json(
            output / "server-output.receipt.json", server_output
        )
        _write_json(
            output / "server-termination.receipt.json", termination
        )
''',
        "bounded server finalization",
    )
    replace_once(
        harness,
        '''    artifacts_ok = all(item["present"] for item in artifacts)
''',
        '''    artifacts_ok = all(
        item["present"] and item["within_size_limit"]
        for item in artifacts
    )
''',
        "artifact size gate",
    )
    replace_once(
        harness,
        '''        "artifacts": artifacts,
        "server_termination": termination,
''',
        '''        "artifacts": artifacts,
        "server_output": server_output,
        "server_termination": termination,
''',
        "server output receipt binding",
    )

    wrapper = Path("scripts/aura_architecture_harness.py")
    replace_once(
        wrapper,
        '''def main(argv: Iterable[str] | None = None) -> int:
    arguments = list(argv) if argv is not None else list(sys.argv[1:])
    if "runtime" in arguments:
        runtime_index = arguments.index("runtime")
''',
        '''def _runtime_command_index(arguments: list[str]) -> int | None:
    index = 0
    while index < len(arguments):
        value = arguments[index]
        if value == "--repo-root":
            index += 2
            continue
        if value.startswith("-"):
            index += 1
            continue
        return index if value == "runtime" else None
    return None


def main(argv: Iterable[str] | None = None) -> int:
    arguments = list(argv) if argv is not None else list(sys.argv[1:])
    runtime_index = _runtime_command_index(arguments)
    if runtime_index is not None:
''',
        "exact runtime command dispatch",
    )

    tests = Path("tests/test_aura_runtime_refactor_harness.py")
    replace_once(
        tests,
        '''from scripts.aura_runtime_refactor_harness import (
    PROFILE_VERSION,
''',
        '''from scripts.aura_architecture_harness import _runtime_command_index
from scripts.aura_runtime_refactor_harness import (
    MAX_OUTPUT_BYTES,
    PROFILE_VERSION,
''',
        "test imports",
    )
    replace_once(
        tests,
        '''    *,
    readiness_url: str | None = None,
) -> Path:
''',
        '''    *,
    readiness_url: str | None = None,
    verification_code: str = "print('verified')",
) -> Path:
''',
        "verification code fixture argument",
    )
    replace_once(
        tests,
        '''        "verification_commands": [
            ["{python}", "-c", "print('verified')"]
        ],
''',
        '''        "verification_commands": [
            ["{python}", "-c", verification_code]
        ],
''',
        "verification code fixture use",
    )
    replace_once(
        tests,
        '''import sys

class Handler(BaseHTTPRequestHandler):
''',
        '''import sys

print("server-output-" + "s" * 70000, flush=True)

class Handler(BaseHTTPRequestHandler):
''',
        "noisy server fixture",
    )
    replace_once(
        tests,
        '''    assert result["verification"][0]["returncode"] == 0
    assert result["artifacts"][0]["present"] is True
''',
        '''    assert result["verification"][0]["returncode"] == 0
    assert result["artifacts"][0]["present"] is True
    assert result["artifacts"][0]["within_size_limit"] is True
    assert result["server_output"]["stdout"]["truncated"] is True
    assert (output / "server.stdout.log").stat().st_size <= MAX_OUTPUT_BYTES
''',
        "bounded server assertions",
    )
    tests.write_text(
        tests.read_text(encoding="utf-8")
        + '''


def test_runtime_command_dispatch_ignores_objective_words() -> None:
    assert _runtime_command_index(["--repo-root", ".", "runtime"]) == 2
    assert _runtime_command_index(
        ["--repo-root", ".", "run", "--objective", "inspect runtime"]
    ) is None


def test_runtime_command_output_is_streamed_and_bounded(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    output = tmp_path / "evidence"
    _write_fixture(root)
    profile = _write_profile(
        root,
        _free_port(),
        verification_code=(
            "import sys;"
            "print('x' * 70000);"
            "print('y' * 70000, file=sys.stderr)"
        ),
    )
    result = run_runtime_profile(
        root,
        profile_path=profile.name,
        output_dir=output,
    )
    receipt = result["verification"][0]
    assert result["ok"] is True
    assert receipt["capture_complete"] is True
    assert receipt["stdout"]["truncated"] is True
    assert receipt["stderr"]["truncated"] is True
    assert receipt["stdout"]["total_bytes"] > MAX_OUTPUT_BYTES
    assert receipt["stderr"]["total_bytes"] > MAX_OUTPUT_BYTES
    assert (output / "verify-00.stdout.log").stat().st_size <= MAX_OUTPUT_BYTES
    assert (output / "verify-00.stderr.log").stat().st_size <= MAX_OUTPUT_BYTES
''',
        encoding="utf-8",
    )

    docs = Path("docs/AURA_RUNTIME_REFACTOR_HARNESS.md")
    replace_once(
        docs,
        "- bounded command counts, argument counts, argument sizes, timeouts, output capture, and artifact counts;\n",
        "- bounded command counts, argument counts, argument sizes, timeouts, continuously drained 64 KiB stdout/stderr tails, and artifact counts/sizes;\n",
        "bounded capture documentation",
    )
    replace_once(
        docs,
        "- loopback HTTP readiness URLs with explicit ports and no credentials;\n",
        "- literal loopback HTTP readiness URLs with explicit ports, no credentials, and redirects disabled;\n",
        "readiness redirect documentation",
    )


if __name__ == "__main__":
    main()
