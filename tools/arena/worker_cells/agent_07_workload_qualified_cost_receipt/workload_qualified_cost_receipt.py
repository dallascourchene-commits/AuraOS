from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import math
import re
from typing import Sequence

SCHEMA = "AURA-WORKLOAD-QUALIFIED-COST-RECEIPT-v1"
_HEX40 = re.compile(r"^[0-9a-f]{40}$")


class QualifiedCostError(ValueError):
    pass


def _canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _digest(obj) -> str:
    return sha256(_canon(obj)).hexdigest()


def _strict_int(value, name: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise QualifiedCostError(f"INVALID_INT:{name}")
    return value


def _strict_bool(value, name: str) -> bool:
    if type(value) is not bool:
        raise QualifiedCostError(f"INVALID_BOOL:{name}")
    return value


def _nonempty(value, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise QualifiedCostError(f"INVALID_STRING:{name}")
    return value


def _decimal(value: str, name: str, *, minimum: Decimal = Decimal("0")) -> Decimal:
    if not isinstance(value, str) or not value:
        raise QualifiedCostError(f"INVALID_DECIMAL:{name}")
    try:
        out = Decimal(value)
    except InvalidOperation as exc:
        raise QualifiedCostError(f"INVALID_DECIMAL:{name}") from exc
    if not out.is_finite() or out < minimum:
        raise QualifiedCostError(f"INVALID_DECIMAL:{name}")
    return out


def _dstr(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


@dataclass(frozen=True)
class WorkloadSample:
    sample_id: str
    category: str
    rendered_prefix: str
    ranking_eligible: bool
    control_group: str | None = None

    def canonical(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class TransferCharge:
    transfer_id: str
    sequence: int
    sample_id: str
    kind: str
    bytes_moved: int

    def canonical(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class CostEnvelope:
    source_head: str
    runtime_generation: str
    hardware_fingerprint: str
    benchmark_generation: str
    joules_per_gb: str
    speculative_energy_budget_j: str
    bytes_per_gb: int = 1_000_000_000
    effect_authority: bool = False
    gate10: bool = False

    def canonical(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class QualifiedCostReceipt:
    schema: str
    source_head: str
    envelope_id: str
    workload_root: str
    transfer_root: str
    ranking_categories: tuple[str, ...]
    ranking_sample_count: int
    control_sample_count: int
    transfer_count: int
    demand_transfer_count: int
    speculative_transfer_count: int
    total_bytes: int
    demand_bytes: int
    speculative_bytes: int
    total_modeled_energy_j: str
    demand_modeled_energy_j: str
    speculative_modeled_energy_j: str
    speculative_energy_budget_j: str
    speculative_energy_remaining_j: str
    policy_ranking_eligible: bool
    effect_authority: bool
    gate10: bool
    result_root: str

    def canonical_without_result_root(self) -> dict:
        d = asdict(self)
        d.pop("result_root")
        return d


def validate_workload(samples: Sequence[WorkloadSample]) -> tuple[str, ...]:
    if not samples:
        raise QualifiedCostError("EMPTY_WORKLOAD")
    seen_ids: set[str] = set()
    ranking_by_prefix: dict[str, set[str]] = {}
    ranking_categories: set[str] = set()
    for sample in samples:
        sid = _nonempty(sample.sample_id, "sample_id")
        if sid in seen_ids:
            raise QualifiedCostError("DUPLICATE_SAMPLE_ID")
        seen_ids.add(sid)
        category = _nonempty(sample.category, "category")
        prefix = _nonempty(sample.rendered_prefix, "rendered_prefix")
        eligible = _strict_bool(sample.ranking_eligible, "ranking_eligible")
        if eligible:
            if sample.control_group is not None:
                raise QualifiedCostError("RANKING_SAMPLE_CANNOT_BE_CONTROL")
            ranking_categories.add(category)
            ranking_by_prefix.setdefault(prefix, set()).add(category)
        else:
            _nonempty(sample.control_group, "control_group")
    if len(ranking_categories) < 2:
        raise QualifiedCostError("NEED_AT_LEAST_TWO_RANKING_CATEGORIES")
    if any(len(categories) > 1 for categories in ranking_by_prefix.values()):
        raise QualifiedCostError("CROSS_CATEGORY_EXACT_PREFIX_COLLISION")
    return tuple(sorted(ranking_categories))


def workload_root(samples: Sequence[WorkloadSample]) -> str:
    validate_workload(samples)
    return _digest([s.canonical() for s in samples])


def validate_envelope(envelope: CostEnvelope) -> tuple[Decimal, Decimal]:
    if not _HEX40.fullmatch(envelope.source_head):
        raise QualifiedCostError("INVALID_SOURCE_HEAD")
    for name in ("runtime_generation", "hardware_fingerprint", "benchmark_generation"):
        _nonempty(getattr(envelope, name), name)
    rate = _decimal(envelope.joules_per_gb, "joules_per_gb")
    budget = _decimal(envelope.speculative_energy_budget_j, "speculative_energy_budget_j")
    _strict_int(envelope.bytes_per_gb, "bytes_per_gb", minimum=1)
    if envelope.effect_authority is not False or envelope.gate10 is not False:
        raise QualifiedCostError("D0_AUTHORITY_ESCALATION")
    return rate, budget


def envelope_id(envelope: CostEnvelope) -> str:
    validate_envelope(envelope)
    return _digest(envelope.canonical())


def validate_transfers(samples: Sequence[WorkloadSample], transfers: Sequence[TransferCharge]) -> None:
    validate_workload(samples)
    sample_ids = {s.sample_id for s in samples}
    seen: set[str] = set()
    for expected, transfer in enumerate(transfers, 1):
        tid = _nonempty(transfer.transfer_id, "transfer_id")
        if tid in seen:
            raise QualifiedCostError("DUPLICATE_PHYSICAL_TRANSFER_ID")
        seen.add(tid)
        if _strict_int(transfer.sequence, "transfer.sequence", minimum=1) != expected:
            raise QualifiedCostError("NONCONTIGUOUS_TRANSFER_SEQUENCE")
        if transfer.sample_id not in sample_ids:
            raise QualifiedCostError("TRANSFER_UNKNOWN_SAMPLE")
        if transfer.kind not in {"DEMAND", "SPECULATIVE"}:
            raise QualifiedCostError("INVALID_TRANSFER_KIND")
        _strict_int(transfer.bytes_moved, "transfer.bytes_moved", minimum=1)


def transfer_root(samples: Sequence[WorkloadSample], transfers: Sequence[TransferCharge]) -> str:
    validate_transfers(samples, transfers)
    return _digest([t.canonical() for t in transfers])


def _byte_sums(transfers: Sequence[TransferCharge]) -> tuple[int, int, int, int, int, int]:
    demand = [t for t in transfers if t.kind == "DEMAND"]
    speculative = [t for t in transfers if t.kind == "SPECULATIVE"]
    demand_bytes = sum(t.bytes_moved for t in demand)
    speculative_bytes = sum(t.bytes_moved for t in speculative)
    return (
        demand_bytes + speculative_bytes,
        demand_bytes,
        speculative_bytes,
        len(transfers),
        len(demand),
        len(speculative),
    )


def energy_from_bytes(byte_count: int, envelope: CostEnvelope) -> Decimal:
    _strict_int(byte_count, "byte_count")
    rate, _ = validate_envelope(envelope)
    return (Decimal(byte_count) * rate) / Decimal(envelope.bytes_per_gb)


def compile_receipt(samples: Sequence[WorkloadSample], transfers: Sequence[TransferCharge], envelope: CostEnvelope) -> QualifiedCostReceipt:
    categories = validate_workload(samples)
    validate_transfers(samples, transfers)
    _, budget = validate_envelope(envelope)
    total_b, demand_b, spec_b, total_n, demand_n, spec_n = _byte_sums(transfers)
    total_e = energy_from_bytes(total_b, envelope)
    demand_e = energy_from_bytes(demand_b, envelope)
    spec_e = energy_from_bytes(spec_b, envelope)
    if spec_e > budget:
        raise QualifiedCostError("CUMULATIVE_SPECULATIVE_ENERGY_BUDGET_EXCEEDED")
    ranking_count = sum(1 for s in samples if s.ranking_eligible)
    control_count = len(samples) - ranking_count
    base = QualifiedCostReceipt(
        SCHEMA,
        envelope.source_head,
        envelope_id(envelope),
        workload_root(samples),
        transfer_root(samples, transfers),
        categories,
        ranking_count,
        control_count,
        total_n,
        demand_n,
        spec_n,
        total_b,
        demand_b,
        spec_b,
        _dstr(total_e),
        _dstr(demand_e),
        _dstr(spec_e),
        _dstr(budget),
        _dstr(budget - spec_e),
        True,
        False,
        False,
        "",
    )
    return replace(base, result_root=_digest(base.canonical_without_result_root()))


def verify_receipt(samples: Sequence[WorkloadSample], transfers: Sequence[TransferCharge], envelope: CostEnvelope, receipt: QualifiedCostReceipt) -> bool:
    if receipt.schema != SCHEMA:
        return False
    try:
        expected = compile_receipt(samples, transfers, envelope)
    except QualifiedCostError:
        return False
    return receipt == expected and receipt.result_root == _digest(receipt.canonical_without_result_root())


def crystalline_admission(omega8: Sequence[int]) -> bool:
    if len(omega8) != 8 or any(type(v) is not int or v not in (0, 1, 2) for v in omega8):
        raise QualifiedCostError("INVALID_OMEGA8")
    if any(v == 0 for v in omega8):
        return False
    return omega8[7] == 1


def admission_13d(omega8: Sequence[int], routing5: Sequence[int]) -> bool:
    if len(routing5) != 5 or any(type(v) is not int or v not in (0, 1, 2) for v in routing5):
        raise QualifiedCostError("INVALID_ROUTING5")
    return crystalline_admission(omega8)
