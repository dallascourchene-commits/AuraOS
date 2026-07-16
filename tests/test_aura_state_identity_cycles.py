from __future__ import annotations

from types import SimpleNamespace

from aura_refactor_state_identity import canonical, digest
from aura_refactor_state_ledger import build_state_ledger


def _session(event):
    return SimpleNamespace(
        session_id="CYCLE",
        plan_phase_hash="PLAN",
        objective="cycle-safe identity",
        active_task_index=0,
        act_capsules=[],
        pending_turn=None,
        turns=[event],
        stage_results=[],
        verification_results=[],
        status="OPEN",
    )


def test_cyclic_event_container_is_bounded_and_deterministic() -> None:
    first: list[object] = []
    first.append(first)
    second: list[object] = []
    second.append(second)
    first_ledger = build_state_ledger(_session({"cycle": first}))
    second_ledger = build_state_ledger(_session({"cycle": second}))
    assert first_ledger.history_root_digest == second_ledger.history_root_digest
    assert "__cycle__" in canonical(first)


def test_opaque_objects_use_stable_type_identity_not_memory_address() -> None:
    one = object()
    two = object()
    assert digest(one) == digest(two)
    assert "0x" not in canonical(one)
