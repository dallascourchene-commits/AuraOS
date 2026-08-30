"""Fail-closed GLM-5.3 W3 admission over the current official-W2 producer binder.

The important invariant is compositional: merely having a producer binder somewhere in
an earlier plane is not enough. The W3 consumer itself traverses
``bind_official_w2_pager_plan`` for the supplied lower pager plan. A lower-plane plan
or a caller-authored serialized wrapper therefore cannot bypass the producer proof.

This module remains D0/nonpromoting. It admits no model/tensor payload, runtime,
provider effect, checkpoint, G2, merge, or deployment. The current GLM metadata
producer still does not own MTP resolver provenance, so a caller-provided affirmative
boolean cannot clear that blocker.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping

from tools.awj032.glm53_official_w2_observation import OFFICIAL_W2_OBSERVATION
from tools.awj032.glm53_official_w2_plan_binding import (
    OfficialW2PlanBindingError,
    bind_official_w2_pager_plan,
)

SCHEMA = "AWJ032GLM53W3OfficialProducerAdmissionV1"
CURRENT_AIRLLM_SECURITY_SEMANTIC_HEAD = "e26f5228b2a7ad97aa8325593cf5550febce61ed"
CURRENT_GLM53_METADATA_SEMANTIC_HEAD = "2f5aac5c6519305aab6dec6d9849c4bb1e0c86ce"
_SHA40 = re.compile(r"^[0-9a-f]{40}$")


class W3OfficialProducerAdmissionError(ValueError):
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
        raise W3OfficialProducerAdmissionError(code)
    return value


def _sha40(value: Any, code: str) -> str:
    if not isinstance(value, str):
        raise W3OfficialProducerAdmissionError(code)
    out = value.strip().lower()
    if not _SHA40.fullmatch(out):
        raise W3OfficialProducerAdmissionError(code)
    return out


def _security_payload(evidence: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(evidence, Mapping):
        raise W3OfficialProducerAdmissionError("AIRLLM_SECURITY_EVIDENCE_REQUIRED")
    return {
        "semantic_head": _sha40(
            evidence.get("semantic_head"), "AIRLLM_SECURITY_SEMANTIC_HEAD_REQUIRED"
        ),
        "hosted_contract_pass": _bool(
            evidence.get("hosted_contract_pass"), "AIRLLM_HOSTED_PASS_BOOL_REQUIRED"
        ),
        "static_source_security_only": _bool(
            evidence.get("static_source_security_only"), "AIRLLM_STATIC_ONLY_BOOL_REQUIRED"
        ),
        "hard_false_remote_code_proven": _bool(
            evidence.get("hard_false_remote_code_proven"), "AIRLLM_HARD_FALSE_BOOL_REQUIRED"
        ),
    }


def _metadata_payload(evidence: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(evidence, Mapping):
        raise W3OfficialProducerAdmissionError("GLM53_METADATA_EVIDENCE_REQUIRED")
    return {
        "semantic_head": _sha40(
            evidence.get("semantic_head"), "GLM53_METADATA_SEMANTIC_HEAD_REQUIRED"
        ),
        "hosted_contract_pass": _bool(
            evidence.get("hosted_contract_pass"), "GLM53_METADATA_HOSTED_PASS_BOOL_REQUIRED"
        ),
        "resolver_provenance_proven": _bool(
            evidence.get("resolver_provenance_proven"),
            "GLM53_RESOLVER_PROVENANCE_BOOL_REQUIRED",
        ),
        "source_binding_proven": _bool(
            evidence.get("source_binding_proven"), "GLM53_SOURCE_BINDING_BOOL_REQUIRED"
        ),
    }


def _bind_official_plan(lower_plan: Any) -> dict[str, Any]:
    """Force the W3 consumer through the producer-owned binder.

    This deliberately does not accept a free-form OfficialW2BoundPagerPlanV1 mapping.
    The binder needs the lower plan's binding object and independently compares it to
    the immutable W2 observation before the W3 plane receives producer-proof credit.
    """
    try:
        bound = bind_official_w2_pager_plan(lower_plan)
    except OfficialW2PlanBindingError as exc:
        raise W3OfficialProducerAdmissionError(
            "OFFICIAL_W2_PRODUCER_BINDING_REQUIRED", exc.code
        ) from exc

    raw = bound.to_dict()
    o = OFFICIAL_W2_OBSERVATION
    expected = {
        "official_w2_observation_digest": o.observation_digest,
        "official_w2_receipt_digest": o.receipt_digest,
        "official_w2_producer_semantic_head": o.producer_semantic_head,
        "official_w2_producer_run_ref": o.producer_run_ref,
        "official_w2_drive_observation_ref": o.drive_observation_ref,
        "representative_layer": o.layer,
        "representative_expert": o.expert,
    }
    for key, value in expected.items():
        if raw.get(key) != value:
            raise W3OfficialProducerAdmissionError(
                "OFFICIAL_W2_PRODUCER_IDENTITY_MISMATCH", key
            )
    if raw.get("schema") != "OfficialW2BoundPagerPlanV1":
        raise W3OfficialProducerAdmissionError("OFFICIAL_W2_BOUND_PLAN_SCHEMA_REQUIRED")
    if raw.get("official_w2_producer_observation_proven") is not True:
        raise W3OfficialProducerAdmissionError("OFFICIAL_W2_PRODUCER_PROOF_REQUIRED")
    for field in (
        "all_experts_header_uniformity_proven",
        "g2_admitted",
        "runtime_execution_proven",
        "large_checkpoint_admitted",
        "authority",
    ):
        if raw.get(field) is not False:
            raise W3OfficialProducerAdmissionError("OFFICIAL_W2_EFFECT_CEILING_WIDENED", field)
    return {
        "bound_plan_digest": _digest(raw),
        "inner_source_plan_digest": str(raw["inner_source_plan_digest"]),
        **expected,
    }


@dataclass(frozen=True)
class W3OfficialProducerAdmissionReceipt:
    status: str
    blockers: tuple[str, ...]
    official_w2_bound_plan_digest: str
    inner_source_plan_digest: str
    official_w2_observation_digest: str
    official_w2_receipt_digest: str
    official_w2_producer_semantic_head: str
    official_w2_producer_run_ref: str
    official_w2_drive_observation_ref: str
    representative_layer: int
    representative_expert: int
    airllm_security_semantic_head: str
    glm53_metadata_semantic_head: str
    official_w2_producer_proof_consumed: bool = True
    synthetic_tiny_fixture_admitted: bool = False
    g2_admitted: bool = False
    runtime_execution_admitted: bool = False
    checkpoint_payload_admitted: bool = False
    provider_effect_admitted: bool = False
    authority: bool = False
    schema: str = SCHEMA

    @property
    def logical_id(self) -> str:
        return _digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "status": self.status,
            "blockers": list(self.blockers),
            "official_w2_bound_plan_digest": self.official_w2_bound_plan_digest,
            "inner_source_plan_digest": self.inner_source_plan_digest,
            "official_w2_observation_digest": self.official_w2_observation_digest,
            "official_w2_receipt_digest": self.official_w2_receipt_digest,
            "official_w2_producer_semantic_head": self.official_w2_producer_semantic_head,
            "official_w2_producer_run_ref": self.official_w2_producer_run_ref,
            "official_w2_drive_observation_ref": self.official_w2_drive_observation_ref,
            "representative_layer": self.representative_layer,
            "representative_expert": self.representative_expert,
            "airllm_security_semantic_head": self.airllm_security_semantic_head,
            "glm53_metadata_semantic_head": self.glm53_metadata_semantic_head,
            "official_w2_producer_proof_consumed": True,
            "synthetic_tiny_fixture_admitted": False,
            "g2_admitted": False,
            "runtime_execution_admitted": False,
            "checkpoint_payload_admitted": False,
            "provider_effect_admitted": False,
            "authority": False,
        }


def evaluate_w3_official_producer_admission(
    *,
    pager_plan: Any,
    airllm_security_evidence: Mapping[str, Any],
    glm53_metadata_evidence: Mapping[str, Any],
) -> W3OfficialProducerAdmissionReceipt:
    plan = _bind_official_plan(pager_plan)
    security = _security_payload(airllm_security_evidence)
    metadata = _metadata_payload(glm53_metadata_evidence)
    blockers: list[str] = []

    if security["semantic_head"] != CURRENT_AIRLLM_SECURITY_SEMANTIC_HEAD:
        blockers.append("AIRLLM_SECURITY_GENERATION_STALE")
    if not security["hosted_contract_pass"]:
        blockers.append("AIRLLM_SECURITY_HOSTED_CONTRACT_REQUIRED")
    if not security["hard_false_remote_code_proven"]:
        blockers.append("AIRLLM_HARD_FALSE_REMOTE_CODE_REQUIRED")
    if not security["static_source_security_only"]:
        blockers.append("AIRLLM_SECURITY_CLAIM_CEILING_INVALID")

    if metadata["semantic_head"] != CURRENT_GLM53_METADATA_SEMANTIC_HEAD:
        blockers.append("GLM53_METADATA_GENERATION_STALE")
    if not metadata["hosted_contract_pass"]:
        blockers.append("GLM53_METADATA_HOSTED_CONTRACT_REQUIRED")
    if not metadata["source_binding_proven"]:
        blockers.append("GLM53_SOURCE_BINDING_REQUIRED")

    # Current PR340 semantics explicitly say this producer cannot authenticate its
    # own resolver provenance. Refuse to let a caller flip the boolean to clear W3.
    blockers.append("GLM53_MTP_RESOLVER_PROVENANCE_REQUIRED")
    if metadata["resolver_provenance_proven"]:
        blockers.append("GLM53_MTP_CALLER_PROVENANCE_WIDENING_FORBIDDEN")

    blockers = sorted(set(blockers))
    return W3OfficialProducerAdmissionReceipt(
        status="BLOCKED",
        blockers=tuple(blockers),
        official_w2_bound_plan_digest=plan["bound_plan_digest"],
        inner_source_plan_digest=plan["inner_source_plan_digest"],
        official_w2_observation_digest=plan["official_w2_observation_digest"],
        official_w2_receipt_digest=plan["official_w2_receipt_digest"],
        official_w2_producer_semantic_head=plan["official_w2_producer_semantic_head"],
        official_w2_producer_run_ref=plan["official_w2_producer_run_ref"],
        official_w2_drive_observation_ref=plan["official_w2_drive_observation_ref"],
        representative_layer=plan["representative_layer"],
        representative_expert=plan["representative_expert"],
        airllm_security_semantic_head=security["semantic_head"],
        glm53_metadata_semantic_head=metadata["semantic_head"],
    )
