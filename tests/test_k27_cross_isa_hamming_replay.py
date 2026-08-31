from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from tools import k27_cross_isa_hamming_replay as replay


class CrossISAHammingReplayTests(unittest.TestCase):
    def test_frozen_corpus_digest_and_expected_distances(self):
        replay.verify_frozen_identities()
        self.assertEqual(tuple(replay.logical_hamming(v.a, v.b) for v in replay.vectors()), replay.EXPECTED_DISTANCES)

    def test_representation_map_digest_is_exact(self):
        digest = hashlib.sha256(replay._canonical_json(replay.representation_map())).hexdigest()
        self.assertEqual(digest, replay.MAP_SHA256)

    def test_canonical_wire_roundtrip_all_vectors(self):
        self.assertTrue(replay.representation_roundtrip_passes())
        for vector in replay.vectors():
            self.assertEqual(len(replay.encode_wire(vector.a)), 128)
            self.assertEqual(replay.decode_wire(replay.encode_wire(vector.b)), vector.b)

    def test_wire_is_explicit_word_order_and_little_endian(self):
        changed = [0] * 16
        changed[0] = 0x0102030405060708
        wire = replay.encode_wire(tuple(changed))
        self.assertEqual(wire[:8], bytes.fromhex("0807060504030201"))
        self.assertEqual(wire[8:], bytes(120))

    def test_reverse_word_order_is_not_wire_compatible(self):
        vector = replay.vectors()[2]
        forward = replay.encode_wire(vector.b)
        reversed_wire = replay.encode_wire(tuple(reversed(vector.b)))
        self.assertNotEqual(forward, reversed_wire)
        self.assertEqual(replay.logical_hamming(vector.a, vector.b), 1)

    def test_big_endian_per_word_is_not_canonical_wire(self):
        vector = replay.vectors()[6]
        canonical = replay.encode_wire(vector.a)
        big_endian = b"".join(word.to_bytes(8, "big") for word in vector.a)
        self.assertNotEqual(canonical, big_endian)

    def test_emit_tsv_is_complete_and_ordered(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "corpus.tsv"
            replay.emit_tsv(path)
            rows = [line.split("\t") for line in path.read_text().splitlines()]
        self.assertEqual(len(rows), 8)
        self.assertEqual(tuple(row[0] for row in rows), tuple(v.name for v in replay.vectors()))
        self.assertEqual(tuple(int(row[1]) for row in rows), replay.EXPECTED_DISTANCES)

    def test_pr623_exact_software_reference_replays_corpus(self):
        self.assertEqual(replay.replay_pr623(), replay.EXPECTED_DISTANCES)

    def test_receipt_keeps_representation_abi_hardware_effect_ceiling_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pr613.tsv"
            path.write_text("\n".join(f"{vector.name}\t{vector.expected_hamming}\t{vector.expected_hamming}\tSCALAR_PORTABLE" for vector in replay.vectors()) + "\n")
            receipt = replay.build_receipt(path)
        self.assertTrue(receipt["cross_isa_consequence_agreement"])
        self.assertTrue(receipt["canonical_wire_map_self_consistent"])
        for key in (
            "pr613_native_wire_compatibility_proven",
            "pr623_native_wire_compatibility_proven",
            "compiler_abi_compatibility_proven",
            "architectural_register_compatibility_proven",
            "riscv_simulator_execution_proven",
            "rtl_implementation_proven",
            "hardware_performance_equality_proven",
            "semantic_k27_authority_proven",
            "effect_authority_proven",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
        ):
            self.assertIs(receipt[key], False)


if __name__ == "__main__":
    unittest.main()
