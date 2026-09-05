from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import Enum
from hashlib import sha256
import json
import re
from typing import Any, Sequence

SCHEMA = "AURA-CONTAMINATION-BOUND-FUSED-COST-ADJUDICATOR-v1"
CONTAMINATION_SCHEMA = "AURA-WORKLOAD-CONTAMINATION-RECEIPT-v1"
COST_SCHEMA = "AURA-FUSED-ROUTE-COST-RECEIPT-v1"
CONTAMINATION_PARENT_COMMIT = "b6aca91ce25589cf581c46e4582194529ed90dda"
COST_PARENT_COMMIT = "1833f12c31e89c498235f3a6b5806b8e08036224"
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class AdjudicationError(ValueError):
    pass


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise AdjudicationError("NON_CANONICAL_VALUE") from exc


def digest(value: Any) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


class Decision(str, Enum):
    READY_NONAUTHORIZING = "READY_NONAUTHORIZING"
    HOLD_PARENT_SCHEMA = "HOLD_PARENT_SCHEMA"
    HOLD_PARENT_GENERATION = "HOLD_PARENT_GENERATION"
    HOLD_PARENT_ATTESTATION = "HOLD_PARENT_ATTESTATION"
    HOLD_PARENT_UNVERIFIED = "HOLD_PARENT_UNVERIFIED"
    HOLD_PARENT_STALE = "HOLD_PARENT_STALE"
    HOLD_PARENT_NOT_READY = "HOLD_PARENT_NOT_READY"
    HOLD_PARENT_LINEAGE_COLLISION = "HOLD_PARENT_LINEAGE_COLLISION"
    HOLD_SOURCE_IDENTITY_MISMATCH = "HOLD_SOURCE_IDENTITY_MISMATCH"
    HOLD_BENCHMARK_GENERATION_MISMATCH = "HOLD_BENCHMARK_GENERATION_MISMATCH"
    HOLD_ENVELOPE_BINDING_MISMATCH = "HOLD_ENVELOPE_BINDING_MISMATCH"
    HOLD_AUTHORITY_CEILING = "HOLD_AUTHORITY_CEILING"


@dataclass(frozen=True)
class ParentAttestation:
    role: str
    schema: str
    semantic_commit: str
    result_root: str
    source_identity: str
    benchmark_generation: str
    envelope_identity: str
    verified: bool
    current: bool
    ready_non_authorizing: bool
    truth_authority: bool = False
    effect_authority: bool = False
    gate10: bool = False
    attestation_root: str = ""

    def canonical_without_root(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("attestation_root")
        return data

    def internally_valid(self) -> bool:
        if self.role not in {"WORKLOAD_CONTAMINATION", "FUSED_ROUTE_COST"}:
            return False
        if not isinstance(self.schema, str) or not self.schema:
            return False
        if not _HEX40.fullmatch(self.semantic_commit):
            return False
        if not _HEX64.fullmatch(self.result_root):
            return False
        if not _HEX40.fullmatch(self.source_identity):
            return False
        if not isinstance(self.benchmark_generation, str) or not self.benchmark_generation:
            return False
        if not _HEX64.fullmatch(self.envelope_identity):
            return False
        for value in (
            self.verified,
            self.current,
            self.ready_non_authorizing,
            self.truth_authority,
            self.effect_authority,
            self.gate10,
        ):
            if type(value) is not bool:
                return False
        return self.attestation_root == digest(self.canonical_without_root())


def make_attestation(
    *,
    role: str,
    schema: str,
    semantic_commit: str,
    result_root: str,
    source_identity: str,
    benchmark_generation: str,
    envelope_identity: str,
    verified: bool,
    current: bool,
    ready_non_authorizing: bool,
    truth_authority: bool = False,
    effect_authority: bool = False,
    gate10: bool = False,
) -> ParentAttestation:
    base = ParentAttestation(
        role=role,
        schema=schema,
        semantic_commit=semantic_commit,
        result_root=result_root,
        source_identity=source_identity,
        benchmark_generation=benchmark_generation,
        envelope_identity=envelope_identity,
        verified=verified,
        current=current,
        ready_non_authorizing=ready_non_authorizing,
        truth_authority=truth_authority,
        effect_authority=effect_authority,
        gate10=gate10,
    )
    return replace(base, attestation_root=digest(base.canonical_without_root()))


@dataclass(frozen=True)
class CompositeReceipt:
    schema: str
    decision: Decision
    contamination_parent_commit: str
    cost_parent_commit: str
    contamination_result_root: str
    cost_result_root: str
    contamination_attestation_root: str
    cost_attestation_root: str
    source_identity: str
    benchmark_generation: str
    envelope_identity: str
    parent_binding_root: str
    comparative_cost_ranking_eligible: bool
    truth_authority: bool = False
    effect_authority: bool = False
    gate10: bool = False
    result_root: str = ""

    def canonical_without_result_root(self) -> dict[str, Any]:
        data = asdict(self)
        data["decision"] = self.decision.value
        data.pop("result_root")
        return data


def _receipt(decision: Decision, contamination: ParentAttestation, cost: ParentAttestation) -> CompositeReceipt:
    source_identity = contamination.source_identity if contamination.source_identity == cost.source_identity else ""
    benchmark_generation = contamination.benchmark_generation if contamination.benchmark_generation == cost.benchmark_generation else ""
    envelope_identity = contamination.envelope_identity if contamination.envelope_identity == cost.envelope_identity else ""
    binding_root = digest({
        "contamination": contamination.attestation_root,
        "cost": cost.attestation_root,
        "source_identity": source_identity,
        "benchmark_generation": benchmark_generation,
        "envelope_identity": envelope_identity,
    })
    base = CompositeReceipt(
        schema=SCHEMA,
        decision=decision,
        contamination_parent_commit=contamination.semantic_commit,
        cost_parent_commit=cost.semantic_commit,
        contamination_result_root=contamination.result_root,
        cost_result_root=cost.result_root,
        contamination_attestation_root=contamination.attestation_root,
        cost_attestation_root=cost.attestation_root,
        source_identity=source_identity,
        benchmark_generation=benchmark_generation,
        envelope_identity=envelope_identity,
        parent_binding_root=binding_root,
        comparative_cost_ranking_eligible=decision == Decision.READY_NONAUTHORIZING,
    )
    return replace(base, result_root=digest(base.canonical_without_result_root()))


class ContaminationBoundCostAdjudicator:
    """Composition membrane over two independently verified parent proof surfaces.

    The parent workers remain canonical owners of workload-contamination validity
    and fused route/cost validity. This adapter only checks exact parent generation,
    currentness, D0 authority, and cross-parent comparability bindings.
    """

    def adjudicate(self, contamination: ParentAttestation, cost: ParentAttestation) -> CompositeReceipt:
        if (
            contamination.role != "WORKLOAD_CONTAMINATION"
            or cost.role != "FUSED_ROUTE_COST"
            or contamination.schema != CONTAMINATION_SCHEMA
            or cost.schema != COST_SCHEMA
        ):
            return _receipt(Decision.HOLD_PARENT_SCHEMA, contamination, cost)
        if (
            contamination.semantic_commit != CONTAMINATION_PARENT_COMMIT
            or cost.semantic_commit != COST_PARENT_COMMIT
        ):
            return _receipt(Decision.HOLD_PARENT_GENERATION, contamination, cost)
        if contamination.semantic_commit == cost.semantic_commit:
            return _receipt(Decision.HOLD_PARENT_LINEAGE_COLLISION, contamination, cost)
        if not contamination.internally_valid() or not cost.internally_valid():
            return _receipt(Decision.HOLD_PARENT_ATTESTATION, contamination, cost)
        if not contamination.verified or not cost.verified:
            return _receipt(Decision.HOLD_PARENT_UNVERIFIED, contamination, cost)
        if not contamination.current or not cost.current:
            return _receipt(Decision.HOLD_PARENT_STALE, contamination, cost)
        if not contamination.ready_non_authorizing or not cost.ready_non_authorizing:
            return _receipt(Decision.HOLD_PARENT_NOT_READY, contamination, cost)
        if (
            contamination.truth_authority
            or contamination.effect_authority
            or contamination.gate10
            or cost.truth_authority
            or cost.effect_authority
            or cost.gate10
        ):
            return _receipt(Decision.HOLD_AUTHORITY_CEILING, contamination, cost)
        if contamination.source_identity != cost.source_identity:
            return _receipt(Decision.HOLD_SOURCE_IDENTITY_MISMATCH, contamination, cost)
        if contamination.benchmark_generation != cost.benchmark_generation:
            return _receipt(Decision.HOLD_BENCHMARK_GENERATION_MISMATCH, contamination, cost)
        if contamination.envelope_identity != cost.envelope_identity:
            return _receipt(Decision.HOLD_ENVELOPE_BINDING_MISMATCH, contamination, cost)
        return _receipt(Decision.READY_NONAUTHORIZING, contamination, cost)


def verify_composite_receipt(
    contamination: ParentAttestation,
    cost: ParentAttestation,
    receipt: CompositeReceipt,
) -> bool:
    expected = ContaminationBoundCostAdjudicator().adjudicate(contamination, cost)
    return (
        receipt == expected
        and receipt.result_root == digest(receipt.canonical_without_result_root())
        and receipt.truth_authority is False
        and receipt.effect_authority is False
        and receipt.gate10 is False
    )


def crystalline_admission(omega8: Sequence[int]) -> bool:
    if len(omega8) != 8 or any(type(v) is not int or v not in (0, 1, 2) for v in omega8):
        raise AdjudicationError("INVALID_OMEGA8")
    return tuple(omega8) == (2, 2, 2, 2, 2, 2, 2, 1)


def admission_13d(omega8: Sequence[int], routing5: Sequence[int]) -> bool:
    if len(routing5) != 5 or any(type(v) is not int or v not in (0, 1, 2) for v in routing5):
        raise AdjudicationError("INVALID_ROUTING5")
    return crystalline_admission(omega8)


def valid_pair() -> tuple[ParentAttestation, ParentAttestation]:
    source = "a" * 40
    benchmark = "bench-g1"
    envelope = "e" * 64
    contamination = make_attestation(
        role="WORKLOAD_CONTAMINATION",
        schema=CONTAMINATION_SCHEMA,
        semantic_commit=CONTAMINATION_PARENT_COMMIT,
        result_root="c" * 64,
        source_identity=source,
        benchmark_generation=benchmark,
        envelope_identity=envelope,
        verified=True,
        current=True,
        ready_non_authorizing=True,
    )
    cost = make_attestation(
        role="FUSED_ROUTE_COST",
        schema=COST_SCHEMA,
        semantic_commit=COST_PARENT_COMMIT,
        result_root="d" * 64,
        source_identity=source,
        benchmark_generation=benchmark,
        envelope_identity=envelope,
        verified=True,
        current=True,
        ready_non_authorizing=True,
    )
    return contamination, cost
