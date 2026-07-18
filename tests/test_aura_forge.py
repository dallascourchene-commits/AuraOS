from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import aura_forge as aura_forge_module
from aura_forge import (
    FORGE_CONTRACT_VERSION,
    AuraForgeRuntime,
    ForgeRunRequest,
    forge_contract_digest,
    validate_forge_contract,
)


class FakeBridge:
    def __init__(self) -> None:
        self.prepare_calls: list[dict[str, Any]] = []
        self.context_calls: list[dict[str, Any]] = []
        self.blocked = False
        self.digest_ok = True
        self.context_target = "pkg/router.py"

    def aura_repo_digest(self, **_kwargs: Any) -> dict[str, Any]:
        if not self.digest_ok:
            return {"ok": False, "error": "no_codemap"}
        return {
            "ok": True,
            "codemap_status": "AURA_CODEMAP_ACTIVE",
            "file_count": 100,
            "symbol_count": 500,
            "topology_nodes": 800,
            "topology_edges": 1200,
            "source_of_truth": ["CODEMAP.json", "exact source files", "tests"],
        }

    def aura_prepare_arena(self, **kwargs: Any) -> dict[str, Any]:
        self.prepare_calls.append(kwargs)
        return {
            "ok": True,
            "plan_phase_hash": "phase-123",
            "act_capsules": [
                {
                    "task_id": "A1",
                    "target_file": "pkg/router.py",
                    "target_symbol": "route_failure",
                    "related_files": ["pkg/state.py"],
                    "objective": kwargs["objective"],
                }
            ],
            "grounding_evidence": [{"task_id": "A1", "file_exists": True}],
            "routing_decisions": [{"task_id": "A1", "route": "BUILDER_PATCH"}],
            "builder_patch_authorized": not self.blocked,
            "blockers": [{"severity": "blocker"}] if self.blocked else [],
            "warnings": [],
        }

    def aura_get_micro_context(self, **kwargs: Any) -> dict[str, Any]:
        self.context_calls.append(kwargs)
        return {
            "ok": True,
            "task_id": "A1",
            "target_file": self.context_target,
            "target_symbol": "route_failure",
            "line_ranges": [
                {
                    "file": "pkg/router.py",
                    "symbol": "route_failure",
                    "line_range": [20, 60],
                }
            ],
            "dependencies": ["pkg/state.py"],
            "tests": ["tests/test_router.py"],
            "route_decision": {"route": "BUILDER_PATCH"},
            "compressed_context": "exact compact context",
            "jspace_packet": "state",
            "st3gg_egress": {},
        }

    def aura_hotswap_status(self, **_kwargs: Any) -> dict[str, Any]:
        return {"ok": True, "hotswap_ready": True, "promotion_performed": False}


class FakeManager:
    def __init__(self) -> None:
        self.status = "WAITING_FOR_MODEL"
        self.opened: dict[str, Any] | None = None
        self.open_calls = 0
        self.submit_calls = 0
        self.exported: tuple[str, str] | None = None

    def open_prepared_session(self, **kwargs: Any) -> dict[str, Any]:
        self.open_calls += 1
        self.opened = kwargs
        return {
            "ok": True,
            "session_created": True,
            "session": {
                "session_id": "ELLM-1",
                "status": self.status,
                "pending_turn": {"turn_id": "TURN-1"},
            },
            "turn": {"turn_id": "TURN-1", "allowed_files": ["pkg/router.py"]},
            "control_profile": {"human_review_required": True, "production_mutation": False},
        }

    def submit_response(self, **_kwargs: Any) -> dict[str, Any]:
        self.submit_calls += 1
        self.status = "READY_FOR_HUMAN_REVIEW"
        return {
            "ok": True,
            "status": self.status,
            "session": {"session_id": "ELLM-1", "status": self.status},
            "verification": {"ok": True, "hotswap_ready": True, "failures": [], "tests": {"passed": 8, "total": 8}},
            "hotswap_status": {"hotswap_ready": True, "promotion_performed": False},
        }

    def get_session(self, _session_id: str) -> dict[str, Any]:
        return {"ok": True, "session": {"session_id": "ELLM-1", "status": self.status}}

    def export_session(self, session_id: str, output_path: str | Path) -> dict[str, Any]:
        self.exported = (session_id, str(output_path))
        return {
            "ok": True,
            "relative_path": "Aura_Staging/external_llm_sessions/forge.json",
            "production_mutation": False,
        }


def build_runtime(tmp_path: Path) -> tuple[AuraForgeRuntime, FakeBridge, FakeManager]:
    git_dir = tmp_path / ".git"
    git_dir.mkdir(parents=True, exist_ok=True)
    (git_dir / "HEAD").write_text("a" * 40, encoding="ascii")
    codemap = tmp_path / ".aura" / "CODEMAP.json"
    codemap.parent.mkdir(parents=True, exist_ok=True)
    if not codemap.exists():
        codemap.write_text('{"version": 1}', encoding="utf-8")
    bridge = FakeBridge()
    manager = FakeManager()
    runtime = AuraForgeRuntime(
        tmp_path,
        bridge=bridge,
        session_manager_factory=lambda _request, _bridge, _root: manager,
    )
    return runtime, bridge, manager


def request() -> dict[str, Any]:
    return {
        "objective": "Refactor failure routing and preserve public APIs",
        "target_file": "pkg/router.py",
        "target_symbol": "route_failure",
        "acceptance_criteria": ["all hidden tests pass", "public APIs remain stable"],
        "risk_map": ["interface drift", "scope expansion"],
        "provider": "test-provider",
        "model": "test-model",
        "metadata": {
            "ticket": "ENG-42",
            "api_key": "must-not-leak",
            "forge_contract_id": "spoofed-lineage",
            "github_token": "must-not-leak",
            "input_tokens": 321,
        },
    }


def test_prepare_compiles_exact_evidence_contract(tmp_path: Path) -> None:
    runtime, bridge, _manager = build_runtime(tmp_path)

    result = runtime.prepare(request())

    assert result["ok"] is True
    contract = result["contract"]
    assert contract["version"] == FORGE_CONTRACT_VERSION
    assert contract["plan_phase_hash"] == "phase-123"
    assert contract["allowed_files"] == [
        "pkg/router.py",
        "pkg/state.py",
        "tests/test_router.py",
    ]
    assert contract["task_evidence"][0]["line_ranges"][0]["line_range"] == [20, 60]
    assert contract["authority"]["production_mutation"] is False
    assert contract["authority"]["automatic_merge"] is False
    assert contract["metadata"] == {
        "ticket": "ENG-42",
        "forge_contract_id": "spoofed-lineage",
        "input_tokens": 321,
    }
    assert validate_forge_contract(contract) == []
    assert bridge.context_calls[0]["max_tokens_est"] == 800
    assert "external_workers_receive_slices_only" in bridge.prepare_calls[0]["constraints"]


def test_contract_identity_is_stable_for_same_grounded_evidence(tmp_path: Path) -> None:
    runtime_a, _bridge_a, _manager_a = build_runtime(tmp_path)
    runtime_b, _bridge_b, _manager_b = build_runtime(tmp_path)

    first = runtime_a.prepare(request())
    second = runtime_b.prepare(request())
    third = runtime_a.prepare(request())

    assert first["contract"]["contract_id"] == second["contract"]["contract_id"]
    assert first["contract"]["contract_id"] == third["contract"]["contract_id"]
    assert first["run_id"] != second["run_id"]
    assert first["run_id"] != third["run_id"]


def test_start_freezes_prepared_plan_and_opens_controlled_session(tmp_path: Path) -> None:
    runtime, _bridge, manager = build_runtime(tmp_path)

    result = runtime.start(request())

    assert result["ok"] is True
    assert result["status"] == "WAITING_FOR_MODEL"
    assert result["turn"]["turn_id"] == "TURN-1"
    assert manager.opened is not None
    assert manager.opened["prepared_arena"]["plan_phase_hash"] == "phase-123"
    assert manager.opened["metadata"]["forge_contract_id"] == result["contract"]["contract_id"]
    assert manager.opened["metadata"]["forge_contract_id"] != "spoofed-lineage"
    assert manager.opened["metadata"]["forge_version"] == "AURA_FORGE_V1"


def test_start_prepared_binds_exact_retained_contract_without_reprepare(tmp_path: Path) -> None:
    runtime, bridge, manager = build_runtime(tmp_path)
    prepared = runtime.prepare(request())
    run_id = prepared["run_id"]
    retained_prepared = runtime._runs[run_id]["prepared"]
    observed: dict[str, Any] = {}

    def factory(actual_request: ForgeRunRequest, actual_bridge: Any, actual_root: Path) -> FakeManager:
        observed.update(
            {
                "request": actual_request,
                "bridge": actual_bridge,
                "root": actual_root,
                "status_before_manager": runtime._runs[run_id]["status"],
            }
        )
        return manager

    runtime._session_manager_factory = factory
    started = runtime.start_prepared(
        run_id,
        expected_contract_id=prepared["contract"]["contract_id"],
        expected_contract_digest=prepared["contract_digest"],
    )

    assert started["ok"] is True
    assert len(bridge.prepare_calls) == 1
    assert manager.open_calls == 1
    assert manager.opened is not None
    assert manager.opened["prepared_arena"] is retained_prepared
    assert manager.opened["objective"] == request()["objective"]
    assert manager.opened["provider"] == "test-provider"
    assert manager.opened["model"] == "test-model"
    assert manager.opened["run_id"] == run_id
    assert manager.opened["metadata"]["forge_contract_digest"] == prepared["contract_digest"]
    assert observed["request"] == runtime._runs[run_id]["request"]
    assert observed["bridge"]._bridge is bridge
    assert observed["root"] == tmp_path.resolve()
    assert observed["status_before_manager"] == "STARTING"


def test_start_uses_retained_micro_context_after_bridge_drift(tmp_path: Path) -> None:
    runtime, bridge, manager = build_runtime(tmp_path)
    prepared = runtime.prepare(request())
    bridge.context_target = "pkg/unleased.py"
    observed: dict[str, Any] = {}

    def factory(_request: ForgeRunRequest, actual_bridge: Any, _root: Path) -> FakeManager:
        observed.update(
            actual_bridge.aura_get_micro_context(
                plan_phase_hash="phase-123",
                task_id="A1",
                depth=1,
                format="both",
                max_tokens_est=800,
            )
        )
        return manager

    runtime._session_manager_factory = factory
    started = runtime.start_prepared(prepared["run_id"])

    assert started["ok"] is True
    assert observed["target_file"] == "pkg/router.py"
    assert len(bridge.context_calls) == 1


def test_start_serves_only_contract_hashed_retained_source_slices(tmp_path: Path) -> None:
    target = tmp_path / "pkg" / "router.py"
    test_file = tmp_path / "tests" / "test_router.py"
    target.parent.mkdir(parents=True)
    test_file.parent.mkdir(parents=True)
    target.write_text(
        "def route_failure():\n    return 'retained'\n",
        encoding="utf-8",
    )
    test_file.write_text("def test_route_failure():\n    assert True\n", encoding="utf-8")
    runtime, _bridge, manager = build_runtime(tmp_path)
    prepared = runtime.prepare(request())
    observed: dict[str, Any] = {}

    def factory(_request: ForgeRunRequest, actual_bridge: Any, _root: Path) -> FakeManager:
        observed["retained"] = actual_bridge.aura_read_slice(
            file="pkg/router.py",
            symbol="route_failure",
            max_lines=40,
        )
        observed["unretained"] = actual_bridge.aura_read_slice(
            file="pkg/router.py",
            line_start=1,
            line_end=1,
            max_lines=1,
        )
        observed["live_read_exposed"] = hasattr(actual_bridge, "aura_repo_digest")
        target.write_text(
            "def route_failure():\n    return 'changed after drift check'\n",
            encoding="utf-8",
        )
        observed["after_change"] = actual_bridge.aura_read_slice(
            file="pkg/router.py",
            symbol="route_failure",
            max_lines=40,
        )
        return manager

    runtime._session_manager_factory = factory
    started = runtime.start_prepared(prepared["run_id"])

    assert started["ok"] is True
    assert "return 'retained'" in observed["retained"]["content"]
    assert observed["after_change"] == observed["retained"]
    assert observed["unretained"] == {
        "ok": False,
        "error": "unretained_forge_source_slice",
    }
    assert observed["live_read_exposed"] is False


def test_concurrent_submit_accepts_one_response_only(tmp_path: Path) -> None:
    runtime, _bridge, manager = build_runtime(tmp_path)
    started = runtime.start(request())
    calls = 0
    original = manager.submit_response

    def counted_submit(**kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return original(**kwargs)

    manager.submit_response = counted_submit  # type: ignore[method-assign]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _index: runtime.submit(
                    run_id=started["run_id"],
                    turn_id="TURN-1",
                    response="patch",
                ),
                range(2),
            )
        )

    assert calls == 1
    assert sum(result["ok"] is True for result in results) == 1
    assert {result.get("error") for result in results if not result["ok"]} == {"forge_run_not_waiting_for_response"}
    assert started["contract_digest"] == forge_contract_digest(started["contract"])


def test_start_prepared_consumes_run_once_and_rejects_double_start(tmp_path: Path) -> None:
    runtime, _bridge, manager = build_runtime(tmp_path)
    missing = runtime.start_prepared("FORGE-missing")
    prepared = runtime.prepare(request())

    first = runtime.start_prepared(prepared["run_id"])
    second = runtime.start_prepared(prepared["run_id"])

    assert missing["error"] == "forge_run_not_found"
    assert first["ok"] is True
    assert second["ok"] is False
    assert second["error"] == "forge_run_not_prepared"
    assert manager.open_calls == 1


def test_submit_enforces_output_budget_before_session_manager(tmp_path: Path) -> None:
    runtime, _bridge, manager = build_runtime(tmp_path)
    prepared = runtime.prepare(request())
    started = runtime.start_prepared(prepared["run_id"])
    assert started["ok"] is True

    denied = runtime.submit(
        run_id=prepared["run_id"],
        turn_id="TURN-1",
        response="x" * (2400 * 4 + 1),
    )

    assert denied["ok"] is False
    assert denied["error"] == "forge_output_budget_exceeded"
    assert manager.submit_calls == 0


def test_start_prepared_contract_expectations_fail_closed_before_manager(tmp_path: Path) -> None:
    runtime, _bridge, manager = build_runtime(tmp_path)
    id_bound = runtime.prepare(request())
    digest_bound = runtime.prepare(request())

    bad_id = runtime.start_prepared(
        id_bound["run_id"],
        expected_contract_id="wrong-contract",
    )
    bad_digest = runtime.start_prepared(
        digest_bound["run_id"],
        expected_contract_digest="blake2b-256:wrong",
    )

    assert bad_id["error"] == "expected_forge_contract_id_mismatch"
    assert bad_digest["error"] == "expected_forge_contract_digest_mismatch"
    assert manager.open_calls == 0
    assert runtime.start_prepared(id_bound["run_id"])["error"] == "forge_run_not_prepared"
    assert runtime.start_prepared(digest_bound["run_id"])["error"] == "forge_run_not_prepared"


def test_start_prepared_rejects_head_drift(tmp_path: Path, monkeypatch: Any) -> None:
    head_a = "a" * 40
    head_b = "b" * 40
    monkeypatch.setattr(aura_forge_module, "_git_head", lambda _root: head_a)
    runtime, _bridge, manager = build_runtime(tmp_path)
    prepared = runtime.prepare(request())
    monkeypatch.setattr(aura_forge_module, "_git_head", lambda _root: head_b)

    result = runtime.start_prepared(prepared["run_id"])

    assert result["error"] == "forge_repository_evidence_drift"
    assert result["details"]["drift"]["head_sha"] == {
        "expected": head_a,
        "actual": head_b,
    }
    assert manager.open_calls == 0


def test_start_prepared_rejects_codemap_drift(tmp_path: Path) -> None:
    codemap = tmp_path / ".aura" / "CODEMAP.json"
    codemap.parent.mkdir(parents=True)
    codemap.write_text('{"version": 1}', encoding="utf-8")
    runtime, _bridge, manager = build_runtime(tmp_path)
    prepared = runtime.prepare(request())
    codemap.write_text('{"version": 2}', encoding="utf-8")

    result = runtime.start_prepared(prepared["run_id"])

    assert result["error"] == "forge_repository_evidence_drift"
    assert ".aura/CODEMAP.json" == prepared["contract"]["repository"]["codemap_path"]
    assert "codemap_digest" in result["details"]["drift"]
    assert manager.open_calls == 0


def test_start_prepared_rejects_exact_allowed_source_drift(tmp_path: Path) -> None:
    target = tmp_path / "pkg" / "router.py"
    related = tmp_path / "pkg" / "state.py"
    target.parent.mkdir(parents=True)
    target.write_text("def route_failure():\n    return 'before'\n", encoding="utf-8")
    related.write_text("STATE = 'stable'\n", encoding="utf-8")
    runtime, _bridge, manager = build_runtime(tmp_path)
    prepared = runtime.prepare(request())
    target.write_text("def route_failure():\n    return 'after'\n", encoding="utf-8")

    result = runtime.start_prepared(prepared["run_id"])

    assert result["error"] == "forge_repository_evidence_drift"
    source_drift = result["details"]["drift"]["allowed_file_source_hashes"]
    assert list(source_drift) == ["pkg/router.py"]
    assert manager.open_calls == 0


def test_start_compatibility_prepares_once_then_uses_bound_seam(tmp_path: Path) -> None:
    runtime, bridge, manager = build_runtime(tmp_path)

    started = runtime.start(request())

    assert started["ok"] is True
    assert len(bridge.prepare_calls) == 1
    assert manager.open_calls == 1
    assert manager.opened is not None
    assert manager.opened["metadata"]["forge_contract_digest"] == started["contract_digest"]


def test_status_does_not_claim_decision_eligibility_without_proof(tmp_path: Path) -> None:
    runtime, _bridge, manager = build_runtime(tmp_path)
    started = runtime.start(request())
    manager.status = "READY_FOR_HUMAN_REVIEW"

    status = runtime.status(started["run_id"])

    assert status["status"] == "READY_FOR_HUMAN_REVIEW"
    assert status["decision_eligible"] is False
    assert status["human_review_packet"]["required_gate_results"] == {
        "canonical_arena_verifier": False,
        "hotswap_readiness": True,
    }


def test_submit_stops_at_human_review_without_promotion(tmp_path: Path) -> None:
    runtime, _bridge, _manager = build_runtime(tmp_path)
    started = runtime.start(request())

    result = runtime.submit(
        run_id=started["run_id"],
        turn_id="TURN-1",
        response="diff --git a/pkg/router.py b/pkg/router.py\n",
        provider_usage={"input_tokens": 100, "api_key": "redact"},
    )

    packet = result["human_review_packet"]
    assert result["status"] == "READY_FOR_HUMAN_REVIEW"
    assert packet["decision_eligible"] is True
    assert packet["required_gate_results"] == {
        "canonical_arena_verifier": True,
        "hotswap_readiness": True,
    }
    assert packet["promotion_performed"] is False
    assert packet["automatic_commit"] is False
    assert packet["automatic_merge"] is False


def test_fail_closed_when_codemap_or_plan_is_unavailable(tmp_path: Path) -> None:
    runtime, bridge, _manager = build_runtime(tmp_path)
    bridge.digest_ok = False
    missing = runtime.prepare(request())
    assert missing["ok"] is False
    assert missing["error"] == "repository_digest_unavailable"

    bridge.digest_ok = True
    bridge.blocked = True
    blocked = runtime.prepare(request())
    assert blocked["ok"] is False
    assert blocked["error"] == "arena_prepare_blocked"
    assert blocked["production_mutation"] is False


def test_prepare_rejects_missing_exact_codemap_evidence(tmp_path: Path) -> None:
    runtime, _bridge, _manager = build_runtime(tmp_path)
    (tmp_path / ".aura" / "CODEMAP.json").unlink()

    result = runtime.prepare(request())

    assert result["ok"] is False
    assert result["error"] == "compiled_forge_contract_invalid"
    assert result["details"] == {"errors": ["repository_codemap_digest_invalid"]}


def test_request_rejects_unsafe_paths_and_invalid_budgets() -> None:
    try:
        ForgeRunRequest.from_value({"objective": "x", "target_file": "../secret.py"})
    except ValueError as exc:
        assert "repository-relative" in str(exc)
    else:
        raise AssertionError("unsafe path was accepted")

    try:
        ForgeRunRequest.from_value({"objective": "x", "max_turns": 0})
    except ValueError as exc:
        assert "max_turns" in str(exc)
    else:
        raise AssertionError("invalid max_turns was accepted")

    try:
        ForgeRunRequest.from_value({"objective": "x", "required_gates": ["hidden_tests"]})
    except ValueError as exc:
        assert "unsupported required_gates" in str(exc)
    else:
        raise AssertionError("unsupported gate was accepted")


def test_malformed_request_collections_fail_closed(tmp_path: Path) -> None:
    runtime, _bridge, _manager = build_runtime(tmp_path)

    criteria = runtime.prepare({"objective": "x", "acceptance_criteria": 7})
    metadata = runtime.prepare({"objective": "x", "metadata": ["not", "an", "object"]})
    empty_gates = runtime.prepare({"objective": "x", "required_gates": []})

    assert criteria["ok"] is False
    assert criteria["stage"] == "REQUEST"
    assert criteria["error"] == "expected an array of strings"
    assert metadata["ok"] is False
    assert metadata["stage"] == "REQUEST"
    assert metadata["error"] == "metadata must be an object"
    assert empty_gates["ok"] is False
    assert empty_gates["error"] == "required_gates must not be empty"


def test_dot_prefixed_repository_paths_are_preserved() -> None:
    parsed = ForgeRunRequest.from_value({"objective": "x", "target_file": ".aura/ARCHITECTURE.md"})
    assert parsed.target_file == ".aura/ARCHITECTURE.md"


def test_contract_validator_rejects_unsupported_gates(tmp_path: Path) -> None:
    runtime, _bridge, _manager = build_runtime(tmp_path)
    contract = runtime.prepare(request())["contract"]
    contract["required_gates"] = ["hidden_tests"]
    assert validate_forge_contract(contract) == ["unsupported_required_gates:hidden_tests"]


def test_contract_validator_rejects_authority_and_lifecycle_tampering(tmp_path: Path) -> None:
    runtime, _bridge, _manager = build_runtime(tmp_path)
    contract = runtime.prepare(request())["contract"]
    contract["authority"]["automatic_push"] = True
    contract["lifecycle"] = ["FRAME", "ACT"]
    contract["allowed_files"] = ["../escape.py"]

    errors = validate_forge_contract(contract)

    assert "invalid_authority:automatic_push" in errors
    assert "invalid_lifecycle" in errors
    assert "invalid_allowed_file:../escape.py" in errors


def test_bridge_exceptions_fail_closed(tmp_path: Path) -> None:
    runtime, bridge, _manager = build_runtime(tmp_path)

    def explode(**_kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("secret backend detail")

    bridge.aura_repo_digest = explode  # type: ignore[method-assign]
    result = runtime.prepare(request())

    assert result["ok"] is False
    assert result["error"] == "repository_digest_error"
    assert result["details"] == {"exception_type": "RuntimeError"}


def test_contract_validator_never_raises_on_malformed_arrays(tmp_path: Path) -> None:
    runtime, _bridge, _manager = build_runtime(tmp_path)
    contract = runtime.prepare(request())["contract"]
    contract["required_gates"] = 7
    contract["act_capsules"] = {"bad": "shape"}
    contract["task_evidence"] = None
    contract["lifecycle"] = 42

    errors = validate_forge_contract(contract)

    assert "required_gates_must_be_array" in errors
    assert "act_capsules_must_be_array" in errors
    assert "task_evidence_must_be_array" in errors
    assert "invalid_lifecycle" in errors
    assert validate_forge_contract([]) == ["contract_must_be_object"]  # type: ignore[arg-type]


def test_invalid_bridge_packet_fails_closed(tmp_path: Path) -> None:
    runtime, bridge, _manager = build_runtime(tmp_path)
    bridge.aura_repo_digest = lambda **_kwargs: None  # type: ignore[method-assign]

    result = runtime.prepare(request())

    assert result["ok"] is False
    assert result["error"] == "repository_digest_invalid"


def test_export_delegates_to_safe_session_owner(tmp_path: Path) -> None:
    runtime, _bridge, manager = build_runtime(tmp_path)
    started = runtime.start(request())

    exported = runtime.export(started["run_id"], "forge.json")

    assert exported["ok"] is True
    assert exported["production_mutation"] is False
    assert manager.exported == ("ELLM-1", "forge.json")
