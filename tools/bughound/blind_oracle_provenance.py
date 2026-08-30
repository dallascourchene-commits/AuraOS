"""Producer-bound evaluator resolutions for BugHound blind discovery.

D0 / local benchmark only. This module strengthens the lower-plane
EvaluatorFindingResolutionV1 contract by requiring an evaluator-held secret to
bind the exact resolution, producer identity, and generation before seeded true
positive credit can be consumed.

The HMAC is a benchmark-local producer-authenticity membrane, not general
cryptographic authority. The evaluator secret must remain outside candidate
packets. No network, provider, external target, repair, merge, promotion, or
runtime authority is granted here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import hmac
import json
from typing import Any

from tools.bughound.blind_discovery import (
    BlindAdjudicationV1,
    BlindDiscoveryError,
    BlindDiscoveryPacketV1,
    BlindFindingV1,
    EvaluatorFindingResolutionV1,
    HiddenCaseBindingV1,
    adjudicate_blind_finding,
)
from tools.bughound.seedlab_benchmark import SeedBugCaseV1

SCHEMA = "EvaluatorResolutionEnvelopeV1"
ADJUDICATION_SCHEMA = "ProducerBoundBlindAdjudicationV1"
DEFAULT_PRODUCER_REF = "AURA_BUGHOUND_HIDDEN_EVALUATOR_V1"


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise BlindDiscoveryError("NONCANONICAL_STATE") from exc


def _digest(domain: str, value: object) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical(value)).hexdigest()


def _secret_bytes(value: str | bytes) -> bytes:
    if isinstance(value, str):
        value = value.encode("utf-8")
    if not isinstance(value, bytes) or len(value) < 16:
        raise BlindDiscoveryError("EVALUATOR_PRODUCER_SECRET_INVALID")
    return value


def _text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BlindDiscoveryError(code)
    return value.strip()


def _resolution_payload(
    resolution: EvaluatorFindingResolutionV1,
    *,
    producer_ref: str,
    producer_generation: str,
) -> dict[str, Any]:
    if not isinstance(resolution, EvaluatorFindingResolutionV1):
        raise BlindDiscoveryError("EVALUATOR_RESOLUTION_REQUIRED")
    if not resolution.independent_oracle:
        raise BlindDiscoveryError("INDEPENDENT_ORACLE_REQUIRED")
    if resolution.authority or resolution.external_effect:
        raise BlindDiscoveryError("EFFECT_OR_AUTHORITY_WIDENING_FORBIDDEN")
    producer_ref = _text(producer_ref, "EVALUATOR_PRODUCER_REF_REQUIRED")
    producer_generation = _text(
        producer_generation, "EVALUATOR_PRODUCER_GENERATION_REQUIRED"
    )
    return {
        "resolution_digest": resolution.resolution_digest,
        "target_id": resolution.target_id,
        "finding_id": resolution.finding_id,
        "hidden_case_digest": resolution.hidden_case_digest,
        "oracle_id": resolution.oracle_id,
        "evaluator_generation": resolution.evaluator_generation,
        "producer_ref": producer_ref,
        "producer_generation": producer_generation,
        "authority": False,
        "external_effect": False,
        "schema": SCHEMA,
    }


@dataclass(frozen=True)
class EvaluatorResolutionEnvelopeV1:
    resolution_digest: str
    target_id: str
    finding_id: str
    hidden_case_digest: str
    oracle_id: str
    evaluator_generation: str
    producer_ref: str
    producer_generation: str
    producer_mac: str
    independent_oracle_producer_bound: bool = True
    authority: bool = False
    external_effect: bool = False
    schema: str = SCHEMA

    @property
    def envelope_digest(self) -> str:
        return _digest("AURA_BUGHOUND_EVALUATOR_ENVELOPE_V1", asdict(self))


def issue_evaluator_resolution_envelope(
    resolution: EvaluatorFindingResolutionV1,
    *,
    evaluator_secret: str | bytes,
    producer_ref: str = DEFAULT_PRODUCER_REF,
    producer_generation: str,
) -> EvaluatorResolutionEnvelopeV1:
    """Issue an evaluator-only producer binding for one exact resolution."""
    payload = _resolution_payload(
        resolution,
        producer_ref=producer_ref,
        producer_generation=producer_generation,
    )
    key = _secret_bytes(evaluator_secret)
    mac = hmac.new(
        key,
        b"AURA_BUGHOUND_EVALUATOR_PRODUCER_V1\0" + _canonical(payload),
        hashlib.sha256,
    ).hexdigest()
    return EvaluatorResolutionEnvelopeV1(
        resolution_digest=payload["resolution_digest"],
        target_id=payload["target_id"],
        finding_id=payload["finding_id"],
        hidden_case_digest=payload["hidden_case_digest"],
        oracle_id=payload["oracle_id"],
        evaluator_generation=payload["evaluator_generation"],
        producer_ref=payload["producer_ref"],
        producer_generation=payload["producer_generation"],
        producer_mac=mac,
    )


def verify_evaluator_resolution_envelope(
    envelope: EvaluatorResolutionEnvelopeV1,
    resolution: EvaluatorFindingResolutionV1,
    *,
    evaluator_secret: str | bytes,
    expected_producer_ref: str = DEFAULT_PRODUCER_REF,
    expected_producer_generation: str,
) -> None:
    """Fail closed unless the envelope authenticates this exact resolution."""
    if not isinstance(envelope, EvaluatorResolutionEnvelopeV1):
        raise BlindDiscoveryError("EVALUATOR_PRODUCER_ENVELOPE_REQUIRED")
    if envelope.independent_oracle_producer_bound is not True:
        raise BlindDiscoveryError("EVALUATOR_PRODUCER_BINDING_REQUIRED")
    if envelope.authority or envelope.external_effect:
        raise BlindDiscoveryError("EFFECT_OR_AUTHORITY_WIDENING_FORBIDDEN")
    payload = _resolution_payload(
        resolution,
        producer_ref=expected_producer_ref,
        producer_generation=expected_producer_generation,
    )
    for field in (
        "resolution_digest",
        "target_id",
        "finding_id",
        "hidden_case_digest",
        "oracle_id",
        "evaluator_generation",
        "producer_ref",
        "producer_generation",
    ):
        if getattr(envelope, field) != payload[field]:
            raise BlindDiscoveryError("EVALUATOR_PRODUCER_BINDING_MISMATCH", field)
    key = _secret_bytes(evaluator_secret)
    expected_mac = hmac.new(
        key,
        b"AURA_BUGHOUND_EVALUATOR_PRODUCER_V1\0" + _canonical(payload),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(envelope.producer_mac, expected_mac):
        raise BlindDiscoveryError("EVALUATOR_PRODUCER_MAC_MISMATCH")


@dataclass(frozen=True)
class ProducerBoundBlindAdjudicationV1:
    inner_adjudication: BlindAdjudicationV1
    evaluator_envelope_digest: str | None
    independent_oracle_producer_proven: bool
    authority: bool = False
    external_effect: bool = False
    schema: str = ADJUDICATION_SCHEMA

    @property
    def adjudication_digest(self) -> str:
        return _digest(
            "AURA_BUGHOUND_PRODUCER_BOUND_ADJUDICATION_V1",
            {
                "schema": self.schema,
                "inner_adjudication_digest": self.inner_adjudication.adjudication_digest,
                "evaluator_envelope_digest": self.evaluator_envelope_digest,
                "independent_oracle_producer_proven": self.independent_oracle_producer_proven,
                "authority": False,
                "external_effect": False,
            },
        )


def adjudicate_producer_bound_blind_finding(
    *,
    packet: BlindDiscoveryPacketV1,
    binding: HiddenCaseBindingV1,
    case: SeedBugCaseV1,
    finding: BlindFindingV1 | None,
    resolution: EvaluatorFindingResolutionV1 | None = None,
    resolution_envelope: EvaluatorResolutionEnvelopeV1 | None = None,
    evaluator_secret: str | bytes,
    expected_producer_ref: str = DEFAULT_PRODUCER_REF,
    expected_producer_generation: str,
) -> ProducerBoundBlindAdjudicationV1:
    """Canonical scored path requiring producer proof whenever resolution is used."""
    envelope_digest: str | None = None
    producer_proven = False
    if resolution is None:
        if resolution_envelope is not None:
            raise BlindDiscoveryError("EVALUATOR_RESOLUTION_REQUIRED")
    else:
        if resolution_envelope is None:
            raise BlindDiscoveryError("EVALUATOR_PRODUCER_ENVELOPE_REQUIRED")
        verify_evaluator_resolution_envelope(
            resolution_envelope,
            resolution,
            evaluator_secret=evaluator_secret,
            expected_producer_ref=expected_producer_ref,
            expected_producer_generation=expected_producer_generation,
        )
        envelope_digest = resolution_envelope.envelope_digest
        producer_proven = True

    inner = adjudicate_blind_finding(
        packet=packet,
        binding=binding,
        case=case,
        finding=finding,
        resolution=resolution,
    )
    if inner.seeded_true_positive and not producer_proven:
        raise BlindDiscoveryError("SEEDED_TP_WITHOUT_EVALUATOR_PRODUCER_PROOF")
    return ProducerBoundBlindAdjudicationV1(
        inner_adjudication=inner,
        evaluator_envelope_digest=envelope_digest,
        independent_oracle_producer_proven=producer_proven,
    )
