#!/usr/bin/env python3
"""Matched D0 benchmark over the deterministic BugBot ground-truth lab.

This benchmark measures one narrow capability: whether a differential-oracle
BugHound route detects seeded behavioral divergence that a simple smoke-only
control misses.  Because the trusted fixed variant is available to the BugHound
route, this is TRAIN_REFERENCE evidence only; it is not a claim about blind
real-world vulnerability discovery.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable

from scripts.bughound_bugbot_lab import CASES, run_case

SCHEMA = "BugHoundMatchedBenchmarkV1"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Task:
    task_id: str
    case_id: str
    variant: str
    expected_defect: bool

    def public_packet(self) -> dict[str, Any]:
        # No expected label or fixed-output answer is exposed here.
        return {
            "schema": SCHEMA,
            "task_id": self.task_id,
            "case_id": self.case_id,
            "variant": self.variant,
            "instruction": "Return DEFECT if the route establishes an invariant-breaking behavioral divergence; otherwise NO_DEFECT.",
        }

    def hidden_key(self) -> dict[str, Any]:
        packet = self.public_packet()
        return {
            "task_id": self.task_id,
            "expected_defect": self.expected_defect,
            "public_digest": _digest(packet),
        }


def task_bank() -> tuple[Task, ...]:
    rows = []
    for case in CASES:
        rows.append(Task(f"{case.case_id}-BUGGY", case.case_id, "buggy", True))
        rows.append(Task(f"{case.case_id}-FIXED", case.case_id, "fixed", False))
    return tuple(rows)


def control_smoke_route(task: Task) -> bool:
    """Simple control: only crashes/type failures count as a defect."""
    try:
        run_case(task.case_id, task.variant)
    except Exception:
        return True
    return False


def bughound_differential_route(task: Task) -> bool:
    """Known-bug differential oracle route for TRAIN_REFERENCE cases."""
    candidate = run_case(task.case_id, task.variant)
    trusted_fixed = run_case(task.case_id, "fixed")
    return candidate != trusted_fixed


def _score(tasks: tuple[Task, ...], route: Callable[[Task], bool]) -> dict[str, Any]:
    tp = fp = tn = fn = 0
    rows = []
    for task in tasks:
        predicted = bool(route(task))
        expected = task.expected_defect
        if predicted and expected:
            tp += 1
        elif predicted and not expected:
            fp += 1
        elif not predicted and not expected:
            tn += 1
        else:
            fn += 1
        rows.append({"task_id": task.task_id, "predicted_defect": predicted, "expected_defect": expected})

    precision = None if tp + fp == 0 else tp / (tp + fp)
    recall = None if tp + fn == 0 else tp / (tp + fn)
    specificity = None if tn + fp == 0 else tn / (tn + fp)
    accuracy = (tp + tn) / len(tasks) if tasks else None
    return {
        "task_count": len(tasks),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "accuracy": accuracy,
        "rows": rows,
    }


def run_matched_benchmark() -> dict[str, Any]:
    tasks = task_bank()
    public_packets = [task.public_packet() for task in tasks]
    hidden_keys = [task.hidden_key() for task in tasks]
    control = _score(tasks, control_smoke_route)
    bughound = _score(tasks, bughound_differential_route)

    summary = {
        "schema": SCHEMA,
        "visibility": "TRAIN_REFERENCE",
        "case_count": len(CASES),
        "task_count": len(tasks),
        "public_bank_digest": _digest(public_packets),
        "hidden_key_digest": _digest(hidden_keys),
        "control": {k: v for k, v in control.items() if k != "rows"},
        "bughound": {k: v for k, v in bughound.items() if k != "rows"},
        "negative_findings": [
            "CONTROL_SMOKE has no seeded false positives but cannot detect non-crashing semantic defects in this lab.",
            "BUGHOUND_DIFFERENTIAL consumes a trusted fixed reference, so its result does not estimate blind real-world hunt recall.",
            "LATTICE_REGISTRY_GAP remains active; no eight-lattice performance claim is measured or implied.",
        ],
        "hyper_scale": "HS1",
        "physical_fanout_earned": False,
        "claim_ceiling": "D0_TRAIN_REFERENCE_DIFFERENTIAL_ORACLE_WIRING_ONLY",
    }
    return {**summary, "receipt_digest": _digest(summary)}


if __name__ == "__main__":
    print(json.dumps(run_matched_benchmark(), indent=2, sort_keys=True))
