"""ZF-00C thin browser-observation -> ZF-00 friction projection.

This module does not own a receipt schema, route selection, browser execution, or
telemetry. It turns bounded browser witness observations into the canonical
StageEvent / AcceptedValue inputs owned by adoption_friction_receipt.py and may
delegate final receipt construction to that owner.

Key law: technical success is not user acceptance, and download/save initiation
is not observed reopen. Unknown evidence remains UNKNOWN.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from tools.aura_adopt.adoption_friction_receipt import (
    AcceptedValue,
    FRICTION_COMPONENTS,
    FrictionReceipt,
    FrictionReceiptError,
    RouteDecisionBinding,
    StageEvent,
    StageStatus,
    build_friction_receipt,
)


ADAPTER_SCHEMA = "BrowserFrictionObservationAdapterV1"
ACCEPTED_VALUE_CRITERION = "user explicitly marks rendered local output as useful"


class BrowserAdapterError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


class AcceptanceEvidenceMode(str, Enum):
    USER_EXPLICIT = "USER_EXPLICIT"
    USER_REJECTED = "USER_REJECTED"
    SYNTHETIC_TECHNICAL = "SYNTHETIC_TECHNICAL"
    UNKNOWN = "UNKNOWN"


class PersistenceEvidenceMode(str, Enum):
    REOPEN_OBSERVED = "REOPEN_OBSERVED"
    SAVE_OBSERVED = "SAVE_OBSERVED"
    DOWNLOAD_INITIATED = "DOWNLOAD_INITIATED"
    SIMULATED = "SIMULATED"
    UNKNOWN = "UNKNOWN"


def _text(value: object, code: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise BrowserAdapterError(code)
    value = value.strip()
    if not value and not allow_empty:
        raise BrowserAdapterError(code)
    return value


def _tri_bool(value: object, code: str) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    raise BrowserAdapterError(code)


def _nn_int(value: object, code: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise BrowserAdapterError(code)
    return value


@dataclass(frozen=True)
class BrowserWitnessObservationV1:
    route_id: str
    build_ref: str
    recipe_ref: str
    browser_opened: bool | None
    trust_binding_current: bool | None
    capability_supported: bool | None
    input_observed: bool | None
    render_observed: bool | None
    output_bytes: int | None
    acceptance_mode: AcceptanceEvidenceMode
    acceptance_evidence_ref: str = ""
    persistence_mode: PersistenceEvidenceMode = PersistenceEvidenceMode.UNKNOWN
    persistence_evidence_ref: str = ""
    browser_failure_code: str = ""
    schema: str = "BrowserWitnessObservationV1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "route_id", _text(self.route_id, "ROUTE_ID_REQUIRED"))
        object.__setattr__(self, "build_ref", _text(self.build_ref, "BUILD_REF_REQUIRED"))
        object.__setattr__(self, "recipe_ref", _text(self.recipe_ref, "RECIPE_REF_REQUIRED"))
        object.__setattr__(self, "browser_opened", _tri_bool(self.browser_opened, "BROWSER_OPENED_INVALID"))
        object.__setattr__(
            self,
            "trust_binding_current",
            _tri_bool(self.trust_binding_current, "TRUST_BINDING_CURRENT_INVALID"),
        )
        object.__setattr__(
            self,
            "capability_supported",
            _tri_bool(self.capability_supported, "CAPABILITY_SUPPORTED_INVALID"),
        )
        object.__setattr__(self, "input_observed", _tri_bool(self.input_observed, "INPUT_OBSERVED_INVALID"))
        object.__setattr__(self, "render_observed", _tri_bool(self.render_observed, "RENDER_OBSERVED_INVALID"))
        object.__setattr__(self, "output_bytes", _nn_int(self.output_bytes, "OUTPUT_BYTES_INVALID"))
        if not isinstance(self.acceptance_mode, AcceptanceEvidenceMode):
            raise BrowserAdapterError("ACCEPTANCE_MODE_INVALID")
        if not isinstance(self.persistence_mode, PersistenceEvidenceMode):
            raise BrowserAdapterError("PERSISTENCE_MODE_INVALID")
        object.__setattr__(
            self,
            "acceptance_evidence_ref",
            _text(self.acceptance_evidence_ref, "ACCEPTANCE_EVIDENCE_REF_INVALID", allow_empty=True),
        )
        object.__setattr__(
            self,
            "persistence_evidence_ref",
            _text(self.persistence_evidence_ref, "PERSISTENCE_EVIDENCE_REF_INVALID", allow_empty=True),
        )
        object.__setattr__(
            self,
            "browser_failure_code",
            _text(self.browser_failure_code, "BROWSER_FAILURE_CODE_INVALID", allow_empty=True),
        )
        if self.acceptance_mode in {AcceptanceEvidenceMode.USER_EXPLICIT, AcceptanceEvidenceMode.USER_REJECTED}:
            if not self.acceptance_evidence_ref:
                raise BrowserAdapterError("USER_ACCEPTANCE_EVIDENCE_REQUIRED")
        if self.persistence_mode in {
            PersistenceEvidenceMode.REOPEN_OBSERVED,
            PersistenceEvidenceMode.SAVE_OBSERVED,
            PersistenceEvidenceMode.DOWNLOAD_INITIATED,
        } and not self.persistence_evidence_ref:
            raise BrowserAdapterError("PERSISTENCE_EVIDENCE_REQUIRED")
        if self.render_observed is True and self.output_bytes is None:
            raise BrowserAdapterError("RENDER_OUTPUT_BYTES_REQUIRED")


@dataclass(frozen=True)
class BrowserFrictionProjectionV1:
    route_id: str
    build_refs: tuple[str, ...]
    recipe_refs: tuple[str, ...]
    stage_events: tuple[StageEvent, ...]
    accepted_value: AcceptedValue
    acceptance_mode: AcceptanceEvidenceMode
    persistence_mode: PersistenceEvidenceMode
    schema: str = ADAPTER_SCHEMA
    effect_authorized: bool = False
    execution_proven: bool = False


def _status_from_observation(
    value: bool | None,
    *,
    stage: str,
    success_reason: str,
    false_reason: str,
    false_code: str,
) -> StageEvent:
    if value is True:
        return StageEvent(stage, StageStatus.COMPLETED, reason=success_reason)
    if value is False:
        return StageEvent(
            stage,
            StageStatus.BLOCKED,
            reason=false_reason,
            failure_code=false_code,
        )
    return StageEvent(stage, StageStatus.UNKNOWN, reason="evidence not observed")


def _acceptance(obs: BrowserWitnessObservationV1) -> tuple[StageEvent, AcceptedValue]:
    mode = obs.acceptance_mode
    if mode is AcceptanceEvidenceMode.USER_EXPLICIT:
        return (
            StageEvent(
                "VERIFY_ACCEPT",
                StageStatus.COMPLETED,
                reason=f"USER_EXPLICIT evidence={obs.acceptance_evidence_ref}",
            ),
            AcceptedValue(
                criterion=ACCEPTED_VALUE_CRITERION,
                result=True,
                verifier=f"USER_EXPLICIT:{obs.acceptance_evidence_ref}",
            ),
        )
    if mode is AcceptanceEvidenceMode.USER_REJECTED:
        return (
            StageEvent(
                "VERIFY_ACCEPT",
                StageStatus.BLOCKED,
                reason=f"user explicitly rejected output; evidence={obs.acceptance_evidence_ref}",
                failure_code="VALUE_NOT_ACCEPTED",
            ),
            AcceptedValue(
                criterion=ACCEPTED_VALUE_CRITERION,
                result=False,
                verifier=f"USER_REJECTED:{obs.acceptance_evidence_ref}",
            ),
        )
    if mode is AcceptanceEvidenceMode.SYNTHETIC_TECHNICAL:
        return (
            StageEvent(
                "VERIFY_ACCEPT",
                StageStatus.UNKNOWN,
                reason="synthetic technical render cannot prove USER_EXPLICIT acceptance",
            ),
            AcceptedValue(
                criterion=ACCEPTED_VALUE_CRITERION,
                result=None,
                verifier="SYNTHETIC_TECHNICAL_NOT_USER_ACCEPTANCE",
            ),
        )
    return (
        StageEvent("VERIFY_ACCEPT", StageStatus.UNKNOWN, reason="user acceptance not observed"),
        AcceptedValue(
            criterion=ACCEPTED_VALUE_CRITERION,
            result=None,
            verifier="ACCEPTANCE_UNKNOWN",
        ),
    )


def _persistence(obs: BrowserWitnessObservationV1) -> StageEvent:
    mode = obs.persistence_mode
    if mode is PersistenceEvidenceMode.REOPEN_OBSERVED:
        return StageEvent(
            "SAVE_REOPEN",
            StageStatus.COMPLETED,
            reason=f"save/readback/reopen observed; evidence={obs.persistence_evidence_ref}",
        )
    if mode is PersistenceEvidenceMode.SAVE_OBSERVED:
        return StageEvent(
            "SAVE_REOPEN",
            StageStatus.UNKNOWN,
            reason=f"save observed but reopen not observed; evidence={obs.persistence_evidence_ref}",
        )
    if mode is PersistenceEvidenceMode.DOWNLOAD_INITIATED:
        return StageEvent(
            "SAVE_REOPEN",
            StageStatus.UNKNOWN,
            reason=f"download initiated; saved bytes/reopen not observed; evidence={obs.persistence_evidence_ref}",
        )
    if mode is PersistenceEvidenceMode.SIMULATED:
        return StageEvent(
            "SAVE_REOPEN",
            StageStatus.UNKNOWN,
            reason="simulated persistence cannot prove save/readback/reopen",
        )
    return StageEvent("SAVE_REOPEN", StageStatus.UNKNOWN, reason="persistence/reopen not observed")


def project_browser_observation(obs: BrowserWitnessObservationV1) -> BrowserFrictionProjectionV1:
    if not isinstance(obs, BrowserWitnessObservationV1):
        raise BrowserAdapterError("BROWSER_OBSERVATION_REQUIRED")

    discover = _status_from_observation(
        obs.browser_opened,
        stage="DISCOVER",
        success_reason="browser witness opened",
        false_reason="browser witness did not open",
        false_code="BROWSER_NOT_OPENED",
    )
    if obs.trust_binding_current is True:
        trust = StageEvent(
            "TRUST",
            StageStatus.COMPLETED,
            reason=f"exact build={obs.build_ref}; recipe={obs.recipe_ref}; current binding observed",
        )
    elif obs.trust_binding_current is False:
        trust = StageEvent(
            "TRUST",
            StageStatus.BLOCKED,
            reason="build/recipe trust binding stale or mismatched",
            failure_code="TRUST_BINDING_STALE",
        )
    else:
        trust = StageEvent("TRUST", StageStatus.UNKNOWN, reason="trust/currentness evidence not observed")

    capability = _status_from_observation(
        obs.capability_supported,
        stage="CAPABILITY_RESOLVE",
        success_reason="minimum browser capabilities observed",
        false_reason="required browser capability unavailable",
        false_code=obs.browser_failure_code or "BROWSER_CAPABILITY_UNAVAILABLE",
    )
    input_event = _status_from_observation(
        obs.input_observed,
        stage="INPUT",
        success_reason="local creator input observed",
        false_reason="creator input not observed",
        false_code="INPUT_REQUIRED",
    )
    execute = _status_from_observation(
        obs.render_observed,
        stage="EXECUTE",
        success_reason=(
            f"local render observed; output_bytes={obs.output_bytes}"
            if obs.render_observed is True
            else "local render observed"
        ),
        false_reason="render result not observed",
        false_code="RENDER_NOT_OBSERVED",
    )
    verify_accept, accepted_value = _acceptance(obs)

    events = (
        discover,
        trust,
        StageEvent("OPEN_INSTALL", StageStatus.NOT_APPLICABLE, reason="zero-install browser route"),
        StageEvent(
            "PERMISSION",
            StageStatus.NOT_APPLICABLE,
            reason="no persistent permission required by bounded local-file witness",
        ),
        StageEvent(
            "STORAGE_CHOICE",
            StageStatus.NOT_APPLICABLE,
            reason="persistent Aura Drive selection outside first-value witness",
        ),
        StageEvent("OPTIONAL_ACCOUNT", StageStatus.NOT_APPLICABLE, reason="no account required"),
        StageEvent("OPTIONAL_KEY", StageStatus.NOT_APPLICABLE, reason="no API key required"),
        input_event,
        capability,
        execute,
        verify_accept,
        _persistence(obs),
        StageEvent(
            "SHARE_OR_REUSE",
            StageStatus.NOT_APPLICABLE,
            reason="share/remix outside bounded first-value witness",
        ),
    )
    return BrowserFrictionProjectionV1(
        route_id=obs.route_id,
        build_refs=(obs.build_ref,),
        recipe_refs=(obs.recipe_ref,),
        stage_events=events,
        accepted_value=accepted_value,
        acceptance_mode=obs.acceptance_mode,
        persistence_mode=obs.persistence_mode,
    )


def build_browser_friction_receipt(
    decision: RouteDecisionBinding,
    observation: BrowserWitnessObservationV1,
    *,
    mission_head: str,
    cohort: Mapping[str, str],
    starting_state: Mapping[str, Any],
    friction_vector: Mapping[str, int | float | None],
    weights: Mapping[str, int | float],
    weighting_method: str,
    reopen_trigger: str,
    invalidators: Sequence[str] = (),
) -> FrictionReceipt:
    """Delegate final receipt identity to the canonical ZF-00 builder."""
    if not isinstance(decision, RouteDecisionBinding):
        raise BrowserAdapterError("ROUTE_DECISION_BINDING_REQUIRED")
    if decision.entry_surface != "ZERO_INSTALL_WEB_PWA":
        raise BrowserAdapterError("BROWSER_ROUTE_DECISION_REQUIRED")
    if set(friction_vector) != set(FRICTION_COMPONENTS):
        raise BrowserAdapterError("FRICTION_VECTOR_COMPONENTS_MISMATCH")

    projection = project_browser_observation(observation)
    try:
        return build_friction_receipt(
            decision,
            route_id=projection.route_id,
            mission_head=mission_head,
            build_refs=projection.build_refs,
            cohort=cohort,
            starting_state=starting_state,
            stage_events=projection.stage_events,
            accepted_value=projection.accepted_value,
            friction_vector=friction_vector,
            weights=weights,
            weighting_method=weighting_method,
            reopen_trigger=reopen_trigger,
            mandatory_account=False,
            mandatory_key=False,
            permissions=(),
            capability_refs=(decision.first_use_capability,),
            recipe_refs=projection.recipe_refs,
            privacy_telemetry_mode="LOCAL_ONLY_NO_TELEMETRY",
            invalidators=invalidators,
            evidence_class="LOCAL_TEST",
        )
    except FrictionReceiptError:
        raise
