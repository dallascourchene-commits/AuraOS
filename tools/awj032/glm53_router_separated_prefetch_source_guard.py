"""W3 guard for G1 router-separated expert prefetch.

D0 / HS1 / NONPROMOTING.

G1 correctly separates speculative transfer prediction from native execution routing,
but its first generation allowed ``stage_then_demand_load`` to pass independent
``model_revision`` / ``index_digest`` values to an arbitrary pager without proving
that the concrete pager itself was bound to the same source named by the prediction
and native route. A trace could therefore describe source A while page reads targeted
source B.

This module closes only that transfer-provenance seam. It composes G1 unchanged with
PR338's immutable pager-binding surface, checks the concrete binding *before* any read,
and checks every returned page *after* each read. It never calls model forward and
cannot grant execution, effect, G2, K27, KV, deployment, or benchmark authority.
"""
from __future__ import annotations

from typing import Any, Mapping

from tools.awj032 import glm53_router_separated_prefetch as g1

SCHEMA = "AURA-GLM53-SOURCE-BOUND-PREFETCH-GUARD-v1"


def _required_attr(obj: Any, name: str) -> Any:
    if not hasattr(obj, name):
        raise ValueError(f"PAGER_{name.upper()}_REQUIRED")
    return getattr(obj, name)


def _validate_pager_binding_before_read(
    *,
    pager: Any,
    prediction: g1.PrefetchPrediction,
    native_route: g1.NativeRoute,
    num_experts: int,
    model_revision: str,
    index_digest: str,
) -> None:
    """Require the concrete pager binding to commute with the G1 source identity."""
    binding = _required_attr(pager, "binding")
    binding_digest = _required_attr(binding, "digest")
    binding_layer = _required_attr(binding, "layer_id")
    binding_num_experts = _required_attr(binding, "num_experts")
    binding_revision = _required_attr(binding, "model_revision")
    binding_index = _required_attr(binding, "index_digest")

    if binding_digest != prediction.binding_digest or binding_digest != native_route.binding_digest:
        raise ValueError("PAGER_BINDING_DIGEST_MISMATCH")
    if binding_layer != prediction.layer_id or binding_layer != native_route.layer_id:
        raise ValueError("PAGER_LAYER_ID_MISMATCH")
    if binding_num_experts != num_experts:
        raise ValueError("PAGER_NUM_EXPERTS_MISMATCH")
    if binding_revision != model_revision:
        raise ValueError("PAGER_MODEL_REVISION_ARGUMENT_MISMATCH")
    if binding_index != index_digest:
        raise ValueError("PAGER_INDEX_DIGEST_ARGUMENT_MISMATCH")


def _load_and_verify_page(
    *,
    pager: Any,
    expert_ids: tuple[int, ...],
    binding_digest: str,
    model_revision: str,
    index_digest: str,
) -> None:
    page = pager.load_selected(
        expert_ids,
        model_revision=model_revision,
        index_digest=index_digest,
    )
    page_binding = _required_attr(page, "binding_digest")
    page_experts = tuple(_required_attr(page, "expert_ids"))
    if page_binding != binding_digest:
        raise ValueError("RETURNED_PAGE_BINDING_DIGEST_MISMATCH")
    if page_experts != expert_ids:
        raise ValueError("RETURNED_PAGE_EXPERT_SET_MISMATCH")


def stage_then_demand_load_source_bound(
    *,
    pager: Any,
    prediction: g1.PrefetchPrediction,
    native_route: g1.NativeRoute,
    num_experts: int,
    logical_bytes_by_expert: Mapping[int, int],
    model_revision: str,
    index_digest: str,
) -> g1.PrefetchTrace:
    """Stage speculative pages only under the exact PR338 pager source binding.

    The native route still owns the execution set. Prediction misses demand-load the
    exact native-selected experts. The guard proves only transfer/source conformance;
    it does not prove physical I/O behavior or model execution.
    """
    trace = g1.build_prefetch_trace(
        prediction=prediction,
        native_route=native_route,
        num_experts=num_experts,
        logical_bytes_by_expert=logical_bytes_by_expert,
    )
    _validate_pager_binding_before_read(
        pager=pager,
        prediction=prediction,
        native_route=native_route,
        num_experts=num_experts,
        model_revision=model_revision,
        index_digest=index_digest,
    )

    if prediction.predicted_experts:
        _load_and_verify_page(
            pager=pager,
            expert_ids=prediction.predicted_experts,
            binding_digest=trace.binding_digest,
            model_revision=model_revision,
            index_digest=index_digest,
        )
    if trace.demand_misses:
        _load_and_verify_page(
            pager=pager,
            expert_ids=trace.demand_misses,
            binding_digest=trace.binding_digest,
            model_revision=model_revision,
            index_digest=index_digest,
        )

    trace.validate_claim_ceiling()
    return trace


LAWS = (
    "PredictionBinding==NativeRouteBinding==ConcretePagerBindingBeforeRead",
    "PagerCallArgumentsMustEqualImmutablePagerSourceIdentity",
    "ReturnedPageBindingMustEqualTraceBinding",
    "ReturnedPageExpertSetMustEqualExactRequestedSet",
    "SourceBoundTransfer!=ExecutionAuthorization",
    "PredictionMiss=>DemandLoadExactNativeExpertsNotRouteMutation",
    "K27Coordinate!=PagerBinding!=RoutingAuthority!=ExecutionAuthority",
)
