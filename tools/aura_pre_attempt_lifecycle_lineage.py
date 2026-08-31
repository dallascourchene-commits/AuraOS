#!/usr/bin/env python3
"""Q21: bind an owner-resolved pre-attempt envelope to terminal lifecycle lineage.

D0 / HS1 / NONPROMOTING.

This is a relation membrane, not an execution owner. It consumes already-owned typed
receipts from O65 pre-attempt admission and the owner-resolved proposal/lifecycle
bridge. It can prove only that the exact proposal, serializable pre-attempt identity,
and admitted lifecycle consequence are content-addressed into one lineage relation.

It deliberately cannot prove that the host consumed the pre-attempt envelope, that
the pre-attempt authorized execution, or that a terminal result retroactively
establishes authorization. Those require an effect-bound, host-observed causal witness.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping

SCHEMA = "AURA-PRE-ATTEMPT-LIFECYCLE-LINEAGE-v1"
O65_SCHEMA = "AURA-PRE-ATTEMPT-ADMISSION-RECEIPT-v1"
O65_ELIGIBLE = "PRE_ATTEMPT_ENVELOPE_ELIGIBLE"
LIFECYCLE_SCHEMA = "AURA-OWNER-RESOLVED-PROPOSAL-LIFECYCLE-BRIDGE-v1"
O65_HEAD = "7efca33d95f6dc39c4e159250d45373b260060ed"
O65_RUN = 33410032496
LIFECYCLE_HEAD = "22e72fd3de7b008752bbb5176347d61518f4e83a"
LIFECYCLE_RUN = 33409821076
HEX = frozenset("0123456789abcdef")


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _required(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")
    return value


def _sha256(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in HEX for c in value):
        raise ValueError(f"{name}_MUST_BE_SHA256_HEX")
    return value


def _bool(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name}_MUST_BE_BOOL")
    return value


O65_FORBIDDEN = (
    "execution_authorized",
    "execution_lease_minted",
    "provider_effect_authorized",
    "provider_effect_started",
    "semantic_k27_authority",
    "native_private_transformer_kv_accessed",
    "gate10_promoted",
    "merge_deploy_spend_public_financial_human_effect",
)
LIFECYCLE_FORBIDDEN = (
    "execution_authority_granted",
    "provider_effect_authority_granted",
    "semantic_k27_authority_minted",
    "native_private_transformer_kv_accessed",
    "gate10_promoted",
    "merge_deploy_spend_public_human_effect_authorized",
)


def validate_o65_receipt(receipt: Mapping[str, Any]) -> None:
    if receipt.get("schema_version") != O65_SCHEMA:
        raise ValueError("O65_RECEIPT_SCHEMA_MISMATCH")
    for key in ("proposal_id", "proposal_basis_digest", "pre_attempt_id", "policy_digest", "concurrency_scope_digest"):
        _sha256(receipt.get(key), f"O65_{key.upper()}")
    for key in ("owner_state_epoch", "policy_generation", "expected_route_fingerprint", "expected_observer_identity"):
        _required(receipt.get(key), f"O65_{key.upper()}")
    if receipt.get("disposition") != O65_ELIGIBLE:
        raise ValueError("O65_PRE_ATTEMPT_NOT_ELIGIBLE")
    required_true = (
        "proposal_current",
        "policy_current",
        "authority_scope_matches",
        "action_matches_proposal",
        "resource_envelope_matches",
        "revalidation_required_at_effect_boundary",
    )
    for key in required_true:
        if _bool(receipt.get(key), f"O65_{key.upper()}") is not True:
            raise ValueError(f"O65_{key.upper()}_REQUIRED_TRUE")
    if receipt.get("concurrent_live_attempt_conflict") is not False:
        raise ValueError("O65_CONCURRENCY_MUST_BE_EXACT_FALSE")
    for key in O65_FORBIDDEN:
        if _bool(receipt.get(key), f"O65_{key.upper()}") is not False:
            raise ValueError(f"O65_CLAIM_CEILING_WIDENED:{key}")


def validate_lifecycle_receipt(receipt: Mapping[str, Any]) -> None:
    if receipt.get("schema") != LIFECYCLE_SCHEMA:
        raise ValueError("LIFECYCLE_RECEIPT_SCHEMA_MISMATCH")
    for key in ("proposal_id", "proposal_basis_digest", "model_output_digest"):
        _sha256(receipt.get(key), f"LIFECYCLE_{key.upper()}")
    for key in (
        "model_objective_id",
        "model_attempt_id",
        "lifecycle_source_generation",
        "lifecycle_authority_scope",
        "lifecycle_terminal_state",
        "lifecycle_reason_code",
    ):
        _required(receipt.get(key), f"LIFECYCLE_{key.upper()}")
    if receipt.get("proposal_currentness_state") != "CURRENT_NONEXECUTABLE":
        raise ValueError("LIFECYCLE_PROPOSAL_NOT_CURRENT_NONEXECUTABLE")
    for key in (
        "proposal_ref_present",
        "proposal_ref_required_by_policy",
        "source_generation_bound_to_proposal",
        "authority_scope_bound_to_proposal",
        "consequence_key_bound_to_proposal",
    ):
        if _bool(receipt.get(key), f"LIFECYCLE_{key.upper()}") is not True:
            raise ValueError(f"LIFECYCLE_{key.upper()}_REQUIRED_TRUE")
    if _bool(receipt.get("semantic_commit_eligible"), "LIFECYCLE_SEMANTIC_COMMIT_ELIGIBLE") is not True:
        raise ValueError("LIFECYCLE_SEMANTIC_COMMIT_NOT_ELIGIBLE")
    _sha256(receipt.get("semantic_commit_key"), "LIFECYCLE_SEMANTIC_COMMIT_KEY")
    _bool(receipt.get("reusable_evidence_eligible"), "LIFECYCLE_REUSABLE_EVIDENCE_ELIGIBLE")
    for key in LIFECYCLE_FORBIDDEN:
        if _bool(receipt.get(key), f"LIFECYCLE_{key.upper()}") is not False:
            raise ValueError(f"LIFECYCLE_CLAIM_CEILING_WIDENED:{key}")


@dataclass(frozen=True)
class PreAttemptLifecycleLineageReceipt:
    schema: str
    o65_head: str
    o65_run: int
    lifecycle_head: str
    lifecycle_run: int
    proposal_id: str
    proposal_basis_digest: str
    pre_attempt_id: str
    owner_state_epoch: str
    pre_attempt_policy_generation: str
    pre_attempt_policy_digest: str
    expected_route_fingerprint: str
    expected_observer_identity: str
    concurrency_scope_digest: str
    lifecycle_model_objective_id: str
    lifecycle_model_attempt_id: str
    lifecycle_model_output_digest: str
    lifecycle_source_generation: str
    lifecycle_authority_scope: str
    lifecycle_terminal_state: str
    lifecycle_reason_code: str
    lifecycle_semantic_commit_key: str
    lifecycle_reusable_evidence_eligible: bool
    proposal_identity_shared: bool
    lineage_association_bound: bool
    lineage_digest: str | None
    effect_boundary_revalidation_still_required: bool = True
    route_observer_to_host_witness_relation_proven: bool = False
    pre_attempt_caused_execution: bool = False
    pre_attempt_authorized_execution: bool = False
    terminal_result_retroactively_authorizes_pre_attempt: bool = False
    execution_lease_minted: bool = False
    execution_authority_granted: bool = False
    provider_effect_authority_granted: bool = False
    semantic_k27_authority_minted: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False
    merge_deploy_spend_public_financial_human_effect_authorized: bool = False
    reason: str = "EXACT_PRE_ATTEMPT_AND_TERMINAL_LIFECYCLE_ASSOCIATED_WITHOUT_CAUSAL_AUTHORITY_CLAIM"

    def validate_claim_ceiling(self) -> None:
        if self.effect_boundary_revalidation_still_required is not True:
            raise ValueError("Q21_EFFECT_BOUNDARY_REVALIDATION_MUST_REMAIN_REQUIRED")
        forbidden = (
            self.route_observer_to_host_witness_relation_proven,
            self.pre_attempt_caused_execution,
            self.pre_attempt_authorized_execution,
            self.terminal_result_retroactively_authorizes_pre_attempt,
            self.execution_lease_minted,
            self.execution_authority_granted,
            self.provider_effect_authority_granted,
            self.semantic_k27_authority_minted,
            self.native_private_transformer_kv_accessed,
            self.gate10_promoted,
            self.merge_deploy_spend_public_financial_human_effect_authorized,
        )
        if any(value is not False for value in forbidden):
            raise ValueError("Q21_LINEAGE_CANNOT_CARRY_CAUSAL_OR_EFFECT_AUTHORITY")

    @property
    def receipt_digest(self) -> str:
        self.validate_claim_ceiling()
        return _sha({"domain": SCHEMA, "receipt": asdict(self)})

    def to_dict(self) -> dict[str, Any]:
        body = asdict(self)
        body["receipt_digest"] = self.receipt_digest
        return body


def bind_pre_attempt_lifecycle(
    *, o65_receipt: Mapping[str, Any], lifecycle_receipt: Mapping[str, Any]
) -> PreAttemptLifecycleLineageReceipt:
    """Create one bounded association over two independently owned receipts.

    Extra fields, including K27 coordinates or narrative labels, are intentionally not
    identity-bearing. The result establishes relation identity only, never causal use.
    """
    validate_o65_receipt(o65_receipt)
    validate_lifecycle_receipt(lifecycle_receipt)

    proposal_shared = (
        o65_receipt["proposal_id"] == lifecycle_receipt["proposal_id"]
        and o65_receipt["proposal_basis_digest"] == lifecycle_receipt["proposal_basis_digest"]
    )
    if not proposal_shared:
        raise ValueError("Q21_PROPOSAL_IDENTITY_OR_BASIS_MISMATCH")

    identity_payload = {
        "domain": SCHEMA,
        "o65_parent": {"head": O65_HEAD, "run": O65_RUN},
        "lifecycle_parent": {"head": LIFECYCLE_HEAD, "run": LIFECYCLE_RUN},
        "proposal_id": o65_receipt["proposal_id"],
        "proposal_basis_digest": o65_receipt["proposal_basis_digest"],
        "pre_attempt_id": o65_receipt["pre_attempt_id"],
        "owner_state_epoch": o65_receipt["owner_state_epoch"],
        "pre_attempt_policy_generation": o65_receipt["policy_generation"],
        "pre_attempt_policy_digest": o65_receipt["policy_digest"],
        "expected_route_fingerprint": o65_receipt["expected_route_fingerprint"],
        "expected_observer_identity": o65_receipt["expected_observer_identity"],
        "concurrency_scope_digest": o65_receipt["concurrency_scope_digest"],
        "lifecycle_model_objective_id": lifecycle_receipt["model_objective_id"],
        "lifecycle_model_attempt_id": lifecycle_receipt["model_attempt_id"],
        "lifecycle_model_output_digest": lifecycle_receipt["model_output_digest"],
        "lifecycle_source_generation": lifecycle_receipt["lifecycle_source_generation"],
        "lifecycle_authority_scope": lifecycle_receipt["lifecycle_authority_scope"],
        "lifecycle_terminal_state": lifecycle_receipt["lifecycle_terminal_state"],
        "lifecycle_semantic_commit_key": lifecycle_receipt["semantic_commit_key"],
    }
    lineage_digest = _sha(identity_payload)
    result = PreAttemptLifecycleLineageReceipt(
        schema=SCHEMA,
        o65_head=O65_HEAD,
        o65_run=O65_RUN,
        lifecycle_head=LIFECYCLE_HEAD,
        lifecycle_run=LIFECYCLE_RUN,
        proposal_id=o65_receipt["proposal_id"],
        proposal_basis_digest=o65_receipt["proposal_basis_digest"],
        pre_attempt_id=o65_receipt["pre_attempt_id"],
        owner_state_epoch=o65_receipt["owner_state_epoch"],
        pre_attempt_policy_generation=o65_receipt["policy_generation"],
        pre_attempt_policy_digest=o65_receipt["policy_digest"],
        expected_route_fingerprint=o65_receipt["expected_route_fingerprint"],
        expected_observer_identity=o65_receipt["expected_observer_identity"],
        concurrency_scope_digest=o65_receipt["concurrency_scope_digest"],
        lifecycle_model_objective_id=lifecycle_receipt["model_objective_id"],
        lifecycle_model_attempt_id=lifecycle_receipt["model_attempt_id"],
        lifecycle_model_output_digest=lifecycle_receipt["model_output_digest"],
        lifecycle_source_generation=lifecycle_receipt["lifecycle_source_generation"],
        lifecycle_authority_scope=lifecycle_receipt["lifecycle_authority_scope"],
        lifecycle_terminal_state=lifecycle_receipt["lifecycle_terminal_state"],
        lifecycle_reason_code=lifecycle_receipt["lifecycle_reason_code"],
        lifecycle_semantic_commit_key=lifecycle_receipt["semantic_commit_key"],
        lifecycle_reusable_evidence_eligible=lifecycle_receipt["reusable_evidence_eligible"],
        proposal_identity_shared=True,
        lineage_association_bound=True,
        lineage_digest=lineage_digest,
    )
    result.validate_claim_ceiling()
    return result


def example_o65() -> dict[str, Any]:
    return {
        "schema_version": O65_SCHEMA,
        "disposition": O65_ELIGIBLE,
        "reason_code": "ALL_OWNER_RESOLVED_GATES_PASS",
        "proposal_id": "1" * 64,
        "proposal_basis_digest": "2" * 64,
        "pre_attempt_id": "3" * 64,
        "owner_state_epoch": "epoch-17",
        "policy_generation": "policy-gen-9",
        "policy_digest": "4" * 64,
        "expected_route_fingerprint": "route:bounded:v1",
        "expected_observer_identity": "HOST_OBSERVER_V1",
        "concurrency_scope_digest": "5" * 64,
        "proposal_current": True,
        "policy_current": True,
        "authority_scope_matches": True,
        "action_matches_proposal": True,
        "resource_envelope_matches": True,
        "concurrent_live_attempt_conflict": False,
        "revalidation_required_at_effect_boundary": True,
        "execution_authorized": False,
        "execution_lease_minted": False,
        "provider_effect_authorized": False,
        "provider_effect_started": False,
        "semantic_k27_authority": False,
        "native_private_transformer_kv_accessed": False,
        "gate10_promoted": False,
        "merge_deploy_spend_public_financial_human_effect": False,
    }


def example_lifecycle() -> dict[str, Any]:
    return {
        "schema": LIFECYCLE_SCHEMA,
        "proposal_id": "1" * 64,
        "proposal_basis_digest": "2" * 64,
        "proposal_currentness_state": "CURRENT_NONEXECUTABLE",
        "proposal_currentness_reason": "ALL_OWNER_STATE_CURRENT",
        "model_objective_id": "objective:bounded:v1",
        "model_attempt_id": "attempt:42",
        "model_output_digest": "6" * 64,
        "lifecycle_source_generation": "source-gen-8",
        "lifecycle_authority_scope": "D0_BOUNDED",
        "proposal_ref_required": "proposal:" + "1" * 64,
        "proposal_ref_present": True,
        "proposal_ref_required_by_policy": True,
        "source_generation_bound_to_proposal": True,
        "authority_scope_bound_to_proposal": True,
        "consequence_key_bound_to_proposal": True,
        "lifecycle_terminal_state": "COMMITTED",
        "lifecycle_reason_code": "ALL_REQUIRED_EVIDENCE_SATISFIED",
        "semantic_commit_eligible": True,
        "semantic_commit_key": "7" * 64,
        "reusable_evidence_eligible": True,
        "execution_authority_granted": False,
        "provider_effect_authority_granted": False,
        "semantic_k27_authority_minted": False,
        "native_private_transformer_kv_accessed": False,
        "gate10_promoted": False,
        "merge_deploy_spend_public_human_effect_authorized": False,
    }


def main() -> None:
    print(json.dumps(bind_pre_attempt_lifecycle(o65_receipt=example_o65(), lifecycle_receipt=example_lifecycle()).to_dict(), sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
