"""AWJ032-GLM53-05A bounded cache adapter for the single PR #338 pager owner.

D0/reference only. This module wraps the existing PR #338 packed/per-expert
pagers; it is not a second checkpoint/pager owner. It adds the independently
useful PR #336 cache semantics without weakening source identity or physical-I/O
claim ceilings.

Cache budgets are based only on caller-supplied exact *logical* bundle-byte
metadata. Physical bytes saved/touched remain UNKNOWN; the underlying pager's
backend attestation remains the only physical-I/O evidence surface.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

import glm53_packed_expert_pager as packed
import glm53_per_expert_index_pager as per_expert


class CacheAdapterError(RuntimeError):
    pass


@dataclass(frozen=True)
class CacheReceipt:
    schema: str
    binding_digest: str
    selected_experts: tuple[int, ...]
    cache_hit_experts: tuple[int, ...]
    backend_miss_experts: tuple[int, ...]
    backend_read_count: int
    logical_bytes_returned: int
    cache_budget_bytes: int
    cache_entries_after: int
    cache_bytes_after: int
    physical_bytes_saved: None = None
    g2_admitted: bool = False
    claim_ceiling: str = "D0_LOGICAL_CACHE_ONLY_PHYSICAL_IO_UNKNOWN_NO_G2_PROOF"


@dataclass
class _Entry:
    payload: Any
    logical_nbytes: int


class _BoundedLRU:
    def __init__(self, budget_bytes: int) -> None:
        if isinstance(budget_bytes, bool) or not isinstance(budget_bytes, int) or budget_bytes < 0:
            raise CacheAdapterError("CACHE_BUDGET_INVALID")
        self.budget_bytes = budget_bytes
        self._items: OrderedDict[int, _Entry] = OrderedDict()
        self._bytes = 0

    @property
    def entries(self) -> int:
        return len(self._items)

    @property
    def bytes(self) -> int:
        return self._bytes

    def get(self, expert_id: int) -> _Entry | None:
        item = self._items.get(expert_id)
        if item is not None:
            self._items.move_to_end(expert_id)
        return item

    def put(self, expert_id: int, payload: Any, logical_nbytes: int) -> None:
        if isinstance(logical_nbytes, bool) or not isinstance(logical_nbytes, int) or logical_nbytes < 0:
            raise CacheAdapterError("LOGICAL_BUNDLE_NBYTES_INVALID")
        if self.budget_bytes == 0 or logical_nbytes > self.budget_bytes:
            return
        old = self._items.pop(expert_id, None)
        if old is not None:
            self._bytes -= old.logical_nbytes
        self._items[expert_id] = _Entry(payload=payload, logical_nbytes=logical_nbytes)
        self._bytes += logical_nbytes
        while self._bytes > self.budget_bytes and self._items:
            _, evicted = self._items.popitem(last=False)
            self._bytes -= evicted.logical_nbytes

    def evict(self, expert_ids: Sequence[int] | None = None) -> int:
        if expert_ids is None:
            count = len(self._items)
            self._items.clear()
            self._bytes = 0
            return count
        removed = 0
        for expert_id in tuple(dict.fromkeys(expert_ids)):
            item = self._items.pop(expert_id, None)
            if item is not None:
                self._bytes -= item.logical_nbytes
                removed += 1
        return removed


LogicalSizer = Callable[[int, Mapping[str, Any]], int]


class CachedPackedExpertPager:
    """Bounded cache wrapper around PR #338 ``PackedExpertPager``."""

    def __init__(
        self,
        pager: packed.PackedExpertPager,
        *,
        cache_budget_bytes: int,
        logical_bundle_nbytes: LogicalSizer,
    ) -> None:
        if not callable(logical_bundle_nbytes):
            raise CacheAdapterError("LOGICAL_BUNDLE_SIZER_REQUIRED")
        self.pager = pager
        self.binding = pager.binding
        self._sizer = logical_bundle_nbytes
        self._cache = _BoundedLRU(cache_budget_bytes)
        self._last_receipt: CacheReceipt | None = None

    def _assert_current(self, model_revision: str, index_digest: str) -> None:
        if model_revision != self.binding.model_revision or index_digest != self.binding.index_digest:
            raise packed.StaleSourceError("cache source identity is stale")

    def load_selected(
        self,
        expert_ids: Sequence[int],
        *,
        model_revision: str,
        index_digest: str,
    ) -> packed.PagedExperts:
        self._assert_current(model_revision, index_digest)
        selected = packed.canonical_expert_ids(expert_ids, self.binding.num_experts)
        if len(selected) == self.binding.num_experts:
            raise packed.WholeTensorReadForbidden("single-call selection may not materialize the full expert bank")

        payloads: dict[int, Mapping[str, Any]] = {}
        sizes: dict[int, int] = {}
        hits: list[int] = []
        misses: list[int] = []
        for expert_id in selected:
            item = self._cache.get(expert_id)
            if item is None:
                misses.append(expert_id)
            else:
                hits.append(expert_id)
                payloads[expert_id] = item.payload
                sizes[expert_id] = item.logical_nbytes

        backend_reads = 0
        if misses:
            page = self.pager.load_selected(
                misses, model_revision=model_revision, index_digest=index_digest
            )
            backend_reads = page.read_count
            # Stage every miss completely before any new entry is published.
            staged: list[tuple[int, Mapping[str, Any], int]] = []
            for expert_id in misses:
                row = page.local_row_by_expert[expert_id]
                bundle: dict[str, Any] = {
                    "gate_up": page.gate_up[row],
                    "down": page.down[row],
                    "scales": {name: values[row] for name, values in page.scale_bundle.items()},
                }
                nbytes = self._sizer(expert_id, bundle)
                if isinstance(nbytes, bool) or not isinstance(nbytes, int) or nbytes < 0:
                    raise CacheAdapterError("LOGICAL_BUNDLE_NBYTES_INVALID")
                staged.append((expert_id, bundle, nbytes))
            for expert_id, bundle, nbytes in staged:
                payloads[expert_id] = bundle
                sizes[expert_id] = nbytes
                self._cache.put(expert_id, bundle, nbytes)

        gate_up = tuple(payloads[e]["gate_up"] for e in selected)
        down = tuple(payloads[e]["down"] for e in selected)
        scale_names = tuple(sorted(next(iter(payloads.values()))["scales"])) if payloads else ()
        scales = {name: tuple(payloads[e]["scales"][name] for e in selected) for name in scale_names}
        result = packed.PagedExperts(
            expert_ids=selected,
            local_row_by_expert={e: i for i, e in enumerate(selected)},
            gate_up=gate_up,
            down=down,
            scale_bundle=scales,
            contiguous_runs=packed.contiguous_runs(selected),
            binding_digest=self.binding.digest,
            read_count=backend_reads,
        )
        self._last_receipt = CacheReceipt(
            schema="AuraExpertPagerCacheReceiptV1",
            binding_digest=self.binding.digest,
            selected_experts=selected,
            cache_hit_experts=tuple(hits),
            backend_miss_experts=tuple(misses),
            backend_read_count=backend_reads,
            logical_bytes_returned=sum(sizes[e] for e in selected),
            cache_budget_bytes=self._cache.budget_bytes,
            cache_entries_after=self._cache.entries,
            cache_bytes_after=self._cache.bytes,
        )
        return result

    def receipt(self) -> CacheReceipt:
        if self._last_receipt is None:
            raise CacheAdapterError("NO_SUCCESSFUL_CACHE_PAGE")
        return self._last_receipt

    def evict(self, expert_ids: Sequence[int] | None = None) -> int:
        return self._cache.evict(expert_ids)


class CachedPerExpertIndexPager:
    """Bounded cache wrapper around PR #338 ``PerExpertIndexPager``."""

    def __init__(
        self,
        pager: per_expert.PerExpertIndexPager,
        *,
        cache_budget_bytes: int,
        logical_bundle_nbytes: LogicalSizer,
    ) -> None:
        if not callable(logical_bundle_nbytes):
            raise CacheAdapterError("LOGICAL_BUNDLE_SIZER_REQUIRED")
        self.pager = pager
        self.binding = pager.binding
        self._sizer = logical_bundle_nbytes
        self._cache = _BoundedLRU(cache_budget_bytes)
        self._last_receipt: CacheReceipt | None = None

    def _assert_current(self, model_revision: str, index_digest: str) -> None:
        if model_revision != self.binding.model_revision:
            raise per_expert.PerExpertSourceError("MODEL_REVISION_STALE")
        if index_digest != self.binding.index_digest:
            raise per_expert.PerExpertSourceError("INDEX_DIGEST_STALE")

    def load_selected(
        self,
        expert_ids: Sequence[int],
        *,
        model_revision: str,
        index_digest: str,
    ) -> per_expert.PerExpertPage:
        self._assert_current(model_revision, index_digest)
        selected = per_expert.canonical_expert_ids(expert_ids, self.binding.num_experts)
        if len(selected) == self.binding.num_experts:
            raise per_expert.PerExpertReadError(
                "WHOLE_EXPERT_BANK_SINGLE_CALL_FORBIDDEN",
                "full reopenability must be exercised across bounded selections",
            )

        payloads: dict[int, Mapping[str, Any]] = {}
        sizes: dict[int, int] = {}
        hits: list[int] = []
        misses: list[int] = []
        for expert_id in selected:
            item = self._cache.get(expert_id)
            if item is None:
                misses.append(expert_id)
            else:
                hits.append(expert_id)
                payloads[expert_id] = item.payload
                sizes[expert_id] = item.logical_nbytes

        backend_reads = 0
        if misses:
            page = self.pager.load_selected(
                misses, model_revision=model_revision, index_digest=index_digest
            )
            backend_reads = page.tensor_reads
            staged: list[tuple[int, Mapping[str, Any], int]] = []
            for expert_id in misses:
                bundle: dict[str, Any] = {
                    "weights": dict(page.weights_by_expert[expert_id]),
                    "scales": dict(page.scales_by_expert[expert_id]),
                }
                nbytes = self._sizer(expert_id, bundle)
                if isinstance(nbytes, bool) or not isinstance(nbytes, int) or nbytes < 0:
                    raise CacheAdapterError("LOGICAL_BUNDLE_NBYTES_INVALID")
                staged.append((expert_id, bundle, nbytes))
            for expert_id, bundle, nbytes in staged:
                payloads[expert_id] = bundle
                sizes[expert_id] = nbytes
                self._cache.put(expert_id, bundle, nbytes)

        result = per_expert.PerExpertPage(
            expert_ids=selected,
            weights_by_expert={e: payloads[e]["weights"] for e in selected},
            scales_by_expert={e: payloads[e]["scales"] for e in selected},
            binding_digest=self.binding.digest,
            tensor_reads=backend_reads,
        )
        self._last_receipt = CacheReceipt(
            schema="AuraExpertPagerCacheReceiptV1",
            binding_digest=self.binding.digest,
            selected_experts=selected,
            cache_hit_experts=tuple(hits),
            backend_miss_experts=tuple(misses),
            backend_read_count=backend_reads,
            logical_bytes_returned=sum(sizes[e] for e in selected),
            cache_budget_bytes=self._cache.budget_bytes,
            cache_entries_after=self._cache.entries,
            cache_bytes_after=self._cache.bytes,
        )
        return result

    def receipt(self) -> CacheReceipt:
        if self._last_receipt is None:
            raise CacheAdapterError("NO_SUCCESSFUL_CACHE_PAGE")
        return self._last_receipt

    def evict(self, expert_ids: Sequence[int] | None = None) -> int:
        return self._cache.evict(expert_ids)
