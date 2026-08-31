from __future__ import annotations

from dataclasses import replace
import unittest

import tools.awj032.glm53_g6_gate10_owner_host_evidence_request as g6
import tools.awj032.glm53_g6_admission_identity_binding_addendum as a

D0 = "0" * 64
D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64
D4 = "4" * 64
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
        D4,
        g6.REQUIRED_EVIDENCE_AXES,
        g6.OPEN_GATE10_DEBT,
        True,
    )


def identity() -> a.AdmissionReuseIdentityProjection:
    return a.AdmissionReuseIdentityProjection(
        proof_head=a.REUSE_HEAD,
        proof_run=a.REUSE_RUN,
        proof_job=a.REUSE_JOB,
        source_blob=a.REUSE_SOURCE_BLOB,
        test_blob=a.REUSE_TEST_BLOB,
        admission_family=a.REUSE_FAMILY,
        disposition=a.REUSE_DISPOSITION,
        admission_receipt_digest=D4,
        reuse_digest=D5,
        subject_identity="glm53:q18:representative-e8-c2",
        source_generation_key="source:glm53:7cda819:q18-set",
        evidence_generation_key="evidence:q18:current-generation",
        owner_context_key="owner-context:glm53-c2:g1",
        decision_context_key="decision-context:q18:g1",
    )


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

    def test_exact_identity_binds_without_authenticating_or_executing(self) -> None:
        receipt = compile_bound()
        self.assertEqual(receipt.disposition, a.IDENTITY_BOUND_EXTERNAL_AUTH_REQUIRED)
        self.assertTrue(receipt.base_g6_request_compiled)
        self.assertTrue(receipt.base_g6_request_constructed_by_this_contract)
        self.assertFalse(receipt.caller_supplied_base_request_accepted)
        self.assertTrue(receipt.exact_glm53_reuse_family_bound)
        self.assertTrue(receipt.exact_reuse_candidate_identity_bound)
        self.assertEqual(receipt.admission_receipt_digest, D4)
        self.assertEqual(receipt.reuse_digest, D5)
        self.assertEqual(receipt.subject_identity, identity().subject_identity)
        self.assertFalse(receipt.reuse_receipt_authenticated_by_this_contract)
        self.assertFalse(receipt.source_currentness_proven_by_this_contract)
        self.assertFalse(receipt.execution_authorized)
        self.assertFalse(receipt.gate10_promoted)

    def test_generic_bounded_c2_family_cannot_cross_cast_as_glm53(self) -> None:
        for wrong in ("BOUNDED_C2_PROPOSAL", "HYDRATION_TRANSACTION", "OTHER"):
            with self.subTest(wrong=wrong), self.assertRaisesRegex(
                ValueError, a.HOLD_EXACT_REUSE_FAMILY_REQUIRED
            ):
                compile_bound(reuse_identity=replace(identity(), admission_family=wrong))

    def test_non_candidate_disposition_cannot_bind(self) -> None:
        with self.assertRaisesRegex(ValueError, a.HOLD_REUSE_CANDIDATE_REQUIRED):
            compile_bound(
                reuse_identity=replace(identity(), disposition="HOLD_SUBJECT_CHANGED")
            )

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
            with self.subTest(field=field), self.assertRaises(ValueError):
                compile_bound(reuse_identity=replace(identity(), **{field: " "}))

    def test_every_pr769_digest_identity_axis_is_required(self) -> None:
        for field in ("admission_receipt_digest", "reuse_digest"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                compile_bound(
                    reuse_identity=replace(identity(), **{field: "not-a-digest"})
                )

    def test_every_pr769_identity_axis_changes_binding_even_when_base_summary_is_same(self) -> None:
        canonical = compile_bound()
        substitutions = {
            "admission_receipt_digest": "a" * 64,
            "reuse_digest": "b" * 64,
            "subject_identity": identity().subject_identity + ":other",
            "source_generation_key": identity().source_generation_key + ":other",
            "evidence_generation_key": identity().evidence_generation_key + ":other",
            "owner_context_key": identity().owner_context_key + ":other",
            "decision_context_key": identity().decision_context_key + ":other",
        }
        for field, value in substitutions.items():
            with self.subTest(field=field):
                changed = compile_bound(
                    reuse_identity=replace(identity(), **{field: value})
                )
                self.assertEqual(
                    canonical.base_g6_request_digest, changed.base_g6_request_digest
                )
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
            with self.subTest(field=field), self.assertRaisesRegex(
                ValueError, "REUSE_PARENT_PROOF_COORDINATE_MISMATCH"
            ):
                compile_bound(reuse_identity=replace(identity(), **{field: value}))

    def test_reuse_projection_cannot_self_mint_truth_or_authority(self) -> None:
        for field in (
            "admission_reused_as_authority",
            "source_currentness_proven",
            "execution_authorized",
            "effect_authorized",
            "semantic_k27_authority",
            "native_private_transformer_kv_accessed",
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                compile_bound(reuse_identity=replace(identity(), **{field: True}))

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

    def test_deterministic(self) -> None:
        first = compile_bound()
        second = compile_bound()
        self.assertEqual(first, second)
        self.assertEqual(first.receipt_digest, second.receipt_digest)

    def test_identity_binding_lattice_exhausts_16_summary_states(self) -> None:
        self.assertEqual(a.prove_identity_binding_lattice(), 16)

    def test_laws(self) -> None:
        for law in (
            "ReuseCandidateSummary!=AdmissionReuseReceiptIdentity",
            "GLM53AdmissionFamilyMustRemainExact",
            "AdmissionReceiptDigest+Subject+Source+Evidence+Owner+Decision+ReuseDigestMustSurviveProjection",
            "CallerSuppliedBaseRequest+IndependentIdentity!=JoinedRequestIdentity",
            "IdentityBoundWrapperMustConstructBaseRequest",
            "IdentityBinding!=ReceiptProducerAuthentication",
            "RepoHeadChanged!=TensorSourceGenerationChanged",
            "CoordinateMemory!=MODEL_PREFIX_KV",
        ):
            self.assertIn(law, a.LAWS)


if __name__ == "__main__":
    unittest.main()
