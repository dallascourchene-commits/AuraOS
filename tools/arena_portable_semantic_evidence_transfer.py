#!/usr/bin/env python3
"""Portable semantic-evidence transfer membrane for AuraOS Arena artifacts.

Green execution is necessary but not sufficient for semantic reuse. This V1
admits evidence only when subject identity, producer generation, hosted job,
consequence scope, consequence identity, and consumer class are all exact.

Frozen exemplars:
- PR #640 semantic generation 4137aabd... / run 33370305329 / job 99419644910
- PR #638 semantic generation 21e67a4a... / provider-observed run 33370308884 / job 99419657614

This contract does not authenticate a human producer, prove semantic truth,
grant effect authority, mint semantic K27 authority, access native/private
transformer KV state, or promote Gate-10.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

VERSION = "AURA_ARENA_PORTABLE_SEMANTIC_EVIDENCE_TRANSFER_V1"

Q6_HEAD = "4137aabd972feff9c4412bb4786ef8fd4de207e0"
Q6_RUN = 33370305329
Q6_JOB = 99419644910
Q6_WORKFLOW = "GLM53 Quantization Evidence Transfer"

R3_HEAD = "21e67a4a744806d7637f6d6d68e97801f692fef6"
R3_RUN = 33370308884
R3_JOB = 99419657614
R3_WORKFLOW = "K27 HDV1024 RISC-V Corpus Replay"
R3_STALE_PR_PROSE_RUN = 33371434136

Q6_SCOPE = "REPRESENTATION_EXACT_SYNTHETIC_EVIDENCE_TRANSFER_DISPOSITION"
R3_SCOPE = "HDV1024_LOGICAL_CONSEQUENCE_AGREEMENT"
Q6_CONSUMER = "glm53.quantization.representation_evidence_consumer.v1"
R3_CONSUMER = "k27.hdv1024.logical_consequence_consumer.v1"

Q6_SUBJECT = {
    "domain": "glm53-quantization",
    "source_representation": "E8_ROOT_240_U8_V1",
    "target_representation": "AURA_E8_BALL10_16BIT_REF_V1",
    "source_scope": "SYNTHETIC_DISTORTION_ONLY",
    "expected_disposition": "DIFFERENT_REPRESENTATION_NO_EVIDENCE_TRANSFER",
}
R3_SUBJECT = {
    "domain": "k27-hdv1024",
    "corpus_sha256": "30014dc3d6e16454a41c91599460dddb2b72aa947fbf297f7b6985e543884b85",
    "expected_distances": [0, 1024, 1, 1, 1024, 4, 472, 510],
    "implementation_scope": "PR623_RISCV_SOFTWARE_REFERENCE_ONLY",
}


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha256_field(name: str, value: str) -> None:
    if (
        type(value) is not str
        or len(value) != 64
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise ValueError("INVALID_SHA256:" + name)


def _head_field(name: str, value: str) -> None:
    if (
        type(value) is not str
        or len(value) != 40
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise ValueError("INVALID_GIT_HEAD:" + name)


@dataclass(frozen=True)
class SemanticEvidenceDescriptor:
    artifact_name: str
    subject_digest: str
    producer_head: str
    producer_run: int
    producer_job: int
    workflow_name: str
    consequence_scope: str
    consequence_digest: str
    native_consumer_class: str

    def validate(self) -> None:
        if not self.artifact_name.strip():
            raise ValueError("ARTIFACT_NAME_REQUIRED")
        _sha256_field("subject_digest", self.subject_digest)
        _head_field("producer_head", self.producer_head)
        for name in ("producer_run", "producer_job"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError("INVALID_POSITIVE_INT:" + name)
        if not self.workflow_name.strip():
            raise ValueError("WORKFLOW_NAME_REQUIRED")
        if not self.consequence_scope.strip():
            raise ValueError("CONSEQUENCE_SCOPE_REQUIRED")
        _sha256_field("consequence_digest", self.consequence_digest)
        if not self.native_consumer_class.strip():
            raise ValueError("CONSUMER_CLASS_REQUIRED")

    @property
    def descriptor_digest(self) -> str:
        self.validate()
        return _sha(asdict(self))


@dataclass(frozen=True)
class ConsumerExpectation:
    subject_digest: str
    producer_head: str
    producer_run: int
    producer_job: int
    consequence_scope: str
    consequence_digest: str
    consumer_class: str

    def validate(self) -> None:
        _sha256_field("subject_digest", self.subject_digest)
        _head_field("producer_head", self.producer_head)
        for name in ("producer_run", "producer_job"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError("INVALID_EXPECTED_POSITIVE_INT:" + name)
        if not self.consequence_scope.strip():
            raise ValueError("EXPECTED_SCOPE_REQUIRED")
        _sha256_field("consequence_digest", self.consequence_digest)
        if not self.consumer_class.strip():
            raise ValueError("EXPECTED_CONSUMER_CLASS_REQUIRED")


@dataclass(frozen=True)
class EvidenceTransferReceipt:
    version: str
    producer_descriptor_digest: str
    subject_identity_exact: bool
    producer_generation_exact: bool
    producer_job_exact: bool
    consequence_scope_exact: bool
    consequence_identity_exact: bool
    consumer_identity_exact: bool
    disposition: str
    portable_semantic_evidence_admitted: bool
    inherited_scope: str | None
    producer_authenticated: bool = False
    semantic_truth_proven: bool = False
    broader_claims_inherited: bool = False
    effect_authority_granted: bool = False
    semantic_k27_authority_minted: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False

    @property
    def receipt_digest(self) -> str:
        return _sha(asdict(self))


def q6_descriptor() -> SemanticEvidenceDescriptor:
    return SemanticEvidenceDescriptor(
        artifact_name="PR640_Q6_REPRESENTATION_EXACT_EVIDENCE_TRANSFER",
        subject_digest=_sha(Q6_SUBJECT),
        producer_head=Q6_HEAD,
        producer_run=Q6_RUN,
        producer_job=Q6_JOB,
        workflow_name=Q6_WORKFLOW,
        consequence_scope=Q6_SCOPE,
        consequence_digest=_sha(
            {
                "disposition": "DIFFERENT_REPRESENTATION_NO_EVIDENCE_TRANSFER",
                "glm53_tensor_gain_inherited": False,
                "coding_quality_inherited": False,
                "runtime_performance_inherited": False,
            }
        ),
        native_consumer_class=Q6_CONSUMER,
    )


def r3_descriptor() -> SemanticEvidenceDescriptor:
    return SemanticEvidenceDescriptor(
        artifact_name="PR638_R3_HDV1024_RISCV_CORPUS_REPLAY",
        subject_digest=_sha(R3_SUBJECT),
        producer_head=R3_HEAD,
        producer_run=R3_RUN,
        producer_job=R3_JOB,
        workflow_name=R3_WORKFLOW,
        consequence_scope=R3_SCOPE,
        consequence_digest=_sha(
            {
                "all_logical_consequences_match": True,
                "expected_distances": R3_SUBJECT["expected_distances"],
                "byte_serialization_bound": False,
                "compiler_abi_bound": False,
                "riscv_instruction_execution_proven": False,
                "hardware_performance_proven": False,
            }
        ),
        native_consumer_class=R3_CONSUMER,
    )


def native_expectation(evidence: SemanticEvidenceDescriptor) -> ConsumerExpectation:
    evidence.validate()
    return ConsumerExpectation(
        subject_digest=evidence.subject_digest,
        producer_head=evidence.producer_head,
        producer_run=evidence.producer_run,
        producer_job=evidence.producer_job,
        consequence_scope=evidence.consequence_scope,
        consequence_digest=evidence.consequence_digest,
        consumer_class=evidence.native_consumer_class,
    )


def classify_transfer(
    *, evidence: SemanticEvidenceDescriptor, consumer: ConsumerExpectation
) -> EvidenceTransferReceipt:
    evidence.validate()
    consumer.validate()

    subject_ok = evidence.subject_digest == consumer.subject_digest
    generation_ok = (
        evidence.producer_head == consumer.producer_head
        and evidence.producer_run == consumer.producer_run
    )
    job_ok = evidence.producer_job == consumer.producer_job
    scope_ok = evidence.consequence_scope == consumer.consequence_scope
    consequence_ok = evidence.consequence_digest == consumer.consequence_digest
    consumer_ok = evidence.native_consumer_class == consumer.consumer_class

    checks = [
        ("SUBJECT_IDENTITY_MISMATCH", subject_ok),
        ("PRODUCER_GENERATION_MISMATCH", generation_ok),
        ("PRODUCER_JOB_MISMATCH", job_ok),
        ("CONSEQUENCE_SCOPE_MISMATCH", scope_ok),
        ("CONSEQUENCE_IDENTITY_MISMATCH", consequence_ok),
        ("CONSUMER_IDENTITY_MISMATCH", consumer_ok),
    ]
    failures = [name for name, ok in checks if not ok]
    admitted = not failures
    disposition = (
        "ADMIT_EXACT_PORTABLE_SEMANTIC_EVIDENCE"
        if admitted
        else "HOLD_" + "__".join(failures)
    )

    return EvidenceTransferReceipt(
        version=VERSION,
        producer_descriptor_digest=evidence.descriptor_digest,
        subject_identity_exact=subject_ok,
        producer_generation_exact=generation_ok,
        producer_job_exact=job_ok,
        consequence_scope_exact=scope_ok,
        consequence_identity_exact=consequence_ok,
        consumer_identity_exact=consumer_ok,
        disposition=disposition,
        portable_semantic_evidence_admitted=admitted,
        inherited_scope=evidence.consequence_scope if admitted else None,
    )


def portable_current_receipt() -> dict[str, Any]:
    q6 = classify_transfer(
        evidence=q6_descriptor(), consumer=native_expectation(q6_descriptor())
    )
    r3 = classify_transfer(
        evidence=r3_descriptor(), consumer=native_expectation(r3_descriptor())
    )
    cross = classify_transfer(
        evidence=q6_descriptor(), consumer=native_expectation(r3_descriptor())
    )
    payload = {
        "version": VERSION,
        "q6_native": {**asdict(q6), "receipt_digest": q6.receipt_digest},
        "r3_native": {**asdict(r3), "receipt_digest": r3.receipt_digest},
        "q6_to_r3_cross_domain": {
            **asdict(cross),
            "receipt_digest": cross.receipt_digest,
        },
        "stale_pr_prose_run_rejected": R3_STALE_PR_PROSE_RUN != R3_RUN,
        "provider_observed_r3_run": R3_RUN,
    }
    return {**payload, "portable_receipt_digest": _sha(payload)}


def main() -> None:
    print(json.dumps(portable_current_receipt(), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
