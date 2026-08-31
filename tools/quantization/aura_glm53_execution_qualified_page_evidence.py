#!/usr/bin/env python3
"""Bind the exact Q14 official-source E8 page artifact to provider-observed execution.

Q15 is intentionally a relation owner, not another page producer and not another
workflow-execution classifier.  Q14 owns the bounded page semantics.  A7 owns the
generic law that a green label is insufficient without the exact successful
producer job.  This module freezes those two exact-green generations and admits
only their exact Q14 relation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

SCHEMA = "AURA_GLM53_EXECUTION_QUALIFIED_PAGE_EVIDENCE_V1"

Q14_HEAD = "ee70934e0c45572588829e742e512a897b23863f"
Q14_RUN = 33399560819
Q14_JOB = 99512247000
Q14_WORKFLOW = "GLM53 Official Source E8 Materialization Canary"
Q14_JOB_NAME = "q14-official-source-e8-canary"
Q14_SOURCE_BLOB = "ef26cf18731b2f6dfc3c63d08260fb64aded96f6"
Q14_PAGE_SET_DIGEST = "90c74a2badbade73ec3994211fa5d7721774905fcbd558558657a41083255975"
Q14_ARTIFACT_NAME = "q14-official-source-e8-materialization-canary"
Q14_ARTIFACT_DIGEST = "sha256:edc22355df8bfeff25f469f11b54d7948b10bbf72a831b769857068c63c77276"
Q14_DOWN_PAGE_PAYLOAD_SHA256 = "602e23735a3653eadd7a733adb028fcef8dd247a3faf078a7b629a8968538402"
Q14_GATE_UP_PAGE_PAYLOAD_SHA256 = "b47b1696ea89638660220e9f0b9a86e75d3d6a0b3c8be25fdfb7a37d58a2cb6"

A7_HEAD = "10481aa76117c24e5fdf7f93752e7820713a8285"
A7_RUN = 33400287890
A7_JOB = 99514663480
A7_WORKFLOW = "Aura Execution-Qualified Portable Evidence Admission"
A7_SOURCE_BLOB = "4ea62a80e6146ea47feb02bd22f545a933268a98"


def _sha(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class PageArtifactDescriptor:
    producer_head: str
    producer_run: int
    producer_job: int
    producer_workflow: str
    producer_job_name: str
    source_blob_sha: str
    page_set_digest: str
    artifact_name: str
    artifact_digest: str
    role_payload_sha256s: tuple[str, str]
    consequence_scope: str = "Q14_TWO_OFFICIAL_SOURCE_BOUND_TILE_PAGES_ONLY"

    @property
    def descriptor_digest(self) -> str:
        return _sha(asdict(self))


@dataclass(frozen=True)
class ExecutionQualifiedPageEvidenceReceipt:
    schema: str
    q14_descriptor_digest: str
    q14_head: str
    q14_run: int
    q14_job: int
    q14_workflow: str
    q14_page_set_digest: str
    q14_artifact_digest: str
    a7_head: str
    a7_run: int
    a7_job: int
    a7_workflow: str
    q14_semantic_descriptor_exact: bool
    provider_run_identity_exact: bool
    provider_run_completed_success: bool
    exact_producer_job_present_once: bool
    exact_producer_job_completed_success: bool
    exact_producer_job_name: bool
    exact_receipt_artifact_present_once: bool
    exact_receipt_artifact_digest: bool
    receipt_artifact_unexpired: bool
    producer_execution_observed: bool
    execution_qualified_official_source_page_evidence: bool
    later_branch_tip_may_replace_exact_generation: bool
    execution_qualification_mints_page_semantics: bool
    execution_qualification_mints_semantic_truth: bool
    full_role_page_materialization_proven: bool
    whole_model_quantization_proven: bool
    model_execution_observed: bool
    generalized_quality_proven: bool
    runtime_performance_proven: bool
    native_private_transformer_kv_accessed: bool
    semantic_k27_authority_minted: bool
    gate10_promoted: bool
    merge_or_deployment_authorized: bool
    reason: str

    @property
    def receipt_digest(self) -> str:
        return _sha(asdict(self))


def q14_descriptor() -> PageArtifactDescriptor:
    return PageArtifactDescriptor(
        producer_head=Q14_HEAD,
        producer_run=Q14_RUN,
        producer_job=Q14_JOB,
        producer_workflow=Q14_WORKFLOW,
        producer_job_name=Q14_JOB_NAME,
        source_blob_sha=Q14_SOURCE_BLOB,
        page_set_digest=Q14_PAGE_SET_DIGEST,
        artifact_name=Q14_ARTIFACT_NAME,
        artifact_digest=Q14_ARTIFACT_DIGEST,
        role_payload_sha256s=(
            Q14_DOWN_PAGE_PAYLOAD_SHA256,
            Q14_GATE_UP_PAGE_PAYLOAD_SHA256,
        ),
    )


def classify_execution_qualified_page_evidence(
    *,
    descriptor: PageArtifactDescriptor,
    run: dict[str, Any],
    jobs: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
) -> ExecutionQualifiedPageEvidenceReceipt:
    """Qualify one frozen Q14 artifact against exact provider execution records.

    This is deliberately Q14-specific.  It does not generalize A7's execution
    classifier or mint a new quantization/materialization owner.
    """
    expected = q14_descriptor()
    descriptor_exact = descriptor == expected

    run_exact = bool(
        run.get("id") == descriptor.producer_run
        and run.get("head_sha") == descriptor.producer_head
        and run.get("name") == descriptor.producer_workflow
    )
    run_success = bool(
        run_exact
        and run.get("status") == "completed"
        and run.get("conclusion") == "success"
    )

    exact_jobs = [job for job in jobs if job.get("id") == descriptor.producer_job]
    job_once = len(exact_jobs) == 1
    job_success = bool(
        job_once
        and exact_jobs[0].get("status") == "completed"
        and exact_jobs[0].get("conclusion") == "success"
    )
    job_name_exact = bool(job_once and exact_jobs[0].get("name") == descriptor.producer_job_name)

    exact_artifacts = [artifact for artifact in artifacts if artifact.get("name") == descriptor.artifact_name]
    artifact_once = len(exact_artifacts) == 1
    artifact_digest_exact = bool(
        artifact_once and exact_artifacts[0].get("digest") == descriptor.artifact_digest
    )
    artifact_unexpired = bool(artifact_once and exact_artifacts[0].get("expired") is False)

    execution_observed = bool(run_success and job_success and job_name_exact)
    qualified = bool(
        descriptor_exact
        and execution_observed
        and artifact_once
        and artifact_digest_exact
        and artifact_unexpired
    )

    if not descriptor_exact:
        reason = "Q14_SEMANTIC_DESCRIPTOR_MISMATCH"
    elif not run_exact:
        reason = "Q14_PROVIDER_RUN_IDENTITY_MISMATCH"
    elif not run_success:
        reason = "Q14_PROVIDER_RUN_NOT_COMPLETED_SUCCESS"
    elif not job_once:
        reason = "Q14_EXACT_PRODUCER_JOB_NOT_PRESENT_ONCE"
    elif not job_success:
        reason = "Q14_EXACT_PRODUCER_JOB_NOT_SUCCESS"
    elif not job_name_exact:
        reason = "Q14_EXACT_PRODUCER_JOB_NAME_MISMATCH"
    elif not artifact_once:
        reason = "Q14_EXACT_RECEIPT_ARTIFACT_NOT_PRESENT_ONCE"
    elif not artifact_digest_exact:
        reason = "Q14_RECEIPT_ARTIFACT_DIGEST_MISMATCH"
    elif not artifact_unexpired:
        reason = "Q14_RECEIPT_ARTIFACT_EXPIRED"
    else:
        reason = "EXECUTION_QUALIFIED_OFFICIAL_SOURCE_PAGE_EVIDENCE"

    return ExecutionQualifiedPageEvidenceReceipt(
        schema=SCHEMA,
        q14_descriptor_digest=descriptor.descriptor_digest,
        q14_head=descriptor.producer_head,
        q14_run=descriptor.producer_run,
        q14_job=descriptor.producer_job,
        q14_workflow=descriptor.producer_workflow,
        q14_page_set_digest=descriptor.page_set_digest,
        q14_artifact_digest=descriptor.artifact_digest,
        a7_head=A7_HEAD,
        a7_run=A7_RUN,
        a7_job=A7_JOB,
        a7_workflow=A7_WORKFLOW,
        q14_semantic_descriptor_exact=descriptor_exact,
        provider_run_identity_exact=run_exact,
        provider_run_completed_success=run_success,
        exact_producer_job_present_once=job_once,
        exact_producer_job_completed_success=job_success,
        exact_producer_job_name=job_name_exact,
        exact_receipt_artifact_present_once=artifact_once,
        exact_receipt_artifact_digest=artifact_digest_exact,
        receipt_artifact_unexpired=artifact_unexpired,
        producer_execution_observed=execution_observed,
        execution_qualified_official_source_page_evidence=qualified,
        later_branch_tip_may_replace_exact_generation=False,
        execution_qualification_mints_page_semantics=False,
        execution_qualification_mints_semantic_truth=False,
        full_role_page_materialization_proven=False,
        whole_model_quantization_proven=False,
        model_execution_observed=False,
        generalized_quality_proven=False,
        runtime_performance_proven=False,
        native_private_transformer_kv_accessed=False,
        semantic_k27_authority_minted=False,
        gate10_promoted=False,
        merge_or_deployment_authorized=False,
        reason=reason,
    )


def exact_fixture() -> ExecutionQualifiedPageEvidenceReceipt:
    d = q14_descriptor()
    run = {
        "id": Q14_RUN,
        "head_sha": Q14_HEAD,
        "name": Q14_WORKFLOW,
        "status": "completed",
        "conclusion": "success",
    }
    jobs = [{
        "id": Q14_JOB,
        "name": Q14_JOB_NAME,
        "status": "completed",
        "conclusion": "success",
    }]
    artifacts = [{
        "name": Q14_ARTIFACT_NAME,
        "digest": Q14_ARTIFACT_DIGEST,
        "expired": False,
    }]
    return classify_execution_qualified_page_evidence(
        descriptor=d,
        run=run,
        jobs=jobs,
        artifacts=artifacts,
    )


def main() -> None:
    receipt = exact_fixture()
    body = asdict(receipt)
    body["receipt_digest"] = receipt.receipt_digest
    body["laws"] = (
        "PageMaterialized+WorkflowGreen!=ExecutionQualifiedPageEvidence",
        "ExactPageSet+ExactProducerGeneration+ExactSuccessfulJob+ExactReceiptArtifact=>ExecutionQualifiedPageEvidence",
        "LaterMutableBranchTip!=FrozenExactGreenGeneration",
        "ExecutionQualification!=PageSemanticOwnership!=SemanticTruth",
        "ExecutionQualifiedTilePages!=FullRolePages!=WholeModelQuantization!=ModelExecution",
        "K27Coordinate!=SemanticAuthority",
    )
    print(json.dumps(body, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
