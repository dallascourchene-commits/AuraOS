import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np

MODULE = Path(__file__).resolve().parents[1] / 'tools' / 'spatial' / 'optical_invariant_witness.py'
spec = importlib.util.spec_from_file_location('optical_invariant_witness', MODULE)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class OpticalInvariantWitnessTests(unittest.TestCase):
    def setUp(self):
        self.field = mod.deterministic_fixture(64)
        self.kw = dict(dx_m=8e-6, dy_m=8e-6, wavelength_m=532e-9, distance_m=0.03)

    def test_full_complex_field_roundtrip_and_power_are_measured(self):
        r = mod.measure_invariants(self.field, **self.kw)
        self.assertGreaterEqual(r.propagating_spectral_power_fraction, 1.0 - 1e-12)
        self.assertTrue(r.power_conservation_measured)
        self.assertTrue(r.full_field_roundtrip_measured)
        self.assertLess(r.forward_power_relative_residual, 1e-10)
        self.assertLess(r.full_field_roundtrip_nrmse, 1e-10)

    def test_phase_only_can_match_power_without_preserving_field(self):
        r = mod.measure_invariants(self.field, **self.kw)
        self.assertTrue(r.phase_only_power_matched)
        self.assertLess(r.phase_only_power_relative_residual, 1e-10)
        self.assertGreater(r.phase_only_roundtrip_nrmse, 0.1)
        self.assertFalse(r.phase_only_full_field_fidelity_proven)
        self.assertFalse(r.speckle_elimination_proven)

    def test_propagator_is_named_as_angular_spectrum_not_rayleigh_sommerfeld(self):
        r = mod.measure_invariants(self.field, **self.kw)
        self.assertEqual(r.propagator, 'ANGULAR_SPECTRUM_PROPAGATING_BAND_ONLY_V1')
        self.assertFalse(r.rayleigh_sommerfeld_implementation_proven)

    def test_metadata_string_cannot_mint_physical_display_fidelity(self):
        r = mod.measure_invariants(self.field, **self.kw)
        self.assertFalse(r.physical_display_fidelity_proven)
        self.assertFalse(r.semantic_k27_authority)
        self.assertFalse(r.native_transformer_kv_accessed)
        self.assertEqual(len(r.receipt_sha256), 64)

    def test_codec_extension_mismatch_is_rejected(self):
        with self.assertRaises(mod.OpticalContractError):
            mod.validate_codec_filename('phase_mask.zstd', 'zlib')
        mod.validate_codec_filename('phase_mask.zlib', 'zlib')
        mod.validate_codec_filename('phase_mask.zst', 'zstd')

    def test_invalid_sampling_fails_closed(self):
        with self.assertRaises(mod.OpticalContractError):
            mod.angular_spectrum_propagate(
                self.field, dx_m=0.0, dy_m=8e-6, wavelength_m=532e-9, distance_m=0.03
            )

    def test_phase_only_projection_has_uniform_amplitude(self):
        propagated = mod.angular_spectrum_propagate(self.field, **self.kw)
        phase_only = mod.phase_only_projection(propagated)
        amplitudes = np.abs(phase_only)
        self.assertLess(float(np.max(amplitudes) - np.min(amplitudes)), 1e-12)


if __name__ == '__main__':
    unittest.main()
