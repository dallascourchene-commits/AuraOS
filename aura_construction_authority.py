"""Construction authority, attestation, and chained receipt adapter.

This adapter reuses Aura's relational-authority contracts. It evaluates digital
readiness and preserves human release requirements; it never authorizes physical
work or creates cryptographic identity claims.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import re
from typing import Any, Iterable, Mapping

from aura_event_contracts import stable_digest, stable_id
from aura_relational_authority import (
    ApprovalAttestation,
    AuthorityGrant,
    ChainedAuthorityReceipt,
    GENESIS_CHAIN_DIGEST,
    GovernanceDecision,
    QuorumPolicy,
    RiskClass,
    TrustedCheckpoint,
    evaluate_governance,
    verify_receipt_chain,
)
from aura_construction_contracts import (
    ConstructionClaim,
    ConstructionEvidence,
    ConstructionScope,
    PATCH_AUTHORITY,
    PROPOSAL_ONLY,
    VSA_PATCH_AUTHORITY,
)
from aura_construction_state import (
    ConstructionProjectState,
    ConstructionReadinessReport,
    query_claim_readiness,
)

CONSTRUCTION_AUTHORITY_VERSION = "AURA_CONSTRUCTION_AUTHORITY_V1"
_HEX = re.compile(r"^[0-9a-f]+$")
_CAPABILITY_SCOPE = re.compile(
    r"^construction\.[a-z0-9][a-z0-9_-]*(?:\.[a-z0-9][a-z0-9_-]*)*$"
)
_EVALUATION_TOKEN = object()


def _text(value: Any, name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    normalized = " ".join(value.split())
    if normalized != value:
        raise ValueError(f"{name} must be normalized")
    return value


def _normalized_text_input(
    value: Any, name: str, *, allow_empty: bool = False
) -> str:
    if type(value) is not str:
        raise ValueError(f"{name} must be a string")
    normalized = " ".join(value.split())
    if not allow_empty and not normalized:
        raise ValueError(f"{name} must not be empty")
    return normalized


def _digest(value: Any, name: str) -> str:
    if type(value) is not str:
        raise ValueError(f"{name} must be a hexadecimal digest")
    normalized = value.lower()
    if len(normalized) not in {32, 64} or _HEX.fullmatch(normalized) is None:
        raise ValueError(f"{name} must be a 32- or 64-character hexadecimal digest")
    if value != normalized:
        raise ValueError(f"{name} must use canonical lowercase hexadecimal")
    return normalized


def _tuple_strings(value: Any, name: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise ValueError(f"{name} must be a tuple")
    normalized = tuple(_text(item, f"{name}[]") for item in value)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{name} must not contain duplicates")
    if normalized != tuple(sorted(normalized)):
        raise ValueError(f"{name} must use canonical sorted order")
    if not allow_empty and not normalized:
        raise ValueError(f"{name} must not be empty")
    return normalized


def _sequence_input(value: Any, name: str) -> tuple[Any, ...]:
    if type(value) not in {list, tuple}:
        raise ValueError(f"{name} must be a list or tuple")
    return tuple(value)


def _normalized_unique(values: Iterable[Any], name: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    items = _sequence_input(values, name)
    result: list[str] = []
    seen: set[str] = set()
    for raw in items:
        if type(raw) is not str:
            raise ValueError(f"{name} contains a non-string value")
        normalized = " ".join(raw.split())
        if not normalized:
            raise ValueError(f"{name} contains an empty value")
        if normalized in seen:
            raise ValueError(f"{name} contains duplicate or normalization-colliding values")
        seen.add(normalized)
        result.append(normalized)
    if not allow_empty and not result:
        raise ValueError(f"{name} must not be empty")
    return tuple(sorted(result))


def _trusted_refs(values: Iterable[Any], name: str) -> tuple[str, ...]:
    return _normalized_unique(values, name, allow_empty=False)


def _verified_digest_bindings(
    values: Mapping[str, str],
    name: str,
) -> dict[str, str]:
    if not isinstance(values, Mapping) or not values:
        raise ValueError(f"{name} must be a non-empty mapping")
    result: dict[str, str] = {}
    for raw_ref, raw_digest in values.items():
        ref = _text(raw_ref, f"{name}.reference")
        if ref in result:
            raise ValueError(f"{name} contains a duplicate reference")
        result[ref] = _digest(raw_digest, f"{name}[{ref}]")
    return result


def _timestamp(value: Any, name: str) -> float:
    if type(value) not in {int, float}:
        raise ValueError(f"{name} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _require_canonical_float(value: Any, name: str) -> None:
    if type(value) is not float or not math.isfinite(value):
        raise ValueError(f"{name} must be a canonical finite float")


def _validate_policy_scope(scope: ConstructionScope, policy_scope: str) -> None:
    parts = policy_scope.split("/")
    if not 2 <= len(parts) <= 4 or parts[0] != "construction":
        raise ValueError("action policy scope must use construction/project[/zone[/work-package]]")
    expected = (scope.project_id, scope.zone_id, scope.work_package_id)
    supplied = tuple(parts[1:])
    for index, value in enumerate(supplied):
        if value != expected[index]:
            label = ("project", "zone", "work package")[index]
            raise ValueError(f"action policy scope {label} does not match its Construction scope")
    if any(not item for item in supplied):
        raise ValueError("action policy scope contains an empty component")


def _validate_authority_boundary(
    *,
    proposal_only: bool,
    human_release_required: bool,
    physical_work_authorized: bool,
    patch_authority: str,
    vsa_patch_authority: bool,
) -> None:
    if proposal_only is not True or human_release_required is not True or physical_work_authorized is not False:
        raise ValueError("construction authority boundary was modified")
    if patch_authority != PATCH_AUTHORITY or vsa_patch_authority is not False:
        raise ValueError("construction patch-authority boundary was modified")


@dataclass(frozen=True)
class ConstructionGovernanceReplay:
    grants: tuple[AuthorityGrant, ...]
    attestations: tuple[ApprovalAttestation, ...]
    quorum_policy: QuorumPolicy
    verified_authority_refs: tuple[str, ...]
    verified_attestation_refs: tuple[str, ...]
    proposer_principal_id: str = ""
    normal_policy: QuorumPolicy | None = None
    emergency_reason: str = ""

    def __post_init__(self) -> None:
        if type(self.grants) is not tuple or not all(
            type(item) is AuthorityGrant for item in self.grants
        ):
            raise ValueError("governance replay grants must be exact AuthorityGrant values")
        if type(self.attestations) is not tuple or not all(
            type(item) is ApprovalAttestation for item in self.attestations
        ):
            raise ValueError(
                "governance replay attestations must be exact ApprovalAttestation values"
            )
        if type(self.quorum_policy) is not QuorumPolicy:
            raise ValueError("governance replay requires an exact QuorumPolicy")
        _tuple_strings(
            self.verified_authority_refs,
            "governance_replay.verified_authority_refs",
            allow_empty=False,
        )
        _tuple_strings(
            self.verified_attestation_refs,
            "governance_replay.verified_attestation_refs",
            allow_empty=False,
        )
        if type(self.proposer_principal_id) is not str:
            raise ValueError("governance replay proposer_principal_id must be a string")
        if self.normal_policy is not None and type(self.normal_policy) is not QuorumPolicy:
            raise ValueError("governance replay normal_policy must be a QuorumPolicy")
        if type(self.emergency_reason) is not str:
            raise ValueError("governance replay emergency_reason must be a string")

    @classmethod
    def create(
        cls,
        *,
        grants: Iterable[AuthorityGrant],
        attestations: Iterable[ApprovalAttestation],
        quorum_policy: QuorumPolicy,
        verified_authority_refs: Iterable[str],
        verified_attestation_refs: Iterable[str],
        proposer_principal_id: str = "",
        normal_policy: QuorumPolicy | None = None,
        emergency_reason: str = "",
    ) -> "ConstructionGovernanceReplay":
        return cls(
            grants=tuple(grants),
            attestations=tuple(attestations),
            quorum_policy=quorum_policy,
            verified_authority_refs=_trusted_refs(
                verified_authority_refs, "verified_authority_refs"
            ),
            verified_attestation_refs=_trusted_refs(
                verified_attestation_refs, "verified_attestation_refs"
            ),
            proposer_principal_id=_normalized_text_input(
                proposer_principal_id, "proposer_principal_id", allow_empty=True
            ),
            normal_policy=normal_policy,
            emergency_reason=_normalized_text_input(
                emergency_reason, "emergency_reason", allow_empty=True
            ),
        )


@dataclass(frozen=True)
class ConstructionActionRequest:
    action_id: str
    action_digest: str
    scope: ConstructionScope
    action_kind: str
    policy_scope: str
    capability_scope: str
    risk_class: str
    required_claim_ids: tuple[str, ...]
    created_at: float
    expires_at: float
    version: str = CONSTRUCTION_AUTHORITY_VERSION
    proposal_only: bool = PROPOSAL_ONLY
    human_release_required: bool = True
    physical_work_authorized: bool = False
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    def __post_init__(self) -> None:
        if self.version != CONSTRUCTION_AUTHORITY_VERSION:
            raise ValueError("unsupported construction authority version")
        if type(self.scope) is not ConstructionScope:
            raise ValueError("action scope must be an exact ConstructionScope")
        _text(self.action_kind, "action.action_kind")
        _text(self.policy_scope, "action.policy_scope")
        _text(self.capability_scope, "action.capability_scope")
        _validate_policy_scope(self.scope, self.policy_scope)
        if _CAPABILITY_SCOPE.fullmatch(self.capability_scope) is None:
            raise ValueError(
                "action capability scope must use canonical construction.component syntax"
            )
        if type(self.risk_class) is not str or self.risk_class not in {
            item.value for item in RiskClass
        }:
            raise ValueError(f"unknown action risk_class: {self.risk_class}")
        _tuple_strings(self.required_claim_ids, "action.required_claim_ids", allow_empty=False)
        _require_canonical_float(self.created_at, "action.created_at")
        _require_canonical_float(self.expires_at, "action.expires_at")
        created = _timestamp(self.created_at, "action.created_at")
        if _timestamp(self.expires_at, "action.expires_at") <= created:
            raise ValueError("action expires_at must be later than created_at")
        _validate_authority_boundary(
            proposal_only=self.proposal_only,
            human_release_required=self.human_release_required,
            physical_work_authorized=self.physical_work_authorized,
            patch_authority=self.patch_authority,
            vsa_patch_authority=self.vsa_patch_authority,
        )
        payload = self._identity_payload()
        if self.action_digest != stable_digest(payload):
            raise ValueError("action digest does not match its content")
        if self.action_id != stable_id("construction-action", payload):
            raise ValueError("action ID does not match its content")

    @classmethod
    def create(
        cls,
        *,
        scope: ConstructionScope,
        action_kind: str,
        policy_scope: str,
        capability_scope: str,
        risk_class: str | RiskClass,
        required_claim_ids: Iterable[str],
        created_at: float,
        expires_at: float,
    ) -> "ConstructionActionRequest":
        if type(scope) is not ConstructionScope:
            raise ValueError("scope must be an exact ConstructionScope")
        if isinstance(risk_class, RiskClass):
            risk = risk_class.value
        elif type(risk_class) is str:
            risk = risk_class.upper()
        else:
            raise ValueError("risk_class must be a string or RiskClass")
        values = {
            "scope": scope,
            "action_kind": _normalized_text_input(action_kind, "action_kind"),
            "policy_scope": _normalized_text_input(policy_scope, "policy_scope"),
            "capability_scope": _normalized_text_input(
                capability_scope, "capability_scope"
            ),
            "risk_class": risk,
            "required_claim_ids": _normalized_unique(required_claim_ids, "required_claim_ids", allow_empty=False),
            "created_at": _timestamp(created_at, "created_at"),
            "expires_at": _timestamp(expires_at, "expires_at"),
            "version": CONSTRUCTION_AUTHORITY_VERSION,
            "proposal_only": PROPOSAL_ONLY,
            "human_release_required": True,
            "physical_work_authorized": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        payload = cls._payload_from_values(values)
        return cls(action_id=stable_id("construction-action", payload), action_digest=stable_digest(payload), **values)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ConstructionActionRequest":
        data = dict(value)
        return cls(
            action_id=data.get("action_id"),
            action_digest=data.get("action_digest"),
            scope=ConstructionScope.from_dict(dict(data.get("scope") or {})),
            action_kind=data.get("action_kind"),
            policy_scope=data.get("policy_scope"),
            capability_scope=data.get("capability_scope"),
            risk_class=data.get("risk_class"),
            required_claim_ids=tuple(data.get("required_claim_ids", ())),
            created_at=data.get("created_at"),
            expires_at=data.get("expires_at"),
            version=data.get("version"),
            proposal_only=data.get("proposal_only"),
            human_release_required=data.get("human_release_required"),
            physical_work_authorized=data.get("physical_work_authorized"),
            patch_authority=data.get("patch_authority"),
            vsa_patch_authority=data.get("vsa_patch_authority"),
        )

    @staticmethod
    def _payload_from_values(values: Mapping[str, Any]) -> dict[str, Any]:
        return {**values, "scope": values["scope"].to_dict(), "required_claim_ids": list(values["required_claim_ids"])}

    def _identity_payload(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("action_id")
        data.pop("action_digest")
        return data

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConstructionAuthorityResult:
    result_id: str
    result_digest: str
    project_id: str
    scope_key: str
    request_id: str
    request_digest: str
    required_claim_ids: tuple[str, ...]
    state_digest: str
    governance_decision_id: str
    governance_decision_digest: str
    governance_authorized: bool
    evidence_ready: bool
    digitally_ready: bool
    readiness_reports: tuple[ConstructionReadinessReport, ...]
    missing_reasons: tuple[str, ...]
    evaluated_at: float
    expires_at: float
    version: str = CONSTRUCTION_AUTHORITY_VERSION
    proposal_only: bool = PROPOSAL_ONLY
    human_release_required: bool = True
    physical_work_authorized: bool = False
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    def __post_init__(self) -> None:
        if self.version != CONSTRUCTION_AUTHORITY_VERSION:
            raise ValueError("unsupported construction authority result version")
        _text(self.project_id, "result.project_id")
        _text(self.scope_key, "result.scope_key")
        if not self.scope_key.startswith(f"{self.project_id}/"):
            raise ValueError("authority result scope does not belong to its project")
        _text(self.request_id, "result.request_id")
        _digest(self.request_digest, "result.request_digest")
        _tuple_strings(
            self.required_claim_ids,
            "result.required_claim_ids",
            allow_empty=False,
        )
        _digest(self.state_digest, "result.state_digest")
        _text(self.governance_decision_id, "result.governance_decision_id")
        _digest(self.governance_decision_digest, "result.governance_decision_digest")
        flags = (
            self.governance_authorized,
            self.evidence_ready,
            self.digitally_ready,
        )
        if any(type(value) is not bool for value in flags):
            raise ValueError("authority result flags must be booleans")
        reports_are_exact = (
            type(self.readiness_reports) is tuple
            and bool(self.readiness_reports)
            and all(
                type(item) is ConstructionReadinessReport
                for item in self.readiness_reports
            )
        )
        if not reports_are_exact:
            raise ValueError("authority result requires exact readiness reports")
        report_claims = tuple(item.claim_id for item in self.readiness_reports)
        if report_claims != tuple(sorted(report_claims)):
            raise ValueError("authority result readiness reports must use canonical claim order")
        if report_claims != self.required_claim_ids:
            raise ValueError("authority result readiness reports do not match required claims")
        if any(item.state_digest != self.state_digest for item in self.readiness_reports):
            raise ValueError("authority result mixes readiness reports from another state")
        _require_canonical_float(self.evaluated_at, "result.evaluated_at")
        if any(item.evaluated_at != self.evaluated_at for item in self.readiness_reports):
            raise ValueError("authority result mixes readiness reports from another evaluation")
        actual_evidence_ready = all(item.ready for item in self.readiness_reports)
        if self.evidence_ready is not actual_evidence_ready:
            raise ValueError("authority result evidence-ready flag is inconsistent")
        _tuple_strings(self.missing_reasons, "result.missing_reasons")
        _require_canonical_float(self.evaluated_at, "result.evaluated_at")
        _require_canonical_float(self.expires_at, "result.expires_at")
        evaluated = _timestamp(self.evaluated_at, "result.evaluated_at")
        if _timestamp(self.expires_at, "result.expires_at") <= evaluated:
            raise ValueError("authority result expires_at must be later than evaluated_at")
        expected_ready = self.governance_authorized and self.evidence_ready and not self.missing_reasons
        if self.digitally_ready is not expected_ready:
            raise ValueError("authority result digital-readiness flag is inconsistent")
        _validate_authority_boundary(
            proposal_only=self.proposal_only,
            human_release_required=self.human_release_required,
            physical_work_authorized=self.physical_work_authorized,
            patch_authority=self.patch_authority,
            vsa_patch_authority=self.vsa_patch_authority,
        )
        payload = self._identity_payload()
        if self.result_digest != stable_digest(payload):
            raise ValueError("authority result digest does not match its content")
        if self.result_id != stable_id("construction-authority-result", payload):
            raise ValueError("authority result ID does not match its content")

    @classmethod
    def create(
        cls,
        *,
        request: ConstructionActionRequest,
        state: ConstructionProjectState,
        governance_decision: GovernanceDecision,
        evaluated_at: float,
        _evaluation_token: object | None = None,
    ) -> "ConstructionAuthorityResult":
        if _evaluation_token is not _EVALUATION_TOKEN:
            raise ValueError(
                "ConstructionAuthorityResult must be created by the canonical evaluator"
            )
        request.__post_init__()
        state.__post_init__()
        current = _timestamp(evaluated_at, "evaluated_at")
        if request.scope.project_id != state.project_id:
            raise ValueError("authority result request and state project do not match")
        _validate_decision_binding(governance_decision, request, now=current)
        readiness_reports = tuple(
            query_claim_readiness(state, claim_id=claim_id, now=current)
            for claim_id in request.required_claim_ids
        )
        evidence_ready = all(item.ready for item in readiness_reports)
        readiness_expiries: list[float] = []
        active_claims = {
            event.record.claim_id: event.record
            for event in state.active_claim_events
            if type(event.record) is ConstructionClaim
        }
        active_evidence = {
            event.record.evidence_id: event.record
            for event in state.active_evidence_events
            if type(event.record) is ConstructionEvidence
        }
        for claim_id in request.required_claim_ids:
            claim = active_claims.get(claim_id)
            if claim is None:
                continue
            if claim.expires_at is not None:
                readiness_expiries.append(claim.expires_at)
            for evidence_id in claim.evidence_refs:
                evidence = active_evidence.get(evidence_id)
                if evidence is not None and evidence.expires_at is not None:
                    readiness_expiries.append(evidence.expires_at)
        reasons: set[str] = set()
        for report in readiness_reports:
            reasons.update(f"claim:{report.claim_id}:{item}" for item in report.blockers)
        reasons.update(str(item) for item in governance_decision.authority_missing_reasons)
        if not governance_decision.authorized:
            reasons.add("governance_not_authorized")
        ready = governance_decision.authorized and evidence_ready and not reasons
        values = {
            "project_id": request.scope.project_id,
            "scope_key": request.scope.scope_key,
            "request_id": request.action_id,
            "request_digest": request.action_digest,
            "required_claim_ids": request.required_claim_ids,
            "state_digest": state.state_digest,
            "governance_decision_id": governance_decision.decision_id,
            "governance_decision_digest": governance_decision.decision_digest,
            "governance_authorized": bool(governance_decision.authorized),
            "evidence_ready": evidence_ready,
            "digitally_ready": ready,
            "readiness_reports": readiness_reports,
            "missing_reasons": tuple(sorted(reasons)),
            "evaluated_at": current,
            "expires_at": _timestamp(
                min(
                    request.expires_at,
                    governance_decision.expires_at,
                    *readiness_expiries,
                )
                if ready
                else request.expires_at,
                "expires_at",
            ),
            "version": CONSTRUCTION_AUTHORITY_VERSION,
            "proposal_only": PROPOSAL_ONLY,
            "human_release_required": True,
            "physical_work_authorized": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        payload = cls._payload_from_values(values)
        return cls(
            result_id=stable_id("construction-authority-result", payload),
            result_digest=stable_digest(payload),
            **values,
        )

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        *,
        request: ConstructionActionRequest | None = None,
        state: ConstructionProjectState | None = None,
        governance_decision: GovernanceDecision | None = None,
    ) -> "ConstructionAuthorityResult":
        data = dict(value)
        result = cls(
            result_id=data.get("result_id"),
            result_digest=data.get("result_digest"),
            project_id=data.get("project_id"),
            scope_key=data.get("scope_key"),
            request_id=data.get("request_id"),
            request_digest=data.get("request_digest"),
            required_claim_ids=_sequence_input(
                data.get("required_claim_ids", ()), "result.required_claim_ids"
            ),
            state_digest=data.get("state_digest"),
            governance_decision_id=data.get("governance_decision_id"),
            governance_decision_digest=data.get("governance_decision_digest"),
            governance_authorized=data.get("governance_authorized"),
            evidence_ready=data.get("evidence_ready"),
            digitally_ready=data.get("digitally_ready"),
            readiness_reports=tuple(
                ConstructionReadinessReport.from_dict(dict(item))
                for item in _sequence_input(
                    data.get("readiness_reports", ()), "result.readiness_reports"
                )
            ),
            missing_reasons=_sequence_input(
                data.get("missing_reasons", ()), "result.missing_reasons"
            ),
            evaluated_at=data.get("evaluated_at"),
            expires_at=data.get("expires_at"),
            version=data.get("version"),
            proposal_only=data.get("proposal_only"),
            human_release_required=data.get("human_release_required"),
            physical_work_authorized=data.get("physical_work_authorized"),
            patch_authority=data.get("patch_authority"),
            vsa_patch_authority=data.get("vsa_patch_authority"),
        )
        contexts = (request, state, governance_decision)
        if any(item is not None for item in contexts):
            if any(item is None for item in contexts):
                raise ValueError(
                    "authority result contextual validation requires request, state, and decision"
                )
            result.validate_against(
                request=request,
                state=state,
                governance_decision=governance_decision,
                now=result.evaluated_at,
            )
        elif result.digitally_ready:
            raise ValueError(
                "digitally ready authority results require contextual lineage validation"
            )
        return result

    @staticmethod
    def _payload_from_values(values: Mapping[str, Any]) -> dict[str, Any]:
        return {
            **values,
            "required_claim_ids": list(values["required_claim_ids"]),
            "readiness_reports": [item.to_dict() for item in values["readiness_reports"]],
            "missing_reasons": list(values["missing_reasons"]),
        }

    def _identity_payload(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("result_id")
        data.pop("result_digest")
        return data

    def validate_against(
        self,
        *,
        request: ConstructionActionRequest,
        state: ConstructionProjectState,
        governance_decision: GovernanceDecision,
        now: float,
    ) -> None:
        _validate_result_bindings(
            self,
            request=request,
            state=state,
            governance_decision=governance_decision,
            now=_timestamp(now, "now"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _validate_decision_binding(
    decision: GovernanceDecision,
    request: ConstructionActionRequest,
    *,
    now: float,
) -> None:
    if type(decision) is not GovernanceDecision:
        raise ValueError("decision must be an exact GovernanceDecision")
    if type(request) is not ConstructionActionRequest:
        raise ValueError("request must be an exact ConstructionActionRequest")
    decision.validate_integrity()
    if decision.action_id != request.action_id:
        raise ValueError("governance decision is bound to another action ID")
    if decision.action_payload_digest != request.action_digest:
        raise ValueError("governance decision is bound to another action digest")
    if decision.policy_scope != request.policy_scope:
        raise ValueError("governance decision policy scope does not match")
    if decision.capability_scope != request.capability_scope:
        raise ValueError("governance decision capability scope does not match")
    if decision.authorized:
        if now >= decision.expires_at:
            raise ValueError("governance decision is expired")
        decision.validate_for_action(
            action_id=request.action_id,
            action_payload_digest=request.action_digest,
            policy_scope=request.policy_scope,
            capability_scope=request.capability_scope,
            now=now,
        )


def _validate_result_bindings(
    result: ConstructionAuthorityResult,
    *,
    request: ConstructionActionRequest,
    state: ConstructionProjectState,
    governance_decision: GovernanceDecision,
    now: float,
) -> None:
    if type(result) is not ConstructionAuthorityResult:
        raise ValueError("result must be an exact ConstructionAuthorityResult")
    if type(request) is not ConstructionActionRequest:
        raise ValueError("request must be an exact ConstructionActionRequest")
    if type(state) is not ConstructionProjectState:
        raise ValueError("state must be an exact ConstructionProjectState")
    if type(governance_decision) is not GovernanceDecision:
        raise ValueError("governance_decision must be an exact GovernanceDecision")
    result.__post_init__()
    request.__post_init__()
    state.__post_init__()
    _validate_decision_binding(governance_decision, request, now=now)
    expected = {
        "project_id": request.scope.project_id,
        "scope_key": request.scope.scope_key,
        "request_id": request.action_id,
        "request_digest": request.action_digest,
        "required_claim_ids": request.required_claim_ids,
        "state_digest": state.state_digest,
        "governance_decision_id": governance_decision.decision_id,
        "governance_decision_digest": governance_decision.decision_digest,
        "governance_authorized": governance_decision.authorized,
    }
    for field, value in expected.items():
        if getattr(result, field) != value:
            raise ValueError(f"authority result is not bound to the supplied {field}")
    recomputed = ConstructionAuthorityResult.create(
        request=request,
        state=state,
        governance_decision=governance_decision,
        evaluated_at=result.evaluated_at,
        _evaluation_token=_EVALUATION_TOKEN,
    )
    if result != recomputed:
        raise ValueError("authority result does not match deterministic readiness replay")
    if now < result.evaluated_at:
        raise ValueError("construction authority receipt cannot predate evaluation")
    if now >= result.expires_at:
        raise ValueError("construction authority result is expired")


def _validate_evaluation_lineage(
    *,
    result: ConstructionAuthorityResult,
    decision: GovernanceDecision,
    request: ConstructionActionRequest,
    state: ConstructionProjectState,
    governance_replay: ConstructionGovernanceReplay,
) -> None:
    if type(governance_replay) is not ConstructionGovernanceReplay:
        raise ValueError("construction receipt requires exact governance replay material")
    replayed_result, replayed_decision = evaluate_construction_authority(
        request=request,
        state=state,
        grants=governance_replay.grants,
        attestations=governance_replay.attestations,
        quorum_policy=governance_replay.quorum_policy,
        verified_authority_refs=governance_replay.verified_authority_refs,
        verified_attestation_refs=governance_replay.verified_attestation_refs,
        proposer_principal_id=governance_replay.proposer_principal_id,
        normal_policy=governance_replay.normal_policy,
        emergency_reason=governance_replay.emergency_reason,
        now=result.evaluated_at,
    )
    if replayed_decision != decision:
        raise ValueError("governance decision does not match deterministic lineage replay")
    if replayed_result != result:
        raise ValueError("authority result does not match deterministic lineage replay")


def evaluate_construction_authority(
    *,
    request: ConstructionActionRequest,
    state: ConstructionProjectState,
    grants: Iterable[AuthorityGrant],
    attestations: Iterable[ApprovalAttestation],
    quorum_policy: QuorumPolicy,
    verified_authority_refs: Iterable[str],
    verified_attestation_refs: Iterable[str],
    proposer_principal_id: str = "",
    normal_policy: QuorumPolicy | None = None,
    emergency_reason: str = "",
    now: float,
) -> tuple[ConstructionAuthorityResult, GovernanceDecision]:
    """Evaluate exact Construction evidence and Aura relational authority.

    The evaluator is intentionally not injectable. This prevents a caller from
    supplying a self-consistent but unearned GovernanceDecision.
    """
    if type(request) is not ConstructionActionRequest:
        raise ValueError("request must be an exact ConstructionActionRequest")
    if type(state) is not ConstructionProjectState:
        raise ValueError("state must be an exact ConstructionProjectState")
    if type(quorum_policy) is not QuorumPolicy:
        raise ValueError("quorum_policy must be an exact QuorumPolicy")
    if normal_policy is not None and type(normal_policy) is not QuorumPolicy:
        raise ValueError("normal_policy must be an exact QuorumPolicy")
    grant_items = tuple(grants)
    attestation_items = tuple(attestations)
    if not all(type(item) is AuthorityGrant for item in grant_items):
        raise ValueError("grants must contain exact AuthorityGrant values")
    if not all(type(item) is ApprovalAttestation for item in attestation_items):
        raise ValueError("attestations must contain exact ApprovalAttestation values")
    request.__post_init__()
    state.__post_init__()
    current = _timestamp(now, "now")
    if request.scope.project_id != state.project_id:
        raise ValueError("construction action request and project state do not match")
    if current < request.created_at:
        raise ValueError("construction action request is not active yet")
    if current >= request.expires_at:
        raise ValueError("construction action request is expired")
    quorum_policy.validate()
    if quorum_policy.risk_class != request.risk_class:
        raise ValueError("construction action risk class and quorum policy disagree")

    authority_refs = _trusted_refs(
        verified_authority_refs,
        "verified_authority_refs",
    )
    attestation_refs = _trusted_refs(
        verified_attestation_refs,
        "verified_attestation_refs",
    )
    decision = evaluate_governance(
        action_id=request.action_id,
        action_payload_digest=request.action_digest,
        policy_scope=request.policy_scope,
        capability_scope=request.capability_scope,
        grants=grant_items,
        attestations=attestation_items,
        quorum_policy=quorum_policy,
        verified_authority_refs=authority_refs,
        verified_attestation_refs=attestation_refs,
        proposer_principal_id=proposer_principal_id,
        normal_policy=normal_policy,
        emergency_reason=emergency_reason,
        now=current,
    )
    if type(decision) is not GovernanceDecision:
        raise ValueError("Aura governance evaluator returned an invalid decision type")
    _validate_decision_binding(decision, request, now=current)
    result = ConstructionAuthorityResult.create(
        request=request,
        state=state,
        governance_decision=decision,
        evaluated_at=current,
        _evaluation_token=_EVALUATION_TOKEN,
    )
    return result, decision


@dataclass(frozen=True)
class ConstructionReceiptBinding:
    binding_id: str
    binding_digest: str
    project_id: str
    request_id: str
    request_digest: str
    state_digest: str
    governance_decision_id: str
    governance_decision_digest: str
    authority_result_id: str
    authority_result_digest: str
    chain_receipt_id: str
    chain_digest: str
    externally_verified_receipt_ref: str
    created_at: float
    version: str = CONSTRUCTION_AUTHORITY_VERSION
    proposal_only: bool = PROPOSAL_ONLY
    human_release_required: bool = True
    physical_work_authorized: bool = False
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    def __post_init__(self) -> None:
        _text(self.project_id, "binding.project_id")
        _text(self.request_id, "binding.request_id")
        _digest(self.request_digest, "binding.request_digest")
        _digest(self.state_digest, "binding.state_digest")
        _text(self.governance_decision_id, "binding.governance_decision_id")
        _digest(self.governance_decision_digest, "binding.governance_decision_digest")
        _text(self.authority_result_id, "binding.authority_result_id")
        _digest(self.authority_result_digest, "binding.authority_result_digest")
        _text(self.chain_receipt_id, "binding.chain_receipt_id")
        _digest(self.chain_digest, "binding.chain_digest")
        _text(self.externally_verified_receipt_ref, "binding.externally_verified_receipt_ref")
        _require_canonical_float(self.created_at, "binding.created_at")
        _timestamp(self.created_at, "binding.created_at")
        if self.version != CONSTRUCTION_AUTHORITY_VERSION:
            raise ValueError("unsupported construction receipt binding version")
        _validate_authority_boundary(
            proposal_only=self.proposal_only,
            human_release_required=self.human_release_required,
            physical_work_authorized=self.physical_work_authorized,
            patch_authority=self.patch_authority,
            vsa_patch_authority=self.vsa_patch_authority,
        )
        payload = self._identity_payload()
        if self.binding_digest != stable_digest(payload):
            raise ValueError("receipt binding digest does not match")
        if self.binding_id != stable_id("construction-receipt-binding", payload):
            raise ValueError("receipt binding ID does not match")

    @classmethod
    def create(
        cls,
        *,
        authority_result: ConstructionAuthorityResult,
        request: ConstructionActionRequest,
        state: ConstructionProjectState,
        governance_decision: GovernanceDecision,
        governance_replay: ConstructionGovernanceReplay,
        chain_receipt: ChainedAuthorityReceipt,
        externally_verified_receipt_ref: str,
        verified_receipt_bindings: Mapping[str, str],
        created_at: float,
        previous_receipt: ChainedAuthorityReceipt | None = None,
        trusted_checkpoint: TrustedCheckpoint | None = None,
        verified_checkpoint_refs: Iterable[str] = (),
    ) -> "ConstructionReceiptBinding":
        created = _timestamp(created_at, "created_at")
        _validate_result_bindings(
            authority_result,
            request=request,
            state=state,
            governance_decision=governance_decision,
            now=created,
        )
        _validate_evaluation_lineage(
            result=authority_result,
            decision=governance_decision,
            request=request,
            state=state,
            governance_replay=governance_replay,
        )
        chain_receipt.validate_integrity()
        _validate_receipt_predecessor(
            ledger_id=chain_receipt.ledger_id,
            sequence_number=chain_receipt.sequence_number,
            previous_chain_digest=chain_receipt.previous_chain_digest,
            created_at=chain_receipt.created_at,
            previous_receipt=previous_receipt,
            trusted_checkpoint=trusted_checkpoint,
            verified_checkpoint_refs=verified_checkpoint_refs,
        )
        expected_ledger = f"construction-authority/{authority_result.project_id}"
        if chain_receipt.ledger_id != expected_ledger:
            raise ValueError(f"construction receipt must use ledger {expected_ledger}")
        if chain_receipt.created_at < authority_result.evaluated_at:
            raise ValueError("chain receipt cannot predate the authority evaluation")
        if chain_receipt.created_at >= authority_result.expires_at:
            raise ValueError("chain receipt cannot be created after authority expiry")
        if chain_receipt.created_at > created:
            raise ValueError("receipt binding cannot predate its chain receipt")
        if not authority_result.digitally_ready:
            raise ValueError("cannot issue a receipt for a non-ready authority result")
        external_ref = _text(
            externally_verified_receipt_ref,
            "externally_verified_receipt_ref",
        )
        bindings = _verified_digest_bindings(
            verified_receipt_bindings,
            "verified_receipt_bindings",
        )
        bound_digest = bindings.get(external_ref)
        if bound_digest != authority_result.result_digest:
            raise ValueError("external receipt reference is not bound to this authority result")
        receipt_is_bound = (
            chain_receipt.record_id == authority_result.result_id
            and chain_receipt.record_digest == authority_result.result_digest
        )
        if not receipt_is_bound:
            raise ValueError("chain receipt is not bound to the authority result")
        values = {
            "project_id": authority_result.project_id,
            "request_id": request.action_id,
            "request_digest": request.action_digest,
            "state_digest": state.state_digest,
            "governance_decision_id": governance_decision.decision_id,
            "governance_decision_digest": governance_decision.decision_digest,
            "authority_result_id": authority_result.result_id,
            "authority_result_digest": authority_result.result_digest,
            "chain_receipt_id": chain_receipt.receipt_id,
            "chain_digest": chain_receipt.chain_digest,
            "externally_verified_receipt_ref": external_ref,
            "created_at": created,
            "version": CONSTRUCTION_AUTHORITY_VERSION,
            "proposal_only": PROPOSAL_ONLY,
            "human_release_required": True,
            "physical_work_authorized": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        payload = dict(values)
        return cls(
            binding_id=stable_id("construction-receipt-binding", payload),
            binding_digest=stable_digest(payload),
            **values,
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ConstructionReceiptBinding":
        data = dict(value)
        return cls(
            binding_id=data.get("binding_id"),
            binding_digest=data.get("binding_digest"),
            project_id=data.get("project_id"),
            request_id=data.get("request_id"),
            request_digest=data.get("request_digest"),
            state_digest=data.get("state_digest"),
            governance_decision_id=data.get("governance_decision_id"),
            governance_decision_digest=data.get("governance_decision_digest"),
            authority_result_id=data.get("authority_result_id"),
            authority_result_digest=data.get("authority_result_digest"),
            chain_receipt_id=data.get("chain_receipt_id"),
            chain_digest=data.get("chain_digest"),
            externally_verified_receipt_ref=data.get("externally_verified_receipt_ref"),
            created_at=data.get("created_at"),
            version=data.get("version"),
            proposal_only=data.get("proposal_only"),
            human_release_required=data.get("human_release_required"),
            physical_work_authorized=data.get("physical_work_authorized"),
            patch_authority=data.get("patch_authority"),
            vsa_patch_authority=data.get("vsa_patch_authority"),
        )

    def _identity_payload(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("binding_id")
        data.pop("binding_digest")
        return data

    def validate_against(
        self,
        *,
        authority_result: ConstructionAuthorityResult,
        request: ConstructionActionRequest,
        state: ConstructionProjectState,
        governance_decision: GovernanceDecision,
        governance_replay: ConstructionGovernanceReplay,
        chain_receipt: ChainedAuthorityReceipt,
        verified_receipt_bindings: Mapping[str, str],
        previous_receipt: ChainedAuthorityReceipt | None = None,
        trusted_checkpoint: TrustedCheckpoint | None = None,
        verified_checkpoint_refs: Iterable[str] = (),
    ) -> None:
        recreated = type(self).create(
            authority_result=authority_result,
            request=request,
            state=state,
            governance_decision=governance_decision,
            governance_replay=governance_replay,
            chain_receipt=chain_receipt,
            externally_verified_receipt_ref=self.externally_verified_receipt_ref,
            verified_receipt_bindings=verified_receipt_bindings,
            created_at=self.created_at,
            previous_receipt=previous_receipt,
            trusted_checkpoint=trusted_checkpoint,
            verified_checkpoint_refs=verified_checkpoint_refs,
        )
        if self != recreated:
            raise ValueError("receipt binding does not match exact persisted lineage")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _validate_receipt_predecessor(
    *,
    ledger_id: str,
    sequence_number: int,
    previous_chain_digest: str,
    created_at: float,
    previous_receipt: ChainedAuthorityReceipt | None,
    trusted_checkpoint: TrustedCheckpoint | None,
    verified_checkpoint_refs: Iterable[str],
) -> None:
    if sequence_number == 1:
        if previous_receipt is not None or trusted_checkpoint is not None:
            raise ValueError("genesis receipt cannot declare a predecessor")
        if previous_chain_digest != GENESIS_CHAIN_DIGEST:
            raise ValueError("first construction receipt must use the genesis digest")
        return
    if (previous_receipt is None) == (trusted_checkpoint is None):
        raise ValueError(
            "non-genesis receipt requires exactly one previous receipt or trusted checkpoint"
        )
    if previous_receipt is not None:
        if type(previous_receipt) is not ChainedAuthorityReceipt:
            raise ValueError("previous_receipt must be an exact ChainedAuthorityReceipt")
        previous_receipt.validate_integrity()
        if previous_receipt.ledger_id != ledger_id:
            raise ValueError("previous receipt belongs to another ledger")
        if sequence_number != previous_receipt.sequence_number + 1:
            raise ValueError("receipt sequence does not follow its previous receipt")
        if previous_chain_digest != previous_receipt.chain_digest:
            raise ValueError("receipt previous digest does not match its previous receipt")
        if created_at < previous_receipt.created_at:
            raise ValueError("receipt predates its previous receipt")
        return
    if type(trusted_checkpoint) is not TrustedCheckpoint:
        raise ValueError("trusted_checkpoint must be an exact TrustedCheckpoint")
    trusted_checkpoint.validate_integrity(
        verified_checkpoint_refs=_trusted_refs(
            verified_checkpoint_refs, "verified_checkpoint_refs"
        )
    )
    if trusted_checkpoint.ledger_id != ledger_id:
        raise ValueError("trusted checkpoint belongs to another ledger")
    if sequence_number != trusted_checkpoint.sequence_number + 1:
        raise ValueError("receipt sequence does not follow its trusted checkpoint")
    if previous_chain_digest != trusted_checkpoint.chain_digest:
        raise ValueError("receipt previous digest does not match its trusted checkpoint")
    if created_at < trusted_checkpoint.created_at:
        raise ValueError("receipt predates its trusted checkpoint")


def create_construction_receipt(
    *,
    authority_result: ConstructionAuthorityResult,
    request: ConstructionActionRequest,
    state: ConstructionProjectState,
    governance_decision: GovernanceDecision,
    governance_replay: ConstructionGovernanceReplay,
    ledger_id: str,
    sequence_number: int,
    previous_chain_digest: str = GENESIS_CHAIN_DIGEST,
    previous_receipt: ChainedAuthorityReceipt | None = None,
    trusted_checkpoint: TrustedCheckpoint | None = None,
    verified_checkpoint_refs: Iterable[str] = (),
    externally_verified_receipt_ref: str,
    verified_receipt_bindings: Mapping[str, str],
    created_at: float,
) -> tuple[ChainedAuthorityReceipt, ConstructionReceiptBinding]:
    created = _timestamp(created_at, "created_at")
    if type(sequence_number) is not int or sequence_number < 1:
        raise ValueError("construction receipt sequence_number must be a positive integer")
    if type(previous_chain_digest) is not str:
        raise ValueError("construction receipt previous_chain_digest must be a string")
    if sequence_number > 1:
        _digest(previous_chain_digest, "previous_chain_digest")
    _validate_receipt_predecessor(
        ledger_id=ledger_id,
        sequence_number=sequence_number,
        previous_chain_digest=previous_chain_digest,
        created_at=created,
        previous_receipt=previous_receipt,
        trusted_checkpoint=trusted_checkpoint,
        verified_checkpoint_refs=verified_checkpoint_refs,
    )
    _validate_result_bindings(
        authority_result,
        request=request,
        state=state,
        governance_decision=governance_decision,
        now=created,
    )
    _validate_evaluation_lineage(
        result=authority_result,
        decision=governance_decision,
        request=request,
        state=state,
        governance_replay=governance_replay,
    )
    expected_ledger = f"construction-authority/{authority_result.project_id}"
    if ledger_id != expected_ledger:
        raise ValueError(f"construction authority receipt ledger must be {expected_ledger}")
    receipt = ChainedAuthorityReceipt.create(
        ledger_id=ledger_id,
        sequence_number=sequence_number,
        previous_chain_digest=previous_chain_digest,
        record_id=authority_result.result_id,
        record_digest=authority_result.result_digest,
        created_at=created,
    )
    binding = ConstructionReceiptBinding.create(
        authority_result=authority_result,
        request=request,
        state=state,
        governance_decision=governance_decision,
        governance_replay=governance_replay,
        chain_receipt=receipt,
        externally_verified_receipt_ref=externally_verified_receipt_ref,
        verified_receipt_bindings=verified_receipt_bindings,
        created_at=created,
        previous_receipt=previous_receipt,
        trusted_checkpoint=trusted_checkpoint,
        verified_checkpoint_refs=verified_checkpoint_refs,
    )
    return receipt, binding


def verify_construction_receipts(
    receipts: Iterable[ChainedAuthorityReceipt],
    *,
    results_by_id: Mapping[str, ConstructionAuthorityResult],
    trusted_checkpoint: TrustedCheckpoint | None = None,
    verified_checkpoint_refs: Iterable[str] = (),
    require_digitally_ready: bool = True,
):
    """Verify receipt continuity and result-content binding only.

    This does not establish actor authenticity or replay governance lineage. Full
    authority validation requires ``ConstructionReceiptBinding.validate_against``
    with the exact grants, attestations, quorum, trusted references, state, and
    action request used by the canonical evaluator.
    """
    if type(require_digitally_ready) is not bool:
        raise ValueError("require_digitally_ready must be boolean")
    if trusted_checkpoint is not None and type(trusted_checkpoint) is not TrustedCheckpoint:
        raise ValueError("trusted_checkpoint must be an exact TrustedCheckpoint")
    record_digests: dict[str, str] = {}
    for key, result in results_by_id.items():
        if type(result) is not ConstructionAuthorityResult:
            raise ValueError("results_by_id contains an invalid result type")
        result.__post_init__()
        if key != result.result_id:
            raise ValueError("results_by_id key does not match result identity")
        if require_digitally_ready and not result.digitally_ready:
            raise ValueError("receipt verification requires digitally ready authority results")
        record_digests[key] = result.result_digest

    items = tuple(receipts)
    for receipt in items:
        if type(receipt) is not ChainedAuthorityReceipt:
            raise ValueError("receipts contains an invalid receipt type")
        result = results_by_id.get(receipt.record_id)
        if result is None:
            raise ValueError(f"receipt references an unknown authority result: {receipt.record_id}")
        expected_ledger = f"construction-authority/{result.project_id}"
        if receipt.ledger_id != expected_ledger:
            raise ValueError(f"construction receipt must use ledger {expected_ledger}")
        if receipt.created_at < result.evaluated_at:
            raise ValueError("construction receipt predates its authority evaluation")
        if receipt.created_at >= result.expires_at:
            raise ValueError("construction receipt was created after authority expiry")

    return verify_receipt_chain(
        items,
        record_digests=record_digests,
        trusted_checkpoint=trusted_checkpoint,
        verified_checkpoint_refs=verified_checkpoint_refs,
    )


__all__ = [
    "CONSTRUCTION_AUTHORITY_VERSION",
    "ConstructionGovernanceReplay",
    "ConstructionActionRequest",
    "ConstructionAuthorityResult",
    "ConstructionReceiptBinding",
    "evaluate_construction_authority",
    "create_construction_receipt",
    "verify_construction_receipts",
]
