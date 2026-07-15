"""P7 immutable contracts for Coding Arena Planning Board shadow evidence."""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import string
from typing import Any

from aura_event_contracts import canonical_json, stable_digest
from aura_planning_board import (
    ActionContinuityEvidence,
    AuthorityRequirement,
    BoardContinuityReport,
    PlanningBoard,
)

CODING_ARENA_PLANNING_VERSION = "AURA_CODING_ARENA_PLANNING_P7"
CODING_ARENA_COMPATIBILITY_VERSION = "AURA_CODING_ARENA_COMPATIBILITY_P7"
CODING_ARENA_BENCHMARK_VERSION = "AURA_CODING_ARENA_BENCHMARK_P7"
_PATCH_OUTPUT_MODES = frozenset({"PATCH", "UNIFIED_DIFF", "JSON_EDIT_PLAN", "PYTHON"})
_HEX = frozenset(string.hexdigits)


class CodingArenaCompatibilityStatus(str, Enum):
    VERIFIED_SHADOW = "VERIFIED_SHADOW"
    BLOCKED_LEGACY = "BLOCKED_LEGACY"
    MISMATCHED = "MISMATCHED"
    UNAVAILABLE = "UNAVAILABLE"


def _required_text(value: Any, field_name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _optional_text(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if type(value) is not str:
        raise ValueError(f"{field_name} must be a string or null")
    stripped = value.strip()
    return stripped or None


def _stable_digest(value: Any, field_name: str) -> str:
    if type(value) is not str or len(value) != 32 or any(character not in _HEX for character in value):
        raise ValueError(f"{field_name} must be a 32-character hexadecimal digest")
    return value.lower()


def _string_tuple(value: Any, field_name: str, *, allow_empty: bool = False, allow_duplicates: bool = False) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise ValueError(f"{field_name} must be a tuple")
    normalized = tuple(_required_text(item, f"{field_name}[]") for item in value)
    if not allow_empty and not normalized:
        raise ValueError(f"{field_name} must not be empty")
    if not allow_duplicates and len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must not contain duplicates")
    return normalized


@dataclass(frozen=True)
class CodingArenaCompatibilityFinding:
    code: str
    message: str
    task_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", _required_text(self.code, "code"))
        object.__setattr__(self, "message", _required_text(self.message, "message"))
        object.__setattr__(self, "task_id", _optional_text(self.task_id, "task_id"))

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "task_id": self.task_id}


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

    def __post_init__(self) -> None:
        object.__setattr__(self, "task_id", _required_text(self.task_id, "task_id"))
        object.__setattr__(self, "action_id", _required_text(self.action_id, "action_id"))
        object.__setattr__(self, "target_file", _optional_text(self.target_file, "target_file"))
        object.__setattr__(self, "target_symbol", _optional_text(self.target_symbol, "target_symbol"))
        object.__setattr__(self, "expected_output", _required_text(self.expected_output, "expected_output").upper())
        object.__setattr__(self, "route", _required_text(self.route, "route"))
        for field_name in ("act_digest", "grounding_digest", "route_digest", "lease_digest", "boundary_digest"):
            object.__setattr__(self, field_name, _stable_digest(getattr(self, field_name), field_name))
        object.__setattr__(self, "evidence_refs", _string_tuple(self.evidence_refs, "evidence_refs"))
        object.__setattr__(self, "verifier_ids", _string_tuple(self.verifier_ids, "verifier_ids"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id, "action_id": self.action_id,
            "target_file": self.target_file, "target_symbol": self.target_symbol,
            "expected_output": self.expected_output, "route": self.route,
            "act_digest": self.act_digest, "grounding_digest": self.grounding_digest,
            "route_digest": self.route_digest, "lease_digest": self.lease_digest,
            "boundary_digest": self.boundary_digest,
            "evidence_refs": list(self.evidence_refs), "verifier_ids": list(self.verifier_ids),
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

    def __post_init__(self) -> None:
        if self.version != CODING_ARENA_COMPATIBILITY_VERSION:
            raise ValueError("unsupported Coding Arena compatibility version")
        try:
            status = self.status if isinstance(self.status, CodingArenaCompatibilityStatus) else CodingArenaCompatibilityStatus(str(self.status))
        except ValueError as exc:
            raise ValueError("invalid Coding Arena compatibility status") from exc
        object.__setattr__(self, "status", status)
        for field_name in ("task_count", "mapped_action_count"):
            value = getattr(self, field_name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")
        for field_name in ("task_order_preserved", "exact_legacy_preserved", "legacy_mutated", "authority_changed", "proposal_only", "continuity_complete"):
            if type(getattr(self, field_name)) is not bool:
                raise ValueError(f"{field_name} must be a boolean")
        if self.legacy_ready_for_incubator is not None and type(self.legacy_ready_for_incubator) is not bool:
            raise ValueError("legacy_ready_for_incubator must be a boolean or null")
        if self.proposal_only is not True or self.authority_changed is not False or self.legacy_mutated is not False:
            raise ValueError("compatibility evidence crossed its mutation or authority boundary")
        object.__setattr__(self, "plan_phase_hash", _optional_text(self.plan_phase_hash, "plan_phase_hash"))
        for field_name in ("legacy_plan_digest", "legacy_arena_digest", "legacy_shadow_digest", "board_digest"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, _stable_digest(value, field_name))
        object.__setattr__(self, "legacy_shadow_gate", _optional_text(self.legacy_shadow_gate, "legacy_shadow_gate"))
        object.__setattr__(self, "highest_contiguous_level", _optional_text(self.highest_contiguous_level, "highest_contiguous_level"))
        object.__setattr__(self, "legacy_routes", _string_tuple(self.legacy_routes, "legacy_routes", allow_empty=True, allow_duplicates=True))
        if type(self.findings) is not tuple or not all(isinstance(item, CodingArenaCompatibilityFinding) for item in self.findings):
            raise ValueError("findings must be a tuple of compatibility findings")
        projected = status in {CodingArenaCompatibilityStatus.VERIFIED_SHADOW, CodingArenaCompatibilityStatus.BLOCKED_LEGACY}
        if projected:
            if self.task_count <= 0 or self.mapped_action_count != self.task_count:
                raise ValueError("projected task and action counts disagree")
            if not self.task_order_preserved or not self.exact_legacy_preserved or self.findings:
                raise ValueError("projected evidence does not preserve exact legacy state")
            if self.plan_phase_hash is None or any(getattr(self, name) is None for name in ("legacy_plan_digest", "legacy_arena_digest", "legacy_shadow_digest", "board_digest")):
                raise ValueError("projected evidence requires source and board digests")
            if self.legacy_ready_for_incubator is None or self.legacy_shadow_gate is None:
                raise ValueError("projected evidence requires legacy disposition fields")
            if len(self.legacy_routes) != self.task_count:
                raise ValueError("projected route count must equal task count")
        else:
            if self.mapped_action_count != 0 or self.board_digest is not None:
                raise ValueError("failed evidence cannot carry projected state")
            if self.task_order_preserved or self.exact_legacy_preserved:
                raise ValueError("failed evidence cannot claim exact preservation")
            if self.highest_contiguous_level is not None or self.continuity_complete or not self.findings:
                raise ValueError("failed evidence must carry findings without continuity")

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version, "status": self.status.value,
            "plan_phase_hash": self.plan_phase_hash,
            "legacy_plan_digest": self.legacy_plan_digest,
            "legacy_arena_digest": self.legacy_arena_digest,
            "legacy_shadow_digest": self.legacy_shadow_digest,
            "board_digest": self.board_digest, "task_count": self.task_count,
            "mapped_action_count": self.mapped_action_count,
            "task_order_preserved": self.task_order_preserved,
            "exact_legacy_preserved": self.exact_legacy_preserved,
            "legacy_mutated": self.legacy_mutated,
            "authority_changed": self.authority_changed, "proposal_only": self.proposal_only,
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

    def __post_init__(self) -> None:
        if not isinstance(self.report, CodingArenaCompatibilityReport):
            raise ValueError("report must be a CodingArenaCompatibilityReport")
        if type(self.action_evidence) is not tuple or not all(isinstance(item, ActionContinuityEvidence) for item in self.action_evidence):
            raise ValueError("action_evidence must contain continuity evidence")
        if type(self.mappings) is not tuple or not all(isinstance(item, CodingArenaActionMapping) for item in self.mappings):
            raise ValueError("mappings must contain action mappings")
        patch_mappings = tuple(mapping for mapping in self.mappings if mapping.expected_output in _PATCH_OUTPUT_MODES)
        blocked_patch = any(mapping.route != "BUILDER_PATCH" for mapping in patch_mappings) or (bool(patch_mappings) and self.report.legacy_ready_for_incubator is not True)
        if blocked_patch and self.report.status is CodingArenaCompatibilityStatus.VERIFIED_SHADOW:
            object.__setattr__(self, "report", replace(self.report, status=CodingArenaCompatibilityStatus.BLOCKED_LEGACY))
        projected = self.report.status in {CodingArenaCompatibilityStatus.VERIFIED_SHADOW, CodingArenaCompatibilityStatus.BLOCKED_LEGACY}
        if not projected:
            if self.board is not None or self.continuity is not None or self.action_evidence or self.mappings:
                raise ValueError("failed inspection cannot carry projected board state")
            return
        if not isinstance(self.board, PlanningBoard) or not isinstance(self.continuity, BoardContinuityReport):
            raise ValueError("projected inspection requires board and continuity records")
        if self.board.digest != self.report.board_digest or len(self.board.actions) != self.report.task_count or len(self.mappings) != self.report.mapped_action_count:
            raise ValueError("projected report does not self-bind to the board")
        action_ids = tuple(action.action_id for action in self.board.actions)
        if action_ids != tuple(mapping.action_id for mapping in self.mappings) or action_ids != tuple(item.action_id for item in self.action_evidence):
            raise ValueError("projected action identities disagree")
        if tuple(mapping.route for mapping in self.mappings) != self.report.legacy_routes:
            raise ValueError("report routes do not match mappings")
        highest = self.continuity.highest_contiguous_level
        if (highest.value if highest is not None else None) != self.report.highest_contiguous_level or self.continuity.continuity_complete != self.report.continuity_complete:
            raise ValueError("report continuity does not self-bind")
        if any(action.proposal_only is not True or action.authority_requirement is not AuthorityRequirement.HUMAN for action in self.board.actions):
            raise ValueError("projected actions crossed the proposal-only human boundary")

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
        return {"case_id": self.case_id, "plan": self.plan, "grounding": list(self.grounding), "shadow_report": self.shadow_report, "arena": self.arena, "expected_status": self.expected_status.value}


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
        return {"case_id": self.case_id, "expected_status": self.expected_status.value, "observed_status": self.observed_status.value, "passed": self.passed, "task_count": self.task_count, "mapped_action_count": self.mapped_action_count, "deterministic": self.deterministic, "task_order_preserved": self.task_order_preserved, "exact_legacy_preserved": self.exact_legacy_preserved, "legacy_mutated": self.legacy_mutated, "authority_changed": self.authority_changed, "proposal_only": self.proposal_only, "verifier_declaration_rate": self.verifier_declaration_rate, "baseline_bytes": self.baseline_bytes, "candidate_bytes": self.candidate_bytes, "baseline_token_proxy": self.baseline_token_proxy, "candidate_token_proxy": self.candidate_token_proxy, "overhead_ratio": self.overhead_ratio, "board_digest": self.board_digest, "inspection_digest": self.inspection_digest, "finding_codes": list(self.finding_codes)}


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
        return {"version": self.version, "measurement_class": self.measurement_class, "repeats": self.repeats, "total_cases": self.total_cases, "passed_cases": self.passed_cases, "total_tasks": self.total_tasks, "mapped_actions": self.mapped_actions, "action_coverage": self.action_coverage, "deterministic_case_rate": self.deterministic_case_rate, "order_preservation_rate": self.order_preservation_rate, "verifier_declaration_rate": self.verifier_declaration_rate, "mutation_drift_count": self.mutation_drift_count, "authority_drift_count": self.authority_drift_count, "identifier_collision_count": self.identifier_collision_count, "baseline_bytes": self.baseline_bytes, "candidate_bytes": self.candidate_bytes, "baseline_token_proxy": self.baseline_token_proxy, "candidate_token_proxy": self.candidate_token_proxy, "overhead_ratio": self.overhead_ratio, "gate_passed": self.gate_passed, "cases": [item.to_dict() for item in self.cases], "limitations": list(self.limitations)}

    @property
    def digest(self) -> str:
        return stable_digest(self.to_dict())

    def to_json(self) -> str:
        return canonical_json(self.to_dict())
