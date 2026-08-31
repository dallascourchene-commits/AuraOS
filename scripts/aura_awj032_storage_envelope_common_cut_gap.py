#!/usr/bin/env python3
"""Expose the missing common-cut relation between two valid ThinkPad observations.

PR606 can make one bounded storage-probe artifact current in its *owned evidence
generation*. PR605 can observe one sustained operating envelope at an absolute
time. Neither artifact owns an authenticated host/session-generation join, and
the storage receipt carries no absolute observation timestamp. Therefore the
pair cannot be promoted to same-host/same-time evidence, causal attribution, or
performance admission merely because both are valid.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
from typing import Any

from scripts.aura_awj032_storage_probe_currentness_domain import (
    CURRENTNESS_DOMAIN as STORAGE_CURRENTNESS_DOMAIN,
    project_bounded_storage_probe_currentness,
)
from tools.awj032.glm53_owner_host_c2_handoff import OwnerHostC2CanaryRequest
from tools.awj032.thinkpad_bounded_storage_probe import ThinkPadStorageProbeReceipt
from tools.thinkpad_sustained_operating_envelope import (
    CURRENTNESS_DOMAIN as ENVELOPE_CURRENTNESS_DOMAIN,
    SustainedOperatingEnvelope,
)

VERSION = "AURA_AWJ032_STORAGE_ENVELOPE_COMMON_CUT_GAP_V1"
PR606_EXACT_HEAD = "91a591d7208ff66b679cbb03ee9adc2118f29cc3"
PR606_EXACT_RUN = 33364662491
PR605_EXACT_HEAD = "c6d691dbef07e7249c470bd34feb19f1d023987b"
PR605_EXACT_RUN = 33364574120

MISSING_COMMON_CUT_KEYS = (
    "authenticated_host_session_or_generation_ref",
    "storage_observed_at_utc",
)


class StorageEnvelopeCommonCutGapError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise StorageEnvelopeCommonCutGapError("NONCANONICAL_COMMON_CUT_GAP") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _parse_offset_aware_timestamp(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StorageEnvelopeCommonCutGapError("ENVELOPE_OBSERVATION_TIME_REQUIRED")
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise StorageEnvelopeCommonCutGapError("ENVELOPE_OBSERVATION_TIME_INVALID") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise StorageEnvelopeCommonCutGapError("ENVELOPE_OBSERVATION_TIME_MUST_BE_OFFSET_AWARE")
    return text


def _assert_envelope_ceiling(envelope: SustainedOperatingEnvelope) -> None:
    if type(envelope) is not SustainedOperatingEnvelope:
        raise StorageEnvelopeCommonCutGapError("EXACT_OPERATING_ENVELOPE_TYPE_REQUIRED")
    if envelope.currentness_domain != ENVELOPE_CURRENTNESS_DOMAIN:
        raise StorageEnvelopeCommonCutGapError("OPERATING_ENVELOPE_CURRENTNESS_DOMAIN_DRIFT")
    if envelope.current_at_observation_time_only is not True:
        raise StorageEnvelopeCommonCutGapError("OPERATING_ENVELOPE_CURRENTNESS_SCOPE_WIDENED")
    for field in (
        "thinkpad_identity_proven",
        "thermal_throttling_proven",
        "battery_power_limit_proven",
        "memory_pressure_safe_for_model",
        "performance_effect_proven",
        "model_execution_observed",
        "producer_authenticated",
        "effect_authority_proven",
        "g2_admitted",
    ):
        if getattr(envelope, field) is not False:
            raise StorageEnvelopeCommonCutGapError("OPERATING_ENVELOPE_CEILING_WIDENED", field)


@dataclass(frozen=True)
class StorageEnvelopeCommonCutGapReceipt:
    request_digest: str
    request_host_snapshot_digest: str
    storage_probe_receipt_digest: str
    storage_probe_evidence_ref: str
    storage_currentness_domain: str
    storage_current_in_owned_generation: bool
    envelope_observation_digest: str
    envelope_evidence_ref: str
    envelope_currentness_domain: str
    envelope_observed_at_utc: str
    envelope_current_at_observation_time_only: bool
    missing_common_cut_keys: tuple[str, ...] = MISSING_COMMON_CUT_KEYS
    authenticated_host_session_or_generation_bound: bool = False
    storage_absolute_observation_time_available: bool = False
    same_host_identity_proven: bool = False
    temporal_overlap_proven: bool = False
    same_host_common_cut_proven: bool = False
    host_snapshot_digest_is_authenticated_host_identity: bool = False
    causal_attribution_proven: bool = False
    performance_join_admissible: bool = False
    physical_nvme_currentness_proven: bool = False
    producer_authenticated: bool = False
    w4_admitted: bool = False
    g2_admitted: bool = False
    effect_authority_proven: bool = False
    semantic_k27_authority_minted: bool = False
    native_private_transformer_kv_accessed: bool = False
    version: str = VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def receipt_digest(self) -> str:
        return _digest(self.to_dict())


def assess_storage_envelope_common_cut_gap(
    *,
    request: OwnerHostC2CanaryRequest,
    probe_receipt: ThinkPadStorageProbeReceipt,
    envelope: SustainedOperatingEnvelope,
) -> StorageEnvelopeCommonCutGapReceipt:
    """Validate both parent artifacts and emit only the missing-common-cut fact."""
    if type(request) is not OwnerHostC2CanaryRequest:
        raise StorageEnvelopeCommonCutGapError("EXACT_C2_REQUEST_TYPE_REQUIRED")
    if type(probe_receipt) is not ThinkPadStorageProbeReceipt:
        raise StorageEnvelopeCommonCutGapError("EXACT_STORAGE_PROBE_RECEIPT_REQUIRED")

    storage_projection = project_bounded_storage_probe_currentness(
        request=request,
        probe_receipt=probe_receipt,
    )
    node = storage_projection["evidence_node"]
    if storage_projection["storage_probe_current_in_generation"] is not True:
        raise StorageEnvelopeCommonCutGapError("STORAGE_NOT_CURRENT_IN_OWNED_GENERATION")
    if node["currentness_domain"] != STORAGE_CURRENTNESS_DOMAIN:
        raise StorageEnvelopeCommonCutGapError("STORAGE_CURRENTNESS_DOMAIN_DRIFT")

    _assert_envelope_ceiling(envelope)
    observed_at = _parse_offset_aware_timestamp(envelope.observed_at_utc)

    # A host snapshot digest names request state.  Neither parent authenticates
    # it as a host/session identity shared by the two observations.
    if not isinstance(request.host_snapshot_digest, str) or len(request.host_snapshot_digest) != 64:
        raise StorageEnvelopeCommonCutGapError("REQUEST_HOST_SNAPSHOT_DIGEST_INVALID")

    return StorageEnvelopeCommonCutGapReceipt(
        request_digest=request.request_digest,
        request_host_snapshot_digest=request.host_snapshot_digest,
        storage_probe_receipt_digest=probe_receipt.receipt_digest,
        storage_probe_evidence_ref=probe_receipt.evidence_ref,
        storage_currentness_domain=node["currentness_domain"],
        storage_current_in_owned_generation=True,
        envelope_observation_digest=envelope.observation_digest,
        envelope_evidence_ref=envelope.evidence_ref,
        envelope_currentness_domain=envelope.currentness_domain,
        envelope_observed_at_utc=observed_at,
        envelope_current_at_observation_time_only=True,
    )
