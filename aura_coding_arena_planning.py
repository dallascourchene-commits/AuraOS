"""P7 proposal-only Planning Board shadow adapter for the Coding Arena.

The legacy Architect/Refactor Arena remains the live owner. This module only
projects already-produced legacy records into canonical Planning Board evidence.
It never executes, routes, leases, stages, verifies, hotswaps, merges, or mutates.
"""
from __future__ import annotations
from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
import hashlib
import json
from pathlib import PurePosixPath
import re
from typing import Any
from aura_coding_arena_planning_types import CODING_ARENA_COMPATIBILITY_VERSION, CodingArenaActionMapping, CodingArenaCompatibilityFinding, CodingArenaCompatibilityReport, CodingArenaCompatibilityStatus, CodingArenaPlanningInspection
from aura_event_contracts import MeasurementClass, canonical_json, stable_digest
from aura_planning_board import ActionContinuityEvidence, ActionSpec, AuthorityRequirement, ConstraintKind, ConstraintSpec, EffectSpec, GoalSpec, PlanningBoard, PortCardinality, PortDirection, PortSpec, PredicateOperator, PredicateSpec, ResourceDemand, RetryPolicy, ReversibilityClass, verify_board_continuity
_PATCH_OUTPUT_MODES = frozenset({'PATCH', 'UNIFIED_DIFF', 'JSON_EDIT_PLAN', 'PYTHON'})
_DRIVE_PREFIX = re.compile('^[A-Za-z]:')

class CodingArenaProjectionError(ValueError):
    """Fail-closed projection error with a stable public finding code."""

    def __init__(self, code: str, message: str, *, task_id: str | None=None, unavailable: bool=False) -> None:
        super().__init__(message)
        self.code = str(code)
        self.message = str(message)
        self.task_id = str(task_id) if task_id is not None else None
        self.unavailable = bool(unavailable)

def _fail(code: str, message: str, *, task_id: str | None=None, unavailable: bool=False) -> None:
    raise CodingArenaProjectionError(code, message, task_id=task_id, unavailable=unavailable)

def _required(value: Any, field_name: str, *, task_id: str | None=None) -> str:
    if not isinstance(value, str):
        _fail('INVALID_STRING', f'{field_name} must be a string', task_id=task_id)
    text = value.strip()
    if not text:
        _fail('MISSING_REQUIRED_FIELD', f'{field_name} must not be empty', task_id=task_id)
    return text

def _strict_bool(value: Any, field_name: str, *, task_id: str | None=None) -> bool:
    if type(value) is not bool:
        _fail('INVALID_BOOLEAN', f'{field_name} must be a boolean', task_id=task_id)
    return value

def _snapshot_record(value: Any, field_name: str) -> dict[str, Any]:
    if value is None:
        _fail('INPUT_UNAVAILABLE', f'{field_name} is unavailable', unavailable=True)
    if isinstance(value, Mapping):
        raw = dict(value)
    elif hasattr(value, 'to_dict') and callable(value.to_dict):
        raw = value.to_dict()
    elif is_dataclass(value):
        raw = asdict(value)
    else:
        _fail('INPUT_UNAVAILABLE', f'{field_name} must be a mapping, dataclass, or to_dict record', unavailable=True)
    if not isinstance(raw, dict):
        _fail('INVALID_RECORD', f'{field_name} did not produce a mapping')
    try:
        encoded = canonical_json(raw)
    except (TypeError, ValueError) as exc:
        _fail('NONCANONICAL_RECORD', f'{field_name} is not canonical JSON: {exc}')
    decoded = json.loads(encoded)
    if not isinstance(decoded, dict):
        _fail('INVALID_RECORD', f'{field_name} must normalize to an object')
    return decoded

def _snapshot_records(values: Any, field_name: str) -> tuple[dict[str, Any], ...]:
    if values is None:
        _fail('INPUT_UNAVAILABLE', f'{field_name} is unavailable', unavailable=True)
    if type(values) not in (list, tuple):
        _fail('INVALID_SEQUENCE', f'{field_name} must be a concrete list or tuple')
    return tuple((_snapshot_record(value, f'{field_name}[{index}]') for index, value in enumerate(values)))

def _record_list(record: Mapping[str, Any], key: str, field_name: str) -> tuple[dict[str, Any], ...]:
    values = record.get(key)
    if isinstance(values, (str, bytes, bytearray, Mapping)) or not isinstance(values, list):
        _fail('INVALID_SEQUENCE', f'{field_name} must be a JSON array')
    result = []
    for index, value in enumerate(values):
        if not isinstance(value, dict):
            _fail('INVALID_RECORD', f'{field_name}[{index}] must be an object')
        result.append(value)
    return tuple(result)

def _string_list(values: Any, field_name: str, *, task_id: str | None=None, allow_empty: bool=True) -> tuple[str, ...]:
    if values is None and allow_empty:
        return ()
    if isinstance(values, (str, bytes, bytearray, Mapping)) or not isinstance(values, list):
        _fail('INVALID_SEQUENCE', f'{field_name} must be a JSON array', task_id=task_id)
    result = tuple((_required(value, f'{field_name}[{index}]', task_id=task_id) for index, value in enumerate(values)))
    if len(result) != len(set(result)):
        _fail('DUPLICATE_VALUE', f'{field_name} must not contain duplicates', task_id=task_id)
    return result

def _safe_repo_path(value: Any, field_name: str, *, task_id: str | None=None) -> str:
    path = _required(value, field_name, task_id=task_id)
    if '\\' in path:
        _fail('NONCANONICAL_PATH', f'{field_name} must use forward slashes', task_id=task_id)
    if path.startswith('/') or _DRIVE_PREFIX.match(path):
        _fail('UNSAFE_PATH', f'{field_name} must be repository-relative', task_id=task_id)
    pure = PurePosixPath(path)
    if any((part in {'', '.', '..'} for part in pure.parts)):
        _fail('UNSAFE_PATH', f'{field_name} must be normalized without traversal', task_id=task_id)
    normalized = pure.as_posix()
    if normalized != path:
        _fail('NONCANONICAL_PATH', f'{field_name} must be normalized', task_id=task_id)
    return normalized

def _optional_repo_path(value: Any, field_name: str, *, task_id: str | None=None) -> str | None:
    if value is None:
        return None
    if not str(value).strip():
        return None
    return _safe_repo_path(value, field_name, task_id=task_id)

def _optional_string(value: Any, field_name: str='value', *, task_id: str | None=None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        _fail('INVALID_STRING', f'{field_name} must be a string or null', task_id=task_id)
    text = value.strip()
    return text or None

def _ordered_index(records: Sequence[dict[str, Any]], *, key: str, source: str, expected_order: Sequence[str]) -> dict[str, dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    order = []
    for index, record in enumerate(records):
        item_id = _required(record.get(key), f'{source}[{index}].{key}')
        if item_id in seen:
            _fail('DUPLICATE_TASK_EVIDENCE', f"{source} contains duplicate {key} '{item_id}'", task_id=item_id)
        seen[item_id] = record
        order.append(item_id)
    expected = list(expected_order)
    if order != expected:
        missing = [item for item in expected if item not in seen]
        extra = [item for item in order if item not in set(expected)]
        if missing or extra:
            _fail('TASK_SET_MISMATCH', f'{source} task set differs; missing={missing}, extra={extra}')
        _fail('TASK_ORDER_MISMATCH', f'{source} task order differs from the legacy plan')
    return seen

def _digest_ref(label: str, value: Any) -> str:
    return f'{label}:blake2b-128:{stable_digest(value)}'

def _declared_files(act: Mapping[str, Any], task_id: str) -> tuple[str, ...]:
    files = []
    target_file = _optional_repo_path(act.get('target_file'), 'act.target_file', task_id=task_id)
    if target_file:
        files.append(target_file)
    related = _string_list(act.get('related_files', []), 'act.related_files', task_id=task_id)
    for index, value in enumerate(related):
        path = _safe_repo_path(value, f'act.related_files[{index}]', task_id=task_id)
        if path not in files:
            files.append(path)
    return tuple(files)

def _region_files(lease: Mapping[str, Any], task_id: str) -> tuple[tuple[str, str], ...]:
    regions = lease.get('regions')
    if isinstance(regions, (str, bytes, bytearray, Mapping)) or not isinstance(regions, list):
        _fail('INVALID_LEASE_REGIONS', 'lease.regions must be an array', task_id=task_id)
    files = []
    seen = set()
    for index, region in enumerate(regions):
        if not isinstance(region, dict):
            _fail('INVALID_LEASE_REGION', f'lease.regions[{index}] must be an object', task_id=task_id)
        if region.get('region_type') != 'file':
            continue
        path = _safe_repo_path(region.get('id'), f'lease.regions[{index}].id', task_id=task_id)
        mode = _required(region.get('mode'), f'lease.regions[{index}].mode', task_id=task_id)
        if mode not in {'read', 'write'}:
            _fail('INVALID_LEASE_MODE', f"unsupported lease mode '{mode}'", task_id=task_id)
        key = (path, mode)
        if key in seen:
            _fail('DUPLICATE_LEASE_REGION', f'duplicate lease region {key}', task_id=task_id)
        seen.add(key)
        files.append(key)
    return tuple(files)

def _constraint(*, description: str, kind: ConstraintKind, evidence_ref: str, namespace: str) -> ConstraintSpec:
    payload = {'description': description, 'kind': kind.value, 'evidence_ref': evidence_ref, 'namespace': namespace}
    return ConstraintSpec(constraint_id=f'constraint_{stable_digest(payload, digest_size=12)}', kind=kind, description=description, evidence_refs=(evidence_ref,), blocking=True)

def _projection_inputs(plan: Any, grounding: Any, shadow_report: Any, arena: Any) -> tuple[dict[str, Any], tuple[dict[str, Any], ...], dict[str, Any], dict[str, Any]]:
    return (_snapshot_record(plan, 'plan'), _snapshot_records(grounding, 'grounding'), _snapshot_record(shadow_report, 'shadow_report'), _snapshot_record(arena, 'arena'))

def project_coding_arena_planning_board(plan: Any, grounding: Any, shadow_report: Any, arena: Any) -> CodingArenaPlanningInspection:
    """Strictly project unchanged legacy records into a canonical Planning Board.

    Any mismatch raises ``CodingArenaProjectionError``. Call
    ``inspect_coding_arena_planning_compatibility`` for a status-bearing,
    non-raising compatibility result.
    """
    plan_data, grounding_data, shadow_data, arena_data = _projection_inputs(plan, grounding, shadow_report, arena)
    before = canonical_json({'plan': plan_data, 'grounding': grounding_data, 'shadow_report': shadow_data, 'arena': arena_data})
    plan_phase_hash = _required(plan_data.get('phase_hash'), 'plan.phase_hash')
    objective = _required(plan_data.get('objective'), 'plan.objective')
    architecture_decision = _required(plan_data.get('architecture_decision'), 'plan.architecture_decision')
    act_capsules = _record_list(plan_data, 'act_capsules', 'plan.act_capsules')
    if not act_capsules:
        _fail('EMPTY_PLAN', 'plan.act_capsules must not be empty')
    task_ids = []
    acts_by_task = {}
    for index, act in enumerate(act_capsules):
        task_id = _required(act.get('task_id'), f'plan.act_capsules[{index}].task_id')
        if task_id in acts_by_task:
            _fail('DUPLICATE_TASK_ID', f"duplicate plan task_id '{task_id}'", task_id=task_id)
        acts_by_task[task_id] = act
        task_ids.append(task_id)
    arena_phase_hash = _required(arena_data.get('plan_phase_hash'), 'arena.plan_phase_hash')
    if arena_phase_hash != plan_phase_hash:
        _fail('PLAN_PHASE_HASH_MISMATCH', 'arena.plan_phase_hash does not match plan.phase_hash')
    arena_version = _required(arena_data.get('arena_version'), 'arena.arena_version')
    arena_agents = _record_list(arena_data, 'agent_capsules', 'arena.agent_capsules')
    agents_by_task = _ordered_index(arena_agents, key='task_id', source='arena.agent_capsules', expected_order=task_ids)
    grounding_by_task = _ordered_index(grounding_data, key='task_id', source='grounding', expected_order=task_ids)
    route_records = _record_list(arena_data, 'routing_decisions', 'arena.routing_decisions')
    routes_by_task = _ordered_index(route_records, key='task_id', source='arena.routing_decisions', expected_order=task_ids)
    lease_records = _record_list(arena_data, 'agent_leases', 'arena.agent_leases')
    leases_by_task = _ordered_index(lease_records, key='capsule_id', source='arena.agent_leases', expected_order=task_ids)
    boundary_records = _record_list(arena_data, 'boundary_contracts', 'arena.boundary_contracts')
    boundaries_by_task = _ordered_index(boundary_records, key='task_id', source='arena.boundary_contracts', expected_order=task_ids)
    if canonical_json(arena_data.get('shadow_report')) != canonical_json(shadow_data):
        _fail('SHADOW_REPORT_MISMATCH', 'arena.shadow_report is not the exact supplied legacy ShadowReport')
    shadow_ok = _strict_bool(shadow_data.get('ok'), 'shadow_report.ok')
    shadow_gate = _required(shadow_data.get('gate'), 'shadow_report.gate')
    shadow_findings = _record_list(shadow_data, 'findings', 'shadow_report.findings')
    for index, finding in enumerate(shadow_findings):
        finding_task = _required(finding.get('task_id'), f'shadow_report.findings[{index}].task_id')
        if finding_task not in acts_by_task:
            _fail('SHADOW_UNKNOWN_TASK', f"shadow finding references unknown task '{finding_task}'", task_id=finding_task)
    shadow_hash_payload = {'plan_phase_hash': plan_phase_hash, 'findings': list(shadow_findings)}
    shadow_hash_body = json.dumps(shadow_hash_payload, sort_keys=True, separators=(',', ':'), default=str)
    expected_shadow_phase_hash = hashlib.blake2b(shadow_hash_body.encode('utf-8'), digest_size=16).hexdigest()
    if shadow_data.get('phase_hash') != expected_shadow_phase_hash:
        _fail('SHADOW_PHASE_HASH_MISMATCH', 'shadow_report.phase_hash does not verify against the legacy payload')
    expected_affected = sorted({_safe_repo_path(item.get('target_file'), 'grounding.target_file', task_id=str(item.get('task_id'))) for item in grounding_data if item.get('target_file') is not None and _strict_bool(item.get('file_exists'), 'grounding.file_exists', task_id=str(item.get('task_id')))})
    affected_files = [_safe_repo_path(value, f'arena.affected_files[{index}]') for index, value in enumerate(_string_list(arena_data.get('affected_files', []), 'arena.affected_files'))]
    if affected_files != expected_affected:
        _fail('AFFECTED_FILES_MISMATCH', 'arena.affected_files does not exactly match existing grounded targets')
    liquid = arena_data.get('liquid_arena')
    if liquid is not None:
        if not isinstance(liquid, dict):
            _fail('INVALID_LIQUID_ARENA', 'arena.liquid_arena must be an object')
        if liquid:
            if liquid.get('plan_ref') != plan_phase_hash:
                _fail('LIQUID_PLAN_REF_MISMATCH', 'liquid_arena.plan_ref differs from plan.phase_hash')
            if liquid.get('domain') != 'code':
                _fail('LIQUID_DOMAIN_MISMATCH', "liquid_arena.domain must remain 'code'")
            liquid_actions = liquid.get('action_capsules')
            if not isinstance(liquid_actions, list) or len(liquid_actions) != len(task_ids):
                _fail('LIQUID_ACTION_COUNT_MISMATCH', 'liquid_arena.action_capsules must preserve the plan action count')
            liquid_task_order = [str(item.get('capsule_id') or '') for item in liquid_actions if isinstance(item, dict)]
            if liquid_task_order != task_ids:
                _fail('LIQUID_ACTION_ORDER_MISMATCH', 'liquid_arena.action_capsules must preserve task identity and order')
    plan_digest = stable_digest(plan_data)
    arena_digest = stable_digest(arena_data)
    shadow_digest = stable_digest(shadow_data)
    plan_ref = _digest_ref('legacy-plan', plan_data)
    arena_ref = _digest_ref('legacy-arena', arena_data)
    shadow_ref = _digest_ref('legacy-shadow', shadow_data)
    goal_constraints = tuple((_constraint(description=_required(value, f'plan.constraints[{index}]'), kind=ConstraintKind.SAFETY, evidence_ref=plan_ref, namespace='plan') for index, value in enumerate(_string_list(plan_data.get('constraints', []), 'plan.constraints'))))
    actions = []
    mappings = []
    continuity_evidence = []
    goal_state = []
    for task_id in task_ids:
        act = acts_by_task[task_id]
        arena_act = agents_by_task[task_id]
        ground = grounding_by_task[task_id]
        route = routes_by_task[task_id]
        lease = leases_by_task[task_id]
        boundary = boundaries_by_task[task_id]
        if canonical_json(arena_act) != canonical_json(act):
            _fail('ACT_CAPSULE_SUBSTITUTION', 'arena.agent_capsules does not exactly preserve the plan ActCapsule', task_id=task_id)
        act_target_file = _optional_repo_path(act.get('target_file'), 'act.target_file', task_id=task_id)
        act_target_symbol = _optional_string(act.get('target_symbol'), 'act.target_symbol', task_id=task_id)
        ground_target_file = _optional_repo_path(ground.get('target_file'), 'grounding.target_file', task_id=task_id)
        ground_target_symbol = _optional_string(ground.get('target_symbol'), 'grounding.target_symbol', task_id=task_id)
        if ground_target_file != act_target_file or ground_target_symbol != act_target_symbol:
            _fail('GROUNDING_IDENTITY_MISMATCH', 'grounding target identity differs from the ActCapsule', task_id=task_id)
        route_target_file = _optional_repo_path(route.get('target_file'), 'route.target_file', task_id=task_id)
        route_target_symbol = _optional_string(route.get('target_symbol'), 'route.target_symbol', task_id=task_id)
        if route_target_file != act_target_file or route_target_symbol != act_target_symbol:
            _fail('ROUTE_IDENTITY_MISMATCH', 'routing decision target identity differs from the ActCapsule', task_id=task_id)
        frame = route.get('frame')
        if not isinstance(frame, dict):
            _fail('MISSING_ROUTING_FRAME', 'route.frame must be an object', task_id=task_id)
        if _optional_repo_path(frame.get('target_file'), 'route.frame.target_file', task_id=task_id) != act_target_file or _optional_string(frame.get('target_symbol'), 'route.frame.target_symbol', task_id=task_id) != act_target_symbol:
            _fail('ROUTING_FRAME_IDENTITY_MISMATCH', 'routing frame target identity differs from the ActCapsule', task_id=task_id)
        route_name = _required(route.get('route'), 'route.route', task_id=task_id)
        declared_files = _declared_files(act, task_id)
        boundary_scope = tuple((_safe_repo_path(value, f'boundary.owned_scope[{index}]', task_id=task_id) for index, value in enumerate(_string_list(boundary.get('owned_scope', []), 'boundary.owned_scope', task_id=task_id))))
        if boundary_scope != declared_files:
            _fail('BOUNDARY_SCOPE_MISMATCH', 'boundary.owned_scope differs from the ActCapsule declared files', task_id=task_id)
        if _optional_repo_path(boundary.get('target_file'), 'boundary.target_file', task_id=task_id) != act_target_file:
            _fail('BOUNDARY_TARGET_MISMATCH', 'boundary target_file differs from the ActCapsule', task_id=task_id)
        if _optional_string(boundary.get('target_symbol'), 'boundary.target_symbol', task_id=task_id) != act_target_symbol:
            _fail('BOUNDARY_SYMBOL_MISMATCH', 'boundary target_symbol differs from the ActCapsule', task_id=task_id)
        metadata = boundary.get('metadata')
        if not isinstance(metadata, dict):
            _fail('MISSING_BOUNDARY_METADATA', 'boundary.metadata must be an object', task_id=task_id)
        if str(metadata.get('task_id') or '') != task_id:
            _fail('BOUNDARY_TASK_MISMATCH', 'boundary.metadata.task_id differs from the ActCapsule', task_id=task_id)
        lease_files = _region_files(lease, task_id)
        write_files = tuple((path for path, mode in lease_files if mode == 'write'))
        if write_files != declared_files:
            _fail('LEASE_WRITE_SCOPE_MISMATCH', 'lease write regions differ from the ActCapsule declared files', task_id=task_id)
        neighbors = tuple((_safe_repo_path(value, f'grounding.neighbor_files[{index}]', task_id=task_id) for index, value in enumerate(_string_list(ground.get('neighbor_files', []), 'grounding.neighbor_files', task_id=task_id))))
        allowed_read = set(neighbors) - set(declared_files)
        read_files = tuple((path for path, mode in lease_files if mode == 'read'))
        if set(read_files) - allowed_read:
            _fail('LEASE_READ_SCOPE_ESCAPE', 'lease read regions include files absent from grounding.neighbor_files', task_id=task_id)
        if len(read_files) != len(set(read_files)):
            _fail('DUPLICATE_LEASE_READ_SCOPE', 'lease read regions must not contain duplicate files', task_id=task_id)
        tests = tuple((_safe_repo_path(value, f'grounding.test_files[{index}]', task_id=task_id) for index, value in enumerate(_string_list(ground.get('test_files', []), 'grounding.test_files', task_id=task_id))))
        file_exists = _strict_bool(ground.get('file_exists'), 'grounding.file_exists', task_id=task_id)
        codemap_hit = _strict_bool(ground.get('codemap_file_hit'), 'grounding.codemap_file_hit', task_id=task_id)
        symbol_exists = _strict_bool(ground.get('symbol_exists'), 'grounding.symbol_exists', task_id=task_id)
        act_ref = _digest_ref('legacy-act', act)
        ground_ref = _digest_ref('legacy-grounding', ground)
        route_ref = _digest_ref('legacy-route', route)
        lease_ref = _digest_ref('legacy-lease', lease)
        boundary_ref = _digest_ref('legacy-boundary', boundary)
        evidence_refs = (plan_ref, arena_ref, shadow_ref, act_ref, ground_ref, route_ref, lease_ref, boundary_ref)
        if len(evidence_refs) != len(set(evidence_refs)):
            _fail('EVIDENCE_REFERENCE_COLLISION', 'distinct legacy records produced colliding evidence references', task_id=task_id)
        expected_output = _required(act.get('expected_output'), 'act.expected_output', task_id=task_id).upper()
        patch_like = expected_output in _PATCH_OUTPUT_MODES
        role = _required(act.get('role'), 'act.role', task_id=task_id)
        action_payload = {'plan_phase_hash': plan_phase_hash, 'task_id': task_id, 'act_digest': stable_digest(act), 'grounding_digest': stable_digest(ground), 'route_digest': stable_digest(route), 'lease_digest': stable_digest(lease), 'boundary_digest': stable_digest(boundary)}
        action_id = f'coding_action_{stable_digest(action_payload, digest_size=12)}'
        task_fact = f'coding_arena.{action_id}.candidate_prepared'
        goal_state.append(PredicateSpec(task_fact, True))
        declared_action_constraints = tuple((_constraint(description=_required(value, f'act.constraints[{index}]', task_id=task_id), kind=ConstraintKind.SAFETY, evidence_ref=act_ref, namespace=task_id) for index, value in enumerate(_string_list(act.get('constraints', []), 'act.constraints', task_id=task_id))))
        action_constraints = (_constraint(description='Preserve the exact legacy task scope and lease boundary.', kind=ConstraintKind.SAFETY, evidence_ref=boundary_ref, namespace=f'{task_id}:boundary'), _constraint(description='Keep the Planning Board projection proposal-only and human-authority-bound.', kind=ConstraintKind.POLICY, evidence_ref=act_ref, namespace=f'{task_id}:authority'), *declared_action_constraints)
        verifier_ids = tuple([*(f'test:{path}' for path in tests), f'shadow:{shadow_gate}', f'route:{route_name}'])
        if len(verifier_ids) != len(set(verifier_ids)):
            _fail('DUPLICATE_VERIFIER_ID', 'derived verifier IDs must be unique', task_id=task_id)
        input_ports = (PortSpec('legacy_act', 'digest_reference', PortDirection.INPUT, PortCardinality.ONE, True), PortSpec('grounding_evidence', 'digest_reference', PortDirection.INPUT, PortCardinality.ONE, True), PortSpec('arena_boundary', 'digest_reference', PortDirection.INPUT, PortCardinality.ONE, True))
        output_name = 'candidate_patch' if patch_like else 'candidate_analysis'
        output_ports = (PortSpec(output_name, expected_output.lower(), PortDirection.OUTPUT, PortCardinality.ONE, True),)
        action = ActionSpec(action_id=action_id, name=_required(act.get('objective'), 'act.objective', task_id=task_id), domain='code', preconditions=(PredicateSpec(f'coding_arena.{action_id}.file_exists', file_exists), PredicateSpec(f'coding_arena.{action_id}.codemap_grounded', codemap_hit), PredicateSpec(f'coding_arena.{action_id}.symbol_exists', symbol_exists), PredicateSpec(f'coding_arena.{action_id}.route', route_name, PredicateOperator.EQ)), effects=(EffectSpec(task_fact, True),), input_ports=input_ports, output_ports=output_ports, constraints=action_constraints, required_capabilities=(f'arena-role:{role}', f'arena-output:{expected_output}', 'exact-source-read', 'proposal-only'), verifier_ids=verifier_ids, authority_requirement=AuthorityRequirement.HUMAN, resource_demand=ResourceDemand(measurement_class=MeasurementClass.UNAVAILABLE), reversibility=ReversibilityClass.REVERSIBLE, idempotency_key=f'coding-arena:{plan_phase_hash}:{task_id}', retry_policy=RetryPolicy(max_attempts=1), evidence_refs=evidence_refs, proposal_only=True)
        actions.append(action)
        constraint_refs = tuple((reference for constraint in (*goal_constraints, *action_constraints) for reference in constraint.evidence_refs))
        grounded = file_exists and codemap_hit and symbol_exists
        continuity_evidence.append(ActionContinuityEvidence(action_id=action_id, constrained_evidence_refs=tuple(dict.fromkeys(constraint_refs)), grounded_evidence_refs=evidence_refs if grounded else (), authority_decision_ids=(), verifier_receipts=()))
        mappings.append(CodingArenaActionMapping(task_id=task_id, action_id=action_id, target_file=act_target_file, target_symbol=act_target_symbol, expected_output=expected_output, route=route_name, act_digest=stable_digest(act), grounding_digest=stable_digest(ground), route_digest=stable_digest(route), lease_digest=stable_digest(lease), boundary_digest=stable_digest(boundary), evidence_refs=evidence_refs, verifier_ids=verifier_ids))
    purpose_digest = stable_digest({'objective': objective, 'architecture_decision': architecture_decision, 'legacy_plan_phase_hash': plan_phase_hash})
    goal = GoalSpec(goal_id=f"coding_goal_{stable_digest({'purpose': purpose_digest, 'state': [item.to_dict() for item in goal_state]}, digest_size=12)}", objective=objective, desired_state=tuple(goal_state), constraints=goal_constraints, evidence_refs=(plan_ref, arena_ref, shadow_ref))
    board_payload = {'arena_version': arena_version, 'legacy_arena_digest': arena_digest, 'purpose_digest': purpose_digest, 'goal': goal.to_dict(), 'actions': [item.to_dict() for item in actions], 'current_state_refs': [plan_ref, arena_ref, shadow_ref]}
    board = PlanningBoard(board_id=f'coding_board_{stable_digest(board_payload, digest_size=12)}', arena_id=f'legacy_coding_arena_{arena_digest[:24]}', purpose_digest=purpose_digest, goal=goal, actions=tuple(actions), current_state_refs=(plan_ref, arena_ref, shadow_ref))
    continuity = verify_board_continuity(board, evidence=tuple(continuity_evidence))
    after_plan, after_grounding, after_shadow, after_arena = _projection_inputs(plan, grounding, shadow_report, arena)
    after = canonical_json({'plan': after_plan, 'grounding': after_grounding, 'shadow_report': after_shadow, 'arena': after_arena})
    if before != after:
        _fail('LEGACY_MUTATION_DETECTED', 'projection observed mutation of a legacy input')
    routes = tuple((mapping.route for mapping in mappings))
    blocked = not shadow_ok or any((route.upper().startswith('BLOCK') for route in routes))
    status = CodingArenaCompatibilityStatus.BLOCKED_LEGACY if blocked else CodingArenaCompatibilityStatus.VERIFIED_SHADOW
    highest = continuity.highest_contiguous_level
    report = CodingArenaCompatibilityReport(version=CODING_ARENA_COMPATIBILITY_VERSION, status=status, plan_phase_hash=plan_phase_hash, legacy_plan_digest=plan_digest, legacy_arena_digest=arena_digest, legacy_shadow_digest=shadow_digest, board_digest=board.digest, task_count=len(task_ids), mapped_action_count=len(mappings), task_order_preserved=True, exact_legacy_preserved=True, legacy_mutated=False, authority_changed=False, proposal_only=True, legacy_ready_for_incubator=_strict_bool(arena_data.get('ready_for_incubator'), 'arena.ready_for_incubator'), legacy_shadow_gate=shadow_gate, legacy_routes=routes, highest_contiguous_level=highest.value if highest is not None else None, continuity_complete=continuity.continuity_complete, findings=())
    return CodingArenaPlanningInspection(report=report, board=board, continuity=continuity, action_evidence=tuple(continuity_evidence), mappings=tuple(mappings))

def inspect_coding_arena_planning_compatibility(plan: Any, grounding: Any, shadow_report: Any, arena: Any) -> CodingArenaPlanningInspection:
    """Return a status-bearing inspection and preserve mismatch diagnostics."""
    plan_phase_hash = None
    plan_digest = None
    arena_digest = None
    shadow_digest = None
    ready = None
    gate = None
    routes: tuple[str, ...] = ()
    task_count = 0
    try:
        if plan is not None:
            plan_snapshot = _snapshot_record(plan, 'plan')
            plan_phase_hash = _optional_string(plan_snapshot.get('phase_hash'), 'plan.phase_hash')
            plan_digest = stable_digest(plan_snapshot)
            acts = plan_snapshot.get('act_capsules')
            if isinstance(acts, list):
                task_count = len(acts)
        if arena is not None:
            arena_snapshot = _snapshot_record(arena, 'arena')
            arena_digest = stable_digest(arena_snapshot)
            if type(arena_snapshot.get('ready_for_incubator')) is bool:
                ready = arena_snapshot['ready_for_incubator']
            route_values = arena_snapshot.get('routing_decisions')
            if isinstance(route_values, list):
                routes = tuple((str(item.get('route') or '') for item in route_values if isinstance(item, dict)))
        if shadow_report is not None:
            shadow_snapshot = _snapshot_record(shadow_report, 'shadow_report')
            shadow_digest = stable_digest(shadow_snapshot)
            gate = _optional_string(shadow_snapshot.get('gate'), 'shadow_report.gate')
        return project_coding_arena_planning_board(plan, grounding, shadow_report, arena)
    except CodingArenaProjectionError as exc:
        status = CodingArenaCompatibilityStatus.UNAVAILABLE if exc.unavailable else CodingArenaCompatibilityStatus.MISMATCHED
        report = CodingArenaCompatibilityReport(version=CODING_ARENA_COMPATIBILITY_VERSION, status=status, plan_phase_hash=plan_phase_hash, legacy_plan_digest=plan_digest, legacy_arena_digest=arena_digest, legacy_shadow_digest=shadow_digest, board_digest=None, task_count=task_count, mapped_action_count=0, task_order_preserved=False, exact_legacy_preserved=False, legacy_mutated=False, authority_changed=False, proposal_only=True, legacy_ready_for_incubator=ready, legacy_shadow_gate=gate, legacy_routes=routes, highest_contiguous_level=None, continuity_complete=False, findings=(CodingArenaCompatibilityFinding(code=exc.code, message=exc.message, task_id=exc.task_id),))
        return CodingArenaPlanningInspection(report=report)
