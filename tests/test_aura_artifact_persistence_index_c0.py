from dataclasses import asdict
import copy
import unittest

from aura_arena_artifact_event_core import (
    UNKNOWN,
    ArtifactIdentity,
    ArtifactMutationEvent,
    MirrorLineage,
)
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


PAYLOAD_A = b"data"
PAYLOAD_B = b"delta"
IDENTITY_A = ArtifactIdentity.from_bytes(PAYLOAD_A, extension=".txt")
IDENTITY_B = ArtifactIdentity.from_bytes(PAYLOAD_B, extension=".txt")
SID_A = IDENTITY_A.artifact_sid
SID_B = IDENTITY_B.artifact_sid


def canonical_event(
    event_type="MODIFY",
    *,
    generation=1,
    currentness="head:1",
    claim_id=UNKNOWN,
    worker_id=UNKNOWN,
    work_order_id=UNKNOWN,
    prior_artifact_id="",
    prior_resource_ref="",
):
    origin_id = f"origin:{event_type.lower()}:{generation}"
    lineage = MirrorLineage.start(
        origin_id,
        "local:aura-drive-2",
        artifact_generation=generation,
    )
    return ArtifactMutationEvent(
        origin_id=origin_id,
        provider="LOCAL_FS",
        source_surface="local:aura-drive-2",
        event_type=event_type,
        resource_ref="local-root-0://artifact.txt",
        project_id="project:cs",
        producer_worker_id=worker_id,
        claim_id=claim_id,
        work_order_id=work_order_id,
        source_currentness_ref=currentness,
        observed_at="2026-08-30T10:00:00Z",
        generation=generation,
        mirror_fence=lineage.fence,
        prior_artifact_id=prior_artifact_id,
        prior_resource_ref=prior_resource_ref,
    )


def landed(identity=IDENTITY_A, *, version="v1", resource="drive:file:1"):
    return {
        "status": "LANDED_BYTES_VERIFIED",
        "artifact_write_observed": True,
        "persisted_sha256": identity.sha256,
        "byte_size": identity.byte_size,
        "destination_resource_id": resource,
        "destination_version_token": version,
    }


def receipt(
    event=None,
    identity=IDENTITY_A,
    *,
    claim_fence=None,
    observed_at="t1",
    verification=None,
    **overrides,
):
    event = event or canonical_event()
    params = dict(
        event=event.to_dict() if isinstance(event, ArtifactMutationEvent) else event,
        identity=asdict(identity),
        landed_verification=verification or landed(identity),
        persisted_surface="cloud:aura-drive",
        currentness_ref="head:1",
        mirror_fence=(event.mirror_fence if isinstance(event, ArtifactMutationEvent) else event["mirror_fence"]),
        persistence_verification_ref="verify:1",
        claim_fence=claim_fence,
        observed_at=observed_at,
    )
    params.update(overrides)
    return build_persistence_receipt_from_landed_verification(**params)


class ArtifactPersistenceIndexC0Tests(unittest.TestCase):
    def test_01_repaired_as02_unknown_claim_is_preserved_without_fake_fence(self):
        r = receipt()
        self.assertEqual(r.claim_id, UNKNOWN)
        self.assertEqual(r.producer_worker_id, UNKNOWN)
        self.assertEqual(r.work_order_id, UNKNOWN)
        self.assertIsNone(r.claim_fence)

    def test_02_unknown_claim_cannot_be_laundered_into_a_real_claim_fence(self):
        with self.assertRaisesRegex(ArtifactPersistenceError, "CLAIM_FENCE_FOR_UNKNOWN_CLAIM"):
            receipt(claim_fence=3)

    def test_03_known_claim_still_requires_monotonic_fence(self):
        event = canonical_event(claim_id="claim:1", worker_id="worker:1", work_order_id="AS-06")
        with self.assertRaisesRegex(ArtifactPersistenceError, "CLAIM_FENCE_REQUIRED"):
            receipt(event=event)
        r = receipt(event=event, claim_fence=7)
        self.assertEqual(r.claim_fence, 7)

    def test_04_unknown_currentness_rebases_before_persistence(self):
        event = canonical_event(currentness=UNKNOWN)
        with self.assertRaisesRegex(ArtifactPersistenceError, "STALE_CURRENTNESS_REBASE_REQUIRED"):
            build_persistence_receipt_from_landed_verification(
                event=event.to_dict(),
                identity=asdict(IDENTITY_A),
                landed_verification=landed(),
                persisted_surface="cloud:aura-drive",
                currentness_ref=UNKNOWN,
                mirror_fence=event.mirror_fence,
                persistence_verification_ref="verify:unknown",
            )

    def test_05_event_mirror_fence_is_exactly_bound(self):
        event = canonical_event()
        with self.assertRaisesRegex(ArtifactPersistenceError, "MIRROR_FENCE_BINDING_MISMATCH"):
            receipt(event=event, mirror_fence="mf-forged")

    def test_06_event_generation_is_receipted_and_changes_identity(self):
        a = receipt(event=canonical_event(generation=7))
        b = receipt(event=canonical_event(generation=8))
        self.assertEqual(a.event_generation, 7)
        self.assertEqual(b.event_generation, 8)
        self.assertNotEqual(a.receipt_id, b.receipt_id)

    def test_07_repaired_prior_resource_lineage_survives_rename_receipt(self):
        event = canonical_event("RENAME", prior_resource_ref="local-root-0://old.txt")
        r = receipt(event=event)
        self.assertEqual(r.prior_resource_ref, "local-root-0://old.txt")

    def test_08_as06_defensively_rejects_lineage_required_event_without_lineage(self):
        event = canonical_event().to_dict()
        event["event_type"] = "RENAME"
        event["prior_artifact_id"] = ""
        event["prior_resource_ref"] = ""
        with self.assertRaisesRegex(ArtifactPersistenceError, "PRIOR_LINEAGE_REQUIRED"):
            receipt(event=event)

    def test_09_tombstone_binds_source_prior_artifact_sid(self):
        event = canonical_event("TOMBSTONE", prior_artifact_id=SID_A)
        tomb = build_tombstone_receipt(
            event=event.to_dict(),
            artifact_sid=SID_A,
            persisted_surface="cloud:aura-drive",
            resource_ref="drive:file:1",
            currentness_ref="head:1",
            mirror_fence=event.mirror_fence,
            persistence_verification_ref="verify:tombstone",
        )
        self.assertEqual(tomb.prior_artifact_sid, SID_A)
        self.assertEqual(tomb.source_prior_artifact_id, SID_A)

    def test_10_tombstone_rejects_source_artifact_substitution(self):
        event = canonical_event("DELETE", prior_artifact_id=SID_A)
        with self.assertRaisesRegex(ArtifactPersistenceError, "TOMBSTONE_SOURCE_ARTIFACT_MISMATCH"):
            build_tombstone_receipt(
                event=event.to_dict(),
                artifact_sid=SID_B,
                persisted_surface="cloud:aura-drive",
                resource_ref="drive:file:1",
                currentness_ref="head:1",
                mirror_fence=event.mirror_fence,
                persistence_verification_ref="verify:delete",
            )

    def test_11_landed_hash_must_match_identity(self):
        bad = landed(IDENTITY_A)
        bad["persisted_sha256"] = IDENTITY_B.sha256
        with self.assertRaisesRegex(ArtifactPersistenceError, "LANDED_HASH_IDENTITY_MISMATCH"):
            receipt(verification=bad)

    def test_12_receipt_id_is_stable_across_observation_time(self):
        self.assertEqual(receipt(observed_at="t1").receipt_id, receipt(observed_at="t2").receipt_id)

    def test_13_live_index_rejects_unknown_currentness(self):
        with self.assertRaisesRegex(ArtifactPersistenceError, "STALE_CURRENTNESS_REBASE_REQUIRED"):
            new_live_artifact_index(project_id="project:cs", currentness_ref=UNKNOWN)

    def test_14_apply_remains_compare_and_set(self):
        state = new_live_artifact_index(project_id="project:cs", currentness_ref="head:1")
        with self.assertRaisesRegex(ArtifactPersistenceError, "LIVE_INDEX_STALE_CAS"):
            apply_persistence_receipt(state, receipt(), expected_revision="stale")

    def test_15_apply_rejects_currentness_divergence(self):
        state = new_live_artifact_index(project_id="project:cs", currentness_ref="head:2")
        with self.assertRaisesRegex(ArtifactPersistenceError, "STALE_CURRENTNESS_REBASE_REQUIRED"):
            apply_persistence_receipt(state, receipt(), expected_revision=index_revision(state))

    def test_16_identical_receipt_replay_does_not_churn_index(self):
        state = new_live_artifact_index(project_id="project:cs", currentness_ref="head:1")
        state, _ = apply_persistence_receipt(state, receipt(), expected_revision=index_revision(state))
        before = index_revision(state)
        replay, result = apply_persistence_receipt(
            state,
            receipt(observed_at="later"),
            expected_revision=before,
        )
        self.assertEqual(result["decision"], "IDEMPOTENT_REPLAY")
        self.assertEqual(index_revision(replay), before)

    def test_17_same_resource_new_content_preserves_history_and_supersedes_old(self):
        state = new_live_artifact_index(project_id="project:cs", currentness_ref="head:1")
        first = receipt()
        state, _ = apply_persistence_receipt(state, first, expected_revision=index_revision(state))
        event2 = canonical_event(generation=2)
        second = receipt(
            event=event2,
            identity=IDENTITY_B,
            verification=landed(IDENTITY_B, version="v2"),
            persistence_verification_ref="verify:2",
        )
        state, _ = apply_persistence_receipt(state, second, expected_revision=index_revision(state))
        key = "cloud:aura-drive::drive:file:1"
        self.assertEqual(state["resource_heads"][key], SID_B)
        self.assertEqual(state["artifacts"][SID_A]["locations"][key]["state"], "SUPERSEDED")
        self.assertEqual(len(state["receipts"]), 2)

    def test_18_tombstone_removes_head_but_preserves_history(self):
        state = new_live_artifact_index(project_id="project:cs", currentness_ref="head:1")
        first = receipt()
        state, _ = apply_persistence_receipt(state, first, expected_revision=index_revision(state))
        event = canonical_event("TOMBSTONE", generation=2, prior_artifact_id=SID_A)
        tomb = build_tombstone_receipt(
            event=event.to_dict(),
            artifact_sid=SID_A,
            persisted_surface="cloud:aura-drive",
            resource_ref="drive:file:1",
            currentness_ref="head:1",
            mirror_fence=event.mirror_fence,
            persistence_verification_ref="verify:tomb",
        )
        state, _ = apply_persistence_receipt(state, tomb, expected_revision=index_revision(state))
        self.assertNotIn("cloud:aura-drive::drive:file:1", state["resource_heads"])
        self.assertEqual(state["artifacts"][SID_A]["state"], "TOMBSTONED")
        self.assertEqual(len(state["artifacts"][SID_A]["history_receipt_ids"]), 2)

    def test_19_availability_event_keeps_as07_zero_authority_abi(self):
        state = new_live_artifact_index(project_id="project:cs", currentness_ref="head:1")
        r = receipt()
        state, _ = apply_persistence_receipt(state, r, expected_revision=index_revision(state))
        event = artifact_available_event(r, live_index_revision=index_revision(state))
        self.assertEqual(event["schema"], "ArtifactAvailableEventV1")
        self.assertEqual(event["event_type"], "ARTIFACT_AVAILABLE")
        self.assertTrue(event["delivery_intent_only"])
        self.assertFalse(event["execution_authorized"])
        self.assertFalse(event["effect_authorized"])
        self.assertFalse(event["provider_calls_authorized"])
        self.assertFalse(event["runtime_execution_proven"])
        self.assertFalse(event["background_execution_claimed"])
        self.assertEqual(event["source_event_generation"], r.event_generation)
        self.assertEqual(event["mirror_fence"], r.mirror_fence)

    def test_20_bound_owner_or_coordinate_requires_exact_ref(self):
        with self.assertRaisesRegex(ArtifactPersistenceError, "BOUND_OWNER_REF_REQUIRED"):
            receipt(owner_binding_status="BOUND")
        with self.assertRaisesRegex(ArtifactPersistenceError, "BOUND_COORDINATE_REF_REQUIRED"):
            receipt(coordinate_binding_status="BOUND")

    def test_21_authority_cannot_be_laundered_into_receipt(self):
        with self.assertRaisesRegex(ArtifactPersistenceError, "AUTHORITY_WIDENING"):
            ArtifactPersistenceReceipt(
                event_id="evt:1",
                artifact_sid=SID_A,
                project_id="project:cs",
                source_surface="local",
                persisted_surface="cloud",
                resource_ref="drive:file:1",
                currentness_ref="head:1",
                mirror_fence="mf:1",
                persistence_verification_ref="verify:1",
                owner_binding_status=UNKNOWN,
                coordinate_binding_status=UNKNOWN,
                sha256=IDENTITY_A.sha256,
                byte_size=IDENTITY_A.byte_size,
                provider_version="v1",
                effect_authorized=True,
            )

    def test_22_observation_metadata_alone_does_not_churn_index_revision(self):
        state = new_live_artifact_index(project_id="project:cs", currentness_ref="head:1")
        state, _ = apply_persistence_receipt(state, receipt(observed_at="t1"), expected_revision=index_revision(state))
        variant = copy.deepcopy(state)
        rid = next(iter(variant["receipts"]))
        variant["receipts"][rid]["observed_at"] = "t2"
        self.assertEqual(index_revision(state), index_revision(variant))


if __name__ == "__main__":
    unittest.main()
