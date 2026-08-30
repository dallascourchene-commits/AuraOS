"""Fail-closed packed-expert pager for AWJ032-GLM53-01A.

This module owns only selected-slice materialization.  It does not own a model
router, Transformers expert math, remote code, checkpoint download, or G2
admission.  A caller supplies the expert ids selected by the model's native
router; the pager returns the exact first-axis slices for the required tensor
families while preserving source/revision identity and a bounded cache.

The default production seam is safetensors ``safe_open(...).get_slice(key)``.
That reader is imported lazily so the deterministic in-memory fixture has no
third-party dependency.  ``logical_bytes_returned`` is measured exactly;
physical storage bytes touched remain UNKNOWN until host I/O instrumentation
measures filesystem/page-cache amplification.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

PAGER_SCHEMA = "AuraPackedExpertPagerV1"
RECEIPT_SCHEMA = "AuraPackedExpertPagerReceiptV1"
UNKNOWN = "UNKNOWN"


class PackedExpertPagerError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


def _text(value: Any, *, code: str) -> str:
    out = str(value or "").strip()
    if not out:
        raise PackedExpertPagerError(code)
    return out


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise PackedExpertPagerError("NONCANONICAL_PAGER_STATE") from exc


def _digest(domain: str, value: Any) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical(value)).hexdigest()


def selected_expert_ids(top_k_index: Sequence[Sequence[int]], *, num_experts: int) -> tuple[int, ...]:
    """Return the stable unique routed expert set without changing router semantics."""
    if isinstance(num_experts, bool) or not isinstance(num_experts, int) or num_experts < 1:
        raise PackedExpertPagerError("NUM_EXPERTS_INVALID")
    if isinstance(top_k_index, (str, bytes)) or not isinstance(top_k_index, Sequence):
        raise PackedExpertPagerError("TOPK_INDEX_INVALID")
    selected: set[int] = set()
    for row in top_k_index:
        if isinstance(row, (str, bytes)) or not isinstance(row, Sequence):
            raise PackedExpertPagerError("TOPK_INDEX_INVALID")
        for expert_id in row:
            if isinstance(expert_id, bool) or not isinstance(expert_id, int):
                raise PackedExpertPagerError("EXPERT_ID_INVALID")
            if expert_id < 0 or expert_id >= num_experts:
                raise PackedExpertPagerError("EXPERT_ID_OUT_OF_RANGE", str(expert_id))
            selected.add(expert_id)
    return tuple(sorted(selected))


@dataclass(frozen=True)
class ExpertSlice:
    tensor_key: str
    expert_id: int
    payload: Any
    shape: tuple[int, ...]
    nbytes: int
    source_revision: str
    source_digest: str

    def __post_init__(self) -> None:
        _text(self.tensor_key, code="TENSOR_KEY_REQUIRED")
        if isinstance(self.expert_id, bool) or not isinstance(self.expert_id, int) or self.expert_id < 0:
            raise PackedExpertPagerError("EXPERT_ID_INVALID")
        if not isinstance(self.shape, tuple) or not self.shape:
            raise PackedExpertPagerError("SLICE_SHAPE_INVALID")
        if any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in self.shape):
            raise PackedExpertPagerError("SLICE_SHAPE_INVALID")
        if isinstance(self.nbytes, bool) or not isinstance(self.nbytes, int) or self.nbytes < 0:
            raise PackedExpertPagerError("SLICE_NBYTES_INVALID")
        _text(self.source_revision, code="SOURCE_REVISION_REQUIRED")
        digest = _text(self.source_digest, code="SOURCE_DIGEST_REQUIRED")
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest.lower()):
            raise PackedExpertPagerError("SOURCE_DIGEST_INVALID")


class PackedTensorReader(Protocol):
    @property
    def source_revision(self) -> str: ...

    @property
    def source_digest(self) -> str: ...

    def first_axis_size(self, tensor_key: str) -> int: ...

    def read_expert(self, tensor_key: str, expert_id: int) -> ExpertSlice: ...


@dataclass(frozen=True)
class PagerBinding:
    model_revision: str
    layer_id: str
    representation: str
    total_experts: int
    tensor_families: tuple[str, ...]
    expected_source_revision: str
    expected_source_digest: str
    schema: str = PAGER_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != PAGER_SCHEMA:
            raise PackedExpertPagerError("PAGER_SCHEMA_MISMATCH")
        for value, code in (
            (self.model_revision, "MODEL_REVISION_REQUIRED"),
            (self.layer_id, "LAYER_ID_REQUIRED"),
            (self.representation, "REPRESENTATION_REQUIRED"),
            (self.expected_source_revision, "SOURCE_REVISION_REQUIRED"),
        ):
            _text(value, code=code)
        if isinstance(self.total_experts, bool) or not isinstance(self.total_experts, int) or self.total_experts < 1:
            raise PackedExpertPagerError("TOTAL_EXPERTS_INVALID")
        if not isinstance(self.tensor_families, tuple) or not self.tensor_families:
            raise PackedExpertPagerError("TENSOR_FAMILIES_REQUIRED")
        if len(set(self.tensor_families)) != len(self.tensor_families):
            raise PackedExpertPagerError("TENSOR_FAMILY_DUPLICATE")
        for key in self.tensor_families:
            _text(key, code="TENSOR_KEY_REQUIRED")
        digest = _text(self.expected_source_digest, code="SOURCE_DIGEST_REQUIRED").lower()
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise PackedExpertPagerError("SOURCE_DIGEST_INVALID")


@dataclass(frozen=True)
class PagerReceipt:
    schema: str
    pager_id: str
    model_revision: str
    layer_id: str
    representation: str
    source_revision: str
    source_digest: str
    requested_expert_ids: tuple[int, ...]
    materialized_expert_ids: tuple[int, ...]
    cache_hit_expert_ids: tuple[int, ...]
    tensor_families: tuple[str, ...]
    logical_bytes_returned: int
    physical_bytes_observed: str
    whole_bank_materialized: bool
    cache_entries_after: int
    cache_bytes_after: int
    status: str
    execution_authorized: bool = False
    model_execution_proven: bool = False
    g2_admitted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PagerLoad:
    slices: Mapping[int, Mapping[str, ExpertSlice]]
    receipt: PagerReceipt


class PackedExpertPager:
    """Source-bound selected-expert slice pager with an LRU cache.

    Cache entries are individual (tensor_family, expert_id) slices.  One expert
    load is atomic across all required families: if any family is missing or
    mismatched, no newly read slice from that expert is committed to the cache.
    """

    def __init__(
        self,
        binding: PagerBinding,
        reader: PackedTensorReader,
        *,
        cache_budget_bytes: int = 0,
    ) -> None:
        if isinstance(cache_budget_bytes, bool) or not isinstance(cache_budget_bytes, int) or cache_budget_bytes < 0:
            raise PackedExpertPagerError("CACHE_BUDGET_INVALID")
        self.binding = binding
        self.reader = reader
        self.cache_budget_bytes = cache_budget_bytes
        self._cache: OrderedDict[tuple[str, int], ExpertSlice] = OrderedDict()
        self._cache_bytes = 0
        self._validate_source_binding()
        self._validate_tensor_families()
        self.pager_id = "pager-" + _digest(
            "AURA_PACKED_EXPERT_PAGER_V1",
            {
                "model_revision": binding.model_revision,
                "layer_id": binding.layer_id,
                "representation": binding.representation,
                "total_experts": binding.total_experts,
                "tensor_families": binding.tensor_families,
                "source_revision": binding.expected_source_revision,
                "source_digest": binding.expected_source_digest,
                "cache_budget_bytes": cache_budget_bytes,
            },
        )[:24]

    def _validate_source_binding(self) -> None:
        if self.reader.source_revision != self.binding.expected_source_revision:
            raise PackedExpertPagerError(
                "SOURCE_REVISION_MISMATCH",
                f"expected={self.binding.expected_source_revision},observed={self.reader.source_revision}",
            )
        if self.reader.source_digest.lower() != self.binding.expected_source_digest.lower():
            raise PackedExpertPagerError("SOURCE_DIGEST_MISMATCH")

    def _validate_tensor_families(self) -> None:
        for key in self.binding.tensor_families:
            try:
                size = self.reader.first_axis_size(key)
            except (KeyError, FileNotFoundError) as exc:
                raise PackedExpertPagerError("TENSOR_FAMILY_MISSING", key) from exc
            if size != self.binding.total_experts:
                raise PackedExpertPagerError(
                    "TENSOR_EXPERT_AXIS_MISMATCH",
                    f"{key}:expected={self.binding.total_experts},observed={size}",
                )

    def _cache_key(self, tensor_key: str, expert_id: int) -> tuple[str, int]:
        return tensor_key, expert_id

    def _cached(self, tensor_key: str, expert_id: int) -> ExpertSlice | None:
        key = self._cache_key(tensor_key, expert_id)
        item = self._cache.get(key)
        if item is not None:
            self._cache.move_to_end(key)
        return item

    def _commit_cache(self, item: ExpertSlice) -> None:
        if self.cache_budget_bytes == 0 or item.nbytes > self.cache_budget_bytes:
            return
        key = self._cache_key(item.tensor_key, item.expert_id)
        old = self._cache.pop(key, None)
        if old is not None:
            self._cache_bytes -= old.nbytes
        self._cache[key] = item
        self._cache_bytes += item.nbytes
        while self._cache_bytes > self.cache_budget_bytes and self._cache:
            _, evicted = self._cache.popitem(last=False)
            self._cache_bytes -= evicted.nbytes

    def evict(self, *, expert_ids: Sequence[int] | None = None) -> int:
        if expert_ids is None:
            count = len(self._cache)
            self._cache.clear()
            self._cache_bytes = 0
            return count
        selected = set(selected_expert_ids([tuple(expert_ids)], num_experts=self.binding.total_experts))
        removed = 0
        for key in list(self._cache):
            if key[1] not in selected:
                continue
            item = self._cache.pop(key)
            self._cache_bytes -= item.nbytes
            removed += 1
        return removed

    def load_selected(self, expert_ids: Sequence[int]) -> PagerLoad:
        self._validate_source_binding()
        selected = selected_expert_ids([tuple(expert_ids)], num_experts=self.binding.total_experts)
        result: dict[int, dict[str, ExpertSlice]] = {}
        materialized: set[int] = set()
        all_cached: set[int] = set()
        logical_bytes = 0

        for expert_id in selected:
            staged: dict[str, ExpertSlice] = {}
            staged_new: list[ExpertSlice] = []
            expert_all_cached = True
            for tensor_key in self.binding.tensor_families:
                item = self._cached(tensor_key, expert_id)
                if item is None:
                    expert_all_cached = False
                    try:
                        item = self.reader.read_expert(tensor_key, expert_id)
                    except (KeyError, FileNotFoundError, IndexError) as exc:
                        raise PackedExpertPagerError(
                            "EXPERT_SLICE_MISSING", f"{tensor_key}:{expert_id}"
                        ) from exc
                    self._validate_slice(item, tensor_key=tensor_key, expert_id=expert_id)
                    staged_new.append(item)
                staged[tensor_key] = item
                logical_bytes += item.nbytes
            # Commit only after every family for this expert validated.
            for item in staged_new:
                self._commit_cache(item)
            if staged_new:
                materialized.add(expert_id)
            if expert_all_cached:
                all_cached.add(expert_id)
            result[expert_id] = staged

        receipt_body = {
            "pager_id": self.pager_id,
            "model_revision": self.binding.model_revision,
            "layer_id": self.binding.layer_id,
            "representation": self.binding.representation,
            "source_revision": self.binding.expected_source_revision,
            "source_digest": self.binding.expected_source_digest,
            "requested_expert_ids": selected,
            "materialized_expert_ids": tuple(sorted(materialized)),
            "cache_hit_expert_ids": tuple(sorted(all_cached)),
            "tensor_families": self.binding.tensor_families,
            "logical_bytes_returned": logical_bytes,
            "physical_bytes_observed": UNKNOWN,
            "whole_bank_materialized": False,
            "cache_entries_after": len(self._cache),
            "cache_bytes_after": self._cache_bytes,
            "status": "SLICES_READY",
        }
        receipt = PagerReceipt(schema=RECEIPT_SCHEMA, **receipt_body)
        return PagerLoad(slices=result, receipt=receipt)

    def _validate_slice(self, item: ExpertSlice, *, tensor_key: str, expert_id: int) -> None:
        if item.tensor_key != tensor_key or item.expert_id != expert_id:
            raise PackedExpertPagerError("SLICE_BINDING_MISMATCH")
        if item.source_revision != self.binding.expected_source_revision:
            raise PackedExpertPagerError("SLICE_SOURCE_REVISION_MISMATCH")
        if item.source_digest.lower() != self.binding.expected_source_digest.lower():
            raise PackedExpertPagerError("SLICE_SOURCE_DIGEST_MISMATCH")
        # A first-axis expert slice must retain exactly one row at axis 0.
        if not item.shape or item.shape[0] != 1:
            raise PackedExpertPagerError("SLICE_FIRST_AXIS_INVALID", f"{tensor_key}:{item.shape}")


class InMemoryPackedTensorReader:
    """Deterministic fixture reader which exposes first-axis slices only."""

    def __init__(self, tensors: Mapping[str, Sequence[Any]], *, source_revision: str) -> None:
        self._tensors = {key: tuple(value) for key, value in tensors.items()}
        self._source_revision = _text(source_revision, code="SOURCE_REVISION_REQUIRED")
        self.slice_reads: list[tuple[str, int]] = []
        self.whole_tensor_reads = 0
        self._source_digest = _digest("AURA_IN_MEMORY_PACKED_TENSORS_V1", self._tensors)

    @property
    def source_revision(self) -> str:
        return self._source_revision

    @property
    def source_digest(self) -> str:
        return self._source_digest

    def first_axis_size(self, tensor_key: str) -> int:
        return len(self._tensors[tensor_key])

    def read_expert(self, tensor_key: str, expert_id: int) -> ExpertSlice:
        bank = self._tensors[tensor_key]
        payload = bank[expert_id]
        self.slice_reads.append((tensor_key, expert_id))
        shape = (1,) + _payload_shape(payload)
        nbytes = _logical_nbytes(payload)
        return ExpertSlice(
            tensor_key=tensor_key,
            expert_id=expert_id,
            payload=payload,
            shape=shape,
            nbytes=nbytes,
            source_revision=self.source_revision,
            source_digest=self.source_digest,
        )


class SafetensorsFirstAxisReader:
    """Lazy first-axis reader for one safetensors shard.

    This proves the software access pattern (``get_slice`` rather than
    ``get_tensor``).  It intentionally does not claim exact physical NVMe bytes
    read; filesystem/page-cache instrumentation belongs to the host performance
    receipt.
    """

    def __init__(self, path: str | Path, *, source_revision: str, source_digest: str) -> None:
        self.path = Path(path)
        self._source_revision = _text(source_revision, code="SOURCE_REVISION_REQUIRED")
        digest = _text(source_digest, code="SOURCE_DIGEST_REQUIRED").lower()
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise PackedExpertPagerError("SOURCE_DIGEST_INVALID")
        self._source_digest = digest
        if not self.path.is_file():
            raise PackedExpertPagerError("SAFETENSORS_FILE_MISSING", str(self.path))

    @property
    def source_revision(self) -> str:
        return self._source_revision

    @property
    def source_digest(self) -> str:
        return self._source_digest

    @staticmethod
    def _safe_open():
        try:
            from safetensors import safe_open
        except ImportError as exc:
            raise PackedExpertPagerError("SAFETENSORS_DEPENDENCY_MISSING") from exc
        return safe_open

    def first_axis_size(self, tensor_key: str) -> int:
        safe_open = self._safe_open()
        with safe_open(str(self.path), framework="pt", device="cpu") as handle:
            shape = tuple(handle.get_slice(tensor_key).get_shape())
        if not shape:
            raise PackedExpertPagerError("PACKED_TENSOR_RANK_INVALID", tensor_key)
        return int(shape[0])

    def read_expert(self, tensor_key: str, expert_id: int) -> ExpertSlice:
        safe_open = self._safe_open()
        with safe_open(str(self.path), framework="pt", device="cpu") as handle:
            view = handle.get_slice(tensor_key)
            full_shape = tuple(view.get_shape())
            if not full_shape or expert_id < 0 or expert_id >= full_shape[0]:
                raise IndexError(expert_id)
            payload = view[expert_id : expert_id + 1]
        nbytes = int(payload.numel() * payload.element_size())
        return ExpertSlice(
            tensor_key=tensor_key,
            expert_id=expert_id,
            payload=payload,
            shape=tuple(int(v) for v in payload.shape),
            nbytes=nbytes,
            source_revision=self.source_revision,
            source_digest=self.source_digest,
        )


def _payload_shape(value: Any) -> tuple[int, ...]:
    if isinstance(value, (list, tuple)):
        if not value:
            return (0,)
        child = _payload_shape(value[0])
        for item in value[1:]:
            if _payload_shape(item) != child:
                raise PackedExpertPagerError("FIXTURE_TENSOR_RAGGED")
        return (len(value),) + child
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return ()
    raise PackedExpertPagerError("FIXTURE_TENSOR_VALUE_INVALID")


def _logical_nbytes(value: Any) -> int:
    # The fixture models ordinary float32 values: four bytes per scalar.
    if isinstance(value, (list, tuple)):
        return sum(_logical_nbytes(item) for item in value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return 4
    raise PackedExpertPagerError("FIXTURE_TENSOR_VALUE_INVALID")
