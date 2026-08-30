import unittest

from aura_arena_admission import ArenaAdmissionContext
from aura_arena_workgraph import apply_action, project_workgraph
from creator_studio_harness_integration import (
    READY,
    plan_idle_worker_wake,
    prepare_substantive_act,
)


WORKER = "W-HI"
CELL = "H-I-01"
MISSION = "mission:CS-HARNESS-001"
BOARD = "drive:collab-board"
BOARD_REV = "rev:42"
CURRENT = "current:42"


def base_state(*, cells=None, claims=None, worker_current=CURRENT):
    if cells is None:
        cells = [
            {
                "cell_id": CELL,
                "parent_objective": "integrate harness",
                "state": "OPEN",
                "priority": "P0",
                "dependencies": [],
                "required_capabilities": ["reasoning"],
                "effect_class": "D0",
                "reuse_value": 9,
                "estimated_effort": 1,
                "cost_ceiling_provider_usd": 0.0,
                "free_first_route": ["R1_LOCAL_DETERMINISTIC"],
                "expected_output": "integration receipt",
                "acceptance": ["fail closed"],
                "currentness_ref": CURRENT,
                "reopen_conditions": ["currentness changes"],
                "execution_state": "NOT_STARTED",
                "execution_receipt_refs": [],
                "blocker_reason": "",
            }
        ]
    return {
        "schema": "AuraArenaWorkGraphStateV1",
        "project_id": "CS-PROJ-001",
        "mission_ref": MISSION,
        "canonical_orientation_ref": "front-door:canonical",
        "board_ref": BOARD,
        "board_revision": BOARD_REV,
        "route_policy_ref": "H-D:PR322",
        "source_digests": ["sha256:source"],
        "currentness_ref": CURRENT,
        "workers": [
            {
                "worker_id": WORKER,
                "worker_class": "CHATGPT",
                "capabilities": ["reasoning"],
                "currentness_ref": worker_current,
                "joined": True,
                "state": "IDLE",
                "effect_ceiling": "D0",
                "eligible": True,
            }
        ],
        "cells": cells,
        "claims": list(claims or []),
    }


def claim_state(now_ms=1000):
    state = base_state()
    projection = project_workgraph(state, now_ms=now_ms)
    next_state, receipt = apply_action(
        state,
        action={
            "action": "CLAIM",
            "basis_graph_digest": projection["graph_digest"],
            "cell_id": CELL,
            "worker_id": WORKER,
            "lease_ms": 10000,
        },
        now_ms=now_ms,
    )
    return next_state, receipt


def admission_for(state, *, now_ms=1000, route_tier="R1", **overrides):
    projection = project_workgraph(state, now_ms=now_ms)
    values = dict(
        worker_id=WORKER,
        role="worker",
        capabilities=("reasoning",),
        effect_ceiling="D0",
        project_coordinate="aura://creator-studio/project/CS-PROJ-001",
        front_door_ref="drive:front-door",
        collab_board_ref=BOARD,
        mission_ref=MISSION,
        purpose_ref="purpose:continual-work",
        temporary_mission_active=True,
        temporary_mission_ref="drive:CS-HARNESS-001",
        authoritative_head_ref=CURRENT,
        currentness_current=True,
        join_record_ref="board:join:W-HI",
        claimed_cells=(CELL,),
        sibling_state_ref=BOARD_REV,
        sibling_state_digest=projection["graph_digest"],
        route_tier=route_tier,
        route_reason="local deterministic integration",
    )
    values.update(overrides)
    return ArenaAdmissionContext(**values)


def route_request(**overrides):
    values = dict(
        task_id=CELL,
        project_currentness="CURRENT",
        paid_provider_authorized=False,
        owner_swarm_deploy_authorized=False,
        earned_swarm_reason="",
        awj033_physical_swarm_ready=False,
        pro_escalation_earned=False,
        pro_escalation_ref="",
        cost_ceiling_usd=0.0,
    )
    values.update(overrides)
    return values


def local_candidate(**overrides):
    values = dict(
        route_id="local-r1",
        route_class="R1_LOCAL_DETERMINISTIC",
        currentness="CURRENT",
        capability_fit=True,
        adequacy="ELIGIBLE",
        requires_effect=False,
        effect_authorized=False,
        external_provider=False,
        provider_id="",
        model_id="",
        allow_provider_fallback=False,
        paid=False,
        estimated_marginal_cost_usd=0.0,
        deepseek_physical_swarm=False,
    )
    values.update(overrides)
    return values


class CrossLaneHarnessIntegrationTests(unittest.TestCase):
    def test_idle_worker_gets_exactly_one_nonexecution_wake_then_claim(self):
        state = base_state()
        wake = plan_idle_worker_wake(state, worker_id=WORKER, now_ms=1000)
        self.assertEqual("SELECT_WORK", wake["decision"])
        self.assertEqual(CELL, wake["selected_cell_id"])
        self.assertTrue(wake["delivery_required"])
        self.assertFalse(wake["runtime_execution_proven"])
        self.assertFalse(wake["effect_allowed"])

        projection = project_workgraph(state, now_ms=1000)
        claimed, receipt = apply_action(
            state,
            action={
                "action": "CLAIM",
                "basis_graph_digest": projection["graph_digest"],
                "cell_id": wake["selected_cell_id"],
                "worker_id": WORKER,
                "lease_ms": 10000,
            },
            now_ms=1000,
        )
        self.assertEqual("CLAIM", receipt["action"])
        self.assertFalse(receipt["runtime_execution_proven"])
        claimed_projection = project_workgraph(claimed, now_ms=1000)
        owned = [
            c for c in claimed_projection["cells"]
            if any(x["worker_id"] == WORKER for x in c["active_claims"])
        ]
        self.assertEqual(1, len(owned))

    def test_valid_claim_admission_and_route_produce_ready_not_execution(self):
        state, _ = claim_state()
        result = prepare_substantive_act(
            admission_ctx=admission_for(state),
            workgraph_state=state,
            worker_id=WORKER,
            now_ms=1000,
            route_request=route_request(),
            route_candidates=[local_candidate()],
        )
        self.assertEqual(READY, result["decision"])
        self.assertEqual(CELL, result["cell_id"])
        self.assertEqual("local-r1", result["route_id"])
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["runtime_execution_proven"])
        self.assertFalse(result["background_execution_claimed"])
        self.assertEqual(0, result["provider_calls"])

    def test_incomplete_admission_stops_before_workgraph_act(self):
        state, _ = claim_state()
        ctx = ArenaAdmissionContext(worker_id=WORKER)
        result = prepare_substantive_act(
            admission_ctx=ctx,
            workgraph_state=state,
            worker_id=WORKER,
            now_ms=1000,
            route_request=route_request(),
            route_candidates=[local_candidate()],
        )
        self.assertEqual("ADMISSION_REQUIRED", result["decision"])
        self.assertFalse(result["execution_authorized"])

    def test_graph_digest_or_board_revision_mismatch_requires_rebase(self):
        state, _ = claim_state()
        result = prepare_substantive_act(
            admission_ctx=admission_for(state, sibling_state_digest="sha256:stale", sibling_state_ref="rev:old"),
            workgraph_state=state,
            worker_id=WORKER,
            now_ms=1000,
            route_request=route_request(),
            route_candidates=[local_candidate()],
        )
        self.assertEqual("REBASE_REQUIRED", result["decision"])
        self.assertIn("GRAPH_DIGEST_MISMATCH", result["reason_codes"])
        self.assertIn("BOARD_REVISION_MISMATCH", result["reason_codes"])

    def test_expired_not_started_claim_is_not_act_ready(self):
        state, _ = claim_state(now_ms=1000)
        ctx = admission_for(state, now_ms=12000)
        result = prepare_substantive_act(
            admission_ctx=ctx,
            workgraph_state=state,
            worker_id=WORKER,
            now_ms=12000,
            route_request=route_request(),
            route_candidates=[local_candidate()],
        )
        self.assertEqual("CLAIM_REQUIRED", result["decision"])
        self.assertIn("NO_ACTIVE_OWNED_CLAIM", result["reason_codes"])

    def test_expired_possible_effect_requires_reconciliation(self):
        state, _ = claim_state(now_ms=1000)
        state["cells"][0]["execution_state"] = "EFFECT_STARTED"
        state["cells"][0]["execution_receipt_refs"] = ["effect:receipt"]
        ctx = admission_for(state, now_ms=12000)
        result = prepare_substantive_act(
            admission_ctx=ctx,
            workgraph_state=state,
            worker_id=WORKER,
            now_ms=12000,
            route_request=route_request(),
            route_candidates=[local_candidate()],
        )
        self.assertEqual("RECONCILE_EFFECT_STATE_REQUIRED", result["decision"])

    def test_worker_with_two_active_claims_fails_closed(self):
        state, _ = claim_state(now_ms=1000)
        second = {
            "cell_id": "H-I-02",
            "parent_objective": "second",
            "state": "CLAIMED",
            "priority": "P1",
            "dependencies": [],
            "required_capabilities": ["reasoning"],
            "effect_class": "D0",
            "reuse_value": 1,
            "estimated_effort": 1,
            "cost_ceiling_provider_usd": 0.0,
            "free_first_route": ["R1_LOCAL_DETERMINISTIC"],
            "expected_output": "second output",
            "acceptance": ["bounded"],
            "currentness_ref": CURRENT,
            "reopen_conditions": [],
            "execution_state": "NOT_STARTED",
            "execution_receipt_refs": [],
            "blocker_reason": "",
        }
        state["cells"].append(second)
        state["claims"].append(
            {
                "claim_id": "b" * 64,
                "cell_id": "H-I-02",
                "worker_id": WORKER,
                "claimed_at_ms": 1000,
                "lease_expires_at_ms": 11000,
                "basis_graph_digest": "a" * 64,
                "currentness_ref": CURRENT,
                "dependency_snapshot": [],
                "capability_snapshot": ["reasoning"],
                "active": True,
                "generation": 1,
            }
        )
        ctx = admission_for(state)
        result = prepare_substantive_act(
            admission_ctx=ctx,
            workgraph_state=state,
            worker_id=WORKER,
            now_ms=1000,
            route_request=route_request(),
            route_candidates=[local_candidate()],
        )
        self.assertEqual("CLAIM_CONFLICT", result["decision"])
        self.assertIn("WORKER_HAS_MULTIPLE_ACTIVE_CLAIMS", result["reason_codes"])

    def test_route_rejection_stops_before_act(self):
        state, _ = claim_state()
        result = prepare_substantive_act(
            admission_ctx=admission_for(state),
            workgraph_state=state,
            worker_id=WORKER,
            now_ms=1000,
            route_request=route_request(),
            route_candidates=[local_candidate(capability_fit=False)],
        )
        self.assertEqual("ROUTE_REQUIRED", result["decision"])
        self.assertIn("CAPABILITY_MISMATCH", result["reason_codes"])

    def test_route_cost_ceiling_cannot_widen_cell_authority(self):
        state, _ = claim_state()
        result = prepare_substantive_act(
            admission_ctx=admission_for(state),
            workgraph_state=state,
            worker_id=WORKER,
            now_ms=1000,
            route_request=route_request(cost_ceiling_usd=1.0),
            route_candidates=[local_candidate()],
        )
        self.assertEqual("ROUTE_BINDING_MISMATCH", result["decision"])
        self.assertIn("ROUTE_COST_CEILING_WIDENING", result["reason_codes"])

    def test_admission_route_tier_must_match_selected_route(self):
        state, _ = claim_state()
        result = prepare_substantive_act(
            admission_ctx=admission_for(state, route_tier="R2"),
            workgraph_state=state,
            worker_id=WORKER,
            now_ms=1000,
            route_request=route_request(),
            route_candidates=[local_candidate()],
        )
        self.assertEqual("ROUTE_BINDING_MISMATCH", result["decision"])
        self.assertIn("ADMISSION_ROUTE_TIER_MISMATCH", result["reason_codes"])


if __name__ == "__main__":
    unittest.main()
