from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))

from aura_arena_triads import (
    ArenaTriadBudgetExceeded,
    ArenaTriadStale,
    LeafResult,
    execute_arena_triads,
)


class FakeExecutor:
    def __init__(self):
        self.calls = []

    def __call__(self, call):
        self.calls.append(call)
        return LeafResult(
            status="OK",
            payload={
                "claims": [call.role],
                "evidence": [f"evidence:{call.role}"],
                "dissent": [f"dissent:{call.role}"] if "CHALLENGE" in call.role else [],
                "residuals": [f"residual:{call.role}"] if "VERIFY" in call.role else [],
                "reopen": [],
                "next_action": f"next:{call.role}",
                "claim_ceiling": "MODEL_OUTPUT_ONLY",
            },
            provider="deepseek",
            model="test",
            provider_attempt_id=f"attempt-{len(self.calls)}",
            usage={"total_tokens": 10},
        )


def command(mode="INDEPENDENT_RECIPROCAL", cells=1):
    return {
        "command_id": "AWJ026-TEST",
        "idempotency_key": f"AWJ026-TEST-{mode}-{cells}",
        "arena_head": "AWJ-001@GEN24:abc",
        "objective": "test objective",
        "mode": mode,
        "max_leaf_calls": 100,
        "max_concurrency": 9,
        "cells": [
            {
                "cell_id": f"CELL-{i}",
                "objective": f"cell {i}",
                "source_refs": ["SRC"],
                "constraints": ["D0"],
            }
            for i in range(cells)
        ],
    }


def test_independent_mode_is_seven_calls_and_first_three_are_independent(tmp_path):
    fake = FakeExecutor()
    result = execute_arena_triads(
        command(), current_arena_head="AWJ-001@GEN24:abc",
        leaf_executor=fake, output_root=tmp_path
    )
    assert result["planned_leaf_calls"] == 7
    assert [c.role for c in fake.calls[:3]] == ["A_CONSTRUCT", "B_CHALLENGE", "C_VERIFY"]
    assert all(not c.prior_artifacts for c in fake.calls[:3])
    assert [c.role for c in fake.calls[3:6]] == ["BASE_TRIAD_A", "BASE_TRIAD_B", "BASE_TRIAD_C"]
    assert fake.calls[6].role == "FINAL_DIMENSIONAL_REBASE"
    assert len(list((tmp_path/result["idempotency_key"]/"leaves"/"CELL-0").glob("*.json"))) == 7


def test_staggered_mode_is_four_calls_with_ordered_dependencies(tmp_path):
    fake = FakeExecutor()
    result = execute_arena_triads(
        command("STAGGERED_EFFICIENT"),
        current_arena_head="AWJ-001@GEN24:abc",
        leaf_executor=fake, output_root=tmp_path
    )
    assert result["planned_leaf_calls"] == 4
    assert [c.role for c in fake.calls] == ["A_CONSTRUCT", "B_CHALLENGE", "C_VERIFY", "A_REBASE"]
    assert "A_CONSTRUCT" in fake.calls[1].prior_artifacts
    assert set(fake.calls[2].prior_artifacts) == {"A_CONSTRUCT", "B_CHALLENGE"}


def test_hyperscale_parallelizes_independent_cells(tmp_path):
    fake = FakeExecutor()
    result = execute_arena_triads(
        command(cells=3), current_arena_head="AWJ-001@GEN24:abc",
        leaf_executor=fake, output_root=tmp_path
    )
    assert result["planned_leaf_calls"] == 21
    assert {x["cell_id"] for x in result["cells"]} == {"CELL-0", "CELL-1", "CELL-2"}


def test_stale_head_blocks_before_leaf_effect(tmp_path):
    fake = FakeExecutor()
    try:
        execute_arena_triads(
            command(), current_arena_head="AWJ-001@GEN25:def",
            leaf_executor=fake, output_root=tmp_path
        )
    except ArenaTriadStale:
        pass
    else:
        raise AssertionError("expected stale")
    assert fake.calls == []


def test_budget_blocks_before_leaf_effect(tmp_path):
    fake = FakeExecutor()
    raw = command(cells=2)
    raw["max_leaf_calls"] = 13
    try:
        execute_arena_triads(
            raw, current_arena_head="AWJ-001@GEN24:abc",
            leaf_executor=fake, output_root=tmp_path
        )
    except ArenaTriadBudgetExceeded:
        pass
    else:
        raise AssertionError("expected budget error")
    assert fake.calls == []


def test_replay_uses_terminal_result_without_new_effect(tmp_path):
    fake = FakeExecutor()
    raw = command()
    first = execute_arena_triads(
        raw, current_arena_head="AWJ-001@GEN24:abc",
        leaf_executor=fake, output_root=tmp_path
    )
    n = len(fake.calls)
    second = execute_arena_triads(
        raw, current_arena_head="AWJ-001@GEN24:abc",
        leaf_executor=fake, output_root=tmp_path
    )
    assert len(fake.calls) == n
    assert second["idempotent_replay"] is True
    assert second["result_digest"] == first["result_digest"]


def test_child_idempotency_keys_are_unique(tmp_path):
    fake = FakeExecutor()
    execute_arena_triads(
        command(), current_arena_head="AWJ-001@GEN24:abc",
        leaf_executor=fake, output_root=tmp_path
    )
    keys = [c.child_idempotency_key for c in fake.calls]
    assert len(keys) == len(set(keys))


def test_leaf_results_are_persisted_before_dependents(tmp_path):
    observed = []

    class CheckingExecutor(FakeExecutor):
        def __call__(self, call):
            if call.sequence > 1:
                prev = list((tmp_path/call.parent_idempotency_key/"leaves"/call.cell_id).glob("*.json"))
                observed.append(len(prev))
            return super().__call__(call)

    fake = CheckingExecutor()
    execute_arena_triads(
        command("STAGGERED_EFFICIENT"),
        current_arena_head="AWJ-001@GEN24:abc",
        leaf_executor=fake, output_root=tmp_path
    )
    assert observed == [1, 2, 3]
