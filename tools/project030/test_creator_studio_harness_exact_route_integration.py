from __future__ import annotations

import unittest
from unittest.mock import patch

from aura_arena_route_binding import select_exact_bound_route
from creator_studio_harness_exact_route_integration import prepare_exact_bound_substantive_act


def request(**overrides):
    row = {
        "task_id": "cell:1",
        "project_currentness": "CURRENT",
        "route_policy_ref": "policy:42",
        "currentness_ref": "head:42",
        "cost_ceiling_usd": 0.0,
    }
    row.update(overrides)
    return row


def candidate(route_id="r1", **overrides):
    row = {
        "route_id": route_id,
        "route_class": "R1_LOCAL_DETERMINISTIC",
        "route_policy_ref": "policy:42",
        "currentness_ref": "head:42",
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
        "estimated_marginal_cost_usd": 0.0,
    }
    row.update(overrides)
    return row


def fake_selector(req, candidates):
    if not candidates:
        return {"schema": "RouterV1", "decision": "NO_ELIGIBLE_ROUTE", "selected_route": None, "reason_codes": ["NONE"]}
    chosen = candidates[0]
    return {
        "schema": "RouterV1",
        "decision": "ROUTE_SELECTED",
        "selected_route": {"route_id": chosen["route_id"], "route_class": chosen["route_class"]},
        "reason_codes": ["OK"],
    }


class ExactRouteGenerationBindingTests(unittest.TestCase):
    def test_valid_binding_carries_exact_refs_and_zero_authority(self):
        result = select_exact_bound_route(
            request=request(),
            candidates=[candidate()],
            expected_route_policy_ref="policy:42",
            expected_currentness_ref="head:42",
            selector=fake_selector,
        )
        self.assertEqual("ROUTE_SELECTED", result["decision"])
        self.assertEqual("policy:42", result["route_policy_ref"])
        self.assertEqual("head:42", result["currentness_ref"])
        self.assertEqual("policy:42", result["selected_route"]["route_policy_ref"])
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["runtime_execution_proven"])

    def test_stale_policy_request_rebases(self):
        result = select_exact_bound_route(
            request=request(route_policy_ref="policy:old"),
            candidates=[candidate()],
            expected_route_policy_ref="policy:42",
            expected_currentness_ref="head:42",
            selector=fake_selector,
        )
        self.assertEqual("REBASE_REQUIRED", result["decision"])
        self.assertIn("ROUTE_POLICY_REF_MISMATCH", result["reason_codes"])

    def test_wrong_currentness_ref_rebases_despite_current_label(self):
        result = select_exact_bound_route(
            request=request(currentness_ref="head:old"),
            candidates=[candidate()],
            expected_route_policy_ref="policy:42",
            expected_currentness_ref="head:42",
            selector=fake_selector,
        )
        self.assertEqual("REBASE_REQUIRED", result["decision"])
        self.assertIn("ROUTE_CURRENTNESS_REF_MISMATCH", result["reason_codes"])

    def test_foreign_policy_candidate_is_filtered(self):
        seen = []
        def selector(req, candidates):
            seen.extend(x["route_id"] for x in candidates)
            return fake_selector(req, candidates)
        result = select_exact_bound_route(
            request=request(),
            candidates=[candidate("foreign", route_policy_ref="other-arena:policy"), candidate("good")],
            expected_route_policy_ref="policy:42",
            expected_currentness_ref="head:42",
            selector=selector,
        )
        self.assertEqual("good", result["selected_route"]["route_id"])
        self.assertEqual(["good"], seen)
        self.assertEqual("foreign", result["filtered_candidates"][0]["route_id"])

    def test_only_foreign_candidates_fail_closed(self):
        result = select_exact_bound_route(
            request=request(),
            candidates=[candidate(route_policy_ref="other:policy")],
            expected_route_policy_ref="policy:42",
            expected_currentness_ref="head:42",
            selector=fake_selector,
        )
        self.assertEqual("NO_EXACT_BOUND_ROUTE", result["decision"])
        self.assertIn("CANDIDATE_ROUTE_POLICY_REF_MISMATCH", result["reason_codes"])

    @patch("creator_studio_harness_exact_route_integration.prepare_substantive_act")
    @patch("creator_studio_harness_exact_route_integration.project_workgraph")
    def test_h_i_wrapper_ready_remains_zero_authority(self, project, prepare):
        project.return_value = {"route_policy_ref": "policy:42", "currentness_ref": "head:42"}
        prepare.return_value = {
            "decision": "READY_FOR_BOUNDED_ACT",
            "reason_codes": ["OK"],
            "integration_receipt_id": "hi:1",
            "worker_id": "W1",
            "cell_id": "cell:1",
            "graph_digest": "graph:1",
            "claim_id": "claim:1",
            "route_id": "r1",
            "route_class": "R1_LOCAL_DETERMINISTIC",
            "board_revision": "board:42",
        }
        result = prepare_exact_bound_substantive_act(
            admission_ctx=object(),
            workgraph_state={},
            worker_id="W1",
            now_ms=1,
            route_request=request(),
            route_candidates=[candidate()],
        )
        self.assertEqual("READY_FOR_BOUNDED_ACT", result["decision"])
        self.assertEqual("policy:42", result["route_policy_ref"])
        self.assertEqual("head:42", result["currentness_ref"])
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["runtime_execution_proven"])
        self.assertFalse(result["background_execution_claimed"])
        self.assertEqual(0, result["provider_calls"])
        self.assertEqual(1, len(prepare.call_args.kwargs["route_candidates"]))

    @patch("creator_studio_harness_exact_route_integration.prepare_substantive_act")
    @patch("creator_studio_harness_exact_route_integration.project_workgraph")
    def test_stale_request_never_reaches_underlying_h_i(self, project, prepare):
        project.return_value = {"route_policy_ref": "policy:42", "currentness_ref": "head:42"}
        result = prepare_exact_bound_substantive_act(
            admission_ctx=object(),
            workgraph_state={},
            worker_id="W1",
            now_ms=1,
            route_request=request(route_policy_ref="policy:old"),
            route_candidates=[candidate()],
        )
        self.assertEqual("REBASE_REQUIRED", result["decision"])
        prepare.assert_not_called()

    @patch("creator_studio_harness_exact_route_integration.prepare_substantive_act")
    @patch("creator_studio_harness_exact_route_integration.project_workgraph")
    def test_duplicate_selected_route_identity_fails_closed(self, project, prepare):
        project.return_value = {"route_policy_ref": "policy:42", "currentness_ref": "head:42"}
        result = prepare_exact_bound_substantive_act(
            admission_ctx=object(),
            workgraph_state={},
            worker_id="W1",
            now_ms=1,
            route_request=request(),
            route_candidates=[candidate("dup"), candidate("dup")],
        )
        self.assertEqual("REBASE_REQUIRED", result["decision"])
        self.assertIn("EXACT_SELECTED_CANDIDATE_NOT_UNIQUE", result["reason_codes"])
        prepare.assert_not_called()


if __name__ == "__main__":
    unittest.main()
