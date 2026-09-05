from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from itertools import product
import json
import re
from typing import Sequence

SCHEMA_SOURCE = "AURA-RECOMPUTED-SOURCE-RECEIPT-v1"
SCHEMA_TRACE = "AURA-RECOMPUTED-FUSED-TRACE-RECEIPT-v1"
SCHEMA_WORKLOAD = "AURA-RECOMPUTED-WORKLOAD-RECEIPT-v1"
SCHEMA_COST = "AURA-EXACT-CUMULATIVE-COST-RECEIPT-v1"
SCHEMA_COMPOSITE = "AURA-RECOMPUTED-EVIDENCE-COST-ADMISSION-v1"
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class AdmissionError(ValueError):
    pass


def _canon(value) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise AdmissionError("NON_CANONICAL_VALUE") from exc


def _digest(value) -> str:
    return sha256(_canon(value)).hexdigest()


def _nonempty(value, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise AdmissionError(f"INVALID_STRING:{name}")
    return value


def _strict_bool(value, name: str) -> bool:
    if type(value) is not bool:
        raise AdmissionError(f"INVALID_BOOL:{name}")
    return value


def _strict_int(value, name: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise AdmissionError(f"INVALID_INT:{name}")
    return value


def _decimal(value: str, name: str) -> Decimal:
    if not isinstance(value, str) or not value:
        raise AdmissionError(f"INVALID_DECIMAL:{name}")
    try:
        out = Decimal(value)
    except InvalidOperation as exc:
        raise AdmissionError(f"INVALID_DECIMAL:{name}") from exc
    if not out.is_finite() or out < 0:
        raise AdmissionError(f"INVALID_DECIMAL:{name}")
    return out


def _dstr(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


@dataclass(frozen=True)
class SourceEvidence:
    source_head: str
    current_head: str
    runtime_path: str
    runtime_bytes: bytes
    expected_runtime_sha256: str
    source_generation: str
    benchmark_generation: str
    hardware_fingerprint: str


@dataclass(frozen=True)
class SourceReceipt:
    schema: str
    source_head: str
    source_generation: str
    benchmark_generation: str
    hardware_fingerprint: str
    runtime_path_root: str
    runtime_sha256: str
    source_current: bool
    receipt_root: str

    def without_root(self):
        d = asdict(self); d.pop("receipt_root"); return d


@dataclass(frozen=True)
class FusedEvent:
    event_id: str
    sample_id: str
    token_index: int
    layer: int
    native_experts: tuple[int, ...]

    def canonical(self):
        return asdict(self)


@dataclass(frozen=True)
class TraceReceipt:
    schema: str
    source_generation: str
    event_count: int
    sample_count: int
    event_root: str
    sample_event_roots: tuple[tuple[str, str], ...]
    receipt_root: str

    def without_root(self):
        d = asdict(self); d.pop("receipt_root"); return d


@dataclass(frozen=True)
class WorkloadSample:
    sample_id: str
    category: str
    rendered_prefix: str
    source_generation: str
    ranking_eligible: bool
    control_group: str | None = None

    def canonical(self):
        return asdict(self)


@dataclass(frozen=True)
class WorkloadReceipt:
    schema: str
    source_generation: str
    workload_root: str
    trace_root: str
    ranking_categories: tuple[str, ...]
    ranking_sample_count: int
    control_sample_count: int
    receipt_root: str

    def without_root(self):
        d = asdict(self); d.pop("receipt_root"); return d


@dataclass(frozen=True)
class TransferCharge:
    transfer_id: str
    sequence: int
    event_id: str
    kind: str
    bytes_moved: int

    def canonical(self):
        return asdict(self)


@dataclass(frozen=True)
class CostEvidence:
    joules_per_gb: str
    speculative_budget_j: str
    bytes_per_gb: int
    transfers: tuple[TransferCharge, ...]


@dataclass(frozen=True)
class CostReceipt:
    schema: str
    trace_root: str
    transfer_root: str
    transfer_count: int
    demand_transfer_count: int
    speculative_transfer_count: int
    total_bytes: int
    demand_bytes: int
    speculative_bytes: int
    total_modeled_energy_j: str
    demand_modeled_energy_j: str
    speculative_modeled_energy_j: str
    speculative_budget_j: str
    speculative_remaining_j: str
    receipt_root: str

    def without_root(self):
        d = asdict(self); d.pop("receipt_root"); return d


@dataclass(frozen=True)
class CompositeReceipt:
    schema: str
    source_receipt_root: str
    trace_receipt_root: str
    workload_receipt_root: str
    cost_receipt_root: str
    source_head: str
    runtime_sha256: str
    ranking_categories: tuple[str, ...]
    total_bytes: int
    speculative_bytes: int
    total_modeled_energy_j: str
    speculative_modeled_energy_j: str
    efficiency_credit: bool
    effect_authority: bool
    gate10: bool
    result_root: str

    def without_root(self):
        d = asdict(self); d.pop("result_root"); return d


def compile_source(e: SourceEvidence) -> SourceReceipt:
    if not isinstance(e, SourceEvidence):
        raise AdmissionError("SOURCE_EVIDENCE_REQUIRED")
    if not _HEX40.fullmatch(_nonempty(e.source_head, "source_head")):
        raise AdmissionError("INVALID_SOURCE_HEAD")
    if not _HEX40.fullmatch(_nonempty(e.current_head, "current_head")):
        raise AdmissionError("INVALID_CURRENT_HEAD")
    _nonempty(e.runtime_path, "runtime_path")
    _nonempty(e.source_generation, "source_generation")
    _nonempty(e.benchmark_generation, "benchmark_generation")
    _nonempty(e.hardware_fingerprint, "hardware_fingerprint")
    if not isinstance(e.runtime_bytes, bytes) or not e.runtime_bytes:
        raise AdmissionError("RUNTIME_BYTES_REQUIRED")
    if not _HEX64.fullmatch(_nonempty(e.expected_runtime_sha256, "expected_runtime_sha256")):
        raise AdmissionError("INVALID_EXPECTED_RUNTIME_SHA256")
    runtime_sha = sha256(e.runtime_bytes).hexdigest()
    if runtime_sha != e.expected_runtime_sha256:
        raise AdmissionError("RUNTIME_SOURCE_DIGEST_MISMATCH")
    if e.source_head != e.current_head:
        raise AdmissionError("STALE_SOURCE_HEAD")
    base = SourceReceipt(
        SCHEMA_SOURCE, e.source_head, e.source_generation, e.benchmark_generation,
        e.hardware_fingerprint, _digest({"runtime_path": e.runtime_path}), runtime_sha,
        True, ""
    )
    return replace(base, receipt_root=_digest(base.without_root()))


def compile_trace(events: Sequence[FusedEvent], source: SourceReceipt) -> TraceReceipt:
    if source.schema != SCHEMA_SOURCE or not source.source_current:
        raise AdmissionError("VALID_SOURCE_RECEIPT_REQUIRED")
    if not events:
        raise AdmissionError("EMPTY_FUSED_TRACE")
    seen_ids: set[str] = set(); seen_slots: set[tuple[str, int, int]] = set()
    by_sample: dict[str, list[FusedEvent]] = {}
    for event in events:
        if type(event) is not FusedEvent:
            raise AdmissionError("INVALID_FUSED_EVENT_TYPE")
        eid = _nonempty(event.event_id, "event_id")
        sid = _nonempty(event.sample_id, "sample_id")
        if eid in seen_ids:
            raise AdmissionError("DUPLICATE_EVENT_ID")
        seen_ids.add(eid)
        token = _strict_int(event.token_index, "token_index")
        layer = _strict_int(event.layer, "layer")
        slot = (sid, token, layer)
        if slot in seen_slots:
            raise AdmissionError("FUSED_EVENT_SLOT_SPLIT_OR_DUPLICATED")
        seen_slots.add(slot)
        if not isinstance(event.native_experts, tuple) or not event.native_experts:
            raise AdmissionError("NATIVE_EXPERT_TUPLE_REQUIRED")
        if any(type(x) is not int or x < 0 for x in event.native_experts):
            raise AdmissionError("INVALID_NATIVE_EXPERT")
        if len(set(event.native_experts)) != len(event.native_experts):
            raise AdmissionError("DUPLICATE_NATIVE_EXPERT")
        by_sample.setdefault(sid, []).append(event)
    ordered = sorted(events, key=lambda x: (x.sample_id, x.token_index, x.layer, x.event_id))
    event_root = _digest([e.canonical() for e in ordered])
    sample_roots = tuple((sid, _digest([e.canonical() for e in sorted(xs, key=lambda x:(x.token_index,x.layer,x.event_id))])) for sid, xs in sorted(by_sample.items()))
    base = TraceReceipt(SCHEMA_TRACE, source.source_generation, len(events), len(by_sample), event_root, sample_roots, "")
    return replace(base, receipt_root=_digest(base.without_root()))


def compile_workload(samples: Sequence[WorkloadSample], trace: TraceReceipt, source: SourceReceipt) -> WorkloadReceipt:
    if trace.schema != SCHEMA_TRACE or source.schema != SCHEMA_SOURCE:
        raise AdmissionError("PARENT_RECEIPTS_REQUIRED")
    if trace.source_generation != source.source_generation:
        raise AdmissionError("TRACE_SOURCE_GENERATION_MISMATCH")
    if not samples:
        raise AdmissionError("EMPTY_WORKLOAD")
    traced_samples = {sid for sid, _ in trace.sample_event_roots}
    seen: set[str] = set(); ranking_categories: set[str] = set(); by_prefix: dict[str, set[str]] = {}
    for sample in samples:
        if type(sample) is not WorkloadSample:
            raise AdmissionError("INVALID_WORKLOAD_SAMPLE_TYPE")
        sid = _nonempty(sample.sample_id, "sample_id")
        if sid in seen: raise AdmissionError("DUPLICATE_SAMPLE_ID")
        seen.add(sid)
        if sid not in traced_samples: raise AdmissionError("WORKLOAD_SAMPLE_MISSING_TRACE")
        if sample.source_generation != source.source_generation: raise AdmissionError("WORKLOAD_SOURCE_GENERATION_MISMATCH")
        category = _nonempty(sample.category, "category")
        prefix = _nonempty(sample.rendered_prefix, "rendered_prefix")
        eligible = _strict_bool(sample.ranking_eligible, "ranking_eligible")
        if eligible:
            if sample.control_group is not None: raise AdmissionError("RANKING_SAMPLE_CANNOT_BE_CONTROL")
            ranking_categories.add(category)
            by_prefix.setdefault(prefix, set()).add(category)
        else:
            _nonempty(sample.control_group, "control_group")
    if traced_samples - seen:
        raise AdmissionError("TRACE_HAS_UNDECLARED_WORKLOAD_SAMPLE")
    if len(ranking_categories) < 2:
        raise AdmissionError("NEED_AT_LEAST_TWO_RANKING_CATEGORIES")
    if any(len(categories) > 1 for categories in by_prefix.values()):
        raise AdmissionError("CROSS_CATEGORY_EXACT_PREFIX_COLLISION")
    ordered = sorted(samples, key=lambda s:s.sample_id)
    base = WorkloadReceipt(
        SCHEMA_WORKLOAD, source.source_generation, _digest([s.canonical() for s in ordered]),
        trace.event_root, tuple(sorted(ranking_categories)),
        sum(1 for s in samples if s.ranking_eligible),
        sum(1 for s in samples if not s.ranking_eligible), ""
    )
    return replace(base, receipt_root=_digest(base.without_root()))


def compile_cost(evidence: CostEvidence, events: Sequence[FusedEvent], source: SourceReceipt, trace: TraceReceipt) -> CostReceipt:
    if type(evidence) is not CostEvidence:
        raise AdmissionError("COST_EVIDENCE_REQUIRED")
    if trace.schema != SCHEMA_TRACE or source.schema != SCHEMA_SOURCE:
        raise AdmissionError("VALID_TRACE_SOURCE_RECEIPTS_REQUIRED")
    # A lower-level cost receipt is nonauthorizing, but it still may not trust an
    # opaque trace root. Recompute the fused trace from raw events and require the
    # supplied parent receipt to be byte-for-byte identical before charging it.
    recomputed_trace = compile_trace(events, source)
    if recomputed_trace != trace:
        raise AdmissionError("TRACE_RECEIPT_RECOMPUTE_MISMATCH")
    event_ids = {event.event_id for event in events}
    rate = _decimal(evidence.joules_per_gb, "joules_per_gb")
    budget = _decimal(evidence.speculative_budget_j, "speculative_budget_j")
    bpg = _strict_int(evidence.bytes_per_gb, "bytes_per_gb", minimum=1)
    seen: set[str] = set(); expected_seq = 1; demand_b = spec_b = 0; demand_n = spec_n = 0
    for t in evidence.transfers:
        if type(t) is not TransferCharge: raise AdmissionError("INVALID_TRANSFER_TYPE")
        tid = _nonempty(t.transfer_id, "transfer_id")
        if tid in seen: raise AdmissionError("DUPLICATE_PHYSICAL_TRANSFER_ID")
        seen.add(tid)
        if _strict_int(t.sequence, "transfer.sequence", minimum=1) != expected_seq:
            raise AdmissionError("NONCONTIGUOUS_TRANSFER_SEQUENCE")
        expected_seq += 1
        event_id = _nonempty(t.event_id, "transfer.event_id")
        if event_id not in event_ids:
            raise AdmissionError("TRANSFER_EVENT_NOT_IN_FUSED_TRACE")
        n = _strict_int(t.bytes_moved, "transfer.bytes_moved", minimum=1)
        if t.kind == "DEMAND": demand_b += n; demand_n += 1
        elif t.kind == "SPECULATIVE": spec_b += n; spec_n += 1
        else: raise AdmissionError("INVALID_TRANSFER_KIND")
    total_b = demand_b + spec_b
    total_e = Decimal(total_b) * rate / Decimal(bpg)
    demand_e = Decimal(demand_b) * rate / Decimal(bpg)
    spec_e = Decimal(spec_b) * rate / Decimal(bpg)
    if spec_e > budget: raise AdmissionError("CUMULATIVE_SPECULATIVE_ENERGY_BUDGET_EXCEEDED")
    base = CostReceipt(
        SCHEMA_COST, trace.event_root, _digest([t.canonical() for t in evidence.transfers]),
        len(evidence.transfers), demand_n, spec_n, total_b, demand_b, spec_b,
        _dstr(total_e), _dstr(demand_e), _dstr(spec_e), _dstr(budget), _dstr(budget-spec_e), ""
    )
    return replace(base, receipt_root=_digest(base.without_root()))


def compile_composite(source_evidence: SourceEvidence, events: Sequence[FusedEvent], samples: Sequence[WorkloadSample], cost_evidence: CostEvidence) -> CompositeReceipt:
    source = compile_source(source_evidence)
    trace = compile_trace(events, source)
    workload = compile_workload(samples, trace, source)
    cost = compile_cost(cost_evidence, events, source, trace)
    if workload.trace_root != cost.trace_root or workload.trace_root != trace.event_root:
        raise AdmissionError("PARENT_TRACE_ROOT_MISMATCH")
    base = CompositeReceipt(
        SCHEMA_COMPOSITE, source.receipt_root, trace.receipt_root, workload.receipt_root, cost.receipt_root,
        source.source_head, source.runtime_sha256, workload.ranking_categories,
        cost.total_bytes, cost.speculative_bytes, cost.total_modeled_energy_j, cost.speculative_modeled_energy_j,
        True, False, False, ""
    )
    return replace(base, result_root=_digest(base.without_root()))


def verify_composite(source_evidence, events, samples, cost_evidence, receipt: CompositeReceipt) -> bool:
    if type(receipt) is not CompositeReceipt or receipt.schema != SCHEMA_COMPOSITE:
        return False
    try:
        expected = compile_composite(source_evidence, events, samples, cost_evidence)
    except AdmissionError:
        return False
    return receipt == expected and receipt.result_root == _digest(receipt.without_root()) and receipt.effect_authority is False and receipt.gate10 is False


AXES8 = ("source_identity","currentness","fused_trace","workload_integrity","transfer_binding","exact_cumulative_cost","composition","effect_ceiling")

def classify8(state: Sequence[int]) -> str:
    if len(state) != 8 or any(type(v) is not int or v not in (0,1,2) for v in state):
        raise AdmissionError("INVALID_OMEGA8")
    if any(v == 0 for v in state[:7]) or state[7] == 0:
        return "HOLD_HARD_INVALID"
    if any(v == 1 for v in state[:7]):
        return "HOLD_UNRESOLVED"
    if state[7] == 2:
        return "HOLD_AUTHORITY_WIDENING"
    return "ADMIT_D0_RECOMPUTED_EVIDENCE"


def classify13(state: Sequence[int]) -> str:
    if len(state) != 13 or any(type(v) is not int or v not in (0,1,2) for v in state):
        raise AdmissionError("INVALID_13D")
    core = classify8(state[:8])
    if core != "ADMIT_D0_RECOMPUTED_EVIDENCE":
        return core
    observer, known_at, runtime_env, resource_env, k27_reopen = state[8:]
    if 0 in (observer, known_at, runtime_env, resource_env, k27_reopen):
        return "HOLD_TRAILING_CONTEXT_INVALID"
    if 1 in (observer, known_at, runtime_env, resource_env, k27_reopen):
        return "HOLD_TRAILING_CONTEXT_UNRESOLVED"
    return core


def exhaustive8() -> dict[str,int]:
    counts: dict[str,int] = {}
    for s in product(range(3), repeat=8):
        d=classify8(s); counts[d]=counts.get(d,0)+1
    return counts
