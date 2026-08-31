#!/usr/bin/env python3
"""Rebind host-observation admission to the causally correct raw-owner O10 transition.

PR559 owns the five host/control-plane observation gates and their fail-closed
resolver boundary. PR556 owns the stronger causal temporal substrate after the
PR547 falsifier: PRE raw owner -> PRE O8/HOLD; POST raw owner -> candidate;
O10(previous, PRE O8, POST candidate) -> exact CLOSED transition.

This D0 membrane changes only the temporal owner generation beneath the PR559
host lattice. Complete host observations remain non-authorizing, and no local
receipt, pointer, cache coordinate, or temporal closure is promoted to host rank.
"""
from __future__ import annotations

import hashlib
from typing import Any, Mapping

from scripts.aura_workcapsule_raw_owner_derived_post_closure_transition import (
    admit_raw_owner_derived_post_closure_transition,
    verify_raw_owner_derived_post_closure_transition,
)
from scripts.aura_workcapsule_temporal_host_observation_admission import (
    GATES,
    GATE_INDEX,
    GATE_PROBES,
    PROBE_ORDER,
    HostObservationResolverV1,
    _canonical_bytes,
    _resolve_host_gates,
)

VERSION = "AURA_WORKCAPSULE_CAUSAL_TEMPORAL_HOST_OBSERVATION_ADMISSION_V2"


def verify_causal_temporal_host_observation_admission(
    *,
    host_observations: Mapping[str, Any] | None = None,
    host_observation_resolver: HostObservationResolverV1 | None = None,
    **temporal_kwargs: Any,
) -> list[str]:
    """Verify exact PR556 temporal ownership and PR559 host-gate transport."""
    try:
        temporal_violations = verify_raw_owner_derived_post_closure_transition(
            **temporal_kwargs
        )
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


def admit_causal_temporal_host_observation_admission(
    *,
    host_observations: Mapping[str, Any] | None = None,
    host_observation_resolver: HostObservationResolverV1 | None = None,
    **temporal_kwargs: Any,
) -> dict[str, Any]:
    """Emit host readiness above exact causal O10 closure, without authority."""
    violations = verify_causal_temporal_host_observation_admission(
        host_observations=host_observations,
        host_observation_resolver=host_observation_resolver,
        **temporal_kwargs,
    )
    if violations:
        raise ValueError(
            "causal temporal host observation admission failed: " + ",".join(violations)
        )

    temporal = admit_raw_owner_derived_post_closure_transition(**temporal_kwargs)
    if temporal.get("pre_closure_status") != "HOLD":
        raise ValueError("CAUSAL_PRE_NOT_HOLD")
    if temporal.get("post_closure_status") != "CLOSED":
        raise ValueError("CAUSAL_POST_NOT_CLOSED")
    if temporal.get("exact_hold_to_closed_transition") is not True:
        raise ValueError("CAUSAL_TRANSITION_NOT_EXACT_CLOSED")
    if temporal.get("pre_reentry_receipt_reused_for_post_o10") is not True:
        raise ValueError("CAUSAL_PRE_REENTRY_NOT_REUSED_FOR_O10")
    if temporal.get("fresh_post_reentry_receipt_substituted") is not False:
        raise ValueError("CAUSAL_FRESH_POST_REENTRY_SUBSTITUTED")

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
    candidate_probes = {gate: list(GATE_PROBES[gate]) for gate in unknown_gates}
    probe_union = {probe for probes in candidate_probes.values() for probe in probes}
    ordered_required_probes = [probe for probe in PROBE_ORDER if probe in probe_union]

    out: dict[str, Any] = {
        "version": VERSION,
        "disposition": disposition,
        "causal_temporal_owner_reproved": True,
        "raw_owner_pre_lifecycle_derived": temporal["raw_owner_pre_lifecycle_derived"],
        "raw_owner_post_candidate_derived": temporal["raw_owner_post_candidate_derived"],
        "post_o10_closure_derived": temporal["post_o10_closure_derived"],
        "pre_reentry_receipt_reused_for_post_o10": temporal[
            "pre_reentry_receipt_reused_for_post_o10"
        ],
        "fresh_post_reentry_receipt_substituted": temporal[
            "fresh_post_reentry_receipt_substituted"
        ],
        "local_temporal_closure_proven": True,
        "pre_closure_status": temporal["pre_closure_status"],
        "post_closure_status": temporal["post_closure_status"],
        "exact_hold_to_closed_transition": temporal["exact_hold_to_closed_transition"],
        "pre_reentry_receipt_identity": temporal["pre_reentry_receipt_identity"],
        "post_closure_receipt_identity": temporal["post_o10_closure_receipt_identity"],
        "host_gate_states": {gate: resolved[gate]["state"] for gate in GATES},
        "host_gate_resolutions": {gate: resolved[gate]["resolution"] for gate in GATES},
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
