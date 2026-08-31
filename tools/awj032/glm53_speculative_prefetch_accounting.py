"""Router-separated speculative expert-prefetch accounting for GLM-5.3.

D0 / HS1 / NONPROMOTING.

This membrane composes two already-owned Aura artifacts without changing either:
- PR #333 owns the requirement to preserve the native GLM router / FP8 expert semantics.
- PR #338 owns immutable source-bound bounded expert paging and its physical-I/O
  attestation boundary.

A prediction may stage bounded expert pages. It never chooses the executed expert set.
The native route remains the sole source of expert-selection truth; prediction misses
require exact demand loading. Physical-byte claims remain UNKNOWN because PR #338's
pager receipt does not measure bytes.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Sequence

from tools.awj032.glm53_packed_expert_pager import (
    ExpertSourceBinding,
    PagerReceipt,
    canonical_expert_ids,
)

SCHEMA = "AuraGLM53SpeculativePrefetchAccountingV1"
NATIVE_ROUTER_PARENT_PR = 333
NATIVE_ROUTER_PARENT_HEAD = "815ec64338114d8d3947af6c295b28f8f401287e"
NATIVE_ROUTER_SOURCE_BLOB = "6f2c2c7e577a451ffeb46af65fa70d9ce25f1aaa"
PAGER_PARENT_PR = 338
PAGER_PARENT_HEAD = "7f33d2e8f6e53b8862f8ecf0ddc28e0564fb388a"
PAGER_SOURCE_BLOB = "2b9b50e23b8ed963be4c1981598d30adb04dc1fe"
PAGER_SCHEMA = "AuraPackedExpertPagerReceiptV1"
PAGER_CEILING = "SYNTHETIC_PAGER_CORE_ONLY_NO_FLAGSHIP_WEIGHT_OR_RUNTIME_PROOF"


class PrefetchAccountingError(RuntimeError):
    """Fail-closed prefetch accounting failure."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _ppm(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        return 0
    return (numerator * 1_000_000) // denominator


def _validate_prefetch_receipt(
    *,
    binding: ExpertSourceBinding,
    staged: tuple[int, ...],
    receipt: PagerReceipt,
) -> None:
    if not isinstance(receipt, PagerReceipt):
        raise PrefetchAccountingError("PREFETCH_RECEIPT_MUST_BE_PR338_TYPED_RECEIPT")
    if receipt.schema != PAGER_SCHEMA:
        raise PrefetchAccountingError("PREFETCH_RECEIPT_SCHEMA_MISMATCH")
    if receipt.binding_digest != binding.digest or receipt.layer_id != binding.layer_id:
        raise PrefetchAccountingError("PREFETCH_RECEIPT_SOURCE_BINDING_MISMATCH")
    if tuple(receipt.selected_experts) != staged:
        raise PrefetchAccountingError("PREFETCH_RECEIPT_STAGED_EXPERT_SET_MISMATCH")
    if receipt.logical_bounded_row_requests is not True:
        raise PrefetchAccountingError("PREFETCH_MUST_USE_BOUNDED_ROW_REQUESTS")
    if receipt.g2_admitted is not False or receipt.claim_ceiling != PAGER_CEILING:
        raise PrefetchAccountingError("PREFETCH_PAGER_CLAIM_CEILING_WIDENED")
    if isinstance(receipt.read_count, bool) or not isinstance(receipt.read_count, int) or receipt.read_count < 1:
        raise PrefetchAccountingError("PREFETCH_READ_COUNT_INVALID")
    if type(receipt.physical_io_attested) is not bool:
        raise PrefetchAccountingError("PREFETCH_PHYSICAL_ATTESTATION_FLAG_INVALID")
    if receipt.physical_io_attested is False:
        if any(
            value is not None
            for value in (
                receipt.physical_selected_only,
                receipt.whole_tensor_reads,
                receipt.whole_bank_materialized,
                receipt.backend_attestation_id,
            )
        ):
            raise PrefetchAccountingError("UNATTESTED_PREFETCH_CANNOT_CARRY_PHYSICAL_CLAIMS")
    else:
        if type(receipt.physical_selected_only) is not bool:
            raise PrefetchAccountingError("ATTESTED_PREFETCH_SELECTED_ONLY_MUST_BE_BOOL")
        if (
            isinstance(receipt.whole_tensor_reads, bool)
            or not isinstance(receipt.whole_tensor_reads, int)
            or receipt.whole_tensor_reads < 0
        ):
            raise PrefetchAccountingError("ATTESTED_PREFETCH_WHOLE_READ_COUNT_INVALID")
        if type(receipt.whole_bank_materialized) is not bool:
            raise PrefetchAccountingError("ATTESTED_PREFETCH_WHOLE_BANK_FLAG_INVALID")
        if not isinstance(receipt.backend_attestation_id, str) or not receipt.backend_attestation_id.strip():
            raise PrefetchAccountingError("ATTESTED_PREFETCH_ID_REQUIRED")


@dataclass(frozen=True)
class PrefetchAccountingReceipt:
    schema: str
    native_router_parent_pr: int
    native_router_parent_head: str
    native_router_source_blob: str
    pager_parent_pr: int
    pager_parent_head: str
    pager_source_blob: str
    binding_digest: str
    layer_id: str
    num_experts: int
    predicted_experts: tuple[int, ...]
    logically_staged_experts: tuple[int, ...]
    native_route_experts: tuple[int, ...]
    useful_prefetch_experts: tuple[int, ...]
    wasted_prefetch_experts: tuple[int, ...]
    demand_load_experts: tuple[int, ...]
    prediction_precision_ppm: int
    native_route_coverage_ppm: int
    logical_prefetch_read_count: int
    physical_io_attested: bool
    physical_selected_only: bool | None
    whole_bank_reads: int | None
    whole_bank_materialized: bool | None
    backend_attestation_id: str | None
    physical_bytes_read: int | None = None
    native_route_is_expert_selection_truth: bool = True
    prediction_can_change_native_route: bool = False
    demand_load_required_for_misses: bool = True
    demand_load_observed: bool = False
    execution_authorized: bool = False
    provider_effect_authorized: bool = False
    g2_admitted: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False
    claim_ceiling: str = "PREFETCH_ACCOUNTING_ONLY_NO_ROUTE_MUTATION_EXECUTION_OR_PHYSICAL_BYTE_PROOF"

    def validate_claim_ceiling(self) -> None:
        if self.native_route_is_expert_selection_truth is not True:
            raise PrefetchAccountingError("NATIVE_ROUTE_TRUTH_MUST_REMAIN_TRUE")
        forbidden = (
            self.prediction_can_change_native_route,
            self.demand_load_observed,
            self.execution_authorized,
            self.provider_effect_authorized,
            self.g2_admitted,
            self.semantic_k27_authority,
            self.native_private_transformer_kv_accessed,
        )
        if any(value is not False for value in forbidden):
            raise PrefetchAccountingError("PREFETCH_ACCOUNTING_CANNOT_PROMOTE_ROUTE_OR_EFFECT_AUTHORITY")
        if self.physical_bytes_read is not None:
            raise PrefetchAccountingError("PHYSICAL_BYTE_COUNT_UNEARNED")
        if self.demand_load_required_for_misses is not bool(self.demand_load_experts):
            raise PrefetchAccountingError("DEMAND_LOAD_REQUIREMENT_MUST_MATCH_MISS_SET")

    @property
    def receipt_digest(self) -> str:
        self.validate_claim_ceiling()
        return _digest({"domain": SCHEMA, "receipt": asdict(self)})

    def to_dict(self) -> dict[str, Any]:
        body = asdict(self)
        body["receipt_digest"] = self.receipt_digest
        return body


def account_speculative_prefetch(
    *,
    binding: ExpertSourceBinding,
    predicted_expert_ids: Sequence[int],
    native_route_expert_ids: Sequence[int],
    prefetch_receipt: PagerReceipt,
) -> PrefetchAccountingReceipt:
    """Account staged prediction vs native route without allowing prediction to route.

    ``prefetch_receipt`` proves only that PR #338's bounded logical pager completed for
    the predicted expert set. The native route is supplied separately and is never
    derived from prediction. Any native expert absent from the staged set is a
    mandatory exact demand-load residual, not a route mutation opportunity.
    """
    predicted = canonical_expert_ids(predicted_expert_ids, binding.num_experts)
    if len(predicted) == binding.num_experts:
        raise PrefetchAccountingError("PREFETCH_MAY_NOT_STAGE_FULL_EXPERT_BANK")
    native_route = canonical_expert_ids(native_route_expert_ids, binding.num_experts)
    _validate_prefetch_receipt(binding=binding, staged=predicted, receipt=prefetch_receipt)

    predicted_set = set(predicted)
    route_set = set(native_route)
    useful = tuple(sorted(predicted_set & route_set))
    wasted = tuple(sorted(predicted_set - route_set))
    misses = tuple(sorted(route_set - predicted_set))

    receipt = PrefetchAccountingReceipt(
        schema=SCHEMA,
        native_router_parent_pr=NATIVE_ROUTER_PARENT_PR,
        native_router_parent_head=NATIVE_ROUTER_PARENT_HEAD,
        native_router_source_blob=NATIVE_ROUTER_SOURCE_BLOB,
        pager_parent_pr=PAGER_PARENT_PR,
        pager_parent_head=PAGER_PARENT_HEAD,
        pager_source_blob=PAGER_SOURCE_BLOB,
        binding_digest=binding.digest,
        layer_id=binding.layer_id,
        num_experts=binding.num_experts,
        predicted_experts=predicted,
        logically_staged_experts=tuple(prefetch_receipt.selected_experts),
        native_route_experts=native_route,
        useful_prefetch_experts=useful,
        wasted_prefetch_experts=wasted,
        demand_load_experts=misses,
        prediction_precision_ppm=_ppm(len(useful), len(predicted)),
        native_route_coverage_ppm=_ppm(len(useful), len(native_route)),
        logical_prefetch_read_count=prefetch_receipt.read_count,
        physical_io_attested=prefetch_receipt.physical_io_attested,
        physical_selected_only=prefetch_receipt.physical_selected_only,
        whole_bank_reads=prefetch_receipt.whole_tensor_reads,
        whole_bank_materialized=prefetch_receipt.whole_bank_materialized,
        backend_attestation_id=prefetch_receipt.backend_attestation_id,
        demand_load_required_for_misses=bool(misses),
    )
    receipt.validate_claim_ceiling()
    return receipt
