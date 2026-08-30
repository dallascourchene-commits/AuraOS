import copy
import unittest

from aura_artifact_persistence_index import (
    ArtifactPersistenceError,
    ArtifactPersistenceReceipt,
    apply_persistence_receipt,
    artifact_available_event,
    build_persistence_receipt_from_landed_verification,
    build_tombstone_receipt,
    index_revision,
    new_live_artifact_index,
)

SHA_A = "a" * 64
SHA_B = "b" * 64
SID_A = "artifact-sha256-" + SHA_A
SID_B = "artifact-sha256-" + SHA_B


def event(event_type="MODIFY", *, currentness="head:1", claim_id="claim:1"):
    return {
        "schema": "ArtifactMutationEventV1",
        "event_id": f"evt:{event_type.lower()}",
        "project_id": "project:cs",
        "source_surface": "local:aura-drive-2",
        "event_type": event_type,
        "source_currentness_ref": currentness,
        "producer_worker_id": "worker:a",
        "claim_id": claim_id,
        "work_order_id": "AS-06",
    }


def identity(sha=SHA_A, size=4):
    return {
        "schema": "ArtifactIdentityV1",
        "sha256": sha,
        "byte_size": size,
        "artifact_sid": "artifact-sha256-" + sha,
    }


def landed(sha=SHA_A, size=4, resource="drive:file:1", version="v1"):
    return {
        "status": "LANDED_BYTES_VERIFIED",
        "artifact_write_observed": True,
        "persisted_sha256": sha,
        "byte_size": size,
        "destination_resource_id": resource,
        "destination_version_token": version,
    }


def receipt_a(**overrides):
    params = dict(
        event=event(),
        identity=identity(),
        landed_verification=landed(),
        persisted_surface="cloud:aura-drive",
        currentness_ref="head:1",
        mirror_fence="mf:1",
        persistence_verification_ref="verify:cloud:1",
        claim_fence=7,
        observed_at="2026-08-30T10:00:00Z",
    )
    params.update(overrides)
    return build_persistence_receipt_from_landed_verification(**params)


class ArtifactPersistenceIndexTests(unittest.TestCase):
    def test_01_receipt_id_is_replay_stable_across_observation_time(self):
        a = receipt_a(observed_at="t1")
        b = receipt_a(observed_at="t2")
        self.assertEqual(a.receipt_id, b.receipt_id)

    def test_02_landed_hash_must_match_artifact_identity(self):
        with self.assertRaisesRegex(ArtifactPersistenceError, "LANDED_HASH_IDENTITY_MISMATCH"):
            receipt_a(landed_verification=landed(sha=SHA_B))

    def test_03_verified_landed_write_is_required(self):
        bad = landed()
        bad["status"] = "UNVERIFIED"
        with self.assertRaisesRegex(ArtifactPersistenceError, "LANDED_BYTES_VERIFICATION_REQUIRED"):
            receipt_a(landed_verification=bad)

    def test_04_claim_id_requires_monotonic_fence_operand(self):
        with self.assertRaisesRegex(ArtifactPersistenceError, "CLAIM_FENCE_REQUIRED"):
            receipt_a(claim_fence=None)

    def test_05_effect_authority_cannot_be_laundered_into_receipt(self):
        with self.assertRaisesRegex(ArtifactPersistenceError, "AUTHORITY_WIDENING"):
            ArtifactPersistenceReceipt(
                event_id="e",
                artifact_sid=SID_A,
                project_id="p",
                source_surface="s",
                persisted_surface="d",
                resource_ref="r",
                currentness_ref="h",
                mirror_fence="mf",
                persistence_verification_ref="v",
                owner_binding_status="UNKNOWN",
                coordinate_binding_status="UNKNOWN",
                sha256=SHA_A,
                byte_size=4,
                provider_version="v1",
                effect_authorized=True,
            )

    def test_06_pending_external_owner_and_coordinate_are_explicit_and_allowed(self):
        r = receipt_a()
        self.assertEqual(r.owner_binding_status, "PENDING_EXTERNAL_OWNER")
        self.assertEqual(r.coordinate_binding_status, "PENDING_EXTERNAL_OWNER")
        self.assertFalse(r.semantic_authority)
        self.assertFalse(r.coordinate_authority)

    def test_07_apply_requires_currentness_match(self):
        state = new_live_artifact_index(project_id="project:cs", currentness_ref="head:2")
        with self.assertRaisesRegex(ArtifactPersistenceError, "STALE_CURRENTNESS_REBASE_REQUIRED"):
            apply_persistence_receipt(state, receipt_a(), expected_revision=index_revision(state))

    def test_08_apply_is_compare_and_set(self):
        state = new_live_artifact_index(project_id="project:cs", currentness_ref="head:1")
        with self.assertRaisesRegex(ArtifactPersistenceError, "LIVE_INDEX_STALE_CAS"):
            apply_persistence_receipt(state, receipt_a(), expected_revision="stale")

    def test_09_replay_is_idempotent_and_does_not_change_revision(self):
        state = new_live_artifact_index(project_id="project:cs", currentness_ref="head:1")
        first, _ = apply_persistence_receipt(
            state, receipt_a(), expected_revision=index_revision(state)
        )
        before = index_revision(first)
        replay, replay_result = apply_persistence_receipt(
            first,
            receipt_a(observed_at="later"),
            expected_revision=before,
        )
        self.assertEqual(replay_result["decision"], "IDEMPOTENT_REPLAY")
        self.assertEqual(index_revision(replay), before)
        self.assertEqual(replay["generation"], 1)

    def test_10_append_only_receipt_history_survives_same_resource_new_content(self):
        state = new_live_artifact_index(project_id="project:cs", currentness_ref="head:1")
        r1 = receipt_a()
        state, _ = apply_persistence_receipt(state, r1, expected_revision=index_revision(state))
        r2 = receipt_a(
            event={**event(), "event_id": "evt:modify:2"},
            identity=identity(SHA_B, 5),
            landed_verification=landed(SHA_B, 5, version="v2"),
            persistence_verification_ref="verify:cloud:2",
        )
        state, _ = apply_persistence_receipt(state, r2, expected_revision=index_revision(state))
        self.assertEqual(len(state["receipts"]), 2)
        self.assertIn(SID_A, state["artifacts"])
        self.assertIn(SID_B, state["artifacts"])
        key = "cloud:aura-drive::drive:file:1"
        self.assertEqual(state["resource_heads"][key], SID_B)
        self.assertEqual(state["artifacts"][SID_A]["locations"][key]["state"], "SUPERSEDED")

    def test_11_tombstone_removes_live_head_but_preserves_history(self):
        state = new_live_artifact_index(project_id="project:cs", currentness_ref="head:1")
        r1 = receipt_a()
        state, _ = apply_persistence_receipt(state, r1, expected_revision=index_revision(state))
        tomb = build_tombstone_receipt(
            event=event("TOMBSTONE"),
            artifact_sid=SID_A,
            persisted_surface="cloud:aura-drive",
            resource_ref="drive:file:1",
            currentness_ref="head:1",
            mirror_fence="mf:2",
            persistence_verification_ref="verify:tombstone:1",
            claim_fence=8,
        )
        state, _ = apply_persistence_receipt(state, tomb, expected_revision=index_revision(state))
        self.assertEqual(len(state["receipts"]), 2)
        self.assertNotIn("cloud:aura-drive::drive:file:1", state["resource_heads"])
        self.assertEqual(state["artifacts"][SID_A]["state"], "TOMBSTONED")
        self.assertEqual(len(state["artifacts"][SID_A]["history_receipt_ids"]), 2)

    def test_12_tombstone_never_claims_new_bytes(self):
        with self.assertRaisesRegex(ArtifactPersistenceError, "TOMBSTONE_MUST_NOT_CLAIM_BYTES"):
            ArtifactPersistenceReceipt(
                event_id="e",
                artifact_sid=SID_A,
                project_id="p",
                source_surface="s",
                persisted_surface="d",
                resource_ref="r",
                currentness_ref="h",
                mirror_fence="mf",
                persistence_verification_ref="v",
                owner_binding_status="UNKNOWN",
                coordinate_binding_status="UNKNOWN",
                operation="TOMBSTONE",
                prior_artifact_sid=SID_A,
                sha256=SHA_A,
                byte_size=4,
            )

    def test_13_observation_metadata_alone_does_not_churn_logical_index_revision(self):
        state = new_live_artifact_index(project_id="project:cs", currentness_ref="head:1")
        state, _ = apply_persistence_receipt(
            state, receipt_a(observed_at="t1"), expected_revision=index_revision(state)
        )
        variant = copy.deepcopy(state)
        rid = next(iter(variant["receipts"]))
        variant["receipts"][rid]["observed_at"] = "t2"
        self.assertEqual(index_revision(state), index_revision(variant))

    def test_14_artifact_available_is_coordination_only(self):
        state = new_live_artifact_index(project_id="project:cs", currentness_ref="head:1")
        r = receipt_a()
        state, _ = apply_persistence_receipt(state, r, expected_revision=index_revision(state))
        out = artifact_available_event(r, live_index_revision=index_revision(state))
        self.assertEqual(out["event_type"], "ARTIFACT_AVAILABLE")
        self.assertTrue(out["delivery_intent_only"])
        self.assertFalse(out["execution_authorized"])
        self.assertFalse(out["effect_authorized"])
        self.assertFalse(out["runtime_execution_proven"])

    def test_15_tombstone_event_is_typed_and_not_execution(self):
        tomb = build_tombstone_receipt(
            event=event("DELETE"),
            artifact_sid=SID_A,
            persisted_surface="cloud:aura-drive",
            resource_ref="drive:file:1",
            currentness_ref="head:1",
            mirror_fence="mf:3",
            persistence_verification_ref="verify:delete",
            claim_fence=9,
        )
        out = artifact_available_event(tomb, live_index_revision="idx:1")
        self.assertEqual(out["event_type"], "ARTIFACT_TOMBSTONED")
        self.assertFalse(out["background_execution_claimed"])

    def test_16_bound_owner_or_coordinate_requires_exact_ref(self):
        with self.assertRaisesRegex(ArtifactPersistenceError, "BOUND_OWNER_REF_REQUIRED"):
            receipt_a(owner_binding_status="BOUND")
        with self.assertRaisesRegex(ArtifactPersistenceError, "BOUND_COORDINATE_REF_REQUIRED"):
            receipt_a(coordinate_binding_status="BOUND")

    def test_17_artifact_sid_is_hash_bound(self):
        with self.assertRaisesRegex(ArtifactPersistenceError, "ARTIFACT_SID_HASH_BINDING_MISMATCH"):
            ArtifactPersistenceReceipt(
                event_id="e",
                artifact_sid=SID_B,
                project_id="p",
                source_surface="s",
                persisted_surface="d",
                resource_ref="r",
                currentness_ref="h",
                mirror_fence="mf",
                persistence_verification_ref="v",
                owner_binding_status="UNKNOWN",
                coordinate_binding_status="UNKNOWN",
                sha256=SHA_A,
                byte_size=4,
                provider_version="v1",
            )

    def test_18_index_projection_itself_has_no_semantic_or_effect_authority(self):
        state = new_live_artifact_index(project_id="project:cs", currentness_ref="head:1")
        self.assertFalse(state["semantic_authority"])
        self.assertFalse(state["coordinate_authority"])
        self.assertFalse(state["effect_authorized"])
        self.assertFalse(state["runtime_execution_proven"])


if __name__ == "__main__":
    unittest.main()
