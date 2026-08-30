"""AURA-ADOPT-001 ZF-05B/ZF-07C share-to-model escalation firewall.

D0 integration verifier. Caller-supplied projections can establish structural
compatibility only. Escalation readiness additionally requires a non-serialized
resolver capability to attest exact owner/currentness/revocation and, for remote
routes, the exact recipient/route/provider/model/rate target.

This module never reads credentials, downloads a model, calls a provider, takes
payment, or grants network/effect/execution authority.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping, Protocol, Sequence

SCHEMA = "ShareEscalationFirewallV1"
DECISION_SCHEMA = "ShareEscalationFirewallDecisionV1"
SHARE_PLAN_SCHEMA = "ShareLaunchPlanV1"
RECIPE_PLAN_SCHEMA = "ArenaRecipePlanV1"
ROUTER_SCHEMA = "CapabilityEscalationRouterV1"
ROUTER_DECISION_SCHEMA = "CapabilityEscalationDecisionV1"

ZF05A_OWNER_REF = "aura-adopt://zf05a/share-capsule-owner"
ZF05A_OWNER_HEAD = "f5c3aeb362b978feb71927f43223e6f2501e5288"
ZF05A_OWNER_BLOB = "87a5bd403f1180c580a6352c36da9e326ce23711"
ZF03A_OWNER_REF = "aura-adopt://zf03a/arena-recipe-owner"
ZF03A_OWNER_HEAD = "458dc8c3974d5dc73956f133168bcc5e18f6aa87"
ZF03A_OWNER_BLOB = "8616bf91832696feeea599a255c3ad6ecdce9524"
ZF07A_OWNER_REF = "aura-adopt://zf07a/capability-escalation-owner"
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
    "OPEN_ENTRY_SURFACE", "REVIEW_PROVENANCE_AND_ATTRIBUTION",
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
        self.code, self.detail = code, detail


def _canonical_plain(value: object) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    except (TypeError, ValueError) as exc:
        raise FirewallError("NONCANONICAL_OWNER_PROJECTION") from exc


def _canonical_router(value: object) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
    except (TypeError, ValueError) as exc:
        raise FirewallError("NONCANONICAL_ROUTER_PROJECTION") from exc


def _plain_digest(value: object) -> str:
    return hashlib.sha256(_canonical_plain(value)).hexdigest()


def _domain_digest(domain: str, value: object) -> str:
    return hashlib.sha256(domain.encode() + b"\0" + _canonical_router(value)).hexdigest()


def _sha(value: object, code: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value.strip().lower()):
        raise FirewallError(code)
    return value.strip().lower()


def _token(value: object, code: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise FirewallError(code)
    value = value.strip()
    if not value and allow_empty:
        return ""
    if not value or not _TOKEN.fullmatch(value):
        raise FirewallError(code)
    return value


def _seq(value: object, code: str) -> list[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise FirewallError(code)
    return list(value)


def _strict_fields(raw: Mapping[str, Any], allowed: frozenset[str], code: str) -> None:
    extra, missing = sorted(set(raw) - allowed), sorted(allowed - set(raw))
    if extra or missing:
        raise FirewallError(code, f"extra={','.join(extra)};missing={','.join(missing)}")


def _hard_false(raw: Mapping[str, Any], fields: Sequence[str], code: str) -> None:
    for field in fields:
        if raw.get(field) is not False:
            raise FirewallError(code, field)


def verify_share_launch_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(plan, Mapping):
        raise FirewallError("SHARE_PLAN_MAPPING_REQUIRED")
    raw = dict(plan); _strict_fields(raw, SHARE_PLAN_FIELDS, "SHARE_PLAN_FIELDS_MISMATCH")
    if raw["schema"] != SHARE_PLAN_SCHEMA:
        raise FirewallError("SHARE_PLAN_SCHEMA_MISMATCH")
    claimed = _sha(raw["plan_digest"], "SHARE_PLAN_DIGEST_INVALID")
    logical = dict(raw); logical.pop("plan_digest")
    if _plain_digest(logical) != claimed:
        raise FirewallError("SHARE_PLAN_DIGEST_MISMATCH")
    _sha(raw["capsule_digest"], "SHARE_CAPSULE_DIGEST_INVALID")
    for key in ("capsule_id", "preferred_entry_surface", "creator_ref"):
        _token(raw[key], f"SHARE_{key.upper()}_INVALID")
    if raw["next_surface"] is not None:
        _token(raw["next_surface"], "SHARE_NEXT_SURFACE_INVALID")
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
    blockers = _seq(raw["blockers"], "SHARE_BLOCKERS_INVALID")
    if raw["status"] not in {"READY_FOR_USER_ACTION", "EVIDENCE_REQUIRED", "ROUTE_OR_EVIDENCE_REQUIRED"}:
        raise FirewallError("SHARE_STATUS_INVALID")
    if raw["status"] == "READY_FOR_USER_ACTION" and (blockers or not raw["attribution_evidence_current"]):
        raise FirewallError("READY_SHARE_EVIDENCE_INCONSISTENT")
    _hard_false(raw, ("network_fetch_authorized", "install_authorized", "execution_authorized", "execution_proven", "publication_authorized", "payment_authorized", "telemetry_authorized", "recipient_tracking_authorized", "provider_call_authorized", "adoption_success_proven"), "SHARE_AUTHORITY_WIDENING")
    return raw


def verify_recipe_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(plan, Mapping):
        raise FirewallError("RECIPE_PLAN_MAPPING_REQUIRED")
    raw = dict(plan); _strict_fields(raw, RECIPE_PLAN_FIELDS, "RECIPE_PLAN_FIELDS_MISMATCH")
    if raw["schema"] != RECIPE_PLAN_SCHEMA:
        raise FirewallError("RECIPE_PLAN_SCHEMA_MISMATCH")
    claimed = _sha(raw["plan_digest"], "RECIPE_PLAN_DIGEST_INVALID")
    logical = dict(raw); logical.pop("plan_digest")
    if _plain_digest(logical) != claimed:
        raise FirewallError("RECIPE_PLAN_DIGEST_MISMATCH")
    _sha(raw["recipe_digest"], "RECIPE_DIGEST_INVALID")
    for key in ("recipe_id", "recipe_version"):
        _token(raw[key], f"{key.upper()}_INVALID")
    if not isinstance(raw["purpose"], str) or not raw["purpose"].strip():
        raise FirewallError("RECIPE_PURPOSE_REQUIRED")
    caps = [_token(x, "RECIPE_CAPABILITY_REF_INVALID") for x in _seq(raw["capability_refs"], "RECIPE_CAPABILITY_REFS_INVALID")]
    if not caps or len(caps) != len(set(caps)):
        raise FirewallError("RECIPE_CAPABILITY_REFS_INVALID")
    _seq(raw["asset_refs"], "RECIPE_ASSET_REFS_INVALID")
    if not isinstance(raw["parameters"], Mapping) or not isinstance(raw["constraints"], Mapping) or not isinstance(raw["rights"], Mapping):
        raise FirewallError("RECIPE_MAPPING_FIELD_INVALID")
    blockers = _seq(raw["blockers"], "RECIPE_BLOCKERS_INVALID")
    if raw["status"] not in {"READY_FOR_ADMISSION", "BINDING_EVIDENCE_REQUIRED"}:
        raise FirewallError("RECIPE_PLAN_STATUS_INVALID")
    if raw["status"] == "READY_FOR_ADMISSION" and blockers:
        raise FirewallError("READY_RECIPE_PLAN_CANNOT_HAVE_BLOCKERS")
    _hard_false(raw, ("authority_owner_resolved", "effect_authorized", "execution_proven", "publication_authorized", "payment_authorized", "marketplace_listed"), "RECIPE_PLAN_AUTHORITY_WIDENING")
    return raw


def verify_router_currentness(currentness: Mapping[str, Any]) -> tuple[dict[str, str], str]:
    if not isinstance(currentness, Mapping):
        raise FirewallError("ROUTER_CURRENTNESS_MAPPING_REQUIRED")
    raw = dict(currentness); _strict_fields(raw, CURRENTNESS_FIELDS, "ROUTER_CURRENTNESS_FIELDS_MISMATCH")
    for key in CURRENTNESS_FIELDS:
        raw[key] = _token(raw[key], f"{key.upper()}_INVALID")
    return raw, _domain_digest("AURA_ADOPT_ROUTER_CURRENTNESS_V1", raw)


def verify_capability_residual(residual: Mapping[str, Any], *, recipe_plan: Mapping[str, Any], currentness: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(residual, Mapping):
        raise FirewallError("CAPABILITY_RESIDUAL_MAPPING_REQUIRED")
    raw = dict(residual); _strict_fields(raw, RESIDUAL_FIELDS, "CAPABILITY_RESIDUAL_FIELDS_MISMATCH")
    for key in ("residual_id", "capability_ref", "source_generation", "source_currentness_ref"):
        raw[key] = _token(raw[key], f"RESIDUAL_{key.upper()}_INVALID")
    raw["recipe_plan_digest"] = _sha(raw["recipe_plan_digest"], "RESIDUAL_RECIPE_PLAN_DIGEST_INVALID")
    if raw["residual_kind"] not in {"MODEL_INFERENCE_REQUIRED", "NON_MODEL_RESIDUAL"} or type(raw["unresolved"]) is not bool:
        raise FirewallError("RESIDUAL_STATE_INVALID")
    if isinstance(raw["minimum_context_tokens"], bool) or not isinstance(raw["minimum_context_tokens"], int) or raw["minimum_context_tokens"] < 0:
        raise FirewallError("RESIDUAL_MINIMUM_CONTEXT_INVALID")
    if raw["recipe_plan_digest"] != recipe_plan["plan_digest"] or raw["capability_ref"] not in recipe_plan["capability_refs"]:
        raise FirewallError("RESIDUAL_RECIPE_BINDING_MISMATCH")
    if raw["source_currentness_ref"] != currentness["source_currentness_ref"]:
        raise FirewallError("RESIDUAL_SOURCE_CURRENTNESS_STALE")
    return raw


def _verify_option(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise FirewallError("ROUTER_OPTION_MAPPING_REQUIRED")
    raw = dict(value); _strict_fields(raw, OPTION_FIELDS, "ROUTER_OPTION_FIELDS_MISMATCH")
    for key in ("route_id", "model_ref", "candidate_evidence_ref"):
        raw[key] = _token(raw[key], f"OPTION_{key.upper()}_INVALID")
    raw["provider_ref"] = _token(raw["provider_ref"], "OPTION_PROVIDER_REF_INVALID", allow_empty=True)
    raw["candidate_evidence_digest"] = _sha(raw["candidate_evidence_digest"], "OPTION_CANDIDATE_EVIDENCE_DIGEST_INVALID")
    if raw["execution_location"] not in EXECUTION_LOCATIONS or raw["cost_class"] not in COST_CLASSES:
        raise FirewallError("OPTION_CLASS_INVALID")
    actions = tuple(_token(x, "OPTION_ACTION_INVALID") for x in _seq(raw["required_actions"], "OPTION_ACTIONS_INVALID"))
    if len(actions) != len(set(actions)) or type(raw["zero_effect_ready"]) is not bool or raw["zero_effect_ready"] != (not actions):
        raise FirewallError("OPTION_ACTION_STATE_INVALID")
    raw["required_actions"] = actions
    if raw["download_bytes"] is not None and (isinstance(raw["download_bytes"], bool) or not isinstance(raw["download_bytes"], int) or raw["download_bytes"] < 0):
        raise FirewallError("OPTION_DOWNLOAD_BYTES_INVALID")
    raw["evidence_summary"] = tuple(str(x) for x in _seq(raw["evidence_summary"], "OPTION_EVIDENCE_SUMMARY_INVALID"))
    if (raw["execution_location"] == "REMOTE") != bool(raw["provider_ref"]):
        raise FirewallError("OPTION_PROVIDER_LOCATION_MISMATCH")
    return raw


def _option_logical(o: Mapping[str, Any]) -> dict[str, Any]:
    return {k: (tuple(o[k]) if k in {"required_actions", "evidence_summary"} else o[k]) for k in OPTION_FIELDS}


def verify_router_decision(decision: Mapping[str, Any], *, residual: Mapping[str, Any], router_currentness_digest: str) -> dict[str, Any]:
    if not isinstance(decision, Mapping):
        raise FirewallError("ROUTER_DECISION_MAPPING_REQUIRED")
    raw = dict(decision); _strict_fields(raw, ROUTER_DECISION_FIELDS, "ROUTER_DECISION_FIELDS_MISMATCH")
    if raw["schema"] != ROUTER_DECISION_SCHEMA or raw["router_schema"] != ROUTER_SCHEMA or raw["disposition"] not in ROUTER_DISPOSITIONS:
        raise FirewallError("ROUTER_DECISION_SCHEMA_OR_DISPOSITION_INVALID")
    for key in ("residual_id", "capability_ref", "residual_source_generation", "residual_source_currentness_ref"):
        raw[key] = _token(raw[key], f"DECISION_{key.upper()}_INVALID")
    raw["recipe_plan_digest"] = _sha(raw["recipe_plan_digest"], "DECISION_RECIPE_PLAN_DIGEST_INVALID")
    raw["router_currentness_digest"] = _sha(raw["router_currentness_digest"], "DECISION_ROUTER_CURRENTNESS_DIGEST_INVALID")
    if raw["selected_route_id"] is not None:
        raw["selected_route_id"] = _token(raw["selected_route_id"], "DECISION_SELECTED_ROUTE_INVALID")
    options = tuple(_verify_option(x) for x in _seq(raw["options"], "ROUTER_OPTIONS_INVALID"))
    blockers = tuple(sorted(set(str(x) for x in _seq(raw["blockers"], "ROUTER_BLOCKERS_INVALID"))))
    earned = tuple(sorted(set(_token(x, "DECISION_EARNED_ACTION_INVALID") for x in _seq(raw["earned_action_classes"], "DECISION_EARNED_ACTIONS_INVALID"))))
    if earned != tuple(sorted({a for o in options for a in o["required_actions"]})):
        raise FirewallError("DECISION_EARNED_ACTIONS_MISMATCH")
    if raw["selected_route_id"] is not None and raw["selected_route_id"] not in {o["route_id"] for o in options}:
        raise FirewallError("DECISION_SELECTED_ROUTE_NOT_IN_OPTIONS")
    _hard_false(raw, ("credential_prompt_performed", "credential_collected", "model_download_started", "provider_call_made", "payment_performed", "effect_authorized", "execution_proven", "catalog_evidence_authenticated"), "ROUTER_DECISION_AUTHORITY_WIDENING")
    for left, right, code in (
        (raw["residual_id"], residual["residual_id"], "DECISION_RESIDUAL_MISMATCH"),
        (raw["capability_ref"], residual["capability_ref"], "DECISION_CAPABILITY_MISMATCH"),
        (raw["recipe_plan_digest"], residual["recipe_plan_digest"], "DECISION_RECIPE_PLAN_MISMATCH"),
        (raw["residual_source_generation"], residual["source_generation"], "DECISION_RESIDUAL_SOURCE_GENERATION_MISMATCH"),
        (raw["residual_source_currentness_ref"], residual["source_currentness_ref"], "DECISION_RESIDUAL_CURRENTNESS_MISMATCH"),
        (raw["router_currentness_digest"], router_currentness_digest, "DECISION_ROUTER_CURRENTNESS_MISMATCH"),
    ):
        if left != right: raise FirewallError(code)
    logical = {"schema": ROUTER_DECISION_SCHEMA, "router_schema": ROUTER_SCHEMA, "residual_id": raw["residual_id"], "capability_ref": raw["capability_ref"], "recipe_plan_digest": raw["recipe_plan_digest"], "residual_source_generation": raw["residual_source_generation"], "residual_source_currentness_ref": raw["residual_source_currentness_ref"], "router_currentness_digest": raw["router_currentness_digest"], "disposition": raw["disposition"], "selected_route_id": raw["selected_route_id"], "options": [_option_logical(o) for o in options], "blockers": blockers, "earned_action_classes": earned, "credential_prompt_performed": False, "credential_collected": False, "model_download_started": False, "provider_call_made": False, "payment_performed": False, "effect_authorized": False, "execution_proven": False, "catalog_evidence_authenticated": False}
    if _sha(raw["decision_digest"], "ROUTER_DECISION_DIGEST_INVALID") != _domain_digest("AURA_ADOPT_CAPABILITY_ESCALATION_DECISION_V1", logical):
        raise FirewallError("ROUTER_DECISION_DIGEST_MISMATCH")
    raw["options"], raw["blockers"], raw["earned_action_classes"] = options, blockers, earned
    return raw


@dataclass(frozen=True)
class OwnerProjectionQueryV1:
    evidence_domain: str
    responsibility_class: str
    owner_ref: str
    owner_head: str
    owner_blob: str
    subject_ref: str
    subject_generation: str
    source_semantic_digest: str
    projection_schema: str
    projection_version: str
    projection_payload_digest: str
    owner_currentness_ref: str
    consequence_ceiling: str = "PRESENTATION_ONLY"

    @property
    def digest(self) -> str:
        return _domain_digest("AURA_OWNER_PROJECTION_QUERY_V1", self.__dict__)


@dataclass(frozen=True)
class OwnerProjectionResolutionV1:
    query_digest: str
    resolver_ref: str
    resolver_generation: str
    issuer_ref: str
    owner_ref: str
    owner_head: str
    owner_blob: str
    owner_currentness_ref: str
    subject_ref: str
    subject_generation: str
    projection_payload_digest: str
    currentness_state: str
    revoked: bool
    lineage_ref: str
    consequence_ceiling: str


@dataclass(frozen=True)
class ProviderTargetQueryV1:
    principal_ref: str
    route_id: str
    provider_ref: str
    model_ref: str
    candidate_evidence_ref: str
    candidate_evidence_digest: str
    cost_class: str
    provider_currentness_ref: str
    rate_currentness_ref: str

    @property
    def digest(self) -> str:
        return _domain_digest("AURA_PROVIDER_TARGET_QUERY_V1", self.__dict__)


@dataclass(frozen=True)
class ProviderTargetResolutionV1:
    query_digest: str
    resolver_ref: str
    resolver_generation: str
    issuer_ref: str
    evidence_ref: str
    evidence_digest: str
    source_generation: str
    currentness_ref: str
    currentness_state: str
    revoked: bool
    principal_ref: str
    route_id: str
    provider_ref: str
    model_ref: str
    candidate_evidence_ref: str
    candidate_evidence_digest: str
    cost_class: str
    provider_currentness_ref: str
    rate_currentness_ref: str


class AuthorityResolverV1(Protocol):
    """Trusted runtime capability boundary; never serialized inside share data."""
    def resolve_owner_projection(self, query: OwnerProjectionQueryV1) -> OwnerProjectionResolutionV1 | None: ...
    def resolve_provider_target(self, query: ProviderTargetQueryV1) -> ProviderTargetResolutionV1 | None: ...


def _valid_owner_resolution(query: OwnerProjectionQueryV1, receipt: object) -> bool:
    if not isinstance(receipt, OwnerProjectionResolutionV1): return False
    expected = (query.digest, query.owner_ref, query.owner_head, query.owner_blob, query.owner_currentness_ref, query.subject_ref, query.subject_generation, query.projection_payload_digest, "CURRENT", False, query.consequence_ceiling)
    actual = (receipt.query_digest, receipt.owner_ref, receipt.owner_head, receipt.owner_blob, receipt.owner_currentness_ref, receipt.subject_ref, receipt.subject_generation, receipt.projection_payload_digest, receipt.currentness_state, receipt.revoked, receipt.consequence_ceiling)
    try:
        _token(receipt.resolver_ref, "OWNER_RESOLVER_REF_INVALID"); _token(receipt.resolver_generation, "OWNER_RESOLVER_GENERATION_INVALID"); _token(receipt.issuer_ref, "OWNER_ISSUER_REF_INVALID"); _token(receipt.lineage_ref, "OWNER_LINEAGE_REF_INVALID")
    except FirewallError:
        return False
    return actual == expected


def _valid_provider_resolution(query: ProviderTargetQueryV1, receipt: object) -> bool:
    if not isinstance(receipt, ProviderTargetResolutionV1): return False
    expected = (query.digest, "CURRENT", False, query.principal_ref, query.route_id, query.provider_ref, query.model_ref, query.candidate_evidence_ref, query.candidate_evidence_digest, query.cost_class, query.provider_currentness_ref, query.rate_currentness_ref)
    actual = (receipt.query_digest, receipt.currentness_state, receipt.revoked, receipt.principal_ref, receipt.route_id, receipt.provider_ref, receipt.model_ref, receipt.candidate_evidence_ref, receipt.candidate_evidence_digest, receipt.cost_class, receipt.provider_currentness_ref, receipt.rate_currentness_ref)
    try:
        for value, code in ((receipt.resolver_ref,"TARGET_RESOLVER_REF_INVALID"),(receipt.resolver_generation,"TARGET_RESOLVER_GENERATION_INVALID"),(receipt.issuer_ref,"TARGET_ISSUER_REF_INVALID"),(receipt.evidence_ref,"TARGET_EVIDENCE_REF_INVALID"),(receipt.source_generation,"TARGET_SOURCE_GENERATION_INVALID"),(receipt.currentness_ref,"TARGET_CURRENTNESS_REF_INVALID")):
            _token(value, code)
        _sha(receipt.evidence_digest, "TARGET_EVIDENCE_DIGEST_INVALID")
    except FirewallError:
        return False
    return actual == expected


def compile_share_escalation_firewall(
    share_plan: Mapping[str, Any], recipe_plan: Mapping[str, Any], residual: Mapping[str, Any],
    router_decision: Mapping[str, Any], *, router_currentness: Mapping[str, Any],
    principal_ref: str, resolver: AuthorityResolverV1 | None = None,
) -> dict[str, Any]:
    share, recipe = verify_share_launch_plan(share_plan), verify_recipe_plan(recipe_plan)
    currentness, currentness_digest = verify_router_currentness(router_currentness)
    residual_v = verify_capability_residual(residual, recipe_plan=recipe, currentness=currentness)
    decision = verify_router_decision(router_decision, residual=residual_v, router_currentness_digest=currentness_digest)
    principal = _token(principal_ref, "RECIPIENT_PRINCIPAL_REF_INVALID")

    queries = (
        OwnerProjectionQueryV1("SHARE_PLAN", "PORTABLE_SHARE", ZF05A_OWNER_REF, ZF05A_OWNER_HEAD, ZF05A_OWNER_BLOB, share["capsule_id"], share["capsule_digest"], share["capsule_digest"], SHARE_PLAN_SCHEMA, "V1", share["plan_digest"], ZF05A_OWNER_HEAD),
        OwnerProjectionQueryV1("RECIPE_PLAN", "PORTABLE_RECIPE", ZF03A_OWNER_REF, ZF03A_OWNER_HEAD, ZF03A_OWNER_BLOB, recipe["recipe_id"], recipe["recipe_version"], recipe["recipe_digest"], RECIPE_PLAN_SCHEMA, "V1", recipe["plan_digest"], ZF03A_OWNER_HEAD),
        OwnerProjectionQueryV1("ESCALATION_DECISION", "MODEL_ESCALATION", ZF07A_OWNER_REF, ZF07A_OWNER_HEAD, ZF07A_OWNER_BLOB, residual_v["residual_id"], residual_v["source_generation"], decision["decision_digest"], ROUTER_DECISION_SCHEMA, "V1", decision["decision_digest"], ZF07A_OWNER_HEAD),
    )
    blockers: list[str] = []
    owner_resolutions: list[OwnerProjectionResolutionV1] = []
    if resolver is None:
        blockers.append("OWNER_RESOLVER_REQUIRED")
    else:
        for query in queries:
            receipt = resolver.resolve_owner_projection(query)
            if not _valid_owner_resolution(query, receipt):
                blockers.append(f"OWNER_RESOLUTION_REQUIRED:{query.evidence_domain}")
            else:
                owner_resolutions.append(receipt)

    presentable: list[dict[str, Any]] = []
    target_resolutions: list[ProviderTargetResolutionV1] = []
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
    elif len(owner_resolutions) != len(queries):
        disposition = "EVIDENCE_REQUIRED"
    else:
        for option in decision["options"]:
            if option["execution_location"] == "REMOTE":
                query = ProviderTargetQueryV1(principal, option["route_id"], option["provider_ref"], option["model_ref"], option["candidate_evidence_ref"], option["candidate_evidence_digest"], option["cost_class"], currentness["provider_catalog_currentness_ref"], currentness["rate_catalog_currentness_ref"])
                receipt = resolver.resolve_provider_target(query) if resolver is not None else None
                if not _valid_provider_resolution(query, receipt):
                    blockers.append(f"PROVIDER_TARGET_RESOLUTION_REQUIRED:{option['route_id']}"); continue
                target_resolutions.append(receipt)
            presentable.append({k: option[k] for k in ("route_id","model_ref","provider_ref","execution_location","cost_class","required_actions","candidate_evidence_ref","candidate_evidence_digest")})
        disposition = "EVIDENCE_REQUIRED" if blockers else "RECIPIENT_ESCALATION_READY"

    logical = {
        "schema": DECISION_SCHEMA, "firewall_schema": SCHEMA,
        "share_plan_digest": share["plan_digest"], "recipe_plan_digest": recipe["plan_digest"],
        "residual_id": residual_v["residual_id"], "capability_ref": residual_v["capability_ref"],
        "residual_kind": residual_v["residual_kind"], "residual_unresolved": residual_v["unresolved"],
        "router_currentness_digest": currentness_digest, "router_decision_digest": decision["decision_digest"],
        "router_disposition": decision["disposition"], "principal_ref": principal,
        "disposition": disposition, "presentable_options": presentable, "blockers": tuple(sorted(set(blockers))),
        "owner_projection_compatibility_recomputed": True,
        "owner_resolution_proven": len(owner_resolutions) == len(queries),
        "provider_targets_resolved": bool(target_resolutions) or all(o["execution_location"] != "REMOTE" for o in decision["options"]),
        "owner_resolution_refs": tuple(sorted(r.lineage_ref for r in owner_resolutions)),
        "provider_resolution_refs": tuple(sorted(r.evidence_ref for r in target_resolutions)),
        "credential_authorized": False, "model_download_authorized": False,
        "provider_call_authorized": False, "payment_authorized": False,
        "network_authorized": False, "effect_authorized": False, "execution_proven": False,
        "owner_contract_refs": {
            "zf05a": {"head": ZF05A_OWNER_HEAD, "blob": ZF05A_OWNER_BLOB},
            "zf03a": {"head": ZF03A_OWNER_HEAD, "blob": ZF03A_OWNER_BLOB},
            "zf07a": {"head": ZF07A_OWNER_HEAD, "blob": ZF07A_OWNER_BLOB},
        },
    }
    logical["firewall_digest"] = _domain_digest("AURA_ADOPT_SHARE_ESCALATION_FIREWALL_V1", logical)
    return logical
