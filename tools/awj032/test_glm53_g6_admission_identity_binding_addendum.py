from __future__ import annotations

from dataclasses import replace
import unittest

import tools.aura_generation_bound_admission_reuse as parent769
import tools.awj032.glm53_g6_gate10_owner_host_evidence_request as g6
import tools.awj032.glm53_g6_admission_identity_binding_addendum as a

D0 = "0" * 64
D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64
D5 = "5" * 64


def provenance(*, complete: bool = True) -> g6.ObservationProvenanceContractProjection:
    return g6.ObservationProvenanceContractProjection(
        g6.PROV_HEAD,
        g6.PROV_RUN,
        g6.PROV_JOB,
        g6.PROV_SOURCE_BLOB,
        True,
        True,
        complete,
    )


def owner() -> g6.OwnerHostTargetProjection:
    return g6.OwnerHostTargetProjection(
        "owner-host:local:glm53-c2",
        "principal:g1",
        "host:g1",
        "runtime:g1",
        "cache:g1",
        "storage:g1",
        D0,
        "artifact:awj032:g6:owner-host-evidence",
    )


def evidence() -> g6.EvidenceContractProjection:
    return g6.EvidenceContractProjection(
        D1,
        D2,
        D3,
        "4" * 64,
        g6.REQUIRED_EVIDENCE_AXES,
        g6.OPEN_GATE10_DEBT,
        True,
    )


def identity(**changes: object) -> a.AdmissionReuseIdentityProjection:
    candidate = a.AdmissionReuseIdentityProjection(
        proof_head=a.REUSE_HEAD,
        proof_run=a.REUSE_RUN,
        proof_job=a.REUSE_JOB,
        source_blob=a.REUSE_SOURCE_BLOB,
        test_blob=a.REUSE_TEST_BLOB,
        admission_family=a.REUSE_FAMILY,
        disposition=a.REUSE_DISPOSITION,
        admission_receipt_digest=a.Q18_RECEIPT_DIGEST,
        reuse_digest=D5,
        subject_identity="subject:q18",
        source_generation_key="source-generation:q18:1",
        evidence_generation_key="evidence-generation:q18:1",
        owner_context_key="owner-context:q18:1",
        decision_context_key="decision-context:q18:1",
    )
    candidate = replace(candidate, **changes)
    return replace(candidate, reuse_digest=a.expected_pr769_reuse_digest(candidate))


def compile_bound(
    *,
    reuse_identity: a.AdmissionReuseIdentityProjection | None = None,
    provenance_complete: bool = True,
) -> a.G6AdmissionIdentityBindingReceipt:
    return a.compile_identity_bound_g6_request(
        reuse_identity=reuse_identity or identity(),
        provenance=provenance(complete=provenance_complete),
        owner=owner(),
        evidence=evidence(),
    )


class G6AdmissionIdentityBindingTests(unittest.TestCase):
    def test_public_api_constructs_base_internally_and_accepts_no_base_request(self) -> None:
        self.assertEqual(
            a.public_api_parameters(),
            ("reuse_identity", "provenance", "owner", "evidence"),
        )
        self.assertFalse(hasattr(a, "bind_g6_request_to_admission_identity"))

    def test_exact_q18_pr769_identity_binds_without_authenticating_or_executing(self) -> None:
        receipt = compile_bound()
        self.assertEqual(receipt.disposition, a.IDENTITY_BOUND_EXTERNAL_AUTH_REQUIRED)
        self.assertTrue(receipt.base_g6_request_compiled)
        self.assertTrue(receipt.base_g6_request_constructed_by_this_contract)
        self.assertFalse(receipt.caller_supplied_base_request_accepted)
        self.assertTrue(receipt.exact_glm53_reuse_family_bound)
        self.assertTrue(receipt.exact_q18_admission_receipt_bound)
        self.assertTrue(receipt.pr769_reuse_digest_structurally_verified)
        self.assertTrue(receipt.exact_reuse_candidate_identity_bound)
        self.assertEqual(receipt.admission_receipt_digest, a.Q18_RECEIPT_DIGEST)
        self.assertEqual(receipt.reuse_digest, identity().reuse_digest)
        self.assertEqual(receipt.subject_identity, identity().subject_identity)
        self.assertFalse(receipt.reuse_receipt_authenticated_by_this_contract)
        self.assertFalse(receipt.source_currentness_proven_by_this_contract)
        self.assertFalse(receipt.execution_authorized)
        self.assertFalse(receipt.gate10_promoted)

    def test_parent769_emission_matches_reproduced_reuse_digest(self) -> None:
        projected = identity()
        family = parent769.AdmissionFamily.GLM53_BOUNDED_C2_PROPOSAL
        admission = parent769.AdmissionReceiptProjectionV1(
            family=family,
            producer_head=parent769.EXPECTED_HEAD[family],
            receipt_digest=projected.admission_receipt_digest,
            admission_disposition=parent769.EXPECTED_POSITIVE_DISPOSITION[family],
            subject_identity=projected.subject_identity,
            source_generation_key=projected.source_generation_key,
            evidence_generation_key=projected.evidence_generation_key,
            owner_context_key=projected.owner_context_key,
            decision_context_key=projected.decision_context_key,
            bounded_admission_positive=True,
        )
        current = parent769.CurrentAdmissionUseContextV1(
            producer_head=admission.producer_head,
            subject_identity=admission.subject_identity,
            source_generation_key=admission.source_generation_key,
            evidence_generation_key=admission.evidence_generation_key,
            owner_context_key=admission.owner_context_key,
            decision_context_key=admission.decision_context_key,
        )
        parent_receipt = parent769.revalidate_admission_reuse(
            admission=admission, current=current
        )
        self.assertEqual(
            parent_receipt.disposition, parent769.ReuseDisposition.REUSE_CANDIDATE
        )
        self.assertEqual(parent_receipt.admission_receipt_digest, a.Q18_RECEIPT_DIGEST)
        self.assertEqual(parent_receipt.reuse_digest, projected.reuse_digest)
        self.assertEqual(
            parent_receipt.reuse_digest, a.expected_pr769_reuse_digest(projected)
        )

    def test_generic_bounded_c2_family_cannot_cross_cast_as_glm53(self) -> None:
        for wrong in ("BOUNDED_C2_PROPOSAL", "HYDRATION_TRANSACTION", "OTHER"):
            with self.subTest(wrong=wrong), self.assertRaisesRegex(
                ValueError, a.HOLD_EXACT_REUSE_FAMILY_REQUIRED
            ):
                compile_bound(reuse_identity=identity(admission_family=wrong))

    def test_non_candidate_disposition_cannot_bind(self) -> None:
        with self.assertRaisesRegex(ValueError, a.HOLD_REUSE_CANDIDATE_REQUIRED):
            compile_bound(reuse_identity=identity(disposition="HOLD_SUBJECT_CHANGED"))

    def test_same_family_different_glm53_admission_receipt_cannot_cross_cast(self) -> None:
        other = identity(admission_receipt_digest="a" * 64)
        with self.assertRaisesRegex(
            ValueError, a.HOLD_EXACT_Q18_ADMISSION_RECEIPT_REQUIRED
        ):
            compile_bound(reuse_identity=other)

    def test_digest_shaped_but_unrelated_reuse_digest_is_rejected(self) -> None:
        forged = replace(identity(), reuse_digest="b" * 64)
        with self.assertRaisesRegex(ValueError, a.HOLD_PR769_REUSE_DIGEST_MISMATCH):
            compile_bound(reuse_identity=forged)

    def test_identity_change_with_stale_reuse_digest_is_rejected(self) -> None:
        original = identity()
        forged = replace(original, subject_identity=original.subject_identity + ":drift")
        with self.assertRaisesRegex(ValueError, a.HOLD_PR769_REUSE_DIGEST_MISMATCH):
            compile_bound(reuse_identity=forged)

    def test_failed_base_g6_precondition_cannot_receive_identity_binding(self) -> None:
        with self.assertRaisesRegex(ValueError, a.HOLD_BASE_G6_REQUEST_REQUIRED):
            compile_bound(provenance_complete=False)

    def test_every_pr769_text_identity_axis_is_required(self) -> None:
        for field in (
            "subject_identity",
            "source_generation_key",
            "evidence_generation_key",
            "owner_context_key",
            "decision_context_key",
        ):
            candidate = replace(identity(), **{field: " "})
            with self.subTest(field=field), self.assertRaises(ValueError):
                compile_bound(reuse_identity=candidate)

    def test_malformed_identity_digests_are_rejected(self) -> None:
        for field in ("admission_receipt_digest", "reuse_digest"):
            candidate = replace(identity(), **{field: "not-a-digest"})
            with self.subTest(field=field), self.assertRaises(ValueError):
                compile_bound(reuse_identity=candidate)

    def test_each_coherent_current_use_axis_changes_final_binding_while_base_summary_stays_same(self) -> None:
        canonical = compile_bound()
        substitutions = {
            "subject_identity": identity().subject_identity + ":other",
            "source_generation_key": identity().source_generation_key + ":other",
            "evidence_generation_key": identity().evidence_generation_key + ":other",
            "owner_context_key": identity().owner_context_key + ":other",
            "decision_context_key": identity().decision_context_key + ":other",
        }
        for field, value in substitutions.items():
            with self.subTest(field=field):
                changed = compile_bound(reuse_identity=identity(**{field: value}))
                self.assertEqual(
                    canonical.base_g6_request_digest, changed.base_g6_request_digest
                )
                self.assertNotEqual(canonical.reuse_digest, changed.reuse_digest)
                self.assertNotEqual(canonical.binding_digest, changed.binding_digest)
                self.assertNotEqual(canonical.receipt_digest, changed.receipt_digest)

    def test_parent_proof_coordinate_substitution_rejected(self) -> None:
        for field, value in (
            ("proof_head", "f" * 40),
            ("proof_run", a.REUSE_RUN + 1),
            ("proof_job", a.REUSE_JOB + 1),
            ("source_blob", "f" * 40),
            ("test_blob", "e" * 40),
        ):
            candidate = replace(identity(), **{field: value})
            with self.subTest(field=field), self.assertRaisesRegex(
                ValueError, "REUSE_PARENT_PROOF_COORDINATE_MISMATCH"
            ):
                compile_bound(reuse_identity=candidate)

    def test_reuse_projection_cannot_self_mint_truth_or_authority(self) -> None:
        for field in (
            "admission_reused_as_authority",
            "source_currentness_proven",
            "execution_authorized",
            "effect_authorized",
            "semantic_k27_authority",
            "native_private_transformer_kv_accessed",
        ):
            candidate = replace(identity(), **{field: True})
            with self.subTest(field=field), self.assertRaises(ValueError):
                compile_bound(reuse_identity=candidate)

    def test_binding_receipt_cannot_accept_caller_base_or_mint_truth_authority_gate10(self) -> None:
        receipt = compile_bound()
        for field in (
            "caller_supplied_base_request_accepted",
            "reuse_receipt_authenticated_by_this_contract",
            "source_currentness_proven_by_this_contract",
            "owner_authenticated_by_this_contract",
            "tensor_payload_bound",
            "model_or_provider_execution_observed",
            "physical_io_proven",
            "observer_backend_authenticated",
            "auraos_resident_routing_proven",
            "replay_recovery_proven",
            "execution_authorized",
            "semantic_k27_authority_minted",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
            "merge_deploy_spend_public_financial_human_effect",
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                replace(receipt, **{field: True}).validate_claim_ceiling()

    def test_parent_reuse_digest_reproduction_is_deterministic(self) -> None:
        first = identity()
        second = identity()
        self.assertEqual(first.reuse_digest, second.reuse_digest)
        self.assertEqual(first.reuse_digest, a.expected_pr769_reuse_digest(first))

    def test_binding_is_deterministic(self) -> None:
        first = compile_bound()
        second = compile_bound()
        self.assertEqual(first, second)
        self.assertEqual(first.receipt_digest, second.receipt_digest)

    def test_identity_binding_lattice_exhausts_64_summary_states(self) -> None:
        self.assertEqual(a.prove_identity_binding_lattice(), 64)

    def test_laws(self) -> None:
        for law in (
            "ReuseCandidateSummary!=AdmissionReuseReceiptIdentity",
            "GLM53AdmissionFamilyMustRemainExact",
            "ExactQ18AdmissionReceiptMustRemainBound",
            "PR769ReuseDigestMustCommitExactIdentityVector",
            "DigestShape!=DigestRelationProof",
            "CallerSuppliedBaseRequest+IndependentIdentity!=JoinedRequestIdentity",
            "IdentityBoundWrapperMustConstructBaseRequest",
            "IdentityBinding!=ReceiptProducerAuthentication",
            "RepoHeadChanged!=TensorSourceGenerationChanged",
            "CoordinateMemory!=MODEL_PREFIX_KV",
        ):
            self.assertIn(law, a.LAWS)


if __name__ == "__main__":
    unittest.main()
