import hashlib
import unittest
from dataclasses import replace

from tools.aura_fractal_k27 import K27Path
from tools.aura_nav13_lawfield import LawFieldOverlay, root_law_field
from tools.aura_nav13_minimum_hydration import (
    ROUTE_PROJECTION_SCHEMA,
    SOURCE_PROJECTION_SCHEMA,
    EpistemicRouteProjection,
    EvidenceRequirement,
    HydrationLevel,
    HydrationSourceProjection,
    PlanDisposition,
    compile_minimum_hydration_route,
)


def d(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


class Nav13MinimumHydrationTests(unittest.TestCase):
    def law(self, *, allow_hydrate=True, required=("REQ_A", "REQ_B")):
        actions = ("HYDRATE", "READ") if allow_hydrate else ("READ",)
        return root_law_field(
            LawFieldOverlay(
                path=K27Path.parse("K27:/11.17.15"),
                owner_ref="owner:nav13",
                rule_generation="law-g1",
                hard_constraints_add=("NO_EFFECT",),
                allowed_actions_limit=actions,
                denied_actions_add=(),
                required_evidence_add=required,
                authority_scopes_limit=("NAVIGATE",),
                effect_scopes_limit=("READ_ONLY",),
                domain_roles=("SEMANTIC", "EVIDENCE"),
                evidence_state_digest=d("evidence-state"),
                authority_state_digest=d("authority-state"),
                temporal_state_digest=d("temporal-state"),
                provider_policy_digest=d("provider-policy"),
            )
        )

    def route(self, state="EXTERNAL_UNHYDRATED"):
        transitions = {
            "KNOWN_CURRENT": "NONE",
            "EXTERNAL_UNHYDRATED": "HYDRATE_MINIMUM",
            "STALE": "REOPEN_CURRENTNESS",
            "HISTORICAL": "HISTORY_ONLY",
            "UNRESOLVED": "RESOLVE_VERSION",
            "COLLISION": "QUOTIENT_COLLISION",
            "OWNER_MISSING": "DISCOVER_OWNER",
            "MAP_GAP": "REPAIR_MAP",
            "UNKNOWN": "RESOLVE_CURRENTNESS",
        }
        return EpistemicRouteProjection(
            schema=ROUTE_PROJECTION_SCHEMA,
            state=state,
            next_transition=transitions[state],
            route_receipt_digest=d(f"route:{state}"),
        )

    def req(self, rid, key, level, *, current=True, exact=True):
        return EvidenceRequirement(
            requirement_id=rid,
            semantic_key=key,
            minimum_level=level,
            currentness_required=current,
            exact_source_required=exact,
        )

    def source(
        self,
        key,
        level,
        *,
        currentness="RESOLVED_CURRENT",
        state="CURRENT_REFERENCE",
        reader="FOUND_VERIFIED",
        uri=True,
        placement=(4, 5, 6),
        generation="g1",
    ):
        return HydrationSourceProjection(
            schema=SOURCE_PROJECTION_SCHEMA,
            semantic_key=key,
            subject_key=d(f"subject:{key}"),
            evidence_generation_key=d(f"evidence:{key}:{generation}"),
            knowledge_node_digest=d(f"node:{key}:{generation}"),
            validation_fingerprint=d(f"vf:{key}:{generation}"),
            reader_receipt_digest=d(f"reader:{key}:{generation}"),
            knowledge_state=state,
            reader_disposition=reader,
            source_currentness=currentness,
            available_level=level,
            exact_source_uri=f"https://example.org/{key}/{generation}" if uri else None,
            evidence_domain="EXTERNAL_RESEARCH",
            principal="navigator:nav13",
            k27_placement_hint=placement,
        )

    def test_two_sources_compile_only_missing_contiguous_levels(self):
        plan = compile_minimum_hydration_route(
            law=self.law(),
            epistemic_route=self.route(),
            requirements=(
                self.req("REQ_A", "A", HydrationLevel.L2),
                self.req("REQ_B", "B", HydrationLevel.L3),
            ),
            sources=(
                self.source("A", HydrationLevel.L0),
                self.source("B", HydrationLevel.L1),
            ),
        )
        self.assertEqual(plan.disposition, PlanDisposition.HYDRATE_MINIMUM)
        self.assertTrue(plan.minimum_level_proven)
        self.assertFalse(plan.minimum_bytes_proven)
        self.assertFalse(plan.minimum_ast_cone_proven)
        self.assertEqual(len(plan.steps), 2)
        self.assertEqual(plan.steps[0].missing_levels, ("L1", "L2"))
        self.assertEqual(plan.steps[1].missing_levels, ("L2", "L3"))
        self.assertFalse(plan.materialization_started)
        self.assertFalse(plan.effect_authorized)

    def test_shared_source_collapses_to_maximum_required_level(self):
        law = self.law(required=("REQ_A", "REQ_B"))
        plan = compile_minimum_hydration_route(
            law=law,
            epistemic_route=self.route(),
            requirements=(
                self.req("REQ_A", "A", HydrationLevel.L1),
                self.req("REQ_B", "A", HydrationLevel.L4),
            ),
            sources=(self.source("A", HydrationLevel.L2),),
        )
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[0].target_level, HydrationLevel.L4)
        self.assertEqual(plan.steps[0].requirement_ids, ("REQ_A", "REQ_B"))
        self.assertEqual(plan.steps[0].missing_levels, ("L3", "L4"))

    def test_satisfied_current_route_needs_no_hydration(self):
        plan = compile_minimum_hydration_route(
            law=self.law(),
            epistemic_route=self.route("KNOWN_CURRENT"),
            requirements=(
                self.req("REQ_A", "A", HydrationLevel.L2),
                self.req("REQ_B", "B", HydrationLevel.L3),
            ),
            sources=(
                self.source("A", HydrationLevel.L2),
                self.source("B", HydrationLevel.L4),
            ),
        )
        self.assertEqual(plan.disposition, PlanDisposition.READY_NO_HYDRATION)
        self.assertEqual(plan.steps, ())
        self.assertTrue(plan.minimum_level_proven)

    def test_blocking_epistemic_debt_precedes_hydration(self):
        for state in (
            "STALE",
            "HISTORICAL",
            "UNRESOLVED",
            "COLLISION",
            "OWNER_MISSING",
            "MAP_GAP",
            "UNKNOWN",
        ):
            with self.subTest(state=state):
                plan = compile_minimum_hydration_route(
                    law=self.law(),
                    epistemic_route=self.route(state),
                    requirements=(
                        self.req("REQ_A", "A", HydrationLevel.L4),
                        self.req("REQ_B", "B", HydrationLevel.L4),
                    ),
                    sources=(),
                )
                self.assertEqual(plan.disposition, PlanDisposition.HOLD_EPISTEMIC_DEBT)
                self.assertFalse(plan.minimum_level_proven)
                self.assertEqual(plan.steps, ())

    def test_deficit_with_known_current_requires_route_rebase(self):
        plan = compile_minimum_hydration_route(
            law=self.law(),
            epistemic_route=self.route("KNOWN_CURRENT"),
            requirements=(
                self.req("REQ_A", "A", HydrationLevel.L4),
                self.req("REQ_B", "B", HydrationLevel.L2),
            ),
            sources=(
                self.source("A", HydrationLevel.L1),
                self.source("B", HydrationLevel.L2),
            ),
        )
        self.assertEqual(plan.disposition, PlanDisposition.HOLD_ROUTE_REBASE_REQUIRED)
        self.assertFalse(plan.minimum_level_proven)

    def test_no_deficit_with_external_unhydrated_requires_route_rebase(self):
        plan = compile_minimum_hydration_route(
            law=self.law(),
            epistemic_route=self.route("EXTERNAL_UNHYDRATED"),
            requirements=(
                self.req("REQ_A", "A", HydrationLevel.L1),
                self.req("REQ_B", "B", HydrationLevel.L1),
            ),
            sources=(
                self.source("A", HydrationLevel.L2),
                self.source("B", HydrationLevel.L3),
            ),
        )
        self.assertEqual(plan.disposition, PlanDisposition.HOLD_ROUTE_REBASE_REQUIRED)

    def test_effective_law_can_forbid_hydration(self):
        plan = compile_minimum_hydration_route(
            law=self.law(allow_hydrate=False),
            epistemic_route=self.route(),
            requirements=(
                self.req("REQ_A", "A", HydrationLevel.L2),
                self.req("REQ_B", "B", HydrationLevel.L2),
            ),
            sources=(
                self.source("A", HydrationLevel.L0),
                self.source("B", HydrationLevel.L0),
            ),
        )
        self.assertEqual(plan.disposition, PlanDisposition.HOLD_LAW_FORBIDS_HYDRATION)
        self.assertEqual(plan.steps, ())

    def test_currentness_unknown_or_not_required_cannot_pay_required_debt(self):
        for currentness in ("UNKNOWN", "NOT_REQUIRED", "STALE"):
            with self.subTest(currentness=currentness):
                plan = compile_minimum_hydration_route(
                    law=self.law(),
                    epistemic_route=self.route(),
                    requirements=(
                        self.req("REQ_A", "A", HydrationLevel.L2),
                        self.req("REQ_B", "B", HydrationLevel.L1),
                    ),
                    sources=(
                        self.source("A", HydrationLevel.L0, currentness=currentness),
                        self.source("B", HydrationLevel.L1),
                    ),
                )
                self.assertEqual(
                    plan.disposition,
                    PlanDisposition.HOLD_SOURCE_CURRENTNESS_UNRESOLVED,
                )

    def test_noncurrent_eki_node_and_unverified_reader_fail_closed(self):
        stale_node = compile_minimum_hydration_route(
            law=self.law(),
            epistemic_route=self.route(),
            requirements=(
                self.req("REQ_A", "A", HydrationLevel.L2),
                self.req("REQ_B", "B", HydrationLevel.L1),
            ),
            sources=(
                self.source("A", HydrationLevel.L0, state="STALE_REVERIFY_REQUIRED"),
                self.source("B", HydrationLevel.L1),
            ),
        )
        self.assertEqual(stale_node.disposition, PlanDisposition.HOLD_SOURCE_NOT_CURRENT)

        bad_reader = compile_minimum_hydration_route(
            law=self.law(),
            epistemic_route=self.route(),
            requirements=(
                self.req("REQ_A", "A", HydrationLevel.L2),
                self.req("REQ_B", "B", HydrationLevel.L1),
            ),
            sources=(
                self.source("A", HydrationLevel.L0, reader="WRONG_RESPONSIBILITY_OWNER"),
                self.source("B", HydrationLevel.L1),
            ),
        )
        self.assertEqual(
            bad_reader.disposition,
            PlanDisposition.HOLD_SOURCE_READER_UNVERIFIED,
        )

    def test_exact_source_required_missing_holds(self):
        plan = compile_minimum_hydration_route(
            law=self.law(),
            epistemic_route=self.route(),
            requirements=(
                self.req("REQ_A", "A", HydrationLevel.L1, exact=True),
                self.req("REQ_B", "B", HydrationLevel.L1),
            ),
            sources=(
                self.source("A", HydrationLevel.L1, uri=False),
                self.source("B", HydrationLevel.L1),
            ),
        )
        self.assertEqual(plan.disposition, PlanDisposition.HOLD_EXACT_SOURCE_UNRESOLVED)

    def test_exact_source_optional_but_new_hydration_still_needs_reopen_handle(self):
        plan = compile_minimum_hydration_route(
            law=self.law(),
            epistemic_route=self.route(),
            requirements=(
                self.req("REQ_A", "A", HydrationLevel.L3, exact=False),
                self.req("REQ_B", "B", HydrationLevel.L1),
            ),
            sources=(
                self.source("A", HydrationLevel.L1, uri=False),
                self.source("B", HydrationLevel.L1),
            ),
        )
        self.assertEqual(plan.disposition, PlanDisposition.HOLD_EXACT_SOURCE_UNRESOLVED)
        self.assertIn("HYDRATION_DEFICIT_REQUIRES_EXACT_SOURCE", plan.reason)
        self.assertEqual(plan.steps, ())

    def test_exact_source_optional_and_already_satisfied_is_allowed(self):
        plan = compile_minimum_hydration_route(
            law=self.law(),
            epistemic_route=self.route("KNOWN_CURRENT"),
            requirements=(
                self.req("REQ_A", "A", HydrationLevel.L1, exact=False),
                self.req("REQ_B", "B", HydrationLevel.L1),
            ),
            sources=(
                self.source("A", HydrationLevel.L2, uri=False),
                self.source("B", HydrationLevel.L1),
            ),
        )
        self.assertEqual(plan.disposition, PlanDisposition.READY_NO_HYDRATION)

    def test_k27_placement_changes_routing_not_semantic_plan(self):
        kwargs = dict(
            law=self.law(),
            epistemic_route=self.route(),
            requirements=(
                self.req("REQ_A", "A", HydrationLevel.L3),
                self.req("REQ_B", "B", HydrationLevel.L1),
            ),
        )
        a = compile_minimum_hydration_route(
            **kwargs,
            sources=(
                self.source("A", HydrationLevel.L0, placement=(1, 2, 3)),
                self.source("B", HydrationLevel.L1),
            ),
        )
        b = compile_minimum_hydration_route(
            **kwargs,
            sources=(
                self.source("A", HydrationLevel.L0, placement=(7, 8, 9)),
                self.source("B", HydrationLevel.L1),
            ),
        )
        self.assertEqual(a.semantic_plan_digest, b.semantic_plan_digest)
        self.assertNotEqual(a.routing_receipt_digest, b.routing_receipt_digest)

    def test_evidence_generation_change_changes_semantic_plan(self):
        kwargs = dict(
            law=self.law(),
            epistemic_route=self.route(),
            requirements=(
                self.req("REQ_A", "A", HydrationLevel.L3),
                self.req("REQ_B", "B", HydrationLevel.L1),
            ),
        )
        a = compile_minimum_hydration_route(
            **kwargs,
            sources=(
                self.source("A", HydrationLevel.L0, generation="g1"),
                self.source("B", HydrationLevel.L1),
            ),
        )
        b = compile_minimum_hydration_route(
            **kwargs,
            sources=(
                self.source("A", HydrationLevel.L0, generation="g2"),
                self.source("B", HydrationLevel.L1),
            ),
        )
        self.assertNotEqual(a.semantic_plan_digest, b.semantic_plan_digest)

    def test_law_requirement_binding_is_exact(self):
        plan = compile_minimum_hydration_route(
            law=self.law(),
            epistemic_route=self.route(),
            requirements=(self.req("REQ_A", "A", HydrationLevel.L1),),
            sources=(self.source("A", HydrationLevel.L0),),
        )
        self.assertEqual(plan.disposition, PlanDisposition.HOLD_REQUIREMENT_UNBOUND)
        self.assertIn("REQ_B", plan.unresolved_requirements)

    def test_duplicate_requirement_or_source_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_EVIDENCE_REQUIREMENT"):
            compile_minimum_hydration_route(
                law=self.law(),
                epistemic_route=self.route(),
                requirements=(
                    self.req("REQ_A", "A", HydrationLevel.L1),
                    self.req("REQ_A", "B", HydrationLevel.L1),
                ),
                sources=(self.source("A", HydrationLevel.L0),),
            )

        with self.assertRaisesRegex(ValueError, "DUPLICATE_HYDRATION_SOURCE_SEMANTIC_KEY"):
            compile_minimum_hydration_route(
                law=self.law(),
                epistemic_route=self.route(),
                requirements=(
                    self.req("REQ_A", "A", HydrationLevel.L1),
                    self.req("REQ_B", "B", HydrationLevel.L1),
                ),
                sources=(
                    self.source("A", HydrationLevel.L0),
                    replace(self.source("A", HydrationLevel.L0), reader_receipt_digest=d("other")),
                    self.source("B", HydrationLevel.L0),
                ),
            )

    def test_nonpromotion_fields_remain_false(self):
        plan = compile_minimum_hydration_route(
            law=self.law(),
            epistemic_route=self.route(),
            requirements=(
                self.req("REQ_A", "A", HydrationLevel.L2),
                self.req("REQ_B", "B", HydrationLevel.L2),
            ),
            sources=(
                self.source("A", HydrationLevel.L0),
                self.source("B", HydrationLevel.L0),
            ),
        )
        self.assertFalse(plan.source_truth_proven)
        self.assertFalse(plan.authorization_issued)
        self.assertFalse(plan.effect_authorized)
        self.assertFalse(plan.effect_executed)
        self.assertFalse(plan.semantic_k27_authority)
        self.assertFalse(plan.native_private_transformer_kv_accessed)


if __name__ == "__main__":
    unittest.main()
