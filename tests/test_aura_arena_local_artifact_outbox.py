import tempfile
import time
import unittest
from pathlib import Path

from aura_arena_artifact_event_core import ArtifactEventRefusal, FileObservation, MirrorLineage
from aura_arena_local_artifact_outbox import LocalArtifactOutbox, LocalOutboxRefusal, LocalWatchConfig


def obs(path, t):
    st = Path(path).stat()
    return FileObservation(st.st_size, st.st_mtime_ns, t)


class LocalOutboxTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "Aura Drive 2"
        self.root.mkdir()
        self.db = Path(self.tmp.name) / "outbox.sqlite"
        self.cfg = LocalWatchConfig(
            roots=(str(self.root),),
            source_surface="AURA_DRIVE_2_LOCAL",
            project_id="CS-PROJ-001",
            source_currentness_ref="board-rev-1",
            producer_worker_id="W1",
            claim_id="AS04",
            work_order_id="CS-ARENA-SYNC-001",
            min_stable_ns=10,
        )
        self.out = LocalArtifactOutbox(self.db, self.cfg)

    def tearDown(self):
        self.out.close()
        self.tmp.cleanup()

    def stable(self, path):
        return [obs(path, 100), obs(path, 120)]

    def current(self):
        return {"expected_currentness_ref": "board-rev-1", "currentness": "CURRENT"}

    def cloud_lineage(self, generation=7):
        return MirrorLineage.start("cloud-origin", "AURA_DRIVE_CLOUD", artifact_generation=generation)

    def mirror_kwargs(self, generation=7):
        return {
            "inbound_mirror_lineage": self.cloud_lineage(generation),
            "expected_mirror_origin_id": "cloud-origin",
            "expected_mirror_generation": generation,
        }

    def test_outside_root_refused(self):
        p = Path(self.tmp.name) / "x.txt"
        p.write_text("x")
        with self.assertRaisesRegex(LocalOutboxRefusal, "PATH_OUTSIDE_CONFIGURED_ROOT"):
            self.out.ingest_file_notification(
                p, event_type="CREATE", observations=self.stable(p), observed_at="t", **self.current()
            )

    def test_partial_write_not_quiescent(self):
        p = self.root / "x.txt"
        p.write_text("a")
        a = obs(p, 100)
        p.write_text("abcdef")
        b = obs(p, 120)
        with self.assertRaisesRegex(ArtifactEventRefusal, "ARTIFACT_NOT_QUIESCENT"):
            self.out.ingest_file_notification(
                p, event_type="CREATE", observations=[a, b], observed_at="t", **self.current()
            )

    def test_short_stability_window_refused(self):
        p = self.root / "x.txt"
        p.write_text("a")
        st = p.stat()
        samples = [
            FileObservation(st.st_size, st.st_mtime_ns, 100),
            FileObservation(st.st_size, st.st_mtime_ns, 105),
        ]
        with self.assertRaisesRegex(ArtifactEventRefusal, "ARTIFACT_STABILITY_WINDOW_TOO_SHORT"):
            self.out.ingest_file_notification(
                p, event_type="CREATE", observations=samples, observed_at="t", **self.current()
            )

    def test_closed_evidence_allows_single_sample(self):
        p = self.root / "x.txt"
        p.write_text("a")
        result = self.out.ingest_file_notification(
            p,
            event_type="CREATE",
            observations=[obs(p, 100)],
            observed_at="t",
            closed_evidence=True,
            **self.current(),
        )
        self.assertEqual(result.disposition, "ENQUEUED")

    def test_atomic_publish_allows_single_sample(self):
        p = self.root / "x.txt"
        p.write_text("a")
        result = self.out.ingest_file_notification(
            p,
            event_type="CREATE",
            observations=[obs(p, 100)],
            observed_at="t",
            atomic_publish_evidence=True,
            **self.current(),
        )
        self.assertEqual(result.disposition, "ENQUEUED")

    def test_duplicate_notification_is_idempotent_without_generation_bump(self):
        p = self.root / "x.txt"
        p.write_text("one")
        samples = self.stable(p)
        first = self.out.ingest_file_notification(
            p, event_type="CREATE", observations=samples, observed_at="t1", **self.current()
        )
        second = self.out.ingest_file_notification(
            p, event_type="CREATE", observations=samples, observed_at="t2", **self.current()
        )
        self.assertEqual(second.disposition, "IDEMPOTENT_REPLAY")
        self.assertEqual(first.record.event.event_id, second.record.event.event_id)
        self.assertEqual(self.out.generation_for(p), 1)
        self.assertEqual(len(self.out.pending()), 1)

    def test_same_name_new_content_versions_without_collision(self):
        p = self.root / "x.txt"
        p.write_text("one")
        first = self.out.ingest_file_notification(
            p, event_type="CREATE", observations=self.stable(p), observed_at="t1", **self.current()
        )
        time.sleep(0.001)
        p.write_text("two")
        second = self.out.ingest_file_notification(
            p, event_type="MODIFY", observations=self.stable(p), observed_at="t2", **self.current()
        )
        self.assertNotEqual(first.record.identity.artifact_sid, second.record.identity.artifact_sid)
        self.assertEqual(second.record.event.generation, 2)
        self.assertEqual(len(self.out.pending()), 2)

    def test_restart_replays_pending_exactly(self):
        p = self.root / "x.txt"
        p.write_text("one")
        first = self.out.ingest_file_notification(
            p, event_type="CREATE", observations=self.stable(p), observed_at="t", **self.current()
        )
        self.out.close()
        self.out = LocalArtifactOutbox(self.db, self.cfg)
        pending = self.out.pending()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].event.event_id, first.record.event.event_id)

    def test_ack_is_idempotent_and_removes_pending(self):
        p = self.root / "x.txt"
        p.write_text("one")
        result = self.out.ingest_file_notification(
            p, event_type="CREATE", observations=self.stable(p), observed_at="t", **self.current()
        )
        self.assertEqual(self.out.ack(result.record.event.event_id, persistence_receipt_ref="receipt:1"), "ACKED")
        self.assertEqual(
            self.out.ack(result.record.event.event_id, persistence_receipt_ref="receipt:1"), "IDEMPOTENT_ACK"
        )
        self.assertEqual(self.out.pending(), [])

    def test_ack_conflict_fails_closed(self):
        p = self.root / "x.txt"
        p.write_text("one")
        result = self.out.ingest_file_notification(
            p, event_type="CREATE", observations=self.stable(p), observed_at="t", **self.current()
        )
        self.out.ack(result.record.event.event_id, persistence_receipt_ref="receipt:1")
        with self.assertRaisesRegex(LocalOutboxRefusal, "ACK_RECEIPT_CONFLICT"):
            self.out.ack(result.record.event.event_id, persistence_receipt_ref="receipt:2")

    def test_tombstone_requires_prior_lineage_and_no_bytes(self):
        p = self.root / "gone.txt"
        with self.assertRaisesRegex(LocalOutboxRefusal, "PRIOR_LINEAGE_REQUIRED"):
            self.out.ingest_tombstone(p, observed_at="t", **self.current())
        result = self.out.ingest_tombstone(
            p,
            observed_at="t",
            prior_artifact_id="artifact-sha256-" + "0" * 64,
            **self.current(),
        )
        self.assertIsNone(result.record.identity)
        self.assertEqual(result.record.event.event_type, "TOMBSTONE")

    def test_rename_binds_old_resource_lineage(self):
        old = self.root / "a.txt"
        new = self.root / "b.txt"
        new.write_text("body")
        result = self.out.ingest_rename(
            old, new, observations=self.stable(new), observed_at="t", **self.current()
        )
        self.assertEqual(result.record.event.event_type, "RENAME")
        self.assertIn("a.txt", result.record.event.prior_resource_ref)

    def test_inbound_mirror_to_same_surface_is_suppressed(self):
        p = self.root / "x.txt"
        p.write_text("one")
        lineage = self.cloud_lineage().next_hop("AURA_DRIVE_2_LOCAL")
        result = self.out.ingest_file_notification(
            p,
            event_type="MODIFY",
            observations=self.stable(p),
            observed_at="t",
            inbound_mirror_lineage=lineage,
            **self.current(),
        )
        self.assertEqual(result.disposition, "SELF_LOOP_SUPPRESSED")
        self.assertEqual(self.out.pending(), [])

    def test_records_never_claim_execution_or_provider_authority(self):
        p = self.root / "x.txt"
        p.write_text("one")
        result = self.out.ingest_file_notification(
            p, event_type="CREATE", observations=self.stable(p), observed_at="t", **self.current()
        )
        data = result.record.to_dict()
        self.assertFalse(data["execution_authorized"])
        self.assertFalse(data["provider_calls_authorized"])
        self.assertFalse(data["background_execution_claimed"])

    def test_unknown_currentness_config_is_refused(self):
        with self.assertRaisesRegex(LocalOutboxRefusal, "CURRENTNESS_REF_REQUIRED"):
            LocalWatchConfig(
                roots=(str(self.root),),
                source_surface="LOCAL",
                project_id="P",
                source_currentness_ref="UNKNOWN",
            )

    def test_sqlite_wal_and_full_sync_enabled(self):
        mode = self.out._conn.execute("PRAGMA journal_mode").fetchone()[0]
        sync = self.out._conn.execute("PRAGMA synchronous").fetchone()[0]
        self.assertEqual(mode.lower(), "wal")
        self.assertEqual(sync, 2)

    def test_stale_exact_currentness_rebases_without_generation_or_enqueue(self):
        p = self.root / "x.txt"
        p.write_text("one")
        result = self.out.ingest_file_notification(
            p,
            event_type="CREATE",
            observations=self.stable(p),
            observed_at="t",
            expected_currentness_ref="board-rev-2",
            currentness="CURRENT",
        )
        self.assertEqual(result.disposition, "REBASE")
        self.assertIsNone(result.record)
        self.assertEqual(self.out.generation_for(p), 0)
        self.assertEqual(self.out.pending(), [])

    def test_qualitative_stale_currentness_rebases_without_generation_or_enqueue(self):
        p = self.root / "x.txt"
        p.write_text("one")
        result = self.out.ingest_file_notification(
            p,
            event_type="CREATE",
            observations=self.stable(p),
            observed_at="t",
            expected_currentness_ref="board-rev-1",
            currentness="STALE",
        )
        self.assertEqual(result.disposition, "REBASE")
        self.assertEqual(self.out.generation_for(p), 0)
        self.assertEqual(self.out.pending(), [])

    def test_inbound_cloud_lineage_is_extended_not_reset(self):
        p = self.root / "x.txt"
        p.write_text("one")
        inbound = self.cloud_lineage()
        expected = inbound.next_hop("AURA_DRIVE_2_LOCAL")
        result = self.out.ingest_file_notification(
            p,
            event_type="MODIFY",
            observations=self.stable(p),
            observed_at="t",
            inbound_mirror_lineage=inbound,
            expected_mirror_origin_id="cloud-origin",
            expected_mirror_generation=7,
            **self.current(),
        )
        self.assertEqual(result.disposition, "ENQUEUED")
        self.assertEqual(result.record.event.origin_id, "cloud-origin")
        self.assertEqual(result.record.event.generation, 7)
        self.assertEqual(result.record.event.mirror_fence, expected.fence)
        self.assertEqual(self.out.generation_for(p), 0)

        # A later true local mutation starts its own local generation sequence at 1.
        time.sleep(0.001)
        p.write_text("local edit")
        local = self.out.ingest_file_notification(
            p, event_type="MODIFY", observations=self.stable(p), observed_at="t2", **self.current()
        )
        self.assertEqual(local.record.event.generation, 1)
        self.assertEqual(self.out.generation_for(p), 1)

    def test_inbound_mirror_binding_mismatch_fails_closed(self):
        p = self.root / "x.txt"
        p.write_text("one")
        inbound = self.cloud_lineage()
        with self.assertRaisesRegex(LocalOutboxRefusal, "MIRROR_ORIGIN_BINDING_MISMATCH"):
            self.out.ingest_file_notification(
                p,
                event_type="MODIFY",
                observations=self.stable(p),
                observed_at="t",
                inbound_mirror_lineage=inbound,
                expected_mirror_origin_id="wrong-origin",
                expected_mirror_generation=7,
                **self.current(),
            )
        self.assertEqual(self.out.generation_for(p), 0)
        self.assertEqual(self.out.pending(), [])

    def test_mirrored_rename_preserves_origin_generation_fence_without_local_generation(self):
        old = self.root / "old.txt"
        new = self.root / "new.txt"
        new.write_text("mirrored body")
        inbound = self.cloud_lineage(11)
        expected = inbound.next_hop("AURA_DRIVE_2_LOCAL")
        result = self.out.ingest_rename(
            old,
            new,
            observations=self.stable(new),
            observed_at="t",
            inbound_mirror_lineage=inbound,
            expected_mirror_origin_id="cloud-origin",
            expected_mirror_generation=11,
            **self.current(),
        )
        self.assertEqual(result.disposition, "ENQUEUED")
        self.assertEqual(result.record.event.event_type, "RENAME")
        self.assertEqual(result.record.event.origin_id, "cloud-origin")
        self.assertEqual(result.record.event.generation, 11)
        self.assertEqual(result.record.event.mirror_fence, expected.fence)
        self.assertEqual(self.out.generation_for(new), 0)

    def test_mirrored_tombstone_preserves_origin_generation_fence_and_prior_lineage(self):
        gone = self.root / "gone-cloud.txt"
        inbound = self.cloud_lineage(12)
        expected = inbound.next_hop("AURA_DRIVE_2_LOCAL")
        result = self.out.ingest_tombstone(
            gone,
            observed_at="t",
            prior_artifact_id="artifact-sha256-" + "a" * 64,
            inbound_mirror_lineage=inbound,
            expected_mirror_origin_id="cloud-origin",
            expected_mirror_generation=12,
            **self.current(),
        )
        self.assertEqual(result.disposition, "ENQUEUED")
        self.assertEqual(result.record.event.event_type, "TOMBSTONE")
        self.assertEqual(result.record.event.origin_id, "cloud-origin")
        self.assertEqual(result.record.event.generation, 12)
        self.assertEqual(result.record.event.mirror_fence, expected.fence)
        self.assertIsNone(result.record.identity)
        self.assertEqual(self.out.generation_for(gone), 0)

    def test_mirrored_rename_and_tombstone_binding_mismatch_are_zero_state(self):
        old = self.root / "old.txt"
        new = self.root / "new.txt"
        new.write_text("body")
        inbound = self.cloud_lineage(7)
        with self.assertRaisesRegex(LocalOutboxRefusal, "MIRROR_ORIGIN_BINDING_MISMATCH"):
            self.out.ingest_rename(
                old,
                new,
                observations=self.stable(new),
                observed_at="t",
                inbound_mirror_lineage=inbound,
                expected_mirror_origin_id="wrong",
                expected_mirror_generation=7,
                **self.current(),
            )
        with self.assertRaisesRegex(LocalOutboxRefusal, "MIRROR_GENERATION_BINDING_MISMATCH"):
            self.out.ingest_tombstone(
                self.root / "gone.txt",
                observed_at="t2",
                prior_artifact_id="artifact-sha256-" + "b" * 64,
                inbound_mirror_lineage=inbound,
                expected_mirror_origin_id="cloud-origin",
                expected_mirror_generation=8,
                **self.current(),
            )
        self.assertEqual(self.out.generation_for(new), 0)
        self.assertEqual(self.out.generation_for(self.root / "gone.txt"), 0)
        self.assertEqual(self.out.pending(), [])

    def test_mirrored_rename_and_tombstone_self_loop_suppress_without_state(self):
        lineage = self.cloud_lineage().next_hop("AURA_DRIVE_2_LOCAL")
        rename = self.out.ingest_rename(
            self.root / "old.txt",
            self.root / "new.txt",
            observations=[],
            observed_at="t",
            inbound_mirror_lineage=lineage,
            **self.current(),
        )
        tomb = self.out.ingest_tombstone(
            self.root / "gone.txt",
            observed_at="t2",
            inbound_mirror_lineage=lineage,
            **self.current(),
        )
        self.assertEqual(rename.disposition, "SELF_LOOP_SUPPRESSED")
        self.assertEqual(tomb.disposition, "SELF_LOOP_SUPPRESSED")
        self.assertEqual(self.out.pending(), [])
        self.assertEqual(self.out.generation_for(self.root / "new.txt"), 0)
        self.assertEqual(self.out.generation_for(self.root / "gone.txt"), 0)

    def test_local_mutations_after_mirrored_rename_and_tombstone_use_independent_generation(self):
        old = self.root / "old.txt"
        new = self.root / "new.txt"
        new.write_text("mirrored rename")
        self.out.ingest_rename(
            old,
            new,
            observations=self.stable(new),
            observed_at="t1",
            **self.mirror_kwargs(21),
            **self.current(),
        )
        time.sleep(0.001)
        new.write_text("true local edit")
        local_new = self.out.ingest_file_notification(
            new, event_type="MODIFY", observations=self.stable(new), observed_at="t2", **self.current()
        )
        self.assertEqual(local_new.record.event.generation, 1)
        self.assertEqual(self.out.generation_for(new), 1)

        gone = self.root / "gone.txt"
        self.out.ingest_tombstone(
            gone,
            observed_at="t3",
            prior_artifact_id="artifact-sha256-" + "c" * 64,
            **self.mirror_kwargs(22),
            **self.current(),
        )
        gone.write_text("recreated locally")
        local_gone = self.out.ingest_file_notification(
            gone, event_type="CREATE", observations=self.stable(gone), observed_at="t4", **self.current()
        )
        self.assertEqual(local_gone.record.event.generation, 1)
        self.assertEqual(self.out.generation_for(gone), 1)


if __name__ == "__main__":
    unittest.main()
