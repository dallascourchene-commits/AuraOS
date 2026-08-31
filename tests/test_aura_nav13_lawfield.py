import hashlib
import unittest
from dataclasses import replace

from tools.aura_fractal_k27 import K27Path, K27Segment
from tools.aura_nav13_lawfield import (
    BoundaryReason,
    LawFieldOverlay,
    SupersessionProjection,
    boundary_reasons_explicit,
    boundary_reasons_table,
    detect_lawfield_boundary,
    inherit_law_field,
    root_law_field,
    snapshot_from_field,
)


def d(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


class Nav13LawFieldTests(unittest.TestCase):
    def root_overlay(self):
        return LawFieldOverlay(
            path=K27Path.parse("K27:/11.17.15"),
            owner_ref="owner:root",
            rule_generation="g1",
            hard_constraints_add=("NO_MERGE", "NO_PAYMENT"),
            allowed_actions_limit=("READ", "PROPOSE", "HYDRATE"),
            denied_actions_add=(),
            required_evidence_add=("SOURCE_CURRENT",),
            authority_scopes_limit=("NAVIGATE", "PROPOSE"),
            effect_scopes_limit=("READ_ONLY",),
            domain_roles=("SEMANTIC", "AUTHORITY"),
            evidence_state_digest=d("e1"),
            authority_state_digest=d("a1"),
            temporal_state_digest=d("t1"),
            provider_policy_digest=d("p1"),
        )

    def child_overlay(self, segment=K27Segment(2, 8, 21), **kw):
        base = dict(
            path=K27Path.parse("K27:/11.17.15").child(segment),
            owner_ref="owner:child",
            rule_generation="g2",
            hard_constraints_add=("LOCAL_PATIO_BOUNDARY",),
            allowed_actions_limit=("READ", "PROPOSE"),
            denied_actions_add=("PROPOSE",),
            required_evidence_add=("LOCAL_LICENSE",),
            authority_scopes_limit=("NAVIGATE",),
            effect_scopes_limit=("READ_ONLY",),
            domain_roles=("OPERATIONAL",),
            evidence_state_digest=d("e2"),
            authority_state_digest=d("a2"),
            temporal_state_digest=d("t2"),
            provider_policy_digest=d("p2"),
        )
        base.update(kw)
        return LawFieldOverlay(**base)

    def test_child_narrows_parent_and_accumulates_constraints(self):
        root = root_law_field(self.root_overlay())
        child = inherit_law_field(root, self.child_overlay())
        self.assertEqual(child.allowed_actions, ("READ",))
        self.assertEqual(child.authority_scopes, ("NAVIGATE",))
        self.assertEqual(child.effect_scopes, ("READ_ONLY",))
        self.assertIn("NO_MERGE", child.hard_constraints)
        self.assertIn("NO_PAYMENT", child.hard_constraints)
        self.assertIn("LOCAL_PATIO_BOUNDARY", child.hard_constraints)
        self.assertEqual(child.required_evidence, ("LOCAL_LICENSE", "SOURCE_CURRENT"))
        self.assertFalse(child.transition_authorized)
        self.assertFalse(child.effect_authorized)
        self.assertFalse(child.k27_semantic_authority)

    def test_child_cannot_widen_parent_permissions(self):
        root = root_law_field(self.root_overlay())
        with self.assertRaisesRegex(ValueError, "CHILD_PERMISSION_WIDENING_REJECTED"):
            inherit_law_field(
                root,
                self.child_overlay(allowed_actions_limit=("READ", "WRITE")),
            )

    def test_child_cannot_widen_parent_authority_or_effect_scope(self):
        root = root_law_field(self.root_overlay())
        with self.assertRaisesRegex(ValueError, "CHILD_AUTHORITY_WIDENING_REJECTED"):
            inherit_law_field(
                root,
                self.child_overlay(authority_scopes_limit=("NAVIGATE", "EXECUTE")),
            )
        with self.assertRaisesRegex(ValueError, "CHILD_EFFECT_WIDENING_REJECTED"):
            inherit_law_field(
                root,
                self.child_overlay(effect_scopes_limit=("READ_ONLY", "WRITE")),
            )

    def test_parent_hard_constraint_survives_without_supersession(self):
        root = root_law_field(self.root_overlay())
        child = inherit_law_field(root, self.child_overlay())
        self.assertIn("NO_PAYMENT", child.hard_constraints)

    def test_exact_bounded_supersession_can_remove_one_parent_constraint(self):
        root = root_law_field(self.root_overlay())
        child_overlay = self.child_overlay()
        sup = SupersessionProjection(
            target_constraint="NO_PAYMENT",
            parent_law_digest=root.digest,
            child_path=str(child_overlay.path),
            authority_owner_ref="authority:higher",
            authority_generation="auth-g7",
            authority_receipt_digest=d("supersession"),
        )
        child = inherit_law_field(root, child_overlay, supersessions=(sup,))
        self.assertNotIn("NO_PAYMENT", child.hard_constraints)
        self.assertIn("NO_MERGE", child.hard_constraints)
        self.assertEqual(len(child.supersession_fingerprints), 1)
        self.assertFalse(child.authorization_issued)

    def test_stale_or_wrong_supersession_projection_fails_closed(self):
        root = root_law_field(self.root_overlay())
        child_overlay = self.child_overlay()
        base = SupersessionProjection(
            target_constraint="NO_PAYMENT",
            parent_law_digest=root.digest,
            child_path=str(child_overlay.path),
            authority_owner_ref="authority:higher",
            authority_generation="auth-g7",
            authority_receipt_digest=d("supersession"),
        )
        with self.assertRaisesRegex(ValueError, "SUPERSESSION_PARENT_DIGEST_MISMATCH"):
            inherit_law_field(
                root,
                child_overlay,
                supersessions=(replace(base, parent_law_digest=d("wrong")),),
            )
        with self.assertRaisesRegex(
            ValueError, "SUPERSESSION_AUTHORITY_NOT_VERIFIED_BOUNDED"
        ):
            inherit_law_field(
                root,
                child_overlay,
                supersessions=(replace(base, authority_state="STALE"),),
            )

    def test_skipping_intermediate_k27_lawfield_is_rejected(self):
        root = root_law_field(self.root_overlay())
        grandchild = LawFieldOverlay(
            **{
                **self.child_overlay().__dict__,
                "path": K27Path.parse("K27:/11.17.15/2.8.21/0.4.6"),
            }
        )
        with self.assertRaisesRegex(ValueError, "CHILD_LAWFIELD_MUST_BE_DIRECT_K27_CHILD"):
            inherit_law_field(root, grandchild)

    def test_adjacent_siblings_can_have_distinct_effective_laws(self):
        root = root_law_field(self.root_overlay())
        left = inherit_law_field(
            root,
            self.child_overlay(
                K27Segment(2, 8, 21),
                denied_actions_add=("PROPOSE",),
            ),
        )
        right = inherit_law_field(
            root,
            self.child_overlay(
                K27Segment(2, 8, 22),
                denied_actions_add=(),
                hard_constraints_add=("INSIDE_LICENSED_ZONE",),
            ),
        )
        self.assertNotEqual(left.digest, right.digest)
        self.assertEqual(K27Path.parse(left.path).parent, K27Path.parse(right.path).parent)

    def test_tiny_path_delta_requires_recomputation(self):
        root = root_law_field(self.root_overlay())
        left = inherit_law_field(root, self.child_overlay(K27Segment(2, 8, 21)))
        right = inherit_law_field(root, self.child_overlay(K27Segment(2, 8, 22)))
        before = snapshot_from_field(
            left,
            semantic_owner_ref="sem:1",
            execution_environment_digest=d("env"),
            work_order_state_digest=d("wo"),
        )
        after = snapshot_from_field(
            right,
            semantic_owner_ref="sem:1",
            execution_environment_digest=d("env"),
            work_order_state_digest=d("wo"),
        )
        decision = detect_lawfield_boundary(before, after)
        self.assertTrue(decision.requires_recomputation)
        self.assertIn(BoundaryReason.K27_PATH_CHANGED, decision.reasons)
        self.assertIn(BoundaryReason.EFFECTIVE_LAW_CHANGED, decision.reasons)
        self.assertFalse(decision.transition_authorized)

    def test_every_declared_boundary_axis_triggers_recomputation(self):
        root = root_law_field(self.root_overlay())
        field = inherit_law_field(root, self.child_overlay())
        base = snapshot_from_field(
            field,
            semantic_owner_ref="sem:1",
            execution_environment_digest=d("env"),
            work_order_state_digest=d("wo"),
        )
        cases = {
            "semantic_owner_ref": ("sem:2", BoundaryReason.SEMANTIC_OWNER_CHANGED),
            "domain_role_digest": (d("roles2"), BoundaryReason.DOMAIN_ROLE_CHANGED),
            "evidence_state_digest": (d("e3"), BoundaryReason.EVIDENCE_STATE_CHANGED),
            "authority_state_digest": (d("a3"), BoundaryReason.AUTHORITY_STATE_CHANGED),
            "temporal_state_digest": (d("t3"), BoundaryReason.TEMPORAL_STATE_CHANGED),
            "execution_environment_digest": (
                d("env2"),
                BoundaryReason.EXECUTION_ENVIRONMENT_CHANGED,
            ),
            "provider_policy_digest": (d("p3"), BoundaryReason.PROVIDER_POLICY_CHANGED),
            "work_order_state_digest": (d("wo2"), BoundaryReason.WORK_ORDER_STATE_CHANGED),
        }
        for attr, (value, reason) in cases.items():
            with self.subTest(attr=attr):
                changed = replace(base, **{attr: value})
                decision = detect_lawfield_boundary(base, changed)
                self.assertTrue(decision.requires_recomputation)
                self.assertIn(reason, decision.reasons)

    def test_identical_snapshot_does_not_recompute(self):
        root = root_law_field(self.root_overlay())
        field = inherit_law_field(root, self.child_overlay())
        snap = snapshot_from_field(
            field,
            semantic_owner_ref="sem:1",
            execution_environment_digest=d("env"),
            work_order_state_digest=d("wo"),
        )
        decision = detect_lawfield_boundary(snap, snap)
        self.assertFalse(decision.requires_recomputation)
        self.assertEqual(decision.reasons, ())
        self.assertEqual(decision.before_digest, decision.after_digest)

    def test_boundary_different_j_formulations_commute(self):
        root = root_law_field(self.root_overlay())
        field = inherit_law_field(root, self.child_overlay())
        before = snapshot_from_field(
            field,
            semantic_owner_ref="sem:1",
            execution_environment_digest=d("env"),
            work_order_state_digest=d("wo"),
        )
        fields = [
            ("semantic_owner_ref", "sem:2"),
            ("domain_role_digest", d("roles2")),
            ("evidence_state_digest", d("e3")),
            ("authority_state_digest", d("a3")),
            ("temporal_state_digest", d("t3")),
            ("execution_environment_digest", d("env2")),
            ("provider_policy_digest", d("p3")),
            ("work_order_state_digest", d("wo2")),
        ]
        variants = [before]
        for attr, value in fields:
            variants.append(replace(before, **{attr: value}))
        for after in variants:
            self.assertEqual(
                boundary_reasons_explicit(before, after),
                boundary_reasons_table(before, after),
            )

    def test_duplicate_policy_atoms_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_HARD_CONSTRAINT"):
            root_law_field(
                replace(
                    self.root_overlay(),
                    hard_constraints_add=("NO_MERGE", "NO_MERGE"),
                )
            )


if __name__ == "__main__":
    unittest.main()
