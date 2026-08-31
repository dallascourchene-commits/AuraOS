from pathlib import Path
import hashlib
import sys
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import k27_phase_mask_artifact_contract as phase


PARENTS = (
    "1l8FLO6a0ebJX1D4L2VP5PThii4P_vcGGrGMxBHYy_Ew",
    "github:pr599@afa99994532b20ce9d945f3873461eca80e50ccc",
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


PAYLOAD = b"phase-mask-fixture-v1"


def artifact(**overrides):
    values = dict(
        scene_source_sha256=sha(b"scene-v1"),
        optical_model_generation="asm-bandlimited-v1",
        phase_encoding_generation="fp16-phase-v1",
        wavelength_nm=532,
        width_px=512,
        height_px=512,
        dtype="float16",
        payload_sha256=sha(PAYLOAD),
        payload_bytes=len(PAYLOAD),
    )
    values.update(overrides)
    return phase.PhaseMaskArtifactIdentity(**values)


def plan(**overrides):
    values = dict(
        storage_object_id="phase-mask-store-A",
        storage_generation="store-gen-9",
        storage_plan_digest=sha(b"residency-plan"),
        planned_backend="MMAP_DEMAND",
        byte_offset=4096,
        aligned_extent_bytes=4096,
    )
    values.update(overrides)
    return phase.PlannedMaterialization(**values)


def observation(**overrides):
    values = dict(
        storage_object_id="phase-mask-store-A",
        storage_generation="store-gen-9",
        observed_byte_offset=4096,
        observed_payload_sha256=sha(PAYLOAD),
        observed_payload_bytes=len(PAYLOAD),
    )
    values.update(overrides)
    return phase.RetrievalObservation(**values)


class PhaseMaskArtifactContractTests(unittest.TestCase):
    def test_exact_retrieval_admits_semantic_reuse_only(self):
        a = artifact()
        p = plan()
        h = phase.make_handle(k27_coordinate=13, artifact=a, plan=p)
        gate = phase.validate_retrieval(handle=h, artifact=a, plan=p, observation=observation())
        self.assertTrue(gate.admissible_for_semantic_reuse)
        self.assertFalse(gate.planned_backend_observed)
        self.assertFalse(gate.physical_io_attested)
        self.assertFalse(gate.optical_effect_authority)

    def test_same_coordinate_wrong_payload_rejects(self):
        a = artifact()
        p = plan()
        h = phase.make_handle(k27_coordinate=13, artifact=a, plan=p)
        gate = phase.validate_retrieval(
            handle=h, artifact=a, plan=p,
            observation=observation(observed_payload_sha256=sha(b"other-mask")),
        )
        self.assertFalse(gate.payload_exact)
        self.assertFalse(gate.admissible_for_semantic_reuse)

    def test_reused_offset_new_storage_generation_rejects_aba(self):
        a = artifact()
        p = plan()
        h = phase.make_handle(k27_coordinate=13, artifact=a, plan=p)
        gate = phase.validate_retrieval(
            handle=h, artifact=a, plan=p,
            observation=observation(storage_generation="store-gen-10"),
        )
        self.assertFalse(gate.materialization_generation_exact)
        self.assertFalse(gate.admissible_for_semantic_reuse)

    def test_scene_generation_change_changes_artifact_identity(self):
        a = artifact()
        p = plan()
        h = phase.make_handle(k27_coordinate=13, artifact=a, plan=p)
        changed = artifact(scene_source_sha256=sha(b"scene-v2"))
        gate = phase.validate_retrieval(handle=h, artifact=changed, plan=p, observation=observation())
        self.assertFalse(gate.artifact_exact)
        self.assertFalse(gate.admissible_for_semantic_reuse)

    def test_optical_model_generation_change_changes_artifact_identity(self):
        a = artifact()
        p = plan()
        h = phase.make_handle(k27_coordinate=13, artifact=a, plan=p)
        changed = artifact(optical_model_generation="asm-bandlimited-v2")
        gate = phase.validate_retrieval(handle=h, artifact=changed, plan=p, observation=observation())
        self.assertFalse(gate.artifact_exact)

    def test_storage_plan_change_rebinds_materialization(self):
        a = artifact()
        p = plan()
        h = phase.make_handle(k27_coordinate=13, artifact=a, plan=p)
        changed = plan(storage_plan_digest=sha(b"new-plan"))
        gate = phase.validate_retrieval(handle=h, artifact=a, plan=changed, observation=observation())
        self.assertFalse(gate.materialization_generation_exact)
        self.assertFalse(gate.admissible_for_semantic_reuse)

    def test_coordinate_is_not_identity(self):
        a = artifact()
        p = plan()
        h13 = phase.make_handle(k27_coordinate=13, artifact=a, plan=p)
        h14 = phase.make_handle(k27_coordinate=14, artifact=a, plan=p)
        self.assertNotEqual(h13.k27_coordinate, h14.k27_coordinate)
        self.assertEqual(h13.artifact_identity_digest, h14.artifact_identity_digest)

    def test_receipt_is_two_parent_tamper_evident_and_nonauthorizing(self):
        a = artifact()
        p = plan()
        h = phase.make_handle(k27_coordinate=13, artifact=a, plan=p)
        gate = phase.validate_retrieval(handle=h, artifact=a, plan=p, observation=observation())
        receipt = phase.build_phase_mask_receipt(
            handle=h, artifact=a, plan=p, gate=gate, parent_artifact_ids=PARENTS
        )
        self.assertTrue(phase.verify_phase_mask_receipt(receipt))
        self.assertTrue(all(v is False for v in receipt["claim_ceiling"].values()))
        tampered = dict(receipt)
        tampered["k27_scheme"] = "authority-by-coordinate"
        self.assertFalse(phase.verify_phase_mask_receipt(tampered))

    def test_exactly_two_distinct_parent_artifacts_required(self):
        a = artifact()
        p = plan()
        h = phase.make_handle(k27_coordinate=13, artifact=a, plan=p)
        gate = phase.validate_retrieval(handle=h, artifact=a, plan=p, observation=observation())
        with self.assertRaises(ValueError):
            phase.build_phase_mask_receipt(
                handle=h, artifact=a, plan=p, gate=gate,
                parent_artifact_ids=(PARENTS[0], PARENTS[0]),
            )


if __name__ == "__main__":
    unittest.main()
