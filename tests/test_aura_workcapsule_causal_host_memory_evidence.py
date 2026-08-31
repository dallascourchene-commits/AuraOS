from __future__ import annotations

import copy
import inspect
import unittest

from scripts.aura_workcapsule_causal_host_memory_evidence import (
    ARTIFACT_REF_SCHEME,
    EVIDENCE_TYPE,
    admit_causal_host_memory_evidence,
    causal_host_evidence_ref,
    verify_causal_host_memory_evidence,
)
from scripts.aura_workcapsule_live_causal_artifact_causal_host_envelope import (
    admit_live_causal_artifact_causal_host_envelope,
)
from tests.test_aura_provenance_corroboration_memory_admission import node
from tests.test_aura_workcapsule_live_causal_artifact_causal_host_envelope import (
    WorkCapsuleLiveCausalArtifactCausalHostEnvelopeTests,
)


class CausalHostMemoryEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = WorkCapsuleLiveCausalArtifactCausalHostEnvelopeTests(
            "test_exact_causal_envelope_binds_to_exact_live_artifact_and_world"
        )
        cls.case.setUp()
        cls.inputs = cls.case.o42_kwargs()
        cls.receipt = admit_live_causal_artifact_causal_host_envelope(**cls.inputs)
        cls.ref = causal_host_evidence_ref(cls.receipt)

    @classmethod
    def tearDownClass(cls):
        cls.case.tearDown()

    def context(self, accepted=None):
        return {
            "scope": "arena",
            "use_class": "retrieval",
            "accepted_evidence_types": accepted or [EVIDENCE_TYPE],
        }

    def evidence(self, *, ref=None, current=True, revoked=False, evidence_type=EVIDENCE_TYPE):
        ref = ref or self.ref
        return node(
            ref,
            evidence_type=evidence_type,
            claim_key="workcapsule:causal-host-observation",
            claim_value_ref="o42-receipt:" + ref.split(":", 1)[1],
            world_ref="workcapsule:o42:causal-host-world",
            dependency_class_ref="workcapsule:o42:raw-owner-chain",
            generation_ref="o42:69e7af0f7190f841d459890343b8a96f6961764a",
            current=current,
            revoked=revoked,
        )

    def test_exact_o42_host_evidence_can_be_remembered_without_authority(self):
        out = admit_causal_host_memory_evidence(
            o42_inputs=self.inputs,
            evidence_node=self.evidence(),
            context=self.context(),
        )
        self.assertTrue(out["o42_causal_host_evidence_reproved_at_admission"])
        self.assertTrue(out["pr581_memory_admission_owner_reused"])
        self.assertTrue(out["memory_evidence_eligible"])
        self.assertEqual(self.receipt["host_gate_states"], out["remembered_host_gate_states"])
        self.assertEqual(
            self.receipt["live_causal_artifact_target_ref"],
            out["remembered_live_causal_artifact_target_ref"],
        )
        self.assertFalse(out["memory_node_currentness_derived_from_o42"])
        self.assertFalse(out["memory_currentness_reproved_by_child"])
        self.assertFalse(out["host_state_currentness_reproved_after_memory_admission"])
        self.assertFalse(out["memory_admission_promotes_host_observation_authority"])
        self.assertFalse(out["causal_host_resolver_trust_proven"])
        self.assertFalse(out["causal_host_observation_authority_proven"])
        self.assertFalse(out["semantic_truth_proven"])
        self.assertFalse(out["host_effect_ready"])
        self.assertFalse(any(out["authority"].values()))

    def test_o42_cannot_promote_stale_memory_node_to_current(self):
        violations = verify_causal_host_memory_evidence(
            o42_inputs=self.inputs,
            evidence_node=self.evidence(current=False),
            context=self.context(),
        )
        self.assertIn("MEMORY_NOT_ELIGIBLE:NOT_CURRENT", violations)

    def test_o42_cannot_promote_revoked_memory_node(self):
        violations = verify_causal_host_memory_evidence(
            o42_inputs=self.inputs,
            evidence_node=self.evidence(revoked=True),
            context=self.context(),
        )
        self.assertIn("MEMORY_NOT_ELIGIBLE:REVOKED", violations)

    def test_internally_valid_foreign_memory_ref_rejects_at_relation_layer(self):
        foreign = f"{ARTIFACT_REF_SCHEME}:" + "0" * 64
        violations = verify_causal_host_memory_evidence(
            o42_inputs=self.inputs,
            evidence_node=self.evidence(ref=foreign),
            context=self.context(),
        )
        self.assertIn("O42_MEMORY_ARTIFACT_REF_MISMATCH", violations)
        self.assertIn("O42_MEMORY_REF_VALUE_MISMATCH", violations)

    def test_context_type_gate_remains_hard_after_exact_o42_reproof(self):
        violations = verify_causal_host_memory_evidence(
            o42_inputs=self.inputs,
            evidence_node=self.evidence(),
            context=self.context(accepted=["other-evidence"]),
        )
        self.assertIn("MEMORY_NOT_ELIGIBLE:EVIDENCE_TYPE_NOT_ACCEPTED", violations)

    def test_host_state_change_changes_memory_evidence_identity_not_live_artifact_target(self):
        complete_inputs = self.case.o42_kwargs(
            host=self.case.causal_host_receipt(all_pass=True)
        )
        complete = admit_live_causal_artifact_causal_host_envelope(**complete_inputs)
        self.assertNotEqual(self.receipt["host_gate_states"], complete["host_gate_states"])
        self.assertEqual(
            self.receipt["live_causal_artifact_target_ref"],
            complete["live_causal_artifact_target_ref"],
        )
        self.assertNotEqual(causal_host_evidence_ref(self.receipt), causal_host_evidence_ref(complete))
        violations = verify_causal_host_memory_evidence(
            o42_inputs=complete_inputs,
            evidence_node=self.evidence(),
            context=self.context(),
        )
        self.assertIn("O42_MEMORY_ARTIFACT_REF_MISMATCH", violations)

    def test_all_pass_o42_evidence_remains_nonauthorizing_after_memory_admission(self):
        complete_inputs = self.case.o42_kwargs(
            host=self.case.causal_host_receipt(all_pass=True)
        )
        complete = admit_live_causal_artifact_causal_host_envelope(**complete_inputs)
        ref = causal_host_evidence_ref(complete)
        evidence = node(
            ref,
            evidence_type=EVIDENCE_TYPE,
            claim_key="workcapsule:causal-host-observation",
            claim_value_ref="o42-receipt:" + ref.split(":", 1)[1],
            world_ref="workcapsule:o42:causal-host-world",
            dependency_class_ref="workcapsule:o42:raw-owner-chain",
            generation_ref="o42:69e7af0f7190f841d459890343b8a96f6961764a",
        )
        out = admit_causal_host_memory_evidence(
            o42_inputs=complete_inputs,
            evidence_node=evidence,
            context=self.context(),
        )
        self.assertEqual({"PASS"}, set(out["remembered_host_gate_states"].values()))
        self.assertFalse(out["causal_host_observation_authority_proven"])
        self.assertFalse(out["trusted_continuation_ready"])
        self.assertFalse(out["host_effect_ready"])
        self.assertFalse(out["effect_authority_proven"])

    def test_public_boundary_has_no_memory_currentness_resolver_or_authority_override(self):
        params = set(inspect.signature(verify_causal_host_memory_evidence).parameters)
        self.assertEqual({"o42_inputs", "evidence_node", "context"}, params)
        forbidden = {
            "memory_current",
            "host_state_current",
            "host_observation_resolver",
            "producer_authenticated",
            "semantic_truth",
            "trusted_continuation_ready",
            "host_effect_ready",
            "execution_authorized",
            "k27_coordinate",
        }
        self.assertTrue(params.isdisjoint(forbidden))

    def test_output_is_deterministic(self):
        kwargs = {
            "o42_inputs": self.inputs,
            "evidence_node": self.evidence(),
            "context": self.context(),
        }
        first = admit_causal_host_memory_evidence(**kwargs)
        second = admit_causal_host_memory_evidence(**kwargs)
        self.assertEqual(first, second)
        self.assertEqual(64, len(first["receipt_identity"]["value"]))


if __name__ == "__main__":
    unittest.main()
