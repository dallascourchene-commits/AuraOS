import copy
import unittest

from scripts.aura_workcapsule_context_binding import (
    ACTIVE,
    COLD,
    CURRENT,
    STALE,
    UNKNOWN,
    compile_workcapsule_context_binding,
    roundtrip_binding,
    verify_workcapsule_context_binding,
)


def identity(value: str) -> dict[str, str]:
    return {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "TEST_V1",
        "scope_profile": "TEST_SCOPE",
        "value": value,
        "schema_version": "1",
    }


class WorkCapsuleContextBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.capsule = {
            "capsule_id": "CAP-001",
            "capsule_generation": 7,
            "parent_work_order_interface_binding_generation": 11,
            "execution_basis_identity": identity("execution-basis-7"),
        }
        self.graph = {
            "graph_id": "ASTGE-GRAPH-1",
            "graph_generation": 41,
            "graph_basis_identity": identity("graph-basis-41"),
            "currentness": CURRENT,
            "witness_ref": "PR491:5bfa1903",
        }
        self.sources = [
            {
                "role": ACTIVE,
                "file_id": 3,
                "relative_path": "src/active.py",
                "source_generation": 9001,
                "source_sha256": "a" * 64,
                "source_byte_len": 123,
                "currentness": CURRENT,
                "witness_ref": "SOURCE:3:GEN9001",
            },
            {
                "role": COLD,
                "file_id": 9,
                "relative_path": "docs/cold.md",
                "source_generation": 12,
                "source_sha256": "b" * 64,
                "source_byte_len": 77,
                "currentness": UNKNOWN,
                "witness_ref": "SOURCE:9:UNKNOWN",
            },
        ]

    def compile(self, *, graph=None, sources=None):
        return compile_workcapsule_context_binding(
            capsule=self.capsule,
            graph_witness=graph or self.graph,
            source_witnesses=sources if sources is not None else self.sources,
        )

    def test_exact_current_active_context_is_admitted_without_authority(self):
        binding = self.compile()
        self.assertTrue(binding["context_admitted"])
        self.assertEqual(binding["binding_status"], CURRENT)
        self.assertEqual(binding["active_source_count"], 1)
        self.assertEqual(binding["cold_source_count"], 1)
        self.assertTrue(all(value is False for value in binding["authority"].values()))
        self.assertEqual(verify_workcapsule_context_binding(binding), [])

    def test_unknown_cold_source_survives_roundtrip_without_blocking_active_context(self):
        binding = roundtrip_binding(self.compile())
        cold = [row for row in binding["source_witnesses"] if row["role"] == COLD]
        self.assertEqual(len(cold), 1)
        self.assertEqual(cold[0]["currentness"], UNKNOWN)
        self.assertTrue(binding["context_admitted"])
        self.assertEqual(verify_workcapsule_context_binding(binding), [])

    def test_stale_active_source_blocks_and_preserves_exact_reopen_reason(self):
        sources = copy.deepcopy(self.sources)
        sources[0]["currentness"] = STALE
        binding = self.compile(sources=sources)
        self.assertFalse(binding["context_admitted"])
        self.assertEqual(binding["binding_status"], STALE)
        self.assertIn("ACTIVE_SOURCE_3_STALE", binding["reason_codes"])
        self.assertEqual(binding["source_witnesses"][0]["source_generation"], 9001)
        self.assertEqual(verify_workcapsule_context_binding(binding), [])

    def test_unknown_active_source_needs_rebind_and_cannot_be_laundered(self):
        sources = copy.deepcopy(self.sources)
        sources[0]["currentness"] = UNKNOWN
        binding = self.compile(sources=sources)
        self.assertFalse(binding["context_admitted"])
        self.assertEqual(binding["binding_status"], "NEEDS_REBIND")
        self.assertIn("ACTIVE_SOURCE_3_UNKNOWN", binding["reason_codes"])
        self.assertEqual(verify_workcapsule_context_binding(binding), [])

    def test_stale_graph_blocks_even_when_source_is_current(self):
        graph = copy.deepcopy(self.graph)
        graph["currentness"] = STALE
        binding = self.compile(graph=graph)
        self.assertFalse(binding["context_admitted"])
        self.assertEqual(binding["binding_status"], STALE)
        self.assertIn("GRAPH_STALE", binding["reason_codes"])
        self.assertEqual(verify_workcapsule_context_binding(binding), [])

    def test_no_active_source_witnesses_fail_closed(self):
        sources = copy.deepcopy(self.sources)
        sources[0]["role"] = COLD
        binding = self.compile(sources=sources)
        self.assertFalse(binding["context_admitted"])
        self.assertIn("NO_ACTIVE_SOURCE_WITNESSES", binding["reason_codes"])
        self.assertEqual(verify_workcapsule_context_binding(binding), [])

    def test_roundtrip_preserves_graph_and_source_generations_separately(self):
        binding = roundtrip_binding(self.compile())
        self.assertEqual(binding["graph_witness"]["graph_generation"], 41)
        active = [row for row in binding["source_witnesses"] if row["role"] == ACTIVE][0]
        self.assertEqual(active["source_generation"], 9001)
        self.assertNotEqual(active["source_generation"], binding["graph_witness"]["graph_generation"])
        self.assertEqual(verify_workcapsule_context_binding(binding), [])

    def test_tampered_currentness_is_detected_even_if_context_admitted_flag_is_left_true(self):
        binding = self.compile()
        active = [row for row in binding["source_witnesses"] if row["role"] == ACTIVE][0]
        active["currentness"] = STALE
        self.assertIn("ACTIVE_CURRENTNESS_LAUNDERING", verify_workcapsule_context_binding(binding))

    def test_tampered_authority_is_detected(self):
        binding = self.compile()
        binding["authority"]["execution_authorized"] = True
        self.assertIn("AUTHORITY_MINTED_BY_CONTEXT_BINDING", verify_workcapsule_context_binding(binding))

    def test_payload_tamper_breaks_binding_identity(self):
        binding = self.compile()
        binding["graph_witness"]["graph_generation"] = 42
        self.assertIn("BINDING_IDENTITY_MISMATCH", verify_workcapsule_context_binding(binding))

    def test_duplicate_source_identity_is_rejected(self):
        sources = copy.deepcopy(self.sources)
        duplicate = copy.deepcopy(sources[0])
        duplicate["relative_path"] = "src/other.py"
        sources.append(duplicate)
        with self.assertRaisesRegex(ValueError, "duplicate source file_id"):
            self.compile(sources=sources)


if __name__ == "__main__":
    unittest.main()
