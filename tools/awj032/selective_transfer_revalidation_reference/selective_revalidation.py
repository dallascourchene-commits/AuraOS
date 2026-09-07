from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import FrozenSet, Iterable, Optional


class Decision(str, Enum):
    PLAN_ELIGIBLE_D0 = "PLAN_ELIGIBLE_D0"
    REPROOF_REQUIRED = "REPROOF_REQUIRED"
    ABSTAIN_STALE_ESTIMATE = "ABSTAIN_STALE_ESTIMATE"
    ABSTAIN_LOW_CONFIDENCE = "ABSTAIN_LOW_CONFIDENCE"
    ABSTAIN_NONPOSITIVE_MARGIN = "ABSTAIN_NONPOSITIVE_MARGIN"
    ABSTAIN_ENERGY_DEBT = "ABSTAIN_ENERGY_DEBT"
    HOLD_AUTHORITY = "HOLD_AUTHORITY"


@dataclass(frozen=True)
class CurrentnessState:
    model_source_rev: str
    airllm_source_rev: str
    topology_rev: str
    tokenizer_rev: str
    runtime_rev: str
    adapter_rev: str
    router_rev: str
    pager_rev: str
    calibration_rev: str
    cost_model_rev: str
    authority_epoch: str
    gate_state: str

    def x12(self) -> tuple[str, ...]:
        return (
            self.model_source_rev,
            self.airllm_source_rev,
            self.topology_rev,
            self.tokenizer_rev,
            self.runtime_rev,
            self.adapter_rev,
            self.router_rev,
            self.pager_rev,
            self.calibration_rev,
            self.cost_model_rev,
            self.authority_epoch,
            self.gate_state,
        )


@dataclass(frozen=True)
class EvidenceLeaf:
    name: str
    dependencies: FrozenSet[str]


@dataclass(frozen=True)
class TransferEstimate:
    model_source_rev: str
    topology_rev: str
    calibration_rev: str
    cost_model_rev: str
    p_hit: float
    miss_stall_seconds: float
    logical_bytes: int
    effective_storage_bytes_per_second: float
    eviction_penalty_seconds: float = 0.0
    rework_penalty_seconds: float = 0.0
    energy_joules: Optional[float] = None


@dataclass(frozen=True)
class RevalidationReceipt:
    changed_dimensions: tuple[str, ...]
    reproof_leaves: tuple[str, ...]
    expected_latency_value_seconds: float
    planning_latency_cost_seconds: float
    expected_latency_margin_seconds: float
    decision: Decision
    y13: tuple[str, ...]
    k27: tuple[int, int, int]
    claim_ceiling: str = "D0_NONPROMOTING"


STATE_FIELDS = (
    "model_source_rev",
    "airllm_source_rev",
    "topology_rev",
    "tokenizer_rev",
    "runtime_rev",
    "adapter_rev",
    "router_rev",
    "pager_rev",
    "calibration_rev",
    "cost_model_rev",
    "authority_epoch",
    "gate_state",
)

ESTIMATE_IDENTITY_FIELDS = (
    "model_source_rev",
    "topology_rev",
    "calibration_rev",
    "cost_model_rev",
)


def _hash(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def changed_dimensions(previous: CurrentnessState, current: CurrentnessState) -> tuple[str, ...]:
    return tuple(name for name in STATE_FIELDS if getattr(previous, name) != getattr(current, name))


def selective_reproof(changed: Iterable[str], leaves: Iterable[EvidenceLeaf]) -> tuple[str, ...]:
    changed_set = frozenset(changed)
    return tuple(sorted(leaf.name for leaf in leaves if leaf.dependencies & changed_set))


def _estimate_matches_current(estimate: TransferEstimate, current: CurrentnessState) -> bool:
    return all(getattr(estimate, name) == getattr(current, name) for name in ESTIMATE_IDENTITY_FIELDS)


def _costs(estimate: TransferEstimate) -> tuple[float, float, float]:
    if not 0.0 <= estimate.p_hit <= 1.0:
        raise ValueError("p_hit must be in [0,1]")
    if estimate.miss_stall_seconds < 0.0 or estimate.logical_bytes < 0:
        raise ValueError("stall time and logical bytes must be nonnegative")
    if estimate.effective_storage_bytes_per_second <= 0.0:
        raise ValueError("effective storage bandwidth must be positive")
    if estimate.eviction_penalty_seconds < 0.0 or estimate.rework_penalty_seconds < 0.0:
        raise ValueError("penalties must be nonnegative")
    value = estimate.p_hit * estimate.miss_stall_seconds
    cost = (
        estimate.logical_bytes / estimate.effective_storage_bytes_per_second
        + estimate.eviction_penalty_seconds
        + estimate.rework_penalty_seconds
    )
    return value, cost, value - cost


def _k27(current_ok: bool, estimate_ok: bool, economics_ok: bool) -> tuple[int, int, int]:
    # Diagnostic navigation coordinate only; it never grants execution authority.
    return tuple(1 if x else -1 for x in (current_ok, estimate_ok, economics_ok))


def revalidate(
    previous: CurrentnessState,
    current: CurrentnessState,
    estimate: TransferEstimate,
    leaves: Iterable[EvidenceLeaf],
    *,
    min_hit_probability: float = 0.50,
    energy_budget_joules: Optional[float] = None,
) -> RevalidationReceipt:
    changed = changed_dimensions(previous, current)
    reproof = selective_reproof(changed, leaves)
    value, cost, margin = _costs(estimate)
    estimate_ok = _estimate_matches_current(estimate, current)
    current_ok = not any(not getattr(current, name) for name in STATE_FIELDS)
    economics_ok = estimate.p_hit >= min_hit_probability and margin > 0.0

    if not current_ok or current.gate_state != "NO_GATE10" or current.authority_epoch != "D0_NONPROMOTING":
        decision = Decision.HOLD_AUTHORITY
    elif not estimate_ok:
        decision = Decision.ABSTAIN_STALE_ESTIMATE
    elif reproof:
        decision = Decision.REPROOF_REQUIRED
    elif estimate.p_hit < min_hit_probability:
        decision = Decision.ABSTAIN_LOW_CONFIDENCE
    elif margin <= 0.0:
        decision = Decision.ABSTAIN_NONPOSITIVE_MARGIN
    elif energy_budget_joules is not None and (
        estimate.energy_joules is None or estimate.energy_joules > energy_budget_joules
    ):
        decision = Decision.ABSTAIN_ENERGY_DEBT
    else:
        decision = Decision.PLAN_ELIGIBLE_D0

    operation_root = _hash({
        "previous": previous.x12(),
        "current": current.x12(),
        "changed": changed,
        "reproof": reproof,
        "estimate": estimate.__dict__,
        "min_hit_probability": min_hit_probability,
        "energy_budget_joules": energy_budget_joules,
        "decision": decision.value,
    })
    # 13D = X12 current consequence state + derived W0 witness.
    y13 = current.x12() + (_hash({"x12": current.x12(), "operation_root": operation_root}),)
    return RevalidationReceipt(
        changed_dimensions=changed,
        reproof_leaves=reproof,
        expected_latency_value_seconds=value,
        planning_latency_cost_seconds=cost,
        expected_latency_margin_seconds=margin,
        decision=decision,
        y13=y13,
        k27=_k27(current_ok, estimate_ok, economics_ok),
    )
