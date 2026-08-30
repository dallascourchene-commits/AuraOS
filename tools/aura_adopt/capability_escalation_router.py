"""AURA-ADOPT-001 ZF-07A capability-residual optional model/key router.

Pure D0 decision layer. It never probes models/providers, reads credentials,
downloads models, calls providers, takes payment, or grants execution authority.

The router is invoked only after an upstream ArenaRecipePlanV1 and a typed
capability residual exist. Startup/configuration alone cannot earn model/key
friction.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

ROUTER_SCHEMA = "CapabilityEscalationRouterV1"
DECISION_SCHEMA = "CapabilityEscalationDecisionV1"
SUPPORTED_PLAN_SCHEMA = "ArenaRecipePlanV1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,255}$")


class RouterError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


class ResidualKind(str, Enum):
    MODEL_INFERENCE_REQUIRED = "MODEL_INFERENCE_REQUIRED"
    NON_MODEL_RESIDUAL = "NON_MODEL_RESIDUAL"


class Availability(str, Enum):
    PROVEN_AVAILABLE = "PROVEN_AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class ExecutionLocation(str, Enum):
    LOCAL = "LOCAL"
    REMOTE = "REMOTE"


class Materialization(str, Enum):
    PRESENT = "PRESENT"
    DOWNLOAD_REQUIRED = "DOWNLOAD_REQUIRED"
    REMOTE_SERVICE = "REMOTE_SERVICE"


class CostClass(str, Enum):
    INCLUDED = "INCLUDED"
    FREE_BOUNDED = "FREE_BOUNDED"
    PAID = "PAID"
    UNKNOWN = "UNKNOWN"


class CredentialRequirement(str, Enum):
    NONE = "NONE"
    BYOK = "BYOK"
    PROVIDER_ACCOUNT = "PROVIDER_ACCOUNT"


class RemoteAdmission(str, Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    ADMITTED_BOUNDED = "ADMITTED_BOUNDED"
    NOT_ADMITTED = "NOT_ADMITTED"
    UNKNOWN = "UNKNOWN"


class EscalationDisposition(str, Enum):
    NO_ESCALATION_REQUIRED = "NO_ESCALATION_REQUIRED"
    LOCAL_ROUTE_READY = "LOCAL_ROUTE_READY"
    USER_CHOICE_REQUIRED = "USER_CHOICE_REQUIRED"
    EVIDENCE_REQUIRED = "EVIDENCE_REQUIRED"
    UPSTREAM_BLOCKED = "UPSTREAM_BLOCKED"


def _text(value: object, code: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise RouterError(code)
    value = value.strip()
    if not value and not allow_empty:
        raise RouterError(code)
    return value


def _token(value: object, code: str, *, allow_empty: bool = False) -> str:
    value = _text(value, code, allow_empty=allow_empty)
    if not value and allow_empty:
        return value
    if not _TOKEN.fullmatch(value):
        raise RouterError(code)
    return value


def _sha(value: object, code: str) -> str:
    value = _text(value, code).lower()
    if not _SHA256.fullmatch(value):
        raise RouterError(code)
    return value


def _strict_enum(value: object, enum_type: type[Enum], code: str):
    if not isinstance(value, enum_type):
        raise RouterError(code)
    return value


def _nn_int(value: object, code: str, *, allow_none: bool = True) -> int | None:
    if value is None and allow_none:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RouterError(code)
    return value


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise RouterError("NONCANONICAL_ROUTER_STATE") from exc


def _digest(domain: str, value: object) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical(value)).hexdigest()


@dataclass(frozen=True)
class RouterCurrentnessV1:
    source_currentness_ref: str
    model_catalog_currentness_ref: str
    provider_catalog_currentness_ref: str
    rate_catalog_currentness_ref: str

    def __post_init__(self) -> None:
        for name in (
            "source_currentness_ref",
            "model_catalog_currentness_ref",
            "provider_catalog_currentness_ref",
            "rate_catalog_currentness_ref",
        ):
            object.__setattr__(self, name, _token(getattr(self, name), f"{name.upper()}_INVALID"))


@dataclass(frozen=True)
class CapabilityResidualV1:
    residual_id: str
    recipe_plan_digest: str
    capability_ref: str
    residual_kind: ResidualKind
    unresolved: bool
    source_generation: str
    source_currentness_ref: str
    minimum_context_tokens: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "residual_id", _token(self.residual_id, "RESIDUAL_ID_INVALID"))
        object.__setattr__(
            self, "recipe_plan_digest", _sha(self.recipe_plan_digest, "RECIPE_PLAN_DIGEST_INVALID")
        )
        object.__setattr__(
            self, "capability_ref", _token(self.capability_ref, "CAPABILITY_REF_INVALID")
        )
        object.__setattr__(
            self, "residual_kind", _strict_enum(self.residual_kind, ResidualKind, "RESIDUAL_KIND_INVALID")
        )
        if type(self.unresolved) is not bool:
            raise RouterError("RESIDUAL_UNRESOLVED_BOOL_REQUIRED")
        object.__setattr__(
            self, "source_generation", _token(self.source_generation, "SOURCE_GENERATION_INVALID")
        )
        object.__setattr__(
            self,
            "source_currentness_ref",
            _token(self.source_currentness_ref, "SOURCE_CURRENTNESS_REF_INVALID"),
        )
        _nn_int(self.minimum_context_tokens, "MINIMUM_CONTEXT_TOKENS_INVALID", allow_none=False)


@dataclass(frozen=True)
class CandidateRouteEvidenceV1:
    route_id: str
    model_ref: str
    capability_refs: tuple[str, ...]
    execution_location: ExecutionLocation
    materialization: Materialization
    availability: Availability
    cost_class: CostClass
    credential_requirement: CredentialRequirement
    remote_admission: RemoteAdmission
    source_generation: str
    model_currentness_ref: str
    context_window_tokens: int
    provider_ref: str = ""
    provider_currentness_ref: str = ""
    rate_currentness_ref: str = ""
    free_evidence_ref: str = ""
    rate_limit_evidence_ref: str = ""
    download_bytes: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "route_id", _token(self.route_id, "ROUTE_ID_INVALID"))
        object.__setattr__(self, "model_ref", _token(self.model_ref, "MODEL_REF_INVALID"))
        if not isinstance(self.capability_refs, tuple) or not self.capability_refs:
            raise RouterError("CAPABILITY_REFS_REQUIRED")
        clean_caps = tuple(sorted({_token(v, "CANDIDATE_CAPABILITY_REF_INVALID") for v in self.capability_refs}))
        object.__setattr__(self, "capability_refs", clean_caps)
        for name, enum_type in (
            ("execution_location", ExecutionLocation),
            ("materialization", Materialization),
            ("availability", Availability),
            ("cost_class", CostClass),
            ("credential_requirement", CredentialRequirement),
            ("remote_admission", RemoteAdmission),
        ):
            object.__setattr__(
                self, name, _strict_enum(getattr(self, name), enum_type, f"{name.upper()}_INVALID")
            )
        object.__setattr__(
            self, "source_generation", _token(self.source_generation, "CANDIDATE_SOURCE_GENERATION_INVALID")
        )
        object.__setattr__(
            self,
            "model_currentness_ref",
            _token(self.model_currentness_ref, "MODEL_CURRENTNESS_REF_INVALID"),
        )
        _nn_int(self.context_window_tokens, "CONTEXT_WINDOW_TOKENS_INVALID", allow_none=False)
        for name in (
            "provider_ref",
            "provider_currentness_ref",
            "rate_currentness_ref",
            "free_evidence_ref",
            "rate_limit_evidence_ref",
        ):
            object.__setattr__(
                self, name, _token(getattr(self, name), f"{name.upper()}_INVALID", allow_empty=True)
            )
        _nn_int(self.download_bytes, "DOWNLOAD_BYTES_INVALID", allow_none=True)

        if self.execution_location is ExecutionLocation.LOCAL:
            if self.materialization is Materialization.REMOTE_SERVICE:
                raise RouterError("LOCAL_ROUTE_CANNOT_BE_REMOTE_SERVICE")
            if self.remote_admission is not RemoteAdmission.NOT_APPLICABLE:
                raise RouterError("LOCAL_ROUTE_REMOTE_ADMISSION_MUST_BE_NA")
            if self.provider_ref or self.provider_currentness_ref:
                raise RouterError("LOCAL_ROUTE_PROVIDER_FIELDS_FORBIDDEN")
            if self.credential_requirement is not CredentialRequirement.NONE:
                raise RouterError("LOCAL_ROUTE_CREDENTIAL_REQUIREMENT_FORBIDDEN")
            if self.materialization is Materialization.PRESENT and self.download_bytes is not None:
                raise RouterError("PRESENT_ROUTE_DOWNLOAD_BYTES_FORBIDDEN")
            if self.materialization is Materialization.DOWNLOAD_REQUIRED and self.download_bytes is None:
                raise RouterError("DOWNLOAD_BYTES_REQUIRED")
        else:
            if self.materialization is not Materialization.REMOTE_SERVICE:
                raise RouterError("REMOTE_ROUTE_SERVICE_MATERIALIZATION_REQUIRED")
            if not self.provider_ref or not self.provider_currentness_ref or not self.rate_currentness_ref:
                raise RouterError("REMOTE_PROVIDER_RATE_BINDING_REQUIRED")
            if self.remote_admission is RemoteAdmission.NOT_APPLICABLE:
                raise RouterError("REMOTE_ADMISSION_REQUIRED")
            if self.download_bytes is not None:
                raise RouterError("REMOTE_ROUTE_DOWNLOAD_BYTES_FORBIDDEN")

        if self.cost_class is CostClass.FREE_BOUNDED:
            if not self.free_evidence_ref or not self.rate_limit_evidence_ref:
                raise RouterError("FREE_BOUNDED_EVIDENCE_REQUIRED")


@dataclass(frozen=True)
class EscalationOptionV1:
    route_id: str
    model_ref: str
    provider_ref: str
    execution_location: ExecutionLocation
    cost_class: CostClass
    required_actions: tuple[str, ...]
    zero_effect_ready: bool
    download_bytes: int | None
    evidence_summary: tuple[str, ...]

    def logical(self) -> dict[str, Any]:
        value = asdict(self)
        value["execution_location"] = self.execution_location.value
        value["cost_class"] = self.cost_class.value
        return value


@dataclass(frozen=True)
class CapabilityEscalationDecisionV1:
    residual_id: str
    capability_ref: str
    disposition: EscalationDisposition
    selected_route_id: str | None
    options: tuple[EscalationOptionV1, ...]
    blockers: tuple[str, ...]
    earned_action_classes: tuple[str, ...]
    decision_digest: str
    schema: str = DECISION_SCHEMA
    router_schema: str = ROUTER_SCHEMA
    credential_prompt_performed: bool = False
    credential_collected: bool = False
    model_download_started: bool = False
    provider_call_made: bool = False
    payment_performed: bool = False
    effect_authorized: bool = False
    execution_proven: bool = False


def _validate_plan(plan: Mapping[str, Any]) -> tuple[str, tuple[str, ...], str]:
    if not isinstance(plan, Mapping):
        raise RouterError("RECIPE_PLAN_MAPPING_REQUIRED")
    if plan.get("schema") != SUPPORTED_PLAN_SCHEMA:
        raise RouterError("RECIPE_PLAN_SCHEMA_MISMATCH")
    digest = _sha(plan.get("plan_digest"), "RECIPE_PLAN_DIGEST_INVALID")
    caps = plan.get("capability_refs")
    if not isinstance(caps, list) or not caps:
        raise RouterError("RECIPE_PLAN_CAPABILITY_REFS_REQUIRED")
    capability_refs = tuple(_token(x, "RECIPE_PLAN_CAPABILITY_REF_INVALID") for x in caps)
    status = _token(plan.get("status"), "RECIPE_PLAN_STATUS_REQUIRED")
    for flag in (
        "effect_authorized",
        "execution_proven",
        "publication_authorized",
        "payment_authorized",
    ):
        if plan.get(flag) is not False:
            raise RouterError("UPSTREAM_AUTHORITY_WIDENING", flag)
    return digest, capability_refs, status


def _candidate_blockers(
    candidate: CandidateRouteEvidenceV1,
    *,
    residual: CapabilityResidualV1,
    currentness: RouterCurrentnessV1,
) -> tuple[str, ...]:
    blockers: list[str] = []
    prefix = candidate.route_id
    if residual.capability_ref not in candidate.capability_refs:
        blockers.append(f"{prefix}:CAPABILITY_UNSUPPORTED")
    if candidate.availability is Availability.UNKNOWN:
        blockers.append(f"{prefix}:AVAILABILITY_UNKNOWN")
    elif candidate.availability is Availability.UNAVAILABLE:
        blockers.append(f"{prefix}:UNAVAILABLE")
    if candidate.model_currentness_ref != currentness.model_catalog_currentness_ref:
        blockers.append(f"{prefix}:MODEL_CURRENTNESS_STALE")
    if candidate.context_window_tokens < residual.minimum_context_tokens:
        blockers.append(f"{prefix}:CONTEXT_WINDOW_INSUFFICIENT")

    if candidate.execution_location is ExecutionLocation.REMOTE:
        if candidate.provider_currentness_ref != currentness.provider_catalog_currentness_ref:
            blockers.append(f"{prefix}:PROVIDER_CURRENTNESS_STALE")
        if candidate.rate_currentness_ref != currentness.rate_catalog_currentness_ref:
            blockers.append(f"{prefix}:RATE_CURRENTNESS_STALE")
        if candidate.remote_admission is RemoteAdmission.UNKNOWN:
            blockers.append(f"{prefix}:REMOTE_ADMISSION_UNKNOWN")
        elif candidate.remote_admission is RemoteAdmission.NOT_ADMITTED:
            blockers.append(f"{prefix}:REMOTE_NOT_ADMITTED")

    if candidate.cost_class is CostClass.UNKNOWN:
        blockers.append(f"{prefix}:COST_CLASSIFICATION_UNKNOWN")

    return tuple(blockers)


def _option(candidate: CandidateRouteEvidenceV1) -> EscalationOptionV1:
    actions: list[str] = []
    evidence: list[str] = [
        f"source_generation={candidate.source_generation}",
        f"model_currentness={candidate.model_currentness_ref}",
        f"availability={candidate.availability.value}",
        f"cost={candidate.cost_class.value}",
    ]
    if candidate.execution_location is ExecutionLocation.LOCAL:
        if candidate.materialization is Materialization.DOWNLOAD_REQUIRED:
            actions.append("EXPLICIT_MODEL_DOWNLOAD_CONSENT")
            evidence.append(f"download_bytes={candidate.download_bytes}")
    else:
        actions.append("EXPLICIT_REMOTE_EXECUTION_CONSENT")
        evidence.extend(
            (
                f"provider={candidate.provider_ref}",
                f"provider_currentness={candidate.provider_currentness_ref}",
                f"rate_currentness={candidate.rate_currentness_ref}",
            )
        )
        if candidate.credential_requirement is CredentialRequirement.BYOK:
            actions.append("REQUEST_CREDENTIAL_VIA_SECURE_OWNER")
        elif candidate.credential_requirement is CredentialRequirement.PROVIDER_ACCOUNT:
            actions.append("REQUEST_PROVIDER_ACCOUNT_VIA_OWNER")
        if candidate.cost_class is CostClass.PAID:
            actions.append("EXPLICIT_PAYMENT_CONSENT")
        elif candidate.cost_class is CostClass.FREE_BOUNDED:
            evidence.append(f"free_evidence={candidate.free_evidence_ref}")
            evidence.append(f"rate_limit_evidence={candidate.rate_limit_evidence_ref}")

    return EscalationOptionV1(
        route_id=candidate.route_id,
        model_ref=candidate.model_ref,
        provider_ref=candidate.provider_ref,
        execution_location=candidate.execution_location,
        cost_class=candidate.cost_class,
        required_actions=tuple(actions),
        zero_effect_ready=not actions,
        download_bytes=candidate.download_bytes,
        evidence_summary=tuple(evidence),
    )


def _option_sort_key(option: EscalationOptionV1) -> tuple[int, int, str]:
    paid = 1 if option.cost_class is CostClass.PAID else 0
    return (len(option.required_actions), paid, option.route_id)


def _decision(
    residual: CapabilityResidualV1,
    disposition: EscalationDisposition,
    *,
    selected_route_id: str | None = None,
    options: Sequence[EscalationOptionV1] = (),
    blockers: Sequence[str] = (),
) -> CapabilityEscalationDecisionV1:
    opts = tuple(sorted(options, key=_option_sort_key))
    earned = tuple(sorted({action for option in opts for action in option.required_actions}))
    logical = {
        "schema": DECISION_SCHEMA,
        "router_schema": ROUTER_SCHEMA,
        "residual_id": residual.residual_id,
        "capability_ref": residual.capability_ref,
        "disposition": disposition.value,
        "selected_route_id": selected_route_id,
        "options": [option.logical() for option in opts],
        "blockers": tuple(sorted(set(blockers))),
        "earned_action_classes": earned,
        "credential_prompt_performed": False,
        "credential_collected": False,
        "model_download_started": False,
        "provider_call_made": False,
        "payment_performed": False,
        "effect_authorized": False,
        "execution_proven": False,
    }
    digest = _digest("AURA_ADOPT_CAPABILITY_ESCALATION_DECISION_V1", logical)
    return CapabilityEscalationDecisionV1(
        residual_id=residual.residual_id,
        capability_ref=residual.capability_ref,
        disposition=disposition,
        selected_route_id=selected_route_id,
        options=opts,
        blockers=tuple(sorted(set(blockers))),
        earned_action_classes=earned,
        decision_digest=digest,
    )


def compile_capability_escalation(
    recipe_plan: Mapping[str, Any],
    residual: CapabilityResidualV1,
    candidates: Sequence[CandidateRouteEvidenceV1],
    *,
    currentness: RouterCurrentnessV1,
) -> CapabilityEscalationDecisionV1:
    """Compile one unresolved capability into optional model/provider choices.

    The function is intentionally single-residual. Multi-capability planning remains
    with the upstream capability/recipe planner; this layer does not become a second
    planner or model marketplace.
    """
    plan_digest, capability_refs, plan_status = _validate_plan(recipe_plan)
    if not isinstance(residual, CapabilityResidualV1):
        raise RouterError("CAPABILITY_RESIDUAL_REQUIRED")
    if not isinstance(currentness, RouterCurrentnessV1):
        raise RouterError("ROUTER_CURRENTNESS_REQUIRED")
    if isinstance(candidates, (str, bytes)) or not isinstance(candidates, Sequence):
        raise RouterError("CANDIDATE_SEQUENCE_REQUIRED")
    if any(not isinstance(candidate, CandidateRouteEvidenceV1) for candidate in candidates):
        raise RouterError("CANDIDATE_EVIDENCE_INVALID")

    if residual.recipe_plan_digest != plan_digest:
        raise RouterError("RESIDUAL_PLAN_DIGEST_MISMATCH")
    if residual.capability_ref not in capability_refs:
        raise RouterError("RESIDUAL_CAPABILITY_NOT_IN_PLAN")

    if plan_status != "READY_FOR_ADMISSION":
        upstream = recipe_plan.get("blockers", ())
        if not isinstance(upstream, list):
            upstream = ()
        return _decision(
            residual,
            EscalationDisposition.UPSTREAM_BLOCKED,
            blockers=tuple(f"UPSTREAM:{str(x)}" for x in upstream) or ("UPSTREAM_PLAN_NOT_READY",),
        )

    if residual.source_currentness_ref != currentness.source_currentness_ref:
        return _decision(
            residual,
            EscalationDisposition.EVIDENCE_REQUIRED,
            blockers=("RESIDUAL_SOURCE_CURRENTNESS_STALE",),
        )

    if not residual.unresolved or residual.residual_kind is ResidualKind.NON_MODEL_RESIDUAL:
        return _decision(residual, EscalationDisposition.NO_ESCALATION_REQUIRED)

    eligible: list[EscalationOptionV1] = []
    rejected: list[str] = []
    for candidate in candidates:
        blockers = _candidate_blockers(candidate, residual=residual, currentness=currentness)
        if blockers:
            rejected.extend(blockers)
            continue
        eligible.append(_option(candidate))

    zero_effect = [option for option in eligible if option.zero_effect_ready]
    if zero_effect:
        selected = sorted(zero_effect, key=_option_sort_key)[0]
        return _decision(
            residual,
            EscalationDisposition.LOCAL_ROUTE_READY,
            selected_route_id=selected.route_id,
            options=eligible,
            blockers=rejected,
        )

    if eligible:
        return _decision(
            residual,
            EscalationDisposition.USER_CHOICE_REQUIRED,
            options=eligible,
            blockers=rejected,
        )

    return _decision(
        residual,
        EscalationDisposition.EVIDENCE_REQUIRED,
        blockers=rejected or ("NO_CURRENT_CAPABLE_ROUTE_EVIDENCE",),
    )
