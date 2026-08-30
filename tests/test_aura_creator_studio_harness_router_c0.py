import unittest

from aura_creator_studio_harness_router import (
    HarnessRoutePolicyError,
    select_creator_studio_route,
)


def request(**overrides):
    out = {
        "task_id": "CS-C0-REPAIR",
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


class HarnessRouteC0RepairTests(unittest.TestCase):
    def test_external_paid_effect_cannot_opt_out_via_requires_effect_false(self):
        result = select_creator_studio_route(
            request(paid_provider_authorized=True, cost_ceiling_usd=1),
            [candidate(
                "R6_PAID_EXTERNAL",
                external_provider=True,
                provider_id="x",
                model_id="exact-model",
                paid=True,
                requires_effect=False,
                effect_authorized=False,
                estimated_marginal_cost_usd=0.01,
            )],
        )
        self.assertIn("EFFECT_AUTHORITY_REQUIRED", result["reason_codes"])

    def test_r0_external_paid_rank_spoof_is_rejected(self):
        result = select_creator_studio_route(
            request(paid_provider_authorized=True, cost_ceiling_usd=1),
            [candidate(
                "R0_REUSE",
                external_provider=True,
                provider_id="x",
                model_id="exact-model",
                paid=True,
                effect_authorized=True,
                estimated_marginal_cost_usd=0.01,
            )],
        )
        self.assertIn("ROUTE_ATTRIBUTE_MISMATCH", result["reason_codes"])

    def test_r6_requires_paid_external_semantics(self):
        result = select_creator_studio_route(
            request(),
            [candidate("R6_PAID_EXTERNAL", external_provider=False, paid=False)],
        )
        self.assertIn("ROUTE_ATTRIBUTE_MISMATCH", result["reason_codes"])

    def test_nan_cost_ceiling_is_invalid(self):
        with self.assertRaisesRegex(HarnessRoutePolicyError, "INVALID_COST_CEILING"):
            select_creator_studio_route(request(cost_ceiling_usd=float("nan")), [candidate("R0_REUSE")])

    def test_infinite_cost_ceiling_is_invalid(self):
        with self.assertRaisesRegex(HarnessRoutePolicyError, "INVALID_COST_CEILING"):
            select_creator_studio_route(request(cost_ceiling_usd=float("inf")), [candidate("R0_REUSE")])

    def test_paid_nan_cost_is_not_eligible(self):
        result = select_creator_studio_route(
            request(paid_provider_authorized=True, cost_ceiling_usd=1),
            [candidate(
                "R6_PAID_EXTERNAL",
                external_provider=True,
                provider_id="x",
                model_id="exact-model",
                paid=True,
                effect_authorized=True,
                estimated_marginal_cost_usd=float("nan"),
            )],
        )
        self.assertIn("PAID_COST_UNKNOWN_OR_INVALID", result["reason_codes"])

    def test_nonpaid_nan_cost_is_rejected_not_sorted(self):
        result = select_creator_studio_route(
            request(),
            [candidate("R1_LOCAL_DETERMINISTIC", estimated_marginal_cost_usd=float("nan"))],
        )
        self.assertIn("COST_INVALID", result["reason_codes"])

    def test_deepseek_swarm_gate_is_derived_even_when_flag_false(self):
        result = select_creator_studio_route(
            request(owner_swarm_deploy_authorized=True, awj033_physical_swarm_ready=False),
            [candidate(
                "R5_SWARM",
                requires_effect=False,
                effect_authorized=True,
                external_provider=True,
                provider_id="deepseek",
                model_id="deepseek-v4-flash",
                allow_provider_fallback=False,
                deepseek_physical_swarm=False,
            )],
        )
        self.assertIn("AWJ033_PHYSICAL_SWARM_GATE_REQUIRED", result["reason_codes"])

    def test_selected_route_uses_deterministic_fallback_id(self):
        result = select_creator_studio_route(
            request(),
            [candidate("R1_LOCAL_DETERMINISTIC", route_id="")],
        )
        self.assertEqual("candidate-0", result["selected_route"]["route_id"])
        self.assertEqual("candidate-0", result["evaluated"][0]["route_id"])


if __name__ == "__main__":
    unittest.main()
