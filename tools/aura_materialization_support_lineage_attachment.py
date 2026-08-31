#!/usr/bin/env python3
"""O67: explicit attachment gate between materialization support and pre-attempt lifecycle lineage.

D0 / HS1 / NONPROMOTING.

O65-R/PR708 proves bounded authority-scoped evidence supports one exact
materialization-bound proposal basis, but deliberately does not resolve live
proposal currentness. O66/PR710 proves an epoch-serializable pre-attempt to
typed-witness lifecycle lineage for an owner-resolved proposal, but does not
claim that O65-R's materialization support belongs to that proposal.

O67 owns only the missing cross-plane attachment rule:
bounded support may enter a lineage only through an owner-resolved explicit
attachment binding both exact parent identities. Matching hashes, narratives,
K27/cache coordinates, or parent greenness cannot substitute.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Protocol

SCHEMA = "AURA-MATERIALIZATION-SUPPORT-LINEAGE-ATTACHMENT-v1"
BOUND = "MATERIALIZATION_SUPPORT_LINEAGE_BOUND"
HOLD_REQUIRED = "HOLD_EXPLICIT_SUPPORT_ATTACHMENT_REQUIRED"

O65R_PROOF_HEAD = "361b01579ab2debc34f4b836c3ea605de635a8c3"
O65R_SEMANTIC_HEAD = "fff1e38f78c54c387c1131543ce332d115ad7f5c"
O65R_RUN = 33411109692
O65R_JOB = 99550605797
O65R_SOURCE_BLOB = "bdaa9b0338cdab05c48dc0337ab46522b40ac42f"
O65R_MATERIALIZATION_BASIS = "e94c482318e0c25ad7052328fcd6722ac85470ba756ac7d6e2056131f4ff0c0d"

O66_PROOF_HEAD = "2034bb9afcc801e1655bf334548042f6602c8c17"
O66_RUN = 33410906307
O66_JOB = 99549924922
O66_SOURCE_BLOB = "bdd5b9639995eaf9353efbe454db5817698c9690"
O66_BOUND = "PRE_ATTEMPT_LIFECYCLE_LINEAGE_BOUND"

HEX = frozenset("0123456789abcdef")


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha256(value: str, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in HEX for c in value):
        raise ValueError(f"{name}_MUST_BE_SHA256_HEX")
    return value


def _required(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")
    return value


@dataclass(frozen=True)
class MaterializationSupportProjection:
    proof_head: str
    semantic_head: str
    run_id: int
    job_id: int
    source_blob: str
    materialization_proposal_basis_digest: str
    proposal_evidence_support_digest: str
    bounded_evidence_supports_exact_proposal: bool
    live_proposal_currentness_resolved: bool = False
    execution_authorized: bool = False
    provider_effect_authorized: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False

    def validate(self) -> None:
        if (self.proof_head, self.semantic_head, self.run_id, self.job_id, self.source_blob) != (
            O65R_PROOF_HEAD, O65R_SEMANTIC_HEAD, O65R_RUN, O65R_JOB, O65R_SOURCE_BLOB
        ):
            raise ValueError("O67_O65R_EXACT_PARENT_REQUIRED")
        if self.materialization_proposal_basis_digest != O65R_MATERIALIZATION_BASIS:
            raise ValueError("O67_O65R_MATERIALIZATION_BASIS_MISMATCH")
        _sha256(self.proposal_evidence_support_digest, "O65R_SUPPORT_DIGEST")
        if self.bounded_evidence_supports_exact_proposal is not True:
            raise ValueError("O67_O65R_BOUNDED_SUPPORT_REQUIRED")
        if self.live_proposal_currentness_resolved is not False:
            raise ValueError("O67_O65R_MUST_NOT_SELF_RESOLVE_CURRENTNESS")
        if any((
            self.execution_authorized,
            self.provider_effect_authorized,
            self.semantic_k27_authority,
            self.native_private_transformer_kv_accessed,
            self.gate10_promoted,
        )):
            raise ValueError("O67_O65R_CLAIM_CEILING_WIDENED")


@dataclass(frozen=True)
class PreAttemptLifecycleProjection:
    proof_head: str
    run_id: int
    job_id: int
    source_blob: str
    disposition: str
    relation_id: str
    proposal_id: str
    proposal_basis_digest: str
    relation_owner_epoch: str
    effect_boundary_revalidation_required: bool = True
    execution_authority_granted: bool = False
    execution_lease_minted: bool = False
    provider_effect_authority_granted: bool = False
    semantic_k27_authority_minted: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False

    def validate(self) -> None:
        if (self.proof_head, self.run_id, self.job_id, self.source_blob) != (
            O66_PROOF_HEAD, O66_RUN, O66_JOB, O66_SOURCE_BLOB
        ):
            raise ValueError("O67_O66_EXACT_PARENT_REQUIRED")
        if self.disposition != O66_BOUND:
            raise ValueError("O67_O66_BOUND_LINEAGE_REQUIRED")
        for value, name in (
            (self.relation_id, "O66_RELATION_ID"),
            (self.proposal_id, "O66_PROPOSAL_ID"),
            (self.proposal_basis_digest, "O66_PROPOSAL_BASIS"),
        ):
            _sha256(value, name)
        _required(self.relation_owner_epoch, "O66_RELATION_OWNER_EPOCH")
        if self.effect_boundary_revalidation_required is not True:
            raise ValueError("O67_EFFECT_BOUNDARY_REVALIDATION_REQUIRED")
        if any((
            self.execution_authority_granted,
            self.execution_lease_minted,
            self.provider_effect_authority_granted,
            self.semantic_k27_authority_minted,
            self.native_private_transformer_kv_accessed,
            self.gate10_promoted,
        )):
            raise ValueError("O67_O66_CLAIM_CEILING_WIDENED")


@dataclass(frozen=True)
class SupportLineageAttachment:
    owner_ref: str
    owner_generation: str
    owner_state_epoch: str
    materialization_proposal_basis_digest: str
    materialization_support_digest: str
    lineage_proposal_id: str
    lineage_proposal_basis_digest: str
    mapping_state: str = "CURRENT_EXPLICIT"
    execution_authority_granted: bool = False
    provider_effect_authority_granted: bool = False
    semantic_k27_authority_minted: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False

    def validate(self) -> None:
        owner = _required(self.owner_ref, "ATTACHMENT_OWNER_REF")
        if not owner.startswith("owner:"):
            raise ValueError("ATTACHMENT_OWNER_MUST_BE_OWNER_REF_NOT_COORDINATE")
        generation = _required(self.owner_generation, "ATTACHMENT_OWNER_GENERATION")
        if not generation.startswith("attachment-generation:"):
            raise ValueError("ATTACHMENT_GENERATION_DOMAIN_REQUIRED")
        _required(self.owner_state_epoch, "ATTACHMENT_OWNER_STATE_EPOCH")
        for value, name in (
            (self.materialization_proposal_basis_digest, "ATTACHMENT_MATERIALIZATION_BASIS"),
            (self.materialization_support_digest, "ATTACHMENT_SUPPORT_DIGEST"),
            (self.lineage_proposal_id, "ATTACHMENT_LINEAGE_PROPOSAL_ID"),
            (self.lineage_proposal_basis_digest, "ATTACHMENT_LINEAGE_PROPOSAL_BASIS"),
        ):
            _sha256(value, name)
        if self.mapping_state != "CURRENT_EXPLICIT":
            raise ValueError("ATTACHMENT_NOT_CURRENT_EXPLICIT")
        if any((
            self.execution_authority_granted,
            self.provider_effect_authority_granted,
            self.semantic_k27_authority_minted,
            self.native_private_transformer_kv_accessed,
            self.gate10_promoted,
        )):
            raise ValueError("ATTACHMENT_CANNOT_CARRY_EFFECT_AUTHORITY")

    @property
    def attachment_id(self) -> str:
        self.validate()
        return _sha({"domain": "AURA-O67-SUPPORT-LINEAGE-ATTACHMENT-ID-v1", **asdict(self)})


class SupportLineageAttachmentResolver(Protocol):
    def resolve_support_lineage_attachment(
        self,
        *,
        materialization_proposal_basis_digest: str,
        materialization_support_digest: str,
        lineage_proposal_id: str,
        lineage_proposal_basis_digest: str,
    ) -> SupportLineageAttachment | None: ...


@dataclass(frozen=True)
class SupportLineageDecision:
    schema: str
    disposition: str
    reason_code: str
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
    provider_effect_started: bool = False
    semantic_k27_authority_minted: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False
    merge_deploy_spend_public_financial_human_effect_authorized: bool = False

    @property
    def receipt_digest(self) -> str:
        return _sha({"domain": SCHEMA, "receipt": asdict(self)})

    def to_dict(self) -> dict[str, Any]:
        body = asdict(self)
        body["receipt_digest"] = self.receipt_digest
        return body


def _decision(
    support: MaterializationSupportProjection,
    lineage: PreAttemptLifecycleProjection,
    *,
    disposition: str,
    reason_code: str,
    attachment: SupportLineageAttachment | None = None,
    relation_id: str | None = None,
) -> SupportLineageDecision:
    return SupportLineageDecision(
        schema=SCHEMA,
        disposition=disposition,
        reason_code=reason_code,
        relation_id=relation_id,
        materialization_proposal_basis_digest=support.materialization_proposal_basis_digest,
        materialization_support_digest=support.proposal_evidence_support_digest,
        lineage_proposal_id=lineage.proposal_id,
        lineage_proposal_basis_digest=lineage.proposal_basis_digest,
        lineage_relation_id=lineage.relation_id,
        attachment_id=attachment.attachment_id if attachment else None,
        attachment_owner_ref=attachment.owner_ref if attachment else None,
        attachment_owner_generation=attachment.owner_generation if attachment else None,
        attachment_owner_state_epoch=attachment.owner_state_epoch if attachment else None,
        support_attached_to_lineage_proposal=relation_id is not None,
    )


def evaluate_materialization_support_lineage(
    *,
    support: MaterializationSupportProjection,
    lineage: PreAttemptLifecycleProjection,
    attachment_resolver: SupportLineageAttachmentResolver | None,
) -> SupportLineageDecision:
    support.validate()
    lineage.validate()

    if attachment_resolver is None:
        return _decision(
            support, lineage, disposition=HOLD_REQUIRED,
            reason_code="NO_OWNER_RESOLVED_CROSS_PLANE_ATTACHMENT",
        )

    try:
        attachment = attachment_resolver.resolve_support_lineage_attachment(
            materialization_proposal_basis_digest=support.materialization_proposal_basis_digest,
            materialization_support_digest=support.proposal_evidence_support_digest,
            lineage_proposal_id=lineage.proposal_id,
            lineage_proposal_basis_digest=lineage.proposal_basis_digest,
        )
    except Exception:
        return _decision(
            support, lineage, disposition="HOLD_ATTACHMENT_OWNER_RESOLUTION_ERROR",
            reason_code="ATTACHMENT_OWNER_RESOLUTION_ERROR",
        )

    if attachment is None:
        return _decision(
            support, lineage, disposition=HOLD_REQUIRED,
            reason_code="OWNER_REPORTS_NO_CURRENT_EXPLICIT_ATTACHMENT",
        )

    try:
        attachment.validate()
    except ValueError as exc:
        return _decision(
            support, lineage, disposition="HOLD_ATTACHMENT_INVALID",
            reason_code=str(exc),
        )

    expected = (
        support.materialization_proposal_basis_digest,
        support.proposal_evidence_support_digest,
        lineage.proposal_id,
        lineage.proposal_basis_digest,
    )
    observed = (
        attachment.materialization_proposal_basis_digest,
        attachment.materialization_support_digest,
        attachment.lineage_proposal_id,
        attachment.lineage_proposal_basis_digest,
    )
    if observed != expected:
        return _decision(
            support, lineage, disposition="HOLD_ATTACHMENT_IDENTITY_MISMATCH",
            reason_code="OWNER_ATTACHMENT_DOES_NOT_BIND_EXACT_PARENT_IDENTITIES",
            attachment=attachment,
        )

    relation_id = _sha({
        "domain": SCHEMA,
        "o65r_proof": [support.proof_head, support.run_id, support.job_id],
        "o66_proof": [lineage.proof_head, lineage.run_id, lineage.job_id],
        "materialization_basis": support.materialization_proposal_basis_digest,
        "support_digest": support.proposal_evidence_support_digest,
        "lineage_proposal_id": lineage.proposal_id,
        "lineage_proposal_basis": lineage.proposal_basis_digest,
        "lineage_relation_id": lineage.relation_id,
        "lineage_owner_epoch": lineage.relation_owner_epoch,
        "attachment_id": attachment.attachment_id,
        "attachment_owner_generation": attachment.owner_generation,
        "attachment_owner_state_epoch": attachment.owner_state_epoch,
        "authority_ceiling": "NONEXECUTABLE_D0",
    })
    return _decision(
        support, lineage, disposition=BOUND,
        reason_code="EXACT_OWNER_ATTACHMENT_BINDS_SUPPORT_TO_LINEAGE_WITHOUT_AUTHORITY_PROMOTION",
        attachment=attachment, relation_id=relation_id,
    )


def example_support() -> MaterializationSupportProjection:
    return MaterializationSupportProjection(
        proof_head=O65R_PROOF_HEAD,
        semantic_head=O65R_SEMANTIC_HEAD,
        run_id=O65R_RUN,
        job_id=O65R_JOB,
        source_blob=O65R_SOURCE_BLOB,
        materialization_proposal_basis_digest=O65R_MATERIALIZATION_BASIS,
        proposal_evidence_support_digest=_sha({"fixture": "o67:o65r:support"}),
        bounded_evidence_supports_exact_proposal=True,
    )


def example_lineage() -> PreAttemptLifecycleProjection:
    return PreAttemptLifecycleProjection(
        proof_head=O66_PROOF_HEAD,
        run_id=O66_RUN,
        job_id=O66_JOB,
        source_blob=O66_SOURCE_BLOB,
        disposition=O66_BOUND,
        relation_id=_sha({"fixture": "o67:o66:relation"}),
        proposal_id=_sha({"fixture": "o67:o66:proposal"}),
        proposal_basis_digest=_sha({"fixture": "o67:o66:proposal-basis"}),
        relation_owner_epoch="relation-epoch:o67:1",
    )


def main() -> None:
    decision = evaluate_materialization_support_lineage(
        support=example_support(),
        lineage=example_lineage(),
        attachment_resolver=None,
    )
    print(json.dumps(decision.to_dict(), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
