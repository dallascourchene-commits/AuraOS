from __future__ import annotations

import copy
import hashlib
import inspect
from pathlib import Path
import tempfile

from scripts.aura_astge_anchor_hydration import WITNESS_VERSION
from scripts.aura_workcapsule_observation_bound_closure import (
    CLOSED,
    HOLD,
    compile_observation_bound_reentry_closure,
)
from scripts.aura_workcapsule_observation_bound_exact_verifier import (
    verify_exact_observation_bound_reentry_closure,
)
from scripts.aura_workcapsule_two_phase_observation_bound_exact import (
    SAME_PHASE_ROOT,
    admit_two_phase_observation_bound_exact,
    verify_two_phase_observation_bound_exact,
)
from tests.test_aura_workcapsule_two_phase_source_bound_closure import (
    WorkCapsuleTwoPhaseSourceBoundClosureTests,
    identity,
)


class WorkCapsuleTwoPhaseObservationBoundExactTests(
    WorkCapsuleTwoPhaseSourceBoundClosureTests
):
    """O26 extends the exact PR518 fixture with complete PR519 outer-receipt replay."""

    def setUp(self) -> None:
        super().setUp()
        self.observation_receipt = self.compile_outer(
            self.post_root,
            self.post_witness,
            self.graph,
        )
        self.assertEqual(CLOSED, self.observation_receipt["closure_status"])

    def compile_outer(self, root: Path, witness: dict, graph: dict) -> dict:
        return copy.deepcopy(
            compile_observation_bound_reentry_closure(
                root=root,
                codemap=self.codemap,
                anchor_manifest=self.anchors,
                witness_manifest=witness,
                previous_binding=self.previous,
                reentry_receipt=self.reentry,
                candidate_graph_witness=graph,
            )
        )

    def verify_outer(
        self,
        receipt: dict | None = None,
        *,
        pre_root: Path | None = None,
        post_root: Path | None = None,
        post_witness: dict | None = None,
        post_graph: dict | None = None,
    ) -> list[str]:
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
            post_witness_manifest=(
                post_witness if post_witness is not None else self.post_witness
            ),
            post_graph_witness=post_graph if post_graph is not None else self.graph,
            observation_bound_receipt=(
                receipt if receipt is not None else self.observation_receipt
            ),
        )

    def test_o26_exact_closed_replays_pre_post_and_inner_lifecycle(self) -> None:
        self.assertEqual([], self.verify_outer())
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
            observation_bound_receipt=self.observation_receipt,
        )
        self.assertTrue(admission["two_phase_observation_bound_exact_reproduction"])
        self.assertTrue(admission["pre_and_post_evidence_are_distinct_phases"])
        self.assertTrue(admission["inner_two_phase_exact_lifecycle_replayed"])
        self.assertEqual(CLOSED, admission["closure_status"])
        self.assertFalse(admission["source_currentness_minted"])
        self.assertFalse(any(admission["authority"].values()))

    def test_o26_same_live_root_cannot_impersonate_two_phases(self) -> None:
        self.assertEqual(
            [SAME_PHASE_ROOT],
            self.verify_outer(post_root=self.pre_root),
        )

    def test_o26_pre_phase_drift_invalidates_before_post_receipt(self) -> None:
        (self.pre_root / "src/a.py").write_bytes(self.original)
        violations = self.verify_outer()
        self.assertTrue(any(item.startswith("PRE_") for item in violations))

    def test_o26_foreign_exact_post_receipt_rejected_against_pinned_post(self) -> None:
        foreign_body = b"def target(x):\n    return x + 4\n"
        self.assertEqual(len(self.repaired), len(foreign_body))
        with tempfile.TemporaryDirectory(prefix="aura-o26-foreign-") as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src/a.py").write_bytes(foreign_body)
            witness = {
                "version": WITNESS_VERSION,
                "witnesses": [
                    {
                        "anchor_id": "target-anchor",
                        "file_id": 17,
                        "source_generation": 44,
                        "expected_byte_len": len(foreign_body),
                        "expected_body_sha256": hashlib.sha256(foreign_body).hexdigest(),
                        "witness_ref": "fixture://foreign-owner/44",
                        "checked_at": "2026-08-31T02:00:00Z",
                    }
                ],
            }
            foreign_receipt = self.compile_outer(root, witness, self.graph)
            self.assertEqual(
                [],
                verify_exact_observation_bound_reentry_closure(
                    root=root,
                    codemap=self.codemap,
                    anchor_manifest=self.anchors,
                    witness_manifest=witness,
                    previous_binding=self.previous,
                    reentry_receipt=self.reentry,
                    candidate_graph_witness=self.graph,
                    receipt=foreign_receipt,
                ),
            )
        violations = self.verify_outer(foreign_receipt)
        self.assertTrue(any(item.startswith("POST_") for item in violations))

    def test_o26_graph_drift_hold_replays_inner_lifecycle_and_stays_hold(self) -> None:
        changed_graph = copy.deepcopy(self.graph)
        changed_graph["graph_generation"] = 8
        changed_graph["graph_basis_identity"] = identity("graph-o26-8")
        changed_graph["witness_ref"] = "GRAPH:O26:8:CURRENT"
        receipt = self.compile_outer(self.post_root, self.post_witness, changed_graph)
        self.assertEqual(HOLD, receipt["closure_status"])
        self.assertIsInstance(receipt["closure_receipt"], dict)
        self.assertEqual([], self.verify_outer(receipt, post_graph=changed_graph))
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
        self.assertTrue(admission["inner_two_phase_exact_lifecycle_replayed"])
        self.assertFalse(any(admission["authority"].values()))

    def test_o26_public_boundary_has_no_candidate_or_source_witness_slot(self) -> None:
        params = inspect.signature(verify_two_phase_observation_bound_exact).parameters
        self.assertNotIn("candidate_binding", params)
        self.assertNotIn("observed_source_witnesses", params)
        self.assertIn("pre_root", params)
        self.assertIn("post_root", params)
        self.assertIn("observation_bound_receipt", params)
