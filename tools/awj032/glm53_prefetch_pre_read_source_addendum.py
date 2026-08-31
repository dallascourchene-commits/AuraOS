"""Collision-rebased pre-read source addendum for GLM53 G1.

D0 / HS1 / NONPROMOTING.

PR720 owns the canonical post-read pager-result validation. This addendum preserves
only the consequence-distinct residue discovered independently in PR719: before any
speculative or demand transfer occurs, the concrete PR338-style pager's immutable
binding must already commute with the G1 prediction/native-route source identity and
with the call's model revision/index digest.

A mismatch fails before ``load_selected`` can be called. After this pre-read gate,
canonical G1/PR720 owns transfer ordering and returned-page validation.
"""
from __future__ import annotations

from typing import Any, Mapping

from tools.awj032 import glm53_router_separated_prefetch as g1

SCHEMA = "AURA-GLM53-PREFETCH-PRE-READ-SOURCE-ADDENDUM-v1"


def _require(obj: Any, name: str) -> Any:
    if not hasattr(obj, name):
        raise ValueError(f"PREFETCH_PAGER_{name.upper()}_REQUIRED")
    return getattr(obj, name)


def validate_concrete_pager_source_before_read(
    *,
    pager: Any,
    prediction: g1.PrefetchPrediction,
    native_route: g1.NativeRoute,
    num_experts: int,
    model_revision: str,
    index_digest: str,
) -> None:
    """Fail closed before transfer when concrete pager source does not commute."""
    prediction.validate(num_experts=num_experts)
    native_route.validate(num_experts=num_experts)
    if prediction.layer_id != native_route.layer_id:
        raise ValueError("PREFETCH_NATIVE_LAYER_MISMATCH")
    if prediction.binding_digest != native_route.binding_digest:
        raise ValueError("PREFETCH_NATIVE_SOURCE_BINDING_MISMATCH")

    binding = _require(pager, "binding")
    digest = _require(binding, "digest")
    layer_id = _require(binding, "layer_id")
    pager_num_experts = _require(binding, "num_experts")
    pager_revision = _require(binding, "model_revision")
    pager_index = _require(binding, "index_digest")

    if digest != prediction.binding_digest:
        raise ValueError("PREFETCH_CONCRETE_PAGER_BINDING_MISMATCH")
    if layer_id != prediction.layer_id:
        raise ValueError("PREFETCH_CONCRETE_PAGER_LAYER_MISMATCH")
    if pager_num_experts != num_experts:
        raise ValueError("PREFETCH_CONCRETE_PAGER_NUM_EXPERTS_MISMATCH")
    if pager_revision != model_revision:
        raise ValueError("PREFETCH_CALL_REVISION_NOT_PAGER_REVISION")
    if pager_index != index_digest:
        raise ValueError("PREFETCH_CALL_INDEX_NOT_PAGER_INDEX")


def stage_then_demand_load_prebound(
    *,
    pager: Any,
    prediction: g1.PrefetchPrediction,
    native_route: g1.NativeRoute,
    num_experts: int,
    logical_bytes_by_expert: Mapping[int, int],
    model_revision: str,
    index_digest: str,
) -> g1.PrefetchTrace:
    """Run canonical G1 only after the concrete pager source passes pre-read proof."""
    validate_concrete_pager_source_before_read(
        pager=pager,
        prediction=prediction,
        native_route=native_route,
        num_experts=num_experts,
        model_revision=model_revision,
        index_digest=index_digest,
    )
    trace = g1.stage_then_demand_load(
        pager=pager,
        prediction=prediction,
        native_route=native_route,
        num_experts=num_experts,
        logical_bytes_by_expert=logical_bytes_by_expert,
        model_revision=model_revision,
        index_digest=index_digest,
    )
    trace.validate_claim_ceiling()
    return trace


LAWS = (
    "CollisionOverlapPostRead=>PR720CanonicalOwner",
    "PR719UniqueResidual=>ConcretePagerIdentityBeforeRead",
    "PredictionBinding==NativeRouteBinding==ConcretePagerBindingBeforeRead",
    "WrongPagerSource=>ZeroTransferCalls",
    "PreReadSourceProof+PostReadResultProof!=ExecutionAuthorization",
    "K27Coordinate!=PagerSource!=RoutingAuthority!=ExecutionAuthority",
)
