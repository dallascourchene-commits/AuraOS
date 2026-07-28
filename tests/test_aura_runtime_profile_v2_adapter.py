from __future__ import annotations

import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from scripts.aura_architecture_harness import _runtime_profile_version
from scripts.aura_runtime_profile_v2_adapter import (
    CURRENT_HEAD,
    CURRENT_TREE,
    PROFILE_VERSION,
    BilateralRuntimeProfileError,
    _json_digest,
    load_runtime_profile_v2,
    run_runtime_profile_v2,
)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_fixture(root: Path, *, expected_head: str = CURRENT_HEAD, positive_expected: bool = True) -> Path:
    port = _free_port()
    (root / "server.py").write_text(
        """from http.server import BaseHTTPRequestHandler, HTTPServer
import sys

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

output = Path(os.environ["AURA_RUNTIME_EVIDENCE_DIR"])
output.mkdir(parents=True, exist_ok=True)
(output / "browser-evidence.json").write_text(
    json.dumps({
        "ok": True,
        "automaticMerge": False,
        "sourceGeometryUnchanged": True,
        "fault": {"explicit": True},
    }),
    encoding="utf-8",
)
""",
        encoding="utf-8",
    )
    v1 = {
        "version": "AURA_RUNTIME_PROFILE_V1",
        "profile_id": "fixture-runtime-v1",
        "objective": "Run a bounded fixture through the canonical V1 harness.",
        "environment": {"create_venv": False, "requirements": []},
        "server": {
            "command": ["{python}", "server.py", str(port)],
            "readiness_url": f"http://127.0.0.1:{port}/ready",
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
        "verification_commands": [["{python}", "-c", "print('verified')"]],
    }
    (root / "profile-v1.json").write_text(json.dumps(v1), encoding="utf-8")

    allowed_paths = sorted(["probe.py", "profile-v1.json", "profile-v2.json", "server.py"])
    guardrail_ids = sorted(
        [
            "construction_no_authority_inference",
            "runtime_no_source_mutation",
            "runtime_no_self_authorization",
        ]
    )
    assertion_ids = ["positive-ok", "negative-no-merge", "preserve-source", "fault-explicit"]
    v2 = {
        "version": PROFILE_VERSION,
        "profile_id": "fixture-runtime-v2",
        "objective": "Prove positive, negative, preservation, and fault behavior.",
        "runtime_candidate_id": "fixture-candidate-v2",
        "base_profile": "profile-v1.json",
        "intent_contract": {
            "intent_digest": "1" * 64,
            "semantic_ledger_digest": "2" * 64,
            "confirmation_digest": "3" * 64,
            "guardrail_set_digest": _json_digest(guardrail_ids),
            "intent_revision_id": "intent-revision-1",
            "expected_repository_head": expected_head,
            "expected_source_tree": CURRENT_TREE,
            "allowed_path_set_digest": _json_digest(allowed_paths),
        },
        "allowed_paths": allowed_paths,
        "guardrail_ids": guardrail_ids,
        "scenarios": [
            {
                "scenario_id": "fixture-runtime-proof",
                "description": "Exercise all four proof classes.",
                "required_assertion_ids": assertion_ids,
            }
        ],
        "positive_assertions": [
            {
                "assertion_id": "positive-ok",
                "artifact": "browser-evidence.json",
                "json_path": "ok",
                "operator": "equals",
                "expected": positive_expected,
            }
        ],
        "negative_assertions": [
            {
                "assertion_id": "negative-no-merge",
                "artifact": "browser-evidence.json",
                "json_path": "automaticMerge",
                "operator": "falsy",
            }
        ],
        "preservation_assertions": [
            {
                "assertion_id": "preserve-source",
                "artifact": "runtime_harness_receipt.json",
                "json_path": "repository_unchanged",
                "operator": "truthy",
            }
        ],
        "fault_injections": [
            {
                "assertion_id": "fault-explicit",
                "artifact": "browser-evidence.json",
                "json_path": "fault.explicit",
                "operator": "truthy",
            }
        ],
        "required_trace_artifacts": [
            "browser-evidence.json",
            "runtime_harness_receipt.json",
            "server-termination.receipt.json",
        ],
        "repair_policy": {
            "automatic_fix": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_pull_request": False,
            "automatic_merge": False,
            "production_mutation": False,
            "professional_authority": False,
            "physical_work_authority": False,
            "learning_promotion": False,
            "max_attempts": 1,
            "retry_failed_assertions": False,
            "human_review_required": True,
        },
        "independent_verifier": {
            "verifier_id": "fixture-browser-probe",
            "source_path": "probe.py",
            "source_sha256": _sha256(root / "probe.py"),
        },
    }
    path = root / "profile-v2.json"
    path.write_text(json.dumps(v2), encoding="utf-8")
    return path


def _repo(tmp_path: Path, **fixture_kwargs) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "aura-tests@example.invalid")
    _git(root, "config", "user.name", "Aura Tests")
    profile = _write_fixture(root, **fixture_kwargs)
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture")
    return root, profile


def test_v2_profile_loads_without_reinterpreting_v1(tmp_path: Path) -> None:
    root, profile = _repo(tmp_path)
    loaded = load_runtime_profile_v2(root, profile.name)
    assert loaded["version"] == PROFILE_VERSION
    assert loaded["base_profile_id"] == "fixture-runtime-v1"
    assert loaded["repair_policy"]["max_attempts"] == 1


def test_architecture_harness_routes_only_explicit_v2_profiles(tmp_path: Path) -> None:
    root, profile = _repo(tmp_path)
    assert _runtime_profile_version(["--repo-root", str(root), "--profile", profile.name]) == PROFILE_VERSION
    assert _runtime_profile_version(["--repo-root", str(root), "--profile", "profile-v1.json"]) == "AURA_RUNTIME_PROFILE_V1"


def test_v2_runtime_binds_exact_identity_and_all_proof_classes(tmp_path: Path) -> None:
    root, profile = _repo(tmp_path)
    result = run_runtime_profile_v2(
        root,
        profile_path=profile.name,
        output_dir=tmp_path / "evidence",
    )
    assert result["ok"] is True
    assert result["repository_identity_unchanged"] is True
    assert result["resolved_expected_repository_head"] == _git(root, "rev-parse", "HEAD")
    assert result["resolved_expected_source_tree"] == _git(root, "rev-parse", "HEAD^{tree}")
    assert result["positive_requirements_proved"] == ["positive-ok"]
    assert result["negative_requirements_proved"] == ["negative-no-merge"]
    assert result["preservation_requirements_proved"] == ["preserve-source"]
    assert result["fault_behaviors_proved"] == ["fault-explicit"]
    assert result["requirements_unproved"] == []
    assert result["automatic_merge"] is False
    assert result["physical_work_authority"] is False
    assert Path(result["proof_path"]).is_file()


def test_v2_profile_rejects_partial_intent_identity(tmp_path: Path) -> None:
    root, profile = _repo(tmp_path)
    payload = json.loads(profile.read_text(encoding="utf-8"))
    del payload["intent_contract"]["confirmation_digest"]
    profile.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BilateralRuntimeProfileError, match="complete and exact"):
        load_runtime_profile_v2(root, profile.name)


def test_v2_profile_rejects_allowed_path_digest_mismatch(tmp_path: Path) -> None:
    root, profile = _repo(tmp_path)
    payload = json.loads(profile.read_text(encoding="utf-8"))
    payload["intent_contract"]["allowed_path_set_digest"] = "f" * 64
    profile.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BilateralRuntimeProfileError, match="allowed_path_set_digest"):
        load_runtime_profile_v2(root, profile.name)


def test_v2_profile_cannot_grant_itself_repair_authority(tmp_path: Path) -> None:
    root, profile = _repo(tmp_path)
    payload = json.loads(profile.read_text(encoding="utf-8"))
    payload["repair_policy"]["automatic_fix"] = True
    profile.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BilateralRuntimeProfileError, match="cannot grant automatic_fix"):
        load_runtime_profile_v2(root, profile.name)


def test_v2_runtime_rejects_exact_head_mismatch(tmp_path: Path) -> None:
    root, profile = _repo(tmp_path, expected_head="f" * 40)
    with pytest.raises(BilateralRuntimeProfileError, match="expected repository head mismatch"):
        run_runtime_profile_v2(
            root,
            profile_path=profile.name,
            output_dir=tmp_path / "evidence",
        )


def test_v2_runtime_reports_unproved_assertion_without_claiming_success(tmp_path: Path) -> None:
    root, profile = _repo(tmp_path, positive_expected=False)
    result = run_runtime_profile_v2(
        root,
        profile_path=profile.name,
        output_dir=tmp_path / "evidence",
    )
    assert result["ok"] is False
    assert result["requirements_unproved"] == ["positive-ok"]
    assert result["residual_risks"]
    assert result["automatic_fix"] is False
