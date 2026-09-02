#!/usr/bin/env python3
"""Integrity/adequacy checks for Aura provider and physical-swarm receipts.

Transport success is not objective success. These checks are intentionally conservative
and are designed to prevent refusal text, provider identity contradictions, metadata route
mismatches, or a single self-triangulating response from being promoted as a valid
physical swarm result.

The installed host remains the authority for authenticated endpoint identity, transport
request IDs, durable idempotency, billing/accounting identity, and effect receipts.
A digest proves internal consistency, not authority: physical-swarm proof therefore
requires a host-persisted fanout compile manifest plus exact leaf-to-child binding.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

REFUSAL_MARKERS = (
    "i cannot execute",
    "i can't execute",
    "i cannot access",
    "i can't access",
    "i don't have access",
    "i do not have access",
    "i cannot perform",
    "i can't perform",
)
DEEPSEEK_IDENTITY_CONTRADICTIONS = (
    "i'm claude",
    "i am claude",
    "created by anthropic",
    "anthropic, not deepseek",
)
ROLE_SIMULATION_MARKERS = (
    "a+ construct",
    "b- challenge",
    "c0 verify",
    "three distinct identity roles",
)
FANOUT_MANIFEST_SCHEMA = "AuraPhysicalSwarmCompileReceiptV1"


class SwarmIntegrityError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _identity(value: Any) -> str:
    """Normalize provider/model identifiers without inventing aliases."""
    return str(value or "").strip().casefold()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def classify_model_output(
    record: Mapping[str, Any],
    *,
    expected_provider: str | None = None,
    expected_model: str | None = None,
    physical_swarm_expected: bool = False,
) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise SwarmIntegrityError("TERMINAL_RECORD_NOT_OBJECT")
    text = str(record.get("result") or record.get("response") or "")
    low = " ".join(text.casefold().split())
    provider = _identity(record.get("provider"))
    model = _identity(record.get("model"))
    expected_provider_norm = _identity(expected_provider)
    expected_model_norm = _identity(expected_model)

    reasons: list[str] = []
    classification = "RESULT_UNVERIFIED"

    if not text.strip():
        reasons.append("EMPTY_MODEL_OUTPUT")
        classification = "RESULT_INVALID"

    if expected_provider_norm:
        if not provider:
            reasons.append("PROVIDER_METADATA_MISSING")
            classification = "PROVIDER_IDENTITY_MISMATCH"
        elif provider != expected_provider_norm:
            reasons.append("PROVIDER_METADATA_MISMATCH")
            classification = "PROVIDER_IDENTITY_MISMATCH"

    if expected_model_norm:
        if not model:
            reasons.append("MODEL_METADATA_MISSING")
            if classification == "RESULT_UNVERIFIED":
                classification = "MODEL_IDENTITY_MISMATCH"
        elif model != expected_model_norm:
            reasons.append("MODEL_METADATA_MISMATCH")
            if classification == "RESULT_UNVERIFIED":
                classification = "MODEL_IDENTITY_MISMATCH"

    if any(marker in low for marker in REFUSAL_MARKERS):
        reasons.append("MODEL_REFUSAL")
        if classification == "RESULT_UNVERIFIED":
            classification = "MODEL_REFUSAL"

    expected_for_text = expected_provider_norm or provider
    if expected_for_text == "deepseek" and any(
        marker in low for marker in DEEPSEEK_IDENTITY_CONTRADICTIONS
    ):
        reasons.append("TEXTUAL_PROVIDER_IDENTITY_CONTRADICTION")
        classification = "PROVIDER_IDENTITY_MISMATCH"

    role_hits = sum(marker in low for marker in ROLE_SIMULATION_MARKERS)
    if physical_swarm_expected and role_hits >= 3:
        reasons.append("ROLE_FANOUT_VIOLATION")
        if classification == "RESULT_UNVERIFIED":
            classification = "ROLE_FANOUT_VIOLATION"

    if not reasons:
        classification = "RESULT_NEEDS_OBJECTIVE_VERIFICATION"

    return {
        "classification": classification,
        "reasons": reasons,
        "provider_observed": provider or "UNKNOWN",
        "model_observed": model or "UNKNOWN",
        "provider_expected": expected_provider_norm or "UNKNOWN",
        "model_expected": expected_model_norm or "UNKNOWN",
        "text_present": bool(text.strip()),
        "objective_verification_required": classification
        == "RESULT_NEEDS_OBJECTIVE_VERIFICATION",
    }


def _validated_manifest(
    manifest: Mapping[str, Any],
    *,
    parent_command_id: str,
    target_size: int,
) -> tuple[str, dict[str, dict[str, Any]]]:
    """Validate internal manifest consistency before comparing trusted expected leaves."""
    if not isinstance(manifest, Mapping):
        raise SwarmIntegrityError("FANOUT_MANIFEST_REQUIRED")
    if manifest.get("schema") != FANOUT_MANIFEST_SCHEMA:
        raise SwarmIntegrityError("FANOUT_MANIFEST_SCHEMA_MISMATCH")
    if manifest.get("parent_command_id") != parent_command_id:
        raise SwarmIntegrityError("FANOUT_MANIFEST_PARENT_MISMATCH")
    if manifest.get("target_size") != target_size or manifest.get("child_count") != target_size:
        raise SwarmIntegrityError("FANOUT_MANIFEST_TARGET_MISMATCH")

    parent_payload_digest = str(manifest.get("parent_payload_digest") or "")
    if len(parent_payload_digest) != 64:
        raise SwarmIntegrityError("FANOUT_MANIFEST_PAYLOAD_DIGEST_INVALID")

    refs = manifest.get("child_refs")
    if not isinstance(refs, Sequence) or isinstance(refs, (str, bytes)):
        raise SwarmIntegrityError("FANOUT_MANIFEST_CHILD_REFS_INVALID")
    if len(refs) != target_size:
        raise SwarmIntegrityError("FANOUT_MANIFEST_CHILD_COUNT_MISMATCH")

    expected: dict[str, dict[str, Any]] = {}
    canonical_refs: list[dict[str, Any]] = []
    seen_idempotency: set[str] = set()
    seen_ordinals: set[int] = set()
    seen_roles: set[str] = set()
    seen_workers: set[str] = set()
    for ref in refs:
        if not isinstance(ref, Mapping):
            raise SwarmIntegrityError("FANOUT_MANIFEST_CHILD_REF_INVALID")
        command_id = str(ref.get("command_id") or "")
        idempotency_key = str(ref.get("idempotency_key") or "")
        role_id = str(ref.get("role_id") or "")
        worker_id = str(ref.get("worker_id") or "")
        ordinal = ref.get("ordinal")
        if (
            not command_id
            or not idempotency_key
            or not role_id
            or not worker_id
            or isinstance(ordinal, bool)
            or not isinstance(ordinal, int)
            or ordinal < 0
            or ordinal >= target_size
        ):
            raise SwarmIntegrityError("FANOUT_MANIFEST_CHILD_REF_INVALID")
        if command_id in expected:
            raise SwarmIntegrityError("FANOUT_MANIFEST_COMMAND_DUPLICATE")
        if idempotency_key in seen_idempotency:
            raise SwarmIntegrityError("FANOUT_MANIFEST_IDEMPOTENCY_DUPLICATE")
        if ordinal in seen_ordinals:
            raise SwarmIntegrityError("FANOUT_MANIFEST_ORDINAL_DUPLICATE")
        if role_id in seen_roles:
            raise SwarmIntegrityError("FANOUT_MANIFEST_ROLE_DUPLICATE")
        if worker_id in seen_workers:
            raise SwarmIntegrityError("FANOUT_MANIFEST_WORKER_DUPLICATE")
        normalized = {
            "command_id": command_id,
            "idempotency_key": idempotency_key,
            "role_id": role_id,
            "worker_id": worker_id,
            "ordinal": ordinal,
        }
        expected[command_id] = normalized
        canonical_refs.append(normalized)
        seen_idempotency.add(idempotency_key)
        seen_ordinals.add(ordinal)
        seen_roles.add(role_id)
        seen_workers.add(worker_id)

    expected_manifest_digest = _digest(
        {
            "schema": FANOUT_MANIFEST_SCHEMA,
            "parent_command_id": parent_command_id,
            "parent_idempotency_key": str(manifest.get("parent_idempotency_key") or ""),
            "parent_payload_digest": parent_payload_digest,
            "target_size": target_size,
            "children": canonical_refs,
        }
    )
    if manifest.get("manifest_digest") != expected_manifest_digest:
        raise SwarmIntegrityError("FANOUT_MANIFEST_DIGEST_MISMATCH")
    return parent_payload_digest, expected


def validate_physical_swarm_receipts(
    *,
    parent_command_id: str,
    target_size: int,
    fanout_manifest: Mapping[str, Any],
    child_receipts: Sequence[Mapping[str, Any]],
    expected_provider: str = "deepseek",
    expected_model: str | None = None,
) -> dict[str, Any]:
    """Prove physical fanout only from a trusted manifest-to-leaf bijection.

    The caller is responsible for obtaining ``fanout_manifest`` from the host-persisted
    fanout transaction rather than from the provider/model output being validated.
    """
    if isinstance(target_size, bool) or not isinstance(target_size, int) or target_size < 1:
        raise SwarmIntegrityError("INVALID_TARGET_SIZE")
    if len(child_receipts) != target_size:
        raise SwarmIntegrityError("PHYSICAL_CHILD_COUNT_MISMATCH")

    parent_payload_digest, expected_children = _validated_manifest(
        fanout_manifest,
        parent_command_id=parent_command_id,
        target_size=target_size,
    )

    worker_ids: set[str] = set()
    role_ids: set[str] = set()
    attempt_ids: set[str] = set()
    provider_request_ids: set[str] = set()
    seen_commands: set[str] = set()
    classifications: list[dict[str, Any]] = []

    for receipt in child_receipts:
        if not isinstance(receipt, Mapping):
            raise SwarmIntegrityError("INVALID_CHILD_RECEIPT")
        if receipt.get("parent_command_id") != parent_command_id:
            raise SwarmIntegrityError("PARENT_BINDING_MISMATCH")
        if receipt.get("parent_payload_digest") != parent_payload_digest:
            raise SwarmIntegrityError("PARENT_PAYLOAD_DIGEST_MISMATCH")

        command_id = str(receipt.get("command_id") or receipt.get("child_command_id") or "")
        idempotency_key = str(
            receipt.get("idempotency_key") or receipt.get("child_idempotency_key") or ""
        )
        worker_id = str(receipt.get("worker_id") or "")
        role_id = str(receipt.get("role_id") or "")
        ordinal = receipt.get("ordinal")
        attempt_id = str(receipt.get("attempt_id") or "")
        request_id = str(receipt.get("provider_request_id") or "")

        expected = expected_children.get(command_id)
        if expected is None or command_id in seen_commands:
            raise SwarmIntegrityError("CHILD_NOT_IN_FANOUT_MANIFEST")
        if (
            idempotency_key != expected["idempotency_key"]
            or worker_id != expected["worker_id"]
            or role_id != expected["role_id"]
            or ordinal != expected["ordinal"]
        ):
            raise SwarmIntegrityError("CHILD_MANIFEST_BINDING_MISMATCH")

        if worker_id in worker_ids:
            raise SwarmIntegrityError("WORKER_ID_MISSING_OR_DUPLICATE")
        if role_id in role_ids:
            raise SwarmIntegrityError("ROLE_ID_MISSING_OR_DUPLICATE")
        if not attempt_id or attempt_id in attempt_ids or attempt_id == "UNKNOWN":
            raise SwarmIntegrityError("ATTEMPT_ID_MISSING_UNKNOWN_OR_DUPLICATE")
        if not request_id or request_id in provider_request_ids:
            raise SwarmIntegrityError("PROVIDER_REQUEST_ID_MISSING_OR_DUPLICATE")

        seen_commands.add(command_id)
        worker_ids.add(worker_id)
        role_ids.add(role_id)
        attempt_ids.add(attempt_id)
        provider_request_ids.add(request_id)

        check = classify_model_output(
            receipt,
            expected_provider=expected_provider,
            expected_model=expected_model,
            physical_swarm_expected=False,
        )
        classifications.append(check)
        if check["classification"] in {
            "RESULT_INVALID",
            "MODEL_REFUSAL",
            "PROVIDER_IDENTITY_MISMATCH",
            "MODEL_IDENTITY_MISMATCH",
        }:
            raise SwarmIntegrityError(check["classification"])

    if seen_commands != set(expected_children):
        raise SwarmIntegrityError("FANOUT_MANIFEST_LEAF_SET_INCOMPLETE")

    return {
        "schema": "AuraPhysicalSwarmIntegrityReceiptV1",
        "parent_command_id": parent_command_id,
        "parent_payload_digest": parent_payload_digest,
        "fanout_manifest_digest": str(fanout_manifest["manifest_digest"]),
        "target_size": target_size,
        "physical_child_count": len(child_receipts),
        "unique_worker_count": len(worker_ids),
        "unique_role_count": len(role_ids),
        "unique_attempt_count": len(attempt_ids),
        "unique_provider_request_count": len(provider_request_ids),
        "expected_provider": _identity(expected_provider) or "UNKNOWN",
        "expected_model": _identity(expected_model) or "UNKNOWN",
        "all_children_need_objective_verification": all(
            c["classification"] == "RESULT_NEEDS_OBJECTIVE_VERIFICATION"
            for c in classifications
        ),
        "physical_fanout_proven": True,
        "reduction_allowed": True,
    }
