from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path
import tempfile
import unittest

from scripts.aura_astge_anchor_hydration import WITNESS_VERSION
from scripts.aura_workcapsule_canonical_stale_lifecycle import (
    LIFECYCLE_NOT_EXACT_RAW_INPUT_REPRODUCTION,
    PROJECTION_IDENTITY_SPLIT_BRAIN,
    REENTRY_PATH_DECISION_MISMATCH,
    compile_canonical_stale_lifecycle,
    verify_canonical_stale_lifecycle,
    verify_canonical_stale_lifecycle_receipt,
)
from scripts.aura_workcapsule_context_binding import ACTIVE, CURRENT, compile_workcapsule_context_binding
from scripts.aura_workcapsule_observation_bound_closure import HOLD, compile_observation_bound_reentry_closure
from scripts.aura_workcapsule_reentry_invalidation import FULL_GRAPH, SELECTED_SOURCES, compile_reentry_invalidation
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


def reseal(receipt: dict) -> None:
    without = copy.deepcopy(receipt)
    prior = without.pop("receipt_identity")
    canonical = json.dumps(without, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    new_identity = copy.deepcopy(prior)
    new_identity["value"] = hashlib.sha256(canonical).hexdigest()
    receipt["receipt_identity"] = new_identity


class CanonicalStaleLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="aura-canonical-stale-lifecycle-")
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
                    "checked_at": "2026-08-31T02:00:00Z",
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
        self.previous = compile_workcapsule_context_binding(
            capsule={
                "capsule_id": "CAP-O12-1",
                "capsule_generation": 3,
                "parent_work_order_interface_binding_generation": 5,
                "execution_basis_identity": identity("basis-3"),
            },
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

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def evidence(self, *, witness=None, observed_graph=None, candidate_graph=None):
        witness_manifest = witness if witness is not None else self.witness
        observed = observed_graph if observed_graph is not None else self.graph
        candidate = candidate_graph if candidate_graph is not None else self.graph
        projection = compile_source_reentry_observations(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=witness_manifest,
            previous_binding=self.previous,
        )
        reentry = compile_reentry_invalidation(
            previous_binding=self.previous,
            observed_graph_witness=observed,
            observed_source_witnesses=projection["o7_source_witnesses"],
        )
        closure = compile_observation_bound_reentry_closure(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=witness_manifest,
            previous_binding=self.previous,
            reentry_receipt=reentry,
            candidate_graph_witness=candidate,
        )
        return projection, reentry, closure, observed, candidate

    def lifecycle(self, *, witness=None, observed_graph=None, candidate_graph=None):
        projection, reentry, closure, observed, candidate = self.evidence(
            witness=witness, observed_graph=observed_graph, candidate_graph=candidate_graph
        )
        receipt = compile_canonical_stale_lifecycle(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=witness if witness is not None else self.witness,
            previous_binding=self.previous,
            reentry_receipt=reentry,
            observed_graph_witness=observed,
            candidate_graph_witness=candidate,
            closure_receipt=closure,
        )
        return projection, reentry, closure, receipt, observed, candidate

    def test_stale_selected_source_converges_one_projection_two_reentry_paths_and_hold(self):
        projection, reentry, _, receipt, _, _ = self.lifecycle()
        self.assertEqual(SELECTED_SOURCES, reentry["minimum_reentry_scope"])
        self.assertEqual(HOLD, receipt["closure_status"])
        self.assertTrue(receipt["projection_identity_continuity_proven"])
        self.assertTrue(receipt["reentry_path_equivalence_proven"])
        self.assertEqual(projection["receipt_identity"], receipt["source_projection_identity"])
        self.assertEqual(
            projection["receipt_identity"],
            receipt["raw_owner_stale_safe_admission"]["source_projection_receipt_identity"],
        )
        self.assertEqual(
            projection["receipt_identity"],
            receipt["stale_observation_closure_admission"]["source_observation_identity"],
        )
        self.assertEqual([], verify_canonical_stale_lifecycle_receipt(receipt))
        self.assertFalse(any(receipt["authority"].values()))

    def test_unknown_projection_converges_without_identity_guess_and_holds(self):
        empty = {"version": WITNESS_VERSION, "witnesses": []}
        projection, reentry, _, receipt, _, _ = self.lifecycle(witness=empty)
        self.assertEqual(SELECTED_SOURCES, reentry["minimum_reentry_scope"])
        self.assertEqual(1, len(projection["unresolved_prior_sources"]))
        self.assertFalse(projection["unresolved_prior_sources"][0]["identity_guessed"])
        self.assertEqual(HOLD, receipt["closure_status"])
        self.assertFalse(receipt["unknown_identity_guessed"])
        self.assertEqual([], verify_canonical_stale_lifecycle_receipt(receipt))

    def test_full_graph_reentry_paths_converge_without_source_currentness_minting(self):
        changed = copy.deepcopy(self.graph)
        changed["graph_generation"] = 8
        changed["graph_basis_identity"] = identity("graph-8")
        changed["witness_ref"] = "GRAPH:8:CURRENT"
        _, reentry, _, receipt, _, _ = self.lifecycle(observed_graph=changed, candidate_graph=changed)
        self.assertEqual(FULL_GRAPH, reentry["minimum_reentry_scope"])
        self.assertEqual(FULL_GRAPH, receipt["canonical_reentry_decision"]["minimum_reentry_scope"])
        self.assertEqual(HOLD, receipt["closure_status"])
        self.assertFalse(receipt["source_currentness_minted"])
        self.assertFalse(receipt["observed_graph_producer_authenticated"])

    def test_observed_and_candidate_graph_roles_are_distinct_even_when_values_differ(self):
        candidate = copy.deepcopy(self.graph)
        candidate["graph_generation"] = 9
        candidate["graph_basis_identity"] = identity("candidate-9")
        candidate["witness_ref"] = "GRAPH:9:CURRENT"
        _, _, _, receipt, _, _ = self.lifecycle(candidate_graph=candidate)
        self.assertEqual("REENTRY_OBSERVATION", receipt["observed_graph_phase"]["role"])
        self.assertEqual("CLOSURE_CANDIDATE", receipt["candidate_graph_phase"]["role"])
        self.assertNotEqual(
            receipt["observed_graph_phase"]["graph_generation"],
            receipt["candidate_graph_phase"]["graph_generation"],
        )
        self.assertEqual(HOLD, receipt["closure_status"])

    def test_resealed_projection_identity_split_brain_is_rejected(self):
        _, _, _, receipt, _, _ = self.lifecycle()
        tampered = copy.deepcopy(receipt)
        tampered["source_projection_identity"]["value"] = "f" * 64
        reseal(tampered)
        violations = verify_canonical_stale_lifecycle_receipt(tampered)
        self.assertIn(PROJECTION_IDENTITY_SPLIT_BRAIN, violations)

    def test_resealed_canonical_decision_split_brain_is_rejected(self):
        _, _, _, receipt, _, _ = self.lifecycle()
        tampered = copy.deepcopy(receipt)
        tampered["canonical_reentry_decision"]["minimum_reentry_scope"] = FULL_GRAPH
        reseal(tampered)
        violations = verify_canonical_stale_lifecycle_receipt(tampered)
        self.assertIn(REENTRY_PATH_DECISION_MISMATCH, violations)

    def test_foreign_raw_world_lifecycle_is_not_exact_for_current_raw_world(self):
        self.path.write_bytes(self.stale_b)
        _, reentry_b, closure_b, lifecycle_b, observed_b, candidate_b = self.lifecycle()
        self.path.write_bytes(self.stale_a)
        violations = verify_canonical_stale_lifecycle(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=self.witness,
            previous_binding=self.previous,
            reentry_receipt=reentry_b,
            observed_graph_witness=observed_b,
            candidate_graph_witness=candidate_b,
            closure_receipt=closure_b,
            lifecycle_receipt=lifecycle_b,
        )
        self.assertTrue(
            LIFECYCLE_NOT_EXACT_RAW_INPUT_REPRODUCTION in violations
            or any(item.startswith("EXPECTED_LIFECYCLE_RECOMPILE_FAILED:") for item in violations)
        )

    def test_public_boundary_has_no_projection_witness_or_sibling_admission_escape_hatch(self):
        params = inspect.signature(compile_canonical_stale_lifecycle).parameters
        self.assertNotIn("source_observation_receipt", params)
        self.assertNotIn("observed_source_witnesses", params)
        self.assertNotIn("raw_owner_admission", params)
        self.assertNotIn("stale_safe_admission", params)
        self.assertIn("root", params)
        self.assertIn("observed_graph_witness", params)
        self.assertIn("candidate_graph_witness", params)


if __name__ == "__main__":
    unittest.main()
