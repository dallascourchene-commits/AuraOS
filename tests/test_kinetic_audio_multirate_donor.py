from __future__ import annotations

import unittest

from tools.arena.kinetic_audio_multirate_donor import (
    GestureIntentCompiler,
    GestureObservation,
    K27ConstraintProjector,
    K27Coordinate,
    KineticAudioMembrane,
    KineticAudioOwner,
    ProjectedMusicalIntent,
    RawGestureIntent,
    digest,
    replay_root,
    synthetic_callback_benchmark,
)

RECIPE = digest("recipe-v1")
ENGINE = digest("engine-v1")


def owner(**kw):
    params = dict(
        recipe_root=RECIPE,
        engine_root=ENGINE,
        sample_rate=8_000,
        block_size=64,
        bpm_milli=120_000,
        beats_per_bar=1,
        bars_per_phrase=1,
        queue_capacity=16,
        lookahead_blocks=2,
        smoothing_ms=20,
    )
    params.update(kw)
    return KineticAudioOwner(**params)


def intent(o: KineticAudioOwner, kind: str, controls, gesture="test", coord=K27Coordinate(1, 1, 1)):
    snap = o.snapshot()
    return ProjectedMusicalIntent(
        kind, tuple(sorted(controls)), coord, gesture, digest([kind, controls, gesture]),
        snap.graph_generation, snap.mutation_epoch, snap.timeline_epoch, snap.projection_root,
    )


class KineticAudioMultirateTests(unittest.TestCase):
    def test_confidence_hysteresis_emits_once_until_release(self):
        c = GestureIntentCompiler(activation_milli=750, release_milli=550, hold_frames=2)
        coord = K27Coordinate(1, 1, 1)
        self.assertIsNone(c.observe(GestureObservation(0, "open", 800, 500, coord)))
        self.assertIsNotNone(c.observe(GestureObservation(1, "open", 800, 500, coord)))
        self.assertIsNone(c.observe(GestureObservation(2, "open", 900, 500, coord)))
        self.assertIsNone(c.observe(GestureObservation(3, "open", 500, 500, coord)))
        self.assertIsNone(c.observe(GestureObservation(4, "open", 800, 500, coord)))
        self.assertIsNotNone(c.observe(GestureObservation(5, "open", 800, 500, coord)))

    def test_soft_control_is_block_aligned_and_smoothed(self):
        o = owner()
        r = o.schedule(intent(o, "soft", (("brightness_milli", 750),)))
        self.assertTrue(r.admitted)
        self.assertEqual(r.target_sample, 128)
        receipts = o.process_until(192)
        applied = [a for b in receipts for a in b.applied]
        self.assertEqual(len(applied), 1)
        self.assertGreaterEqual(applied[0].ramp_frames, o.block_size)
        self.assertEqual(dict(o.snapshot().soft_controls)["brightness_milli"], 750)

    def test_hard_transition_uses_audio_owned_phrase_boundary(self):
        o = owner()
        r = o.schedule(intent(o, "hard", (("bpm_milli", 124_000),), gesture="swipe_up"))
        self.assertTrue(r.admitted)
        self.assertEqual(r.target_sample, 4_000)
        self.assertEqual(r.target_sample % o.block_size, 32)
        receipts = o.process_until(4_064)
        applied = [a for b in receipts for a in b.applied]
        self.assertEqual(len(applied), 1)
        self.assertEqual(o.snapshot().bpm_milli, 124_000)

    def test_identical_graph_write_advances_epoch_not_generation(self):
        o = owner()
        s0 = o.snapshot()
        wr = o.governed_graph_write(recipe_root=RECIPE, engine_root=ENGINE)
        s1 = wr.snapshot
        self.assertFalse(wr.changed)
        self.assertEqual(s1.graph_generation, s0.graph_generation)
        self.assertEqual(s1.graph_root, s0.graph_root)
        self.assertEqual(s1.mutation_epoch, s0.mutation_epoch + 1)

    def test_projection_to_schedule_toctou_fails_closed(self):
        o = owner()
        p = K27ConstraintProjector()
        snap = o.snapshot()
        raw = RawGestureIntent.build(GestureObservation(0, "swipe_up", 900, 800, K27Coordinate(2, 1, 1)))
        projected = p.project(raw, snap)
        o.governed_graph_write(recipe_root=RECIPE)
        r = o.schedule(projected)
        self.assertFalse(r.admitted)
        self.assertEqual(r.reason, "HOLD_STALE_PROJECTION")
        self.assertEqual(o.queue_depth, 0)

    def test_graph_epoch_mutation_invalidates_scheduled_permit(self):
        o = owner()
        r = o.schedule(intent(o, "soft", (("density_milli", 800),)))
        self.assertTrue(r.admitted)
        wr = o.governed_graph_write(recipe_root=RECIPE)
        self.assertEqual(wr.invalidated_events, (r.event_id,))
        self.assertEqual(o.queue_depth, 0)
        receipts = o.process_until(r.target_sample + o.block_size)
        applied = [a for b in receipts for a in b.applied]
        self.assertEqual(applied, [])

    def test_hard_transition_invalidates_other_old_timeline_permits(self):
        o = owner()
        a = o.schedule(intent(o, "hard", (("drop_state", 1),), gesture="fist"))
        b = o.schedule(intent(o, "hard", (("scale_index", 7),), gesture="rotate"))
        self.assertTrue(a.admitted and b.admitted)
        self.assertEqual(a.target_sample, b.target_sample)
        receipts = o.process_until(a.target_sample + o.block_size)
        applied = [x for br in receipts for x in br.applied]
        stale = [x for br in receipts for x in br.held_stale]
        self.assertEqual(len(applied), 1)
        self.assertEqual(len(stale), 1)
        self.assertEqual({applied[0].event_id, stale[0]}, {a.event_id, b.event_id})
        self.assertEqual(o.snapshot().timeline_epoch, 2)

    def test_queue_capacity_fails_closed(self):
        o = owner(queue_capacity=1)
        a = o.schedule(intent(o, "soft", (("width_milli", 700),)))
        b = o.schedule(intent(o, "soft", (("density_milli", 700),)))
        self.assertTrue(a.admitted)
        self.assertFalse(b.admitted)
        self.assertEqual(b.reason, "HOLD_QUEUE_FULL")
        self.assertEqual(o.queue_depth, 1)

    def test_k27_all_27_project_to_bounded_controls_deterministically(self):
        p = K27ConstraintProjector()
        s = owner().snapshot()
        seen = set()
        for x in range(3):
            for y in range(3):
                for z in range(3):
                    c = K27Coordinate(x, y, z)
                    raw = RawGestureIntent.build(GestureObservation(c.code, "open", 900, 600, c))
                    a = p.project(raw, s)
                    b = p.project(raw, s)
                    self.assertEqual(a, b)
                    value = a.controls[0][1]
                    self.assertTrue(0 <= value <= 1000)
                    seen.add(c.code)
        self.assertEqual(seen, set(range(27)))

    def test_out_of_bounds_control_is_held(self):
        o = owner()
        bad = intent(o, "soft", (("brightness_milli", 1001),))
        r = o.schedule(bad)
        self.assertFalse(r.admitted)
        self.assertEqual(r.reason, "HOLD_CONTROL_BOUNDS")
        self.assertEqual(o.queue_depth, 0)

    def test_graph_epoch_invalidation_reclaims_queue_capacity_immediately(self):
        o = owner(queue_capacity=2)
        a = o.schedule(intent(o, "hard", (("drop_state", 1),), gesture="fist"))
        b = o.schedule(intent(o, "hard", (("scale_index", 5),), gesture="rotate"))
        self.assertTrue(a.admitted and b.admitted)
        self.assertEqual(o.queue_depth, 2)
        wr = o.governed_graph_write(recipe_root=RECIPE)
        self.assertEqual(set(wr.invalidated_events), {a.event_id, b.event_id})
        self.assertEqual(o.queue_depth, 0)
        c = o.schedule(intent(o, "soft", (("width_milli", 650),)))
        self.assertTrue(c.admitted)

    def test_malformed_control_schema_is_held(self):
        o = owner()
        bad = intent(o, "soft", (("raw_audio_sample", 1),))
        r = o.schedule(bad)
        self.assertFalse(r.admitted)
        self.assertEqual(r.reason, "HOLD_CONTROL_SCHEMA")

    def test_membrane_keeps_gesture_work_outside_audio_owner_callback(self):
        o = owner()
        m = KineticAudioMembrane(o)
        c = K27Coordinate(2, 1, 1)
        self.assertIsNone(m.ingest(GestureObservation(0, "open", 900, 700, c)))
        r = m.ingest(GestureObservation(1, "open", 900, 700, c))
        self.assertTrue(r and r.admitted)
        self.assertFalse(hasattr(o, "compiler"))
        self.assertFalse(hasattr(o, "projector"))
        o.process_until(r.target_sample + o.block_size)
        self.assertNotEqual(dict(o.snapshot().soft_controls)["brightness_milli"], 500)

    def test_replay_is_deterministic(self):
        seq = [
            GestureObservation(0, "open", 900, 600, K27Coordinate(2, 1, 1)),
            GestureObservation(1, "open", 900, 600, K27Coordinate(2, 1, 1)),
            GestureObservation(2, "open", 400, 600, K27Coordinate(2, 1, 1)),
            GestureObservation(3, "rotate", 900, 800, K27Coordinate(0, 2, 2)),
            GestureObservation(4, "rotate", 900, 800, K27Coordinate(0, 2, 2)),
        ]
        self.assertEqual(
            replay_root(seq, recipe_root=RECIPE, engine_root=ENGINE),
            replay_root(seq, recipe_root=RECIPE, engine_root=ENGINE),
        )

    def test_synthetic_callback_probe_has_explicit_nonhardware_ceiling(self):
        o = owner(sample_rate=48_000, block_size=128)
        b = synthetic_callback_benchmark(o, blocks=500)
        self.assertEqual(b.claim_ceiling, "PROCESS_LEVEL_SYNTHETIC_ONLY")
        self.assertEqual(b.blocks, 500)
        self.assertGreater(b.callback_budget_ns, 0)
        self.assertGreaterEqual(b.max_ns, b.p99_ns)


if __name__ == "__main__":
    unittest.main()
