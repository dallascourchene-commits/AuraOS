#!/usr/bin/env python3
"""Route-bound physical-swarm reduction for AWJ-033.

The lower-level physical receipt validator proves manifest/leaf identity. This wrapper
adds the Gate-10 route invariant: an exact current provider/model must be supplied and
each leaf must carry the same pre-effect admitted route before physical fanout can be
promoted.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from drive_route_admission import RETIRED_MODELS
from drive_swarm_integrity import SwarmIntegrityError, validate_physical_swarm_receipts


def _identity(value: Any) -> str:
    return str(value or "").strip().casefold()


def validate_route_bound_physical_swarm_receipts(
    *,
    parent_command_id: str,
    target_size: int,
    fanout_manifest: Mapping[str, Any],
    child_receipts: Sequence[Mapping[str, Any]],
    expected_provider: str,
    expected_model: str,
) -> dict[str, Any]:
    provider = _identity(expected_provider)
    model = _identity(expected_model)
    if not provider:
        raise SwarmIntegrityError("EXPECTED_PROVIDER_REQUIRED")
    if not model:
        raise SwarmIntegrityError("EXPECTED_MODEL_REQUIRED")
    if model in RETIRED_MODELS:
        raise SwarmIntegrityError("EXPECTED_MODEL_RETIRED")

    route_digests: set[str] = set()
    for receipt in child_receipts:
        if not isinstance(receipt, Mapping):
            raise SwarmIntegrityError("INVALID_CHILD_RECEIPT")
        if _identity(receipt.get("route_provider")) != provider:
            raise SwarmIntegrityError("CHILD_ROUTE_PROVIDER_MISMATCH")
        if _identity(receipt.get("route_model")) != model:
            raise SwarmIntegrityError("CHILD_ROUTE_MODEL_MISMATCH")
        route_digest = str(receipt.get("route_admission_digest") or "").strip()
        if len(route_digest) != 64:
            raise SwarmIntegrityError("CHILD_ROUTE_ADMISSION_MISSING")
        if route_digest in route_digests:
            # Each physical child is command-bound, so its route admission digest
            # must be independently bound rather than copied from a sibling.
            raise SwarmIntegrityError("CHILD_ROUTE_ADMISSION_DUPLICATE")
        route_digests.add(route_digest)

    out = validate_physical_swarm_receipts(
        parent_command_id=parent_command_id,
        target_size=target_size,
        fanout_manifest=fanout_manifest,
        child_receipts=child_receipts,
        expected_provider=provider,
        expected_model=model,
    )
    out["schema"] = "AuraRouteBoundPhysicalSwarmIntegrityReceiptV1"
    out["route_bound"] = True
    out["route_admission_count"] = len(route_digests)
    out["expected_provider"] = provider
    out["expected_model"] = model
    return out
