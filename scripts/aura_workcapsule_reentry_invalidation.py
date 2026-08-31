#!/usr/bin/env python3
"""Minimum WorkCapsule re-entry invalidation over witnessed currentness.

This module is a narrow consumer of ``aura_workcapsule_context_binding``.  It
compares one previously admitted WorkCapsuleV2 context binding with a fresh set
of graph/source witnesses and emits the minimum *dependency-class* re-entry
scope that can be justified by the available evidence:

- NONE when the admitted active dependency set is unchanged and CURRENT;
- SELECTED_SOURCES when one or more previously ACTIVE source dependencies are
  missing, stale, unknown, or have changed generation/body identity;
- FULL_GRAPH when graph currentness or graph identity changes.

No source->graph-node dependency map is proven here, so this module does not
claim node/subgraph-cone invalidation.  COLD witnesses are retained as reopen
state and cannot poison ACTIVE context.  Fresh observations cannot silently add
new ACTIVE dependencies to the prior capsule.

The receipt grants no semantic, review, mutation, execution, promotion, merge,
provider, public, or human authority.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from scripts.aura_workcapsule_context_binding import (
    ACTIVE,
    COLD,
    CURRENT,
    STALE,
    UNKNOWN,
    compile_workcapsule_context_binding,
    verify_workcapsule_context_binding,
)

VERSION = "AURA_WORKCAPSULE_REENTRY_INVALIDATION_V1"
NONE = "NONE"
SELECTED_SOURCES = "SELECTED_SOURCES"
FULL_GRAPH = "FULL_GRAPH"
REENTRY_SCOPES = {NONE, SELECTED_SOURCES, FULL_GRAPH}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _receipt_identity(payload_without_identity: dict[str, Any]) -> dict[str, str]:
    return {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
        "scope_profile": "WORKCAPSULE_REENTRY_INVALIDATION_V1_FULL_PAYLOAD_EXCEPT_RECEIPT_IDENTITY",
        "value": hashlib.sha256(_canonical_bytes(payload_without_identity)).hexdigest(),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }


def _source_key(row: dict[str, Any]) -> tuple[int, str]:
    return int(row["file_id"]), str(row["relative_path"])


def _source_ref(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "file_id": int(row["file_id"]),
        "relative_path": str(row["relative_path"]),
        "role": str(row["role"]),
        "source_generation": int(row["source_generation"]),
        "source_sha256": str(row["source_sha256"]),
        "source_byte_len": int(row["source_byte_len"]),
        "currentness": str(row["currentness"]),
        "witness_ref": str(row["witness_ref"]),
    }


def _source_binding_equal(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return all(
        left.get(field) == right.get(field)
        for field in ("file_id", "relative_path", "source_generation", "source_sha256", "source_byte_len")
    )


def _graph_identity_equal(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return all(
        left.get(field) == right.get(field)
        for field in ("graph_id", "graph_generation", "graph_basis_identity")
    )


def compile_reentry_invalidation(
    *,
    previous_binding: dict[str, Any],
    observed_graph_witness: dict[str, Any],
    observed_source_witnesses: list[dict[str, Any]],
) -> dict[str, Any]:
    """Emit a fail-closed minimum dependency-class re-entry receipt.

    ``previous_binding`` must be a coherent, previously admitted O7 binding.
    Fresh observations are normalized by the same O7 membrane so duplicate
    source identities and malformed currentness cannot bypass its owner rules.
    """
    previous_violations = verify_workcapsule_context_binding(previous_binding)
    if previous_violations:
        raise ValueError(
            "previous_binding is not a coherent WorkCapsule context binding: "
            + ",".join(previous_violations)
        )
    if previous_binding.get("context_admitted") is not True:
        raise ValueError("previous_binding must be an admitted CURRENT baseline")

    capsule = previous_binding.get("capsule")
    if not isinstance(capsule, dict):
        raise ValueError("previous_binding.capsule must be an object")

    observed_binding = compile_workcapsule_context_binding(
        capsule=capsule,
        graph_witness=observed_graph_witness,
        source_witnesses=observed_source_witnesses,
    )

    previous_graph = previous_binding["graph_witness"]
    observed_graph = observed_binding["graph_witness"]
    graph_reasons: list[str] = []
    if observed_graph["currentness"] != CURRENT:
        graph_reasons.append(f"GRAPH_{observed_graph['currentness']}")
    if not _graph_identity_equal(previous_graph, observed_graph):
        graph_reasons.append("GRAPH_IDENTITY_CHANGED")
    graph_rebind_required = bool(graph_reasons)

    previous_rows = previous_binding["source_witnesses"]
    observed_rows = observed_binding["source_witnesses"]
    previous_by_key = {_source_key(row): row for row in previous_rows}
    observed_by_key = {_source_key(row): row for row in observed_rows}

    retained_active: list[dict[str, Any]] = []
    selected_rebind: list[dict[str, Any]] = []
    unresolved_active: list[dict[str, Any]] = []
    cold_frontier_changes: list[dict[str, Any]] = []
    unbound_observations: list[dict[str, Any]] = []

    for key, prior in sorted(previous_by_key.items()):
        observed = observed_by_key.get(key)
        if prior["role"] == ACTIVE:
            if observed is None:
                row = {
                    "prior": _source_ref(prior),
                    "observed": None,
                    "reason": "ACTIVE_SOURCE_OBSERVATION_MISSING",
                }
                selected_rebind.append(row)
                unresolved_active.append(row)
                continue
            if observed["currentness"] != CURRENT:
                selected_rebind.append(
                    {
                        "prior": _source_ref(prior),
                        "observed": _source_ref(observed),
                        "reason": f"ACTIVE_SOURCE_{observed['currentness']}",
                    }
                )
                continue
            if not _source_binding_equal(prior, observed):
                selected_rebind.append(
                    {
                        "prior": _source_ref(prior),
                        "observed": _source_ref(observed),
                        "reason": "ACTIVE_SOURCE_BINDING_CHANGED",
                    }
                )
                continue
            retained_active.append(_source_ref(prior))
            continue

        # COLD evidence is reopen state only.  Record drift without making it an
        # ACTIVE invalidation cause.
        if observed is None:
            cold_frontier_changes.append(
                {
                    "prior": _source_ref(prior),
                    "observed": None,
                    "reason": "COLD_SOURCE_OBSERVATION_MISSING",
                }
            )
        elif observed["currentness"] != prior["currentness"] or not _source_binding_equal(
            prior, observed
        ):
            cold_frontier_changes.append(
                {
                    "prior": _source_ref(prior),
                    "observed": _source_ref(observed),
                    "reason": "COLD_SOURCE_STATE_CHANGED",
                }
            )

    for key, observed in sorted(observed_by_key.items()):
        if key not in previous_by_key:
            unbound_observations.append(
                {
                    "observed": _source_ref(observed),
                    "reason": "OBSERVED_SOURCE_NOT_IN_PRIOR_CAPSULE_DEPENDENCY_SET",
                    "auto_promoted_to_active_dependency": False,
                }
            )

    if graph_rebind_required:
        minimum_scope = FULL_GRAPH
        minimum_source_keys: list[dict[str, Any]] = []
    elif selected_rebind:
        minimum_scope = SELECTED_SOURCES
        minimum_source_keys = [
            {
                "file_id": row["prior"]["file_id"],
                "relative_path": row["prior"]["relative_path"],
            }
            for row in selected_rebind
        ]
    else:
        minimum_scope = NONE
        minimum_source_keys = []

    payload: dict[str, Any] = {
        "version": VERSION,
        "workcapsule_schema_id": previous_binding["workcapsule_schema_id"],
        "workcapsule_schema_version": previous_binding["workcapsule_schema_version"],
        "capsule": capsule,
        "previous_binding_identity": previous_binding["binding_identity"],
        "observed_binding_identity": observed_binding["binding_identity"],
        "minimum_reentry_scope": minimum_scope,
        "minimum_reentry_source_keys": minimum_source_keys,
        "graph_rebind_required": graph_rebind_required,
        "graph_rebind_reasons": graph_reasons,
        "previous_graph_witness": previous_graph,
        "observed_graph_witness": observed_graph,
        "retained_current_active_sources": retained_active,
        "selected_source_rebinds": selected_rebind,
        "unresolved_active_sources": unresolved_active,
        "cold_frontier_changes": cold_frontier_changes,
        "unbound_observations": unbound_observations,
        "node_level_dependency_cone_proven": False,
        "source_to_graph_dependency_map_proven": False,
        "cold_change_invalidates_active_context": False,
        "new_observation_auto_promotes_active_dependency": False,
        "authority": {
            "semantic_truth_minted": False,
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
    payload["receipt_identity"] = _receipt_identity(payload)
    return payload


def verify_reentry_invalidation(receipt: dict[str, Any]) -> list[str]:
    """Return deterministic contract violations for one O8 receipt."""
    violations: list[str] = []
    if receipt.get("version") != VERSION:
        violations.append("UNSUPPORTED_VERSION")
    scope = receipt.get("minimum_reentry_scope")
    if scope not in REENTRY_SCOPES:
        violations.append("INVALID_REENTRY_SCOPE")

    authority = receipt.get("authority")
    if not isinstance(authority, dict):
        violations.append("MALFORMED_AUTHORITY")
    elif any(bool(value) for value in authority.values()):
        violations.append("AUTHORITY_MINTED_BY_REENTRY_RECEIPT")

    graph_rebind = receipt.get("graph_rebind_required") is True
    selected = receipt.get("selected_source_rebinds")
    if not isinstance(selected, list):
        violations.append("MALFORMED_SELECTED_SOURCE_REBINDS")
        selected = []
    if graph_rebind and scope != FULL_GRAPH:
        violations.append("GRAPH_REBIND_NOT_FULL_GRAPH")
    if not graph_rebind and selected and scope != SELECTED_SOURCES:
        violations.append("SELECTED_SOURCE_REBIND_SCOPE_LAUNDERING")
    if not graph_rebind and not selected and scope != NONE:
        violations.append("UNNECESSARY_REENTRY_SCOPE")
    if receipt.get("node_level_dependency_cone_proven") is not False:
        violations.append("UNPROVEN_NODE_LEVEL_CONE_PROMOTED")
    if receipt.get("source_to_graph_dependency_map_proven") is not False:
        violations.append("UNPROVEN_SOURCE_GRAPH_MAP_PROMOTED")
    if receipt.get("cold_change_invalidates_active_context") is not False:
        violations.append("COLD_FRONTIER_PROMOTED_TO_ACTIVE_INVALIDATION")
    if receipt.get("new_observation_auto_promotes_active_dependency") is not False:
        violations.append("UNBOUND_OBSERVATION_PROMOTED")

    supplied_identity = receipt.get("receipt_identity")
    without_identity = dict(receipt)
    without_identity.pop("receipt_identity", None)
    if supplied_identity != _receipt_identity(without_identity):
        violations.append("RECEIPT_IDENTITY_MISMATCH")
    return violations
