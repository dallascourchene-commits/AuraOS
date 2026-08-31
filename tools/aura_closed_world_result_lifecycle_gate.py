#!/usr/bin/env python3
"""Closed-world result lifecycle gate for AuraOS.

D0 / HS1 / NONPROMOTING.

This generic membrane joins two independently earned laws without taking over their
owners:
- PR #666: execution-qualified evidence is not semantic truth, producer auth,
  freshness, or effect authority.
- PR #677: positive evidence cannot compensate for a failed orthogonal hard gate.

It also makes the Drive-side result contract executable: model self-report ->
validation/currentness/authority -> host observation when required -> deterministic
reducer -> optional exact-once semantic commit. Narrative text and K27/external
coordinates are non-authoritative retrieval/context surfaces.

Host execution receipts are not self-authenticating. When execution is required,
host authority must arrive through the trusted policy/control-plane input and bind
the expected route and observer identity before receipt fields can satisfy the
execution gate.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

VERSION = "AURA_CLOSED_WORLD_RESULT_LIFECYCLE_GATE_V1"
MODEL_SCHEMA = "AURA-MODEL-RESULT-v1"
HOST_SCHEMA = "AURA-HOST-EXEC-v1"
REDUCER_SCHEMA = "AURA-REDUCER-DECISION-v1"
PR666_HEAD = "49cc2947c04c1914e343d816a53d2576917523c8"
PR677_HEAD = "7ce2296763a3bfd6d13f87be6a1b3e7d89f108a7"

MODEL_DISPOSITIONS = frozenset(
    {"COMPLETED", "PARTIAL", "BLOCKED", "REFUSED", "ERROR", "UNKNOWN", "REVIEW_REQUIRED"}
)
TRANSPORT_STATES = frozenset({"NOT_STARTED", "SENT", "RETURNED", "FAILED", "UNKNOWN"})
REUSE_STATES = frozenset(
    {
        "LOOKUP_ONLY",
        "SEMANTIC_PACKET",
        "VALIDATED_PACKET",
        "MATERIAL_PRESENT",
        "DIGEST_VERIFIED",
        "VALIDATOR_CURRENT",
        "EXECUTION_COMPATIBLE",
        "NATIVE_CONSUMED",
    }
)
HEX = frozenset("0123456789abcdef")


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _required(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")


def _sha256(value: str, name: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(c not in HEX for c in value):
        raise ValueError(f"{name}_MUST_BE_SHA256_HEX")


@dataclass(frozen=True)
class ClaimRef:
    claim_id: str
    claim_class: str
    value: str
    evidence_refs: tuple[str, ...]

    def validate(self) -> None:
        _required(self.claim_id, "CLAIM_ID")
        _required(self.claim_class, "CLAIM_CLASS")
        _required(self.value, "CLAIM_VALUE")
        if not self.evidence_refs or any(
            not isinstance(ref, str) or not ref.strip() for ref in self.evidence_refs
        ):
            raise ValueError("CLAIM_EVIDENCE_REQUIRED")


@dataclass(frozen=True)
class ModelResultEnvelope:
    schema_version: str
    objective_id: str
    attempt_id: str
    worker_id: str
    disposition: str
    result_code: str
    claims: tuple[ClaimRef, ...]
    artifact_refs: tuple[str, ...]
    narrative: str | None
    output_digest: str
    source_generation_ref: str
    authority_scope: str
    consequence_key: str

    def validate(self) -> None:
        if self.schema_version != MODEL_SCHEMA:
            raise ValueError("MODEL_SCHEMA_MISMATCH")
        for value, name in (
            (self.objective_id, "OBJECTIVE_ID"),
            (self.attempt_id, "ATTEMPT_ID"),
            (self.worker_id, "WORKER_ID"),
            (self.result_code, "RESULT_CODE"),
            (self.source_generation_ref, "SOURCE_GENERATION_REF"),
            (self.authority_scope, "AUTHORITY_SCOPE"),
            (self.consequence_key, "CONSEQUENCE_KEY"),
        ):
            _required(value, name)
        if self.disposition not in MODEL_DISPOSITIONS:
            raise ValueError("UNKNOWN_MODEL_DISPOSITION")
        _sha256(self.output_digest, "OUTPUT_DIGEST")
        if len({claim.claim_id for claim in self.claims}) != len(self.claims):
            raise ValueError("DUPLICATE_CLAIM_ID")
        for claim in self.claims:
            claim.validate()
        if any(not isinstance(ref, str) or not ref.strip() for ref in self.artifact_refs):
            raise ValueError("ARTIFACT_REF_INVALID")


@dataclass(frozen=True)
class HostExecutionReceipt:
    schema_version: str
    attempt_id: str
    output_digest: str | None
    route_fingerprint: str
    provider_effect_started: bool
    provider_effect_completed: bool | None
    physical_fanout_observed: int | None
    transport_state: str
    observer_identity: str
    receipt_digest: str

    def validate(self) -> None:
        if self.schema_version != HOST_SCHEMA:
            raise ValueError("HOST_SCHEMA_MISMATCH")
        _required(self.attempt_id, "HOST_ATTEMPT_ID")
        if self.output_digest is not None:
            _sha256(self.output_digest, "HOST_OUTPUT_DIGEST")
        _required(self.route_fingerprint, "ROUTE_FINGERPRINT")
        if type(self.provider_effect_started) is not bool:
            raise ValueError("PROVIDER_EFFECT_STARTED_MUST_BE_BOOL")
        if self.provider_effect_completed is not None and type(self.provider_effect_completed) is not bool:
            raise ValueError("PROVIDER_EFFECT_COMPLETED_MUST_BE_BOOL_OR_UNKNOWN")
        if self.physical_fanout_observed is not None and (
            type(self.physical_fanout_observed) is not int or self.physical_fanout_observed < 0
        ):
            raise ValueError("PHYSICAL_FANOUT_MUST_BE_NONNEGATIVE_INT_OR_UNKNOWN")
        if self.transport_state not in TRANSPORT_STATES:
            raise ValueError("UNKNOWN_TRANSPORT_STATE")
        _required(self.observer_identity, "OBSERVER_IDENTITY")
        _sha256(self.receipt_digest, "HOST_RECEIPT_DIGEST")


@dataclass(frozen=True)
class HardGate:
    gate_id: str
    passed: bool
    blocker: str | None = None

    def validate(self) -> None:
        _required(self.gate_id, "GATE_ID")
        if type(self.passed) is not bool:
            raise ValueError("HARD_GATE_PASSED_MUST_BE_BOOL")
        if self.passed and self.blocker is not None:
            raise ValueError("PASSED_GATE_CANNOT_HAVE_BLOCKER")
        if not self.passed and (self.blocker is None or not self.blocker.strip()):
            raise ValueError("FAILED_GATE_REQUIRES_BLOCKER")


@dataclass(frozen=True)
class LifecyclePolicy:
    policy_generation_ref: str
    execution_required: bool
    physical_fanout_required: int | None
    required_artifact_refs: tuple[str, ...]
    required_claim_classes: tuple[str, ...]
    current_source_generation_ref: str
    authority_scope: str
    validation_fingerprint: str
    parent_validation_passed: bool
    contradiction_present: bool
    independent_review_required: bool
    distinct_reviewer_receipt_present: bool
    hard_gates: tuple[HardGate, ...]
    expected_route_fingerprint: str | None = None
    expected_observer_identity: str | None = None
    host_receipt_authority_verified: bool = False

    def validate(self) -> None:
        _required(self.policy_generation_ref, "POLICY_GENERATION_REF")
        if type(self.execution_required) is not bool:
            raise ValueError("EXECUTION_REQUIRED_MUST_BE_BOOL")
        if self.physical_fanout_required is not None and (
            type(self.physical_fanout_required) is not int or self.physical_fanout_required < 1
        ):
            raise ValueError("PHYSICAL_FANOUT_REQUIRED_MUST_BE_POSITIVE_INT_OR_NONE")
        _required(self.current_source_generation_ref, "CURRENT_SOURCE_GENERATION_REF")
        _required(self.authority_scope, "POLICY_AUTHORITY_SCOPE")
        _sha256(self.validation_fingerprint, "VALIDATION_FINGERPRINT")
        if type(self.parent_validation_passed) is not bool:
            raise ValueError("PARENT_VALIDATION_PASSED_MUST_BE_BOOL")
        if type(self.contradiction_present) is not bool:
            raise ValueError("CONTRADICTION_PRESENT_MUST_BE_BOOL")
        if type(self.independent_review_required) is not bool:
            raise ValueError("INDEPENDENT_REVIEW_REQUIRED_MUST_BE_BOOL")
        if type(self.distinct_reviewer_receipt_present) is not bool:
            raise ValueError("DISTINCT_REVIEWER_RECEIPT_PRESENT_MUST_BE_BOOL")
        if type(self.host_receipt_authority_verified) is not bool:
            raise ValueError("HOST_RECEIPT_AUTHORITY_VERIFIED_MUST_BE_BOOL")
        if self.execution_required:
            if self.expected_route_fingerprint is None:
                raise ValueError("EXPECTED_ROUTE_FINGERPRINT_REQUIRED")
            if self.expected_observer_identity is None:
                raise ValueError("EXPECTED_OBSERVER_IDENTITY_REQUIRED")
            _required(self.expected_route_fingerprint, "EXPECTED_ROUTE_FINGERPRINT")
            _required(self.expected_observer_identity, "EXPECTED_OBSERVER_IDENTITY")
        else:
            if self.expected_route_fingerprint is not None:
                _required(self.expected_route_fingerprint, "EXPECTED_ROUTE_FINGERPRINT")
            if self.expected_observer_identity is not None:
                _required(self.expected_observer_identity, "EXPECTED_OBSERVER_IDENTITY")
        if len({gate.gate_id for gate in self.hard_gates}) != len(self.hard_gates):
            raise ValueError("DUPLICATE_HARD_GATE_ID")
        for gate in self.hard_gates:
            gate.validate()


@dataclass(frozen=True)
class ReducerDecision:
    schema_version: str
    terminal_state: str
    reason_code: str
    failed_hard_gate_ids: tuple[str, ...]
    semantic_commit_eligible: bool
    semantic_commit_key: str | None
    reusable_evidence_eligible: bool
    model_self_report_is_execution_truth: bool = False
    narrative_can_mint_success: bool = False
    coordinate_can_satisfy_hard_gate: bool = False
    cache_hit_can_mint_evidence_truth: bool = False
    execution_qualification_grants_semantic_truth: bool = False
    evidence_can_compensate_hard_gate: bool = False
    effect_authority_granted: bool = False
    native_private_transformer_kv_accessed: bool = False
    semantic_k27_authority_minted: bool = False
    gate10_promoted: bool = False
    merge_or_deployment_authorized: bool = False

    @property
    def reducer_digest(self) -> str:
        return _sha(asdict(self))


def _decision(
    *,
    model: ModelResultEnvelope,
    policy: LifecyclePolicy,
    terminal_state: str,
    reason_code: str,
    failed_hard_gate_ids: tuple[str, ...] = (),
    semantic_commit_eligible: bool = False,
    reusable_evidence_eligible: bool = False,
) -> ReducerDecision:
    commit_key = None
    if semantic_commit_eligible:
        commit_key = _sha(
            {
                "domain": "AURA-SEMANTIC-COMMIT-v1",
                "consequence_key": model.consequence_key,
                "validation_fingerprint": policy.validation_fingerprint,
                "source_generation_ref": policy.current_source_generation_ref,
                "authority_scope": policy.authority_scope,
                "policy_generation_ref": policy.policy_generation_ref,
                "result_code": model.result_code,
            }
        )
    return ReducerDecision(
        schema_version=REDUCER_SCHEMA,
        terminal_state=terminal_state,
        reason_code=reason_code,
        failed_hard_gate_ids=failed_hard_gate_ids,
        semantic_commit_eligible=semantic_commit_eligible,
        semantic_commit_key=commit_key,
        reusable_evidence_eligible=reusable_evidence_eligible,
    )


def reduce_result_lifecycle(
    *,
    model: ModelResultEnvelope,
    policy: LifecyclePolicy,
    host: HostExecutionReceipt | None = None,
) -> ReducerDecision:
    """Reduce typed evidence to a bounded lifecycle decision.

    Ordering is fail-closed and non-compensatory. A model's narrative is never read by
    this reducer. Coordinates/cache labels are deliberately absent from admission
    inputs so they cannot satisfy source, validation, authority, review, or host gates.

    Host receipt fields cannot self-mint host authority: a trusted policy/control-plane
    input must independently verify receipt authority and bind the expected route and
    observer identity.
    """
    model.validate()
    policy.validate()
    if host is not None:
        host.validate()

    failed = tuple(sorted(gate.gate_id for gate in policy.hard_gates if not gate.passed))
    if failed:
        return _decision(
            model=model,
            policy=policy,
            terminal_state="HOLD",
            reason_code="HARD_GATE_FAILED_NONCOMPENSATORY",
            failed_hard_gate_ids=failed,
        )
    if not policy.parent_validation_passed:
        return _decision(
            model=model, policy=policy, terminal_state="HOLD",
            reason_code="PARENT_VALIDATION_NOT_CURRENT_OR_LOSSLESS"
        )
    if model.source_generation_ref != policy.current_source_generation_ref:
        return _decision(
            model=model, policy=policy, terminal_state="HOLD", reason_code="SOURCE_GENERATION_NOT_CURRENT"
        )
    if model.authority_scope != policy.authority_scope:
        return _decision(
            model=model, policy=policy, terminal_state="HOLD", reason_code="AUTHORITY_SCOPE_MISMATCH"
        )
    if policy.contradiction_present:
        return _decision(
            model=model, policy=policy, terminal_state="REVIEW", reason_code="CONTRADICTION_PRESENT"
        )
    if policy.independent_review_required and not policy.distinct_reviewer_receipt_present:
        return _decision(
            model=model, policy=policy, terminal_state="REVIEW", reason_code="DISTINCT_REVIEW_REQUIRED"
        )

    if not set(policy.required_artifact_refs).issubset(model.artifact_refs):
        return _decision(
            model=model, policy=policy, terminal_state="HOLD", reason_code="REQUIRED_ARTIFACTS_MISSING"
        )
    if not set(policy.required_claim_classes).issubset({claim.claim_class for claim in model.claims}):
        return _decision(
            model=model, policy=policy, terminal_state="HOLD", reason_code="REQUIRED_TYPED_CLAIMS_MISSING"
        )

    if policy.execution_required:
        if host is None:
            return _decision(
                model=model, policy=policy, terminal_state="HOLD", reason_code="HOST_EXECUTION_RECEIPT_REQUIRED"
            )
        if not policy.host_receipt_authority_verified:
            return _decision(
                model=model, policy=policy, terminal_state="HOLD",
                reason_code="HOST_RECEIPT_AUTHORITY_NOT_VERIFIED"
            )
        if host.route_fingerprint != policy.expected_route_fingerprint:
            return _decision(
                model=model, policy=policy, terminal_state="HOLD",
                reason_code="HOST_ROUTE_FINGERPRINT_MISMATCH"
            )
        if host.observer_identity != policy.expected_observer_identity:
            return _decision(
                model=model, policy=policy, terminal_state="HOLD",
                reason_code="HOST_OBSERVER_IDENTITY_MISMATCH"
            )
        if host.attempt_id != model.attempt_id:
            return _decision(
                model=model, policy=policy, terminal_state="HOLD", reason_code="HOST_ATTEMPT_MISMATCH"
            )
        if host.output_digest != model.output_digest:
            return _decision(
                model=model, policy=policy, terminal_state="HOLD", reason_code="HOST_OUTPUT_DIGEST_MISMATCH"
            )
        if not host.provider_effect_started or host.provider_effect_completed is not True:
            return _decision(
                model=model, policy=policy, terminal_state="HOLD", reason_code="HOST_EFFECT_NOT_COMPLETED"
            )
        if host.transport_state != "RETURNED":
            return _decision(
                model=model, policy=policy, terminal_state="HOLD", reason_code="HOST_TRANSPORT_NOT_RETURNED"
            )

    if policy.physical_fanout_required is not None:
        if host is None or host.physical_fanout_observed is None:
            return _decision(
                model=model, policy=policy, terminal_state="HOLD",
                reason_code="PHYSICAL_FANOUT_OBSERVATION_REQUIRED"
            )
        if host.physical_fanout_observed < policy.physical_fanout_required:
            return _decision(
                model=model, policy=policy, terminal_state="HOLD", reason_code="PHYSICAL_FANOUT_BELOW_POLICY"
            )

    if model.disposition in {"UNKNOWN", "REVIEW_REQUIRED", "PARTIAL"}:
        return _decision(
            model=model,
            policy=policy,
            terminal_state="REVIEW",
            reason_code=f"MODEL_DISPOSITION_{model.disposition}",
        )
    if model.disposition in {"BLOCKED", "REFUSED"}:
        return _decision(
            model=model,
            policy=policy,
            terminal_state="TERMINAL_BLOCKED",
            reason_code=f"MODEL_DISPOSITION_{model.disposition}",
            reusable_evidence_eligible=True,
        )
    if model.disposition == "ERROR":
        return _decision(
            model=model,
            policy=policy,
            terminal_state="TERMINAL_ERROR",
            reason_code="MODEL_DISPOSITION_ERROR",
            reusable_evidence_eligible=True,
        )

    return _decision(
        model=model,
        policy=policy,
        terminal_state="TERMINAL_SUCCESS",
        reason_code="ALL_CLOSED_WORLD_GATES_SATISFIED",
        semantic_commit_eligible=True,
        reusable_evidence_eligible=True,
    )


def validate_reuse_state(state: str) -> str:
    """Validate a cache/persistent-cognition state without inferring any higher state."""
    if state not in REUSE_STATES:
        raise ValueError("UNKNOWN_REUSE_STATE")
    return state


def main() -> None:
    print(
        json.dumps(
            {
                "schema": VERSION,
                "parent_heads": [PR666_HEAD, PR677_HEAD],
                "laws": [
                    "ModelSelfReport!=HostExecutionTruth",
                    "NarrativeText!=TerminalAuthority",
                    "PositiveEvidenceCannotPayHardGateDebt",
                    "ExecutionQualified!=SemanticTruth!=EffectAuthority",
                    "HostReceiptFields!=HostAuthority",
                    "HostAuthorityRequiresPolicyBoundRouteAndObserver",
                    "ConsequenceCommitOccursAfterValidationCurrentnessAndAuthority",
                    "K27Coordinate!=EvidenceTruth!=Authority!=PhysicalPlacement",
                    "CacheStateDoesNotPromoteWithoutExplicitWitness",
                ],
                "claim_ceiling": {
                    "semantic_truth_minted": False,
                    "effect_authority_granted": False,
                    "native_private_transformer_kv_accessed": False,
                    "semantic_k27_authority_minted": False,
                    "gate10_promoted": False,
                    "merge_or_deployment_authorized": False,
                },
            },
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
