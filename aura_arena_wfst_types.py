"""Typed contracts for Aura's shared guarded Arena WFST fabric.

Grammar manifests remain declarative and may reference registered guards, grounded
capabilities, and C2 repository-local route capsules. They cannot embed executable
code, prompts, secrets, or authority-bearing hooks.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

ARENA_WFST_TYPES_VERSION = "AURA_ARENA_WFST_TYPES_V2"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


@dataclass(frozen=True)
class GuardSpec:
    guard_id: str
    args: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: dict[str, Any] | str) -> "GuardSpec":
        if isinstance(value, str):
            return cls(guard_id=value)
        if not isinstance(value, dict):
            raise TypeError("guard must be a string or object")
        guard_id = str(value.get("id") or value.get("guard_id") or "").strip()
        if not guard_id:
            raise ValueError("guard id is required")
        args = value.get("args") or {}
        if not isinstance(args, dict):
            raise TypeError(f"guard args for {guard_id} must be an object")
        return cls(guard_id=guard_id, args=dict(args))

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.guard_id, "args": dict(self.args)}


@dataclass(frozen=True)
class SoftWeightProfile:
    """Static ranking hints. Dynamic measurements are supplied by the runtime."""

    base_priority: float = 0.5
    empirical_uncertainty: float = 1.0
    context_switch_cost: float = 0.0
    latency_cost: float | None = None
    token_cost: float | None = None
    thermal_cost: float | None = None
    user_fit: float = 0.5

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "SoftWeightProfile":
        data = dict(value or {})
        return cls(
            base_priority=_bounded(data.get("base_priority", 0.5)),
            empirical_uncertainty=_bounded(data.get("empirical_uncertainty", 1.0)),
            context_switch_cost=_nonnegative(data.get("context_switch_cost", 0.0)),
            latency_cost=_optional_nonnegative(data.get("latency_cost")),
            token_cost=_optional_nonnegative(data.get("token_cost")),
            thermal_cost=_optional_nonnegative(data.get("thermal_cost")),
            user_fit=_bounded(data.get("user_fit", 0.5)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ArenaTransition:
    transition_id: str
    arena_id: str
    grammar_version: str
    from_state: str
    accepted_input_symbols: tuple[str, ...]
    aliases: tuple[str, ...]
    output_symbol: str
    next_state: str
    hard_guards: tuple[GuardSpec, ...] = ()
    requested_capabilities: tuple[str, ...] = ()
    required_evidence: tuple[str, ...] = ()
    produced_evidence: tuple[str, ...] = ()
    verifier_requirement: str = "none"
    approval_requirement: str = "none"
    risk: str = "low"
    soft_weight_profile: SoftWeightProfile = field(default_factory=SoftWeightProfile)
    morphology_profile_ref: str = ""
    route_capsule_ref: str = ""
    capsule_feature_flag: str = ""
    ui_label: str = ""
    ui_description: str = ""
    explanation_ref: str = ""
    rollback_transition: str = ""
    deprecation_status: str = "active"
    provenance: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        arena_id: str,
        grammar_version: str,
    ) -> "ArenaTransition":
        if not isinstance(data, dict):
            raise TypeError("transition must be an object")
        transition_id = _required_text(data, "transition_id")
        from_state = _required_text(data, "from_state")
        next_state = _required_text(data, "next_state")
        output_symbol = _required_text(data, "output_symbol")
        symbols = _text_tuple(data.get("accepted_input_symbols") or (transition_id,))
        aliases = _text_tuple(data.get("aliases") or ())
        guards = tuple(GuardSpec.from_dict(item) for item in data.get("hard_guards", ()) or ())
        return cls(
            transition_id=transition_id,
            arena_id=arena_id,
            grammar_version=grammar_version,
            from_state=from_state,
            accepted_input_symbols=symbols,
            aliases=aliases,
            output_symbol=output_symbol,
            next_state=next_state,
            hard_guards=guards,
            requested_capabilities=_text_tuple(data.get("requested_capabilities") or ()),
            required_evidence=_text_tuple(data.get("required_evidence") or ()),
            produced_evidence=_text_tuple(data.get("produced_evidence") or ()),
            verifier_requirement=str(data.get("verifier_requirement") or "none").strip().lower(),
            approval_requirement=str(data.get("approval_requirement") or "none").strip().lower(),
            risk=str(data.get("risk") or "low").strip().lower(),
            soft_weight_profile=SoftWeightProfile.from_dict(data.get("soft_weight_profile")),
            morphology_profile_ref=str(data.get("morphology_profile_ref") or "").strip(),
            route_capsule_ref=str(data.get("route_capsule_ref") or "").strip(),
            capsule_feature_flag=str(data.get("capsule_feature_flag") or "").strip(),
            ui_label=str(data.get("ui_label") or transition_id).strip(),
            ui_description=str(data.get("ui_description") or "").strip(),
            explanation_ref=str(data.get("explanation_ref") or "").strip(),
            rollback_transition=str(data.get("rollback_transition") or "").strip(),
            deprecation_status=str(data.get("deprecation_status") or "active").strip().lower(),
            provenance=dict(data.get("provenance") or {}),
        )

    def input_phrases(self) -> tuple[str, ...]:
        return _unique((*self.accepted_input_symbols, *self.aliases, self.transition_id, self.ui_label))

    def to_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "arena_id": self.arena_id,
            "grammar_version": self.grammar_version,
            "from_state": self.from_state,
            "accepted_input_symbols": list(self.accepted_input_symbols),
            "aliases": list(self.aliases),
            "output_symbol": self.output_symbol,
            "next_state": self.next_state,
            "hard_guards": [item.to_dict() for item in self.hard_guards],
            "requested_capabilities": list(self.requested_capabilities),
            "required_evidence": list(self.required_evidence),
            "produced_evidence": list(self.produced_evidence),
            "verifier_requirement": self.verifier_requirement,
            "approval_requirement": self.approval_requirement,
            "risk": self.risk,
            "soft_weight_profile": self.soft_weight_profile.to_dict(),
            "morphology_profile_ref": self.morphology_profile_ref,
            "route_capsule_ref": self.route_capsule_ref,
            "capsule_feature_flag": self.capsule_feature_flag,
            "ui_label": self.ui_label,
            "ui_description": self.ui_description,
            "explanation_ref": self.explanation_ref,
            "rollback_transition": self.rollback_transition,
            "deprecation_status": self.deprecation_status,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True)
class CompiledArenaGrammar:
    arena_id: str
    arena_version: str
    grammar_version: str
    start_state: str
    states: tuple[str, ...]
    transitions: tuple[ArenaTransition, ...]
    manifest_digest: str
    source_path: str = ""
    meta_grammar: bool = False

    def outgoing(self, state: str) -> tuple[ArenaTransition, ...]:
        return tuple(
            transition
            for transition in self.transitions
            if transition.from_state == state or (self.meta_grammar and transition.from_state == "*")
        )

    def transition_by_id(self, transition_id: str) -> ArenaTransition | None:
        wanted = str(transition_id or "").strip()
        return next((item for item in self.transitions if item.transition_id == wanted), None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": ARENA_WFST_TYPES_VERSION,
            "arena_id": self.arena_id,
            "arena_version": self.arena_version,
            "grammar_version": self.grammar_version,
            "start_state": self.start_state,
            "states": list(self.states),
            "transitions": [item.to_dict() for item in self.transitions],
            "manifest_digest": self.manifest_digest,
            "source_path": self.source_path,
            "meta_grammar": self.meta_grammar,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }


@dataclass(frozen=True)
class GuardResult:
    guard_id: str
    passed: bool
    reason: str
    missing_evidence: tuple[str, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "guard_id": self.guard_id,
            "passed": self.passed,
            "reason": self.reason,
            "missing_evidence": list(self.missing_evidence),
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class RankVector:
    unresolved_risk: float
    declared_evidence_gap: float
    empirical_uncertainty: float
    semantic_ambiguity: float
    context_switch_cost: float
    latency_cost: float
    token_cost: float
    thermal_cost: float
    negative_semantic_fit: float
    negative_user_fit: float
    stable_transition_id: str
    measurement_classes: dict[str, str] = field(default_factory=dict)
    negative_capsule_resonance: float = 0.0

    def sort_key(self) -> tuple[Any, ...]:
        return (
            self.unresolved_risk,
            self.declared_evidence_gap,
            self.empirical_uncertainty,
            self.semantic_ambiguity,
            self.negative_capsule_resonance,
            self.context_switch_cost,
            self.latency_cost,
            self.token_cost,
            self.thermal_cost,
            self.negative_semantic_fit,
            self.negative_user_fit,
            self.stable_transition_id,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "unresolved_risk": self.unresolved_risk,
            "declared_evidence_gap": self.declared_evidence_gap,
            "empirical_uncertainty": self.empirical_uncertainty,
            "semantic_ambiguity": self.semantic_ambiguity,
            "negative_capsule_resonance": self.negative_capsule_resonance,
            "context_switch_cost": self.context_switch_cost,
            "latency_cost": self.latency_cost,
            "token_cost": self.token_cost,
            "thermal_cost": self.thermal_cost,
            "negative_semantic_fit": self.negative_semantic_fit,
            "negative_user_fit": self.negative_user_fit,
            "stable_transition_id": self.stable_transition_id,
            "measurement_classes": dict(self.measurement_classes),
        }


def _required_text(data: dict[str, Any], key: str) -> str:
    value = str(data.get(key) or "").strip()
    if not value:
        raise ValueError(f"{key} is required")
    return value


def _text_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        value = (value,)
    if not isinstance(value, (list, tuple, set)):
        raise TypeError("expected a string or sequence of strings")
    return _unique(str(item).strip() for item in value if str(item).strip())


def _unique(values: Any) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = str(raw)
        if value not in seen:
            seen.add(value)
            result.append(value)
    return tuple(result)


def _bounded(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return max(0.0, min(1.0, number))


def _nonnegative(value: Any) -> float:
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return 0.0


def _optional_nonnegative(value: Any) -> float | None:
    return None if value is None else _nonnegative(value)
