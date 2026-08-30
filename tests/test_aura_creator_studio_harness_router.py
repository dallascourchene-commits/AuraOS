import unittest

from aura_creator_studio_harness_router import (
    EARNED_SWARM_REASONS,
    HarnessRoutePolicyError,
    select_creator_studio_route,
)


def request(**overrides):
    out = {
        "task_id": "CS-TEST",
        "project_currentness": "CURRENT",
        "paid_provider_authorized": False,
        "owner_swarm_deploy_authorized": False,
        "earned_swarm_reason": "",
        "awj033_physical_swarm_ready": False,
        "pro_escalation_earned": False,
        "pro_escalation_ref": "",
        "cost_ceiling_usd": 0.0,
    }
    out.update(overrides)
    return out


def candidate(route_class, **overrides):
    out = {
        "route_id": route_class,
        "route_class": route_class,
        "currentness": "CURRENT",
        "capability_fit": True,
        "adequacy": "ELIGIBLE",
        "requires_effect": False,
        "effect_authorized": False,
        "external_provider": False,
        "provider_id": "",
        "model_id": "",
        "allow_provider_fallback": False,
        "paid": False,
        "estimated_marginal_cost_usd": None,
        "deepseek_physical_swarm": False,
    }
    out.update(overrides)
    return out


class HarnessRouteTests(unittest.TestCase):
    def test_r0_reuse_beats_every_higher_route(self):
        result = select_creator_studio_route(request(paid_provider_authorized=True, cost_ceiling_usd=10), [candidate("R6_PAID_EXTERNAL", external_provider=True, provider_id="x", model_id="exact-model", paid=True, requires_effect=True, effect_authorized=True, estimated_marginal_cost_usd=0.01), candidate("R0_REUSE")])
        self.assertEqual("R0_REUSE", result["selected_route"]["route_class"])

    def test_local_beats_chatgpt(self):
        result = select_creator_studio_route(request(), [candidate("R3_CHATGPT"), candidate("R1_LOCAL_DETERMINISTIC")])
        self.assertEqual("R1_LOCAL_DETERMINISTIC", result["selected_route"]["route_class"])

    def test_stale_project_requires_rebase(self):
        self.assertEqual("REBASE_REQUIRED", select_creator_studio_route(request(project_currentness="STALE"), [candidate("R0_REUSE")])["decision"])

    def test_stale_candidate_is_not_selected(self):
        result = select_creator_studio_route(request(), [candidate("R1_LOCAL_DETERMINISTIC", currentness="STALE")])
        self.assertIn("CANDIDATE_NOT_CURRENT", result["reason_codes"])

    def test_model_role_alias_is_forbidden_for_external_effect(self):
        result = select_creator_studio_route(request(paid_provider_authorized=True, cost_ceiling_usd=1), [candidate("R6_PAID_EXTERNAL", external_provider=True, provider_id="deepseek", model_id="coding", paid=True, requires_effect=True, effect_authorized=True, estimated_marginal_cost_usd=0.01)])
        self.assertIn("MODEL_ROLE_ALIAS_FORBIDDEN", result["reason_codes"])

    def test_external_route_requires_exact_provider_and_model(self):
        result = select_creator_studio_route(request(paid_provider_authorized=True, cost_ceiling_usd=1), [candidate("R6_PAID_EXTERNAL", external_provider=True, paid=True, requires_effect=True, effect_authorized=True, estimated_marginal_cost_usd=0.01)])
        self.assertIn("EXACT_PROVIDER_MODEL_REQUIRED", result["reason_codes"])

    def test_provider_fallback_is_forbidden(self):
        result = select_creator_studio_route(request(paid_provider_authorized=True, cost_ceiling_usd=1), [candidate("R6_PAID_EXTERNAL", external_provider=True, provider_id="x", model_id="exact-model", allow_provider_fallback=True, paid=True, requires_effect=True, effect_authorized=True, estimated_marginal_cost_usd=0.01)])
        self.assertIn("IMPLICIT_PROVIDER_FALLBACK_FORBIDDEN", result["reason_codes"])

    def test_paid_route_requires_authority(self):
        result = select_creator_studio_route(request(paid_provider_authorized=False, cost_ceiling_usd=1), [candidate("R6_PAID_EXTERNAL", external_provider=True, provider_id="x", model_id="exact-model", paid=True, requires_effect=True, effect_authorized=True, estimated_marginal_cost_usd=0.01)])
        self.assertIn("PAID_PROVIDER_AUTHORITY_REQUIRED", result["reason_codes"])

    def test_paid_unknown_cost_is_not_treated_as_zero(self):
        result = select_creator_studio_route(request(paid_provider_authorized=True, cost_ceiling_usd=1), [candidate("R6_PAID_EXTERNAL", external_provider=True, provider_id="x", model_id="exact-model", paid=True, requires_effect=True, effect_authorized=True, estimated_marginal_cost_usd=None)])
        self.assertIn("PAID_COST_UNKNOWN_OR_INVALID", result["reason_codes"])

    def test_paid_route_over_ceiling_is_rejected(self):
        result = select_creator_studio_route(request(paid_provider_authorized=True, cost_ceiling_usd=0.01), [candidate("R6_PAID_EXTERNAL", external_provider=True, provider_id="x", model_id="exact-model", paid=True, requires_effect=True, effect_authorized=True, estimated_marginal_cost_usd=0.02)])
        self.assertIn("COST_CEILING_EXCEEDED", result["reason_codes"])

    def test_no_swarm_by_default(self):
        result = select_creator_studio_route(request(), [candidate("R5_SWARM", requires_effect=True, effect_authorized=True)])
        self.assertIn("SWARM_NOT_AUTHORIZED_OR_EARNED", result["reason_codes"])

    def test_explicit_owner_swarm_authority_allows_bounded_swarm(self):
        result = select_creator_studio_route(request(owner_swarm_deploy_authorized=True), [candidate("R5_SWARM", requires_effect=True, effect_authorized=True)])
        self.assertEqual("R5_SWARM", result["selected_route"]["route_class"])

    def test_each_typed_earned_parallelism_reason_can_enable_swarm_route(self):
        for reason in EARNED_SWARM_REASONS:
            with self.subTest(reason=reason):
                result = select_creator_studio_route(request(earned_swarm_reason=reason), [candidate("R5_SWARM", requires_effect=True, effect_authorized=True)])
                self.assertEqual("R5_SWARM", result["selected_route"]["route_class"])

    def test_swarm_routing_does_not_invent_effect_authority(self):
        result = select_creator_studio_route(request(owner_swarm_deploy_authorized=True), [candidate("R5_SWARM", requires_effect=True, effect_authorized=False)])
        self.assertIn("EFFECT_AUTHORITY_REQUIRED", result["reason_codes"])

    def test_deepseek_physical_swarm_requires_awj033(self):
        result = select_creator_studio_route(request(owner_swarm_deploy_authorized=True, awj033_physical_swarm_ready=False), [candidate("R5_SWARM", requires_effect=True, effect_authorized=True, external_provider=True, provider_id="deepseek", model_id="deepseek-v4-flash", allow_provider_fallback=False, deepseek_physical_swarm=True)])
        self.assertIn("AWJ033_PHYSICAL_SWARM_GATE_REQUIRED", result["reason_codes"])

    def test_deepseek_pro_requires_earned_escalation(self):
        result = select_creator_studio_route(request(paid_provider_authorized=True, cost_ceiling_usd=1), [candidate("R6_PAID_EXTERNAL", external_provider=True, provider_id="deepseek", model_id="deepseek-v4-pro", paid=True, requires_effect=True, effect_authorized=True, estimated_marginal_cost_usd=0.01)])
        self.assertIn("DEEPSEEK_PRO_ESCALATION_REQUIRED", result["reason_codes"])

    def test_deepseek_pro_may_route_with_typed_escalation(self):
        result = select_creator_studio_route(request(paid_provider_authorized=True, cost_ceiling_usd=1, pro_escalation_earned=True, pro_escalation_ref="receipt:pro-1"), [candidate("R6_PAID_EXTERNAL", external_provider=True, provider_id="deepseek", model_id="deepseek-v4-pro", paid=True, requires_effect=True, effect_authorized=True, estimated_marginal_cost_usd=0.01)])
        self.assertEqual("R6_PAID_EXTERNAL", result["selected_route"]["route_class"])

    def test_no_implicit_fallback_in_decision_receipt(self):
        self.assertFalse(select_creator_studio_route(request(), [candidate("R2_AURA_NATIVE")])["fallback_allowed"])

    def test_invalid_cost_ceiling_fails_input_validation(self):
        with self.assertRaisesRegex(HarnessRoutePolicyError, "INVALID_COST_CEILING"):
            select_creator_studio_route(request(cost_ceiling_usd=-1), [candidate("R0_REUSE")])


if __name__ == "__main__":
    unittest.main()
