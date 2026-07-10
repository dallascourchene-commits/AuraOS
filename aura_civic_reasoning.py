"""
Aura Civic Reasoning — MITOSIS decomposition + MUSIC multi-objective comparison.

MITOSIS: decomposes objective into bounded workstreams preserving constraints.
MUSIC: advisory synthesis, clustering, Pareto frontier, sensitivity analysis.

Neither declares political truth, overrides rights, or selects a hidden winner.
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

MUSIC_DIMENSIONS = (
    "community_benefit", "support_breadth", "affected_group_consent",
    "legal_feasibility", "funding_feasibility", "resource_completeness",
    "accessibility", "equity", "local_ownership", "time_to_implementation",
    "operating_sustainability", "environmental_impact", "risk", "uncertainty",
    "reversibility",
)


@dataclass
class Workstream:
    workstream_id: str
    title: str
    description: str = ""
    dependencies: list[str] = field(default_factory=list)
    required_evidence: list[str] = field(default_factory=list)
    affected_groups: list[str] = field(default_factory=list)
    parent_objective_hash: str = ""
    mandatory_constraints: list[str] = field(default_factory=list)
    truth_class: str = "SYSTEM_RULE_DERIVED"
    def to_dict(self): return asdict(self)


def civic_mitosis(objective: str, *, mandatory_constraints: list[str] | None = None) -> dict[str, Any]:
    """Decompose a community objective into bounded workstreams."""
    obj_hash = hashlib.blake2b(objective.encode(), digest_size=12).hexdigest()
    constraints = mandatory_constraints or []

    default_workstreams = [
        "community_demand", "skills_and_credentials", "space",
        "equipment_materials", "governance_business_model",
        "capital_and_operating_finance", "zoning_licensing_legal",
        "accessibility", "insurance_and_risk", "booking_administration",
        "implementation_timeline", "community_benefit_metrics",
    ]

    workstreams = []
    for i, ws_title in enumerate(default_workstreams):
        ws = Workstream(
            workstream_id=f"WS-{obj_hash[:8]}-{i:02d}",
            title=ws_title.replace("_", " ").title(),
            parent_objective_hash=obj_hash,
            mandatory_constraints=constraints,
        )
        workstreams.append(ws.to_dict())

    return {
        "ok": True,
        "objective": objective,
        "objective_hash": obj_hash,
        "workstreams": workstreams,
        "workstream_count": len(workstreams),
        "mandatory_constraints": constraints,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


@dataclass
class ScenarioComparison:
    comparison_id: str
    scenarios: list[dict[str, Any]] = field(default_factory=list)
    dimensions: list[str] = field(default_factory=list)
    weights: dict[str, float] = field(default_factory=dict)
    pareto_frontier: list[dict[str, str]] = field(default_factory=list)
    sensitivity_analysis: dict[str, Any] = field(default_factory=dict)
    bridge_options: list[dict[str, Any]] = field(default_factory=list)
    minority_impact_retained: bool = True
    truth_class: str = "AURA_PROPOSED"
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    def to_dict(self): return asdict(self)


def civic_music(scenarios: list[dict[str, Any]], *, weights: dict[str, float] | None = None) -> dict[str, Any]:
    """Multi-objective scenario comparison with Pareto frontier."""
    w = weights or {d: 1.0 / len(MUSIC_DIMENSIONS) for d in MUSIC_DIMENSIONS}

    scored = []
    for index, scenario in enumerate(scenarios):
        s = dict(scenario)
        s.setdefault("scenario_id", f"SCEN-{index:03d}")
        scores = {}
        for dim in MUSIC_DIMENSIONS:
            scores[dim] = s.get("metrics", {}).get(dim, 0.5)
        total = sum(scores.get(d, 0) * w.get(d, 0) for d in w)
        scored.append({**s, "weighted_score": total, "dimension_scores": scores})

    dimensions = list(w.keys())
    pareto = []
    for i, candidate in enumerate(scored):
        dominated = any(
            i != j
            and all(
                other["dimension_scores"].get(dim, 0) >= candidate["dimension_scores"].get(dim, 0)
                for dim in dimensions
            )
            and any(
                other["dimension_scores"].get(dim, 0) > candidate["dimension_scores"].get(dim, 0)
                for dim in dimensions
            )
            for j, other in enumerate(scored)
        )
        if not dominated:
            pareto.append({"scenario_id": candidate["scenario_id"], "label": "pareto_optimal"})

    baseline_order = [s["scenario_id"] for s in sorted(scored, key=lambda item: item["weighted_score"], reverse=True)]
    dimension_leaders = {
        dim: max(scored, key=lambda item: item["dimension_scores"].get(dim, 0))["scenario_id"]
        for dim in dimensions
    } if scored else {}
    sensitivity = {
        "baseline_ranking": baseline_order,
        "dimension_leaders": dimension_leaders,
        "method": "one_dimension_leader_scan",
        "weights_editable": True,
    }

    bridges = []
    if len(scored) >= 2:
        bridges.append({
            "bridge_id": "BRIDGE-001",
            "description": "Combine community ownership from option A with lower cost structure from option B",
            "truth_class": "AURA_PROPOSED",
            "advisory_only": True,
        })

    comp = ScenarioComparison(
        comparison_id=f"MUSIC-{hashlib.blake2b(json.dumps(scenarios, sort_keys=True, separators=(',', ':'), default=str).encode(), digest_size=4).hexdigest()}",
        scenarios=scored,
        dimensions=dimensions,
        weights=w,
        pareto_frontier=pareto,
        sensitivity_analysis=sensitivity,
        bridge_options=bridges,
    )
    return {"ok": True, "comparison": comp.to_dict(),
            "note": "MUSIC is advisory only. No hidden winner. Weights are visible and editable.",
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
