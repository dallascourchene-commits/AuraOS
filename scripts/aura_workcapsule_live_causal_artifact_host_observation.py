#!/usr/bin/env python3
"""Bind host-observation target references to one exact live causal raw-slice artifact.

PR568 owns the live recursive raw slice -> exact PR556 causal POST relation.
PR565 owns integrity checking and artifact-target qualification for serialized PR559
host-admission evidence. This D0 membrane changes only the artifact generation used
for target qualification: resolved host gates must name the digest of the exact PR568
live-causal admission, not the older PR562 local-artifact consequence.

The host-admission envelope is integrity-checked but not producer-authenticated or
reproved by this child. Binding a resolved gate to the live causal artifact does not
mint resolver trust, host authority, semantic correctness, continuation, or effects.
"""
from __future__ import annotations

from typing import Any

from scripts.aura_workcapsule_artifact_qualified_host_observation import (
    GATES,
    HOST_PREFIX,
    TARGET_REF_MISMATCH,
    _host_gate_partition,
    _target_binding_violations,
    artifact_target_ref,
    verify_host_admission_envelope,
)
from scripts.aura_workcapsule_live_causal_raw_slice_join import (
    admit_live_causal_raw_slice_join,
    verify_live_causal_raw_slice_join,
)

VERSION = "AURA_WORKCAPSULE_LIVE_CAUSAL_ARTIFACT_HOST_OBSERVATION_V1"
LIVE_PREFIX = "LIVE_CAUSAL_ARTIFACT_"


def live_causal_artifact_target_ref(live_receipt: dict[str, Any]) -> str:
    """Return an evidence reference over the full PR568 consequence receipt."""
    return artifact_target_ref(live_receipt)


def _live_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in kwargs.items() if key != "host_admission_receipt"}


def verify_live_causal_artifact_host_observation(
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
    host_admission_receipt: dict[str, Any],
) -> list[str]:
    """Require every resolved host gate to target the exact PR568 consequence."""
    kwargs = locals()
    live_violations = verify_live_causal_raw_slice_join(**_live_kwargs(kwargs))
    violations = [LIVE_PREFIX + item for item in live_violations]
    violations.extend(
        HOST_PREFIX + item
        for item in verify_host_admission_envelope(host_admission_receipt)
    )
    if violations:
        return list(dict.fromkeys(violations))

    live = admit_live_causal_raw_slice_join(**_live_kwargs(kwargs))
    expected_ref = live_causal_artifact_target_ref(live)
    violations.extend(
        _target_binding_violations(
            host_receipt=host_admission_receipt,
            expected_ref=expected_ref,
        )
    )
    return list(dict.fromkeys(violations))


def admit_live_causal_artifact_host_observation(**kwargs: Any) -> dict[str, Any]:
    """Emit only artifact-qualified evidence or fail closed."""
    violations = verify_live_causal_artifact_host_observation(**kwargs)
    if violations:
        raise ValueError(
            "live causal artifact host observation failed: " + ",".join(violations)
        )

    live = admit_live_causal_raw_slice_join(**_live_kwargs(kwargs))
    host = kwargs["host_admission_receipt"]
    states = dict(host["host_gate_states"])
    resolved, unknown = _host_gate_partition(states)
    expected_ref = live_causal_artifact_target_ref(live)

    return {
        "version": VERSION,
        "live_causal_raw_slice_reproved": True,
        "live_causal_artifact_target_ref": expected_ref,
        "host_admission_integrity_checked": True,
        "host_admission_reproved_by_child": False,
        "host_admission_producer_authenticated": False,
        "resolved_host_gates_bound_to_live_causal_artifact": True,
        "resolved_host_gate_count": len(resolved),
        "resolved_host_gates": resolved,
        "unknown_host_gates": unknown,
        "host_gate_states": states,
        "host_observation_set_complete": bool(host["host_observation_set_complete"]),
        "all_host_gates_pass_for_live_causal_artifact": all(
            states[gate] == "PASS" for gate in GATES
        ),
        "causal_post_owner_reproved_from_raw_evidence": bool(
            live["causal_post_owner_reproved_from_raw_evidence"]
        ),
        "same_exact_post_source_instance_proven": bool(
            live["same_exact_post_source_instance_proven"]
        ),
        "same_exact_raw_target_slice_proven": bool(
            live["same_exact_raw_target_slice_proven"]
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
        "target_slice_sha256_hex": live["target_slice_sha256_hex"],
        "selected_target_semantic_handle_digest_hex": live[
            "selected_target_semantic_handle_digest_hex"
        ],
        "semantic_handle_derived_from_raw_slice": False,
        "semantic_identity_proven_by_raw_slice": False,
        "host_resolver_trust_proven": False,
        "host_observation_authority_proven": False,
        "trusted_continuation_ready": False,
        "host_effect_ready": False,
        "semantic_repair_correctness_proven": False,
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
