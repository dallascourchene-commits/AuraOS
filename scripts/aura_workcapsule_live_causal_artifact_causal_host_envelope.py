#!/usr/bin/env python3
"""Bind one causal-current host envelope to the exact live-causal artifact consequence.

PR575 owns the live-causal artifact target reference by hashing the exact PR568
live-causal consequence. PR573 owns integrity/currentness checks for the closed
PR567 causal-host envelope, but its top-level target binding still names the older
PR562 artifact generation. This child composes only the missing relation:

    live artifact ref + same causal O10 closure + causal envelope integrity
        -> causal-current host evidence about that exact live artifact.

It deliberately does not hash host observation state into artifact identity, does
not redefine the causal envelope schema, and does not authenticate the transported
causal-host producer. Host observation, resolver trust, semantics and effects remain
separate non-authorizing proof planes.
"""
from __future__ import annotations

from typing import Any

from scripts.aura_workcapsule_artifact_qualified_host_observation import (
    GATES,
    _host_gate_partition,
    _target_binding_violations,
)
from scripts.aura_workcapsule_causal_artifact_qualified_host_envelope import (
    verify_causal_host_admission_envelope,
)
from scripts.aura_workcapsule_live_causal_artifact_host_observation import (
    live_causal_artifact_target_ref,
)
from scripts.aura_workcapsule_live_causal_raw_slice_join import (
    admit_live_causal_raw_slice_join,
    verify_live_causal_raw_slice_join,
)

VERSION = "AURA_WORKCAPSULE_LIVE_CAUSAL_ARTIFACT_CAUSAL_HOST_ENVELOPE_V1"
LIVE_PREFIX = "LIVE_CAUSAL_ARTIFACT_"
CAUSAL_HOST_PREFIX = "CAUSAL_HOST_ENVELOPE_"
CAUSAL_CLOSURE_IDENTITY_MISMATCH = "CAUSAL_HOST_POST_CLOSURE_NOT_LIVE_ARTIFACT_POST_CLOSURE"


def _live_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in kwargs.items()
        if key != "causal_host_admission_receipt"
    }


def verify_live_causal_artifact_causal_host_envelope(
    *,
    scoped_target_inputs: dict[str, Any],
    higher_owner_projection: dict[str, Any],
    raw_slice_receipt: dict[str, Any],
    raw_slice_projection: dict[str, Any],
    pre_root: Any,
    pre_codemap: dict[str, Any],
    pre_anchor_manifest: dict[str, Any],
    pre_witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    pre_graph_witness: dict[str, Any],
    post_root: Any,
    post_codemap: dict[str, Any],
    post_anchor_manifest: dict[str, Any],
    post_witness_manifest: dict[str, Any],
    post_graph_witness: dict[str, Any],
    causal_host_admission_receipt: dict[str, Any],
) -> list[str]:
    """Require causal-current host evidence to concern the exact live artifact/world."""
    kwargs = locals()
    violations = [
        LIVE_PREFIX + item
        for item in verify_live_causal_raw_slice_join(**_live_kwargs(kwargs))
    ]
    violations.extend(
        CAUSAL_HOST_PREFIX + item
        for item in verify_causal_host_admission_envelope(
            causal_host_admission_receipt
        )
    )
    if violations:
        return list(dict.fromkeys(violations))

    live = admit_live_causal_raw_slice_join(**_live_kwargs(kwargs))
    if causal_host_admission_receipt.get("post_closure_receipt_identity") != live.get(
        "causal_post_closure_receipt_identity"
    ):
        violations.append(CAUSAL_CLOSURE_IDENTITY_MISMATCH)

    expected_ref = live_causal_artifact_target_ref(live)
    violations.extend(
        _target_binding_violations(
            host_receipt=causal_host_admission_receipt,
            expected_ref=expected_ref,
        )
    )
    return list(dict.fromkeys(violations))


def admit_live_causal_artifact_causal_host_envelope(**kwargs: Any) -> dict[str, Any]:
    """Emit only target-qualified causal-current evidence or fail closed."""
    violations = verify_live_causal_artifact_causal_host_envelope(**kwargs)
    if violations:
        raise ValueError(
            "live-causal artifact/causal-host envelope failed: " + ",".join(violations)
        )

    live = admit_live_causal_raw_slice_join(**_live_kwargs(kwargs))
    host = kwargs["causal_host_admission_receipt"]
    states = dict(host["host_gate_states"])
    resolved, unknown = _host_gate_partition(states)
    artifact_ref = live_causal_artifact_target_ref(live)
    return {
        "version": VERSION,
        "live_causal_artifact_reproved": True,
        "live_causal_artifact_target_ref": artifact_ref,
        "artifact_target_ref_excludes_host_observation_state": True,
        "causal_host_envelope_integrity_checked": True,
        "causal_host_envelope_reproved_by_child": False,
        "causal_host_envelope_producer_authenticated": False,
        "same_causal_post_closure_identity_proven": True,
        "resolved_causal_host_gates_bound_to_live_artifact": True,
        "resolved_host_gate_count": len(resolved),
        "resolved_host_gates": resolved,
        "unknown_host_gates": unknown,
        "host_gate_states": states,
        "host_observation_set_complete": bool(host["host_observation_set_complete"]),
        "all_host_gates_pass_for_live_artifact": all(
            states[gate] == "PASS" for gate in GATES
        ),
        "causal_post_closure_receipt_identity": dict(
            live["causal_post_closure_receipt_identity"]
        ),
        "dependency_key": dict(live["dependency_key"]),
        "source_generation": live["source_generation"],
        "full_source_sha256_hex": live["full_source_sha256_hex"],
        "full_source_byte_len": live["full_source_byte_len"],
        "target_byte_start": live["target_byte_start"],
        "target_byte_end": live["target_byte_end"],
        "target_slice_byte_len": live["target_slice_byte_len"],
        "target_slice_sha256_hex": live["target_slice_sha256_hex"],
        "selected_target_semantic_handle_digest_hex": live[
            "selected_target_semantic_handle_digest_hex"
        ],
        "semantic_handle_derived_from_raw_slice": False,
        "semantic_identity_proven_by_raw_slice": False,
        "semantic_repair_correctness_proven": False,
        "causal_host_resolver_trust_proven": False,
        "causal_host_observation_authority_proven": False,
        "trusted_continuation_ready": False,
        "host_effect_ready": False,
        "producer_authenticated": False,
        "authority": {
            "review_authorized": False,
            "mutation_authorized": False,
            "execution_authorized": False,
            "commit_authorized": False,
            "merge_authorized": False,
            "promotion_authorized": False,
            "provider_effect_authorized": False,
            "public_effect_authorized": False,
            "human_authority": False,
        },
    }
