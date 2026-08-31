import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

PROBE_PATH = Path(__file__).resolve().parents[1] / 'tools' / 'k27_astge_thinkpad_host_probe.py'
spec = importlib.util.spec_from_file_location('k27_astge_thinkpad_host_probe', PROBE_PATH)
probe = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = probe
spec.loader.exec_module(probe)


class ProbeTests(unittest.TestCase):
    def test_intel_hybrid_flags_select_avx2(self):
        flags = probe.cpu_flags('flags : sse4_2 avx avx2 popcnt')
        self.assertEqual(probe.select_simd_path(flags), 'AVX2_POPCNT64')

    def test_avx512_requires_vpopcnt(self):
        self.assertEqual(probe.select_simd_path({'avx512f','avx2','popcnt'}), 'AVX2_POPCNT64')
        self.assertEqual(probe.select_simd_path({'avx512f','avx512_vpopcntdq','avx2','popcnt'}), 'AVX512_VPOPCNTDQ')

    def test_wsl_detection(self):
        self.assertTrue(probe.detect_wsl('Linux 5.15.153.1-microsoft-standard-WSL2'))
        self.assertFalse(probe.detect_wsl('Linux 6.10.0-generic'))

    def test_memtotal(self):
        self.assertEqual(probe.memory_total_bytes('MemTotal:       16384000 kB\n'), 16384000*1024)

    def test_same_page_benchmark_has_same_consequence(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'x.bin'
            probe.deterministic_file(path, 4*1024*1024)
            result = probe.benchmark_same_pages(path, samples=128, seed=27)
            self.assertTrue(result['same_byte_consequence'])
            self.assertFalse(result['cold_nvme_performance_proven'])
            self.assertFalse(result['production_backend_promotion_authorized'])

    def test_bandwidth_sanity_rejects_impossible_claim(self):
        result = probe.bandwidth_sanity(128_000_000, 0.00125, 51_200_000_000)
        self.assertTrue(result['claim_exceeds_theoretical_stream_bandwidth'])

    def test_qualify_never_promotes(self):
        with tempfile.TemporaryDirectory() as td:
            result = probe.qualify(Path(td), 4, 64)
            self.assertEqual(result['schema'], probe.SCHEMA)
            self.assertFalse(result['production_mmap_promotion_authorized'])
            self.assertFalse(result['io_uring_direct_path_proven'])
            self.assertFalse(result['native_transformer_kv_accessed'])
            self.assertFalse(result['semantic_k27_authority'])
            self.assertEqual(len(result['receipt_sha256']), 64)


if __name__ == '__main__':
    unittest.main()
