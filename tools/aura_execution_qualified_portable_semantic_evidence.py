#!/usr/bin/env python3
"""Execution-qualified portable semantic-evidence composition membrane.

A7 composes, without replacing, two exact parent owners:
- PR659 owns portable semantic-evidence identity.
- PR661 owns workflow execution-state routing into HyperScale.

Portable evidence is reusable through this child only when the producer run,
head, workflow, and exact producer job are observed as the successful executed
producer generation *and* PR659 admits the exact subject/consequence/consumer
transfer. Execution success does not prove semantic truth or grant effects.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

from tools.arena_portable_semantic_evidence_transfer import (
    ConsumerExpectation,
    SemanticEvidenceDescriptor,
    classify_transfer,
    native_expectation,
    q6_descriptor,
)
from tools.aura_execution_aware_hyperscale_admission import (
    ROUTE_INSUFFICIENT,
    ROUTE_PROVIDER_HOLD,
    ROUTE_WAIT,
    route_workflow_through_hyperscale,
)

SCHEMA = "AURA_EXECUTION_QUALIFIED_PORTABLE_SEMANTIC_EVIDENCE_V1"

ADMIT = "ADMIT_EXECUTION_QUALIFIED_PORTABLE_SEMANTIC_EVIDENCE"
HOLD_PROVIDER = "HOLD_PROVIDER_ELIGIBILITY"
HOLD_WAIT = "HOLD_WAIT_FOR_EXECUTION"
HOLD_INSUFFICIENT = "HOLD_EXECUTION_EVIDENCE_INSUFFICIENT"
HOLD_FAILURE = "HOLD_EXECUTED_JOB_FAILURE"
HOLD_RUN = "HOLD_PRODUCER_RUN_IDENTITY_MISMATCH"
HOLD_HEAD = "HOLD_PRODUCER_HEAD_MISMATCH"
HOLD_WORKFLOW = "HOLD_PRODUCER_WORKFLOW_MISMATCH"
HOLD_JOB = "HOLD_EXACT_PRODUCER_JOB_NOT_SUCCESSFUL"


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


@dataclass(frozen=True)
class ExecutionQualifiedPortableReceipt:
    schema: str
    producer_descriptor_digest: str
    workflow_run_id: int
    workflow_head_sha: str
    execution_classification: str
    execution_route: str
    producer_run_exact: bool
    producer_head_exact: bool
    producer_workflow_exact: bool
    exact_producer_job_success: bool
    portable_transfer_evaluated: bool
    portable_transfer_admitted: bool
    portable_transfer_disposition: str | None
    execution_qualified_portable_evidence_admitted: bool
    disposition: str
    inherited_scope: str | None
    producer_authenticated: bool = False
    semantic_truth_proven: bool = False
    broader_claims_inherited: bool = False
    effect_authority_granted: bool = False
    semantic_k27_authority_minted: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False
    merge_or_deployment_authorized: bool = False

    @property
    def receipt_digest(self) -> str:
        return _sha(asdict(self))


def _job_success_exact(jobs: list[dict[str, Any]], producer_job: int) -> bool:
    matches = [job for job in jobs if job.get("id") == producer_job]
    return (
        len(matches) == 1
        and matches[0].get("status") == "completed"
        and matches[0].get("conclusion") == "success"
    )


def classify_execution_qualified_transfer(
    *,
    run: dict[str, Any],
    jobs: list[dict[str, Any]],
    evidence: SemanticEvidenceDescriptor,
    consumer: ConsumerExpectation,
) -> ExecutionQualifiedPortableReceipt:
    """Require decisive exact producer execution before PR659 transfer reuse."""
    evidence.validate()
    consumer.validate()

    execution = route_workflow_through_hyperscale(
        run=run,
        jobs=jobs,
        semantic_disposition="PROCESS_DUPLICATE",
        hard_gates_pass=True,
    )

    run_exact = run.get("id") == evidence.producer_run
    head_exact = run.get("head_sha") == evidence.producer_head
    workflow_exact = run.get("name") == evidence.workflow_name
    job_exact = _job_success_exact(jobs, evidence.producer_job)

    portable_evaluated = False
    portable_admitted = False
    portable_disposition: str | None = None
    inherited_scope: str | None = None

    if execution.route == ROUTE_PROVIDER_HOLD:
        disposition = HOLD_PROVIDER
    elif execution.route == ROUTE_WAIT:
        disposition = HOLD_WAIT
    elif execution.route == ROUTE_INSUFFICIENT:
        disposition = HOLD_INSUFFICIENT
    elif execution.execution_classification == "EXECUTED_JOB_FAILURE_OBSERVED":
        disposition = HOLD_FAILURE
    elif execution.execution_classification != "EXECUTED_JOB_SUCCESS_OBSERVED":
        disposition = HOLD_INSUFFICIENT
    elif not run_exact:
        disposition = HOLD_RUN
    elif not head_exact:
        disposition = HOLD_HEAD
    elif not workflow_exact:
        disposition = HOLD_WORKFLOW
    elif not job_exact:
        disposition = HOLD_JOB
    else:
        portable_evaluated = True
        transfer = classify_transfer(evidence=evidence, consumer=consumer)
        portable_admitted = transfer.portable_semantic_evidence_admitted
        portable_disposition = transfer.disposition
        inherited_scope = transfer.inherited_scope if portable_admitted else None
        disposition = ADMIT if portable_admitted else transfer.disposition

    admitted = disposition == ADMIT
    if not admitted:
        inherited_scope = None

    return ExecutionQualifiedPortableReceipt(
        schema=SCHEMA,
        producer_descriptor_digest=evidence.descriptor_digest,
        workflow_run_id=execution.workflow_run_id,
        workflow_head_sha=execution.workflow_head_sha,
        execution_classification=execution.execution_classification,
        execution_route=execution.route,
        producer_run_exact=run_exact,
        producer_head_exact=head_exact,
        producer_workflow_exact=workflow_exact,
        exact_producer_job_success=job_exact,
        portable_transfer_evaluated=portable_evaluated,
        portable_transfer_admitted=portable_admitted,
        portable_transfer_disposition=portable_disposition,
        execution_qualified_portable_evidence_admitted=admitted,
        disposition=disposition,
        inherited_scope=inherited_scope,
    )


def q6_success_fixture() -> ExecutionQualifiedPortableReceipt:
    evidence = q6_descriptor()
    run = {
        "id": evidence.producer_run,
        "name": evidence.workflow_name,
        "head_sha": evidence.producer_head,
        "status": "completed",
        "conclusion": "success",
    }
    jobs = [
        {
            "id": evidence.producer_job,
            "status": "completed",
            "conclusion": "success",
        }
    ]
    return classify_execution_qualified_transfer(
        run=run,
        jobs=jobs,
        evidence=evidence,
        consumer=native_expectation(evidence),
    )


def main() -> None:
    receipt = q6_success_fixture()
    body = asdict(receipt)
    body["receipt_digest"] = receipt.receipt_digest
    body["laws"] = (
        "PortableSemanticEvidence!=ExecutionQualifiedPortableEvidence",
        "ExecutedJobSuccess!=SemanticTruth",
        "RunSuccess!=ExactProducerJobSuccess",
        "SomeSuccessfulJob!=ProducerJobSuccess",
        "ProviderEligibility!=ProducerExecution",
        "ProducerExecutionExact+PortableIdentityExact!=EffectAuthority",
        "K27Coordinate!=SemanticAuthority",
    )
    print(json.dumps(body, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
