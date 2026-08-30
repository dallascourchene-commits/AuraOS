import unittest

from artifact_sync_core import (
    ArtifactIdentityV1,
    ArtifactMirrorFenceV1,
    ArtifactMutationEventV1,
    ArtifactSyncError,
    QuiescenceSampleV1,
    evaluate_quiescence,
    event_for_mirrored_observation,
    mirror_route_decision,
)


def event(**changes):
    data = dict(
        origin_id="origin-001",
        provider="LOCAL_FS",
        source_surface="AURA_DRIVE2_LOCAL",
        event_type="CREATE",
        source_path_or_resource_id="/arena/assets/hero.png",
        producer_worker_id="worker-a",
        claim_id="claim-001",
        work_order_id="AS-02",
        project_id="CS-PROJ-001",
        source_currentness_ref="cur-001",
        observed_at="2026-08-30T15:00:00Z",
        generation=1,
        mirror_fence=None,
        prior_artifact_id=None,
        prior_source_path_or_resource_id=None,
        metadata={},
    )
    data.update(changes)
    return ArtifactMutationEventV1.build(**data)


class ArtifactMutationTests(unittest.TestCase):
    def test_observation_clock_does_not_churn_event_identity(self):
        a = event(observed_at="2026-08-30T15:00:00Z")
        b = event(observed_at="2026-08-30T15:00:09Z")
        self.assertEqual(a.event_id, b.event_id)
        self.assertEqual(a.idempotency_key(), b.idempotency_key())

    def test_generation_changes_mutation_identity(self):
        self.assertNotEqual(event(generation=1).event_id, event(generation=2).event_id)

    def test_metadata_does_not_change_logical_mutation_identity(self):
        a = event(metadata={"transport_delivery": "x"})
        b = event(metadata={"transport_delivery": "y"})
        self.assertEqual(a.event_id, b.event_id)

    def test_bad_event_id_fails_closed(self):
        good = event()
        raw = {**good.__dict__, "event_id": "forged"}
        with self.assertRaises(ArtifactSyncError) as ctx:
            ArtifactMutationEventV1(**raw).validate()
        self.assertEqual(ctx.exception.code, "EVENT_ID_MISMATCH")

    def test_rename_requires_prior_lineage(self):
        with self.assertRaises(ArtifactSyncError) as ctx:
            event(event_type="RENAME")
        self.assertEqual(ctx.exception.code, "PRIOR_LINEAGE_REQUIRED")

    def test_rename_with_prior_source_is_valid(self):
        item = event(
            event_type="RENAME",
            source_path_or_resource_id="/arena/assets/new.png",
            prior_source_path_or_resource_id="/arena/assets/old.png",
        )
        item.validate()

    def test_tombstone_requires_prior_lineage(self):
        with self.assertRaises(ArtifactSyncError) as ctx:
            event(event_type="TOMBSTONE")
        self.assertEqual(ctx.exception.code, "PRIOR_LINEAGE_REQUIRED")

    def test_tombstone_preserves_prior_artifact_lineage(self):
        item = event(event_type="TOMBSTONE", prior_artifact_id="artifact-old")
        self.assertEqual(item.to_dict()["prior_artifact_id"], "artifact-old")


class ArtifactIdentityTests(unittest.TestCase):
    def test_same_bytes_same_provenance_same_sid(self):
        kwargs = dict(
            mime="image/png",
            extension=".png",
            source_surface="AURA_DRIVE2_LOCAL",
            source_path_or_resource_id="/arena/a.png",
            origin_id="origin-a",
            generation=1,
        )
        a = ArtifactIdentityV1.from_bytes(b"pixels", **kwargs)
        b = ArtifactIdentityV1.from_bytes(b"pixels", **kwargs)
        self.assertEqual(a.artifact_sid, b.artifact_sid)
        self.assertEqual(a.sha256, b.sha256)

    def test_same_bytes_different_provenance_do_not_collapse_sid(self):
        base = dict(mime="image/png", extension=".png", generation=1)
        a = ArtifactIdentityV1.from_bytes(
            b"same",
            source_surface="AURA_DRIVE2_LOCAL",
            source_path_or_resource_id="/arena/a.png",
            origin_id="origin-a",
            **base,
        )
        b = ArtifactIdentityV1.from_bytes(
            b"same",
            source_surface="AURA_DRIVE_CLOUD",
            source_path_or_resource_id="drive:file-b",
            origin_id="origin-b",
            **base,
        )
        self.assertEqual(a.sha256, b.sha256)
        self.assertEqual(a.content_key(), b.content_key())
        self.assertNotEqual(a.artifact_sid, b.artifact_sid)

    def test_different_bytes_same_path_do_not_collapse(self):
        kwargs = dict(
            mime="text/plain",
            extension=".txt",
            source_surface="AURA_DRIVE2_LOCAL",
            source_path_or_resource_id="/arena/output.txt",
            origin_id="origin-a",
        )
        a = ArtifactIdentityV1.from_bytes(b"v1", generation=1, **kwargs)
        b = ArtifactIdentityV1.from_bytes(b"v2", generation=2, **kwargs)
        self.assertNotEqual(a.sha256, b.sha256)
        self.assertNotEqual(a.artifact_sid, b.artifact_sid)

    def test_semantic_type_is_not_used_as_coordinate_truth(self):
        item = ArtifactIdentityV1.from_bytes(
            b"data",
            mime="application/octet-stream",
            extension=".bin",
            source_surface="LOCAL",
            source_path_or_resource_id="x.bin",
            origin_id="o",
            generation=1,
        )
        self.assertEqual(item.semantic_type, "UNKNOWN")


class MirrorFenceTests(unittest.TestCase):
    def test_forward_mirror_mints_deterministic_fence_without_authority(self):
        result = mirror_route_decision(event=event(), target_surface="AURA_DRIVE_CLOUD")
        self.assertEqual(result["decision"], "ALLOW_MIRROR_PLAN")
        self.assertFalse(result["execution_authorized"])
        self.assertEqual(result["fence"]["source_surface"], "AURA_DRIVE2_LOCAL")
        self.assertEqual(result["fence"]["target_surface"], "AURA_DRIVE_CLOUD")

    def test_same_surface_mirror_is_refused(self):
        result = mirror_route_decision(event=event(), target_surface="AURA_DRIVE2_LOCAL")
        self.assertEqual(result["code"], "MIRROR_SAME_SURFACE_FORBIDDEN")

    def test_reflected_mirror_is_suppressed(self):
        original = event()
        fence = ArtifactMirrorFenceV1.mint(
            origin_id=original.origin_id,
            generation=original.generation,
            source_surface=original.source_surface,
            target_surface="AURA_DRIVE_CLOUD",
        )
        reflected = event_for_mirrored_observation(
            original,
            observed_surface="AURA_DRIVE_CLOUD",
            observed_source_ref="drive:file-1",
            fence=fence,
            observed_at="2026-08-30T15:00:05Z",
            provider="GOOGLE_DRIVE",
        )
        result = mirror_route_decision(
            event=reflected,
            target_surface="AURA_DRIVE2_LOCAL",
            inbound_fence=fence,
        )
        self.assertEqual(result["decision"], "SUPPRESSED")
        self.assertEqual(result["code"], "MIRROR_BOUNCE_SUPPRESSED")

    def test_wrong_fence_lineage_is_refused(self):
        original = event()
        alien = ArtifactMirrorFenceV1.mint(
            origin_id="other-origin",
            generation=1,
            source_surface="AURA_DRIVE2_LOCAL",
            target_surface="AURA_DRIVE_CLOUD",
        )
        result = mirror_route_decision(
            event=original,
            target_surface="THIRD_SURFACE",
            inbound_fence=alien,
        )
        self.assertEqual(result["code"], "MIRROR_FENCE_LINEAGE_MISMATCH")

    def test_generation_change_mints_new_fence(self):
        a = ArtifactMirrorFenceV1.mint(
            origin_id="o", generation=1, source_surface="A", target_surface="B"
        )
        b = ArtifactMirrorFenceV1.mint(
            origin_id="o", generation=2, source_surface="A", target_surface="B"
        )
        self.assertNotEqual(a.fence_token, b.fence_token)


class QuiescenceTests(unittest.TestCase):
    def test_no_samples_waits(self):
        self.assertEqual(
            evaluate_quiescence([], min_stable_ns=100)["code"], "NO_OBSERVATIONS"
        )

    def test_partial_write_does_not_ingest(self):
        samples = [
            QuiescenceSampleV1(10, 100, 0),
            QuiescenceSampleV1(20, 200, 200),
        ]
        result = evaluate_quiescence(samples, min_stable_ns=100)
        self.assertEqual(result["decision"], "WAIT")
        self.assertEqual(result["code"], "MUTATION_STILL_ACTIVE")

    def test_stable_window_is_quiescent(self):
        samples = [
            QuiescenceSampleV1(20, 200, 0),
            QuiescenceSampleV1(20, 200, 150),
        ]
        result = evaluate_quiescence(samples, min_stable_ns=100)
        self.assertEqual(result["decision"], "QUIESCENT")
        self.assertEqual(result["code"], "STABLE_WINDOW_OBSERVED")

    def test_stability_window_must_be_long_enough(self):
        samples = [
            QuiescenceSampleV1(20, 200, 0),
            QuiescenceSampleV1(20, 200, 50),
        ]
        self.assertEqual(
            evaluate_quiescence(samples, min_stable_ns=100)["decision"], "WAIT"
        )

    def test_close_evidence_short_circuits_sampling(self):
        samples = [QuiescenceSampleV1(20, 200, 0, close_evidence=True)]
        result = evaluate_quiescence(samples, min_stable_ns=1_000_000)
        self.assertEqual(result["code"], "CLOSE_EVIDENCE")

    def test_atomic_publish_evidence_short_circuits_sampling(self):
        samples = [QuiescenceSampleV1(20, 200, 0, atomic_publish_evidence=True)]
        result = evaluate_quiescence(samples, min_stable_ns=1_000_000)
        self.assertEqual(result["code"], "ATOMIC_PUBLISH_EVIDENCE")

    def test_out_of_order_samples_fail_closed(self):
        samples = [
            QuiescenceSampleV1(20, 200, 100),
            QuiescenceSampleV1(20, 200, 90),
        ]
        with self.assertRaises(ArtifactSyncError) as ctx:
            evaluate_quiescence(samples, min_stable_ns=1)
        self.assertEqual(ctx.exception.code, "QUIESCENCE_OBSERVATION_ORDER_INVALID")


if __name__ == "__main__":
    unittest.main()
