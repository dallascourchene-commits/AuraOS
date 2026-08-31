"""Router-separated speculative expert prefetch for AWJ032 GLM-5.3.

D0 / HS1 / NONPROMOTING.

This module owns only the missing transfer-planning/accounting membrane between the
native GLM router and PR338's source-bound pager. A predictor may stage expert pages,
but it is never allowed to select the experts that execute. Prediction misses are
recovered by demand-loading the exact native-selected experts.

No model/provider execution, physical-I/O claim, G2 admission, native/private KV
access, semantic K27 authority, Gate-10, merge/deploy/spend or human/public effect
is granted by this module.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping, Protocol, Sequence

from tools.awj032.glm53_packed_expert_pager import canonical_expert_ids

SCHEMA = "AURA-GLM53-ROUTER-SEPARATED-PREFETCH-v1"
PREFETCH_SCHEMA = "AURA-GLM53-PREFETCH-PREDICTION-v1"
NATIVE_ROUTE_SCHEMA = "AURA-GLM53-NATIVE-ROUTE-v1"
IO_SCHEMA = "AURA-GLM53-PREFETCH-PHYSICAL-IO-ATTESTATION-v1"

PR333_HEAD = "815ec64338114d8d3947af6c295b28f8f401287e"
PR338_HEAD = "7f33d2e8f6e53b8862f8ecf0ddc28e0564fb388a"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _canonical_prefetch_expert_ids(expert_ids: Sequence[int], num_experts: int) -> tuple[int, ...]:
    """Canonicalize a speculative transfer set while permitting abstention.

    PR338's ``canonical_expert_ids`` correctly forbids an empty routed-expert
    request. A speculative predictor has a different contract: it may safely
    abstain and let the authoritative native route demand-load every required
    expert. Non-empty predictions retain the exact PR338 range/canonicalization
    rules rather than introducing a second expert-ID policy.
    """
    if not expert_ids:
        return ()
    return canonical_expert_ids(expert_ids, num_experts)


@dataclass(frozen=True)
class PrefetchPrediction:
    schema: str
    predictor_generation: str
    layer_id: str
    binding_digest: str
    predicted_experts: tuple[int, ...]

    def validate(self, *, num_experts: int) -> None:
        if self.schema != PREFETCH_SCHEMA:
            raise ValueError("PREFETCH_SCHEMA_MISMATCH")
        if not self.predictor_generation.strip() or not self.layer_id.strip() or not self.binding_digest.strip():
            raise ValueError("PREFETCH_IDENTITY_FIELDS_REQUIRED")
        expected = _canonical_prefetch_expert_ids(self.predicted_experts, num_experts)
        if expected != self.predicted_experts:
            raise ValueError("PREDICTED_EXPERTS_MUST_BE_CANONICAL")

    @property
    def digest(self) -> str:
        return _sha({"domain": PREFETCH_SCHEMA, "prediction": asdict(self)})


@dataclass(frozen=True)
class NativeRoute:
    schema: str
    router_generation: str
    layer_id: str
    binding_digest: str
    top_k: int
    selected_experts: tuple[int, ...]

    def validate(self, *, num_experts: int) -> None:
        if self.schema != NATIVE_ROUTE_SCHEMA:
            raise ValueError("NATIVE_ROUTE_SCHEMA_MISMATCH")
        if not self.router_generation.strip() or not self.layer_id.strip() or not self.binding_digest.strip():
            raise ValueError("NATIVE_ROUTE_IDENTITY_FIELDS_REQUIRED")
        if isinstance(self.top_k, bool) or not isinstance(self.top_k, int) or self.top_k <= 0:
            raise ValueError("NATIVE_ROUTE_TOP_K_INVALID")
        expected = canonical_expert_ids(self.selected_experts, num_experts)
        if expected != self.selected_experts:
            raise ValueError("NATIVE_SELECTED_EXPERTS_MUST_BE_CANONICAL")
        if len(expected) != self.top_k:
            raise ValueError("NATIVE_ROUTE_TOP_K_MISMATCH")

    @property
    def digest(self) -> str:
        return _sha({"domain": NATIVE_ROUTE_SCHEMA, "route": asdict(self)})


@dataclass(frozen=True)
class PhysicalIOAttestation:
    schema: str
    binding_digest: str
    prediction_digest: str
    native_route_digest: str
    prefetch_experts: tuple[int, ...]
    demand_experts: tuple[int, ...]
    physical_prefetch_bytes: int
    physical_demand_bytes: int
    attestation_id: str

    def validate(self) -> None:
        if self.schema != IO_SCHEMA:
            raise ValueError("PHYSICAL_IO_ATTESTATION_SCHEMA_MISMATCH")
        for value, name in (
            (self.binding_digest, "BINDING_DIGEST"),
            (self.prediction_digest, "PREDICTION_DIGEST"),
            (self.native_route_digest, "NATIVE_ROUTE_DIGEST"),
            (self.attestation_id, "ATTESTATION_ID"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"PHYSICAL_IO_{name}_REQUIRED")
        for value in (self.physical_prefetch_bytes, self.physical_demand_bytes):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError("PHYSICAL_IO_BYTES_MUST_BE_NONNEGATIVE_INTS")


@dataclass(frozen=True)
class PrefetchTrace:
    schema: str
    layer_id: str
    binding_digest: str
    prediction_digest: str
    native_route_digest: str
    predicted_experts: tuple[int, ...]
    native_selected_experts: tuple[int, ...]
    prefetch_hits: tuple[int, ...]
    demand_misses: tuple[int, ...]
    wasted_prefetches: tuple[int, ...]
    executed_experts: tuple[int, ...]
    logical_prefetch_bytes: int
    logical_native_required_bytes: int
    logical_demand_bytes: int
    logical_wasted_prefetch_bytes: int
    prediction_recall_numerator: int
    prediction_recall_denominator: int
    prediction_precision_numerator: int
    prediction_precision_denominator: int
    physical_io_attested: bool
    physical_prefetch_bytes: int | None
    physical_demand_bytes: int | None
    physical_total_bytes: int | None
    io_attestation_id: str | None
    routing_mutated_by_predictor: bool = False
    output_semantics_changed_by_prediction: bool = False
    g2_admitted: bool = False
    execution_authorized: bool = False
    provider_effect_authorized: bool = False
    native_private_transformer_kv_accessed: bool = False
    semantic_k27_authority_minted: bool = False
    gate10_promoted: bool = False
    merge_deploy_spend_public_financial_human_effect: bool = False

    def validate_claim_ceiling(self) -> None:
        if self.schema != SCHEMA:
            raise ValueError("PREFETCH_TRACE_SCHEMA_MISMATCH")
        if self.executed_experts != self.native_selected_experts:
            raise ValueError("EXECUTION_SET_MUST_EQUAL_NATIVE_ROUTE")
        forbidden = (
            self.routing_mutated_by_predictor,
            self.output_semantics_changed_by_prediction,
            self.g2_admitted,
            self.execution_authorized,
            self.provider_effect_authorized,
            self.native_private_transformer_kv_accessed,
            self.semantic_k27_authority_minted,
            self.gate10_promoted,
            self.merge_deploy_spend_public_financial_human_effect,
        )
        if any(v is not False for v in forbidden):
            raise ValueError("PREFETCH_TRACE_CANNOT_WIDEN_AUTHORITY_OR_ROUTING")
        if self.physical_io_attested:
            if None in (self.physical_prefetch_bytes, self.physical_demand_bytes, self.physical_total_bytes, self.io_attestation_id):
                raise ValueError("ATTESTED_PHYSICAL_IO_REQUIRES_COMPLETE_FIELDS")
        else:
            if any(v is not None for v in (self.physical_prefetch_bytes, self.physical_demand_bytes, self.physical_total_bytes, self.io_attestation_id)):
                raise ValueError("UNATTESTED_PHYSICAL_IO_MUST_REMAIN_UNKNOWN")

    @property
    def receipt_digest(self) -> str:
        self.validate_claim_ceiling()
        return _sha({"domain": SCHEMA, "trace": asdict(self)})


class ExpertPageLoader(Protocol):
    def load_selected(self, expert_ids: Sequence[int], *, model_revision: str, index_digest: str) -> Any: ...


def _logical_bytes(experts: Sequence[int], logical_bytes_by_expert: Mapping[int, int]) -> int:
    total = 0
    for expert in experts:
        if expert not in logical_bytes_by_expert:
            raise ValueError(f"LOGICAL_BYTES_MISSING_FOR_EXPERT_{expert}")
        value = logical_bytes_by_expert[expert]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError("LOGICAL_BYTES_PER_EXPERT_MUST_BE_POSITIVE_INT")
        total += value
    return total


def _validate_loaded_pages(
    result: Any,
    *,
    requested_experts: Sequence[int],
    expected_binding_digest: str,
    num_experts: int,
    phase: str,
) -> None:
    """Require the pager result to prove the exact requested source-bound pages."""
    observed_binding = getattr(result, "binding_digest", None)
    if not isinstance(observed_binding, str) or not observed_binding.strip():
        raise ValueError(f"{phase}_PAGER_RESULT_BINDING_REQUIRED")
    if observed_binding != expected_binding_digest:
        raise ValueError(f"{phase}_PAGER_RESULT_BINDING_MISMATCH")

    observed_experts = getattr(result, "expert_ids", None)
    if observed_experts is None:
        raise ValueError(f"{phase}_PAGER_RESULT_EXPERTS_REQUIRED")
    expected_experts = canonical_expert_ids(requested_experts, num_experts)
    try:
        observed_tuple = tuple(observed_experts)
    except TypeError as exc:
        raise ValueError(f"{phase}_PAGER_RESULT_EXPERTS_INVALID") from exc
    if observed_tuple != expected_experts:
        raise ValueError(f"{phase}_PAGER_RESULT_EXPERTS_MISMATCH")


def build_prefetch_trace(
    *,
    prediction: PrefetchPrediction,
    native_route: NativeRoute,
    num_experts: int,
    logical_bytes_by_expert: Mapping[int, int],
    physical_io: PhysicalIOAttestation | None = None,
) -> PrefetchTrace:
    """Join prediction and native route without allowing prediction to affect execution."""
    prediction.validate(num_experts=num_experts)
    native_route.validate(num_experts=num_experts)
    if prediction.layer_id != native_route.layer_id:
        raise ValueError("PREFETCH_NATIVE_LAYER_MISMATCH")
    if prediction.binding_digest != native_route.binding_digest:
        raise ValueError("PREFETCH_NATIVE_SOURCE_BINDING_MISMATCH")

    predicted = set(prediction.predicted_experts)
    native = set(native_route.selected_experts)
    hits = tuple(sorted(predicted & native))
    misses = tuple(sorted(native - predicted))
    wasted = tuple(sorted(predicted - native))

    logical_prefetch = _logical_bytes(prediction.predicted_experts, logical_bytes_by_expert)
    logical_native = _logical_bytes(native_route.selected_experts, logical_bytes_by_expert)
    logical_demand = _logical_bytes(misses, logical_bytes_by_expert) if misses else 0
    logical_waste = _logical_bytes(wasted, logical_bytes_by_expert) if wasted else 0

    physical_attested = physical_io is not None
    p_prefetch = p_demand = p_total = None
    attestation_id = None
    if physical_io is not None:
        physical_io.validate()
        if physical_io.binding_digest != prediction.binding_digest:
            raise ValueError("PHYSICAL_IO_BINDING_MISMATCH")
        if physical_io.prediction_digest != prediction.digest:
            raise ValueError("PHYSICAL_IO_PREDICTION_MISMATCH")
        if physical_io.native_route_digest != native_route.digest:
            raise ValueError("PHYSICAL_IO_ROUTE_MISMATCH")
        if physical_io.prefetch_experts != prediction.predicted_experts:
            raise ValueError("PHYSICAL_IO_PREFETCH_SET_MISMATCH")
        if physical_io.demand_experts != misses:
            raise ValueError("PHYSICAL_IO_DEMAND_SET_MISMATCH")
        p_prefetch = physical_io.physical_prefetch_bytes
        p_demand = physical_io.physical_demand_bytes
        p_total = p_prefetch + p_demand
        attestation_id = physical_io.attestation_id

    trace = PrefetchTrace(
        schema=SCHEMA,
        layer_id=native_route.layer_id,
        binding_digest=native_route.binding_digest,
        prediction_digest=prediction.digest,
        native_route_digest=native_route.digest,
        predicted_experts=prediction.predicted_experts,
        native_selected_experts=native_route.selected_experts,
        prefetch_hits=hits,
        demand_misses=misses,
        wasted_prefetches=wasted,
        executed_experts=native_route.selected_experts,
        logical_prefetch_bytes=logical_prefetch,
        logical_native_required_bytes=logical_native,
        logical_demand_bytes=logical_demand,
        logical_wasted_prefetch_bytes=logical_waste,
        prediction_recall_numerator=len(hits),
        prediction_recall_denominator=len(native_route.selected_experts),
        prediction_precision_numerator=len(hits),
        prediction_precision_denominator=len(prediction.predicted_experts),
        physical_io_attested=physical_attested,
        physical_prefetch_bytes=p_prefetch,
        physical_demand_bytes=p_demand,
        physical_total_bytes=p_total,
        io_attestation_id=attestation_id,
    )
    trace.validate_claim_ceiling()
    return trace


def stage_then_demand_load(
    *,
    pager: ExpertPageLoader,
    prediction: PrefetchPrediction,
    native_route: NativeRoute,
    num_experts: int,
    logical_bytes_by_expert: Mapping[int, int],
    model_revision: str,
    index_digest: str,
) -> PrefetchTrace:
    """Exercise transfer order while preserving native execution semantics."""
    trace = build_prefetch_trace(
        prediction=prediction,
        native_route=native_route,
        num_experts=num_experts,
        logical_bytes_by_expert=logical_bytes_by_expert,
    )
    if prediction.predicted_experts:
        staged = pager.load_selected(
            prediction.predicted_experts,
            model_revision=model_revision,
            index_digest=index_digest,
        )
        _validate_loaded_pages(
            staged,
            requested_experts=prediction.predicted_experts,
            expected_binding_digest=trace.binding_digest,
            num_experts=num_experts,
            phase="PREFETCH",
        )
    if trace.demand_misses:
        demanded = pager.load_selected(
            trace.demand_misses,
            model_revision=model_revision,
            index_digest=index_digest,
        )
        _validate_loaded_pages(
            demanded,
            requested_experts=trace.demand_misses,
            expected_binding_digest=trace.binding_digest,
            num_experts=num_experts,
            phase="DEMAND",
        )
    return trace


LAWS = (
    "PrefetchPrediction!=NativeExecutionRoute",
    "PredictionMiss=>DemandLoadExactNativeExpertsNotRouteMutation",
    "PredictionWasteMayIncreaseIOWithoutChangingExecutedExperts",
    "PredictionAbstention!=RoutingFailure",
    "EmptyTransferPlan!=EmptyExecutionPlan",
    "NoPrefetchPrediction=>DemandLoadExactNativeRoute",
    "PredictorMayAbstainNativeRouterMayNot",
    "Abstention!=PhysicalIOSavingsProof",
    "PagerResultMustBindExactRequestedExpertsAndSource",
    "LogicalPrefetchBytes!=PhysicalNVMeBytesAbsentAttestation",
    "FullShardLoad!=SelectivePrefetch",
    "CoordinateMemory!=TransformerKVCache",
    "K27Coordinate!=RoutingAuthority!=ExecutionAuthority",
)
