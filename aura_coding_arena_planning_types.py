"""P7 immutable contracts for Coding Arena Planning Board shadow evidence."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from aura_event_contracts import canonical_json, stable_digest
from aura_planning_board import (
    ActionContinuityEvidence,
    BoardContinuityReport,
    PlanningBoard,
)

CODING_ARENA_PLANNING_VERSION = "AURA_CODING_ARENA_PLANNING_P7"
CODING_ARENA_COMPATIBILITY_VERSION = "AURA_CODING_ARENA_COMPATIBILITY_P7"
CODING_ARENA_BENCHMARK_VERSION = "AURA_CODING_ARENA_BENCHMARK_P7"


class CodingArenaCompatibilityStatus(str, Enum):
    VERIFIED_SHADOW = "VERIFIED_SHADOW"
    BLOCKED_LEGACY = "BLOCKED_LEGACY"
    MISMATCHED = "MISMATCHED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class CodingArenaCompatibilityFinding:
    code: str
    message: str
    task_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "task_id": self.task_id,
        }


@dataclass(frozen=True)
class CodingArenaActionMapping:
    task_id: str
    action_id: str
    target_file: str | None
    target_symbol: str | None
    expected_output: str
    route: str
    act_digest: str
    grounding_digest: str
    route_digest: str
    lease_digest: str
    boundary_digest: str
    evidence_refs: tuple[str, ...]
    verifier_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "action_id": self.action_id,
            "target_file": self.target_file,
            "target_symbol": self.target_symbol,
            "expected_output": self.expected_output,
            "route": self.route,
            "act_digest": self.act_digest,
            "grounding_digest": self.grounding_digest,
            "route_digest": self.route_digest,
            "lease_digest": self.lease_digest,
            "boundary_digest": self.boundary_digest,
            "evidence_refs": list(self.evidence_refs),
            "verifier_ids": list(self.verifier_ids),
        }


@dataclass(frozen=True)
class CodingArenaCompatibilityReport:
    version: str
    status: CodingArenaCompatibilityStatus
    plan_phase_hash: str | None
    legacy_plan_digest: str | None
    legacy_arena_digest: str | None
    legacy_shadow_digest: str | None
    board_digest: str | None
    task_count: int
    mapped_action_count: int
    task_order_preserved: bool
    exact_legacy_preserved: bool
    legacy_mutated: bool
    authority_changed: bool
    proposal_only: bool
    legacy_ready_for_incubator: bool | None
    legacy_shadow_gate: str | None
    legacy_routes: tuple[str, ...]
    highest_contiguous_level: str | None
    continuity_complete: bool
    findings: tuple[CodingArenaCompatibilityFinding, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "status": self.status.value,
            "plan_phase_hash": self.plan_phase_hash,
            "legacy_plan_digest": self.legacy_plan_digest,
            "legacy_arena_digest": self.legacy_arena_digest,
            "legacy_shadow_digest": self.legacy_shadow_digest,
            "board_digest": self.board_digest,
            "task_count": self.task_count,
            "mapped_action_count": self.mapped_action_count,
            "task_order_preserved": self.task_order_preserved,
            "exact_legacy_preserved": self.exact_legacy_preserved,
            "legacy_mutated": self.legacy_mutated,
            "authority_changed": self.authority_changed,
            "proposal_only": self.proposal_only,
            "legacy_ready_for_incubator": self.legacy_ready_for_incubator,
            "legacy_shadow_gate": self.legacy_shadow_gate,
            "legacy_routes": list(self.legacy_routes),
            "highest_contiguous_level": self.highest_contiguous_level,
            "continuity_complete": self.continuity_complete,
            "findings": [item.to_dict() for item in self.findings],
        }

    @property
    def digest(self) -> str:
        return stable_digest(self.to_dict())


@dataclass(frozen=True)
class CodingArenaPlanningInspection:
    report: CodingArenaCompatibilityReport
    board: PlanningBoard | None = None
    continuity: BoardContinuityReport | None = None
    action_evidence: tuple[ActionContinuityEvidence, ...] = ()
    mappings: tuple[CodingArenaActionMapping, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "report": self.report.to_dict(),
            "board": self.board.to_dict() if self.board is not None else None,
            "continuity": self.continuity.to_dict() if self.continuity is not None else None,
            "action_evidence": [item.to_dict() for item in self.action_evidence],
            "mappings": [item.to_dict() for item in self.mappings],
        }

    @property
    def digest(self) -> str:
        return stable_digest(self.to_dict())


@dataclass(frozen=True)
class CodingArenaBenchmarkCase:
    case_id: str
    plan: dict[str, Any]
    grounding: tuple[dict[str, Any], ...]
    shadow_report: dict[str, Any]
    arena: dict[str, Any]
    expected_status: CodingArenaCompatibilityStatus

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "plan": self.plan,
            "grounding": list(self.grounding),
            "shadow_report": self.shadow_report,
            "arena": self.arena,
            "expected_status": self.expected_status.value,
        }


@dataclass(frozen=True)
class CodingArenaBenchmarkCaseResult:
    case_id: str
    expected_status: CodingArenaCompatibilityStatus
    observed_status: CodingArenaCompatibilityStatus
    passed: bool
    task_count: int
    mapped_action_count: int
    deterministic: bool
    task_order_preserved: bool
    exact_legacy_preserved: bool
    legacy_mutated: bool
    authority_changed: bool
    proposal_only: bool
    verifier_declaration_rate: float
    baseline_bytes: int
    candidate_bytes: int
    baseline_token_proxy: int
    candidate_token_proxy: int
    overhead_ratio: float
    board_digest: str | None
    inspection_digest: str
    finding_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "expected_status": self.expected_status.value,
            "observed_status": self.observed_status.value,
            "passed": self.passed,
            "task_count": self.task_count,
            "mapped_action_count": self.mapped_action_count,
            "deterministic": self.deterministic,
            "task_order_preserved": self.task_order_preserved,
            "exact_legacy_preserved": self.exact_legacy_preserved,
            "legacy_mutated": self.legacy_mutated,
            "authority_changed": self.authority_changed,
            "proposal_only": self.proposal_only,
            "verifier_declaration_rate": self.verifier_declaration_rate,
            "baseline_bytes": self.baseline_bytes,
            "candidate_bytes": self.candidate_bytes,
            "baseline_token_proxy": self.baseline_token_proxy,
            "candidate_token_proxy": self.candidate_token_proxy,
            "overhead_ratio": self.overhead_ratio,
            "board_digest": self.board_digest,
            "inspection_digest": self.inspection_digest,
            "finding_codes": list(self.finding_codes),
        }


@dataclass(frozen=True)
class CodingArenaBenchmarkReport:
    version: str
    measurement_class: str
    repeats: int
    total_cases: int
    passed_cases: int
    total_tasks: int
    mapped_actions: int
    action_coverage: float
    deterministic_case_rate: float
    order_preservation_rate: float
    verifier_declaration_rate: float
    mutation_drift_count: int
    authority_drift_count: int
    identifier_collision_count: int
    baseline_bytes: int
    candidate_bytes: int
    baseline_token_proxy: int
    candidate_token_proxy: int
    overhead_ratio: float
    gate_passed: bool
    cases: tuple[CodingArenaBenchmarkCaseResult, ...]
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "measurement_class": self.measurement_class,
            "repeats": self.repeats,
            "total_cases": self.total_cases,
            "passed_cases": self.passed_cases,
            "total_tasks": self.total_tasks,
            "mapped_actions": self.mapped_actions,
            "action_coverage": self.action_coverage,
            "deterministic_case_rate": self.deterministic_case_rate,
            "order_preservation_rate": self.order_preservation_rate,
            "verifier_declaration_rate": self.verifier_declaration_rate,
            "mutation_drift_count": self.mutation_drift_count,
            "authority_drift_count": self.authority_drift_count,
            "identifier_collision_count": self.identifier_collision_count,
            "baseline_bytes": self.baseline_bytes,
            "candidate_bytes": self.candidate_bytes,
            "baseline_token_proxy": self.baseline_token_proxy,
            "candidate_token_proxy": self.candidate_token_proxy,
            "overhead_ratio": self.overhead_ratio,
            "gate_passed": self.gate_passed,
            "cases": [item.to_dict() for item in self.cases],
            "limitations": list(self.limitations),
        }

    @property
    def digest(self) -> str:
        return stable_digest(self.to_dict())

    def to_json(self) -> str:
        return canonical_json(self.to_dict())
