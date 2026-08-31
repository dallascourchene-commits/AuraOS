#!/usr/bin/env python3
"""Evidence-only persistent cognition admission and corroboration projector.

This module is intentionally storage-free and effect-free. It verifies closed
evidence-node records, applies hard eligibility before any relation/ranking use,
preserves distinct artifact identities, and emits deterministic relations plus
dependency-distinct corroboration counts.

It does NOT establish semantic truth, producer authentication, effect authority,
or native/private model KV state.
"""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

VERSION = "AURA_PROVENANCE_CORROBORATION_MEMORY_ADMISSION_V1"
NODE_VERSION = "AURA_PROVENANCE_EVIDENCE_NODE_V1"
DIGEST_PROFILE = "JSON_SORT_KEYS_COMPACT_UTF8_V1"

NODE_FIELDS = {
    "version",
    "artifact_ref",
    "claim_key",
    "claim_value_ref",
    "world_ref",
    "dependency_class_ref",
    "generation_ref",
    "allowed_scopes",
    "allowed_use_classes",
    "current",
    "digest_verified",
    "schema_ok",
    "revoked",
    "supersedes_artifact_refs",
    "receipt_identity",
}
IDENTITY_FIELDS = {
    "kind",
    "algorithm_or_provider",
    "canonicalization_profile",
    "scope_profile",
    "value",
    "schema_version",
}
CONTEXT_FIELDS = {"scope", "use_class"}

ELIGIBILITY_REASON_ORDER = (
    "SCOPE_NOT_ALLOWED",
    "USE_CLASS_NOT_ALLOWED",
    "NOT_CURRENT",
    "DIGEST_NOT_VERIFIED",
    "SCHEMA_NOT_OK",
    "REVOKED",
)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _require_exact_bool(value: Any, field: str) -> None:
    if type(value) is not bool:
        raise ValueError(f"{field}:EXPECTED_BOOL")


def _require_str(value: Any, field: str) -> None:
    if type(value) is not str or not value:
        raise ValueError(f"{field}:EXPECTED_NONEMPTY_STRING")


def _require_string_list(value: Any, field: str, *, allow_empty: bool = False) -> None:
    if type(value) is not list:
        raise ValueError(f"{field}:EXPECTED_LIST")
    if not allow_empty and not value:
        raise ValueError(f"{field}:EXPECTED_NONEMPTY_LIST")
    if any(type(item) is not str or not item for item in value):
        raise ValueError(f"{field}:EXPECTED_STRING_ITEMS")
    if len(set(value)) != len(value):
        raise ValueError(f"{field}:DUPLICATE_ITEM")


def _identity_for(payload: dict[str, Any], *, scope: str) -> dict[str, str]:
    return {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": DIGEST_PROFILE,
        "scope_profile": scope,
        "value": _sha(payload),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }


def seal_evidence_node(node: dict[str, Any]) -> dict[str, Any]:
    """Return a deep-copied node with a deterministic self-integrity identity."""
    out = copy.deepcopy(node)
    out.pop("receipt_identity", None)
    out["receipt_identity"] = _identity_for(out, scope=NODE_VERSION)
    violations = verify_evidence_node(out)
    if violations:
        raise ValueError(";".join(violations))
    return out


def verify_evidence_node(node: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    if type(node) is not dict:
        return ["NODE_EXPECTED_DICT"]
    if set(node) != NODE_FIELDS:
        return ["NODE_CLOSED_SCHEMA_MISMATCH"]
    try:
        if node["version"] != NODE_VERSION:
            violations.append("NODE_VERSION_MISMATCH")
        for field in (
            "artifact_ref",
            "claim_key",
            "claim_value_ref",
            "world_ref",
            "dependency_class_ref",
            "generation_ref",
        ):
            _require_str(node[field], field)
        _require_string_list(node["allowed_scopes"], "allowed_scopes")
        _require_string_list(node["allowed_use_classes"], "allowed_use_classes")
        _require_string_list(
            node["supersedes_artifact_refs"],
            "supersedes_artifact_refs",
            allow_empty=True,
        )
        for field in ("current", "digest_verified", "schema_ok", "revoked"):
            _require_exact_bool(node[field], field)
    except ValueError as exc:
        violations.append(str(exc))

    identity = node.get("receipt_identity")
    if type(identity) is not dict or set(identity) != IDENTITY_FIELDS:
        violations.append("NODE_RECEIPT_IDENTITY_SCHEMA_MISMATCH")
        return violations
    expected_meta = {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": DIGEST_PROFILE,
        "scope_profile": NODE_VERSION,
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }
    for key, expected in expected_meta.items():
        if identity.get(key) != expected:
            violations.append(f"NODE_RECEIPT_IDENTITY_{key.upper()}_MISMATCH")
    payload = copy.deepcopy(node)
    payload.pop("receipt_identity", None)
    if identity.get("value") != _sha(payload):
        violations.append("NODE_RECEIPT_IDENTITY_DIGEST_MISMATCH")
    return violations


def verify_context(context: dict[str, Any]) -> list[str]:
    if type(context) is not dict or set(context) != CONTEXT_FIELDS:
        return ["CONTEXT_CLOSED_SCHEMA_MISMATCH"]
    violations: list[str] = []
    for field in ("scope", "use_class"):
        if type(context[field]) is not str or not context[field]:
            violations.append(f"CONTEXT_{field.upper()}_INVALID")
    return violations


def eligibility_violations(node: dict[str, Any], context: dict[str, Any]) -> list[str]:
    violations = verify_evidence_node(node)
    violations.extend(verify_context(context))
    if violations:
        return violations

    reasons: list[str] = []
    if context["scope"] not in node["allowed_scopes"] and "*" not in node["allowed_scopes"]:
        reasons.append("SCOPE_NOT_ALLOWED")
    if (
        context["use_class"] not in node["allowed_use_classes"]
        and "*" not in node["allowed_use_classes"]
    ):
        reasons.append("USE_CLASS_NOT_ALLOWED")
    if not node["current"]:
        reasons.append("NOT_CURRENT")
    if not node["digest_verified"]:
        reasons.append("DIGEST_NOT_VERIFIED")
    if not node["schema_ok"]:
        reasons.append("SCHEMA_NOT_OK")
    if node["revoked"]:
        reasons.append("REVOKED")
    return [reason for reason in ELIGIBILITY_REASON_ORDER if reason in reasons]


def _relation(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any] | None:
    if b["artifact_ref"] in a["supersedes_artifact_refs"]:
        return {
            "kind": "SUPERSEDES",
            "from_artifact_ref": a["artifact_ref"],
            "to_artifact_ref": b["artifact_ref"],
        }
    if a["artifact_ref"] in b["supersedes_artifact_refs"]:
        return {
            "kind": "SUPERSEDES",
            "from_artifact_ref": b["artifact_ref"],
            "to_artifact_ref": a["artifact_ref"],
        }
    if a["claim_key"] != b["claim_key"] or a["world_ref"] != b["world_ref"]:
        return None
    left, right = sorted((a["artifact_ref"], b["artifact_ref"]))
    if a["claim_value_ref"] != b["claim_value_ref"]:
        return {
            "kind": "CONTRADICTS",
            "left_artifact_ref": left,
            "right_artifact_ref": right,
            "claim_key": a["claim_key"],
            "world_ref": a["world_ref"],
        }
    if a["artifact_ref"] == b["artifact_ref"]:
        return None
    return {
        "kind": "CORROBORATES",
        "left_artifact_ref": left,
        "right_artifact_ref": right,
        "claim_key": a["claim_key"],
        "claim_value_ref": a["claim_value_ref"],
        "world_ref": a["world_ref"],
        "dependency_distinct": a["dependency_class_ref"] != b["dependency_class_ref"],
    }


def admit_evidence_nodes(
    nodes: list[dict[str, Any]],
    context: dict[str, Any],
) -> dict[str, Any]:
    """Project verified evidence into an evidence-only admission receipt.

    Hard eligibility is evaluated before corroboration counts. Supersession relations
    are retained even when the superseded node is stale, but CORROBORATES and
    CONTRADICTS edges are computed only between eligible nodes.
    """
    if type(nodes) is not list:
        raise ValueError("NODES_EXPECTED_LIST")
    context_violations = verify_context(context)
    if context_violations:
        raise ValueError(";".join(context_violations))

    verified: list[dict[str, Any]] = []
    seen_artifacts: set[str] = set()
    excluded: dict[str, list[str]] = {}

    for raw in nodes:
        node_violations = verify_evidence_node(raw)
        if node_violations:
            raise ValueError(";".join(node_violations))
        artifact_ref = raw["artifact_ref"]
        if artifact_ref in seen_artifacts:
            raise ValueError(f"DUPLICATE_ARTIFACT_REF:{artifact_ref}")
        seen_artifacts.add(artifact_ref)
        node = copy.deepcopy(raw)
        verified.append(node)
        reasons = eligibility_violations(node, context)
        if reasons:
            excluded[artifact_ref] = reasons

    eligible = [
        node for node in verified if node["artifact_ref"] not in excluded
    ]

    relations: list[dict[str, Any]] = []
    for i, left in enumerate(verified):
        for right in verified[i + 1 :]:
            rel = _relation(left, right)
            if rel and rel["kind"] == "SUPERSEDES":
                relations.append(rel)

    for i, left in enumerate(eligible):
        for right in eligible[i + 1 :]:
            rel = _relation(left, right)
            if rel and rel["kind"] != "SUPERSEDES":
                relations.append(rel)

    relation_key = lambda r: (
        r["kind"],
        r.get("from_artifact_ref", r.get("left_artifact_ref", "")),
        r.get("to_artifact_ref", r.get("right_artifact_ref", "")),
    )
    relations.sort(key=relation_key)

    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for node in eligible:
        key = (node["claim_key"], node["claim_value_ref"], node["world_ref"])
        groups.setdefault(key, []).append(node)

    corroboration_groups: list[dict[str, Any]] = []
    for key in sorted(groups):
        members = groups[key]
        dep_classes = sorted({node["dependency_class_ref"] for node in members})
        corroboration_groups.append(
            {
                "claim_key": key[0],
                "claim_value_ref": key[1],
                "world_ref": key[2],
                "eligible_artifact_refs": sorted(
                    node["artifact_ref"] for node in members
                ),
                "dependency_class_refs": dep_classes,
                "kappa": len(dep_classes),
            }
        )

    contradictory_claim_worlds = sorted(
        {
            (rel["claim_key"], rel["world_ref"])
            for rel in relations
            if rel["kind"] == "CONTRADICTS"
        }
    )

    payload: dict[str, Any] = {
        "version": VERSION,
        "context": copy.deepcopy(context),
        "verified_artifact_refs": sorted(node["artifact_ref"] for node in verified),
        "eligible_artifact_refs": sorted(node["artifact_ref"] for node in eligible),
        "excluded_by_artifact_ref": {
            key: excluded[key] for key in sorted(excluded)
        },
        "relations": relations,
        "corroboration_groups": corroboration_groups,
        "contradictory_claim_worlds": [
            {"claim_key": claim_key, "world_ref": world_ref}
            for claim_key, world_ref in contradictory_claim_worlds
        ],
        "hard_eligibility_precedes_ranking": True,
        "input_currentness_reproved_by_this_module": False,
        "claim_world_semantics_reproved_by_this_module": False,
        "artifact_identity_collapse_performed": False,
        "last_write_wins_performed": False,
        "semantic_truth_proven": False,
        "producer_authentication_proven": False,
        "effect_authority_proven": False,
        "native_private_transformer_kv_accessed": False,
    }
    payload["receipt_identity"] = _identity_for(payload, scope=VERSION)
    return payload
