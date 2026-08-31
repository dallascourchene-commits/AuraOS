from __future__ import annotations

import copy
import hashlib
import inspect
from pathlib import Path
import tempfile
import unittest

from scripts.aura_astge_anchor_hydration import WITNESS_VERSION
from scripts.aura_workcapsule_context_binding import ACTIVE, CURRENT, compile_workcapsule_context_binding
from scripts.aura_workcapsule_observation_bound_closure import CLOSED, HOLD
from scripts.aura_workcapsule_owner_bound_reentry_closure import (
    EXACT_END_TO_END_MISMATCH,
    admit_owner_bound_reentry_closure,
    compile_owner_bound_reentry_closure,
    verify_owner_bound_reentry_closure,
)
from scripts.aura_workcapsule_reentry_invalidation import FULL_GRAPH, NONE, SELECTED_SOURCES


def identity(value: str) -> dict[str, str]:
    return {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "TEST_V1",
        "scope_profile": "TEST_SCOPE",
        "value": value,
        "schema_version": "1",
    }


class WorkCapsuleOwnerBoundReentryClosureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="aura-owner-bound-reentry-closure-")
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        self.path = self.root / "src/a.py"
        self.original = b"def target(x):\n    return x + 1\n"
        self.changed = b"def target(x):\n    return x + 2\n"
        self.path.write_bytes(self.original)
        self.original_sha = hashlib.sha256(self.original).hexdigest()
        self.changed_sha = hashlib.sha256(self.changed).hexdigest()
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
        self.witness42 = self._witness(42, self.original, self.original_sha)
        self.graph7 = {
            "graph_id": "ASTGE-GRAPH-1",
            "graph_generation": 7,
            "graph_basis_identity": identity("graph-7"),
            "currentness": CURRENT,
            "witness_ref": "GRAPH:7:CURRENT",
        }
        self.capsule = {
            "capsule_id": "CAP-O25-1",
            "capsule_generation": 3,
            "parent_work_order_interface_binding_generation": 5,
            "execution_basis_identity": identity("basis-3"),
        }
        self.previous = compile_workcapsule_context_binding(
            capsule=self.capsule,
            graph_witness=self.graph7,
            source_witnesses=[
                {
                    "role": ACTIVE,
                    "file_id": 17,
                    "relative_path": "src/a.py",
                    "source_generation": 42,
                    "source_sha256": self.original_sha,
                    "source_byte_len": len(self.original),
                    "currentness": CURRENT,
                    "witness_ref": "fixture://prior-current/42",
                }
            ],
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _witness(self, generation: int, body: bytes, sha: str) -> dict:
        return {
            "version": WITNESS_VERSION,
            "witnesses": [
                {
                    "anchor_id": "target-anchor",
                    "file_id": 17,
                    "source_generation": generation,
                    "expected_byte_len": len(body),
                    "expected_body_sha256": sha,
                    "witness_ref": f"fixture://source-owner/{generation}",
                    "checked_at": "2026-08-31T02:00:00Z",
                }
            ],
        }

    def compile(self, *, witness=None, observed_graph=None, candidate_graph=None):
        return compile_owner_bound_reentry_closure(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=witness if witness is not None else self.witness42,
            previous_binding=self.previous,
            observed_graph_witness=observed_graph if observed_graph is not None else self.graph7,
            candidate_graph_witness=candidate_graph if candidate_graph is not None else self.graph7,
        )

    def verify(self, receipt, *, witness=None, observed_graph=None, candidate_graph=None):
        return verify_owner_bound_reentry_closure(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=witness if witness is not None else self.witness42,
            previous_binding=self.previous,
            observed_graph_witness=observed_graph if observed_graph is not None else self.graph7,
            candidate_graph_witness=candidate_graph if candidate_graph is not None else self.graph7,
            receipt=receipt,
        )

    def test_unchanged_raw_owner_evidence_derives_none_and_closes(self) -> None:
        receipt = self.compile()
        self.assertEqual(NONE, receipt["owner_derived_reentry_scope"])
        self.assertEqual(CLOSED, receipt["closure_status"])
        self.assertTrue(receipt["same_raw_source_observation_drives_plan_and_candidate"])
        self.assertFalse(receipt["caller_reentry_receipt_accepted"])
        self.assertFalse(receipt["caller_candidate_binding_accepted"])
        self.assertEqual([], self.verify(receipt))
        admitted = admit_owner_bound_reentry_closure(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=self.witness42,
            previous_binding=self.previous,
            observed_graph_witness=self.graph7,
            candidate_graph_witness=self.graph7,
            receipt=receipt,
        )
        self.assertTrue(admitted["exact_end_to_end_reproduction"])
        self.assertFalse(any(admitted["authority"].values()))

    def test_changed_current_source_derives_selected_sources_and_closes(self) -> None:
        self.path.write_bytes(self.changed)
        witness43 = self._witness(43, self.changed, self.changed_sha)
        receipt = self.compile(witness=witness43)
        self.assertEqual(SELECTED_SOURCES, receipt["owner_derived_reentry_scope"])
        self.assertEqual([{"file_id": 17, "relative_path": "src/a.py"}], receipt["owner_derived_reentry_source_keys"])
        self.assertEqual(CLOSED, receipt["closure_status"])
        candidate = receipt["observation_bound_closure"]["derived_candidate_binding"]
        self.assertEqual(43, candidate["source_witnesses"][0]["source_generation"])
        self.assertEqual(self.changed_sha, candidate["source_witnesses"][0]["source_sha256"])
        self.assertEqual([], self.verify(receipt, witness=witness43))

    def test_stale_raw_source_derives_reentry_but_holds_closure(self) -> None:
        self.path.write_bytes(self.changed)
        receipt = self.compile()
        self.assertEqual(SELECTED_SOURCES, receipt["owner_derived_reentry_scope"])
        self.assertEqual(HOLD, receipt["closure_status"])
        closure = receipt["observation_bound_closure"]
        self.assertIn("DERIVED_CANDIDATE_NOT_CURRENT", closure["hold_reasons"])
        self.assertFalse(receipt["source_bound_exact_reentry_admission"]["stale_observed_bytes_bound_to_source_generation"])
        self.assertEqual([], self.verify(receipt))

    def test_unknown_raw_source_derives_reentry_but_never_guesses_identity(self) -> None:
        empty = {"version": WITNESS_VERSION, "witnesses": []}
        receipt = self.compile(witness=empty)
        self.assertEqual(SELECTED_SOURCES, receipt["owner_derived_reentry_scope"])
        self.assertEqual(HOLD, receipt["closure_status"])
        admission = receipt["source_bound_exact_reentry_admission"]
        self.assertEqual(1, admission["unknown_dependency_count"])
        self.assertFalse(admission["unknown_identity_guessed"])
        self.assertEqual([], self.verify(receipt, witness=empty))

    def test_changed_graph_derives_full_graph_and_closes_against_same_candidate_graph(self) -> None:
        graph8 = copy.deepcopy(self.graph7)
        graph8["graph_generation"] = 8
        graph8["graph_basis_identity"] = identity("graph-8")
        graph8["witness_ref"] = "GRAPH:8:CURRENT"
        receipt = self.compile(observed_graph=graph8, candidate_graph=graph8)
        self.assertEqual(FULL_GRAPH, receipt["owner_derived_reentry_scope"])
        self.assertEqual(CLOSED, receipt["closure_status"])
        self.assertEqual([], self.verify(receipt, observed_graph=graph8, candidate_graph=graph8))

    def test_public_compile_boundary_accepts_no_caller_plan_or_candidate(self) -> None:
        params = inspect.signature(compile_owner_bound_reentry_closure).parameters
        self.assertNotIn("reentry_receipt", params)
        self.assertNotIn("candidate_binding", params)
        self.assertIn("witness_manifest", params)
        self.assertIn("observed_graph_witness", params)
        self.assertIn("candidate_graph_witness", params)

    def test_end_to_end_receipt_tamper_fails_exact_reproduction(self) -> None:
        receipt = self.compile()
        tampered = copy.deepcopy(receipt)
        tampered["owner_derived_reentry_scope"] = SELECTED_SOURCES
        violations = self.verify(tampered)
        self.assertIn(EXACT_END_TO_END_MISMATCH, violations)


if __name__ == "__main__":
    unittest.main()
