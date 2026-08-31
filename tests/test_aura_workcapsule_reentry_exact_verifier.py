import copy
import hashlib
import json
import unittest

from scripts.aura_workcapsule_context_binding import (
    ACTIVE,
    COLD,
    CURRENT,
    STALE,
    UNKNOWN,
    compile_workcapsule_context_binding,
)
from scripts.aura_workcapsule_reentry_exact_verifier import (
    EXACT_INPUT_MISMATCH,
    OBSERVED_IDENTITY_MISMATCH,
    PREVIOUS_IDENTITY_MISMATCH,
    admit_exact_reentry_receipt,
    verify_exact_reentry_receipt,
)
from scripts.aura_workcapsule_reentry_invalidation import (
    SELECTED_SOURCES,
    compile_reentry_invalidation,
    verify_reentry_invalidation,
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


def reseal_o8_self_digest(receipt: dict) -> None:
    """Recompute the public O8 self-digest after a payload substitution."""
    without_identity = copy.deepcopy(receipt)
    prior_identity = without_identity.pop("receipt_identity")
    canonical = json.dumps(
        without_identity,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    new_identity = copy.deepcopy(prior_identity)
    new_identity["value"] = hashlib.sha256(canonical).hexdigest()
    receipt["receipt_identity"] = new_identity


class WorkCapsuleReentryExactVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.capsule = {
            "capsule_id": "CAP-EXACT-001",
            "capsule_generation": 8,
            "parent_work_order_interface_binding_generation": 12,
            "execution_basis_identity": identity("execution-basis-8"),
        }
        self.graph = {
            "graph_id": "ASTGE-GRAPH-1",
            "graph_generation": 41,
            "graph_basis_identity": identity("graph-basis-41"),
            "currentness": CURRENT,
            "witness_ref": "GRAPH:41:CURRENT",
        }
        self.sources = [
            {
                "role": ACTIVE,
                "file_id": 3,
                "relative_path": "src/alpha.py",
                "source_generation": 9001,
                "source_sha256": "a" * 64,
                "source_byte_len": 123,
                "currentness": CURRENT,
                "witness_ref": "SOURCE:3:GEN9001",
            },
            {
                "role": ACTIVE,
                "file_id": 4,
                "relative_path": "src/beta.py",
                "source_generation": 9002,
                "source_sha256": "b" * 64,
                "source_byte_len": 456,
                "currentness": CURRENT,
                "witness_ref": "SOURCE:4:GEN9002",
            },
            {
                "role": COLD,
                "file_id": 9,
                "relative_path": "docs/frontier.md",
                "source_generation": 12,
                "source_sha256": "c" * 64,
                "source_byte_len": 77,
                "currentness": UNKNOWN,
                "witness_ref": "SOURCE:9:UNKNOWN",
            },
        ]
        self.previous = compile_workcapsule_context_binding(
            capsule=self.capsule,
            graph_witness=self.graph,
            source_witnesses=self.sources,
        )

    def receipt(self, *, graph=None, sources=None):
        return compile_reentry_invalidation(
            previous_binding=self.previous,
            observed_graph_witness=graph or self.graph,
            observed_source_witnesses=sources if sources is not None else self.sources,
        )

    def verify(self, receipt, *, graph=None, sources=None):
        return verify_exact_reentry_receipt(
            previous_binding=self.previous,
            observed_graph_witness=graph or self.graph,
            observed_source_witnesses=sources if sources is not None else self.sources,
            receipt=receipt,
        )

    def test_exact_canonical_receipt_is_admitted(self):
        receipt = self.receipt()
        self.assertEqual(self.verify(receipt), [])
        admitted = admit_exact_reentry_receipt(
            previous_binding=self.previous,
            observed_graph_witness=self.graph,
            observed_source_witnesses=self.sources,
            receipt=receipt,
        )
        self.assertTrue(admitted["exact_input_reproduction"])
        self.assertFalse(any(admitted["authority"].values()))

    def test_self_consistent_source_key_substitution_fails_exact_reproduction(self):
        observed = copy.deepcopy(self.sources)
        observed[0]["currentness"] = STALE
        observed[0]["witness_ref"] = "SOURCE:3:STALE"
        receipt = self.receipt(sources=observed)
        self.assertEqual(receipt["minimum_reentry_scope"], SELECTED_SOURCES)

        tampered = copy.deepcopy(receipt)
        tampered["minimum_reentry_source_keys"] = [
            {"file_id": 999, "relative_path": "src/not-the-dependency.py"}
        ]
        reseal_o8_self_digest(tampered)

        # O8's verifier establishes self-consistency, not exact input reproduction.
        self.assertEqual(verify_reentry_invalidation(tampered), [])
        self.assertIn(EXACT_INPUT_MISMATCH, self.verify(tampered, sources=observed))

    def test_self_consistent_previous_identity_substitution_is_rejected(self):
        receipt = self.receipt()
        tampered = copy.deepcopy(receipt)
        tampered["previous_binding_identity"]["value"] = "f" * 64
        reseal_o8_self_digest(tampered)

        self.assertEqual(verify_reentry_invalidation(tampered), [])
        violations = self.verify(tampered)
        self.assertIn(PREVIOUS_IDENTITY_MISMATCH, violations)
        self.assertIn(EXACT_INPUT_MISMATCH, violations)

    def test_self_consistent_observed_identity_substitution_is_rejected(self):
        receipt = self.receipt()
        tampered = copy.deepcopy(receipt)
        tampered["observed_binding_identity"]["value"] = "e" * 64
        reseal_o8_self_digest(tampered)

        self.assertEqual(verify_reentry_invalidation(tampered), [])
        violations = self.verify(tampered)
        self.assertIn(OBSERVED_IDENTITY_MISMATCH, violations)
        self.assertIn(EXACT_INPUT_MISMATCH, violations)

    def test_old_receipt_cannot_verify_against_fresh_changed_source_evidence(self):
        old_receipt = self.receipt()
        changed = copy.deepcopy(self.sources)
        changed[1]["source_generation"] = 9003
        changed[1]["source_sha256"] = "d" * 64
        changed[1]["witness_ref"] = "SOURCE:4:GEN9003"

        violations = self.verify(old_receipt, sources=changed)
        self.assertIn(OBSERVED_IDENTITY_MISMATCH, violations)
        self.assertIn(EXACT_INPUT_MISMATCH, violations)

    def test_old_receipt_cannot_verify_against_fresh_stale_graph(self):
        old_receipt = self.receipt()
        stale_graph = copy.deepcopy(self.graph)
        stale_graph["currentness"] = STALE
        stale_graph["witness_ref"] = "GRAPH:41:STALE"

        violations = self.verify(old_receipt, graph=stale_graph)
        self.assertIn(OBSERVED_IDENTITY_MISMATCH, violations)
        self.assertIn(EXACT_INPUT_MISMATCH, violations)


if __name__ == "__main__":
    unittest.main()
