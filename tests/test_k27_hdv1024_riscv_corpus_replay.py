from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest

from tools.k27_hdv1024_consequence_corpus import DEFAULT_CORPUS, EXPECTED_DIGEST, EXPECTED_DISTANCES
from tools.k27_hdv1024_riscv_corpus_replay import (
    PR623_EXACT_HEAD,
    PR623_EXACT_RUN,
    PR635_EXACT_HEAD,
    PR635_EXACT_RUN,
    R3_CONVERGENCE_COMMIT,
    portable_riscv_corpus_replay_receipt,
    replay_corpus_through_pr623,
)


class RiscvCorpusReplayTests(unittest.TestCase):
    def test_all_eight_canonical_consequences_match_pr623(self):
        out = replay_corpus_through_pr623()
        self.assertTrue(out.all_logical_consequences_match)
        self.assertEqual(out.corpus_sha256, EXPECTED_DIGEST)
        self.assertEqual(out.expected_distances, EXPECTED_DISTANCES)
        self.assertEqual(out.riscv_reference_distances, EXPECTED_DISTANCES)
        self.assertEqual(len(out.vector_names), 8)

    def test_exact_parent_generations_are_pinned(self):
        out = replay_corpus_through_pr623()
        self.assertEqual(out.exact_parent_heads, (PR635_EXACT_HEAD, PR623_EXACT_HEAD))
        self.assertEqual(out.exact_parent_runs, (PR635_EXACT_RUN, PR623_EXACT_RUN))
        self.assertEqual(R3_CONVERGENCE_COMMIT, "d41f204afb158e4eb793711d686fc40f27a3b1f6")
        self.assertEqual(len(out.pr623_source_blob_sha), 40)

    def test_corpus_tamper_is_rejected_by_canonical_owner_before_replay(self):
        corpus = json.loads(DEFAULT_CORPUS.read_text(encoding="utf-8"))
        corpus["vectors"][0]["expected_hamming"] = 1
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "tampered.json"
            path.write_text(json.dumps(corpus), encoding="utf-8")
            with self.assertRaises(Exception):
                replay_corpus_through_pr623(path)

    def test_vector_order_tamper_is_rejected(self):
        corpus = json.loads(DEFAULT_CORPUS.read_text(encoding="utf-8"))
        corpus["vectors"][0], corpus["vectors"][1] = corpus["vectors"][1], corpus["vectors"][0]
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "reordered.json"
            path.write_text(json.dumps(corpus), encoding="utf-8")
            with self.assertRaises(Exception):
                replay_corpus_through_pr623(path)

    def test_portable_receipt_is_deterministic_and_tamper_sensitive(self):
        a = portable_riscv_corpus_replay_receipt()
        b = portable_riscv_corpus_replay_receipt()
        self.assertEqual(a, b)
        self.assertEqual(len(a["receipt_digest"]), 64)
        payload = dict(a); supplied = payload.pop("receipt_digest")
        self.assertNotEqual(supplied, "0" * 64)

    def test_logical_agreement_does_not_promote_representation_abi_or_hardware(self):
        out = replay_corpus_through_pr623()
        for name in (
            "byte_serialization_bound",
            "byte_endianness_bound",
            "architectural_register_mapping_bound",
            "compiler_abi_bound",
            "riscv_instruction_execution_proven",
            "spike_or_qemu_execution_proven",
            "hidden_h_register_abi_proven",
            "os_context_state_proven",
            "rtl_implementation_proven",
            "synthesis_or_timing_proven",
            "hardware_performance_proven",
            "cross_isa_performance_equivalence_proven",
            "semantic_k27_authority",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
            "deployment_authorized",
        ):
            self.assertFalse(getattr(out, name), name)

    def test_parent_ownership_is_preserved_not_reimplemented(self):
        out = replay_corpus_through_pr623()
        self.assertTrue(out.canonical_corpus_owner_retained)
        self.assertTrue(out.riscv_reference_owner_retained)
        self.assertEqual(out.pr623_candidate_source_sha256, "98bc8189027158a2cfbc0cb8eaf443836dd9e6ec125ac3fcadaeee9bcc8ba412")


if __name__ == "__main__":
    unittest.main()
