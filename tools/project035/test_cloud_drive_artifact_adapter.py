import hashlib
import unittest

from artifact_sync_core import ArtifactMirrorFenceV1
from cloud_drive_artifact_adapter import (
    ABSENT_REVISION,
    CloudAdapterContextV1,
    CloudAdapterError,
    CloudArtifactEffectAdmissionV1,
    CloudReadbackV1,
    CloudWriteEffectReceiptV1,
    DriveArtifactHydrationV1,
    admission_binding_digest,
    prepare_cloud_publish_plan,
    prepare_effect_handoff,
    translate_custodian_event,
    verify_cloud_write,
)


class Envelope:
    provider = "google"
    source = "drive_changes"
    resource_id = "file-1"
    provider_event_id = "provider-event-1"
    observed_at = "2026-08-30T15:00:00Z"

    @property
    def event_key(self):
        return "google:provider-event-1"


def context(**overrides):
    values = dict(
        durable_intake_ref="custodian-inbox:event-1",
        inbox_state="PROCESSING",
        project_id="CS-PROJ-001",
        work_order_id="CS-ARENA-SYNC-001",
        claim_id="AS-05",
        producer_worker_id="GPT-5.6-SOL-WG-05",
        source_currentness_ref="drive-currentness-1",
        currentness_state="CURRENT",
        origin_id="origin-1",
        generation=3,
    )
    values.update(overrides)
    return CloudAdapterContextV1(**values)


def hydration(**overrides):
    raw = b"artifact-bytes"
    values = dict(
        resource_id="file-1",
        provider_revision="drive-revision-1",
        content_sha256=hashlib.sha256(raw).hexdigest(),
        byte_size=len(raw),
        mime="text/plain",
        extension=".txt",
        mutation_type="MODIFY",
        hydrated_currentness_ref="drive-currentness-1",
    )
    values.update(overrides)
    return DriveArtifactHydrationV1(**values)


def normalized():
    return translate_custodian_event(Envelope(), context=context(), hydration=hydration())


def plan():
    return prepare_cloud_publish_plan(
        normalized(),
        target_surface="AURA_DRIVE_2",
        target_parent_ref="local:/Aura Drive 2",
    )


def admission(item, **overrides):
    values = dict(
        admission_ref="effect-admission:1",
        plan_id=item.plan_id,
        plan_digest=admission_binding_digest(item),
        source_currentness_ref=item.source_currentness_ref,
        effect_class="D0",
        authorized=True,
        cost_ceiling_usd=0.0,
    )
    values.update(overrides)
    return CloudArtifactEffectAdmissionV1(**values)


class CloudDriveArtifactAdapterTests(unittest.TestCase):
    def test_translation_requires_durable_claim_and_preserves_nonexecution(self):
        item = normalized()
        self.assertEqual(item.event.event_type, "MODIFY")
        self.assertIsNotNone(item.identity)
        self.assertFalse(item.execution_authorized)
        self.assertFalse(item.persistence_proven)

    def test_observation_clock_does_not_change_logical_event_identity(self):
        first = normalized()

        class LaterEnvelope(Envelope):
            observed_at = "2026-08-30T15:01:00Z"

        second = translate_custodian_event(
            LaterEnvelope(), context=context(), hydration=hydration()
        )
        self.assertEqual(first.event.event_id, second.event.event_id)

    def test_pending_intake_is_rejected(self):
        with self.assertRaisesRegex(CloudAdapterError, "DURABLE_INTAKE_NOT_CLAIMED"):
            translate_custodian_event(
                Envelope(), context=context(inbox_state="PENDING"), hydration=hydration()
            )

    def test_stale_currentness_rebases_before_hydration_translation(self):
        with self.assertRaisesRegex(CloudAdapterError, "STALE_CURRENTNESS"):
            translate_custodian_event(
                Envelope(), context=context(currentness_state="STALE"), hydration=hydration()
            )

    def test_hydration_currentness_must_match_context(self):
        with self.assertRaisesRegex(CloudAdapterError, "HYDRATION_CURRENTNESS_MISMATCH"):
            translate_custodian_event(
                Envelope(),
                context=context(),
                hydration=hydration(hydrated_currentness_ref="other"),
            )

    def test_delete_requires_prior_lineage(self):
        with self.assertRaisesRegex(CloudAdapterError, "PRIOR_LINEAGE_REQUIRED"):
            hydration(
                mutation_type="DELETE",
                removed=True,
                content_sha256=None,
                byte_size=None,
            ).validate()

    def test_publish_plan_is_coordination_only_and_fenced(self):
        item = plan()
        self.assertFalse(item.execution_authorized)
        self.assertFalse(item.provider_calls_authorized)
        self.assertEqual(item.mirror_fence.origin_id, "origin-1")

    def test_reverse_mirror_bounce_is_suppressed(self):
        item = normalized()
        incoming = ArtifactMirrorFenceV1.mint(
            origin_id="origin-1",
            generation=3,
            source_surface="AURA_DRIVE_2",
            target_surface="GOOGLE_DRIVE",
        )
        with self.assertRaisesRegex(CloudAdapterError, "MIRROR_BOUNCE_SUPPRESSED"):
            prepare_cloud_publish_plan(
                item,
                target_surface="AURA_DRIVE_2",
                target_parent_ref="local:/Aura Drive 2",
                inbound_fence=incoming,
            )

    def test_effect_admission_binds_exact_plan_but_does_not_prove_runtime(self):
        item = plan()
        handoff = prepare_effect_handoff(item, admission(item))
        self.assertTrue(handoff["execution_authorized"])
        self.assertFalse(handoff["runtime_execution_proven"])
        self.assertFalse(handoff["provider_call_started"])

    def test_effect_admission_cannot_widen_zero_provider_cost(self):
        item = plan()
        with self.assertRaisesRegex(CloudAdapterError, "AS05_PROVIDER_COST_MUST_BE_ZERO"):
            prepare_effect_handoff(item, admission(item, cost_ceiling_usd=1.0))

    def test_effect_receipt_must_match_cas_prior_revision(self):
        item = plan()
        auth = admission(item)
        effect = CloudWriteEffectReceiptV1(
            item.plan_id,
            auth.admission_ref,
            "new-file",
            "wrong-prior",
            "drive-revision-2",
            True,
            True,
            "command-receipt:1",
        )
        with self.assertRaisesRegex(CloudAdapterError, "CAS_PRIOR_REVISION_MISMATCH"):
            effect.validate_for(item, auth)

    def test_verified_readback_is_evidence_for_as06_not_as06_completion(self):
        item = plan()
        auth = admission(item)
        effect = CloudWriteEffectReceiptV1(
            item.plan_id,
            auth.admission_ref,
            "new-file",
            ABSENT_REVISION,
            "drive-revision-2",
            True,
            True,
            "command-receipt:1",
        )
        readback = CloudReadbackV1(
            "new-file", "drive-revision-2", item.content_sha256, item.byte_size
        )
        receipt = verify_cloud_write(item, auth, effect, readback)
        self.assertTrue(receipt["execution_proven_for_file_effect"])
        self.assertFalse(receipt["artifact_persistence_receipt_proven"])
        self.assertFalse(receipt["coordinate_owner_bound"])
        self.assertFalse(receipt["workgraph_wake_emitted"])

    def test_landed_hash_mismatch_fails_closed(self):
        item = plan()
        auth = admission(item)
        effect = CloudWriteEffectReceiptV1(
            item.plan_id,
            auth.admission_ref,
            "new-file",
            ABSENT_REVISION,
            "drive-revision-2",
            True,
            True,
            "command-receipt:1",
        )
        readback = CloudReadbackV1("new-file", "drive-revision-2", "0" * 64, item.byte_size)
        with self.assertRaisesRegex(CloudAdapterError, "LANDED_HASH_MISMATCH"):
            verify_cloud_write(item, auth, effect, readback)


if __name__ == "__main__":
    unittest.main()
