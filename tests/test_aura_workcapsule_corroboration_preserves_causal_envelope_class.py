from __future__ import annotations

import copy
import inspect
import unittest

from scripts import aura_workcapsule_corroboration_preserves_causal_envelope_class as target
from scripts.aura_workcapsule_causal_artifact_qualified_host_envelope import (
    verify_causal_host_admission_envelope,
)
from tests.test_aura_workcapsule_causal_envelope_raw_slice_noninterchangeability import (
    pr573_receipt,
    pr574_receipt,
)
from tests.test_aura_workcapsule_live_causal_corroboration import (
    pr568_receipt,
    pr572_receipt,
)


class CorroborationPreservesCausalEnvelopeClassTests(unittest.TestCase):
    def kwargs(self):
        return {
            "causal_artifact_host_receipt": pr573_receipt(),
            "causal_raw_slice_host_separation_receipt": pr574_receipt(),
            "pr568_receipt": pr568_receipt(),
            "pr572_receipt": pr572_receipt(),
        }

    def test_exact_parent_relations_preserve_causal_envelope_class(self) -> None:
        kwargs = self.kwargs()
        self.assertEqual([], target.verify_corroboration_preserves_causal_envelope_class(**kwargs))
        out = target.admit_corroboration_preserves_causal_envelope_class(**kwargs)
        self.assertTrue(out["pr583_noninterchangeability_owner_reproved"])
        self.assertTrue(out["pr577_corroboration_owner_reproved"])
        self.assertTrue(out["proof_artifact_refs_distinct"])
        self.assertFalse(out["pr568_proof_is_causal_host_envelope"])
        self.assertFalse(out["pr572_proof_is_causal_host_envelope"])
        self.assertFalse(out["corroboration_converts_proof_to_causal_host_envelope"])
        self.assertFalse(out["causal_raw_slice_promoted_to_host_rank"])
        self.assertFalse(out["proof_artifacts_interchangeable"])
        self.assertFalse(out["producer_authenticated"])
        self.assertFalse(out["semantic_truth_proven"])
        self.assertFalse(out["host_observation_authority_proven"])
        self.assertFalse(out["effect_authority_proven"])
        self.assertFalse(any(out["authority"].values()))

    def test_each_corroborating_proof_object_is_not_causal_host_envelope(self) -> None:
        self.assertEqual(
            [target.MALFORMED], verify_causal_host_admission_envelope(pr568_receipt())
        )
        self.assertEqual(
            [target.MALFORMED], verify_causal_host_admission_envelope(pr572_receipt())
        )

    def test_pr577_world_drift_fails_before_type_preservation_credit(self) -> None:
        kwargs = self.kwargs()
        kwargs["pr572_receipt"] = pr572_receipt(source_generation=44)
        violations = target.verify_corroboration_preserves_causal_envelope_class(**kwargs)
        self.assertIn("PR577_LIVE_SOURCE_INSTANCE_MISMATCH", violations)

    def test_pr583_parent_ceiling_widening_fails_before_composition(self) -> None:
        kwargs = self.kwargs()
        kwargs["causal_raw_slice_host_separation_receipt"] = pr574_receipt(
            raw_slice_used_as_host_resolution=True
        )
        violations = target.verify_corroboration_preserves_causal_envelope_class(**kwargs)
        self.assertIn(
            "PR583_PR574_CEILING_VIOLATED:raw_slice_used_as_host_resolution",
            violations,
        )

    def test_pr577_authority_widening_fails_before_composition(self) -> None:
        kwargs = self.kwargs()
        widened = pr568_receipt()
        widened["authority"]["execution_authorized"] = True
        kwargs["pr568_receipt"] = widened
        violations = target.verify_corroboration_preserves_causal_envelope_class(**kwargs)
        self.assertIn("PR577_PR568_AUTHORITY_WIDENED", violations)

    def test_public_boundary_is_exactly_four_closed_parent_receipts(self) -> None:
        params = set(
            inspect.signature(
                target.verify_corroboration_preserves_causal_envelope_class
            ).parameters
        )
        self.assertEqual(
            {
                "causal_artifact_host_receipt",
                "causal_raw_slice_host_separation_receipt",
                "pr568_receipt",
                "pr572_receipt",
            },
            params,
        )
        for forbidden in (
            "resolver",
            "host_rank",
            "evidence_class_override",
            "corroboration_override",
            "producer_authenticated",
            "semantic_truth",
            "effect_authority",
        ):
            self.assertNotIn(forbidden, params)

    def test_admission_is_deterministic(self) -> None:
        kwargs = self.kwargs()
        first = target.admit_corroboration_preserves_causal_envelope_class(
            **copy.deepcopy(kwargs)
        )
        second = target.admit_corroboration_preserves_causal_envelope_class(
            **copy.deepcopy(kwargs)
        )
        self.assertEqual(first, second)
        self.assertEqual(64, len(first["receipt_identity"]["value"]))


if __name__ == "__main__":
    unittest.main()
