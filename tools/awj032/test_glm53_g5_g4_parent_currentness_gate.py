from __future__ import annotations

from dataclasses import replace
import unittest

from tools.awj032.glm53_g5_recompute_admission import (
    ADMIT_BOUNDED_G3_RECOMPUTE_ATTEMPT,
    G4_PROOF_HEAD,
    G4_PROOF_JOB,
    G4_PROOF_RUN,
    G5RecomputeAdmissionReceipt,
    PR754_OWNER_HEAD,
    PR754_PROOF_JOB,
    PR754_PROOF_MIRROR_HEAD,
    PR754_PROOF_RUN,
    PR755_HEAD,
    PR755_PROOF_JOB,
    PR755_PROOF_RUN,
    SCHEMA as G5_SCHEMA,
)
from tools.awj032.glm53_g5_g4_parent_currentness_gate import (
    CURRENT_G4_PROOF_COORDINATES_PRESENT,
    G4_V1_HISTORICAL_PROOF_HEAD,
    G4_V1_HISTORICAL_PROOF_JOB,
    G4_V1_HISTORICAL_PROOF_RUN,
    G4_V2_PROOF_HEAD,
    G4_V2_PROOF_JOB,
    G4_V2_PROOF_RUN,
    HOLD_STALE_G4_PARENT_PROOF,
    HOLD_UNKNOWN_G4_PARENT_PROOF,
    audit_g5_g4_parent_currentness,
)


def d(ch: str) -> str:
    return ch * 64


def stale_g5_receipt() -> G5RecomputeAdmissionReceipt:
    return G5RecomputeAdmissionReceipt(
        schema=G5_SCHEMA,
        g4_proof_head=G4_PROOF_HEAD,
        g4_proof_run=G4_PROOF_RUN,
        g4_proof_job=G4_PROOF_JOB,
        pr754_owner_head=PR754_OWNER_HEAD,
        pr754_proof_mirror_head=PR754_PROOF_MIRROR_HEAD,
        pr754_proof_run=PR754_PROOF_RUN,
        pr754_proof_job=PR754_PROOF_JOB,
        pr755_head=PR755_HEAD,
        pr755_proof_run=PR755_PROOF_RUN,
        pr755_proof_job=PR755_PROOF_JOB,
        g4_receipt_digest=d("a"),
        progress_receipt_digest=d("b"),
        version_transition_receipt_digest=d("c"),
        read_currentness_witness_digest=d("d"),
        disposition=ADMIT_BOUNDED_G3_RECOMPUTE_ATTEMPT,
        source_binding_changed=True,
        bounded_g3_recompute_attempt_admitted=True,
    )


class G5G4ParentCurrentnessGateTests(unittest.TestCase):
    def test_current_g5_owner_reproduces_historical_v1_coordinates(self) -> None:
        self.assertEqual(
            (G4_PROOF_HEAD, G4_PROOF_RUN, G4_PROOF_JOB),
            (
                G4_V1_HISTORICAL_PROOF_HEAD,
                G4_V1_HISTORICAL_PROOF_RUN,
                G4_V1_HISTORICAL_PROOF_JOB,
            ),
        )

    def test_positive_g5_receipt_is_quarantined_when_parent_proof_is_v1(self) -> None:
        audit = audit_g5_g4_parent_currentness(stale_g5_receipt())
        self.assertEqual(audit.disposition, HOLD_STALE_G4_PARENT_PROOF)
        self.assertTrue(audit.historical_green_recognized)
        self.assertFalse(audit.current_parent_proof_coordinates_match)
        self.assertFalse(audit.g5_terminal_credit_allowed)
        self.assertFalse(audit.g5_recompute_admission_reissued)

    def test_current_v2_coordinates_are_distinguished_but_not_self_promoted(self) -> None:
        receipt = replace(
            stale_g5_receipt(),
            g4_proof_head=G4_V2_PROOF_HEAD,
            g4_proof_run=G4_V2_PROOF_RUN,
            g4_proof_job=G4_V2_PROOF_JOB,
        )
        audit = audit_g5_g4_parent_currentness(receipt)
        self.assertEqual(audit.disposition, CURRENT_G4_PROOF_COORDINATES_PRESENT)
        self.assertTrue(audit.current_parent_proof_coordinates_match)
        self.assertFalse(audit.g5_terminal_credit_allowed)
        self.assertFalse(audit.g5_recompute_admission_reissued)

    def test_unknown_parent_generation_fails_closed(self) -> None:
        receipt = replace(
            stale_g5_receipt(),
            g4_proof_head="f" * 40,
            g4_proof_run=1,
            g4_proof_job=2,
        )
        audit = audit_g5_g4_parent_currentness(receipt)
        self.assertEqual(audit.disposition, HOLD_UNKNOWN_G4_PARENT_PROOF)
        self.assertFalse(audit.historical_green_recognized)
        self.assertFalse(audit.current_parent_proof_coordinates_match)

    def test_projection_receipt_is_deterministic(self) -> None:
        a = audit_g5_g4_parent_currentness(stale_g5_receipt())
        b = audit_g5_g4_parent_currentness(stale_g5_receipt())
        self.assertEqual(a.receipt_digest, b.receipt_digest)

    def test_gate_cannot_grant_terminal_credit_or_effects(self) -> None:
        audit = audit_g5_g4_parent_currentness(stale_g5_receipt())
        for field in (
            "g5_terminal_credit_allowed",
            "g5_recompute_admission_reissued",
            "g4_owner_currentness_minted",
            "model_or_provider_execution_authorized",
            "transfer_effect_authorized",
            "physical_io_proven",
            "semantic_k27_authority_minted",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
            "merge_deploy_spend_public_financial_human_effect",
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                replace(audit, **{field: True}).validate_claim_ceiling()


if __name__ == "__main__":
    unittest.main()
