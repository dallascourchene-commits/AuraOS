"""Canonical score-admission membrane for BugHound blind discovery.

D0 / local benchmark only. A shape-valid BlindAdjudicationV1 is diagnostic
evidence, not a score-admission object. This module does not accept a precomputed
adjudication. It re-runs the producer-bound evaluator path from source inputs so
seeded true-positive credit cannot be laundered through the legacy shape-only
adjudicator.

No network, provider, external target, public submission, repair, merge,
promotion, deployment, spend, or authority effect is performed here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

from tools.bughound.blind_discovery import (
    BlindDiscoveryPacketV1,
    BlindFindingV1,
    EvaluatorFindingResolutionV1,
    HiddenCaseBindingV1,
)
from tools.bughound.blind_oracle_provenance import (
    DEFAULT_PRODUCER_REF,
    EvaluatorResolutionEnvelopeV1,
    adjudicate_producer_bound_blind_finding,
)
from tools.bughound.seedlab_benchmark import SeedBugCaseV1

SCHEMA = "ProducerBoundBlindScoreReceiptV1"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _digest(domain: str, value: object) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical(value)).hexdigest()


@dataclass(frozen=True)
class ProducerBoundBlindScoreReceiptV1:
    target_id: str
    outcome: str
    seeded_true_positive: bool
    clean_control_correct: bool
    novelty_verification_required: bool
    producer_bound_adjudication_digest: str
    evaluator_envelope_digest: str | None
    independent_oracle_producer_proven: bool
    authority: bool = False
    external_effect: bool = False
    schema: str = SCHEMA

    @property
    def score_receipt_digest(self) -> str:
        return _digest("AURA_BUGHOUND_PRODUCER_BOUND_SCORE_V1", asdict(self))


def score_producer_bound_blind_finding(
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
) -> ProducerBoundBlindScoreReceiptV1:
    """Canonical blind score path; producer proof is verified during scoring.

    Deliberately no `adjudication` argument exists. Callers cannot submit a
    legacy/precomputed BlindAdjudicationV1 as score evidence. The score boundary
    reconstructs the producer-bound adjudication from its exact source inputs.
    """
    adjudicated = adjudicate_producer_bound_blind_finding(
        packet=packet,
        binding=binding,
        case=case,
        finding=finding,
        resolution=resolution,
        resolution_envelope=resolution_envelope,
        evaluator_secret=evaluator_secret,
        expected_producer_ref=expected_producer_ref,
        expected_producer_generation=expected_producer_generation,
    )
    inner = adjudicated.inner_adjudication
    if inner.seeded_true_positive and not adjudicated.independent_oracle_producer_proven:
        # Defense in depth. The producer-bound adjudicator already enforces this.
        raise ValueError("SEEDED_TP_WITHOUT_EVALUATOR_PRODUCER_PROOF")
    if inner.seeded_true_positive and not adjudicated.evaluator_envelope_digest:
        raise ValueError("SEEDED_TP_WITHOUT_EVALUATOR_ENVELOPE_DIGEST")
    return ProducerBoundBlindScoreReceiptV1(
        target_id=inner.target_id,
        outcome=inner.outcome,
        seeded_true_positive=inner.seeded_true_positive,
        clean_control_correct=inner.clean_control_correct,
        novelty_verification_required=inner.novelty_verification_required,
        producer_bound_adjudication_digest=adjudicated.adjudication_digest,
        evaluator_envelope_digest=adjudicated.evaluator_envelope_digest,
        independent_oracle_producer_proven=adjudicated.independent_oracle_producer_proven,
    )
