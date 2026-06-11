"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8b7-[Q-SYS:D4FAE19AB3EF864B]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: dataclasses, aura_nesy_sat_reasoner, aura_ontology_circuit, os, numpy, aura_spvm, __future__, json
FUNCTIONS: speculative_topology_check, validate_proposed_mutation, human_report
SYNOPSIS: The `aura_os_audit_core` module provides strict structural validation and speculative mutation analysis for Aura OS environments, leveraging `dataclasses`, `aura_nesy_sat_reasoner`, `aura_ontology_circuit`, `os`, `numpy`, `aura_spvm`, `__future__`, and `json` to execute `speculative_topology_check` for topological integrity, `validate_proposed_mutation` for mutation safety, and `human_report` for human-readable diagnostic output.
[/AURA_MASTER_KEY]
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

import numpy as np

from aura_ontology_circuit import CircuitVerdict, get_ontology_circuit
from aura_nesy_sat_reasoner import batch_evaluate_implication
from aura_spvm import get_semantic_vector


@dataclass
class MutationVerdict:
    approved: bool
    shield_ok: bool
    circuit: CircuitVerdict
    topology_ok: bool
    topology_note: str = ""
    friction_delta: int | None = None
    reasons: list[str] = field(default_factory=list)

    def human_report(self) -> str:
        parts = []
        if not self.shield_ok:
            parts.append("shield_fail")
        if not self.circuit.consistent:
            parts.extend(self.circuit.violations)
        if not self.topology_ok:
            parts.append(self.topology_note or "topology_fail")
        if self.approved:
            return "APPROVED"
        return "REJECTED: " + "; ".join(parts) if parts else "REJECTED"


def speculative_topology_check(
    module_name: str,
    topo_path: str = "Aura_Memory/live_topology_ast.json",
    *,
    sweep_dim: int = 512,
    fracture_floor: float = 0.55,
) -> tuple[bool, str]:
    """
    O(E_local) SPVM screen on explicit edges touching the target module.
    Returns (ok, note). Missing topology is non-fatal (pass).
    """
    if not os.path.exists(topo_path):
        return True, "topology_absent_skip"

    with open(topo_path, "r", encoding="utf-8") as f:
        topo = json.load(f)

    nodes = topo.get("nodes", [])
    edges = topo.get("edges", [])
    if not nodes or not edges:
        return True, "topology_empty_skip"

    needle = module_name.replace(".py", "")
    related: list[tuple[str, str, str]] = []
    for edge in edges:
        if not isinstance(edge, (list, tuple)) or len(edge) < 3:
            continue
        src, tgt, etype = edge[0], edge[1], edge[2]
        if etype != "explicit_function_call":
            continue
        if needle in src or needle in tgt:
            related.append((src, tgt, etype))

    if not related:
        return True, "no_explicit_edges_for_module"

    worst = 1.0
    for src, tgt, _ in related:
        v_src = get_semantic_vector(src, dim=sweep_dim)
        v_tgt = get_semantic_vector(tgt, dim=sweep_dim)
        impl = float(batch_evaluate_implication(
            np.asarray([v_src]), np.asarray([v_tgt])
        )[0])
        worst = min(worst, impl)
        if impl < fracture_floor:
            return (
                False,
                f"SPVM implication {impl:.2%} on {src}->{tgt} "
                f"(floor {fracture_floor:.0%})",
            )

    return True, f"min_implication={worst:.2%} across {len(related)} edges"


def validate_proposed_mutation(
    source: str,
    *,
    module_name: str | None = None,
    baseline_friction: int | None = None,
    proposed_friction: int | None = None,
    check_topology: bool = True,
) -> MutationVerdict:
    circuit = get_ontology_circuit()
    circuit_result = circuit.evaluate_source(
        source,
        baseline_friction=baseline_friction,
        proposed_friction=proposed_friction,
    )
    shield_ok = not any(v.startswith("SHIELD:") for v in circuit_result.violations)

    topo_ok = True
    topo_note = ""
    if check_topology and module_name:
        topo_ok, topo_note = speculative_topology_check(module_name)

    friction_delta = None
    if baseline_friction is not None and proposed_friction is not None:
        friction_delta = baseline_friction - proposed_friction

    approved = circuit_result.consistent and topo_ok

    reasons: list[str] = []
    if not shield_ok:
        reasons.append("symbolic_shield")
    if not circuit_result.consistent:
        reasons.extend(circuit_result.violations)
    if not topo_ok:
        reasons.append(topo_note)

    return MutationVerdict(
        approved=approved,
        shield_ok=shield_ok,
        circuit=circuit_result,
        topology_ok=topo_ok,
        topology_note=topo_note,
        friction_delta=friction_delta,
        reasons=reasons,
    )
