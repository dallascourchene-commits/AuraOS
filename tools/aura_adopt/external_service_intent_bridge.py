"""AURA-ADOPT-001 ZF-07B/ZF-08B cross-cloud intent separation bridge.

Pure D0 integration membrane. It composes the *presentation* of already-earned
storage and model/provider choices without merging their authority scopes.
It never links accounts, reads credentials, performs storage/network effects,
downloads models, calls providers, or takes payment.
"""
from __future__ import annotations

from dataclasses import dataclass
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
        return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
    except (TypeError, ValueError) as exc:
        raise IntentBridgeError("NONCANONICAL_INPUT") from exc

def _digest(domain: str, v: Any) -> str:
    return hashlib.sha256(domain.encode() + b"\0" + _canonical(v)).hexdigest()

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
    out = []
    for item in v:
        out.append(_token(item, code))
    return tuple(out)

def _storage_projection(plan: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(plan, Mapping):
        raise IntentBridgeError("STORAGE_PLAN_MAPPING_REQUIRED")
    if plan.get("schema") != STORAGE_SCHEMA:
        raise IntentBridgeError("STORAGE_SCHEMA_MISMATCH")
    status = _token(plan.get("status"), "STORAGE_STATUS_INVALID")
    if status not in STORAGE_STATUSES:
        raise IntentBridgeError("STORAGE_STATUS_UNSUPPORTED", status)
    digest = _sha(plan.get("plan_digest"), "STORAGE_PLAN_DIGEST_INVALID")
    _bool_false(plan, (
        "local_write_authorized", "local_read_authorized", "portable_export_authorized",
        "portable_reopen_proven", "cloud_read_authorized", "cloud_write_authorized",
        "cloud_sync_authorized", "account_link_authorized", "network_fetch_authorized",
        "effect_authorized", "execution_proven",
    ), "STORAGE_AUTHORITY_WIDENING")
    actions = _string_list(plan.get("required_user_actions", []), "STORAGE_ACTION_INVALID")
    unknown = tuple(sorted(set(actions) - STORAGE_ACTIONS))
    if unknown:
        raise IntentBridgeError("STORAGE_ACTION_UNSUPPORTED", ",".join(unknown))
    cloud_selected = plan.get("cloud_selected")
    if type(cloud_selected) is not bool:
        raise IntentBridgeError("STORAGE_CLOUD_SELECTED_BOOL_REQUIRED")
    if not cloud_selected and actions:
        raise IntentBridgeError("STORAGE_ACTION_WITHOUT_CLOUD_SELECTION")
    if cloud_selected and status == "READY_FOR_LOCAL_USER_ACTION":
        raise IntentBridgeError("STORAGE_STATUS_CLOUD_CONTRADICTION")
    return {
        "plan_digest": digest,
        "status": status,
        "cloud_selected": cloud_selected,
        "required_user_actions": actions,
        "primary_location": _token(plan.get("primary_location"), "PRIMARY_LOCATION_INVALID"),
        "secondary_location": _token(plan.get("secondary_location"), "SECONDARY_LOCATION_INVALID"),
    }

def _model_projection(decision: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(decision, Mapping):
        raise IntentBridgeError("MODEL_DECISION_MAPPING_REQUIRED")
    if decision.get("schema") != MODEL_SCHEMA:
        raise IntentBridgeError("MODEL_SCHEMA_MISMATCH")
    digest = _sha(decision.get("decision_digest"), "MODEL_DECISION_DIGEST_INVALID")
    disposition = _token(decision.get("disposition"), "MODEL_DISPOSITION_INVALID")
    if disposition not in MODEL_DISPOSITIONS:
        raise IntentBridgeError("MODEL_DISPOSITION_UNSUPPORTED", disposition)
    _bool_false(decision, (
        "credential_prompt_performed", "credential_collected", "model_download_started",
        "provider_call_made", "payment_performed", "effect_authorized", "execution_proven",
    ), "MODEL_AUTHORITY_WIDENING")
    # ZF-07A exposes the union of already-earned future action classes.
    actions = _string_list(decision.get("earned_action_classes", []), "MODEL_ACTION_INVALID")
    unknown = tuple(sorted(set(actions) - MODEL_ACTIONS))
    if unknown:
        raise IntentBridgeError("MODEL_ACTION_UNSUPPORTED", ",".join(unknown))
    if disposition in {"NO_ESCALATION_REQUIRED", "LOCAL_ROUTE_READY"} and actions:
        raise IntentBridgeError("MODEL_ACTION_WITHOUT_ESCALATION")
    options = decision.get("options", [])
    if not isinstance(options, (list, tuple)):
        raise IntentBridgeError("MODEL_OPTIONS_SEQUENCE_REQUIRED")
    provider_refs: set[str] = set()
    for option in options:
        if not isinstance(option, Mapping):
            raise IntentBridgeError("MODEL_OPTION_MAPPING_REQUIRED")
        for field in ("candidate_evidence_digest",):
            if field in option:
                _sha(option[field], "MODEL_OPTION_EVIDENCE_DIGEST_INVALID")
        ref = option.get("provider_ref", "")
        if ref:
            provider_refs.add(_token(ref, "MODEL_PROVIDER_REF_INVALID"))
    return {
        "decision_digest": digest,
        "disposition": disposition,
        "earned_action_classes": actions,
        "provider_refs": tuple(sorted(provider_refs)),
    }

@dataclass(frozen=True)
class ScopeEvidenceV1:
    """Optional evidence identity for a future authority owner.

    The bridge never treats this evidence as authority. It only enforces that
    the same evidence identity is not cross-used for storage and model scopes.
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
    storage_plan: Mapping[str, Any],
    model_decision: Mapping[str, Any],
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

    storage_actions = tuple(storage["required_user_actions"])
    model_actions = tuple(model["earned_action_classes"])

    # Coalescing means one presentation surface can display both groups. It does
    # not merge actions, evidence, accounts, credentials, payment, or authority.
    groups = []
    if storage_actions:
        groups.append({
            "scope": "AURA_DRIVE_STORAGE",
            "actions": storage_actions,
            "authority_owner": "EXTERNAL_STORAGE_AUTHORITY_OWNER",
            "evidence_present": "AURA_DRIVE_STORAGE" in by_scope,
        })
    if model_actions:
        groups.append({
            "scope": "MODEL_PROVIDER",
            "actions": model_actions,
            "authority_owner": "EXTERNAL_MODEL_PROVIDER_AUTHORITY_OWNER",
            "evidence_present": "MODEL_PROVIDER" in by_scope,
        })

    blockers = []
    if storage["status"] == "STORAGE_EVIDENCE_OR_ASSISTANCE_REQUIRED":
        blockers.append("STORAGE_PLAN_NOT_READY")
    if model["disposition"] in {"EVIDENCE_REQUIRED", "UPSTREAM_BLOCKED"}:
        blockers.append("MODEL_DECISION_NOT_READY")

    if blockers:
        disposition = "REBASE_OR_EVIDENCE_REQUIRED"
    elif not groups:
        disposition = "NO_EXTERNAL_SERVICE_ACTIONS"
    elif len(groups) == 1:
        disposition = "ONE_SEPARATE_SCOPE_USER_CHOICE"
    else:
        disposition = "MULTI_SCOPE_USER_CHOICES_SEPARATED"

    logical = {
        "schema": SCHEMA,
        "storage_plan_digest": storage["plan_digest"],
        "model_decision_digest": model["decision_digest"],
        "storage_status": storage["status"],
        "model_disposition": model["disposition"],
        "storage_primary_location": storage["primary_location"],
        "storage_secondary_location": storage["secondary_location"],
        "storage_cloud_selected": storage["cloud_selected"],
        "model_provider_refs": model["provider_refs"],
        "presentation_groups": groups,
        "blockers": tuple(blockers),
        "disposition": disposition,
        "scope_evidence_refs": tuple(sorted(
            (scope, ev.evidence_ref, ev.evidence_digest, ev.source_generation, ev.currentness_ref)
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
    logical["plan_digest"] = _digest("AURA_ADOPT_EXTERNAL_SERVICE_INTENT_PLAN_V1", logical)
    return logical
