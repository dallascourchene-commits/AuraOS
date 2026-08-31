#!/usr/bin/env python3
"""Route workflow execution evidence into HyperScale without semantic laundering.

This child composes two exact parent owners:
* PR637 classifies provider/pre-job state versus actual job execution evidence.
* PR654 admits semantic exploration or evidence verification through bounded value channels.

The child adds one firewall only: a workflow that has not produced decisive job
execution evidence cannot enter HyperScale's semantic/evidence admission lanes.
In particular, ``action_required`` with zero jobs is a provider-eligibility HOLD,
not a failed semantic test, new SCK, new EGK, or automatic retry instruction.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Sequence

from tools.arena_workflow_execution_evidence import classify
from tools.aura_hyperscale_work_admission import EvidenceObservation, admit_work

SCHEMA = "AURA_EXECUTION_AWARE_HYPERSCALE_ADMISSION_V1"

ROUTE_PROVIDER_HOLD = "PROVIDER_ELIGIBILITY_HOLD"
ROUTE_WAIT = "WAIT_FOR_JOB_EXECUTION_EVIDENCE"
ROUTE_INSUFFICIENT = "HOLD_EXECUTION_EVIDENCE_INSUFFICIENT"
ROUTE_SEMANTIC = "SEMANTIC_ADMISSION_EVALUATED"

EXECUTED_CLASSES = {
    "EXECUTED_JOB_FAILURE_OBSERVED",
    "EXECUTED_JOB_SUCCESS_OBSERVED",
}
WAIT_CLASSES = {
    "RUN_IN_PROGRESS",
    "RUN_NOT_YET_EXECUTION_EVIDENCE",
}


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class ExecutionAwareAdmissionReceipt:
    schema: str
    workflow_run_id: int
    workflow_head_sha: str
    execution_classification: str
    execution_receipt_digest: str
    route: str
    semantic_disposition: str
    semantic_admission_evaluated: bool
    semantic_admission_payload: dict[str, Any] | None
    semantic_admission_digest: str | None
    provider_eligibility_repair_required: bool
    provider_gate_counts_as_semantic_failure: bool
    provider_gate_counts_as_new_sck: bool
    provider_gate_counts_as_new_egk: bool
    execution_evidence_grants_semantic_meaning: bool
    execution_evidence_grants_effect_authority: bool
    automatic_retry_scheduled: bool
    process_retry_inflates_evidence_mass: bool
    k27_coordinate_growth_grants_semantic_authority: bool
    native_private_transformer_kv_accessed: bool
    gate10_promoted: bool
    merge_or_deployment_authorized: bool
    reason: str

    @property
    def receipt_digest(self) -> str:
        return _sha(asdict(self))


def route_workflow_through_hyperscale(
    *,
    run: dict[str, Any],
    jobs: list[dict[str, Any]],
    semantic_disposition: str,
    hard_gates_pass: bool,
    unresolved_leaves: Sequence[str] = (),
    observations: Sequence[EvidenceObservation] = (),
    exploration_benefit_score: int = 0,
    exploration_cost_score: int = 0,
    verification_benefit_score: int = 0,
) -> ExecutionAwareAdmissionReceipt:
    """Classify execution first; only executed-job evidence can reach A4.

    ``semantic_disposition`` is deliberately *not* inferred from workflow state.
    If the execution domain is decisive, it is forwarded unchanged to PR654's
    admission owner. A separate typed semantic owner is still responsible for
    the disposition's meaning and provenance.
    """
    execution = classify(run, jobs)
    classification = execution.classification
    semantic_payload: dict[str, Any] | None = None
    semantic_digest: str | None = None
    semantic_evaluated = False
    provider_repair = False

    if classification == "PRE_JOB_ACTION_REQUIRED":
        route = ROUTE_PROVIDER_HOLD
        provider_repair = True
        reason = "PRE_JOB_PROVIDER_GATE_HAS_NO_JOB_EXECUTION_EVIDENCE"
    elif classification in WAIT_CLASSES:
        route = ROUTE_WAIT
        reason = "WORKFLOW_NOT_TERMINAL_WITH_DECISIVE_JOB_EXECUTION"
    elif classification in EXECUTED_CLASSES:
        route = ROUTE_SEMANTIC
        semantic_evaluated = True
        admission = admit_work(
            semantic_disposition=semantic_disposition,
            hard_gates_pass=hard_gates_pass,
            unresolved_leaves=unresolved_leaves,
            observations=observations,
            exploration_benefit_score=exploration_benefit_score,
            exploration_cost_score=exploration_cost_score,
            verification_benefit_score=verification_benefit_score,
        )
        semantic_payload = asdict(admission)
        semantic_digest = admission.receipt_digest
        reason = "EXECUTED_JOB_EVIDENCE_REACHED_EXISTING_HYPERSCALE_ADMISSION_OWNER"
    else:
        route = ROUTE_INSUFFICIENT
        reason = "TERMINAL_OR_JOB_RECORD_STATE_IS_NOT_DECISIVE_EXECUTION_EVIDENCE"

    return ExecutionAwareAdmissionReceipt(
        schema=SCHEMA,
        workflow_run_id=execution.run_id,
        workflow_head_sha=execution.head_sha,
        execution_classification=classification,
        execution_receipt_digest=execution.digest,
        route=route,
        semantic_disposition=semantic_disposition,
        semantic_admission_evaluated=semantic_evaluated,
        semantic_admission_payload=semantic_payload,
        semantic_admission_digest=semantic_digest,
        provider_eligibility_repair_required=provider_repair,
        provider_gate_counts_as_semantic_failure=False,
        provider_gate_counts_as_new_sck=False,
        provider_gate_counts_as_new_egk=False,
        execution_evidence_grants_semantic_meaning=False,
        execution_evidence_grants_effect_authority=False,
        automatic_retry_scheduled=False,
        process_retry_inflates_evidence_mass=False,
        k27_coordinate_growth_grants_semantic_authority=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
        merge_or_deployment_authorized=False,
        reason=reason,
    )


def provider_gate_fixture() -> ExecutionAwareAdmissionReceipt:
    run = {
        "id": 33372603380,
        "name": "K27 HDV1024 RISC-V Corpus Replay",
        "head_sha": "b6e7c1f8a5442a7f3531928a24c01c98318aed95",
        "status": "completed",
        "conclusion": "action_required",
    }
    return route_workflow_through_hyperscale(
        run=run,
        jobs=[],
        semantic_disposition="SEMANTIC_SIBLING",
        hard_gates_pass=True,
        exploration_benefit_score=100,
        exploration_cost_score=1,
    )


def main() -> None:
    receipt = provider_gate_fixture()
    body = asdict(receipt)
    body["receipt_digest"] = receipt.receipt_digest
    body["laws"] = (
        "PreJobActionRequired!=SemanticFailure",
        "ProviderEligibilityCurrentness!=CommitSemanticCurrentness",
        "ProviderGateRetry!=NewSCK!=NewEGK",
        "ExecutionEvidence!=SemanticMeaningUntilTypedOwnerBound",
        "ExecutedJobEvidenceMayReachHyperScaleButCannotDeriveSemanticDisposition",
        "K27Coordinate!=SemanticAuthority",
    )
    print(json.dumps(body, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
