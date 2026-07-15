"""Immutable P8 contracts for a read-only Civic Commons Planning Board shadow."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import PurePosixPath
import re
import string
from typing import Any

from aura_event_contracts import stable_digest
from aura_planning_board import (
    ActionContinuityEvidence,
    AuthorityRequirement,
    ConstraintKind,
    PlanningBoard,
    PortCardinality,
    PortDirection,
    ResourceDemand,
    ReversibilityClass,
)

CIVIC_P8_VERSION = "AURA_CIVIC_PLANNING_P8"
CIVIC_INVENTORY_VERSION = "AURA_CIVIC_SURFACE_INVENTORY_P8"
CIVIC_OWNERSHIP_DISPOSITION = "RETAIN_CIVIC_COMMONS_OWNER"
_HEX = frozenset(string.hexdigits)
_DRIVE = re.compile(r"^[A-Za-z]:")
_PROJECTED_BLOCKERS = frozenset({
    ("human_governance_authorization_contract_absent",),
    ("human_governance_authorization_contract_absent", "decision_packet_absent"),
})
_MUTATION_FINDING_CODES = frozenset({
    "PROJECT_CHANGED_DURING_INSPECTION",
    "SESSION_CHANGED_DURING_INSPECTION",
})
_AUTHORITY_FINDING_CODES = frozenset({
    "PATCH_AUTHORITY_MISMATCH",
    "ADVISORY_AUTHORITY_ESCALATION",
})


class CivicCompatibilityStatus(str, Enum):
    BLOCKED_BY_GOVERNANCE = "BLOCKED_BY_GOVERNANCE"
    MISMATCHED = "MISMATCHED"
    UNAVAILABLE = "UNAVAILABLE"


def _text(value: Any, name: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _digest(value: Any, name: str, *, size: int = 32) -> str:
    if type(value) is not str or len(value) != size or any(ch not in _HEX for ch in value):
        raise ValueError(f"{name} must be a {size}-character hexadecimal digest")
    return value.lower()


def _strings(value: Any, name: str) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise ValueError(f"{name} must be a tuple")
    result = tuple(_text(item, f"{name}[]") for item in value)
    if len(result) != len(set(result)):
        raise ValueError(f"{name} must not contain duplicates")
    return result  # type: ignore[return-value]


def _path(value: Any, name: str) -> str:
    result = _text(value, name)
    assert isinstance(result, str)
    pure = PurePosixPath(result)
    if "\\" in result or result.startswith("/") or _DRIVE.match(result):
        raise ValueError(f"{name} must be repository-relative")
    if pure.as_posix() != result or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError(f"{name} must be normalized without traversal")
    return result


@dataclass(frozen=True)
class CivicFinding:
    code: str
    message: str
    subject_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", _text(self.code, "finding.code"))
        object.__setattr__(self, "message", _text(self.message, "finding.message"))
        object.__setattr__(self, "subject_id", _text(self.subject_id, "finding.subject_id", optional=True))

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "subject_id": self.subject_id}


@dataclass(frozen=True)
class CivicSurfaceEntry:
    path: str
    role: str
    symbols: tuple[str, ...]
    sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _path(self.path, "surface.path"))
        object.__setattr__(self, "role", _text(self.role, "surface.role"))
        object.__setattr__(self, "symbols", _strings(self.symbols, "surface.symbols"))
        object.__setattr__(self, "sha256", _digest(self.sha256, "surface.sha256", size=64))

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "role": self.role, "symbols": list(self.symbols), "sha256": self.sha256}


@dataclass(frozen=True)
class CivicSurfaceInventory:
    entries: tuple[CivicSurfaceEntry, ...]
    version: str = CIVIC_INVENTORY_VERSION
    live_owner: str = "aura_civic_runtime"
    ownership_disposition: str = CIVIC_OWNERSHIP_DISPOSITION

    def __post_init__(self) -> None:
        if self.version != CIVIC_INVENTORY_VERSION:
            raise ValueError("unsupported inventory version")
        if type(self.entries) is not tuple or not self.entries or not all(isinstance(x, CivicSurfaceEntry) for x in self.entries):
            raise ValueError("inventory entries must be a non-empty tuple")
        paths = tuple(item.path for item in self.entries)
        if paths != tuple(sorted(set(paths))):
            raise ValueError("inventory paths must be unique and sorted")
        if self.live_owner != "aura_civic_runtime" or self.ownership_disposition != CIVIC_OWNERSHIP_DISPOSITION:
            raise ValueError("inventory ownership boundary changed")

    def to_dict(self) -> dict[str, Any]:
        return {"version": self.version, "entries": [x.to_dict() for x in self.entries], "live_owner": self.live_owner, "ownership_disposition": self.ownership_disposition}

    @property
    def digest(self) -> str:
        return stable_digest(self.to_dict())


@dataclass(frozen=True)
class CivicRecordBindings:
    consent_arc_digest: str
    convergence_digest: str
    pilot_digest: str
    decision_packet_digest: str | None
    decision_packet_present: bool
    authorization_contract_present: bool = False

    def __post_init__(self) -> None:
        for field in ("consent_arc_digest", "convergence_digest", "pilot_digest"):
            object.__setattr__(self, field, _digest(getattr(self, field), f"bindings.{field}"))
        if self.decision_packet_digest is not None:
            object.__setattr__(self, "decision_packet_digest", _digest(self.decision_packet_digest, "bindings.decision_packet_digest"))
        if type(self.decision_packet_present) is not bool or type(self.authorization_contract_present) is not bool:
            raise ValueError("binding presence flags must be booleans")
        if self.decision_packet_present != (self.decision_packet_digest is not None):
            raise ValueError("decision packet presence and digest disagree")
        if self.authorization_contract_present:
            raise ValueError("P8 has no machine-verifiable governance authorization contract")

    @property
    def blockers(self) -> tuple[str, ...]:
        result = ["human_governance_authorization_contract_absent"]
        if not self.decision_packet_present:
            result.append("decision_packet_absent")
        return tuple(result)

    def to_dict(self) -> dict[str, Any]:
        return {
            "consent_arc_digest": self.consent_arc_digest,
            "convergence_digest": self.convergence_digest,
            "pilot_digest": self.pilot_digest,
            "decision_packet_digest": self.decision_packet_digest,
            "decision_packet_present": self.decision_packet_present,
            "authorization_contract_present": False,
            "blockers": list(self.blockers),
        }

    @property
    def digest(self) -> str:
        return stable_digest(self.to_dict())


@dataclass(frozen=True)
class CivicActionMapping:
    workstream_id: str
    action_id: str
    workstream_digest: str
    dependency_ids: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "workstream_id", _text(self.workstream_id, "mapping.workstream_id"))
        object.__setattr__(self, "action_id", _text(self.action_id, "mapping.action_id"))
        object.__setattr__(self, "workstream_digest", _digest(self.workstream_digest, "mapping.workstream_digest"))
        object.__setattr__(self, "dependency_ids", _strings(self.dependency_ids, "mapping.dependency_ids"))
        object.__setattr__(self, "evidence_refs", _strings(self.evidence_refs, "mapping.evidence_refs"))
        if len(self.evidence_refs) != 5:
            raise ValueError("mapping must carry exactly five evidence references")

    def to_dict(self) -> dict[str, Any]:
        return {"workstream_id": self.workstream_id, "action_id": self.action_id, "workstream_digest": self.workstream_digest, "dependency_ids": list(self.dependency_ids), "evidence_refs": list(self.evidence_refs)}


@dataclass(frozen=True)
class CivicCompatibilityReport:
    status: CivicCompatibilityStatus
    project_id: str | None
    session_id: str | None
    project_digest: str | None
    session_digest: str | None
    inventory_digest: str | None
    bindings_digest: str | None
    board_digest: str | None
    workstream_count: int
    mapped_action_count: int
    mapping_verified: bool
    source_mutated: bool
    authority_changed: bool
    governance_blockers: tuple[str, ...]
    findings: tuple[CivicFinding, ...]
    version: str = CIVIC_P8_VERSION
    ownership_disposition: str = CIVIC_OWNERSHIP_DISPOSITION

    def __post_init__(self) -> None:
        if self.version != CIVIC_P8_VERSION or self.ownership_disposition != CIVIC_OWNERSHIP_DISPOSITION:
            raise ValueError("unsupported P8 report contract")
        if not isinstance(self.status, CivicCompatibilityStatus):
            object.__setattr__(self, "status", CivicCompatibilityStatus(str(self.status)))
        for field in ("project_id", "session_id"):
            object.__setattr__(self, field, _text(getattr(self, field), f"report.{field}", optional=True))
        for field in ("project_digest", "session_digest", "inventory_digest", "bindings_digest", "board_digest"):
            value = getattr(self, field)
            if value is not None:
                object.__setattr__(self, field, _digest(value, f"report.{field}"))
        if type(self.workstream_count) is not int or type(self.mapped_action_count) is not int or min(self.workstream_count, self.mapped_action_count) < 0:
            raise ValueError("report counts must be non-negative integers")
        if any(type(x) is not bool for x in (self.mapping_verified, self.source_mutated, self.authority_changed)):
            raise ValueError("report boundary flags must be booleans")
        object.__setattr__(self, "governance_blockers", _strings(self.governance_blockers, "report.governance_blockers"))
        if type(self.findings) is not tuple or not all(isinstance(x, CivicFinding) for x in self.findings):
            raise ValueError("report findings are invalid")
        projected = self.status is CivicCompatibilityStatus.BLOCKED_BY_GOVERNANCE
        if projected:
            if self.workstream_count <= 0 or self.mapped_action_count != self.workstream_count or not self.mapping_verified:
                raise ValueError("projected report requires complete structural mapping")
            if self.source_mutated or self.authority_changed or self.findings:
                raise ValueError("projected report crossed a boundary")
            if self.governance_blockers not in _PROJECTED_BLOCKERS:
                raise ValueError("projected report has an unsupported blocker set")
            required = (self.project_id, self.session_id, self.project_digest, self.session_digest, self.inventory_digest, self.bindings_digest, self.board_digest)
            if any(value is None for value in required):
                raise ValueError("projected report is missing exact bindings")
        else:
            if self.mapped_action_count or self.mapping_verified or self.bindings_digest or self.board_digest or self.governance_blockers:
                raise ValueError("failed report cannot carry projected state")
            if not self.findings:
                raise ValueError("failed report requires a finding")
            codes = frozenset(item.code for item in self.findings)
            object.__setattr__(self, "source_mutated", bool(codes & _MUTATION_FINDING_CODES))
            object.__setattr__(self, "authority_changed", bool(codes & _AUTHORITY_FINDING_CODES))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "status": self.status.value,
            "ownership_disposition": self.ownership_disposition,
            "project_id": self.project_id,
            "session_id": self.session_id,
            "project_digest": self.project_digest,
            "session_digest": self.session_digest,
            "inventory_digest": self.inventory_digest,
            "bindings_digest": self.bindings_digest,
            "board_digest": self.board_digest,
            "workstream_count": self.workstream_count,
            "mapped_action_count": self.mapped_action_count,
            "mapping_verified": self.mapping_verified,
            "source_mutated": self.source_mutated,
            "authority_changed": self.authority_changed,
            "governance_blockers": list(self.governance_blockers),
            "findings": [x.to_dict() for x in self.findings],
        }

    @property
    def digest(self) -> str:
        return stable_digest(self.to_dict())


@dataclass(frozen=True)
class CivicPlanningInspection:
    report: CivicCompatibilityReport
    inventory: CivicSurfaceInventory | None = None
    bindings: CivicRecordBindings | None = None
    board: PlanningBoard | None = None
    action_evidence: tuple[ActionContinuityEvidence, ...] = ()
    mappings: tuple[CivicActionMapping, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.report, CivicCompatibilityReport):
            raise ValueError("inspection report is invalid")
        if self.report.status is not CivicCompatibilityStatus.BLOCKED_BY_GOVERNANCE:
            if any(x is not None for x in (self.inventory, self.bindings, self.board)) or self.action_evidence or self.mappings:
                raise ValueError("failed inspection cannot carry projected state")
            return
        if not isinstance(self.inventory, CivicSurfaceInventory) or not isinstance(self.bindings, CivicRecordBindings) or not isinstance(self.board, PlanningBoard):
            raise ValueError("projected inspection is incomplete")
        if self.inventory.digest != self.report.inventory_digest or self.bindings.digest != self.report.bindings_digest or self.board.digest != self.report.board_digest:
            raise ValueError("inspection digest binding failed")
        if self.bindings.blockers != self.report.governance_blockers:
            raise ValueError("governance blockers do not self-bind")
        if self.report.workstream_count != len(self.board.actions) or self.report.mapped_action_count != len(self.mappings):
            raise ValueError("report counts do not self-bind")
        state_refs = (
            f"civic-project:blake2b-128:{self.report.project_digest}",
            f"civic-session:blake2b-128:{self.report.session_digest}",
            f"civic-record-bindings:blake2b-128:{self.report.bindings_digest}",
            f"civic-surface-inventory:blake2b-128:{self.report.inventory_digest}",
        )
        if self.board.current_state_refs != state_refs or self.board.goal.evidence_refs != state_refs:
            raise ValueError("board source references do not self-bind")
        if self.board.arena_id != f"civic_commons:{self.report.project_id}":
            raise ValueError("board arena identity does not self-bind")
        expected_board_id = f"civic_board_{stable_digest({'project': self.report.project_digest, 'session': self.report.session_digest}, digest_size=12)}"
        if self.board.board_id != expected_board_id:
            raise ValueError("board identifier does not self-bind")
        expected_goal_id = f"civic_goal_{stable_digest({'project': self.report.project_id, 'session': self.report.session_id}, digest_size=12)}"
        if self.board.goal.goal_id != expected_goal_id:
            raise ValueError("goal identifier does not self-bind")
        expected_purpose = stable_digest({
            "project_id": self.report.project_id,
            "session_id": self.report.session_id,
            "objective": self.board.goal.objective,
            "bindings": self.bindings.digest,
        })
        if self.board.purpose_digest != expected_purpose:
            raise ValueError("board purpose does not self-bind")
        if len(self.board.actions) != len(self.mappings) or len(self.mappings) != len(self.action_evidence):
            raise ValueError("projected evidence counts disagree")
        expected_goal_facts = tuple(
            f"civic.workstream.{mapping.workstream_id}.shadow_projected"
            for mapping in self.mappings
        )
        if tuple(item.fact for item in self.board.goal.desired_state) != expected_goal_facts:
            raise ValueError("goal desired state does not self-bind")
        if any(item.expected is not True or item.operator.value != "EQ" for item in self.board.goal.desired_state):
            raise ValueError("goal desired state changed its exact truth requirement")
        if len(self.board.goal.constraints) < 2:
            raise ValueError("board must retain project and external-authority constraints")
        for constraint in self.board.goal.constraints[:-1]:
            if constraint.kind is not ConstraintKind.DOMAIN or constraint.evidence_refs != (state_refs[0],) or constraint.blocking is not True:
                raise ValueError("project constraints do not self-bind")
        authority_constraint = self.board.goal.constraints[-1]
        if (
            authority_constraint.kind is not ConstraintKind.POLICY
            or authority_constraint.description != "External human governance authorization is required before execution."
            or authority_constraint.evidence_refs != (state_refs[2],)
            or authority_constraint.blocking is not True
        ):
            raise ValueError("external-authority constraint does not self-bind")
        default_resource = ResourceDemand().to_dict()
        for index, (action, mapping, evidence) in enumerate(zip(self.board.actions, self.mappings, self.action_evidence, strict=True)):
            expected_id = f"civic_p8_{index:03d}_{stable_digest({'workstream': mapping.workstream_id, 'digest': mapping.workstream_digest}, digest_size=10)}"
            expected_refs = (
                f"civic-workstream:blake2b-128:{mapping.workstream_digest}",
                state_refs[0], state_refs[1], state_refs[2], state_refs[3],
            )
            if mapping.action_id != expected_id or action.action_id != expected_id or evidence.action_id != expected_id:
                raise ValueError("projected action identities disagree")
            if mapping.evidence_refs != expected_refs or tuple(action.evidence_refs) != expected_refs:
                raise ValueError("action evidence references do not self-bind")
            if not action.name.startswith("Shadow project Civic workstream: ") or action.domain != "civic_commons":
                raise ValueError("action label or domain does not self-bind")
            if action.required_capabilities != ("civic_commons.shadow_project",):
                raise ValueError("action capabilities do not self-bind")
            if action.authority_requirement is not AuthorityRequirement.HUMAN or action.proposal_only is not True or action.verifier_ids:
                raise ValueError("action crossed its HUMAN proposal-only boundary")
            if action.constraints != self.board.goal.constraints:
                raise ValueError("action constraints do not self-bind")
            if (
                len(action.input_ports) != 1
                or action.input_ports[0].name != "civic_source_record"
                or action.input_ports[0].data_type != "CivicWorkstreamRecord"
                or action.input_ports[0].direction is not PortDirection.INPUT
                or action.input_ports[0].cardinality is not PortCardinality.ONE
                or action.input_ports[0].required is not True
            ):
                raise ValueError("action input port does not self-bind")
            if (
                len(action.output_ports) != 1
                or action.output_ports[0].name != "planning_shadow_action"
                or action.output_ports[0].data_type != "PlanningBoardAction"
                or action.output_ports[0].direction is not PortDirection.OUTPUT
                or action.output_ports[0].cardinality is not PortCardinality.ONE
                or action.output_ports[0].required is not True
            ):
                raise ValueError("action output port does not self-bind")
            expected_preconditions = tuple(f"civic.workstream.{item}.proposal_exists" for item in mapping.dependency_ids) + ("civic.governance.external_human_authorization_required",)
            if tuple(item.fact for item in action.preconditions) != expected_preconditions:
                raise ValueError("dependency preconditions do not self-bind")
            if any(item.expected is not True or item.operator.value != "EQ" for item in action.preconditions):
                raise ValueError("preconditions changed their exact truth requirement")
            if len(action.effects) != 1 or action.effects[0].fact != f"civic.workstream.{mapping.workstream_id}.shadow_projected" or action.effects[0].value is not True:
                raise ValueError("action effect does not self-bind")
            if action.idempotency_key != f"civic-p8:{mapping.workstream_digest}":
                raise ValueError("action idempotency does not self-bind")
            if action.resource_demand.to_dict() != default_resource:
                raise ValueError("action resource demand does not self-bind")
            if action.reversibility is not ReversibilityClass.REVERSIBLE:
                raise ValueError("action reversibility does not self-bind")
            if (
                action.retry_policy.max_attempts != 1
                or action.retry_policy.backoff_seconds != 0.0
                or action.retry_policy.fallback_action_ids
            ):
                raise ValueError("action retry policy does not self-bind")
            if evidence.authority_decision_ids or evidence.verifier_receipts:
                raise ValueError("P8 cannot fabricate authority or verifier evidence")
            if evidence.constrained_evidence_refs != (expected_refs[1], expected_refs[3]):
                raise ValueError("constrained evidence does not self-bind")
            if evidence.grounded_evidence_refs != (expected_refs[0], expected_refs[2], expected_refs[4]):
                raise ValueError("grounded evidence does not self-bind")

    def to_dict(self) -> dict[str, Any]:
        return {
            "report": self.report.to_dict(),
            "inventory": self.inventory.to_dict() if self.inventory else None,
            "bindings": self.bindings.to_dict() if self.bindings else None,
            "board": self.board.to_dict() if self.board else None,
            "action_evidence": [x.to_dict() for x in self.action_evidence],
            "mappings": [x.to_dict() for x in self.mappings],
        }
