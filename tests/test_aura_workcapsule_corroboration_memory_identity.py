from __future__ import annotations

import copy
import inspect
import unittest

from scripts import aura_workcapsule_corroboration_memory_identity as target
from tests.test_aura_workcapsule_corroboration_preserves_evidence_classes import exact_inputs
from tests.test_aura_workcapsule_live_causal_corroboration import pr572_receipt


class WorkCapsuleCorroborationMemoryIdentityTests(unittest.TestCase):
    def kwargs(self):
        live, raw, a, b = exact_inputs()
        return {
            "live_artifact_host_receipt": live,
            "causal_raw_slice_host_separation_receipt": raw,
            "pr568_receipt": a,
            "pr572_receipt": b,
        }

    def test_exact_corroborating_proofs_remain_two_memory_nodes(self):
        out = target.admit_corroboration_memory_identity(**self.kwargs())
        a = out["pr568_memory_node"]
        b = out["pr572_memory_node"]
        self.assertTrue(out["two_proof_artifacts_preserved"])
        self.assertNotEqual(a["artifact_ref"], b["artifact_ref"])
        self.assertEqual(target.PROOF_TYPE, a["evidence_type"])
        self.assertEqual(target.PROOF_TYPE, b["evidence_type"])
        self.assertEqual(target.CURRENTNESS_DOMAIN, a["currentness_domain"])
        self.assertEqual(target.CURRENTNESS_DOMAIN, b["currentness_domain"])
        self.assertNotEqual(a["dependency_class_ref"], b["dependency_class_ref"])
        self.assertFalse(out["artifact_identity_collapse_performed"])
        self.assertFalse(out["evidence_class_conversion_performed"])

    def test_memory_contains_one_rank_neutral_corroboration_edge_with_kappa_two(self):
        out = target.admit_corroboration_memory_identity(**self.kwargs())
        admission = out["memory_admission"]
        edges = [r for r in admission["relations"] if r["kind"] == "CORROBORATES"]
        self.assertEqual(1, len(edges))
        self.assertTrue(edges[0]["dependency_distinct"])
        self.assertFalse(edges[0]["proof_artifacts_interchangeable"])
        self.assertFalse(edges[0]["rank_transition_credit"])
        self.assertEqual(2, admission["corroboration_groups"][0]["kappa"])
        self.assertEqual(2, out["dependency_distinct_kappa"])
        self.assertFalse(out["corroboration_rank_transition_performed"])

    def test_memory_owner_preserves_currentness_and_authority_ceiling(self):
        out = target.admit_corroboration_memory_identity(**self.kwargs())
        admission = out["memory_admission"]
        self.assertTrue(admission["typed_currentness_domains_preserved"])
        self.assertTrue(admission["current_true_is_domain_scoped"])
        self.assertFalse(admission["currentness_domain_cross_cast_performed"])
        self.assertFalse(admission["corroboration_rank_transition_performed"])
        self.assertFalse(admission["input_currentness_reproved_by_this_module"])
        self.assertFalse(admission["semantic_truth_proven"])
        self.assertFalse(admission["producer_authentication_proven"])
        self.assertFalse(admission["effect_authority_proven"])
        self.assertFalse(out["ambient_currentness_reproved"])
        self.assertFalse(out["producer_authenticated"])
        self.assertFalse(out["semantic_truth_proven"])
        self.assertFalse(out["host_observation_authority_proven"])
        self.assertFalse(out["effect_authority_proven"])

    def test_pr587_world_drift_fails_before_memory_admission(self):
        kwargs = self.kwargs()
        kwargs["pr572_receipt"] = pr572_receipt(source_generation=44)
        with self.assertRaisesRegex(ValueError, "CORROBORATION_LIVE_SOURCE_INSTANCE_MISMATCH"):
            target.admit_corroboration_memory_identity(**kwargs)

    def test_parent_authority_widening_fails_before_memory_admission(self):
        kwargs = self.kwargs()
        kwargs["live_artifact_host_receipt"]["authority"]["execution_authorized"] = True
        with self.assertRaises(ValueError):
            target.admit_corroboration_memory_identity(**kwargs)

    def test_memory_refs_are_exact_pr587_proof_refs(self):
        kwargs = self.kwargs()
        from scripts.aura_workcapsule_corroboration_preserves_evidence_classes import (
            admit_corroboration_preserves_evidence_classes,
        )
        relation = admit_corroboration_preserves_evidence_classes(**copy.deepcopy(kwargs))
        out = target.admit_corroboration_memory_identity(**copy.deepcopy(kwargs))
        self.assertEqual(relation["pr568_proof_artifact_ref"], out["pr568_memory_node"]["artifact_ref"])
        self.assertEqual(relation["pr572_proof_artifact_ref"], out["pr572_memory_node"]["artifact_ref"])
        self.assertNotEqual(out["pr568_memory_node"]["artifact_ref"], out["pr572_memory_node"]["artifact_ref"])

    def test_public_boundary_has_no_memory_identity_or_rank_overrides(self):
        params = set(inspect.signature(target.admit_corroboration_memory_identity).parameters)
        self.assertEqual(
            {
                "live_artifact_host_receipt",
                "causal_raw_slice_host_separation_receipt",
                "pr568_receipt",
                "pr572_receipt",
            },
            params,
        )
        for forbidden in (
            "artifact_ref", "evidence_type", "currentness_domain", "dependency_class_ref",
            "context", "kappa", "rank_transition_credit", "host_resolver", "authority",
        ):
            self.assertNotIn(forbidden, params)

    def test_admission_is_deterministic(self):
        kwargs = self.kwargs()
        first = target.admit_corroboration_memory_identity(**copy.deepcopy(kwargs))
        second = target.admit_corroboration_memory_identity(**copy.deepcopy(kwargs))
        self.assertEqual(first, second)
        self.assertEqual(64, len(first["receipt_identity"]["value"]))


if __name__ == "__main__":
    unittest.main()
