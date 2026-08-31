#!/usr/bin/env python3
"""Bind the exact Q5 official equal-rate canary to Aura's A7 portable execution-evidence membrane.

This adapter owns no quantizer and no scientific inference. It makes the already-owned
Q5 representative consequence safely reusable only inside its exact scope, with exact
producer execution evidence and without resetting semantic freshness.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json

from tools import arena_portable_semantic_evidence_transfer as portable
from tools import aura_execution_qualified_portable_evidence_admission as a7

VERSION = "AURA_Q5_EXECUTION_QUALIFIED_PORTABLE_SCIENTIFIC_EVIDENCE_V1"
Q5_HEAD = "23c8345a1e3d5034ce88bea1ab32c69c1a9cf3f2"
Q5_RUN = 33400399223
Q5_JOB = 99515030515
Q5_WORKFLOW = "GLM53 Official Equal Rate E8 Canary"
Q5_RECEIPT_DIGEST = "00bae035570665f19c40405c8d04002f894f6a7c05c75155ce9e63d8dcf9f01a"
Q5_SEMANTIC_GENERATED_AT = "2026-08-31T14:02:22Z"
Q5_TRANSFER_OBSERVED_AT = "2026-08-31T14:07:48Z"
CURRENT_CUT = "2026-08-31T15:24:42Z"
Q5_SCOPE = "GLM53_OFFICIAL_EQUAL_RATE_REPRESENTATIVE_CANARY_V1"
Q5_CONSUMER = "glm53.quantization.representative_scientific_evidence_consumer.v1"

Q5_SUBJECT = {
    "official_repository": "zai-org/GLM-5.3",
    "official_revision": "7cda81930d6e4cef42f48555de830aa32ecdde28",
    "source_set_digest": "f41495beb566f4c49f5674f2820f3d5c32591647be552048cf711a885a1b71b6",
    "layer": 3,
    "expert": 0,
    "tile_count": 8,
    "weights": 512,
    "candidate": "E8",
    "control": "HYPERCUBE",
    "candidate_bpw": 1.25,
    "control_bpw": 1.25,
}
Q5_CONSEQUENCE = {
    "receipt_digest": Q5_RECEIPT_DIGEST,
    "tile_outcomes": {"E8_WIN": 8, "CONTROL_WIN": 0, "TIE": 0},
    "aggregate_candidate_mse": 1.934803016678301e-05,
    "aggregate_control_mse": 3.1101250336599024e-05,
    "aggregate_e8_over_control": 0.6220981458103897,
    "representative_scope_only": True,
    "geometry_privileged": False,
    "full_tensor_quantized": False,
    "whole_model_quantized": False,
    "quality_proven": False,
    "runtime_performance_proven": False,
}


def _sha(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def q5_descriptor() -> portable.SemanticEvidenceDescriptor:
    return portable.SemanticEvidenceDescriptor(
        artifact_name="PR671_Q5_OFFICIAL_EQUAL_RATE_E8_REPRESENTATIVE_CANARY",
        subject_digest=_sha(Q5_SUBJECT),
        producer_head=Q5_HEAD,
        producer_run=Q5_RUN,
        producer_job=Q5_JOB,
        workflow_name=Q5_WORKFLOW,
        consequence_scope=Q5_SCOPE,
        consequence_digest=_sha(Q5_CONSEQUENCE),
        native_consumer_class=Q5_CONSUMER,
    )


def classify_q5(*, run: dict, jobs: list[dict], cut: str = CURRENT_CUT):
    evidence = q5_descriptor()
    receipt = a7.classify_execution_qualified_portable_evidence(
        evidence=evidence,
        consumer=portable.native_expectation(evidence),
        producer_semantic_generated_at=Q5_SEMANTIC_GENERATED_AT,
        transfer_observed_at=Q5_TRANSFER_OBSERVED_AT,
        terminal_at=Q5_TRANSFER_OBSERVED_AT,
        cut=cut,
        artifact_id="portable:q5:official-equal-rate-representative-canary",
        run=run,
        jobs=jobs,
        agent_id="OTHER_AGENT_Q5",
        current_agent_id="GPT56SOL_Q9",
    )
    return receipt


def exact_q5_execution_fixture():
    return classify_q5(
        run={
            "id": Q5_RUN,
            "name": Q5_WORKFLOW,
            "head_sha": Q5_HEAD,
            "status": "completed",
            "conclusion": "success",
        },
        jobs=[{"id": Q5_JOB, "status": "completed", "conclusion": "success"}],
    )


def main() -> None:
    receipt = exact_q5_execution_fixture()
    body = asdict(receipt)
    body["receipt_digest"] = receipt.receipt_digest
    body["q5_scientific_receipt_digest"] = Q5_RECEIPT_DIGEST
    body["scientific_scope"] = Q5_SCOPE
    body["representative_e8_over_control"] = Q5_CONSEQUENCE["aggregate_e8_over_control"]
    body["scientific_claim_ceiling_preserved"] = True
    body["laws"] = [
        "ScientificReceiptReusable!=ScientificReceiptFresh",
        "ExactProducerExecution+ExactScopeIdentity=>ExecutionQualifiedPortableScientificEvidence",
        "EvidenceTransferTime!=SemanticGenerationTime",
        "ExecutionQualification!=ScientificTruth!=SourceAuthority!=EffectAuthority",
        "RepresentativeScientificEvidence!=GeometryWideEvidence",
        "K27Coordinate!=SemanticAuthority",
    ]
    print(json.dumps(body, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
