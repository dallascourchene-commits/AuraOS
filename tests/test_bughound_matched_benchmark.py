from __future__ import annotations

from scripts.bughound_matched_benchmark import run_matched_benchmark, task_bank


def test_task_bank_is_matched_buggy_fixed_per_case():
    tasks = task_bank()
    assert len(tasks) == 24
    by_case = {}
    for task in tasks:
        by_case.setdefault(task.case_id, set()).add(task.variant)
    assert len(by_case) == 12
    assert all(variants == {"buggy", "fixed"} for variants in by_case.values())


def test_public_packets_do_not_expose_hidden_expected_label():
    for task in task_bank():
        packet = task.public_packet()
        assert "expected_defect" not in packet
        key = task.hidden_key()
        assert key["expected_defect"] is task.expected_defect
        assert len(key["public_digest"]) == 64


def test_matched_benchmark_has_expected_observable_counts():
    receipt = run_matched_benchmark()
    assert receipt["case_count"] == 12
    assert receipt["task_count"] == 24
    assert receipt["control"] == {
        "task_count": 24,
        "tp": 0,
        "fp": 0,
        "tn": 12,
        "fn": 12,
        "precision": None,
        "recall": 0.0,
        "specificity": 1.0,
        "accuracy": 0.5,
    }
    assert receipt["bughound"] == {
        "task_count": 24,
        "tp": 12,
        "fp": 0,
        "tn": 12,
        "fn": 0,
        "precision": 1.0,
        "recall": 1.0,
        "specificity": 1.0,
        "accuracy": 1.0,
    }


def test_claim_ceiling_prevents_blind_hunt_or_lattice_overclaim():
    receipt = run_matched_benchmark()
    assert receipt["visibility"] == "TRAIN_REFERENCE"
    assert receipt["hyper_scale"] == "HS1"
    assert receipt["physical_fanout_earned"] is False
    assert receipt["claim_ceiling"] == "D0_TRAIN_REFERENCE_DIFFERENTIAL_ORACLE_WIRING_ONLY"
    assert any("trusted fixed reference" in item for item in receipt["negative_findings"])
    assert any("LATTICE_REGISTRY_GAP" in item for item in receipt["negative_findings"])


def test_receipt_is_deterministic():
    first = run_matched_benchmark()
    second = run_matched_benchmark()
    assert first == second
    assert len(first["public_bank_digest"]) == 64
    assert len(first["hidden_key_digest"]) == 64
    assert len(first["receipt_digest"]) == 64
