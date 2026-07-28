from __future__ import annotations

import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from aura_bilateral_intent_compiler import (
    VERSION as CONFIRMATION_PACKET_VERSION,
    bilateral_compiler_capabilities,
)
from aura_event_contracts import stable_digest
from aura_intent_refinement import IntentConfirmationReceipt, IntentRefinementSession
from aura_unified_memory_continuity import (
    AuthorityEnvelope,
    IntentPacket,
    SemanticDefinition,
    SemanticLedger,
)
from scripts.aura_architecture_harness import _runtime_profile_version
from scripts.aura_runtime_profile_v2_adapter import (
    NO_POST_CONFIRMATION_REVISION,
    PROFILE_VERSION,
    U7_INTENT_REVISION_OWNER,
    U7_REPROOF_OWNER,
    BilateralRuntimeProfileError,
    _json_digest,
    _matches,
    load_runtime_profile_v2,
    run_runtime_profile_v2,
)

POSITIVE_REQUIREMENT = "The fixture runtime succeeds through the canonical V1 path."
NEGATIVE_REQUIREMENT = "Do not grant automatic merge or mutate the source checkout."
ALLOWED_PATHS = sorted(
    [
        ".aura/waboose_requests/bilateral.json",
        "aura_coding_waboose_cli.py",
        "probe.py",
        "profile-v1.json",
        "profile-v2.json",
        "server.py",
    ]
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


def _source_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _write_fixture(
    root: Path,
    *,
    positive_expected: bool = True,
    waboose_overwrite_trace: bool = False,
) -> Path:
    port = _free_port()
    (root / "server.py").write_text(
        """from http.server import BaseHTTPRequestHandler, HTTPServer
import sys
import time

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"ready"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *_):
        pass

last_error = None
for _ in range(100):
    try:
        server = HTTPServer(("127.0.0.1", int(sys.argv[1])), Handler)
    except OSError as error:
        last_error = error
        time.sleep(0.05)
    else:
        server.serve_forever()
raise last_error
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
    overwrite_trace = (
        """
output = state.parent
(output / "browser-evidence.json").write_text(
    json.dumps({"ok": False, "automaticMerge": True}),
    encoding="utf-8",
)
"""
        if waboose_overwrite_trace
        else ""
    )
    (root / "aura_coding_waboose_cli.py").write_text(
        """import json
import sys
from pathlib import Path

state = Path(sys.argv[sys.argv.index("--state-file") + 1])
state.write_text(json.dumps({"ok": True}), encoding="utf-8")
"""
        + overwrite_trace
        + """
print("bilateral request verified")
""",
        encoding="utf-8",
    )
    request_path = root / ".aura" / "waboose_requests" / "bilateral.json"
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text('{"version":"FIXTURE_WABOOSE_REQUEST_V1"}', encoding="utf-8")
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

    assertion_ids = [
        "positive-ok",
        "bilateral-waboose-ok",
        "negative-no-merge",
        "preserve-source",
        "fault-explicit",
        "termination-terminal",
    ]
    v2 = {
        "version": PROFILE_VERSION,
        "profile_id": "fixture-runtime-v2",
        "objective": "Prove positive, negative, preservation, and fault behavior.",
        "runtime_candidate_id": "fixture-candidate-v2",
        "base_profile": "profile-v1.json",
        "bilateral_waboose_request": ".aura/waboose_requests/bilateral.json",
        "intent_contract": {
            "confirmation_packet_version": CONFIRMATION_PACKET_VERSION,
            "intent_revision_status": NO_POST_CONFIRMATION_REVISION,
        },
        "allowed_paths": ALLOWED_PATHS,
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
            },
            {
                "assertion_id": "bilateral-waboose-ok",
                "artifact": "verify-bilateral-waboose.receipt.json",
                "json_path": "returncode",
                "operator": "equals",
                "expected": 0,
            },
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
            },
            {
                "assertion_id": "termination-terminal",
                "artifact": "server-termination.receipt.json",
                "json_path": "returncode",
                "operator": "not_equals",
                "expected": None,
            },
        ],
        "requirement_bindings": {
            "positive_assertions": [
                {
                    "requirement_digest": _json_digest(POSITIVE_REQUIREMENT),
                    "assertion_ids": ["positive-ok", "bilateral-waboose-ok"],
                }
            ],
            "negative_assertions": [
                {
                    "requirement_digest": _json_digest(NEGATIVE_REQUIREMENT),
                    "assertion_ids": ["negative-no-merge"],
                }
            ],
            "preservation_assertions": [
                {
                    "requirement_digest": _json_digest(NEGATIVE_REQUIREMENT),
                    "assertion_ids": ["preserve-source"],
                }
            ],
            "fault_injections": [
                {
                    "requirement_digest": _json_digest(NEGATIVE_REQUIREMENT),
                    "assertion_ids": ["fault-explicit", "termination-terminal"],
                }
            ],
        },
        "required_trace_artifacts": [
            "browser-evidence.json",
            "runtime_harness_receipt.json",
            "server-termination.receipt.json",
            "verify-bilateral-waboose.receipt.json",
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
            "source_sha256": _source_sha256(root / "probe.py"),
        },
    }
    path = root / "profile-v2.json"
    path.write_text(json.dumps(v2), encoding="utf-8")
    return path


def _write_confirmation_packet(
    root: Path,
    profile: Path,
    target: Path,
    *,
    repository_head: str | None = None,
    source_tree: str | None = None,
    positive_requirements: list[str] | None = None,
    negative_requirements: list[str] | None = None,
) -> Path:
    positives = positive_requirements or [POSITIVE_REQUIREMENT]
    negatives = negative_requirements or [NEGATIVE_REQUIREMENT]
    authority = AuthorityEnvelope(inspect=True)
    intent = IntentPacket.create(
        objective=positives[0],
        purpose="Exercise the canonical fixture confirmation path.",
        user_meaning=f"{positives[0]} {negatives[0]}",
        mode="PROPOSE",
        arena="CONSTRUCTION",
        constraints=(),
        prohibitions=negatives,
        authority=authority,
        acceptance_criteria=positives,
        required_evidence=("current canonical confirmation",),
        risk_class="BOUNDED_FIXTURE",
        cost_budget="BOUNDED",
        context_budget="MINIMUM_SUFFICIENT",
        privacy_class="PROJECT",
        freshness_requirement="CURRENT_HEAD",
        output_contract="evidence-only fixture proof",
    )
    ledger = SemanticLedger.create(
        intent_digest=intent.intent_digest,
        definitions=(
            SemanticDefinition(
                term="fixture confirmation",
                means=("the exact positive and negative fixture requirements",),
                does_not_mean=("patch or merge authority",),
                source_refs=("fixture:test",),
            ),
        ),
    )
    guardrails = [
        {
            "guardrail_id": "guardrail-fixture-no-self-authorization",
            "statement": "Do not self-authorize fixture execution.",
            "human_disposition": "CONFIRMED",
        }
    ]
    source_request_digest = stable_digest(intent.user_meaning)
    teach_back_digest = "a" * 64
    head = repository_head or _git(root, "rev-parse", "HEAD")
    tree = source_tree or _git(root, "rev-parse", "HEAD^{tree}")
    session = IntentRefinementSession.create(
        repository_head=head,
        working_tree_digest=tree,
        arena="CONSTRUCTION",
        source_request=intent.user_meaning,
        created_at=1.0,
        expires_at=4_102_444_800.0,
    )
    session = session.transition(
        "ANALYZED",
        positive_requirements=positives,
        negative_requirements=negatives,
        guardrails=guardrails,
        unresolved_ambiguities=(),
        now=1.0,
    )
    teach_back = {
        "teach_back_digest": teach_back_digest,
        "required_human_decisions": [],
    }
    session = session.transition(
        "TEACH_BACK_PENDING",
        teach_back=teach_back,
        now=1.0,
    )
    session = session.transition(
        "HUMAN_CONFIRMED",
        confirmation_status="CONFIRMED",
        now=1.0,
    )
    receipt = IntentConfirmationReceipt.create(
        session_id=session.session_id,
        repository_head=head,
        source_tree_digest=tree,
        working_tree_clean_receipt=stable_digest({"clean": True}),
        source_request_digest=source_request_digest,
        positive_requirements=positives,
        negative_requirements=negatives,
        semantic_ledger_digest=ledger.ledger_digest,
        guardrails=guardrails,
        authority=authority.to_dict(),
        teach_back=type(
            "FixtureTeachBack",
            (),
            {"teach_back_digest": teach_back_digest},
        )(),
        allowed_paths=ALLOWED_PATHS,
        runtime_profile_digest=_sha256(profile),
        unified_execution_binding_ref="aura://fixture/execution-binding",
        human_reviewer="fixture-human",
        human_disposition="CONFIRMED",
        confirmed_at=1.0,
        expires_at=4_102_444_800.0,
        expires_or_stales_on=(
            "repository head changes",
            "source tree digest changes",
            "requirements change",
        ),
    )
    session = session.transition(
        "COMPILED",
        confirmation_receipt=receipt,
        confirmation_evidence={
            "source_tree_digest": tree,
            "semantic_ledger_digest": ledger.ledger_digest,
            "authority": authority.to_dict(),
            "allowed_paths": ALLOWED_PATHS,
            "runtime_profile_digest": _sha256(profile),
        },
        now=1.0,
    )
    u7_payload = {
        "confirmation_digest": receipt.confirmation_id,
        "negative_requirements_digest": receipt.negative_requirements_digest,
        "guardrail_set_digest": receipt.guardrail_set_digest,
        "intent_revision_status": NO_POST_CONFIRMATION_REVISION,
        "incident_replay_status": "NOT_OBSERVED_NO_EXECUTION_INCIDENT",
        "observed_guardrail_violation_refs": [],
        "proposal_only": True,
        "current_reproof_required_before_learning": True,
        "current_reproof_owner": U7_REPROOF_OWNER,
        "intent_revision_owner": U7_INTENT_REVISION_OWNER,
    }
    packet_authority = bilateral_compiler_capabilities()
    packet_authority.pop("version")
    packet = {
        "version": CONFIRMATION_PACKET_VERSION,
        "intent_packet": intent.to_dict(),
        "semantic_ledger": ledger.to_dict(),
        "confirmation_receipt": receipt.to_dict(),
        "refinement_session": session.to_dict(),
        "guardrails": guardrails,
        "u7_references": {
            **u7_payload,
            "u7_binding_digest": stable_digest(u7_payload),
        },
        "authority": packet_authority,
    }
    target.write_text(json.dumps(packet), encoding="utf-8")
    return target


def _repo(
    tmp_path: Path,
    **fixture_kwargs: object,
) -> tuple[Path, Path, Path]:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "aura-tests@example.invalid")
    _git(root, "config", "user.name", "Aura Tests")
    profile = _write_fixture(root, **fixture_kwargs)
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture")
    confirmation = _write_confirmation_packet(
        root,
        profile,
        tmp_path / "canonical-confirmation.json",
    )
    return root, profile, confirmation


def test_v2_profile_loads_without_reinterpreting_v1(tmp_path: Path) -> None:
    root, profile, _ = _repo(tmp_path)
    loaded = load_runtime_profile_v2(root, profile.name)
    assert loaded["version"] == PROFILE_VERSION
    assert loaded["base_profile_id"] == "fixture-runtime-v1"
    assert loaded["repair_policy"]["max_attempts"] == 1


def test_architecture_harness_routes_all_explicit_v2_option_forms(
    tmp_path: Path,
) -> None:
    root, profile, _ = _repo(tmp_path)
    assert _runtime_profile_version(["--repo-root", str(root), "--profile", profile.name]) == PROFILE_VERSION
    assert _runtime_profile_version([f"--repo-root={root}", f"--profile={profile.name}"]) == PROFILE_VERSION
    assert (
        _runtime_profile_version(["--repo-root", str(root), "--profile", "profile-v1.json"])
        == "AURA_RUNTIME_PROFILE_V1"
    )


def test_v2_runtime_binds_canonical_confirmation_and_one_trace_snapshot(
    tmp_path: Path,
) -> None:
    root, profile, confirmation = _repo(tmp_path)
    result = run_runtime_profile_v2(
        root,
        profile_path=profile.name,
        confirmation_packet=confirmation,
        output_dir=tmp_path / "evidence",
    )
    assert result["ok"] is True
    assert result["repository_identity_unchanged"] is True
    assert result["resolved_expected_repository_head"] == _git(root, "rev-parse", "HEAD")
    assert result["resolved_expected_source_tree"] == _git(root, "rev-parse", "HEAD^{tree}")
    assert result["positive_requirements_proved"] == ["positive-ok", "bilateral-waboose-ok"]
    assert result["negative_requirements_proved"] == ["negative-no-merge"]
    assert result["preservation_requirements_proved"] == ["preserve-source"]
    assert result["fault_behaviors_proved"] == ["fault-explicit", "termination-terminal"]
    assert result["requirements_unproved"] == []
    assert result["automatic_merge"] is False
    assert result["physical_work_authority"] is False
    inventory = {item["path"]: item["sha256"] for item in result["required_trace_artifacts"]}
    for group in (
        "positive_assertions",
        "negative_assertions",
        "preservation_assertions",
        "fault_injections",
    ):
        for assertion in result[group]:
            assert assertion["artifact_sha256"] == inventory[assertion["artifact"]]
    assert Path(result["proof_path"]).is_file()


def test_v2_profile_rejects_partial_intent_contract(tmp_path: Path) -> None:
    root, profile, _ = _repo(tmp_path)
    payload = json.loads(profile.read_text(encoding="utf-8"))
    del payload["intent_contract"]["confirmation_packet_version"]
    profile.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BilateralRuntimeProfileError, match="complete and exact"):
        load_runtime_profile_v2(root, profile.name)


def test_v2_profile_rejects_non_array_and_unbounded_inputs(
    tmp_path: Path,
) -> None:
    root, profile, _ = _repo(tmp_path)
    payload = json.loads(profile.read_text(encoding="utf-8"))
    payload["allowed_paths"] = "probe.py"
    profile.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BilateralRuntimeProfileError, match="allowed_paths"):
        load_runtime_profile_v2(root, profile.name)

    profile = _write_fixture(root)
    payload = json.loads(profile.read_text(encoding="utf-8"))
    payload["scenarios"][0]["required_assertion_ids"] = "positive-ok"
    profile.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BilateralRuntimeProfileError, match="bounded array"):
        load_runtime_profile_v2(root, profile.name)


def test_v2_profile_binds_verifier_to_probe_command(tmp_path: Path) -> None:
    root, profile, _ = _repo(tmp_path)
    payload = json.loads(profile.read_text(encoding="utf-8"))
    payload["independent_verifier"]["source_path"] = "server.py"
    payload["independent_verifier"]["source_sha256"] = _source_sha256(root / "server.py")
    profile.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BilateralRuntimeProfileError, match="direct entry point"):
        load_runtime_profile_v2(root, profile.name)


def test_v2_profile_rejects_wrapper_that_merely_mentions_verifier(tmp_path: Path) -> None:
    root, profile, _ = _repo(tmp_path)
    (root / "wrapper.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
    v1_path = root / "profile-v1.json"
    payload = json.loads(v1_path.read_text(encoding="utf-8"))
    payload["probe"]["command"] = ["{python}", "wrapper.py", "probe.py"]
    v1_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BilateralRuntimeProfileError, match="direct entry point"):
        load_runtime_profile_v2(root, profile.name)


def test_v2_profile_cannot_grant_itself_repair_authority(
    tmp_path: Path,
) -> None:
    root, profile, _ = _repo(tmp_path)
    payload = json.loads(profile.read_text(encoding="utf-8"))
    payload["repair_policy"]["automatic_fix"] = True
    profile.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(
        BilateralRuntimeProfileError,
        match="cannot grant automatic_fix",
    ):
        load_runtime_profile_v2(root, profile.name)


def test_v2_runtime_rejects_stale_canonical_confirmation(
    tmp_path: Path,
) -> None:
    root, profile, _ = _repo(tmp_path)
    confirmation = _write_confirmation_packet(
        root,
        profile,
        tmp_path / "stale-confirmation.json",
        repository_head="f" * 40,
    )
    with pytest.raises(BilateralRuntimeProfileError, match="stale, expired"):
        run_runtime_profile_v2(
            root,
            profile_path=profile.name,
            confirmation_packet=confirmation,
            output_dir=tmp_path / "evidence",
        )


def test_v2_runtime_rejects_dirty_execution_even_when_requested(
    tmp_path: Path,
) -> None:
    root, profile, confirmation = _repo(tmp_path)
    (root / "probe.py").write_text("# dirty\n", encoding="utf-8")
    with pytest.raises(BilateralRuntimeProfileError, match="cannot bind dirty"):
        run_runtime_profile_v2(
            root,
            profile_path=profile.name,
            confirmation_packet=confirmation,
            output_dir=tmp_path / "evidence",
            allow_dirty=True,
        )


def test_v2_runtime_rejects_reused_output_before_reading_stale_evidence(
    tmp_path: Path,
) -> None:
    root, profile, confirmation = _repo(tmp_path)
    output = tmp_path / "evidence"
    output.mkdir()
    (output / "browser-evidence.json").write_text(
        '{"ok": true}',
        encoding="utf-8",
    )
    with pytest.raises(BilateralRuntimeProfileError, match="fresh empty"):
        run_runtime_profile_v2(
            root,
            profile_path=profile.name,
            confirmation_packet=confirmation,
            output_dir=output,
        )


def test_v2_runtime_rejects_incomplete_confirmed_requirement_coverage(
    tmp_path: Path,
) -> None:
    root, profile, confirmation = _repo(tmp_path)
    payload = json.loads(profile.read_text(encoding="utf-8"))
    payload["requirement_bindings"]["positive_assertions"][0]["requirement_digest"] = "f" * 64
    profile.write_text(json.dumps(payload), encoding="utf-8")
    _git(root, "add", "profile-v2.json")
    _git(root, "commit", "-qm", "change requirement binding")
    confirmation = _write_confirmation_packet(
        root,
        profile,
        confirmation,
    )
    with pytest.raises(BilateralRuntimeProfileError, match="exact confirmed positive"):
        run_runtime_profile_v2(
            root,
            profile_path=profile.name,
            confirmation_packet=confirmation,
            output_dir=tmp_path / "evidence",
        )


def test_v2_runtime_reports_unproved_assertion_without_claiming_success(
    tmp_path: Path,
) -> None:
    root, profile, confirmation = _repo(tmp_path, positive_expected=False)
    result = run_runtime_profile_v2(
        root,
        profile_path=profile.name,
        confirmation_packet=confirmation,
        output_dir=tmp_path / "evidence",
    )
    assert result["ok"] is False
    assert result["requirements_unproved"] == ["positive-ok"]
    assert result["residual_risks"]
    assert result["automatic_fix"] is False


def test_v2_runtime_rejects_replayed_confirmation_for_fresh_output(
    tmp_path: Path,
) -> None:
    root, profile, confirmation = _repo(tmp_path)
    first = run_runtime_profile_v2(
        root,
        profile_path=profile.name,
        confirmation_packet=confirmation,
        output_dir=tmp_path / "evidence-first",
    )
    assert first["ok"] is True
    with pytest.raises(BilateralRuntimeProfileError, match="already been consumed"):
        run_runtime_profile_v2(
            root,
            profile_path=profile.name,
            confirmation_packet=confirmation,
            output_dir=tmp_path / "evidence-second",
        )


def test_v2_runtime_accepts_a_linked_git_worktree(tmp_path: Path) -> None:
    root, profile, confirmation = _repo(tmp_path)
    linked = tmp_path / "linked-worktree"
    _git(root, "worktree", "add", "--detach", "-q", str(linked), "HEAD")
    result = run_runtime_profile_v2(
        linked,
        profile_path=profile.name,
        confirmation_packet=confirmation,
        output_dir=tmp_path / "linked-evidence",
    )
    assert result["ok"] is True


def test_v2_profile_rejects_unreferenced_assertions(tmp_path: Path) -> None:
    root, profile, _ = _repo(tmp_path)
    payload = json.loads(profile.read_text(encoding="utf-8"))
    payload["scenarios"][0]["required_assertion_ids"].remove("termination-terminal")
    profile.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BilateralRuntimeProfileError, match="scenarios leave assertions unreferenced"):
        load_runtime_profile_v2(root, profile.name)


def test_v2_profile_rejects_assertion_artifact_outside_admitted_traces(
    tmp_path: Path,
) -> None:
    root, profile, _ = _repo(tmp_path)
    payload = json.loads(profile.read_text(encoding="utf-8"))
    payload["positive_assertions"][0]["artifact"] = "unlisted-evidence.json"
    profile.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BilateralRuntimeProfileError, match="artifact is not an admitted trace"):
        load_runtime_profile_v2(root, profile.name)


def test_v2_json_equality_keeps_booleans_distinct_from_numbers() -> None:
    assert _matches(True, "equals", True) is True
    assert _matches(True, "equals", 1) is False
    assert _matches(False, "equals", 0) is False
    assert _matches(True, "not_equals", 1) is True


@pytest.mark.parametrize(
    ("replacement", "message"),
    [
        (
            '"version": "AURA_RUNTIME_PROFILE_V2", "version": "AURA_RUNTIME_PROFILE_V2"',
            "duplicate JSON object key",
        ),
        ('"max_attempts": NaN', "non-finite JSON constant"),
    ],
)
def test_v2_profile_rejects_noncanonical_json(
    tmp_path: Path,
    replacement: str,
    message: str,
) -> None:
    root, profile, _ = _repo(tmp_path)
    body = profile.read_text(encoding="utf-8")
    if replacement.startswith('"version"'):
        body = body.replace('"version": "AURA_RUNTIME_PROFILE_V2"', replacement, 1)
    else:
        body = body.replace('"max_attempts": 1', replacement, 1)
    profile.write_text(body, encoding="utf-8")
    with pytest.raises(BilateralRuntimeProfileError, match=message):
        load_runtime_profile_v2(root, profile.name)


def test_v2_runtime_rejects_confirmation_replay_from_renamed_copy(
    tmp_path: Path,
) -> None:
    root, profile, confirmation = _repo(tmp_path)
    first = run_runtime_profile_v2(
        root,
        profile_path=profile.name,
        confirmation_packet=confirmation,
        output_dir=tmp_path / "evidence-first",
    )
    assert first["ok"] is True
    copied_confirmation = tmp_path / "renamed-confirmation-copy.json"
    copied_confirmation.write_text(
        json.dumps(
            json.loads(confirmation.read_text(encoding="utf-8")),
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    with pytest.raises(BilateralRuntimeProfileError, match="already been consumed"):
        run_runtime_profile_v2(
            root,
            profile_path=profile.name,
            confirmation_packet=copied_confirmation,
            output_dir=tmp_path / "evidence-second",
        )


def test_v2_runtime_rejects_partial_or_rebound_u7_references(tmp_path: Path) -> None:
    root, profile, confirmation = _repo(tmp_path)
    packet = json.loads(confirmation.read_text(encoding="utf-8"))
    packet["u7_references"].pop("guardrail_set_digest")
    confirmation.write_text(json.dumps(packet), encoding="utf-8")
    with pytest.raises(BilateralRuntimeProfileError, match="U7 references"):
        run_runtime_profile_v2(
            root,
            profile_path=profile.name,
            confirmation_packet=confirmation,
            output_dir=tmp_path / "evidence-partial-u7",
        )

    confirmation = _write_confirmation_packet(root, profile, confirmation)
    packet = json.loads(confirmation.read_text(encoding="utf-8"))
    packet["u7_references"]["u7_binding_digest"] = "f" * 64
    confirmation.write_text(json.dumps(packet), encoding="utf-8")
    with pytest.raises(BilateralRuntimeProfileError, match="U7 references"):
        run_runtime_profile_v2(
            root,
            profile_path=profile.name,
            confirmation_packet=confirmation,
            output_dir=tmp_path / "evidence-rebound-u7",
        )


def test_v2_runtime_rejects_noncanonical_authority_projection(tmp_path: Path) -> None:
    root, profile, confirmation = _repo(tmp_path)
    packet = json.loads(confirmation.read_text(encoding="utf-8"))
    packet["authority"]["automatic_commit"] = True
    confirmation.write_text(json.dumps(packet), encoding="utf-8")
    with pytest.raises(BilateralRuntimeProfileError, match="canonical inspect-only"):
        run_runtime_profile_v2(
            root,
            profile_path=profile.name,
            confirmation_packet=confirmation,
            output_dir=tmp_path / "evidence-authority",
        )


def test_v2_runtime_rejects_waboose_overwrite_of_v1_trace(
    tmp_path: Path,
) -> None:
    root, profile, confirmation = _repo(tmp_path, waboose_overwrite_trace=True)
    with pytest.raises(BilateralRuntimeProfileError, match="V1 runtime traces changed after"):
        run_runtime_profile_v2(
            root,
            profile_path=profile.name,
            confirmation_packet=confirmation,
            output_dir=tmp_path / "evidence",
        )
