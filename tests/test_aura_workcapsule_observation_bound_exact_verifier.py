from __future__ import annotations

import copy
import hashlib
import inspect
import json
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
from scripts.aura_workcapsule_observation_bound_exact_verifier import (
    DERIVED_CANDIDATE_IDENTITY_MISMATCH,
    EXACT_OBSERVATION_BOUND_INPUT_MISMATCH,
    PREVIOUS_BINDING_IDENTITY_MISMATCH,
    REENTRY_RECEIPT_IDENTITY_MISMATCH,
    SOURCE_OBSERVATION_IDENTITY_MISMATCH,
    admit_exact_observation_bound_reentry_closure,
    verify_exact_observation_bound_reentry_closure,
)
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


def reseal_outer(receipt: dict) -> None:
    without = copy.deepcopy(receipt)
    prior = without.pop("receipt_identity")
    canonical = json.dumps(without, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    new_identity = copy.deepcopy(prior)
    new_identity["value"] = hashlib.sha256(canonical).hexdigest()
    receipt["receipt_identity"] = new_identity


class WorkCapsuleObservationBoundExactVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="aura-observation-bound-exact-")
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
            "capsule_id": "CAP-O12-1",
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

    def verify(self, receipt, *, graph=None, witness=None):
        return verify_exact_observation_bound_reentry_closure(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=witness if witness is not None else self.witness,
            previous_binding=self.previous,
            reentry_receipt=self.reentry,
            candidate_graph_witness=graph if graph is not None else self.graph,
            receipt=receipt,
        )

    def test_exact_current_closed_receipt_roundtrips_and_admits(self) -> None:
        self.path.write_bytes(self.original)
        receipt = self.compile()
        self.assertEqual(CLOSED, receipt["closure_status"])
        self.assertEqual([], self.verify(receipt))
        admitted = admit_exact_observation_bound_reentry_closure(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=self.witness,
            previous_binding=self.previous,
            reentry_receipt=self.reentry,
            candidate_graph_witness=self.graph,
            receipt=receipt,
        )
        self.assertTrue(admitted["exact_observation_bound_input_reproduction"])
        self.assertTrue(admitted["inner_closure_exact_reproduction"])
        self.assertEqual(CLOSED, admitted["closure_status"])
        self.assertFalse(admitted["producer_identity_authenticated"])
        self.assertFalse(admitted["semantic_truth_minted"])
        self.assertFalse(any(admitted["authority"].values()))

    def test_resealed_previous_binding_identity_substitution_is_rejected(self) -> None:
        self.path.write_bytes(self.original)
        tampered = self.compile()
        tampered["previous_binding_identity"]["value"] = "f" * 64
        reseal_outer(tampered)
        self.assertEqual([], verify_observation_bound_reentry_closure(tampered))
        violations = self.verify(tampered)
        self.assertIn(PREVIOUS_BINDING_IDENTITY_MISMATCH, violations)
        self.assertIn(EXACT_OBSERVATION_BOUND_INPUT_MISMATCH, violations)

    def test_resealed_reentry_identity_substitution_is_rejected(self) -> None:
        self.path.write_bytes(self.original)
        tampered = self.compile()
        tampered["reentry_receipt_identity"]["value"] = "e" * 64
        reseal_outer(tampered)
        self.assertEqual([], verify_observation_bound_reentry_closure(tampered))
        violations = self.verify(tampered)
        self.assertIn(REENTRY_RECEIPT_IDENTITY_MISMATCH, violations)
        self.assertIn(EXACT_OBSERVATION_BOUND_INPUT_MISMATCH, violations)

    def test_resealed_embedded_source_observation_identity_substitution_is_rejected(self) -> None:
        self.path.write_bytes(self.original)
        tampered = self.compile()
        fake = "d" * 64
        tampered["source_observation"]["receipt_identity"]["value"] = fake
        tampered["source_observation_identity"]["value"] = fake
        reseal_outer(tampered)
        self.assertEqual([], verify_observation_bound_reentry_closure(tampered))
        violations = self.verify(tampered)
        self.assertIn(SOURCE_OBSERVATION_IDENTITY_MISMATCH, violations)
        self.assertIn(EXACT_OBSERVATION_BOUND_INPUT_MISMATCH, violations)

    def test_resealed_derived_candidate_identity_substitution_is_rejected(self) -> None:
        self.path.write_bytes(self.original)
        tampered = self.compile()
        fake = "c" * 64
        tampered["derived_candidate_binding"]["binding_identity"]["value"] = fake
        tampered["derived_candidate_binding_identity"]["value"] = fake
        reseal_outer(tampered)
        self.assertEqual([], verify_observation_bound_reentry_closure(tampered))
        violations = self.verify(tampered)
        self.assertIn(DERIVED_CANDIDATE_IDENTITY_MISMATCH, violations)
        self.assertIn(EXACT_OBSERVATION_BOUND_INPUT_MISMATCH, violations)

    def test_old_receipt_rejected_after_raw_source_changes(self) -> None:
        self.path.write_bytes(self.original)
        receipt = self.compile()
        self.path.write_bytes(self.mutated)
        violations = self.verify(receipt)
        self.assertIn(SOURCE_OBSERVATION_IDENTITY_MISMATCH, violations)
        self.assertIn(EXACT_OBSERVATION_BOUND_INPUT_MISMATCH, violations)

    def test_old_receipt_rejected_against_changed_graph_witness(self) -> None:
        self.path.write_bytes(self.original)
        receipt = self.compile()
        changed = copy.deepcopy(self.graph)
        changed["graph_generation"] = 8
        changed["graph_basis_identity"] = identity("graph-8")
        changed["witness_ref"] = "GRAPH:8:CURRENT"
        violations = self.verify(receipt, graph=changed)
        self.assertIn(DERIVED_CANDIDATE_IDENTITY_MISMATCH, violations)
        self.assertIn(EXACT_OBSERVATION_BOUND_INPUT_MISMATCH, violations)

    def test_exact_hold_is_reproducible_but_not_promoted(self) -> None:
        receipt = self.compile()
        self.assertEqual(HOLD, receipt["closure_status"])
        self.assertIsNone(receipt["closure_receipt"])
        self.assertEqual([], self.verify(receipt))
        admitted = admit_exact_observation_bound_reentry_closure(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=self.witness,
            previous_binding=self.previous,
            reentry_receipt=self.reentry,
            candidate_graph_witness=self.graph,
            receipt=receipt,
        )
        self.assertEqual(HOLD, admitted["closure_status"])
        self.assertFalse(admitted["inner_closure_exact_reproduction"])
        self.assertFalse(admitted["semantic_truth_minted"])
        self.assertFalse(any(admitted["authority"].values()))

    def test_public_exact_verifier_has_no_candidate_or_source_witness_escape_hatch(self) -> None:
        params = inspect.signature(verify_exact_observation_bound_reentry_closure).parameters
        self.assertNotIn("candidate_binding", params)
        self.assertNotIn("observed_source_witnesses", params)
        self.assertIn("root", params)
        self.assertIn("witness_manifest", params)
        self.assertIn("candidate_graph_witness", params)


if __name__ == "__main__":
    unittest.main()
