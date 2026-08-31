from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from tools.awj032.glm53_owner_host_c2_handoff import OwnerHostC2CanaryRequest
from tools.awj032.thinkpad_bounded_storage_probe import (
    ThinkPadStorageProbeError,
    run_bounded_storage_probe,
)


class ThinkPadBoundedStorageProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.payload = (b"aura-thinkpad-probe\n" * 8192) + b"tail"
        (self.root / "model.safetensors").write_bytes(self.payload)
        self.request = OwnerHostC2CanaryRequest(
            w3_proof_logical_id="fixture:w3",
            preflight_receipt_digest="1" * 64,
            airllm_source_revision="fixture-airllm-revision",
            airllm_security_evidence_digest="2" * 64,
            host_snapshot_digest="3" * 64,
            storage_plan_digest="4" * 64,
            workspace_root=str(self.root),
            max_payload_bytes=2 * 1024 * 1024,
            max_wall_seconds=10,
            effect_admission_ref="effect:none",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def probe(self, **updates):
        values = dict(
            request=self.request,
            relative_path="model.safetensors",
            byte_offset=0,
            probe_bytes=len(self.payload),
            chunk_bytes=4096,
            max_wall_seconds=2.0,
        )
        values.update(updates)
        return run_bounded_storage_probe(**values)

    def test_reads_exact_bounded_window_and_preserves_file(self):
        before = (self.root / "model.safetensors").read_bytes()
        receipt = self.probe()
        after = (self.root / "model.safetensors").read_bytes()
        self.assertEqual(before, after)
        self.assertEqual(receipt.logical_bytes_read, len(self.payload))
        self.assertEqual(receipt.window_sha256, hashlib.sha256(self.payload).hexdigest())
        self.assertGreater(receipt.read_operations, 0)
        self.assertGreater(receipt.observed_logical_read_bytes_per_second, 0)

    def test_probe_remains_below_physical_io_and_authority(self):
        receipt = self.probe()
        self.assertFalse(receipt.page_cache_bypass_proven)
        self.assertFalse(receipt.physical_nvme_io_attested)
        self.assertFalse(receipt.storage_medium_nvme_proven)
        self.assertFalse(receipt.producer_authenticated)
        self.assertFalse(receipt.model_execution_observed)
        self.assertFalse(receipt.lifecycle_measurement_admitted)
        self.assertFalse(receipt.effect_authority_proven)
        self.assertFalse(receipt.g2_admitted)

    def test_path_traversal_is_rejected(self):
        with self.assertRaisesRegex(ThinkPadStorageProbeError, "TARGET_PATH_NOT_BOUNDED_RELATIVE"):
            self.probe(relative_path="../outside")

    def test_symlink_is_rejected(self):
        target = self.root / "link.safetensors"
        try:
            target.symlink_to(self.root / "model.safetensors")
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        with self.assertRaisesRegex(ThinkPadStorageProbeError, "TARGET_SYMLINK_FORBIDDEN"):
            self.probe(relative_path="link.safetensors")

    def test_c2_payload_bound_is_enforced(self):
        with self.assertRaisesRegex(ThinkPadStorageProbeError, "PROBE_EXCEEDS_C2_PAYLOAD_BOUND"):
            self.probe(probe_bytes=self.request.max_payload_bytes + 1)

    def test_c2_wall_bound_is_enforced(self):
        with self.assertRaisesRegex(ThinkPadStorageProbeError, "PROBE_EXCEEDS_C2_WALL_BOUND"):
            self.probe(max_wall_seconds=self.request.max_wall_seconds + 1)

    def test_bool_int_confusion_is_rejected(self):
        with self.assertRaisesRegex(ThinkPadStorageProbeError, "PROBE_BYTES_INVALID"):
            self.probe(probe_bytes=True)

    def test_short_file_sets_eof_without_fabricating_requested_bytes(self):
        receipt = self.probe(probe_bytes=len(self.payload) + 4096)
        self.assertTrue(receipt.eof_reached)
        self.assertEqual(receipt.logical_bytes_read, len(self.payload))
        self.assertLess(receipt.logical_bytes_read, receipt.requested_probe_bytes)

    def test_evidence_identity_binds_request_and_observed_window(self):
        receipt = self.probe(probe_bytes=8192)
        self.assertEqual(receipt.request_digest, self.request.request_digest)
        self.assertTrue(receipt.evidence_ref.startswith("awj032-thinkpad-storage-probe-sha256:"))
        self.assertEqual(len(receipt.receipt_digest), 64)


if __name__ == "__main__":
    unittest.main()
