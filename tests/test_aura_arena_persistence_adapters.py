"""Cross-arena tests for Aura temporal persistence adapters."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aura_arena_persistence_adapters import ArenaPersistenceCoordinator
from aura_construction_fixtures import build_sco_construction_demo_fixture


HEAD = "a" * 40


class _Coding:
    session_id = "CWFST-1"

    def __init__(self):
        self.state = {
            "ok": True,
            "session_id": self.session_id,
            "state": "PLAN_READY",
            "objective": "Change one symbol",
            "evidence": {"topology": "healthy"},
            "gate": {"allowed_actions": ["stage_patch"]},
            "patch_authority": "exact_source_spans_and_hashes_only",
            "vsa_patch_authority": False,
        }

    def get_state_without_routing(self):
        return dict(self.state)


class _Human:
    workflow_id = "HUMAN-1"

    def __init__(self):
        self.state = {
            "ok": True,
            "workflow_id": self.workflow_id,
            "current_phase": "PLAN",
            "objective": "Coordinate a construction handoff",
            "evidence": {"project": "fictional"},
            "routing": {"selected": "prepare_capsule"},
            "patch_authority": "exact_source_spans_and_hashes_only",
            "vsa_patch_authority": False,
        }

    def get_state(self):
        return dict(self.state)


@dataclass
class _Act:
    task_id: str = "A1"
    target_file: str = "a.py"
    target_symbol: str = "f"
    role: str = "surgeon"
    size: str = "small"


class _Plan:
    phase_hash = "phase-bridge"
    act_capsules = [_Act()]


class _Prepared:
    plan = _Plan()


class _Arena:
    affected_files = ["a.py"]
    routing_decisions = [{"task_id": "A1", "route": "BUILDER_PATCH"}]


class _Patch:
    patch_id = "PATCH-1"
    task_id = "A1"
    affected_files = ["a.py"]
    status = "staged"


class _Stage:
    ok = True
    patch = _Patch()


class _Verification:
    ok = True
    stage = "verified"
    hotswap_ready = True
    failures = []


class _Bridge:
    def __init__(self):
        self.session = {
            "prepared": _Prepared(),
            "arena": _Arena(),
            "stage_results": [_Stage()],
            "verification": _Verification(),
            "hotswap_capsule": {"status": "review_required"},
        }

    def _require_session(self, plan_phase_hash):
        assert plan_phase_hash == "phase-bridge"
        return self.session


def test_coding_and_human_adapters_checkpoint_without_mutating_live_state(tmp_path: Path):
    coordinator = ArenaPersistenceCoordinator(str(tmp_path))
    coding = _Coding()
    human = _Human()
    coding_before = dict(coding.state)
    human_before = dict(human.state)

    coding_result = coordinator.checkpoint_coding_workbench(
        coding,
        repo_head=HEAD,
        created_at=1.0,
    )
    human_result = coordinator.checkpoint_human_agent(
        human,
        repo_head=HEAD,
        created_at=2.0,
    )

    assert coding_result["checkpoint"]["arena_id"] == "coding_workbench"
    assert human_result["checkpoint"]["arena_id"] == "human_agent_arena"
    assert coding.state == coding_before
    assert human.state == human_before


def test_agent_bridge_checkpoint_preserves_only_bounded_session_projection(tmp_path: Path):
    coordinator = ArenaPersistenceCoordinator(str(tmp_path))
    bridge = _Bridge()

    result = coordinator.checkpoint_agent_bridge(
        bridge,
        plan_phase_hash="phase-bridge",
        repo_head=HEAD,
        created_at=3.0,
    )
    payload = result["checkpoint"]["payload"]

    assert payload["plan_phase_hash"] == "phase-bridge"
    assert payload["verification"]["hotswap_ready"] is True
    assert payload["stage_results"][0]["patch_id"] == "PATCH-1"
    assert "diff" not in str(payload).lower()
    assert payload["automatic_hotswap"] is False


def test_construction_adapter_preserves_proposal_only_authority(tmp_path: Path):
    coordinator = ArenaPersistenceCoordinator(str(tmp_path))
    fixture = build_sco_construction_demo_fixture()

    result = coordinator.checkpoint_construction(
        fixture.state,
        repo_head=HEAD,
        created_at=4.0,
    )
    payload = result["checkpoint"]["payload"]

    assert payload["project_id"] == fixture.state.project_id
    assert payload["state_digest"] == fixture.state.state_digest
    assert payload["arena_persistence"]["physical_work_authorized"] is False
    assert payload["arena_persistence"]["payment_released"] is False


def test_cross_arena_handoff_is_payload_free_and_review_gated(tmp_path: Path):
    coordinator = ArenaPersistenceCoordinator(str(tmp_path))
    result = coordinator.checkpoint_human_agent(
        _Human(),
        repo_head=HEAD,
        created_at=5.0,
    )
    checkpoint_id = result["checkpoint"]["checkpoint_id"]
    invariants = {
        "patch_authority": "exact_source_spans_and_hashes_only",
        "vsa_patch_authority": False,
        "current_phase": "PLAN",
        "objective": "Coordinate a construction handoff",
        "evidence": {"project": "fictional"},
        "routing": {"selected": "prepare_capsule"},
    }

    handoff = coordinator.handoff_packet(
        checkpoint_id,
        target_arena_id="agent_bridge_arena",
        current_repo_head=HEAD,
        current_invariant_values=invariants,
    )

    assert handoff["digital_baton_only"] is True
    assert handoff["payload_included"] is False
    assert handoff["target_arena_mutated"] is False
    assert handoff["human_review_required"] is True


def test_observatory_projection_omits_payload(tmp_path: Path):
    coordinator = ArenaPersistenceCoordinator(str(tmp_path))
    result = coordinator.checkpoint_coding_workbench(
        _Coding(),
        repo_head=HEAD,
        created_at=6.0,
    )
    projection = coordinator.observatory_projection(
        result["checkpoint"]["checkpoint_id"]
    )

    assert projection["read_only"] is True
    assert projection["payload_included"] is False
    assert "payload" not in projection
