"""G2-A: abstention-neutral bridge from lawful G1 prediction abstention to G2 planning.

D0 / HS1 / NONPROMOTING.

Exactly two hosted other-Agent artifacts motivate this relation:
- G2 / PR #722: cost-aware non-executing transfer admission for nonempty predictions.
- G1 abstention / PR #723: an empty speculative prediction is lawful because the
  native router remains authoritative and exact native demand loading still owns
  execution correctness.

G2's W4-derived reuse algebra intentionally requires positive logical bytes. Therefore
an empty prediction must not be coerced through ``required_reuse(0, ...)`` and must not
silently invent ``required_reuse = 0``. The correct typed result is an empty transfer
plan with reuse feasibility NOT_APPLICABLE and all physical/effect claims still false.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping

from tools.awj032 import glm53_prefetch_transfer_admission as g2

SCHEMA = "AURA-GLM53-G2-ABSTENTION-NEUTRAL-ADMISSION-v1"
G2_PARENT_HEAD = "44831fd5454d08a97bd0b172337cf4c48a339dfe"
G2_PARENT_RUN = 33414707814
G2_PARENT_JOB = 99562465599
G1_ABSTENTION_HEAD = "83d47da6f19b42d42d1bbcfd26bce8620d2b42fb"
G1_ABSTENTION_RUN = 33414653661
G1_ABSTENTION_JOB = 99562295582
ABSTENTION_DISPOSITION = "ABSTENTION_EMPTY_TRANSFER_PLAN"
REUSE_NOT_APPLICABLE = "NOT_APPLICABLE_ZERO_LOGICAL_BYTES"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _required(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")
    return value


@dataclass(frozen=True)
class G1AbstentionProjection:
    """Typed projection of the exact PR723 abstention consequence."""

    schema: str
    predictor_generation: str
    layer_id: str
    binding_digest: str
    predicted_experts: tuple[int, ...]
    prediction_abstention_lawful: bool
    native_route_remains_authoritative: bool
    no_prefetch_call_required: bool

    def validate(self) -> None:
        if self.schema != "AURA-GLM53-PREFETCH-PREDICTION-v1":
            raise ValueError("G2A_G1_PREDICTION_SCHEMA_MISMATCH")
        _required(self.predictor_generation, "G2A_PREDICTOR_GENERATION")
        _required(self.layer_id, "G2A_LAYER_ID")
        _required(self.binding_digest, "G2A_BINDING_DIGEST")
        if self.predicted_experts != ():
            raise ValueError("G2A_REQUIRES_EXACT_EMPTY_PREDICTION")
        if self.prediction_abstention_lawful is not True:
            raise ValueError("G2A_ABSTENTION_MUST_BE_LAWFUL")
        if self.native_route_remains_authoritative is not True:
            raise ValueError("G2A_NATIVE_ROUTE_AUTHORITY_MUST_REMAIN")
        if self.no_prefetch_call_required is not True:
            raise ValueError("G2A_EMPTY_PREDICTION_MUST_REQUIRE_NO_PREFETCH_CALL")


@dataclass(frozen=True)
class G2AbstentionNeutralReceipt:
    schema: str
    g2_parent_head: str
    g1_abstention_head: str
    predictor_generation: str
    policy_generation: str
    predictor_calibration_generation: str
    layer_id: str
    binding_digest: str
    predicted_experts: tuple[int, ...]
    admitted_experts: tuple[int, ...]
    candidate_decisions: tuple[Any, ...]
    cold_predicted_logical_bytes: int
    cold_required_reuse_for_window: None
    cold_required_reuse_disposition: str
    admitted_logical_bytes: int
    admitted_logical_transfer_seconds: float
    admitted_expected_latency_margin_seconds: float
    admitted_estimated_energy_joules: None
    disposition: str
    physical_io_attested: bool = False
    physical_prefetch_bytes: None = None
    physical_storage_budget_proven: bool = False
    native_route_mutated: bool = False
    model_output_semantics_changed: bool = False
    transfer_effect_authorized: bool = False
    g2_admitted: bool = False
    native_private_transformer_kv_accessed: bool = False
    semantic_k27_authority_minted: bool = False
    gate10_promoted: bool = False
    merge_deploy_spend_public_financial_human_effect: bool = False

    def validate_claim_ceiling(self) -> None:
        if self.schema != SCHEMA:
            raise ValueError("G2A_SCHEMA_MISMATCH")
        if self.predicted_experts != () or self.admitted_experts != () or self.candidate_decisions != ():
            raise ValueError("G2A_ABSTENTION_MUST_REMAIN_EMPTY")
        if self.cold_predicted_logical_bytes != 0 or self.admitted_logical_bytes != 0:
            raise ValueError("G2A_ABSTENTION_BYTES_MUST_BE_ZERO")
        if self.cold_required_reuse_for_window is not None:
            raise ValueError("G2A_ZERO_BYTE_REUSE_MUST_REMAIN_NOT_APPLICABLE")
        if self.cold_required_reuse_disposition != REUSE_NOT_APPLICABLE:
            raise ValueError("G2A_REUSE_DISPOSITION_MISMATCH")
        if self.admitted_logical_transfer_seconds != 0.0 or self.admitted_expected_latency_margin_seconds != 0.0:
            raise ValueError("G2A_ABSTENTION_LATENCY_PLAN_MUST_BE_ZERO")
        if self.admitted_estimated_energy_joules is not None:
            raise ValueError("G2A_ABSTENTION_ENERGY_MUST_REMAIN_UNKNOWN_NOT_ZERO")
        if self.disposition != ABSTENTION_DISPOSITION:
            raise ValueError("G2A_ABSTENTION_DISPOSITION_MISMATCH")
        if self.physical_io_attested is not False or self.physical_prefetch_bytes is not None:
            raise ValueError("G2A_ABSTENTION_CANNOT_SELF_ATTEST_PHYSICAL_SAVINGS")
        forbidden = (
            self.physical_storage_budget_proven,
            self.native_route_mutated,
            self.model_output_semantics_changed,
            self.transfer_effect_authorized,
            self.g2_admitted,
            self.native_private_transformer_kv_accessed,
            self.semantic_k27_authority_minted,
            self.gate10_promoted,
            self.merge_deploy_spend_public_financial_human_effect,
        )
        if any(value is not False for value in forbidden):
            raise ValueError("G2A_ABSTENTION_CANNOT_WIDEN_AUTHORITY")

    @property
    def receipt_digest(self) -> str:
        self.validate_claim_ceiling()
        return _sha({"domain": SCHEMA, "receipt": asdict(self)})


def admit_abstention_neutral(
    *,
    abstention: G1AbstentionProjection,
    forecasts: tuple[g2.CalibratedExpertForecast, ...],
    policy: g2.PrefetchTransferPolicy,
) -> G2AbstentionNeutralReceipt:
    """Return the unique lawful G2 plan for an exact empty speculative prediction."""
    abstention.validate()
    policy.validate()
    if forecasts != ():
        raise ValueError("G2A_EMPTY_PREDICTION_REQUIRES_EMPTY_FORECAST_SET")
    if abstention.layer_id != policy.layer_id:
        raise ValueError("G2A_PREDICTION_POLICY_LAYER_MISMATCH")
    if abstention.binding_digest != policy.binding_digest:
        raise ValueError("G2A_PREDICTION_POLICY_BINDING_MISMATCH")

    receipt = G2AbstentionNeutralReceipt(
        schema=SCHEMA,
        g2_parent_head=G2_PARENT_HEAD,
        g1_abstention_head=G1_ABSTENTION_HEAD,
        predictor_generation=abstention.predictor_generation,
        policy_generation=policy.policy_generation,
        predictor_calibration_generation=policy.predictor_calibration_generation,
        layer_id=abstention.layer_id,
        binding_digest=abstention.binding_digest,
        predicted_experts=(),
        admitted_experts=(),
        candidate_decisions=(),
        cold_predicted_logical_bytes=0,
        cold_required_reuse_for_window=None,
        cold_required_reuse_disposition=REUSE_NOT_APPLICABLE,
        admitted_logical_bytes=0,
        admitted_logical_transfer_seconds=0.0,
        admitted_expected_latency_margin_seconds=0.0,
        admitted_estimated_energy_joules=None,
        disposition=ABSTENTION_DISPOSITION,
    )
    receipt.validate_claim_ceiling()
    return receipt


def example_abstention() -> G1AbstentionProjection:
    return G1AbstentionProjection(
        schema="AURA-GLM53-PREFETCH-PREDICTION-v1",
        predictor_generation="predictor:g2a:v1",
        layer_id="layer:07",
        binding_digest="binding:g2:source",
        predicted_experts=(),
        prediction_abstention_lawful=True,
        native_route_remains_authoritative=True,
        no_prefetch_call_required=True,
    )


def example_policy() -> g2.PrefetchTransferPolicy:
    return g2.PrefetchTransferPolicy(
        policy_generation="policy:g2:v1",
        predictor_calibration_generation="calibration:g2:v1",
        layer_id="layer:07",
        binding_digest="binding:g2:source",
        effective_storage_bandwidth_bytes_per_second=1_000_000_000.0,
        prefetch_window_seconds=0.010,
        minimum_hit_probability_numerator=1,
        minimum_hit_probability_denominator=2,
    )


def main() -> None:
    receipt = admit_abstention_neutral(
        abstention=example_abstention(), forecasts=(), policy=example_policy()
    )
    print(json.dumps({**asdict(receipt), "receipt_digest": receipt.receipt_digest}, sort_keys=True, separators=(",", ":")))


LAWS = (
    "PredictionAbstention!=RoutingFailure",
    "EmptyTransferPlan!=EmptyExecutionPlan",
    "ZeroPredictedBytes=>RequiredReuseNotApplicable",
    "RequiredReuseNotApplicable!=ZeroReuseRequirement",
    "NoTransferPlan!=PhysicalIOSavingsProof",
    "AbstentionNeutrality!=G2Admission!=TransferAuthority",
    "K27Coordinate!=AbstentionTruth!=ExecutionAuthority",
)


if __name__ == "__main__":
    main()
