from __future__ import annotations

from pathlib import Path
from typing import Any

from aura_forge import (
    AuraForgeRuntime,
    FORGE_CONTRACT_VERSION,
    ForgeRunRequest,
    validate_forge_contract,
)


class FakeBridge:
    def __init__(self) -> None:
        self.prepare_calls: list[dict[str, Any]] = []
        self.context_calls: list[dict[str, Any]] = []
        self.blocked = False
        self.digest_ok = True

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
            "target_file": "pkg/router.py",
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
        self.exported: tuple[str, str] | None = None

    def open_prepared_session(self, **kwargs: Any) -> dict[str, Any]:
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
    assert contract["allowed_files"] == ["pkg/router.py", "pkg/state.py"]
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


def test_export_delegates_to_safe_session_owner(tmp_path: Path) -> None:
    runtime, _bridge, manager = build_runtime(tmp_path)
    started = runtime.start(request())

    exported = runtime.export(started["run_id"], "forge.json")

    assert exported["ok"] is True
    assert exported["production_mutation"] is False
    assert manager.exported == ("ELLM-1", "forge.json")
