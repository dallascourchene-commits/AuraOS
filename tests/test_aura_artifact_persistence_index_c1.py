from dataclasses import asdict
import copy
import unittest

from aura_artifact_persistence_index import (
    ArtifactPersistenceError,
    apply_persistence_receipt,
    artifact_available_event,
    build_tombstone_receipt,
    index_revision,
    new_live_artifact_index,
)
from tests.test_aura_artifact_persistence_index_c0 import (
    IDENTITY_A,
    IDENTITY_B,
    SID_A,
    SID_B,
    canonical_event,
    landed,
    receipt,
)


LOCATION = "cloud:aura-drive::drive:file:1"


def apply(state, item):
    return apply_persistence_receipt(
        state,
        item,
        expected_revision=index_revision(state),
    )


def upsert(generation, identity=IDENTITY_A, *, resource="drive:file:1", version=None):
    event = canonical_event(generation=generation)
    return receipt(
        event=event,
        identity=identity,
        verification=landed(
            identity,
            version=version or f"v{generation}",
            resource=resource,
        ),
        persistence_verification_ref=f"verify:{resource}:{generation}:{identity.sha256[:8]}",
    )


def tombstone(generation, sid=SID_A, *, resource="drive:file:1"):
    event = canonical_event(
        "TOMBSTONE",
        generation=generation,
        prior_artifact_id=sid,
        prior_resource_ref=resource,
    )
    return build_tombstone_receipt(
        event=event.to_dict(),
        artifact_sid=sid,
        persisted_surface="cloud:aura-drive",
        resource_ref=resource,
        currentness_ref="head:1",
        mirror_fence=event.mirror_fence,
        persistence_verification_ref=f"verify:tomb:{resource}:{generation}",
    )


class ArtifactPersistenceIndexC1GenerationTests(unittest.TestCase):
    def test_01_gen1_gen3_delayed_gen2_cannot_roll_back_resource_head(self):
        state = new_live_artifact_index(project_id="project:cs", currentness_ref="head:1")
        state, _ = apply(state, upsert(1, IDENTITY_A))
        state, _ = apply(state, upsert(3, IDENTITY_B))
        before = index_revision(state)
        with self.assertRaisesRegex(ArtifactPersistenceError, "RESOURCE_GENERATION_STALE"):
            apply(state, upsert(2, IDENTITY_A))
        self.assertEqual(index_revision(state), before)
        self.assertEqual(state["resource_heads"][LOCATION], SID_B)
        self.assertEqual(state["resource_generations"][LOCATION], 3)

    def test_02_delayed_tombstone_cannot_remove_newer_head(self):
        state = new_live_artifact_index(project_id="project:cs", currentness_ref="head:1")
        state, _ = apply(state, upsert(1, IDENTITY_A))
        state, _ = apply(state, upsert(3, IDENTITY_B))
        before = copy.deepcopy(state)
        with self.assertRaisesRegex(ArtifactPersistenceError, "RESOURCE_GENERATION_STALE"):
            apply(state, tombstone(2, SID_B))
        self.assertEqual(state, before)
        self.assertEqual(state["resource_heads"][LOCATION], SID_B)

    def test_03_equal_generation_conflicting_consequence_fails_closed(self):
        state = new_live_artifact_index(project_id="project:cs", currentness_ref="head:1")
        state, _ = apply(state, upsert(4, IDENTITY_A))
        with self.assertRaisesRegex(ArtifactPersistenceError, "RESOURCE_GENERATION_CONFLICT"):
            apply(state, upsert(4, IDENTITY_B, version="v4b"))
        self.assertEqual(state["resource_heads"][LOCATION], SID_A)

    def test_04_exact_duplicate_receipt_remains_idempotent(self):
        state = new_live_artifact_index(project_id="project:cs", currentness_ref="head:1")
        r = upsert(5, IDENTITY_A)
        state, _ = apply(state, r)
        before = index_revision(state)
        replay, result = apply(state, r)
        self.assertEqual(result["decision"], "IDEMPOTENT_REPLAY")
        self.assertFalse(result["state_changed"])
        self.assertEqual(index_revision(replay), before)

    def test_05_generation_fence_is_scoped_per_persisted_resource(self):
        state = new_live_artifact_index(project_id="project:cs", currentness_ref="head:1")
        state, _ = apply(state, upsert(9, IDENTITY_A, resource="drive:file:1"))
        state, _ = apply(state, upsert(1, IDENTITY_B, resource="drive:file:2"))
        self.assertEqual(state["resource_generations"]["cloud:aura-drive::drive:file:1"], 9)
        self.assertEqual(state["resource_generations"]["cloud:aura-drive::drive:file:2"], 1)

    def test_06_tombstone_preserves_generation_fence_against_stale_resurrection(self):
        state = new_live_artifact_index(project_id="project:cs", currentness_ref="head:1")
        state, _ = apply(state, upsert(1, IDENTITY_A))
        state, _ = apply(state, tombstone(2, SID_A))
        self.assertNotIn(LOCATION, state["resource_heads"])
        self.assertEqual(state["resource_generations"][LOCATION], 2)
        with self.assertRaisesRegex(ArtifactPersistenceError, "RESOURCE_GENERATION_STALE"):
            apply(state, upsert(1, IDENTITY_A, version="late-v1"))
        with self.assertRaisesRegex(ArtifactPersistenceError, "RESOURCE_GENERATION_CONFLICT"):
            apply(state, upsert(2, IDENTITY_A, version="same-v2"))

    def test_07_strictly_newer_generation_can_resurrect_after_tombstone(self):
        state = new_live_artifact_index(project_id="project:cs", currentness_ref="head:1")
        state, _ = apply(state, upsert(1, IDENTITY_A))
        state, _ = apply(state, tombstone(2, SID_A))
        state, result = apply(state, upsert(3, IDENTITY_B))
        self.assertEqual(result["resource_generation"], 3)
        self.assertEqual(state["resource_heads"][LOCATION], SID_B)
        self.assertEqual(state["resource_generations"][LOCATION], 3)

    def test_08_legacy_c0_index_derives_generation_fence_from_receipts(self):
        state = new_live_artifact_index(project_id="project:cs", currentness_ref="head:1")
        state, _ = apply(state, upsert(3, IDENTITY_A))
        legacy = copy.deepcopy(state)
        legacy.pop("resource_generations")
        migrated_revision = index_revision(legacy)
        migrated, _ = apply_persistence_receipt(
            legacy,
            upsert(4, IDENTITY_B),
            expected_revision=migrated_revision,
        )
        self.assertEqual(migrated["resource_generations"][LOCATION], 4)
        self.assertEqual(migrated["resource_heads"][LOCATION], SID_B)

    def test_09_legacy_index_without_generation_evidence_fails_closed(self):
        state = new_live_artifact_index(project_id="project:cs", currentness_ref="head:1")
        state, _ = apply(state, upsert(1, IDENTITY_A))
        legacy = copy.deepcopy(state)
        legacy.pop("resource_generations")
        rid = next(iter(legacy["receipts"]))
        legacy["receipts"][rid].pop("event_generation")
        with self.assertRaisesRegex(
            ArtifactPersistenceError,
            "LIVE_INDEX_RESOURCE_GENERATION_MIGRATION_REQUIRED",
        ):
            index_revision(legacy)

    def test_10_resource_generation_map_is_revision_bearing(self):
        state = new_live_artifact_index(project_id="project:cs", currentness_ref="head:1")
        state, _ = apply(state, upsert(2, IDENTITY_A))
        variant = copy.deepcopy(state)
        variant["resource_generations"][LOCATION] = 3
        self.assertNotEqual(index_revision(state), index_revision(variant))

    def test_11_availability_event_remains_zero_authority_after_ordered_apply(self):
        state = new_live_artifact_index(project_id="project:cs", currentness_ref="head:1")
        r = upsert(7, IDENTITY_A)
        state, _ = apply(state, r)
        event = artifact_available_event(r, live_index_revision=index_revision(state))
        self.assertEqual(event["source_event_generation"], 7)
        self.assertTrue(event["delivery_intent_only"])
        self.assertFalse(event["execution_authorized"])
        self.assertFalse(event["effect_authorized"])
        self.assertFalse(event["provider_calls_authorized"])
        self.assertFalse(event["runtime_execution_proven"])
        self.assertFalse(event["background_execution_claimed"])


if __name__ == "__main__":
    unittest.main()
