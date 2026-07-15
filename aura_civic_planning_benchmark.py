"""Deterministic structural-parity benchmark for P8 Civic Commons planning."""
from __future__ import annotations

from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from aura_civic_planning import PATCH_AUTHORITY, VSA_PATCH_AUTHORITY, inspect_civic_commons_planning_compatibility
from aura_civic_planning_inventory import build_civic_surface_inventory
from aura_civic_planning_types import CivicCompatibilityStatus
from aura_event_contracts import canonical_json

VERSION = "AURA_CIVIC_PLANNING_BENCHMARK_P8"


def _profile() -> dict[str, Any]:
    value = {
        "schema_version": "AURA_CIVIC_PROFILE_SET_V1",
        "jurisdiction_profile_refs": ["jurisdiction://fixture"],
        "community_governance_profile_ref": "community://fixture",
    }
    value["digest"] = hashlib.blake2b(json.dumps(value, sort_keys=True, default=str).encode(), digest_size=12).hexdigest()
    return value


def build_case_records(case_id: str, *, responses: list[str], include_decision_packet: bool = True, mutate_note: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    objective = f"Create a bounded Civic Commons planning shadow for {case_id}"
    objective_hash = hashlib.blake2b(objective.encode(), digest_size=12).hexdigest()
    constraints = ["human_authority", "community_authority", "non_binding_outputs"]
    workstreams = [
        {"workstream_id": f"WS-{case_id}-00", "title": "Record Evidence", "description": "Record bounded proposal evidence.", "dependencies": [], "parent_objective_hash": objective_hash, "mandatory_constraints": constraints, "truth_class": "SYSTEM_RULE_DERIVED"},
        {"workstream_id": f"WS-{case_id}-01", "title": "Review Reversible Pilot", "description": "Prepare a non-binding pilot for human review.", "dependencies": [f"WS-{case_id}-00"], "parent_objective_hash": objective_hash, "mandatory_constraints": constraints, "truth_class": "SYSTEM_RULE_DERIVED"},
    ]
    scenario = {"scenario_id": f"SCEN-{case_id}", "title": "Fixture scenario", "truth_class": "AURA_PROPOSED", "note": mutate_note}
    arc = {"proposal_ref": scenario["scenario_id"], "responses": [{"response_type": item, "binding": False} for item in responses], "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    convergence = {"status": "RECORDED_NON_BINDING_INPUT", "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    pilot = {"pilot_id": f"PILOT-{case_id}", "scenario_ref": scenario["scenario_id"], "status": "NOT_STARTED", "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    project = {"project_id": f"project-{case_id}", "objective": objective, "mandatory_constraints": constraints, "non_binding": True, "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    session = {
        "session_id": f"CIVIC-{case_id}", "project_id": project["project_id"], "objective": objective, "objective_hash": objective_hash,
        "mandatory_constraints": constraints, "profile_set": _profile(), "workstreams": deepcopy(workstreams), "scenarios": [deepcopy(scenario)],
        "consent_arc": deepcopy(arc), "convergence": deepcopy(convergence), "pilot": deepcopy(pilot), "decision_packet": {},
        "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
    if include_decision_packet:
        session["decision_packet"] = {
            "packet_id": f"PACKET-{case_id}",
            "objective": objective,
            "active_profiles": list(session["profile_set"]["jurisdiction_profile_refs"]),
            "workstreams": deepcopy(workstreams),
            "scenarios": [deepcopy(scenario)],
            "consent_arc": deepcopy(arc),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
    return project, session


def _token_proxy(text: str) -> int:
    return (len(text.encode("utf-8")) + 3) // 4


def run_benchmark(*, repeats: int = 4, repo_root: str | Path | None = None) -> dict[str, Any]:
    if type(repeats) is not int or repeats < 2:
        raise ValueError("repeats must be an integer >= 2")
    inventory = build_civic_surface_inventory(repo_root)
    cases = (
        ("recorded-support", ["CONSENT"], True),
        ("recorded-reservation", ["CONSENT_WITH_RESERVATION"], True),
        ("recorded-objection", ["CRITICAL_OBJECTION"], True),
        ("recorded-withdrawal", ["WITHDRAW"], True),
        ("mixed-records", ["CONSENT", "ABSTAIN", "OBJECT"], True),
        ("missing-decision", ["CONSENT"], False),
    )
    records: list[dict[str, Any]] = []
    action_ids: list[str] = []
    baseline_bytes = candidate_bytes = mapped = total_workstreams = 0
    mutation_drift = authority_drift = deterministic_failures = 0
    for case_id, responses, include_decision in cases:
        project, session = build_case_records(case_id, responses=responses, include_decision_packet=include_decision)
        original_project, original_session = deepcopy(project), deepcopy(session)
        runs = [inspect_civic_commons_planning_compatibility(project, session, inventory=inventory) for _ in range(repeats)]
        rendered = [canonical_json(item.to_dict()) for item in runs]
        deterministic = len(set(rendered)) == 1
        result = runs[0]
        if not deterministic:
            deterministic_failures += 1
        if project != original_project or session != original_session:
            mutation_drift += 1
        if result.report.authority_changed:
            authority_drift += 1
        count = len(session["workstreams"])
        total_workstreams += count
        mapped += result.report.mapped_action_count
        if result.board:
            action_ids.extend(item.action_id for item in result.board.actions)
        baseline = canonical_json({"project": project, "session": session})
        candidate = canonical_json(result.to_dict())
        baseline_bytes += len(baseline.encode())
        candidate_bytes += len(candidate.encode())
        records.append({
            "case_id": case_id,
            "status": result.report.status.value,
            "workstream_count": count,
            "mapped_action_count": result.report.mapped_action_count,
            "deterministic": deterministic,
            "governance_blockers": list(result.report.governance_blockers),
            "report_digest": result.report.digest,
        })
    passed = sum(
        item["status"] == CivicCompatibilityStatus.BLOCKED_BY_GOVERNANCE.value
        and item["mapped_action_count"] == item["workstream_count"]
        and item["deterministic"]
        for item in records
    )
    collisions = len(action_ids) - len(set(action_ids))
    result = {
        "version": VERSION,
        "measurement_class": "EMPIRICAL_FIXTURE_WITH_HEURISTIC_TOKEN_PROXY",
        "total_cases": len(records), "passed_cases": passed,
        "total_workstreams": total_workstreams, "mapped_actions": mapped,
        "action_coverage": mapped / total_workstreams,
        "deterministic_case_rate": (len(records) - deterministic_failures) / len(records),
        "all_governance_blocked": all(item["status"] == CivicCompatibilityStatus.BLOCKED_BY_GOVERNANCE.value for item in records),
        "mutation_drift_count": mutation_drift, "authority_drift_count": authority_drift,
        "identifier_collision_count": collisions,
        "baseline_bytes": baseline_bytes, "candidate_bytes": candidate_bytes,
        "baseline_token_proxy": _token_proxy("x" * baseline_bytes),
        "candidate_token_proxy": _token_proxy("x" * candidate_bytes),
        "cases": records,
        "limitations": [
            "Fixture measurements do not prove general latency, token, model-quality, or governance improvement.",
            "The adapter records Civic evidence by digest and does not determine consent sufficiency.",
        ],
    }
    result["gate_passed"] = (
        passed == len(records) and mapped == total_workstreams and result["action_coverage"] == 1.0
        and result["deterministic_case_rate"] == 1.0 and result["all_governance_blocked"]
        and mutation_drift == authority_drift == collisions == 0
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--repeats", type=int, default=4)
    args = parser.parse_args()
    payload = run_benchmark(repeats=args.repeats)
    text = canonical_json(payload) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if payload["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
