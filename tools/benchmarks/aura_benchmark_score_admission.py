from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

SCHEMA_ID = "AURA_BENCHMARK_TASK_RECEIPT_V1"
POLICY_SCHEMA_ID = "AURA_BENCHMARK_ADMISSION_POLICY_V1"
MEASUREMENT_CLASSES = {"OBSERVED", "ESTIMATED", "UNKNOWN"}
RESULT_STATES = {"PASS", "FAIL", "ERROR", "UNKNOWN"}


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _required(value: str | None, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"MISSING_{name}")


@dataclass(frozen=True)
class BenchmarkAdmissionPolicy:
    """Trusted score-admission boundary.

    Receipt booleans and labels are evidence fields, not self-authenticating authority.
    The caller that owns score admission must supply this policy from the trusted
    benchmark control plane.
    """

    policy_generation: str
    authority_scope: str
    expected_execution_route_fingerprint: str
    trusted_execution_observer_identity: str
    trusted_source_verifier_identity: str
    execution_authority_verified: bool
    source_verifier_authority_verified: bool

    def validate(self) -> None:
        for value, name in (
            (self.policy_generation, "POLICY_GENERATION"),
            (self.authority_scope, "POLICY_AUTHORITY_SCOPE"),
            (self.expected_execution_route_fingerprint, "EXPECTED_EXECUTION_ROUTE_FINGERPRINT"),
            (self.trusted_execution_observer_identity, "TRUSTED_EXECUTION_OBSERVER_IDENTITY"),
            (self.trusted_source_verifier_identity, "TRUSTED_SOURCE_VERIFIER_IDENTITY"),
        ):
            _required(value, name)
        if type(self.execution_authority_verified) is not bool:
            raise ValueError("EXECUTION_AUTHORITY_VERIFIED_MUST_BE_BOOL")
        if type(self.source_verifier_authority_verified) is not bool:
            raise ValueError("SOURCE_VERIFIER_AUTHORITY_VERIFIED_MUST_BE_BOOL")

    def validate_receipt(self, receipt: "BenchmarkTaskReceipt") -> None:
        if receipt.authority_scope != self.authority_scope:
            raise ValueError("BENCHMARK_AUTHORITY_SCOPE_MISMATCH")
        if receipt.result_state in {"PASS", "FAIL"}:
            if not self.execution_authority_verified:
                raise ValueError("EXECUTION_AUTHORITY_NOT_VERIFIED")
            if receipt.execution_route_fingerprint != self.expected_execution_route_fingerprint:
                raise ValueError("EXECUTION_ROUTE_FINGERPRINT_MISMATCH")
            if receipt.execution_observer_identity != self.trusted_execution_observer_identity:
                raise ValueError("EXECUTION_OBSERVER_IDENTITY_MISMATCH")
            if not self.source_verifier_authority_verified:
                raise ValueError("SOURCE_VERIFIER_AUTHORITY_NOT_VERIFIED")
            if receipt.source_verifier_identity != self.trusted_source_verifier_identity:
                raise ValueError("SOURCE_VERIFIER_IDENTITY_MISMATCH")


@dataclass(frozen=True)
class BenchmarkTaskReceipt:
    campaign_id: str
    suite_id: str
    suite_generation: str
    harness_id: str
    harness_generation: str
    task_id: str
    task_input_digest: str
    agent_id: str
    agent_generation: str
    model_id: str
    run_id: str
    attempt_id: str
    result_state: str
    measurement_class: str
    wall_time_ms: float | None = None
    peak_rss_mb: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    source_verified: bool = False
    execution_observed: bool = False
    authority_scope: str = "BENCHMARK_EVIDENCE_ONLY"
    execution_route_fingerprint: str | None = None
    execution_observer_identity: str | None = None
    source_verifier_identity: str | None = None

    def validate(self) -> None:
        for name in (
            "campaign_id", "suite_id", "suite_generation", "harness_id",
            "harness_generation", "task_id", "task_input_digest", "agent_id",
            "agent_generation", "model_id", "run_id", "attempt_id", "authority_scope",
        ):
            if not getattr(self, name):
                raise ValueError(f"MISSING_{name.upper()}")
        if self.result_state not in RESULT_STATES:
            raise ValueError("INVALID_RESULT_STATE")
        if self.measurement_class not in MEASUREMENT_CLASSES:
            raise ValueError("INVALID_MEASUREMENT_CLASS")
        if type(self.source_verified) is not bool:
            raise ValueError("SOURCE_VERIFIED_MUST_BE_BOOL")
        if type(self.execution_observed) is not bool:
            raise ValueError("EXECUTION_OBSERVED_MUST_BE_BOOL")
        if self.measurement_class == "UNKNOWN":
            if any(
                value is not None
                for value in (
                    self.wall_time_ms,
                    self.peak_rss_mb,
                    self.input_tokens,
                    self.output_tokens,
                    self.cost_usd,
                )
            ):
                raise ValueError("UNKNOWN_MEASUREMENT_CANNOT_CARRY_VALUES")
        if self.measurement_class == "ESTIMATED" and self.cost_usd is not None and self.cost_usd < 0:
            raise ValueError("NEGATIVE_ESTIMATED_COST")
        for name in ("wall_time_ms", "peak_rss_mb", "cost_usd"):
            value = getattr(self, name)
            if value is not None and (not math.isfinite(value) or value < 0):
                raise ValueError(f"INVALID_{name.upper()}")
        for name in ("input_tokens", "output_tokens"):
            value = getattr(self, name)
            if value is not None and (
                not isinstance(value, int) or isinstance(value, bool) or value < 0
            ):
                raise ValueError(f"INVALID_{name.upper()}")

        if self.result_state in {"PASS", "FAIL"}:
            if not self.execution_observed:
                raise ValueError("RESULT_WITHOUT_OBSERVED_EXECUTION")
            if not self.source_verified:
                raise ValueError("RESULT_WITHOUT_VERIFIED_SOURCE")
            _required(self.execution_route_fingerprint, "EXECUTION_ROUTE_FINGERPRINT")
            _required(self.execution_observer_identity, "EXECUTION_OBSERVER_IDENTITY")
            _required(self.source_verifier_identity, "SOURCE_VERIFIER_IDENTITY")

    @property
    def score_identity(self) -> str:
        parent_state = {
            "schema_id": SCHEMA_ID,
            "campaign_id": self.campaign_id,
            "suite_id": self.suite_id,
            "suite_generation": self.suite_generation,
            "harness_id": self.harness_id,
            "harness_generation": self.harness_generation,
            "task_id": self.task_id,
            "task_input_digest": self.task_input_digest,
            "agent_id": self.agent_id,
            "agent_generation": self.agent_generation,
            "model_id": self.model_id,
            "authority_scope": self.authority_scope,
        }
        return _digest(parent_state)

    @property
    def receipt_digest(self) -> str:
        self.validate()
        return _digest(self.to_dict(include_digest=False))

    def to_dict(self, *, include_digest: bool = True) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema_id": SCHEMA_ID,
            "campaign_id": self.campaign_id,
            "suite_id": self.suite_id,
            "suite_generation": self.suite_generation,
            "harness_id": self.harness_id,
            "harness_generation": self.harness_generation,
            "task_id": self.task_id,
            "task_input_digest": self.task_input_digest,
            "agent_id": self.agent_id,
            "agent_generation": self.agent_generation,
            "model_id": self.model_id,
            "run_id": self.run_id,
            "attempt_id": self.attempt_id,
            "result_state": self.result_state,
            "measurement_class": self.measurement_class,
            "wall_time_ms": self.wall_time_ms,
            "peak_rss_mb": self.peak_rss_mb,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": self.cost_usd,
            "source_verified": self.source_verified,
            "execution_observed": self.execution_observed,
            "authority_scope": self.authority_scope,
            "execution_route_fingerprint": self.execution_route_fingerprint,
            "execution_observer_identity": self.execution_observer_identity,
            "source_verifier_identity": self.source_verifier_identity,
            "score_identity": self.score_identity,
        }
        if include_digest:
            body["receipt_digest"] = _digest(body)
        return body


def admit_score(
    receipts: Iterable[BenchmarkTaskReceipt],
    *,
    policy: BenchmarkAdmissionPolicy,
) -> dict[str, Any]:
    """Award at most one score slot per verified parent state.

    The policy is intentionally mandatory: receipt-local `source_verified` and
    `execution_observed` booleans cannot self-mint benchmark admission authority.
    """
    policy.validate()
    admitted: dict[str, BenchmarkTaskReceipt] = {}
    duplicates: list[str] = []
    for receipt in receipts:
        receipt.validate()
        policy.validate_receipt(receipt)
        key = receipt.score_identity
        existing = admitted.get(key)
        if existing is None:
            admitted[key] = receipt
            continue
        if existing.result_state != receipt.result_state:
            raise ValueError("CONTRADICTORY_RESULT_FOR_SCORE_IDENTITY")
        duplicates.append(receipt.receipt_digest)

    ordered = [admitted[key] for key in sorted(admitted)]
    passed = sum(item.result_state == "PASS" for item in ordered)
    failed = sum(item.result_state == "FAIL" for item in ordered)
    errors = sum(item.result_state == "ERROR" for item in ordered)
    unknown = sum(item.result_state == "UNKNOWN" for item in ordered)
    return {
        "policy_schema_id": POLICY_SCHEMA_ID,
        "policy_generation": policy.policy_generation,
        "unique_task_count": len(ordered),
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "unknown": unknown,
        "duplicate_process_count": len(duplicates),
        "duplicate_receipt_digests": sorted(duplicates),
        "admitted_receipt_digests": [item.receipt_digest for item in ordered],
    }
