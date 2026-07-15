"""Read-only P8 Civic Commons Planning Board shadow projection.

The adapter binds existing Civic Commons records by exact digest and maps only
already-declared workstreams. It does not interpret participant responses,
consent sufficiency, dissent, pilot status, or governance outcomes.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from aura_civic_planning_inventory import CivicInventoryError, build_civic_surface_inventory
from aura_civic_planning_types import (
    CivicActionMapping,
    CivicCompatibilityReport,
    CivicCompatibilityStatus,
    CivicFinding,
    CivicPlanningInspection,
    CivicRecordBindings,
    CivicSurfaceInventory,
)
from aura_event_contracts import canonical_json, stable_digest
from aura_exact_record_identity import ExactRecordIdentityError, require_exact_copied_fields
from aura_planning_board import (
    ActionContinuityEvidence,
    ActionSpec,
    AuthorityRequirement,
    ConstraintKind,
    ConstraintSpec,
    EffectSpec,
    GoalSpec,
    PlanningBoard,
    PortCardinality,
    PortDirection,
    PortSpec,
    PredicateOperator,
    PredicateSpec,
    ResourceDemand,
    RetryPolicy,
    ReversibilityClass,
)

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


class CivicProjectionError(ValueError):
    def __init__(self, code: str, message: str, *, subject_id: str | None = None, unavailable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.subject_id = subject_id
        self.unavailable = unavailable


def _fail(code: str, message: str, *, subject_id: str | None = None, unavailable: bool = False) -> None:
    raise CivicProjectionError(code, message, subject_id=subject_id, unavailable=unavailable)


def _text(value: Any, name: str) -> str:
    if type(value) is not str or not value.strip():
        _fail("MISSING_REQUIRED_FIELD", f"{name} must be a non-empty string")
    return value.strip()


def _bool(value: Any, name: str) -> bool:
    if type(value) is not bool:
        _fail("INVALID_BOOLEAN", f"{name} must be a boolean")
    return value


def _strings(value: Any, name: str, *, required: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list):
        _fail("INVALID_SEQUENCE", f"{name} must be a JSON array")
    result = tuple(_text(item, f"{name}[]") for item in value)
    if required and not result:
        _fail("EMPTY_SEQUENCE", f"{name} must not be empty")
    if len(result) != len(set(result)):
        _fail("DUPLICATE_VALUE", f"{name} must not contain duplicates")
    return result


def _snapshot(value: Any, name: str) -> dict[str, Any]:
    if value is None:
        _fail("INPUT_UNAVAILABLE", f"{name} is unavailable", unavailable=True)
    try:
        if type(value) is dict:
            raw = dict(value)
        elif isinstance(value, Mapping):
            raw = dict(value.items())
        elif hasattr(value, "to_dict") and callable(value.to_dict):
            raw = value.to_dict()
        elif is_dataclass(value):
            raw = asdict(value)
        else:
            _fail("INPUT_UNAVAILABLE", f"{name} is not a supported record", unavailable=True)
        result = json.loads(canonical_json(raw))
    except CivicProjectionError:
        raise
    except Exception as exc:
        _fail("INPUT_SNAPSHOT_FAILED", f"{name} snapshot failed: {type(exc).__name__}: {exc}", unavailable=True)
    if not isinstance(result, dict):
        _fail("INVALID_RECORD", f"{name} must normalize to an object")
    return result


def _authority(record: Mapping[str, Any], name: str) -> None:
    if record.get("patch_authority") != PATCH_AUTHORITY:
        _fail("PATCH_AUTHORITY_MISMATCH", f"{name} changed exact-source patch authority")
    if _bool(record.get("vsa_patch_authority"), f"{name}.vsa_patch_authority"):
        _fail("ADVISORY_AUTHORITY_ESCALATION", f"{name} grants advisory patch authority")


def _objective_hash(objective: str) -> str:
    return hashlib.blake2b(objective.encode("utf-8"), digest_size=12).hexdigest()


def _failure(error: CivicProjectionError, *, project_id: str | None = None, session_id: str | None = None, project_digest: str | None = None, session_digest: str | None = None, inventory_digest: str | None = None, workstream_count: int = 0) -> CivicPlanningInspection:
    status = CivicCompatibilityStatus.UNAVAILABLE if error.unavailable else CivicCompatibilityStatus.MISMATCHED
    return CivicPlanningInspection(report=CivicCompatibilityReport(
        status=status, project_id=project_id, session_id=session_id,
        project_digest=project_digest, session_digest=session_digest,
        inventory_digest=inventory_digest, bindings_digest=None, board_digest=None,
        workstream_count=workstream_count, mapped_action_count=0,
        mapping_verified=False, source_mutated=False, authority_changed=False,
        governance_blockers=(), findings=(CivicFinding(error.code, error.message, error.subject_id),),
    ))


def _validate_identity(project: dict[str, Any], session: dict[str, Any]) -> tuple[str, str, str, tuple[str, ...]]:
    _authority(project, "project")
    _authority(session, "session")
    if _bool(project.get("non_binding"), "project.non_binding") is not True:
        _fail("BINDING_PROJECT", "project must remain non-binding")
    project_id = _text(project.get("project_id"), "project.project_id")
    session_id = _text(session.get("session_id"), "session.session_id")
    objective = _text(project.get("objective"), "project.objective")
    if session.get("project_id") != project_id or session.get("objective") != objective:
        _fail("PROJECT_SESSION_MISMATCH", "project and session identities disagree")
    if session.get("objective_hash") != _objective_hash(objective):
        _fail("OBJECTIVE_HASH_MISMATCH", "session objective hash is inconsistent")
    constraints = _strings(project.get("mandatory_constraints"), "project.mandatory_constraints", required=True)
    if _strings(session.get("mandatory_constraints"), "session.mandatory_constraints", required=True) != constraints:
        _fail("CONSTRAINT_MISMATCH", "session constraints do not preserve the project")
    profile_set = session.get("profile_set")
    if not isinstance(profile_set, dict) or not profile_set:
        _fail("PROFILE_SET_UNAVAILABLE", "session profile set is unavailable", unavailable=True)
    claimed = _text(profile_set.get("digest"), "profile_set.digest")
    payload = dict(profile_set)
    payload.pop("digest", None)
    expected = hashlib.blake2b(json.dumps(payload, sort_keys=True, default=str).encode(), digest_size=12).hexdigest()
    if claimed != expected:
        _fail("PROFILE_DIGEST_MISMATCH", "profile set digest is inconsistent")
    return project_id, session_id, objective, constraints


def _validate_workstreams(session: dict[str, Any], objective: str, constraints: tuple[str, ...]) -> tuple[dict[str, Any], ...]:
    raw = session.get("workstreams")
    if not isinstance(raw, list) or not raw or not all(isinstance(item, dict) for item in raw):
        _fail("WORKSTREAMS_UNAVAILABLE", "workstreams must be a non-empty array", unavailable=True)
    objective_hash = _objective_hash(objective)
    workstreams = tuple(raw)
    ids: list[str] = []
    for index, item in enumerate(workstreams):
        workstream_id = _text(item.get("workstream_id"), f"workstreams[{index}].workstream_id")
        if workstream_id in ids:
            _fail("DUPLICATE_WORKSTREAM", "workstream ids must be unique", subject_id=workstream_id)
        ids.append(workstream_id)
        _text(item.get("title"), f"workstream[{workstream_id}].title")
        if item.get("parent_objective_hash") != objective_hash:
            _fail("WORKSTREAM_OBJECTIVE_MISMATCH", "workstream objective lineage is inconsistent", subject_id=workstream_id)
        if _strings(item.get("mandatory_constraints"), f"workstream[{workstream_id}].mandatory_constraints") != constraints:
            _fail("WORKSTREAM_CONSTRAINT_MISMATCH", "workstream constraints are inconsistent", subject_id=workstream_id)
        _strings(item.get("dependencies"), f"workstream[{workstream_id}].dependencies")
    positions = {value: index for index, value in enumerate(ids)}
    for item in workstreams:
        for dependency in item["dependencies"]:
            if dependency not in positions or positions[dependency] >= positions[item["workstream_id"]]:
                _fail("WORKSTREAM_DEPENDENCY_MISMATCH", "dependencies must exist and precede the workstream", subject_id=item["workstream_id"])
    return workstreams


def _bind_records(session: dict[str, Any]) -> CivicRecordBindings:
    records: dict[str, dict[str, Any]] = {}
    for name in ("consent_arc", "convergence", "pilot"):
        record = session.get(name)
        if not isinstance(record, dict) or not record:
            _fail("CIVIC_RECORD_UNAVAILABLE", f"{name} is unavailable", subject_id=name, unavailable=True)
        _authority(record, name)
        records[name] = record
    decision = session.get("decision_packet")
    if decision is not None and not isinstance(decision, dict):
        _fail("INVALID_DECISION_PACKET", "decision_packet must be an object")
    if isinstance(decision, dict) and decision:
        _authority(decision, "decision_packet")
        _text(decision.get("packet_id"), "decision_packet.packet_id")
        profile_set = session.get("profile_set")
        assert isinstance(profile_set, dict)
        identity_source = {
            "objective": session.get("objective"),
            "active_profiles": profile_set.get("jurisdiction_profile_refs"),
            "workstreams": session.get("workstreams"),
            "scenarios": session.get("scenarios"),
            "consent_arc": session.get("consent_arc"),
        }
        try:
            require_exact_copied_fields(
                identity_source,
                decision,
                tuple((field, field) for field in identity_source),
            )
        except ExactRecordIdentityError as exc:
            _fail(
                "DECISION_PACKET_IDENTITY_MISMATCH",
                str(exc),
                subject_id=exc.field,
            )
        decision_digest = stable_digest(decision)
    else:
        decision_digest = None
    return CivicRecordBindings(
        consent_arc_digest=stable_digest(records["consent_arc"]),
        convergence_digest=stable_digest(records["convergence"]),
        pilot_digest=stable_digest(records["pilot"]),
        decision_packet_digest=decision_digest,
        decision_packet_present=decision_digest is not None,
        authorization_contract_present=False,
    )


def _constraint(description: str, kind: ConstraintKind, ref: str) -> ConstraintSpec:
    return ConstraintSpec(
        constraint_id=f"constraint_{stable_digest({'description': description, 'kind': kind.value, 'ref': ref}, digest_size=12)}",
        kind=kind, description=description, evidence_refs=(ref,), blocking=True,
    )


def _build_board(project_id: str, session_id: str, objective: str, constraints: tuple[str, ...], workstreams: tuple[dict[str, Any], ...], project_digest: str, session_digest: str, bindings: CivicRecordBindings, inventory: CivicSurfaceInventory) -> tuple[PlanningBoard, tuple[CivicActionMapping, ...], tuple[ActionContinuityEvidence, ...]]:
    project_ref = f"civic-project:blake2b-128:{project_digest}"
    session_ref = f"civic-session:blake2b-128:{session_digest}"
    bindings_ref = f"civic-record-bindings:blake2b-128:{bindings.digest}"
    inventory_ref = f"civic-surface-inventory:blake2b-128:{inventory.digest}"
    state_refs = (project_ref, session_ref, bindings_ref, inventory_ref)
    shared_constraints = tuple(_constraint(item, ConstraintKind.DOMAIN, project_ref) for item in constraints) + (
        _constraint("External human governance authorization is required before execution.", ConstraintKind.POLICY, bindings_ref),
    )
    actions: list[ActionSpec] = []
    mappings: list[CivicActionMapping] = []
    evidence: list[ActionContinuityEvidence] = []
    for index, item in enumerate(workstreams):
        workstream_id = item["workstream_id"]
        workstream_digest = stable_digest(item)
        workstream_ref = f"civic-workstream:blake2b-128:{workstream_digest}"
        refs = (workstream_ref, project_ref, session_ref, bindings_ref, inventory_ref)
        action_id = f"civic_p8_{index:03d}_{stable_digest({'workstream': workstream_id, 'digest': workstream_digest}, digest_size=10)}"
        dependencies = tuple(item["dependencies"])
        preconditions = tuple(PredicateSpec(fact=f"civic.workstream.{dep}.proposal_exists", expected=True, operator=PredicateOperator.EQ) for dep in dependencies) + (
            PredicateSpec(fact="civic.governance.external_human_authorization_required", expected=True, operator=PredicateOperator.EQ),
        )
        actions.append(ActionSpec(
            action_id=action_id, name=f"Shadow project Civic workstream: {item['title']}", domain="civic_commons",
            preconditions=preconditions,
            effects=(EffectSpec(fact=f"civic.workstream.{workstream_id}.shadow_projected", value=True),),
            input_ports=(PortSpec("civic_source_record", "CivicWorkstreamRecord", PortDirection.INPUT, PortCardinality.ONE, True),),
            output_ports=(PortSpec("planning_shadow_action", "PlanningBoardAction", PortDirection.OUTPUT, PortCardinality.ONE, True),),
            constraints=shared_constraints, required_capabilities=("civic_commons.shadow_project",), verifier_ids=(),
            authority_requirement=AuthorityRequirement.HUMAN, resource_demand=ResourceDemand(),
            reversibility=ReversibilityClass.REVERSIBLE, idempotency_key=f"civic-p8:{workstream_digest}",
            retry_policy=RetryPolicy(max_attempts=1, backoff_seconds=0.0), evidence_refs=refs, proposal_only=True,
        ))
        mappings.append(CivicActionMapping(workstream_id, action_id, workstream_digest, dependencies, refs))
        evidence.append(ActionContinuityEvidence(
            action_id=action_id,
            grounded_evidence_refs=(workstream_ref, session_ref, inventory_ref),
            constrained_evidence_refs=(project_ref, bindings_ref),
            authority_decision_ids=(), verifier_receipts=(),
        ))
    goal = GoalSpec(
        goal_id=f"civic_goal_{stable_digest({'project': project_id, 'session': session_id}, digest_size=12)}",
        objective=objective,
        desired_state=tuple(PredicateSpec(fact=f"civic.workstream.{item['workstream_id']}.shadow_projected", expected=True, operator=PredicateOperator.EQ) for item in workstreams),
        constraints=shared_constraints,
        evidence_refs=state_refs,
    )
    board = PlanningBoard(
        board_id=f"civic_board_{stable_digest({'project': project_digest, 'session': session_digest}, digest_size=12)}",
        arena_id=f"civic_commons:{project_id}",
        purpose_digest=stable_digest({"project_id": project_id, "session_id": session_id, "objective": objective, "bindings": bindings.digest}),
        goal=goal, actions=tuple(actions), current_state_refs=state_refs,
    )
    return board, tuple(mappings), tuple(evidence)


def inspect_civic_commons_planning_compatibility(project: Any, session: Any, *, repo_root: str | Path | None = None, inventory: CivicSurfaceInventory | None = None) -> CivicPlanningInspection:
    project_record: dict[str, Any] | None = None
    session_record: dict[str, Any] | None = None
    project_id = session_id = project_digest = session_digest = inventory_digest = None
    workstream_count = 0
    try:
        project_record = _snapshot(project, "project")
        session_record = _snapshot(session, "session")
        project_digest = stable_digest(project_record)
        session_digest = stable_digest(session_record)
        project_id, session_id, objective, constraints = _validate_identity(project_record, session_record)
        workstreams = _validate_workstreams(session_record, objective, constraints)
        workstream_count = len(workstreams)
        bindings = _bind_records(session_record)
        if inventory is None:
            try:
                inventory = build_civic_surface_inventory(repo_root)
            except CivicInventoryError as exc:
                _fail("INVENTORY_UNAVAILABLE", str(exc), unavailable=True)
        if not isinstance(inventory, CivicSurfaceInventory):
            _fail("INVALID_INVENTORY", "inventory contract is invalid")
        inventory_digest = inventory.digest
        board, mappings, action_evidence = _build_board(project_id, session_id, objective, constraints, workstreams, project_digest, session_digest, bindings, inventory)
        if _snapshot(project, "project") != project_record:
            _fail("PROJECT_CHANGED_DURING_INSPECTION", "project changed during inspection")
        if _snapshot(session, "session") != session_record:
            _fail("SESSION_CHANGED_DURING_INSPECTION", "session changed during inspection")
        report = CivicCompatibilityReport(
            status=CivicCompatibilityStatus.BLOCKED_BY_GOVERNANCE,
            project_id=project_id, session_id=session_id,
            project_digest=project_digest, session_digest=session_digest,
            inventory_digest=inventory_digest, bindings_digest=bindings.digest, board_digest=board.digest,
            workstream_count=workstream_count, mapped_action_count=len(mappings), mapping_verified=True,
            source_mutated=False, authority_changed=False, governance_blockers=bindings.blockers, findings=(),
        )
        return CivicPlanningInspection(report, inventory, bindings, board, action_evidence, mappings)
    except CivicProjectionError as exc:
        return _failure(exc, project_id=project_id, session_id=session_id, project_digest=project_digest, session_digest=session_digest, inventory_digest=inventory_digest, workstream_count=workstream_count)


__all__ = ["CivicProjectionError", "inspect_civic_commons_planning_compatibility"]
