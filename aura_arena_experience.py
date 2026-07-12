"""Authoritative observable Arena experience records with C2 capsule provenance."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
import re
import secrets
import time
from typing import Any, Mapping

ARENA_EXPERIENCE_VERSION = "AURA_ARENA_EXPERIENCE_V3"
OUTCOME_VECTOR_VERSION = "AURA_OUTCOME_VECTOR_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

_DIMENSIONS = (
    "task_progress",
    "evidence_quality",
    "verification_quality",
    "safety_quality",
    "human_alignment",
    "cost_efficiency",
    "latency_efficiency",
    "abstention_quality",
    "recovery_quality",
)
_DEFAULT_WEIGHTS = {
    "task_progress": 0.20,
    "evidence_quality": 0.15,
    "verification_quality": 0.20,
    "safety_quality": 0.20,
    "human_alignment": 0.10,
    "cost_efficiency": 0.05,
    "latency_efficiency": 0.05,
    "abstention_quality": 0.03,
    "recovery_quality": 0.02,
}
_SECRET_KEY = re.compile(
    r"(?i)(api[_-]?key|access[_-]?token|auth[_-]?token|authorization|secret|"
    r"password|private[_-]?key|cookie)"
)
_SECRET_VALUES = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/-]{12,}"),
)
_FORBIDDEN_REASONING_KEYS = {
    "chain_of_thought",
    "chain-of-thought",
    "hidden_reasoning",
    "private_reasoning",
    "scratchpad",
    "internal_monologue",
}


@dataclass(frozen=True)
class OutcomeVector:
    """Nullable observable dimensions; every projection remains proposal-only."""

    terminal_class: str
    task_progress: float | None = None
    evidence_quality: float | None = None
    verification_quality: float | None = None
    safety_quality: float | None = None
    human_alignment: float | None = None
    cost_efficiency: float | None = None
    latency_efficiency: float | None = None
    abstention_quality: float | None = None
    recovery_quality: float | None = None
    measurement_classes: dict[str, str] = field(default_factory=dict)
    labels: tuple[str, ...] = ()
    version: str = OUTCOME_VECTOR_VERSION
    proposal_only: bool = True
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = False

    def __post_init__(self) -> None:
        if not str(self.terminal_class).strip():
            raise ValueError("terminal_class is required")
        for name in _DIMENSIONS:
            value = getattr(self, name)
            if value is not None and (
                not math.isfinite(float(value)) or not 0.0 <= float(value) <= 1.0
            ):
                raise ValueError(f"{name} must be None or in [0, 1]")
        if (
            not self.proposal_only
            or self.patch_authority != PATCH_AUTHORITY
            or self.vsa_patch_authority
        ):
            raise ValueError("OutcomeVector cannot carry authority")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OutcomeVector":
        data = dict(value or {})
        unknown = set(data) - set(cls.__dataclass_fields__)
        if unknown:
            raise ValueError(f"unknown OutcomeVector fields: {sorted(unknown)}")
        data["labels"] = tuple(str(item) for item in data.get("labels", ()) if str(item))
        data["measurement_classes"] = {
            str(key): str(item)
            for key, item in dict(data.get("measurement_classes") or {}).items()
        }
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["labels"] = list(self.labels)
        return data

    def proposal_projection(
        self, weights: Mapping[str, float] | None = None
    ) -> dict[str, Any]:
        chosen = dict(_DEFAULT_WEIGHTS if weights is None else weights)
        if set(chosen) - set(_DIMENSIONS):
            raise ValueError("unknown outcome projection dimension")
        total = sum(max(0.0, float(value)) for value in chosen.values())
        observed: dict[str, float] = {}
        mass = 0.0
        score = 0.0
        for name, raw_weight in chosen.items():
            value = getattr(self, name)
            weight = max(0.0, float(raw_weight))
            if value is None or weight == 0.0:
                continue
            observed[name] = float(value)
            mass += weight
            score += weight * float(value)
        return {
            "score": round(score / mass, 6) if mass else None,
            "coverage": round(mass / total, 6) if total else 0.0,
            "observed_dimensions": observed,
            "weights": chosen,
            "proposal_only": True,
            "runtime_authority": False,
        }


@dataclass(frozen=True)
class ArenaExperience:
    experience_id: str
    correlation_id: str
    task_id: str
    workflow_id: str
    arena_id: str
    arena_version: str
    grammar_version: str
    grammar_manifest_digest: str
    runtime_version: str
    compiler_version: str
    started_at: float
    completed_at: float
    state_before: str
    state_after: str
    selected_transition: str
    final_outcome: str
    outcome_vector: OutcomeVector
    admissible_alternatives: tuple[dict[str, Any], ...] = ()
    predictions: tuple[dict[str, Any], ...] = ()
    route_observation_digest: str = ""
    repository_commit_sha: str = ""
    working_tree_digest: str = ""
    objective_hash: str = ""
    source_hash_digest: str = ""
    provider: str = ""
    model: str = ""
    measurement_class: str = "UNAVAILABLE"
    cost_run_id: str = ""
    trace_atom_ids: tuple[str, ...] = ()
    raw_evidence_refs: tuple[str, ...] = ()
    payload: dict[str, Any] = field(default_factory=dict)
    redactions: tuple[str, ...] = ()
    # C2 fields are appended to preserve the V2 positional contract.
    intent_packet_digest: str = ""
    vsa_profile_digest: str = ""
    route_capsule_digest: str = ""
    aperture_digest: str = ""
    actual_context_digest: str = ""
    actual_tool_calls: tuple[str, ...] = ()
    actual_model: str = ""
    budget_requested: dict[str, Any] = field(default_factory=dict)
    budget_consumed: dict[str, Any] = field(default_factory=dict)
    version: str = ARENA_EXPERIENCE_VERSION
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = False
    learned_weight_patch_authority: bool = False
    crystallization_patch_authority: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["outcome_vector"] = self.outcome_vector.to_dict()
        for key in (
            "admissible_alternatives",
            "predictions",
            "trace_atom_ids",
            "raw_evidence_refs",
            "redactions",
            "actual_tool_calls",
        ):
            data[key] = list(getattr(self, key))
        return data


def build_arena_experience(
    *,
    arena_id: str,
    arena_version: str,
    grammar_version: str,
    runtime_version: str,
    compiler_version: str,
    state_before: str,
    state_after: str,
    selected_transition: str,
    final_outcome: str,
    payload: dict[str, Any] | None = None,
    grammar_manifest_digest: str = "",
    outcome_vector: OutcomeVector | Mapping[str, Any] | None = None,
    admissible_alternatives: Any = None,
    predictions: Any = None,
    experience_id: str = "",
    correlation_id: str = "",
    task_id: str = "",
    workflow_id: str = "",
    started_at: float | None = None,
    completed_at: float | None = None,
    repository_commit_sha: str = "",
    working_tree_digest: str = "",
    objective: str = "",
    source_hashes: Any = (),
    provider: str = "",
    model: str = "",
    measurement_class: str = "UNAVAILABLE",
    cost_run_id: str = "",
    trace_atom_ids: Any = (),
    raw_evidence_refs: Any = (),
    intent_packet_digest: str = "",
    vsa_profile_digest: str = "",
    route_capsule_digest: str = "",
    aperture_digest: str = "",
    actual_context_digest: str = "",
    actual_tool_calls: Any = (),
    actual_model: str = "",
    budget_requested: Mapping[str, Any] | None = None,
    budget_consumed: Mapping[str, Any] | None = None,
) -> ArenaExperience:
    safe_payload, payload_redactions = sanitize_experience_payload(dict(payload or {}))
    route = _route_packet(safe_payload)
    manifest_digest = str(
        grammar_manifest_digest or route.get("grammar_digest") or ""
    ).strip()
    if not manifest_digest:
        raise ValueError("grammar_manifest_digest is required for every ArenaExperience")

    derived_alternatives, derived_predictions = capture_route_observation(route)
    safe_alternatives, alternative_redactions = sanitize_experience_payload(
        derived_alternatives if admissible_alternatives is None else list(admissible_alternatives)
    )
    safe_predictions, prediction_redactions = sanitize_experience_payload(
        derived_predictions if predictions is None else list(predictions)
    )
    if not isinstance(safe_alternatives, list) or not all(
        isinstance(item, dict) for item in safe_alternatives
    ):
        raise ValueError("admissible_alternatives must be objects")
    if not isinstance(safe_predictions, list) or not all(
        isinstance(item, dict) for item in safe_predictions
    ):
        raise ValueError("predictions must be objects")

    vector = (
        derive_outcome_vector(
            final_outcome=final_outcome,
            payload=safe_payload,
            state_before=state_before,
            state_after=state_after,
        )
        if outcome_vector is None
        else (
            outcome_vector
            if isinstance(outcome_vector, OutcomeVector)
            else OutcomeVector.from_dict(outcome_vector)
        )
    )
    now = time.time()
    started = float(now if started_at is None else started_at)
    completed = float(now if completed_at is None else completed_at)
    if completed < started:
        raise ValueError("completed_at cannot be earlier than started_at")

    capsule = _capsule_observation(route, safe_payload)
    exp_id = experience_id or f"EXP-{secrets.token_hex(12)}"
    correlation = correlation_id or (
        f"CORR-{_hash(f'{arena_id}:{task_id}:{workflow_id}:{started}')[:16]}"
    )
    return ArenaExperience(
        experience_id=_required(exp_id, "experience_id"),
        correlation_id=_required(correlation, "correlation_id"),
        task_id=str(task_id or ""),
        workflow_id=str(workflow_id or ""),
        arena_id=_required(arena_id, "arena_id"),
        arena_version=_required(arena_version, "arena_version"),
        grammar_version=_required(grammar_version, "grammar_version"),
        grammar_manifest_digest=_required(manifest_digest, "grammar_manifest_digest"),
        runtime_version=_required(runtime_version, "runtime_version"),
        compiler_version=_required(compiler_version, "compiler_version"),
        started_at=started,
        completed_at=completed,
        state_before=_required(state_before, "state_before"),
        state_after=_required(state_after, "state_after"),
        selected_transition=str(selected_transition or ""),
        final_outcome=_required(final_outcome, "final_outcome"),
        outcome_vector=vector,
        admissible_alternatives=tuple(dict(item) for item in safe_alternatives),
        predictions=tuple(dict(item) for item in safe_predictions),
        route_observation_digest=canonical_observation_digest(
            selected_transition=selected_transition,
            alternatives=safe_alternatives,
            predictions=safe_predictions,
        ),
        repository_commit_sha=str(repository_commit_sha or "")[:128],
        working_tree_digest=str(working_tree_digest or "")[:256],
        objective_hash=_hash(objective) if objective else "",
        source_hash_digest=(
            _hash(
                json.dumps(
                    sorted(str(item) for item in source_hashes if str(item)),
                    separators=(",", ":"),
                )
            )
            if source_hashes
            else ""
        ),
        provider=str(provider or "")[:120],
        model=str(model or "")[:160],
        measurement_class=str(measurement_class or "UNAVAILABLE").upper(),
        cost_run_id=str(cost_run_id or "")[:160],
        trace_atom_ids=tuple(str(item) for item in trace_atom_ids if str(item)),
        raw_evidence_refs=tuple(str(item) for item in raw_evidence_refs if str(item)),
        payload=safe_payload,
        redactions=tuple(
            sorted(
                set(
                    (*payload_redactions, *alternative_redactions, *prediction_redactions)
                )
            )
        ),
        intent_packet_digest=str(
            intent_packet_digest or capsule["intent_packet_digest"]
        ),
        vsa_profile_digest=str(vsa_profile_digest or capsule["vsa_profile_digest"]),
        route_capsule_digest=str(
            route_capsule_digest or capsule["route_capsule_digest"]
        ),
        aperture_digest=str(aperture_digest or capsule["aperture_digest"]),
        actual_context_digest=str(
            actual_context_digest or capsule["actual_context_digest"]
        ),
        actual_tool_calls=tuple(
            str(item)
            for item in (actual_tool_calls or capsule["actual_tool_calls"])
            if str(item)
        ),
        actual_model=str(actual_model or capsule["actual_model"]),
        budget_requested=dict(budget_requested or capsule["budget_requested"]),
        budget_consumed=dict(budget_consumed or capsule["budget_consumed"]),
    )


def capture_route_observation(
    route: Mapping[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    packet = dict(route or {})
    alternatives = [
        dict(item) for item in packet.get("available", []) if isinstance(item, dict)
    ]
    selected = str((packet.get("selected") or {}).get("transition_id") or "")
    predictions: list[dict[str, Any]] = []
    for position, row in enumerate(alternatives):
        rank = dict(row.get("rank") or {}) if isinstance(row.get("rank"), dict) else {}
        capsule = (
            dict(row.get("route_capsule") or {})
            if isinstance(row.get("route_capsule"), dict)
            else {}
        )
        aperture = (
            dict(row.get("materialized_aperture") or {})
            if isinstance(row.get("materialized_aperture"), dict)
            else {}
        )
        predictions.append(
            {
                "transition_id": str(row.get("transition_id") or ""),
                "rank_position": position,
                "predicted_selected": str(row.get("transition_id") or "") == selected,
                "predicted_next_state": str(row.get("next_state") or ""),
                "semantic_fit": row.get("semantic_fit"),
                "capsule_resonance": capsule.get("resonance"),
                "route_capsule_digest": capsule.get("capsule_digest"),
                "aperture_digest": aperture.get("aperture_digest"),
                "rank": rank,
                "measurement_classes": dict(rank.get("measurement_classes") or {}),
                "risk": str(row.get("risk") or "unknown"),
                "required_evidence": list(row.get("required_evidence") or []),
                "produced_evidence": list(row.get("produced_evidence") or []),
                "meta_transition": bool(row.get("meta_transition")),
            }
        )
    return alternatives, predictions


def derive_outcome_vector(
    *,
    final_outcome: str,
    payload: Mapping[str, Any] | None,
    state_before: str,
    state_after: str,
) -> OutcomeVector:
    data = dict(payload or {})
    route = _route_packet(data)
    selected = dict(route.get("selected") or {})
    result = data.get("action_result") if isinstance(data.get("action_result"), dict) else {}
    terminal = str(final_outcome or "UNKNOWN").upper()
    success = {
        "ALLOWED", "COMPLETED", "PASS", "PASSED", "SUCCEEDED", "SUCCESS",
        "VERIFIED", "META_COMPLETED",
    }
    failure = {"DENIED", "FAILED", "FAIL", "ERROR", "INVALIDATED"}
    abstain = {"BLOCKED", "ABSTAINED"}
    progress = 1.0 if terminal in success else (0.0 if terminal in failure | abstain else None)

    required = {str(item) for item in selected.get("required_evidence", []) if str(item)}
    keys = {str(item) for item in data.get("evidence_keys", []) if str(item)}
    missing = {str(item) for item in result.get("missing_evidence", []) if str(item)}
    if required:
        observed = len(required & keys) if keys else max(0, len(required) - len(missing))
        evidence_quality = max(0.0, min(1.0, observed / len(required)))
    else:
        evidence_quality = 0.0 if missing else (1.0 if selected else None)

    verifier = str(selected.get("verifier_requirement") or "none").lower()
    verification_quality = (
        1.0
        if terminal in {"VERIFIED", "PASS", "PASSED"}
        or result.get("verification_ok") is True
        else (0.0 if verifier != "none" and terminal in failure else None)
    )
    violation = any(
        bool(data.get(key) or result.get(key))
        for key in (
            "active_grammar_mutated", "automatic_commit", "automatic_push",
            "automatic_merge", "learned_weight_patch_authority",
            "crystallization_patch_authority",
        )
    )
    safety_quality = 0.0 if violation else 1.0
    approval = str(selected.get("approval_requirement") or "none").lower()
    human_alignment = (
        (1.0 if terminal in success else 0.0)
        if approval not in {"", "none"}
        else None
    )
    rank = dict(selected.get("rank") or {})
    classes = dict(rank.get("measurement_classes") or {})
    return OutcomeVector(
        terminal_class=terminal,
        task_progress=progress,
        evidence_quality=evidence_quality,
        verification_quality=verification_quality,
        safety_quality=safety_quality,
        human_alignment=human_alignment,
        cost_efficiency=_efficiency(rank.get("token_cost"), classes.get("tokens")),
        latency_efficiency=_efficiency(
            rank.get("latency_cost"), classes.get("latency")
        ),
        abstention_quality=(
            1.0
            if terminal in abstain and bool(route.get("abstained") or route.get("blocked"))
            else None
        ),
        recovery_quality=(
            (1.0 if str(state_after) != str(state_before) else 0.0)
            if terminal in failure | abstain
            else None
        ),
        measurement_classes={str(key): str(value) for key, value in classes.items()},
        labels=tuple(
            item
            for item in (terminal, str(route.get("abstention_reason") or ""))
            if item
        ),
    )


def sanitize_experience_payload(value: Any) -> tuple[Any, list[str]]:
    redactions: list[str] = []

    def walk(item: Any, path: str = "") -> Any:
        if isinstance(item, dict):
            output: dict[str, Any] = {}
            for raw_key, raw_value in item.items():
                key = str(raw_key)
                child = f"{path}.{key}" if path else key
                if key.casefold() in _FORBIDDEN_REASONING_KEYS:
                    redactions.append(f"forbidden_reasoning:{child}")
                    continue
                if _SECRET_KEY.search(key):
                    redactions.append(f"secret_key:{child}")
                    output[key] = "[REDACTED]"
                    continue
                output[key] = walk(raw_value, child)
            return output
        if isinstance(item, (list, tuple, set)):
            sequence = (
                sorted(item, key=lambda value: (type(value).__name__, str(value)))
                if isinstance(item, set)
                else item
            )
            return [walk(value, f"{path}[{index}]") for index, value in enumerate(sequence)]
        if isinstance(item, bytes):
            item = item.decode("utf-8", errors="replace")
        if isinstance(item, str):
            text = item
            for pattern in _SECRET_VALUES:
                replaced = pattern.sub("[REDACTED]", text)
                if replaced != text:
                    redactions.append(f"secret_value:{path or '<root>'}")
                text = replaced
            return text
        if item is None or isinstance(item, (bool, int, float)):
            return item
        return str(item)

    return walk(value), sorted(set(redactions))


def canonical_experience_digest(experience: ArenaExperience | Mapping[str, Any]) -> str:
    data = experience.to_dict() if isinstance(experience, ArenaExperience) else dict(experience)
    return hashlib.blake2b(
        json.dumps(
            data, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str
        ).encode(),
        digest_size=20,
    ).hexdigest()


def canonical_observation_digest(
    *, selected_transition: str, alternatives: Any, predictions: Any
) -> str:
    return _hash(
        json.dumps(
            {
                "selected_transition": str(selected_transition or ""),
                "admissible_alternatives": alternatives,
                "predictions": predictions,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        )
    )


def _capsule_observation(
    route: Mapping[str, Any], payload: Mapping[str, Any]
) -> dict[str, Any]:
    selected = dict(route.get("selected") or {})
    capsule = dict(selected.get("route_capsule") or {})
    aperture = dict(selected.get("materialized_aperture") or {})
    result = payload.get("action_result") if isinstance(payload.get("action_result"), dict) else {}
    usage = (
        dict(result.get("capsule_usage") or {})
        if isinstance(result.get("capsule_usage"), dict)
        else (
            dict(payload.get("capsule_usage") or {})
            if isinstance(payload.get("capsule_usage"), dict)
            else {}
        )
    )
    context_items = usage.get("context_items") or aperture.get("actual_context_items") or []
    return {
        "intent_packet_digest": str(
            selected.get("intent_packet_digest")
            or (route.get("intent_packet") or {}).get("packet_digest")
            or ""
        ),
        "vsa_profile_digest": str(
            capsule.get("vsa_profile_digest") or selected.get("vsa_profile_digest") or ""
        ),
        "route_capsule_digest": str(
            capsule.get("capsule_digest") or aperture.get("capsule_digest") or ""
        ),
        "aperture_digest": str(aperture.get("aperture_digest") or ""),
        "actual_context_digest": (
            _hash(
                json.dumps(
                    context_items,
                    sort_keys=True,
                    separators=(",", ":"),
                    default=str,
                )
            )
            if context_items
            else ""
        ),
        "actual_tool_calls": tuple(
            str(item) for item in usage.get("tool_calls", ()) if str(item)
        ),
        "actual_model": str(usage.get("model") or aperture.get("selected_model") or ""),
        "budget_requested": dict(aperture.get("execution_budget") or {}),
        "budget_consumed": dict(
            usage.get("budget_consumed") or aperture.get("budget_consumed") or {}
        ),
    }


def _route_packet(payload: Mapping[str, Any]) -> dict[str, Any]:
    for key in ("route", "route_decision"):
        if isinstance(payload.get(key), dict):
            return dict(payload[key])
    result = payload.get("action_result")
    if isinstance(result, dict):
        for key in ("route", "route_decision"):
            if isinstance(result.get(key), dict):
                return dict(result[key])
    return {}


def _efficiency(value: Any, measurement_class: Any) -> float | None:
    if str(measurement_class or "").upper() in {"", "UNAVAILABLE", "UNKNOWN"}:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number < 0:
        return None
    return round(1.0 / (1.0 + number), 6)


def _required(value: Any, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def _hash(value: Any) -> str:
    return hashlib.blake2b(str(value).encode(), digest_size=16).hexdigest()
