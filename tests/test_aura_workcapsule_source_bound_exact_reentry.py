from __future__ import annotations

import copy
import hashlib
import inspect
from pathlib import Path
import tempfile
import unittest

from scripts.aura_astge_anchor_hydration import WITNESS_VERSION
from scripts.aura_workcapsule_context_binding import ACTIVE, CURRENT, compile_workcapsule_context_binding
from scripts.aura_workcapsule_reentry_exact_verifier import verify_exact_reentry_receipt
from scripts.aura_workcapsule_reentry_invalidation import (
    SELECTED_SOURCES,
    compile_reentry_invalidation,
)
from scripts.aura_workcapsule_source_bound_exact_reentry import (
    admit_source_bound_exact_reentry,
    compile_expected_source_bound_reentry,
    verify_source_bound_exact_reentry,
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


class WorkCapsuleSourceBoundExactReentryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="aura-workcapsule-source-bound-exact-")
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        self.original = b"def target(x):\n    return x + 1\n"
        (self.root / "src/a.py").write_bytes(self.original)
        self.original_sha = hashlib.sha256(self.original).hexdigest()
        self.codemap = {
            "files": [{"path": "src/a.py", "digest8": "projection"}],
            "symbol_index": {
                "target": [
                    {
                        "file": "src/a.py",
                        "kind": "function",
                        "semantic_id": "src/a.py#function:target:stable",
                        "signature_hash": "sig-stable",
                        "line": 1,
                        "end_line": 2,
                    }
                ]
            },
        }
        self.anchors = {
            "version": "AURA_SOURCE_ANCHOR_MANIFEST_V1",
            "anchors": [
                {
                    "anchor_id": "target-anchor",
                    "mechanism": "fixture",
                    "path": "src/a.py",
                    "symbol": "target",
                    "kind": "function",
                    "semantic_id": "src/a.py#function:target:stable",
                    "signature_hash": "sig-stable",
                    "role": "fixture anchor",
                }
            ],
        }
        self.witness = {
            "version": WITNESS_VERSION,
            "witnesses": [
                {
                    "anchor_id": "target-anchor",
                    "file_id": 17,
                    "source_generation": 42,
                    "expected_byte_len": len(self.original),
                    "expected_body_sha256": self.original_sha,
                    "witness_ref": "fixture://source-owner/42",
                    "checked_at": "2026-08-30T20:00:00-05:00",
                }
            ],
        }
        self.graph = {
            "graph_id": "ASTGE-GRAPH-1",
            "graph_generation": 7,
            "graph_basis_identity": identity("graph-7"),
            "currentness": CURRENT,
            "witness_ref": "GRAPH:7:CURRENT",
        }
        self.capsule = {
            "capsule_id": "CAP-O10-1",
            "capsule_generation": 3,
            "parent_work_order_interface_binding_generation": 5,
            "execution_basis_identity": identity("basis-3"),
        }
        self.prior_source = {
            "role": ACTIVE,
            "file_id": 17,
            "relative_path": "src/a.py",
            "source_generation": 42,
            "source_sha256": self.original_sha,
            "source_byte_len": len(self.original),
            "currentness": CURRENT,
            "witness_ref": "fixture://prior-current/42",
        }
        self.previous = compile_workcapsule_context_binding(
            capsule=self.capsule,
            graph_witness=self.graph,
            source_witnesses=[self.prior_source],
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def expected(self, *, witness=None, graph=None):
        return compile_expected_source_bound_reentry(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=witness if witness is not None else self.witness,
            previous_binding=self.previous,
            observed_graph_witness=graph if graph is not None else self.graph,
        )

    def verify(self, receipt, *, witness=None, graph=None):
        return verify_source_bound_exact_reentry(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=witness if witness is not None else self.witness,
            previous_binding=self.previous,
            observed_graph_witness=graph if graph is not None else self.graph,
            receipt=receipt,
        )

    def admit(self, receipt, *, witness=None, graph=None):
        return admit_source_bound_exact_reentry(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=witness if witness is not None else self.witness,
            previous_binding=self.previous,
            observed_graph_witness=graph if graph is not None else self.graph,
            receipt=receipt,
        )

    def test_current_raw_owner_evidence_roundtrips_to_exact_admission(self) -> None:
        projected, receipt = self.expected()
        self.assertEqual([], self.verify(receipt))
        admission = self.admit(receipt)
        self.assertTrue(admission["source_owner_bound_exact_reproduction"])
        self.assertTrue(admission["canonical_o8_receipt_equal"])
        self.assertEqual(projected["receipt_identity"], admission["source_projection_receipt_identity"])
        self.assertEqual(0, admission["stale_dependency_count"])
        self.assertEqual(0, admission["unknown_dependency_count"])
        self.assertFalse(any(admission["authority"].values()))
        self.assertFalse(admission["semantic_truth_minted"])

    def test_stale_raw_body_preserves_expected_identity_and_exactly_selects_source(self) -> None:
        mutated = b"def target(x):\n    return x + 2\n"
        self.assertEqual(len(mutated), len(self.original))
        (self.root / "src/a.py").write_bytes(mutated)

        projected, receipt = self.expected()
        self.assertEqual(SELECTED_SOURCES, receipt["minimum_reentry_scope"])
        self.assertEqual([{"file_id": 17, "relative_path": "src/a.py"}], receipt["minimum_reentry_source_keys"])
        self.assertEqual("STALE", projected["source_observations"][0]["currentness"])
        admission = self.admit(receipt)
        self.assertEqual(1, admission["stale_dependency_count"])
        self.assertTrue(admission["stale_expected_dependency_identity_preserved"])
        self.assertFalse(admission["stale_observed_bytes_bound_to_source_generation"])
        self.assertTrue(admission["source_owner_bound_exact_reproduction"])

    def test_caller_current_witness_cannot_launder_raw_stale_source(self) -> None:
        (self.root / "src/a.py").write_bytes(b"def target(x):\n    return x + 2\n")
        forged_current = [copy.deepcopy(self.prior_source)]
        forged_receipt = compile_reentry_invalidation(
            previous_binding=self.previous,
            observed_graph_witness=self.graph,
            observed_source_witnesses=forged_current,
        )

        # PR510 is correct relative to the exact caller-supplied witness set.
        self.assertEqual(
            [],
            verify_exact_reentry_receipt(
                previous_binding=self.previous,
                observed_graph_witness=self.graph,
                observed_source_witnesses=forged_current,
                receipt=forged_receipt,
            ),
        )
        # The successor independently recomputes PR509 from raw owner evidence,
        # where the source is STALE, so the same receipt must fail closed.
        self.assertNotEqual([], self.verify(forged_receipt))
        with self.assertRaises(ValueError):
            self.admit(forged_receipt)

    def test_unknown_raw_evidence_remains_unresolved_but_exactly_reproducible(self) -> None:
        missing = {"version": WITNESS_VERSION, "witnesses": []}
        projected, receipt = self.expected(witness=missing)
        self.assertEqual([], projected["o7_source_witnesses"])
        self.assertEqual(SELECTED_SOURCES, receipt["minimum_reentry_scope"])
        self.assertEqual(1, len(receipt["unresolved_active_sources"]))
        admission = self.admit(receipt, witness=missing)
        self.assertEqual(1, admission["unknown_dependency_count"])
        self.assertFalse(admission["unknown_identity_guessed"])
        self.assertTrue(admission["source_owner_bound_exact_reproduction"])

    def test_caller_current_witness_cannot_guess_identity_for_raw_unknown(self) -> None:
        missing = {"version": WITNESS_VERSION, "witnesses": []}
        forged_current = [copy.deepcopy(self.prior_source)]
        forged_receipt = compile_reentry_invalidation(
            previous_binding=self.previous,
            observed_graph_witness=self.graph,
            observed_source_witnesses=forged_current,
        )
        self.assertEqual(
            [],
            verify_exact_reentry_receipt(
                previous_binding=self.previous,
                observed_graph_witness=self.graph,
                observed_source_witnesses=forged_current,
                receipt=forged_receipt,
            ),
        )
        self.assertNotEqual([], self.verify(forged_receipt, witness=missing))

    def test_old_receipt_fails_if_graph_witness_changes(self) -> None:
        _, receipt = self.expected()
        changed_graph = copy.deepcopy(self.graph)
        changed_graph["graph_generation"] = 8
        changed_graph["graph_basis_identity"] = identity("graph-8")
        self.assertNotEqual([], self.verify(receipt, graph=changed_graph))

    def test_public_verifier_does_not_accept_caller_source_witnesses(self) -> None:
        params = inspect.signature(verify_source_bound_exact_reentry).parameters
        self.assertNotIn("observed_source_witnesses", params)
        self.assertIn("witness_manifest", params)
        self.assertIn("anchor_manifest", params)
        self.assertIn("codemap", params)
        self.assertIn("root", params)


if __name__ == "__main__":
    unittest.main()
