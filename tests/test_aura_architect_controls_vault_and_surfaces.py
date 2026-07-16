from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from aura_architect_control import normalize_control_profile
from aura_arena_architect_connector import AuraArenaArchitectConnector, _task_projection
from aura_arena_connector_server import ArenaConnectorServerState, dispatch_connector_request
from aura_external_llm_session_safe import AuraExternalLLMSessionManager
from aura_human_agent_arena_architect import HumanAgentArchitectCockpit
from aura_refactor_output_vault import RefactorOutputVault


def _plan(candidate_id: str = "PLAN-A", *, target_file: str = "a.py") -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "arm_family": "TEST_ARM",
        "provenance": {"generation_mode": "TEST_FIXTURE"},
        "token_usage": {"input_tokens": 10, "output_tokens": 5},
        "plan": {
            "architecture_decision": "Reuse the bounded Aura architecture.",
            "target_file": target_file,
            "target_symbol": "f",
            "coverage_tags": ["routing", "ledger"],
            "architecture_reuse": True,
            "act_tasks": [
                {
                    "task_id": "A1",
                    "objective": "Change one exact symbol.",
                    "target_file": target_file,
                    "target_symbol": "f",
                    "related_files": [],
                    "allowed_scope": "one exact symbol",
                    "acceptance": "Focused tests pass.",
                    "expected_output": "UNIFIED_DIFF",
                    "size": "S",
                }
            ],
            "acceptance_criteria": ["Focused tests pass."],
            "rollback_conditions": ["Discard the staged patch."],
            "risk_map": ["Preserve the public interface."],
            "constraints": ["Proposal only."],
        },
    }


def test_control_profile_fails_closed_on_string_booleans_and_unsafe_roots() -> None:
    with pytest.raises(ValueError, match="boolean"):
        normalize_control_profile({"record_outputs": "false"}, surface="mcp_external")
    with pytest.raises(ValueError, match="Aura_Staging"):
        normalize_control_profile({"output_root": "Aura_Memory/private"})
    with pytest.raises(ValueError, match="production mutation"):
        normalize_control_profile({"production_mutation": True})
    with pytest.raises(ValueError, match="VSA"):
        normalize_control_profile({"vsa_patch_authority": True})


def test_plan_projection_preserves_dot_prefixed_repository_paths() -> None:
    projection = _task_projection(_plan(target_file=".github/workflows/x.yml")["plan"]["act_tasks"][0])
    assert projection["target_file"] == ".github/workflows/x.yml"


def test_vault_is_idempotent_redacts_secrets_and_preserves_token_metrics(tmp_path: Path) -> None:
    vault = RefactorOutputVault(tmp_path)
    first = vault.start_run(
        run_id="RUN-1",
        objective="Inspect generated code",
        surface="native",
        control_profile={"surgeon_context_tokens": 2200},
        metadata={
            "api_key": "sk-super-secret-value-123456789",
            "token_usage": {"input_tokens": 10, "output_tokens": 5},
        },
    )
    second = vault.start_run(
        run_id="RUN-1",
        objective="Inspect generated code",
        surface="native",
        control_profile={"surgeon_context_tokens": 2200},
        metadata={
            "api_key": "sk-super-secret-value-123456789",
            "token_usage": {"input_tokens": 10, "output_tokens": 5},
        },
    )
    assert first["reused"] is False
    assert second["reused"] is True
    run = vault.load_artifact("RUN-1/run.json")["content"]
    assert run["metadata"]["api_key"]["redacted"] is True
    assert run["metadata"]["token_usage"]["input_tokens"] == 10
    assert run["control_profile"]["surgeon_context_tokens"] == 2200

    prompt = "Authorization: Bearer very-secret-token-value-123456"
    response = "diff --git a/a.py b/a.py\n+API_KEY=sk-secret-secret-secret-123456\n"
    evidence = vault.record_generated_output(
        run_id="RUN-1",
        turn_id="TURN-1",
        task_id="A1",
        role="worker",
        prompt=prompt,
        response=response,
        result={"ok": True, "authorization": "private"},
        provider_usage={"input_tokens": 10},
    )
    stored_prompt = (tmp_path / evidence["artifacts"]["prompt"]).read_text(encoding="utf-8")
    stored_response = (tmp_path / evidence["artifacts"]["generated_output"]).read_text(
        encoding="utf-8"
    )
    assert "very-secret-token" not in stored_prompt
    assert "sk-secret" not in stored_response
    assert evidence["prompt_digest"] == hashlib.blake2b(
        prompt.encode("utf-8"), digest_size=16
    ).hexdigest()
    assert evidence["response_digest"] == hashlib.blake2b(
        response.encode("utf-8"), digest_size=16
    ).hexdigest()
    manifest = vault.load_artifact("RUN-1/manifest.jsonl")["content"]
    assert manifest[-1]["previous_event_digest"] == manifest[-2]["event_digest"]


def test_vault_rejects_run_id_reuse_with_different_identity(tmp_path: Path) -> None:
    vault = RefactorOutputVault(tmp_path)
    vault.start_run(
        run_id="RUN-1",
        objective="first",
        surface="native",
        control_profile={},
    )
    with pytest.raises(ValueError, match="different immutable metadata"):
        vault.start_run(
            run_id="RUN-1",
            objective="different",
            surface="native",
            control_profile={},
        )


class _Capsule:
    def __init__(self, task: dict[str, Any]) -> None:
        self.task = dict(task)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.task)


class _PreparedLoop:
    blockers = False
    drift = False

    def __init__(self, *, repo_root: Path) -> None:
        self.repo_root = repo_root

    def prepare(self, _objective: str, *, act_tasks: list[dict[str, Any]], **_kwargs: Any) -> Any:
        tasks = [dict(item) for item in act_tasks]
        if self.drift:
            tasks[0]["target_file"] = "different.py"
        findings = (
            [SimpleNamespace(to_dict=lambda: {"severity": "blocker", "message": "bad"})]
            if self.blockers
            else []
        )
        routes = [
            {"task_id": item["task_id"], "route": "SHADOW_REVIEW" if self.blockers else "BUILDER_PATCH"}
            for item in tasks
        ]
        return SimpleNamespace(
            plan=SimpleNamespace(
                phase_hash="PHASE-1",
                act_capsules=[_Capsule(item) for item in tasks],
            ),
            grounding=[],
            shadow_report=SimpleNamespace(findings=findings, gate="BLOCK" if findings else "ALLOW"),
            arena=SimpleNamespace(
                agent_capsules=[dict(item) for item in tasks],
                routing_decisions=routes,
                agent_leases=[],
                ready_for_incubator=not findings,
            ),
            intensity=1,
        )


class _SessionBridge:
    def __init__(self) -> None:
        self._sessions: dict[str, Any] = {}


def test_selected_plan_is_bound_to_all_prepared_act_capsules(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import aura_architect_loop

    monkeypatch.setattr(aura_architect_loop, "ArchitectFusionLoop", _PreparedLoop)
    candidate = _plan()
    candidate["plan"]["act_tasks"].append(
        {
            "task_id": "A2",
            "objective": "Change the second symbol.",
            "target_file": "b.py",
            "target_symbol": "g",
            "related_files": [],
            "allowed_scope": "one exact symbol",
            "acceptance": "Focused tests pass.",
            "expected_output": "UNIFIED_DIFF",
            "size": "S",
            "depends_on": ["A1"],
        }
    )
    bridge = _SessionBridge()
    connector = AuraArenaArchitectConnector(tmp_path, bridge=bridge)
    result = connector.prepare_refactor(
        objective="two bounded edits",
        candidates=[candidate],
        required_capabilities=["routing"],
        control={"record_outputs": False},
    )
    assert result["ok"] is True
    prepared = result["arena_preparation"]
    assert [item["task_id"] for item in prepared["act_capsules"]] == ["A1", "A2"]
    assert prepared["dependency_map"]["A2"] == ["A1"]
    assert prepared["requested_act_projection_digest"] == prepared["prepared_act_projection_digest"]
    assert bridge._sessions["PHASE-1"]["selected_plan_digest"] == prepared["selected_plan_digest"]


def test_selected_plan_projection_drift_and_blockers_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import aura_architect_loop

    bridge = _SessionBridge()
    connector = AuraArenaArchitectConnector(tmp_path, bridge=bridge)
    _PreparedLoop.drift = True
    _PreparedLoop.blockers = False
    monkeypatch.setattr(aura_architect_loop, "ArchitectFusionLoop", _PreparedLoop)
    with pytest.raises(ValueError, match="do not match"):
        connector.prepare_refactor(
            objective="x",
            candidates=[_plan()],
            control={"record_outputs": False},
        )
    _PreparedLoop.drift = False
    _PreparedLoop.blockers = True
    result = connector.prepare_refactor(
        objective="x",
        candidates=[_plan()],
        control={"record_outputs": False},
    )
    assert result["ok"] is False
    assert result["arena_preparation"]["blockers"]
    assert "PHASE-1" not in bridge._sessions
    _PreparedLoop.blockers = False


class _HTTPConnector:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def validate_control(self, control: Any, *, surface: str) -> dict[str, Any]:
        self.calls.append(("control", {"control": control, "surface": surface}))
        return {"ok": True, "surface": surface}

    def compare_plans(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("compare", kwargs))
        return {"ok": True, "selected_candidate_id": "A"}

    def prepare_refactor(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("prepare", kwargs))
        return {"ok": True}

    def open_surgeon_session(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("open", kwargs))
        return {"ok": True, "session": {"session_id": "S1"}}

    def surgeon_next(self, session_id: str) -> dict[str, Any]:
        return {"ok": True, "session_id": session_id}

    def surgeon_submit(self, **kwargs: Any) -> dict[str, Any]:
        return {"ok": True, **kwargs}

    def surgeon_status(self, session_id: str) -> dict[str, Any]:
        return {"ok": True, "session_id": session_id}

    def surgeon_replan(self, **kwargs: Any) -> dict[str, Any]:
        return {"ok": True, **kwargs}

    def list_refactor_outputs(self, *, limit: int) -> dict[str, Any]:
        return {"ok": True, "limit": limit, "runs": []}

    def load_refactor_output(self, relative_path: str, *, max_bytes: int) -> dict[str, Any]:
        return {"ok": True, "relative_path": relative_path, "max_bytes": max_bytes}

    def route_native_model(self, **kwargs: Any) -> dict[str, Any]:
        return {"status": "PROPOSED", **kwargs}

    def execute_native_model(self, **kwargs: Any) -> dict[str, Any]:
        return {"status": "SHADOW_ONLY", **kwargs}


def test_http_aliases_use_the_same_connector_with_explicit_surface(tmp_path: Path) -> None:
    connector = _HTTPConnector()
    state = ArenaConnectorServerState(tmp_path, connector=connector)
    for route, expected_surface in (
        ("/v1/architect/compare", "http_external"),
        ("/v1/coding-arena/architect/compare", "coding_arena"),
        ("/v1/human-agent/architect/compare", "human_agent_arena"),
    ):
        status, result = dispatch_connector_request(
            state,
            "POST",
            route,
            {"objective": "x", "candidates": [_plan()]},
        )
        assert status == 200
        assert result["selected_candidate_id"] == "A"
        assert connector.calls[-1][1]["surface"] == expected_surface
    status, result = dispatch_connector_request(
        state,
        "POST",
        "/v1/human-agent/architect/surgeon/open",
        {"objective": "x", "candidates": [_plan()]},
    )
    assert status == 200
    assert result["session"]["session_id"] == "S1"
    assert connector.calls[-1][1]["surface"] == "human_agent_arena"


def test_mcp_discovery_contains_controlled_architect_and_output_tools() -> None:
    import aura_agent_arena_mcp_architect as mcp

    names = {item["name"] for item in mcp.base_mcp.TOOL_DEFINITIONS}
    assert {
        "aura_architect_control_validate",
        "aura_architect_compare_plans",
        "aura_architect_prepare",
        "aura_architect_surgeon_open",
        "aura_architect_surgeon_next",
        "aura_architect_surgeon_submit",
        "aura_architect_surgeon_status",
        "aura_architect_council_replan",
        "aura_refactor_outputs_list",
        "aura_refactor_output_load",
    } <= names


class _TwoTaskBridge:
    def aura_prepare_arena(self, **_kwargs: Any) -> dict[str, Any]:
        return {
            "ok": True,
            "plan_phase_hash": "P1",
            "act_capsules": [
                {
                    "task_id": "A1",
                    "target_file": "a.py",
                    "target_symbol": "f",
                    "related_files": [],
                    "objective": "first",
                    "size": "S",
                    "role": "cheap_builder",
                },
                {
                    "task_id": "A2",
                    "target_file": "b.py",
                    "target_symbol": "g",
                    "related_files": [],
                    "objective": "second",
                    "size": "S",
                    "role": "cheap_builder",
                },
            ],
        }

    def aura_get_micro_context(self, *, task_id: str, **_kwargs: Any) -> dict[str, Any]:
        file = "a.py" if task_id == "A1" else "b.py"
        symbol = "f" if task_id == "A1" else "g"
        return {
            "ok": True,
            "task_id": task_id,
            "target_file": file,
            "target_symbol": symbol,
            "line_ranges": [{"file": file, "symbol": symbol, "line_range": [1, 2]}],
            "tests": [],
            "compressed_context": "small",
        }

    def aura_read_slice(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "ok": True,
            "file": kwargs["file"],
            "symbol": kwargs.get("symbol", ""),
            "line_start": 1,
            "line_end": 2,
            "total_lines": 2,
            "content": "def f():\n    return 1\n",
            "warnings": [],
        }

    def aura_stage_patch(self, **kwargs: Any) -> dict[str, Any]:
        return {"ok": True, "patch": {"task_id": kwargs["task_id"]}}

    def aura_verify_arena(self, **_kwargs: Any) -> dict[str, Any]:
        return {"ok": True, "hotswap_ready": True, "failures": [], "checks": []}

    def aura_hotswap_status(self, **_kwargs: Any) -> dict[str, Any]:
        return {"ok": True, "production_mutation": False}


def test_safe_session_never_advertises_turn_after_max_turns(tmp_path: Path) -> None:
    manager = AuraExternalLLMSessionManager(tmp_path, bridge=_TwoTaskBridge())
    opened = manager.open_session(objective="two tasks", max_turns=1)
    turn = opened["turn"]
    result = manager.submit_response(
        session_id=opened["session"]["session_id"],
        turn_id=turn["turn_id"],
        response=(
            "diff --git a/a.py b/a.py\n"
            "--- a/a.py\n"
            "+++ b/a.py\n"
            "@@ -1 +1 @@\n"
            "-x = 1\n"
            "+x = 2\n"
        ),
    )
    assert result["ok"] is False
    assert result["status"] == "BLOCKED_MAX_TURNS"
    assert result["next_turn"] is None
    assert result["session"]["pending_turn"] is None


def test_safe_slice_budget_charges_complete_payload(tmp_path: Path) -> None:
    class HugeBridge:
        def aura_read_slice(self, **kwargs: Any) -> dict[str, Any]:
            return {
                "ok": True,
                "file": kwargs["file"],
                "symbol": "",
                "line_start": 1,
                "line_end": 1,
                "total_lines": 1,
                "content": "x",
                "warnings": ["w" * 500],
            }

    manager = AuraExternalLLMSessionManager(tmp_path, bridge=HugeBridge())
    source, tests = manager._lease_slices(
        {"target_file": "a.py", "target_symbol": None, "tests": []},
        token_budget=20,
    )
    assert source == []
    assert tests == []


class _ArenaState:
    def __init__(self) -> None:
        self.prepared_handoff_packets: list[dict[str, Any]] = []
        self.events: list[tuple[str, str]] = []

    def add_event(self, kind: str, detail: str) -> None:
        self.events.append((kind, detail))


class _Arena:
    def __init__(self) -> None:
        self.state = _ArenaState()

    def get_state(self) -> dict[str, Any]:
        return {"prepared_handoff_packets": self.state.prepared_handoff_packets}

    def route_command(self, command: str, **_kwargs: Any) -> dict[str, Any]:
        return {"ok": True, "answer": command}


class _ArchitectRuntime:
    def __init__(self) -> None:
        self.control = SimpleNamespace(
            output_root="Aura_Staging/refactor_output_vault",
            to_dict=lambda: {
                "control_digest": "CONTROL-1",
                "output_root": "Aura_Staging/refactor_output_vault",
            },
        )

    def load_refactor_output(self, relative_path: str, *, max_bytes: int) -> dict[str, Any]:
        return {
            "ok": True,
            "relative_path": relative_path,
            "bytes": 12,
            "digest": "D1",
            "visibility": "LOCAL_PRIVATE_REDACTED_OUTPUT",
            "content": "diff --git a/a.py b/a.py",
        }


def test_human_agent_cockpit_loads_local_output_into_review_state(tmp_path: Path) -> None:
    arena = _Arena()
    cockpit = HumanAgentArchitectCockpit(
        tmp_path,
        arena=arena,
        architect=_ArchitectRuntime(),
    )
    result = cockpit.load_refactor_output("RUN-1/turns/T1/generated.patch")
    assert result["loaded_into_human_agent_arena"] is True
    artifact = arena.state.prepared_handoff_packets[-1]
    assert artifact["kind"] == "local_refactor_output"
    assert artifact["production_mutation"] is False
