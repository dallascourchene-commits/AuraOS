#!/usr/bin/env python3
"""Semantic validator for ARCH v2.3 continuity capsules.

JSON Schema owns structural/type validation. This module owns relational and
trusted-time invariants Draft 2020-12 cannot express, especially equality
between values at different instance paths and expiry against authoritative
current time. It is a validator only: no mutation, promotion, or merge authority.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

VERSION = "AURA_ARCH_V2_3_CAPSULE_SEMANTIC_VALIDATOR_V1"

_REQUIRED_AUTH_GATES = (
    "identity_binding",
    "witness_fresh_and_unrevoked",
    "lease_current_and_eligible",
    "causal_prior",
    "effect_binding_current",
    "dependency_and_threat_model_freshness",
    "proof_freshness",
    "verifier_independence",
    "governance_disposition",
)


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return value


def _trusted_now(now: datetime | None) -> datetime:
    current = datetime.now(timezone.utc) if now is None else now
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("validator current time must be timezone-aware")
    return current.astimezone(timezone.utc)


def _timestamp(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty RFC3339 timestamp")
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a valid RFC3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{name} must include a timezone offset")
    return parsed.astimezone(timezone.utc)


def validate_arch_v2_3_capsule_semantics(
    capsule: Mapping[str, Any], *, now: datetime | None = None
) -> None:
    """Raise ValueError if ARCH v2.3 relational/freshness invariants are violated."""
    root = _mapping(capsule, "capsule")
    current = _trusted_now(now)
    if root.get("schema_version") != "AURA_PR_CONTINUITY_CAPSULE_V2_3":
        raise ValueError("unsupported capsule schema_version")
    if root.get("harness_version") != "AURA_ARCH_V2_3":
        raise ValueError("unsupported harness_version")

    head_sha = root.get("head_sha")
    if not isinstance(head_sha, str) or len(head_sha) != 40:
        raise ValueError("capsule head_sha must be a 40-character SHA")

    jspace = _mapping(root.get("jspace_projection"), "jspace_projection")
    if jspace.get("status") == "ENABLED":
        if jspace.get("head_sha") != head_sha:
            raise ValueError("enabled JSpace head_sha must equal capsule head_sha")
        if jspace.get("freshness") != "CURRENT":
            raise ValueError("enabled JSpace must be CURRENT")
        if not jspace.get("source_refs"):
            raise ValueError("enabled JSpace requires source_refs")
        if not jspace.get("origin_refs"):
            raise ValueError("enabled JSpace requires origin_refs")
        if _timestamp(jspace.get("expires_at"), "jspace_projection.expires_at") <= current:
            raise ValueError("enabled JSpace projection is expired")

    authorization = _mapping(root.get("commit_authorization"), "commit_authorization")
    if authorization.get("status") == "VALIDATED":
        if authorization.get("validated_head_sha") != head_sha:
            raise ValueError("validated commit authorization head must equal capsule head_sha")
        gates = _mapping(authorization.get("gate_outcomes"), "commit_authorization.gate_outcomes")
        failed = [name for name in _REQUIRED_AUTH_GATES if gates.get(name) != "PASSED"]
        if failed:
            raise ValueError("validated commit authorization has non-PASSED gates: " + ", ".join(failed))
        effect_values = (
            authorization.get("authorized_effect_digest"),
            authorization.get("planned_effect_digest"),
            authorization.get("candidate_effect_digest"),
        )
        if any(not isinstance(value, str) or not value for value in effect_values):
            raise ValueError("validated commit authorization requires all effect digests")
        if len(set(effect_values)) != 1:
            raise ValueError("authorized, planned, and candidate effect digests must match")
        if _timestamp(
            authorization.get("expires_at"), "commit_authorization.expires_at"
        ) <= current:
            raise ValueError("validated commit authorization is expired")

    independence = _mapping(root.get("verification_independence"), "verification_independence")
    if independence.get("status") == "INDEPENDENT":
        required_evidence = (
            "verifier_refs",
            "model_provider_refs",
            "input_origin_refs",
            "sybil_resistance_evidence",
        )
        empty = [name for name in required_evidence if not independence.get(name)]
        if empty:
            raise ValueError("INDEPENDENT verification lacks evidence: " + ", ".join(empty))
        if not independence.get("disposition"):
            raise ValueError("INDEPENDENT verification requires disposition")
        if not independence.get("receipt_ref"):
            raise ValueError("INDEPENDENT verification requires receipt_ref")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capsule", type=Path)
    args = parser.parse_args(argv)
    value = json.loads(args.capsule.read_text(encoding="utf-8"))
    validate_arch_v2_3_capsule_semantics(value)
    print(json.dumps({"ok": True, "validator": VERSION, "capsule": str(args.capsule)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
