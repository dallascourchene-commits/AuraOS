from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from decimal import Decimal
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import subprocess
from typing import Iterable, Sequence

SCHEMA = "AURA-FUSED-ROUTE-COST-RECEIPT-v1"
_HEX40 = re.compile(r"^[0-9a-f]{40}$")

class CostReceiptError(ValueError):
    pass

def _canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")

def _digest(obj) -> str:
    return sha256(_canon(obj)).hexdigest()

def _strict_int(value, name: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise CostReceiptError(f"INVALID_INT:{name}")
    return value

def _finite_number(value, name: str, *, minimum: float = 0.0) -> float:
    if type(value) not in (int, float) or isinstance(value, bool):
        raise CostReceiptError(f"INVALID_NUMBER:{name}")
    out = float(value)
    if not math.isfinite(out) or out < minimum:
        raise CostReceiptError(f"INVALID_NUMBER:{name}")
    return out

def _decimal_number(value, name: str) -> Decimal:
    _finite_number(value, name)
    return Decimal(str(value))

@dataclass(frozen=True)
class RouteEvent:
    sequence: int
    token: int
    layer: int
    experts: tuple[int, ...]
    def canonical(self) -> dict:
        return {"sequence": self.sequence, "token": self.token, "layer": self.layer, "experts": list(self.experts)}

@dataclass(frozen=True)
class TransferCharge:
    transfer_id: str
    sequence: int
    kind: str
    trigger_event_sequence: int
    target_event_sequence: int
    expert_id: int
    bytes_moved: int
    modeled_time_s: float
    modeled_energy_j: float
    def canonical(self) -> dict:
        return asdict(self)

@dataclass(frozen=True)
class CostEnvelope:
    source_head: str
    runtime_generation: str
    hardware_fingerprint: str
    benchmark_generation: str
    cost_model_id: str
    speculative_energy_budget_j: float
    effect_authority: bool = False
    gate10: bool = False
    def canonical(self) -> dict:
        return asdict(self)

@dataclass(frozen=True)
class CostReceipt:
    schema: str
    source_head: str
    envelope_id: str
    event_root: str
    transfer_root: str
    event_count: int
    transfer_count: int
    demand_transfer_count: int
    speculative_transfer_count: int
    total_bytes: int
    demand_bytes: int
    speculative_bytes: int
    total_modeled_time_s: float
    demand_modeled_time_s: float
    speculative_modeled_time_s: float
    total_modeled_energy_j: float
    demand_modeled_energy_j: float
    speculative_modeled_energy_j: float
    speculative_energy_budget_j: float
    speculative_energy_remaining_j: float
    effect_authority: bool
    gate10: bool
    result_root: str
    def canonical_without_result_root(self) -> dict:
        d = asdict(self); d.pop("result_root"); return d
    def canonical(self) -> dict:
        return asdict(self)

def validate_route_events(events: Sequence[RouteEvent]) -> None:
    if not events:
        raise CostReceiptError("EMPTY_EVENT_STREAM")
    for expected, event in enumerate(events, 1):
        if _strict_int(event.sequence, "event.sequence", minimum=1) != expected:
            raise CostReceiptError("NONCONTIGUOUS_EVENT_SEQUENCE")
        _strict_int(event.token, "event.token"); _strict_int(event.layer, "event.layer")
        if not isinstance(event.experts, tuple) or not event.experts:
            raise CostReceiptError("INVALID_EXPERT_GROUP")
        seen = set()
        for expert in event.experts:
            _strict_int(expert, "event.expert")
            if expert in seen:
                raise CostReceiptError("DUPLICATE_EXPERT_IN_FUSED_EVENT")
            seen.add(expert)

def event_root(events: Sequence[RouteEvent]) -> str:
    validate_route_events(events)
    return _digest([e.canonical() for e in events])

def validate_envelope(envelope: CostEnvelope) -> None:
    if not _HEX40.fullmatch(envelope.source_head):
        raise CostReceiptError("INVALID_SOURCE_HEAD")
    for name in ("runtime_generation", "hardware_fingerprint", "benchmark_generation", "cost_model_id"):
        value = getattr(envelope, name)
        if not isinstance(value, str) or not value.strip():
            raise CostReceiptError(f"INVALID_ENVELOPE_FIELD:{name}")
    _finite_number(envelope.speculative_energy_budget_j, "speculative_energy_budget_j")
    if envelope.effect_authority is not False or envelope.gate10 is not False:
        raise CostReceiptError("D0_AUTHORITY_ESCALATION")

def envelope_id(envelope: CostEnvelope) -> str:
    validate_envelope(envelope)
    return _digest(envelope.canonical())

def validate_transfers(events: Sequence[RouteEvent], transfers: Sequence[TransferCharge], envelope: CostEnvelope) -> None:
    validate_route_events(events); validate_envelope(envelope)
    by_sequence = {e.sequence: e for e in events}
    seen_ids: set[str] = set(); speculative_spent = Decimal(0)
    speculative_budget = _decimal_number(envelope.speculative_energy_budget_j, "speculative_energy_budget_j")
    for expected, charge in enumerate(transfers, 1):
        if not isinstance(charge.transfer_id, str) or not charge.transfer_id:
            raise CostReceiptError("INVALID_TRANSFER_ID")
        if charge.transfer_id in seen_ids:
            raise CostReceiptError("DUPLICATE_PHYSICAL_TRANSFER_ID")
        seen_ids.add(charge.transfer_id)
        if _strict_int(charge.sequence, "transfer.sequence", minimum=1) != expected:
            raise CostReceiptError("NONCONTIGUOUS_TRANSFER_SEQUENCE")
        if charge.kind not in {"DEMAND", "SPECULATIVE"}:
            raise CostReceiptError("INVALID_TRANSFER_KIND")
        trigger = _strict_int(charge.trigger_event_sequence, "transfer.trigger", minimum=1)
        target = _strict_int(charge.target_event_sequence, "transfer.target", minimum=1)
        expert = _strict_int(charge.expert_id, "transfer.expert")
        if trigger not in by_sequence or target not in by_sequence:
            raise CostReceiptError("TRANSFER_EVENT_OUT_OF_RANGE")
        if expert not in by_sequence[target].experts:
            raise CostReceiptError("TRANSFER_EXPERT_NOT_IN_TARGET_FUSED_EVENT")
        if charge.kind == "DEMAND" and trigger != target:
            raise CostReceiptError("DEMAND_TRANSFER_MUST_TARGET_CURRENT_EVENT")
        if charge.kind == "SPECULATIVE" and trigger >= target:
            raise CostReceiptError("SPECULATIVE_TRANSFER_MUST_TARGET_FUTURE_EVENT")
        _strict_int(charge.bytes_moved, "transfer.bytes", minimum=1)
        _finite_number(charge.modeled_time_s, "transfer.modeled_time_s")
        energy = _decimal_number(charge.modeled_energy_j, "transfer.modeled_energy_j")
        if charge.kind == "SPECULATIVE":
            speculative_spent += energy
            if speculative_spent > speculative_budget:
                raise CostReceiptError("CUMULATIVE_SPECULATIVE_ENERGY_BUDGET_EXCEEDED")

def transfer_root(events: Sequence[RouteEvent], transfers: Sequence[TransferCharge], envelope: CostEnvelope) -> str:
    validate_transfers(events, transfers, envelope)
    return _digest([t.canonical() for t in transfers])

def _sum_energy_decimal(transfers: Sequence[TransferCharge], kind: str | None = None) -> Decimal:
    return sum(
        (_decimal_number(t.modeled_energy_j, "transfer.modeled_energy_j") for t in transfers if kind is None or t.kind == kind),
        Decimal(0),
    )

def _sum_fields(transfers: Sequence[TransferCharge], kind: str | None = None) -> tuple[int, float, float, int]:
    xs = [t for t in transfers if kind is None or t.kind == kind]
    return (
        sum(t.bytes_moved for t in xs),
        math.fsum(float(t.modeled_time_s) for t in xs),
        float(_sum_energy_decimal(xs)),
        len(xs),
    )

def compile_receipt(events: Sequence[RouteEvent], transfers: Sequence[TransferCharge], envelope: CostEnvelope) -> CostReceipt:
    validate_transfers(events, transfers, envelope)
    total_b, total_t, total_e, total_n = _sum_fields(transfers)
    demand_b, demand_t, demand_e, demand_n = _sum_fields(transfers, "DEMAND")
    spec_b, spec_t, spec_e, spec_n = _sum_fields(transfers, "SPECULATIVE")
    budget_decimal = _decimal_number(envelope.speculative_energy_budget_j, "speculative_energy_budget_j")
    spec_decimal = _sum_energy_decimal(transfers, "SPECULATIVE")
    remaining_decimal = max(Decimal(0), budget_decimal - spec_decimal)
    base = CostReceipt(
        SCHEMA, envelope.source_head, envelope_id(envelope), event_root(events), transfer_root(events, transfers, envelope),
        len(events), total_n, demand_n, spec_n, total_b, demand_b, spec_b, total_t, demand_t, spec_t,
        total_e, demand_e, spec_e, float(envelope.speculative_energy_budget_j),
        float(remaining_decimal), False, False, ""
    )
    return replace(base, result_root=_digest(base.canonical_without_result_root()))

def verify_receipt(events: Sequence[RouteEvent], transfers: Sequence[TransferCharge], envelope: CostEnvelope, receipt: CostReceipt) -> bool:
    if receipt.schema != SCHEMA:
        return False
    try:
        expected = compile_receipt(events, transfers, envelope)
    except CostReceiptError:
        return False
    return receipt == expected and receipt.result_root == _digest(receipt.canonical_without_result_root())

def resolve_clean_git_head(repo_root: str | Path, scoped_paths: Iterable[str] = ()) -> str:
    root = str(Path(repo_root).resolve())
    try:
        head = subprocess.check_output(["git", "-C", root, "rev-parse", "HEAD"], stderr=subprocess.STDOUT, text=True).strip().lower()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise CostReceiptError("GIT_HEAD_UNAVAILABLE") from exc
    if not _HEX40.fullmatch(head):
        raise CostReceiptError("INVALID_GIT_HEAD")
    cmd = ["git", "-C", root, "status", "--porcelain", "--untracked-files=no"]
    paths = tuple(scoped_paths)
    if paths:
        cmd.extend(["--", *paths])
    try:
        dirty = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise CostReceiptError("GIT_STATUS_UNAVAILABLE") from exc
    if dirty.strip():
        raise CostReceiptError("TRACKED_SOURCE_DIRTY")
    return head

def bind_envelope_to_clean_git(repo_root: str | Path, *, runtime_generation: str, hardware_fingerprint: str, benchmark_generation: str, cost_model_id: str, speculative_energy_budget_j: float, scoped_paths: Iterable[str] = ()) -> CostEnvelope:
    return CostEnvelope(resolve_clean_git_head(repo_root, scoped_paths), runtime_generation, hardware_fingerprint, benchmark_generation, cost_model_id, speculative_energy_budget_j)

def crystalline_admission(omega8: Sequence[int]) -> bool:
    if len(omega8) != 8 or any(type(v) is not int or v not in (0, 1, 2) for v in omega8):
        raise CostReceiptError("INVALID_OMEGA8")
    if any(v == 0 for v in omega8):
        return False
    return omega8[7] == 1

def admission_13d(omega8: Sequence[int], routing5: Sequence[int]) -> bool:
    if len(routing5) != 5 or any(type(v) is not int or v not in (0, 1, 2) for v in routing5):
        raise CostReceiptError("INVALID_ROUTING5")
    return crystalline_admission(omega8)
