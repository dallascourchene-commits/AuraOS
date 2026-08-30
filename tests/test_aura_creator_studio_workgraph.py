import json
import unittest

from aura_creator_studio_workgraph import (
    ClaimCASStatus,
    ClaimLease,
    CompletionRecord,
    ExecutionState,
    Priority,
    ProjectionStatus,
    RecoveryDecision,
    SelectionDecision,
    WorkGraphParseError,
    WorkItem,
    WorkState,
    WorkerSpec,
    WorkerState,
    compile_successor_residual,
    parse_group_work_orders,
    prepare_claim_compare_and_set,
    project_workgraph,
    projection_json,
    reconcile_stale_claim,
    select_next_work,
)

NOW = 2_000_000
CURRENT = "front-door-r8"


def worker(worker_id="W1", capabilities=("python", "drive"), *, state=WorkerState.IDLE, ceiling="D0", current=CURRENT):
    return WorkerSpec(
        worker_id=worker_id,
        worker_class="CHATGPT",
        capabilities=capabilities,
        join_ref=f"board:join:{worker_id}",
        currentness_basis=current,
        effect_ceiling=ceiling,
        state=state,
    )


def item(
    work_id,
    state=WorkState.OPEN,
    priority=Priority.P1,
    dependencies=(),
    required=(),
    order=0,
    *,
    current=CURRENT,
    lease=None,
    execution=ExecutionState.NOT_STARTED,
    receipts=(),
    cost=0,
    required_effect="D0",
):
    return WorkItem(
        work_id=work_id,
        state=state,
        priority=priority,
        parent_objective="O5 reusable Creator Studio runtime",
        residual=f"Close {work_id}",
        currentness_basis=current,
        dependencies=dependencies,
        required_capabilities=required,
        expected_output="receipt",
        acceptance=("tests pass",),
        cost_ceiling_microusd=cost,
        required_effect_ceiling=required_effect,
        claim_lease=lease,
        execution_state=execution,
        execution_receipt_refs=receipts,
        hydration_refs=(f"ref:{work_id}",),
        source_order=order,
    )


def snapshot(work_items, workers=None, *, board_rev="board-r1", invalidators=()):
    return project_workgraph(
        project_id="CS-PROJ-001",
        canonical_orientation_ref="drive:front-door",
        canonical_orientation_revision=CURRENT,
        board_ref="drive:board",
        board_revision=board_rev,
        generated_at_ms=NOW,
        workers=tuple(workers or (worker(),)),
        work_items=tuple(work_items),
        route_policy_ref="drive:route-policy",
        source_digests=("source-a",),
        currentness_invalidators=invalidators,
    )


class WorkGraphTests(unittest.TestCase):
    def test_01_projection_is_deterministic_coordination_only(self):
        a = snapshot((item("A"),))
        b = snapshot((item("A"),))
        self.assertEqual(a.revision, b.revision)
        payload = json.loads(projection_json(a))
        self.assertEqual("WorkGraphProjectionV1", payload["schema"])
        self.assertFalse(payload["execution_proven"])
        self.assertFalse(payload["wake_effect_started"])

    def test_02_selector_prefers_p0_then_board_order(self):
        snap = snapshot((
            item("P1", priority=Priority.P1, order=0),
            item("P0-B", priority=Priority.P0, order=2),
            item("P0-A", priority=Priority.P0, order=1),
        ))
        proposal = select_next_work(snap, worker_id="W1")
        self.assertEqual(SelectionDecision.SELECT_WORK, proposal.decision)
        self.assertEqual("P0-A", proposal.selected_work_id)
        self.assertFalse(proposal.effect_allowed)

    def test_03_live_lease_prevents_duplicate_selection(self):
        lease = ClaimLease("L1", "W1", NOW - 100, NOW + 1000, "board-r1", CURRENT)
        snap = snapshot((item("A", state=WorkState.CLAIMED, lease=lease),), workers=(worker("W1"), worker("W2")))
        self.assertFalse(snap.work[0].eligible)
        self.assertEqual(SelectionDecision.IDLE, select_next_work(snap, worker_id="W2").decision)

    def test_04_stale_revision_claim_fails_closed(self):
        snap = snapshot((item("A"),))
        result = prepare_claim_compare_and_set(
            snap, expected_projection_revision="old", worker_id="W1", work_id="A",
            lease_id="L1", acquired_at_ms=NOW, expires_at_ms=NOW + 1000,
        )
        self.assertEqual(ClaimCASStatus.STALE, result.status)
        self.assertIn("CLAIM_STALE_REBASE_REQUIRED", result.reason_codes)
        self.assertFalse(result.effect_started)

    def test_05_unsatisfied_dependency_not_selected(self):
        snap = snapshot((item("A"), item("B", dependencies=("A",), order=1)))
        b = next(p for p in snap.work if p.work.work_id == "B")
        self.assertFalse(b.eligible)

    def test_06_capability_mismatch_not_selected(self):
        snap = snapshot((item("A", required=("image",)),), workers=(worker(capabilities=("python",)),))
        self.assertFalse(snap.work[0].eligible)

    def test_07_effect_ceiling_blocks_higher_effect_work(self):
        snap = snapshot((item("A", required_effect="D1"),), workers=(worker(ceiling="D0"),))
        self.assertFalse(snap.work[0].eligible)

    def test_08_complete_coordination_state_does_not_prove_execution(self):
        snap = snapshot((item("A", state=WorkState.COMPLETE),))
        self.assertFalse(snap.execution_proven)
        self.assertEqual(ExecutionState.NOT_STARTED, snap.work[0].work.execution_state)

    def test_09_verified_execution_requires_receipt_refs(self):
        with self.assertRaisesRegex(ValueError, "VERIFIED_COMPLETE requires"):
            item("A", execution=ExecutionState.VERIFIED_COMPLETE)
        accepted = item("A", execution=ExecutionState.VERIFIED_COMPLETE, receipts=("effect:receipt",))
        self.assertEqual(("effect:receipt",), accepted.execution_receipt_refs)

    def test_10_stale_lease_not_started_can_reopen(self):
        lease = ClaimLease("L1", "W1", NOW - 5000, NOW - 1, "board-r1", CURRENT)
        snap = snapshot((item("A", state=WorkState.CLAIMED, lease=lease),))
        proposal = reconcile_stale_claim(snap.work[0], now_ms=NOW, currentness_basis=CURRENT)
        self.assertEqual(RecoveryDecision.RELEASE_TO_OPEN, proposal.decision)
        self.assertEqual(WorkState.OPEN, proposal.recovered_state)

    def test_11_stale_lease_unknown_effect_blocks_replay(self):
        lease = ClaimLease("L1", "W1", NOW - 5000, NOW - 1, "board-r1", CURRENT)
        snap = snapshot((item("A", state=WorkState.CLAIMED, lease=lease, execution=ExecutionState.UNKNOWN),))
        proposal = reconcile_stale_claim(snap.work[0], now_ms=NOW, currentness_basis=CURRENT)
        self.assertEqual(RecoveryDecision.RECONCILE_EFFECT_STATE_REQUIRED, proposal.decision)
        self.assertEqual(WorkState.BLOCKED, proposal.recovered_state)

    def test_12_restart_reprojection_same_revision(self):
        lease = ClaimLease("L1", "W1", NOW - 100, NOW + 1000, "board-r1", CURRENT)
        work = (item("A", state=WorkState.CLAIMED, lease=lease),)
        self.assertEqual(snapshot(work).revision, snapshot(work).revision)

    def test_13_currentness_invalidator_forces_rebase(self):
        snap = snapshot((item("A"),), invalidators=("front-door-moved",))
        self.assertEqual(ProjectionStatus.STALE, snap.projection_status)
        self.assertEqual(SelectionDecision.REBASE, select_next_work(snap, worker_id="W1").decision)

    def test_14_idle_selection_is_zero_effect(self):
        snap = snapshot((item("DONE", state=WorkState.COMPLETE),))
        proposal = select_next_work(snap, worker_id="W1")
        self.assertEqual(SelectionDecision.IDLE, proposal.decision)
        self.assertFalse(proposal.runtime_effect_started)
        self.assertFalse(proposal.effect_allowed)

    def test_15_same_generation_coalesces_to_same_revision(self):
        self.assertEqual(snapshot((item("A"),)).revision, snapshot((item("A"),)).revision)

    def test_16_selection_never_grants_provider_effect(self):
        proposal = select_next_work(snapshot((item("A"),)), worker_id="W1")
        self.assertFalse(proposal.effect_allowed)
        self.assertFalse(proposal.runtime_effect_started)

    def test_17_board_prose_cannot_replace_canonical_orientation_owner(self):
        snap = snapshot((item("A"),))
        self.assertEqual("drive:front-door", snap.canonical_orientation_ref)
        self.assertEqual(CURRENT, snap.canonical_orientation_revision)

    def test_18_successor_residual_is_deterministic_and_deduplicatable(self):
        parent = item("A", state=WorkState.COMPLETE)
        completion = CompletionRecord("A", "W1", ("receipt:1",), residual="Verify runtime consumer", residual_priority=Priority.P0)
        a = compile_successor_residual(parent=parent, completion=completion, currentness_basis=CURRENT, source_order=10)
        b = compile_successor_residual(parent=parent, completion=completion, currentness_basis=CURRENT, source_order=10)
        self.assertEqual(a, b)
        self.assertEqual(("receipt:1",), a.hydration_refs)

    def test_19_no_residual_does_not_invent_successor(self):
        parent = item("A", state=WorkState.COMPLETE)
        completion = CompletionRecord("A", "W1", ("receipt:1",))
        self.assertIsNone(compile_successor_residual(parent=parent, completion=completion, currentness_basis=CURRENT, source_order=10))

    def test_20_successor_preserves_parent_complete_history(self):
        parent = item("A", state=WorkState.COMPLETE)
        completion = CompletionRecord("A", "W1", ("receipt:1",), residual="New generation")
        child = compile_successor_residual(parent=parent, completion=completion, currentness_basis=CURRENT, source_order=10)
        self.assertEqual(WorkState.COMPLETE, parent.state)
        self.assertEqual(("A",), child.dependencies)

    def test_21_priority_tie_break_is_lexically_stable(self):
        snap = snapshot((item("B", order=0), item("A", order=0)))
        self.assertEqual("A", select_next_work(snap, worker_id="W1").selected_work_id)

    def test_22_malformed_group_work_order_is_typed_error(self):
        with self.assertRaisesRegex(WorkGraphParseError, "MALFORMED_GROUP_WO_HEADER"):
            parse_group_work_orders("GROUP-WO broken header", currentness_basis=CURRENT)

    def test_23_duplicate_worker_identity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            snapshot((item("A"),), workers=(worker("W1"), worker("W1")))

    def test_24_stale_lease_effect_started_requires_reconcile(self):
        lease = ClaimLease("L1", "W1", NOW - 5000, NOW - 1, "board-r1", CURRENT)
        snap = snapshot((item("A", state=WorkState.CLAIMED, lease=lease, execution=ExecutionState.EFFECT_STARTED),))
        proposal = reconcile_stale_claim(snap.work[0], now_ms=NOW, currentness_basis=CURRENT)
        self.assertEqual(RecoveryDecision.RECONCILE_EFFECT_STATE_REQUIRED, proposal.decision)

    def test_25_superseded_work_not_claimable(self):
        snap = snapshot((item("A", state=WorkState.SUPERSEDED),))
        result = prepare_claim_compare_and_set(
            snap, expected_projection_revision=snap.revision, worker_id="W1", work_id="A",
            lease_id="L1", acquired_at_ms=NOW, expires_at_ms=NOW + 1000,
        )
        self.assertEqual(ClaimCASStatus.REJECTED, result.status)

    def test_26_missing_cost_remains_unknown_not_zero(self):
        snap = snapshot((item("UNKNOWN", cost=None, order=0), item("ZERO", cost=0, order=1)))
        self.assertEqual("ZERO", select_next_work(snap, worker_id="W1").selected_work_id)
        unknown = next(p for p in snap.work if p.work.work_id == "UNKNOWN")
        self.assertIn("COST_CEILING_UNKNOWN", unknown.reasons)

    def test_27_selection_returns_minimum_hydration_refs(self):
        proposal = select_next_work(snapshot((item("A"),)), worker_id="W1")
        self.assertEqual(("ref:A",), proposal.required_hydration_refs)

    def test_28_repeat_claim_preparation_is_deterministic_and_zero_effect(self):
        snap = snapshot((item("A"),))
        kwargs = dict(
            expected_projection_revision=snap.revision, worker_id="W1", work_id="A",
            lease_id="L1", acquired_at_ms=NOW, expires_at_ms=NOW + 1000,
        )
        a = prepare_claim_compare_and_set(snap, **kwargs)
        b = prepare_claim_compare_and_set(snap, **kwargs)
        self.assertEqual(a, b)
        self.assertEqual(ClaimCASStatus.READY, a.status)
        self.assertFalse(a.effect_started)

    def test_29_crash_after_claim_before_effect_is_recoverable(self):
        lease = ClaimLease("L1", "W1", NOW - 5000, NOW - 1, "board-r1", CURRENT)
        snap = snapshot((item("A", state=WorkState.CLAIMED, lease=lease, execution=ExecutionState.NOT_STARTED),))
        self.assertEqual(RecoveryDecision.RELEASE_TO_OPEN, reconcile_stale_claim(snap.work[0], now_ms=NOW, currentness_basis=CURRENT).decision)

    def test_30_crash_after_effect_admission_is_not_auto_replayed(self):
        lease = ClaimLease("L1", "W1", NOW - 5000, NOW - 1, "board-r1", CURRENT)
        for state in (ExecutionState.EFFECT_ADMITTED, ExecutionState.RESULT_PARTIAL, ExecutionState.FAILED):
            snap = snapshot((item("A", state=WorkState.CLAIMED, lease=lease, execution=state),))
            self.assertEqual(RecoveryDecision.RECONCILE_EFFECT_STATE_REQUIRED, reconcile_stale_claim(snap.work[0], now_ms=NOW, currentness_basis=CURRENT).decision)

    def test_31_parser_extracts_formal_group_wo_subset(self):
        text = """
GROUP-WO | CS-WG-RUNTIME-001 | STATE: OPEN | PRIORITY: P1
PARENT OBJECTIVE: O5 reusable Creator Studio project/sub-arena pattern.
RESIDUAL: implement deterministic WorkGraph projection.
DEPENDENCIES: NONE
FREE-FIRST ROUTE: R0 reuse -> R1 deterministic local
EXPECTED OUTPUT: typed WorkGraph schema/projector/tests/receipt.
ACCEPTANCE: 20 tests pass.
COST CEILING: $0 provider.
REOPEN: board/schema changes.
"""
        parsed = parse_group_work_orders(text, currentness_basis=CURRENT)
        self.assertEqual(1, len(parsed))
        self.assertEqual("CS-WG-RUNTIME-001", parsed[0].work_id)
        self.assertEqual(0, parsed[0].cost_ceiling_microusd)


if __name__ == "__main__":
    unittest.main()
