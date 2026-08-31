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
from scripts.aura_workcapsule_reentry_invalidation import SELECTED_SOURCES, compile_reentry_invalidation
from scripts.aura_workcapsule_source_reentry_observation import compile_source_reentry_observations
from scripts.aura_workcapsule_stale_observation_closure_exact_verifier import (
    RAW_INPUT_CLOSURE_MISMATCH,
    REJECTED_CURRENTNESS_MUST_HOLD,
    STALE_SAFE_REENTRY_INVALID_PREFIX,
    admit_stale_observation_closure_exact_reproduction,
    verify_stale_observation_closure_exact_reproduction,
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


class WorkCapsuleStaleObservationClosureExactVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="aura-stale-observation-closure-exact-")
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        self.original = b"def target(x):\n    return x + 1\n"
        self.stale_a = b"def target(x):\n    return x + 2\n"
        self.stale_b = b"def target(x):\n    return x + 3\n"
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
                    "checked_at": "2026-08-31T01:50:00Z",
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
            "capsule_id": "CAP-O25-1",
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
        self.path.write_bytes(self.stale_a)
        stale = self.observation()
        self.reentry = compile_reentry_invalidation(
            previous_binding=self.previous,
            observed_graph_witness=self.graph,
            observed_source_witnesses=stale["o7_source_witnesses"],
        )
        self.assertEqual(SELECTED_SOURCES, self.reentry["minimum_reentry_scope"])

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def observation(self, *, witness=None):
        return compile_source_reentry_observations(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=witness if witness is not None else self.witness,
            previous_binding=self.previous,
        )

    def closure(self, *, witness=None, graph=None):
        return compile_observation_bound_reentry_closure(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=witness if witness is not None else self.witness,
            previous_binding=self.previous,
            reentry_receipt=self.reentry,
            candidate_graph_witness=graph if graph is not None else self.graph,
        )

    def verify(self, receipt, *, witness=None, observed_graph=None, candidate_graph=None):
        return verify_stale_observation_closure_exact_reproduction(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=witness if witness is not None else self.witness,
            previous_binding=self.previous,
            reentry_receipt=self.reentry,
            observed_graph_witness=observed_graph if observed_graph is not None else self.graph,
            candidate_graph_witness=candidate_graph if candidate_graph is not None else self.graph,
            closure_receipt=receipt,
        )

    def test_stale_raw_evidence_exactly_reproduces_hold_without_currentness_minting(self):
        receipt = self.closure()
        self.assertEqual(HOLD, receipt["closure_status"])
        self.assertEqual([], self.verify(receipt))
        admitted = admit_stale_observation_closure_exact_reproduction(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=self.witness,
            previous_binding=self.previous,
            reentry_receipt=self.reentry,
            observed_graph_witness=self.graph,
            candidate_graph_witness=self.graph,
            closure_receipt=receipt,
        )
        self.assertTrue(admitted["raw_input_bound_reproduction"])
        self.assertTrue(admitted["rejected_currentness_path"])
        self.assertEqual(HOLD, admitted["closure_status"])
        self.assertTrue(admitted["reentry_required"])
        self.assertFalse(admitted["source_currentness_minted"])
        self.assertFalse(admitted["stale_observed_bytes_bound_to_source_generation"])
        self.assertFalse(admitted["producer_identity_authenticated"])
        self.assertFalse(any(admitted["authority"].values()))

    def test_missing_witness_unknown_exactly_reproduces_hold_without_identity_guess(self):
        empty = {"version": WITNESS_VERSION, "witnesses": []}
        observation = self.observation(witness=empty)
        reentry = compile_reentry_invalidation(
            previous_binding=self.previous,
            observed_graph_witness=self.graph,
            observed_source_witnesses=observation["o7_source_witnesses"],
        )
        receipt = compile_observation_bound_reentry_closure(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=empty,
            previous_binding=self.previous,
            reentry_receipt=reentry,
            candidate_graph_witness=self.graph,
        )
        violations = verify_stale_observation_closure_exact_reproduction(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=empty,
            previous_binding=self.previous,
            reentry_receipt=reentry,
            observed_graph_witness=self.graph,
            candidate_graph_witness=self.graph,
            closure_receipt=receipt,
        )
        self.assertEqual([], violations)
        self.assertEqual(HOLD, receipt["closure_status"])
        self.assertFalse(receipt["source_observation"]["unresolved_prior_sources"][0]["identity_guessed"])

    def test_coherent_receipt_for_different_raw_bytes_passes_parent_self_check_but_fails_raw_replay(self):
        self.path.write_bytes(self.stale_b)
        foreign = self.closure()
        self.assertEqual(HOLD, foreign["closure_status"])
        self.assertEqual([], verify_observation_bound_reentry_closure(foreign))

        self.path.write_bytes(self.stale_a)
        violations = self.verify(foreign)
        self.assertIn(RAW_INPUT_CLOSURE_MISMATCH, violations)

    def test_old_closure_rejected_when_witness_generation_changes(self):
        old = self.closure()
        changed = copy.deepcopy(self.witness)
        changed["witnesses"][0]["source_generation"] = 43
        violations = self.verify(old, witness=changed)
        self.assertTrue(
            RAW_INPUT_CLOSURE_MISMATCH in violations
            or any(item.startswith(STALE_SAFE_REENTRY_INVALID_PREFIX) for item in violations)
        )

    def test_current_only_raw_evidence_cannot_use_rejected_currentness_verifier(self):
        self.path.write_bytes(self.original)
        receipt = self.closure()
        self.assertEqual(CLOSED, receipt["closure_status"])
        violations = self.verify(receipt)
        self.assertTrue(any(item.startswith(STALE_SAFE_REENTRY_INVALID_PREFIX) for item in violations))
        self.assertIn(REJECTED_CURRENTNESS_MUST_HOLD, violations)

    def test_graph_drift_cannot_be_hidden_inside_exact_raw_reproduction(self):
        changed_graph = copy.deepcopy(self.graph)
        changed_graph["graph_generation"] = 8
        changed_graph["graph_basis_identity"] = identity("graph-8")
        changed_graph["witness_ref"] = "GRAPH:8:CURRENT"
        receipt = self.closure(graph=changed_graph)
        self.assertEqual(HOLD, receipt["closure_status"])
        self.assertEqual([], self.verify(receipt, candidate_graph=changed_graph))
        violations = self.verify(receipt, candidate_graph=self.graph)
        self.assertIn(RAW_INPUT_CLOSURE_MISMATCH, violations)


if __name__ == "__main__":
    unittest.main()
