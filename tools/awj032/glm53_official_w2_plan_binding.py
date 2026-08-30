"""Independent official-W2 producer binding for PR350 pager plans.

This additive proof-plane wrapper consumes an already validated PagerSourcePlan and
compares its exact source/coordinate/receipt identity to the immutable PR398 W2
producer observation. Generic/synthetic plans remain valid lower-plane artifacts
but cannot set `official_w2_producer_observation_proven` through caller-provided
expected values. No tensor payload, runtime, G2, or authority is admitted.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping

from tools.awj032.glm53_official_w2_observation import (
    OFFICIAL_W2_OBSERVATION,
    OfficialW2ObservationError,
    bind_official_w2_observation,
)

SCHEMA = "OfficialW2BoundPagerPlanV1"


class OfficialW2PlanBindingError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _plan_dict(plan: Any) -> Mapping[str, Any]:
    if hasattr(plan, "to_dict") and callable(plan.to_dict):
        value = plan.to_dict()
    elif isinstance(plan, Mapping):
        value = plan
    else:
        raise OfficialW2PlanBindingError("PAGER_PLAN_REQUIRED")
    if not isinstance(value, Mapping):
        raise OfficialW2PlanBindingError("PAGER_PLAN_INVALID")
    return value


def _binding(plan: Any) -> Any:
    value = getattr(plan, "binding", None)
    if value is None and hasattr(plan, "inner_plan"):
        value = getattr(plan.inner_plan, "binding", None)
    if value is None:
        raise OfficialW2PlanBindingError("PAGER_BINDING_OBJECT_REQUIRED")
    return value


def _text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OfficialW2PlanBindingError(code)
    return value.strip()


def _exact_false(value: Any, code: str) -> None:
    if value is not False:
        raise OfficialW2PlanBindingError(code)


@dataclass(frozen=True)
class OfficialW2BoundPagerPlan:
    inner_source_plan_digest: str
    official_w2_observation_digest: str
    official_w2_producer_semantic_head: str
    official_w2_producer_run_ref: str
    official_w2_drive_observation_ref: str
    representative_layer: int
    representative_expert: int
    official_w2_producer_observation_proven: bool = True
    all_experts_header_uniformity_proven: bool = False
    g2_admitted: bool = False
    runtime_execution_proven: bool = False
    large_checkpoint_admitted: bool = False
    authority: bool = False
    schema: str = SCHEMA

    @property
    def source_plan_digest(self) -> str:
        return _digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "inner_source_plan_digest": self.inner_source_plan_digest,
            "official_w2_observation_digest": self.official_w2_observation_digest,
            "official_w2_producer_semantic_head": self.official_w2_producer_semantic_head,
            "official_w2_producer_run_ref": self.official_w2_producer_run_ref,
            "official_w2_drive_observation_ref": self.official_w2_drive_observation_ref,
            "representative_layer": self.representative_layer,
            "representative_expert": self.representative_expert,
            "official_w2_producer_observation_proven": True,
            "all_experts_header_uniformity_proven": False,
            "g2_admitted": False,
            "runtime_execution_proven": False,
            "large_checkpoint_admitted": False,
            "authority": False,
        }


def bind_official_w2_pager_plan(plan: Any) -> OfficialW2BoundPagerPlan:
    p = _plan_dict(plan)
    b = _binding(plan)
    inner_digest = _text(p.get("source_plan_digest"), "PAGER_SOURCE_PLAN_DIGEST_REQUIRED")
    receipt = _text(p.get("header_receipt_digest"), "PAGER_HEADER_RECEIPT_REQUIRED").lower()
    repo_id = _text(p.get("header_observation_repo_id"), "PAGER_HEADER_REPO_REQUIRED")
    if p.get("representative_header_bound") is not True:
        raise OfficialW2PlanBindingError("REPRESENTATIVE_HEADER_BINDING_REQUIRED")
    if p.get("all_experts_header_uniformity_proven") is not False:
        raise OfficialW2PlanBindingError("REPRESENTATIVE_TO_UNIVERSAL_CAST_FORBIDDEN")
    _exact_false(p.get("g2_admitted"), "PAGER_G2_WIDENING_FORBIDDEN")
    _exact_false(p.get("runtime_execution_proven"), "PAGER_RUNTIME_WIDENING_FORBIDDEN")
    _exact_false(p.get("large_checkpoint_admitted"), "PAGER_CHECKPOINT_WIDENING_FORBIDDEN")
    layer = p.get("representative_layer")
    expert = p.get("representative_expert")
    if isinstance(layer, bool) or not isinstance(layer, int):
        raise OfficialW2PlanBindingError("REPRESENTATIVE_LAYER_REQUIRED")
    if isinstance(expert, bool) or not isinstance(expert, int):
        raise OfficialW2PlanBindingError("REPRESENTATIVE_EXPERT_REQUIRED")
    model_revision = _text(getattr(b, "model_revision", None), "PAGER_MODEL_REVISION_REQUIRED")
    index_digest = _text(getattr(b, "index_digest", None), "PAGER_INDEX_DIGEST_REQUIRED")
    try:
        observed = bind_official_w2_observation(
            repo_id=repo_id,
            model_revision=model_revision,
            index_sha256=index_digest,
            layer=layer,
            expert=expert,
            observed_receipt_digest=receipt,
        )
    except OfficialW2ObservationError as exc:
        raise OfficialW2PlanBindingError(exc.code, exc.detail) from exc
    if observed is None:
        raise OfficialW2PlanBindingError("OFFICIAL_W2_SOURCE_COORDINATE_MISMATCH")
    o = OFFICIAL_W2_OBSERVATION
    return OfficialW2BoundPagerPlan(
        inner_source_plan_digest=inner_digest,
        official_w2_observation_digest=o.observation_digest,
        official_w2_producer_semantic_head=o.producer_semantic_head,
        official_w2_producer_run_ref=o.producer_run_ref,
        official_w2_drive_observation_ref=o.drive_observation_ref,
        representative_layer=layer,
        representative_expert=expert,
    )
