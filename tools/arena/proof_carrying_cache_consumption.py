from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json

SCHEMA = "AURA-O21R-PROOF-CARRYING-IMMUTABLE-CACHE-CONSUMPTION-v1"

def digest(x):
    return sha256(json.dumps(x, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

class Disposition(str, Enum):
    REUSE_D0 = "REUSE_CACHE_ARTIFACT_D0"
    HOLD = "HOLD"

@dataclass(frozen=True)
class ImmutableCacheArtifact:
    stable_operation_root: str
    content_root: str
    output_kind: str
    renderer_root: str
    dependency_closure_root: str
    producer_semantics_root: str
    producer_receipt_root: str
    namespace: str
    authenticated_producer: bool
    claimed_artifact_root: str
    def canonical_root(self):
        return digest({
            "schema": SCHEMA,
            "stable_operation_root": self.stable_operation_root,
            "content_root": self.content_root,
            "output_kind": self.output_kind,
            "renderer_root": self.renderer_root,
            "dependency_closure_root": self.dependency_closure_root,
            "producer_semantics_root": self.producer_semantics_root,
            "namespace": self.namespace,
        })

@dataclass(frozen=True)
class RuntimeBoundConsumerPermit:
    stable_operation_root: str
    source_incarnation_root: str
    runtime_bound_permit_root: str
    allowed_output_kinds: frozenset[str]
    allowed_namespaces: frozenset[str]
    generation: int
    current: bool
    proof_bound: bool

@dataclass(frozen=True)
class EffectTimeProcessWitness:
    runtime_bound_permit_root: str
    source_incarnation_root: str
    effect_time_process_root: str
    current: bool
    authenticated: bool

@dataclass(frozen=True)
class CacheConsumptionRequest:
    stable_operation_root: str
    source_incarnation_root: str
    content_root: str
    output_kind: str
    renderer_root: str
    dependency_closure_root: str
    namespace: str
    actor: str
    view_id: str
    k27_coordinate: str
    attempt_generation: int

@dataclass(frozen=True)
class Decision:
    disposition: Disposition
    reason: str
    artifact_root: str
    consumption_receipt_root: str | None = None
    cache_write_authority: bool = False
    render_authority: bool = False
    effect_authority: bool = False
    gate10: bool = False

def decide(artifact: ImmutableCacheArtifact, permit: RuntimeBoundConsumerPermit, process: EffectTimeProcessWitness, request: CacheConsumptionRequest):
    canonical = artifact.canonical_root()
    def hold(reason): return Decision(Disposition.HOLD, reason, canonical)
    if not artifact.authenticated_producer or not artifact.producer_receipt_root:
        return hold("PRODUCER_PROVENANCE_NOT_AUTHENTICATED")
    if artifact.claimed_artifact_root != canonical:
        return hold("CACHE_ARTIFACT_ROOT_MISMATCH")
    if request.stable_operation_root != artifact.stable_operation_root:
        return hold("CACHE_OPERATION_MISMATCH")
    if request.content_root != artifact.content_root:
        return hold("CACHE_CONTENT_MISMATCH")
    if request.output_kind != artifact.output_kind:
        return hold("CACHE_OUTPUT_KIND_MISMATCH")
    if request.renderer_root != artifact.renderer_root:
        return hold("CACHE_RENDERER_SEMANTICS_MISMATCH")
    if request.dependency_closure_root != artifact.dependency_closure_root:
        return hold("CACHE_DEPENDENCY_CLOSURE_MISMATCH")
    if request.namespace != artifact.namespace:
        return hold("CACHE_NAMESPACE_MISMATCH")
    if permit.stable_operation_root != request.stable_operation_root:
        return hold("CONSUMER_PERMIT_OPERATION_MISMATCH")
    if not permit.current:
        return hold("CONSUMER_PERMIT_STALE")
    if not permit.proof_bound:
        return hold("CONSUMER_PERMIT_NOT_PROOF_BOUND")
    if request.output_kind not in permit.allowed_output_kinds:
        return hold("OUTPUT_KIND_OUTSIDE_PERMIT")
    if request.namespace not in permit.allowed_namespaces:
        return hold("CACHE_NAMESPACE_OUTSIDE_PERMIT")
    if permit.source_incarnation_root != request.source_incarnation_root:
        return hold("SOURCE_INCARNATION_MOVED")
    if not process.authenticated or not process.current or not process.effect_time_process_root:
        return hold("EFFECT_TIME_PROCESS_NOT_CURRENT_AUTHENTIC")
    if process.runtime_bound_permit_root != permit.runtime_bound_permit_root:
        return hold("PROCESS_PERMIT_BINDING_MISMATCH")
    if process.source_incarnation_root != request.source_incarnation_root:
        return hold("PROCESS_SOURCE_INCARNATION_MISMATCH")
    receipt = digest({
        "schema": SCHEMA,
        "artifact_root": canonical,
        "producer_receipt_root": artifact.producer_receipt_root,
        "runtime_bound_permit_root": permit.runtime_bound_permit_root,
        "permit_generation": permit.generation,
        "effect_time_process_root": process.effect_time_process_root,
        "source_incarnation_root": request.source_incarnation_root,
        "actor": request.actor,
        "view_id": request.view_id,
        "k27_coordinate": request.k27_coordinate,
        "attempt_generation": request.attempt_generation,
    })
    return Decision(Disposition.REUSE_D0, "CURRENT_CACHE_CONSUMPTION_D0", canonical, receipt)
