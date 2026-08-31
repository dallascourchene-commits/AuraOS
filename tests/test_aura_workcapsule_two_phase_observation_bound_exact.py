from __future__ import annotations

import copy
import hashlib
import inspect
from pathlib import Path
import tempfile
import unittest

from scripts.aura_astge_anchor_hydration import WITNESS_VERSION
from scripts.aura_workcapsule_context_binding import ACTIVE, CURRENT, compile_workcapsule_context_binding
from scripts.aura_workcapsule_observation_bound_closure import CLOSED, HOLD, compile_observation_bound_reentry_closure
from scripts.aura_workcapsule_observation_bound_exact_verifier import verify_exact_observation_bound_reentry_closure
from scripts.aura_workcapsule_source_bound_exact_reentry import compile_expected_source_bound_reentry
from scripts.aura_workcapsule_two_phase_observation_bound_exact import (
    SAME_PHASE_ROOT,
    admit_two_phase_observation_bound_exact,
    verify_two_phase_observation_bound_exact,
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


class WorkCapsuleTwoPhaseObservationBoundExactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pre_tmp = tempfile.TemporaryDirectory(prefix="aura-o26-pre-")
        self.post_tmp = tempfile.TemporaryDirectory(prefix="aura-o26-post-")
        self.foreign_tmp = tempfile.TemporaryDirectory(prefix="aura-o26-foreign-")
        self.pre_root = Path(self.pre_tmp.name)
        self.post_root = Path(self.post_tmp.name)
        self.foreign_root = Path(self.foreign_tmp.name)
        for root in (self.pre_root, self.post_root, self.foreign_root):
            (root / "src").mkdir()

        self.original = b"def target(x):\n    return x + 1\n"
        self.stale = b"def target(x):\n    return x + 2\n"
        self.repaired = b"def target(x):\n    return x + 3\n"
        self.foreign = b"def target(x):\n    return x + 4\n"
        self.assertEqual(len(self.original), len(self.stale))
        self.assertEqual(len(self.original), len(self.repaired))
        self.assertEqual(len(self.original), len(self.foreign))
        (self.pre_root / "src/a.py").write_bytes(self.stale)
        (self.post_root / "src/a.py").write_bytes(self.repaired)
        (self.foreign_root / "src/a.py").write_bytes(self.foreign)

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
        self.pre_witness = self.witness(42, self.original, "pre")
        self.post_witness = self.witness(43, self.repaired, "post")
        self.foreign_witness = self.witness(44, self.foreign, "foreign")
        self.graph = {
            "graph_id": "ASTGE-GRAPH-O26",
            "graph_generation": 7,
            "graph_basis_identity": identity("graph-o26-7"),
            "currentness": CURRENT,
            "witness_ref": "GRAPH:O26:7:CURRENT",
        }
        self.capsule = {
            "capsule_id": "CAP-O26-1",
            "capsule_generation": 3,
            "parent_work_order_interface_binding_generation": 5,
            "execution_basis_identity": identity("basis-o26"),
        }
        original_sha = hashlib.sha256(self.original).hexdigest()
        self.previous = compile_workcapsule_context_binding(
            capsule=self.capsule,
            graph_witness=self.graph,
            source_witnesses=[{
                "role": ACTIVE,
                "file_id": 17,
                "relative_path": "src/a.py",
                "source_generation": 42,
                "source_sha256": original_sha,
                "source_byte_len": len(self.original),
                "currentness": CURRENT,
                "witness_ref": "fixture://prior/42",
            }],
        )
        _, self.reentry = compile_expected_source_bound_reentry(
            root=self.pre_root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=self.pre_witness,
            previous_binding=self.previous,
            observed_graph_witness=self.graph,
        )
        self.receipt = self.compile_post(self.post_root, self.post_witness, self.graph)
        self.assertEqual(CLOSED, self.receipt["closure_status"])

    def tearDown(self) -> None:
        self.pre_tmp.cleanup()
        self.post_tmp.cleanup()
        self.foreign_tmp.cleanup()

    def witness(self, generation: int, body: bytes, label: str) -> dict:
        return {
            "version": WITNESS_VERSION,
            "witnesses": [{
                "anchor_id": "target-anchor",
                "file_id": 17,
                "source_generation": generation,
                "expected_byte_len": len(body),
                "expected_body_sha256": hashlib.sha256(body).hexdigest(),
                "witness_ref": f"fixture://{label}/{generation}",
                "checked_at": "2026-08-31T02:00:00Z",
            }],
        }

    def compile_post(self, root: Path, witness: dict, graph: dict) -> dict:
        return copy.deepcopy(compile_observation_bound_reentry_closure(
            root=root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=witness,
            previous_binding=self.previous,
            reentry_receipt=self.reentry,
            candidate_graph_witness=graph,
        ))

    def verify(self, receipt=None, *, pre_root=None, post_root=None, post_witness=None, post_graph=None):
        return verify_two_phase_observation_bound_exact(
            pre_root=pre_root if pre_root is not None else self.pre_root,
            pre_codemap=self.codemap,
            pre_anchor_manifest=self.anchors,
            pre_witness_manifest=self.pre_witness,
            previous_binding=self.previous,
            pre_graph_witness=self.graph,
            reentry_receipt=self.reentry,
            post_root=post_root if post_root is not None else self.post_root,
            post_codemap=self.codemap,
            post_anchor_manifest=self.anchors,
            post_witness_manifest=post_witness if post_witness is not None else self.post_witness,
            post_graph_witness=post_graph if post_graph is not None else self.graph,
            observation_bound_receipt=receipt if receipt is not None else self.receipt,
        )

    def test_exact_two_phase_closed_observation_receipt_replays_both_owners(self) -> None:
        self.assertEqual([], self.verify())
        admission = admit_two_phase_observation_bound_exact(
            pre_root=self.pre_root,
            pre_codemap=self.codemap,
            pre_anchor_manifest=self.anchors,
            pre_witness_manifest=self.pre_witness,
            previous_binding=self.previous,
            pre_graph_witness=self.graph,
            reentry_receipt=self.reentry,
            post_root=self.post_root,
            post_codemap=self.codemap,
            post_anchor_manifest=self.anchors,
            post_witness_manifest=self.post_witness,
            post_graph_witness=self.graph,
            observation_bound_receipt=self.receipt,
        )
        self.assertTrue(admission["two_phase_observation_bound_exact_reproduction"])
        self.assertTrue(admission["pre_and_post_evidence_are_distinct_phases"])
        self.assertTrue(admission["inner_two_phase_exact_lifecycle_replayed"])
        self.assertEqual(CLOSED, admission["closure_status"])
        self.assertFalse(admission["source_currentness_minted"])
        self.assertFalse(any(admission["authority"].values()))

    def test_same_live_root_cannot_impersonate_two_temporal_phases(self) -> None:
        self.assertEqual([SAME_PHASE_ROOT], self.verify(post_root=self.pre_root))

    def test_pre_phase_drift_invalidates_reentry_before_post_receipt_matters(self) -> None:
        (self.pre_root / "src/a.py").write_bytes(self.original)
        violations = self.verify()
        self.assertTrue(any(item.startswith("PRE_") for item in violations))

    def test_exact_foreign_post_receipt_rejected_against_pinned_post_snapshot(self) -> None:
        foreign_receipt = self.compile_post(self.foreign_root, self.foreign_witness, self.graph)
        self.assertEqual(
            [],
            verify_exact_observation_bound_reentry_closure(
                root=self.foreign_root,
                codemap=self.codemap,
                anchor_manifest=self.anchors,
                witness_manifest=self.foreign_witness,
                previous_binding=self.previous,
                reentry_receipt=self.reentry,
                candidate_graph_witness=self.graph,
                receipt=foreign_receipt,
            ),
        )
        violations = self.verify(foreign_receipt)
        self.assertTrue(any(item.startswith("POST_") for item in violations))

    def test_exact_post_hold_is_preserved_without_fabricating_inner_lifecycle(self) -> None:
        changed_graph = copy.deepcopy(self.graph)
        changed_graph["graph_generation"] = 8
        changed_graph["graph_basis_identity"] = identity("graph-o26-8")
        changed_graph["witness_ref"] = "GRAPH:O26:8:CURRENT"
        receipt = self.compile_post(self.post_root, self.post_witness, changed_graph)
        self.assertEqual(HOLD, receipt["closure_status"])
        self.assertEqual([], self.verify(receipt, post_graph=changed_graph))
        admission = admit_two_phase_observation_bound_exact(
            pre_root=self.pre_root,
            pre_codemap=self.codemap,
            pre_anchor_manifest=self.anchors,
            pre_witness_manifest=self.pre_witness,
            previous_binding=self.previous,
            pre_graph_witness=self.graph,
            reentry_receipt=self.reentry,
            post_root=self.post_root,
            post_codemap=self.codemap,
            post_anchor_manifest=self.anchors,
            post_witness_manifest=self.post_witness,
            post_graph_witness=changed_graph,
            observation_bound_receipt=receipt,
        )
        self.assertEqual(HOLD, admission["closure_status"])
        self.assertFalse(admission["inner_two_phase_exact_lifecycle_replayed"])
        self.assertFalse(any(admission["authority"].values()))

    def test_public_boundary_has_no_candidate_or_source_witness_escape_hatch(self) -> None:
        params = inspect.signature(verify_two_phase_observation_bound_exact).parameters
        self.assertNotIn("candidate_binding", params)
        self.assertNotIn("observed_source_witnesses", params)
        self.assertIn("pre_root", params)
        self.assertIn("post_root", params)
        self.assertIn("observation_bound_receipt", params)


if __name__ == "__main__":
    unittest.main()
