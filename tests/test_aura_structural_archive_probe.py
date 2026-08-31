from __future__ import annotations

import json
import os
import unittest
import zlib

from tools.aura_structural_archive_probe import (
    ArchiveError,
    MODE_JSON_COLUMNS_LZMA,
    MODE_JSON_COLUMNS_ZLIB,
    RESPONSIBILITY,
    build_40_rack_matrix,
    decode,
    encode,
    make_aura_node_rows,
)


class AuraStructuralArchiveProbeTests(unittest.TestCase):
    def test_canonical_structured_rows_roundtrip_exact_and_select_structural_on_large_fixture(self):
        data = make_aura_node_rows(2000)
        blob, receipt = encode(data)
        self.assertEqual(data, decode(blob))
        self.assertTrue(receipt.structured_candidate_admissible)
        self.assertTrue(receipt.structured_candidate_selected)
        self.assertIn(receipt.mode, {MODE_JSON_COLUMNS_ZLIB, MODE_JSON_COLUMNS_LZMA})
        self.assertLess(receipt.archive_size, len(zlib.compress(data, 9)))
        self.assertFalse(receipt.transformer_kv_claim)
        self.assertFalse(receipt.coordinate_memory_claim)
        self.assertFalse(receipt.model_state_claim)
        self.assertFalse(receipt.k27_authority)

    def test_noncanonical_json_falls_back_without_byte_normalization(self):
        data = b'{ "b": 2, "a": 1 }\n'
        blob, receipt = encode(data)
        self.assertFalse(receipt.structured_candidate_admissible)
        self.assertFalse(receipt.structured_candidate_selected)
        self.assertEqual(data, decode(blob))

    def test_prose_does_not_receive_fake_semantic_compression_credit(self):
        data = b"semantic-looking prose does not imply structural compressibility\n" * 200
        blob, receipt = encode(data)
        self.assertFalse(receipt.structured_candidate_admissible)
        self.assertEqual(data, decode(blob))

    def test_random_bytes_roundtrip_and_never_cross_cast_to_structure(self):
        data = os.urandom(32768)
        blob, receipt = encode(data)
        self.assertEqual(data, decode(blob))
        self.assertFalse(receipt.structured_candidate_admissible)
        self.assertEqual(RESPONSIBILITY, receipt.responsibility)

    def test_precompressed_payload_roundtrips(self):
        source = make_aura_node_rows(200)
        data = zlib.compress(source, 9)
        blob, receipt = encode(data)
        self.assertEqual(data, decode(blob))
        self.assertFalse(receipt.structured_candidate_admissible)

    def test_heterogeneous_json_rows_do_not_structurally_project(self):
        data = json.dumps(
            [{"a": 1}, {"a": 2, "b": 3}], sort_keys=True, separators=(",", ":")
        ).encode()
        blob, receipt = encode(data)
        self.assertFalse(receipt.structured_candidate_admissible)
        self.assertEqual(data, decode(blob))

    def test_claim_ceiling_tamper_fails_closed(self):
        data = make_aura_node_rows(80)
        blob, _ = encode(data)
        magic = b"AURAAR1"
        header_len = int.from_bytes(blob[len(magic) : len(magic) + 4], "big")
        start = len(magic) + 4
        header = json.loads(blob[start : start + header_len])
        header["transformer_kv_claim"] = True
        new_header = json.dumps(header, sort_keys=True, separators=(",", ":")).encode()
        tampered = (
            magic
            + len(new_header).to_bytes(4, "big")
            + new_header
            + blob[start + header_len :]
        )
        with self.assertRaisesRegex(ArchiveError, "CLAIM_CEILING_WIDENED"):
            decode(tampered)

    def test_forty_rack_matrix_is_exact_and_contains_both_structural_wins_and_fallbacks(self):
        racks = build_40_rack_matrix()
        self.assertEqual(40, len(racks))
        structured = 0
        fallbacks = 0
        for payload in racks:
            blob, receipt = encode(payload)
            self.assertEqual(payload, decode(blob))
            if receipt.structured_candidate_selected:
                structured += 1
            else:
                fallbacks += 1
        self.assertGreater(structured, 0)
        self.assertGreater(fallbacks, 0)

    def test_empty_bytes_roundtrip(self):
        blob, receipt = encode(b"")
        self.assertEqual(b"", decode(blob))
        self.assertEqual(0, receipt.original_size)


if __name__ == "__main__":
    unittest.main()
