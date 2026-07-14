"""Domain-neutral, proposal-only Planning Board contracts for AuraOS.

The Planning Board is an intermediate representation for possible action. It does
not execute tools, grant authority, mutate authoritative state, or replace exact
sidecars. Existing planners may project proposals into this module while their
runtime behaviour remains unchanged.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import json
import math
from typing import Any, Iterable, Mapping, Sequence


PLANNING_BOARD_VERSION = "AURA_PLANNING_BOARD_V1"
SCHEMA_VERSION = "1.0"
PROPOSAL_ONLY = True


class ContinuityLevel(str, Enum):
    BC0_STRUCTURAL = "BC0_STRUCTURAL"
    BC1_TYPED = "BC1_TYPED"
    BC2_CONSTRAINED = "BC2_CONSTRAINED"
    BC3_GROUNDED = "BC3_GROUNDED"
    BC4_AUTHORIZED = "BC4_AUTHORIZED"
    BC5_VERIFIED = "BC5_VERIFIED"


class PortDirection(str, Enum):
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"


class ReversibilityClass(str, Enum):
    UNSPECIFIED = "UNSPECIFIED"
    REVERSIBLE = "REVERSIBLE"
    COMPENSATABLE = "COMPENSATABLE"
    TIME_LIMITED_REVERSAL = "TIME_LIMITED_REVERSAL"
    IRREVERSIBLE = "IRREVERSIBLE"
    HUMAN_REMEDIATION_REQUIRED = "HUMAN_REMEDIATION_REQUIRED"


class AuthorityRequirement(str, Enum):
    NONE = "NONE"
    INDIVIDUAL = "INDIVIDUAL"
    DELEGATED = "DELEGATED"
    QUORUM = "QUORUM"
    EXTERNAL_POLICY = "EXTERNAL_POLICY"


class ConstraintKind(str, Enum):
    PRECONDITION = "PRECONDITION"
    POLICY = "POLICY"
    RESOURCE = "RESOURCE"
    BUDGET = "BUDGET"
    TEMPORAL = "TEMPORAL"
    OTHER = "OTHER"


def _canonicalize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return _canonicalize(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _canonicalize(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (tuple, list)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, (set, frozenset)):
        items = [_canonicalize(item) for item in value]
        return sorted(items, key=lambda item: json.dumps(item, sort_keys=True, default=str))
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite floats are not permitted")
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(
        _canonicalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def stable_digest(value: Any, *, digest_size: int = 16) -> str:
    size = int(digest_size)
    if not 1 <= size <= 64:
        raise ValueError("digest_size must be between 1 and 64 bytes")
    return hashlib.blake2b(canonical_json(value).encode("utf-8"), digest_size=size).hexdigest()


def _required(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} must not be empty")
    return text


def _enum(value: Any, enum_type: type[Enum], field_name: str) -> str:
    raw = value.value if isinstance(value, Enum) else str(value).upper()
    allowed = {item.value for item in enum_type}
    if raw not in allowed:
        raise ValueError(f"unknown {field_name}: {raw}")
    return raw


def _strict_bool(value: Any, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field_name} must be a boolean")
    return value


def _non_negative(value: Any, field_name: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{field_name} must be finite and non-negative")
    return number


def _unique(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    normalized = tuple(_required(value, field_name) for value in values)
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{field_name} contains duplicates")
    return normalized


@dataclass(frozen=True)
class TypedPort:
    port_id: str
    direction: str
    value_type: str
    required: bool = True
    unit: str | None = None
    schema_ref: str | None = None
    cardinality: str = "ONE"

    def __post_init__(self) -> None:
        object.__setattr__(self, "port_id", _required(self.port_id, "port_id"))
        object.__setattr__(self, "direction", _enum(self.direction, PortDirection, "direction"))
        object.__setattr__(self, "value_type", _required(self.value_type, "value_type"))
        object.__setattr__(self, "required", _strict_bool(self.required, "required"))
        object.__setattr__(self, "cardinality", _required(self.cardinality, "cardinality").upper())
        if self.unit is not None:
            object.__setattr__(self, "unit", _required(self.unit, "unit"))
        if self.schema_ref is not None:
            object.__setattr__(self, "schema_ref", _required(self.schema_ref, "schema_ref"))


@dataclass(frozen=True)
class PredicateSpec:
    predicate_id: str
    fact_key: str
    operator: str
    expected: Any

    def __post_init__(self) -> None:
        object.__setattr__(self, "predicate_id", _required(self.predicate_id, "predicate_id"))
        object.__setattr__(self, "fact_key", _required(self.fact_key, "fact_key"))
        object.__setattr__(self, "operator", _required(self.operator, "operator").upper())
        canonical_json(self.expected)


@dataclass(frozen=True)
class EffectSpec:
    effect_id: str
    fact_key: str
    value: Any

    def __post_init__(self) -> None:
        object.__setattr__(self, "effect_id", _required(self.effect_id, "effect_id"))
        object.__setattr__(self, "fact_key", _required(self.fact_key, "fact_key"))
        canonical_json(self.value)


@dataclass(frozen=True)
class ConstraintSpec:
    constraint_id: str
    kind: str
    description: str
    evidence_ref: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "constraint_id", _required(self.constraint_id, "constraint_id"))
        object.__setattr__(self, "kind", _enum(self.kind, ConstraintKind, "kind"))
        object.__setattr__(self, "description", _required(self.description, "description"))
        if self.evidence_ref is not None:
            object.__setattr__(self, "evidence_ref", _required(self.evidence_ref, "evidence_ref"))


@dataclass(frozen=True)
class ResourceDemand:
    cpu_ms: float | None = None
    memory_bytes: float | None = None
    context_tokens: float | None = None
    network_egress_bytes: float | None = None
    estimated_cost: float | None = None
    human_attention_minutes: float | None = None

    def __post_init__(self) -> None:
        for name in (
            "cpu_ms",
            "memory_bytes",
            "context_tokens",
            "network_egress_bytes",
            "estimated_cost",
            "human_attention_minutes",
        ):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _non_negative(value, name))


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 1
    fallback_action_ids: tuple[str, ...] = ()
    recovery_action_id: str | None = None

    def __post_init__(self) -> None:
        attempts = int(self.max_attempts)
        if isinstance(self.max_attempts, bool) or attempts < 1:
            raise ValueError("max_attempts must be an integer greater than zero")
        object.__setattr__(self, "max_attempts", attempts)
        object.__setattr__(
            self,
            "fallback_action_ids",
            _unique(self.fallback_action_ids, "fallback_action_ids"),
        )
        if self.recovery_action_id is not None:
            object.__setattr__(
                self,
                "recovery_action_id",
                _required(self.recovery_action_id, "recovery_action_id"),
            )


@dataclass(frozen=True)
class VerifierRequirement:
    verifier_id: str
    receipt_ref: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "verifier_id", _required(self.verifier_id, "verifier_id"))
        if self.receipt_ref is not None:
            object.__setattr__(self, "receipt_ref", _required(self.receipt_ref, "receipt_ref"))


@dataclass(frozen=True)
class AuthoritySpec:
    requirement: str
    policy_ref: str
    governance_function: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "requirement",
            _enum(self.requirement, AuthorityRequirement, "authority requirement"),
        )
        # Classification remains external even for NONE; absence is not evidence.
        object.__setattr__(self, "policy_ref", _required(self.policy_ref, "policy_ref"))
        if self.governance_function is not None:
            object.__setattr__(
                self,
                "governance_function",
                _required(self.governance_function, "governance_function").upper(),
            )


@dataclass(frozen=True)
class GoalSpec:
    goal_id: str
    description: str
    desired_predicates: tuple[PredicateSpec, ...]
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "goal_id", _required(self.goal_id, "goal_id"))
        object.__setattr__(self, "description", _required(self.description, "description"))
        if not self.desired_predicates:
            raise ValueError("desired_predicates must not be empty")
        _assert_unique_ids(self.desired_predicates, "predicate_id", "desired_predicates")
        object.__setattr__(self, "evidence_refs", _unique(self.evidence_refs, "evidence_refs"))


@dataclass(frozen=True)
class ActionSpec:
    action_id: str
    name: str
    domain: str
    preconditions: tuple[PredicateSpec, ...] = ()
    effects: tuple[EffectSpec, ...] = ()
    constraints: tuple[ConstraintSpec, ...] = ()
    ports: tuple[TypedPort, ...] = ()
    capability_requirements: tuple[str, ...] = ()
    verifier_requirements: tuple[VerifierRequirement, ...] = ()
    authority: AuthoritySpec | None = None
    resource_demand: ResourceDemand | None = None
    reversibility: str = ReversibilityClass.UNSPECIFIED.value
    idempotency_key: str | None = None
    retry_policy: RetryPolicy | None = None
    evidence_refs: tuple[str, ...] = ()
    proposal_only: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "action_id", _required(self.action_id, "action_id"))
        object.__setattr__(self, "name", _required(self.name, "name"))
        object.__setattr__(self, "domain", _required(self.domain, "domain"))
        _assert_unique_ids(self.preconditions, "predicate_id", "preconditions")
        _assert_unique_ids(self.effects, "effect_id", "effects")
        _assert_unique_ids(self.constraints, "constraint_id", "constraints")
        _assert_unique_ids(self.ports, "port_id", "ports")
        _assert_unique_ids(self.verifier_requirements, "verifier_id", "verifier_requirements")
        object.__setattr__(
            self,
            "capability_requirements",
            _unique(self.capability_requirements, "capability_requirements"),
        )
        object.__setattr__(self, "evidence_refs", _unique(self.evidence_refs, "evidence_refs"))
        object.__setattr__(
            self,
            "reversibility",
            _enum(self.reversibility, ReversibilityClass, "reversibility"),
        )
        if self.idempotency_key is not None:
            object.__setattr__(
                self,
                "idempotency_key",
                _required(self.idempotency_key, "idempotency_key"),
            )
        if _strict_bool(self.proposal_only, "proposal_only") is not True:
            raise ValueError("Planning Board actions must remain proposal_only")

    def to_dict(self) -> dict[str, Any]:
        return _canonicalize(self)

    @property
    def digest(self) -> str:
        return stable_digest(self.to_dict())


@dataclass(frozen=True)
class PlanningBoard:
    board_id: str
    goal: GoalSpec
    actions: tuple[ActionSpec, ...]
    initial_state_ref: str
    plan_ref: str | None = None
    proposal_only: bool = True
    version: str = PLANNING_BOARD_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "board_id", _required(self.board_id, "board_id"))
        object.__setattr__(self, "initial_state_ref", _required(self.initial_state_ref, "initial_state_ref"))
        if self.plan_ref is not None:
            object.__setattr__(self, "plan_ref", _required(self.plan_ref, "plan_ref"))
        if _strict_bool(self.proposal_only, "proposal_only") is not True:
            raise ValueError("Planning Board must remain proposal_only")
        _assert_unique_ids(self.actions, "action_id", "actions")
        action_ids = {action.action_id for action in self.actions}
        for action in self.actions:
            if action.retry_policy is None:
                continue
            refs = set(action.retry_policy.fallback_action_ids)
            if action.retry_policy.recovery_action_id:
                refs.add(action.retry_policy.recovery_action_id)
            unresolved = refs - action_ids
            if unresolved:
                raise ValueError(
                    f"action '{action.action_id}' has unresolved retry references: {sorted(unresolved)}"
                )

    def to_dict(self) -> dict[str, Any]:
        return _canonicalize(self)

    @property
    def digest(self) -> str:
        return stable_digest(self.to_dict())


@dataclass(frozen=True)
class ContinuityEvidence:
    constraint_refs: tuple[str, ...] = ()
    grounding_refs: tuple[str, ...] = ()
    authority_decision_refs: tuple[str, ...] = ()
    verifier_receipt_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in (
            "constraint_refs",
            "grounding_refs",
            "authority_decision_refs",
            "verifier_receipt_refs",
        ):
            object.__setattr__(self, field_name, _unique(getattr(self, field_name), field_name))


@dataclass(frozen=True)
class ContinuityResult:
    highest_level: str | None
    passed_levels: tuple[str, ...]
    blocking_reasons: tuple[str, ...]
    board_digest: str

    @property
    def complete(self) -> bool:
        return self.highest_level == ContinuityLevel.BC5_VERIFIED.value


def _assert_unique_ids(items: Sequence[Any], attribute: str, field_name: str) -> None:
    ids = tuple(_required(getattr(item, attribute), attribute) for item in items)
    if len(set(ids)) != len(ids):
        raise ValueError(f"{field_name} contains duplicate {attribute} values")


def project_continuity(
    board: PlanningBoard,
    evidence: ContinuityEvidence | None = None,
) -> ContinuityResult:
    """Project contiguous BC0-BC5 status without granting authority.

    BC0 and BC1 are determined from the immutable board structure. BC2-BC5 require
    explicit external references. A failed earlier level prevents later levels from
    being reported as passed, even when later references are supplied.
    """
    supplied = evidence or ContinuityEvidence()
    passed: list[str] = []
    blocked: list[str] = []

    # Construction already validates identifiers, references, and proposal-only state.
    passed.append(ContinuityLevel.BC0_STRUCTURAL.value)

    typed_ok = all(
        port.value_type and port.direction in {item.value for item in PortDirection}
        for action in board.actions
        for port in action.ports
    )
    if not typed_ok:
        blocked.append("BC1_TYPED: invalid typed port")
        return _continuity_result(board, passed, blocked)
    passed.append(ContinuityLevel.BC1_TYPED.value)

    required_constraints = {
        constraint.evidence_ref
        for action in board.actions
        for constraint in action.constraints
        if constraint.evidence_ref
    }
    if not required_constraints.issubset(set(supplied.constraint_refs)):
        missing = sorted(required_constraints - set(supplied.constraint_refs))
        blocked.append(f"BC2_CONSTRAINED: missing constraint refs {missing}")
        return _continuity_result(board, passed, blocked)
    passed.append(ContinuityLevel.BC2_CONSTRAINED.value)

    required_grounding = set(board.goal.evidence_refs)
    required_grounding.update(ref for action in board.actions for ref in action.evidence_refs)
    if not required_grounding.issubset(set(supplied.grounding_refs)):
        missing = sorted(required_grounding - set(supplied.grounding_refs))
        blocked.append(f"BC3_GROUNDED: missing grounding refs {missing}")
        return _continuity_result(board, passed, blocked)
    passed.append(ContinuityLevel.BC3_GROUNDED.value)

    authority_required = any(action.authority is not None for action in board.actions)
    if authority_required and not supplied.authority_decision_refs:
        blocked.append("BC4_AUTHORIZED: missing authority decision refs")
        return _continuity_result(board, passed, blocked)
    passed.append(ContinuityLevel.BC4_AUTHORIZED.value)

    required_receipts = {
        requirement.receipt_ref
        for action in board.actions
        for requirement in action.verifier_requirements
        if requirement.receipt_ref
    }
    declared_without_receipt = sorted(
        requirement.verifier_id
        for action in board.actions
        for requirement in action.verifier_requirements
        if requirement.receipt_ref is None
    )
    if declared_without_receipt:
        blocked.append(
            f"BC5_VERIFIED: verifier requirements lack bound receipts {declared_without_receipt}"
        )
        return _continuity_result(board, passed, blocked)
    if not required_receipts.issubset(set(supplied.verifier_receipt_refs)):
        missing = sorted(required_receipts - set(supplied.verifier_receipt_refs))
        blocked.append(f"BC5_VERIFIED: missing verifier receipt refs {missing}")
        return _continuity_result(board, passed, blocked)
    passed.append(ContinuityLevel.BC5_VERIFIED.value)
    return _continuity_result(board, passed, blocked)


def _continuity_result(
    board: PlanningBoard,
    passed: Sequence[str],
    blocked: Sequence[str],
) -> ContinuityResult:
    return ContinuityResult(
        highest_level=passed[-1] if passed else None,
        passed_levels=tuple(passed),
        blocking_reasons=tuple(blocked),
        board_digest=board.digest,
    )


def board_from_goap_plan(plan: Any, *, initial_state_ref: str) -> PlanningBoard:
    """Shadow-project an existing GoalPlan without changing or enriching it.

    The adapter intentionally invents neither evidence, authority, reversibility,
    capability leases, nor verifier receipts. Existing GOAP gates are represented as
    verifier declarations without receipts, so the projection cannot reach BC5 until
    authoritative receipts are supplied by later runtime stages.
    """
    plan_id = _required(getattr(plan, "plan_id", ""), "plan.plan_id")
    goal_text = _required(getattr(plan, "goal", ""), "plan.goal")
    actions: list[ActionSpec] = []
    for index, action in enumerate(tuple(getattr(plan, "actions", ()) or ())):
        action_name = _required(getattr(action, "name", ""), "action.name")
        preconditions = tuple(
            PredicateSpec(
                predicate_id=f"{action_name}:pre:{key}",
                fact_key=str(key),
                operator="EQUALS",
                expected=value,
            )
            for key, value in sorted(dict(getattr(action, "preconditions", {})).items())
        )
        effects = tuple(
            EffectSpec(
                effect_id=f"{action_name}:effect:{key}",
                fact_key=str(key),
                value=value,
            )
            for key, value in sorted(dict(getattr(action, "effects", {})).items())
        )
        verifier_requirements = tuple(
            VerifierRequirement(verifier_id=str(gate), receipt_ref=None)
            for gate in tuple(getattr(action, "must_pass_gates", ()) or ())
        )
        required_organ = str(getattr(action, "required_organ", "") or "").strip()
        capabilities = (f"organ:{required_organ}",) if required_organ else ()
        actions.append(
            ActionSpec(
                action_id=f"{plan_id}:{index}:{action_name}",
                name=action_name,
                domain=_required(getattr(action, "domain", ""), "action.domain"),
                preconditions=preconditions,
                effects=effects,
                capability_requirements=capabilities,
                verifier_requirements=verifier_requirements,
                authority=None,
                resource_demand=ResourceDemand(
                    estimated_cost=_non_negative(getattr(action, "cost", 0.0), "action.cost")
                ),
                reversibility=ReversibilityClass.UNSPECIFIED.value,
                proposal_only=True,
            )
        )
    if not actions:
        raise ValueError("plan.actions must not be empty")

    final_state = dict(getattr(plan, "final_state", {}) or {})
    desired = tuple(
        PredicateSpec(
            predicate_id=f"{plan_id}:goal:{key}",
            fact_key=str(key),
            operator="EQUALS",
            expected=value,
        )
        for key, value in sorted(final_state.items())
    )
    if not desired:
        desired = (
            PredicateSpec(
                predicate_id=f"{plan_id}:goal:declared",
                fact_key="goal_declared",
                operator="EQUALS",
                expected=True,
            ),
        )
    goal = GoalSpec(
        goal_id=f"goal:{plan_id}",
        description=goal_text,
        desired_predicates=desired,
    )
    return PlanningBoard(
        board_id=f"board:{plan_id}",
        goal=goal,
        actions=tuple(actions),
        initial_state_ref=_required(initial_state_ref, "initial_state_ref"),
        plan_ref=plan_id,
        proposal_only=True,
    )
