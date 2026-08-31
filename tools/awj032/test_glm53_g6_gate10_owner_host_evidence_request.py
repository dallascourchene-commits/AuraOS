from __future__ import annotations

from dataclasses import replace
import unittest

import tools.awj032.glm53_g6_gate10_owner_host_evidence_request as m


D0 = "0" * 64
D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64
D4 = "4" * 64


def q18() -> m.Q18ProposalProjection:
    return m.Q18ProposalProjection(
        semantic_head=m.Q18_SEMANTIC_HEAD,
        proof_only_head=m.Q18_PROOF_ONLY_HEAD,
        proof_run=m.Q18_PROOF_RUN,
        proof_job=m.Q18_PROOF_JOB,
        receipt_digest=m.Q18_RECEIPT_DIGEST,
        disposition=m.Q18_ELIGIBLE,
        official_repository=m.OFFICIAL_REPOSITORY,
        official_revision=m.Q18_PINNED_OFFICIAL_REVISION,
        source_set_digest=m.Q18_SOURCE_SET_DIGEST,
        bounded_proposal_eligible=True,
    )


def g5() -> m.G5ContractProjection:
    return m.G5ContractProjection(
        semantic_proof_head=m.G5_SEMANTIC_PROOF_HEAD,
        proof_run=m.G5_PROOF_RUN,
        proof_job=m.G5_PROOF_JOB,
        source_blob=m.G5_SOURCE_BLOB,
        test_blob=m.G5_TEST_BLOB,
        schema=m.G5_CONTRACT_SCHEMA,
        terminal_green=True,
        require_current_transfer_plan_at_execution=True,
        require_independent_progress_on_recompute=True,
        require_future_read_currentness_on_source_change=True,
    )


def owner() -> m.OwnerHostTargetProjection:
    return m.OwnerHostTargetProjection(
        owner_host_ref="owner-host:local:glm53-c2",
        principal_generation="principal:g1",
        host_profile_generation="host:g1",
        runtime_generation="runtime:g1",
        cache_generation="cache:g1",
        storage_geometry_generation="storage:g1",
        resource_envelope_digest=D0,
        evidence_sink_ref="artifact:awj032:g6:owner-host-evidence",
    )


def evidence() -> m.EvidenceContractProjection:
    return m.EvidenceContractProjection(
        request_manifest_digest=D1,
        benchmark_harness_digest=D2,
        replay_contract_digest=D3,
        recovery_contract_digest=D4,
        required_evidence_axes=m.REQUIRED_EVIDENCE_AXES,
        open_gate10_debt=m.OPEN_GATE10_DEBT,
        official_revision_revalidation_required=True,
    )


class G6Gate10OwnerHostEvidenceRequestTests(unittest.TestCase):
    def test_exact_inputs_compile_only_nonexecuting_request_envelope(self) -> None:
        r = m.compile_gate10_owner_host_evidence_request(
            q18=q18(), g5=g5(), owner=owner(), evidence=evidence()
        )
        self.assertEqual(r.disposition, m.COMPILED)
        self.assertTrue(r.request_envelope_compiled)
        self.assertTrue(r.official_revision_revalidation_required)
        self.assertFalse(r.tensor_payload_bound)
        self.assertFalse(r.real_tensor_quantization_observed)
        self.assertFalse(r.owner_host_execution_observed)
        self.assertFalse(r.full_flagship_model_loaded)
        self.assertFalse(r.physical_io_proven)
        self.assertFalse(r.auraos_resident_routing_proven)
        self.assertFalse(r.replay_recovery_proven)
        self.assertFalse(r.execution_authorized)
        self.assertFalse(r.gate10_promoted)

    def test_q18_must_be_current_generation_eligible(self) -> None:
        r = m.compile_gate10_owner_host_evidence_request(
            q18=replace(q18(), disposition="HOLD", bounded_proposal_eligible=False),
            g5=g5(), owner=owner(), evidence=evidence(),
        )
        self.assertEqual(r.disposition, m.HOLD_Q18)
        self.assertFalse(r.request_envelope_compiled)

    def test_g5_terminal_contract_and_all_three_runtime_laws_are_required(self) -> None:
        for mutated in (
            replace(g5(), terminal_green=False),
            replace(g5(), require_current_transfer_plan_at_execution=False),
            replace(g5(), require_independent_progress_on_recompute=False),
            replace(g5(), require_future_read_currentness_on_source_change=False),
        ):
            with self.subTest(mutated=mutated):
                r = m.compile_gate10_owner_host_evidence_request(
                    q18=q18(), g5=mutated, owner=owner(), evidence=evidence()
                )
                self.assertEqual(r.disposition, m.HOLD_G5)

    def test_q18_parent_cannot_launder_tensor_binding_or_execution(self) -> None:
        for field in ("tensor_payload_bound", "execution_authorized", "gate10_promoted"):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    m.compile_gate10_owner_host_evidence_request(
                        q18=replace(q18(), **{field: True}),
                        g5=g5(), owner=owner(), evidence=evidence(),
                    )

    def test_g5_parent_cannot_launder_execution_or_gate10(self) -> None:
        for field in ("execution_authorized", "gate10_promoted"):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    m.compile_gate10_owner_host_evidence_request(
                        q18=q18(), g5=replace(g5(), **{field: True}),
                        owner=owner(), evidence=evidence(),
                    )

    def test_owner_projection_is_targeting_not_authentication_or_authority(self) -> None:
        for field in ("owner_authenticated_by_this_contract", "execution_authorized_by_this_contract"):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    m.compile_gate10_owner_host_evidence_request(
                        q18=q18(), g5=g5(), owner=replace(owner(), **{field: True}), evidence=evidence()
                    )

    def test_evidence_contract_carries_exact_required_axes_and_gate10_debt(self) -> None:
        with self.assertRaises(ValueError):
            m.compile_gate10_owner_host_evidence_request(
                q18=q18(), g5=g5(), owner=owner(),
                evidence=replace(evidence(), required_evidence_axes=m.REQUIRED_EVIDENCE_AXES[:-1]),
            )
        with self.assertRaises(ValueError):
            m.compile_gate10_owner_host_evidence_request(
                q18=q18(), g5=g5(), owner=owner(),
                evidence=replace(evidence(), open_gate10_debt=m.OPEN_GATE10_DEBT[:-1]),
            )
        with self.assertRaises(ValueError):
            m.compile_gate10_owner_host_evidence_request(
                q18=q18(), g5=g5(), owner=owner(),
                evidence=replace(evidence(), official_revision_revalidation_required=False),
            )

    def test_evidence_request_cannot_claim_observations_that_have_not_happened(self) -> None:
        for field in (
            "actual_owner_host_evidence_already_observed",
            "full_flagship_execution_already_proven",
            "auraos_resident_routing_already_proven",
            "replay_recovery_already_proven",
            "gate10_promoted",
        ):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    m.compile_gate10_owner_host_evidence_request(
                        q18=q18(), g5=g5(), owner=owner(),
                        evidence=replace(evidence(), **{field: True}),
                    )

    def test_proof_coordinates_and_blob_substitutions_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            m.compile_gate10_owner_host_evidence_request(
                q18=replace(q18(), proof_job=m.Q18_PROOF_JOB + 1),
                g5=g5(), owner=owner(), evidence=evidence(),
            )
        with self.assertRaises(ValueError):
            m.compile_gate10_owner_host_evidence_request(
                q18=q18(), g5=replace(g5(), source_blob="f" * 40),
                owner=owner(), evidence=evidence(),
            )

    def test_request_digest_is_deterministic_and_generation_sensitive(self) -> None:
        a = m.compile_gate10_owner_host_evidence_request(q18=q18(), g5=g5(), owner=owner(), evidence=evidence())
        b = m.compile_gate10_owner_host_evidence_request(q18=q18(), g5=g5(), owner=owner(), evidence=evidence())
        self.assertEqual(a, b)
        self.assertEqual(a.request_digest, b.request_digest)
        c = m.compile_gate10_owner_host_evidence_request(
            q18=q18(), g5=g5(), owner=replace(owner(), runtime_generation="runtime:g2"), evidence=evidence()
        )
        self.assertNotEqual(a.request_digest, c.request_digest)

    def test_different_j_exhausts_complete_512_state_precondition_lattice(self) -> None:
        self.assertEqual(m.prove_different_j(), 512)

    def test_laws_preserve_coordinate_and_gate10_boundaries(self) -> None:
        self.assertIn("CoordinateMemory!=MODEL_PREFIX_KV", m.LAWS)
        self.assertIn("Gate10DebtMustRemainExplicitUntilObserved", m.LAWS)
        self.assertIn("FullFlagshipIdentity!=FullFlagshipExecution", m.LAWS)


if __name__ == "__main__":
    unittest.main()
