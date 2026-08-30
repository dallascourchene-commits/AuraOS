import unittest

from aura_creator_studio_workgraph import (
    ClaimCASStatus,
    ClaimLease,
    Priority,
    SelectionDecision,
    WorkItem,
    WorkState,
    WorkerSpec,
    prepare_claim_compare_and_set,
    project_workgraph,
    select_next_work,
)

NOW = 2_000_000
CURRENT = "front-door-r8"


def worker(worker_id):
    return WorkerSpec(
        worker_id=worker_id,
        worker_class="CHATGPT",
        capabilities=("python", "drive"),
        join_ref=f"board:join:{worker_id}",
        currentness_basis=CURRENT,
        effect_ceiling="D0",
    )


def item(work_id, *, state=WorkState.OPEN, dependencies=(), lease: ClaimLease | None = None, order=0):
    return WorkItem(
        work_id=work_id,
        state=state,
        priority=Priority.P1,
        parent_objective="CS-HARNESS-001 H-C",
        residual=f"Close {work_id}",
        currentness_basis=CURRENT,
        dependencies=dependencies,
        required_capabilities=("python",),
        expected_output="receipt",
        acceptance=("transition is receipt-bound",),
        cost_ceiling_microusd=0,
        claim_lease=lease,
        hydration_refs=(f"ref:{work_id}",),
        source_order=order,
    )


def snapshot(work_items, *, board_revision="board-r1"):
    return project_workgraph(
        project_id="CS-PROJ-001",
        canonical_orientation_ref="drive:front-door",
        canonical_orientation_revision=CURRENT,
        board_ref="drive:board",
        board_revision=board_revision,
        generated_at_ms=NOW,
        workers=(worker("W1"), worker("W2")),
        work_items=work_items,
        route_policy_ref="drive:route-policy",
    )


class WorkGraphTransitionTests(unittest.TestCase):
    def test_dependency_completion_makes_downstream_newly_eligible(self):
        before = snapshot((item("A"), item("B", dependencies=("A",), order=1)))
        before_b = next(projection for projection in before.work if projection.work.work_id == "B")
        self.assertFalse(before_b.eligible)

        after = snapshot((item("A", state=WorkState.COMPLETE), item("B", dependencies=("A",), order=1)))
        after_b = next(projection for projection in after.work if projection.work.work_id == "B")
        self.assertTrue(after_b.eligible)
        self.assertEqual("B", select_next_work(after, worker_id="W1").selected_work_id)

    def test_reprojection_after_first_claim_blocks_second_worker(self):
        open_snapshot = snapshot((item("A"),))
        prepared = prepare_claim_compare_and_set(
            open_snapshot,
            expected_projection_revision=open_snapshot.revision,
            worker_id="W1",
            work_id="A",
            lease_id="L1",
            acquired_at_ms=NOW,
            expires_at_ms=NOW + 1000,
        )
        self.assertEqual(ClaimCASStatus.READY, prepared.status)

        claimed_snapshot = snapshot(
            (item("A", state=WorkState.CLAIMED, lease=prepared.proposed_lease),),
            board_revision="board-r2",
        )
        self.assertEqual(
            SelectionDecision.IDLE,
            select_next_work(claimed_snapshot, worker_id="W2").decision,
        )


if __name__ == "__main__":
    unittest.main()
