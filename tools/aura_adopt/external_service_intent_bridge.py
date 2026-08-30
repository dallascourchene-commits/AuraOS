"""AURA-ADOPT-001 ZF-07B/ZF-08B cross-cloud intent separation bridge.

Pure D0 integration membrane. It composes candidate presentation state from
already-earned storage and model/provider choices without merging authority.
It never links accounts, reads credentials, performs storage/network effects,
downloads models, calls providers, takes payment, or proves live currentness.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

SCHEMA = "ExternalServiceIntentPlanV1"
STORAGE_SCHEMA = "AuraDriveLocationPlanV1"
MODEL_SCHEMA = "CapabilityEscalationDecisionV1"

SHA256 = re.compile(r"^[0-9a-f]{64}$")
SAFE_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,255}$")

STORAGE_STATUSES = frozenset({
    "READY_FOR_LOCAL_USER_ACTION",
    "READY_FOR_STORAGE_AUTHORITY_GATE",
    "STORAGE_EVIDENCE_OR_ASSISTANCE_REQUIRED",
})
MODEL_DISPOSITIONS = frozenset({
    "NO_ESCALATION_REQUIRED",
    "LOCAL_ROUTE_READY",
    "USER_CHOICE_REQUIRED",
    "EVIDENCE_REQUIRED",
    "UPSTREAM_BLOCKED",
})
STORAGE_ACTIONS = frozenset({
    "USER_LINK_CLOUD_ACCOUNT",
    "USER_CONFIRM_CLOUD_STORAGE_SCOPE",
})
MODEL_ACTIONS = frozenset({
    "EXPLICIT_MODEL_DOWNLOAD_CONSENT",
    "EXPLICIT_REMOTE_EXECUTION_CONSENT",
    "REQUEST_CREDENTIAL_VIA_SECURE_OWNER",
    "REQUEST_PROVIDER_ACCOUNT_VIA_OWNER",
    "EXPLICIT_PAYMENT_CONSENT",
})


class IntentBridgeError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(v: Any) -> bytes:
    try:
        return json.dumps(
            v,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise IntentBridgeError("NONCANONICAL_INPUT") from exc


def _canonical_storage(v: Any) -> bytes:
    """Match the ZF-08A producer's exact canonicalization."""
    try:
        return json.dumps(
            v,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise IntentBridgeError("NONCANONICAL_STORAGE_INPUT") from exc


def _digest(domain: str, v: Any) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical(v)).hexdigest()


def _plain(value: Any) -> Any:
    value = getattr(value, "value", value)
    if isinstance(value, Mapping):
        return {str(key): _plain(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(child) for child in value]
    return value


def _token(v: Any, code: str) -> str:
    if not isinstance(v, str) or not SAFE_TOKEN.fullmatch(v):
        raise IntentBridgeError(code)
    return v


def _sha(v: Any, code: str) -> str:
    if not isinstance(v, str) or not SHA256.fullmatch(v):
        raise IntentBridgeError(code)
    return v


def _bool_false(m: Mapping[str, Any], fields: Sequence[str], code: str) -> None:
    for field in fields:
        if m.get(field) is not False:
            raise IntentBridgeError(code, field)


def _string_list(v: Any, code: str) -> tuple[str, ...]:
    if not isinstance(v, (list, tuple)):
        raise IntentBridgeError(code)
    return tuple(_token(item, code) for item in v)


def _as_mapping(value: Any, code: str) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    raise IntentBridgeError(code)


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _verify_storage_identity(plan: Mapping[str, Any], claimed_digest: str) -> None:
    logical = {key: _plain(value) for key, value in plan.items() if key != "plan_digest"}
    actual = hashlib.sha256(_canonical_storage(logical)).hexdigest()
    if actual != claimed_digest:
        raise IntentBridgeError("STORAGE_PLAN_DIGEST_MISMATCH")


def _verify_model_identity(decision: Mapping[str, Any], claimed_digest: str) -> None:
    logical = {
        key: _plain(value)
        for key, value in decision.items()
        if key != "decision_digest"
    }
    actual = _digest("AURA_ADOPT_CAPABILITY_ESCALATION_DECISION_V1", logical)
    if actual != claimed_digest:
        raise IntentBridgeError("MODEL_DECISION_DIGEST_MISMATCH")


def _storage_projection(plan: Mapping[str, Any] | Any) -> dict[str, Any]:
    plan = _as_mapping(plan, "STORAGE_PLAN_MAPPING_REQUIRED")
    if plan.get("schema") != STORAGE_SCHEMA:
        raise IntentBridgeError("STORAGE_SCHEMA_MISMATCH")
    digest = _sha(plan.get("plan_digest"), "STORAGE_PLAN_DIGEST_INVALID")
    _verify_storage_identity(plan, digest)

    status = _token(_enum_value(plan.get("status")), "STORAGE_STATUS_INVALID")
    if status not in STORAGE_STATUSES:
        raise IntentBridgeError("STORAGE_STATUS_UNSUPPORTED", status)
    _bool_false(
        plan,
        (
            "local_write_authorized",
            "local_read_authorized",
            "portable_export_authorized",
            "portable_reopen_proven",
            "cloud_read_authorized",
            "cloud_write_authorized",
            "cloud_sync_authorized",
            "account_link_authorized",
            "network_fetch_authorized",
            "effect_authorized",
            "execution_proven",
        ),
        "STORAGE_AUTHORITY_WIDENING",
    )
    actions = _string_list(plan.get("required_user_actions", []), "STORAGE_ACTION_INVALID")
    unknown = tuple(sorted(set(actions) - STORAGE_ACTIONS))
    if unknown:
        raise IntentBridgeError("STORAGE_ACTION_UNSUPPORTED", ",".join(unknown))
    cloud_selected = plan.get("cloud_selected")
    if type(cloud_selected) is not bool:
        raise IntentBridgeError("STORAGE_CLOUD_SELECTED_BOOL_REQUIRED")
    if not cloud_selected and actions:
        raise IntentBridgeError("STORAGE_ACTION_WITHOUT_CLOUD_SELECTION")
    if status == "READY_FOR_LOCAL_USER_ACTION" and (cloud_selected or actions):
        raise IntentBridgeError("STORAGE_STATUS_LOCAL_CONTRADICTION")
    if status == "READY_FOR_STORAGE_AUTHORITY_GATE":
        if not cloud_selected:
            raise IntentBridgeError("STORAGE_AUTHORITY_GATE_REQUIRES_CLOUD_SELECTION")
        if not actions:
            raise IntentBridgeError("STORAGE_AUTHORITY_GATE_ACTION_REQUIRED")

    return {
        "plan_digest": digest,
        "status": status,
        "cloud_selected": cloud_selected,
        "required_user_actions": actions,
        "primary_location": _token(plan.get("primary_location"), "PRIMARY_LOCATION_INVALID"),
        "secondary_location": _token(plan.get("secondary_location"), "SECONDARY_LOCATION_INVALID"),
        "request_source_digest": _sha(
            plan.get("request_source_digest"), "REQUEST_SOURCE_DIGEST_INVALID"
        ),
        "capability_source_digest": _sha(
            plan.get("capability_source_digest"), "CAPABILITY_SOURCE_DIGEST_INVALID"
        ),
    }


def _model_projection(decision: Mapping[str, Any] | Any) -> dict[str, Any]:
    decision = _as_mapping(decision, "MODEL_DECISION_MAPPING_REQUIRED")
    if decision.get("schema") != MODEL_SCHEMA:
        raise IntentBridgeError("MODEL_SCHEMA_MISMATCH")
    digest = _sha(decision.get("decision_digest"), "MODEL_DECISION_DIGEST_INVALID")
    _verify_model_identity(decision, digest)

    disposition = _token(_enum_value(decision.get("disposition")), "MODEL_DISPOSITION_INVALID")
    if disposition not in MODEL_DISPOSITIONS:
        raise IntentBridgeError("MODEL_DISPOSITION_UNSUPPORTED", disposition)
    _bool_false(
        decision,
        (
            "credential_prompt_performed",
            "credential_collected",
            "model_download_started",
            "provider_call_made",
            "payment_performed",
            "effect_authorized",
            "execution_proven",
        ),
        "MODEL_AUTHORITY_WIDENING",
    )

    # ZF-07A deliberately exposes the union of future action classes across all
    # eligible options. That union is diagnostic candidate-set information; an
    # actionable USER_CHOICE surface must preserve each exact option binding.
    earned_actions = _string_list(
        decision.get("earned_action_classes", []), "MODEL_ACTION_INVALID"
    )
    unknown = tuple(sorted(set(earned_actions) - MODEL_ACTIONS))
    if unknown:
        raise IntentBridgeError("MODEL_ACTION_UNSUPPORTED", ",".join(unknown))
    if disposition == "NO_ESCALATION_REQUIRED" and earned_actions:
        raise IntentBridgeError("MODEL_ACTION_WITHOUT_ESCALATION")

    selected_route_id = decision.get("selected_route_id")
    if selected_route_id is not None:
        selected_route_id = _token(selected_route_id, "MODEL_SELECTED_ROUTE_INVALID")

    options = decision.get("options", [])
    if not isinstance(options, (list, tuple)):
        raise IntentBridgeError("MODEL_OPTIONS_SEQUENCE_REQUIRED")
    provider_refs: set[str] = set()
    candidate_choices: list[dict[str, Any]] = []
    selected_required_actions: tuple[str, ...] | None = None
    saw_routed_option = False
    for option in options:
        if not isinstance(option, Mapping):
            raise IntentBridgeError("MODEL_OPTION_MAPPING_REQUIRED")

        route_id = _token(option.get("route_id"), "MODEL_OPTION_ROUTE_ID_INVALID")
        saw_routed_option = True
        required_actions = _string_list(
            option.get("required_actions", ()), "MODEL_OPTION_ACTION_INVALID"
        )
        option_unknown = tuple(sorted(set(required_actions) - MODEL_ACTIONS))
        if option_unknown:
            raise IntentBridgeError(
                "MODEL_OPTION_ACTION_UNSUPPORTED", ",".join(option_unknown)
            )
        evidence_digest = _sha(
            option.get("candidate_evidence_digest"),
            "MODEL_OPTION_EVIDENCE_DIGEST_INVALID",
        )
        evidence_ref = _token(
            option.get("candidate_evidence_ref"), "MODEL_OPTION_EVIDENCE_REF_INVALID"
        )
        model_ref = _token(option.get("model_ref"), "MODEL_OPTION_MODEL_REF_INVALID")
        provider_ref = option.get("provider_ref", "")
        if provider_ref:
            provider_ref = _token(provider_ref, "MODEL_PROVIDER_REF_INVALID")
            provider_refs.add(provider_ref)
        execution_location = _token(
            _enum_value(option.get("execution_location")),
            "MODEL_OPTION_EXECUTION_LOCATION_INVALID",
        )
        cost_class = _token(
            _enum_value(option.get("cost_class")), "MODEL_OPTION_COST_CLASS_INVALID"
        )
        candidate_choices.append({
            "route_id": route_id,
            "model_ref": model_ref,
            "provider_ref": provider_ref,
            "execution_location": execution_location,
            "cost_class": cost_class,
            "required_actions": required_actions,
            "candidate_evidence_ref": evidence_ref,
            "candidate_evidence_digest": evidence_digest,
        })
        if selected_route_id is not None and route_id == selected_route_id:
            selected_required_actions = required_actions

    if disposition == "LOCAL_ROUTE_READY":
        if selected_route_id is None:
            raise IntentBridgeError("MODEL_SELECTED_ROUTE_REQUIRED")
        if saw_routed_option and selected_required_actions is None:
            raise IntentBridgeError("MODEL_SELECTED_ROUTE_NOT_IN_OPTIONS")
        if selected_required_actions:
            raise IntentBridgeError("MODEL_SELECTED_ROUTE_REQUIRES_ACTION")
        presentable_choices: tuple[dict[str, Any], ...] = ()
    elif disposition == "USER_CHOICE_REQUIRED":
        if not candidate_choices:
            raise IntentBridgeError("MODEL_PRESENTABLE_CHOICES_REQUIRED")
        presentable_choices = tuple(candidate_choices)
    else:
        presentable_choices = ()

    return {
        "decision_digest": digest,
        "disposition": disposition,
        "selected_route_id": selected_route_id,
        "earned_action_classes": earned_actions,
        "candidate_choices": tuple(candidate_choices),
        "presentable_choices": presentable_choices,
        "provider_refs": tuple(sorted(provider_refs)),
        "residual_source_generation": _token(
            decision.get("residual_source_generation"),
            "MODEL_RESIDUAL_SOURCE_GENERATION_INVALID",
        ),
        "residual_source_currentness_ref": _token(
            decision.get("residual_source_currentness_ref"),
            "MODEL_RESIDUAL_CURRENTNESS_REF_INVALID",
        ),
        "router_currentness_digest": _sha(
            decision.get("router_currentness_digest"),
            "MODEL_ROUTER_CURRENTNESS_DIGEST_INVALID",
        ),
    }


@dataclass(frozen=True)
class ScopeEvidenceV1:
    """Caller-supplied source identity for a future authority owner.

    This is not an owner attestation. It is recorded only as unverified
    provenance and never clears currentness or authority gates.
    """

    scope: str
    evidence_ref: str
    evidence_digest: str
    source_generation: str
    currentness_ref: str

    def __post_init__(self) -> None:
        if self.scope not in {"AURA_DRIVE_STORAGE", "MODEL_PROVIDER"}:
            raise IntentBridgeError("EVIDENCE_SCOPE_INVALID", self.scope)
        _token(self.evidence_ref, "EVIDENCE_REF_INVALID")
        _sha(self.evidence_digest, "EVIDENCE_DIGEST_INVALID")
        _token(self.source_generation, "EVIDENCE_SOURCE_GENERATION_INVALID")
        _token(self.currentness_ref, "EVIDENCE_CURRENTNESS_REF_INVALID")


def compile_external_service_intent_plan(
    storage_plan: Mapping[str, Any] | Any,
    model_decision: Mapping[str, Any] | Any,
    *,
    scope_evidence: Sequence[ScopeEvidenceV1] = (),
) -> dict[str, Any]:
    storage = _storage_projection(storage_plan)
    model = _model_projection(model_decision)

    if not isinstance(scope_evidence, (list, tuple)):
        raise IntentBridgeError("SCOPE_EVIDENCE_SEQUENCE_REQUIRED")
    by_scope: dict[str, ScopeEvidenceV1] = {}
    refs: dict[str, str] = {}
    digests: dict[str, str] = {}
    for ev in scope_evidence:
        if not isinstance(ev, ScopeEvidenceV1):
            raise IntentBridgeError("SCOPE_EVIDENCE_INVALID")
        if ev.scope in by_scope:
            raise IntentBridgeError("DUPLICATE_SCOPE_EVIDENCE", ev.scope)
        by_scope[ev.scope] = ev
        if ev.evidence_ref in refs and refs[ev.evidence_ref] != ev.scope:
            raise IntentBridgeError("CROSS_SCOPE_EVIDENCE_REF_REUSE", ev.evidence_ref)
        refs[ev.evidence_ref] = ev.scope
        if ev.evidence_digest in digests and digests[ev.evidence_digest] != ev.scope:
            raise IntentBridgeError("CROSS_SCOPE_EVIDENCE_DIGEST_REUSE", ev.evidence_digest)
        digests[ev.evidence_digest] = ev.scope

    hard_blockers = []
    if storage["status"] == "STORAGE_EVIDENCE_OR_ASSISTANCE_REQUIRED":
        hard_blockers.append("STORAGE_PLAN_NOT_READY")
    if model["disposition"] in {"EVIDENCE_REQUIRED", "UPSTREAM_BLOCKED"}:
        hard_blockers.append("MODEL_DECISION_NOT_READY")

    candidate_groups: list[dict[str, Any]] = []
    if not hard_blockers:
        storage_actions = tuple(storage["required_user_actions"])
        if storage_actions:
            candidate_groups.append({
                "scope": "AURA_DRIVE_STORAGE",
                "actions": storage_actions,
                "authority_owner": "EXTERNAL_STORAGE_AUTHORITY_OWNER",
                "evidence_ref_supplied_unverified": "AURA_DRIVE_STORAGE" in by_scope,
                "evidence_owner_proven": False,
            })
        model_choices = tuple(model["presentable_choices"])
        if model_choices:
            candidate_groups.append({
                "scope": "MODEL_PROVIDER",
                "choices": model_choices,
                "candidate_action_classes": model["earned_action_classes"],
                "authority_owner": "EXTERNAL_MODEL_PROVIDER_AUTHORITY_OWNER",
                "evidence_ref_supplied_unverified": "MODEL_PROVIDER" in by_scope,
                "evidence_owner_proven": False,
            })

    # Producer identity is verified above, but this bridge does not own the live
    # storage/model currentness catalogs. Candidate actions therefore stop at an
    # explicit owner-currentness gate rather than becoming presentable prompts.
    presentation_groups: list[dict[str, Any]] = []
    blockers = list(hard_blockers)
    if hard_blockers:
        disposition = "REBASE_OR_EVIDENCE_REQUIRED"
    elif not candidate_groups:
        disposition = "NO_EXTERNAL_SERVICE_ACTIONS"
    else:
        blockers.append("OWNER_CURRENTNESS_RECHECK_REQUIRED")
        disposition = "OWNER_CURRENTNESS_GATE_REQUIRED"

    logical = {
        "schema": SCHEMA,
        "storage_plan_digest": storage["plan_digest"],
        "model_decision_digest": model["decision_digest"],
        "storage_status": storage["status"],
        "model_disposition": model["disposition"],
        "model_selected_route_id": model["selected_route_id"],
        "model_candidate_action_classes": model["earned_action_classes"],
        "model_candidate_choices": model["candidate_choices"],
        "storage_primary_location": storage["primary_location"],
        "storage_secondary_location": storage["secondary_location"],
        "storage_cloud_selected": storage["cloud_selected"],
        "storage_request_source_digest": storage["request_source_digest"],
        "storage_capability_source_digest": storage["capability_source_digest"],
        "model_residual_source_generation": model["residual_source_generation"],
        "model_residual_source_currentness_ref": model["residual_source_currentness_ref"],
        "model_router_currentness_digest": model["router_currentness_digest"],
        "model_provider_refs": model["provider_refs"],
        "candidate_action_groups": candidate_groups,
        "presentation_groups": presentation_groups,
        "blockers": tuple(blockers),
        "disposition": disposition,
        "owner_currentness_gate_required": bool(candidate_groups),
        "ready_for_user_presentation": False,
        "scope_evidence_refs_unverified": tuple(sorted(
            (
                scope,
                ev.evidence_ref,
                ev.evidence_digest,
                ev.source_generation,
                ev.currentness_ref,
            )
            for scope, ev in by_scope.items()
        )),
        "authority_scopes_coalesced": False,
        "storage_account_state_satisfies_model_credentials": False,
        "model_credentials_satisfy_storage_authority": False,
        "storage_read_authorized": False,
        "storage_write_authorized": False,
        "storage_sync_authorized": False,
        "account_link_authorized": False,
        "credential_prompt_performed": False,
        "credential_collected": False,
        "model_download_started": False,
        "provider_call_made": False,
        "payment_performed": False,
        "network_fetch_authorized": False,
        "effect_authorized": False,
        "execution_proven": False,
    }
    logical["plan_digest"] = _digest(
        "AURA_ADOPT_EXTERNAL_SERVICE_INTENT_PLAN_V1", logical
    )
    return logical
