"""Shared bounded cache/telemetry layer for the AWJ032 GLM-5.3 pager owner.

D0 only. This module composes the already fail-closed packed and per-expert pager
cores in this PR. It never widens checkpoint, runtime, provider, or G2 authority.
The cache is expert-atomic: a newly fetched expert is committed only after every
required weight/scale role has been returned successfully by the underlying pager.
Physical storage bytes remain UNKNOWN on backend misses unless a lower backend
supplies stronger evidence; cache-only calls can truthfully report zero backend I/O
while still exposing RAM residency and leaving energy/page-cache cost UNKNOWN.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

try:  # package import
    from . import glm53_packed_expert_pager as packed
    from . import glm53_per_expert_index_pager as per_expert
except ImportError:  # focused tests run from tools/awj032
    import glm53_packed_expert_pager as packed
    import glm53_per_expert_index_pager as per_expert

CACHE_SCHEMA = "AuraGLM53ExpertCacheTelemetryV1"


class CacheTelemetryError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _nbytes(value: Any) -> int:
    """Deterministic logical resident-byte estimator for fixture/runtime payloads."""
    nbytes = getattr(value, "nbytes", None)
    if isinstance(nbytes, int) and not isinstance(nbytes, bool) and nbytes >= 0:
        return nbytes
    numel = getattr(value, "numel", None)
    element_size = getattr(value, "element_size", None)
    if callable(numel) and callable(element_size):
        return int(numel() * element_size())
    if isinstance(value, bytes):
        return len(value)
    if isinstance(value, str):
        return len(value.encode("utf-8"))
    if isinstance(value, bool):
        return 1
    if isinstance(value, (int, float)):
        return 8
    if isinstance(value, Mapping):
        return sum(_nbytes(k) + _nbytes(v) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return sum(_nbytes(v) for v in value)
    raise CacheTelemetryError("CACHE_PAYLOAD_SIZE_UNKNOWN", type(value).__name__)


@dataclass(frozen=True)
class CacheValue:
    role: str
    payload: Any
    nbytes: int


@dataclass(frozen=True)
class ExpertCacheIdentity:
    model_revision: str
    representation_revision: str
    layer_id: str
    representation: str
    expert_id: int

    def role_key(self, role: str) -> tuple[str, str, str, str, int, str]:
        return (
            self.model_revision,
            self.representation_revision,
            self.layer_id,
            self.representation,
            self.expert_id,
            role,
        )


@dataclass(frozen=True)
class CacheGroup:
    identity: ExpertCacheIdentity
    values: Mapping[str, CacheValue]
    nbytes: int


@dataclass(frozen=True)
class CacheTelemetryReceipt:
    schema: str
    binding_digest: str
    layer_id: str
    selected_experts: tuple[int, ...]
    cache_budget_bytes: int
    cache_state_before: str
    cache_state_after: str
    cache_epoch: int
    cache_hit_entries: int
    cache_miss_entries: int
    cache_bytes_served: int
    logical_backend_bytes_required: int
    cache_entries_after: int
    cache_experts_after: int
    cache_bytes_after: int
    evicted_entries: int
    eviction_reason: str | None
    backend_read_operations: int
    logical_source_ranges: tuple[Any, ...]
    physical_io_attested: bool
    physical_expert_bytes_read: int | None
    physical_selected_only: bool | None
    whole_bank_reads: int | None
    whole_bank_materialized: bool | None
    backend_attestation_id: str | None
    page_cache_provenance: str | None
    cache_energy_joules: float | None
    g2_admitted: bool = False
    runtime_execution_proven: bool = False
    claim_ceiling: str = "D0_CACHE_TELEMETRY_ONLY_NO_FLAGSHIP_RUNTIME_OR_G2_PROOF"


class BoundedExpertLRU:
    """Byte-budget LRU storing complete expert role groups, never partial groups."""

    def __init__(self, budget_bytes: int) -> None:
        if isinstance(budget_bytes, bool) or not isinstance(budget_bytes, int) or budget_bytes < 0:
            raise CacheTelemetryError("CACHE_BUDGET_INVALID")
        self.budget_bytes = budget_bytes
        self._groups: OrderedDict[ExpertCacheIdentity, CacheGroup] = OrderedDict()
        self._bytes = 0
        self.epoch = 0

    @property
    def bytes(self) -> int:
        return self._bytes

    @property
    def expert_count(self) -> int:
        return len(self._groups)

    @property
    def entry_count(self) -> int:
        return sum(len(group.values) for group in self._groups.values())

    @property
    def state(self) -> str:
        return "COLD" if not self._groups else "WARM"

    def get_complete(self, identity: ExpertCacheIdentity, required_roles: Sequence[str]) -> CacheGroup | None:
        group = self._groups.get(identity)
        if group is None:
            return None
        if set(group.values) != set(required_roles):
            raise CacheTelemetryError("CACHE_GROUP_ROLE_SET_CORRUPT", str(identity.expert_id))
        for role, value in group.values.items():
            if value.role != role or value.nbytes < 0:
                raise CacheTelemetryError("CACHE_GROUP_VALUE_CORRUPT", role)
            # Expose the exact identity law in one reconstructable key.
            identity.role_key(role)
        self._groups.move_to_end(identity)
        return group

    def commit_complete(
        self,
        identity: ExpertCacheIdentity,
        values: Mapping[str, Any],
        required_roles: Sequence[str],
    ) -> tuple[int, str | None]:
        if set(values) != set(required_roles):
            raise CacheTelemetryError("CACHE_COMMIT_ROLE_SET_INCOMPLETE", str(identity.expert_id))
        cache_values = {
            role: CacheValue(role=role, payload=values[role], nbytes=_nbytes(values[role]))
            for role in required_roles
        }
        total = sum(v.nbytes for v in cache_values.values())
        # Never commit a partial expert merely because the budget is too small.
        if self.budget_bytes == 0 or total > self.budget_bytes:
            return 0, "EXPERT_GROUP_EXCEEDS_BUDGET" if total > self.budget_bytes else None

        old = self._groups.pop(identity, None)
        if old is not None:
            self._bytes -= old.nbytes

        evicted_entries = 0
        while self._groups and self._bytes + total > self.budget_bytes:
            _, evicted = self._groups.popitem(last=False)
            self._bytes -= evicted.nbytes
            evicted_entries += len(evicted.values)

        group = CacheGroup(identity=identity, values=cache_values, nbytes=total)
        self._groups[identity] = group
        self._bytes += total
        return evicted_entries, "BUDGET" if evicted_entries else None

    def evict_all(self) -> int:
        removed = self.entry_count
        self._groups.clear()
        self._bytes = 0
        self.epoch += 1
        return removed


class _CachedPagerBase:
    def __init__(self, cache_budget_bytes: int) -> None:
        self.cache = BoundedExpertLRU(cache_budget_bytes)
        self._last_receipt: CacheTelemetryReceipt | None = None

    def receipt(self) -> CacheTelemetryReceipt:
        if self._last_receipt is None:
            raise CacheTelemetryError("NO_SUCCESSFUL_CACHE_PAGE")
        return self._last_receipt

    def evict(self) -> int:
        return self.cache.evict_all()

    def _identity(self, binding: Any, expert_id: int) -> ExpertCacheIdentity:
        return ExpertCacheIdentity(
            model_revision=binding.model_revision,
            representation_revision=binding.index_digest,
            layer_id=binding.layer_id,
            representation=binding.representation,
            expert_id=expert_id,
        )


class CachedPackedExpertPager(_CachedPagerBase):
    """Cache wrapper preserving PackedExpertPager source and whole-bank laws."""

    def __init__(self, binding: packed.ExpertSourceBinding, backend: packed.SliceBackend, *, cache_budget_bytes: int) -> None:
        super().__init__(cache_budget_bytes)
        self.binding = binding
        self.core = packed.PackedExpertPager(binding, backend)

    def load_selected(self, expert_ids: Sequence[int], *, model_revision: str, index_digest: str) -> packed.PagedExperts:
        # Stale calls must fail before cache lookup/serve.
        if model_revision != self.binding.model_revision or index_digest != self.binding.index_digest:
            raise packed.StaleSourceError("cache source identity mismatch")
        selected = packed.canonical_expert_ids(expert_ids, self.binding.num_experts)
        if len(selected) == self.binding.num_experts:
            raise packed.WholeTensorReadForbidden("single-call selection may not materialize the full expert bank")

        families = dict(self.binding.tensor_map)
        families.update({f"scale:{name}": key for name, key in self.binding.scale_map.items()})
        roles = tuple(families)
        before = self.cache.state
        hits: dict[int, CacheGroup] = {}
        misses: list[int] = []
        hit_entries = 0
        miss_entries = 0
        cache_bytes_served = 0
        for expert_id in selected:
            identity = self._identity(self.binding, expert_id)
            group = self.cache.get_complete(identity, roles)
            if group is None:
                misses.append(expert_id)
                miss_entries += len(roles)
            else:
                hits[expert_id] = group
                hit_entries += len(roles)
                cache_bytes_served += group.nbytes

        fetched: packed.PagedExperts | None = None
        core_receipt = None
        logical_backend_bytes = 0
        read_operations = 0
        source_ranges: tuple[Any, ...] = ()
        evicted_entries = 0
        eviction_reason = None
        if misses:
            fetched = self.core.load_selected(misses, model_revision=model_revision, index_digest=index_digest)
            core_receipt = self.core.receipt()
            read_operations = fetched.read_count
            source_ranges = tuple(fetched.contiguous_runs)
            # Commit only after the whole underlying page operation has succeeded.
            for expert_id in fetched.expert_ids:
                row = fetched.local_row_by_expert[expert_id]
                values = {
                    "gate_up": fetched.gate_up[row],
                    "down": fetched.down[row],
                    **{f"scale:{name}": rows[row] for name, rows in fetched.scale_bundle.items()},
                }
                logical_backend_bytes += sum(_nbytes(v) for v in values.values())
                evicted, reason = self.cache.commit_complete(self._identity(self.binding, expert_id), values, roles)
                evicted_entries += evicted
                eviction_reason = reason or eviction_reason

        gate_up = []
        down = []
        scales: dict[str, list[Any]] = {name: [] for name in self.binding.scale_map}
        local = {}
        for row, expert_id in enumerate(selected):
            local[expert_id] = row
            group = self.cache.get_complete(self._identity(self.binding, expert_id), roles)
            if group is not None:
                values = {role: value.payload for role, value in group.values.items()}
            elif fetched is not None and expert_id in fetched.local_row_by_expert:
                idx = fetched.local_row_by_expert[expert_id]
                values = {
                    "gate_up": fetched.gate_up[idx],
                    "down": fetched.down[idx],
                    **{f"scale:{name}": rows[idx] for name, rows in fetched.scale_bundle.items()},
                }
            else:
                raise CacheTelemetryError("CACHE_PAGE_RECONSTRUCTION_FAILED", str(expert_id))
            gate_up.append(values["gate_up"])
            down.append(values["down"])
            for name in scales:
                scales[name].append(values[f"scale:{name}"])

        cache_only = not misses
        physical_attested = cache_only or bool(core_receipt and core_receipt.physical_io_attested)
        physical_selected_only = True if cache_only else (None if core_receipt is None else core_receipt.physical_selected_only)
        whole_reads = 0 if cache_only else (None if core_receipt is None else core_receipt.whole_tensor_reads)
        whole_materialized = False if cache_only else (None if core_receipt is None else core_receipt.whole_bank_materialized)
        attestation_id = "AURA_CACHE_ONLY_NO_BACKEND_CALL" if cache_only else (None if core_receipt is None else core_receipt.backend_attestation_id)
        physical_bytes = 0 if cache_only else None

        result = packed.PagedExperts(
            expert_ids=selected,
            local_row_by_expert=local,
            gate_up=tuple(gate_up),
            down=tuple(down),
            scale_bundle={name: tuple(values) for name, values in scales.items()},
            contiguous_runs=packed.contiguous_runs(selected),
            binding_digest=self.binding.digest,
            read_count=read_operations,
        )
        self._last_receipt = CacheTelemetryReceipt(
            schema=CACHE_SCHEMA,
            binding_digest=self.binding.digest,
            layer_id=self.binding.layer_id,
            selected_experts=selected,
            cache_budget_bytes=self.cache.budget_bytes,
            cache_state_before=before,
            cache_state_after=self.cache.state,
            cache_epoch=self.cache.epoch,
            cache_hit_entries=hit_entries,
            cache_miss_entries=miss_entries,
            cache_bytes_served=cache_bytes_served,
            logical_backend_bytes_required=logical_backend_bytes,
            cache_entries_after=self.cache.entry_count,
            cache_experts_after=self.cache.expert_count,
            cache_bytes_after=self.cache.bytes,
            evicted_entries=evicted_entries,
            eviction_reason=eviction_reason,
            backend_read_operations=read_operations,
            logical_source_ranges=source_ranges,
            physical_io_attested=physical_attested,
            physical_expert_bytes_read=physical_bytes,
            physical_selected_only=physical_selected_only,
            whole_bank_reads=whole_reads,
            whole_bank_materialized=whole_materialized,
            backend_attestation_id=attestation_id,
            page_cache_provenance=None,
            cache_energy_joules=None,
        )
        return result


class CachedPerExpertIndexPager(_CachedPagerBase):
    """Cache wrapper preserving PerExpertIndexPager exact-key/source laws."""

    def __init__(self, binding: per_expert.PerExpertIndexBinding, backend: per_expert.TensorKeyBackend, *, cache_budget_bytes: int) -> None:
        super().__init__(cache_budget_bytes)
        self.binding = binding
        self.core = per_expert.PerExpertIndexPager(binding, backend)

    def _roles(self) -> tuple[str, ...]:
        roles = tuple(f"weight:{role}" for role in per_expert.WEIGHT_ROLES)
        if self.binding.require_fp8_scales:
            roles += tuple(f"scale:{role}" for role in per_expert.SCALE_ROLES)
        return roles

    def load_selected(self, expert_ids: Sequence[int], *, model_revision: str, index_digest: str) -> per_expert.PerExpertPage:
        if model_revision != self.binding.model_revision or index_digest != self.binding.index_digest:
            raise per_expert.PerExpertSourceError("CACHE_SOURCE_IDENTITY_MISMATCH")
        selected = per_expert.canonical_expert_ids(expert_ids, self.binding.num_experts)
        if len(selected) == self.binding.num_experts:
            raise per_expert.PerExpertReadError("WHOLE_EXPERT_BANK_SINGLE_CALL_FORBIDDEN")
        roles = self._roles()
        before = self.cache.state
        misses: list[int] = []
        hit_entries = 0
        miss_entries = 0
        cache_bytes_served = 0
        for expert_id in selected:
            group = self.cache.get_complete(self._identity(self.binding, expert_id), roles)
            if group is None:
                misses.append(expert_id)
                miss_entries += len(roles)
            else:
                hit_entries += len(roles)
                cache_bytes_served += group.nbytes

        fetched: per_expert.PerExpertPage | None = None
        core_receipt = None
        logical_backend_bytes = 0
        read_operations = 0
        source_ranges: list[Any] = []
        evicted_entries = 0
        eviction_reason = None
        if misses:
            fetched = self.core.load_selected(misses, model_revision=model_revision, index_digest=index_digest)
            core_receipt = self.core.receipt()
            read_operations = fetched.tensor_reads
            for expert_id in fetched.expert_ids:
                values = {f"weight:{role}": payload for role, payload in fetched.weights_by_expert[expert_id].items()}
                values.update({f"scale:{role}": payload for role, payload in fetched.scales_by_expert[expert_id].items()})
                logical_backend_bytes += sum(_nbytes(v) for v in values.values())
                source = self.binding.experts[expert_id]
                for key in list(source.weight_keys.values()) + list(source.scale_keys.values()):
                    source_ranges.append((source.shard_by_key[key], key))
                evicted, reason = self.cache.commit_complete(self._identity(self.binding, expert_id), values, roles)
                evicted_entries += evicted
                eviction_reason = reason or eviction_reason

        weights_by_expert: dict[int, dict[str, Any]] = {}
        scales_by_expert: dict[int, dict[str, Any]] = {}
        for expert_id in selected:
            group = self.cache.get_complete(self._identity(self.binding, expert_id), roles)
            if group is not None:
                values = {role: value.payload for role, value in group.values.items()}
            elif fetched is not None and expert_id in fetched.weights_by_expert:
                values = {f"weight:{role}": payload for role, payload in fetched.weights_by_expert[expert_id].items()}
                values.update({f"scale:{role}": payload for role, payload in fetched.scales_by_expert[expert_id].items()})
            else:
                raise CacheTelemetryError("CACHE_PAGE_RECONSTRUCTION_FAILED", str(expert_id))
            weights_by_expert[expert_id] = {role: values[f"weight:{role}"] for role in per_expert.WEIGHT_ROLES}
            scales_by_expert[expert_id] = {
                role: values[f"scale:{role}"]
                for role in per_expert.SCALE_ROLES
                if f"scale:{role}" in values
            }

        cache_only = not misses
        physical_attested = cache_only or bool(core_receipt and core_receipt.physical_io_attested)
        physical_selected_only = True if cache_only else (None if core_receipt is None else core_receipt.selected_expert_tensor_reads_only)
        whole_reads = 0 if cache_only else (None if core_receipt is None else core_receipt.whole_bank_reads)
        whole_materialized = False if cache_only else (None if core_receipt is None else core_receipt.whole_expert_bank_materialized)
        attestation_id = "AURA_CACHE_ONLY_NO_BACKEND_CALL" if cache_only else (None if core_receipt is None else core_receipt.backend_attestation_id)
        physical_bytes = 0 if cache_only else None

        page = per_expert.PerExpertPage(
            expert_ids=selected,
            weights_by_expert=weights_by_expert,
            scales_by_expert=scales_by_expert,
            binding_digest=self.binding.digest,
            tensor_reads=read_operations,
        )
        self._last_receipt = CacheTelemetryReceipt(
            schema=CACHE_SCHEMA,
            binding_digest=self.binding.digest,
            layer_id=self.binding.layer_id,
            selected_experts=selected,
            cache_budget_bytes=self.cache.budget_bytes,
            cache_state_before=before,
            cache_state_after=self.cache.state,
            cache_epoch=self.cache.epoch,
            cache_hit_entries=hit_entries,
            cache_miss_entries=miss_entries,
            cache_bytes_served=cache_bytes_served,
            logical_backend_bytes_required=logical_backend_bytes,
            cache_entries_after=self.cache.entry_count,
            cache_experts_after=self.cache.expert_count,
            cache_bytes_after=self.cache.bytes,
            evicted_entries=evicted_entries,
            eviction_reason=eviction_reason,
            backend_read_operations=read_operations,
            logical_source_ranges=tuple(source_ranges),
            physical_io_attested=physical_attested,
            physical_expert_bytes_read=physical_bytes,
            physical_selected_only=physical_selected_only,
            whole_bank_reads=whole_reads,
            whole_bank_materialized=whole_materialized,
            backend_attestation_id=attestation_id,
            page_cache_provenance=None,
            cache_energy_joules=None,
        )
        return page
