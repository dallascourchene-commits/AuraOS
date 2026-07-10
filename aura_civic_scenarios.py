"""Aura Civic Scenarios — What-If simulation + Pilot Tunnel.

What-If: SIMULATION_ONLY, NOT_A_PREDICTION, ASSUMPTION_DEPENDENT.
Pilot Tunnel: non-binding human-owned pilot packet.
"""
from __future__ import annotations
import hashlib, json, time
from dataclasses import dataclass, field, asdict
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

PILOT_STATUSES = ("NOT_STARTED","IN_DISCUSSION","OWNER_ACCEPTED","IN_PROGRESS","BLOCKED","COMPLETE","WITHDRAWN")


@dataclass
class WhatIfSimulation:
    sim_id: str
    base_scenario_id: str
    changed_assumptions: dict[str, Any] = field(default_factory=dict)
    unchanged_assumptions: list[str] = field(default_factory=list)
    affected_metrics: dict[str, float] = field(default_factory=dict)
    calculation_method: str = ""
    uncertainty: str = ""
    missing_data: list[str] = field(default_factory=list)
    invalid_comparisons: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=lambda: ["SIMULATION_ONLY","NOT_A_PREDICTION","ASSUMPTION_DEPENDENT"])
    truth_class: str = "AURA_PROPOSED"
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    def to_dict(self): return asdict(self)

def run_what_if(base_scenario: dict[str, Any], changes: dict[str, Any]) -> dict[str, Any]:
    payload = json.dumps({"base_scenario": base_scenario, "changes": changes}, sort_keys=True, separators=(",", ":"), default=str)
    sim = WhatIfSimulation(
        sim_id=f"WHATIF-{hashlib.blake2b(payload.encode(), digest_size=4).hexdigest()}",
        base_scenario_id=base_scenario.get("scenario_id",""),
        changed_assumptions=changes,
        unchanged_assumptions=[k for k in base_scenario.get("metrics",{}) if k not in changes],
        affected_metrics={k: v for k,v in changes.items() if isinstance(v,(int,float))},
        calculation_method="weighted_scenario_adjustment",
        uncertainty="high",
    )
    return {"ok": True, "simulation": sim.to_dict(),
            "labels": sim.labels,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


@dataclass
class PilotPacket:
    pilot_id: str
    scenario_ref: str
    minimum_viable_scope: str = ""
    requirements: list[str] = field(default_factory=list)
    responsible_roles: list[dict[str, str]] = field(default_factory=list)
    accepted_human_owners: list[str] = field(default_factory=list)
    legal_checks: list[str] = field(default_factory=list)
    funding_checks: list[str] = field(default_factory=list)
    safety_checks: list[str] = field(default_factory=list)
    timeline: str = ""
    success_metrics: list[str] = field(default_factory=list)
    stop_conditions: list[str] = field(default_factory=list)
    contingencies: list[str] = field(default_factory=list)
    review_date: str = ""
    authority_status: str = "NOT_STARTED"
    status: str = "NOT_STARTED"
    truth_class: str = "AURA_PROPOSED"
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    def to_dict(self): return asdict(self)

def create_pilot(scenario: dict[str, Any], *, timeline: str = "3 months") -> dict[str, Any]:
    payload = json.dumps(scenario, sort_keys=True, separators=(",", ":"), default=str)
    pilot = PilotPacket(
        pilot_id=f"PILOT-{hashlib.blake2b(payload.encode(), digest_size=4).hexdigest()}",
        scenario_ref=scenario.get("scenario_id",""),
        minimum_viable_scope=scenario.get("description","")[:200],
        timeline=timeline,
        authority_status="NOT_STARTED",
        status="NOT_STARTED",
    )
    return {"ok": True, "pilot": pilot.to_dict(),
            "note": "Aura may propose a role but may not assign responsibility without acceptance. No automatic spending or applications.",
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
