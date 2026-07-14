"""Domain-neutral, proposal-only Planning Board contracts for AuraOS.

This additive P2.1 layer can shadow-project existing GOAP plans without
changing routing, provider calls, tool schemas, authority, or execution.
Planning proposes; governance authorizes; verification proves.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
import json
import math
from typing import Any

from aura_event_contracts import MeasurementClass, canonical_json, stable_digest

PLANNING_BOARD_VERSION = "AURA_PLANNING_BOARD_V1"
SCHEMA_VERSION = "1.0"


class BoardContinuityLevel(str, Enum):
    """Board continuity namespace, distinct from Aura route phases C1-C3."""

    BC0_STRUCTURAL = "BC0_STRUCTURAL"
    BC1_TYPED = "BC1_TYPED"
    BC2_CONSTRAINED = "BC2_CONSTRAINED"
    BC3_GROUNDED = "BC3_GROUNDED"
    BC4_AUTHORIZED = "BC4_AUTHORIZED"
    BC5_VERIFIED = "BC5_VERIFIED"


_CONTINUITY_ORDER = tuple(BoardContinuityLevel)


class PortDirection(str, Enum):
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"


class PortCardinality(str, Enum):
    ONE = "ONE"
    OPTIONAL = "OPTIONAL"
    MANY = "MANY"


class PredicateOperator(str, Enum):
    EQ = "EQ"
    IN = "IN"
    EXISTS = "EXISTS"


class ConstraintKind(str, Enum):
    POLICY = "POLICY"
    RESOURCE = "RESOURCE"
    BUDGET = "BUDGET"
    TEMPORAL = "TEMPORAL"
    SAFETY = "SAFETY"
    DOMAIN = "DOMAIN"


class ReversibilityClass(str, Enum):
    UNSPECIFIED = "UNSPECIFIED"
    REVERSIBLE = "REVERSIBLE"
    COMPENSATABLE = "COMPENSATABLE"
    TIME_LIMITED_REVERSAL = "TIME_LIMITED_REVERSAL"
    IRREVERSIBLE = "IRREVERSIBLE"
    HUMAN_REMEDIATION_REQUIRED = "HUMAN_REMEDIATION_REQUIRED"


class AuthorityRequirement(str, Enum):
    UNSPECIFIED = "UNSPECIFIED"
    NONE = "NONE"
    CAPABILITY_LEASE = "CAPABILITY_LEASE"
    HUMAN = "HUMAN"
    COMMUNITY = "COMMUNITY"
    QUORUM = "QUORUM"


def _required(value: Any, field_name: str) -> str:
    value = str(value or "").strip()
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    return value


def _strict_bool(value: Any, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field_name} must be a boolean")
    return value


def _enum(value: str | Enum, enum_type: type[Enum], field_name: str) -> Enum:
    raw = value.value if isinstance(value, Enum) else str(value)
    try:
        return enum_type(raw)
    except ValueError as exc:
        raise ValueError(f"unknown {field_name}: {raw}") from exc


def _strings(values: Sequence[Any] | None, field_name: str) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes, bytearray)):
        raise ValueError(f"{field_name} must be a sequence of strings")
    result = tuple(_required(value, field_name) for value in values)
    if len(result) != len(set(result)):
        raise ValueError(f"{field_name} must not contain duplicates")
    return result


def _records(values: Sequence[Any], record_type: type, field_name: str) -> tuple:
    if isinstance(values, (str, bytes, bytearray)):
        raise ValueError(f"{field_name} must be a sequence")
    result = tuple(values)
    if not all(isinstance(value, record_type) for value in result):
        raise ValueError(f"{field_name} contains an invalid value")
    return result


def _nonnegative_int(value: int | None, field_name: str) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


def _nonnegative_number(value: float | None, field_name: str) -> float | None:
    if value is None:
        return None
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{field_name} must be finite and non-negative")
    return number


class CanonicalRecord:
    def to_dict(self) -> dict[str, Any]:
        return json.loads(canonical_json(self))


@dataclass(frozen=True)
class PortSpec(CanonicalRecord):
    name: str
    data_type: str
    direction: PortDirection | str
    cardinality: PortCardinality | str = PortCardinality.ONE
    required: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required(self.name, "port.name"))
        object.__setattr__(self, "data_type", _required(self.data_type, "port.data_type"))
        object.__setattr__(self, "direction", _enum(self.direction, PortDirection, "port.direction"))
        object.__setattr__(
            self, "cardinality", _enum(self.cardinality, PortCardinality, "port.cardinality")
        )
        object.__setattr__(self, "required", _strict_bool(self.required, "port.required"))
        if self.cardinality is PortCardinality.OPTIONAL and self.required:
            raise ValueError("optional ports cannot be marked required")


@dataclass(frozen=True)
class PredicateSpec(CanonicalRecord):
    fact: str
    expected: Any
    operator: PredicateOperator | str = PredicateOperator.EQ

    def __post_init__(self) -> None:
        object.__setattr__(self, "fact", _required(self.fact, "predicate.fact"))
        object.__setattr__(
            self, "operator", _enum(self.operator, PredicateOperator, "predicate.operator")
        )
        canonical_json(self.expected)
        if self.operator is PredicateOperator.IN and not isinstance(
            self.expected, (tuple, list, set, frozenset)
        ):
            raise ValueError("IN predicates require a collection expected value")
        if self.operator is PredicateOperator.EXISTS and type(self.expected) is not bool:
            raise ValueError("EXISTS predicates require a boolean expected value")


@dataclass(frozen=True)
class EffectSpec(CanonicalRecord):
    fact: str
    value: Any

    def __post_init__(self) -> None:
        object.__setattr__(self, "fact", _required(self.fact, "effect.fact"))
        canonical_json(self.value)


@dataclass(frozen=True)
class ConstraintSpec(CanonicalRecord):
    constraint_id: str
    kind: ConstraintKind | str
    description: str
    evidence_refs: tuple[str, ...] = ()
    blocking: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "constraint_id", _required(self.constraint_id, "constraint.constraint_id")
        )
        object.__setattr__(self, "kind", _enum(self.kind, ConstraintKind, "constraint.kind"))
        object.__setattr__(
            self, "description", _required(self.description, "constraint.description")
        )
        object.__setattr__(
            self, "evidence_refs", _strings(self.evidence_refs, "constraint.evidence_refs")
        )
        object.__setattr__(
            self, "blocking", _strict_bool(self.blocking, "constraint.blocking")
        )


@dataclass(frozen=True)
class ResourceDemand(CanonicalRecord):
    """Advisory estimates; never budget approval or execution authority."""

    context_tokens: int | None = None
    expected_latency_ms: int | None = None
    memory_bytes: int | None = None
    human_attention_minutes: float | None = None
    estimated_cost: float | None = None
    cost_unit: str | None = None
    measurement_class: MeasurementClass | str = MeasurementClass.UNAVAILABLE

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "context_tokens", _nonnegative_int(self.context_tokens, "resource.context_tokens")
        )
        object.__setattr__(
            self,
            "expected_latency_ms",
            _nonnegative_int(self.expected_latency_ms, "resource.expected_latency_ms"),
        )
        object.__setattr__(
            self, "memory_bytes", _nonnegative_int(self.memory_bytes, "resource.memory_bytes")
        )
        object.__setattr__(
            self,
            "human_attention_minutes",
            _nonnegative_number(self.human_attention_minutes, "resource.human_attention_minutes"),
        )
        object.__setattr__(
            self, "estimated_cost", _nonnegative_number(self.estimated_cost, "resource.estimated_cost")
        )
        if self.cost_unit is not None:
            object.__setattr__(self, "cost_unit", _required(self.cost_unit, "resource.cost_unit"))
        if (self.estimated_cost is None) != (self.cost_unit is None):
            raise ValueError("resource.estimated_cost and resource.cost_unit must be supplied together")
        object.__setattr__(
            self,
            "measurement_class",
            _enum(self.measurement_class, MeasurementClass, "resource.measurement_class"),
        )
        estimates = (
            self.context_tokens,
            self.expected_latency_ms,
            self.memory_bytes,
            self.human_attention_minutes,
            self.estimated_cost,
        )
        if any(value is not None for value in estimates) and self.measurement_class is MeasurementClass.UNAVAILABLE:
            raise ValueError("resource estimates require an explicit measurement_class")


@dataclass(frozen=True)
class RetryPolicy(CanonicalRecord):
    max_attempts: int = 1
    backoff_seconds: float = 0.0
    fallback_action_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.max_attempts) is not int or self.max_attempts < 1:
            raise ValueError("retry.max_attempts must be a positive integer")
        object.__setattr__(
            self, "backoff_seconds", _nonnegative_number(self.backoff_seconds, "retry.backoff_seconds")
        )
        object.__setattr__(
            self, "fallback_action_ids", _strings(self.fallback_action_ids, "retry.fallback_action_ids")
        )


@dataclass(frozen=True)
class GoalSpec(CanonicalRecord):
    goal_id: str
    objective: str
    desired_state: tuple[PredicateSpec, ...]
    constraints: tuple[ConstraintSpec, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "goal_id", _required(self.goal_id, "goal.goal_id"))
        object.__setattr__(self, "objective", _required(self.objective, "goal.objective"))
        desired = _records(self.desired_state, PredicateSpec, "goal.desired_state")
        if not desired:
            raise ValueError("goal.desired_state must not be empty")
        object.__setattr__(self, "desired_state", desired)
        object.__setattr__(
            self, "constraints", _records(self.constraints, ConstraintSpec, "goal.constraints")
        )
        object.__setattr__(self, "evidence_refs", _strings(self.evidence_refs, "goal.evidence_refs"))


@dataclass(frozen=True)
class ActionSpec(CanonicalRecord):
    """One possible action. It can never authorize or execute itself."""

    action_id: str
    name: str
    domain: str
    preconditions: tuple[PredicateSpec, ...]
    effects: tuple[EffectSpec, ...]
    input_ports: tuple[PortSpec, ...] = ()
    output_ports: tuple[PortSpec, ...] = ()
    constraints: tuple[ConstraintSpec, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    verifier_ids: tuple[str, ...] = ()
    authority_requirement: AuthorityRequirement | str = AuthorityRequirement.UNSPECIFIED
    resource_demand: ResourceDemand = field(default_factory=ResourceDemand)
    reversibility: ReversibilityClass | str = ReversibilityClass.UNSPECIFIED
    idempotency_key: str | None = None
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    evidence_refs: tuple[str, ...] = ()
    proposal_only: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "action_id", _required(self.action_id, "action.action_id"))
        object.__setattr__(self, "name", _required(self.name, "action.name"))
        object.__setattr__(self, "domain", _required(self.domain, "action.domain"))
        object.__setattr__(
            self, "preconditions", _records(self.preconditions, PredicateSpec, "action.preconditions")
        )
        object.__setattr__(self, "effects", _records(self.effects, EffectSpec, "action.effects"))
        object.__setattr__(
            self, "input_ports", _records(self.input_ports, PortSpec, "action.input_ports")
        )
        object.__setattr__(
            self, "output_ports", _records(self.output_ports, PortSpec, "action.output_ports")
        )
        object.__setattr__(
            self, "constraints", _records(self.constraints, ConstraintSpec, "action.constraints")
        )
        input_names = [port.name for port in self.input_ports]
        output_names = [port.name for port in self.output_ports]
        if len(input_names) != len(set(input_names)) or len(output_names) != len(set(output_names)):
            raise ValueError("action port names must be unique within their direction")
        if set(input_names) & set(output_names):
            raise ValueError("input and output port names must not overlap")
        if any(port.direction is not PortDirection.INPUT for port in self.input_ports):
            raise ValueError("action.input_ports must use INPUT direction")
        if any(port.direction is not PortDirection.OUTPUT for port in self.output_ports):
            raise ValueError("action.output_ports must use OUTPUT direction")
        object.__setattr__(
            self,
            "required_capabilities",
            _strings(self.required_capabilities, "action.required_capabilities"),
        )
        object.__setattr__(self, "verifier_ids", _strings(self.verifier_ids, "action.verifier_ids"))
        object.__setattr__(
            self,
            "authority_requirement",
            _enum(self.authority_requirement, AuthorityRequirement, "action.authority_requirement"),
        )
        if not isinstance(self.resource_demand, ResourceDemand):
            raise ValueError("action.resource_demand must be a ResourceDemand")
        object.__setattr__(
            self, "reversibility", _enum(self.reversibility, ReversibilityClass, "action.reversibility")
        )
        if self.idempotency_key is not None:
            object.__setattr__(
                self, "idempotency_key", _required(self.idempotency_key, "action.idempotency_key")
            )
        if not isinstance(self.retry_policy, RetryPolicy):
            raise ValueError("action.retry_policy must be a RetryPolicy")
        object.__setattr__(self, "evidence_refs", _strings(self.evidence_refs, "action.evidence_refs"))
        if _strict_bool(self.proposal_only, "action.proposal_only") is not True:
            raise ValueError("Planning Board actions must remain proposal_only")


@dataclass(frozen=True)
class PlanningBoard(CanonicalRecord):
    board_id: str
    arena_id: str
    purpose_digest: str
    goal: GoalSpec
    actions: tuple[ActionSpec, ...]
    current_state_refs: tuple[str, ...] = ()
    version: str = PLANNING_BOARD_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "board_id", _required(self.board_id, "board.board_id"))
        object.__setattr__(self, "arena_id", _required(self.arena_id, "board.arena_id"))
        object.__setattr__(
            self, "purpose_digest", _required(self.purpose_digest, "board.purpose_digest")
        )
        if not isinstance(self.goal, GoalSpec):
            raise ValueError("board.goal must be a GoalSpec")
        actions = _records(self.actions, ActionSpec, "board.actions")
        if not actions:
            raise ValueError("board.actions must not be empty")
        action_ids = [action.action_id for action in actions]
        if len(action_ids) != len(set(action_ids)):
            raise ValueError("board.actions must have unique action_id values")
        object.__setattr__(self, "actions", actions)
        object.__setattr__(
            self, "current_state_refs", _strings(self.current_state_refs, "board.current_state_refs")
        )
        if self.version != PLANNING_BOARD_VERSION:
            raise ValueError(f"unsupported Planning Board version: {self.version}")

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": SCHEMA_VERSION, **super().to_dict()}

    @property
    def digest(self) -> str:
        return stable_digest(self.to_dict())


@dataclass(frozen=True)
class VerifierReceiptEvidence(CanonicalRecord):
    verifier_id: str
    receipt_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "verifier_id", _required(self.verifier_id, "verifier.verifier_id"))
        object.__setattr__(self, "receipt_id", _required(self.receipt_id, "verifier.receipt_id"))


@dataclass(frozen=True)
class ActionContinuityEvidence(CanonicalRecord):
    """References emitted by authoritative external subsystems."""

    action_id: str
    constrained_evidence_refs: tuple[str, ...] = ()
    grounded_evidence_refs: tuple[str, ...] = ()
    authority_decision_ids: tuple[str, ...] = ()
    verifier_receipts: tuple[VerifierReceiptEvidence, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "action_id", _required(self.action_id, "evidence.action_id"))
        for name in (
            "constrained_evidence_refs",
            "grounded_evidence_refs",
            "authority_decision_ids",
        ):
            object.__setattr__(self, name, _strings(getattr(self, name), f"evidence.{name}"))
        receipts = _records(
            self.verifier_receipts, VerifierReceiptEvidence, "evidence.verifier_receipts"
        )
        verifier_ids = [receipt.verifier_id for receipt in receipts]
        receipt_ids = [receipt.receipt_id for receipt in receipts]
        if len(verifier_ids) != len(set(verifier_ids)):
            raise ValueError("evidence.verifier_receipts must have unique verifier_id values")
        if len(receipt_ids) != len(set(receipt_ids)):
            raise ValueError("evidence.verifier_receipts must have unique receipt_id values")
        object.__setattr__(self, "verifier_receipts", receipts)


@dataclass(frozen=True)
class ContinuityFinding(CanonicalRecord):
    level: BoardContinuityLevel | str
    code: str
    message: str
    subject_id: str
    blocking: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "level", _enum(self.level, BoardContinuityLevel, "finding.level"))
        object.__setattr__(self, "code", _required(self.code, "finding.code"))
        object.__setattr__(self, "message", _required(self.message, "finding.message"))
        object.__setattr__(self, "subject_id", _required(self.subject_id, "finding.subject_id"))
        object.__setattr__(self, "blocking", _strict_bool(self.blocking, "finding.blocking"))


@dataclass(frozen=True)
class BoardContinuityReport(CanonicalRecord):
    board_id: str
    board_digest: str
    passed_levels: tuple[BoardContinuityLevel, ...]
    findings: tuple[ContinuityFinding, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "board_id", _required(self.board_id, "report.board_id"))
        object.__setattr__(self, "board_digest", _required(self.board_digest, "report.board_digest"))
        levels = _records(self.passed_levels, BoardContinuityLevel, "report.passed_levels")
        if len(levels) != len(set(levels)):
            raise ValueError("report.passed_levels must not contain duplicates")
        object.__setattr__(self, "passed_levels", levels)
        object.__setattr__(
            self, "findings", _records(self.findings, ContinuityFinding, "report.findings")
        )

    @property
    def highest_contiguous_level(self) -> BoardContinuityLevel | None:
        highest = None
        passed = set(self.passed_levels)
        for level in _CONTINUITY_ORDER:
            if level not in passed:
                break
            highest = level
        return highest

    @property
    def continuity_complete(self) -> bool:
        """BC0-BC5 are contiguous; this is not an execution grant."""

        return self.highest_contiguous_level is BoardContinuityLevel.BC5_VERIFIED

    def to_dict(self) -> dict[str, Any]:
        value = super().to_dict()
        value["highest_contiguous_level"] = (
            self.highest_contiguous_level.value if self.highest_contiguous_level else None
        )
        value["continuity_complete"] = self.continuity_complete
        return value


def action_spec_from_goal_action(action: Any) -> ActionSpec:
    """Shadow-adapt a legacy GoalAction without inventing authority or safety."""

    name = _required(getattr(action, "name", None), "goal_action.name")
    domain = _required(getattr(action, "domain", None), "goal_action.domain")
    preconditions = getattr(action, "preconditions", {})
    effects = getattr(action, "effects", {})
    if not isinstance(preconditions, Mapping) or not isinstance(effects, Mapping):
        raise ValueError("GoalAction preconditions and effects must be mappings")
    organ = str(getattr(action, "required_organ", "") or "").strip()
    gates = _strings(getattr(action, "must_pass_gates", ()), "goal_action.gates")
    payload = {
        "name": name,
        "domain": domain,
        "preconditions": preconditions,
        "effects": effects,
        "required_organ": organ,
        "gates": gates,
    }
    return ActionSpec(
        action_id=f"action_{stable_digest(payload, digest_size=12)}",
        name=name,
        domain=domain,
        preconditions=tuple(
            PredicateSpec(str(key), value)
            for key, value in sorted(preconditions.items(), key=lambda item: str(item[0]))
        ),
        effects=tuple(
            EffectSpec(str(key), value)
            for key, value in sorted(effects.items(), key=lambda item: str(item[0]))
        ),
        required_capabilities=(f"organ:{organ}",) if organ else (),
        verifier_ids=tuple(f"gate:{gate}" for gate in gates),
        authority_requirement=AuthorityRequirement.UNSPECIFIED,
        reversibility=ReversibilityClass.UNSPECIFIED,
        proposal_only=True,
    )


def planning_board_from_goal_plan(
    plan: Any,
    *,
    arena_id: str,
    purpose_digest: str,
    current_state_refs: Sequence[str] = (),
) -> PlanningBoard:
    """Build a deterministic, non-authoritative board projection from GoalPlan."""

    goal_name = _required(getattr(plan, "goal", None), "goal_plan.goal")
    final_state = getattr(plan, "final_state", None)
    actions = getattr(plan, "actions", None)
    if not isinstance(final_state, Mapping):
        raise ValueError("GoalPlan final_state must be a mapping")
    if isinstance(actions, (str, bytes, bytearray)) or not isinstance(actions, Sequence):
        raise ValueError("GoalPlan actions must be a sequence")
    action_specs = tuple(action_spec_from_goal_action(action) for action in actions)
    if not action_specs:
        raise ValueError("GoalPlan actions must not be empty")
    goal = GoalSpec(
        goal_id=f"goal_{stable_digest({'goal': goal_name, 'state': final_state}, digest_size=12)}",
        objective=goal_name,
        desired_state=tuple(
            PredicateSpec(str(key), value)
            for key, value in sorted(final_state.items(), key=lambda item: str(item[0]))
        ),
    )
    payload = {
        "arena_id": arena_id,
        "purpose_digest": purpose_digest,
        "goal": goal.to_dict(),
        "actions": [action.to_dict() for action in action_specs],
    }
    return PlanningBoard(
        board_id=f"board_{stable_digest(payload, digest_size=12)}",
        arena_id=arena_id,
        purpose_digest=purpose_digest,
        goal=goal,
        actions=action_specs,
        current_state_refs=tuple(current_state_refs),
    )


def _finding(
    findings: list[ContinuityFinding],
    level: BoardContinuityLevel,
    code: str,
    message: str,
    action_id: str,
) -> None:
    findings.append(ContinuityFinding(level, code, message, action_id))


def verify_board_continuity(
    board: PlanningBoard,
    *,
    evidence: Sequence[ActionContinuityEvidence] = (),
) -> BoardContinuityReport:
    """Project BC0-BC5 from board declarations and authoritative references.

    The function never executes actions, validates the referenced records, or
    grants authority. Trusted adapters must resolve those records first.
    """

    if not isinstance(board, PlanningBoard):
        raise ValueError("board must be a PlanningBoard")
    evidence_items = _records(evidence, ActionContinuityEvidence, "evidence")
    by_action = {item.action_id: item for item in evidence_items}
    if len(by_action) != len(evidence_items):
        raise ValueError("evidence must contain at most one record per action_id")
    action_ids = {action.action_id for action in board.actions}
    unknown = set(by_action) - action_ids
    if unknown:
        raise ValueError(f"evidence references unknown action IDs: {sorted(unknown)}")

    findings: list[ContinuityFinding] = []
    for action in board.actions:
        for fallback_id in action.retry_policy.fallback_action_ids:
            if fallback_id not in action_ids:
                _finding(
                    findings,
                    BoardContinuityLevel.BC0_STRUCTURAL,
                    "UNKNOWN_FALLBACK_ACTION",
                    f"fallback action '{fallback_id}' is not present on the board",
                    action.action_id,
                )
            elif fallback_id == action.action_id:
                _finding(
                    findings,
                    BoardContinuityLevel.BC0_STRUCTURAL,
                    "SELF_FALLBACK_ACTION",
                    "an action cannot fall back to itself",
                    action.action_id,
                )

        if not action.effects:
            _finding(
                findings,
                BoardContinuityLevel.BC1_TYPED,
                "MISSING_EFFECTS",
                "typed actions must declare at least one effect",
                action.action_id,
            )
        if not action.verifier_ids:
            _finding(
                findings,
                BoardContinuityLevel.BC1_TYPED,
                "MISSING_VERIFIER_CONTRACT",
                "typed actions must declare at least one verifier or gate",
                action.action_id,
            )

        item = by_action.get(action.action_id)
        if item is None or not item.constrained_evidence_refs:
            _finding(
                findings,
                BoardContinuityLevel.BC2_CONSTRAINED,
                "MISSING_CONSTRAINT_EVIDENCE",
                "no exact reference proves current constraints are satisfiable",
                action.action_id,
            )
        if action.reversibility is ReversibilityClass.UNSPECIFIED:
            _finding(
                findings,
                BoardContinuityLevel.BC2_CONSTRAINED,
                "UNCLASSIFIED_REVERSIBILITY",
                "action reversibility has not been classified",
                action.action_id,
            )
        if action.reversibility is not ReversibilityClass.REVERSIBLE and not action.idempotency_key:
            _finding(
                findings,
                BoardContinuityLevel.BC2_CONSTRAINED,
                "MISSING_IDEMPOTENCY_KEY",
                "non-reversible or unspecified actions require an idempotency key",
                action.action_id,
            )

        grounded = set(() if item is None else item.grounded_evidence_refs)
        if not grounded:
            _finding(
                findings,
                BoardContinuityLevel.BC3_GROUNDED,
                "MISSING_GROUNDING_EVIDENCE",
                "action has no resolved exact grounding reference",
                action.action_id,
            )
        unresolved = set(action.evidence_refs) - grounded
        if unresolved:
            _finding(
                findings,
                BoardContinuityLevel.BC3_GROUNDED,
                "UNRESOLVED_GROUNDING_REFERENCE",
                f"declared grounding refs were not resolved: {sorted(unresolved)}",
                action.action_id,
            )

        if action.authority_requirement is AuthorityRequirement.UNSPECIFIED:
            _finding(
                findings,
                BoardContinuityLevel.BC4_AUTHORIZED,
                "UNSPECIFIED_AUTHORITY_REQUIREMENT",
                "authority requirement must be explicitly classified",
                action.action_id,
            )
        if item is None or not item.authority_decision_ids:
            _finding(
                findings,
                BoardContinuityLevel.BC4_AUTHORIZED,
                "MISSING_AUTHORITY_DECISION",
                "action-bound authority or policy-classification evidence is missing",
                action.action_id,
            )

        receipts = () if item is None else item.verifier_receipts
        receipt_verifiers = {receipt.verifier_id for receipt in receipts}
        undeclared = receipt_verifiers - set(action.verifier_ids)
        missing = set(action.verifier_ids) - receipt_verifiers
        if undeclared:
            _finding(
                findings,
                BoardContinuityLevel.BC5_VERIFIED,
                "UNDECLARED_VERIFIER_RECEIPT",
                f"receipts reference undeclared verifiers: {sorted(undeclared)}",
                action.action_id,
            )
        if missing:
            _finding(
                findings,
                BoardContinuityLevel.BC5_VERIFIED,
                "MISSING_VERIFIER_RECEIPT",
                f"declared verifiers lack bound receipts: {sorted(missing)}",
                action.action_id,
            )

    failed = {finding.level for finding in findings if finding.blocking}
    return BoardContinuityReport(
        board_id=board.board_id,
        board_digest=board.digest,
        passed_levels=tuple(level for level in _CONTINUITY_ORDER if level not in failed),
        findings=tuple(findings),
    )
