#!/usr/bin/env python3
"""Bind the exact PR671 official GLM-5.3 canary to PR668 execution-qualified portable evidence."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

from tools import arena_portable_semantic_evidence_transfer as o61
from tools import aura_execution_qualified_portable_evidence_admission as a7

VERSION = "AURA_GLM53_EXECUTION_QUALIFIED_OFFICIAL_CANARY_EVIDENCE_V1"
Q5_HEAD = "23c8345a1e3d5034ce88bea1ab32c69c1a9cf3f2"
Q5_RUN = 33400399223
Q5_JOB = 99515030515
Q5_WORKFLOW = "GLM53 Official Equal Rate E8 Canary"
Q5_SEMANTIC_GENERATED_AT = "2026-08-31T14:02:22Z"
Q5_TERMINAL_AT = "2026-08-31T14:07:45Z"
OBJECTIVE_CUT = "2026-08-31T14:07:46Z"
TRANSFER_OBSERVED_AT = "2026-08-31T14:08:00Z"
TRANSFER_TERMINAL_AT = "2026-08-31T14:08:01Z"
A7_HEAD = "10481aa76117c24e5fdf7f93752e7820713a8285"
A7_RUN = 33400287890
A7_JOB = 99514663480
Q5_RECEIPT_DIGEST = "00bae035570665f19c40405c8d04002f894f6a7c05c75155ce9e63d8dcf9f01a"
Q13_HEAD = "eb09b5ffd14577d1676f57bb908e5ddd81125605"
Q13_RUN = 33397035043
Q13_SOURCE_BLOB = "5d3b365911ecd78bb2698a9423807dbf13f1b5ad"
Q13_SOURCE_SET_DIGEST = "f41495beb566f4c49f5674f2820f3d5c32591647be552048cf711a885a1b71b6"
Q4_CODEC_BLOB = "8c35c47f6b162bf03324f509dc1b820b6eb689f9"
OFFICIAL_REPOSITORY = "zai-org/GLM-5.3"
OFFICIAL_REVISION = "7cda81930d6e4cef42f48555de830aa32ecdde28"
SELECTED_LAYER = 3
SELECTED_EXPERT = 0
SELECTED_SHARD = "model-00038-of-00141.safetensors"
TOTAL_WEIGHTS = 512
RATE_BPW = 1.25
AGGREGATE_OUTCOME = "E8_WIN"
AGGREGATE_E8_OVER_CONTROL = 0.6220981458103897
SCOPE = "OFFICIAL_GLM53_EQUAL_RATE_E8_REPRESENTATIVE_CANARY_DISTORTION_ONLY"
CONSUMER = "glm53.quantization.official_canary.portable_history_consumer.v1"

def _sha(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
    return hashlib.sha256(raw).hexdigest()

Q5_SUBJECT = {
    "official_repository": OFFICIAL_REPOSITORY,
    "official_revision": OFFICIAL_REVISION,
    "q13_head": Q13_HEAD,
    "q13_run": Q13_RUN,
    "q13_source_blob": Q13_SOURCE_BLOB,
    "q13_source_tensor_set_digest": Q13_SOURCE_SET_DIGEST,
    "q4_codec_blob": Q4_CODEC_BLOB,
    "selected_layer": SELECTED_LAYER,
    "selected_expert": SELECTED_EXPERT,
    "selected_shard": SELECTED_SHARD,
    "total_official_weights_observed": TOTAL_WEIGHTS,
    "codec_bpw_e8": RATE_BPW,
    "codec_bpw_control": RATE_BPW,
}
Q5_CONSEQUENCE = {
    "q5_receipt_digest": Q5_RECEIPT_DIGEST,
    "aggregate_outcome": AGGREGATE_OUTCOME,
    "aggregate_e8_over_control": AGGREGATE_E8_OVER_CONTROL,
    "representative_canary_scope_only": True,
    "geometry_privileged": False,
    "full_tensor_quantized": False,
    "whole_model_quantized": False,
    "glm_quality_proven": False,
    "runtime_performance_proven": False,
    "semantic_k27_authority": False,
    "gate10_promoted": False,
}

def q5_descriptor() -> o61.SemanticEvidenceDescriptor:
    return o61.SemanticEvidenceDescriptor(
        artifact_name="PR671_Q5_OFFICIAL_EQUAL_RATE_E8_CANARY",
        subject_digest=_sha(Q5_SUBJECT),
        producer_head=Q5_HEAD,
        producer_run=Q5_RUN,
        producer_job=Q5_JOB,
        workflow_name=Q5_WORKFLOW,
        consequence_scope=SCOPE,
        consequence_digest=_sha(Q5_CONSEQUENCE),
        native_consumer_class=CONSUMER,
    )

@dataclass(frozen=True)
class ExecutionQualifiedOfficialCanaryEvidenceReceipt:
    schema: str
    q5_receipt_digest: str
    portable_execution_receipt_digest: str
    exact_q5_receipt_identity: bool
    exact_q5_source_identity: bool
    exact_q5_scope_ceiling: bool
    exact_q5_outcome_bound: bool
    execution_qualified_portable_evidence: bool
    historical_exact_execution_reuse: bool
    semantic_sibling_credit: bool
    fresh_semantic_sibling_execution_qualified: bool
    representative_canary_scope_only: bool
    generalized_e8_superiority_proven: bool = False
    full_tensor_quantized: bool = False
    whole_model_quantized: bool = False
    glm_quality_proven: bool = False
    runtime_performance_proven: bool = False
    c2_execution_authority_granted: bool = False
    producer_authenticated: bool = False
    effect_authority_granted: bool = False
    semantic_k27_authority_minted: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False

    @property
    def receipt_digest(self) -> str:
        return _sha(asdict(self))

def validate_q5_observation(observed: dict[str, Any]) -> tuple[bool, bool, bool, bool]:
    if type(observed) is not dict:
        raise ValueError("Q5_OBSERVATION_MAPPING_REQUIRED")
    receipt = observed.get("receipt_digest") == Q5_RECEIPT_DIGEST
    source = all((
        observed.get("official_repository") == OFFICIAL_REPOSITORY,
        observed.get("official_revision") == OFFICIAL_REVISION,
        observed.get("q13_head") == Q13_HEAD,
        observed.get("q13_run") == Q13_RUN,
        observed.get("q13_source_blob") == Q13_SOURCE_BLOB,
        observed.get("q13_source_tensor_set_digest") == Q13_SOURCE_SET_DIGEST,
        observed.get("q4_codec_blob") == Q4_CODEC_BLOB,
        observed.get("selected_layer") == SELECTED_LAYER,
        observed.get("selected_expert") == SELECTED_EXPERT,
        observed.get("selected_shard") == SELECTED_SHARD,
        observed.get("total_official_weights_observed") == TOTAL_WEIGHTS,
        observed.get("codec_bpw_e8") == RATE_BPW,
        observed.get("codec_bpw_control") == RATE_BPW,
        observed.get("equal_rate") is True,
    ))
    scope = all((
        observed.get("official_source_equal_rate_distortion_evidence") is True,
        observed.get("representative_canary_scope_only") is True,
        observed.get("geometry_privileged") is False,
        observed.get("full_tensor_quantized") is False,
        observed.get("whole_model_quantized") is False,
        observed.get("glm_quality_proven") is False,
        observed.get("runtime_performance_proven") is False,
        observed.get("semantic_k27_authority") is False,
        observed.get("gate10_promoted") is False,
    ))
    outcome = (
        observed.get("aggregate_outcome") == AGGREGATE_OUTCOME
        and observed.get("aggregate_e8_over_control") == AGGREGATE_E8_OVER_CONTROL
    )
    return bool(receipt), bool(source), bool(scope), bool(outcome)

def classify_official_canary_portable_evidence(
    *, q5_observation: dict[str, Any], run: dict[str, Any], jobs: list[dict[str, Any]]
) -> ExecutionQualifiedOfficialCanaryEvidenceReceipt:
    receipt, source, scope, outcome = validate_q5_observation(q5_observation)
    if not receipt:
        raise ValueError("Q5_RECEIPT_IDENTITY_MISMATCH")
    if not source:
        raise ValueError("Q5_SOURCE_IDENTITY_MISMATCH")
    if not scope:
        raise ValueError("Q5_SCOPE_CEILING_MISMATCH")
    if not outcome:
        raise ValueError("Q5_OUTCOME_MISMATCH")
    evidence = q5_descriptor()
    joined = a7.classify_execution_qualified_portable_evidence(
        evidence=evidence,
        consumer=o61.native_expectation(evidence),
        producer_semantic_generated_at=Q5_SEMANTIC_GENERATED_AT,
        transfer_observed_at=TRANSFER_OBSERVED_AT,
        terminal_at=TRANSFER_TERMINAL_AT,
        cut=OBJECTIVE_CUT,
        artifact_id="glm53:q5:official-equal-rate-canary:execution-qualified-portable-history",
        run=run,
        jobs=jobs,
        agent_id="OTHER_AGENT_Q5",
        current_agent_id="GPT56SOL_Q15",
    )
    return ExecutionQualifiedOfficialCanaryEvidenceReceipt(
        schema=VERSION,
        q5_receipt_digest=Q5_RECEIPT_DIGEST,
        portable_execution_receipt_digest=joined.receipt_digest,
        exact_q5_receipt_identity=receipt,
        exact_q5_source_identity=source,
        exact_q5_scope_ceiling=scope,
        exact_q5_outcome_bound=outcome,
        execution_qualified_portable_evidence=joined.execution_qualified_portable_semantic_evidence,
        historical_exact_execution_reuse=joined.historical_exact_execution_reuse,
        semantic_sibling_credit=joined.semantic_sibling_credit,
        fresh_semantic_sibling_execution_qualified=joined.fresh_semantic_sibling_execution_qualified,
        representative_canary_scope_only=True,
    )

def exact_execution_fixture() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    return (
        {"id": Q5_RUN, "name": Q5_WORKFLOW, "head_sha": Q5_HEAD, "status": "completed", "conclusion": "success"},
        [{"id": Q5_JOB, "status": "completed", "conclusion": "success"}],
    )
