#!/usr/bin/env python3
"""Triadic addendum: preserve Q22 directed-basis provenance inside O67 attachment.

D0 / HS1 / NONPROMOTING.

This module deliberately does not create a second Q22 or O67 owner. It consumes:
- Q22: a directed base-proposal -> materialization-bound support association; and
- O67: an owner-resolved explicit support -> lifecycle attachment decision.

The addendum exists because an explicit attachment between two hashes is stronger
when it also commits to the independently derived directed provenance relation
between those domains. Collision is therefore rebased into reusable delta rather
than discarded cognition.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

SCHEMA = "AURA-DIRECTED-SUPPORT-ATTACHMENT-ADDENDUM-v1"
Q22_SCHEMA = "AURA-MATERIALIZATION-SUPPORT-LIFECYCLE-LINEAGE-v1"
O67_SCHEMA = "AURA-MATERIALIZATION-SUPPORT-LINEAGE-ATTACHMENT-v1"
HEX = frozenset("0123456789abcdef")

Q22_SOURCE_HEAD = "7dcd146ebcecb7ca7ab53b6ba5eb0d8c9a649cc6"
O67_SOURCE_HEAD = "3b2e5230dccc9782a2714c8621446679a25de6b2"

BOUND = "DIRECTED_ATTACHMENT_PROVENANCE_BOUND"
HOLD = "HOLD_DIRECTED_ATTACHMENT_PROVENANCE_REQUIRED"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


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


@dataclass(frozen=True)
class Q22DirectedSupportProjection:
    schema: str
    source_head: str
    proposal_id: str
    base_proposal_basis_digest: str
    materialization_bound_proposal_basis_digest: str
    base_to_materialization_relation_digest: str
    proposal_evidence_support_digest: str
    supported_lineage_digest: str
    bounded_support_associated_with_lineage: bool
    support_live_currentness_revalidated_for_lineage: bool = False
    support_fresh_at_pre_attempt_proven: bool = False
    support_fresh_at_effect_boundary_proven: bool = False
    support_caused_execution: bool = False
    execution_authorized: bool = False
    provider_effect_authorized: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False

    def validate(self) -> None:
        if (self.schema, self.source_head) != (Q22_SCHEMA, Q22_SOURCE_HEAD):
            raise ValueError("ADDENDUM_Q22_EXACT_SOURCE_REQUIRED")
        for value, name in (
            (self.proposal_id, "Q22_PROPOSAL_ID"),
            (self.base_proposal_basis_digest, "Q22_BASE_BASIS"),
            (self.materialization_bound_proposal_basis_digest, "Q22_MATERIALIZATION_BASIS"),
            (self.base_to_materialization_relation_digest, "Q22_DIRECTED_BASIS_RELATION"),
            (self.proposal_evidence_support_digest, "Q22_SUPPORT_DIGEST"),
            (self.supported_lineage_digest, "Q22_SUPPORTED_LINEAGE_DIGEST"),
        ):
            _sha256(value, name)
        if self.base_proposal_basis_digest == self.materialization_bound_proposal_basis_digest:
            raise ValueError("ADDENDUM_DIRECTED_BASIS_MUST_NOT_COLLAPSE_TO_IDENTITY")
        if self.bounded_support_associated_with_lineage is not True:
            raise ValueError("ADDENDUM_Q22_ASSOCIATION_REQUIRED")
        if any((
            self.support_live_currentness_revalidated_for_lineage,
            self.support_fresh_at_pre_attempt_proven,
            self.support_fresh_at_effect_boundary_proven,
            self.support_caused_execution,
            self.execution_authorized,
            self.provider_effect_authorized,
            self.semantic_k27_authority,
            self.native_private_transformer_kv_accessed,
            self.gate10_promoted,
        )):
            raise ValueError("ADDENDUM_Q22_CLAIM_CEILING_WIDENED")


@dataclass(frozen=True)
class O67AttachmentProjection:
    schema: str
    source_head: str
    disposition: str
    relation_id: str | None
    materialization_proposal_basis_digest: str
    materialization_support_digest: str
    lineage_proposal_id: str
    lineage_proposal_basis_digest: str
    lineage_relation_id: str
    attachment_id: str | None
    attachment_owner_ref: str | None
    attachment_owner_generation: str | None
    attachment_owner_state_epoch: str | None
    support_attached_to_lineage_proposal: bool
    support_currentness_self_resolved: bool = False
    effect_boundary_revalidation_required: bool = True
    execution_authority_granted: bool = False
    execution_lease_minted: bool = False
    provider_effect_authority_granted: bool = False
    semantic_k27_authority_minted: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False

    def validate(self) -> None:
        if (self.schema, self.source_head) != (O67_SCHEMA, O67_SOURCE_HEAD):
            raise ValueError("ADDENDUM_O67_EXACT_SOURCE_REQUIRED")
        for value, name in (
            (self.materialization_proposal_basis_digest, "O67_MATERIALIZATION_BASIS"),
            (self.materialization_support_digest, "O67_SUPPORT_DIGEST"),
            (self.lineage_proposal_id, "O67_LINEAGE_PROPOSAL_ID"),
            (self.lineage_proposal_basis_digest, "O67_LINEAGE_PROPOSAL_BASIS"),
            (self.lineage_relation_id, "O67_LINEAGE_RELATION_ID"),
        ):
            _sha256(value, name)
        if self.effect_boundary_revalidation_required is not True:
            raise ValueError("ADDENDUM_EFFECT_BOUNDARY_REVALIDATION_REQUIRED")
        if any((
            self.support_currentness_self_resolved,
            self.execution_authority_granted,
            self.execution_lease_minted,
            self.provider_effect_authority_granted,
            self.semantic_k27_authority_minted,
            self.native_private_transformer_kv_accessed,
            self.gate10_promoted,
        )):
            raise ValueError("ADDENDUM_O67_CLAIM_CEILING_WIDENED")
        if self.support_attached_to_lineage_proposal:
            if self.disposition != "MATERIALIZATION_SUPPORT_LINEAGE_BOUND":
                raise ValueError("ADDENDUM_O67_BOUND_DISPOSITION_REQUIRED")
            for value, name in ((self.relation_id, "O67_RELATION_ID"), (self.attachment_id, "O67_ATTACHMENT_ID")):
                _sha256(value, name)
            _required(self.attachment_owner_ref, "O67_ATTACHMENT_OWNER_REF")
            _required(self.attachment_owner_generation, "O67_ATTACHMENT_OWNER_GENERATION")
            _required(self.attachment_owner_state_epoch, "O67_ATTACHMENT_OWNER_STATE_EPOCH")


@dataclass(frozen=True)
class DirectedAttachmentAddendumDecision:
    schema: str
    disposition: str
    reason_code: str
    directed_attachment_addendum_id: str | None
    q22_directed_basis_relation_digest: str
    q22_supported_lineage_digest: str
    o67_attachment_id: str | None
    o67_relation_id: str | None
    proposal_id: str
    base_proposal_basis_digest: str
    materialization_bound_proposal_basis_digest: str
    support_digest: str
    directed_provenance_bound_to_attachment: bool
    collision_cognition_preserved_as_addendum: bool = True
    live_support_currentness_resolved: bool = False
    host_causality_proven: bool = False
    execution_authorized: bool = False
    provider_effect_authorized: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False

    @property
    def receipt_digest(self) -> str:
        return _sha({"domain": SCHEMA, "receipt": asdict(self)})


def bind_directed_provenance_addendum(*, q22: Q22DirectedSupportProjection, o67: O67AttachmentProjection) -> DirectedAttachmentAddendumDecision:
    q22.validate()
    o67.validate()
    base = dict(
        q22_directed_basis_relation_digest=q22.base_to_materialization_relation_digest,
        q22_supported_lineage_digest=q22.supported_lineage_digest,
        o67_attachment_id=o67.attachment_id,
        o67_relation_id=o67.relation_id,
        proposal_id=q22.proposal_id,
        base_proposal_basis_digest=q22.base_proposal_basis_digest,
        materialization_bound_proposal_basis_digest=q22.materialization_bound_proposal_basis_digest,
        support_digest=q22.proposal_evidence_support_digest,
    )
    if not o67.support_attached_to_lineage_proposal:
        return DirectedAttachmentAddendumDecision(schema=SCHEMA, disposition=HOLD, reason_code="O67_EXPLICIT_ATTACHMENT_NOT_YET_BOUND", directed_attachment_addendum_id=None, directed_provenance_bound_to_attachment=False, **base)
    exact = (
        q22.proposal_id == o67.lineage_proposal_id
        and q22.base_proposal_basis_digest == o67.lineage_proposal_basis_digest
        and q22.materialization_bound_proposal_basis_digest == o67.materialization_proposal_basis_digest
        and q22.proposal_evidence_support_digest == o67.materialization_support_digest
    )
    if not exact:
        return DirectedAttachmentAddendumDecision(schema=SCHEMA, disposition="HOLD_DIRECTED_ATTACHMENT_IDENTITY_MISMATCH", reason_code="Q22_DIRECTED_PROVENANCE_AND_O67_ATTACHMENT_DO_NOT_COMMUTE", directed_attachment_addendum_id=None, directed_provenance_bound_to_attachment=False, **base)
    addendum_id = _sha({
        "domain": SCHEMA,
        "q22_source_head": q22.source_head,
        "o67_source_head": o67.source_head,
        "proposal_id": q22.proposal_id,
        "base_proposal_basis_digest": q22.base_proposal_basis_digest,
        "materialization_bound_proposal_basis_digest": q22.materialization_bound_proposal_basis_digest,
        "base_to_materialization_relation_digest": q22.base_to_materialization_relation_digest,
        "support_digest": q22.proposal_evidence_support_digest,
        "q22_supported_lineage_digest": q22.supported_lineage_digest,
        "o67_attachment_id": o67.attachment_id,
        "o67_relation_id": o67.relation_id,
        "attachment_owner_ref": o67.attachment_owner_ref,
        "attachment_owner_generation": o67.attachment_owner_generation,
        "attachment_owner_state_epoch": o67.attachment_owner_state_epoch,
        "authority_ceiling": "ADDENDUM_ONLY_NONEXECUTABLE_D0",
    })
    return DirectedAttachmentAddendumDecision(schema=SCHEMA, disposition=BOUND, reason_code="Q22_DIRECTED_PROVENANCE_BOUND_TO_O67_EXPLICIT_ATTACHMENT", directed_attachment_addendum_id=addendum_id, directed_provenance_bound_to_attachment=True, **base)


if __name__ == "__main__":
    print("Triadic addendum module; execute through tests/hosted proof.")
