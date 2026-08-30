"""AURA-ADOPT-001 ZF-00B consequence-complete friction receipt harness.

Consumes a normalized, non-authoritative route-decision receipt. It does not own
route selection or preserve any compiler implementation as a second truth plane.
Observation clocks are provenance only; consequence measurements remain identity-
bearing. UNKNOWN never becomes zero. D0 only: no telemetry collection, install,
permission, credential, provider, publication, or execution authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from typing import Any, Mapping, Sequence

RECEIPT_SCHEMA = "AdoptionFrictionReceiptV1"
HARNESS_SCHEMA = "AdoptionFrictionHarnessV1"
COMPARISON_SCHEMA = "AdoptionFrictionComparisonV1"
SUPPORTED_COMPILER_SCHEMA = "AuraAdoptionBootstrapReceiptV1"


class FrictionReceiptError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


class StageStatus(str, Enum):
    COMPLETED = "COMPLETED"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    BLOCKED = "BLOCKED"


STAGES = (
    "DISCOVER", "TRUST", "OPEN_INSTALL", "PERMISSION", "STORAGE_CHOICE",
    "OPTIONAL_ACCOUNT", "OPTIONAL_KEY", "INPUT", "CAPABILITY_RESOLVE",
    "EXECUTE", "VERIFY_ACCEPT", "SAVE_REOPEN", "SHARE_OR_REUSE",
)
FRICTION_COMPONENTS = (
    "discovery", "trust", "install", "hardware", "storage_network",
    "permission_credential", "learning", "creation_time_to_value",
    "reuse_recovery",
)
ALLOWED_EVIDENCE_CLASSES = frozenset({"SYNTHETIC", "LOCAL_TEST", "CONSENTED_STUDY"})
ALLOWED_COHORT_KEYS = frozenset({
    "device_class", "storage_class", "connectivity_class", "skill_class",
    "trust_preference", "compute_preference", "storage_preference",
    "accessibility_class",
})
FORBIDDEN_KEY_TOKENS = frozenset({
    "api_key", "apikey", "secret", "token", "credential", "credentials",
    "password", "prompt", "content", "email", "phone", "user_id",
    "userid", "ip_address",
})
COMPILER_EFFECT_FLAGS = (
    "installation_performed", "permission_granted", "provider_call_made",
    "credential_stored", "public_deployment_performed", "binary_distributed",
)


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
    except (TypeError, ValueError) as exc:
        raise FrictionReceiptError("NONCANONICAL_RECEIPT_STATE") from exc


def _digest(domain: str, value: Any) -> str:
    return hashlib.sha256(domain.encode() + b"\0" + _canonical(value)).hexdigest()


def _text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FrictionReceiptError(code)
    return value.strip()


def _tuple_text(value: Any, code: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise FrictionReceiptError(code)
    return tuple(_text(v, code) for v in value)


def _reject_private(value: Any, path: str = "root") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).strip().casefold() in FORBIDDEN_KEY_TOKENS:
                raise FrictionReceiptError("PRIVATE_FIELD_FORBIDDEN", f"{path}.{key}")
            _reject_private(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for idx, child in enumerate(value):
            _reject_private(child, f"{path}[{idx}]")


def _nn(value: Any, code: str) -> int | float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise FrictionReceiptError(code)
    return value


@dataclass(frozen=True)
class RouteDecisionBinding:
    compiler_schema: str
    compiler_receipt_digest: str
    projection_digest: str
    source_binding_digest: str
    source_binding_authenticated: bool
    disposition: str
    entry_surface: str
    compute_profile: str
    first_use_capability: str
    required_actions: tuple[str, ...]
    blockers: tuple[str, ...]
    claim_ceiling: str

    def __post_init__(self) -> None:
        for value, code in (
            (self.compiler_schema, "COMPILER_SCHEMA_REQUIRED"),
            (self.compiler_receipt_digest, "COMPILER_RECEIPT_DIGEST_REQUIRED"),
            (self.projection_digest, "PROJECTION_DIGEST_REQUIRED"),
            (self.source_binding_digest, "SOURCE_BINDING_DIGEST_REQUIRED"),
            (self.disposition, "ROUTE_DISPOSITION_REQUIRED"),
            (self.entry_surface, "ENTRY_SURFACE_REQUIRED"),
            (self.compute_profile, "COMPUTE_PROFILE_REQUIRED"),
            (self.first_use_capability, "FIRST_USE_CAPABILITY_REQUIRED"),
            (self.claim_ceiling, "CLAIM_CEILING_REQUIRED"),
        ):
            _text(value, code)
        if self.source_binding_authenticated is not False:
            raise FrictionReceiptError("SOURCE_BINDING_AUTHORITY_WIDENING")


def bind_route_decision(compiler_receipt: Mapping[str, Any]) -> RouteDecisionBinding:
    """Normalize the current compiler receipt without importing its implementation."""
    if not isinstance(compiler_receipt, Mapping):
        raise FrictionReceiptError("COMPILER_RECEIPT_MAPPING_REQUIRED")
    raw = dict(compiler_receipt)
    if raw.get("schema") != SUPPORTED_COMPILER_SCHEMA:
        raise FrictionReceiptError("COMPILER_RECEIPT_SCHEMA_MISMATCH")
    for flag in COMPILER_EFFECT_FLAGS:
        if raw.get(flag) is not False:
            raise FrictionReceiptError("COMPILER_EFFECT_AUTHORITY_WIDENING", flag)
    if raw.get("source_binding_authenticated") is not False:
        raise FrictionReceiptError("SOURCE_BINDING_AUTHORITY_WIDENING")
    friction = raw.get("friction")
    required = _tuple_text(raw.get("required_actions"), "REQUIRED_ACTIONS_INVALID")
    if not isinstance(friction, Mapping):
        raise FrictionReceiptError("COMPILER_FRICTION_MAPPING_REQUIRED")
    declared = friction.get("required_action_count")
    if isinstance(declared, bool) or not isinstance(declared, int) or declared < 0:
        raise FrictionReceiptError("COMPILER_REQUIRED_ACTION_COUNT_INVALID")
    if declared != len(required):
        raise FrictionReceiptError("COMPILER_REQUIRED_ACTION_COUNT_MISMATCH")
    digest = _digest("AURA_ADOPTION_BOOTSTRAP_RECEIPT_V1", raw)
    return RouteDecisionBinding(
        compiler_schema=SUPPORTED_COMPILER_SCHEMA,
        compiler_receipt_digest=digest,
        projection_digest=_text(raw.get("projection_digest"), "PROJECTION_DIGEST_REQUIRED"),
        source_binding_digest=_text(raw.get("source_binding_digest"), "SOURCE_BINDING_DIGEST_REQUIRED"),
        source_binding_authenticated=False,
        disposition=_text(raw.get("disposition"), "ROUTE_DISPOSITION_REQUIRED"),
        entry_surface=_text(raw.get("surface"), "ENTRY_SURFACE_REQUIRED"),
        compute_profile=_text(raw.get("compute_profile"), "COMPUTE_PROFILE_REQUIRED"),
        first_use_capability=_text(raw.get("first_use_capability"), "FIRST_USE_CAPABILITY_REQUIRED"),
        required_actions=required,
        blockers=_tuple_text(raw.get("blockers"), "BLOCKERS_INVALID"),
        claim_ceiling=_text(raw.get("claim_ceiling"), "CLAIM_CEILING_REQUIRED"),
    )


@dataclass(frozen=True)
class StageEvent:
    stage: str
    status: StageStatus
    steps: int | None = None
    wall_time_ms: int | None = None
    downloaded_bytes: int | None = None
    retained_bytes: int | None = None
    monetary_cost_microunits: int | None = None
    retries: int = 0
    reason: str | None = None
    failure_code: str | None = None
    observation_clock_ms: int | None = None

    def __post_init__(self) -> None:
        if self.stage not in STAGES:
            raise FrictionReceiptError("UNKNOWN_STAGE", self.stage)
        if not isinstance(self.status, StageStatus):
            raise FrictionReceiptError("INVALID_STAGE_STATUS", self.stage)
        for name in ("steps", "wall_time_ms", "downloaded_bytes", "retained_bytes", "monetary_cost_microunits", "retries", "observation_clock_ms"):
            value = getattr(self, name)
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
                raise FrictionReceiptError("INVALID_NONNEGATIVE_FIELD", f"{self.stage}.{name}")
        if self.status in {StageStatus.UNKNOWN, StageStatus.NOT_APPLICABLE, StageStatus.BLOCKED} and not (isinstance(self.reason, str) and self.reason.strip()):
            raise FrictionReceiptError("STAGE_REASON_REQUIRED", self.stage)
        if self.status == StageStatus.BLOCKED and not (isinstance(self.failure_code, str) and self.failure_code.strip()):
            raise FrictionReceiptError("BLOCKED_FAILURE_CODE_REQUIRED", self.stage)

    def logical_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["status"] = self.status.value
        out.pop("observation_clock_ms", None)
        return out


@dataclass(frozen=True)
class AcceptedValue:
    criterion: str
    result: bool | None
    verifier: str

    def __post_init__(self) -> None:
        _text(self.criterion, "ACCEPTED_VALUE_CRITERION_REQUIRED")
        _text(self.verifier, "ACCEPTED_VALUE_VERIFIER_REQUIRED")
        if self.result is not None and not isinstance(self.result, bool):
            raise FrictionReceiptError("ACCEPTED_VALUE_RESULT_INVALID")


@dataclass(frozen=True)
class FrictionReceipt:
    schema: str
    harness_schema: str
    route_id: str
    mission_head: str
    build_refs: tuple[str, ...]
    decision: RouteDecisionBinding
    cohort: Mapping[str, str]
    starting_state: Mapping[str, Any]
    stage_events: tuple[StageEvent, ...]
    total_steps: int | None
    total_wall_time_ms: int | None
    total_downloaded_bytes: int | None
    peak_retained_bytes: int | None
    total_retries: int
    total_monetary_cost_microunits: int | None
    permissions: tuple[str, ...]
    mandatory_account: bool
    mandatory_key: bool
    clarification_events: int
    support_events: int
    route_changes: tuple[str, ...]
    accepted_value: AcceptedValue
    capability_refs: tuple[str, ...]
    recipe_refs: tuple[str, ...]
    privacy_telemetry_mode: str
    friction_vector: Mapping[str, int | float | None]
    weights: Mapping[str, float]
    weighting_method: str
    total_score: float | None
    invalidators: tuple[str, ...]
    reopen_trigger: str
    evidence_class: str
    failure_signature: tuple[str, ...]
    logical_id: str
    effect_authorized: bool = False
    execution_proven: bool = False


@dataclass(frozen=True)
class RouteComparison:
    schema: str
    baseline_logical_id: str
    candidate_logical_id: str
    component_delta: Mapping[str, float | None]
    unresolved_components: tuple[str, ...]
    baseline_failure_signature: tuple[str, ...]
    candidate_failure_signature: tuple[str, ...]
    added_burdens: tuple[str, ...]
    removed_burdens: tuple[str, ...]
    scalar_delta: float | None
    comparable_without_scalar_collapse: bool


def _validate_events(events: Sequence[StageEvent]) -> tuple[StageEvent, ...]:
    if isinstance(events, (str, bytes)) or not isinstance(events, Sequence):
        raise FrictionReceiptError("STAGE_EVENTS_REQUIRED")
    out = tuple(events)
    if tuple(e.stage for e in out) != STAGES:
        raise FrictionReceiptError("CONSEQUENCE_STAGE_COVERAGE_INVALID")
    return out


def _validate_cohort(cohort: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(cohort, Mapping) or not cohort:
        raise FrictionReceiptError("COHORT_DESCRIPTOR_REQUIRED")
    extra = sorted(set(str(k) for k in cohort) - ALLOWED_COHORT_KEYS)
    if extra:
        raise FrictionReceiptError("COHORT_FIELD_NOT_PRIVACY_MINIMAL", ",".join(extra))
    return {str(k): _text(v, "COHORT_VALUE_REQUIRED") for k, v in cohort.items()}


def _validate_vector(vector: Mapping[str, int | float | None]) -> dict[str, int | float | None]:
    if not isinstance(vector, Mapping) or set(vector) != set(FRICTION_COMPONENTS):
        raise FrictionReceiptError("FRICTION_VECTOR_COMPONENTS_MISMATCH")
    return {k: _nn(vector[k], f"FRICTION_COMPONENT_INVALID:{k}") for k in FRICTION_COMPONENTS}


def _validate_weights(weights: Mapping[str, int | float]) -> dict[str, float]:
    if not isinstance(weights, Mapping) or set(weights) != set(FRICTION_COMPONENTS):
        raise FrictionReceiptError("FRICTION_WEIGHTS_COMPONENTS_MISMATCH")
    out = {}
    for key in FRICTION_COMPONENTS:
        value = weights[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise FrictionReceiptError("FRICTION_WEIGHT_INVALID", key)
        out[key] = float(value)
    if sum(out.values()) <= 0:
        raise FrictionReceiptError("FRICTION_WEIGHTS_ZERO")
    return out


def _sum(events: Sequence[StageEvent], name: str) -> int | None:
    total = 0
    for event in events:
        if event.status == StageStatus.NOT_APPLICABLE:
            continue
        value = getattr(event, name)
        if value is None:
            return None
        total += int(value)
    return total


def _peak(events: Sequence[StageEvent]) -> int | None:
    values = []
    for event in events:
        if event.status == StageStatus.NOT_APPLICABLE:
            continue
        if event.retained_bytes is None:
            return None
        values.append(event.retained_bytes)
    return max(values, default=0)


def _failure_signature(events: Sequence[StageEvent]) -> tuple[str, ...]:
    out = set()
    for event in events:
        if event.status == StageStatus.BLOCKED:
            out.add(f"{event.stage}:{event.failure_code}")
        elif event.status == StageStatus.UNKNOWN:
            out.add(f"{event.stage}:UNKNOWN")
    return tuple(sorted(out))


def _required_action_burdens(actions: Sequence[str]) -> set[str]:
    burdens = set()
    for action in actions:
        upper = action.upper()
        if "INSTALL" in upper:
            burdens.add("INSTALL")
        if "PERMISSION" in upper or upper.startswith("REQUEST_"):
            burdens.add("PERMISSION")
        if "KEY" in upper or "CREDENTIAL" in upper:
            burdens.add("MANDATORY_KEY")
        if "ACCOUNT" in upper:
            burdens.add("MANDATORY_ACCOUNT")
    return burdens


def _receipt_burdens(receipt: FrictionReceipt) -> set[str]:
    out = _required_action_burdens(receipt.decision.required_actions)
    if receipt.mandatory_account:
        out.add("MANDATORY_ACCOUNT")
    if receipt.mandatory_key:
        out.add("MANDATORY_KEY")
    if receipt.permissions:
        out.add("PERMISSION")
    install = next(e for e in receipt.stage_events if e.stage == "OPEN_INSTALL")
    if install.steps not in (None, 0) or install.downloaded_bytes not in (None, 0):
        out.add("INSTALL")
    return out


def build_friction_receipt(
    decision: RouteDecisionBinding,
    *,
    route_id: str,
    mission_head: str,
    build_refs: Sequence[str],
    cohort: Mapping[str, str],
    starting_state: Mapping[str, Any],
    stage_events: Sequence[StageEvent],
    accepted_value: AcceptedValue,
    friction_vector: Mapping[str, int | float | None],
    weights: Mapping[str, int | float],
    weighting_method: str,
    reopen_trigger: str,
    permissions: Sequence[str] = (),
    mandatory_account: bool = False,
    mandatory_key: bool = False,
    clarification_events: int = 0,
    support_events: int = 0,
    route_changes: Sequence[str] = (),
    capability_refs: Sequence[str] = (),
    recipe_refs: Sequence[str] = (),
    privacy_telemetry_mode: str = "SYNTHETIC_NO_TELEMETRY",
    invalidators: Sequence[str] = (),
    evidence_class: str = "SYNTHETIC",
) -> FrictionReceipt:
    if not isinstance(decision, RouteDecisionBinding):
        raise FrictionReceiptError("ROUTE_DECISION_BINDING_REQUIRED")
    route_id = _text(route_id, "ROUTE_ID_REQUIRED")
    mission_head = _text(mission_head, "MISSION_HEAD_REQUIRED")
    weighting_method = _text(weighting_method, "WEIGHTING_METHOD_REQUIRED")
    reopen_trigger = _text(reopen_trigger, "REOPEN_TRIGGER_REQUIRED")
    if evidence_class not in ALLOWED_EVIDENCE_CLASSES:
        raise FrictionReceiptError("EVIDENCE_CLASS_INVALID", evidence_class)
    if evidence_class == "CONSENTED_STUDY" and "CONSENT" not in privacy_telemetry_mode.upper():
        raise FrictionReceiptError("CONSENT_SCOPE_REQUIRED")
    for count, code in ((clarification_events, "CLARIFICATION_COUNT_INVALID"), (support_events, "SUPPORT_COUNT_INVALID")):
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise FrictionReceiptError(code)

    events = _validate_events(stage_events)
    cohort_clean = _validate_cohort(cohort)
    vector = _validate_vector(friction_vector)
    weight_map = _validate_weights(weights)
    _reject_private(starting_state, "starting_state")
    permission_tuple = tuple(sorted(_text(x, "PERMISSION_NAME_REQUIRED") for x in permissions))
    required_burdens = _required_action_burdens(decision.required_actions)
    if mandatory_account:
        required_burdens.add("MANDATORY_ACCOUNT")
    if mandatory_key:
        required_burdens.add("MANDATORY_KEY")
    if permission_tuple:
        required_burdens.add("PERMISSION")

    stage_by_name = {event.stage: event for event in events}
    mapping = {
        "INSTALL": "OPEN_INSTALL",
        "PERMISSION": "PERMISSION",
        "MANDATORY_ACCOUNT": "OPTIONAL_ACCOUNT",
        "MANDATORY_KEY": "OPTIONAL_KEY",
    }
    for burden, stage in mapping.items():
        if burden in required_burdens and stage_by_name[stage].status == StageStatus.NOT_APPLICABLE:
            raise FrictionReceiptError(f"{burden}_BURDEN_OMITTED")

    build_tuple = tuple(_text(x, "BUILD_REF_REQUIRED") for x in build_refs)
    if not build_tuple:
        raise FrictionReceiptError("BUILD_REFS_REQUIRED")
    failure_signature = _failure_signature(events)
    score = None if any(vector[k] is None for k in FRICTION_COMPONENTS) else float(sum(float(vector[k]) * weight_map[k] for k in FRICTION_COMPONENTS))
    logical = {
        "schema": RECEIPT_SCHEMA, "harness_schema": HARNESS_SCHEMA,
        "route_id": route_id, "mission_head": mission_head, "build_refs": build_tuple,
        "decision": asdict(decision), "cohort": cohort_clean, "starting_state": starting_state,
        "stage_events": [e.logical_dict() for e in events], "permissions": permission_tuple,
        "mandatory_account": bool(mandatory_account), "mandatory_key": bool(mandatory_key),
        "clarification_events": clarification_events, "support_events": support_events,
        "route_changes": tuple(str(x) for x in route_changes), "accepted_value": asdict(accepted_value),
        "capability_refs": tuple(str(x) for x in capability_refs), "recipe_refs": tuple(str(x) for x in recipe_refs),
        "privacy_telemetry_mode": privacy_telemetry_mode, "friction_vector": vector,
        "weights": weight_map, "weighting_method": weighting_method,
        "invalidators": tuple(str(x) for x in invalidators), "reopen_trigger": reopen_trigger,
        "evidence_class": evidence_class, "failure_signature": failure_signature,
        "effect_authorized": False, "execution_proven": False,
    }
    _reject_private(logical)
    logical_id = "afr-" + _digest("AURA_ADOPTION_FRICTION_RECEIPT_V1", logical)[:32]
    return FrictionReceipt(
        schema=RECEIPT_SCHEMA, harness_schema=HARNESS_SCHEMA, route_id=route_id,
        mission_head=mission_head, build_refs=build_tuple, decision=decision,
        cohort=cohort_clean, starting_state=dict(starting_state), stage_events=events,
        total_steps=_sum(events, "steps"), total_wall_time_ms=_sum(events, "wall_time_ms"),
        total_downloaded_bytes=_sum(events, "downloaded_bytes"), peak_retained_bytes=_peak(events),
        total_retries=sum(e.retries for e in events), total_monetary_cost_microunits=_sum(events, "monetary_cost_microunits"),
        permissions=permission_tuple, mandatory_account=bool(mandatory_account), mandatory_key=bool(mandatory_key),
        clarification_events=clarification_events, support_events=support_events,
        route_changes=tuple(str(x) for x in route_changes), accepted_value=accepted_value,
        capability_refs=tuple(str(x) for x in capability_refs), recipe_refs=tuple(str(x) for x in recipe_refs),
        privacy_telemetry_mode=privacy_telemetry_mode, friction_vector=vector, weights=weight_map,
        weighting_method=weighting_method, total_score=score,
        invalidators=tuple(str(x) for x in invalidators), reopen_trigger=reopen_trigger,
        evidence_class=evidence_class, failure_signature=failure_signature,
        logical_id=logical_id, effect_authorized=False, execution_proven=False,
    )


def compare_receipts(baseline: FrictionReceipt, candidate: FrictionReceipt) -> RouteComparison:
    delta, unresolved = {}, []
    for key in FRICTION_COMPONENTS:
        a, b = baseline.friction_vector[key], candidate.friction_vector[key]
        if a is None or b is None:
            delta[key] = None
            unresolved.append(key)
        else:
            delta[key] = float(b) - float(a)
    scalar = None
    if baseline.total_score is not None and candidate.total_score is not None:
        scalar = candidate.total_score - baseline.total_score
    before, after = _receipt_burdens(baseline), _receipt_burdens(candidate)
    return RouteComparison(
        schema=COMPARISON_SCHEMA, baseline_logical_id=baseline.logical_id,
        candidate_logical_id=candidate.logical_id, component_delta=delta,
        unresolved_components=tuple(unresolved), baseline_failure_signature=baseline.failure_signature,
        candidate_failure_signature=candidate.failure_signature,
        added_burdens=tuple(sorted(after - before)), removed_burdens=tuple(sorted(before - after)),
        scalar_delta=scalar, comparable_without_scalar_collapse=True,
    )
