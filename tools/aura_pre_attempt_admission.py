#!/usr/bin/env python3
"""Owner-resolved proposal -> pre-attempt admission for AuraOS.

D0 / HS1 / NONPROMOTING.

A current bounded proposal is still not an execution credential. This membrane composes
O64 owner-resolved proposal currentness with a separately owner-resolved pre-attempt
policy and concurrency state. It may mint only a deterministic PRE_ATTEMPT_ENVELOPE
identity. It never mints an execution lease, starts a provider effect, or grants effect
or Gate-10 authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Protocol

from tools.aura_bounded_proposal_capsule import (
    ProposalCapsule,
    ProposalOwnerResolver,
    revalidate_proposal_capsule,
)

POLICY_SCHEMA = "AURA-PRE-ATTEMPT-POLICY-v1"
RECEIPT_SCHEMA = "AURA-PRE-ATTEMPT-ADMISSION-RECEIPT-v1"
ELIGIBLE = "PRE_ATTEMPT_ENVELOPE_ELIGIBLE"
HEX = frozenset("0123456789abcdef")


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _required(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")


def _sha256(value: str, name: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(c not in HEX for c in value):
        raise ValueError(f"{name}_MUST_BE_SHA256_HEX")


@dataclass(frozen=True)
class PreAttemptPolicyState:
    """Trusted, owner-resolved policy state for one exact proposal/action scope."""

    schema_version: str
    policy_generation: str
    proposal_id: str
    domain_id: str
    action_kind: str
    authority_scope: str
    expected_route_fingerprint: str
    expected_observer_identity: str
    action_parameters_digest: str
    resource_envelope_digest: str
    concurrency_scope_digest: str
    effect_ceiling_digest: str
    policy_current: bool
    execution_authorized: bool = False
    provider_effect_authorized: bool = False

    def validate(self) -> None:
        if self.schema_version != POLICY_SCHEMA:
            raise ValueError("PRE_ATTEMPT_POLICY_SCHEMA_MISMATCH")
        for value, name in (
            (self.policy_generation, "POLICY_GENERATION"),
            (self.domain_id, "POLICY_DOMAIN_ID"),
            (self.action_kind, "POLICY_ACTION_KIND"),
            (self.authority_scope, "POLICY_AUTHORITY_SCOPE"),
            (self.expected_route_fingerprint, "EXPECTED_ROUTE_FINGERPRINT"),
            (self.expected_observer_identity, "EXPECTED_OBSERVER_IDENTITY"),
        ):
            _required(value, name)
        for value, name in (
            (self.proposal_id, "POLICY_PROPOSAL_ID"),
            (self.action_parameters_digest, "POLICY_ACTION_PARAMETERS_DIGEST"),
            (self.resource_envelope_digest, "POLICY_RESOURCE_ENVELOPE_DIGEST"),
            (self.concurrency_scope_digest, "POLICY_CONCURRENCY_SCOPE_DIGEST"),
            (self.effect_ceiling_digest, "POLICY_EFFECT_CEILING_DIGEST"),
        ):
            _sha256(value, name)
        if type(self.policy_current) is not bool:
            raise ValueError("POLICY_CURRENT_MUST_BE_BOOL")
        if self.execution_authorized is not False:
            raise ValueError("PRE_ATTEMPT_POLICY_MUST_NOT_AUTHORIZE_EXECUTION")
        if self.provider_effect_authorized is not False:
            raise ValueError("PRE_ATTEMPT_POLICY_MUST_NOT_AUTHORIZE_PROVIDER_EFFECT")

    @property
    def policy_digest(self) -> str:
        self.validate()
        return _sha({"domain": POLICY_SCHEMA, "policy": asdict(self)})


class PreAttemptOwnerResolver(ProposalOwnerResolver, Protocol):
    """Owner-controlled truth required beyond proposal currentness."""

    def resolve_pre_attempt_policy(
        self, *, proposal_id: str, domain_id: str, action_kind: str
    ) -> PreAttemptPolicyState | None: ...

    def concurrent_live_attempt_exists(
        self, *, proposal_id: str, concurrency_scope_digest: str
    ) -> bool | None: ...


@dataclass(frozen=True)
class PreAttemptAdmissionReceipt:
    schema_version: str
    disposition: str
    reason_code: str
    proposal_id: str
    proposal_basis_digest: str
    pre_attempt_id: str | None
    policy_generation: str | None
    policy_digest: str | None
    expected_route_fingerprint: str | None
    expected_observer_identity: str | None
    concurrency_scope_digest: str | None
    minimum_invalidated_cone: tuple[str, ...]
    proposal_current: bool
    policy_current: bool
    authority_scope_matches: bool
    action_matches_proposal: bool
    resource_envelope_matches: bool
    concurrent_live_attempt_conflict: bool | None
    revalidation_required_at_effect_boundary: bool = True
    execution_authorized: bool = False
    execution_lease_minted: bool = False
    provider_effect_authorized: bool = False
    provider_effect_started: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False
    merge_deploy_spend_public_financial_human_effect: bool = False

    def validate_claim_ceiling(self) -> None:
        if self.revalidation_required_at_effect_boundary is not True:
            raise ValueError("EFFECT_BOUNDARY_REVALIDATION_REQUIRED")
        forbidden = (
            self.execution_authorized,
            self.execution_lease_minted,
            self.provider_effect_authorized,
            self.provider_effect_started,
            self.semantic_k27_authority,
            self.native_private_transformer_kv_accessed,
            self.gate10_promoted,
            self.merge_deploy_spend_public_financial_human_effect,
        )
        if any(value is not False for value in forbidden):
            raise ValueError("PRE_ATTEMPT_RECEIPT_CANNOT_CARRY_EFFECT_AUTHORITY")

    @property
    def receipt_digest(self) -> str:
        self.validate_claim_ceiling()
        return _sha({"domain": RECEIPT_SCHEMA, "receipt": asdict(self)})

    def to_dict(self) -> dict[str, Any]:
        body = asdict(self)
        body["minimum_invalidated_cone"] = list(self.minimum_invalidated_cone)
        body["receipt_digest"] = self.receipt_digest
        return body


def _hold(
    *,
    capsule: ProposalCapsule,
    reason_code: str,
    cone: tuple[str, ...],
    policy: PreAttemptPolicyState | None = None,
    proposal_current: bool = False,
    policy_current: bool = False,
    authority_scope_matches: bool = False,
    action_matches_proposal: bool = False,
    resource_envelope_matches: bool = False,
    concurrent_live_attempt_conflict: bool | None = None,
) -> PreAttemptAdmissionReceipt:
    receipt = PreAttemptAdmissionReceipt(
        schema_version=RECEIPT_SCHEMA,
        disposition=f"HOLD_{reason_code}",
        reason_code=reason_code,
        proposal_id=capsule.proposal_id,
        proposal_basis_digest=capsule.proposal_basis_digest,
        pre_attempt_id=None,
        policy_generation=policy.policy_generation if policy else None,
        policy_digest=policy.policy_digest if policy else None,
        expected_route_fingerprint=policy.expected_route_fingerprint if policy else None,
        expected_observer_identity=policy.expected_observer_identity if policy else None,
        concurrency_scope_digest=policy.concurrency_scope_digest if policy else None,
        minimum_invalidated_cone=cone,
        proposal_current=proposal_current,
        policy_current=policy_current,
        authority_scope_matches=authority_scope_matches,
        action_matches_proposal=action_matches_proposal,
        resource_envelope_matches=resource_envelope_matches,
        concurrent_live_attempt_conflict=concurrent_live_attempt_conflict,
    )
    receipt.validate_claim_ceiling()
    return receipt


def admit_pre_attempt(
    *, capsule: ProposalCapsule, owner_resolver: PreAttemptOwnerResolver | None
) -> PreAttemptAdmissionReceipt:
    """Admit one semantic pre-attempt envelope from owner-resolved current state.

    No caller-supplied policy/currentness/route/observer/concurrency booleans are accepted.
    The proposal producer identity is deliberately absent from pre_attempt_id: identical
    content-addressed proposal bases must collapse to the same semantic envelope.
    """

    capsule.validate_integrity()
    currentness = revalidate_proposal_capsule(capsule=capsule, owner_resolver=owner_resolver)
    if currentness.state != "CURRENT_NONEXECUTABLE":
        return _hold(
            capsule=capsule,
            reason_code="PROPOSAL_NOT_CURRENT",
            cone=("proposal_currentness",),
        )
    if owner_resolver is None:
        return _hold(
            capsule=capsule,
            reason_code="OWNER_RESOLVER_UNAVAILABLE",
            cone=("pre_attempt_policy", "concurrency"),
            proposal_current=True,
        )

    b = capsule.basis
    try:
        policy = owner_resolver.resolve_pre_attempt_policy(
            proposal_id=capsule.proposal_id,
            domain_id=b.domain_id,
            action_kind=b.action_kind,
        )
    except Exception:
        return _hold(
            capsule=capsule,
            reason_code="POLICY_RESOLVER_ERROR",
            cone=("pre_attempt_policy",),
            proposal_current=True,
        )
    if policy is None:
        return _hold(
            capsule=capsule,
            reason_code="POLICY_UNAVAILABLE_OR_UNKNOWN",
            cone=("pre_attempt_policy",),
            proposal_current=True,
        )
    try:
        policy.validate()
    except ValueError:
        return _hold(
            capsule=capsule,
            reason_code="POLICY_INVALID",
            cone=("pre_attempt_policy",),
            policy=policy,
            proposal_current=True,
        )

    if policy.proposal_id != capsule.proposal_id:
        return _hold(
            capsule=capsule,
            reason_code="POLICY_PROPOSAL_MISMATCH",
            cone=("pre_attempt_policy",),
            policy=policy,
            proposal_current=True,
            policy_current=policy.policy_current,
        )
    if not policy.policy_current:
        return _hold(
            capsule=capsule,
            reason_code="POLICY_NOT_CURRENT",
            cone=("pre_attempt_policy",),
            policy=policy,
            proposal_current=True,
        )
    if policy.domain_id != b.domain_id or policy.action_kind != b.action_kind:
        return _hold(
            capsule=capsule,
            reason_code="POLICY_DOMAIN_OR_ACTION_MISMATCH",
            cone=("pre_attempt_policy",),
            policy=policy,
            proposal_current=True,
            policy_current=True,
        )

    authority_match = policy.authority_scope == b.authority_scope
    action_match = policy.action_parameters_digest == b.action_parameters_digest
    resource_match = policy.resource_envelope_digest == b.resource_envelope_digest
    if not authority_match:
        return _hold(
            capsule=capsule,
            reason_code="AUTHORITY_SCOPE_MISMATCH",
            cone=("authority_scope",),
            policy=policy,
            proposal_current=True,
            policy_current=True,
        )
    if not action_match:
        return _hold(
            capsule=capsule,
            reason_code="ACTION_PARAMETERS_MISMATCH",
            cone=("action_parameters",),
            policy=policy,
            proposal_current=True,
            policy_current=True,
            authority_scope_matches=True,
        )
    if not resource_match:
        return _hold(
            capsule=capsule,
            reason_code="RESOURCE_ENVELOPE_MISMATCH",
            cone=("resource_envelope",),
            policy=policy,
            proposal_current=True,
            policy_current=True,
            authority_scope_matches=True,
            action_matches_proposal=True,
        )

    try:
        conflict = owner_resolver.concurrent_live_attempt_exists(
            proposal_id=capsule.proposal_id,
            concurrency_scope_digest=policy.concurrency_scope_digest,
        )
    except Exception:
        return _hold(
            capsule=capsule,
            reason_code="CONCURRENCY_RESOLVER_ERROR",
            cone=("concurrency",),
            policy=policy,
            proposal_current=True,
            policy_current=True,
            authority_scope_matches=True,
            action_matches_proposal=True,
            resource_envelope_matches=True,
        )
    if conflict is not False:
        return _hold(
            capsule=capsule,
            reason_code=("CONCURRENT_LIVE_ATTEMPT" if conflict is True else "CONCURRENCY_UNKNOWN"),
            cone=("concurrency",),
            policy=policy,
            proposal_current=True,
            policy_current=True,
            authority_scope_matches=True,
            action_matches_proposal=True,
            resource_envelope_matches=True,
            concurrent_live_attempt_conflict=conflict,
        )

    identity_payload = {
        "proposal_id": capsule.proposal_id,
        "proposal_basis_digest": capsule.proposal_basis_digest,
        "policy_generation": policy.policy_generation,
        "policy_digest": policy.policy_digest,
        "authority_scope": policy.authority_scope,
        "expected_route_fingerprint": policy.expected_route_fingerprint,
        "expected_observer_identity": policy.expected_observer_identity,
        "action_parameters_digest": policy.action_parameters_digest,
        "resource_envelope_digest": policy.resource_envelope_digest,
        "concurrency_scope_digest": policy.concurrency_scope_digest,
        "effect_ceiling_digest": policy.effect_ceiling_digest,
    }
    receipt = PreAttemptAdmissionReceipt(
        schema_version=RECEIPT_SCHEMA,
        disposition=ELIGIBLE,
        reason_code="ALL_OWNER_RESOLVED_PRE_ATTEMPT_GATES_SATISFIED",
        proposal_id=capsule.proposal_id,
        proposal_basis_digest=capsule.proposal_basis_digest,
        pre_attempt_id=_sha({"domain": "AURA-PRE-ATTEMPT-ID-v1", "basis": identity_payload}),
        policy_generation=policy.policy_generation,
        policy_digest=policy.policy_digest,
        expected_route_fingerprint=policy.expected_route_fingerprint,
        expected_observer_identity=policy.expected_observer_identity,
        concurrency_scope_digest=policy.concurrency_scope_digest,
        minimum_invalidated_cone=(),
        proposal_current=True,
        policy_current=True,
        authority_scope_matches=True,
        action_matches_proposal=True,
        resource_envelope_matches=True,
        concurrent_live_attempt_conflict=False,
    )
    receipt.validate_claim_ceiling()
    return receipt
