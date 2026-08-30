"""AURA-ADOPT-001 ZF-05B/ZF-07C share-to-model escalation firewall.

Pure D0 integration membrane. The firewall consumes JSON-compatible projections
from the exact ZF-05A ShareLaunchPlanV1, ZF-03A ArenaRecipePlanV1, and ZF-07A
CapabilityEscalationDecisionV1 contracts. It recomputes owner-compatible
identities instead of trusting local status/currentness labels.

It never reads credentials, downloads a model, calls a provider, takes payment,
or grants network/effect/execution authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

SCHEMA = "ShareEscalationFirewallV1"
DECISION_SCHEMA = "ShareEscalationFirewallDecisionV1"

SHARE_PLAN_SCHEMA = "ShareLaunchPlanV1"
RECIPE_PLAN_SCHEMA = "ArenaRecipePlanV1"
ROUTER_SCHEMA = "CapabilityEscalationRouterV1"
ROUTER_DECISION_SCHEMA = "CapabilityEscalationDecisionV1"

ZF05A_OWNER_HEAD = "f5c3aeb362b978feb71927f43223e6f2501e5288"
ZF05A_OWNER_BLOB = "87a5bd403f1180c580a6352c36da9e326ce23711"
ZF03A_OWNER_HEAD = "458dc8c3974d5dc73956f133168bcc5e18f6aa87"
ZF03A_OWNER_BLOB = "8616bf91832696feeea599a255c3ad6ecdce9524"
ZF07A_OWNER_HEAD = "bf9de86246709003574143a847706a5c3cbc9afc"
ZF07A_OWNER_BLOB = "dcd9002af00455dafd0404f996c2b43e1a93771c"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,255}$")

SHARE_PLAN_FIELDS = frozenset({
    "schema", "capsule_digest", "capsule_id", "preferred_entry_surface",
    "next_surface", "creator_ref", "claimed_attribution_refs",
    "attribution_evidence_current", "attribution_identity_proven",
    "referral_depth", "required_user_actions", "blockers", "status",
    "network_fetch_authorized", "install_authorized", "execution_authorized",
    "execution_proven", "publication_authorized", "payment_authorized",
    "telemetry_authorized", "recipient_tracking_authorized",
    "provider_call_authorized", "adoption_success_proven", "plan_digest",
})
RECIPE_PLAN_FIELDS = frozenset({
    "schema", "recipe_digest", "recipe_id", "recipe_version", "purpose",
    "capability_refs", "asset_refs", "parameters", "constraints",
    "effect_ceiling", "rights", "blockers", "status",
    "authority_owner_resolved", "effect_authorized", "execution_proven",
    "publication_authorized", "payment_authorized", "marketplace_listed",
    "plan_digest",
})
RESIDUAL_FIELDS = frozenset({
    "residual_id", "recipe_plan_digest", "capability_ref", "residual_kind",
    "unresolved", "source_generation", "source_currentness_ref",
    "minimum_context_tokens",
})
CURRENTNESS_FIELDS = frozenset({
    "source_currentness_ref", "model_catalog_currentness_ref",
    "provider_catalog_currentness_ref", "rate_catalog_currentness_ref",
})
OPTION_FIELDS = frozenset({
    "route_id", "model_ref", "provider_ref", "execution_location", "cost_class",
    "required_actions", "zero_effect_ready", "download_bytes",
    "candidate_evidence_ref", "candidate_evidence_digest", "evidence_summary",
})
ROUTER_DECISION_FIELDS = frozenset({
    "schema", "router_schema", "residual_id", "capability_ref",
    "recipe_plan_digest", "residual_source_generation",
    "residual_source_currentness_ref", "router_currentness_digest",
    "disposition", "selected_route_id", "options", "blockers",
    "earned_action_classes", "decision_digest", "credential_prompt_performed",
    "credential_collected", "model_download_started", "provider_call_made",
    "payment_performed", "effect_authorized", "execution_proven",
    "catalog_evidence_authenticated",
})

SHARE_FIXED_ACTIONS = (
    "OPEN_ENTRY_SURFACE",
    "REVIEW_PROVENANCE_AND_ATTRIBUTION",
    "CONFIRM_REPRODUCTION_INTENT",
)
ROUTER_DISPOSITIONS = frozenset({
    "NO_ESCALATION_REQUIRED", "LOCAL_ROUTE_READY", "USER_CHOICE_REQUIRED",
    "EVIDENCE_REQUIRED", "UPSTREAM_BLOCKED",
})
COST_CLASSES = frozenset({"INCLUDED", "FREE_BOUNDED", "PAID", "UNKNOWN"})
EXECUTION_LOCATIONS = frozenset({"LOCAL", "REMOTE"})


class FirewallError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical_plain(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise FirewallError("NONCANONICAL_OWNER_PROJECTION") from exc


def _canonical_router(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise FirewallError("NONCANONICAL_ROUTER_PROJECTION") from exc


def _plain_digest(value: object) -> str:
    return hashlib.sha256(_canonical_plain(value)).hexdigest()


def _domain_digest(domain: str, value: object) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical_router(value)).hexdigest()


def _sha(value: object, code: str) -> str:
    if not isinstance(value, str):
        raise FirewallError(code)
    value = value.strip().lower()
    if not _SHA256.fullmatch(value):
        raise FirewallError(code)
    return value


def _token(value: object, code: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise FirewallError(code)
    value = value.strip()
    if not value and allow_empty:
        return ""
    if not value or not _TOKEN.fullmatch(value):
        raise FirewallError(code)
    return value


def _strict_fields(raw: Mapping[str, Any], allowed: frozenset[str], code: str) -> None:
    extra = sorted(set(raw) - allowed)
    missing = sorted(allowed - set(raw))
    if extra:
        raise FirewallError(code, "extra=" + ",".join(extra))
    if missing:
        raise FirewallError(code, "missing=" + ",".join(missing))


def _seq(value: object, code: str) -> list[Any]:
    if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)):
        raise FirewallError(code)
    return list(value)


def _false(raw: Mapping[str, Any], names: Sequence[str], code: str) -> None:
    for name in names:
        if raw.get(name) is not False:
            raise FirewallError(code, name)


def verify_share_launch_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(plan, Mapping):
        raise FirewallError("SHARE_PLAN_MAPPING_REQUIRED")
    raw = dict(plan)
    _strict_fields(raw, SHARE_PLAN_FIELDS, "SHARE_PLAN_FIELDS_MISMATCH")
    if raw["schema"] != SHARE_PLAN_SCHEMA:
        raise FirewallError("SHARE_PLAN_SCHEMA_MISMATCH")
    claimed = _sha(raw["plan_digest"], "SHARE_PLAN_DIGEST_INVALID")
    logical = dict(raw); del logical["plan_digest"]
    if _plain_digest(logical) != claimed:
        raise FirewallError("SHARE_PLAN_DIGEST_MISMATCH")
    _sha(raw["capsule_digest"], "SHARE_CAPSULE_DIGEST_INVALID")
    _token(raw["capsule_id"], "SHARE_CAPSULE_ID_INVALID")
    _token(raw["preferred_entry_surface"], "SHARE_ENTRY_SURFACE_INVALID")
    if raw["next_surface"] is not None:
        _token(raw["next_surface"], "SHARE_NEXT_SURFACE_INVALID")
    _token(raw["creator_ref"], "SHARE_CREATOR_REF_INVALID")
    refs = [_token(x, "SHARE_ATTRIBUTION_REF_INVALID") for x in _seq(raw["claimed_attribution_refs"], "SHARE_ATTRIBUTION_REFS_INVALID")]
    if len(refs) != len(set(refs)):
        raise FirewallError("SHARE_ATTRIBUTION_REF_DUPLICATE")
    if type(raw["attribution_evidence_current"]) is not bool:
        raise FirewallError("SHARE_ATTRIBUTION_CURRENT_BOOL_REQUIRED")
    if raw["attribution_identity_proven"] is not False:
        raise FirewallError("SHARE_ATTRIBUTION_IDENTITY_AUTHORITY_FORBIDDEN")
    if isinstance(raw["referral_depth"], bool) or not isinstance(raw["referral_depth"], int) or raw["referral_depth"] < 0:
        raise FirewallError("SHARE_REFERRAL_DEPTH_INVALID")
    if tuple(_seq(raw["required_user_actions"], "SHARE_REQUIRED_ACTIONS_INVALID")) != SHARE_FIXED_ACTIONS:
        raise FirewallError("SHARE_REQUIRED_ACTIONS_OWNER_MISMATCH")
    blockers = [str(x) for x in _seq(raw["blockers"], "SHARE_BLOCKERS_INVALID")]
    if raw["status"] not in {"READY_FOR_USER_ACTION", "EVIDENCE_REQUIRED", "ROUTE_OR_EVIDENCE_REQUIRED"}:
        raise FirewallError("SHARE_STATUS_INVALID")
    if raw["status"] == "READY_FOR_USER_ACTION" and blockers:
        raise FirewallError("READY_SHARE_CANNOT_HAVE_BLOCKERS")
    if raw["status"] == "READY_FOR_USER_ACTION" and not raw["attribution_evidence_current"]:
        raise FirewallError("READY_SHARE_ATTRIBUTION_EVIDENCE_NOT_CURRENT")
    _false(raw, ("network_fetch_authorized", "install_authorized", "execution_authorized", "execution_proven", "publication_authorized", "payment_authorized", "telemetry_authorized", "recipient_tracking_authorized", "provider_call_authorized", "adoption_success_proven"), "SHARE_AUTHORITY_WIDENING")
    return raw


def verify_recipe_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(plan, Mapping):
        raise FirewallError("RECIPE_PLAN_MAPPING_REQUIRED")
    raw = dict(plan)
    _strict_fields(raw, RECIPE_PLAN_FIELDS, "RECIPE_PLAN_FIELDS_MISMATCH")
    if raw["schema"] != RECIPE_PLAN_SCHEMA:
        raise FirewallError("RECIPE_PLAN_SCHEMA_MISMATCH")
    claimed = _sha(raw["plan_digest"], "RECIPE_PLAN_DIGEST_INVALID")
    logical = dict(raw); del logical["plan_digest"]
    if _plain_digest(logical) != claimed:
        raise FirewallError("RECIPE_PLAN_DIGEST_MISMATCH")
    _sha(raw["recipe_digest"], "RECIPE_DIGEST_INVALID")
    _token(raw["recipe_id"], "RECIPE_ID_INVALID")
    _token(raw["recipe_version"], "RECIPE_VERSION_INVALID")
    if not isinstance(raw["purpose"], str) or not raw["purpose"].strip():
        raise FirewallError("RECIPE_PURPOSE_REQUIRED")
    caps = [_token(x, "RECIPE_CAPABILITY_REF_INVALID") for x in _seq(raw["capability_refs"], "RECIPE_CAPABILITY_REFS_INVALID")]
    if not caps:
        raise FirewallError("RECIPE_CAPABILITY_REFS_REQUIRED")
    if len(caps) != len(set(caps)):
        raise FirewallError("RECIPE_CAPABILITY_REF_DUPLICATE")
    _seq(raw["asset_refs"], "RECIPE_ASSET_REFS_INVALID")
    if not isinstance(raw["parameters"], Mapping) or not isinstance(raw["constraints"], Mapping):
        raise FirewallError("RECIPE_PLAN_MAPPING_FIELD_INVALID")
    if not isinstance(raw["rights"], Mapping):
        raise FirewallError("RECIPE_RIGHTS_MAPPING_REQUIRED")
    _seq(raw["blockers"], "RECIPE_BLOCKERS_INVALID")
    if raw["status"] not in {"READY_FOR_ADMISSION", "BINDING_EVIDENCE_REQUIRED"}:
        raise FirewallError("RECIPE_PLAN_STATUS_INVALID")
    if raw["status"] == "READY_FOR_ADMISSION" and raw["blockers"]:
        raise FirewallError("READY_RECIPE_PLAN_CANNOT_HAVE_BLOCKERS")
    _false(raw, ("authority_owner_resolved", "effect_authorized", "execution_proven", "publication_authorized", "payment_authorized", "marketplace_listed"), "RECIPE_PLAN_AUTHORITY_WIDENING")
    return raw


def verify_router_currentness(currentness: Mapping[str, Any]) -> tuple[dict[str, str], str]:
    if not isinstance(currentness, Mapping):
        raise FirewallError("ROUTER_CURRENTNESS_MAPPING_REQUIRED")
    raw = dict(currentness)
    _strict_fields(raw, CURRENTNESS_FIELDS, "ROUTER_CURRENTNESS_FIELDS_MISMATCH")
    for key in CURRENTNESS_FIELDS:
        raw[key] = _token(raw[key], f"{key.upper()}_INVALID")
    return raw, _domain_digest("AURA_ADOPT_ROUTER_CURRENTNESS_V1", raw)


def verify_capability_residual(residual: Mapping[str, Any], *, recipe_plan: Mapping[str, Any], currentness: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(residual, Mapping):
        raise FirewallError("CAPABILITY_RESIDUAL_MAPPING_REQUIRED")
    raw = dict(residual)
    _strict_fields(raw, RESIDUAL_FIELDS, "CAPABILITY_RESIDUAL_FIELDS_MISMATCH")
    raw["residual_id"] = _token(raw["residual_id"], "RESIDUAL_ID_INVALID")
    raw["recipe_plan_digest"] = _sha(raw["recipe_plan_digest"], "RESIDUAL_RECIPE_PLAN_DIGEST_INVALID")
    raw["capability_ref"] = _token(raw["capability_ref"], "RESIDUAL_CAPABILITY_REF_INVALID")
    if raw["residual_kind"] not in {"MODEL_INFERENCE_REQUIRED", "NON_MODEL_RESIDUAL"}:
        raise FirewallError("RESIDUAL_KIND_INVALID")
    if type(raw["unresolved"]) is not bool:
        raise FirewallError("RESIDUAL_UNRESOLVED_BOOL_REQUIRED")
    raw["source_generation"] = _token(raw["source_generation"], "RESIDUAL_SOURCE_GENERATION_INVALID")
    raw["source_currentness_ref"] = _token(raw["source_currentness_ref"], "RESIDUAL_SOURCE_CURRENTNESS_REF_INVALID")
    if isinstance(raw["minimum_context_tokens"], bool) or not isinstance(raw["minimum_context_tokens"], int) or raw["minimum_context_tokens"] < 0:
        raise FirewallError("RESIDUAL_MINIMUM_CONTEXT_INVALID")
    if raw["recipe_plan_digest"] != recipe_plan["plan_digest"]:
        raise FirewallError("RESIDUAL_RECIPE_PLAN_MISMATCH")
    if raw["capability_ref"] not in recipe_plan["capability_refs"]:
        raise FirewallError("RESIDUAL_CAPABILITY_NOT_IN_RECIPE_PLAN")
    if raw["source_currentness_ref"] != currentness["source_currentness_ref"]:
        raise FirewallError("RESIDUAL_SOURCE_CURRENTNESS_STALE")
    return raw


def _verify_option(raw_option: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw_option, Mapping):
        raise FirewallError("ROUTER_OPTION_MAPPING_REQUIRED")
    raw = dict(raw_option)
    _strict_fields(raw, OPTION_FIELDS, "ROUTER_OPTION_FIELDS_MISMATCH")
    raw["route_id"] = _token(raw["route_id"], "OPTION_ROUTE_ID_INVALID")
    raw["model_ref"] = _token(raw["model_ref"], "OPTION_MODEL_REF_INVALID")
    raw["provider_ref"] = _token(raw["provider_ref"], "OPTION_PROVIDER_REF_INVALID", allow_empty=True)
    if raw["execution_location"] not in EXECUTION_LOCATIONS:
        raise FirewallError("OPTION_EXECUTION_LOCATION_INVALID")
    if raw["cost_class"] not in COST_CLASSES:
        raise FirewallError("OPTION_COST_CLASS_INVALID")
    actions = tuple(_token(x, "OPTION_ACTION_INVALID") for x in _seq(raw["required_actions"], "OPTION_ACTIONS_INVALID"))
    if len(actions) != len(set(actions)):
        raise FirewallError("OPTION_ACTION_DUPLICATE")
    raw["required_actions"] = actions
    if type(raw["zero_effect_ready"]) is not bool:
        raise FirewallError("OPTION_ZERO_EFFECT_READY_BOOL_REQUIRED")
    if raw["zero_effect_ready"] != (len(actions) == 0):
        raise FirewallError("OPTION_ZERO_EFFECT_READY_MISMATCH")
    if raw["download_bytes"] is not None and (isinstance(raw["download_bytes"], bool) or not isinstance(raw["download_bytes"], int) or raw["download_bytes"] < 0):
        raise FirewallError("OPTION_DOWNLOAD_BYTES_INVALID")
    raw["candidate_evidence_ref"] = _token(raw["candidate_evidence_ref"], "OPTION_CANDIDATE_EVIDENCE_REF_INVALID")
    raw["candidate_evidence_digest"] = _sha(raw["candidate_evidence_digest"], "OPTION_CANDIDATE_EVIDENCE_DIGEST_INVALID")
    raw["evidence_summary"] = tuple(str(x) for x in _seq(raw["evidence_summary"], "OPTION_EVIDENCE_SUMMARY_INVALID"))
    if raw["execution_location"] == "REMOTE" and not raw["provider_ref"]:
        raise FirewallError("REMOTE_OPTION_PROVIDER_REQUIRED")
    if raw["execution_location"] == "LOCAL" and raw["provider_ref"]:
        raise FirewallError("LOCAL_OPTION_PROVIDER_FORBIDDEN")
    return raw


def _router_option_logical(option: Mapping[str, Any]) -> dict[str, Any]:
    return {"route_id": option["route_id"], "model_ref": option["model_ref"], "provider_ref": option["provider_ref"], "execution_location": option["execution_location"], "cost_class": option["cost_class"], "required_actions": tuple(option["required_actions"]), "zero_effect_ready": option["zero_effect_ready"], "download_bytes": option["download_bytes"], "candidate_evidence_ref": option["candidate_evidence_ref"], "candidate_evidence_digest": option["candidate_evidence_digest"], "evidence_summary": tuple(option["evidence_summary"])}


def verify_router_decision(decision: Mapping[str, Any], *, residual: Mapping[str, Any], router_currentness_digest: str) -> dict[str, Any]:
    if not isinstance(decision, Mapping):
        raise FirewallError("ROUTER_DECISION_MAPPING_REQUIRED")
    raw = dict(decision)
    _strict_fields(raw, ROUTER_DECISION_FIELDS, "ROUTER_DECISION_FIELDS_MISMATCH")
    if raw["schema"] != ROUTER_DECISION_SCHEMA or raw["router_schema"] != ROUTER_SCHEMA:
        raise FirewallError("ROUTER_DECISION_SCHEMA_MISMATCH")
    raw["residual_id"] = _token(raw["residual_id"], "DECISION_RESIDUAL_ID_INVALID")
    raw["capability_ref"] = _token(raw["capability_ref"], "DECISION_CAPABILITY_REF_INVALID")
    raw["recipe_plan_digest"] = _sha(raw["recipe_plan_digest"], "DECISION_RECIPE_PLAN_DIGEST_INVALID")
    raw["residual_source_generation"] = _token(raw["residual_source_generation"], "DECISION_RESIDUAL_SOURCE_GENERATION_INVALID")
    raw["residual_source_currentness_ref"] = _token(raw["residual_source_currentness_ref"], "DECISION_RESIDUAL_CURRENTNESS_REF_INVALID")
    raw["router_currentness_digest"] = _sha(raw["router_currentness_digest"], "DECISION_ROUTER_CURRENTNESS_DIGEST_INVALID")
    if raw["disposition"] not in ROUTER_DISPOSITIONS:
        raise FirewallError("ROUTER_DISPOSITION_INVALID")
    if raw["selected_route_id"] is not None:
        raw["selected_route_id"] = _token(raw["selected_route_id"], "DECISION_SELECTED_ROUTE_INVALID")
    options = tuple(_verify_option(x) for x in _seq(raw["options"], "ROUTER_OPTIONS_INVALID"))
    blockers = tuple(sorted(set(str(x) for x in _seq(raw["blockers"], "ROUTER_BLOCKERS_INVALID"))))
    earned = tuple(sorted(set(_token(x, "DECISION_EARNED_ACTION_INVALID") for x in _seq(raw["earned_action_classes"], "DECISION_EARNED_ACTIONS_INVALID"))))
    recomputed_earned = tuple(sorted({action for option in options for action in option["required_actions"]}))
    if earned != recomputed_earned:
        raise FirewallError("DECISION_EARNED_ACTIONS_MISMATCH")
    if raw["selected_route_id"] is not None and raw["selected_route_id"] not in {o["route_id"] for o in options}:
        raise FirewallError("DECISION_SELECTED_ROUTE_NOT_IN_OPTIONS")
    if raw["disposition"] == "LOCAL_ROUTE_READY":
        selected = [o for o in options if o["route_id"] == raw["selected_route_id"]]
        if len(selected) != 1 or not selected[0]["zero_effect_ready"]:
            raise FirewallError("LOCAL_ROUTE_READY_OWNER_INCONSISTENT")
    if raw["disposition"] == "NO_ESCALATION_REQUIRED" and (options or earned):
        raise FirewallError("NO_ESCALATION_DECISION_HAS_OPTIONS")
    _false(raw, ("credential_prompt_performed", "credential_collected", "model_download_started", "provider_call_made", "payment_performed", "effect_authorized", "execution_proven", "catalog_evidence_authenticated"), "ROUTER_DECISION_AUTHORITY_WIDENING")
    if raw["residual_id"] != residual["residual_id"]:
        raise FirewallError("DECISION_RESIDUAL_MISMATCH")
    if raw["capability_ref"] != residual["capability_ref"]:
        raise FirewallError("DECISION_CAPABILITY_MISMATCH")
    if raw["recipe_plan_digest"] != residual["recipe_plan_digest"]:
        raise FirewallError("DECISION_RECIPE_PLAN_MISMATCH")
    if raw["residual_source_generation"] != residual["source_generation"]:
        raise FirewallError("DECISION_RESIDUAL_SOURCE_GENERATION_MISMATCH")
    if raw["residual_source_currentness_ref"] != residual["source_currentness_ref"]:
        raise FirewallError("DECISION_RESIDUAL_CURRENTNESS_MISMATCH")
    if raw["router_currentness_digest"] != router_currentness_digest:
        raise FirewallError("DECISION_ROUTER_CURRENTNESS_MISMATCH")
    logical = {"schema": ROUTER_DECISION_SCHEMA, "router_schema": ROUTER_SCHEMA, "residual_id": raw["residual_id"], "capability_ref": raw["capability_ref"], "recipe_plan_digest": raw["recipe_plan_digest"], "residual_source_generation": raw["residual_source_generation"], "residual_source_currentness_ref": raw["residual_source_currentness_ref"], "router_currentness_digest": raw["router_currentness_digest"], "disposition": raw["disposition"], "selected_route_id": raw["selected_route_id"], "options": [_router_option_logical(o) for o in options], "blockers": blockers, "earned_action_classes": earned, "credential_prompt_performed": False, "credential_collected": False, "model_download_started": False, "provider_call_made": False, "payment_performed": False, "effect_authorized": False, "execution_proven": False, "catalog_evidence_authenticated": False}
    expected = _domain_digest("AURA_ADOPT_CAPABILITY_ESCALATION_DECISION_V1", logical)
    claimed = _sha(raw["decision_digest"], "ROUTER_DECISION_DIGEST_INVALID")
    if claimed != expected:
        raise FirewallError("ROUTER_DECISION_DIGEST_MISMATCH")
    raw["options"] = options; raw["blockers"] = blockers; raw["earned_action_classes"] = earned
    return raw


@dataclass(frozen=True)
class ProviderTargetEvidenceV1:
    evidence_ref: str
    evidence_digest: str
    currentness_ref: str
    currentness_state: str
    principal_ref: str
    route_id: str
    model_ref: str
    provider_ref: str
    candidate_evidence_ref: str
    candidate_evidence_digest: str
    cost_class: str
    provider_currentness_ref: str
    rate_currentness_ref: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_ref", _token(self.evidence_ref, "TARGET_EVIDENCE_REF_INVALID"))
        object.__setattr__(self, "evidence_digest", _sha(self.evidence_digest, "TARGET_EVIDENCE_DIGEST_INVALID"))
        object.__setattr__(self, "currentness_ref", _token(self.currentness_ref, "TARGET_CURRENTNESS_REF_INVALID"))
        if self.currentness_state != "CURRENT":
            raise FirewallError("TARGET_EVIDENCE_NOT_CURRENT")
        object.__setattr__(self, "principal_ref", _token(self.principal_ref, "TARGET_PRINCIPAL_REF_INVALID"))
        object.__setattr__(self, "route_id", _token(self.route_id, "TARGET_ROUTE_ID_INVALID"))
        object.__setattr__(self, "model_ref", _token(self.model_ref, "TARGET_MODEL_REF_INVALID"))
        object.__setattr__(self, "provider_ref", _token(self.provider_ref, "TARGET_PROVIDER_REF_INVALID"))
        object.__setattr__(self, "candidate_evidence_ref", _token(self.candidate_evidence_ref, "TARGET_CANDIDATE_EVIDENCE_REF_INVALID"))
        object.__setattr__(self, "candidate_evidence_digest", _sha(self.candidate_evidence_digest, "TARGET_CANDIDATE_EVIDENCE_DIGEST_INVALID"))
        if self.cost_class not in COST_CLASSES:
            raise FirewallError("TARGET_COST_CLASS_INVALID")
        object.__setattr__(self, "provider_currentness_ref", _token(self.provider_currentness_ref, "TARGET_PROVIDER_CURRENTNESS_REF_INVALID"))
        object.__setattr__(self, "rate_currentness_ref", _token(self.rate_currentness_ref, "TARGET_RATE_CURRENTNESS_REF_INVALID"))


def _verify_provider_target(option: Mapping[str, Any], evidence: ProviderTargetEvidenceV1, *, principal_ref: str, currentness: Mapping[str, Any]) -> None:
    pairs = (("principal_ref", evidence.principal_ref, principal_ref), ("route_id", evidence.route_id, option["route_id"]), ("model_ref", evidence.model_ref, option["model_ref"]), ("provider_ref", evidence.provider_ref, option["provider_ref"]), ("candidate_evidence_ref", evidence.candidate_evidence_ref, option["candidate_evidence_ref"]), ("candidate_evidence_digest", evidence.candidate_evidence_digest, option["candidate_evidence_digest"]), ("cost_class", evidence.cost_class, option["cost_class"]), ("provider_currentness_ref", evidence.provider_currentness_ref, currentness["provider_catalog_currentness_ref"]), ("rate_currentness_ref", evidence.rate_currentness_ref, currentness["rate_catalog_currentness_ref"]))
    mismatches = [name for name, actual, expected in pairs if actual != expected]
    if mismatches:
        raise FirewallError("PROVIDER_TARGET_EVIDENCE_MISMATCH", ",".join(mismatches))


def compile_share_escalation_firewall(share_plan: Mapping[str, Any], recipe_plan: Mapping[str, Any], residual: Mapping[str, Any], router_decision: Mapping[str, Any], *, router_currentness: Mapping[str, Any], principal_ref: str, provider_targets: Sequence[ProviderTargetEvidenceV1] = ()) -> dict[str, Any]:
    share = verify_share_launch_plan(share_plan)
    recipe = verify_recipe_plan(recipe_plan)
    currentness, currentness_digest = verify_router_currentness(router_currentness)
    residual_v = verify_capability_residual(residual, recipe_plan=recipe, currentness=currentness)
    decision = verify_router_decision(router_decision, residual=residual_v, router_currentness_digest=currentness_digest)
    principal = _token(principal_ref, "RECIPIENT_PRINCIPAL_REF_INVALID")
    if not isinstance(provider_targets, Sequence) or isinstance(provider_targets, (str, bytes)):
        raise FirewallError("PROVIDER_TARGET_SEQUENCE_REQUIRED")
    if any(not isinstance(x, ProviderTargetEvidenceV1) for x in provider_targets):
        raise FirewallError("PROVIDER_TARGET_EVIDENCE_INVALID")
    target_by_route: dict[str, ProviderTargetEvidenceV1] = {}
    for target in provider_targets:
        if target.route_id in target_by_route:
            raise FirewallError("PROVIDER_TARGET_ROUTE_DUPLICATE", target.route_id)
        target_by_route[target.route_id] = target
    decision_routes = {option["route_id"] for option in decision["options"]}
    unknown_target_routes = sorted(set(target_by_route) - decision_routes)
    if unknown_target_routes:
        raise FirewallError("PROVIDER_TARGET_ROUTE_NOT_IN_DECISION", ",".join(unknown_target_routes))
    blockers: list[str] = []
    presentable: list[dict[str, Any]] = []
    if share["status"] != "READY_FOR_USER_ACTION":
        disposition = "SHARE_EVIDENCE_REQUIRED"; blockers.append(f"SHARE_NOT_READY:{share['status']}")
    elif recipe["status"] != "READY_FOR_ADMISSION":
        disposition = "EVIDENCE_REQUIRED"; blockers.append(f"RECIPE_PLAN_NOT_READY:{recipe['status']}")
    elif not residual_v["unresolved"] or residual_v["residual_kind"] != "MODEL_INFERENCE_REQUIRED":
        if decision["disposition"] not in {"NO_ESCALATION_REQUIRED", "UPSTREAM_BLOCKED", "EVIDENCE_REQUIRED"}:
            raise FirewallError("MODEL_ESCALATION_WITHOUT_MODEL_RESIDUAL")
        disposition = "NO_MODEL_ESCALATION"
    elif decision["disposition"] in {"EVIDENCE_REQUIRED", "UPSTREAM_BLOCKED"}:
        disposition = "EVIDENCE_REQUIRED"; blockers.append(f"ROUTER_NOT_READY:{decision['disposition']}")
    else:
        for option in decision["options"]:
            if option["execution_location"] == "REMOTE":
                target = target_by_route.get(option["route_id"])
                if target is None:
                    blockers.append(f"PROVIDER_TARGET_EVIDENCE_REQUIRED:{option['route_id']}"); continue
                _verify_provider_target(option, target, principal_ref=principal, currentness=currentness)
            presentable.append({"route_id": option["route_id"], "model_ref": option["model_ref"], "provider_ref": option["provider_ref"], "execution_location": option["execution_location"], "cost_class": option["cost_class"], "required_actions": tuple(option["required_actions"]), "candidate_evidence_ref": option["candidate_evidence_ref"], "candidate_evidence_digest": option["candidate_evidence_digest"]})
        disposition = "EVIDENCE_REQUIRED" if blockers else "RECIPIENT_ESCALATION_READY"
    logical = {"schema": DECISION_SCHEMA, "firewall_schema": SCHEMA, "share_plan_digest": share["plan_digest"], "recipe_plan_digest": recipe["plan_digest"], "residual_id": residual_v["residual_id"], "capability_ref": residual_v["capability_ref"], "router_currentness_digest": currentness_digest, "router_decision_digest": decision["decision_digest"], "principal_ref": principal, "disposition": disposition, "presentable_options": presentable, "blockers": tuple(sorted(blockers)), "owner_projection_identity_recomputed": True, "provider_targets_verified": bool(presentable) and all(o["execution_location"] != "REMOTE" or o["route_id"] in target_by_route for o in decision["options"]), "credential_authorized": False, "model_download_authorized": False, "provider_call_authorized": False, "payment_authorized": False, "network_authorized": False, "effect_authorized": False, "execution_proven": False, "owner_contract_refs": {"zf05a": {"head": ZF05A_OWNER_HEAD, "blob": ZF05A_OWNER_BLOB}, "zf03a": {"head": ZF03A_OWNER_HEAD, "blob": ZF03A_OWNER_BLOB}, "zf07a": {"head": ZF07A_OWNER_HEAD, "blob": ZF07A_OWNER_BLOB}}}
    logical["firewall_digest"] = _domain_digest("AURA_ADOPT_SHARE_ESCALATION_FIREWALL_V1", logical)
    return logical
