"""AURA-ADOPT-001: zero-install first-value witness -> ZF-00B adapter.

Pure observation adapter only. It does not own browser execution, route selection,
telemetry collection, user consent, trust verification, storage, sharing, or effects.
It converts already-observed witness facts into canonical AdoptionFrictionReceiptV1.

Evidence law:
- SYNTHETIC_TECHNICAL never satisfies USER_EXPLICIT acceptance.
- SAVE_REOPEN observations require a source/currentness-bound output artifact,
  a distinct save predecessor reference, and a distinct reopen reference whose
  observed artifact digests all match the rendered output.
- Caller-authored D0 observations are structural assertions, not authenticated
  physical consequences. This adapter therefore never emits SAVE_REOPEN=COMPLETED;
  a trusted browser/storage witness resolver must earn that state downstream.
- Consequence evidence is committed into stage/verifier digests; it is never
  mislabeled as a capability reference. Public capability refs use `capability:`;
  recipe refs use `arena-recipe:`; serialized references/cohorts are privacy-minimal.
- This adapter cannot complete TRUST; a trust-owner bridge must do that.
- Causally impossible witness combinations fail closed.
- UNKNOWN remains UNKNOWN.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re
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
_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@#+-]{1,255}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_EMAIL_RE = re.compile(r"(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}")
_COHORT_VALUE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:+/-]{0,63}$")
_SENSITIVE_REF_MARKERS = (
    "api_key", "apikey", "token", "secret", "password", "bearer", "sk-",
    "mailto:", "user=", "email=", "phone=", "prompt=", "content=",
)


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


def _private_like(value: str) -> bool:
    lowered = value.casefold()
    return (
        _EMAIL_RE.search(value) is not None
        or "://" in lowered
        or any(marker in lowered for marker in _SENSITIVE_REF_MARKERS)
    )


def _ref(value: str | None, code: str = "EVIDENCE_REF_INVALID") -> str:
    if not isinstance(value, str):
        raise FrictionReceiptError(code)
    clean = value.strip()
    if not _REF_RE.fullmatch(clean) or _private_like(clean):
        raise FrictionReceiptError(code)
    return clean


def _capability_ref(value: str | None) -> str:
    clean = _ref(value, "CAPABILITY_REF_INVALID")
    if not clean.casefold().startswith("capability:"):
        raise FrictionReceiptError("CAPABILITY_REF_NAMESPACE_REQUIRED")
    return clean


def _recipe_ref(value: str | None) -> str:
    clean = _ref(value, "RECIPE_REF_REQUIRED")
    if not clean.casefold().startswith("arena-recipe:"):
        raise FrictionReceiptError("RECIPE_REF_NAMESPACE_REQUIRED")
    return clean


def _privacy_minimal_cohort(cohort: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(cohort, Mapping) or not cohort:
        raise FrictionReceiptError("COHORT_DESCRIPTOR_REQUIRED")
    clean: dict[str, str] = {}
    for key, value in cohort.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise FrictionReceiptError("COHORT_VALUE_NOT_PRIVACY_MINIMAL")
        normalized = value.strip()
        if not _COHORT_VALUE_RE.fullmatch(normalized) or _private_like(normalized):
            raise FrictionReceiptError("COHORT_VALUE_NOT_PRIVACY_MINIMAL", key)
        clean[key] = normalized
    return clean


def _sha(value: str | None, code: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value.lower()):
        raise FrictionReceiptError(code)
    return value.lower()


def _evidence_commitment(kind: str, payload: Mapping[str, str]) -> str:
    encoded = json.dumps(
        {"kind": kind, **dict(payload)},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(b"AURA_FIRST_VALUE_EVIDENCE_V1\0" + encoded).hexdigest()


@dataclass(frozen=True)
class FirstValueWitnessObservationV1:
    opened: bool
    input_selected: bool
    browser_capability_available: bool | None
    rendered: bool
    preview_shown: bool
    acceptance_mode: AcceptanceEvidenceMode
    output_artifact_sha256: str | None = None
    evidence_source_generation: str | None = None
    evidence_currentness_ref: str | None = None
    acceptance_evidence_ref: str | None = None
    save_mode: SaveEvidenceMode = SaveEvidenceMode.NONE
    save_evidence_ref: str | None = None
    save_artifact_sha256: str | None = None
    reopen_evidence_ref: str | None = None
    reopen_artifact_sha256: str | None = None
    trust_failed: bool = False
    share_or_reuse_observed: bool = False
    share_or_reuse_evidence_ref: str | None = None
    schema: str = SCHEMA

    def __post_init__(self) -> None:
        if self.schema != SCHEMA:
            raise FrictionReceiptError("WITNESS_OBSERVATION_SCHEMA_MISMATCH")
        for name in (
            "opened", "input_selected", "rendered", "preview_shown", "trust_failed",
            "share_or_reuse_observed",
        ):
            if type(getattr(self, name)) is not bool:
                raise FrictionReceiptError("WITNESS_BOOL_REQUIRED", name)
        if self.browser_capability_available is not None and type(self.browser_capability_available) is not bool:
            raise FrictionReceiptError("WITNESS_BROWSER_CAPABILITY_STATE_INVALID")
        if not isinstance(self.acceptance_mode, AcceptanceEvidenceMode):
            raise FrictionReceiptError("WITNESS_ACCEPTANCE_MODE_INVALID")
        if not isinstance(self.save_mode, SaveEvidenceMode):
            raise FrictionReceiptError("WITNESS_SAVE_MODE_INVALID")

        explicit = self.acceptance_mode in {
            AcceptanceEvidenceMode.USER_EXPLICIT_ACCEPT,
            AcceptanceEvidenceMode.USER_EXPLICIT_REJECT,
        }
        if explicit:
            _ref(self.acceptance_evidence_ref, "USER_ACCEPTANCE_EVIDENCE_REF_REQUIRED")
        elif self.acceptance_evidence_ref is not None:
            raise FrictionReceiptError("UNBOUND_ACCEPTANCE_EVIDENCE_REF")

        if self.rendered:
            output_sha = _sha(self.output_artifact_sha256, "OUTPUT_ARTIFACT_SHA256_REQUIRED")
            source_generation = _ref(self.evidence_source_generation, "EVIDENCE_SOURCE_GENERATION_REQUIRED")
            currentness_ref = _ref(self.evidence_currentness_ref, "EVIDENCE_CURRENTNESS_REF_REQUIRED")
            object.__setattr__(self, "output_artifact_sha256", output_sha)
            object.__setattr__(self, "evidence_source_generation", source_generation)
            object.__setattr__(self, "evidence_currentness_ref", currentness_ref)
        else:
            for name, value in (
                ("output_artifact_sha256", self.output_artifact_sha256),
                ("evidence_source_generation", self.evidence_source_generation),
                ("evidence_currentness_ref", self.evidence_currentness_ref),
            ):
                if value is not None:
                    raise FrictionReceiptError("UNBOUND_RENDER_EVIDENCE", name)

        if self.save_mode is SaveEvidenceMode.SAVE_OBSERVED:
            _ref(self.save_evidence_ref, "SAVE_EVIDENCE_REF_REQUIRED")
            saved_sha = _sha(self.save_artifact_sha256, "SAVE_ARTIFACT_SHA256_REQUIRED")
            if saved_sha != self.output_artifact_sha256:
                raise FrictionReceiptError("SAVE_ARTIFACT_DIGEST_MISMATCH")
            if self.reopen_evidence_ref is not None or self.reopen_artifact_sha256 is not None:
                raise FrictionReceiptError("UNBOUND_REOPEN_EVIDENCE")
            object.__setattr__(self, "save_artifact_sha256", saved_sha)
        elif self.save_mode is SaveEvidenceMode.REOPEN_OBSERVED:
            save_ref = _ref(self.save_evidence_ref, "SAVE_EVIDENCE_REF_REQUIRED")
            reopen_ref = _ref(self.reopen_evidence_ref, "REOPEN_EVIDENCE_REF_REQUIRED")
            if save_ref == reopen_ref:
                raise FrictionReceiptError("SAVE_REOPEN_EVIDENCE_REF_REUSE")
            saved_sha = _sha(self.save_artifact_sha256, "SAVE_ARTIFACT_SHA256_REQUIRED")
            reopened_sha = _sha(self.reopen_artifact_sha256, "REOPEN_ARTIFACT_SHA256_REQUIRED")
            if saved_sha != self.output_artifact_sha256:
                raise FrictionReceiptError("SAVE_ARTIFACT_DIGEST_MISMATCH")
            if reopened_sha != self.output_artifact_sha256:
                raise FrictionReceiptError("REOPEN_ARTIFACT_DIGEST_MISMATCH")
            object.__setattr__(self, "save_artifact_sha256", saved_sha)
            object.__setattr__(self, "reopen_artifact_sha256", reopened_sha)
        else:
            for name, value in (
                ("save_evidence_ref", self.save_evidence_ref),
                ("save_artifact_sha256", self.save_artifact_sha256),
                ("reopen_evidence_ref", self.reopen_evidence_ref),
                ("reopen_artifact_sha256", self.reopen_artifact_sha256),
            ):
                if value is not None:
                    raise FrictionReceiptError("UNBOUND_SAVE_REOPEN_EVIDENCE", name)

        if self.share_or_reuse_observed:
            _ref(self.share_or_reuse_evidence_ref, "SHARE_REUSE_EVIDENCE_REF_REQUIRED")
        elif self.share_or_reuse_evidence_ref is not None:
            raise FrictionReceiptError("UNBOUND_SHARE_REUSE_EVIDENCE_REF")

        if self.rendered and not self.opened:
            raise FrictionReceiptError("RENDER_REQUIRES_OPENED_WITNESS")
        if self.rendered and not self.input_selected:
            raise FrictionReceiptError("RENDER_REQUIRES_SELECTED_INPUT")
        if self.rendered and self.browser_capability_available is not True:
            raise FrictionReceiptError("RENDER_REQUIRES_BROWSER_CAPABILITY")
        if self.preview_shown and not self.rendered:
            raise FrictionReceiptError("PREVIEW_REQUIRES_RENDER")
        if explicit and not self.preview_shown:
            raise FrictionReceiptError("USER_ACCEPTANCE_REQUIRES_PREVIEW")
        if self.save_mode is not SaveEvidenceMode.NONE and not self.rendered:
            raise FrictionReceiptError("SAVE_OBSERVATION_REQUIRES_RENDER")
        if self.share_or_reuse_observed and not self.rendered:
            raise FrictionReceiptError("SHARE_REUSE_REQUIRES_RENDER")

    def common_evidence_binding(self) -> dict[str, str]:
        if not self.rendered:
            raise FrictionReceiptError("RENDER_EVIDENCE_REQUIRED")
        return {
            "artifact_sha256": str(self.output_artifact_sha256),
            "source_generation": str(self.evidence_source_generation),
            "currentness_ref": str(self.evidence_currentness_ref),
        }


def _event(stage: str, status: StageStatus, *, reason: str | None = None,
           failure_code: str | None = None, steps: int | None = None) -> StageEvent:
    return StageEvent(
        stage=stage, status=status, steps=steps, wall_time_ms=None,
        downloaded_bytes=0 if status is StageStatus.NOT_APPLICABLE else None,
        retained_bytes=0 if status is StageStatus.NOT_APPLICABLE else None,
        monetary_cost_microunits=0 if status is StageStatus.NOT_APPLICABLE else None,
        retries=0, reason=reason, failure_code=failure_code,
    )


def _binary_stage(stage: str, observed: bool, *, blocked_code: str, blocked_reason: str) -> StageEvent:
    if observed:
        return _event(stage, StageStatus.COMPLETED, steps=1)
    return _event(stage, StageStatus.BLOCKED, reason=blocked_reason, failure_code=blocked_code, steps=0)


def _acceptance(obs: FirstValueWitnessObservationV1) -> tuple[StageEvent, AcceptedValue]:
    artifact = obs.output_artifact_sha256 or "UNOBSERVED"
    if obs.acceptance_mode in {
        AcceptanceEvidenceMode.USER_EXPLICIT_ACCEPT,
        AcceptanceEvidenceMode.USER_EXPLICIT_REJECT,
    }:
        ref = _ref(obs.acceptance_evidence_ref, "USER_ACCEPTANCE_EVIDENCE_REF_REQUIRED")
        commitment = _evidence_commitment(
            "USER_EXPLICIT_ACCEPTANCE",
            {
                **obs.common_evidence_binding(),
                "evidence_ref": ref,
                "result": "ACCEPT" if obs.acceptance_mode is AcceptanceEvidenceMode.USER_EXPLICIT_ACCEPT else "REJECT",
            },
        )
        result = obs.acceptance_mode is AcceptanceEvidenceMode.USER_EXPLICIT_ACCEPT
        return (
            _event("VERIFY_ACCEPT", StageStatus.COMPLETED, reason=f"EVIDENCE_COMMITMENT:{commitment}", steps=1),
            AcceptedValue("USER_EXPLICIT_FIRST_VALUE", result, f"EVIDENCE_COMMITMENT:{commitment}"),
        )
    if obs.acceptance_mode is AcceptanceEvidenceMode.SYNTHETIC_TECHNICAL:
        return (
            _event("VERIFY_ACCEPT", StageStatus.UNKNOWN,
                   reason="SYNTHETIC_TECHNICAL_OUTPUT_DOES_NOT_PROVE_USER_ACCEPTANCE"),
            AcceptedValue("USER_EXPLICIT_FIRST_VALUE", None, f"SYNTHETIC_TECHNICAL@sha256:{artifact}"),
        )
    return (
        _event("VERIFY_ACCEPT", StageStatus.UNKNOWN, reason="USER_ACCEPTANCE_NOT_OBSERVED"),
        AcceptedValue("USER_EXPLICIT_FIRST_VALUE", None, f"UNOBSERVED@sha256:{artifact}"),
    )


def _save_reopen(obs: FirstValueWitnessObservationV1) -> StageEvent:
    if obs.save_mode is SaveEvidenceMode.REOPEN_OBSERVED:
        commitment = _evidence_commitment(
            "SAVE_REOPEN_STRUCTURAL_ASSERTION",
            {
                **obs.common_evidence_binding(),
                "save_evidence_ref": _ref(obs.save_evidence_ref, "SAVE_EVIDENCE_REF_REQUIRED"),
                "save_artifact_sha256": str(obs.save_artifact_sha256),
                "reopen_evidence_ref": _ref(obs.reopen_evidence_ref, "REOPEN_EVIDENCE_REF_REQUIRED"),
                "reopen_artifact_sha256": str(obs.reopen_artifact_sha256),
            },
        )
        return _event(
            "SAVE_REOPEN",
            StageStatus.UNKNOWN,
            reason=(
                "STRUCTURALLY_BOUND_REOPEN_REQUIRES_TRUSTED_WITNESS_RESOLVER"
                f"@EVIDENCE_COMMITMENT:{commitment}"
            ),
            steps=2,
        )
    if obs.save_mode is SaveEvidenceMode.SAVE_OBSERVED:
        commitment = _evidence_commitment(
            "SAVE_ONLY_STRUCTURAL_ASSERTION",
            {
                **obs.common_evidence_binding(),
                "save_evidence_ref": _ref(obs.save_evidence_ref, "SAVE_EVIDENCE_REF_REQUIRED"),
                "save_artifact_sha256": str(obs.save_artifact_sha256),
            },
        )
        return _event(
            "SAVE_REOPEN", StageStatus.UNKNOWN,
            reason=f"SAVE_OBSERVED_BUT_REOPEN_NOT_OBSERVED@EVIDENCE_COMMITMENT:{commitment}",
            steps=1,
        )
    if obs.save_mode is SaveEvidenceMode.DOWNLOAD_INITIATED:
        return _event("SAVE_REOPEN", StageStatus.UNKNOWN,
                      reason="DOWNLOAD_INITIATED_DOES_NOT_PROVE_SAVE_OR_REOPEN", steps=1)
    return _event("SAVE_REOPEN", StageStatus.UNKNOWN, reason="SAVE_REOPEN_NOT_OBSERVED")


def _share_or_reuse(obs: FirstValueWitnessObservationV1) -> StageEvent:
    if not obs.share_or_reuse_observed:
        return _event("SHARE_OR_REUSE", StageStatus.NOT_APPLICABLE,
                      reason="NO_SHARE_OR_REUSE_CLAIM_FOR_FIRST_VALUE_WITNESS", steps=0)
    commitment = _evidence_commitment(
        "SHARE_OR_REUSE",
        {
            **obs.common_evidence_binding(),
            "evidence_ref": _ref(obs.share_or_reuse_evidence_ref, "SHARE_REUSE_EVIDENCE_REF_REQUIRED"),
        },
    )
    return _event("SHARE_OR_REUSE", StageStatus.COMPLETED,
                  reason=f"EVIDENCE_COMMITMENT:{commitment}", steps=1)


def compile_first_value_receipt(
    decision: RouteDecisionBinding,
    observation: FirstValueWitnessObservationV1,
    *, route_id: str, mission_head: str, build_refs: Sequence[str],
    cohort: Mapping[str, str], recipe_ref: str, capability_refs: Sequence[str] = (),
    evidence_class: str = "LOCAL_TEST", privacy_telemetry_mode: str = "LOCAL_NO_TELEMETRY",
) -> FrictionReceipt:
    if not isinstance(decision, RouteDecisionBinding):
        raise FrictionReceiptError("ROUTE_DECISION_BINDING_REQUIRED")
    if decision.entry_surface != ZERO_INSTALL_SURFACE:
        raise FrictionReceiptError("ZERO_INSTALL_ROUTE_REQUIRED")
    if decision.disposition != READY_DISPOSITION or decision.blockers:
        raise FrictionReceiptError("ROUTE_NOT_READY_FOR_FIRST_VALUE_WITNESS")
    if not isinstance(observation, FirstValueWitnessObservationV1):
        raise FrictionReceiptError("WITNESS_OBSERVATION_REQUIRED")

    recipe = _recipe_ref(recipe_ref)
    cap_refs = tuple(_capability_ref(value) for value in capability_refs)
    cohort_clean = _privacy_minimal_cohort(cohort)
    build_refs_clean = tuple(_ref(value, "BUILD_REF_INVALID") for value in build_refs)
    events: list[StageEvent] = [
        _binary_stage("DISCOVER", observation.opened,
                      blocked_code="WITNESS_NOT_OPENED",
                      blocked_reason="ZERO_INSTALL_ENTRY_WAS_NOT_OPENED")
    ]

    if observation.trust_failed:
        events.append(_event("TRUST", StageStatus.BLOCKED,
                             reason="TRUST_ADMISSION_FAILED",
                             failure_code="TRUST_ADMISSION_FAILED", steps=0))
    else:
        events.append(_event("TRUST", StageStatus.UNKNOWN,
                             reason="TRUST_OWNER_EVIDENCE_NOT_BOUND_BY_WITNESS_ADAPTER"))

    for stage, reason in (
        ("OPEN_INSTALL", "ZERO_INSTALL_BROWSER_ROUTE"),
        ("PERMISSION", "NO_MANDATORY_PERMISSION_FOR_WITNESS"),
        ("STORAGE_CHOICE", "NO_MANDATORY_STORAGE_CHOICE_FOR_WITNESS"),
        ("OPTIONAL_ACCOUNT", "NO_MANDATORY_ACCOUNT_FOR_WITNESS"),
        ("OPTIONAL_KEY", "NO_MANDATORY_API_KEY_FOR_WITNESS"),
    ):
        events.append(_event(stage, StageStatus.NOT_APPLICABLE, reason=reason, steps=0))

    events.append(_binary_stage("INPUT", observation.input_selected,
                                blocked_code="LOCAL_INPUT_NOT_SELECTED",
                                blocked_reason="LOCAL_INPUT_WAS_NOT_SELECTED"))
    if observation.browser_capability_available is True:
        events.append(_event("CAPABILITY_RESOLVE", StageStatus.COMPLETED, steps=0))
    elif observation.browser_capability_available is False:
        events.append(_event("CAPABILITY_RESOLVE", StageStatus.BLOCKED,
                             reason="REQUIRED_BROWSER_CAPABILITY_UNAVAILABLE",
                             failure_code="BROWSER_CAPABILITY_UNAVAILABLE", steps=0))
    else:
        events.append(_event("CAPABILITY_RESOLVE", StageStatus.UNKNOWN,
                             reason="BROWSER_CAPABILITY_NOT_OBSERVED"))

    events.append(_binary_stage("EXECUTE", observation.rendered and observation.preview_shown,
                                blocked_code="FIRST_VALUE_RENDER_NOT_PROVEN",
                                blocked_reason="RENDER_AND_PREVIEW_WERE_NOT_BOTH_OBSERVED"))
    accept_event, accepted_value = _acceptance(observation)
    events.append(accept_event)
    events.append(_save_reopen(observation))
    events.append(_share_or_reuse(observation))

    vector = {
        "discovery": None, "trust": None, "install": 0, "hardware": None,
        "storage_network": 0, "permission_credential": 0, "learning": None,
        "creation_time_to_value": None, "reuse_recovery": None,
    }
    starting_state = {"witness_schema": SCHEMA, "entry_surface": ZERO_INSTALL_SURFACE}
    if observation.rendered:
        starting_state.update({
            "output_artifact_sha256": observation.output_artifact_sha256,
            "evidence_source_generation": observation.evidence_source_generation,
            "evidence_currentness_ref": observation.evidence_currentness_ref,
        })

    return build_friction_receipt(
        decision, route_id=route_id, mission_head=mission_head, build_refs=build_refs_clean,
        cohort=cohort_clean, starting_state=starting_state, stage_events=tuple(events),
        accepted_value=accepted_value, friction_vector=vector,
        weights={key: 1.0 for key in vector},
        weighting_method="UNWEIGHTED_UNTIL_OBSERVED_FRICTION_VALUES_EXIST",
        reopen_trigger="WITNESS_OR_ZF00B_CONTRACT_CHANGES_OR_NEW_REAL_EVIDENCE",
        permissions=(), mandatory_account=False, mandatory_key=False,
        clarification_events=0, support_events=0, route_changes=(),
        capability_refs=cap_refs, recipe_refs=(recipe,),
        privacy_telemetry_mode=privacy_telemetry_mode,
        invalidators=(
            "SOURCE_CURRENTNESS_MISMATCH",
            "SYNTHETIC_ACCEPTANCE_LAUNDERED_AS_USER_ACCEPTANCE",
            "SIMULATED_SAVE_LAUNDERED_AS_REOPEN",
            "SAVE_REOPEN_ARTIFACT_CHAIN_MISMATCH",
            "STRUCTURAL_EVENT_ASSERTION_LAUNDERED_AS_AUTHENTICATED_CONSEQUENCE",
            "CONSEQUENCE_EVIDENCE_MISLABELED_AS_CAPABILITY",
            "PRIVATE_CONTENT_LAUNDERED_AS_REFERENCE_OR_COHORT",
            "TRUST_POINTER_PRESENCE_LAUNDERED_AS_TRUST_COMPLETION",
            "WITNESS_CAUSALITY_CONTRADICTION",
        ),
        evidence_class=evidence_class,
    )


__all__ = ["AcceptanceEvidenceMode", "FirstValueWitnessObservationV1", "SCHEMA",
           "SaveEvidenceMode", "compile_first_value_receipt"]