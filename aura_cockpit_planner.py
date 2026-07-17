"""
Aura Cockpit Planner — GOAP + Phase Capsule planning.

Dependencies: stdlib only. All Aura imports are lazy.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from hashlib import sha256
import json
import math
from pathlib import PurePosixPath
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
PLANNER_VERSION = "AURA_COCKPIT_PLANNER_V1"
GROUNDED_CAPSULE_COMPILER_VERSION = "AURA_GROUNDED_PHASE_CAPSULE_COMPILER_V1"

_PHASES = [
    ("discovery", "Discover relevant files and symbols through CODEMAP."),
    ("grounding", "Ground through Coding Arena for exact source spans."),
    ("planning", "Plan the approach using FST routing and GOAP."),
    ("agent_handoff", "Prepare agent handoff packet."),
    ("patch", "Agent proposes patch through Arena staging."),
    ("verification", "Run verifier and tests."),
    ("repair", "Produce repair packet if tests fail."),
    ("approval", "Human approves commit."),
    ("pr", "Open pull request."),
]

_DENIED_ROUTES = frozenset({"BLOCKED_WITH_REASON", "LOCALIZE_FIRST"})


def plan_objective_with_goap(
    objective: str,
    repo_root: str = ".",
    initial_state: dict | None = None,
    goal_conditions: dict | None = None,
) -> dict:
    """Plan objective with GOAP planner."""
    plan = {"phases": [], "actions": []}
    try:
        from aura_goal_planner import AuraGOAPPlanner

        planner = AuraGOAPPlanner()
        result = planner.plan(objective, initial_state or {}, goal_conditions or {})
        if hasattr(result, "actions"):
            plan["actions"] = [
                action.to_dict() if hasattr(action, "to_dict") else action
                for action in result.actions
            ]
    except Exception:
        pass
    for phase_name, description in _PHASES:
        plan["phases"].append(
            {
                "phase": phase_name,
                "description": description,
                "allowed_actions": [f"{phase_name}_step"],
                "blocked_actions": (
                    ["patch"]
                    if phase_name in ("discovery", "grounding", "planning")
                    else []
                ),
                "required_evidence": (
                    ["grounding_ok"] if phase_name == "grounding" else []
                ),
                "token_budget": {},
                "output_packet": f"{phase_name}_packet",
                "human_approval_required": phase_name
                in ("agent_handoff", "approval", "pr"),
            }
        )
    return {
        "ok": True,
        "objective": objective,
        "plan": plan,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def objective_to_phase_capsules(
    objective: str,
    repo_root: str = ".",
    grounding_packet: Mapping[str, Any] | None = None,
) -> dict:
    """Decompose an objective into legacy or exact-grounded phase capsules."""
    if grounding_packet is None:
        capsules = [
            {
                "phase": phase_name,
                "description": description,
                "objective": objective,
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }
            for phase_name, description in _PHASES
        ]
        return {
            "ok": True,
            "phase_capsules": capsules,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    compiled = _compile_grounding_evidence(grounding_packet)
    if not compiled["ok"]:
        route = grounding_packet.get("route") if isinstance(grounding_packet, Mapping) else None
        return {
            "ok": False,
            "error": compiled["error"],
            "route": route,
            "phase_capsules": [],
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    evidence = compiled["grounding_evidence"]
    evidence_id = compiled["grounding_evidence_id"]
    capsules = [
        {
            "phase": phase_name,
            "description": description,
            "objective": objective,
            "grounding_evidence_id": evidence_id,
            "scope_ref": "grounding_evidence.allowed_files",
            "tests_ref": "grounding_evidence.required_tests",
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        for phase_name, description in _PHASES
    ]
    return {
        "ok": True,
        "compiler_version": GROUNDED_CAPSULE_COMPILER_VERSION,
        "phase_capsules": capsules,
        "grounding_evidence_id": evidence_id,
        "grounding_evidence": evidence,
        "context_cost_accounting": _context_cost_accounting(capsules, evidence),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def compile_grounded_phase_capsules(
    objective: str,
    repo_root: str = ".",
    target_symbol: str | None = None,
    external_call: str | None = None,
) -> dict:
    """Ground an objective through Coding Arena, then compile phase capsules."""
    from aura_coding_arena_grounding import ground_coding_arena_intent

    grounding_packet = ground_coding_arena_intent(
        objective,
        repo_root,
        target_symbol=target_symbol,
        external_call=external_call,
    )
    return objective_to_phase_capsules(
        objective,
        repo_root=repo_root,
        grounding_packet=grounding_packet,
    )


def _compile_grounding_evidence(
    grounding_packet: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(grounding_packet, Mapping):
        return _compile_denial("grounding_packet_must_be_a_mapping")
    if grounding_packet.get("vsa_patch_authority") is not False:
        return _compile_denial("vsa_patch_authority_must_be_false")

    authorities = [
        grounding_packet.get("safety_policy"),
        grounding_packet.get("patch_authority"),
    ]
    declared = [item for item in authorities if item is not None]
    if not declared:
        return _compile_denial("exact_patch_authority_required")
    if any(item != PATCH_AUTHORITY for item in declared):
        return _compile_denial("grounding_patch_authority_mismatch")
    if grounding_packet.get("grounding_ok") is not True:
        return _compile_denial("grounding_not_admitted")

    try:
        route = _canonical_text(grounding_packet.get("route"), "route")
    except ValueError:
        return _compile_denial("canonical_grounding_route_required")
    if route in _DENIED_ROUTES:
        return _compile_denial("grounding_route_not_patch_admitted")

    raw_hashes = grounding_packet.get("hashes")
    if not isinstance(raw_hashes, Mapping):
        return _compile_denial("source_hashes_must_be_a_mapping")
    try:
        hashes = {
            _canonical_text(key, "source_hash_key"): _canonical_text(
                value, "source_hash_value"
            )
            for key, value in raw_hashes.items()
        }
    except ValueError:
        return _compile_denial("canonical_source_hashes_required")
    if not hashes:
        return _compile_denial("exact_source_hashes_required")

    raw_spans = grounding_packet.get("source_spans")
    if not _is_sequence(raw_spans):
        return _compile_denial("source_spans_must_be_a_sequence")
    if not raw_spans:
        return _compile_denial("exact_source_spans_required")

    source_spans: list[dict[str, Any]] = []
    allowed_files: set[str] = set()
    try:
        for raw_span in raw_spans:
            if not isinstance(raw_span, Mapping):
                raise ValueError("source_span_must_be_a_mapping")
            span = _canonical_value(raw_span)
            file_path = _repo_path(span.get("file_path"), "source_span.file_path")
            start_line, end_line = _span_line_bounds(span)
            span["file_path"] = file_path
            span["start_line"] = start_line
            span["end_line"] = end_line
            span["line_range"] = [start_line, end_line]

            node_id = _optional_text(span.get("node_id"), "source_span.node_id")
            source_hash = _optional_text(
                span.get("source_hash"), "source_span.source_hash"
            )
            file_source_hash = _optional_text(
                span.get("file_source_hash"), "source_span.file_source_hash"
            )
            if node_id is not None:
                span["node_id"] = node_id
            if source_hash is not None:
                span["source_hash"] = source_hash
            if file_source_hash is not None:
                span["file_source_hash"] = file_source_hash

            bound_file_hash = hashes.get(file_path)
            if file_source_hash is not None and bound_file_hash != file_source_hash:
                raise ValueError("file_hash_binding_mismatch")
            if source_hash is not None:
                if node_id is None or hashes.get(node_id) != source_hash:
                    raise ValueError("node_hash_binding_mismatch")
            if bound_file_hash is None and source_hash is None:
                raise ValueError("exact_span_hash_binding_required")

            allowed_files.add(file_path)
            source_spans.append(span)
    except ValueError as exc:
        return _compile_denial(str(exc))

    source_spans.sort(
        key=lambda item: (
            item["file_path"],
            item["start_line"],
            item["end_line"],
            str(item.get("node_id") or ""),
        )
    )

    try:
        target_file = _optional_repo_path(
            grounding_packet.get("target_file"), "target_file"
        )
    except ValueError as exc:
        return _compile_denial(str(exc))
    if target_file is not None and target_file not in allowed_files:
        return _compile_denial("target_file_not_exactly_grounded")

    try:
        target_symbol = _optional_text(
            grounding_packet.get("target_symbol"), "target_symbol"
        )
        tests = _canonical_repo_paths(
            grounding_packet.get("tests", ()), "tests"
        )
        route_reasons = _canonical_strings(
            grounding_packet.get("route_reasons", ()), "route_reasons"
        )
        grounding_version = _optional_text(
            grounding_packet.get("version"), "grounding_version"
        )
        anchor_version = _optional_text(
            grounding_packet.get("anchor_version"), "anchor_version"
        )
    except ValueError as exc:
        return _compile_denial(str(exc))

    evidence = {
        "version": GROUNDED_CAPSULE_COMPILER_VERSION,
        "grounding_version": grounding_version,
        "anchor_version": anchor_version,
        "route": route,
        "route_reasons": route_reasons,
        "target_file": target_file,
        "target_symbol": target_symbol,
        "allowed_files": sorted(allowed_files),
        "source_spans": source_spans,
        "source_hashes": dict(sorted(hashes.items())),
        "required_tests": tests,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
    canonical = _canonical_json(evidence)
    evidence_id = f"GPE-{sha256(canonical.encode('utf-8')).hexdigest()[:24]}"
    return {
        "ok": True,
        "grounding_evidence_id": evidence_id,
        "grounding_evidence": evidence,
    }


def _compile_denial(error: str) -> dict[str, Any]:
    return {"ok": False, "error": error}


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    )


def _canonical_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field}_must_be_canonical_text")
    return value


def _optional_text(value: Any, field: str) -> str | None:
    if value is None or value == "":
        return None
    return _canonical_text(value, field)


def _repo_path(value: Any, field: str) -> str:
    text = _canonical_text(value, field)
    if "\\" in text:
        raise ValueError(f"{field}_must_use_posix_separators")
    path = PurePosixPath(text)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"{field}_must_be_repo_relative")
    return path.as_posix()


def _optional_repo_path(value: Any, field: str) -> str | None:
    if value is None or value == "":
        return None
    return _repo_path(value, field)


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field}_must_be_a_positive_integer")
    return value


def _span_line_bounds(item: Mapping[str, Any]) -> tuple[int, int]:
    line_range = item.get("line_range")
    range_values: list[Any] = []
    if line_range is not None:
        if not _is_sequence(line_range) or len(line_range) != 2:
            raise ValueError("source_span.line_range_must_have_two_integers")
        range_values = list(line_range)

    start_raw = item.get("start_line")
    end_raw = item.get("end_line")
    if start_raw is None and range_values:
        start_raw = range_values[0]
    if end_raw is None and range_values:
        end_raw = range_values[1]
    start = _positive_int(start_raw, "source_span.start_line")
    end = _positive_int(end_raw, "source_span.end_line")
    if end < start:
        raise ValueError("source_span_end_before_start")
    if range_values:
        if start != _positive_int(range_values[0], "source_span.line_range_start"):
            raise ValueError("source_span_start_line_mismatch")
        if end != _positive_int(range_values[1], "source_span.line_range_end"):
            raise ValueError("source_span_end_line_mismatch")
    return start, end


def _canonical_strings(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not _is_sequence(value):
        raise ValueError(f"{field}_must_be_a_sequence")
    normalized = [_canonical_text(item, field) for item in value]
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{field}_must_be_unique")
    return sorted(normalized)


def _canonical_repo_paths(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not _is_sequence(value):
        raise ValueError(f"{field}_must_be_a_sequence")
    normalized = [_repo_path(item, field) for item in value]
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{field}_must_be_unique")
    return sorted(normalized)


def _canonical_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key in sorted(value):
            canonical_key = _canonical_text(key, "mapping_key")
            normalized[canonical_key] = _canonical_value(value[key])
        return normalized
    if _is_sequence(value):
        return [_canonical_value(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non_finite_evidence_value")
        return value
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise ValueError("unsupported_evidence_value")


def _context_cost_accounting(
    capsules: list[dict[str, Any]],
    grounding_evidence: dict[str, Any],
) -> dict[str, Any]:
    """Compare shared evidence with a counterfactual copy in every capsule."""
    shared_payload = {
        "phase_capsules": capsules,
        "grounding_evidence": grounding_evidence,
    }
    repeated_capsules = []
    for capsule in capsules:
        repeated = dict(capsule)
        repeated.pop("grounding_evidence_id", None)
        repeated.pop("scope_ref", None)
        repeated.pop("tests_ref", None)
        repeated["grounding_evidence"] = grounding_evidence
        repeated_capsules.append(repeated)
    repeated_payload = {"phase_capsules": repeated_capsules}

    shared_bytes = len(_canonical_json(shared_payload).encode("utf-8"))
    repeated_bytes = len(_canonical_json(repeated_payload).encode("utf-8"))
    shared_proxy = (shared_bytes + 3) // 4
    repeated_proxy = (repeated_bytes + 3) // 4
    avoided = max(0, repeated_proxy - shared_proxy)
    savings_pct = (
        round((avoided / repeated_proxy) * 100.0, 4)
        if repeated_proxy
        else 0.0
    )
    return {
        "classification": "PROJECTED_STRUCTURAL_TOKEN_PROXY",
        "measurement_class": "ESTIMATED",
        "method": "deterministic_utf8_bytes_divided_by_4_ceiling",
        "provider_reported": False,
        "tokenizer_exact": False,
        "shared_evidence_total_bytes": shared_bytes,
        "repeated_evidence_counterfactual_bytes": repeated_bytes,
        "shared_evidence_total_token_proxy": shared_proxy,
        "repeated_evidence_counterfactual_token_proxy": repeated_proxy,
        "avoided_token_proxy": avoided,
        "projected_savings_percent": savings_pct,
        "savings_status": (
            "SAVINGS_PROVISIONAL" if avoided > 0 else "SAVINGS_INCONCLUSIVE"
        ),
        "scope": "compiled_phase_capsule_output_only",
    }


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def phase_capsules_to_workflow_gates(
    phase_capsules: list,
    repo_root: str = ".",
) -> dict:
    """Map phase capsules to workflow gate states."""
    mapping = {
        "discovery": "CODEMAP_LOCALIZED",
        "grounding": "CODEMAP_LOCALIZED",
        "planning": "PLAN_READY",
        "agent_handoff": "HUMAN_APPROVED_FOR_AGENT",
        "patch": "PATCH_PROPOSED",
        "verification": "VERIFIED",
        "repair": "REPAIR_REQUIRED",
        "approval": "HUMAN_APPROVED_FOR_COMMIT",
        "pr": "PR_READY",
    }
    gate_mapping = []
    for capsule in phase_capsules:
        phase = capsule.get("phase", "")
        gate_mapping.append(
            {"phase": phase, "gate": mapping.get(phase, "INGESTED")}
        )
    return {
        "ok": True,
        "gate_mapping": gate_mapping,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def phase_capsules_to_agent_runbook(
    phase_capsules: list,
    repo_root: str = ".",
) -> dict:
    """Convert phase capsules to agent runbook."""
    steps = [
        (
            f"# Phase: {capsule.get('phase', '')}\n"
            f"# Description: {capsule.get('description', '')}"
        )
        for capsule in phase_capsules
    ]
    return {
        "ok": True,
        "runbook": "\n\n".join(steps),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
