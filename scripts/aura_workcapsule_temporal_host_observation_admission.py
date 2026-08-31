#!/usr/bin/env python3
"""Keep exact local temporal closure below host/control-plane observation authority.

O32 proves an exact PRE-plan -> distinct POST-observation CLOSED lifecycle while
preserving all semantic/effect authority as false. O-MAP-REUSE-05 identifies a
separate host/control-plane observation frontier. This D0 membrane composes the
two without allowing local closure, pointer presence, or caller assertions to
manufacture host evidence rank.

The module recompiles O32 from raw inputs. Host observations can move out of
UNKNOWN only through an explicit resolver boundary. Even a complete resolved
observation set remains non-authorizing here.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Protocol

from scripts.aura_workcapsule_preplan_post_observation_transition import (
    admit_preplan_post_observation_transition,
    verify_preplan_post_observation_transition,
)

VERSION = "AURA_WORKCAPSULE_TEMPORAL_HOST_OBSERVATION_ADMISSION_V1"
HOST_RESOLUTION_SCHEMA = "AURA_HOST_OBSERVATION_RESOLUTION_V1"
HOST_RESOLUTION_VERSION = 1

GATES = ("U_HEAD", "U_ROUTE", "U_F2", "U_CUSTODY", "U_CANARY")
GATE_INDEX = {gate: index for index, gate in enumerate(GATES)}
GATE_PROBES = {
    "U_HEAD": ("P_HEAD",),
    "U_ROUTE": ("P_ROUTE",),
    "U_F2": ("P_J",),
    "U_CUSTODY": ("P_CUSTODY", "P_ROUTE"),
    "U_CANARY": ("P_CANARY",),
}
PROBE_ORDER = ("P_HEAD", "P_ROUTE", "P_J", "P_CUSTODY", "P_CANARY")
STATES = frozenset({"PASS", "FAIL", "UNKNOWN"})

_RESOLUTION_FIELDS = (
    "schema",
    "version",
    "gate",
    "state",
    "observation_ref",
    "producer_ref",
    "producer_generation",
    "currentness_ref",
    "authority_ref",
    "target_ref",
    "resolver_ref",
    "resolver_generation",
    "revoked",
    "resolution_digest",
)
_RESOLUTION_PAYLOAD_FIELDS = tuple(
    field for field in _RESOLUTION_FIELDS if field != "resolution_digest"
)


class HostObservationResolverV1(Protocol):
    """External owner boundary; this module does not certify resolver trust."""

    def resolve(self, *, gate: str, observation: Any) -> Mapping[str, Any] | None:
        """Return one exact host-observation resolution or None when unresolved."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    )


def _resolution_digest(resolution: Mapping[str, Any]) -> str:
    payload = {field: resolution[field] for field in _RESOLUTION_PAYLOAD_FIELDS}
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def verify_host_resolution(*, expected_gate: str, resolution: Any) -> list[str]:
    """Validate the portable shape/binding of one externally resolved observation."""
    if not isinstance(resolution, Mapping):
        return ["HOST_RESOLUTION_NOT_MAPPING"]
    if set(resolution) != set(_RESOLUTION_FIELDS):
        return ["HOST_RESOLUTION_FIELDS_MISMATCH"]

    violations: list[str] = []
    if resolution.get("schema") != HOST_RESOLUTION_SCHEMA:
        violations.append("HOST_RESOLUTION_SCHEMA_MISMATCH")
    if resolution.get("version") != HOST_RESOLUTION_VERSION:
        violations.append("HOST_RESOLUTION_VERSION_MISMATCH")
    if resolution.get("gate") != expected_gate:
        violations.append("HOST_RESOLUTION_GATE_MISMATCH")
    if resolution.get("state") not in STATES:
        violations.append("HOST_RESOLUTION_STATE_INVALID")
    if not isinstance(resolution.get("revoked"), bool):
        violations.append("HOST_RESOLUTION_REVOKED_NOT_BOOL")

    for field in (
        "observation_ref",
        "producer_ref",
        "producer_generation",
        "currentness_ref",
        "authority_ref",
        "target_ref",
        "resolver_ref",
        "resolver_generation",
    ):
        value = resolution.get(field)
        if not isinstance(value, str) or not value.strip():
            violations.append(f"HOST_RESOLUTION_BINDING_MISSING:{field}")

    supplied_digest = resolution.get("resolution_digest")
    if not _is_sha256(supplied_digest):
        violations.append("HOST_RESOLUTION_DIGEST_INVALID")
    else:
        expected = _resolution_digest(resolution)
        if supplied_digest != expected:
            violations.append("HOST_RESOLUTION_DIGEST_MISMATCH")
    return list(dict.fromkeys(violations))


def _resolve_host_gates(
    *,
    host_observations: Mapping[str, Any] | None,
    host_observation_resolver: HostObservationResolverV1 | None,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    observations: Mapping[str, Any] = host_observations or {}
    if not isinstance(observations, Mapping):
        return {}, ["HOST_OBSERVATIONS_NOT_MAPPING"]
    unknown_keys = set(observations) - set(GATES)
    if unknown_keys:
        return {}, ["HOST_OBSERVATIONS_UNKNOWN_GATE:" + ",".join(sorted(unknown_keys))]

    resolved: dict[str, dict[str, Any]] = {}
    violations: list[str] = []
    for gate in GATES:
        observation = observations.get(gate)
        if observation is None or host_observation_resolver is None:
            resolved[gate] = {
                "state": "UNKNOWN",
                "resolution": None,
                "reason": "OBSERVATION_OR_RESOLVER_REQUIRED",
            }
            continue
        try:
            resolution = host_observation_resolver.resolve(gate=gate, observation=observation)
        except Exception as exc:  # fail closed across external resolver boundaries
            resolved[gate] = {
                "state": "UNKNOWN",
                "resolution": None,
                "reason": f"RESOLVER_EXCEPTION:{type(exc).__name__}",
            }
            continue
        if resolution is None:
            resolved[gate] = {
                "state": "UNKNOWN",
                "resolution": None,
                "reason": "RESOLVER_RETURNED_UNRESOLVED",
            }
            continue

        item_violations = verify_host_resolution(expected_gate=gate, resolution=resolution)
        if item_violations:
            violations.extend(f"{gate}:{item}" for item in item_violations)
            continue
        effective_state = "FAIL" if resolution["revoked"] else resolution["state"]
        reason = "RESOLUTION_REVOKED" if resolution["revoked"] else "RESOLVED"
        resolved[gate] = {
            "state": effective_state,
            "resolution": dict(resolution),
            "reason": reason,
        }
    return resolved, list(dict.fromkeys(violations))


def verify_temporal_host_observation_admission(
    *,
    host_observations: Mapping[str, Any] | None = None,
    host_observation_resolver: HostObservationResolverV1 | None = None,
    **temporal_kwargs: Any,
) -> list[str]:
    """Validate O32 and the host-observation transport without inferring effects."""
    try:
        temporal_violations = verify_preplan_post_observation_transition(**temporal_kwargs)
    except TypeError as exc:
        return [f"TEMPORAL_INPUT_CONTRACT_ERROR:{type(exc).__name__}"]
    if temporal_violations:
        return ["TEMPORAL_" + item for item in temporal_violations]

    resolved, host_violations = _resolve_host_gates(
        host_observations=host_observations,
        host_observation_resolver=host_observation_resolver,
    )
    if host_violations:
        return host_violations
    if set(resolved) != set(GATES):
        return ["HOST_GATE_SET_INCOMPLETE"]
    return []


def admit_temporal_host_observation_admission(
    *,
    host_observations: Mapping[str, Any] | None = None,
    host_observation_resolver: HostObservationResolverV1 | None = None,
    **temporal_kwargs: Any,
) -> dict[str, Any]:
    """Emit the local-closure/host-observation split and remain non-authorizing."""
    violations = verify_temporal_host_observation_admission(
        host_observations=host_observations,
        host_observation_resolver=host_observation_resolver,
        **temporal_kwargs,
    )
    if violations:
        raise ValueError(
            "temporal host observation admission verification failed: "
            + ",".join(violations)
        )

    temporal = admit_preplan_post_observation_transition(**temporal_kwargs)
    if temporal.get("pre_closure_status") != "HOLD":
        raise ValueError("O32_PRE_NOT_HOLD")
    if temporal.get("post_closure_status") != "CLOSED":
        raise ValueError("O32_POST_NOT_CLOSED")
    if temporal.get("exact_hold_to_closed_transition") is not True:
        raise ValueError("O32_TRANSITION_NOT_EXACT_CLOSED")

    resolved, _ = _resolve_host_gates(
        host_observations=host_observations,
        host_observation_resolver=host_observation_resolver,
    )
    fail_mask = sum(
        1 << GATE_INDEX[gate] for gate in GATES if resolved[gate]["state"] == "FAIL"
    )
    unknown_mask = sum(
        1 << GATE_INDEX[gate]
        for gate in GATES
        if resolved[gate]["state"] == "UNKNOWN"
    )
    if fail_mask:
        disposition = "FAIL_CLOSED"
    elif unknown_mask:
        disposition = "HOST_OBSERVATION_REQUIRED"
    else:
        disposition = "HOST_OBSERVATIONS_COMPLETE_NONAUTHORIZING"

    unknown_gates = [gate for gate in GATES if resolved[gate]["state"] == "UNKNOWN"]
    candidate_probes = {
        gate: list(GATE_PROBES[gate]) for gate in unknown_gates
    }
    probe_union = {
        probe for probes in candidate_probes.values() for probe in probes
    }
    ordered_required_probes = [probe for probe in PROBE_ORDER if probe in probe_union]

    out: dict[str, Any] = {
        "version": VERSION,
        "disposition": disposition,
        "local_temporal_closure_proven": True,
        "pre_closure_status": temporal["pre_closure_status"],
        "post_closure_status": temporal["post_closure_status"],
        "exact_hold_to_closed_transition": temporal["exact_hold_to_closed_transition"],
        "pre_reentry_receipt_identity": temporal["pre_reentry_receipt_identity"],
        "post_closure_receipt_identity": temporal["post_closure_receipt_identity"],
        "host_gate_states": {gate: resolved[gate]["state"] for gate in GATES},
        "host_gate_resolutions": {
            gate: resolved[gate]["resolution"] for gate in GATES
        },
        "host_gate_reasons": {gate: resolved[gate]["reason"] for gate in GATES},
        "fail_mask": fail_mask,
        "unknown_mask": unknown_mask,
        "candidate_probes_by_unknown_gate": candidate_probes,
        "ordered_required_probes": ordered_required_probes,
        "minimum_cover_computed": False,
        "minimum_cover_reason": "PROBE_COSTS_AND_WORLD_PAIR_SEPARATION_NOT_MEASURED",
        "host_observation_set_complete": fail_mask == 0 and unknown_mask == 0,
        "resolver_trust_proven_by_this_module": False,
        "host_observation_authority_proven_by_this_module": False,
        "local_evidence_promoted_to_host_rank": False,
        "drive_pointer_presence_promoted_to_pass": False,
        "cache_or_coordinate_presence_promoted_to_pass": False,
        "trusted_continuation_ready": False,
        "host_effect_ready": False,
        "source_currentness_minted": False,
        "semantic_repair_correctness_minted": False,
        "producer_identity_authenticated": False,
        "authority": {
            "review_authorized": False,
            "execution_authorized": False,
            "commit_authorized": False,
            "merge_authorized": False,
            "promotion_authorized": False,
            "provider_effect_authorized": False,
            "public_effect_authorized": False,
            "human_authority": False,
        },
    }
    out["receipt_identity"] = {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
        "scope_profile": VERSION,
        "value": hashlib.sha256(_canonical_bytes(out)).hexdigest(),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }
    return out
