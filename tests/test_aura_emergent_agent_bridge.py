from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from aura_agent_arena_bridge import AuraAgentArenaBridge
from aura_agent_arena_persistence_bridge import PersistentAuraAgentArenaBridge


class FakeEmergentSpine:
    def __init__(self, packet: dict[str, Any]) -> None:
        self.packet = packet
        self.run_requests: list[dict[str, Any]] = []
        self.inventory_requests: list[dict[str, Any]] = []

    def run(self, request: dict[str, Any]) -> dict[str, Any]:
        self.run_requests.append(dict(request))
        return dict(self.packet)

    def atomic_inventory(self, **kwargs: Any) -> dict[str, Any]:
        self.inventory_requests.append(dict(kwargs))
        return {
            "ok": True,
            "version": "AURA_ATOMIC_FUNCTION_INVENTORY_V1",
            "total_count": 100,
            "emitted_count": 2,
            "inventory_digest": "inventory-digest",
            "atomic_functions": [
                {"file_path": "core.py", "symbol": "compute"},
                {"file_path": "caller.py", "symbol": "use_compute"},
            ],
            "production_mutation": False,
        }


def _grounded_packet() -> dict[str, Any]:
    return {
        "ok": True,
        "version": "AURA_EMERGENT_EVIDENCE_SPINE_V1",
        "packet_id": "EMERGENT-123",
        "packet_digest": "packet-digest",
        "grounding_ok": True,
        "status": "GROUNDED_ATOMIC_CLOSURE",
        "atomic_inventory": {
            "total_count": 100,
            "inventory_digest": "inventory-digest",
            "selected_count": 3,
            "selected_atomic_functions": [
                {"file_path": "core.py", "symbol": "compute", "source_hash": "compute-hash"},
                {"file_path": "caller.py", "symbol": "use_compute", "source_hash": "caller-hash"},
            ],
        },
        "tests": ["tests/test_core.py"],
        "waboose_focus_directives": [{"name": "atomic_closure_integrity"}],
        "projections": {
            "coding_arena": {
                "target_files": ["core.py", "caller.py"],
                "target_symbols": ["compute", "use_compute"],
                "acceptance_criteria": ["Preserve atomic source hashes."],
                "risk_map": ["dependency_closure_incomplete"],
                "constraints": ["Emergent evidence is advisory."],
                "tests": ["tests/test_core.py"],
                "waboose_focus_directives": [{"name": "atomic_closure_integrity"}],
            },
            "agent_bridge": {
                "target_file": "core.py",
                "target_symbol": "compute",
                "selected_atomic_functions": [{"file_path": "core.py", "symbol": "compute"}],
            },
        },
        "safe_to_patch": False,
        "production_mutation": False,
        "automatic_merge": False,
        "human_review_required": True,
        "patch_authority": "exact_source_spans_and_hashes_only",
        "vsa_patch_authority": False,
    }


@pytest.fixture
def bridge(tmp_path: Path) -> PersistentAuraAgentArenaBridge:
    return PersistentAuraAgentArenaBridge(repo_root=str(tmp_path))


def test_atomic_inventory_tool_forwards_request(bridge: PersistentAuraAgentArenaBridge) -> None:
    fake = FakeEmergentSpine(_grounded_packet())
    bridge.emergent_spine = fake
    result = bridge.aura_atomic_function_inventory(
        query="compute dependencies",
        target_files=["core.py"],
        target_symbols=["compute"],
        limit=12,
        include_source=True,
    )
    assert result["ok"] is True
    assert result["total_count"] == 100
    assert fake.inventory_requests[0]["target_symbols"] == ["compute"]


def test_emergent_evidence_tool_forwards_request(bridge: PersistentAuraAgentArenaBridge) -> None:
    fake = FakeEmergentSpine(_grounded_packet())
    bridge.emergent_spine = fake
    result = bridge.aura_emergent_evidence({
        "objective": "Improve compute",
        "target_arena": "agent_bridge",
        "target_symbols": ["compute"],
    })
    assert result["ok"] is True
    assert result["packet_id"] == "EMERGENT-123"


def test_prepare_preserves_explicit_target_and_merges_projection(
    bridge: PersistentAuraAgentArenaBridge,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeEmergentSpine(_grounded_packet())
    bridge.emergent_spine = fake
    captured: dict[str, Any] = {}

    def fake_prepare(self: AuraAgentArenaBridge, **kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        self._sessions["phase-1"] = {}
        return {"ok": True, "plan_phase_hash": "phase-1"}

    monkeypatch.setattr(AuraAgentArenaBridge, "aura_prepare_arena", fake_prepare)
    result = bridge.aura_prepare_arena(
        objective="Improve explicit target safely",
        target_file="explicit.py",
        target_symbol="explicit_symbol",
        acceptance_criteria=["Keep explicit behavior."],
        risk_map=["explicit_risk"],
        constraints=["Explicit constraint."],
        use_emergent_evidence=True,
        emergent_radius=2,
        emergent_max_atomic_nodes=80,
        emergent_include_source=False,
    )
    assert result["ok"] is True
    assert captured["target_file"] == "explicit.py"
    assert captured["target_symbol"] == "explicit_symbol"
    assert captured["acceptance_criteria"] == ["Keep explicit behavior.", "Preserve atomic source hashes."]
    assert captured["risk_map"] == ["explicit_risk", "dependency_closure_incomplete"]
    assert captured["constraints"] == ["Explicit constraint.", "Emergent evidence is advisory."]
    assert result["emergent_evidence"]["packet_id"] == "EMERGENT-123"
    assert bridge._sessions["phase-1"]["emergent_evidence"]["packet_digest"] == "packet-digest"


def test_prepare_infers_only_missing_target_fields(
    bridge: PersistentAuraAgentArenaBridge,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bridge.emergent_spine = FakeEmergentSpine(_grounded_packet())
    captured: dict[str, Any] = {}

    def fake_prepare(self: AuraAgentArenaBridge, **kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        self._sessions["phase-2"] = {}
        return {"ok": True, "plan_phase_hash": "phase-2"}

    monkeypatch.setattr(AuraAgentArenaBridge, "aura_prepare_arena", fake_prepare)
    result = bridge.aura_prepare_arena(
        objective="Infer the grounded atomic target",
        use_emergent_evidence=True,
    )
    assert result["ok"] is True
    assert captured["target_file"] == "core.py"
    assert captured["target_symbol"] == "compute"


def test_prepare_fails_closed_when_packet_is_not_grounded(
    bridge: PersistentAuraAgentArenaBridge,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = _grounded_packet()
    packet["grounding_ok"] = False
    packet["status"] = "ADVISORY_AFFINITY_ONLY"
    bridge.emergent_spine = FakeEmergentSpine(packet)
    called = False

    def fake_prepare(self: AuraAgentArenaBridge, **kwargs: Any) -> dict[str, Any]:
        nonlocal called
        called = True
        return {"ok": True}

    monkeypatch.setattr(AuraAgentArenaBridge, "aura_prepare_arena", fake_prepare)
    result = bridge.aura_prepare_arena(
        objective="Do not prepare from affinity only",
        use_emergent_evidence=True,
    )
    assert result["ok"] is False
    assert result["error_category"] == "missing_grounding"
    assert called is False


def test_without_flag_preserves_existing_behavior(
    bridge: PersistentAuraAgentArenaBridge,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_prepare(self: AuraAgentArenaBridge, **kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return {"ok": True, "plan_phase_hash": "legacy"}

    monkeypatch.setattr(AuraAgentArenaBridge, "aura_prepare_arena", fake_prepare)
    result = bridge.aura_prepare_arena(
        objective="Legacy preparation",
        target_file="legacy.py",
        target_symbol="legacy_symbol",
    )
    assert result["ok"] is True
    assert captured["target_file"] == "legacy.py"
    assert "emergent_evidence" not in result


def test_catalog_exposes_emergent_tools() -> None:
    names = {item["name"] for item in PersistentAuraAgentArenaBridge.list_tools()}
    assert "aura_atomic_function_inventory" in names
    assert "aura_emergent_evidence" in names
