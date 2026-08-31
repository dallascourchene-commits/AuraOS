#!/usr/bin/env python3
"""Execution-qualified admission for fresh or historical portable semantic evidence.

This membrane composes two exact non-self owners:
* PR664 separates exact portable reuse from semantic-generation freshness.
* PR661 separates provider/pre-job workflow state from actual job execution evidence.

The conjunction remains three-dimensional: portability/reuse, producer execution,
and semantic freshness are independent. Historical exact evidence may therefore be
execution-qualified and reusable without receiving fresh semantic-sibling credit.

Structural post-cut freshness is not itself countable sibling credit. PR664's V1
explicitly leaves producer-generation authentication false; A7 therefore exposes
that structural result as a candidate only and refuses to promote it into fresh
semantic-sibling credit until a separate typed generation-authentication owner is
bound.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

from tools import arena_portable_semantic_evidence_transfer as o61
from tools import aura_execution_aware_hyperscale_admission as execution
from tools import aura_fresh_portable_semantic_evidence_admission as fresh

VERSION = "AURA_EXECUTION_QUALIFIED_PORTABLE_EVIDENCE_ADMISSION_V1"
PR661_HEAD = "8179ffe054abc2ec144757888957c9ca27df991c"
PR661_RUN = 33396942368
PR664_HEAD = "fa428111f83a0f69319c10c1b28bde910544b776"
PR664_RUN = 33397763034
CONVERGENCE = "2e1f2c06acb98d183a2f79129a6b4bdcdd3d9512"


def _sha(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class ExecutionQualifiedPortableEvidenceReceipt:
    schema: str
    parent_heads: tuple[str, str]
    convergence_commit: str
    artifact_id: str
    producer_head: str
    producer_run: int
    producer_job: int
    producer_workflow: str
    portable_receipt_digest: str
    execution_receipt_digest: str
    portable_semantic_evidence_admitted: bool
    portable_evidence_reuse_allowed: bool
    freshness_disposition: str
    structural_freshness_candidate: bool
    producer_generation_authenticated: bool
    semantic_sibling_credit: bool
    structurally_fresh_but_generation_unauthenticated: bool
    execution_classification: str
    execution_route: str
    run_identity_exact: bool
    workflow_identity_exact: bool
    exact_producer_job_present_once: bool
    exact_producer_job_completed_success: bool
    execution_qualified_portable_semantic_evidence: bool
    historical_exact_execution_reuse: bool
    fresh_semantic_sibling_execution_qualified: bool
    provider_gate_counts_as_execution_qualified_evidence: bool
    executed_failure_counts_as_semantic_support: bool
    execution_qualification_resets_semantic_clock: bool
    execution_qualification_grants_semantic_truth: bool
    producer_authenticated: bool
    broader_claims_inherited: bool
    effect_authority_granted: bool
    semantic_k27_authority_minted: bool
    native_private_transformer_kv_accessed: bool
    gate10_promoted: bool
    merge_or_deployment_authorized: bool
    reason: str

    @property
    def receipt_digest(self) -> str:
        return _sha(asdict(self))


def classify_execution_qualified_portable_evidence(
    *,
    evidence: o61.SemanticEvidenceDescriptor,
    consumer: o61.ConsumerExpectation,
    producer_semantic_generated_at: str,
    transfer_observed_at: str,
    terminal_at: str,
    cut: str,
    artifact_id: str,
    run: dict[str, Any],
    jobs: list[dict[str, Any]],
    agent_id: str = "OTHER_AGENT",
    current_agent_id: str = "GPT56SOL_A7",
) -> ExecutionQualifiedPortableEvidenceReceipt:
    """Join portable/freshness evidence to exact provider-observed execution.

    The exact producer run/head/workflow/job must match the portable descriptor.
    PR661 owns the execution classification. A successful run label without the
    exact producer job cannot qualify portable semantic evidence.

    PR664's structural freshness result is preserved, but its own
    `producer_generation_authenticated` ceiling is authoritative: structural
    freshness cannot become countable semantic-sibling credit while that field
    is false.
    """
    portable = fresh.classify_fresh_portable_evidence(
        evidence=evidence,
        consumer=consumer,
        producer_semantic_generated_at=producer_semantic_generated_at,
        transfer_observed_at=transfer_observed_at,
        terminal_at=terminal_at,
        cut=cut,
        artifact_id=artifact_id,
        agent_id=agent_id,
        current_agent_id=current_agent_id,
    )
    routed = execution.route_workflow_through_hyperscale(
        run=run,
        jobs=jobs,
        semantic_disposition="PROCESS_DUPLICATE",
        hard_gates_pass=True,
    )

    run_exact = run.get("id") == evidence.producer_run and run.get("head_sha") == evidence.producer_head
    workflow_exact = run.get("name") == evidence.workflow_name
    exact_jobs = [job for job in jobs if job.get("id") == evidence.producer_job]
    exact_job_once = len(exact_jobs) == 1
    exact_job_success = bool(
        exact_job_once
        and exact_jobs[0].get("status") == "completed"
        and exact_jobs[0].get("conclusion") == "success"
    )
    executed_success = routed.execution_classification == "EXECUTED_JOB_SUCCESS_OBSERVED"
    qualified = bool(
        portable.portable_semantic_evidence_admitted
        and portable.portable_evidence_reuse_allowed
        and run_exact
        and workflow_exact
        and exact_job_success
        and executed_success
    )

    structural_freshness = portable.semantic_sibling_credit
    generation_authenticated = portable.producer_generation_authenticated
    semantic_sibling_credit = bool(structural_freshness and generation_authenticated)
    unauthenticated_freshness = bool(structural_freshness and not generation_authenticated)
    historical = bool(
        qualified and portable.freshness_disposition == "PRE_CUT_SEMANTIC_GENERATION"
    )
    fresh_qualified = bool(qualified and semantic_sibling_credit)

    if not portable.portable_semantic_evidence_admitted:
        reason = "PORTABLE_TRANSFER_NOT_ADMITTED"
    elif not run_exact:
        reason = "PRODUCER_RUN_OR_HEAD_MISMATCH"
    elif not workflow_exact:
        reason = "PRODUCER_WORKFLOW_MISMATCH"
    elif not exact_job_once:
        reason = "EXACT_PRODUCER_JOB_NOT_PRESENT_ONCE"
    elif not exact_job_success:
        reason = "EXACT_PRODUCER_JOB_NOT_SUCCESSFULLY_EXECUTED"
    elif not executed_success:
        reason = "WORKFLOW_EXECUTION_CLASS_NOT_SUCCESS"
    elif unauthenticated_freshness:
        reason = "EXECUTION_QUALIFIED_PORTABLE_EVIDENCE_FRESHNESS_CANDIDATE_GENERATION_UNAUTHENTICATED"
    elif semantic_sibling_credit:
        reason = "EXECUTION_QUALIFIED_FRESH_PORTABLE_SEMANTIC_EVIDENCE"
    elif historical:
        reason = "EXECUTION_QUALIFIED_HISTORICAL_PORTABLE_EVIDENCE_NO_FRESHNESS_RESET"
    else:
        reason = "EXECUTION_QUALIFIED_PORTABLE_EVIDENCE_NO_COUNTABLE_FRESHNESS"

    return ExecutionQualifiedPortableEvidenceReceipt(
        schema=VERSION,
        parent_heads=(PR664_HEAD, PR661_HEAD),
        convergence_commit=CONVERGENCE,
        artifact_id=artifact_id,
        producer_head=evidence.producer_head,
        producer_run=evidence.producer_run,
        producer_job=evidence.producer_job,
        producer_workflow=evidence.workflow_name,
        portable_receipt_digest=portable.receipt_digest,
        execution_receipt_digest=routed.receipt_digest,
        portable_semantic_evidence_admitted=portable.portable_semantic_evidence_admitted,
        portable_evidence_reuse_allowed=portable.portable_evidence_reuse_allowed,
        freshness_disposition=portable.freshness_disposition,
        structural_freshness_candidate=structural_freshness,
        producer_generation_authenticated=generation_authenticated,
        semantic_sibling_credit=semantic_sibling_credit,
        structurally_fresh_but_generation_unauthenticated=unauthenticated_freshness,
        execution_classification=routed.execution_classification,
        execution_route=routed.route,
        run_identity_exact=run_exact,
        workflow_identity_exact=workflow_exact,
        exact_producer_job_present_once=exact_job_once,
        exact_producer_job_completed_success=exact_job_success,
        execution_qualified_portable_semantic_evidence=qualified,
        historical_exact_execution_reuse=historical,
        fresh_semantic_sibling_execution_qualified=fresh_qualified,
        provider_gate_counts_as_execution_qualified_evidence=False,
        executed_failure_counts_as_semantic_support=False,
        execution_qualification_resets_semantic_clock=False,
        execution_qualification_grants_semantic_truth=False,
        producer_authenticated=False,
        broader_claims_inherited=False,
        effect_authority_granted=False,
        semantic_k27_authority_minted=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
        merge_or_deployment_authorized=False,
        reason=reason,
    )


def historical_q6_fixture() -> ExecutionQualifiedPortableEvidenceReceipt:
    evidence = o61.q6_descriptor()
    run = {
        "id": evidence.producer_run,
        "name": evidence.workflow_name,
        "head_sha": evidence.producer_head,
        "status": "completed",
        "conclusion": "success",
    }
    jobs = [{"id": evidence.producer_job, "status": "completed", "conclusion": "success"}]
    return classify_execution_qualified_portable_evidence(
        evidence=evidence,
        consumer=o61.native_expectation(evidence),
        producer_semantic_generated_at=fresh.Q6_SEMANTIC_GENERATED_AT,
        transfer_observed_at="2026-08-31T13:40:00Z",
        terminal_at="2026-08-31T13:40:01Z",
        cut=fresh.CURRENT_CUT,
        artifact_id="portable:q6:execution-qualified-history",
        run=run,
        jobs=jobs,
    )


def main() -> None:
    receipt = historical_q6_fixture()
    body = asdict(receipt)
    body["receipt_digest"] = receipt.receipt_digest
    body["laws"] = (
        "PortableEvidenceReusable!=ExecutionQualified!=FreshSemanticSibling",
        "ExactProducerRun+ExactProducerJobSuccess+PortableScopeIdentity=>ExecutionQualifiedPortableEvidence",
        "HistoricalExecutionQualifiedEvidenceMayBeReusableWithoutResettingSemanticClock",
        "CallerSuppliedGenerationTime!=ProducerGenerationAuthentication",
        "StructuralPostCutFreshness!=CountableSemanticSiblingUntilGenerationAuthenticated",
        "PreJobProviderGate!=ExecutedProducerEvidence",
        "ExecutedJobFailure!=SemanticSupport",
        "ExecutionQualification!=SemanticTruth!=ProducerAuthentication!=EffectAuthority",
        "K27CoordinateGrowth!=SemanticAuthority",
    )
    print(json.dumps(body, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
