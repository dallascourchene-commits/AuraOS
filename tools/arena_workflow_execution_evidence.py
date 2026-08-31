#!/usr/bin/env python3
"""Classify GitHub workflow evidence without laundering provider state into test results.

The classifier deliberately distinguishes a run-level terminal conclusion from
job execution evidence. In particular, GitHub `action_required` with zero jobs
is a pre-job provider/approval gate, not an executed test failure.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA = "AuraWorkflowExecutionEvidenceV1"


class WorkflowEvidenceError(ValueError):
    pass


@dataclass(frozen=True)
class WorkflowExecutionEvidence:
    run_id: int
    workflow_name: str
    head_sha: str
    run_status: str
    run_conclusion: str | None
    job_count: int
    completed_job_count: int
    successful_job_count: int
    failed_job_count: int
    classification: str
    provider_pre_job_gate_observed: bool
    executed_job_failure_observed: bool
    executed_job_success_observed: bool
    semantic_test_failure_proven: bool
    semantic_test_success_proven: bool
    effect_authority: bool = False
    schema: str = SCHEMA

    def payload(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def digest(self) -> str:
        raw = json.dumps(self.payload(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()


def _require_run(run: Any) -> dict[str, Any]:
    if not isinstance(run, dict):
        raise WorkflowEvidenceError("RUN_MUST_BE_OBJECT")
    required = {"id", "name", "head_sha", "status", "conclusion"}
    if not required.issubset(run):
        raise WorkflowEvidenceError("RUN_REQUIRED_FIELDS_MISSING")
    if type(run["id"]) is not int or run["id"] <= 0:
        raise WorkflowEvidenceError("RUN_ID_INVALID")
    if not isinstance(run["name"], str) or not run["name"]:
        raise WorkflowEvidenceError("WORKFLOW_NAME_INVALID")
    if not isinstance(run["head_sha"], str) or len(run["head_sha"]) != 40:
        raise WorkflowEvidenceError("HEAD_SHA_INVALID")
    if not isinstance(run["status"], str) or not run["status"]:
        raise WorkflowEvidenceError("RUN_STATUS_INVALID")
    if run["conclusion"] is not None and not isinstance(run["conclusion"], str):
        raise WorkflowEvidenceError("RUN_CONCLUSION_INVALID")
    return run


def _require_jobs(jobs: Any) -> list[dict[str, Any]]:
    if not isinstance(jobs, list):
        raise WorkflowEvidenceError("JOBS_MUST_BE_LIST")
    out: list[dict[str, Any]] = []
    for job in jobs:
        if not isinstance(job, dict):
            raise WorkflowEvidenceError("JOB_MUST_BE_OBJECT")
        if "status" not in job or "conclusion" not in job:
            raise WorkflowEvidenceError("JOB_REQUIRED_FIELDS_MISSING")
        if not isinstance(job["status"], str):
            raise WorkflowEvidenceError("JOB_STATUS_INVALID")
        if job["conclusion"] is not None and not isinstance(job["conclusion"], str):
            raise WorkflowEvidenceError("JOB_CONCLUSION_INVALID")
        out.append(job)
    return out


def classify(run: Any, jobs: Any) -> WorkflowExecutionEvidence:
    run = _require_run(run)
    jobs = _require_jobs(jobs)

    completed = [job for job in jobs if job["status"] == "completed"]
    successes = [job for job in completed if job["conclusion"] == "success"]
    failures = [job for job in completed if job["conclusion"] == "failure"]

    if run["status"] != "completed":
        if run["status"] == "in_progress":
            classification = "RUN_IN_PROGRESS"
        else:
            classification = "RUN_NOT_YET_EXECUTION_EVIDENCE"
    elif not jobs and run["conclusion"] == "action_required":
        classification = "PRE_JOB_ACTION_REQUIRED"
    elif not jobs:
        classification = "TERMINAL_WITHOUT_JOB_EVIDENCE"
    elif failures:
        classification = "EXECUTED_JOB_FAILURE_OBSERVED"
    elif run["conclusion"] == "success" and successes:
        classification = "EXECUTED_JOB_SUCCESS_OBSERVED"
    else:
        classification = "JOB_RECORD_PRESENT_NONDECISIVE"

    return WorkflowExecutionEvidence(
        run_id=run["id"],
        workflow_name=run["name"],
        head_sha=run["head_sha"],
        run_status=run["status"],
        run_conclusion=run["conclusion"],
        job_count=len(jobs),
        completed_job_count=len(completed),
        successful_job_count=len(successes),
        failed_job_count=len(failures),
        classification=classification,
        provider_pre_job_gate_observed=(classification == "PRE_JOB_ACTION_REQUIRED"),
        executed_job_failure_observed=bool(failures),
        executed_job_success_observed=bool(successes),
        semantic_test_failure_proven=False,
        semantic_test_success_proven=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_json", type=Path)
    parser.add_argument("jobs_json", type=Path)
    args = parser.parse_args()
    run = json.loads(args.run_json.read_text(encoding="utf-8"))
    jobs_payload = json.loads(args.jobs_json.read_text(encoding="utf-8"))
    jobs = jobs_payload["jobs"] if isinstance(jobs_payload, dict) and "jobs" in jobs_payload else jobs_payload
    evidence = classify(run, jobs)
    print(json.dumps(evidence.payload() | {"receipt_digest": evidence.digest}, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
