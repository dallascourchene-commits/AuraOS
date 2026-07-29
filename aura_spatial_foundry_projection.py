"""Backward-compatible V2 projection adapter for Aura's Spatial Foundry.

This module is an evidence projection only.  It wraps the existing B15 V1
projection without becoming a truth, archive, routing, verification, policy, or
authority owner.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from aura_bilateral_live_repair_foundry_contracts import (
    PROJECTION_VERSION,
    BilateralLiveRepairError,
    canonical_sanitize,
    digest,
)

SPATIAL_FOUNDRY_PROJECTION_V2 = "AURA_SPATIAL_FOUNDRY_PROJECTION_V2"
SPATIAL_FOUNDRY_WFST_V1 = "AURA_CONSTRUCTION_SPATIAL_FOUNDRY_GUARDED_WFST_V1"
ALLOWED_FOUNDRY_ARENAS = frozenset({"coding", "construction", "spatial"})
MAX_PROJECTION_NESTING = 12
_HEX = re.compile(r"^[0-9a-f]{40,64}$")
_AUTHORITY_TOKENS = frozenset(
    {
        "accessgranted",
        "approval",
        "authorization",
        "automaticcommit",
        "automaticexecution",
        "automaticmerge",
        "automaticpullrequest",
        "automaticpush",
        "constructiontruth",
        "executionauthority",
        "patchauthority",
        "paymentreleased",
        "physicalworkauthorized",
        "professionalapproval",
        "productionmutation",
        "rendererauthority",
        "surveyauthority",
        "visualtruth",
    }
)
_DOMAIN_FALSE_AUTHORITY = {
    "construction_truth": False,
    "survey_authority": False,
    "professional_approval": False,
    "physical_work_authorized": False,
    "payment_released": False,
    "access_granted": False,
    "automatic_execution": False,
}

_TRANSITIONS = (
    {
        "transition_id": "START_BOUNDED_CAPTURE",
        "from_state": "IDLE",
        "to_state": "CAPTURE_ACTIVE",
        "requires": ("identity_current", "operator_authorized"),
    },
    {
        "transition_id": "MARK_INCIDENT",
        "from_state": "CAPTURE_ACTIVE",
        "to_state": "INCIDENT_MARKED",
        "requires": ("incident_marker_present",),
    },
    {
        "transition_id": "FINALIZE_REPLAY",
        "from_state": "INCIDENT_MARKED",
        "to_state": "REPLAY_READY",
        "requires": ("capture_dissolved", "required_assets_bound"),
    },
    {
        "transition_id": "RUN_RUNTIME_PROOF",
        "from_state": "REPLAY_READY",
        "to_state": "RUNTIME_PROVEN",
        "requires": ("runtime_proof_retained",),
    },
    {
        "transition_id": "ASSESS_REPAIR",
        "from_state": "RUNTIME_PROVEN",
        "to_state": "REPAIR_ASSESSED",
        "requires": ("repair_attempt_retained",),
    },
    {
        "transition_id": "PREVIEW_ISOLATED_CANDIDATE",
        "from_state": "REPAIR_ASSESSED",
        "to_state": "PREVIEWED",
        "requires": ("preview_receipt_retained",),
    },
    {
        "transition_id": "RUN_CURRENT_REPROOF",
        "from_state": "PREVIEWED",
        "to_state": "REPROOF_RETAINED",
        "requires": ("u7_current_reproof_retained",),
    },
    {
        "transition_id": "DISSOLVE_PRESENTATION",
        "from_state": "REPROOF_RETAINED",
        "to_state": "DISSOLVED",
        "requires": ("human_disposition_retained", "resources_dissolved"),
    },
)


def validate_foundry_arena(value: Any) -> str:
    arena = str(value or "").strip().casefold()
    if arena not in ALLOWED_FOUNDRY_ARENAS:
        raise ValueError(
            f"arena_id must be one of {sorted(ALLOWED_FOUNDRY_ARENAS)}"
        )
    return arena


def _required_text(value: Any, name: str, *, limit: int = 4096) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    text = value.strip()
    if len(text.encode("utf-8")) > limit:
        raise ValueError(f"{name} exceeds {limit} UTF-8 bytes")
    return text


def _hex_digest(value: Any, name: str, *, optional: bool = False) -> str:
    text = str(value or "").strip().lower()
    if optional and not text:
        return ""
    if not _HEX.fullmatch(text):
        raise ValueError(f"{name} must be a 40-64 character lowercase hex digest")
    return text


def _normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).casefold())


def _authority_path(
    value: Any,
    path: str = "$",
    *,
    depth: int = 0,
) -> str | None:
    if depth > MAX_PROJECTION_NESTING:
        raise ValueError(
            f"projection nesting exceeds {MAX_PROJECTION_NESTING} levels at {path}"
        )
    if isinstance(value, Mapping):
        for key, item in value.items():
            child = f"{path}.{key}"
            if _normalize_key(key) in _AUTHORITY_TOKENS and item is not False:
                return child
            found = _authority_path(item, child, depth=depth + 1)
            if found:
                return found
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            found = _authority_path(item, f"{path}[{index}]", depth=depth + 1)
            if found:
                return found
    return None


def _clean_mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    authority = _authority_path(value)
    if authority is not None:
        raise ValueError(f"{name} cannot supply authority field: {authority}")
    clean, _ = canonical_sanitize(value)
    if not isinstance(clean, Mapping):
        raise ValueError(f"{name} must remain an object after sanitization")
    return dict(clean)


def _clean_rows(values: Any, name: str, *, limit: int = 256) -> list[dict[str, Any]]:
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        raise ValueError(f"{name} must be a sequence")
    if len(values) > limit:
        raise ValueError(f"{name} exceeds {limit} rows")
    return [_clean_mapping(item, f"{name}[{index}]") for index, item in enumerate(values)]


def _validate_domain_target(row: Mapping[str, Any], index: int) -> dict[str, Any]:
    required = {"target_id", "target_type", "canonical_ref", "digest", "truth_class"}
    if not required.issubset(row):
        raise ValueError(f"domain_targets[{index}] is missing {sorted(required - set(row))}")
    result = dict(row)
    for key in ("target_id", "target_type", "canonical_ref", "truth_class"):
        result[key] = _required_text(result[key], f"domain_targets[{index}].{key}")
    result["digest"] = _hex_digest(result["digest"], f"domain_targets[{index}].digest")
    return result


def _validate_domain_artifact(row: Mapping[str, Any], index: int) -> dict[str, Any]:
    required = {"artifact_id", "artifact_type", "digest", "source_ref"}
    if not required.issubset(row):
        raise ValueError(f"domain_artifacts[{index}] is missing {sorted(required - set(row))}")
    result = dict(row)
    for key in ("artifact_id", "artifact_type", "source_ref"):
        result[key] = _required_text(result[key], f"domain_artifacts[{index}].{key}")
    result["digest"] = _hex_digest(result["digest"], f"domain_artifacts[{index}].digest")
    if "coordinate_receipt_digest" in result:
        result["coordinate_receipt_digest"] = _hex_digest(
            result["coordinate_receipt_digest"],
            f"domain_artifacts[{index}].coordinate_receipt_digest",
            optional=True,
        )
    return result


def validate_projection_v1(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("base_projection must be an object")
    projection = dict(value)
    supplied = str(projection.pop("projection_digest", "") or "").strip().lower()
    if (
        projection.get("version") != PROJECTION_VERSION
        or projection.get("projection_only") is not True
        or projection.get("stale") is not False
        or not _HEX.fullmatch(supplied)
        or digest(projection) != supplied
    ):
        raise BilateralLiveRepairError("base Spatial Foundry V1 projection is invalid")
    return {**projection, "projection_digest": supplied}


def project_guarded_wfst(
    *,
    arena_id: str,
    current_state: str,
    evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project admitted and blocked transitions without dispatching any action."""

    arena = validate_foundry_arena(arena_id)
    state = _required_text(current_state, "current_state", limit=128).upper()
    clean_evidence = _clean_mapping(evidence or {}, "transition_evidence")
    admitted: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for transition in _TRANSITIONS:
        if transition["from_state"] != state:
            continue
        missing = [
            requirement
            for requirement in transition["requires"]
            if clean_evidence.get(requirement) is not True
        ]
        row = {
            **transition,
            "arena_id": arena,
            "missing_evidence": missing,
            "admitted": not missing,
            "recommended": False,
            "execution_authority": False,
            "state_mutation": False,
            "human_review_required": True,
        }
        (admitted if not missing else blocked).append(row)
    if admitted:
        admitted[0]["recommended"] = True
    binding = {
        "grammar_version": SPATIAL_FOUNDRY_WFST_V1,
        "arena_id": arena,
        "current_state": state,
        "evidence": clean_evidence,
    }
    output = {
        **binding,
        "admitted_transitions": admitted,
        "blocked_transitions": blocked,
        "recommended_transition": admitted[0]["transition_id"] if admitted else None,
        "projection_only": True,
        "execution_authority": False,
        "state_mutation": False,
        "human_review_required": True,
    }
    output["state_binding_digest"] = digest(output)
    return output


def build_spatial_foundry_projection_v2(
    *,
    base_projection: Mapping[str, Any],
    arena_id: str,
    domain: Mapping[str, Any],
    domain_targets: Sequence[Mapping[str, Any]] = (),
    domain_artifacts: Sequence[Mapping[str, Any]] = (),
    presentation: Mapping[str, Any] | None = None,
    construction: Mapping[str, Any] | None = None,
    coordination_candidates: Sequence[Mapping[str, Any]] = (),
    domain_decision: Mapping[str, Any] | None = None,
    transition_projection: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Wrap a verified V1 projection with domain-neutral additive evidence."""

    base = validate_projection_v1(base_projection)
    arena = validate_foundry_arena(arena_id)
    clean_domain = _clean_mapping(domain, "domain")
    declared_arena = clean_domain.get("arena_id")
    if declared_arena is not None and validate_foundry_arena(declared_arena) != arena:
        raise BilateralLiveRepairError("domain arena differs from the replay-bound arena")
    clean_domain["arena_id"] = arena
    clean_domain["domain_type"] = _required_text(
        clean_domain.get("domain_type"), "domain.domain_type", limit=128
    )
    for key in ("state_digest", "runtime_packet_digest"):
        if clean_domain.get(key):
            clean_domain[key] = _hex_digest(clean_domain[key], f"domain.{key}")
    clean_targets = [
        _validate_domain_target(row, index)
        for index, row in enumerate(_clean_rows(domain_targets, "domain_targets"))
    ]
    clean_artifacts = [
        _validate_domain_artifact(row, index)
        for index, row in enumerate(_clean_rows(domain_artifacts, "domain_artifacts"))
    ]
    clean_presentation = _clean_mapping(presentation or {}, "presentation")
    clean_construction = _clean_mapping(construction or {}, "construction")
    clean_candidates = _clean_rows(
        coordination_candidates, "coordination_candidates", limit=64
    )
    clean_decision = _clean_mapping(domain_decision or {}, "domain_decision")
    for key, expected in {
        "physical_work_authorized": False,
        "professional_approval": False,
        "payment_released": False,
        "access_granted": False,
        "automatic_execution": False,
    }.items():
        if clean_decision.get(key, expected) is not expected:
            raise BilateralLiveRepairError(f"domain_decision.{key} must remain false")
        clean_decision[key] = expected
    clean_decision["human_review_required"] = True
    transitions = _clean_mapping(
        transition_projection or {}, "guarded_wfst"
    )
    if transitions:
        if transitions.get("arena_id") != arena:
            raise BilateralLiveRepairError("guarded WFST arena differs from replay-bound arena")
        if (
            transitions.get("projection_only") is not True
            or transitions.get("execution_authority") is not False
            or transitions.get("state_mutation") is not False
        ):
            raise BilateralLiveRepairError("guarded WFST projection grants forbidden authority")
        supplied_binding_digest = str(
            transitions.get("state_binding_digest") or ""
        ).strip().lower()
        canonical_transition = {
            key: value
            for key, value in transitions.items()
            if key != "state_binding_digest"
        }
        if (
            not _HEX.fullmatch(supplied_binding_digest)
            or digest(canonical_transition) != supplied_binding_digest
        ):
            raise BilateralLiveRepairError(
                "guarded WFST state binding digest is missing or invalid"
            )

    output = dict(base)
    base_digest = output.pop("projection_digest")
    output.update(
        {
            "version": SPATIAL_FOUNDRY_PROJECTION_V2,
            "compatibility": {
                "base_projection_version": PROJECTION_VERSION,
                "base_projection_digest": base_digest,
                "v1_readable": True,
                "code_targets_retained": True,
            },
            "arena_id": arena,
            "domain": clean_domain,
            "domain_targets": clean_targets,
            "domain_artifacts": clean_artifacts,
            "presentation": clean_presentation,
            "construction": clean_construction,
            "coordination_candidates": clean_candidates,
            "candidate_type_separation": True,
            "domain_decision": clean_decision,
            "guarded_wfst": transitions,
            "authority": {
                **dict(base.get("authority") or {}),
                **_DOMAIN_FALSE_AUTHORITY,
                "human_review_required": True,
            },
        }
    )
    output["projection_digest"] = digest(output)
    return output


__all__ = [
    "ALLOWED_FOUNDRY_ARENAS",
    "SPATIAL_FOUNDRY_PROJECTION_V2",
    "SPATIAL_FOUNDRY_WFST_V1",
    "build_spatial_foundry_projection_v2",
    "project_guarded_wfst",
    "validate_foundry_arena",
    "validate_projection_v1",
]
