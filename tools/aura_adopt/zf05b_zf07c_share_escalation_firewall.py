"""AURA-ADOPT-001 ZF-05B/ZF-07C share-to-model escalation firewall.

Pure D0 integration membrane. It consumes zero-authority projections from the
share/provenance lane and the recipient's capability-escalation lane. It never
creates a capability residual, reads credentials, downloads a model, calls a
provider, takes payment, or grants execution/network authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
import re

SCHEMA = "ShareEscalationFirewallV1"
DECISION_SCHEMA = "ShareEscalationFirewallDecisionV1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,255}$")

SHARE_SCOPES = frozenset({
    "SHARE_SOURCE", "SHARE_RECIPE", "SHARE_OUTPUT", "SHARE_DISTRIBUTION", "SHARE_ATTRIBUTION"
})
PROVIDER_SCOPES = frozenset({
    "MODEL_CATALOG", "PROVIDER_CATALOG", "RATE_CATALOG", "FREE_RATE_EVIDENCE"
})
FORBIDDEN_SHARE_ACTION_PREFIXES = (
    "REQUEST_CREDENTIAL",
    "REQUEST_PROVIDER",
    "EXPLICIT_PAYMENT",
    "EXPLICIT_MODEL_DOWNLOAD",
    "EXPLICIT_REMOTE_EXECUTION",
    "MODEL_INFERENCE_REQUIRED",
)
PROVIDER_ACTION_PREFIXES = (
    "REQUEST_CREDENTIAL",
    "REQUEST_PROVIDER",
    "EXPLICIT_PAYMENT",
    "EXPLICIT_REMOTE_EXECUTION",
)

class FirewallError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail

class ResidualKind(str, Enum):
    MODEL_INFERENCE_REQUIRED = "MODEL_INFERENCE_REQUIRED"
    NON_MODEL_RESIDUAL = "NON_MODEL_RESIDUAL"

class FirewallDisposition(str, Enum):
    SHARE_EVIDENCE_REQUIRED = "SHARE_EVIDENCE_REQUIRED"
    NO_MODEL_ESCALATION = "NO_MODEL_ESCALATION"
    RECIPIENT_ESCALATION_READY = "RECIPIENT_ESCALATION_READY"
    EVIDENCE_REQUIRED = "EVIDENCE_REQUIRED"

def _token(value: object, code: str) -> str:
    if not isinstance(value, str):
        raise FirewallError(code)
    value = value.strip()
    if not value or not _TOKEN.fullmatch(value):
        raise FirewallError(code)
    return value

def _sha(value: object, code: str) -> str:
    if not isinstance(value, str):
        raise FirewallError(code)
    value = value.strip().lower()
    if not _SHA256.fullmatch(value):
        raise FirewallError(code)
    return value

def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise FirewallError("NONCANONICAL_FIREWALL_STATE") from exc

def _digest(domain: str, value: object) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical(value)).hexdigest()

def _false(flag: object, code: str) -> None:
    if flag is not False:
        raise FirewallError(code)

def _tuple_tokens(values: object, code: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise FirewallError(code)
    clean = tuple(_token(v, code) for v in values)
    if len(set(clean)) != len(clean):
        raise FirewallError(f"{code}_DUPLICATE")
    return clean

@dataclass(frozen=True)
class ScopedEvidenceV1:
    ref: str
    digest: str
    source_generation: str
    currentness_ref: str
    currentness_state: str
    scope: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "ref", _token(self.ref, "EVIDENCE_REF_INVALID"))
        object.__setattr__(self, "digest", _sha(self.digest, "EVIDENCE_DIGEST_INVALID"))
        object.__setattr__(self, "source_generation", _token(self.source_generation, "EVIDENCE_GENERATION_INVALID"))
        object.__setattr__(self, "currentness_ref", _token(self.currentness_ref, "EVIDENCE_CURRENTNESS_REF_INVALID"))
        if self.currentness_state not in {"CURRENT", "STALE", "UNKNOWN"}:
            raise FirewallError("EVIDENCE_CURRENTNESS_STATE_INVALID")
        object.__setattr__(self, "scope", _token(self.scope, "EVIDENCE_SCOPE_INVALID"))

@dataclass(frozen=True)
class ShareLaunchProjectionV1:
    capsule_digest: str
    capsule_id: str
    status: str
    creator_ref: str
    evidence: tuple[ScopedEvidenceV1, ...]
    required_user_actions: tuple[str, ...]
    attribution_identity_proven: bool = False
    network_fetch_authorized: bool = False
    install_authorized: bool = False
    execution_authorized: bool = False
    publication_authorized: bool = False
    payment_authorized: bool = False
    telemetry_authorized: bool = False
    recipient_tracking_authorized: bool = False
    provider_call_authorized: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "capsule_digest", _sha(self.capsule_digest, "CAPSULE_DIGEST_INVALID"))
        object.__setattr__(self, "capsule_id", _token(self.capsule_id, "CAPSULE_ID_INVALID"))
        if self.status not in {"READY_FOR_USER_ACTION", "EVIDENCE_REQUIRED", "ROUTE_OR_EVIDENCE_REQUIRED"}:
            raise FirewallError("SHARE_STATUS_INVALID")
        object.__setattr__(self, "creator_ref", _token(self.creator_ref, "CREATOR_REF_INVALID"))
        if not isinstance(self.evidence, tuple) or not self.evidence:
            raise FirewallError("SHARE_EVIDENCE_REQUIRED")
        if any(not isinstance(item, ScopedEvidenceV1) for item in self.evidence):
            raise FirewallError("SHARE_EVIDENCE_INVALID")
        if any(item.scope not in SHARE_SCOPES for item in self.evidence):
            raise FirewallError("SHARE_EVIDENCE_SCOPE_INVALID")
        if len({item.ref for item in self.evidence}) != len(self.evidence):
            raise FirewallError("SHARE_EVIDENCE_REF_DUPLICATE")
        object.__setattr__(self, "required_user_actions", _tuple_tokens(self.required_user_actions, "SHARE_ACTION_INVALID"))
        for action in self.required_user_actions:
            if action.startswith(FORBIDDEN_SHARE_ACTION_PREFIXES):
                raise FirewallError("SHARE_CANNOT_MINT_ESCALATION_ACTION", action)
        _false(self.attribution_identity_proven, "SHARE_ATTRIBUTION_IDENTITY_AUTHORITY_FORBIDDEN")
        for name in (
            "network_fetch_authorized", "install_authorized", "execution_authorized",
            "publication_authorized", "payment_authorized", "telemetry_authorized",
            "recipient_tracking_authorized", "provider_call_authorized",
        ):
            _false(getattr(self, name), f"SHARE_AUTHORITY_WIDENING:{name}")

@dataclass(frozen=True)
class RecipientCapabilityResidualV1:
    residual_id: str
    recipe_plan_digest: str
    capability_ref: str
    residual_kind: ResidualKind
    unresolved: bool
    derivation_origin: str
    derivation_evidence: ScopedEvidenceV1

    def __post_init__(self) -> None:
        object.__setattr__(self, "residual_id", _token(self.residual_id, "RESIDUAL_ID_INVALID"))
        object.__setattr__(self, "recipe_plan_digest", _sha(self.recipe_plan_digest, "RECIPE_PLAN_DIGEST_INVALID"))
        object.__setattr__(self, "capability_ref", _token(self.capability_ref, "CAPABILITY_REF_INVALID"))
        if not isinstance(self.residual_kind, ResidualKind):
            raise FirewallError("RESIDUAL_KIND_INVALID")
        if type(self.unresolved) is not bool:
            raise FirewallError("RESIDUAL_UNRESOLVED_BOOL_REQUIRED")
        if self.derivation_origin != "RECIPIENT_CAPABILITY_PLAN":
            raise FirewallError("RESIDUAL_MUST_BE_RECIPIENT_DERIVED")
        if not isinstance(self.derivation_evidence, ScopedEvidenceV1):
            raise FirewallError("DERIVATION_EVIDENCE_REQUIRED")
        if self.derivation_evidence.scope != "RECIPIENT_CAPABILITY_PLAN":
            raise FirewallError("DERIVATION_EVIDENCE_SCOPE_INVALID")
        if self.derivation_evidence.currentness_state != "CURRENT":
            raise FirewallError("RECIPIENT_DERIVATION_NOT_CURRENT")

@dataclass(frozen=True)
class EscalationDecisionProjectionV1:
    residual_id: str
    capability_ref: str
    recipe_plan_digest: str
    disposition: str
    decision_digest: str
    selected_route_id: str | None
    earned_action_classes: tuple[str, ...]
    provider_evidence: tuple[ScopedEvidenceV1, ...]
    credential_prompt_performed: bool = False
    credential_collected: bool = False
    model_download_started: bool = False
    provider_call_made: bool = False
    payment_performed: bool = False
    effect_authorized: bool = False
    execution_proven: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "residual_id", _token(self.residual_id, "DECISION_RESIDUAL_ID_INVALID"))
        object.__setattr__(self, "capability_ref", _token(self.capability_ref, "DECISION_CAPABILITY_REF_INVALID"))
        object.__setattr__(self, "recipe_plan_digest", _sha(self.recipe_plan_digest, "DECISION_RECIPE_PLAN_DIGEST_INVALID"))
        if self.disposition not in {
            "NO_ESCALATION_REQUIRED", "LOCAL_ROUTE_READY", "USER_CHOICE_REQUIRED",
            "EVIDENCE_REQUIRED", "UPSTREAM_BLOCKED",
        }:
            raise FirewallError("ESCALATION_DISPOSITION_INVALID")
        object.__setattr__(self, "decision_digest", _sha(self.decision_digest, "ESCALATION_DECISION_DIGEST_INVALID"))
        if self.selected_route_id is not None:
            object.__setattr__(self, "selected_route_id", _token(self.selected_route_id, "SELECTED_ROUTE_ID_INVALID"))
        object.__setattr__(self, "earned_action_classes", _tuple_tokens(self.earned_action_classes, "EARNED_ACTION_INVALID"))
        if not isinstance(self.provider_evidence, tuple):
            raise FirewallError("PROVIDER_EVIDENCE_INVALID")
        if any(not isinstance(item, ScopedEvidenceV1) for item in self.provider_evidence):
            raise FirewallError("PROVIDER_EVIDENCE_INVALID")
        if any(item.scope not in PROVIDER_SCOPES for item in self.provider_evidence):
            raise FirewallError("PROVIDER_EVIDENCE_SCOPE_INVALID")
        if any(item.currentness_state != "CURRENT" for item in self.provider_evidence):
            raise FirewallError("PROVIDER_EVIDENCE_NOT_CURRENT")
        if len({item.ref for item in self.provider_evidence}) != len(self.provider_evidence):
            raise FirewallError("PROVIDER_EVIDENCE_REF_DUPLICATE")
        needs_provider = any(action.startswith(PROVIDER_ACTION_PREFIXES) for action in self.earned_action_classes)
        if needs_provider and not self.provider_evidence:
            raise FirewallError("PROVIDER_EVIDENCE_REQUIRED_FOR_ACTIONS")
        if self.disposition == "LOCAL_ROUTE_READY" and self.earned_action_classes:
            raise FirewallError("LOCAL_READY_CANNOT_HAVE_EARNED_ACTIONS")
        for name in (
            "credential_prompt_performed", "credential_collected", "model_download_started",
            "provider_call_made", "payment_performed", "effect_authorized", "execution_proven",
        ):
            _false(getattr(self, name), f"ESCALATION_EFFECT_ALREADY_OCCURRED:{name}")

@dataclass(frozen=True)
class ShareEscalationFirewallDecisionV1:
    capsule_digest: str
    residual_id: str
    capability_ref: str
    recipe_plan_digest: str
    escalation_decision_digest: str
    disposition: FirewallDisposition
    presentable_action_classes: tuple[str, ...]
    blockers: tuple[str, ...]
    firewall_digest: str
    schema: str = DECISION_SCHEMA
    provider_evidence_reused_from_share: bool = False
    credential_authorized: bool = False
    model_download_authorized: bool = False
    provider_call_authorized: bool = False
    payment_authorized: bool = False
    network_authorized: bool = False
    effect_authorized: bool = False
    execution_proven: bool = False

def _evidence_aliases(left: tuple[ScopedEvidenceV1, ...], right: tuple[ScopedEvidenceV1, ...]) -> tuple[str, ...]:
    left_refs = {item.ref for item in left}
    left_digests = {item.digest for item in left}
    aliases = []
    for item in right:
        if item.ref in left_refs:
            aliases.append(f"ref:{item.ref}")
        if item.digest in left_digests:
            aliases.append(f"digest:{item.digest}")
    return tuple(sorted(set(aliases)))

def compile_share_escalation_firewall(
    share: ShareLaunchProjectionV1,
    residual: RecipientCapabilityResidualV1,
    escalation: EscalationDecisionProjectionV1,
) -> ShareEscalationFirewallDecisionV1:
    if not isinstance(share, ShareLaunchProjectionV1):
        raise FirewallError("SHARE_LAUNCH_PROJECTION_REQUIRED")
    if not isinstance(residual, RecipientCapabilityResidualV1):
        raise FirewallError("RECIPIENT_RESIDUAL_REQUIRED")
    if not isinstance(escalation, EscalationDecisionProjectionV1):
        raise FirewallError("ESCALATION_DECISION_REQUIRED")

    if escalation.residual_id != residual.residual_id:
        raise FirewallError("ESCALATION_RESIDUAL_MISMATCH")
    if escalation.capability_ref != residual.capability_ref:
        raise FirewallError("ESCALATION_CAPABILITY_MISMATCH")
    if escalation.recipe_plan_digest != residual.recipe_plan_digest:
        raise FirewallError("ESCALATION_RECIPE_PLAN_MISMATCH")

    residual_alias = _evidence_aliases(share.evidence, (residual.derivation_evidence,))
    if residual_alias:
        raise FirewallError("SHARE_EVIDENCE_CANNOT_DERIVE_RECIPIENT_RESIDUAL", ",".join(residual_alias))
    provider_alias = _evidence_aliases(share.evidence, escalation.provider_evidence)
    if provider_alias:
        raise FirewallError("SHARE_EVIDENCE_CANNOT_SATISFY_PROVIDER_EVIDENCE", ",".join(provider_alias))
    derivation_provider_alias = _evidence_aliases((residual.derivation_evidence,), escalation.provider_evidence)
    if derivation_provider_alias:
        raise FirewallError("RECIPIENT_DERIVATION_CANNOT_SATISFY_PROVIDER_EVIDENCE", ",".join(derivation_provider_alias))

    blockers: list[str] = []
    actions: tuple[str, ...] = ()

    if share.status != "READY_FOR_USER_ACTION":
        disposition = FirewallDisposition.SHARE_EVIDENCE_REQUIRED
        blockers.append(f"SHARE_NOT_READY:{share.status}")
    elif not residual.unresolved or residual.residual_kind is ResidualKind.NON_MODEL_RESIDUAL:
        disposition = FirewallDisposition.NO_MODEL_ESCALATION
        if escalation.disposition not in {"NO_ESCALATION_REQUIRED", "UPSTREAM_BLOCKED", "EVIDENCE_REQUIRED"}:
            raise FirewallError("ESCALATION_PRESENT_WITHOUT_MODEL_RESIDUAL")
    elif escalation.disposition in {"EVIDENCE_REQUIRED", "UPSTREAM_BLOCKED"}:
        disposition = FirewallDisposition.EVIDENCE_REQUIRED
        blockers.append(f"ESCALATION_NOT_READY:{escalation.disposition}")
    else:
        disposition = FirewallDisposition.RECIPIENT_ESCALATION_READY
        actions = tuple(sorted(escalation.earned_action_classes))

    logical = {
        "schema": DECISION_SCHEMA,
        "firewall_schema": SCHEMA,
        "capsule_digest": share.capsule_digest,
        "share_evidence": [asdict(item) for item in sorted(share.evidence, key=lambda x: (x.scope, x.ref))],
        "residual_id": residual.residual_id,
        "capability_ref": residual.capability_ref,
        "recipe_plan_digest": residual.recipe_plan_digest,
        "residual_derivation_evidence": asdict(residual.derivation_evidence),
        "escalation_decision_digest": escalation.decision_digest,
        "provider_evidence": [asdict(item) for item in sorted(escalation.provider_evidence, key=lambda x: (x.scope, x.ref))],
        "disposition": disposition.value,
        "presentable_action_classes": actions,
        "blockers": tuple(blockers),
        "provider_evidence_reused_from_share": False,
        "credential_authorized": False,
        "model_download_authorized": False,
        "provider_call_authorized": False,
        "payment_authorized": False,
        "network_authorized": False,
        "effect_authorized": False,
        "execution_proven": False,
    }
    digest = _digest("AURA_ADOPT_SHARE_ESCALATION_FIREWALL_V1", logical)
    return ShareEscalationFirewallDecisionV1(
        capsule_digest=share.capsule_digest,
        residual_id=residual.residual_id,
        capability_ref=residual.capability_ref,
        recipe_plan_digest=residual.recipe_plan_digest,
        escalation_decision_digest=escalation.decision_digest,
        disposition=disposition,
        presentable_action_classes=actions,
        blockers=tuple(blockers),
        firewall_digest=digest,
    )
