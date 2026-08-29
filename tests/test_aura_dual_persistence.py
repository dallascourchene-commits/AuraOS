import unittest

from core.aura_dual_persistence import (
    ArtifactReplicaRecord,
    Replica,
    SyncState,
    can_dispatch_work,
    currentness_token,
    native_cloud_digest,
    reconcile,
)


def replica(exists=True, digest="A", generation=3, revision="r"):
    return Replica(exists, digest, revision, generation)


class AuraDualPersistenceTests(unittest.TestCase):
    def record(self, local=replica(), cloud=replica(), base="A", generation=3):
        return ArtifactReplicaRecord(
            "SID", "OWNER", generation, base, local, cloud
        )

    def test_synced_is_dispatchable(self):
        self.assertEqual(reconcile(self.record()).state, SyncState.SYNCED)
        self.assertTrue(can_dispatch_work(self.record()))

    def test_local_only_materializes_cloud(self):
        plan = reconcile(self.record(cloud=Replica(False)))
        self.assertEqual(plan.state, SyncState.LOCAL_ONLY)
        self.assertIn("CREATE_CLOUD_REPLICA", plan.actions)

    def test_cloud_only_materializes_local(self):
        plan = reconcile(self.record(local=Replica(False)))
        self.assertEqual(plan.state, SyncState.CLOUD_ONLY)
        self.assertIn("CREATE_LOCAL_REPLICA", plan.actions)

    def test_local_ahead_is_one_sided_safe_update(self):
        plan = reconcile(
            self.record(local=replica(digest="B"), cloud=replica(digest="A"))
        )
        self.assertEqual(plan.state, SyncState.LOCAL_AHEAD)
        self.assertTrue(plan.may_overwrite)

    def test_cloud_ahead_is_one_sided_safe_update(self):
        plan = reconcile(
            self.record(local=replica(digest="A"), cloud=replica(digest="B"))
        )
        self.assertEqual(plan.state, SyncState.CLOUD_AHEAD)
        self.assertTrue(plan.may_overwrite)

    def test_two_sided_divergence_fails_closed(self):
        plan = reconcile(
            self.record(local=replica(digest="B"), cloud=replica(digest="C"))
        )
        self.assertEqual(plan.state, SyncState.CONFLICT)
        self.assertFalse(plan.may_overwrite)
        self.assertTrue(plan.requires_review)
        self.assertIn("PRESERVE_BOTH", plan.actions)

    def test_divergence_without_base_fails_closed(self):
        plan = reconcile(
            self.record(
                local=replica(digest="B"), cloud=replica(digest="C"), base=None
            )
        )
        self.assertEqual(plan.state, SyncState.CONFLICT)

    def test_generation_mismatch_blocks_dispatch(self):
        record = self.record(local=replica(generation=2))
        self.assertEqual(reconcile(record).state, SyncState.STALE_GENERATION)
        self.assertFalse(can_dispatch_work(record))

    def test_missing_digest_is_invalid(self):
        plan = reconcile(
            self.record(local=Replica(True, None, "r", 3))
        )
        self.assertEqual(plan.state, SyncState.INVALID)

    def test_currentness_token_requires_synced_pair(self):
        self.assertEqual(currentness_token(self.record()), "SID:g3:A")
        with self.assertRaises(ValueError):
            currentness_token(self.record(local=replica(digest="B")))

    def test_native_google_object_uses_canonical_export_digest(self):
        self.assertEqual(native_cloud_digest("X"), "X")
        with self.assertRaises(ValueError):
            native_cloud_digest("")


if __name__ == "__main__":
    unittest.main()
