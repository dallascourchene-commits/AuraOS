from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import tempfile
import unittest

from scripts.aura_astge_anchor_hydration import WITNESS_VERSION
from scripts.aura_workcapsule_context_binding import ACTIVE, CURRENT, compile_workcapsule_context_binding
from scripts.aura_workcapsule_reentry_closure import CLOSED, HOLD, compile_reentry_closure
from scripts.aura_workcapsule_reentry_closure_exact_verifier import verify_exact_reentry_closure
from scripts.aura_workcapsule_source_bound_exact_reentry import compile_expected_source_bound_reentry
from scripts.aura_workcapsule_two_phase_source_bound_closure import (
    admit_two_phase_source_bound_exact_closure,
    derive_post_reentry_candidate,
    verify_two_phase_source_bound_exact_closure,
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


class WorkCapsuleTwoPhaseSourceBoundClosureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pre_tmp = tempfile.TemporaryDirectory(prefix="aura-pre-reentry-")
        self.post_tmp = tempfile.TemporaryDirectory(prefix="aura-post-reentry-")
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
        self.pre_witness = {
            "version": WITNESS_VERSION,
            "witnesses": [
                {
                    "anchor_id": "target-anchor",
                    "file_id": 17,
                    "source_generation": 42,
                    "expected_byte_len": len(self.original),
                    "expected_body_sha256": self.original_sha,
                    "witness_ref": "fixture://pre-owner/42",
                    "checked_at": "2026-08-31T01:00:00Z",
                }
            ],
        }
        self.post_witness = {
            "version": WITNESS_VERSION,
            "witnesses": [
                {
                    "anchor_id": "target-anchor",
                    "file_id": 17,
                    "source_generation": 43,
                    "expected_byte_len": len(self.repaired),
                    "expected_body_sha256": self.repaired_sha,
                    "witness_ref": "fixture://post-owner/43",
                    "checked_at": "2026-08-31T01:10:00Z",
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
        _, self.reentry = compile_expected_source_bound_reentry(
            root=self.pre_root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=self.pre_witness,
            previous_binding=self.previous,
            observed_graph_witness=self.graph,
        )
        _, self.candidate = derive_post_reentry_candidate(
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
            candidate_binding=self.candidate,
        )
        self.assertEqual(CLOSED, self.closure["closure_status"])

    def tearDown(self) -> None:
        self.pre_tmp.cleanup()
        self.post_tmp.cleanup()

    def verify(self, *, closure=None, post_root=None, post_graph=None):
        return verify_two_phase_source_bound_exact_closure(
            pre_root=self.pre_root,
            pre_codemap=self.codemap,
            pre_anchor_manifest=self.anchors,
            pre_witness_manifest=self.pre_witness,
            previous_binding=self.previous,
            pre_graph_witness=self.graph,
            reentry_receipt=self.reentry,
            post_root=post_root if post_root is not None else self.post_root,
            post_codemap=self.codemap,
            post_anchor_manifest=self.anchors,
            post_witness_manifest=self.post_witness,
            post_graph_witness=post_graph if post_graph is not None else self.graph,
            closure_receipt=closure if closure is not None else self.closure,
        )

    def admit(self, *, closure=None, post_graph=None):
        return admit_two_phase_source_bound_exact_closure(
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
            post_graph_witness=post_graph if post_graph is not None else self.graph,
            closure_receipt=closure if closure is not None else self.closure,
        )

    def test_two_phase_raw_owner_bound_exact_closed_lifecycle(self) -> None:
        self.assertEqual([], self.verify())
        admission = self.admit()
        self.assertTrue(admission["two_phase_raw_source_bound_exact_lifecycle"])
        self.assertTrue(admission["pre_and_post_evidence_are_distinct_phases"])
        self.assertEqual(CLOSED, admission["closure_status"])
        self.assertTrue(admission["pre_source_owner_bound_exact_reentry"]["source_owner_bound_exact_reproduction"])
        self.assertFalse(admission["caller_source_witnesses_accepted"])
        self.assertFalse(admission["caller_candidate_binding_accepted"])
        self.assertTrue(admission["source_generation_domain_preserved"])
        self.assertFalse(any(admission["authority"].values()))

    def test_exact_closure_for_forged_candidate_is_rejected_against_post_raw_owner_evidence(self) -> None:
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
                    "witness_ref": "caller://forged/999",
                }
            ],
        )
        forged_closure = compile_reentry_closure(
            previous_binding=self.previous,
            reentry_receipt=self.reentry,
            candidate_binding=forged,
        )
        self.assertEqual(
            [],
            verify_exact_reentry_closure(
                previous_binding=self.previous,
                reentry_receipt=self.reentry,
                candidate_binding=forged,
                closure_receipt=forged_closure,
            ),
        )
        violations = self.verify(closure=forged_closure)
        self.assertIn("CLOSURE_CANDIDATE_BINDING_IDENTITY_NOT_EXACT", violations)
        self.assertIn("CLOSURE_RECEIPT_NOT_EXACT_INPUT_REPRODUCTION", violations)

    def test_one_live_root_cannot_masquerade_as_two_phase_evidence(self) -> None:
        violations = self.verify(post_root=self.pre_root)
        self.assertEqual(["PRE_POST_EVIDENCE_ROOTS_NOT_DISTINCT"], violations)

    def test_pre_evidence_drift_invalidates_old_reentry_before_closure(self) -> None:
        (self.pre_root / "src/a.py").write_bytes(self.original)
        violations = self.verify()
        self.assertTrue(any(item.startswith("PRE_") for item in violations))

    def test_post_source_still_stale_cannot_be_promoted_to_current_candidate(self) -> None:
        (self.post_root / "src/a.py").write_bytes(b"def target(x):\n    return x + 4\n")
        violations = self.verify()
        self.assertIn("POST_DERIVED_CANDIDATE_NOT_CURRENT", violations)

    def test_exact_hold_is_preserved_not_promoted_to_closed(self) -> None:
        graph = copy.deepcopy(self.graph)
        graph["graph_generation"] = 8
        graph["graph_basis_identity"] = identity("graph-8")
        graph["witness_ref"] = "GRAPH:8:CURRENT"
        _, candidate = derive_post_reentry_candidate(
            post_root=self.post_root,
            post_codemap=self.codemap,
            post_anchor_manifest=self.anchors,
            post_witness_manifest=self.post_witness,
            previous_binding=self.previous,
            post_graph_witness=graph,
        )
        closure = compile_reentry_closure(
            previous_binding=self.previous,
            reentry_receipt=self.reentry,
            candidate_binding=candidate,
        )
        self.assertEqual(HOLD, closure["closure_status"])
        self.assertEqual([], self.verify(closure=closure, post_graph=graph))
        admission = self.admit(closure=closure, post_graph=graph)
        self.assertEqual(HOLD, admission["closure_status"])
        self.assertFalse(any(admission["authority"].values()))


if __name__ == "__main__":
    unittest.main()
