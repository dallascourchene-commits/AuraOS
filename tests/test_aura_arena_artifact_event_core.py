import unittest

from aura_arena_artifact_event_core import (
    ArtifactEventRefusal,
    ArtifactIdentity,
    ArtifactMutationEvent,
    FileObservation,
    MirrorLineage,
    classify_replay,
    prove_quiescence,
    require_rename_parent,
    validate_event_identity_binding,
)


class ArtifactEventCoreTests(unittest.TestCase):
    def event(self, **overrides):
        base = dict(
            origin_id="origin-1",
            provider="local",
            source_surface="AURA_DRIVE_2_LOCAL",
            event_type="CREATE",
            resource_ref="C:/AuraDrive2/a.txt",
            project_id="CS-PROJ-001",
            producer_worker_id="W-1",
            claim_id="AS-02",
            work_order_id="CS-ARENA-SYNC-001",
            source_currentness_ref="board-r1",
            generation=0,
        )
        base.update(overrides)
        return ArtifactMutationEvent(**base)

    def test_event_id_is_replay_stable_across_observed_time(self):
        a = self.event(observed_at="2026-08-30T10:00:00Z")
        b = self.event(observed_at="2026-08-30T10:01:00Z")
        self.assertEqual(a.event_id, b.event_id)

    def test_event_id_changes_for_generation(self):
        self.assertNotEqual(self.event(generation=0).event_id, self.event(generation=1).event_id)

    def test_supplied_bad_event_id_refused(self):
        with self.assertRaisesRegex(ArtifactEventRefusal, "EVENT_ID_BINDING_MISMATCH"):
            self.event(event_id="evt-wrong")

    def test_unsupported_event_type_refused(self):
        with self.assertRaisesRegex(ArtifactEventRefusal, "UNSUPPORTED_EVENT_TYPE"):
            self.event(event_type="COPY_AND_EXECUTE")

    def test_identity_is_content_addressed_not_filename_addressed(self):
        a = ArtifactIdentity.from_bytes(b"same", extension=".txt", parent_refs=("p1",))
        b = ArtifactIdentity.from_bytes(b"same", extension=".bin", parent_refs=("p2",))
        self.assertEqual(a.artifact_sid, b.artifact_sid)
        self.assertEqual(a.sha256, b.sha256)

    def test_same_filename_different_bytes_are_different_artifacts(self):
        a = ArtifactIdentity.from_bytes(b"a", extension=".txt")
        b = ArtifactIdentity.from_bytes(b"b", extension=".txt")
        self.assertNotEqual(a.artifact_sid, b.artifact_sid)

    def test_invalid_sha_refused(self):
        with self.assertRaisesRegex(ArtifactEventRefusal, "INVALID_SHA256"):
            ArtifactIdentity("notahash", 1, "", ".txt")

    def test_quiescence_requires_stable_tail(self):
        proof = prove_quiescence([FileObservation(5, 10), FileObservation(5, 10)])
        self.assertEqual(proof.stable_samples, 2)
        self.assertFalse(proof.closed_evidence)

    def test_unstable_file_refused(self):
        with self.assertRaisesRegex(ArtifactEventRefusal, "ARTIFACT_NOT_QUIESCENT"):
            prove_quiescence([FileObservation(4, 9), FileObservation(5, 10)])

    def test_single_sample_insufficient_without_close(self):
        with self.assertRaisesRegex(ArtifactEventRefusal, "ARTIFACT_NOT_QUIESCENT"):
            prove_quiescence([FileObservation(5, 10)])

    def test_close_evidence_allows_one_observation(self):
        proof = prove_quiescence([FileObservation(5, 10)], closed_evidence=True)
        self.assertTrue(proof.closed_evidence)

    def test_mirror_lineage_advances_generation(self):
        line = MirrorLineage.start("o", "LOCAL")
        cloud = line.next_hop("CLOUD")
        self.assertEqual(cloud.generation, 1)
        self.assertEqual(cloud.surfaces, ("LOCAL", "CLOUD"))

    def test_mirror_bounce_loop_is_refused(self):
        line = MirrorLineage.start("o", "LOCAL").next_hop("CLOUD")
        with self.assertRaisesRegex(ArtifactEventRefusal, "MIRROR_LOOP_SUPPRESSED"):
            line.next_hop("LOCAL")

    def test_duplicate_surface_inside_lineage_refused(self):
        with self.assertRaisesRegex(ArtifactEventRefusal, "MIRROR_LINEAGE_LOOP"):
            MirrorLineage("o", ("LOCAL", "CLOUD", "LOCAL"), generation=2)

    def test_generation_must_match_lineage(self):
        with self.assertRaisesRegex(ArtifactEventRefusal, "MIRROR_GENERATION_MISMATCH"):
            MirrorLineage("o", ("LOCAL", "CLOUD"), generation=0)

    def test_mirror_fence_is_stable(self):
        a = MirrorLineage.start("o", "LOCAL").next_hop("CLOUD")
        b = MirrorLineage.start("o", "LOCAL").next_hop("CLOUD")
        self.assertEqual(a.fence, b.fence)

    def test_current_event_is_ingest(self):
        self.assertEqual(classify_replay(self.event(), currentness="CURRENT"), "INGEST")

    def test_seen_event_is_idempotent_replay(self):
        e = self.event()
        self.assertEqual(
            classify_replay(e, currentness="CURRENT", seen_event_ids=[e.event_id]),
            "IDEMPOTENT_REPLAY",
        )

    def test_stale_currentness_returns_rebase_before_replay(self):
        e = self.event()
        self.assertEqual(
            classify_replay(e, currentness="STALE", seen_event_ids=[e.event_id]),
            "REBASE",
        )

    def test_delete_is_tombstone_disposition(self):
        e = self.event(event_type="DELETE")
        self.assertEqual(classify_replay(e, currentness="CURRENT"), "TOMBSTONE")

    def test_rename_requires_prior_artifact(self):
        with self.assertRaisesRegex(ArtifactEventRefusal, "RENAME_PRIOR_ARTIFACT_REQUIRED"):
            require_rename_parent(self.event(event_type="RENAME"))

    def test_rename_with_prior_artifact_is_allowed(self):
        require_rename_parent(
            self.event(event_type="RENAME", prior_artifact_id="artifact-sha256-" + "a" * 64)
        )

    def test_non_tombstone_requires_identity(self):
        with self.assertRaisesRegex(ArtifactEventRefusal, "ARTIFACT_IDENTITY_REQUIRED"):
            validate_event_identity_binding(self.event(), None)

    def test_tombstone_accepts_no_identity(self):
        validate_event_identity_binding(self.event(event_type="TOMBSTONE"), None)

    def test_tombstone_rejects_attached_bytes_identity(self):
        ident = ArtifactIdentity.from_bytes(b"x")
        with self.assertRaisesRegex(ArtifactEventRefusal, "TOMBSTONE_MUST_NOT_REQUIRE_BYTES"):
            validate_event_identity_binding(self.event(event_type="TOMBSTONE"), ident)

    def test_parent_refs_deduplicate_and_sort(self):
        ident = ArtifactIdentity.from_bytes(b"x", parent_refs=("b", "a", "b"))
        self.assertEqual(ident.parent_refs, ("a", "b"))

    def test_extension_normalizes_dot(self):
        ident = ArtifactIdentity.from_bytes(b"x", extension="PNG")
        self.assertEqual(ident.extension, ".png")


if __name__ == "__main__":
    unittest.main()
