"""Cloud Drive artifact adapter for CS-ARENA-SYNC-001 AS-05.

Composes the sibling-owned Custodian observation seam and AS-02 artifact sync core.
No network I/O, coordinate ownership, index mutation, wake execution, or provider
execution happens here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any, Mapping

try:
    from .artifact_sync_core import ArtifactIdentityV1, ArtifactMirrorFenceV1, ArtifactMutationEventV1, mirror_route_decision
except ImportError:  # direct-test convenience
    from artifact_sync_core import ArtifactIdentityV1, ArtifactMirrorFenceV1, ArtifactMutationEventV1, mirror_route_decision

CLOUD_ADAPTER_SCHEMA = "CloudDriveArtifactAdapterV1"
HYDRATION_SCHEMA = "DriveArtifactHydrationV1"
PUBLISH_PLAN_SCHEMA = "CloudArtifactPublishPlanV1"
ADMISSION_SCHEMA = "CloudArtifactEffectAdmissionV1"
WRITE_RECEIPT_SCHEMA = "CloudArtifactWriteVerificationV1"
ABSENT_REVISION = "__ABSENT__"
ALLOWED_MUTATIONS = frozenset({"CREATE","MODIFY","RENAME","DELETE","TOMBSTONE","ACCEPT","SUPERSEDE","MIRROR_REPAIR"})
CONTENT_MUTATIONS = ALLOWED_MUTATIONS - {"DELETE", "TOMBSTONE"}

class CloudAdapterError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail

def _text(value: Any, code: str) -> str:
    out = str(value or "").strip()
    if not out:
        raise CloudAdapterError(code)
    return out

def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",",":"), ensure_ascii=False, allow_nan=False).encode()
    except (TypeError, ValueError) as exc:
        raise CloudAdapterError("NONCANONICAL_VALUE") from exc

def _digest(domain: str, value: Any) -> str:
    return hashlib.sha256(domain.encode()+b"\0"+_canonical(value)).hexdigest()

def _sha(value: str) -> str:
    value = _text(value, "SHA256_REQUIRED").lower()
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise CloudAdapterError("SHA256_INVALID")
    return value

def _nni(value: Any, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CloudAdapterError(code)
    return value

@dataclass(frozen=True)
class CloudAdapterContextV1:
    durable_intake_ref: str
    inbox_state: str
    project_id: str
    work_order_id: str
    claim_id: str
    producer_worker_id: str
    source_currentness_ref: str
    currentness_state: str
    origin_id: str
    generation: int
    source_surface: str = "GOOGLE_DRIVE"
    def validate(self) -> None:
        for value, code in ((self.durable_intake_ref,"DURABLE_INTAKE_REF_REQUIRED"),(self.project_id,"PROJECT_ID_REQUIRED"),(self.work_order_id,"WORK_ORDER_ID_REQUIRED"),(self.claim_id,"CLAIM_ID_REQUIRED"),(self.producer_worker_id,"PRODUCER_WORKER_REQUIRED"),(self.source_currentness_ref,"SOURCE_CURRENTNESS_REQUIRED"),(self.origin_id,"ORIGIN_ID_REQUIRED"),(self.source_surface,"SOURCE_SURFACE_REQUIRED")):
            _text(value, code)
        if self.inbox_state.upper() not in {"PROCESSING","CLAIMED"}:
            raise CloudAdapterError("DURABLE_INTAKE_NOT_CLAIMED", self.inbox_state)
        if self.currentness_state.upper() != "CURRENT":
            raise CloudAdapterError("STALE_CURRENTNESS_REBASE_REQUIRED", self.currentness_state)
        _nni(self.generation, "GENERATION_INVALID")

@dataclass(frozen=True)
class DriveArtifactHydrationV1:
    resource_id: str
    provider_revision: str
    content_sha256: str | None
    byte_size: int | None
    mime: str
    extension: str
    mutation_type: str
    hydrated_currentness_ref: str
    provider_etag: str = ""
    parent_source_refs: tuple[str, ...] = ()
    semantic_type: str = "UNKNOWN"
    prior_artifact_id: str | None = None
    prior_resource_id: str | None = None
    removed: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)
    def validate(self) -> None:
        for value, code in ((self.resource_id,"RESOURCE_ID_REQUIRED"),(self.provider_revision,"PROVIDER_REVISION_REQUIRED"),(self.mime,"MIME_REQUIRED"),(self.extension,"EXTENSION_REQUIRED"),(self.hydrated_currentness_ref,"HYDRATED_CURRENTNESS_REQUIRED")):
            _text(value, code)
        mutation = self.mutation_type.upper()
        if mutation not in ALLOWED_MUTATIONS:
            raise CloudAdapterError("MUTATION_TYPE_INVALID", mutation)
        if mutation in {"DELETE","TOMBSTONE"}:
            if not self.removed: raise CloudAdapterError("REMOVAL_EVIDENCE_REQUIRED")
            if self.content_sha256 is not None or self.byte_size is not None: raise CloudAdapterError("REMOVAL_CONTENT_MUST_BE_NONE")
            if not (self.prior_artifact_id or self.prior_resource_id): raise CloudAdapterError("PRIOR_LINEAGE_REQUIRED")
        else:
            if self.removed: raise CloudAdapterError("CONTENT_MUTATION_MARKED_REMOVED")
            if self.content_sha256 is None or self.byte_size is None: raise CloudAdapterError("CONTENT_HYDRATION_REQUIRED")
            _sha(self.content_sha256); _nni(self.byte_size, "BYTE_SIZE_INVALID")
        _canonical(dict(self.metadata))

@dataclass(frozen=True)
class NormalizedCloudMutationV1:
    event: ArtifactMutationEventV1
    identity: ArtifactIdentityV1 | None
    durable_intake_ref: str
    provider_revision: str
    provider_etag: str
    execution_authorized: bool = False
    persistence_proven: bool = False

def translate_custodian_event(envelope: Any, *, context: CloudAdapterContextV1, hydration: DriveArtifactHydrationV1, inbound_fence: ArtifactMirrorFenceV1 | None = None) -> NormalizedCloudMutationV1:
    context.validate(); hydration.validate()
    provider = _text(getattr(envelope,"provider", ""), "ENVELOPE_PROVIDER_REQUIRED").lower()
    source = _text(getattr(envelope,"source", ""), "ENVELOPE_SOURCE_REQUIRED")
    resource = _text(getattr(envelope,"resource_id", ""), "ENVELOPE_RESOURCE_REQUIRED")
    observed = _text(getattr(envelope,"observed_at", ""), "ENVELOPE_OBSERVED_AT_REQUIRED")
    event_key = _text(getattr(envelope,"event_key", ""), "ENVELOPE_EVENT_KEY_REQUIRED")
    if provider != "google": raise CloudAdapterError("PROVIDER_NOT_GOOGLE", provider)
    if source not in {"drive_changes","workspace_events"}: raise CloudAdapterError("ENVELOPE_SOURCE_UNSUPPORTED", source)
    if resource != hydration.resource_id: raise CloudAdapterError("HYDRATION_RESOURCE_MISMATCH")
    if hydration.hydrated_currentness_ref != context.source_currentness_ref: raise CloudAdapterError("HYDRATION_CURRENTNESS_MISMATCH")
    if inbound_fence:
        inbound_fence.validate()
        if inbound_fence.origin_id != context.origin_id or inbound_fence.generation != context.generation: raise CloudAdapterError("INBOUND_FENCE_LINEAGE_MISMATCH")
    metadata = {"custodian_event_key":event_key,"custodian_provider_event_id":str(getattr(envelope,"provider_event_id","") or ""),"custodian_source":source,"provider_revision":hydration.provider_revision,"provider_etag":hydration.provider_etag,"hydration_metadata":dict(hydration.metadata)}
    event = ArtifactMutationEventV1.build(origin_id=context.origin_id, provider="GOOGLE", source_surface=context.source_surface, event_type=hydration.mutation_type.upper(), source_path_or_resource_id=hydration.resource_id, producer_worker_id=context.producer_worker_id, claim_id=context.claim_id, work_order_id=context.work_order_id, project_id=context.project_id, source_currentness_ref=context.source_currentness_ref, observed_at=observed, generation=context.generation, mirror_fence=(inbound_fence.fence_token if inbound_fence else None), prior_artifact_id=hydration.prior_artifact_id, prior_source_path_or_resource_id=hydration.prior_resource_id, metadata=metadata)
    identity = None
    if hydration.mutation_type.upper() in CONTENT_MUTATIONS:
        provisional = ArtifactIdentityV1(artifact_sid="__PENDING__", sha256=_sha(hydration.content_sha256 or ""), byte_size=_nni(hydration.byte_size,"BYTE_SIZE_INVALID"), mime=hydration.mime, extension=hydration.extension, source_surface=context.source_surface, source_path_or_resource_id=hydration.resource_id, origin_id=context.origin_id, generation=context.generation, semantic_type=hydration.semantic_type, parent_source_refs=tuple(sorted(set(hydration.parent_source_refs))))
        identity = ArtifactIdentityV1(**{**asdict(provisional), "artifact_sid":provisional.expected_artifact_sid()}); identity.validate()
    return NormalizedCloudMutationV1(event, identity, context.durable_intake_ref, hydration.provider_revision, hydration.provider_etag)

@dataclass(frozen=True)
class CloudArtifactPublishPlanV1:
    plan_id: str
    artifact_sid: str
    content_sha256: str
    byte_size: int
    source_event_id: str
    source_currentness_ref: str
    target_surface: str
    target_parent_ref: str
    target_resource_id: str | None
    expected_target_revision: str
    mirror_fence: ArtifactMirrorFenceV1
    effect_class: str = "D0"
    execution_authorized: bool = False
    provider_calls_authorized: bool = False
    def logical_payload(self) -> dict[str, Any]:
        return {"schema":PUBLISH_PLAN_SCHEMA,"artifact_sid":self.artifact_sid,"content_sha256":self.content_sha256,"byte_size":self.byte_size,"source_event_id":self.source_event_id,"source_currentness_ref":self.source_currentness_ref,"target_surface":self.target_surface,"target_parent_ref":self.target_parent_ref,"target_resource_id":self.target_resource_id,"expected_target_revision":self.expected_target_revision,"mirror_fence":self.mirror_fence.to_dict(),"effect_class":self.effect_class}
    def expected_plan_id(self) -> str: return "cloud-plan-"+_digest("CLOUD_ARTIFACT_PUBLISH_PLAN_V1",self.logical_payload())[:32]
    def validate(self) -> None:
        for value,code in ((self.plan_id,"PLAN_ID_REQUIRED"),(self.artifact_sid,"ARTIFACT_SID_REQUIRED"),(self.content_sha256,"CONTENT_SHA256_REQUIRED"),(self.source_event_id,"SOURCE_EVENT_ID_REQUIRED"),(self.source_currentness_ref,"SOURCE_CURRENTNESS_REQUIRED"),(self.target_surface,"TARGET_SURFACE_REQUIRED"),(self.target_parent_ref,"TARGET_PARENT_REF_REQUIRED"),(self.expected_target_revision,"EXPECTED_TARGET_REVISION_REQUIRED")):_text(value,code)
        _sha(self.content_sha256); _nni(self.byte_size,"BYTE_SIZE_INVALID"); self.mirror_fence.validate()
        if self.effect_class != "D0": raise CloudAdapterError("AS05_EFFECT_CLASS_MUST_BE_D0")
        if self.execution_authorized or self.provider_calls_authorized: raise CloudAdapterError("PLAN_CANNOT_SELF_AUTHORIZE")
        if self.plan_id != self.expected_plan_id(): raise CloudAdapterError("PLAN_ID_MISMATCH")

def prepare_cloud_publish_plan(normalized: NormalizedCloudMutationV1, *, target_surface: str, target_parent_ref: str, target_resource_id: str | None = None, expected_target_revision: str = ABSENT_REVISION, inbound_fence: ArtifactMirrorFenceV1 | None = None) -> CloudArtifactPublishPlanV1:
    if normalized.identity is None: raise CloudAdapterError("CONTENT_IDENTITY_REQUIRED_FOR_PUBLISH")
    route = mirror_route_decision(event=normalized.event, target_surface=target_surface, inbound_fence=inbound_fence)
    if route["decision"] != "ALLOW_MIRROR_PLAN": raise CloudAdapterError(str(route["code"]), str(route["decision"]))
    f=route["fence"]; fence=ArtifactMirrorFenceV1(f["origin_id"],f["generation"],f["source_surface"],f["target_surface"],f["fence_token"])
    provisional=CloudArtifactPublishPlanV1("__PENDING__",normalized.identity.artifact_sid,normalized.identity.sha256,normalized.identity.byte_size,normalized.event.event_id,normalized.event.source_currentness_ref,_text(target_surface,"TARGET_SURFACE_REQUIRED"),_text(target_parent_ref,"TARGET_PARENT_REF_REQUIRED"),(str(target_resource_id).strip() if target_resource_id else None),_text(expected_target_revision,"EXPECTED_TARGET_REVISION_REQUIRED"),fence)
    plan=CloudArtifactPublishPlanV1(**{**asdict(provisional),"mirror_fence":fence,"plan_id":provisional.expected_plan_id()}); plan.validate(); return plan

@dataclass(frozen=True)
class CloudArtifactEffectAdmissionV1:
    admission_ref: str
    plan_id: str
    plan_digest: str
    source_currentness_ref: str
    effect_class: str
    authorized: bool
    cost_ceiling_usd: float
    def validate_for(self, plan: CloudArtifactPublishPlanV1) -> None:
        plan.validate(); _text(self.admission_ref,"ADMISSION_REF_REQUIRED")
        if self.plan_id != plan.plan_id: raise CloudAdapterError("ADMISSION_PLAN_ID_MISMATCH")
        if self.plan_digest != admission_binding_digest(plan): raise CloudAdapterError("ADMISSION_PLAN_DIGEST_MISMATCH")
        if self.source_currentness_ref != plan.source_currentness_ref: raise CloudAdapterError("ADMISSION_CURRENTNESS_MISMATCH")
        if self.effect_class != plan.effect_class: raise CloudAdapterError("ADMISSION_EFFECT_CLASS_MISMATCH")
        if not self.authorized: raise CloudAdapterError("EFFECT_NOT_AUTHORIZED")
        x=self.cost_ceiling_usd
        if isinstance(x,bool) or not isinstance(x,(int,float)): raise CloudAdapterError("COST_CEILING_INVALID")
        if x != x or x in (float("inf"),float("-inf")): raise CloudAdapterError("COST_CEILING_NONFINITE")
        if x < 0: raise CloudAdapterError("COST_CEILING_NEGATIVE")
        if float(x) != 0.0: raise CloudAdapterError("AS05_PROVIDER_COST_MUST_BE_ZERO")

def admission_binding_digest(plan: CloudArtifactPublishPlanV1) -> str:
    plan.validate(); return _digest("CLOUD_PUBLISH_ADMISSION_BINDING_V1",plan.logical_payload())

def prepare_effect_handoff(plan: CloudArtifactPublishPlanV1, admission: CloudArtifactEffectAdmissionV1) -> dict[str,Any]:
    admission.validate_for(plan)
    return {"schema":ADMISSION_SCHEMA,"decision":"READY_FOR_EXTERNAL_FILE_EFFECT","plan":plan.logical_payload()|{"plan_id":plan.plan_id,"execution_authorized":False,"provider_calls_authorized":False},"admission_ref":admission.admission_ref,"execution_authorized":True,"runtime_execution_proven":False,"provider_call_started":False,"coordinate_owner_bound":False,"persistence_index_updated":False}

@dataclass(frozen=True)
class CloudWriteEffectReceiptV1:
    plan_id: str
    admission_ref: str
    provider_resource_id: str
    prior_revision: str
    landed_revision: str
    provider_effect_started: bool
    write_succeeded: bool
    command_receipt_ref: str
    def validate_for(self, plan: CloudArtifactPublishPlanV1, admission: CloudArtifactEffectAdmissionV1) -> None:
        admission.validate_for(plan)
        if self.plan_id != plan.plan_id or self.admission_ref != admission.admission_ref: raise CloudAdapterError("EFFECT_RECEIPT_BINDING_MISMATCH")
        for v,c in ((self.provider_resource_id,"PROVIDER_RESOURCE_ID_REQUIRED"),(self.prior_revision,"PRIOR_REVISION_REQUIRED"),(self.landed_revision,"LANDED_REVISION_REQUIRED"),(self.command_receipt_ref,"COMMAND_RECEIPT_REF_REQUIRED")):_text(v,c)
        if not self.provider_effect_started: raise CloudAdapterError("PROVIDER_EFFECT_NOT_STARTED")
        if not self.write_succeeded: raise CloudAdapterError("CLOUD_WRITE_NOT_SUCCESSFUL")
        if self.prior_revision != plan.expected_target_revision: raise CloudAdapterError("CAS_PRIOR_REVISION_MISMATCH")
        if plan.target_resource_id and self.provider_resource_id != plan.target_resource_id: raise CloudAdapterError("TARGET_RESOURCE_ID_MISMATCH")

@dataclass(frozen=True)
class CloudReadbackV1:
    provider_resource_id: str
    provider_revision: str
    content_sha256: str
    byte_size: int
    def validate(self) -> None:
        _text(self.provider_resource_id,"READBACK_RESOURCE_ID_REQUIRED"); _text(self.provider_revision,"READBACK_REVISION_REQUIRED"); _sha(self.content_sha256); _nni(self.byte_size,"READBACK_BYTE_SIZE_INVALID")

def verify_cloud_write(plan: CloudArtifactPublishPlanV1, admission: CloudArtifactEffectAdmissionV1, effect: CloudWriteEffectReceiptV1, readback: CloudReadbackV1) -> dict[str,Any]:
    effect.validate_for(plan,admission); readback.validate()
    if readback.provider_resource_id != effect.provider_resource_id: raise CloudAdapterError("READBACK_RESOURCE_MISMATCH")
    if readback.provider_revision != effect.landed_revision: raise CloudAdapterError("READBACK_REVISION_MISMATCH")
    if readback.content_sha256.lower() != plan.content_sha256.lower(): raise CloudAdapterError("LANDED_HASH_MISMATCH")
    if readback.byte_size != plan.byte_size: raise CloudAdapterError("LANDED_SIZE_MISMATCH")
    return {"schema":WRITE_RECEIPT_SCHEMA,"status":"VERIFIED_LANDED_BYTES","plan_id":plan.plan_id,"artifact_sid":plan.artifact_sid,"provider_resource_id":readback.provider_resource_id,"landed_revision":readback.provider_revision,"content_sha256":readback.content_sha256.lower(),"byte_size":readback.byte_size,"mirror_fence":plan.mirror_fence.to_dict(),"admission_ref":admission.admission_ref,"command_receipt_ref":effect.command_receipt_ref,"execution_proven_for_file_effect":True,"artifact_persistence_receipt_proven":False,"coordinate_owner_bound":False,"workgraph_wake_emitted":False}
