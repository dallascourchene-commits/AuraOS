#!/usr/bin/env python3
"""Bind a current causal host envelope to the exact PR568 corroboration member.

PR579 owns the graph-membership relation from a PR575 live-host target to the exact
PR568 member of PR577 corroboration, preserving reference-scheme identity. PR573 owns
closed causal-host-envelope integrity and current host-state derivation. This membrane
proves only that those two earned consequences concern the same host target, the same
five-gate observation state vector, and the same causal O10 world.

It does not reimplement either owner, authenticate either producer, transfer host state
to the PR572 sibling, or mint semantic/effect authority.
"""
from __future__ import annotations

from typing import Any

from scripts.aura_workcapsule_artifact_qualified_host_observation import GATES
from scripts.aura_workcapsule_causal_artifact_qualified_host_envelope import (
    verify_causal_host_admission_envelope,
)
from scripts.aura_workcapsule_corroboration_qualified_host_member import (
    admit_corroboration_qualified_host_member,
    verify_corroboration_qualified_host_member,
)

VERSION = "AURA_WORKCAPSULE_CURRENT_CAUSAL_CORROBORATION_MEMBER_V1"
MEMBER_PREFIX = "CORROBORATION_MEMBER_"
HOST_PREFIX = "CURRENT_CAUSAL_HOST_"
O10_MISMATCH = "CURRENT_CAUSAL_HOST_O10_MISMATCH"
STATE_VECTOR_MISMATCH = "CURRENT_CAUSAL_HOST_STATE_VECTOR_MISMATCH"
TARGET_REF_MISMATCH = "CURRENT_CAUSAL_HOST_TARGET_REF_MISMATCH"


def _resolved_host_targets(host: dict[str, Any]) -> dict[str, str]:
    states = host["host_gate_states"]
    resolutions = host["host_gate_resolutions"]
    return {
        gate: resolutions[gate]["target_ref"]
        for gate in GATES
        if states[gate] in {"PASS", "FAIL"}
    }


def verify_current_causal_corroboration_member(
    *,
    live_host_receipt: dict[str, Any],
    pr568_receipt: dict[str, Any],
    pr572_receipt: dict[str, Any],
    causal_host_admission_receipt: dict[str, Any],
) -> list[str]:
    """Require current causal host evidence to concern the exact PR579-qualified member."""
    violations = [
        MEMBER_PREFIX + item
        for item in verify_corroboration_qualified_host_member(
            live_host_receipt=live_host_receipt,
            pr568_receipt=pr568_receipt,
            pr572_receipt=pr572_receipt,
        )
    ]
    violations.extend(
        HOST_PREFIX + item
        for item in verify_causal_host_admission_envelope(
            causal_host_admission_receipt
        )
    )
    if violations:
        return list(dict.fromkeys(violations))

    member = admit_corroboration_qualified_host_member(
        live_host_receipt=live_host_receipt,
        pr568_receipt=pr568_receipt,
        pr572_receipt=pr572_receipt,
    )

    if causal_host_admission_receipt["post_closure_receipt_identity"] != pr568_receipt[
        "causal_post_closure_receipt_identity"
    ]:
        violations.append(O10_MISMATCH)

    if causal_host_admission_receipt["host_gate_states"] != live_host_receipt[
        "host_gate_states"
    ]:
        violations.append(STATE_VECTOR_MISMATCH)

    expected_target = member["host_target_ref"]
    for gate, target_ref in _resolved_host_targets(causal_host_admission_receipt).items():
        if target_ref != expected_target:
            violations.append(f"{TARGET_REF_MISMATCH}:{gate}")
    return list(dict.fromkeys(violations))


def admit_current_causal_corroboration_member(**kwargs: Any) -> dict[str, Any]:
    violations = verify_current_causal_corroboration_member(**kwargs)
    if violations:
        raise ValueError(
            "current causal corroboration member failed: " + ",".join(violations)
        )

    member = admit_corroboration_qualified_host_member(
        live_host_receipt=kwargs["live_host_receipt"],
        pr568_receipt=kwargs["pr568_receipt"],
        pr572_receipt=kwargs["pr572_receipt"],
    )
    host = kwargs["causal_host_admission_receipt"]
    resolved_targets = _resolved_host_targets(host)
    return {
        "version": VERSION,
        "corroboration_qualified_pr568_member_reproved": True,
        "current_causal_host_envelope_integrity_checked": True,
        "same_causal_o10_world_proven": True,
        "same_host_gate_state_vector_proven": True,
        "resolved_host_gates_bound_to_same_pr568_host_target": True,
        "host_target_ref": member["host_target_ref"],
        "pr568_proof_artifact_ref": member["pr568_proof_artifact_ref"],
        "pr572_proof_artifact_ref": member["pr572_proof_artifact_ref"],
        "reference_scheme_identity_preserved": True,
        "host_target_is_pr572_sibling": False,
        "host_target_is_corroboration_edge": False,
        "resolved_host_gate_count": len(resolved_targets),
        "resolved_host_gates": sorted(resolved_targets),
        "host_gate_states": dict(host["host_gate_states"]),
        "host_observation_set_complete": bool(host["host_observation_set_complete"]),
        "host_observation_transferred_to_pr572_sibling": False,
        "causal_host_envelope_reproved_by_child": False,
        "causal_host_envelope_producer_authenticated": False,
        "live_host_receipt_producer_authenticated": False,
        "corroboration_parent_receipts_producer_authenticated": False,
        "semantic_equivalence_proven": False,
        "semantic_truth_proven": False,
        "host_resolver_trust_proven": False,
        "host_observation_authority_proven": False,
        "trusted_continuation_ready": False,
        "host_effect_ready": False,
        "semantic_k27_authority_proven": False,
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
