from __future__ import annotations

from dataclasses import replace
from itertools import product
import unittest

from workload_contamination_gate import *


class GateTests(unittest.TestCase):
    def setUp(self):
        self.gate = WorkloadContaminationGate()
        self.batch = valid_batch()

    def test_valid_batch_ready_nonauthorizing(self):
        r = self.gate.assess(self.batch)
        self.assertEqual(r.decision, Decision.READY_NONAUTHORIZING)
        self.assertTrue(r.policy_ranking_eligible)
        self.assertFalse(r.truth_authority or r.effect_authority or r.gate10)

    def test_cross_category_exact_prefix_collision_holds(self):
        items = list(self.batch.samples)
        items[2] = replace(items[2], rendered_generation_prefix=items[0].rendered_generation_prefix)
        r = self.gate.assess(replace(self.batch, samples=tuple(items)))
        self.assertEqual(r.decision, Decision.HOLD_PREFIX_CONTAMINATION)
        self.assertFalse(r.policy_ranking_eligible)
        self.assertEqual(r.prefix_collisions[0].categories, ("code", "reasoning"))

    def test_within_category_prefix_repeat_does_not_fake_cross_category_collision(self):
        items = list(self.batch.samples)
        items[1] = replace(items[1], rendered_generation_prefix=items[0].rendered_generation_prefix)
        r = self.gate.assess(replace(self.batch, samples=tuple(items)))
        self.assertEqual(r.decision, Decision.READY_NONAUTHORIZING)

    def test_nonranking_control_may_share_cross_category_prefix(self):
        control = sample(9, "code", self.batch.samples[0].rendered_generation_prefix,
                         ranking_eligible=False, control_group="prefix-sharing-diagnostic")
        r = self.gate.assess(replace(self.batch, samples=self.batch.samples + (control,)))
        self.assertEqual(r.decision, Decision.READY_NONAUTHORIZING)
        self.assertEqual(r.control_sample_count, 1)

    def test_promoting_control_into_ranking_reopens_contamination(self):
        control = sample(9, "code", self.batch.samples[0].rendered_generation_prefix,
                         ranking_eligible=False, control_group="prefix-sharing-diagnostic")
        contaminated = replace(control, ranking_eligible=True)
        r = self.gate.assess(replace(self.batch, samples=self.batch.samples + (contaminated,)))
        self.assertEqual(r.decision, Decision.HOLD_PREFIX_CONTAMINATION)

    def test_nonranking_sample_requires_control_group(self):
        bad = sample(9, "control", "x", ranking_eligible=False, control_group="g")
        bad = replace(bad, control_group=None)
        with self.assertRaisesRegex(WorkloadGateError, "NONRANKING_SAMPLE_REQUIRES_CONTROL_GROUP"):
            self.gate.assess(replace(self.batch, samples=self.batch.samples + (bad,)))

    def test_trace_invalid_precedes_contamination(self):
        items = list(self.batch.samples)
        items[0] = replace(items[0], trace=replace(items[0].trace, atomic_semantics_preserved=False))
        items[2] = replace(items[2], rendered_generation_prefix=items[0].rendered_generation_prefix)
        r = self.gate.assess(replace(self.batch, samples=tuple(items)))
        self.assertEqual(r.decision, Decision.HOLD_TRACE_INVALID)

    def test_envelope_mismatch_holds(self):
        items = list(self.batch.samples)
        items[0] = replace(items[0], trace=replace(items[0].trace, envelope_root="other"))
        r = self.gate.assess(replace(self.batch, samples=tuple(items)))
        self.assertEqual(r.decision, Decision.HOLD_ENVELOPE_MISMATCH)

    def test_source_generation_mismatch_holds(self):
        items = list(self.batch.samples)
        items[0] = replace(items[0], source_generation="stale-gen")
        r = self.gate.assess(replace(self.batch, samples=tuple(items)))
        self.assertEqual(r.decision, Decision.HOLD_SOURCE_GENERATION_MISMATCH)

    def test_stale_source_holds(self):
        self.assertEqual(self.gate.assess(replace(self.batch, source_current=False)).decision,
                         Decision.HOLD_STALE_SOURCE)

    def test_single_ranking_category_holds(self):
        one = tuple(s for s in self.batch.samples if s.category == "code")
        self.assertEqual(self.gate.assess(replace(self.batch, samples=one)).decision,
                         Decision.HOLD_INSUFFICIENT_RANKING_CLASSES)

    def test_effect_authority_never_minted(self):
        r = self.gate.assess(replace(self.batch, asks_effect_authority=True))
        self.assertEqual(r.decision, Decision.HOLD_AUTHORITY_CEILING)
        self.assertFalse(r.effect_authority or r.gate10)

    def test_duplicate_sample_id_rejected(self):
        dup = replace(self.batch.samples[1], sample_id=self.batch.samples[0].sample_id)
        with self.assertRaisesRegex(WorkloadGateError, "DUPLICATE_SAMPLE_ID"):
            self.gate.assess(replace(self.batch, samples=(self.batch.samples[0], dup)))

    def test_empty_prefix_rejected(self):
        bad = replace(self.batch.samples[0], rendered_generation_prefix="")
        with self.assertRaisesRegex(WorkloadGateError, "INVALID_RENDERED_GENERATION_PREFIX"):
            self.gate.assess(replace(self.batch, samples=(bad,) + self.batch.samples[1:]))

    def test_prefix_root_ignores_labels_so_relabeling_cannot_hide_identity(self):
        a = self.batch.samples[0]
        b = replace(a, sample_id="x", category="different", template_id="other-template")
        self.assertEqual(a.prefix_root, b.prefix_root)

    def test_receipt_root_deterministic(self):
        self.assertEqual(self.gate.assess(self.batch).receipt_root, self.gate.assess(self.batch).receipt_root)

    def test_batch_root_changes_on_prefix_mutation(self):
        clean = self.gate.assess(self.batch)
        items = list(self.batch.samples)
        items[0] = replace(items[0], rendered_generation_prefix="changed")
        changed = self.gate.assess(replace(self.batch, samples=tuple(items)))
        self.assertNotEqual(clean.batch_root, changed.batch_root)

    def test_template_change_alone_does_not_change_prefix_identity(self):
        a = self.batch.samples[0]
        b = replace(a, template_id="new-template-name")
        self.assertEqual(a.prefix_root, b.prefix_root)

    def test_trace_root_is_preserved_in_batch_identity(self):
        clean = self.gate.assess(self.batch)
        items = list(self.batch.samples)
        items[0] = replace(items[0], trace=replace(items[0].trace, trace_root="other-trace"))
        changed = self.gate.assess(replace(self.batch, samples=tuple(items)))
        self.assertNotEqual(clean.batch_root, changed.batch_root)

    def test_source_generation_is_preserved_in_batch_identity(self):
        clean = self.gate.assess(self.batch)
        changed = self.gate.assess(replace(self.batch, source_generation="src-g2", samples=tuple(
            replace(s, source_generation="src-g2") for s in self.batch.samples
        )))
        self.assertNotEqual(clean.batch_root, changed.batch_root)

    def test_omega8_exact_keeper(self):
        keepers = [state for state in product((0, 1, 2), repeat=8) if crystalline_admission(state)]
        self.assertEqual(keepers, [(2, 2, 2, 2, 2, 2, 2, 1)])

    def test_omega8_invalid_shape_rejected(self):
        with self.assertRaises(WorkloadGateError):
            crystalline_admission((2,) * 7)

    def test_hard_failure_not_repaired_by_unrelated_context(self):
        items = list(self.batch.samples)
        items[2] = replace(items[2], rendered_generation_prefix=items[0].rendered_generation_prefix)
        failing = replace(self.batch, samples=tuple(items))
        for tail in product((0, 1, 2), repeat=5):
            self.assertEqual(self.gate.assess(failing).decision, Decision.HOLD_PREFIX_CONTAMINATION, tail)


if __name__ == "__main__":
    unittest.main()
