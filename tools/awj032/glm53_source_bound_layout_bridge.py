"""Source-integrity envelope for the GLM53 physical-layout -> pager bridge.

This D0 wrapper makes the #340 raw-source binding continuous through #350. It
requires a source-bound probe report, proves that the weight_map passed to the
bridge is exactly the map whose digest the report carries, then binds the raw
source bundle identity into the final pager-plan identity. For per-expert plans,
the representative W2 header evidence and independently supplied official W2
observation identity are forwarded into the inner bridge and are therefore
covered by the inner source-plan digest. No weights or G2.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Callable, Mapping

SCHEMA = "GLM53SourceBoundPagerSourcePlanV1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class SourceBoundLayoutError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha_field(value: Any, code: str) -> str:
    if not isinstance(value, str):
        raise SourceBoundLayoutError(code)
    value = value.strip().lower()
    if not _SHA256_RE.fullmatch(value):
        raise SourceBoundLayoutError(code)
    return value


def weight_map_digest(weight_map: Mapping[str, str]) -> str:
    if not isinstance(weight_map, Mapping) or not weight_map:
        raise SourceBoundLayoutError("WEIGHT_MAP_REQUIRED")
    normalized: dict[str, str] = {}
    for key, shard in weight_map.items():
        if not isinstance(key, str) or not key or not isinstance(shard, str) or not shard:
            raise SourceBoundLayoutError("WEIGHT_MAP_ENTRY_INVALID")
        normalized[key] = shard
    return _sha(dict(sorted(normalized.items())))


@dataclass(frozen=True)
class SourceBoundPagerSourcePlan:
    inner_plan: Any
    source_bundle_id: str
    weight_map_digest: str
    source_bound_plan_digest: str
    schema: str = SCHEMA
    g2_admitted: bool = False
    large_checkpoint_admitted: bool = False
    runtime_execution_proven: bool = False

    @property
    def binding(self) -> Any:
        return self.inner_plan.binding

    def to_dict(self) -> dict[str, Any]:
        inner = self.inner_plan.to_dict() if hasattr(self.inner_plan, "to_dict") else {
            "source_plan_digest": getattr(self.inner_plan, "source_plan_digest", None),
            "weight_map_digest": getattr(self.inner_plan, "weight_map_digest", None),
        }
        return {
            "schema": self.schema,
            "source_bundle_id": self.source_bundle_id,
            "weight_map_digest": self.weight_map_digest,
            "inner_plan": inner,
            "source_bound_plan_digest": self.source_bound_plan_digest,
            "g2_admitted": False,
            "large_checkpoint_admitted": False,
            "runtime_execution_proven": False,
        }


def compile_source_bound_pager_source_plan(
    report: Mapping[str, Any],
    *,
    weight_map: Mapping[str, str],
    headers: Mapping[str, Mapping[str, Any]] | None,
    expected_model_revision: str,
    expected_index_digest: str,
    per_expert_header_evidence: Mapping[str, Any] | None = None,
    expected_per_expert_header_repo_id: str | None = None,
    expected_per_expert_header_receipt_digest: str | None = None,
    compile_fn: Callable[..., Any] | None = None,
) -> SourceBoundPagerSourcePlan:
    if report.get("source_binding_proven") is not True:
        raise SourceBoundLayoutError("SOURCE_BINDING_REQUIRED")
    source_bundle_id = _sha_field(report.get("source_bundle_id"), "SOURCE_BUNDLE_ID_REQUIRED")
    reported_map_digest = _sha_field(report.get("weight_map_digest"), "SOURCE_WEIGHT_MAP_DIGEST_REQUIRED")
    observed_map_digest = weight_map_digest(weight_map)
    if observed_map_digest != reported_map_digest:
        raise SourceBoundLayoutError(
            "SOURCE_WEIGHT_MAP_DIGEST_MISMATCH",
            f"expected={reported_map_digest},observed={observed_map_digest}",
        )

    if compile_fn is None:
        try:
            from .glm53_layout_binding_bridge import compile_pager_source_plan as compile_fn  # type: ignore
        except ImportError:
            from glm53_layout_binding_bridge import compile_pager_source_plan as compile_fn  # type: ignore

    inner = compile_fn(
        report,
        weight_map=weight_map,
        headers=headers,
        expected_model_revision=expected_model_revision,
        expected_index_digest=expected_index_digest,
        per_expert_header_evidence=per_expert_header_evidence,
        expected_per_expert_header_repo_id=expected_per_expert_header_repo_id,
        expected_per_expert_header_receipt_digest=expected_per_expert_header_receipt_digest,
    )
    inner_map_digest = _sha_field(getattr(inner, "weight_map_digest", None), "INNER_WEIGHT_MAP_DIGEST_REQUIRED")
    if inner_map_digest != observed_map_digest:
        raise SourceBoundLayoutError("INNER_WEIGHT_MAP_DIGEST_MISMATCH")
    inner_plan_digest = _sha_field(getattr(inner, "source_plan_digest", None), "INNER_SOURCE_PLAN_DIGEST_REQUIRED")
    payload = {
        "schema": SCHEMA,
        "source_bundle_id": source_bundle_id,
        "weight_map_digest": observed_map_digest,
        "inner_source_plan_digest": inner_plan_digest,
        "g2_admitted": False,
        "large_checkpoint_admitted": False,
        "runtime_execution_proven": False,
    }
    return SourceBoundPagerSourcePlan(
        inner_plan=inner,
        source_bundle_id=source_bundle_id,
        weight_map_digest=observed_map_digest,
        source_bound_plan_digest=_sha(payload),
    )