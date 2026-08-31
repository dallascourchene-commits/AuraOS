from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import tempfile
import unittest

from scripts.aura_astge_anchor_hydration import WITNESS_VERSION
from scripts.aura_workcapsule_context_binding import ACTIVE, CURRENT, compile_workcapsule_context_binding
from scripts.aura_workcapsule_observation_bound_closure import (
    CLOSED,
    HOLD,
    compile_observation_bound_reentry_closure,
    verify_observation_bound_reentry_closure,
)
from scripts.aura_workcapsule_reentry_closure import compile_reentry_closure
from scripts.aura_workcapsule_reentry_invalidation import SELECTED_SOURCES, compile_reentry_invalidation
from scripts.aura_workcapsule_source_reentry_observation import compile_source_reentry_observations


def identity(value: str) -> dict[str, str]:
    return {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "TEST_V1",
        "scope_profile": "TEST_SCOPE",
        "value": value,
        "schema_version": "1",
    }


class WorkCapsuleObservationBoundClosureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="aura-observation-bound-closure-")
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        self.original = b"def target(x):\n    return x + 1\n"
        self.mutated = b"def target(x):\n    return x + 2\n"
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
            "capsule_id": "CAP-O11-1",
            "capsule_generation": 3,
            "parent_work_order_interface_binding_generation": 5,
            "execution_basis_identity": identity("basis-3"),
        }
        self.previous = compile_workcapsule_context_binding(
            capsule=self.capsule,
            graph_witness=self.graph,
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
        self.path.write_bytes(self.mutated)
        stale = compile_source_reentry_observations(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=self.witness,
            previous_binding=self.previous,
        )
        self.reentry = compile_reentry_invalidation(
            previous_binding=self.previous,
            observed_graph_witness=self.graph,
            observed_source_witnesses=stale["o7_source_witnesses"],
        )
        self.assertEqual(SELECTED_SOURCES, self.reentry["minimum_reentry_scope"])

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def compile(self, *, graph=None, witness=None):
        return compile_observation_bound_reentry_closure(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=witness if witness is not None else self.witness,
            previous_binding=self.previous,
            reentry_receipt=self.reentry,
            candidate_graph_witness=graph if graph is not None else self.graph,
        )

    def test_restored_current_source_is_derived_and_closes(self) -> None:
        self.path.write_bytes(self.original)
        receipt = self.compile()
        self.assertEqual(CLOSED, receipt["closure_status"])
        self.assertTrue(receipt["candidate_source_basis_derived_from_raw_currentness_inputs"])
        self.assertFalse(receipt["caller_candidate_binding_accepted"])
        self.assertEqual(42, receipt["derived_candidate_binding"]["source_witnesses"][0]["source_generation"])
        self.assertEqual(self.original_sha, receipt["derived_candidate_binding"]["source_witnesses"][0]["source_sha256"])
        self.assertEqual(receipt["source_observation"]["o7_source_witnesses"], receipt["derived_candidate_binding"]["source_witnesses"])
        self.assertEqual([], verify_observation_bound_reentry_closure(receipt))

    def test_direct_owner_can_accept_forged_selected_rebind_but_bound_membrane_derives_real_source(self) -> None:
        forged = compile_workcapsule_context_binding(
            capsule=self.capsule,
            graph_witness=self.graph,
            source_witnesses=[
                {
                    "role": ACTIVE,
                    "file_id": 17,
                    "relative_path": "src/a.py",
                    "source_generation": 999,
                    "source_sha256": "f" * 64,
                    "source_byte_len": 999,
                    "currentness": CURRENT,
                    "witness_ref": "caller://forged-current",
                }
            ],
        )
        direct = compile_reentry_closure(
            previous_binding=self.previous,
            reentry_receipt=self.reentry,
            candidate_binding=forged,
        )
        self.assertEqual(CLOSED, direct["closure_status"])

        self.path.write_bytes(self.original)
        bounded = self.compile()
        self.assertEqual(CLOSED, bounded["closure_status"])
        self.assertEqual(42, bounded["derived_candidate_binding"]["source_witnesses"][0]["source_generation"])
        self.assertNotEqual(forged["binding_identity"], bounded["derived_candidate_binding_identity"])

    def test_still_stale_raw_source_holds_without_caller_escape_hatch(self) -> None:
        receipt = self.compile()
        self.assertEqual(HOLD, receipt["closure_status"])
        self.assertIn("DERIVED_CANDIDATE_NOT_CURRENT", receipt["hold_reasons"])
        self.assertIsNone(receipt["closure_receipt"])
        self.assertFalse(receipt["derived_candidate_binding"]["context_admitted"])
        self.assertEqual([], verify_observation_bound_reentry_closure(receipt))

    def test_missing_source_witness_holds_and_never_guesses_candidate(self) -> None:
        empty = {"version": WITNESS_VERSION, "witnesses": []}
        receipt = self.compile(witness=empty)
        self.assertEqual(HOLD, receipt["closure_status"])
        self.assertEqual([], receipt["source_observation"]["o7_source_witnesses"])
        self.assertEqual(1, len(receipt["source_observation"]["unresolved_prior_sources"]))
        self.assertFalse(receipt["source_observation"]["unresolved_prior_sources"][0]["identity_guessed"])
        self.assertEqual([], verify_observation_bound_reentry_closure(receipt))

    def test_selected_source_closure_cannot_hide_graph_drift(self) -> None:
        self.path.write_bytes(self.original)
        graph = copy.deepcopy(self.graph)
        graph["graph_generation"] = 8
        graph["graph_basis_identity"] = identity("graph-8")
        graph["witness_ref"] = "GRAPH:8:CURRENT"
        receipt = self.compile(graph=graph)
        self.assertEqual(HOLD, receipt["closure_status"])
        self.assertIn("GRAPH_CHANGED_OUTSIDE_FULL_GRAPH_REENTRY", receipt["hold_reasons"])
        self.assertFalse(receipt["graph_witness_producer_proven"])
        self.assertEqual([], verify_observation_bound_reentry_closure(receipt))

    def test_source_generation_domain_survives_into_bound_receipt(self) -> None:
        self.path.write_bytes(self.original)
        receipt = self.compile()
        self.assertTrue(receipt["source_generation_domain_preserved"])
        coordinate = receipt["source_observation"]["source_observations"][0]["source_generation_coordinate"]
        self.assertEqual({"domain": "SOURCE", "value": 42}, coordinate)
        self.assertEqual([], verify_observation_bound_reentry_closure(receipt))

    def test_derived_source_basis_tamper_is_detected(self) -> None:
        self.path.write_bytes(self.original)
        receipt = self.compile()
        receipt["derived_candidate_binding"]["source_witnesses"][0]["source_generation"] = 999
        violations = verify_observation_bound_reentry_closure(receipt)
        self.assertIn("DERIVED_CANDIDATE_SOURCE_BASIS_MISMATCH", violations)
        self.assertIn("RECEIPT_IDENTITY_MISMATCH", violations)

    def test_authority_tamper_is_detected(self) -> None:
        self.path.write_bytes(self.original)
        receipt = self.compile()
        receipt["authority"]["execution_authorized"] = True
        violations = verify_observation_bound_reentry_closure(receipt)
        self.assertIn("AUTHORITY_MINTED_BY_OBSERVATION_BOUND_CLOSURE", violations)
        self.assertIn("RECEIPT_IDENTITY_MISMATCH", violations)


if __name__ == "__main__":
    unittest.main()
