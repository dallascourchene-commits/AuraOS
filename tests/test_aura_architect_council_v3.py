from __future__ import annotations

from aura_architect_council_v3 import select_critic_lanes


def _candidate(tasks, *, rollback=None, risks=None):
    return {
        "candidate_id": "candidate",
        "plan": {
            "act_tasks": tasks,
            "rollback_conditions": list(rollback or []),
            "risk_map": list(risks or []),
        },
    }


def test_short_local_plan_uses_only_universal_critics() -> None:
    candidate = _candidate(
        [
            {
                "task_id": "A1",
                "target_file": "one.py",
                "related_files": [],
                "size": "S",
            }
        ]
    )
    assert select_critic_lanes(candidate) == ["scope", "tests"]


def test_dependency_plan_adds_sequence_and_rollback_without_uniform_cost_lane() -> None:
    candidate = _candidate(
        [
            {"task_id": "A1", "target_file": "one.py", "size": "M"},
            {
                "task_id": "A2",
                "target_file": "two.py",
                "depends_on": ["A1"],
                "size": "M",
            },
            {
                "task_id": "A3",
                "target_file": "three.py",
                "depends_on": ["A2"],
                "size": "M",
            },
            {"task_id": "A4", "target_file": "four.py", "size": "M"},
        ],
        rollback=["Restore compatibility adapter."],
    )
    lanes = select_critic_lanes(candidate)
    assert lanes == ["scope", "tests", "sequence", "rollback"]
    assert "cost" not in lanes
    assert "continuity" not in lanes


def test_long_plan_adds_continuity_but_only_adds_cost_under_cost_pressure() -> None:
    tasks = [
        {
            "task_id": f"A{index + 1}",
            "target_file": f"module_{index + 1}.py",
            "size": "M",
        }
        for index in range(8)
    ]
    lanes = select_critic_lanes(_candidate(tasks, risks=["Cross-module regression risk."]))
    assert lanes == ["scope", "tests", "continuity", "rollback"]
    assert "cost" not in lanes


def test_program_scale_plan_adds_cost_lane() -> None:
    tasks = [
        {
            "task_id": f"A{index + 1}",
            "target_file": f"module_{index + 1}.py",
            "size": "L" if index < 2 else "M",
        }
        for index in range(13)
    ]
    lanes = select_critic_lanes(_candidate(tasks))
    assert lanes == ["scope", "tests", "continuity", "rollback", "cost"]
