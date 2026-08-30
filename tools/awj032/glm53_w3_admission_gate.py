"""Exact-generation D0 admission membrane for the AWJ032 GLM-5.3 W3 fixture.

This module intentionally does not execute a model or tensor payload. It composes
three independently versioned evidence planes before a *synthetic* tiny numerical
fixture may be attempted:

1. the current AirLLM static HARD_FALSE source-security contract;
2. the current GLM53 metadata / MTP resolver-provenance contract; and
3. a W2 official-header-bound PR350 per-expert pager source plan.

A caller-shaped packet cannot turn an older positive result into current readiness:
semantic producer generations are pinned here and any source generation change
reopens this membrane. Even an eligible result admits only a bounded synthetic W3
fixture; runtime, checkpoint payload, G2, provider, and deployment effects remain
false.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping

SCHEMA = "AWJ032GLM53W3AdmissionV1"
CURRENT_AIRLLM_SECURITY_SEMANTIC_HEAD = "e26f5228b2a7ad97aa8325593cf5550febce61ed"
CURRENT_GLM53_METADATA_SEMANTIC_HEAD = "2f5aac5c6519305aab6dec6d9849c4bb1e0c86ce"
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA64 = re.compile(r"^[0-9a-f]{64}$")


class W3AdmissionError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _bool(value: Any, code: str) -> bool:
    if type(value) is not bool:
        raise W3AdmissionError(code)
    return value


def _text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise W3AdmissionError(code)
    return value.strip()


def _sha40(value: Any, code: str) -> str:
    out = _text(value, code).lower()
    if not _SHA40.fullmatch(out):
        raise W3AdmissionError(code)
    return out


def _sha64(value: Any, code: str) -> str:
    out = _text(value, code).lower()
    if not _SHA64.fullmatch(out):
        raise W3AdmissionError(code)
    return out


def _plan_payload(plan: Any) -> dict[str, Any]:
    if hasattr(plan, "to_dict") and callable(plan.to_dict):
        raw = plan.to_dict()
    elif isinstance(plan, Mapping):
        raw = dict(plan)
    else:
        raise W3AdmissionError("PAGER_PLAN_REQUIRED")
    if not isinstance(raw, Mapping):
        raise W3AdmissionError("PAGER_PLAN_INVALID")
    source_plan_digest = _sha64(raw.get("source_plan_digest"), "PAGER_SOURCE_PLAN_DIGEST_REQUIRED")
    header_digest = _sha64(raw.get("header_evidence_digest"), "PAGER_HEADER_EVIDENCE_DIGEST_REQUIRED")
    header_receipt = _sha40(raw.get("header_receipt_digest"), "PAGER_HEADER_RECEIPT_DIGEST_REQUIRED")
    representative_header_bound = _bool(
        raw.get("representative_header_bound"), "PAGER_REPRESENTATIVE_HEADER_BOUND_BOOL_REQUIRED"
    )
    uniformity = _bool(
        raw.get("all_experts_header_uniformity_proven"),
        "PAGER_ALL_EXPERTS_UNIFORMITY_BOOL_REQUIRED",
    )
    g2 = _bool(raw.get("g2_admitted"), "PAGER_G2_BOOL_REQUIRED")
    runtime = _bool(raw.get("runtime_execution_proven"), "PAGER_RUNTIME_BOOL_REQUIRED")
    large = _bool(raw.get("large_checkpoint_admitted"), "PAGER_LARGE_CHECKPOINT_BOOL_REQUIRED")
    layer = raw.get("representative_layer")
    expert = raw.get("representative_expert")
    if isinstance(layer, bool) or not isinstance(layer, int) or layer < 0:
        raise W3AdmissionError("PAGER_REPRESENTATIVE_LAYER_REQUIRED")
    if isinstance(expert, bool) or not isinstance(expert, int) or expert < 0:
        raise W3AdmissionError("PAGER_REPRESENTATIVE_EXPERT_REQUIRED")
    return {
        "source_plan_digest": source_plan_digest,
        "header_evidence_digest": header_digest,
        "header_receipt_digest": header_receipt,
        "representative_header_bound": representative_header_bound,
        "representative_layer": layer,
        "representative_expert": expert,
        "all_experts_header_uniformity_proven": uniformity,
        "g2_admitted": g2,
        "runtime_execution_proven": runtime,
        "large_checkpoint_admitted": large,
    }


def _security_payload(evidence: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(evidence, Mapping):
        raise W3AdmissionError("AIRLLM_SECURITY_EVIDENCE_REQUIRED")
    semantic_head = _sha40(
        evidence.get("semantic_head"), "AIRLLM_SECURITY_SEMANTIC_HEAD_REQUIRED"
    )
    hosted_pass = _bool(
        evidence.get("hosted_contract_pass"), "AIRLLM_HOSTED_PASS_BOOL_REQUIRED"
    )
    static_only = _bool(
        evidence.get("static_source_security_only"), "AIRLLM_STATIC_ONLY_BOOL_REQUIRED"
    )
    hard_false = _bool(
        evidence.get("hard_false_remote_code_proven"), "AIRLLM_HARD_FALSE_BOOL_REQUIRED"
    )
    return {
        "semantic_head": semantic_head,
        "hosted_contract_pass": hosted_pass,
        "static_source_security_only": static_only,
        "hard_false_remote_code_proven": hard_false,
    }


def _metadata_payload(evidence: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(evidence, Mapping):
        raise W3AdmissionError("GLM53_METADATA_EVIDENCE_REQUIRED")
    semantic_head = _sha40(
        evidence.get("semantic_head"), "GLM53_METADATA_SEMANTIC_HEAD_REQUIRED"
    )
    hosted_pass = _bool(
        evidence.get("hosted_contract_pass"), "GLM53_METADATA_HOSTED_PASS_BOOL_REQUIRED"
    )
    resolver_provenance = _bool(
        evidence.get("resolver_provenance_proven"),
        "GLM53_RESOLVER_PROVENANCE_BOOL_REQUIRED",
    )
    source_binding = _bool(
        evidence.get("source_binding_proven"), "GLM53_SOURCE_BINDING_BOOL_REQUIRED"
    )
    return {
        "semantic_head": semantic_head,
        "hosted_contract_pass": hosted_pass,
        "resolver_provenance_proven": resolver_provenance,
        "source_binding_proven": source_binding,
    }


@dataclass(frozen=True)
class W3AdmissionReceipt:
    status: str
    blockers: tuple[str, ...]
    pager_source_plan_digest: str
    pager_header_evidence_digest: str
    pager_header_receipt_digest: str
    representative_layer: int
    representative_expert: int
    airllm_security_semantic_head: str
    glm53_metadata_semantic_head: str
    synthetic_tiny_fixture_admitted: bool
    g2_admitted: bool = False
    runtime_execution_admitted: bool = False
    checkpoint_payload_admitted: bool = False
    provider_effect_admitted: bool = False
    schema: str = SCHEMA

    @property
    def logical_id(self) -> str:
        return _digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "status": self.status,
            "blockers": list(self.blockers),
            "pager_source_plan_digest": self.pager_source_plan_digest,
            "pager_header_evidence_digest": self.pager_header_evidence_digest,
            "pager_header_receipt_digest": self.pager_header_receipt_digest,
            "representative_layer": self.representative_layer,
            "representative_expert": self.representative_expert,
            "airllm_security_semantic_head": self.airllm_security_semantic_head,
            "glm53_metadata_semantic_head": self.glm53_metadata_semantic_head,
            "synthetic_tiny_fixture_admitted": self.synthetic_tiny_fixture_admitted,
            "g2_admitted": False,
            "runtime_execution_admitted": False,
            "checkpoint_payload_admitted": False,
            "provider_effect_admitted": False,
        }


def evaluate_w3_admission(
    *,
    pager_plan: Any,
    airllm_security_evidence: Mapping[str, Any],
    glm53_metadata_evidence: Mapping[str, Any],
) -> W3AdmissionReceipt:
    plan = _plan_payload(pager_plan)
    security = _security_payload(airllm_security_evidence)
    metadata = _metadata_payload(glm53_metadata_evidence)
    blockers: list[str] = []

    if security["semantic_head"] != CURRENT_AIRLLM_SECURITY_SEMANTIC_HEAD:
        blockers.append("AIRLLM_SECURITY_GENERATION_STALE")
    if not security["hosted_contract_pass"]:
        blockers.append("AIRLLM_SECURITY_HOSTED_CONTRACT_REQUIRED")
    if not security["hard_false_remote_code_proven"]:
        blockers.append("AIRLLM_HARD_FALSE_REMOTE_CODE_REQUIRED")
    # A static scanner result is intentionally not promoted into host/import proof.
    if not security["static_source_security_only"]:
        blockers.append("AIRLLM_SECURITY_CLAIM_CEILING_INVALID")

    if metadata["semantic_head"] != CURRENT_GLM53_METADATA_SEMANTIC_HEAD:
        blockers.append("GLM53_METADATA_GENERATION_STALE")
    if not metadata["hosted_contract_pass"]:
        blockers.append("GLM53_METADATA_HOSTED_CONTRACT_REQUIRED")
    if not metadata["source_binding_proven"]:
        blockers.append("GLM53_SOURCE_BINDING_REQUIRED")
    if not metadata["resolver_provenance_proven"]:
        blockers.append("GLM53_MTP_RESOLVER_PROVENANCE_REQUIRED")

    if not plan["representative_header_bound"]:
        blockers.append("PAGER_REPRESENTATIVE_HEADER_BINDING_REQUIRED")
    if plan["all_experts_header_uniformity_proven"]:
        blockers.append("REPRESENTATIVE_HEADER_UNIVERSALIZATION_FORBIDDEN")
    if plan["g2_admitted"] or plan["runtime_execution_proven"] or plan["large_checkpoint_admitted"]:
        blockers.append("PAGER_EFFECT_CEILING_WIDENED")

    blockers = sorted(set(blockers))
    eligible = not blockers
    return W3AdmissionReceipt(
        status="ELIGIBLE_FOR_SYNTHETIC_TINY_FIXTURE" if eligible else "BLOCKED",
        blockers=tuple(blockers),
        pager_source_plan_digest=plan["source_plan_digest"],
        pager_header_evidence_digest=plan["header_evidence_digest"],
        pager_header_receipt_digest=plan["header_receipt_digest"],
        representative_layer=plan["representative_layer"],
        representative_expert=plan["representative_expert"],
        airllm_security_semantic_head=security["semantic_head"],
        glm53_metadata_semantic_head=metadata["semantic_head"],
        synthetic_tiny_fixture_admitted=eligible,
    )
