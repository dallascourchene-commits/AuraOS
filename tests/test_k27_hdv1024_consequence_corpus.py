from __future__ import annotations

import copy
import unittest

from tools.k27_hdv1024_consequence_corpus import (
    EXPECTED_DIGEST,
    EXPECTED_DISTANCES,
    CorpusError,
    corpus_digest,
    hamming_words,
    load_corpus,
    validate_corpus,
)


class K27Hdv1024ConsequenceCorpusTests(unittest.TestCase):
    def setUp(self):
        self.corpus = load_corpus()

    def test_exact_frozen_digest_and_distances(self):
        self.assertEqual(corpus_digest(self.corpus), EXPECTED_DIGEST)
        receipt = validate_corpus(self.corpus)
        self.assertEqual(tuple(receipt["expected_distances"]), EXPECTED_DISTANCES)
        self.assertEqual(receipt["vector_count"], 8)

    def test_hamming_extrema_are_logical_1024_bit_consequences(self):
        self.assertEqual(hamming_words(tuple([0] * 16), tuple([0] * 16)), 0)
        self.assertEqual(hamming_words(tuple([0] * 16), tuple([(1 << 64) - 1] * 16)), 1024)

    def test_expected_distance_tamper_fails_closed(self):
        changed = copy.deepcopy(self.corpus)
        changed["vectors"][6]["expected_hamming"] += 1
        with self.assertRaises(CorpusError):
            validate_corpus(changed)

    def test_word_width_and_lowercase_hex_are_exact(self):
        short = copy.deepcopy(self.corpus)
        short["vectors"][0]["a"][0] = "0"
        with self.assertRaises(CorpusError):
            validate_corpus(short)
        upper = copy.deepcopy(self.corpus)
        upper["vectors"][7]["a"][0] = upper["vectors"][7]["a"][0].upper()
        with self.assertRaises(CorpusError):
            validate_corpus(upper)

    def test_vector_order_and_identity_are_bound(self):
        changed = copy.deepcopy(self.corpus)
        changed["vectors"][2], changed["vectors"][3] = changed["vectors"][3], changed["vectors"][2]
        with self.assertRaises(CorpusError):
            validate_corpus(changed)

    def test_width_or_distance_domain_change_fails(self):
        changed = copy.deepcopy(self.corpus)
        changed["word_count"] = 32
        with self.assertRaises(CorpusError):
            validate_corpus(changed)
        changed = copy.deepcopy(self.corpus)
        changed["distance_range"] = [0, 2048]
        with self.assertRaises(CorpusError):
            validate_corpus(changed)

    def test_claim_ceiling_keeps_representation_and_hardware_separate(self):
        receipt = validate_corpus(self.corpus)
        self.assertTrue(receipt["logical_word_indexing_bound"])
        self.assertFalse(receipt["byte_endianness_bound"])
        self.assertFalse(receipt["architectural_register_mapping_bound"])
        self.assertFalse(receipt["compiler_abi_bound"])
        self.assertFalse(receipt["riscv_simulator_semantics_proven"])
        self.assertFalse(receipt["rtl_implementation_proven"])
        self.assertFalse(receipt["hardware_performance_proven"])
        self.assertFalse(receipt["semantic_k27_authority"])
        self.assertFalse(receipt["native_transformer_kv_accessed"])


if __name__ == "__main__":
    unittest.main()
