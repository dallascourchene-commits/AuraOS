"""Deterministic GLM-5.3 host-preflight feasibility reducer for AWJ032 G3.

This module does not benchmark the host or touch model weights. It consumes a
command-bound host measurement record and the preregistered GLM53 expert-I/O
floor, then calculates truthful reuse requirements for target latency classes.
Formal G3 admission remains gated on G1 hard-false + G2 tiny-fixture PASS.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping

SCHEMA = "GLM53HostPreflightReducerV1"
B_ROUTED_GB_PER_TOKEN = 22.6492416
B_SHARED_GB_PER_TOKEN = 2.8311552
B_EXPERT_COLD_GB_PER_TOKEN = B_ROUTED_GB_PER_TOKEN + B_SHARED_GB_PER_TOKEN


class PreflightError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _number(name: str, value: Any, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise PreflightError("INVALID_NUMBER", name)
    value = float(value)
    if value < 0 or (positive and value <= 0):
        raise PreflightError("INVALID_NUMBER", name)
    return value


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def observed_reuse(*, logical_expert_gb: float, physical_expert_gb: float) -> dict[str, Any]:
    logical = _number("logical_expert_gb", logical_expert_gb, positive=True)
    physical = _number("physical_expert_gb", physical_expert_gb)
    raw = 1.0 - physical / logical
    return {
        "raw_reuse": raw,
        "bounded_reuse": min(1.0, max(0.0, raw)),
        "io_amplification": physical > logical,
        "logical_expert_gb": logical,
        "physical_expert_gb": physical,
    }


def _target(
    *,
    bandwidth_gbps: float,
    target_seconds: float,
    non_storage_seconds: float,
    shared_reuse: float,
    fixed_other_gb: float,
) -> dict[str, Any]:
    b = _number("bandwidth_gbps", bandwidth_gbps, positive=True)
    t = _number("target_seconds", target_seconds, positive=True)
    c = _number("non_storage_seconds", non_storage_seconds)
    rs = _number("shared_reuse", shared_reuse)
    if rs > 1:
        raise PreflightError("INVALID_REUSE", "shared_reuse")
    fixed = _number("fixed_other_gb", fixed_other_gb)

    shared_physical = (1.0 - rs) * B_SHARED_GB_PER_TOKEN
    io_budget_seconds = t - c
    byte_budget = b * io_budget_seconds - shared_physical - fixed
    required_raw = 1.0 - byte_budget / B_ROUTED_GB_PER_TOKEN
    required_clamped = min(1.0, max(0.0, required_raw))
    min_possible_seconds = c + (shared_physical + fixed) / b
    attainable = required_raw <= 1.0 and t + 1e-12 >= min_possible_seconds
    return {
        "target_seconds_per_token": t,
        "bandwidth_gbps": b,
        "non_storage_seconds_per_token": c,
        "shared_reuse_assumption": rs,
        "shared_physical_gb_per_token": shared_physical,
        "fixed_other_gb_per_token": fixed,
        "routed_reuse_required_raw": required_raw,
        "routed_reuse_required_bounded": required_clamped,
        "minimum_possible_seconds_per_token_at_full_routed_reuse": min_possible_seconds,
        "attainable_under_assumptions": attainable,
    }


def reduce_host_preflight(
    *,
    measurement: Mapping[str, Any],
    targets_seconds_per_token: Mapping[str, Any],
    g1_hard_false_proven: bool,
    g2_tiny_fixture_pass: bool,
) -> dict[str, Any]:
    if not isinstance(measurement, Mapping):
        raise PreflightError("MEASUREMENT_REQUIRED")
    if not isinstance(targets_seconds_per_token, Mapping) or not targets_seconds_per_token:
        raise PreflightError("TARGETS_REQUIRED")
    if not isinstance(g1_hard_false_proven, bool) or not isinstance(g2_tiny_fixture_pass, bool):
        raise PreflightError("GATE_BOOLEAN_REQUIRED")

    bandwidth = _number("sustained_read_gbps", measurement.get("sustained_read_gbps"), positive=True)
    non_storage_raw = measurement.get("non_storage_seconds_per_token")
    fixed_raw = measurement.get("fixed_other_gb_per_token")
    non_storage_known = non_storage_raw is not None
    fixed_known = fixed_raw is not None
    non_storage = _number("non_storage_seconds_per_token", non_storage_raw) if non_storage_known else 0.0
    fixed = _number("fixed_other_gb_per_token", fixed_raw) if fixed_known else 0.0

    target_results: dict[str, Any] = {}
    for name, seconds in sorted(targets_seconds_per_token.items()):
        if not isinstance(name, str) or not name:
            raise PreflightError("TARGET_NAME_INVALID")
        target_results[name] = {
            "shared_resident": _target(
                bandwidth_gbps=bandwidth,
                target_seconds=seconds,
                non_storage_seconds=non_storage,
                shared_reuse=1.0,
                fixed_other_gb=fixed,
            ),
            "shared_cold": _target(
                bandwidth_gbps=bandwidth,
                target_seconds=seconds,
                non_storage_seconds=non_storage,
                shared_reuse=0.0,
                fixed_other_gb=fixed,
            ),
        }

    disk_free = measurement.get("disk_free_gb")
    required_storage = measurement.get("required_representation_gb")
    if disk_free is None or required_storage is None:
        storage_fit = "UNKNOWN"
    else:
        storage_fit = _number("disk_free_gb", disk_free) >= _number("required_representation_gb", required_storage)

    logical = {
        "schema": SCHEMA,
        "measurement": dict(measurement),
        "targets_seconds_per_token": dict(sorted((str(k), float(v)) for k, v in targets_seconds_per_token.items())),
        "expert_io_floor_gb_per_token": {
            "routed": B_ROUTED_GB_PER_TOKEN,
            "shared": B_SHARED_GB_PER_TOKEN,
            "aggregate": B_EXPERT_COLD_GB_PER_TOKEN,
        },
        "non_storage_cost_known": non_storage_known,
        "fixed_other_bytes_known": fixed_known,
        "unknown_costs_are_zero_only_for_optimistic_lower_bound": not (non_storage_known and fixed_known),
        "target_results": target_results,
        "storage_fit": storage_fit,
        "g1_hard_false_proven": g1_hard_false_proven,
        "g2_tiny_fixture_pass": g2_tiny_fixture_pass,
        "g3_formally_admitted": bool(g1_hard_false_proven and g2_tiny_fixture_pass),
        "large_checkpoint_admitted": False,
        "g4_admitted": False,
    }
    return {
        **logical,
        "logical_id": _digest(logical),
        "claim_ceiling": "G3_PREFLIGHT_REDUCER_ONLY_NO_HOST_BENCHMARK_OR_MODEL_WEIGHT_EFFECT",
    }
