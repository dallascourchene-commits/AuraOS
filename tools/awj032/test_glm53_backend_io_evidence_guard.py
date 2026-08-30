import unittest

import glm53_backend_io_evidence_guard as g


BINDING = "binding-digest"


class Backend:
    def __init__(self, payload):
        self.payload = dict(payload)

    def io_attestation(self, binding_digest):
        out = dict(self.payload)
        out.setdefault("schema", g.BACKEND_IO_ATTESTATION_SCHEMA)
        out.setdefault("binding_digest", binding_digest)
        out.setdefault("attestation_id", "att-1")
        out.setdefault("physical_selected_only", True)
        out.setdefault("whole_bank_reads", 0)
        out.setdefault("whole_bank_materialized", False)
        return out


class NoAttestation:
    pass


class EvidenceGuardTests(unittest.TestCase):
    def test_missing_attestation_stays_unknown_and_not_w4_admissible(self):
        receipt = g.validate_backend_evidence(NoAttestation(), binding_digest=BINDING)
        self.assertFalse(receipt.physical_io_attested)
        self.assertFalse(receipt.w4_metrics_complete)
        self.assertFalse(receipt.w4_admissible)
        self.assertIsNone(receipt.physical_expert_bytes_read)
        self.assertFalse(receipt.g2_admitted)

    def test_safe_complete_attestation_is_w4_admissible(self):
        receipt = g.validate_backend_evidence(
            Backend({
                "physical_expert_bytes_read": 12345,
                "physical_read_operations": 7,
                "read_elapsed_ms": 12.5,
                "page_cache_provenance": "COLD_PAGE_CACHE",
            }),
            binding_digest=BINDING,
        )
        self.assertTrue(receipt.physical_io_attested)
        self.assertTrue(receipt.w4_metrics_complete)
        self.assertTrue(receipt.w4_admissible)
        self.assertEqual(12345, receipt.physical_expert_bytes_read)
        self.assertEqual(7, receipt.physical_read_operations)
        self.assertEqual("COLD_PAGE_CACHE", receipt.page_cache_provenance)
        self.assertFalse(receipt.g2_admitted)

    def test_safe_but_incomplete_attestation_is_not_promoted_to_w4(self):
        receipt = g.validate_backend_evidence(Backend({}), binding_digest=BINDING)
        self.assertTrue(receipt.physical_io_attested)
        self.assertFalse(receipt.w4_metrics_complete)
        self.assertFalse(receipt.w4_admissible)
        self.assertIsNone(receipt.physical_expert_bytes_read)

    def test_nonselected_physical_reads_fail_closed(self):
        with self.assertRaises(g.BackendEvidenceError) as ctx:
            g.validate_backend_evidence(
                Backend({"physical_selected_only": False}), binding_digest=BINDING
            )
        self.assertEqual("PHYSICAL_SELECTED_ONLY_VIOLATION", ctx.exception.code)

    def test_whole_bank_read_fails_closed(self):
        with self.assertRaises(g.BackendEvidenceError) as ctx:
            g.validate_backend_evidence(
                Backend({"whole_bank_reads": 1}), binding_digest=BINDING
            )
        self.assertEqual("WHOLE_BANK_PHYSICAL_READ_FORBIDDEN", ctx.exception.code)

    def test_whole_bank_materialization_fails_closed(self):
        with self.assertRaises(g.BackendEvidenceError) as ctx:
            g.validate_backend_evidence(
                Backend({"whole_bank_materialized": True}), binding_digest=BINDING
            )
        self.assertEqual("WHOLE_BANK_MATERIALIZATION_FORBIDDEN", ctx.exception.code)

    def test_binding_mismatch_fails_closed(self):
        with self.assertRaises(g.BackendEvidenceError) as ctx:
            g.validate_backend_evidence(
                Backend({"binding_digest": "wrong"}), binding_digest=BINDING
            )
        self.assertEqual("BACKEND_IO_ATTESTATION_BINDING_MISMATCH", ctx.exception.code)

    def test_invalid_metrics_fail_closed(self):
        cases = [
            ({"physical_expert_bytes_read": -1}, "PHYSICAL_EXPERT_BYTES_INVALID"),
            ({"physical_read_operations": True}, "PHYSICAL_READ_OPERATIONS_INVALID"),
            ({"read_elapsed_ms": -0.1}, "READ_ELAPSED_MS_INVALID"),
            ({"page_cache_provenance": ""}, "PAGE_CACHE_PROVENANCE_INVALID"),
        ]
        for payload, code in cases:
            with self.subTest(code=code):
                with self.assertRaises(g.BackendEvidenceError) as ctx:
                    g.validate_backend_evidence(Backend(payload), binding_digest=BINDING)
                self.assertEqual(code, ctx.exception.code)

    def test_receipt_is_deterministically_nonpromoting(self):
        a = g.validate_backend_evidence(
            Backend({
                "physical_expert_bytes_read": 10,
                "physical_read_operations": 1,
                "read_elapsed_ms": 1.0,
                "page_cache_provenance": "WARM_PAGE_CACHE",
            }),
            binding_digest=BINDING,
        ).to_dict()
        b = g.validate_backend_evidence(
            Backend({
                "physical_expert_bytes_read": 10,
                "physical_read_operations": 1,
                "read_elapsed_ms": 1.0,
                "page_cache_provenance": "WARM_PAGE_CACHE",
            }),
            binding_digest=BINDING,
        ).to_dict()
        self.assertEqual(a, b)
        self.assertFalse(a["g2_admitted"])
        self.assertIn("NO_MODEL_RUNTIME_OR_G2_PROOF", a["claim_ceiling"])


if __name__ == "__main__":
    unittest.main()
