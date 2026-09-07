from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
import hashlib, hmac, json
from typing import Mapping, Sequence

from tools.arena.attenuated_stable_operation_delegation import (
    StableOperation, DelegationHop, DomainAdmission, AttemptContext, Decision, Disposition, decide,
)

SCHEMA = 'AURA-O19-AUTHENTICATED-ATTENUATED-DELEGATION-v1'
D0 = 'D0_NONPROMOTING'


def _canon(x) -> bytes:
    def default(v):
        if isinstance(v, frozenset): return sorted(v)
        if hasattr(v, '__dict__'): return v.__dict__
        raise TypeError(type(v).__name__)
    return json.dumps(x, sort_keys=True, separators=(',', ':'), default=default).encode()

def root(x) -> str: return sha256(_canon(x)).hexdigest()
def mac(key: bytes, x) -> str: return hmac.new(key, _canon(x), hashlib.sha256).hexdigest()
def _ok_mac(key: bytes, x, sig: str) -> bool:
    return isinstance(sig, str) and hmac.compare_digest(mac(key, x), sig)

@dataclass(frozen=True)
class DelegationGrant:
    operation_root: str
    issuer: str
    subject: str
    scope: frozenset[str]
    budget: int
    generation: int
    parent_grant_root: str | None
    issued_at: int
    expires_at: int
    authority_ceiling: str
    signature: str
    @property
    def unsigned(self):
        d = asdict(self); d.pop('signature'); return d
    @property
    def grant_root(self): return root({'schema': SCHEMA, 'kind': 'grant', **self.unsigned, 'signature': self.signature})

@dataclass(frozen=True)
class GrantCurrentnessReceipt:
    grant_root: str
    subject: str
    generation: int
    currentness_root: str
    observer: str
    issued_at: int
    expires_at: int
    authority_ceiling: str
    signature: str
    @property
    def unsigned(self):
        d = asdict(self); d.pop('signature'); return d
    @property
    def receipt_root(self): return root({'schema': SCHEMA, 'kind': 'grant-currentness', **self.unsigned, 'signature': self.signature})

@dataclass(frozen=True)
class OwnerAdmissionReceipt:
    domain: str
    operation_root: str
    admission_root: str
    allowed_scope: frozenset[str]
    max_budget: int
    generation: int
    source_incarnation_root: str
    owner: str
    verifier: str
    issued_at: int
    expires_at: int
    authority_ceiling: str
    owner_signature: str
    verifier_signature: str
    @property
    def unsigned(self):
        d = asdict(self); d.pop('owner_signature'); d.pop('verifier_signature'); return d
    @property
    def receipt_root(self): return root({'schema': SCHEMA, 'kind': 'owner-admission', **self.unsigned, 'owner_signature': self.owner_signature, 'verifier_signature': self.verifier_signature})

@dataclass(frozen=True)
class AttemptUseReceipt:
    operation_root: str
    actor: str
    workcell_root: str
    workcell_generation: int
    lease_root: str
    source_incarnation_root: str
    currentness_root: str
    verifier: str
    issued_at: int
    expires_at: int
    authority_ceiling: str
    signature: str
    @property
    def unsigned(self):
        d = asdict(self); d.pop('signature'); return d
    @property
    def receipt_root(self): return root({'schema': SCHEMA, 'kind': 'attempt-use', **self.unsigned, 'signature': self.signature})

@dataclass(frozen=True)
class AuthenticatedDelegationDecision:
    parent_decision: Decision
    grant_roots: tuple[str, ...]
    grant_currentness_roots: tuple[str, ...]
    owner_admission_receipt_root: str
    attempt_use_receipt_root: str
    authenticated: bool
    authority_ceiling: str = D0
    effect_authority: bool = False
    training_authority: bool = False
    checkpoint_authority: bool = False
    gate10: bool = False
    @property
    def result_root(self):
        return root({'schema': SCHEMA, 'parent_decision': self.parent_decision, 'grant_roots': self.grant_roots,
                     'grant_currentness_roots': self.grant_currentness_roots,
                     'owner_admission_receipt_root': self.owner_admission_receipt_root,
                     'attempt_use_receipt_root': self.attempt_use_receipt_root,
                     'authenticated': self.authenticated, 'authority_ceiling': self.authority_ceiling,
                     'effect_authority': self.effect_authority, 'training_authority': self.training_authority,
                     'checkpoint_authority': self.checkpoint_authority, 'gate10': self.gate10})

class AuthenticationError(ValueError): pass


def _check_time(issued: int, expires: int, now: int):
    if not (isinstance(issued, int) and isinstance(expires, int) and issued <= now <= expires):
        raise AuthenticationError('EVIDENCE_NOT_CURRENT')

def _key(keys: Mapping[str, bytes], principal: str) -> bytes:
    k = keys.get(principal)
    if not isinstance(k, (bytes, bytearray)) or not k:
        raise AuthenticationError('UNTRUSTED_PRINCIPAL')
    return bytes(k)


def authenticate_and_decide(
    operation: StableOperation,
    grants: Sequence[DelegationGrant],
    currentness_receipts: Sequence[GrantCurrentnessReceipt],
    admission: OwnerAdmissionReceipt,
    attempt_use: AttemptUseReceipt,
    requested_scope: frozenset[str],
    requested_budget: int,
    *,
    principal_keys: Mapping[str, bytes],
    currentness_verifier_keys: Mapping[str, bytes],
    admission_owner_keys: Mapping[str, bytes],
    admission_verifier_keys: Mapping[str, bytes],
    attempt_verifier_keys: Mapping[str, bytes],
    now: int,
) -> AuthenticatedDelegationDecision:
    op_root = operation.root()
    if not grants or len(grants) != len(currentness_receipts):
        raise AuthenticationError('DELEGATION_EVIDENCE_CARDINALITY')
    if not isinstance(requested_scope, frozenset) or not isinstance(requested_budget, int) or requested_budget < 0:
        raise AuthenticationError('REQUEST_MALFORMED')

    projected_hops: list[DelegationHop] = []
    grant_roots: list[str] = []
    current_roots: list[str] = []
    prior: DelegationGrant | None = None
    prior_root: str | None = None

    for grant, cur in zip(grants, currentness_receipts):
        _check_time(grant.issued_at, grant.expires_at, now)
        if grant.operation_root != op_root or grant.authority_ceiling != D0:
            raise AuthenticationError('GRANT_OPERATION_OR_AUTHORITY')
        if not grant.issuer or not grant.subject or grant.issuer == grant.subject:
            raise AuthenticationError('GRANT_PRINCIPAL_INVALID')
        if not grant.scope or grant.budget < 0 or grant.generation < 1:
            raise AuthenticationError('GRANT_SHAPE_INVALID')
        if not _ok_mac(_key(principal_keys, grant.issuer), grant.unsigned, grant.signature):
            raise AuthenticationError('GRANT_NOT_AUTHENTICATED')
        if prior is None:
            if grant.parent_grant_root is not None:
                raise AuthenticationError('ROOT_GRANT_HAS_PARENT')
        else:
            if grant.parent_grant_root != prior_root or grant.issuer != prior.subject:
                raise AuthenticationError('GRANT_PARENT_LINK_INVALID')
            if not grant.scope.issubset(prior.scope) or grant.budget > prior.budget:
                raise AuthenticationError('NON_ATTENUATING_DELEGATION')
            if grant.generation <= prior.generation:
                raise AuthenticationError('GRANT_GENERATION_NOT_MONOTONE')

        _check_time(cur.issued_at, cur.expires_at, now)
        if cur.authority_ceiling != D0 or cur.grant_root != grant.grant_root or cur.subject != grant.subject or cur.generation != grant.generation:
            raise AuthenticationError('GRANT_CURRENTNESS_BINDING')
        if not cur.currentness_root or cur.observer in {grant.issuer, grant.subject}:
            raise AuthenticationError('GRANT_CURRENTNESS_OBSERVER_INVALID')
        if not _ok_mac(_key(currentness_verifier_keys, cur.observer), cur.unsigned, cur.signature):
            raise AuthenticationError('GRANT_CURRENTNESS_NOT_AUTHENTICATED')

        projected_hops.append(DelegationHop(grant.subject, grant.scope, grant.budget, grant.generation, True))
        grant_roots.append(grant.grant_root); current_roots.append(cur.receipt_root)
        prior, prior_root = grant, grant.grant_root

    _check_time(admission.issued_at, admission.expires_at, now)
    if admission.authority_ceiling != D0 or admission.domain != operation.domain or admission.operation_root != op_root:
        raise AuthenticationError('ADMISSION_OPERATION_OR_AUTHORITY')
    if admission.source_incarnation_root != operation.source_incarnation_root:
        raise AuthenticationError('SOURCE_INCARNATION_MOVED')
    if not admission.allowed_scope or admission.max_budget < 0 or admission.generation < 1 or admission.owner == admission.verifier:
        raise AuthenticationError('ADMISSION_SHAPE_INVALID')
    if not _ok_mac(_key(admission_owner_keys, admission.owner), admission.unsigned, admission.owner_signature):
        raise AuthenticationError('ADMISSION_OWNER_NOT_AUTHENTICATED')
    if not _ok_mac(_key(admission_verifier_keys, admission.verifier), admission.unsigned, admission.verifier_signature):
        raise AuthenticationError('ADMISSION_VERIFIER_NOT_AUTHENTICATED')

    _check_time(attempt_use.issued_at, attempt_use.expires_at, now)
    if attempt_use.authority_ceiling != D0 or attempt_use.operation_root != op_root or attempt_use.source_incarnation_root != operation.source_incarnation_root:
        raise AuthenticationError('ATTEMPT_OPERATION_OR_SOURCE')
    if not attempt_use.actor or not attempt_use.workcell_root or not attempt_use.lease_root or attempt_use.workcell_generation < 1 or not attempt_use.currentness_root:
        raise AuthenticationError('ATTEMPT_USE_SHAPE_INVALID')
    if not _ok_mac(_key(attempt_verifier_keys, attempt_use.verifier), attempt_use.unsigned, attempt_use.signature):
        raise AuthenticationError('ATTEMPT_USE_NOT_AUTHENTICATED')

    projected_admission = DomainAdmission(operation.domain, op_root, admission.admission_root, admission.allowed_scope,
                                          admission.max_budget, admission.generation, True, True)
    projected_context = AttemptContext(attempt_use.actor, attempt_use.workcell_root, attempt_use.workcell_generation, True,
                                       attempt_use.lease_root, True, attempt_use.source_incarnation_root,
                                       requested_scope, requested_budget)
    parent = decide(operation, projected_hops, projected_admission, projected_context)
    if parent.effect_authority or parent.training_authority or parent.checkpoint_authority or parent.gate10:
        raise AuthenticationError('PARENT_AUTHORITY_ESCALATION')
    return AuthenticatedDelegationDecision(parent, tuple(grant_roots), tuple(current_roots), admission.receipt_root,
                                           attempt_use.receipt_root, parent.disposition == Disposition.ADMIT_D0)


def sign_grant(unsigned: dict, key: bytes) -> DelegationGrant:
    return DelegationGrant(**unsigned, signature=mac(key, unsigned))
def sign_currentness(unsigned: dict, key: bytes) -> GrantCurrentnessReceipt:
    return GrantCurrentnessReceipt(**unsigned, signature=mac(key, unsigned))
def sign_admission(unsigned: dict, owner_key: bytes, verifier_key: bytes) -> OwnerAdmissionReceipt:
    return OwnerAdmissionReceipt(**unsigned, owner_signature=mac(owner_key, unsigned), verifier_signature=mac(verifier_key, unsigned))
def sign_attempt_use(unsigned: dict, key: bytes) -> AttemptUseReceipt:
    return AttemptUseReceipt(**unsigned, signature=mac(key, unsigned))
