"""AWJ032-GLM53-01A fail-closed packed-expert pager core.

D0 synthetic/reference code only. This module never downloads or imports GLM-5.3,
never opens a real checkpoint by itself, and never grants G2. It establishes the
source-binding and bounded-row-read invariants a real safetensors backend must obey.

Important evidence boundary: ``read_rows`` proves only the pager's caller-facing
bounded-read contract. Physical filesystem/page-cache I/O is UNKNOWN unless the
backend explicitly attests it. The pager must never turn an API shape into a
physical-I/O claim.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from types import MappingProxyType
from typing import Any, Mapping, Protocol, Sequence


UNKNOWN = "UNKNOWN"


class PagerError(RuntimeError):
    """Typed fail-closed pager failure."""


class StaleSourceError(PagerError):
    pass


class SourceBindingError(PagerError):
    pass


class ExpertRangeError(PagerError):
    pass


class WholeBankSelectionForbidden(ExpertRangeError):
    pass


class MissingSliceError(PagerError):
    pass


class WholeTensorReadForbidden(PagerError):
    pass


class SliceBackend(Protocol):
    """Caller-facing contract: bounded first-axis row reads only.

    This protocol deliberately does not claim how a backend satisfies the request
    physically. A backend may optionally implement ``read_evidence()`` to attest
    measured/source-bound physical I/O facts after a successful pager load.
    """

    def read_rows(self, key: str, start: int, end: int) -> Sequence[Any]: ...


@dataclass(frozen=True)
class BackendReadEvidence:
    """Optional backend attestation for physical I/O.

    UNKNOWN is required whenever the backend did not measure a field. Source ranges
    are evidence about requested/observed bounded ranges, not authority to execute.
    """

    physical_bytes_read: int | str = UNKNOWN
    whole_tensor_reads: int | str = UNKNOWN
    read_operations: int | str = UNKNOWN
    source_ranges: tuple[tuple[str, int, int], ...] = ()

    def __post_init__(self) -> None:
        for name in ("physical_bytes_read", "whole_tensor_reads", "read_operations"):
            value = getattr(self, name)
            if value == UNKNOWN:
                continue
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise PagerError(f"invalid backend evidence field {name}={value!r}")
        for item in self.source_ranges:
            if (
                not isinstance(item, tuple)
                or len(item) != 3
                or not isinstance(item[0], str)
                or not item[0]
                or isinstance(item[1], bool)
                or isinstance(item[2], bool)
                or not isinstance(item[1], int)
                or not isinstance(item[2], int)
                or item[1] < 0
                or item[2] <= item[1]
            ):
                raise PagerError(f"invalid backend source range {item!r}")


@dataclass(frozen=True)
class ExpertSourceBinding:
    model_revision: str
    index_digest: str
    layer_id: str
    num_experts: int
    tensor_map: Mapping[str, str]
    scale_map: Mapping[str, str]
    representation: str

    def __post_init__(self) -> None:
        if not self.model_revision or not self.index_digest or not self.layer_id:
            raise SourceBindingError("source identity fields must be non-empty")
        if not isinstance(self.representation, str) or not self.representation:
            raise SourceBindingError("representation must be a non-empty string")
        if isinstance(self.num_experts, bool) or not isinstance(self.num_experts, int) or self.num_experts <= 0:
            raise SourceBindingError("num_experts must be positive")

        # A frozen dataclass is not sufficient when it retains caller-owned mutable
        # dictionaries. Copy then freeze the mappings so validation, digest, and
        # future reads remain bound to one immutable source identity.
        tensor_map = dict(self.tensor_map)
        scale_map = dict(self.scale_map)
        required = {"gate_up", "down"}
        if set(tensor_map) != required:
            raise SourceBindingError(f"tensor_map must contain exactly {sorted(required)}")
        values = list(tensor_map.values()) + list(scale_map.values())
        if not all(isinstance(v, str) and v for v in values):
            raise SourceBindingError("all tensor keys must be non-empty strings")
        if len(set(values)) != len(values):
            raise SourceBindingError("tensor/scale keys must be unambiguous")
        object.__setattr__(self, "tensor_map", MappingProxyType(tensor_map))
        object.__setattr__(self, "scale_map", MappingProxyType(scale_map))

    @property
    def digest(self) -> str:
        payload = {
            "model_revision": self.model_revision,
            "index_digest": self.index_digest,
            "layer_id": self.layer_id,
            "num_experts": self.num_experts,
            "tensor_map": dict(sorted(self.tensor_map.items())),
            "scale_map": dict(sorted(self.scale_map.items())),
            "representation": self.representation,
        }
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PagedExperts:
    expert_ids: tuple[int, ...]
    local_row_by_expert: Mapping[int, int]
    gate_up: tuple[Any, ...]
    down: tuple[Any, ...]
    scale_bundle: Mapping[str, tuple[Any, ...]]
    contiguous_runs: tuple[tuple[int, int], ...]
    binding_digest: str
    read_count: int


@dataclass(frozen=True)
class PagerReceipt:
    schema: str
    binding_digest: str
    layer_id: str
    selected_experts: tuple[int, ...]
    contiguous_runs: tuple[tuple[int, int], ...]
    read_count: int
    physical_bytes_read: int | str
    physical_read_operations: int | str
    whole_tensor_reads: int | str
    backend_evidence_attested: bool
    source_ranges: tuple[tuple[str, int, int], ...]
    g2_admitted: bool = False
    claim_ceiling: str = "SYNTHETIC_PAGER_CORE_ONLY_NO_FLAGSHIP_WEIGHT_OR_RUNTIME_PROOF"


def canonical_expert_ids(expert_ids: Sequence[int], num_experts: int) -> tuple[int, ...]:
    if not expert_ids:
        raise ExpertRangeError("at least one routed expert is required")
    out: set[int] = set()
    for raw in expert_ids:
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise ExpertRangeError(f"expert id must be int, got {raw!r}")
        if raw < 0 or raw >= num_experts:
            raise ExpertRangeError(f"expert id {raw} outside [0,{num_experts})")
        out.add(raw)
    return tuple(sorted(out))


def contiguous_runs(expert_ids: Sequence[int]) -> tuple[tuple[int, int], ...]:
    """Return half-open contiguous first-axis runs for sorted/deduplicated IDs."""
    ids = tuple(expert_ids)
    if not ids:
        return ()
    runs: list[tuple[int, int]] = []
    start = prev = ids[0]
    for current in ids[1:]:
        if current == prev + 1:
            prev = current
            continue
        runs.append((start, prev + 1))
        start = prev = current
    runs.append((start, prev + 1))
    return tuple(runs)


def _backend_evidence(backend: SliceBackend) -> tuple[BackendReadEvidence, bool]:
    provider = getattr(backend, "read_evidence", None)
    if not callable(provider):
        return BackendReadEvidence(), False
    raw = provider()
    if isinstance(raw, BackendReadEvidence):
        return raw, True
    if not isinstance(raw, Mapping):
        raise PagerError("backend read_evidence() must return BackendReadEvidence or a mapping")
    allowed = {"physical_bytes_read", "whole_tensor_reads", "read_operations", "source_ranges"}
    unknown_keys = set(raw) - allowed
    if unknown_keys:
        raise PagerError(f"unknown backend evidence fields: {sorted(unknown_keys)}")
    evidence = BackendReadEvidence(
        physical_bytes_read=raw.get("physical_bytes_read", UNKNOWN),
        whole_tensor_reads=raw.get("whole_tensor_reads", UNKNOWN),
        read_operations=raw.get("read_operations", UNKNOWN),
        source_ranges=tuple(raw.get("source_ranges", ())),
    )
    return evidence, True


class PackedExpertPager:
    """Source-bound first-axis pager for grouped expert tensors.

    The binding is immutable. Each load rechecks the caller's model revision and
    index digest before any backend read, eliminating execution-order/global-state
    inference of layer identity.
    """

    def __init__(self, binding: ExpertSourceBinding, backend: SliceBackend):
        self.binding = binding
        self.backend = backend
        self._last_receipt: PagerReceipt | None = None

    def _assert_current(self, model_revision: str, index_digest: str) -> None:
        if model_revision != self.binding.model_revision:
            raise StaleSourceError("model revision does not match bound source")
        if index_digest != self.binding.index_digest:
            raise StaleSourceError("weight-index digest does not match bound source")

    def load_selected(
        self,
        expert_ids: Sequence[int],
        *,
        model_revision: str,
        index_digest: str,
    ) -> PagedExperts:
        self._assert_current(model_revision, index_digest)
        selected = canonical_expert_ids(expert_ids, self.binding.num_experts)
        if len(selected) == self.binding.num_experts:
            raise WholeBankSelectionForbidden(
                "single-call selection of the complete expert bank is forbidden; "
                "prove all-expert addressability across bounded sparse calls instead"
            )
        runs = contiguous_runs(selected)

        families = dict(self.binding.tensor_map)
        families.update({f"scale:{name}": key for name, key in self.binding.scale_map.items()})
        collected: dict[str, list[Any]] = {name: [] for name in families}
        read_count = 0

        for start, end in runs:
            expected = end - start
            for family, key in families.items():
                rows = tuple(self.backend.read_rows(key, start, end))
                read_count += 1
                if len(rows) != expected:
                    raise MissingSliceError(
                        f"{self.binding.layer_id}:{key}[{start}:{end}] returned {len(rows)} rows; expected {expected}"
                    )
                collected[family].extend(rows)

        if len(collected["gate_up"]) != len(selected) or len(collected["down"]) != len(selected):
            raise MissingSliceError("packed weight families did not return one row per selected expert")

        local = {expert_id: idx for idx, expert_id in enumerate(selected)}
        scales = {
            family.split(":", 1)[1]: tuple(rows)
            for family, rows in collected.items()
            if family.startswith("scale:")
        }
        result = PagedExperts(
            expert_ids=selected,
            local_row_by_expert=local,
            gate_up=tuple(collected["gate_up"]),
            down=tuple(collected["down"]),
            scale_bundle=scales,
            contiguous_runs=runs,
            binding_digest=self.binding.digest,
            read_count=read_count,
        )
        evidence, attested = _backend_evidence(self.backend)
        self._last_receipt = PagerReceipt(
            schema="AuraPackedExpertPagerReceiptV2",
            binding_digest=self.binding.digest,
            layer_id=self.binding.layer_id,
            selected_experts=selected,
            contiguous_runs=runs,
            read_count=read_count,
            physical_bytes_read=evidence.physical_bytes_read,
            physical_read_operations=evidence.read_operations,
            whole_tensor_reads=evidence.whole_tensor_reads,
            backend_evidence_attested=attested,
            source_ranges=evidence.source_ranges,
        )
        return result

    def receipt(self) -> PagerReceipt:
        if self._last_receipt is None:
            raise PagerError("no successful page operation has occurred")
        return self._last_receipt

    def evict(self) -> None:
        # Core holds no tensor cache. A future bounded cache may implement this
        # without weakening source identity or whole-bank prohibitions.
        return None


# --- tiny reference math used only by deterministic synthetic tests -------------------------

def _dot(row: Sequence[float], x: Sequence[float]) -> float:
    if len(row) != len(x):
        raise ValueError("shape mismatch")
    return sum(float(a) * float(b) for a, b in zip(row, x))


def _linear(matrix: Sequence[Sequence[float]], x: Sequence[float]) -> list[float]:
    return [_dot(row, x) for row in matrix]


def _silu(x: float) -> float:
    return x / (1.0 + math.exp(-x))


def expert_forward(
    x: Sequence[float],
    gate_up: Sequence[Sequence[float]],
    down: Sequence[Sequence[float]],
) -> list[float]:
    """Transformers-equivalent gated MLP shape for one tiny synthetic expert."""
    gu = _linear(gate_up, x)
    if len(gu) % 2:
        raise ValueError("gate_up output must divide into gate/up halves")
    half = len(gu) // 2
    hidden = [_silu(gu[i]) * gu[half + i] for i in range(half)]
    return _linear(down, hidden)


def routed_reference(
    x: Sequence[float],
    expert_ids: Sequence[int],
    route_weights: Sequence[float],
    gate_up_bank: Sequence[Any],
    down_bank: Sequence[Any],
) -> list[float]:
    if len(expert_ids) != len(route_weights):
        raise ValueError("route ids/weights length mismatch")
    acc: list[float] | None = None
    for expert_id, weight in zip(expert_ids, route_weights):
        out = expert_forward(x, gate_up_bank[expert_id], down_bank[expert_id])
        if acc is None:
            acc = [0.0] * len(out)
        for i, value in enumerate(out):
            acc[i] += float(weight) * value
    return acc or []


def routed_paged(
    x: Sequence[float],
    expert_ids: Sequence[int],
    route_weights: Sequence[float],
    page: PagedExperts,
) -> list[float]:
    if len(expert_ids) != len(route_weights):
        raise ValueError("route ids/weights length mismatch")
    acc: list[float] | None = None
    for expert_id, weight in zip(expert_ids, route_weights):
        if expert_id not in page.local_row_by_expert:
            raise MissingSliceError(f"expert {expert_id} not present in page")
        row = page.local_row_by_expert[expert_id]
        out = expert_forward(x, page.gate_up[row], page.down[row])
        if acc is None:
            acc = [0.0] * len(out)
        for i, value in enumerate(out):
            acc[i] += float(weight) * value
    return acc or []
