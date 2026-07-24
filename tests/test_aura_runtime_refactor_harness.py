from __future__ import annotations

import json
from pathlib import Path
import socket

import pytest

from scripts.aura_architecture_harness import _runtime_command_index
from scripts.aura_runtime_refactor_harness import (
    MAX_OUTPUT_BYTES,
    PROFILE_VERSION,
    RuntimeHarnessError,
    load_runtime_profile,
    run_runtime_profile,
)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _write_profile(
    root: Path,
    port: int,
    *,
    readiness_url: str | None = None,
    verification_code: str = "print('verified')",
) -> Path:
    profile = {
        "version": PROFILE_VERSION,
        "profile_id": "fixture-runtime",
        "objective": "Prove a bounded local server and probe end to end.",
        "environment": {"create_venv": False, "requirements": []},
        "server": {
            "command": ["{python}", "server.py", str(port)],
            "readiness_url": readiness_url or f"http://127.0.0.1:{port}/ready",
            "readiness_timeout_seconds": 10,
        },
        "probe": {
            "command": ["{python}", "probe.py"],
            "timeout_seconds": 10,
            "env": {"AURA_RUNTIME_EVIDENCE_DIR": "{output}"},
            "required_artifacts": ["browser-evidence.json"],
            "success_json": "browser-evidence.json",
            "success_field": "ok",
        },
        "verification_commands": [["{python}", "-c", verification_code]],
    }
    path = root / "profile.json"
    path.write_text(json.dumps(profile), encoding="utf-8")
    return path


def _write_fixture(root: Path) -> None:
    (root / "server.py").write_text(
        """from http.server import BaseHTTPRequestHandler, HTTPServer
import sys

print("server-output-" + "s" * 70000, flush=True)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"ready"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass

HTTPServer(("127.0.0.1", int(sys.argv[1])), Handler).serve_forever()
""",
        encoding="utf-8",
    )
    (root / "probe.py").write_text(
        """import json
import os
from pathlib import Path

out = Path(os.environ["AURA_RUNTIME_EVIDENCE_DIR"])
out.mkdir(parents=True, exist_ok=True)
(out / "browser-evidence.json").write_text(
    json.dumps({"ok": True, "pageErrors": []}),
    encoding="utf-8",
)
""",
        encoding="utf-8",
    )


def test_profile_rejects_non_loopback_readiness(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    profile = _write_profile(
        tmp_path,
        _free_port(),
        readiness_url="http://example.com:8080/ready",
    )
    with pytest.raises(RuntimeHarnessError, match="loopback"):
        load_runtime_profile(tmp_path, profile.name)


def test_profile_rejects_repository_escape(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    outside = tmp_path.parent / "outside-profile.json"
    outside.write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeHarnessError, match="escapes"):
        load_runtime_profile(tmp_path, "../outside-profile.json")


@pytest.mark.parametrize("value", ["false", "true", 0, 1, [], {}])
def test_profile_rejects_non_boolean_create_venv(tmp_path: Path, value: object) -> None:
    _write_fixture(tmp_path)
    profile = _write_profile(tmp_path, _free_port())
    payload = json.loads(profile.read_text(encoding="utf-8"))
    payload["environment"]["create_venv"] = value
    profile.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(
        RuntimeHarnessError,
        match=r"environment\.create_venv must be a boolean",
    ):
        load_runtime_profile(tmp_path, profile.name)


def test_profile_defaults_create_venv_only_when_absent(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    profile = _write_profile(tmp_path, _free_port())
    payload = json.loads(profile.read_text(encoding="utf-8"))
    del payload["environment"]["create_venv"]
    profile.write_text(json.dumps(payload), encoding="utf-8")
    assert load_runtime_profile(tmp_path, profile.name)["environment"]["create_venv"] is True


def test_runtime_profile_starts_probes_verifies_and_stops(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    output = tmp_path / "evidence"
    _write_fixture(root)
    profile = _write_profile(root, _free_port())
    result = run_runtime_profile(
        root,
        profile_path=profile.name,
        output_dir=output,
    )
    assert result["ok"] is True
    assert result["cycle_state"] == "RUNTIME_VERIFIED"
    assert result["repository_unchanged"] is True
    assert result["readiness"]["ok"] is True
    assert result["probe"]["returncode"] == 0
    assert result["verification"][0]["returncode"] == 0
    assert result["artifacts"][0]["present"] is True
    assert result["artifacts"][0]["within_size_limit"] is True
    assert result["server_output"]["stdout"]["truncated"] is True
    assert result["server_capture_complete"] is True
    assert result["command_capture_complete"] is True
    assert (output / "server.stdout.log").stat().st_size <= MAX_OUTPUT_BYTES
    assert result["production_mutation"] is False
    assert result["automatic_fix"] is False
    assert result["automatic_merge"] is False
    assert result["human_review_required"] is True
    assert len(result["run_digest"]) == 64
    assert Path(result["receipt_path"]).is_file()


def test_runtime_profile_binds_failed_baseline_to_repair(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    output = tmp_path / "evidence"
    _write_fixture(root)
    profile = _write_profile(root, _free_port())
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps(
            {
                "version": "AURA_RUNTIME_REFACTOR_HARNESS_V1",
                "profile_id": "fixture-runtime",
                "ok": False,
                "run_digest": "a" * 64,
            }
        ),
        encoding="utf-8",
    )
    result = run_runtime_profile(
        root,
        profile_path=profile.name,
        output_dir=output,
        baseline_receipt=baseline,
    )
    assert result["ok"] is True
    assert result["cycle_state"] == "REPAIRED_AND_VERIFIED"
    assert result["baseline"]["run_digest"] == "a" * 64


def test_runtime_command_dispatch_ignores_objective_words() -> None:
    assert _runtime_command_index(["--repo-root", ".", "runtime"]) == 2
    assert _runtime_command_index(["--repo-root", ".", "run", "--objective", "inspect runtime"]) is None


def test_runtime_command_output_is_streamed_and_bounded(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    output = tmp_path / "evidence"
    _write_fixture(root)
    profile = _write_profile(
        root,
        _free_port(),
        verification_code=("import sys;print('x' * 70000);print('y' * 70000, file=sys.stderr)"),
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
