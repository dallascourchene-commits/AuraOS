import importlib.util
import sys
import unittest
from pathlib import Path

PROBE_PATH = Path(__file__).resolve().parents[1] / 'tools' / 'k27_astge_io_uring_capability_probe.py'
spec = importlib.util.spec_from_file_location('k27_astge_io_uring_capability_probe', PROBE_PATH)
probe = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = probe
spec.loader.exec_module(probe)


class IoUringProbeTests(unittest.TestCase):
    def test_linux_abi_struct_sizes_are_exact(self):
        self.assertEqual(probe.ctypes.sizeof(probe.IoSqringOffsets), 40)
        self.assertEqual(probe.ctypes.sizeof(probe.IoCqringOffsets), 40)
        self.assertEqual(probe.ctypes.sizeof(probe.IoUringParams), 120)
        self.assertEqual(probe.ctypes.sizeof(probe.IOVec), 16)

    def test_non_x86_fails_closed(self):
        receipt = probe.observe('aarch64')
        self.assertFalse(receipt['io_uring_setup_observed'])
        self.assertFalse(receipt['registered_anonymous_buffer_observed'])
        self.assertEqual(receipt['probe_reason'], 'UNSUPPORTED_PROBE_ARCH')

    def test_observation_never_claims_direct_io_or_performance(self):
        receipt = probe.observe()
        self.assertFalse(receipt['direct_io_file_read_observed'])
        self.assertFalse(receipt['io_uring_direct_performance_proven'])
        self.assertFalse(receipt['cold_nvme_superiority_proven'])
        self.assertFalse(receipt['production_backend_promotion_authorized'])
        self.assertFalse(receipt['native_transformer_kv_accessed'])
        self.assertFalse(receipt['semantic_k27_authority'])

    def test_receipt_is_sealed(self):
        receipt = probe.observe('aarch64')
        self.assertEqual(len(receipt['receipt_sha256']), 64)


if __name__ == '__main__':
    unittest.main()
