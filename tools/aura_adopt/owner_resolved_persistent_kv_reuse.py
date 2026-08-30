"""PCK2: owner-resolved persistent transformer-KV reuse admission (D0 only).

Coordinate/K27 may nominate reuse but is never runtime evidence. This module
does not access cache/model/provider/storage/network resources and grants no
execution, provider, monetary, or promotion authority. HMAC and the caller-
supplied trust registries are deterministic local trust-boundary models, not
production key management or proof that a trust root is canonical.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import hmac
import json
import re
from typing import Any, Mapping, Sequence
_SHA = re.compile('^[0-9a-f]{64}$')
_TOK = re.compile('^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,255}$')
PROJECTION_SCHEMA = 'PersistentKVReuseProjectionV1'

class KVAdmissionError(ValueError):

    def __init__(self, code: str, detail: str=''):
        super().__init__(f'{code}:{detail}' if detail else code)
        self.code, self.detail = (code, detail)

class ResponsibilityClass(str, Enum):
    TRANSFORMER_KV_CACHE = 'TRANSFORMER_KV_CACHE'
    COORDINATE_MEMORY = 'COORDINATE_MEMORY'
    SEMANTIC_RESPONSE_CACHE = 'SEMANTIC_RESPONSE_CACHE'

class ResolverDisposition(str, Enum):
    OWNER_RESOLVED_CURRENT = 'OWNER_RESOLVED_CURRENT'
    OWNER_RESOLVED_HISTORICAL = 'OWNER_RESOLVED_HISTORICAL'
    OWNER_UNRESOLVED = 'OWNER_UNRESOLVED'

class ObservationDisposition(str, Enum):
    PATH_OBSERVED_CURRENT = 'PATH_OBSERVED_CURRENT'
    PATH_OBSERVED_HISTORICAL = 'PATH_OBSERVED_HISTORICAL'
    PATH_UNOBSERVED = 'PATH_UNOBSERVED'

def _canon(v: Any) -> bytes:
    try:
        return json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()
    except (TypeError, ValueError) as e:
        raise KVAdmissionError('NONCANONICAL_KV_STATE') from e

def _dig(domain: str, v: Any) -> str:
    return hashlib.sha256(domain.encode() + b'\x00' + _canon(v)).hexdigest()

def _text(v: Any, code: str) -> str:
    if not isinstance(v, str) or not _TOK.fullmatch(v.strip()):
        raise KVAdmissionError(code)
    return v.strip()

def _sha(v: Any, code: str) -> str:
    if not isinstance(v, str) or not _SHA.fullmatch(v.strip().lower()):
        raise KVAdmissionError(code)
    return v.strip().lower()

def _nn(v: Any, code: str) -> int:
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise KVAdmissionError(code)
    return v

@dataclass(frozen=True)
class PersistentKVReuseTargetV1:
    coordinate_ref: str
    k27_cell: int
    model_revision: str
    tokenizer_digest: str
    chat_template_digest: str
    system_tool_prefix_digest: str
    prefix_token_digest: str
    cache_abi: str
    backend_cache_abi: str
    principal_namespace_digest: str
    workload_digest: str
    host_epoch: str
    route_epoch: str
    source_generation: str
    source_currentness_ref: str
    responsibility: ResponsibilityClass = ResponsibilityClass.TRANSFORMER_KV_CACHE
    schema: str = 'PersistentKVReuseTargetV1'

    def __post_init__(self):
        if self.schema != 'PersistentKVReuseTargetV1':
            raise KVAdmissionError('KV_TARGET_SCHEMA_MISMATCH')
        object.__setattr__(self, 'coordinate_ref', _text(self.coordinate_ref, 'COORDINATE_REF_INVALID'))
        if isinstance(self.k27_cell, bool) or not isinstance(self.k27_cell, int) or (not 0 <= self.k27_cell < 27):
            raise KVAdmissionError('K27_CELL_INVALID')
        for f in ('model_revision', 'cache_abi', 'backend_cache_abi', 'host_epoch', 'route_epoch', 'source_generation', 'source_currentness_ref'):
            object.__setattr__(self, f, _text(getattr(self, f), f'{f.upper()}_INVALID'))
        for f in ('tokenizer_digest', 'chat_template_digest', 'system_tool_prefix_digest', 'prefix_token_digest', 'principal_namespace_digest', 'workload_digest'):
            object.__setattr__(self, f, _sha(getattr(self, f), f'{f.upper()}_INVALID'))
        if not isinstance(self.responsibility, ResponsibilityClass):
            raise KVAdmissionError('RESPONSIBILITY_CLASS_INVALID')

    @property
    def target_digest(self):
        v = asdict(self)
        v['responsibility'] = self.responsibility.value
        return _dig('AURA_PCK2_TARGET_V1', v)

@dataclass(frozen=True)
class PersistentKVPathEvidenceV1:
    evidence_ref: str
    evidence_generation: str
    evidence_currentness_ref: str
    target_digest: str
    responsibility: ResponsibilityClass
    model_revision: str
    tokenizer_digest: str
    chat_template_digest: str
    system_tool_prefix_digest: str
    prefix_token_digest: str
    cache_abi: str
    backend_cache_abi: str
    principal_namespace_digest: str
    workload_digest: str
    host_epoch: str
    route_epoch: str
    persistent_restore_observed: bool
    cache_read_observed: bool
    cache_hit_tokens: int
    prefill_saved_us: int
    transfer_us: int
    restore_us: int
    queue_penalty_us: int
    memory_penalty_us: int
    security_isolation_us: int
    invalidation_penalty_us: int
    schema: str = 'PersistentKVPathEvidenceV1'

    def __post_init__(self):
        if self.schema != 'PersistentKVPathEvidenceV1':
            raise KVAdmissionError('KV_PATH_SCHEMA_MISMATCH')
        for f in ('evidence_ref', 'evidence_generation', 'evidence_currentness_ref', 'model_revision', 'cache_abi', 'backend_cache_abi', 'host_epoch', 'route_epoch'):
            object.__setattr__(self, f, _text(getattr(self, f), f'{f.upper()}_INVALID'))
        for f in ('target_digest', 'tokenizer_digest', 'chat_template_digest', 'system_tool_prefix_digest', 'prefix_token_digest', 'principal_namespace_digest', 'workload_digest'):
            object.__setattr__(self, f, _sha(getattr(self, f), f'{f.upper()}_INVALID'))
        if not isinstance(self.responsibility, ResponsibilityClass):
            raise KVAdmissionError('PATH_RESPONSIBILITY_INVALID')
        for f in ('persistent_restore_observed', 'cache_read_observed'):
            if type(getattr(self, f)) is not bool:
                raise KVAdmissionError(f'{f.upper()}_BOOL_REQUIRED')
        for f in ('cache_hit_tokens', 'prefill_saved_us', 'transfer_us', 'restore_us', 'queue_penalty_us', 'memory_penalty_us', 'security_isolation_us', 'invalidation_penalty_us'):
            object.__setattr__(self, f, _nn(getattr(self, f), f'{f.upper()}_INVALID'))

    @property
    def path_digest(self):
        v = asdict(self)
        v['responsibility'] = self.responsibility.value
        return _dig('AURA_PCK2_PATH_V1', v)

    @property
    def net_reuse_us(self):
        return self.prefill_saved_us - sum((self.transfer_us, self.restore_us, self.queue_penalty_us, self.memory_penalty_us, self.security_isolation_us, self.invalidation_penalty_us))

def resolved_projection_payload_digest(target: PersistentKVReuseTargetV1, path: PersistentKVPathEvidenceV1) -> str:
    if not isinstance(target, PersistentKVReuseTargetV1) or not isinstance(path, PersistentKVPathEvidenceV1):
        raise KVAdmissionError('KV_TARGET_AND_PATH_REQUIRED')
    return _dig('AURA_PCK2_RESOLVED_PROJECTION_V1', {'target_digest': target.target_digest, 'path_digest': path.path_digest})

@dataclass(frozen=True)
class KVReuseProjectionClaimV1:
    owner_ref: str
    owner_generation: str
    owner_head: str
    owner_blob: str
    owner_abi: str
    subject_ref: str
    subject_generation: str
    source_ref: str
    source_generation: str
    source_currentness_ref: str
    projection_schema: str
    projection_payload_digest: str
    consequence_ceiling: str = 'TRANSFORMER_KV_REUSE_EVIDENCE_ONLY'
    schema: str = 'KVReuseProjectionClaimV1'

    def __post_init__(self):
        if self.schema != 'KVReuseProjectionClaimV1':
            raise KVAdmissionError('PROJECTION_CLAIM_SCHEMA_MISMATCH')
        for f in ('owner_ref', 'owner_generation', 'owner_abi', 'subject_ref', 'subject_generation', 'source_ref', 'source_generation', 'source_currentness_ref', 'projection_schema', 'consequence_ceiling'):
            object.__setattr__(self, f, _text(getattr(self, f), f'{f.upper()}_INVALID'))
        object.__setattr__(self, 'owner_head', _sha(self.owner_head, 'OWNER_HEAD_INVALID'))
        object.__setattr__(self, 'owner_blob', _sha(self.owner_blob, 'OWNER_BLOB_INVALID'))
        object.__setattr__(self, 'projection_payload_digest', _sha(self.projection_payload_digest, 'PROJECTION_PAYLOAD_DIGEST_INVALID'))
        if self.projection_schema != PROJECTION_SCHEMA:
            raise KVAdmissionError('PROJECTION_SCHEMA_UNSUPPORTED')
        if self.consequence_ceiling != 'TRANSFORMER_KV_REUSE_EVIDENCE_ONLY':
            raise KVAdmissionError('PROJECTION_CONSEQUENCE_CEILING_WIDENING')

    @property
    def claim_digest(self):
        return _dig('AURA_PCK2_CLAIM_V1', asdict(self))

@dataclass(frozen=True)
class OwnerResolverProofV1:
    projection_claim_digest: str
    owner_ref: str
    owner_generation: str
    owner_head: str
    owner_blob: str
    owner_abi: str
    resolver_ref: str
    resolver_generation: str
    resolver_currentness_ref: str
    source_ref: str
    source_generation: str
    source_currentness_ref: str
    owner_recognized_projection_digest: str
    disposition: ResolverDisposition
    revoked: bool
    supersedes_proof_digest: str | None
    resolver_signature: str
    schema: str = 'OwnerResolverProofV1'

    def __post_init__(self):
        if self.schema != 'OwnerResolverProofV1':
            raise KVAdmissionError('RESOLVER_PROOF_SCHEMA_MISMATCH')
        for f in ('owner_ref', 'owner_generation', 'owner_abi', 'resolver_ref', 'resolver_generation', 'resolver_currentness_ref', 'source_ref', 'source_generation', 'source_currentness_ref'):
            object.__setattr__(self, f, _text(getattr(self, f), f'{f.upper()}_INVALID'))
        for f in ('projection_claim_digest', 'owner_head', 'owner_blob', 'owner_recognized_projection_digest', 'resolver_signature'):
            object.__setattr__(self, f, _sha(getattr(self, f), f'{f.upper()}_INVALID'))
        if self.supersedes_proof_digest is not None:
            object.__setattr__(self, 'supersedes_proof_digest', _sha(self.supersedes_proof_digest, 'SUPERSEDES_PROOF_DIGEST_INVALID'))
        if not isinstance(self.disposition, ResolverDisposition):
            raise KVAdmissionError('RESOLVER_DISPOSITION_INVALID')
        if type(self.revoked) is not bool:
            raise KVAdmissionError('RESOLVER_REVOKED_BOOL_REQUIRED')

    def signing_payload(self):
        v = asdict(self)
        v['disposition'] = self.disposition.value
        v.pop('resolver_signature')
        return v

    @property
    def proof_digest(self):
        v = asdict(self)
        v['disposition'] = self.disposition.value
        return _dig('AURA_PCK2_RESOLVER_PROOF_V1', v)

@dataclass(frozen=True)
class KVPathObservationProofV1:
    path_digest: str
    target_digest: str
    evidence_ref: str
    observer_ref: str
    observer_generation: str
    observer_currentness_ref: str
    source_ref: str
    source_generation: str
    source_currentness_ref: str
    disposition: ObservationDisposition
    revoked: bool
    supersedes_proof_digest: str | None
    observer_signature: str
    schema: str = 'KVPathObservationProofV1'

    def __post_init__(self):
        if self.schema != 'KVPathObservationProofV1':
            raise KVAdmissionError('OBSERVATION_PROOF_SCHEMA_MISMATCH')
        for f in ('evidence_ref', 'observer_ref', 'observer_generation', 'observer_currentness_ref', 'source_ref', 'source_generation', 'source_currentness_ref'):
            object.__setattr__(self, f, _text(getattr(self, f), f'{f.upper()}_INVALID'))
        for f in ('path_digest', 'target_digest', 'observer_signature'):
            object.__setattr__(self, f, _sha(getattr(self, f), f'{f.upper()}_INVALID'))
        if self.supersedes_proof_digest is not None:
            object.__setattr__(self, 'supersedes_proof_digest', _sha(self.supersedes_proof_digest, 'OBSERVATION_SUPERSEDES_DIGEST_INVALID'))
        if not isinstance(self.disposition, ObservationDisposition):
            raise KVAdmissionError('OBSERVATION_DISPOSITION_INVALID')
        if type(self.revoked) is not bool:
            raise KVAdmissionError('OBSERVATION_REVOKED_BOOL_REQUIRED')

    def signing_payload(self):
        v = asdict(self)
        v['disposition'] = self.disposition.value
        v.pop('observer_signature')
        return v

    @property
    def proof_digest(self):
        v = asdict(self)
        v['disposition'] = self.disposition.value
        return _dig('AURA_PCK2_PATH_OBSERVATION_PROOF_V1', v)

def _sign(payload: Mapping[str, Any], key: bytes) -> str:
    if not isinstance(key, bytes) or not key:
        raise KVAdmissionError('RESOLVER_KEY_REQUIRED')
    return hmac.new(key, _canon(dict(payload)), hashlib.sha256).hexdigest()

def build_resolver_proof(*, claim: KVReuseProjectionClaimV1, resolver_ref: str, resolver_generation: str, resolver_currentness_ref: str, owner_recognized_projection_digest: str, disposition: ResolverDisposition, key: bytes, revoked: bool=False, supersedes_proof_digest: str | None=None) -> OwnerResolverProofV1:
    if not isinstance(claim, KVReuseProjectionClaimV1):
        raise KVAdmissionError('PROJECTION_CLAIM_REQUIRED')
    if not isinstance(disposition, ResolverDisposition):
        raise KVAdmissionError('RESOLVER_DISPOSITION_INVALID')
    if type(revoked) is not bool:
        raise KVAdmissionError('RESOLVER_REVOKED_BOOL_REQUIRED')
    u = {'projection_claim_digest': claim.claim_digest, 'owner_ref': claim.owner_ref, 'owner_generation': claim.owner_generation, 'owner_head': claim.owner_head, 'owner_blob': claim.owner_blob, 'owner_abi': claim.owner_abi, 'resolver_ref': _text(resolver_ref, 'RESOLVER_REF_INVALID'), 'resolver_generation': _text(resolver_generation, 'RESOLVER_GENERATION_INVALID'), 'resolver_currentness_ref': _text(resolver_currentness_ref, 'RESOLVER_CURRENTNESS_REF_INVALID'), 'source_ref': claim.source_ref, 'source_generation': claim.source_generation, 'source_currentness_ref': claim.source_currentness_ref, 'owner_recognized_projection_digest': _sha(owner_recognized_projection_digest, 'OWNER_RECOGNIZED_PROJECTION_DIGEST_INVALID'), 'disposition': disposition.value, 'revoked': revoked, 'supersedes_proof_digest': supersedes_proof_digest, 'schema': 'OwnerResolverProofV1'}
    sig = _sign(u, key)
    return OwnerResolverProofV1(**{**u, 'disposition': disposition, 'resolver_signature': sig})

def build_observation_proof(*, path_evidence: PersistentKVPathEvidenceV1, target: PersistentKVReuseTargetV1, claim: KVReuseProjectionClaimV1, observer_ref: str, observer_generation: str, observer_currentness_ref: str, disposition: ObservationDisposition, key: bytes, revoked: bool=False, supersedes_proof_digest: str | None=None) -> KVPathObservationProofV1:
    if not isinstance(path_evidence, PersistentKVPathEvidenceV1):
        raise KVAdmissionError('KV_PATH_EVIDENCE_REQUIRED')
    if not isinstance(target, PersistentKVReuseTargetV1):
        raise KVAdmissionError('KV_TARGET_REQUIRED')
    if not isinstance(claim, KVReuseProjectionClaimV1):
        raise KVAdmissionError('PROJECTION_CLAIM_REQUIRED')
    if not isinstance(disposition, ObservationDisposition):
        raise KVAdmissionError('OBSERVATION_DISPOSITION_INVALID')
    if type(revoked) is not bool:
        raise KVAdmissionError('OBSERVATION_REVOKED_BOOL_REQUIRED')
    u = {'path_digest': path_evidence.path_digest, 'target_digest': target.target_digest, 'evidence_ref': path_evidence.evidence_ref, 'observer_ref': _text(observer_ref, 'OBSERVER_REF_INVALID'), 'observer_generation': _text(observer_generation, 'OBSERVER_GENERATION_INVALID'), 'observer_currentness_ref': _text(observer_currentness_ref, 'OBSERVER_CURRENTNESS_REF_INVALID'), 'source_ref': claim.source_ref, 'source_generation': claim.source_generation, 'source_currentness_ref': claim.source_currentness_ref, 'disposition': disposition.value, 'revoked': revoked, 'supersedes_proof_digest': supersedes_proof_digest, 'schema': 'KVPathObservationProofV1'}
    sig = _sign(u, key)
    return KVPathObservationProofV1(**{**u, 'disposition': disposition, 'observer_signature': sig})

def _trusted_state_tuple(state: Mapping[str, Any], ref: str, *, record_code: str, generation_code: str, currentness_code: str) -> tuple[str, str]:
    raw = state.get(ref)
    if not isinstance(raw, (tuple, list)) or isinstance(raw, (str, bytes)) or len(raw) != 2:
        raise KVAdmissionError(record_code)
    return (_text(raw[0], generation_code), _text(raw[1], currentness_code))

def _resolver_state_tuple(state: Mapping[str, Any], resolver_ref: str) -> tuple[str, str]:
    return _trusted_state_tuple(state, resolver_ref, record_code='RESOLVER_STATE_RECORD_INVALID', generation_code='RESOLVER_STATE_GENERATION_INVALID', currentness_code='RESOLVER_STATE_CURRENTNESS_INVALID')

def _observer_state_tuple(state: Mapping[str, Any], observer_ref: str) -> tuple[str, str]:
    return _trusted_state_tuple(state, observer_ref, record_code='OBSERVER_STATE_RECORD_INVALID', generation_code='OBSERVER_STATE_GENERATION_INVALID', currentness_code='OBSERVER_STATE_CURRENTNESS_INVALID')

def _source_state_tuple(state: Mapping[str, Any], source_ref: str) -> tuple[str, str]:
    return _trusted_state_tuple(state, source_ref, record_code='SOURCE_STATE_RECORD_INVALID', generation_code='SOURCE_STATE_GENERATION_INVALID', currentness_code='SOURCE_STATE_CURRENTNESS_INVALID')

def _current_proof_digest(proof_state: Mapping[str, Any], claim_digest: str) -> str:
    raw = proof_state.get(claim_digest)
    if raw is None:
        raise KVAdmissionError('RESOLVER_PROOF_NOT_REGISTERED')
    if not isinstance(raw, (tuple, list)) or isinstance(raw, (str, bytes)) or (not raw):
        raise KVAdmissionError('RESOLVER_PROOF_STATE_INVALID')
    digests = tuple((_sha(x, 'RESOLVER_PROOF_STATE_DIGEST_INVALID') for x in raw))
    if len(set(digests)) != len(digests):
        raise KVAdmissionError('RESOLVER_PROOF_STATE_DUPLICATE')
    if len(digests) != 1:
        raise KVAdmissionError('RESOLVER_PROOF_STATE_AMBIGUOUS')
    return digests[0]

def _current_observation_proof_digest(proof_state: Mapping[str, Any], path_digest: str) -> str:
    raw = proof_state.get(path_digest)
    if raw is None:
        raise KVAdmissionError('OBSERVATION_PROOF_NOT_REGISTERED')
    if not isinstance(raw, (tuple, list)) or isinstance(raw, (str, bytes)) or (not raw):
        raise KVAdmissionError('OBSERVATION_PROOF_STATE_INVALID')
    digests = tuple((_sha(x, 'OBSERVATION_PROOF_STATE_DIGEST_INVALID') for x in raw))
    if len(set(digests)) != len(digests):
        raise KVAdmissionError('OBSERVATION_PROOF_STATE_DUPLICATE')
    if len(digests) != 1:
        raise KVAdmissionError('OBSERVATION_PROOF_STATE_AMBIGUOUS')
    return digests[0]

def _verify_source_currentness(claim: KVReuseProjectionClaimV1, source_state: Mapping[str, Any]) -> None:
    if not isinstance(source_state, Mapping):
        raise KVAdmissionError('TRUSTED_SOURCE_STATE_REQUIRED')
    if claim.source_ref not in source_state:
        raise KVAdmissionError('SOURCE_UNTRUSTED')
    generation, currentness = _source_state_tuple(source_state, claim.source_ref)
    if claim.source_generation != generation:
        raise KVAdmissionError('SOURCE_GENERATION_STALE')
    if claim.source_currentness_ref != currentness:
        raise KVAdmissionError('SOURCE_CURRENTNESS_STALE')

def _verify_resolver(claim: KVReuseProjectionClaimV1, proof: OwnerResolverProofV1, keys: Mapping[str, Any], state: Mapping[str, Any], proof_state: Mapping[str, Any]):
    if not isinstance(claim, KVReuseProjectionClaimV1) or not isinstance(proof, OwnerResolverProofV1):
        raise KVAdmissionError('RESOLVER_CLAIM_AND_PROOF_REQUIRED')
    if not isinstance(keys, Mapping) or not isinstance(state, Mapping) or (not isinstance(proof_state, Mapping)):
        raise KVAdmissionError('TRUSTED_RESOLVER_STATE_REQUIRED')
    if proof.projection_claim_digest != claim.claim_digest:
        raise KVAdmissionError('RESOLVER_CLAIM_DIGEST_MISMATCH')
    for f in ('owner_ref', 'owner_generation', 'owner_head', 'owner_blob', 'owner_abi'):
        if getattr(proof, f) != getattr(claim, f):
            raise KVAdmissionError('RESOLVER_OWNER_BINDING_MISMATCH', f)
    for f in ('source_ref', 'source_generation', 'source_currentness_ref'):
        if getattr(proof, f) != getattr(claim, f):
            raise KVAdmissionError('RESOLVER_SOURCE_BINDING_MISMATCH', f)
    if proof.owner_recognized_projection_digest != claim.projection_payload_digest:
        raise KVAdmissionError('RESOLVER_RECOGNIZED_PROJECTION_MISMATCH')
    if proof.disposition is not ResolverDisposition.OWNER_RESOLVED_CURRENT:
        raise KVAdmissionError('RESOLVER_NOT_CURRENT')
    if proof.revoked:
        raise KVAdmissionError('RESOLVER_PROOF_REVOKED')
    if proof.resolver_ref not in keys or proof.resolver_ref not in state:
        raise KVAdmissionError('RESOLVER_UNTRUSTED')
    gen, cur = _resolver_state_tuple(state, proof.resolver_ref)
    if proof.resolver_generation != gen:
        raise KVAdmissionError('RESOLVER_GENERATION_STALE')
    if proof.resolver_currentness_ref != cur:
        raise KVAdmissionError('RESOLVER_CURRENTNESS_STALE')
    if not hmac.compare_digest(proof.resolver_signature, _sign(proof.signing_payload(), keys[proof.resolver_ref])):
        raise KVAdmissionError('RESOLVER_SIGNATURE_INVALID')
    current = _current_proof_digest(proof_state, claim.claim_digest)
    if proof.proof_digest != current:
        raise KVAdmissionError('RESOLVER_PROOF_SUPERSEDED_OR_REVOKED')

def _verify_observation(*, target: PersistentKVReuseTargetV1, path: PersistentKVPathEvidenceV1, claim: KVReuseProjectionClaimV1, resolver_proof: OwnerResolverProofV1, observation_proof: KVPathObservationProofV1, keys: Mapping[str, Any], state: Mapping[str, Any], proof_state: Mapping[str, Any], resolver_keys: Mapping[str, Any]) -> None:
    if not isinstance(observation_proof, KVPathObservationProofV1):
        raise KVAdmissionError('KV_PATH_OBSERVATION_PROOF_REQUIRED')
    if not isinstance(keys, Mapping) or not isinstance(state, Mapping) or (not isinstance(proof_state, Mapping)) or (not isinstance(resolver_keys, Mapping)):
        raise KVAdmissionError('TRUSTED_OBSERVER_STATE_REQUIRED')
    if observation_proof.observer_ref == resolver_proof.resolver_ref:
        raise KVAdmissionError('OBSERVER_RESOLVER_ROLE_COLLISION')
    if observation_proof.path_digest != path.path_digest:
        raise KVAdmissionError('OBSERVATION_PATH_DIGEST_MISMATCH')
    if observation_proof.target_digest != target.target_digest:
        raise KVAdmissionError('OBSERVATION_TARGET_DIGEST_MISMATCH')
    if observation_proof.evidence_ref != path.evidence_ref:
        raise KVAdmissionError('OBSERVATION_EVIDENCE_REF_MISMATCH')
    for field in ('source_ref', 'source_generation', 'source_currentness_ref'):
        if getattr(observation_proof, field) != getattr(claim, field):
            raise KVAdmissionError('OBSERVATION_SOURCE_BINDING_MISMATCH', field)
    if observation_proof.disposition is not ObservationDisposition.PATH_OBSERVED_CURRENT:
        raise KVAdmissionError('OBSERVATION_NOT_CURRENT')
    if observation_proof.revoked:
        raise KVAdmissionError('OBSERVATION_PROOF_REVOKED')
    if observation_proof.observer_ref not in keys or observation_proof.observer_ref not in state:
        raise KVAdmissionError('OBSERVER_UNTRUSTED')
    if resolver_proof.resolver_ref not in resolver_keys:
        raise KVAdmissionError('RESOLVER_UNTRUSTED')
    resolver_key = resolver_keys[resolver_proof.resolver_ref]
    observer_key = keys[observation_proof.observer_ref]
    if not isinstance(resolver_key, bytes) or not resolver_key:
        raise KVAdmissionError('RESOLVER_KEY_REQUIRED')
    if not isinstance(observer_key, bytes) or not observer_key:
        raise KVAdmissionError('OBSERVER_KEY_REQUIRED')
    if hmac.compare_digest(resolver_key, observer_key):
        raise KVAdmissionError('OBSERVER_RESOLVER_SIGNING_AUTHORITY_COLLISION')
    generation, currentness = _observer_state_tuple(state, observation_proof.observer_ref)
    if observation_proof.observer_generation != generation:
        raise KVAdmissionError('OBSERVER_GENERATION_STALE')
    if observation_proof.observer_currentness_ref != currentness:
        raise KVAdmissionError('OBSERVER_CURRENTNESS_STALE')
    if not hmac.compare_digest(observation_proof.observer_signature, _sign(observation_proof.signing_payload(), keys[observation_proof.observer_ref])):
        raise KVAdmissionError('OBSERVER_SIGNATURE_INVALID')
    current = _current_observation_proof_digest(proof_state, path.path_digest)
    if observation_proof.proof_digest != current:
        raise KVAdmissionError('OBSERVATION_PROOF_SUPERSEDED_OR_REVOKED')

def _blockers(t: PersistentKVReuseTargetV1, p: PersistentKVPathEvidenceV1):
    b = []
    if t.responsibility is not ResponsibilityClass.TRANSFORMER_KV_CACHE:
        b.append('TARGET_NOT_TRANSFORMER_KV_CACHE')
    if p.responsibility is not ResponsibilityClass.TRANSFORMER_KV_CACHE:
        b.append('PATH_NOT_TRANSFORMER_KV_CACHE')
    if p.target_digest != t.target_digest:
        b.append('PATH_TARGET_DIGEST_MISMATCH')
    for f in ('model_revision', 'tokenizer_digest', 'chat_template_digest', 'system_tool_prefix_digest', 'prefix_token_digest', 'cache_abi', 'backend_cache_abi', 'principal_namespace_digest', 'workload_digest', 'host_epoch', 'route_epoch'):
        if getattr(p, f) != getattr(t, f):
            b.append(f'PATH_{f.upper()}_MISMATCH')
    if p.evidence_generation != t.source_generation:
        b.append('PATH_SOURCE_GENERATION_MISMATCH')
    if p.evidence_currentness_ref != t.source_currentness_ref:
        b.append('PATH_CURRENTNESS_MISMATCH')
    if not p.persistent_restore_observed:
        b.append('PERSISTENT_RESTORE_NOT_OBSERVED')
    if not p.cache_read_observed:
        b.append('CACHE_READ_NOT_OBSERVED')
    if p.cache_hit_tokens <= 0:
        b.append('CACHE_HIT_TOKENS_NOT_POSITIVE')
    return b

def admit_persistent_kv_reuse(*, target: PersistentKVReuseTargetV1, claim: KVReuseProjectionClaimV1, resolver_proof: OwnerResolverProofV1, path_evidence: PersistentKVPathEvidenceV1, observation_proof: KVPathObservationProofV1, trusted_source_state: Mapping[str, Any], trusted_resolver_keys: Mapping[str, Any], trusted_resolver_state: Mapping[str, Any], trusted_resolver_proof_state: Mapping[str, Any], trusted_observer_keys: Mapping[str, Any], trusted_observer_state: Mapping[str, Any], trusted_observation_proof_state: Mapping[str, Any]):
    if not isinstance(target, PersistentKVReuseTargetV1):
        raise KVAdmissionError('KV_TARGET_REQUIRED')
    if not isinstance(path_evidence, PersistentKVPathEvidenceV1):
        raise KVAdmissionError('KV_PATH_EVIDENCE_REQUIRED')
    if not isinstance(claim, KVReuseProjectionClaimV1):
        raise KVAdmissionError('PROJECTION_CLAIM_REQUIRED')
    if not isinstance(resolver_proof, OwnerResolverProofV1):
        raise KVAdmissionError('OWNER_RESOLVER_PROOF_REQUIRED')
    if not isinstance(observation_proof, KVPathObservationProofV1):
        raise KVAdmissionError('KV_PATH_OBSERVATION_PROOF_REQUIRED')
    if not isinstance(trusted_source_state, Mapping) or not isinstance(trusted_resolver_keys, Mapping) or (not isinstance(trusted_resolver_state, Mapping)) or (not isinstance(trusted_resolver_proof_state, Mapping)) or (not isinstance(trusted_observer_keys, Mapping)) or (not isinstance(trusted_observer_state, Mapping)) or (not isinstance(trusted_observation_proof_state, Mapping)):
        raise KVAdmissionError('TRUSTED_EXTERNAL_STATE_REQUIRED')
    if claim.projection_schema != PROJECTION_SCHEMA:
        raise KVAdmissionError('PROJECTION_SCHEMA_UNSUPPORTED')
    if claim.projection_payload_digest != resolved_projection_payload_digest(target, path_evidence):
        raise KVAdmissionError('PROJECTION_PAYLOAD_DIGEST_MISMATCH')
    if claim.subject_ref != target.coordinate_ref:
        raise KVAdmissionError('PROJECTION_COORDINATE_SUBJECT_MISMATCH')
    if claim.subject_generation != target.source_generation:
        raise KVAdmissionError('PROJECTION_SUBJECT_GENERATION_MISMATCH')
    if claim.source_generation != target.source_generation:
        raise KVAdmissionError('PROJECTION_SOURCE_GENERATION_MISMATCH')
    if claim.source_currentness_ref != target.source_currentness_ref:
        raise KVAdmissionError('PROJECTION_SOURCE_CURRENTNESS_MISMATCH')
    _verify_source_currentness(claim, trusted_source_state)
    _verify_resolver(claim, resolver_proof, trusted_resolver_keys, trusted_resolver_state, trusted_resolver_proof_state)
    _verify_observation(target=target, path=path_evidence, claim=claim, resolver_proof=resolver_proof, observation_proof=observation_proof, keys=trusted_observer_keys, state=trusted_observer_state, proof_state=trusted_observation_proof_state, resolver_keys=trusted_resolver_keys)
    b = _blockers(target, path_evidence)
    net = path_evidence.net_reuse_us
    if b:
        disp, ok = ('EVIDENCE_REQUIRED', False)
    elif net <= 0:
        disp, ok = ('KV_REUSE_OBSERVED_NO_POSITIVE_NET_BENEFIT', False)
    else:
        disp, ok = ('TRANSFORMER_KV_REUSE_ADMISSIBLE', True)
    logical = {'schema': 'OwnerResolvedPersistentKVReuseAdmissionV1', 'target_digest': target.target_digest, 'coordinate_ref': target.coordinate_ref, 'k27_cell': target.k27_cell, 'responsibility': target.responsibility.value, 'projection_schema': claim.projection_schema, 'projection_claim_digest': claim.claim_digest, 'owner_resolver_proof_digest': resolver_proof.proof_digest, 'path_evidence_digest': path_evidence.path_digest, 'path_observation_proof_digest': observation_proof.proof_digest, 'source_ref': claim.source_ref, 'source_generation': claim.source_generation, 'source_currentness_ref': claim.source_currentness_ref, 'disposition': disp, 'blockers': tuple(sorted(set(b))), 'persistent_restore_observed': path_evidence.persistent_restore_observed, 'cache_read_observed': path_evidence.cache_read_observed, 'cache_hit_tokens': path_evidence.cache_hit_tokens, 'prefill_saved_us': path_evidence.prefill_saved_us, 'transfer_us': path_evidence.transfer_us, 'restore_us': path_evidence.restore_us, 'queue_penalty_us': path_evidence.queue_penalty_us, 'memory_penalty_us': path_evidence.memory_penalty_us, 'security_isolation_us': path_evidence.security_isolation_us, 'invalidation_penalty_us': path_evidence.invalidation_penalty_us, 'overhead_us': path_evidence.prefill_saved_us - net, 'net_reuse_us': net, 'source_currentness_verified_against_external_state': True, 'owner_resolver_proof_verified': True, 'resolver_proof_current_in_external_registry': True, 'runtime_observation_proof_verified': True, 'observation_proof_current_in_external_registry': True, 'admission_conditioned_on_external_trust_roots': True, 'resolver_trust_root_proven_by_this_module': False, 'proof_registry_authority_proven_by_this_module': False, 'source_registry_authority_proven_by_this_module': False, 'observer_trust_root_proven_by_this_module': False, 'observation_registry_authority_proven_by_this_module': False, 'live_kv_access_performed': False, 'transformer_kv_reuse_admissible': ok, 'coordinate_nomination_is_authority': False, 'coordinate_memory_equated_to_transformer_kv': False, 'semantic_response_cache_equated_to_transformer_kv': False, 'monetary_credit_authorized': False, 'provider_authorized': False, 'execution_authorized': False, 'performance_superiority_claimed': False}
    return {**logical, 'admission_digest': _dig('AURA_PCK2_ADMISSION_V1', logical)}
