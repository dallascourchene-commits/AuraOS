from dataclasses import FrozenInstanceError, replace

import pytest

from aura_topology_scheduler import (
    ContractViolation,
    EvidenceStateV1,
    FailureStateV1,
    NetworkStateV1,
    PhaseReason,
    ReadinessAdmissionState,
    ReadinessValidationState,
    ResourceStateV1,
    SchedulerPhase,
    SchedulerStateV1,
    SourceAccessStateV1,
    SourceAccessStatus,
    WorkerStateV1,
    WorkloadReadinessAuthorityV1,
    WorkloadReadinessBindingV1,
    WorkloadStateV1,
    classify_phase,
    workload_state_digest,
)

D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64
D4 = "4" * 64

WORKLOAD_OWNER = "drive://wo-c2/workload-owner"
WORKLOAD_RECEIPT = "drive://wo-c2/workload-readiness-receipt"
SOURCE_ACCESS_OWNER = "drive://wo-c2/source-access-owner"
SOURCE_ACCESS_EVIDENCE = "drive://wo-c2/source-access-evidence"


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


def readiness_binding(
    item: WorkloadStateV1,
    *,
    generation: int = 7,
    currentness_digest: str = D3,
    owner_ref: str = WORKLOAD_OWNER,
    validation_state: ReadinessValidationState = ReadinessValidationState.CURRENT,
    content_digest: str | None = None,
    receipt_ref: str | None = WORKLOAD_RECEIPT,
    receipt_digest: str | None = D4,
):
    return WorkloadReadinessBindingV1(
        workload_owner_ref=owner_ref,
        workload_generation=generation,
        workload_currentness_digest=currentness_digest,
        workload_state_digest=content_digest or workload_state_digest(item),
        validation_state=validation_state,
        workload_state_receipt_ref=receipt_ref,
        workload_state_receipt_digest=receipt_digest,
    )


def readiness_authority(
    *,
    generation: int = 7,
    currentness_digest: str = D3,
    owner_ref: str = WORKLOAD_OWNER,
    admission_state: ReadinessAdmissionState = ReadinessAdmissionState.ALLOWED,
    receipt_ref: str | None = WORKLOAD_RECEIPT,
    receipt_digest: str | None = D4,
):
    return WorkloadReadinessAuthorityV1(
        workload_owner_ref=owner_ref,
        workload_generation=generation,
        workload_currentness_digest=currentness_digest,
        admission_state=admission_state,
        configured_receipt_ref=receipt_ref,
        configured_receipt_digest=receipt_digest,
    )


def source_access(
    *,
    status: SourceAccessStatus = SourceAccessStatus.ALLOWED,
    generation: int = 7,
    currentness_digest: str = D3,
):
    return SourceAccessStateV1(
        status=status,
        owner_ref=SOURCE_ACCESS_OWNER,
        source_generation=generation,
        currentness_digest=currentness_digest,
        evidence_ref=SOURCE_ACCESS_EVIDENCE,
        evidence_digest=D2,
    )


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
    generation = changes.pop("source_generation", 7)
    currentness = changes.pop("currentness_digest", D3)
    item = changes.pop("workload", workload())
    binding = changes.pop(
        "workload_readiness_binding",
        readiness_binding(item, generation=generation, currentness_digest=currentness),
    )
    authority = changes.pop(
        "workload_readiness_authority",
        readiness_authority(generation=generation, currentness_digest=currentness),
    )
    access = changes.pop(
        "source_access",
        source_access(generation=generation, currentness_digest=currentness),
    )
    base = SchedulerStateV1(
        objective_id="objective-1",
        objective_class="ARCHITECTURE",
        objective_digest=D1,
        acceptance_criteria_digest=D2,
        consequence_class="BOUNDED",
        current_phase=SchedulerPhase.EXECUTE,
        current_topology_profile="W0",
        recursion_depth=0,
        workload=item,
        workload_readiness_binding=binding,
        workload_readiness_authority=authority,
        evidence=evidence(),
        workers=workers(),
        resources=resources(),
        token_budget_remaining=1000,
        model_budget_microunits=100,
        provider_budget_microunits=200,
        provider_availability_refs=("provider-b", "provider-a"),
        source_locality_refs=("drive", "github"),
        source_generation=generation,
        source_current=True,
        source_access=access,
        currentness_digest=currentness,
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


def with_workload(s: SchedulerStateV1, item: WorkloadStateV1) -> SchedulerStateV1:
    return replace(
        s,
        workload=item,
        workload_readiness_binding=readiness_binding(
            item,
            generation=s.source_generation,
            currentness_digest=s.currentness_digest,
        ),
    )


@pytest.mark.parametrize(
    ("mutator", "expected_phase", "expected_reason"),
    [
        (
            lambda s: replace(s, source_current=False),
            SchedulerPhase.REBASE,
            PhaseReason.HARD_GUARD_REBASE,
        ),
        (
            lambda s: replace(
                s, source_access=source_access(status=SourceAccessStatus.DENIED)
            ),
            SchedulerPhase.REBASE,
            PhaseReason.HARD_GUARD_REBASE,
        ),
        (
            lambda s: replace(
                s,
                workload_readiness_binding=replace(
                    s.workload_readiness_binding,
                    validation_state=ReadinessValidationState.STALE,
                ),
            ),
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
            lambda s: replace(s, evidence=evidence(discovery_gap_count=1)),
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
            lambda s: replace(s, evidence=evidence(verification_debt_count=1)),
            SchedulerPhase.VERIFY,
            PhaseReason.VERIFICATION_DEBT,
        ),
        (
            lambda s: replace(
                with_workload(s, workload(ready_task_count=0)),
                evidence=evidence(reduction_ready_count=1),
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
            lambda s: with_workload(s, workload(ready_task_count=0)),
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
        source_access=source_access(status=SourceAccessStatus.UNKNOWN),
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


def test_non_allowed_source_access_dominates_ready_recovery_and_discovery():
    for status in (SourceAccessStatus.DENIED, SourceAccessStatus.UNKNOWN):
        s = replace(
            state(),
            source_access=source_access(status=status),
            failure=failure(recovery_pending=True),
            evidence=evidence(discovery_gap_count=1),
        )
        decision = classify_phase(s)
        assert decision.phase is SchedulerPhase.REBASE
        assert decision.reason is PhaseReason.HARD_GUARD_REBASE


def test_source_current_true_cannot_substitute_for_source_access():
    s = replace(
        state(),
        source_current=True,
        source_access=source_access(status=SourceAccessStatus.DENIED),
    )
    assert classify_phase(s).phase is SchedulerPhase.REBASE


def test_source_access_generation_and_currentness_are_bound():
    assert classify_phase(
        replace(state(), source_access=source_access(generation=8))
    ).phase is SchedulerPhase.REBASE
    assert classify_phase(
        replace(state(), source_access=source_access(currentness_digest=D1))
    ).phase is SchedulerPhase.REBASE


def test_two_node_directed_cycle_fails_closed():
    with pytest.raises(ContractViolation, match="directed cycle"):
        workload(dependency_edges=(("A", "B"), ("B", "A"))).protected_body()


def test_longer_directed_cycle_fails_closed():
    with pytest.raises(ContractViolation, match="directed cycle"):
        workload(
            dependency_edges=(("A", "B"), ("B", "C"), ("C", "A"))
        ).protected_body()


def test_representative_acyclic_workload_remains_valid():
    body = workload(
        dependency_edges=(("A", "B"), ("A", "C"), ("C", "D"))
    ).protected_body()
    assert body["dependency_edges"] == [["A", "B"], ["A", "C"], ["C", "D"]]


def test_duplicate_and_self_dependency_edges_fail_closed():
    with pytest.raises(ContractViolation, match="duplicate canonical"):
        workload(dependency_edges=(("A", "B"), ("A", "B"))).protected_body()
    with pytest.raises(ContractViolation, match="self-edge"):
        workload(dependency_edges=(("A", "A"),)).protected_body()


def test_repair004_exact_workload_digest_vector_is_preserved():
    item = WorkloadStateV1(
        ready_task_count=1,
        blocked_task_count=1,
        dependency_edges=(("task-a", "task-b"),),
        upstream_prerequisite_refs=("task-a",),
        downstream_dependent_refs=("task-b",),
        critical_path_refs=("task-a", "task-b"),
    )
    assert item.workload_state_digest() == (
        "cf8998555834c67cf479e9c97e87b4195855e06dfc6e78fa4b85313e62c9157e"
    )


def test_critical_path_sequence_order_is_semantic():
    first = workload(critical_path_refs=("A", "B", "C"))
    second = workload(critical_path_refs=("A", "C", "B"))
    assert first.protected_body() != second.protected_body()
    assert first.workload_state_digest() != second.workload_state_digest()


def test_set_like_inputs_remain_permutation_invariant():
    first = state()
    second_workload = replace(
        first.workload,
        dependency_edges=tuple(reversed(first.workload.dependency_edges)),
        upstream_prerequisite_refs=tuple(
            reversed(first.workload.upstream_prerequisite_refs)
        ),
        downstream_dependent_refs=tuple(
            reversed(first.workload.downstream_dependent_refs)
        ),
    )
    second = state(
        workload=second_workload,
        provider_availability_refs=tuple(reversed(first.provider_availability_refs)),
        source_locality_refs=tuple(reversed(first.source_locality_refs)),
        prior_topology_outcome_receipt_refs=tuple(
            reversed(first.prior_topology_outcome_receipt_refs)
        ),
    )
    assert first.workload.workload_state_digest() == second.workload.workload_state_digest()
    assert first.state_digest() == second.state_digest()


def test_fabricated_current_and_unrelated_workload_digest_cannot_execute():
    s = state()
    forged = replace(
        s.workload_readiness_binding,
        validation_state=ReadinessValidationState.CURRENT,
        workload_state_digest=D1,
    )
    decision = classify_phase(replace(s, workload_readiness_binding=forged))
    assert decision.phase is SchedulerPhase.REBASE
    assert decision.reason is PhaseReason.HARD_GUARD_REBASE


def test_workload_mutation_invalidates_reused_readiness_binding():
    original = state()
    mutated = replace(original.workload, ready_task_count=2)
    decision = classify_phase(replace(original, workload=mutated))
    assert decision.phase is SchedulerPhase.REBASE


def test_readiness_owner_generation_and_currentness_must_match_authority():
    s = state()
    assert classify_phase(
        replace(
            s,
            workload_readiness_binding=replace(
                s.workload_readiness_binding, workload_owner_ref="drive://wrong"
            ),
        )
    ).phase is SchedulerPhase.REBASE
    assert classify_phase(
        replace(
            s,
            workload_readiness_authority=replace(
                s.workload_readiness_authority, workload_generation=8
            ),
        )
    ).phase is SchedulerPhase.REBASE
    assert classify_phase(
        replace(
            s,
            workload_readiness_authority=replace(
                s.workload_readiness_authority,
                workload_currentness_digest=D1,
            ),
        )
    ).phase is SchedulerPhase.REBASE


def test_canonically_equivalent_readiness_owner_refs_preserve_execute():
    item = workload()
    nfd_owner = "drive://wo-c2/cafe\u0301"
    nfc_owner = "drive://wo-c2/café"
    s = state(
        workload=item,
        workload_readiness_binding=readiness_binding(item, owner_ref=nfd_owner),
        workload_readiness_authority=readiness_authority(owner_ref=nfc_owner),
    )
    assert s.workload_readiness_binding.protected_body()["workload_owner_ref"] == nfc_owner
    assert classify_phase(s).phase is SchedulerPhase.EXECUTE


def test_current_status_alone_cannot_override_denied_admission():
    s = state()
    denied = replace(
        s.workload_readiness_authority,
        admission_state=ReadinessAdmissionState.DENIED,
    )
    assert classify_phase(
        replace(s, workload_readiness_authority=denied)
    ).phase is SchedulerPhase.REBASE


def test_configured_receipt_must_match_binding_exactly():
    s = state()
    mismatch = replace(
        s.workload_readiness_binding,
        workload_state_receipt_ref="drive://wrong-receipt",
    )
    assert classify_phase(
        replace(s, workload_readiness_binding=mismatch)
    ).phase is SchedulerPhase.REBASE


def test_optional_unconfigured_receipt_does_not_require_fake_evidence():
    item = workload()
    s = state(
        workload=item,
        workload_readiness_binding=readiness_binding(
            item, receipt_ref=None, receipt_digest=None
        ),
        workload_readiness_authority=readiness_authority(
            receipt_ref=None, receipt_digest=None
        ),
    )
    assert classify_phase(s).phase is SchedulerPhase.EXECUTE


def test_positive_execute_requires_all_repaired_guards_and_ready_work():
    decision = classify_phase(state())
    assert decision.phase is SchedulerPhase.EXECUTE
    assert decision.reason is PhaseReason.READY_WORK


def test_readiness_is_sibling_not_workload_digest_content():
    item = workload()
    body = item.protected_body()
    assert set(body) == {
        "ready_task_count",
        "blocked_task_count",
        "dependency_edges",
        "upstream_prerequisite_refs",
        "downstream_dependent_refs",
        "critical_path_refs",
    }
    assert "workload_readiness_binding" not in body
    before = item.workload_state_digest()
    s = state(workload=item)
    changed = replace(
        s,
        workload_readiness_binding=replace(
            s.workload_readiness_binding,
            validation_state=ReadinessValidationState.STALE,
        ),
    )
    assert changed.workload.workload_state_digest() == before
    assert changed.state_digest() != s.state_digest()


def test_state_digest_binds_source_currentness_authority_and_creation_basis():
    base = state().state_digest()
    assert state(source_generation=8).state_digest() != base
    assert state(currentness_digest=D1).state_digest() != base
    assert replace(state(), authority_ceiling_digest=D1).state_digest() != base
    assert replace(state(), creation_stage=5).state_digest() != base


def test_phase_decision_contains_no_topology_or_worker_recommendation():
    body = classify_phase(state()).protected_body()
    assert set(body) == {"schema", "phase", "reason", "state_digest"}
    text = repr(body).lower()
    assert "selected_topology" not in text
    assert "selected_worker" not in text


def test_invalid_basis_points_creation_stage_and_digest_fail_closed():
    with pytest.raises(ContractViolation, match="battery_basis_points"):
        replace(
            state(),
            resources=replace(resources(), battery_basis_points=10001),
        ).state_digest()
    with pytest.raises(ContractViolation, match="creation_stage"):
        replace(state(), creation_stage=11).protected_body()
    with pytest.raises(ContractViolation, match="creation_stage"):
        replace(state(), creation_stage=11).state_digest()
    with pytest.raises(ContractViolation, match="objective_digest"):
        replace(state(), objective_digest="bad").state_digest()


def test_bool_is_not_accepted_as_integer():
    with pytest.raises(ContractViolation, match="source_generation"):
        replace(state(), source_generation=True).state_digest()
    with pytest.raises(ContractViolation, match="workload_readiness.workload_generation"):
        state(source_generation=True).workload_readiness_binding.protected_body()


def test_state_and_new_relations_are_frozen():
    item = state()
    with pytest.raises(FrozenInstanceError):
        item.objective_id = "changed"
    with pytest.raises(FrozenInstanceError):
        item.source_access.status = SourceAccessStatus.DENIED
    with pytest.raises(FrozenInstanceError):
        item.workload_readiness_binding.validation_state = ReadinessValidationState.STALE


def test_decision_digest_is_deterministic_and_state_bound():
    a = classify_phase(state())
    b = classify_phase(state())
    assert a.decision_digest() == b.decision_digest()
    changed = classify_phase(state(source_generation=8))
    assert a.decision_digest() != changed.decision_digest()
