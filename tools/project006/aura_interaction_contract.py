from __future__ import annotations
from dataclasses import dataclass
import hashlib, json, re
from typing import Callable

_HEX64=re.compile(r'^[0-9a-f]{64}$')
_DRIVE_ID=re.compile(r'^1[A-Za-z0-9_-]{32,43}$')
_FORBIDDEN_AGENT_FIELDS=frozenset({'api_key','apikey','credential','credentials','endpoint','provider_endpoint','provider_url','fencing_token','fence_token','effect_admission','cost_admission','provider_route_override','executor_command','shell_command'})

class InteractionError(ValueError): pass


def _canon(obj: object) -> bytes:
    return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False,default=lambda x:x.__dict__).encode()

def _sha(obj: object) -> str: return hashlib.sha256(_canon(obj)).hexdigest()

@dataclass(frozen=True)
class SourceIdentity:
    file_id: str
    revision: str
    digest: str
    def validate(self):
        if not _DRIVE_ID.fullmatch(self.file_id): raise InteractionError('SOURCE_FILE_ID_INVALID')
        if not self.revision or len(self.revision)>512: raise InteractionError('SOURCE_REVISION_INVALID')
        if not _HEX64.fullmatch(self.digest): raise InteractionError('SOURCE_DIGEST_INVALID')

@dataclass(frozen=True)
class LiveCurrentness:
    generation: int
    head_digest: str
    def validate(self):
        if not isinstance(self.generation,int) or self.generation < 1: raise InteractionError('GENERATION_INVALID')
        if not re.fullmatch(r'^[0-9a-f]{16,64}$', self.head_digest): raise InteractionError('HEAD_DIGEST_INVALID')

@dataclass(frozen=True)
class AgentIntent:
    agent_id: str
    objective: str
    target_size: int=1
    requested_effect: str='D0'
    def validate(self):
        if not self.agent_id or len(self.agent_id)>256: raise InteractionError('AGENT_ID_INVALID')
        if not self.objective.strip() or len(self.objective)>20000: raise InteractionError('OBJECTIVE_INVALID')
        if self.requested_effect != 'D0': raise InteractionError('ONLY_D0_DRAFTS_SUPPORTED')
        if not isinstance(self.target_size,int) or not 1 <= self.target_size <= 81: raise InteractionError('TARGET_SIZE_INVALID')

@dataclass(frozen=True)
class AgentCommandDraft:
    draft_root: str
    intent: AgentIntent
    source: SourceIdentity
    objective_digest: str
    execution_authorized: bool=False

@dataclass(frozen=True)
class OwnerAdmissionBinding:
    command_id: str
    idempotency_key: str
    source: SourceIdentity
    objective_digest: str
    authority_ref: str
    currentness: LiveCurrentness
    provider_policy: str
    proof_root: str
    execution_authorized: bool
    def validate_shape(self):
        if not self.command_id or len(self.command_id)>512: raise InteractionError('COMMAND_ID_INVALID')
        if not self.idempotency_key or len(self.idempotency_key)>512: raise InteractionError('IDEMPOTENCY_KEY_INVALID')
        self.source.validate(); self.currentness.validate()
        if not _HEX64.fullmatch(self.objective_digest): raise InteractionError('OBJECTIVE_DIGEST_INVALID')
        if not self.authority_ref.startswith('Drive 1'): raise InteractionError('AUTHORITY_REF_NOT_CANONICAL_DRIVE_REF')
        if self.provider_policy != 'DEEPSEEK_STANDARD_ONLY': raise InteractionError('PROVIDER_POLICY_NOT_OWNER_FIXED')
        if not _HEX64.fullmatch(self.proof_root): raise InteractionError('PROOF_ROOT_INVALID')
        if self.execution_authorized is not True: raise InteractionError('EXECUTION_NOT_AUTHORIZED')


def draft_agent_command(intent:AgentIntent, source:SourceIdentity) -> AgentCommandDraft:
    intent.validate(); source.validate()
    objective_digest=_sha({'objective':intent.objective,'requested_effect':'D0','target_size':intent.target_size})
    root=_sha({'agent_id':intent.agent_id,'source':source,'objective_digest':objective_digest,'effect':'D0','authority':'NONE'})
    return AgentCommandDraft(root,intent,source,objective_digest,False)


def compile_authorized_envelope(draft:AgentCommandDraft, admission:OwnerAdmissionBinding, live:LiveCurrentness, verify_admission:Callable[[OwnerAdmissionBinding],bool]) -> dict:
    if draft.execution_authorized: raise InteractionError('DRAFT_MUST_BE_INERT')
    admission.validate_shape(); live.validate()
    if admission.source != draft.source: raise InteractionError('FULL_SOURCE_IDENTITY_MISMATCH')
    if admission.objective_digest != draft.objective_digest: raise InteractionError('OBJECTIVE_BINDING_MISMATCH')
    if admission.currentness != live: raise InteractionError('CURRENTNESS_MOVED_REPROVE')
    if verify_admission(admission) is not True: raise InteractionError('ADMISSION_PROOF_NOT_AUTHENTICATED')
    env={
      'schema':'AuraCommandEnvelopeV1-candidate',
      'command_id':admission.command_id,
      'idempotency_key':admission.idempotency_key,
      'queue_state':'READY',
      'message_authorized':True,
      'execution_authorized':True,
      'requested_effect':'D0',
      'effect_ceiling':'D0',
      'constraints':'D0',
      'authority_ref':admission.authority_ref,
      'target_size':draft.intent.target_size,
      'provider':admission.provider_policy,
      'no_implicit_fallback':True,
      'bound_revision':{'revision':f'AWJ-001@GEN{live.generation}','digest':live.head_digest},
      'currentness':{'observed_generation':live.generation,'observed_digest':live.head_digest},
      'stage_path':['SOURCE','BOUND','AUTHORIZED'],
      'source_file_id':draft.source.file_id,
      'source_revision':draft.source.revision,
      'source_digest':draft.source.digest,
      'objective':{'requested_effect':'D0','text':draft.intent.objective},
      'interaction_contract':'AURA_PROOF_CARRYING_INTERACTION_V1',
      'admission_proof_root':admission.proof_root,
    }
    if _find_forbidden_keys(env): raise InteractionError('COMPILER_EMITTED_FORBIDDEN_FIELD')
    return env


def _find_forbidden_keys(node:object)->list[str]:
    hits=[]; stack=[(node,'envelope')]
    while stack:
        cur,path=stack.pop()
        if isinstance(cur,dict):
            for k,v in cur.items():
                p=f'{path}.{k}'
                if str(k).casefold() in _FORBIDDEN_AGENT_FIELDS: hits.append(p)
                stack.append((v,p))
        elif isinstance(cur,(list,tuple)):
            for i,v in enumerate(cur): stack.append((v,f'{path}.{i}'))
    return hits


def envelope_root(env:dict)->str: return _sha(env)
