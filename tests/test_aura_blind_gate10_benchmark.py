from __future__ import annotations

import importlib.util
import json
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "aura_blind_gate10_benchmark.py"
_spec = importlib.util.spec_from_file_location("aura_blind_gate10_benchmark", MODULE_PATH)
assert _spec and _spec.loader
bench = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bench)


def test_cell01_is_deterministic_and_has_27_slot_cases():
    tasks_a, keys_a = bench.generate_cell01(20260830, 70)
    tasks_b, keys_b = bench.generate_cell01(20260830, 70)
    assert bench.digest(tasks_a) == bench.digest(tasks_b)
    assert bench.digest(keys_a) == bench.digest(keys_b)
    assert all(task["width_bits"] == 27 for task in tasks_a)
    assert {task["mutation"] for task in tasks_a} >= {"clean", "missing", "corrupt_detectable", "conflicting_alias"}


def test_cell01_perfect_responses_score_exact_and_impossible_fabrication_is_penalized():
    tasks, keys = bench.generate_cell01(33, 100)
    saw_unknown = False
    for task, key in zip(tasks, keys):
        if key["expected_status"] == "VALUE":
            response = {
                "status": "VALUE",
                "value": key["expected_value"],
                "provenance": [{"slot": i, "source_id": f"s{i:02d}"} for i in range(27)],
            }
            assert bench.score_cell01(task, key, response)["exact"] is True
        else:
            saw_unknown = True
            assert bench.score_cell01(task, key, {"status": "UNKNOWN"})["exact"] is True
            fabricated = bench.score_cell01(task, key, {"status": "VALUE", "value": 0})
            assert fabricated["fabricated_completion"] is True
    assert saw_unknown


def test_currentness_scorer_rejects_stale_value():
    tasks, keys = bench.generate_cell02(91, 50)
    for task, key in zip(tasks, keys):
        if key["expected_status"] != "VALUE":
            continue
        stale_record = max((r for r in task["records"] if r["generation"] < key["expected_generation"]), key=lambda r: r["generation"])
        score = bench.score_cell02(
            task,
            key,
            {
                "status": "VALUE",
                "value": stale_record["value"],
                "source_id": stale_record["source_id"],
                "generation": stale_record["generation"],
            },
        )
        assert score["exact"] is False
        assert score["stale_answer"] is True
        break
    else:
        raise AssertionError("expected at least one VALUE currentness case")


def test_hallucination_scorer_separates_unknown_from_supported_value():
    tasks, keys = bench.generate_cell04(17, 80)
    unknown_seen = value_seen = False
    for task, key in zip(tasks, keys):
        if key["expected_status"] == "UNKNOWN" and not unknown_seen:
            unknown_seen = True
            wrong = bench.score_cell04(task, key, {"status": "VALUE", "value": "invented", "source_id": "made-up"})
            assert wrong["H_source"] == 1
            assert wrong["H_inference"] == 1
        elif key["expected_status"] == "VALUE" and not value_seen:
            value_seen = True
            right = bench.score_cell04(
                task,
                key,
                {"status": "VALUE", "value": key["expected_value"], "source_id": key["expected_source_id"]},
            )
            assert right["exact"] is True
        if unknown_seen and value_seen:
            break
    assert unknown_seen and value_seen


def test_public_manifest_does_not_reveal_randomized_arm_mapping(tmp_path: Path):
    bench.generate(tmp_path, 28082026)
    public = json.loads((tmp_path / "manifest.public.json").read_text(encoding="utf-8"))
    hidden = json.loads((tmp_path / "manifest.hidden.json").read_text(encoding="utf-8"))
    assert set(public["arm_labels"]) == {"ARM-X", "ARM-Y"}
    assert "CONTROL" not in json.dumps(public["arm_labels"])
    assert "AURA" not in json.dumps(public["arm_labels"])
    assert set(hidden["arm_mapping"].values()) == {"CONTROL", "AURA"}
    assert hidden["public_manifest_digest"] == bench.digest(public)


def test_generated_files_have_hash_manifest(tmp_path: Path):
    bench.generate(tmp_path, 44)
    checksums = json.loads((tmp_path / "SHA256SUMS.json").read_text(encoding="utf-8"))
    assert "manifest.public.json" in checksums
    assert "cell01.tasks.public.jsonl" in checksums
    assert "cell02.tasks.public.jsonl" in checksums
    assert "cell04.tasks.public.jsonl" in checksums
    assert "SHA256SUMS.json" not in checksums
