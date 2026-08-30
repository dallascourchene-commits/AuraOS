"""AURA-ADOPT-001: zero-install first-value witness -> ZF-00B adapter.

This is a pure observation adapter. It does not own browser execution, route
selection, telemetry collection, user consent, storage, sharing, or effects.
It converts already-observed first-value witness facts into the canonical
AdoptionFrictionReceiptV1 owner without creating a parallel receipt identity.

Critical evidence law:
- SYNTHETIC_TECHNICAL never satisfies USER_EXPLICIT acceptance.
- DOWNLOAD_INITIATED or SAVE_OBSERVED never proves REOPEN_OBSERVED.
- UNKNOWN remains UNKNOWN.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Sequence

from tools.aura_adopt.adoption_friction_receipt import (
    AcceptedValue,
    FrictionReceipt,
    FrictionReceiptError,
    RouteDecisionBinding,
    StageEvent,
    StageStatus,
    build_friction_receipt,
)

SCHEMA = "FirstValueWitnessObservationV1"
ZERO_INSTALL_SURFACE = "ZERO_INSTALL_WEB_PWA"
READY_DISPOSITION = "READY_BOUNDED"


class AcceptanceEvidenceMode(str, Enum):
    NONE = "NONE"
    SYNTHETIC_TECHNICAL = "SYNTHETIC_TECHNICAL"
    USER_EXPLICIT_ACCEPT = "USER_EXPLICIT_ACCEPT"
    USER_EXPLICIT_REJECT = "USER_EXPLICIT_REJECT"


class SaveEvidenceMode(str, Enum):
    NONE = "NONE"
    DOWNLOAD_INITIATED = "DOWNLOAD_INITIATED"
    SAVE_OBSERVED = "SAVE_OBSERVED"
    REOPEN_OBSERVED = "REOPEN_OBSERVED"


def _ref(value: str | None) -> bool:
    return isinstance(value, str) and bool(value.strip())


@dataclass(frozen=True)
class FirstValueWitnessObservationV1:
    opened: bool
    trust_satisfied: bool | None
    input_selected: bool
    browser_capability_available: bool | None
    rendered: bool
    preview_shown: bool
    acceptance_mode: AcceptanceEvidenceMode
    acceptance_evidence_ref: str | None = None
    save_mode: SaveEvidenceMode = SaveEvidenceMode.NONE
    save_evidence_ref: str | None = None
    share_or_reuse_observed: bool = False
    share_or_reuse_evidence_ref: str | None = None
    schema: str = SCHEMA

    def __post_init__(self) -> None:
        if self.schema != SCHEMA:
            raise FrictionReceiptError("WITNESS_OBSERVATION_SCHEMA_MISMATCH")
        for name in (
            "opened", "input_selected", "rendered", "preview_shown",
            "share_or_reuse_observed",
        ):
            if type(getattr(self, name)) is not bool:
                raise FrictionReceiptError("WITNESS_BOOL_REQUIRED", name)
        if self.trust_satisfied is not None and type(self.trust_satisfied) is not bool:
            raise FrictionReceiptError("WITNESS_TRUST_STATE_INVALID")
        if self.browser_capability_available is not None and type(self.browser_capability_available) is not bool:
            raise FrictionReceiptError("WITNESS_BROWSER_CAPABILITY_STATE_INVALID")
        if not isinstance(self.acceptance_mode, AcceptanceEvidenceMode):
            raise FrictionReceiptError("WITNESS_ACCEPTANCE_MODE_INVALID")
        if not isinstance(self.save_mode, SaveEvidenceMode):
            raise FrictionReceiptError("WITNESS_SAVE_MODE_INVALID")

        if self.acceptance_mode in {
            AcceptanceEvidenceMode.USER_EXPLICIT_ACCEPT,
            AcceptanceEvidenceMode.USER_EXPLICIT_REJECT,
        } and not _ref(self.acceptance_evidence_ref):
            raise FrictionReceiptError("USER_ACCEPTANCE_EVIDENCE_REF_REQUIRED")
        if self.acceptance_mode in {
            AcceptanceEvidenceMode.NONE,
            AcceptanceEvidenceMode.SYNTHETIC_TECHNICAL,
        } and self.acceptance_evidence_ref is not None:
            raise FrictionReceiptError("UNBOUND_ACCEPTANCE_EVIDENCE_REF")

        if self.save_mode in {
            SaveEvidenceMode.SAVE_OBSERVED,
            SaveEvidenceMode.REOPEN_OBSERVED,
        } and not _ref(self.save_evidence_ref):
            raise FrictionReceiptError("SAVE_EVIDENCE_REF_REQUIRED")
        if self.save_mode in {
            SaveEvidenceMode.NONE,
            SaveEvidenceMode.DOWNLOAD_INITIATED,
        } and self.save_evidence_ref is not None:
            raise FrictionReceiptError("UNBOUND_SAVE_EVIDENCE_REF")

        if self.share_or_reuse_observed and not _ref(self.share_or_reuse_evidence_ref):
            raise FrictionReceiptError("SHARE_REUSE_EVIDENCE_REF_REQUIRED")
        if not self.share_or_reuse_observed and self.share_or_reuse_evidence_ref is not None:
            raise FrictionReceiptError("UNBOUND_SHARE_REUSE_EVIDENCE_REF")


def _event(
    stage: str,
    status: StageStatus,
    *,
    reason: str | None = None,
    failure_code: str | None = None,
    steps: int | None = None,
) -> StageEvent:
    return StageEvent(
        stage=stage,
        status=status,
        steps=steps,
        wall_time_ms=None,
        downloaded_bytes=0 if status is StageStatus.NOT_APPLICABLE else None,
        retained_bytes=0 if status is StageStatus.NOT_APPLICABLE else None,
        monetary_cost_microunits=0 if status is StageStatus.NOT_APPLICABLE else None,
        retries=0,
        reason=reason,
        failure_code=failure_code,
    )


def _binary_stage(stage: str, observed: bool, *, blocked_code: str, blocked_reason: str) -> StageEvent:
    if observed:
        return _event(stage, StageStatus.COMPLETED, steps=1)
    return _event(
        stage,
        StageStatus.BLOCKED,
        reason=blocked_reason,
        failure_code=blocked_code,
        steps=0,
    )


def _acceptance(obs: FirstValueWitnessObservationV1) -> tuple[StageEvent, AcceptedValue]:
    if obs.acceptance_mode is AcceptanceEvidenceMode.USER_EXPLICIT_ACCEPT:
        return (
            _event("VERIFY_ACCEPT", StageStatus.COMPLETED, steps=1),
            AcceptedValue(
                criterion="USER_EXPLICIT_FIRST_VALUE",
                result=True,
                verifier=f"USER_EXPLICIT:{obs.acceptance_evidence_ref}",
            ),
        )
    if obs.acceptance_mode is AcceptanceEvidenceMode.USER_EXPLICIT_REJECT:
        return (
            _event("VERIFY_ACCEPT", StageStatus.COMPLETED, steps=1),
            AcceptedValue(
                criterion="USER_EXPLICIT_FIRST_VALUE",
                result=False,
                verifier=f"USER_EXPLICIT:{obs.acceptance_evidence_ref}",
            ),
        )
    if obs.acceptance_mode is AcceptanceEvidenceMode.SYNTHETIC_TECHNICAL:
        return (
            _event(
                "VERIFY_ACCEPT",
                StageStatus.UNKNOWN,
                reason="SYNTHETIC_TECHNICAL_OUTPUT_DOES_NOT_PROVE_USER_ACCEPTANCE",
            ),
            AcceptedValue(
                criterion="USER_EXPLICIT_FIRST_VALUE",
                result=None,
                verifier="SYNTHETIC_TECHNICAL",
            ),
        )
    return (
        _event("VERIFY_ACCEPT", StageStatus.UNKNOWN, reason="USER_ACCEPTANCE_NOT_OBSERVED"),
        AcceptedValue(
            criterion="USER_EXPLICIT_FIRST_VALUE",
            result=None,
            verifier="UNOBSERVED",
        ),
    )


def _save_reopen(obs: FirstValueWitnessObservationV1) -> StageEvent:
    if obs.save_mode is SaveEvidenceMode.REOPEN_OBSERVED:
        return _event("SAVE_REOPEN", StageStatus.COMPLETED, steps=1)
    if obs.save_mode is SaveEvidenceMode.SAVE_OBSERVED:
        return _event(
            "SAVE_REOPEN", StageStatus.UNKNOWN,
            reason="SAVE_OBSERVED_BUT_REOPEN_NOT_OBSERVED", steps=1,
        )
    if obs.save_mode is SaveEvidenceMode.DOWNLOAD_INITIATED:
        return _event(
            "SAVE_REOPEN", StageStatus.UNKNOWN,
            reason="DOWNLOAD_INITIATED_DOES_NOT_PROVE_SAVE_OR_REOPEN", steps=1,
        )
    return _event("SAVE_REOPEN", StageStatus.UNKNOWN, reason="SAVE_REOPEN_NOT_OBSERVED")


def compile_first_value_receipt(
    decision: RouteDecisionBinding,
    observation: FirstValueWitnessObservationV1,
    *,
    route_id: str,
    mission_head: str,
    build_refs: Sequence[str],
    cohort: Mapping[str, str],
    recipe_ref: str,
    capability_refs: Sequence[str] = (),
    trust_evidence_ref: str | None = None,
    evidence_class: str = "LOCAL_TEST",
    privacy_telemetry_mode: str = "LOCAL_NO_TELEMETRY",
) -> FrictionReceipt:
    """Compile raw witness observations into the canonical ZF-00B receipt."""
    if not isinstance(decision, RouteDecisionBinding):
        raise FrictionReceiptError("ROUTE_DECISION_BINDING_REQUIRED")
    if decision.entry_surface != ZERO_INSTALL_SURFACE:
        raise FrictionReceiptError("ZERO_INSTALL_ROUTE_REQUIRED")
    if decision.disposition != READY_DISPOSITION or decision.blockers:
        raise FrictionReceiptError("ROUTE_NOT_READY_FOR_FIRST_VALUE_WITNESS")
    if not isinstance(observation, FirstValueWitnessObservationV1):
        raise FrictionReceiptError("WITNESS_OBSERVATION_REQUIRED")
    if not _ref(recipe_ref):
        raise FrictionReceiptError("RECIPE_REF_REQUIRED")

    events: list[StageEvent] = []
    events.append(_binary_stage(
        "DISCOVER", observation.opened,
        blocked_code="WITNESS_NOT_OPENED",
        blocked_reason="ZERO_INSTALL_ENTRY_WAS_NOT_OPENED",
    ))

    if observation.trust_satisfied is True:
        if not _ref(trust_evidence_ref):
            raise FrictionReceiptError("TRUST_EVIDENCE_REF_REQUIRED")
        events.append(_event("TRUST", StageStatus.COMPLETED, steps=0))
    elif observation.trust_satisfied is False:
        events.append(_event(
            "TRUST", StageStatus.BLOCKED,
            reason="TRUST_ADMISSION_FAILED",
            failure_code="TRUST_ADMISSION_FAILED",
            steps=0,
        ))
    else:
        if trust_evidence_ref is not None:
            raise FrictionReceiptError("UNBOUND_TRUST_EVIDENCE_REF")
        events.append(_event("TRUST", StageStatus.UNKNOWN, reason="TRUST_EVIDENCE_NOT_OBSERVED"))

    for stage, reason in (
        ("OPEN_INSTALL", "ZERO_INSTALL_BROWSER_ROUTE"),
        ("PERMISSION", "NO_MANDATORY_PERMISSION_FOR_WITNESS"),
        ("STORAGE_CHOICE", "NO_MANDATORY_STORAGE_CHOICE_FOR_WITNESS"),
        ("OPTIONAL_ACCOUNT", "NO_MANDATORY_ACCOUNT_FOR_WITNESS"),
        ("OPTIONAL_KEY", "NO_MANDATORY_API_KEY_FOR_WITNESS"),
    ):
        events.append(_event(stage, StageStatus.NOT_APPLICABLE, reason=reason, steps=0))

    events.append(_binary_stage(
        "INPUT", observation.input_selected,
        blocked_code="LOCAL_INPUT_NOT_SELECTED",
        blocked_reason="LOCAL_INPUT_WAS_NOT_SELECTED",
    ))

    if observation.browser_capability_available is True:
        events.append(_event("CAPABILITY_RESOLVE", StageStatus.COMPLETED, steps=0))
    elif observation.browser_capability_available is False:
        events.append(_event(
            "CAPABILITY_RESOLVE", StageStatus.BLOCKED,
            reason="REQUIRED_BROWSER_CAPABILITY_UNAVAILABLE",
            failure_code="BROWSER_CAPABILITY_UNAVAILABLE",
            steps=0,
        ))
    else:
        events.append(_event(
            "CAPABILITY_RESOLVE", StageStatus.UNKNOWN,
            reason="BROWSER_CAPABILITY_NOT_OBSERVED",
        ))

    events.append(_binary_stage(
        "EXECUTE", observation.rendered and observation.preview_shown,
        blocked_code="FIRST_VALUE_RENDER_NOT_PROVEN",
        blocked_reason="RENDER_AND_PREVIEW_WERE_NOT_BOTH_OBSERVED",
    ))

    accept_event, accepted_value = _acceptance(observation)
    events.append(accept_event)
    events.append(_save_reopen(observation))

    if observation.share_or_reuse_observed:
        events.append(_event("SHARE_OR_REUSE", StageStatus.COMPLETED, steps=1))
    else:
        events.append(_event(
            "SHARE_OR_REUSE", StageStatus.NOT_APPLICABLE,
            reason="NO_SHARE_OR_REUSE_CLAIM_FOR_FIRST_VALUE_WITNESS", steps=0,
        ))

    refs = list(capability_refs)
    for value in (
        trust_evidence_ref,
        observation.acceptance_evidence_ref,
        observation.save_evidence_ref,
        observation.share_or_reuse_evidence_ref,
    ):
        if value:
            refs.append(value)

    unknown_vector = {
        "discovery": None,
        "trust": None,
        "install": 0,
        "hardware": None,
        "storage_network": 0,
        "permission_credential": 0,
        "learning": None,
        "creation_time_to_value": None,
        "reuse_recovery": None,
    }
    unit_weights = {key: 1.0 for key in unknown_vector}

    return build_friction_receipt(
        decision,
        route_id=route_id,
        mission_head=mission_head,
        build_refs=build_refs,
        cohort=cohort,
        starting_state={"witness_schema": SCHEMA, "entry_surface": ZERO_INSTALL_SURFACE},
        stage_events=tuple(events),
        accepted_value=accepted_value,
        friction_vector=unknown_vector,
        weights=unit_weights,
        weighting_method="UNWEIGHTED_UNTIL_OBSERVED_FRICTION_VALUES_EXIST",
        reopen_trigger="WITNESS_OR_ZF00B_CONTRACT_CHANGES_OR_NEW_REAL_EVIDENCE",
        permissions=(),
        mandatory_account=False,
        mandatory_key=False,
        clarification_events=0,
        support_events=0,
        route_changes=(),
        capability_refs=tuple(refs),
        recipe_refs=(recipe_ref,),
        privacy_telemetry_mode=privacy_telemetry_mode,
        invalidators=(
            "SOURCE_CURRENTNESS_MISMATCH",
            "SYNTHETIC_ACCEPTANCE_LAUNDERED_AS_USER_ACCEPTANCE",
            "SIMULATED_SAVE_LAUNDERED_AS_REOPEN",
        ),
        evidence_class=evidence_class,
    )


__all__ = [
    "AcceptanceEvidenceMode",
    "FirstValueWitnessObservationV1",
    "SCHEMA",
    "SaveEvidenceMode",
    "compile_first_value_receipt",
]
