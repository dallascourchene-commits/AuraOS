#!/usr/bin/env python3
"""Storage-free, effect-free evidence admission and provenance projection."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any

VERSION = "AURA_PROVENANCE_CORROBORATION_MEMORY_ADMISSION_V2"
NODE_VERSION = "AURA_PROVENANCE_EVIDENCE_NODE_V2"
DIGEST_PROFILE = "JSON_SORT_KEYS_COMPACT_UTF8_V1"
SCHEME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
NODE_FIELDS = {
    "version", "artifact_ref", "artifact_ref_scheme", "artifact_ref_value",
    "evidence_type", "currentness_domain", "claim_key", "claim_value_ref", "world_ref",
    "dependency_class_ref", "generation_ref", "allowed_scopes",
    "allowed_use_classes", "current", "digest_verified", "schema_ok", "revoked",
    "supersedes_artifact_refs", "receipt_identity",
}
IDENTITY_FIELDS = {
    "kind", "algorithm_or_provider", "canonicalization_profile",
    "scope_profile", "value", "schema_version",
}
CONTEXT_FIELDS = {
    "scope", "use_class", "accepted_evidence_types", "accepted_currentness_domains"
}
REASON_ORDER = (
    "SCOPE_NOT_ALLOWED", "USE_CLASS_NOT_ALLOWED", "EVIDENCE_TYPE_NOT_ACCEPTED",
    "CURRENTNESS_DOMAIN_NOT_ACCEPTED", "NOT_CURRENT", "DIGEST_NOT_VERIFIED",
    "SCHEMA_NOT_OK", "REVOKED",
)


def _bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _sha(value: Any) -> str:
    return hashlib.sha256(_bytes(value)).hexdigest()


def _require_bool(value: Any, field: str) -> None:
    if type(value) is not bool:
        raise ValueError(f"{field}:EXPECTED_BOOL")


def _require_str(value: Any, field: str) -> None:
    if type(value) is not str or not value:
        raise ValueError(f"{field}:EXPECTED_NONEMPTY_STRING")


def _require_list(value: Any, field: str, *, allow_empty: bool = False) -> None:
    if type(value) is not list or (not allow_empty and not value):
        raise ValueError(f"{field}:EXPECTED_LIST")
    if any(type(item) is not str or not item for item in value):
        raise ValueError(f"{field}:EXPECTED_STRING_ITEMS")
    if len(set(value)) != len(value):
        raise ValueError(f"{field}:DUPLICATE_ITEM")


def _require_typed_ref(node: dict[str, Any]) -> None:
    scheme = node["artifact_ref_scheme"]
    value = node["artifact_ref_value"]
    ref = node["artifact_ref"]
    _require_str(scheme, "artifact_ref_scheme")
    _require_str(value, "artifact_ref_value")
    _require_str(ref, "artifact_ref")
    if not SCHEME_RE.fullmatch(scheme):
        raise ValueError("artifact_ref_scheme:INVALID_SCHEME")
    if ":" in value or ref != f"{scheme}:{value}":
        raise ValueError("artifact_ref:TYPED_REFERENCE_MISMATCH")
    if scheme.endswith("sha256") and not SHA256_RE.fullmatch(value):
        raise ValueError("artifact_ref_value:EXPECTED_LOWER_HEX_SHA256")


def _identity(payload: dict[str, Any], scope: str) -> dict[str, str]:
    return {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": DIGEST_PROFILE,
        "scope_profile": scope,
        "value": _sha(payload),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }


def seal_evidence_node(node: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(node)
    out.pop("receipt_identity", None)
    out["receipt_identity"] = _identity(out, NODE_VERSION)
    violations = verify_evidence_node(out)
    if violations:
        raise ValueError(";".join(violations))
    return out


def verify_evidence_node(node: dict[str, Any]) -> list[str]:
    if type(node) is not dict:
        return ["NODE_EXPECTED_DICT"]
    if set(node) != NODE_FIELDS:
        return ["NODE_CLOSED_SCHEMA_MISMATCH"]
    violations: list[str] = []
    try:
        if node["version"] != NODE_VERSION:
            violations.append("NODE_VERSION_MISMATCH")
        _require_typed_ref(node)
        for field in (
            "evidence_type", "currentness_domain", "claim_key", "claim_value_ref",
            "world_ref", "dependency_class_ref", "generation_ref",
        ):
            _require_str(node[field], field)
        _require_list(node["allowed_scopes"], "allowed_scopes")
        _require_list(node["allowed_use_classes"], "allowed_use_classes")
        _require_list(node["supersedes_artifact_refs"], "supersedes_artifact_refs", allow_empty=True)
        for field in ("current", "digest_verified", "schema_ok", "revoked"):
            _require_bool(node[field], field)
    except ValueError as exc:
        violations.append(str(exc))

    identity = node.get("receipt_identity")
    if type(identity) is not dict or set(identity) != IDENTITY_FIELDS:
        return violations + ["NODE_RECEIPT_IDENTITY_SCHEMA_MISMATCH"]
    meta = {
        "kind": "DIGEST", "algorithm_or_provider": "sha256",
        "canonicalization_profile": DIGEST_PROFILE, "scope_profile": NODE_VERSION,
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }
    for key, expected in meta.items():
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
    for field in ("accepted_evidence_types", "accepted_currentness_domains"):
        try:
            _require_list(context[field], field)
        except ValueError as exc:
            violations.append(f"CONTEXT_{exc}")
    return violations


def eligibility_violations(node: dict[str, Any], context: dict[str, Any]) -> list[str]:
    violations = verify_evidence_node(node) + verify_context(context)
    if violations:
        return violations
    reasons: list[str] = []
    if context["scope"] not in node["allowed_scopes"] and "*" not in node["allowed_scopes"]:
        reasons.append("SCOPE_NOT_ALLOWED")
    if context["use_class"] not in node["allowed_use_classes"] and "*" not in node["allowed_use_classes"]:
        reasons.append("USE_CLASS_NOT_ALLOWED")
    accepted_types = context["accepted_evidence_types"]
    if node["evidence_type"] not in accepted_types and "*" not in accepted_types:
        reasons.append("EVIDENCE_TYPE_NOT_ACCEPTED")
    accepted_domains = context["accepted_currentness_domains"]
    if node["currentness_domain"] not in accepted_domains and "*" not in accepted_domains:
        reasons.append("CURRENTNESS_DOMAIN_NOT_ACCEPTED")
    if not node["current"]:
        reasons.append("NOT_CURRENT")
    if not node["digest_verified"]:
        reasons.append("DIGEST_NOT_VERIFIED")
    if not node["schema_ok"]:
        reasons.append("SCHEMA_NOT_OK")
    if node["revoked"]:
        reasons.append("REVOKED")
    return [r for r in REASON_ORDER if r in reasons]


def _relation(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any] | None:
    if b["artifact_ref"] in a["supersedes_artifact_refs"]:
        return {"kind": "SUPERSEDES", "from_artifact_ref": a["artifact_ref"], "to_artifact_ref": b["artifact_ref"]}
    if a["artifact_ref"] in b["supersedes_artifact_refs"]:
        return {"kind": "SUPERSEDES", "from_artifact_ref": b["artifact_ref"], "to_artifact_ref": a["artifact_ref"]}
    if a["claim_key"] != b["claim_key"] or a["world_ref"] != b["world_ref"]:
        return None
    left, right = sorted((a["artifact_ref"], b["artifact_ref"]))
    if a["claim_value_ref"] != b["claim_value_ref"]:
        return {"kind": "CONTRADICTS", "left_artifact_ref": left, "right_artifact_ref": right, "claim_key": a["claim_key"], "world_ref": a["world_ref"]}
    if a["artifact_ref"] == b["artifact_ref"]:
        return None
    return {
        "kind": "CORROBORATES", "left_artifact_ref": left, "right_artifact_ref": right,
        "claim_key": a["claim_key"], "claim_value_ref": a["claim_value_ref"], "world_ref": a["world_ref"],
        "dependency_distinct": a["dependency_class_ref"] != b["dependency_class_ref"],
        "reference_schemes_distinct": a["artifact_ref_scheme"] != b["artifact_ref_scheme"],
        "reference_values_equal": a["artifact_ref_value"] == b["artifact_ref_value"],
        "evidence_types_distinct": a["evidence_type"] != b["evidence_type"],
        "currentness_domains_distinct": a["currentness_domain"] != b["currentness_domain"],
        "proof_artifacts_interchangeable": False,
        "currentness_domains_interchangeable": False,
        "rank_transition_credit": False,
    }


def _type_partition(members: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_type: dict[str, set[str]] = {}
    for member in members:
        by_type.setdefault(member["evidence_type"], set()).add(member["dependency_class_ref"])
    return [
        {
            "evidence_type": evidence_type,
            "dependency_class_refs": sorted(by_type[evidence_type]),
            "kappa": len(by_type[evidence_type]),
        }
        for evidence_type in sorted(by_type)
    ]


def admit_evidence_nodes(nodes: list[dict[str, Any]], context: dict[str, Any]) -> dict[str, Any]:
    if type(nodes) is not list:
        raise ValueError("NODES_EXPECTED_LIST")
    context_violations = verify_context(context)
    if context_violations:
        raise ValueError(";".join(context_violations))

    verified: list[dict[str, Any]] = []
    seen: set[str] = set()
    excluded: dict[str, list[str]] = {}
    for raw in nodes:
        violations = verify_evidence_node(raw)
        if violations:
            raise ValueError(";".join(violations))
        ref = raw["artifact_ref"]
        if ref in seen:
            raise ValueError(f"DUPLICATE_ARTIFACT_REF:{ref}")
        seen.add(ref)
        item = copy.deepcopy(raw)
        verified.append(item)
        reasons = eligibility_violations(item, context)
        if reasons:
            excluded[ref] = reasons
    eligible = [n for n in verified if n["artifact_ref"] not in excluded]

    relations: list[dict[str, Any]] = []
    for i, a in enumerate(verified):
        for b in verified[i + 1:]:
            rel = _relation(a, b)
            if rel and rel["kind"] == "SUPERSEDES":
                relations.append(rel)
    for i, a in enumerate(eligible):
        for b in eligible[i + 1:]:
            rel = _relation(a, b)
            if rel and rel["kind"] != "SUPERSEDES":
                relations.append(rel)
    relations.sort(key=lambda r: (r["kind"], r.get("from_artifact_ref", r.get("left_artifact_ref", "")), r.get("to_artifact_ref", r.get("right_artifact_ref", ""))))

    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for item in eligible:
        groups.setdefault((item["claim_key"], item["claim_value_ref"], item["world_ref"]), []).append(item)
    corroboration_groups = []
    for key in sorted(groups):
        members = groups[key]
        deps = sorted({m["dependency_class_ref"] for m in members})
        corroboration_groups.append({
            "claim_key": key[0], "claim_value_ref": key[1], "world_ref": key[2],
            "eligible_artifact_refs": sorted(m["artifact_ref"] for m in members),
            "artifact_reference_schemes": sorted({m["artifact_ref_scheme"] for m in members}),
            "evidence_types": sorted({m["evidence_type"] for m in members}),
            "currentness_domains": sorted({m["currentness_domain"] for m in members}),
            "dependency_class_refs": deps,
            "kappa": len(deps),
            "kappa_by_evidence_type": _type_partition(members),
            "cross_type_kappa_is_rank_neutral": True,
            "cross_currentness_domain_kappa_is_rank_neutral": True,
            "corroboration_count_grants_host_rank": False,
        })
    contradictory = sorted({(r["claim_key"], r["world_ref"]) for r in relations if r["kind"] == "CONTRADICTS"})

    out: dict[str, Any] = {
        "version": VERSION,
        "context": copy.deepcopy(context),
        "verified_artifact_refs": sorted(n["artifact_ref"] for n in verified),
        "eligible_artifact_refs": sorted(n["artifact_ref"] for n in eligible),
        "excluded_by_artifact_ref": {k: excluded[k] for k in sorted(excluded)},
        "relations": relations,
        "corroboration_groups": corroboration_groups,
        "contradictory_claim_worlds": [{"claim_key": k, "world_ref": w} for k, w in contradictory],
        "hard_eligibility_precedes_ranking": True,
        "typed_artifact_reference_schemes_preserved": True,
        "reference_scheme_aliasing_performed": False,
        "typed_evidence_objects_preserved": True,
        "proof_type_cross_cast_performed": False,
        "typed_currentness_domains_preserved": True,
        "current_true_is_domain_scoped": True,
        "currentness_domain_cross_cast_performed": False,
        "type_partitioned_corroboration_accounting": True,
        "corroboration_rank_transition_performed": False,
        "explicit_resolver_required_for_host_rank_transition": True,
        "input_currentness_reproved_by_this_module": False,
        "claim_world_semantics_reproved_by_this_module": False,
        "artifact_identity_collapse_performed": False,
        "last_write_wins_performed": False,
        "semantic_truth_proven": False,
        "producer_authentication_proven": False,
        "effect_authority_proven": False,
        "native_private_transformer_kv_accessed": False,
    }
    out["receipt_identity"] = _identity(out, VERSION)
    return out
