import tempfile
import unittest
from pathlib import Path

from aura_arena_artifact_event_core import FileObservation, MirrorLineage
from aura_local_artifact_outbox import (
    LOCAL_SURFACE,
    LocalArtifactOutbox,
    LocalArtifactRefusal,
    LocalMutationIntent,
    sample_file_observation,
)


class LocalArtifactOutboxTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "Aura Drive 2"
        self.root.mkdir()
        self.db = Path(self.tmp.name) / "outbox.sqlite3"

    def tearDown(self):
        self.tmp.cleanup()

    def intent(self, **overrides):
        base = dict(
            origin_id="local-event-1",
            event_type="CREATE",
            relative_path="project/a.txt",
            project_id="CS-PROJ-001",
            source_currentness_ref="board-r7",
            artifact_generation=7,
            producer_worker_id="W-AS04",
            claim_id="AS-04",
            work_order_id="CS-ARENA-SYNC-001",
            observed_at="2026-08-30T15:40:00Z",
        )
        base.update(overrides)
        return LocalMutationIntent(**base)

    def write_file(self, relative_path="project/a.txt", body=b"hello"):
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        return path

    def stable_observations(self, relative_path="project/a.txt"):
        path = self.root / relative_path
        stat = path.stat()
        return [
            FileObservation(stat.st_size, stat.st_mtime_ns, 100),
            FileObservation(stat.st_size, stat.st_mtime_ns, 200),
        ]

    def test_sample_file_observation_is_caller_timed(self):
        self.write_file()
        sample = sample_file_observation(self.root, "project/a.txt", observed_monotonic_ns=123)
        self.assertEqual(sample.byte_size, 5)
        self.assertEqual(sample.observed_monotonic_ns, 123)

    def test_stable_file_is_content_addressed_and_enqueued(self):
        self.write_file()
        with LocalArtifactOutbox(self.db) as outbox:
            result = outbox.stage(
                self.root,
                self.intent(),
                expected_currentness_ref="board-r7",
                currentness="CURRENT",
                observations=self.stable_observations(),
                min_stable_ns=100,
            )
            self.assertTrue(result.enqueued)
            self.assertEqual(result.disposition, "INGEST")
            self.assertTrue(result.envelope.identity.artifact_sid.startswith("artifact-sha256-"))
            self.assertEqual(outbox.count(), 1)
            self.assertEqual(len(outbox.pending()), 1)

    def test_atomic_publish_can_stage_with_one_sample(self):
        self.write_file()
        sample = sample_file_observation(self.root, "project/a.txt", observed_monotonic_ns=100)
        with LocalArtifactOutbox(self.db) as outbox:
            result = outbox.stage(
                self.root,
                self.intent(),
                expected_currentness_ref="board-r7",
                currentness="CURRENT",
                observations=[sample],
                min_stable_ns=999999,
                atomic_publish_evidence=True,
            )
            self.assertTrue(result.enqueued)
            self.assertTrue(result.envelope.quiescence.atomic_publish_evidence)

    def test_unstable_file_is_refused_before_outbox(self):
        self.write_file()
        stat = (self.root / "project/a.txt").stat()
        observations = [
            FileObservation(stat.st_size, stat.st_mtime_ns, 100),
            FileObservation(stat.st_size + 1, stat.st_mtime_ns + 1, 200),
        ]
        with LocalArtifactOutbox(self.db) as outbox:
            with self.assertRaisesRegex(LocalArtifactRefusal, "ARTIFACT_NOT_QUIESCENT"):
                outbox.stage(
                    self.root,
                    self.intent(),
                    expected_currentness_ref="board-r7",
                    currentness="CURRENT",
                    observations=observations,
                    min_stable_ns=100,
                )
            self.assertEqual(outbox.count(), 0)

    def test_exact_currentness_ref_mismatch_rebases_without_enqueue(self):
        self.write_file()
        with LocalArtifactOutbox(self.db) as outbox:
            result = outbox.stage(
                self.root,
                self.intent(source_currentness_ref="board-old"),
                expected_currentness_ref="board-r7",
                currentness="CURRENT",
                observations=self.stable_observations(),
                min_stable_ns=100,
            )
            self.assertEqual(result.disposition, "REBASE")
            self.assertFalse(result.enqueued)
            self.assertEqual(outbox.count(), 0)

    def test_qualitative_stale_currentness_rebases_without_enqueue(self):
        self.write_file()
        with LocalArtifactOutbox(self.db) as outbox:
            result = outbox.stage(
                self.root,
                self.intent(),
                expected_currentness_ref="board-r7",
                currentness="STALE",
                observations=self.stable_observations(),
                min_stable_ns=100,
            )
            self.assertEqual(result.disposition, "REBASE")
            self.assertEqual(outbox.count(), 0)

    def test_replay_is_idempotent_and_does_not_duplicate_row(self):
        self.write_file()
        kwargs = dict(
            expected_currentness_ref="board-r7",
            currentness="CURRENT",
            observations=self.stable_observations(),
            min_stable_ns=100,
        )
        with LocalArtifactOutbox(self.db) as outbox:
            first = outbox.stage(self.root, self.intent(), **kwargs)
            second = outbox.stage(self.root, self.intent(observed_at="2026-08-30T15:41:00Z"), **kwargs)
            self.assertTrue(first.enqueued)
            self.assertEqual(second.disposition, "IDEMPOTENT_REPLAY")
            self.assertFalse(second.enqueued)
            self.assertEqual(outbox.count(), 1)

    def test_delete_requires_prior_lineage_and_enqueues_tombstone(self):
        prior = "artifact-sha256-" + "a" * 64
        with LocalArtifactOutbox(self.db) as outbox:
            result = outbox.stage(
                self.root,
                self.intent(event_type="DELETE", prior_artifact_id=prior),
                expected_currentness_ref="board-r7",
                currentness="CURRENT",
            )
            self.assertEqual(result.disposition, "TOMBSTONE")
            self.assertIsNone(result.envelope.identity)
            self.assertTrue(result.enqueued)

    def test_delete_without_prior_lineage_fails_closed(self):
        with LocalArtifactOutbox(self.db) as outbox:
            with self.assertRaisesRegex(LocalArtifactRefusal, "PRIOR_LINEAGE_REQUIRED"):
                outbox.stage(
                    self.root,
                    self.intent(event_type="DELETE"),
                    expected_currentness_ref="board-r7",
                    currentness="CURRENT",
                )

    def test_inbound_mirror_bounce_to_local_is_suppressed(self):
        self.write_file()
        inbound = MirrorLineage.start(
            "local-event-1", LOCAL_SURFACE, artifact_generation=7
        ).next_hop("AURA_DRIVE_CLOUD")
        with LocalArtifactOutbox(self.db) as outbox:
            with self.assertRaisesRegex(LocalArtifactRefusal, "MIRROR_LOOP_SUPPRESSED"):
                outbox.stage(
                    self.root,
                    self.intent(),
                    expected_currentness_ref="board-r7",
                    currentness="CURRENT",
                    observations=self.stable_observations(),
                    min_stable_ns=100,
                    inbound_lineage=inbound,
                )

    def test_foreign_mirror_generation_is_refused(self):
        self.write_file()
        inbound = MirrorLineage.start("local-event-1", "AURA_DRIVE_CLOUD", artifact_generation=6)
        with LocalArtifactOutbox(self.db) as outbox:
            with self.assertRaisesRegex(LocalArtifactRefusal, "MIRROR_GENERATION_BINDING_MISMATCH"):
                outbox.stage(
                    self.root,
                    self.intent(artifact_generation=7),
                    expected_currentness_ref="board-r7",
                    currentness="CURRENT",
                    observations=self.stable_observations(),
                    min_stable_ns=100,
                    inbound_lineage=inbound,
                )

    def test_path_escape_is_refused(self):
        outside = Path(self.tmp.name) / "outside.txt"
        outside.write_text("x")
        with LocalArtifactOutbox(self.db) as outbox:
            with self.assertRaisesRegex(LocalArtifactRefusal, "PATH_OUTSIDE_AURA_DRIVE_2"):
                outbox.stage(
                    self.root,
                    self.intent(relative_path="../outside.txt"),
                    expected_currentness_ref="board-r7",
                    currentness="CURRENT",
                    observations=[],
                )

    def test_authority_flags_remain_false(self):
        self.write_file()
        with LocalArtifactOutbox(self.db) as outbox:
            result = outbox.stage(
                self.root,
                self.intent(),
                expected_currentness_ref="board-r7",
                currentness="CURRENT",
                observations=self.stable_observations(),
                min_stable_ns=100,
            )
            authority = result.envelope.to_dict()["authority"]
            self.assertFalse(authority["semantic_owner_bound"])
            self.assertFalse(authority["coordinate_owner_bound"])
            self.assertFalse(authority["cloud_write_authorized"])
            self.assertFalse(authority["artifact_persistence_indexed"])
            self.assertFalse(authority["workgraph_wake_emitted"])
            self.assertFalse(authority["execution_authorized"])
            self.assertFalse(authority["runtime_execution_proven"])
            self.assertFalse(authority["background_execution_claimed"])
            self.assertEqual(authority["provider_calls"], 0)

    def test_delivery_receipt_is_exact_and_idempotent(self):
        self.write_file()
        with LocalArtifactOutbox(self.db) as outbox:
            result = outbox.stage(
                self.root,
                self.intent(),
                expected_currentness_ref="board-r7",
                currentness="CURRENT",
                observations=self.stable_observations(),
                min_stable_ns=100,
            )
            outbox.mark_delivered(result.event_id, "as06-receipt-1")
            outbox.mark_delivered(result.event_id, "as06-receipt-1")
            self.assertEqual(outbox.pending(), [])
            with self.assertRaisesRegex(LocalArtifactRefusal, "DELIVERY_RECEIPT_BINDING_MISMATCH"):
                outbox.mark_delivered(result.event_id, "different-receipt")


if __name__ == "__main__":
    unittest.main()
