import json
import unittest

from aura_creator_studio_workgraph import (
    ClaimRecord,
    CompletionRecord,
    Priority,
    WorkItem,
    WorkState,
    WorkerSpec,
    compile_successor_residual,
    parse_group_work_orders,
    project_workgraph,
    projection_json,
    select_next_work,
)

NOW = 2_000_000
CURRENT = "front-door-r8"


def worker(worker_id="W1", capabilities=("python", "drive")):
    return WorkerSpec(worker_id, capabilities, CURRENT, NOW - 1000)


def item(work_id, state=WorkState.OPEN, priority=Priority.P1, dependencies=(), required=(), order=0):
    return WorkItem(
        work_id=work_id,
        state=state,
        priority=priority,
        parent_objective="O5 reusable Creator Studio runtime",
        residual=f"Close {work_id}",
        currentness_ref=CURRENT,
        dependencies=dependencies,
        required_capabilities=required,
        expected_output="receipt",
        source_order=order,
    )


class WorkGraphTests(unittest.TestCase):
    def test_projection_is_deterministic_and_never_proves_execution(self):
        kwargs = dict(
            arena_id="CS-PROJ-001",
            currentness_ref=CURRENT,
            observed_at_ms=NOW,
            workers=(worker(),),
            work_items=(item("A"),),
        )
        a = project_workgraph(**kwargs)
        b = project_workgraph(**kwargs)
        self.assertEqual(a.digest, b.digest)
        self.assertFalse(a.execution_proven)
        payload = json.loads(projection_json(a))
        self.assertTrue(payload["coordination_only"])
        self.assertFalse(payload["execution_proven"])
        self.assertFalse(payload["wake_effect_started"])

    def test_selector_prefers_p0_then_board_order_and_requires_claim(self):
        snapshot = project_workgraph(
            arena_id="CS-PROJ-001", currentness_ref=CURRENT, observed_at_ms=NOW,
            workers=(worker(),),
            work_items=(
                item("P1", priority=Priority.P1, order=0),
                item("P0-B", priority=Priority.P0, order=2),
                item("P0-A", priority=Priority.P0, order=1),
            ),
        )
        proposal = select_next_work(snapshot, worker_id="W1")
        self.assertEqual("P0-A", proposal.work_id)
        self.assertTrue(proposal.claim_required)
        self.assertTrue(proposal.wake_needed)
        self.assertFalse(proposal.runtime_effect_started)

    def test_dependency_and_capability_fit_block_unqualified_work(self):
        snapshot = project_workgraph(
            arena_id="CS-PROJ-001", currentness_ref=CURRENT, observed_at_ms=NOW,
            workers=(worker(capabilities=("drive",)),),
            work_items=(
                item("A", state=WorkState.OPEN, required=("python",)),
                item("B", dependencies=("A",), order=1),
            ),
        )
        self.assertIsNone(select_next_work(snapshot, worker_id="W1").work_id)
        reasons = {projection.work.work_id: projection.reasons for projection in snapshot.work}
        self.assertIn("NO_CAPABILITY_FIT", reasons["A"])
        self.assertTrue(any(reason.startswith("DEPENDENCY_BLOCKED") for reason in reasons["B"]))

    def test_live_claim_prevents_collision(self):
        claim = ClaimRecord("claim-a", "A", "W1", NOW - 1000, NOW - 500)
        snapshot = project_workgraph(
            arena_id="CS-PROJ-001", currentness_ref=CURRENT, observed_at_ms=NOW,
            workers=(worker("W1"), worker("W2")), work_items=(item("A"),),
            claims=(claim,), stale_after_ms=10_000,
        )
        self.assertEqual(WorkState.CLAIMED, snapshot.work[0].effective_state)
        self.assertFalse(snapshot.work[0].eligible)
        self.assertIsNone(select_next_work(snapshot, worker_id="W2").work_id)

    def test_stale_claim_is_recoverable_without_execution_claim(self):
        claim = ClaimRecord("claim-a", "A", "W1", NOW - 20_000, NOW - 20_000)
        snapshot = project_workgraph(
            arena_id="CS-PROJ-001", currentness_ref=CURRENT, observed_at_ms=NOW,
            workers=(worker("W1"), worker("W2")),
            work_items=(item("A", state=WorkState.CLAIMED),),
            claims=(claim,), stale_after_ms=10_000,
        )
        projection = snapshot.work[0]
        self.assertTrue(projection.stale_claim_recoverable)
        self.assertTrue(projection.eligible)
        proposal = select_next_work(snapshot, worker_id="W2")
        self.assertEqual("A", proposal.work_id)
        self.assertTrue(proposal.stale_recovery_required)
        self.assertFalse(proposal.runtime_effect_started)

    def test_claim_collision_fails_closed(self):
        claims = (
            ClaimRecord("c1", "A", "W1", NOW - 1000, NOW - 500),
            ClaimRecord("c2", "A", "W2", NOW - 900, NOW - 400),
        )
        snapshot = project_workgraph(
            arena_id="CS-PROJ-001", currentness_ref=CURRENT, observed_at_ms=NOW,
            workers=(worker("W1"), worker("W2")), work_items=(item("A"),),
            claims=claims, stale_after_ms=10_000,
        )
        self.assertFalse(snapshot.work[0].eligible)
        self.assertIn("CLAIM_COLLISION", {finding.code for finding in snapshot.findings})

    def test_successor_residual_is_explicit_and_deterministic(self):
        parent = item("A", state=WorkState.COMPLETE)
        completion = CompletionRecord(
            "A", "W1", ("receipt:1",), residual="Verify the runtime consumer",
            residual_priority=Priority.P0, residual_required_capabilities=("python",),
        )
        a = compile_successor_residual(
            parent=parent, completion=completion, currentness_ref=CURRENT, source_order=10,
        )
        b = compile_successor_residual(
            parent=parent, completion=completion, currentness_ref=CURRENT, source_order=10,
        )
        self.assertEqual(a, b)
        self.assertTrue(a.work_id.startswith("A::RESIDUAL::"))
        self.assertEqual(("A",), a.dependencies)
        self.assertEqual(WorkState.OPEN, a.state)

    def test_no_residual_means_no_invented_successor(self):
        parent = item("A", state=WorkState.COMPLETE)
        completion = CompletionRecord("A", "W1", ("receipt:1",))
        self.assertIsNone(
            compile_successor_residual(
                parent=parent, completion=completion, currentness_ref=CURRENT, source_order=10,
            )
        )

    def test_stale_currentness_blocks_selection(self):
        stale = WorkItem("A", WorkState.OPEN, Priority.P0, "O5", "do it", "old-head")
        snapshot = project_workgraph(
            arena_id="CS-PROJ-001", currentness_ref=CURRENT, observed_at_ms=NOW,
            workers=(worker(),), work_items=(stale,),
        )
        self.assertFalse(snapshot.work[0].eligible)
        self.assertIn("STALE_WORK_CURRENTNESS", snapshot.work[0].reasons)

    def test_parse_formal_group_wo_subset(self):
        text = """
GROUP-WO | CS-WG-RUNTIME-001 | STATE: OPEN | PRIORITY: P1
PARENT OBJECTIVE: O5 reusable Creator Studio project/sub-arena pattern.
RESIDUAL: implement deterministic WorkGraph projection.
DEPENDENCIES: NONE
EXPECTED OUTPUT: typed WorkGraph schema/projector/tests/receipt.
COST CEILING: $0 provider.
REOPEN: board/schema changes.

GROUP-WO | BLOCKED-1 | STATE: BLOCKED on A | PRIORITY: P0
PARENT OBJECTIVE: O2 hero.
RESIDUAL: blocked thing.
DEPENDENCIES: CS-WG-RUNTIME-001
EXPECTED OUTPUT: packet.
COST CEILING: $0.
REOPEN: dependency closes.
"""
        parsed = parse_group_work_orders(text, currentness_ref=CURRENT)
        self.assertEqual(2, len(parsed))
        self.assertEqual("CS-WG-RUNTIME-001", parsed[0].work_id)
        self.assertEqual(Priority.P1, parsed[0].priority)
        self.assertEqual(WorkState.BLOCKED, parsed[1].state)
        self.assertEqual(("CS-WG-RUNTIME-001",), parsed[1].dependencies)


if __name__ == "__main__":
    unittest.main()
