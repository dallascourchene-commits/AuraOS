from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import hashlib, json
from typing import Mapping, Optional

HEX=set('0123456789abcdef')
def _hex64(x): return isinstance(x,str) and len(x)==64 and set(x)<=HEX
def _root(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),default=lambda x:x.value if isinstance(x,Enum) else x.__dict__).encode()).hexdigest()

class AttestationError(ValueError): pass
class RuntimeDisposition(str,Enum):
    OWNER_REPORTED_STALE_UNMEASURED='OWNER_REPORTED_STALE_UNMEASURED'
    UNKNOWN_UNMEASURED='UNKNOWN_UNMEASURED'
    HOLD_UNAUTHENTICATED_MEASUREMENT='HOLD_UNAUTHENTICATED_MEASUREMENT'
    HOLD_SOURCE_INCARNATION_UNRESOLVED='HOLD_SOURCE_INCARNATION_UNRESOLVED'
    HOLD_HOST_INCARNATION_UNBOUND='HOLD_HOST_INCARNATION_UNBOUND'
    HOLD_STALE_MEASUREMENT='HOLD_STALE_MEASUREMENT'
    STALE_MEASURED_HEAD='STALE_MEASURED_HEAD'
    MIXED_GENERATION='MIXED_GENERATION'
    CURRENT_EXACT_HOST_OBSERVED='CURRENT_EXACT_HOST_OBSERVED'

@dataclass(frozen=True)
class RuntimeReleaseManifest:
    release_id:str
    repository:str
    expected_head:str
    owner_generation:int
    canonical_operation_root:str
    components:Mapping[str,str]
    def validate(self):
        if not self.release_id or not self.repository or not self.expected_head: raise AttestationError('MANIFEST_IDENTITY_INVALID')
        if not isinstance(self.owner_generation,int) or self.owner_generation<0: raise AttestationError('GENERATION_INVALID')
        if not _hex64(self.canonical_operation_root): raise AttestationError('CANONICAL_ROOT_INVALID')
        if not self.components or any(not k or not _hex64(v) for k,v in self.components.items()): raise AttestationError('COMPONENT_MANIFEST_INVALID')
    @property
    def release_root(self):
        self.validate(); return _root({'release_id':self.release_id,'repository':self.repository,'expected_head':self.expected_head,'owner_generation':self.owner_generation,'canonical_operation_root':self.canonical_operation_root,'components':dict(sorted(self.components.items()))})

@dataclass(frozen=True)
class HostMeasurement:
    host_id:str
    observed_head:Optional[str]
    observed_components:Mapping[str,str]
    host_incarnation:str
    source_incarnation_root:Optional[str]
    observed_at_ms:int
    k27_coordinate:Optional[tuple[int,int,int]]=None
    def validate_shape(self):
        if not self.host_id: raise AttestationError('HOST_ID_INVALID')
        if self.observed_head is not None and not self.observed_head: raise AttestationError('OBSERVED_HEAD_INVALID')
        if any(not k or not _hex64(v) for k,v in self.observed_components.items()): raise AttestationError('OBSERVED_COMPONENT_INVALID')
        if not self.host_incarnation: raise AttestationError('HOST_INCARNATION_INVALID')
        if self.source_incarnation_root is not None and not _hex64(self.source_incarnation_root): raise AttestationError('SOURCE_INCARNATION_ROOT_INVALID')
        if not isinstance(self.observed_at_ms,int) or self.observed_at_ms<0: raise AttestationError('OBSERVED_TIME_INVALID')
        if self.k27_coordinate is not None and (len(self.k27_coordinate)!=3 or any(not isinstance(v,int) or v<0 or v>26 for v in self.k27_coordinate)): raise AttestationError('K27_INVALID')
    @property
    def technical_root(self):
        self.validate_shape()
        return _root({'host_id':self.host_id,'observed_head':self.observed_head,'observed_components':dict(sorted(self.observed_components.items())),'host_incarnation':self.host_incarnation,'source_incarnation_root':self.source_incarnation_root,'observed_at_ms':self.observed_at_ms})

@dataclass(frozen=True)
class MeasurementEvidence:
    measurement_root:str
    release_root:str
    verifier_id:str
    observer_id:str
    authenticated:bool
    independent:bool
    source_incarnation_reproducible:bool
    host_incarnation_bound:bool
    issued_at_ms:int
    expires_at_ms:int
    def validate_shape(self):
        if not _hex64(self.measurement_root) or not _hex64(self.release_root): raise AttestationError('EVIDENCE_ROOT_INVALID')
        if not self.verifier_id or not self.observer_id: raise AttestationError('EVIDENCE_ACTOR_INVALID')
        if self.verifier_id==self.observer_id: raise AttestationError('OBSERVER_NOT_INDEPENDENT_BY_ID')
        if not isinstance(self.issued_at_ms,int) or not isinstance(self.expires_at_ms,int) or self.issued_at_ms<0 or self.expires_at_ms<self.issued_at_ms: raise AttestationError('EVIDENCE_TIME_INVALID')

@dataclass(frozen=True)
class RuntimeAttestation:
    disposition:RuntimeDisposition
    release_root:str
    measurement_root:Optional[str]
    exact_installed_head:Optional[str]
    current:bool
    design_falsified:bool
    reasons:tuple[str,...]
    owner_reported_updated:Optional[bool]
    def to_dict(self): return {'disposition':self.disposition.value,'release_root':self.release_root,'measurement_root':self.measurement_root,'exact_installed_head':self.exact_installed_head,'current':self.current,'design_falsified':self.design_falsified,'reasons':list(self.reasons),'owner_reported_updated':self.owner_reported_updated}

def attest_runtime(manifest:RuntimeReleaseManifest, *, owner_reported_updated:Optional[bool], measurement:Optional[HostMeasurement], evidence:Optional[MeasurementEvidence], now_ms:int, max_age_ms:int=300_000)->RuntimeAttestation:
    manifest.validate(); rr=manifest.release_root
    if owner_reported_updated not in (True,False,None): raise AttestationError('OWNER_REPORT_INVALID')
    if measurement is None or evidence is None:
        disp=RuntimeDisposition.OWNER_REPORTED_STALE_UNMEASURED if owner_reported_updated is False else RuntimeDisposition.UNKNOWN_UNMEASURED
        reasons=('OWNER_REPORT_STALE_NO_EXACT_HEAD',) if owner_reported_updated is False else ('NO_AUTHENTICATED_HOST_MEASUREMENT',)
        return RuntimeAttestation(disp,rr,None,None,False,False,reasons,owner_reported_updated)
    measurement.validate_shape(); evidence.validate_shape()
    mr=measurement.technical_root
    exact_head=measurement.observed_head
    if evidence.measurement_root!=mr or evidence.release_root!=rr or not evidence.authenticated or not evidence.independent:
        return RuntimeAttestation(RuntimeDisposition.HOLD_UNAUTHENTICATED_MEASUREMENT,rr,mr,exact_head,False,False,('MEASUREMENT_OR_RELEASE_BINDING_UNAUTHENTICATED',),owner_reported_updated)
    if not evidence.source_incarnation_reproducible or measurement.source_incarnation_root is None:
        return RuntimeAttestation(RuntimeDisposition.HOLD_SOURCE_INCARNATION_UNRESOLVED,rr,mr,exact_head,False,False,('SOURCE_INCARNATION_NOT_INDEPENDENTLY_REPRODUCIBLE',),owner_reported_updated)
    if not evidence.host_incarnation_bound:
        return RuntimeAttestation(RuntimeDisposition.HOLD_HOST_INCARNATION_UNBOUND,rr,mr,exact_head,False,False,('HOST_INCARNATION_NOT_BOUND',),owner_reported_updated)
    if now_ms<evidence.issued_at_ms or now_ms>evidence.expires_at_ms or now_ms-measurement.observed_at_ms>max_age_ms:
        return RuntimeAttestation(RuntimeDisposition.HOLD_STALE_MEASUREMENT,rr,mr,exact_head,False,False,('MEASUREMENT_NOT_FRESH_AT_USE',),owner_reported_updated)
    expected=set(manifest.components); observed=set(measurement.observed_components)
    head_match=measurement.observed_head==manifest.expected_head
    all_components=(observed==expected and all(measurement.observed_components[k]==manifest.components[k] for k in expected))
    if not head_match:
        return RuntimeAttestation(RuntimeDisposition.STALE_MEASURED_HEAD,rr,mr,exact_head,False,False,('INSTALLED_HEAD_DIFFERS_FROM_RELEASE',),owner_reported_updated)
    if not all_components:
        return RuntimeAttestation(RuntimeDisposition.MIXED_GENERATION,rr,mr,exact_head,False,False,('INSTALLED_COMPONENT_MANIFEST_DIFFERS_FROM_RELEASE',),owner_reported_updated)
    return RuntimeAttestation(RuntimeDisposition.CURRENT_EXACT_HOST_OBSERVED,rr,mr,exact_head,True,False,(),owner_reported_updated)
