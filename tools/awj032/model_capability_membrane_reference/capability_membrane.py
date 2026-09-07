from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Iterable, Optional, Tuple


class ModelFamily(str, Enum):
    QWEN3_5_DENSE = "qwen3_5_dense"
    QWEN3_8_DENSE = "qwen3_8_dense"
    QWEN4_EXP = "qwen4_exp"
    GLM_5_3 = "glm_5_3"


class Operation(str, Enum):
    STREAMED_TRAINING = "streamed_training"
    INFERENCE_PREFETCH = "inference_prefetch"


class Decision(str, Enum):
    ADMIT_D0 = "ADMIT_D0"
    HOLD_SOURCE_CURRENTNESS = "HOLD_SOURCE_CURRENTNESS"
    HOLD_RUNTIME_PROOF = "HOLD_RUNTIME_PROOF"
    HOLD_ADAPTER_IDENTITY = "HOLD_ADAPTER_IDENTITY"
    HOLD_ROUTER_SEPARATION = "HOLD_ROUTER_SEPARATION"
    HOLD_PORT_REQUIRED = "HOLD_PORT_REQUIRED"
    HOLD_OPERATION_UNSUPPORTED = "HOLD_OPERATION_UNSUPPORTED"


@dataclass(frozen=True)
class SourceBinding:
    model_revision: str
    airllm_revision: str
    topology_root: str
    tokenizer_root: str
    current: bool

    def canonical(self) -> tuple[str, ...]:
        return (
            self.model_revision,
            self.airllm_revision,
            self.topology_root,
            self.tokenizer_root,
            "current" if self.current else "stale",
        )


@dataclass(frozen=True)
class RuntimeProof:
    workcell_root: str
    attempt_root: str
    runtime_generation: str
    current: bool

    def canonical(self) -> tuple[str, ...]:
        return (
            self.workcell_root,
            self.attempt_root,
            self.runtime_generation,
            "current" if self.current else "stale",
        )


@dataclass(frozen=True)
class AdapterIdentity:
    runtime_adapter: str
    adapter_tensor_root: str
    base_tensor_root: str
    verified: bool

    def canonical(self) -> tuple[str, ...]:
        return (
            self.runtime_adapter,
            self.adapter_tensor_root,
            self.base_tensor_root,
            "verified" if self.verified else "unverified",
        )


@dataclass(frozen=True)
class PrefetchContract:
    implementation: str
    native_router_generation: str
    pager_binding_root: str
    prediction_owns_transfer_only: bool
    native_route_owns_execution: bool

    def canonical(self) -> tuple[str, ...]:
        return (
            self.implementation,
            self.native_router_generation,
            self.pager_binding_root,
            str(self.prediction_owns_transfer_only),
            str(self.native_route_owns_execution),
        )


@dataclass(frozen=True)
class ExternalEvidenceCard:
    coordinate: str
    source_url: str
    retrieved_at: str
    claim: str
    evidence_class: str

    def canonical(self) -> tuple[str, ...]:
        return (
            self.coordinate,
            self.source_url,
            self.retrieved_at,
            self.claim,
            self.evidence_class,
        )


@dataclass(frozen=True)
class CapabilityRequest:
    family: ModelFamily
    operation: Operation
    source: SourceBinding
    runtime: Optional[RuntimeProof] = None
    adapter: Optional[AdapterIdentity] = None
    prefetch: Optional[PrefetchContract] = None
    authority_epoch: str = "D0_NONPROMOTING"
    gate_state: str = "NO_GATE10"


@dataclass(frozen=True)
class AdmissionReceipt:
    decision: Decision
    reason: str
    operation_root: str
    y13: tuple[str, ...]
    k27: tuple[int, int, int]
    external_evidence_digest: str
    authority_ceiling: str = "D0_NONPROMOTING"


QWEN_TRAINING_ADAPTERS = {
    ModelFamily.QWEN3_5_DENSE: "AirLLMLoRA(AirLLMQwen3_5)",
    ModelFamily.QWEN3_8_DENSE: "AirLLMLoRA(AirLLMQwen3_5)",
    ModelFamily.QWEN4_EXP: "AirLLMLoRAQwen4Exp(AirLLMQwen4Exp)",
}

GLM_PREFETCH_IMPLEMENTATION = "GLM53RouterSeparatedPrefetch"


def _stable_hash(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(raw).hexdigest()


def _valid_nonempty(*values: str) -> bool:
    return all(isinstance(v, str) and bool(v.strip()) for v in values)


def _external_digest(cards: Iterable[ExternalEvidenceCard]) -> str:
    # External evidence is grounding/index state only. It does not participate in
    # authority or admission decisions; the digest makes that separation auditable.
    rows = sorted(card.canonical() for card in cards)
    return _stable_hash(rows)


def _diagnostic_k27(source_ok: bool, op_specific_ok: bool, proof_ok: bool) -> tuple[int, int, int]:
    # K27 is navigation only. Values are diagnostic ternary coordinates {-1,0,+1}.
    return (
        1 if source_ok else -1,
        1 if op_specific_ok else -1,
        1 if proof_ok else -1,
    )


def _build_y13(req: CapabilityRequest, decision: Decision, operation_root: str) -> tuple[str, ...]:
    # Aura 13D convention: X12 consequence-bearing state + W0 derived witness.
    x12 = (
        req.family.value,
        req.operation.value,
        req.source.model_revision,
        req.source.airllm_revision,
        req.source.topology_root,
        req.source.tokenizer_root,
        req.runtime.runtime_generation if req.runtime else "NONE",
        req.adapter.adapter_tensor_root if req.adapter else "NONE",
        req.prefetch.native_router_generation if req.prefetch else "NONE",
        req.prefetch.pager_binding_root if req.prefetch else "NONE",
        req.authority_epoch,
        req.gate_state + ":" + decision.value,
    )
    w0 = _stable_hash({"x12": x12, "operation_root": operation_root})
    return x12 + (w0,)


def admit(req: CapabilityRequest, external_evidence: Iterable[ExternalEvidenceCard] = ()) -> AdmissionReceipt:
    source_ok = req.source.current and _valid_nonempty(
        req.source.model_revision,
        req.source.airllm_revision,
        req.source.topology_root,
        req.source.tokenizer_root,
    )

    operation_payload = {
        "family": req.family.value,
        "operation": req.operation.value,
        "source": req.source.canonical(),
        "runtime": req.runtime.canonical() if req.runtime else None,
        "adapter": req.adapter.canonical() if req.adapter else None,
        "prefetch": req.prefetch.canonical() if req.prefetch else None,
        "authority_epoch": req.authority_epoch,
        "gate_state": req.gate_state,
    }
    operation_root = _stable_hash(operation_payload)

    if not source_ok:
        decision = Decision.HOLD_SOURCE_CURRENTNESS
        reason = "exact source/currentness binding is missing or stale"
        op_specific_ok = False
        proof_ok = False
    elif req.operation is Operation.STREAMED_TRAINING:
        if req.family is ModelFamily.GLM_5_3:
            decision = Decision.HOLD_PORT_REQUIRED
            reason = "GLM-5.3 streamed training has no proven AirLLM trainer port"
            op_specific_ok = False
            proof_ok = False
        elif req.family not in QWEN_TRAINING_ADAPTERS:
            decision = Decision.HOLD_OPERATION_UNSUPPORTED
            reason = "training family is outside the admitted Qwen/AirLLM set"
            op_specific_ok = False
            proof_ok = False
        elif req.runtime is None or not req.runtime.current or not _valid_nonempty(*req.runtime.canonical()[:3]):
            decision = Decision.HOLD_RUNTIME_PROOF
            reason = "proof-bound current runtime/workcell attempt is required"
            op_specific_ok = True
            proof_ok = False
        else:
            expected = QWEN_TRAINING_ADAPTERS[req.family]
            adapter_ok = (
                req.adapter is not None
                and req.adapter.verified
                and req.adapter.runtime_adapter == expected
                and _valid_nonempty(req.adapter.adapter_tensor_root, req.adapter.base_tensor_root)
                and req.adapter.adapter_tensor_root != req.adapter.base_tensor_root
            )
            if not adapter_ok:
                decision = Decision.HOLD_ADAPTER_IDENTITY
                reason = f"exact verified adapter identity required: {expected}"
                op_specific_ok = False
                proof_ok = True
            else:
                decision = Decision.ADMIT_D0
                reason = "source-bound Qwen streamed-training capability admitted at D0 only"
                op_specific_ok = True
                proof_ok = True
    elif req.operation is Operation.INFERENCE_PREFETCH:
        if req.family is not ModelFamily.GLM_5_3:
            decision = Decision.HOLD_OPERATION_UNSUPPORTED
            reason = "this reference prefetch membrane is scoped to GLM-5.3"
            op_specific_ok = False
            proof_ok = False
        else:
            prefetch_ok = (
                req.prefetch is not None
                and req.prefetch.implementation == GLM_PREFETCH_IMPLEMENTATION
                and req.prefetch.prediction_owns_transfer_only
                and req.prefetch.native_route_owns_execution
                and _valid_nonempty(req.prefetch.native_router_generation, req.prefetch.pager_binding_root)
            )
            if not prefetch_ok:
                decision = Decision.HOLD_ROUTER_SEPARATION
                reason = "prefetch may stage transfers only; native GLM router must own execution"
                op_specific_ok = False
                proof_ok = False
            else:
                decision = Decision.ADMIT_D0
                reason = "router-separated GLM-5.3 inference prefetch admitted at D0 only"
                op_specific_ok = True
                proof_ok = True
    else:
        decision = Decision.HOLD_OPERATION_UNSUPPORTED
        reason = "unknown operation"
        op_specific_ok = False
        proof_ok = False

    # External evidence cannot convert HOLD into ADMIT; it is digested for provenance only.
    ext_digest = _external_digest(external_evidence)
    return AdmissionReceipt(
        decision=decision,
        reason=reason,
        operation_root=operation_root,
        y13=_build_y13(req, decision, operation_root),
        k27=_diagnostic_k27(source_ok, op_specific_ok, proof_ok),
        external_evidence_digest=ext_digest,
    )
