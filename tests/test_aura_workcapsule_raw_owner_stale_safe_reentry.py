from __future__ import annotations

import copy
import hashlib
import inspect
from pathlib import Path
import tempfile
import unittest

from scripts.aura_astge_anchor_hydration import WITNESS_VERSION
from scripts.aura_workcapsule_context_binding import ACTIVE, CURRENT, compile_workcapsule_context_binding
from scripts.aura_workcapsule_reentry_invalidation import FULL_GRAPH, SELECTED_SOURCES, compile_reentry_invalidation
from scripts.aura_workcapsule_raw_owner_stale_safe_reentry import (
    admit_raw_owner_stale_safe_exact_reentry,
    verify_raw_owner_stale_safe_exact_reentry,
)
from scripts.aura_workcapsule_source_bound_exact_reentry import compile_expected_source_bound_reentry
from scripts.aura_workcapsule_stale_exact_reentry import verify_stale_safe_exact_reentry


def identity(value: str) -> dict[str, str]:
    return {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "TEST_V1",
        "scope_profile": "TEST_SCOPE",
        "value": value,
        "schema_version": "1",
    }


class RawOwnerStaleSafeExactReentryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="aura-raw-owner-stale-safe-")
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        self.original = b"def target(x):\n    return x + 1\n"
        self.stale = b"def target(x):\n    return x + 2\n"
        self.assertEqual(len(self.original), len(self.stale))
        self.path = self.root / "src/a.py"
        self.path.write_bytes(self.original)
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
                    "checked_at": "2026-08-31T01:00:00Z",
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
            "capsule_id": "CAP-O13-1",
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
        return verify_raw_owner_stale_safe_exact_reentry(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=witness if witness is not None else self.witness,
            previous_binding=self.previous,
            observed_graph_witness=graph if graph is not None else self.graph,
            reentry_receipt=receipt,
        )

    def admit(self, receipt, *, witness=None, graph=None):
        return admit_raw_owner_stale_safe_exact_reentry(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=witness if witness is not None else self.witness,
            previous_binding=self.previous,
            observed_graph_witness=graph if graph is not None else self.graph,
            reentry_receipt=receipt,
        )

    def test_raw_stale_source_admits_reentry_only_never_currentness(self) -> None:
        self.path.write_bytes(self.stale)
        projected, receipt = self.expected()
        self.assertEqual(SELECTED_SOURCES, receipt["minimum_reentry_scope"])
        self.assertEqual([], self.verify(receipt))
        admission = self.admit(receipt)
        self.assertTrue(admission["raw_source_owner_bound"])
        self.assertTrue(admission["rejected_currentness_exact_reentry_only"])
        self.assertTrue(admission["reentry_required"])
        self.assertFalse(admission["current_source_evidence_admitted"])
        self.assertFalse(admission["source_currentness_minted_by_exact_reproduction"])
        self.assertFalse(admission["stale_observed_bytes_bound_to_source_generation"])
        self.assertEqual(projected["receipt_identity"], admission["source_projection_receipt_identity"])
        self.assertFalse(any(admission["authority"].values()))

    def test_raw_unknown_source_remains_unresolved_and_requires_reentry(self) -> None:
        empty = {"version": WITNESS_VERSION, "witnesses": []}
        projected, receipt = self.expected(witness=empty)
        self.assertEqual(SELECTED_SOURCES, receipt["minimum_reentry_scope"])
        self.assertEqual([], self.verify(receipt, witness=empty))
        admission = self.admit(receipt, witness=empty)
        self.assertEqual(1, len(projected["unresolved_prior_sources"]))
        self.assertFalse(projected["unresolved_prior_sources"][0]["identity_guessed"])
        self.assertTrue(admission["reentry_required"])
        self.assertFalse(admission["current_source_evidence_admitted"])

    def test_current_only_raw_evidence_is_not_a_rejected_currentness_admission(self) -> None:
        _, receipt = self.expected()
        violations = self.verify(receipt)
        self.assertIn("STALE_SAFE_REJECTED_CURRENTNESS_REQUIRED", violations)

    def test_forged_current_o8_receipt_cannot_override_raw_stale_owner_evidence(self) -> None:
        self.path.write_bytes(self.stale)
        forged_receipt = compile_reentry_invalidation(
            previous_binding=self.previous,
            observed_graph_witness=self.graph,
            observed_source_witnesses=[copy.deepcopy(self.prior_source)],
        )
        violations = self.verify(forged_receipt)
        self.assertTrue(any(item.startswith("RAW_OWNER_") for item in violations))

    def test_full_graph_reentry_from_stale_source_is_still_reentry_only(self) -> None:
        self.path.write_bytes(self.stale)
        graph = copy.deepcopy(self.graph)
        graph["graph_generation"] = 8
        graph["graph_basis_identity"] = identity("graph-8")
        graph["witness_ref"] = "GRAPH:8:CURRENT"
        _, receipt = self.expected(graph=graph)
        self.assertEqual(FULL_GRAPH, receipt["minimum_reentry_scope"])
        self.assertEqual([], self.verify(receipt, graph=graph))
        admission = self.admit(receipt, graph=graph)
        self.assertEqual(FULL_GRAPH, admission["minimum_reentry_scope"])
        self.assertTrue(admission["reentry_required"])
        self.assertFalse(admission["current_source_evidence_admitted"])
        self.assertFalse(admission["graph_witness_producer_authenticated"])

    def test_public_boundary_accepts_no_precompiled_source_observation_or_witness_list(self) -> None:
        params = inspect.signature(verify_raw_owner_stale_safe_exact_reentry).parameters
        self.assertNotIn("source_observation_receipt", params)
        self.assertNotIn("observed_source_witnesses", params)
        self.assertIn("root", params)
        self.assertIn("witness_manifest", params)

    def test_direct_pr517_is_correct_for_a_valid_precompiled_projection_but_o13_owns_raw_binding(self) -> None:
        self.path.write_bytes(self.stale)
        projected, receipt = self.expected()
        self.assertEqual(
            [],
            verify_stale_safe_exact_reentry(
                source_observation_receipt=projected,
                previous_binding=self.previous,
                observed_graph_witness=self.graph,
                reentry_receipt=receipt,
            ),
        )
        self.assertEqual([], self.verify(receipt))


if __name__ == "__main__":
    unittest.main()
