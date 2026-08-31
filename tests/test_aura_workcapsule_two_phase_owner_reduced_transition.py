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
)
from scripts.aura_workcapsule_reentry_closure import compile_reentry_closure
from scripts.aura_workcapsule_source_bound_exact_reentry import compile_expected_source_bound_reentry
from scripts.aura_workcapsule_two_phase_owner_reduced_transition import (
    POST_PHASE_NOT_CLOSED,
    TWO_PHASE_PREFIX,
    admit_two_phase_owner_reduced_transition,
    verify_two_phase_owner_reduced_transition,
)
from scripts.aura_workcapsule_two_phase_source_bound_closure import derive_post_reentry_candidate


def identity(value: str) -> dict[str, str]:
    return {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "TEST_V1",
        "scope_profile": "TEST_SCOPE",
        "value": value,
        "schema_version": "1",
    }


class WorkCapsuleTwoPhaseOwnerReducedTransitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pre_tmp = tempfile.TemporaryDirectory(prefix="aura-transition-pre-")
        self.post_tmp = tempfile.TemporaryDirectory(prefix="aura-transition-post-")
        self.pre_root = Path(self.pre_tmp.name)
        self.post_root = Path(self.post_tmp.name)
        (self.pre_root / "src").mkdir()
        (self.post_root / "src").mkdir()

        self.original = b"def target(x):\n    return x + 1\n"
        self.stale = b"def target(x):\n    return x + 2\n"
        self.repaired = b"def target(x):\n    return x + 3\n"
        self.assertEqual(len(self.original), len(self.stale))
        self.assertEqual(len(self.original), len(self.repaired))
        (self.pre_root / "src/a.py").write_bytes(self.stale)
        (self.post_root / "src/a.py").write_bytes(self.repaired)
        self.original_sha = hashlib.sha256(self.original).hexdigest()
        self.repaired_sha = hashlib.sha256(self.repaired).hexdigest()

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
        self.pre_witness = self._witness(42, self.original, self.original_sha, "pre")
        self.post_witness = self._witness(43, self.repaired, self.repaired_sha, "post")
        self.graph = {
            "graph_id": "ASTGE-GRAPH-1",
            "graph_generation": 7,
            "graph_basis_identity": identity("graph-7"),
            "currentness": CURRENT,
            "witness_ref": "GRAPH:7:CURRENT",
        }
        self.capsule = {
            "capsule_id": "CAP-O26-1",
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
        _, self.reentry = compile_expected_source_bound_reentry(
            root=self.pre_root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=self.pre_witness,
            previous_binding=self.previous,
            observed_graph_witness=self.graph,
        )
        self.pre_observation = compile_observation_bound_reentry_closure(
            root=self.pre_root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=self.pre_witness,
            previous_binding=self.previous,
            reentry_receipt=self.reentry,
            candidate_graph_witness=self.graph,
        )
        self.assertEqual(HOLD, self.pre_observation["closure_status"])
        _, self.post_candidate = derive_post_reentry_candidate(
            post_root=self.post_root,
            post_codemap=self.codemap,
            post_anchor_manifest=self.anchors,
            post_witness_manifest=self.post_witness,
            previous_binding=self.previous,
            post_graph_witness=self.graph,
        )
        self.closure = compile_reentry_closure(
            previous_binding=self.previous,
            reentry_receipt=self.reentry,
            candidate_binding=self.post_candidate,
        )
        self.assertEqual(CLOSED, self.closure["closure_status"])

    def tearDown(self) -> None:
        self.pre_tmp.cleanup()
        self.post_tmp.cleanup()

    def _witness(self, generation: int, body: bytes, sha: str, label: str) -> dict:
        return {
            "version": WITNESS_VERSION,
            "witnesses": [
                {
                    "anchor_id": "target-anchor",
                    "file_id": 17,
                    "source_generation": generation,
                    "expected_byte_len": len(body),
                    "expected_body_sha256": sha,
                    "witness_ref": f"fixture://{label}-owner/{generation}",
                    "checked_at": "2026-08-31T02:20:00Z",
                }
            ],
        }

    def verify(self, *, pre_observation=None, post_root=None, post_witness=None, post_graph=None, closure=None):
        return verify_two_phase_owner_reduced_transition(
            pre_root=self.pre_root,
            pre_codemap=self.codemap,
            pre_anchor_manifest=self.anchors,
            pre_witness_manifest=self.pre_witness,
            previous_binding=self.previous,
            pre_graph_witness=self.graph,
            reentry_receipt=self.reentry,
            pre_observation_closure_receipt=pre_observation if pre_observation is not None else self.pre_observation,
            post_root=post_root if post_root is not None else self.post_root,
            post_codemap=self.codemap,
            post_anchor_manifest=self.anchors,
            post_witness_manifest=post_witness if post_witness is not None else self.post_witness,
            post_graph_witness=post_graph if post_graph is not None else self.graph,
            closure_receipt=closure if closure is not None else self.closure,
        )

    def test_exact_owner_reduced_hold_to_distinct_post_closed_transition(self) -> None:
        self.assertEqual([], self.verify())
        admitted = admit_two_phase_owner_reduced_transition(
            pre_root=self.pre_root,
            pre_codemap=self.codemap,
            pre_anchor_manifest=self.anchors,
            pre_witness_manifest=self.pre_witness,
            previous_binding=self.previous,
            pre_graph_witness=self.graph,
            reentry_receipt=self.reentry,
            pre_observation_closure_receipt=self.pre_observation,
            post_root=self.post_root,
            post_codemap=self.codemap,
            post_anchor_manifest=self.anchors,
            post_witness_manifest=self.post_witness,
            post_graph_witness=self.graph,
            closure_receipt=self.closure,
        )
        self.assertTrue(admitted["owner_reduced_pre_hold_proven"])
        self.assertTrue(admitted["two_phase_post_closed_proven"])
        self.assertEqual(HOLD, admitted["pre_closure_status"])
        self.assertEqual(CLOSED, admitted["post_closure_status"])
        self.assertTrue(admitted["same_pre_source_observation_witnessed_by_both_parents"])
        self.assertFalse(admitted["raw_replay_reimplemented_by_child"])
        self.assertFalse(any(admitted["authority"].values()))

    def test_foreign_pre_observation_receipt_is_rejected_by_general_owner(self) -> None:
        with tempfile.TemporaryDirectory(prefix="aura-transition-foreign-") as td:
            foreign_root = Path(td)
            (foreign_root / "src").mkdir()
            (foreign_root / "src/a.py").write_bytes(b"def target(x):\n    return x + 4\n")
            foreign = compile_observation_bound_reentry_closure(
                root=foreign_root,
                codemap=self.codemap,
                anchor_manifest=self.anchors,
                witness_manifest=self.pre_witness,
                previous_binding=self.previous,
                reentry_receipt=self.reentry,
                candidate_graph_witness=self.graph,
            )
        violations = self.verify(pre_observation=foreign)
        self.assertTrue(any(item.startswith("PRE_HOLD_GENERAL_EXACT_") for item in violations))

    def test_one_live_root_cannot_impersonate_pre_and_post_phases(self) -> None:
        violations = self.verify(post_root=self.pre_root)
        self.assertIn(TWO_PHASE_PREFIX + "PRE_POST_EVIDENCE_ROOTS_NOT_DISTINCT", violations)

    def test_current_only_pre_state_cannot_claim_rejected_currentness_hold(self) -> None:
        (self.pre_root / "src/a.py").write_bytes(self.original)
        _, current_reentry = compile_expected_source_bound_reentry(
            root=self.pre_root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=self.pre_witness,
            previous_binding=self.previous,
            observed_graph_witness=self.graph,
        )
        current_observation = compile_observation_bound_reentry_closure(
            root=self.pre_root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=self.pre_witness,
            previous_binding=self.previous,
            reentry_receipt=current_reentry,
            candidate_graph_witness=self.graph,
        )
        self.assertEqual(CLOSED, current_observation["closure_status"])
        violations = verify_two_phase_owner_reduced_transition(
            pre_root=self.pre_root,
            pre_codemap=self.codemap,
            pre_anchor_manifest=self.anchors,
            pre_witness_manifest=self.pre_witness,
            previous_binding=self.previous,
            pre_graph_witness=self.graph,
            reentry_receipt=current_reentry,
            pre_observation_closure_receipt=current_observation,
            post_root=self.post_root,
            post_codemap=self.codemap,
            post_anchor_manifest=self.anchors,
            post_witness_manifest=self.post_witness,
            post_graph_witness=self.graph,
            closure_receipt=self.closure,
        )
        self.assertTrue(any(item.startswith("PRE_HOLD_STALE_SAFE_") or item.endswith("MUST_HOLD") for item in violations))

    def test_post_source_still_stale_cannot_complete_transition(self) -> None:
        (self.post_root / "src/a.py").write_bytes(b"def target(x):\n    return x + 4\n")
        violations = self.verify()
        self.assertIn(TWO_PHASE_PREFIX + "POST_DERIVED_CANDIDATE_NOT_CURRENT", violations)

    def test_exact_post_hold_is_not_promoted_to_closed_transition(self) -> None:
        graph8 = copy.deepcopy(self.graph)
        graph8["graph_generation"] = 8
        graph8["graph_basis_identity"] = identity("graph-8")
        graph8["witness_ref"] = "GRAPH:8:CURRENT"
        _, candidate = derive_post_reentry_candidate(
            post_root=self.post_root,
            post_codemap=self.codemap,
            post_anchor_manifest=self.anchors,
            post_witness_manifest=self.post_witness,
            previous_binding=self.previous,
            post_graph_witness=graph8,
        )
        hold = compile_reentry_closure(
            previous_binding=self.previous,
            reentry_receipt=self.reentry,
            candidate_binding=candidate,
        )
        self.assertEqual(HOLD, hold["closure_status"])
        violations = self.verify(post_graph=graph8, closure=hold)
        self.assertIn(POST_PHASE_NOT_CLOSED, violations)


if __name__ == "__main__":
    unittest.main()
