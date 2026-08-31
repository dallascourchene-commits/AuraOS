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


def base_reuse() -> g6.AdmissionReuseProjection:
    return g6.AdmissionReuseProjection(
        proof_head=g6.REUSE_HEAD,
        proof_run=g6.REUSE_RUN,
        proof_job=g6.REUSE_JOB,
        source_blob=g6.REUSE_SOURCE_BLOB,
        test_blob=g6.REUSE_TEST_BLOB,
        admission_family=g6.REUSE_FAMILY,
        disposition=g6.REUSE_DISPOSITION,
        current_context_exact=True,
    )


def provenance() -> g6.ObservationProvenanceContractProjection:
    return g6.ObservationProvenanceContractProjection(
        g6.PROV_HEAD,
        g6.PROV_RUN,
        g6.PROV_JOB,
        g6.PROV_SOURCE_BLOB,
        True,
        True,
        True,
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


def base_request(*, provenance_ok: bool = True) -> g6.G6RequestReceipt:
    p = provenance()
    if not provenance_ok:
        p = replace(p, producer_authentication_required=False)
    return g6.compile_gate10_owner_host_evidence_request(
        reuse=base_reuse(), provenance=p, owner=owner(), evidence=evidence()
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


class G6AdmissionIdentityBindingTests(unittest.TestCase):
    def test_exact_identity_binds_without_authenticating_or_executing(self) -> None:
        receipt = a.bind_g6_request_to_admission_identity(
            base_request=base_request(), reuse_identity=identity()
        )
        self.assertEqual(receipt.disposition, a.IDENTITY_BOUND_EXTERNAL_AUTH_REQUIRED)
        self.assertTrue(receipt.base_g6_request_compiled)
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
                a.bind_g6_request_to_admission_identity(
                    base_request=base_request(),
                    reuse_identity=replace(identity(), admission_family=wrong),
                )

    def test_non_candidate_disposition_cannot_bind(self) -> None:
        with self.assertRaisesRegex(ValueError, a.HOLD_REUSE_CANDIDATE_REQUIRED):
            a.bind_g6_request_to_admission_identity(
                base_request=base_request(),
                reuse_identity=replace(identity(), disposition="HOLD_SUBJECT_CHANGED"),
            )

    def test_uncompiled_base_request_cannot_receive_identity_binding(self) -> None:
        hold = base_request(provenance_ok=False)
        self.assertNotEqual(hold.disposition, g6.COMPILED)
        with self.assertRaisesRegex(ValueError, a.HOLD_BASE_G6_REQUEST_REQUIRED):
            a.bind_g6_request_to_admission_identity(
                base_request=hold, reuse_identity=identity()
            )

    def test_every_pr769_text_identity_axis_is_required(self) -> None:
        for field in (
            "subject_identity",
            "source_generation_key",
            "evidence_generation_key",
            "owner_context_key",
            "decision_context_key",
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                a.bind_g6_request_to_admission_identity(
                    base_request=base_request(),
                    reuse_identity=replace(identity(), **{field: " "}),
                )

    def test_every_pr769_digest_identity_axis_is_required(self) -> None:
        for field in ("admission_receipt_digest", "reuse_digest"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                a.bind_g6_request_to_admission_identity(
                    base_request=base_request(),
                    reuse_identity=replace(identity(), **{field: "not-a-digest"}),
                )

    def test_every_pr769_identity_axis_changes_binding_digest(self) -> None:
        canonical = a.bind_g6_request_to_admission_identity(
            base_request=base_request(), reuse_identity=identity()
        )
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
                changed = a.bind_g6_request_to_admission_identity(
                    base_request=base_request(),
                    reuse_identity=replace(identity(), **{field: value}),
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
                a.bind_g6_request_to_admission_identity(
                    base_request=base_request(),
                    reuse_identity=replace(identity(), **{field: value}),
                )

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
                a.bind_g6_request_to_admission_identity(
                    base_request=base_request(),
                    reuse_identity=replace(identity(), **{field: True}),
                )

    def test_binding_receipt_cannot_self_mint_truth_authority_or_gate10(self) -> None:
        receipt = a.bind_g6_request_to_admission_identity(
            base_request=base_request(), reuse_identity=identity()
        )
        for field in (
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

    def test_base_flagship_source_identity_substitution_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "BASE_G6_FLAGSHIP_SOURCE_IDENTITY_MISMATCH"):
            a.bind_g6_request_to_admission_identity(
                base_request=replace(base_request(), source_set_digest="c" * 64),
                reuse_identity=identity(),
            )

    def test_deterministic(self) -> None:
        first = a.bind_g6_request_to_admission_identity(
            base_request=base_request(), reuse_identity=identity()
        )
        second = a.bind_g6_request_to_admission_identity(
            base_request=base_request(), reuse_identity=identity()
        )
        self.assertEqual(first, second)
        self.assertEqual(first.receipt_digest, second.receipt_digest)

    def test_identity_binding_lattice_exhausts_16_summary_states(self) -> None:
        self.assertEqual(a.prove_identity_binding_lattice(), 16)

    def test_laws(self) -> None:
        for law in (
            "ReuseCandidateSummary!=AdmissionReuseReceiptIdentity",
            "GLM53AdmissionFamilyMustRemainExact",
            "AdmissionReceiptDigest+Subject+Source+Evidence+Owner+Decision+ReuseDigestMustSurviveProjection",
            "IdentityBinding!=ReceiptProducerAuthentication",
            "RepoHeadChanged!=TensorSourceGenerationChanged",
            "CoordinateMemory!=MODEL_PREFIX_KV",
        ):
            self.assertIn(law, a.LAWS)


if __name__ == "__main__":
    unittest.main()
