#!/usr/bin/env python3
"""Q22: bind bounded materialization/evidence support to exact lifecycle lineage.

D0 / HS1 / NONPROMOTING.

Exactly two post-Q20 hosted other-Agent artifacts are consumed:
- PR #708: authority/materialization proposal conformance.
- PR #709: pre-attempt -> terminal lifecycle lineage association.

This membrane proves only that the Q21 lineage's *base* proposal basis is the exact
Q19 basis from which PR708 derives its richer materialization-bound basis. It then
content-addresses the bounded support and lifecycle lineage together.

It does NOT prove that PR708 support/currentness was revalidated at pre-attempt or
effect time, that the support caused execution, or that any execution/effect was
authorized. Those remain explicit successor gates.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping

from tools import aura_authority_materialization_proposal_conformance as support_owner

SCHEMA = "AURA-MATERIALIZATION-SUPPORT-LIFECYCLE-LINEAGE-v1"
LINEAGE_SCHEMA = "AURA-PRE-ATTEMPT-LIFECYCLE-LINEAGE-v1"
SUPPORT_PROOF_HEAD = "361b01579ab2debc34f4b836c3ea605de635a8c3"
SUPPORT_RUN = 33411109838
SUPPORT_JOB = 99550608648
LINEAGE_PROOF_HEAD = "e83d18126cae4e95abf679f74ee585e6a4025831"
LINEAGE_RUN = 33410723482
LINEAGE_JOB = 99549322339
HEX = frozenset("0123456789abcdef")


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha256(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in HEX for c in value):
        raise ValueError(f"{name}_MUST_BE_SHA256_HEX")
    return value


def _required(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")
    return value


def _exact_bool(value: Any, expected: bool, name: str) -> None:
    if type(value) is not bool or value is not expected:
        raise ValueError(f"{name}_MUST_BE_EXACT_{str(expected).upper()}")


def _validate_support(decision: support_owner.ConformanceDecision) -> None:
    if not isinstance(decision, support_owner.ConformanceDecision):
        raise ValueError("Q22_SUPPORT_MUST_BE_PR708_TYPED_DECISION")
    if decision.disposition != "CONFORMANT_BOUNDED_SUPPORT":
        raise ValueError("Q22_SUPPORT_NOT_CONFORMANT")
    if decision.reason_code != "MATERIALIZATION_PROPOSAL_AND_AUTHORITY_SCOPED_EVIDENCE_COMMUTE":
        raise ValueError("Q22_SUPPORT_REASON_MISMATCH")
    if decision.proposal_basis_digest != support_owner.q20_materialization_bound_basis_digest():
        raise ValueError("Q22_MATERIALIZATION_BOUND_BASIS_MISMATCH")
    if decision.materialization_relation_digest != support_owner.q20_materialization_relation_digest():
        raise ValueError("Q22_MATERIALIZATION_RELATION_MISMATCH")
    if decision.proposal_representation_fingerprint != support_owner.q20_representation_fingerprint():
        raise ValueError("Q22_SUPPORT_REPRESENTATION_MISMATCH")
    if decision.evidence_representation_fingerprint != decision.proposal_representation_fingerprint:
        raise ValueError("Q22_SUPPORT_EVIDENCE_REPRESENTATION_DIVERGENCE")
    for value, name in (
        (decision.authority_fingerprint, "Q22_AUTHORITY_FINGERPRINT"),
        (decision.admission_policy_fingerprint, "Q22_ADMISSION_POLICY_FINGERPRINT"),
        (decision.evidence_admission_fingerprint, "Q22_EVIDENCE_ADMISSION_FINGERPRINT"),
        (decision.proposal_evidence_support_digest, "Q22_PROPOSAL_EVIDENCE_SUPPORT_DIGEST"),
        (decision.receipt_digest, "Q22_SUPPORT_RECEIPT_DIGEST"),
    ):
        _sha256(value, name)
    _exact_bool(
        decision.bounded_evidence_supports_exact_proposal,
        True,
        "Q22_BOUNDED_SUPPORTS_EXACT_PROPOSAL",
    )
    for value, name in (
        (decision.live_proposal_currentness_resolved, "Q22_SUPPORT_LIVE_CURRENTNESS"),
        (decision.execution_authorized, "Q22_SUPPORT_EXECUTION_AUTHORITY"),
        (decision.provider_effect_authorized, "Q22_SUPPORT_PROVIDER_EFFECT"),
        (decision.semantic_k27_authority, "Q22_SUPPORT_SEMANTIC_K27"),
        (decision.native_private_transformer_kv_accessed, "Q22_SUPPORT_NATIVE_KV"),
        (decision.gate10_promoted, "Q22_SUPPORT_GATE10"),
        (decision.merge_or_deployment_authorized, "Q22_SUPPORT_MERGE_DEPLOY"),
    ):
        _exact_bool(value, False, name)


LINEAGE_FALSE = (
    "route_observer_to_host_witness_relation_proven",
    "pre_attempt_caused_execution",
    "pre_attempt_authorized_execution",
    "terminal_result_retroactively_authorizes_pre_attempt",
    "execution_lease_minted",
    "execution_authority_granted",
    "provider_effect_authority_granted",
    "semantic_k27_authority_minted",
    "native_private_transformer_kv_accessed",
    "gate10_promoted",
    "merge_deploy_spend_public_financial_human_effect_authorized",
)


def _validate_lineage(receipt: Mapping[str, Any]) -> None:
    if receipt.get("schema") != LINEAGE_SCHEMA:
        raise ValueError("Q22_LINEAGE_SCHEMA_MISMATCH")
    if receipt.get("o65_head") != "7efca33d95f6dc39c4e159250d45373b260060ed":
        raise ValueError("Q22_LINEAGE_O65_HEAD_MISMATCH")
    if receipt.get("o65_run") != 33410032496:
        raise ValueError("Q22_LINEAGE_O65_RUN_MISMATCH")
    if receipt.get("lifecycle_head") != "22e72fd3de7b008752bbb5176347d61518f4e83a":
        raise ValueError("Q22_LINEAGE_LIFECYCLE_HEAD_MISMATCH")
    if receipt.get("lifecycle_run") != 33409821076:
        raise ValueError("Q22_LINEAGE_LIFECYCLE_RUN_MISMATCH")
    for key in (
        "proposal_id",
        "proposal_basis_digest",
        "pre_attempt_id",
        "pre_attempt_policy_digest",
        "concurrency_scope_digest",
        "lifecycle_model_output_digest",
        "lifecycle_semantic_commit_key",
        "lineage_digest",
    ):
        _sha256(receipt.get(key), f"Q22_LINEAGE_{key.upper()}")
    for key in (
        "owner_state_epoch",
        "pre_attempt_policy_generation",
        "expected_route_fingerprint",
        "expected_observer_identity",
        "lifecycle_model_objective_id",
        "lifecycle_model_attempt_id",
        "lifecycle_source_generation",
        "lifecycle_authority_scope",
        "lifecycle_terminal_state",
        "lifecycle_reason_code",
    ):
        _required(receipt.get(key), f"Q22_LINEAGE_{key.upper()}")
    _exact_bool(receipt.get("proposal_identity_shared"), True, "Q22_PROPOSAL_IDENTITY_SHARED")
    _exact_bool(receipt.get("lineage_association_bound"), True, "Q22_LINEAGE_ASSOCIATION_BOUND")
    _exact_bool(
        receipt.get("effect_boundary_revalidation_still_required"),
        True,
        "Q22_EFFECT_BOUNDARY_REVALIDATION",
    )
    for key in LINEAGE_FALSE:
        _exact_bool(receipt.get(key), False, f"Q22_LINEAGE_{key.upper()}")
    supplied = _sha256(receipt.get("receipt_digest"), "Q22_LINEAGE_RECEIPT_DIGEST")
    body = dict(receipt)
    body.pop("receipt_digest", None)
    expected = _sha({"domain": LINEAGE_SCHEMA, "receipt": body})
    if supplied != expected:
        raise ValueError("Q22_LINEAGE_RECEIPT_DIGEST_MISMATCH")


@dataclass(frozen=True)
class MaterializationSupportedLifecycleLineageReceipt:
    schema: str
    support_proof_head: str
    support_run: int
    support_job: int
    lineage_proof_head: str
    lineage_run: int
    lineage_job: int
    proposal_id: str
    base_proposal_basis_digest: str
    materialization_bound_proposal_basis_digest: str
    base_to_materialization_relation_digest: str
    materialization_relation_digest: str
    representation_fingerprint: str
    authority_fingerprint: str
    admission_policy_fingerprint: str
    evidence_admission_fingerprint: str
    proposal_evidence_support_digest: str
    pre_attempt_id: str
    owner_state_epoch: str
    pre_attempt_policy_generation: str
    lifecycle_model_attempt_id: str
    lifecycle_model_output_digest: str
    lifecycle_semantic_commit_key: str
    lineage_digest: str
    supported_lineage_digest: str
    bounded_support_associated_with_lineage: bool = True
    support_live_currentness_revalidated_for_lineage: bool = False
    support_fresh_at_pre_attempt_proven: bool = False
    support_fresh_at_effect_boundary_proven: bool = False
    support_caused_execution: bool = False
    execution_authorized: bool = False
    execution_lease_minted: bool = False
    provider_effect_authorized: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False
    merge_deploy_spend_public_financial_human_effect_authorized: bool = False

    @property
    def receipt_digest(self) -> str:
        return _sha({"domain": SCHEMA, "receipt": asdict(self)})

    def validate_claim_ceiling(self) -> None:
        _exact_bool(
            self.bounded_support_associated_with_lineage,
            True,
            "Q22_BOUNDED_SUPPORT_ASSOCIATED",
        )
        forbidden = (
            self.support_live_currentness_revalidated_for_lineage,
            self.support_fresh_at_pre_attempt_proven,
            self.support_fresh_at_effect_boundary_proven,
            self.support_caused_execution,
            self.execution_authorized,
            self.execution_lease_minted,
            self.provider_effect_authorized,
            self.semantic_k27_authority,
            self.native_private_transformer_kv_accessed,
            self.gate10_promoted,
            self.merge_deploy_spend_public_financial_human_effect_authorized,
        )
        if any(value is not False for value in forbidden):
            raise ValueError("Q22_ASSOCIATION_CANNOT_PROMOTE_CURRENTNESS_CAUSALITY_OR_EFFECT")

    def to_dict(self) -> dict[str, Any]:
        self.validate_claim_ceiling()
        body = asdict(self)
        body["receipt_digest"] = self.receipt_digest
        return body


def bind_materialization_support_to_lineage(
    *,
    support: support_owner.ConformanceDecision,
    lineage: Mapping[str, Any],
) -> MaterializationSupportedLifecycleLineageReceipt:
    """Associate two exact parent consequences through their directed basis relation."""
    _validate_support(support)
    _validate_lineage(lineage)

    base_basis = support_owner.Q20_Q19_PROPOSAL_BASIS
    if lineage["proposal_basis_digest"] != base_basis:
        raise ValueError("Q22_LINEAGE_NOT_FOR_SUPPORT_BASE_PROPOSAL")

    materialized_basis = support_owner.q20_materialization_bound_basis_digest()
    if support.proposal_basis_digest == base_basis:
        raise ValueError("Q22_BASE_AND_MATERIALIZATION_BOUND_BASIS_MUST_REMAIN_DISTINCT")

    basis_relation = _sha(
        {
            "domain": "AURA-Q22-BASE-TO-MATERIALIZATION-BOUND-BASIS-v1",
            "base_proposal_basis_digest": base_basis,
            "materialization_bound_proposal_basis_digest": materialized_basis,
            "materialization_relation_digest": support.materialization_relation_digest,
            "q19_source_gate_generation": support_owner.Q20_Q19_SOURCE_GATE_GENERATION,
        }
    )
    supported_lineage = _sha(
        {
            "domain": SCHEMA,
            "parent_proofs": {
                "support": [SUPPORT_PROOF_HEAD, SUPPORT_RUN, SUPPORT_JOB],
                "lineage": [LINEAGE_PROOF_HEAD, LINEAGE_RUN, LINEAGE_JOB],
            },
            "proposal_id": lineage["proposal_id"],
            "base_proposal_basis_digest": base_basis,
            "materialization_bound_proposal_basis_digest": materialized_basis,
            "base_to_materialization_relation_digest": basis_relation,
            "support_receipt_digest": support.receipt_digest,
            "proposal_evidence_support_digest": support.proposal_evidence_support_digest,
            "representation_fingerprint": support.proposal_representation_fingerprint,
            "authority_fingerprint": support.authority_fingerprint,
            "admission_policy_fingerprint": support.admission_policy_fingerprint,
            "evidence_admission_fingerprint": support.evidence_admission_fingerprint,
            "lineage_receipt_digest": lineage["receipt_digest"],
            "lineage_digest": lineage["lineage_digest"],
            "pre_attempt_id": lineage["pre_attempt_id"],
            "owner_state_epoch": lineage["owner_state_epoch"],
            "pre_attempt_policy_generation": lineage["pre_attempt_policy_generation"],
            "lifecycle_model_attempt_id": lineage["lifecycle_model_attempt_id"],
            "lifecycle_model_output_digest": lineage["lifecycle_model_output_digest"],
            "lifecycle_semantic_commit_key": lineage["lifecycle_semantic_commit_key"],
            "claim_ceiling": "ASSOCIATION_ONLY_REVALIDATION_REQUIRED",
        }
    )

    result = MaterializationSupportedLifecycleLineageReceipt(
        schema=SCHEMA,
        support_proof_head=SUPPORT_PROOF_HEAD,
        support_run=SUPPORT_RUN,
        support_job=SUPPORT_JOB,
        lineage_proof_head=LINEAGE_PROOF_HEAD,
        lineage_run=LINEAGE_RUN,
        lineage_job=LINEAGE_JOB,
        proposal_id=lineage["proposal_id"],
        base_proposal_basis_digest=base_basis,
        materialization_bound_proposal_basis_digest=materialized_basis,
        base_to_materialization_relation_digest=basis_relation,
        materialization_relation_digest=support.materialization_relation_digest,
        representation_fingerprint=support.proposal_representation_fingerprint,
        authority_fingerprint=support.authority_fingerprint,
        admission_policy_fingerprint=support.admission_policy_fingerprint,
        evidence_admission_fingerprint=support.evidence_admission_fingerprint,
        proposal_evidence_support_digest=support.proposal_evidence_support_digest,
        pre_attempt_id=lineage["pre_attempt_id"],
        owner_state_epoch=lineage["owner_state_epoch"],
        pre_attempt_policy_generation=lineage["pre_attempt_policy_generation"],
        lifecycle_model_attempt_id=lineage["lifecycle_model_attempt_id"],
        lifecycle_model_output_digest=lineage["lifecycle_model_output_digest"],
        lifecycle_semantic_commit_key=lineage["lifecycle_semantic_commit_key"],
        lineage_digest=lineage["lineage_digest"],
        supported_lineage_digest=supported_lineage,
    )
    result.validate_claim_ceiling()
    return result


def example_support() -> support_owner.ConformanceDecision:
    evidence = support_owner.AuthorityScopedEvidenceProjection(
        proof_head=support_owner.O64_PROOF_HEAD,
        semantic_head=support_owner.O64_SEMANTIC_HEAD,
        run_id=support_owner.O64_RUN,
        job_id=support_owner.O64_JOB,
        workflow_name=support_owner.O64_WORKFLOW,
        authority_fingerprint="a" * 64,
        admission_policy_fingerprint="b" * 64,
        evidence_admission_fingerprint="c" * 64,
        representation_fingerprint=support_owner.q20_representation_fingerprint(),
        representation_family=support_owner.Q20_REPRESENTATION_FAMILY,
        representation_digest=support_owner.Q20_Q19_REPRESENTATION_IDENTITY,
        accounting_domain=support_owner.Q20_ACCOUNTING_DOMAIN,
        accounting_contract_digest=support_owner.q20_accounting_contract_digest(),
        rate_numerator=9,
        rate_denominator=4,
        bounded_scope_digest=support_owner.q20_scope_digest(),
        evidence_scope_digest=support_owner.q20_scope_digest(),
        currentness_roots=("authority:exact", "source:exact", "policy:exact", "science:exact"),
        disposition="VERIFIED_BOUNDED",
        score_mass_eligible=True,
        proposal_mass_eligible=True,
    )
    return support_owner.prove_proposal_evidence_conformance(
        proposal=support_owner.exact_q20_projection(), evidence=evidence
    )


def example_lineage() -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema": LINEAGE_SCHEMA,
        "o65_head": "7efca33d95f6dc39c4e159250d45373b260060ed",
        "o65_run": 33410032496,
        "lifecycle_head": "22e72fd3de7b008752bbb5176347d61518f4e83a",
        "lifecycle_run": 33409821076,
        "proposal_id": "1" * 64,
        "proposal_basis_digest": support_owner.Q20_Q19_PROPOSAL_BASIS,
        "pre_attempt_id": "3" * 64,
        "owner_state_epoch": "epoch-q22-example",
        "pre_attempt_policy_generation": "policy-gen-q22-example",
        "pre_attempt_policy_digest": "4" * 64,
        "expected_route_fingerprint": "route:q22:bounded",
        "expected_observer_identity": "HOST_OBSERVER_Q22",
        "concurrency_scope_digest": "5" * 64,
        "lifecycle_model_objective_id": "objective:q22:example",
        "lifecycle_model_attempt_id": "attempt:q22:example",
        "lifecycle_model_output_digest": "6" * 64,
        "lifecycle_source_generation": "source-gen-q22",
        "lifecycle_authority_scope": "D0_BOUNDED",
        "lifecycle_terminal_state": "COMMITTED",
        "lifecycle_reason_code": "ALL_REQUIRED_EVIDENCE_SATISFIED",
        "lifecycle_semantic_commit_key": "7" * 64,
        "lifecycle_reusable_evidence_eligible": True,
        "proposal_identity_shared": True,
        "lineage_association_bound": True,
        "lineage_digest": "8" * 64,
        "effect_boundary_revalidation_still_required": True,
        "route_observer_to_host_witness_relation_proven": False,
        "pre_attempt_caused_execution": False,
        "pre_attempt_authorized_execution": False,
        "terminal_result_retroactively_authorizes_pre_attempt": False,
        "execution_lease_minted": False,
        "execution_authority_granted": False,
        "provider_effect_authority_granted": False,
        "semantic_k27_authority_minted": False,
        "native_private_transformer_kv_accessed": False,
        "gate10_promoted": False,
        "merge_deploy_spend_public_financial_human_effect_authorized": False,
        "reason": "EXACT_PRE_ATTEMPT_AND_TERMINAL_LIFECYCLE_ASSOCIATED_WITHOUT_CAUSAL_AUTHORITY_CLAIM",
    }
    body["receipt_digest"] = _sha({"domain": LINEAGE_SCHEMA, "receipt": body})
    return body


def main() -> None:
    receipt = bind_materialization_support_to_lineage(
        support=example_support(), lineage=example_lineage()
    )
    print(json.dumps(receipt.to_dict(), sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
