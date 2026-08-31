import hashlib
import unittest

from tools.aura_collision_safe_rebase import (
    CandidateContribution,
    CollisionDisposition,
    OwnerState,
    assess_collision,
)


def h(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class CollisionSafeRebaseTests(unittest.TestCase):
    def owner(self, *, current=True, digest=None):
        return OwnerState(
            owner_ref="PR#408",
            semantic_generation="3a7c562f2e0f278bc3f350416ff243893d0eb0ff",
            semantic_digest=digest or h("owner"),
            current=current,
        )

    def candidate(self, *, digest=None, claims=None):
        return CandidateContribution(
            contribution_ref="gemini-airllm-glm53-20260831",
            semantic_digest=digest or h("candidate"),
            claims=tuple(claims or ("pager-owned", "nominal-topk-payload-bound")),
            evidence_refs=("gemini-thread", "pr408"),
            invalidators=("owner-generation-change", "host-measurement"),
        )

    def test_duplicate_semantics_are_retained_but_get_zero_sibling_credit(self):
        digest = h("same")
        result = assess_collision(
            self.owner(digest=digest),
            self.candidate(digest=digest),
            overlapping_claims=("pager-owned",),
            unique_residual_claims=(),
        )
        self.assertEqual(result.disposition, CollisionDisposition.DUPLICATE_RETAINED_AS_LINEAGE)
        self.assertTrue(result.preserve_as_reusable_cognition)
        self.assertTrue(result.duplicate_semantic_mass)
        self.assertFalse(result.sibling_credit_earned)
        self.assertFalse(result.effect_authority_granted)
        self.assertFalse(result.semantic_authority_granted)

    def test_overlap_plus_unique_residual_becomes_addendum_candidate(self):
        result = assess_collision(
            self.owner(),
            self.candidate(),
            overlapping_claims=("pager-owned",),
            unique_residual_claims=("nominal-topk-payload-bound",),
        )
        self.assertEqual(result.disposition, CollisionDisposition.ADDENDUM_CANDIDATE)
        self.assertTrue(result.requires_rebase)
        self.assertTrue(result.requires_revalidation)
        self.assertFalse(result.sibling_credit_earned)

    def test_stale_owner_forces_hold_before_rebase(self):
        result = assess_collision(
            self.owner(current=False),
            self.candidate(),
            overlapping_claims=("pager-owned",),
            unique_residual_claims=("nominal-topk-payload-bound",),
        )
        self.assertEqual(result.disposition, CollisionDisposition.HOLD_OWNER_CURRENTNESS_REQUIRED)
        self.assertFalse(result.requires_rebase)
        self.assertTrue(result.requires_revalidation)

    def test_no_overlap_is_orthogonal_owner_candidate_not_automatic_authority(self):
        candidate = self.candidate(claims=("new-independent-seam",))
        result = assess_collision(
            self.owner(),
            candidate,
            overlapping_claims=(),
            unique_residual_claims=("new-independent-seam",),
        )
        self.assertEqual(result.disposition, CollisionDisposition.ORTHOGONAL_OWNER_CANDIDATE)
        self.assertFalse(result.requires_rebase)
        self.assertTrue(result.requires_revalidation)
        self.assertFalse(result.semantic_authority_granted)

    def test_overlap_and_residual_must_be_disjoint(self):
        with self.assertRaises(ValueError):
            assess_collision(
                self.owner(),
                self.candidate(),
                overlapping_claims=("pager-owned",),
                unique_residual_claims=("pager-owned",),
            )

    def test_claim_sets_must_come_from_candidate(self):
        with self.assertRaises(ValueError):
            assess_collision(
                self.owner(),
                self.candidate(),
                overlapping_claims=("invented-owner-law",),
                unique_residual_claims=(),
            )

    def test_assessment_digest_is_deterministic_under_ordering_noise(self):
        a = CandidateContribution(
            contribution_ref="c",
            semantic_digest=h("c"),
            claims=("u", "o", "u"),
            evidence_refs=("b", "a"),
            invalidators=("z", "y"),
        )
        b = CandidateContribution(
            contribution_ref="c",
            semantic_digest=h("c"),
            claims=("o", "u"),
            evidence_refs=("a", "b"),
            invalidators=("y", "z"),
        )
        owner = self.owner()
        r1 = assess_collision(owner, a, overlapping_claims=("o",), unique_residual_claims=("u",))
        r2 = assess_collision(owner, b, overlapping_claims=("o",), unique_residual_claims=("u",))
        self.assertEqual(r1.assessment_digest, r2.assessment_digest)


if __name__ == "__main__":
    unittest.main()
