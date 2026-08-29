"""Bounded ThinkPad resident/Expert-Fabric routing policy.

This module is deliberately policy-only. It does not install models, widen authority,
or execute provider calls. The host resident supplies measured HostState and receives
a typed route/defer/human-gate decision.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HostState:
    available_ram_gib: float
    free_disk_gib: float
    on_ac_power: bool
    idle_minutes: float
    cpu_percent: float
    thermal_ok: bool = True
    foreground_heavy: bool = False


@dataclass(frozen=True)
class MaintenanceWork:
    task_class: str
    consequence_class: str = "D0"
    deterministic_sufficient: bool = False
    deep_reasoning: bool = False
    gate_target: int = 10


WARM_MODEL = "LiquidAI/LFM2.5-8B-A1B-GGUF:Q4_K_M"
COLD_MODEL = "openai/gpt-oss-20b"
AIRLLM_CANDIDATE = "Qwen/Qwen3-30B-A3B"


def choose_background_route(host: HostState, work: MaintenanceWork) -> dict[str, Any]:
    if work.consequence_class != "D0":
        return {"route": "HUMAN_GATE", "reason": "D1_PLUS_NOT_AUTONOMOUS_BACKGROUND"}
    if work.gate_target > 10:
        return {"route": "BLOCK", "reason": "BACKGROUND_STOPS_AT_GATE10"}
    if work.deterministic_sufficient:
        return {"route": "NO_MODEL"}

    if not host.on_ac_power or not host.thermal_ok or host.foreground_heavy:
        return {"route": "DEFER_MODEL_WORK", "reason": "POWER_THERMAL_FOREGROUND_GATE"}

    warm_eligible = (
        host.idle_minutes >= 5
        and host.available_ram_gib >= 7.0
        and host.free_disk_gib >= 12.0
        and host.cpu_percent <= 60.0
    )
    if warm_eligible and not work.deep_reasoning:
        return {"route": "LOCAL_WARM_MOE", "model": WARM_MODEL}

    if (
        work.deep_reasoning
        and host.idle_minutes >= 30
        and host.available_ram_gib >= 15.0
        and host.free_disk_gib >= 30.0
        and host.cpu_percent <= 35.0
    ):
        return {"route": "LOCAL_COLD_REASONER", "model": COLD_MODEL, "unload_warm_first": True}

    if work.deep_reasoning and host.idle_minutes >= 60 and host.free_disk_gib >= 80.0:
        return {
            "route": "AIRLLM_COLD_EXPERIMENTAL",
            "model": AIRLLM_CANDIDATE,
            "requires_separate_admission": True,
        }

    if warm_eligible:
        return {"route": "LOCAL_WARM_MOE", "model": WARM_MODEL, "reason": "DEEP_SLOT_NOT_EARNED"}
    return {"route": "DEFER_MODEL_WORK", "reason": "RESOURCE_GATE"}
