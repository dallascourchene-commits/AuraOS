"""ZF-05A share readiness/action -> canonical ZF-00 friction projection.

D0 evidence adapter only. A reproducible/READY ShareLaunchPlanV1 is capability
readiness, not an observed share, reuse, referral, conversion, publication, or
adoption result. Only a bounded user-action observation may complete the canonical
SHARE_OR_REUSE stage. The final receipt identity remains owned by ZF-00.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Any, Mapping, Sequence

from tools.aura_adopt.adoption_friction_receipt import (
    FRICTION_COMPONENTS,
    FrictionReceipt,
    RouteDecisionBinding,
    StageEvent,
    StageStatus,
    build_friction_receipt,
)
from tools.aura_adopt.browser_friction_adapter import (
    AcceptanceEvidenceMode,
    BrowserWitnessObservationV1,
    BrowserFrictionProjectionV1,
    PersistenceEvidenceMode,
    project_browser_observation,
)

SHARE_LAUNCH_SCHEMA = "ShareLaunchPlanV1"
ADAPTER_SCHEMA = "ShareFrictionObservationAdapterV1"


class ShareFrictionError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


class ShareActionMode(str, Enum):
    USER_SHARE_OBSERVED = "USER_SHARE_OBSERVED"
    USER_REUSE_OBSERVED = "USER_REUSE_OBSERVED"
    READY_ONLY = "READY_ONLY"
    ATTEMPT_FAILED = "ATTEMPT_FAILED"
    UNKNOWN = "UNKNOWN"


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ShareFrictionError("NONCANONICAL_SHARE_STATE") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: Any, code: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ShareFrictionError(code)
    value = value.strip()
    if not value and not allow_empty:
        raise ShareFrictionError(code)
    return value


def _evidence_ref(value: Any, code: str, *, allow_empty: bool = False) -> str:
    value = _text(value, code, allow_empty=allow_empty)
    if not value:
        return value
    if len(value) > 256 or any(ch.isspace() for ch in value) or ":" not in value:
        raise ShareFrictionError(code)
    lowered = value.casefold()
    if any(token in lowered for token in ("email=", "phone=", "recipient=", "user_id=", "ip=")):
        raise ShareFrictionError("RECIPIENT_OR_PRIVATE_EVIDENCE_FORBIDDEN")
    return value


@dataclass(frozen=True)
class ShareActionObservationV1:
    mode: ShareActionMode
    evidence_ref: str = ""
    failure_code: str = ""
    schema: str = "ShareActionObservationV1"

    def __post_init__(self) -> None:
        if not isinstance(self.mode, ShareActionMode):
            raise ShareFrictionError("SHARE_ACTION_MODE_INVALID")
        object.__setattr__(
            self,
            "evidence_ref",
            _evidence_ref(self.evidence_ref, "SHARE_ACTION_EVIDENCE_INVALID", allow_empty=True),
        )
        object.__setattr__(
            self,
            "failure_code",
            _text(self.failure_code, "SHARE_FAILURE_CODE_INVALID", allow_empty=True),
        )
        if self.mode in {
            ShareActionMode.USER_SHARE_OBSERVED,
            ShareActionMode.USER_REUSE_OBSERVED,
            ShareActionMode.ATTEMPT_FAILED,
        } and not self.evidence_ref:
            raise ShareFrictionError("SHARE_ACTION_EVIDENCE_REQUIRED")
        if self.mode is ShareActionMode.ATTEMPT_FAILED and not self.failure_code:
            raise ShareFrictionError("SHARE_FAILURE_CODE_REQUIRED")


@dataclass(frozen=True)
class BrowserShareFrictionProjectionV1:
    browser_projection: BrowserFrictionProjectionV1
    share_launch_plan_digest: str
    share_capsule_digest: str
    share_action_mode: ShareActionMode
    share_stage: StageEvent
    stage_events: tuple[StageEvent, ...]
    schema: str = ADAPTER_SCHEMA
    publication_authorized: bool = False
    network_fetch_authorized: bool = False
    telemetry_authorized: bool = False
    recipient_tracking_authorized: bool = False
    payment_authorized: bool = False
    provider_call_authorized: bool = False
    adoption_success_proven: bool = False
    effect_authorized: bool = False
    execution_proven: bool = False


def validate_share_launch_plan(plan: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(plan, Mapping):
        raise ShareFrictionError("SHARE_LAUNCH_PLAN_REQUIRED")
    if plan.get("schema") != SHARE_LAUNCH_SCHEMA:
        raise ShareFrictionError("SHARE_LAUNCH_SCHEMA_MISMATCH")
    supplied_digest = _text(plan.get("plan_digest"), "SHARE_LAUNCH_PLAN_DIGEST_REQUIRED")
    logical = dict(plan)
    logical.pop("plan_digest", None)
    if _digest(logical) != supplied_digest:
        raise ShareFrictionError("SHARE_LAUNCH_PLAN_DIGEST_MISMATCH")
    _text(plan.get("capsule_digest"), "SHARE_CAPSULE_DIGEST_REQUIRED")
    status = _text(plan.get("status"), "SHARE_LAUNCH_STATUS_REQUIRED")
    if status not in {"READY_FOR_USER_ACTION", "ROUTE_OR_EVIDENCE_REQUIRED", "EVIDENCE_REQUIRED"}:
        raise ShareFrictionError("SHARE_LAUNCH_STATUS_INVALID")
    for field in (
        "network_fetch_authorized",
        "install_authorized",
        "execution_authorized",
        "execution_proven",
        "publication_authorized",
        "payment_authorized",
        "telemetry_authorized",
        "recipient_tracking_authorized",
        "provider_call_authorized",
        "adoption_success_proven",
    ):
        if plan.get(field) is not False:
            raise ShareFrictionError("SHARE_LAUNCH_AUTHORITY_WIDENING", field)
    blockers = plan.get("blockers")
    if not isinstance(blockers, (list, tuple)) or any(not isinstance(x, str) or not x.strip() for x in blockers):
        raise ShareFrictionError("SHARE_LAUNCH_BLOCKERS_INVALID")
    if status == "READY_FOR_USER_ACTION" and blockers:
        raise ShareFrictionError("READY_SHARE_LAUNCH_HAS_BLOCKERS")
    if status != "READY_FOR_USER_ACTION" and not blockers:
        raise ShareFrictionError("NONREADY_SHARE_LAUNCH_REQUIRES_BLOCKERS")
    return plan


def _share_stage(plan: Mapping[str, Any], observation: ShareActionObservationV1) -> StageEvent:
    status = plan["status"]
    if status != "READY_FOR_USER_ACTION":
        if observation.mode in {
            ShareActionMode.USER_SHARE_OBSERVED,
            ShareActionMode.USER_REUSE_OBSERVED,
        }:
            raise ShareFrictionError("SHARE_ACTION_OBSERVED_FROM_NONREADY_PLAN")
        return StageEvent(
            "SHARE_OR_REUSE",
            StageStatus.BLOCKED,
            reason="share/reuse launch evidence not ready: " + ",".join(plan["blockers"]),
            failure_code="SHARE_LAUNCH_NOT_READY",
        )

    if observation.mode is ShareActionMode.USER_SHARE_OBSERVED:
        return StageEvent(
            "SHARE_OR_REUSE",
            StageStatus.COMPLETED,
            reason=f"user share observed; evidence={observation.evidence_ref}",
        )
    if observation.mode is ShareActionMode.USER_REUSE_OBSERVED:
        return StageEvent(
            "SHARE_OR_REUSE",
            StageStatus.COMPLETED,
            reason=f"user reuse/remix observed; evidence={observation.evidence_ref}",
        )
    if observation.mode is ShareActionMode.ATTEMPT_FAILED:
        return StageEvent(
            "SHARE_OR_REUSE",
            StageStatus.BLOCKED,
            reason=f"share/reuse attempt failed; evidence={observation.evidence_ref}",
            failure_code=observation.failure_code,
        )
    return StageEvent(
        "SHARE_OR_REUSE",
        StageStatus.UNKNOWN,
        reason="share capsule is ready, but no bounded user share/reuse action was observed",
    )


def project_share_into_browser_friction(
    *,
    browser_observation: BrowserWitnessObservationV1,
    share_launch_plan: Mapping[str, Any],
    share_observation: ShareActionObservationV1,
) -> BrowserShareFrictionProjectionV1:
    if not isinstance(browser_observation, BrowserWitnessObservationV1):
        raise ShareFrictionError("BROWSER_OBSERVATION_REQUIRED")
    if not isinstance(share_observation, ShareActionObservationV1):
        raise ShareFrictionError("SHARE_ACTION_OBSERVATION_REQUIRED")
    plan = validate_share_launch_plan(share_launch_plan)
    browser = project_browser_observation(browser_observation)

    if share_observation.mode in {
        ShareActionMode.USER_SHARE_OBSERVED,
        ShareActionMode.USER_REUSE_OBSERVED,
        ShareActionMode.ATTEMPT_FAILED,
    } and browser.acceptance_mode is not AcceptanceEvidenceMode.USER_EXPLICIT:
        raise ShareFrictionError("SHARE_ACTION_REQUIRES_USER_EXPLICIT_ACCEPTANCE")

    stage = _share_stage(plan, share_observation)
    events = tuple(stage if event.stage == "SHARE_OR_REUSE" else event for event in browser.stage_events)
    if sum(event.stage == "SHARE_OR_REUSE" for event in events) != 1:
        raise ShareFrictionError("CANONICAL_SHARE_STAGE_NOT_UNIQUE")
    return BrowserShareFrictionProjectionV1(
        browser_projection=browser,
        share_launch_plan_digest=plan["plan_digest"],
        share_capsule_digest=plan["capsule_digest"],
        share_action_mode=share_observation.mode,
        share_stage=stage,
        stage_events=events,
    )


def build_browser_share_friction_receipt(
    decision: RouteDecisionBinding,
    browser_observation: BrowserWitnessObservationV1,
    share_launch_plan: Mapping[str, Any],
    share_observation: ShareActionObservationV1,
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
    if not isinstance(decision, RouteDecisionBinding):
        raise ShareFrictionError("ROUTE_DECISION_BINDING_REQUIRED")
    if decision.entry_surface != "ZERO_INSTALL_WEB_PWA":
        raise ShareFrictionError("BROWSER_ROUTE_DECISION_REQUIRED")
    if set(friction_vector) != set(FRICTION_COMPONENTS):
        raise ShareFrictionError("FRICTION_VECTOR_COMPONENTS_MISMATCH")

    projection = project_share_into_browser_friction(
        browser_observation=browser_observation,
        share_launch_plan=share_launch_plan,
        share_observation=share_observation,
    )
    browser = projection.browser_projection
    if browser.acceptance_mode is not AcceptanceEvidenceMode.USER_EXPLICIT:
        if friction_vector.get("creation_time_to_value") is not None:
            raise ShareFrictionError("CREATION_VALUE_FRICTION_REQUIRES_USER_ACCEPTANCE")
    if browser.persistence_mode is not PersistenceEvidenceMode.REOPEN_OBSERVED:
        if friction_vector.get("reuse_recovery") is not None:
            raise ShareFrictionError("REUSE_RECOVERY_FRICTION_REQUIRES_REOPEN")

    return build_friction_receipt(
        decision,
        route_id=browser.route_id,
        mission_head=mission_head,
        build_refs=tuple(browser.build_refs) + (
            f"share-launch:{projection.share_launch_plan_digest}",
            f"share-capsule:{projection.share_capsule_digest}",
        ),
        cohort=cohort,
        starting_state=starting_state,
        stage_events=projection.stage_events,
        accepted_value=browser.accepted_value,
        friction_vector=friction_vector,
        weights=weights,
        weighting_method=weighting_method,
        reopen_trigger=reopen_trigger,
        mandatory_account=False,
        mandatory_key=False,
        permissions=(),
        capability_refs=(decision.first_use_capability,),
        recipe_refs=browser.recipe_refs,
        privacy_telemetry_mode="LOCAL_ONLY_NO_TELEMETRY",
        invalidators=invalidators,
        evidence_class="LOCAL_TEST",
    )
