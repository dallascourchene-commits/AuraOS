from __future__ import annotations

import hashlib
import unittest

from tools.aura_collision_safe_rebase import (
    CandidateContribution,
    CollisionDisposition,
    OwnerState,
)
from tools.aura_fractal_k27 import K27Path, ZoomDisposition
from tools.aura_navigator_k27_collision_router import (
    COLLISION_PROOF_JOB,
    COLLISION_PROOF_RUN,
    NAV03A_PROOF_JOB,
    NAV03A_PROOF_RUN,
    TRUE_DIAMOND,
    NavigatorRouteDisposition,
    route_k27_collision,
)


def h(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def owner(*, current: bool = True, digest: str | None = None) -> OwnerState:
    return OwnerState(
        owner_ref="owner-pr",
        semantic_generation="owner-generation-1",
        semantic_digest=digest or h("owner"),
        current=current,
    )


def candidate(*, digest: str | None = None, claims=("shared", "residual")) -> CandidateContribution:
    return CandidateContribution(
        contribution_ref="candidate-agent",
        semantic_digest=digest or h("candidate"),
        claims=tuple(claims),
        evidence_refs=("proof-b", "proof-a"),
        invalidators=("owner-generation-change", "new-falsifier"),
    )


class NavigatorK27CollisionRouterTests(unittest.TestCase):
    def test_different_k27_paths_do_not_override_semantic_duplicate(self):
        same = h("same-semantics")
        receipt = route_k27_collision(
            owner=owner(digest=same),
            candidate=candidate(digest=same, claims=("shared",)),
            owner_path=K27Path.parse("K27:/11.17.15"),
            candidate_path=K27Path.parse("K27:/12.17.15"),
            overlapping_claims=("shared",),
            unique_residual_claims=(),
        )
        self.assertEqual(receipt.locality_disposition, ZoomDisposition.DISTINGUISHED)
        self.assertEqual(
            receipt.semantic_collision_disposition,
            CollisionDisposition.DUPLICATE_RETAINED_AS_LINEAGE,
        )
        self.assertEqual(receipt.route_disposition, NavigatorRouteDisposition.RETAIN_DUPLICATE_LINEAGE)
        self.assertTrue(receipt.duplicate_semantic_mass)
        self.assertFalse(receipt.sibling_credit_earned)
        self.assertIn("DO_NOT_DUPLICATE_CANONICAL_OWNER", receipt.hydration_plan)

    def test_same_k27_path_does_not_override_semantic_orthogonality(self):
        shared_path = K27Path.parse("K27:/11.17.15")
        receipt = route_k27_collision(
            owner=owner(),
            candidate=candidate(claims=("new-independent-seam",)),
            owner_path=shared_path,
            candidate_path=shared_path,
            overlapping_claims=(),
            unique_residual_claims=("new-independent-seam",),
        )
        self.assertEqual(receipt.locality_disposition, ZoomDisposition.LOCALITY_COLLISION)
        self.assertEqual(
            receipt.semantic_collision_disposition,
            CollisionDisposition.ORTHOGONAL_OWNER_CANDIDATE,
        )
        self.assertEqual(
            receipt.route_disposition,
            NavigatorRouteDisposition.ROUTE_ORTHOGONAL_CANDIDATE,
        )
        self.assertFalse(receipt.duplicate_semantic_mass)
        self.assertIn("K27_LOCALITY_COLLISION_DOES_NOT_DECIDE_SEMANTICS", receipt.hydration_plan)

    def test_ancestor_descendant_locality_can_still_route_semantic_addendum(self):
        receipt = route_k27_collision(
            owner=owner(),
            candidate=candidate(),
            owner_path=K27Path.parse("K27:/11.17.15"),
            candidate_path=K27Path.parse("K27:/11.17.15/1.2.3"),
            overlapping_claims=("shared",),
            unique_residual_claims=("residual",),
        )
        self.assertEqual(
            receipt.locality_disposition,
            ZoomDisposition.ANCESTOR_DESCENDANT_COLLISION,
        )
        self.assertEqual(
            receipt.semantic_collision_disposition,
            CollisionDisposition.ADDENDUM_CANDIDATE,
        )
        self.assertEqual(receipt.route_disposition, NavigatorRouteDisposition.ROUTE_ADDENDUM_REBASE)
        self.assertTrue(receipt.requires_rebase)
        self.assertTrue(receipt.requires_semantic_revalidation)
        self.assertIn("ROUTE_TO_TYPED_ADDENDUM_REBASE", receipt.hydration_plan)

    def test_stale_owner_holds_even_when_k27_is_distinguished(self):
        receipt = route_k27_collision(
            owner=owner(current=False),
            candidate=candidate(),
            owner_path=K27Path.parse("K27:/11.17.15"),
            candidate_path=K27Path.parse("K27:/20.1.2"),
            overlapping_claims=("shared",),
            unique_residual_claims=("residual",),
        )
        self.assertEqual(receipt.locality_disposition, ZoomDisposition.DISTINGUISHED)
        self.assertEqual(
            receipt.semantic_collision_disposition,
            CollisionDisposition.HOLD_OWNER_CURRENTNESS_REQUIRED,
        )
        self.assertEqual(
            receipt.route_disposition,
            NavigatorRouteDisposition.HOLD_OWNER_CURRENTNESS_REQUIRED,
        )
        self.assertTrue(receipt.requires_owner_revalidation)
        self.assertFalse(receipt.requires_rebase)

    def test_claim_and_effect_ceiling_stays_false(self):
        receipt = route_k27_collision(
            owner=owner(),
            candidate=candidate(claims=("orthogonal",)),
            owner_path=K27Path.parse("K27:/11.17.15"),
            candidate_path=K27Path.parse("K27:/11.17.16"),
            overlapping_claims=(),
            unique_residual_claims=("orthogonal",),
        )
        self.assertFalse(receipt.k27_semantic_identity)
        self.assertFalse(receipt.k27_evidence_rank)
        self.assertFalse(receipt.k27_currentness_witness)
        self.assertFalse(receipt.semantic_authority_granted)
        self.assertFalse(receipt.read_authority_granted)
        self.assertFalse(receipt.write_authority_granted)
        self.assertFalse(receipt.tool_execution_authority_granted)
        self.assertFalse(receipt.effect_authority_granted)
        self.assertFalse(receipt.native_private_transformer_kv_accessed)
        self.assertEqual(receipt.nav03a_proof_run, NAV03A_PROOF_RUN)
        self.assertEqual(receipt.nav03a_proof_job, NAV03A_PROOF_JOB)
        self.assertEqual(receipt.collision_proof_run, COLLISION_PROOF_RUN)
        self.assertEqual(receipt.collision_proof_job, COLLISION_PROOF_JOB)
        self.assertEqual(receipt.true_diamond, TRUE_DIAMOND)
        self.assertEqual(len(receipt.receipt_digest), 64)

    def test_same_owner_and_candidate_reference_is_rejected(self):
        same_owner = OwnerState("same", "g", h("owner"), True)
        same_candidate = CandidateContribution("same", h("candidate"), ("x",), (), ())
        with self.assertRaisesRegex(ValueError, "OWNER_AND_CANDIDATE_REFS_MUST_BE_DISTINCT"):
            route_k27_collision(
                owner=same_owner,
                candidate=same_candidate,
                owner_path=K27Path.parse("K27:/1.2.3"),
                candidate_path=K27Path.parse("K27:/4.5.6"),
                overlapping_claims=(),
                unique_residual_claims=("x",),
            )

    def test_receipt_is_deterministic_under_claim_order_noise(self):
        a = CandidateContribution(
            "candidate-agent",
            h("candidate"),
            ("residual", "shared", "residual"),
            ("b", "a"),
            ("z", "y"),
        )
        b = CandidateContribution(
            "candidate-agent",
            h("candidate"),
            ("shared", "residual"),
            ("a", "b"),
            ("y", "z"),
        )
        kwargs = dict(
            owner=owner(),
            owner_path=K27Path.parse("K27:/11.17.15"),
            candidate_path=K27Path.parse("K27:/11.17.15/1.1.1"),
            overlapping_claims=("shared",),
            unique_residual_claims=("residual",),
        )
        r1 = route_k27_collision(candidate=a, **kwargs)
        r2 = route_k27_collision(candidate=b, **kwargs)
        self.assertEqual(r1.receipt_digest, r2.receipt_digest)


if __name__ == "__main__":
    unittest.main()
