from __future__ import annotations

import copy
import hashlib
import inspect
from pathlib import Path
import tempfile
import unittest

from scripts.aura_astge_anchor_hydration import WITNESS_VERSION
from scripts.aura_workcapsule_context_binding import ACTIVE, CURRENT, compile_workcapsule_context_binding
from scripts.aura_workcapsule_raw_owner_end_to_end_stale_lifecycle import (
    compile_raw_owner_end_to_end_stale_lifecycle,
    verify_raw_owner_end_to_end_stale_lifecycle,
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


class RawOwnerEndToEndStaleLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="aura-o19-stale-lifecycle-")
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        self.original = b"def target(x):\n    return x + 1\n"
        self.stale = b"def target(x):\n    return x + 2\n"
        self.other_stale = b"def target(x):\n    return x + 3\n"
        self.path = self.root / "src/a.py"
        self.path.write_bytes(self.original)
        original_sha = hashlib.sha256(self.original).hexdigest()
        self.codemap = {
            "files": [{"path": "src/a.py", "digest8": "projection"}],
            "symbol_index": {
                "target": [{
                    "file": "src/a.py",
                    "kind": "function",
                    "semantic_id": "src/a.py#function:target:stable",
                    "signature_hash": "sig-stable",
                    "line": 1,
                    "end_line": 2,
                }]
            },
        }
        self.anchors = {
            "version": "AURA_SOURCE_ANCHOR_MANIFEST_V1",
            "anchors": [{
                "anchor_id": "target-anchor",
                "mechanism": "fixture",
                "path": "src/a.py",
                "symbol": "target",
                "kind": "function",
                "semantic_id": "src/a.py#function:target:stable",
                "signature_hash": "sig-stable",
                "role": "fixture anchor",
            }],
        }
        self.witness = {
            "version": WITNESS_VERSION,
            "witnesses": [{
                "anchor_id": "target-anchor",
                "file_id": 17,
                "source_generation": 42,
                "expected_byte_len": len(self.original),
                "expected_body_sha256": original_sha,
                "witness_ref": "fixture://source-owner/42",
                "checked_at": "2026-08-31T02:00:00Z",
            }],
        }
        self.graph = {
            "graph_id": "ASTGE-GRAPH-1",
            "graph_generation": 7,
            "graph_basis_identity": identity("graph-7"),
            "currentness": CURRENT,
            "witness_ref": "GRAPH:7:CURRENT",
        }
        capsule = {
            "capsule_id": "CAP-O19-1",
            "capsule_generation": 3,
            "parent_work_order_interface_binding_generation": 5,
            "execution_basis_identity": identity("basis-3"),
        }
        prior_source = {
            "role": ACTIVE,
            "file_id": 17,
            "relative_path": "src/a.py",
            "source_generation": 42,
            "source_sha256": original_sha,
            "source_byte_len": len(self.original),
            "currentness": CURRENT,
            "witness_ref": "fixture://prior-current/42",
        }
        self.previous = compile_workcapsule_context_binding(
            capsule=capsule,
            graph_witness=self.graph,
            source_witnesses=[prior_source],
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def compile(self, *, witness=None, observed_graph=None, candidate_graph=None):
        return compile_raw_owner_end_to_end_stale_lifecycle(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=self.witness if witness is None else witness,
            previous_binding=self.previous,
            observed_graph_witness=self.graph if observed_graph is None else observed_graph,
            candidate_graph_witness=self.graph if candidate_graph is None else candidate_graph,
        )

    def verify(self, receipt, *, witness=None, observed_graph=None, candidate_graph=None):
        return verify_raw_owner_end_to_end_stale_lifecycle(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=self.witness if witness is None else witness,
            previous_binding=self.previous,
            observed_graph_witness=self.graph if observed_graph is None else observed_graph,
            candidate_graph_witness=self.graph if candidate_graph is None else candidate_graph,
            lifecycle_receipt=receipt,
        )

    def test_stale_raw_evidence_derives_o8_internally_and_holds(self) -> None:
        self.path.write_bytes(self.stale)
        receipt = self.compile()
        self.assertEqual("HOLD", receipt["closure_status"])
        self.assertTrue(receipt["raw_owner_end_to_end_reproduction"])
        self.assertFalse(receipt["caller_reentry_receipt_accepted"])
        self.assertFalse(receipt["caller_source_observation_receipt_accepted"])
        self.assertFalse(receipt["caller_source_witnesses_accepted"])
        self.assertFalse(receipt["caller_candidate_binding_accepted"])
        self.assertFalse(receipt["source_currentness_minted"])
        self.assertFalse(receipt["stale_observed_bytes_bound_to_source_generation"])
        self.assertFalse(any(receipt["authority"].values()))
        self.assertEqual([], self.verify(receipt))

    def test_unknown_raw_evidence_remains_unresolved_and_holds(self) -> None:
        empty = {"version": WITNESS_VERSION, "witnesses": []}
        receipt = self.compile(witness=empty)
        self.assertEqual("HOLD", receipt["closure_status"])
        self.assertFalse(receipt["unknown_identity_guessed"])
        self.assertFalse(receipt["source_currentness_minted"])
        self.assertEqual([], self.verify(receipt, witness=empty))

    def test_current_only_evidence_is_rejected_from_specialized_stale_lifecycle(self) -> None:
        with self.assertRaises(ValueError):
            self.compile()

    def test_public_boundary_has_no_intermediate_receipt_or_candidate_escape_hatch(self) -> None:
        compile_params = inspect.signature(compile_raw_owner_end_to_end_stale_lifecycle).parameters
        for forbidden in (
            "reentry_receipt",
            "source_observation_receipt",
            "observed_source_witnesses",
            "candidate_binding",
        ):
            self.assertNotIn(forbidden, compile_params)
        self.assertIn("witness_manifest", compile_params)
        self.assertIn("observed_graph_witness", compile_params)
        self.assertIn("candidate_graph_witness", compile_params)

    def test_old_lifecycle_fails_after_raw_stale_bytes_change(self) -> None:
        self.path.write_bytes(self.stale)
        receipt = self.compile()
        self.path.write_bytes(self.other_stale)
        self.assertIn(
            "RAW_OWNER_STALE_LIFECYCLE_NOT_EXACT_REPRODUCTION",
            self.verify(receipt),
        )

    def test_old_lifecycle_fails_after_graph_change(self) -> None:
        self.path.write_bytes(self.stale)
        receipt = self.compile()
        changed = copy.deepcopy(self.graph)
        changed["graph_generation"] = 8
        changed["graph_basis_identity"] = identity("graph-8")
        changed["witness_ref"] = "GRAPH:8:CURRENT"
        self.assertNotEqual([], self.verify(receipt, observed_graph=changed, candidate_graph=changed))


if __name__ == "__main__":
    unittest.main()
