from __future__ import annotations

import inspect
from pathlib import Path
import unittest
from unittest.mock import patch

import scripts.aura_workcapsule_stale_exact_observation_owner_reduction as module


class StaleExactObservationOwnerReductionTests(unittest.TestCase):
    def kwargs(self):
        return {
            "root": Path("."),
            "codemap": {},
            "anchor_manifest": {},
            "witness_manifest": {},
            "previous_binding": {"binding_identity": {"value": "previous"}},
            "reentry_receipt": {"receipt_identity": {"value": "reentry"}},
            "observed_graph_witness": {"graph_id": "observed"},
            "candidate_graph_witness": {"graph_id": "candidate"},
            "receipt": {
                "closure_status": "HOLD",
                "source_observation": {"receipt_identity": {"value": "observation"}},
                "receipt_identity": {"value": "closure"},
                "source_observation_identity": {"value": "observation"},
                "reentry_receipt_identity": {"value": "reentry"},
            },
        }

    @patch.object(module, "verify_stale_safe_exact_reentry", return_value=[])
    @patch.object(module, "verify_exact_observation_bound_reentry_closure", return_value=[])
    def test_general_owner_is_consumed_before_stale_leaf(self, general, stale):
        kwargs = self.kwargs()
        self.assertEqual([], module.verify_stale_exact_observation_owner_reduction(**kwargs))
        general.assert_called_once()
        stale.assert_called_once()
        self.assertIs(stale.call_args.kwargs["source_observation_receipt"], kwargs["receipt"]["source_observation"])

    @patch.object(module, "verify_stale_safe_exact_reentry")
    @patch.object(module, "verify_exact_observation_bound_reentry_closure", return_value=["FOREIGN_RECEIPT"])
    def test_general_exact_failure_short_circuits_stale_owner(self, general, stale):
        violations = module.verify_stale_exact_observation_owner_reduction(**self.kwargs())
        self.assertEqual(["GENERAL_EXACT_FOREIGN_RECEIPT"], violations)
        stale.assert_not_called()

    @patch.object(module, "verify_stale_safe_exact_reentry", return_value=["REJECTED_CURRENTNESS_REQUIRED"])
    @patch.object(module, "verify_exact_observation_bound_reentry_closure", return_value=[])
    def test_stale_leaf_failure_is_preserved(self, _general, _stale):
        violations = module.verify_stale_exact_observation_owner_reduction(**self.kwargs())
        self.assertIn("STALE_SAFE_REJECTED_CURRENTNESS_REQUIRED", violations)

    @patch.object(module, "verify_stale_safe_exact_reentry", return_value=[])
    @patch.object(module, "verify_exact_observation_bound_reentry_closure", return_value=[])
    def test_rejected_currentness_path_must_remain_hold(self, _general, _stale):
        kwargs = self.kwargs()
        kwargs["receipt"]["closure_status"] = "CLOSED"
        violations = module.verify_stale_exact_observation_owner_reduction(**kwargs)
        self.assertIn(module.REJECTED_CURRENTNESS_MUST_HOLD, violations)

    @patch.object(module, "admit_stale_safe_exact_reentry")
    @patch.object(module, "admit_exact_observation_bound_reentry_closure")
    @patch.object(module, "verify_stale_exact_observation_owner_reduction", return_value=[])
    def test_admission_preserves_owner_outputs_and_zero_authority(self, _verify, general, stale):
        general.return_value = {"exact_observation_bound_input_reproduction": True}
        stale.return_value = {
            "minimum_reentry_scope": "SELECTED_SOURCES",
            "minimum_reentry_source_keys": ["SOURCE:17:42"],
            "rejected_dependency_keys": ["SOURCE:17:42"],
            "reentry_required": True,
        }
        admitted = module.admit_stale_exact_observation_owner_reduction(**self.kwargs())
        self.assertTrue(admitted["general_raw_input_owner_consumed"])
        self.assertTrue(admitted["stale_safety_owner_consumed"])
        self.assertFalse(admitted["raw_replay_reimplemented_by_child"])
        self.assertTrue(admitted["exact_observation_bound_input_reproduction"])
        self.assertFalse(admitted["source_currentness_minted"])
        self.assertFalse(any(admitted["authority"].values()))

    def test_public_boundary_has_no_precompiled_projection_or_candidate_slots(self):
        params = inspect.signature(module.verify_stale_exact_observation_owner_reduction).parameters
        self.assertNotIn("source_observation_receipt", params)
        self.assertNotIn("observed_source_witnesses", params)
        self.assertNotIn("candidate_binding", params)
        self.assertIn("root", params)
        self.assertIn("receipt", params)

    def test_child_does_not_import_raw_replay_implementations(self):
        source = inspect.getsource(module)
        self.assertNotIn("compile_source_reentry_observations", source)
        self.assertNotIn("compile_observation_bound_reentry_closure", source)
        self.assertIn("verify_exact_observation_bound_reentry_closure", source)
        self.assertIn("verify_stale_safe_exact_reentry", source)


if __name__ == "__main__":
    unittest.main()
