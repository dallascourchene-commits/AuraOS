#!/usr/bin/env python3
"""Bind one causal host envelope to exactly one member of a corroborated proof pair.

PR577 proves that PR568 and PR572 independently establish the same bounded live-causal
source/target/O10 fact while remaining distinct proof artifacts. PR573 owns integrity and
current derived-state checks for the closed causal host envelope. This child composes only
those relations:

- the envelope must be structurally valid under PR573;
- its POST closure must be the same causal O10 world corroborated by PR577;
- every resolved host gate must target one of the two exact PR577 proof-artifact refs;
- all resolved gates in one envelope must target the same proof artifact.

Corroboration never transfers a PASS/FAIL observation from the targeted lineage to its peer.
No semantic, producer, resolver, continuation, effect, or human authority is minted here.
"""
from __future__ import annotations

from typing import Any

from scripts.aura_workcapsule_artifact_qualified_host_observation import GATES
from scripts.aura_workcapsule_causal_artifact_qualified_host_envelope import (
    verify_causal_host_admission_envelope,
)
from scripts.aura_workcapsule_live_causal_corroboration import (
    admit_live_causal_corroboration,
    verify_live_causal_corroboration,
)

VERSION = "AURA_WORKCAPSULE_CORROBORATION_CAUSAL_HOST_LINEAGE_V1"
CORROBORATION_PREFIX = "CORROBORATION_"
HOST_PREFIX = "CAUSAL_HOST_ENVELOPE_"
CAUSAL_O10_WORLD_MISMATCH = "CAUSAL_HOST_O10_NOT_CORROBORATED_O10"
TARGET_NOT_CORROBORATED = "RESOLVED_HOST_GATE_TARGET_NOT_CORROBORATED_ARTIFACT"
MIXED_LINEAGES = "MIXED_CORROBORATED_ARTIFACT_LINEAGES_IN_ONE_HOST_ENVELOPE"


def _resolved_targets(host: dict[str, Any]) -> dict[str, str]:
    states = host["host_gate_states"]
    resolutions = host["host_gate_resolutions"]
    return {
        gate: resolutions[gate]["target_ref"]
        for gate in GATES
        if states[gate] in {"PASS", "FAIL"}
    }


def verify_corroboration_causal_host_lineage(
    *,
    pr568_receipt: dict[str, Any],
    pr572_receipt: dict[str, Any],
    causal_host_admission_receipt: dict[str, Any],
) -> list[str]:
    """Require one causal envelope to observe one exact corroborated proof lineage."""
    violations = [
        CORROBORATION_PREFIX + item
        for item in verify_live_causal_corroboration(
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

    corroboration = admit_live_causal_corroboration(
        pr568_receipt=pr568_receipt,
        pr572_receipt=pr572_receipt,
    )
    corroborated_o10 = pr568_receipt["causal_post_closure_receipt_identity"]
    if causal_host_admission_receipt["post_closure_receipt_identity"] != corroborated_o10:
        violations.append(CAUSAL_O10_WORLD_MISMATCH)

    allowed_refs = {
        corroboration["pr568_artifact_ref"],
        corroboration["pr572_artifact_ref"],
    }
    resolved_targets = _resolved_targets(causal_host_admission_receipt)
    for gate, target_ref in resolved_targets.items():
        if target_ref not in allowed_refs:
            violations.append(f"{TARGET_NOT_CORROBORATED}:{gate}")

    selected_refs = set(resolved_targets.values()) & allowed_refs
    if len(selected_refs) > 1:
        violations.append(MIXED_LINEAGES)
    return list(dict.fromkeys(violations))


def admit_corroboration_causal_host_lineage(**kwargs: Any) -> dict[str, Any]:
    """Emit evidence about one observed proof lineage while preserving its corroborating peer."""
    violations = verify_corroboration_causal_host_lineage(**kwargs)
    if violations:
        raise ValueError(
            "corroboration causal host lineage failed: " + ",".join(violations)
        )

    corroboration = admit_live_causal_corroboration(
        pr568_receipt=kwargs["pr568_receipt"],
        pr572_receipt=kwargs["pr572_receipt"],
    )
    host = kwargs["causal_host_admission_receipt"]
    resolved_targets = _resolved_targets(host)
    selected = sorted(set(resolved_targets.values()))
    observed_ref = selected[0] if selected else None
    peer_ref = None
    if observed_ref is not None:
        peer_ref = (
            corroboration["pr572_artifact_ref"]
            if observed_ref == corroboration["pr568_artifact_ref"]
            else corroboration["pr568_artifact_ref"]
        )

    return {
        "version": VERSION,
        "corroboration_reproved": True,
        "causal_host_envelope_integrity_checked": True,
        "same_corroborated_causal_o10_world_proven": True,
        "proof_artifacts_remain_distinct": True,
        "pr568_artifact_ref": corroboration["pr568_artifact_ref"],
        "pr572_artifact_ref": corroboration["pr572_artifact_ref"],
        "resolved_host_gate_count": len(resolved_targets),
        "resolved_host_gates": sorted(resolved_targets),
        "observed_proof_artifact_ref": observed_ref,
        "corroborating_peer_artifact_ref": peer_ref,
        "all_resolved_host_gates_share_one_proof_lineage": True,
        "host_observation_transferred_to_peer_artifact": False,
        "host_gate_states": dict(host["host_gate_states"]),
        "host_observation_set_complete": bool(host["host_observation_set_complete"]),
        "causal_host_envelope_reproved_by_child": False,
        "causal_host_envelope_producer_authenticated": False,
        "semantic_equivalence_of_proof_artifacts_proven": False,
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
