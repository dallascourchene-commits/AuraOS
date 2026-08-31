"""G5 W3: fail closed on a superseded G4 parent-proof generation.

D0 / HS1 / NONPROMOTING / STACKED ADDENDUM TO PR #766.

G5's recompute-admission algebra is not reimplemented here. This guard owns only
one temporal/provenance relation: the G4 proof coordinates embedded in a G5
receipt must not be treated as current after canonical G4 semantics changed.

The current G5 owner still embeds the exact-green G4 v1 proof. Canonical G4 has
since repaired its caller-currentness boundary and earned a new exact hosted
proof. A historical green is valid history, not current parent closure.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

from tools.awj032.glm53_g5_recompute_admission import (
    G5RecomputeAdmissionReceipt,
    SCHEMA as G5_SCHEMA,
)

SCHEMA = "AURA-GLM53-G5-G4-PARENT-CURRENTNESS-GATE-v1"

G5_OWNER_PR = 766
G5_OWNER_HEAD_AT_REPAIR = "8b1f38a6c917a9e7f1af941273164ca0db69821b"

G4_V1_HISTORICAL_PROOF_HEAD = "68d76cb7d08366d085be13ad68871ab3c9cf00e1"
G4_V1_HISTORICAL_PROOF_RUN = 33436142388
G4_V1_HISTORICAL_PROOF_JOB = 99632931053

G4_V2_SEMANTIC_REPAIR_HEAD = "981971f5b34da2046f539ee92f3e272eccac8360"
G4_V2_PROOF_HEAD = "025d619d24d95dd6acc29981b1bd61bce92e25a3"
G4_V2_PROOF_RUN = 33436948448
G4_V2_PROOF_JOB = 99635568410

HOLD_STALE_G4_PARENT_PROOF = "HOLD_STALE_G4_PARENT_PROOF"
HOLD_UNKNOWN_G4_PARENT_PROOF = "HOLD_UNKNOWN_G4_PARENT_PROOF"
CURRENT_G4_PROOF_COORDINATES_PRESENT = "CURRENT_G4_PROOF_COORDINATES_PRESENT"


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
class G5ParentCurrentnessGateReceipt:
    schema: str
    g5_owner_pr: int
    g5_owner_head_at_repair: str
    g5_schema: str
    g5_receipt_projection_digest: str
    observed_g4_proof_head: str
    observed_g4_proof_run: int
    observed_g4_proof_job: int
    required_g4_semantic_repair_head: str
    required_g4_proof_head: str
    required_g4_proof_run: int
    required_g4_proof_job: int
    disposition: str
    historical_green_recognized: bool
    current_parent_proof_coordinates_match: bool
    g5_terminal_credit_allowed: bool = False
    g5_recompute_admission_reissued: bool = False
    g4_owner_currentness_minted: bool = False
    model_or_provider_execution_authorized: bool = False
    transfer_effect_authorized: bool = False
    physical_io_proven: bool = False
    semantic_k27_authority_minted: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False
    merge_deploy_spend_public_financial_human_effect: bool = False

    def validate_claim_ceiling(self) -> None:
        if self.schema != SCHEMA:
            raise ValueError("G5_PARENT_GATE_SCHEMA_MISMATCH")
        if self.g5_owner_pr != G5_OWNER_PR:
            raise ValueError("G5_PARENT_GATE_OWNER_MISMATCH")
        if self.g5_owner_head_at_repair != G5_OWNER_HEAD_AT_REPAIR:
            raise ValueError("G5_PARENT_GATE_REPAIR_HEAD_MISMATCH")
        if self.g5_schema != G5_SCHEMA:
            raise ValueError("G5_PARENT_GATE_G5_SCHEMA_MISMATCH")
        if len(self.g5_receipt_projection_digest) != 64:
            raise ValueError("G5_PARENT_GATE_RECEIPT_DIGEST_INVALID")
        if (
            self.required_g4_semantic_repair_head,
            self.required_g4_proof_head,
            self.required_g4_proof_run,
            self.required_g4_proof_job,
        ) != (
            G4_V2_SEMANTIC_REPAIR_HEAD,
            G4_V2_PROOF_HEAD,
            G4_V2_PROOF_RUN,
            G4_V2_PROOF_JOB,
        ):
            raise ValueError("G5_PARENT_GATE_REQUIRED_G4_COORDINATES_MISMATCH")

        if self.disposition == HOLD_STALE_G4_PARENT_PROOF:
            if not self.historical_green_recognized:
                raise ValueError("G5_PARENT_GATE_STALE_MUST_RECOGNIZE_HISTORY")
            if self.current_parent_proof_coordinates_match:
                raise ValueError("G5_PARENT_GATE_STALE_CANNOT_MATCH_CURRENT")
        elif self.disposition == CURRENT_G4_PROOF_COORDINATES_PRESENT:
            if not self.current_parent_proof_coordinates_match:
                raise ValueError("G5_PARENT_GATE_CURRENT_MUST_MATCH_CURRENT")
        elif self.disposition == HOLD_UNKNOWN_G4_PARENT_PROOF:
            if self.historical_green_recognized or self.current_parent_proof_coordinates_match:
                raise ValueError("G5_PARENT_GATE_UNKNOWN_CLASSIFICATION_CONFLICT")
        else:
            raise ValueError("G5_PARENT_GATE_DISPOSITION_INVALID")

        if any(
            (
                self.g5_terminal_credit_allowed,
                self.g5_recompute_admission_reissued,
                self.g4_owner_currentness_minted,
                self.model_or_provider_execution_authorized,
                self.transfer_effect_authorized,
                self.physical_io_proven,
                self.semantic_k27_authority_minted,
                self.native_private_transformer_kv_accessed,
                self.gate10_promoted,
                self.merge_deploy_spend_public_financial_human_effect,
            )
        ):
            raise ValueError("G5_PARENT_GATE_CANNOT_WIDEN_AUTHORITY_OR_TERMINALITY")

    @property
    def receipt_digest(self) -> str:
        self.validate_claim_ceiling()
        return _sha({"domain": SCHEMA, "receipt": asdict(self)})


def audit_g5_g4_parent_currentness(
    receipt: G5RecomputeAdmissionReceipt,
) -> G5ParentCurrentnessGateReceipt:
    """Classify only the parent-proof generation carried by an existing G5 receipt.

    Deliberately do not call the G5 receipt's positive claim validator here: the
    point of this W3 gate is to inspect a historical receipt whose parent-proof
    constants are themselves under challenge. No G5 admission consequence is
    reissued by this function.
    """
    if not isinstance(receipt, G5RecomputeAdmissionReceipt):
        raise TypeError("G5_PARENT_GATE_TYPED_RECEIPT_REQUIRED")

    observed = (
        receipt.g4_proof_head,
        receipt.g4_proof_run,
        receipt.g4_proof_job,
    )
    historical = observed == (
        G4_V1_HISTORICAL_PROOF_HEAD,
        G4_V1_HISTORICAL_PROOF_RUN,
        G4_V1_HISTORICAL_PROOF_JOB,
    )
    current = observed == (G4_V2_PROOF_HEAD, G4_V2_PROOF_RUN, G4_V2_PROOF_JOB)

    if historical:
        disposition = HOLD_STALE_G4_PARENT_PROOF
    elif current:
        disposition = CURRENT_G4_PROOF_COORDINATES_PRESENT
    else:
        disposition = HOLD_UNKNOWN_G4_PARENT_PROOF

    projection_digest = _sha(
        {
            "domain": "AURA-GLM53-G5-RECEIPT-PROJECTION-v1",
            "g5_schema": receipt.schema,
            "g4_proof_head": receipt.g4_proof_head,
            "g4_proof_run": receipt.g4_proof_run,
            "g4_proof_job": receipt.g4_proof_job,
            "g4_receipt_digest": receipt.g4_receipt_digest,
            "progress_receipt_digest": receipt.progress_receipt_digest,
            "version_transition_receipt_digest": receipt.version_transition_receipt_digest,
            "read_currentness_witness_digest": receipt.read_currentness_witness_digest,
            "g5_disposition": receipt.disposition,
            "g5_admission_boolean": receipt.bounded_g3_recompute_attempt_admitted,
        }
    )

    result = G5ParentCurrentnessGateReceipt(
        schema=SCHEMA,
        g5_owner_pr=G5_OWNER_PR,
        g5_owner_head_at_repair=G5_OWNER_HEAD_AT_REPAIR,
        g5_schema=receipt.schema,
        g5_receipt_projection_digest=projection_digest,
        observed_g4_proof_head=receipt.g4_proof_head,
        observed_g4_proof_run=receipt.g4_proof_run,
        observed_g4_proof_job=receipt.g4_proof_job,
        required_g4_semantic_repair_head=G4_V2_SEMANTIC_REPAIR_HEAD,
        required_g4_proof_head=G4_V2_PROOF_HEAD,
        required_g4_proof_run=G4_V2_PROOF_RUN,
        required_g4_proof_job=G4_V2_PROOF_JOB,
        disposition=disposition,
        historical_green_recognized=historical,
        current_parent_proof_coordinates_match=current,
    )
    result.validate_claim_ceiling()
    return result
