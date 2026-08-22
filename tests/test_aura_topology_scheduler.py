from dataclasses import FrozenInstanceError, replace

import pytest

from aura_topology_scheduler import (
    ContractViolation,
    EvidenceStateV1,
    FailureStateV1,
    NetworkStateV1,
    PhaseReason,
    ResourceStateV1,
    SchedulerPhase,
    SchedulerStateV1,
    WorkerStateV1,
    WorkloadStateV1,
    classify_phase,
)

D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64
D4 = "4" * 64


def workload(**changes):
    base = WorkloadStateV1(
        ready_task_count=1,
        blocked_task_count=0,
        dependency_edges=(("A", "B"), ("B", "C")),
        upstream_prerequisite_refs=("up-b", "up-a"),
        downstream_dependent_refs=("down-b", "down-a"),
        critical_path_refs=("A", "B", "C"),
    )
    return replace(base, **changes)


def evidence(**changes):
    base = EvidenceStateV1(
        unresolved_uncertainty_count=0,
        contradiction_refs=(),
        dissent_refs=(),
        candidate_count=1,
        target_candidate_count=1,
        verification_debt_count=0,
        discovery_gap_count=0,
        reduction_ready_count=0,
    )
    return replace(base, **changes)


def workers():
    return WorkerStateV1(
        active_worker_count=3,
        logical_position_refs=("Z", "X", "Y"),
        capability_profile_refs=("cap-b", "cap-a"),
        evidence_independence_groups=("group-b", "group-a"),
        queue_depth=1,
        expected_service_time_ms=120,
    )


def resources():
    return ResourceStateV1(
        available_device_refs=("device-b", "device-a"),
        cpu_millicores_available=2000,
        gpu_memory_bytes_available=0,
        npu_unit_count=0,
        ram_bytes_available=4_000_000_000,
        storage_bytes_available=20_000_000_000,
        battery_basis_points=7500,
        thermal_state="NOMINAL",
    )


def network():
    return NetworkStateV1(
        latency_ms=20,
        jitter_ms=3,
        loss_basis_points=25,
        bandwidth_kbps=100_000,
        network_cost_microunits=5,
    )


def failure(**changes):
    base = FailureStateV1(
        failed_worker_count=0,
        timeout_count=0,
        cancellation_pending=False,
        recovery_pending=False,
    )
    return replace(base, **changes)


def state(**changes):
    base = SchedulerStateV1(
        objective_id="objective-1",
        objective_class="ARCHITECTURE",
        objective_digest=D1,
        acceptance_criteria_digest=D2,
        consequence_class="BOUNDED",
        current_phase=SchedulerPhase.EXECUTE,
        current_topology_profile="W0",
        recursion_depth=0,
        workload=workload(),
        evidence=evidence(),
        workers=workers(),
        resources=resources(),
        token_budget_remaining=1000,
        model_budget_microunits=100,
        provider_budget_microunits=200,
        provider_availability_refs=("provider-b", "provider-a"),
        source_locality_refs=("drive", "github"),
        source_generation=7,
        source_current=True,
        currentness_digest=D3,
        semantic_environment="AURA_V9",
        authority_current=True,
        authority_ceiling_digest=D4,
        privacy_class="PROJECT_INTERNAL",
        privacy_admissible=True,
        network=network(),
        failure=failure(),
        prior_topology_outcome_receipt_refs=("top-b", "top-a"),
        prior_handoff_outcome_receipt_refs=("hand-b", "hand-a"),
        prior_outcome_confidence_basis_points=8000,
        creation_stage=4,
        creation_stage_ready=True,
        step_basis_current=True,
    )
    return replace(base, **changes)


@pytest.mark.parametrize(
    ("mutator", "expected_phase", "expected_reason"),
    [
        (
            lambda s: replace(s, source_current=False),
            SchedulerPhase.REBASE,
            PhaseReason.HARD_GUARD_REBASE,
        ),
        (
            lambda s: replace(s, authority_current=False),
            SchedulerPhase.REBASE,
            PhaseReason.HARD_GUARD_REBASE,
        ),
        (
            lambda s: replace(s, privacy_admissible=False),
            SchedulerPhase.REBASE,
            PhaseReason.HARD_GUARD_REBASE,
        ),
        (
            lambda s: replace(s, step_basis_current=False),
            SchedulerPhase.REBASE,
            PhaseReason.HARD_GUARD_REBASE,
        ),
        (
            lambda s: replace(s, failure=failure(recovery_pending=True)),
            SchedulerPhase.RECOVER,
            PhaseReason.RECOVERY_REQUIRED,
        ),
        (
            lambda s: replace(
                s, evidence=evidence(discovery_gap_count=1)
            ),
            SchedulerPhase.DISCOVER,
            PhaseReason.DISCOVERY_GAP,
        ),
        (
            lambda s: replace(
                s, evidence=evidence(candidate_count=1, target_candidate_count=3)
            ),
            SchedulerPhase.DIVERGE,
            PhaseReason.CANDIDATE_DEFICIT,
        ),
        (
            lambda s: replace(
                s, evidence=evidence(contradiction_refs=("conflict-1",))
            ),
            SchedulerPhase.SYNTHESIZE,
            PhaseReason.CONTRADICTION_OR_DISSENT,
        ),
        (
            lambda s: replace(
                s, evidence=evidence(candidate_count=2, target_candidate_count=2)
            ),
            SchedulerPhase.CONVERGE,
            PhaseReason.MULTIPLE_CANDIDATES,
        ),
        (
            lambda s: replace(
                s, evidence=evidence(verification_debt_count=1)
            ),
            SchedulerPhase.VERIFY,
            PhaseReason.VERIFICATION_DEBT,
        ),
        (
            lambda s: replace(
                s, workload=workload(ready_task_count=0),
                evidence=evidence(reduction_ready_count=1)
            ),
            SchedulerPhase.REDUCE,
            PhaseReason.REDUCTION_READY,
        ),
        (
            lambda s: s,
            SchedulerPhase.EXECUTE,
            PhaseReason.READY_WORK,
        ),
        (
            lambda s: replace(s, workload=workload(ready_task_count=0)),
            SchedulerPhase.VERIFY,
            PhaseReason.ASSURANCE_FALLBACK,
        ),
    ],
)
def test_phase_classifier_explicit_order(mutator, expected_phase, expected_reason):
    decision = classify_phase(mutator(state()))
    assert decision.phase is expected_phase
    assert decision.reason is expected_reason


def test_hard_guard_dominates_recovery_and_workflow_signals():
    s = replace(
        state(),
        source_current=False,
        failure=failure(recovery_pending=True),
        evidence=evidence(discovery_gap_count=9),
    )
    assert classify_phase(s).phase is SchedulerPhase.REBASE


def test_recovery_dominates_discovery_and_candidate_work():
    s = replace(
        state(),
        failure=failure(timeout_count=1),
        evidence=evidence(discovery_gap_count=2, candidate_count=0, target_candidate_count=3),
    )
    assert classify_phase(s).phase is SchedulerPhase.RECOVER


def test_state_digest_is_permutation_invariant_for_set_like_inputs():
    first = state()
    second = replace(
        first,
        provider_availability_refs=tuple(reversed(first.provider_availability_refs)),
        source_locality_refs=tuple(reversed(first.source_locality_refs)),
        prior_topology_outcome_receipt_refs=tuple(
            reversed(first.prior_topology_outcome_receipt_refs)
        ),
        workload=replace(
            first.workload,
            dependency_edges=tuple(reversed(first.workload.dependency_edges)),
            upstream_prerequisite_refs=tuple(
                reversed(first.workload.upstream_prerequisite_refs)
            ),
        ),
    )
    assert first.state_digest() == second.state_digest()


def test_state_digest_binds_source_currentness_authority_and_creation_basis():
    base = state().state_digest()
    assert replace(state(), source_generation=8).state_digest() != base
    assert replace(state(), currentness_digest=D1).state_digest() != base
    assert replace(state(), authority_ceiling_digest=D1).state_digest() != base
    assert replace(state(), creation_stage=5).state_digest() != base


def test_phase_decision_contains_no_topology_or_worker_recommendation():
    body = classify_phase(state()).protected_body()
    assert set(body) == {"schema", "phase", "reason", "state_digest"}
    text = repr(body).lower()
    assert "selected_topology" not in text
    assert "selected_worker" not in text


def test_duplicate_and_self_dependency_edges_fail_closed():
    with pytest.raises(ContractViolation, match="duplicate canonical"):
        replace(
            state(),
            workload=replace(
                workload(), dependency_edges=(("A", "B"), ("A", "B"))
            ),
        ).state_digest()
    with pytest.raises(ContractViolation, match="self-edge"):
        replace(
            state(), workload=replace(workload(), dependency_edges=(("A", "A"),))
        ).state_digest()


def test_invalid_basis_points_creation_stage_and_digest_fail_closed():
    with pytest.raises(ContractViolation, match="battery_basis_points"):
        replace(
            state(),
            resources=replace(resources(), battery_basis_points=10001),
        ).state_digest()
    with pytest.raises(ContractViolation, match="creation_stage"):
        replace(state(), creation_stage=11).state_digest()
    with pytest.raises(ContractViolation, match="objective_digest"):
        replace(state(), objective_digest="bad").state_digest()


def test_bool_is_not_accepted_as_integer():
    with pytest.raises(ContractViolation, match="source_generation"):
        replace(state(), source_generation=True).state_digest()


def test_state_is_frozen():
    item = state()
    with pytest.raises(FrozenInstanceError):
        item.objective_id = "changed"


def test_decision_digest_is_deterministic_and_state_bound():
    a = classify_phase(state())
    b = classify_phase(state())
    assert a.decision_digest() == b.decision_digest()
    changed = classify_phase(replace(state(), source_generation=8))
    assert a.decision_digest() != changed.decision_digest()
