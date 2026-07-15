"""Deterministic P7 fixture benchmark for the Coding Arena Planning Board adapter."""
from __future__ import annotations
import argparse
from collections.abc import Sequence
import hashlib
import json
from pathlib import Path
from typing import Any
from aura_coding_arena_planning import inspect_coding_arena_planning_compatibility
from aura_coding_arena_planning_types import CODING_ARENA_BENCHMARK_VERSION, CodingArenaBenchmarkCase, CodingArenaBenchmarkCaseResult, CodingArenaBenchmarkReport, CodingArenaCompatibilityStatus
from aura_event_contracts import canonical_json, stable_digest

def _legacy_hash(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(',', ':'), default=str)
    return hashlib.blake2b(body.encode('utf-8'), digest_size=16).hexdigest()

def _phase_hash(case_id: str, task_ids: list[str]) -> str:
    return _legacy_hash({'case_id': case_id, 'task_ids': task_ids})

def _task(*, task_id: str, objective: str, target_file: str | None, target_symbol: str | None=None, related_files: tuple[str, ...]=(), expected_output: str='UNIFIED_DIFF', role: str='cheap_builder', constraints: tuple[str, ...]=('NO_FAKE_FILES', 'PRESERVE_SIGNATURES')) -> dict[str, Any]:
    return {'capsule_version': 'AURA_ACT_CAPSULE_V1', 'task_id': task_id, 'role': role, 'objective': objective, 'target_file': target_file, 'target_symbol': target_symbol, 'related_files': list(related_files), 'allowed_scope': 'single bounded edit', 'context_ref': f"ACT-{stable_digest({'task_id': task_id}, digest_size=8)}", 'topological_grounding': {}, 'acceptance': 'Return a bounded candidate or a refusal reason.', 'escalate_if': ['missing target file', 'requires public API change', 'touches files outside allowed scope'], 'constraints': list(constraints), 'expected_output': expected_output, 'size': 'S'}

def _grounding(task: dict[str, Any], *, file_exists: bool=True, codemap_file_hit: bool=True, symbol_exists: bool=True, test_files: tuple[str, ...]=(), neighbor_files: tuple[str, ...]=()) -> dict[str, Any]:
    return {'task_id': task['task_id'], 'target_file': task['target_file'], 'target_symbol': task['target_symbol'], 'file_exists': file_exists, 'codemap_file_hit': codemap_file_hit, 'symbol_exists': symbol_exists, 'codemap_symbol_hits': [{'name': task['target_symbol'], 'file': task['target_file'], 'kind': 'function', 'line': 1, 'end_line': 5}] if task['target_symbol'] and symbol_exists else [], 'test_files': list(test_files), 'neighbor_files': list(neighbor_files), 'dream_scores': []}

def _route(task: dict[str, Any], route: str, reason: str) -> dict[str, Any]:
    action = 'modify' if str(task['expected_output']).upper() in {'PATCH', 'UNIFIED_DIFF', 'JSON_EDIT_PLAN', 'PYTHON'} else 'inspect'
    return {'route': route, 'reason': reason, 'symbol_output': route, 'task_id': task['task_id'], 'target_file': task['target_file'], 'target_symbol': task['target_symbol'], 'frame': {'intent': 'code_refactor', 'artifact': 'python_module' if task['target_file'] else 'documentation', 'action': action, 'scope': 'symbol' if task['target_symbol'] else 'file', 'risk': 'medium', 'grounding': ['file_exists', 'codemap_grounded'], 'tests': 'existing', 'quality': 'balanced', 'cost': 'local_first', 'target_file': task['target_file'], 'target_symbol': task['target_symbol']}}

def _lease(task: dict[str, Any], *, neighbor_files: tuple[str, ...]=()) -> dict[str, Any]:
    declared = []
    if task['target_file']:
        declared.append(task['target_file'])
    for path in task['related_files']:
        if path not in declared:
            declared.append(path)
    regions = [{'region_type': 'file', 'id': path, 'mode': 'write'} for path in declared]
    regions.extend(({'region_type': 'file', 'id': path, 'mode': 'read'} for path in neighbor_files if path not in declared))
    if task['target_symbol']:
        regions.append({'region_type': 'symbol', 'id': task['target_symbol'], 'file': task['target_file'], 'mode': 'write'})
    payload = {'lease_version': 'AURA_ARENA_LEASE_V1', 'domain': 'code', 'capsule_id': task['task_id'], 'holder': task['role'], 'regions': regions, 'allowed_actions': ['read leased files', 'emit one bounded candidate'], 'forbidden_actions': ['mutate production files directly'], 'mode': 'exclusive_write', 'conflict_policy': 'judge_then_reground', 'status': 'active', 'metadata': {'task_id': task['task_id']}}
    lease_id = f'LEASE-{stable_digest(payload, digest_size=6)}'
    return {**payload, 'lease_id': lease_id, 'phase_hash': stable_digest({**payload, 'lease_id': lease_id})}

def _boundary(task: dict[str, Any], *, neighbor_files: tuple[str, ...]=()) -> dict[str, Any]:
    declared = []
    if task['target_file']:
        declared.append(task['target_file'])
    for path in task['related_files']:
        if path not in declared:
            declared.append(path)
    payload = {'contract_version': 'AURA_BOUNDARY_CONTRACT_V1', 'domain': 'code', 'capsule_id': task['task_id'], 'boundary_type': 'code_boundary', 'external_system': 'CODEMAP/topology/test-neighbor surface', 'source_region': {'file': task['target_file'], 'symbol': task['target_symbol']}, 'owned_scope': declared, 'assumptions': ['Only declared files and symbols may be changed.'], 'required_inputs': ['CODEMAP file card', 'nearby tests'], 'promised_outputs': ['bounded candidate or refusal'], 'constraints': list(task['constraints']), 'escalation_triggers': list(task['escalate_if']), 'invariant': 'preserve exact source and test boundaries', 'status': 'placeholder', 'metadata': {'task_id': task['task_id'], 'target_file': task['target_file'], 'target_symbol': task['target_symbol'], 'neighbor_files': list(neighbor_files), 'upstream': 'aura_fusion.build_task_capsule', 'downstream': 'aura_phase_capsule.capture_phase_capsule'}}
    contract_id = f'BC-{stable_digest(payload, digest_size=6)}'
    return {**payload, 'contract_id': contract_id, 'phase_hash': stable_digest({**payload, 'contract_id': contract_id}), 'task_id': task['task_id'], 'target_file': task['target_file'], 'target_symbol': task['target_symbol'], 'upstream': 'aura_fusion.build_task_capsule', 'downstream': 'aura_phase_capsule.capture_phase_capsule', 'agent_scope': task['allowed_scope'], 'neighbor_files': list(neighbor_files)}

def _case(*, case_id: str, tasks: tuple[dict[str, Any], ...], grounding: tuple[dict[str, Any], ...], routes: tuple[tuple[str, str], ...], findings: tuple[dict[str, Any], ...]=(), shadow_ok: bool=True, shadow_gate: str='ALLOW_BUILDER', ready_for_incubator: bool=True, expected_status: CodingArenaCompatibilityStatus=CodingArenaCompatibilityStatus.VERIFIED_SHADOW) -> CodingArenaBenchmarkCase:
    if not tasks:
        raise ValueError('fixture tasks must not be empty')
    if len(tasks) != len(grounding) or len(tasks) != len(routes):
        raise ValueError('fixture tasks, grounding, and routes must have equal lengths')
    task_ids = [str(task['task_id']) for task in tasks]
    plan_phase_hash = _phase_hash(case_id, task_ids)
    plan = {'capsule_version': 'AURA_FRACTAL_PLAN_CAPSULE_V1', 'objective': f'P7 fixture objective: {case_id}', 'architecture_decision': 'Preserve the legacy Coding Arena and add a shadow projection.', 'constraints': ['NO_NEW_DEPS', 'PRESERVE_SIGNATURES'], 'acceptance_criteria': ['Exact task mapping is preserved.'], 'rollback_conditions': ['Discard the shadow projection.'], 'risk_map': [], 'act_capsules': list(tasks), 'escalation_rules': [], 'fusion_capsule': {'phase_hash': f'fusion-{plan_phase_hash}'}, 'context_ref': f'PLAN-{plan_phase_hash}', 'st3gg_capsule': None, 'continuity_capsule': None, 'phase_hash': plan_phase_hash}
    shadow_payload = {'plan_phase_hash': plan_phase_hash, 'findings': list(findings)}
    shadow_report = {'report_version': 'AURA_SHADOW_REPORT_V1', 'ok': shadow_ok, 'phase_hash': _legacy_hash(shadow_payload), 'findings': list(findings), 'gate': shadow_gate}
    route_records = tuple((_route(task, route_name, reason) for task, (route_name, reason) in zip(tasks, routes)))
    leases = tuple((_lease(task, neighbor_files=tuple(ground['neighbor_files'])) for task, ground in zip(tasks, grounding)))
    boundaries = tuple((_boundary(task, neighbor_files=tuple(ground['neighbor_files'])) for task, ground in zip(tasks, grounding)))
    affected_files = sorted({str(item['target_file']) for item in grounding if item['target_file'] and item['file_exists']})
    liquid_actions = [{'capsule_version': 'AURA_ACTION_CAPSULE_V1', 'capsule_id': task['task_id'], 'domain': 'code'} for task in tasks]
    arena = {'arena_version': 'AURA_REFACTOR_ARENA_V1', 'plan_phase_hash': plan_phase_hash, 'affected_files': affected_files, 'boundary_contracts': list(boundaries), 'agent_capsules': list(tasks), 'shared_patch_queue': [], 'conflict_resolver': {'mode': 'liquid_region_lease', 'cross_boundary_edit': 'escalate_to_shadow', 'same_file_conflict': 'judge_then_reground', 'lease_violation': 'block_transaction'}, 'shadow_report': shadow_report, 'verification_ledger': [], 'ready_for_incubator': ready_for_incubator, 'rollback_hint': 'Discard by plan phase hash.', 'agent_leases': list(leases), 'liquid_arena': {'arena_version': 'AURA_LIQUID_PLANNING_ARENA_V1', 'arena_id': f"LPA-{stable_digest({'case_id': case_id}, digest_size=6)}", 'domain': 'code', 'intent': plan['objective'], 'plan_ref': plan_phase_hash, 'domain_objects': ['files', 'symbols', 'diffs', 'tests'], 'action_capsules': liquid_actions, 'boundary_contracts': list(boundaries), 'agent_leases': list(leases), 'shared_action_queue': [], 'verification_ledger': [], 'adapter': {'domain': 'code'}, 'phase_hash': stable_digest({'case_id': case_id, 'kind': 'liquid'})}, 'routing_decisions': list(route_records)}
    return CodingArenaBenchmarkCase(case_id=case_id, plan=plan, grounding=grounding, shadow_report=shadow_report, arena=arena, expected_status=expected_status)

def default_benchmark_cases() -> tuple[CodingArenaBenchmarkCase, ...]:
    single = _task(task_id='SINGLE-1', objective='Patch the declared parser function.', target_file='aura_parser.py', target_symbol='parse')
    single_ground = _grounding(single, test_files=('tests/test_aura_parser.py',), neighbor_files=('aura_tokens.py',))
    multi_a = _task(task_id='MULTI-1', objective='Patch the board adapter.', target_file='aura_adapter.py', related_files=('aura_adapter_types.py',))
    multi_b = _task(task_id='MULTI-2', objective='Add focused adapter tests.', target_file='tests/test_aura_adapter.py')
    multi_a_ground = _grounding(multi_a, test_files=('tests/test_aura_adapter.py',), neighbor_files=('aura_planning_board.py',))
    multi_b_ground = _grounding(multi_b, test_files=('tests/test_aura_adapter.py',), neighbor_files=('aura_adapter.py',))
    inspect_task = _task(task_id='INSPECT-1', objective='Inspect the exact source boundary without a patch.', target_file='aura_architect_loop.py', expected_output='TEXT', role='researcher')
    inspect_ground = _grounding(inspect_task, test_files=('test_aura_architect_loop.py',), neighbor_files=('aura_liquid_planning_arena.py',))
    warning_task = _task(task_id='WARN-1', objective='Prepare a bounded patch while reporting the missing nearby test.', target_file='aura_warning_fixture.py')
    warning_ground = _grounding(warning_task, test_files=())
    warning_finding = {'shadow_type': 'missing_test', 'severity': 'warn', 'message': 'No nearby test file was found for the target file.', 'task_id': warning_task['task_id'], 'target_file': warning_task['target_file'], 'target_symbol': warning_task['target_symbol']}
    blocked_task = _task(task_id='BLOCKED-1', objective='Refuse a patch against a missing file.', target_file='missing_fixture.py')
    blocked_ground = _grounding(blocked_task, file_exists=False, codemap_file_hit=False, symbol_exists=True, test_files=())
    blocked_finding = {'shadow_type': 'fake_file', 'severity': 'blocker', 'message': 'Target file is absent from the working tree.', 'task_id': blocked_task['task_id'], 'target_file': blocked_task['target_file'], 'target_symbol': blocked_task['target_symbol']}
    return (_case(case_id='grounded_single_file_patch', tasks=(single,), grounding=(single_ground,), routes=(('BUILDER_PATCH', 'grounded_patch'),)), _case(case_id='grounded_multi_act_patch', tasks=(multi_a, multi_b), grounding=(multi_a_ground, multi_b_ground), routes=(('BUILDER_PATCH', 'grounded_patch'), ('BUILDER_PATCH', 'grounded_patch'))), _case(case_id='inspect_only_route', tasks=(inspect_task,), grounding=(inspect_ground,), routes=(('RESEARCH_DECOMPOSE', 'inspect_only'),), ready_for_incubator=False), _case(case_id='warning_missing_test', tasks=(warning_task,), grounding=(warning_ground,), routes=(('BUILDER_PATCH', 'grounded_patch'),), findings=(warning_finding,), shadow_gate='ALLOW_BUILDER_WITH_WARNINGS'), _case(case_id='blocked_missing_file', tasks=(blocked_task,), grounding=(blocked_ground,), routes=(('BLOCKED_WITH_REASON', 'missing_grounding'),), findings=(blocked_finding,), shadow_ok=False, shadow_gate='BLOCK_BUILDER', ready_for_incubator=False, expected_status=CodingArenaCompatibilityStatus.BLOCKED_LEGACY))

def _token_proxy(byte_count: int) -> int:
    return (int(byte_count) + 3) // 4

def run_coding_arena_planning_benchmark(*, cases: Sequence[CodingArenaBenchmarkCase] | None=None, repeats: int=3) -> CodingArenaBenchmarkReport:
    if type(repeats) is not int or repeats < 2 or repeats > 20:
        raise ValueError('repeats must be an integer between 2 and 20')
    selected = tuple(default_benchmark_cases() if cases is None else cases)
    if not selected:
        raise ValueError('benchmark cases must not be empty')
    if not all((isinstance(case, CodingArenaBenchmarkCase) for case in selected)):
        raise ValueError('cases must contain CodingArenaBenchmarkCase records')
    case_ids = [case.case_id for case in selected]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError('benchmark case_id values must be unique')
    results = []
    all_board_digests = []
    all_action_ids = []
    for case in selected:
        baseline_payload = {'plan': case.plan, 'grounding': list(case.grounding), 'shadow_report': case.shadow_report, 'arena': case.arena}
        before = canonical_json(baseline_payload)
        inspections = tuple((inspect_coding_arena_planning_compatibility(case.plan, case.grounding, case.shadow_report, case.arena) for _ in range(repeats)))
        after = canonical_json(baseline_payload)
        first = inspections[0]
        inspection_digests = tuple((item.digest for item in inspections))
        deterministic = len(set(inspection_digests)) == 1
        board_digest = first.board.digest if first.board is not None else None
        action_ids = tuple((action.action_id for action in first.board.actions)) if first.board is not None else ()
        verifier_count = sum((1 for action in first.board.actions if action.verifier_ids)) if first.board is not None else 0
        task_count = first.report.task_count
        verifier_rate = verifier_count / task_count if task_count else 0.0
        baseline_bytes = len(before.encode('utf-8'))
        candidate_json = canonical_json(first.to_dict())
        candidate_bytes = len(candidate_json.encode('utf-8'))
        overhead_ratio = candidate_bytes / baseline_bytes if baseline_bytes else 0.0
        mutation = before != after or first.report.legacy_mutated
        passed = first.report.status is case.expected_status and deterministic and (first.report.mapped_action_count == task_count) and first.report.task_order_preserved and first.report.exact_legacy_preserved and (not mutation) and (not first.report.authority_changed) and first.report.proposal_only and (verifier_rate == 1.0) and (first.board is not None) and all((action.proposal_only for action in first.board.actions)) and all((action.authority_requirement.value == 'HUMAN' for action in first.board.actions))
        result = CodingArenaBenchmarkCaseResult(case_id=case.case_id, expected_status=case.expected_status, observed_status=first.report.status, passed=passed, task_count=task_count, mapped_action_count=first.report.mapped_action_count, deterministic=deterministic, task_order_preserved=first.report.task_order_preserved, exact_legacy_preserved=first.report.exact_legacy_preserved, legacy_mutated=mutation, authority_changed=first.report.authority_changed, proposal_only=first.report.proposal_only, verifier_declaration_rate=verifier_rate, baseline_bytes=baseline_bytes, candidate_bytes=candidate_bytes, baseline_token_proxy=_token_proxy(baseline_bytes), candidate_token_proxy=_token_proxy(candidate_bytes), overhead_ratio=overhead_ratio, board_digest=board_digest, inspection_digest=first.digest, finding_codes=tuple((finding.code for finding in first.report.findings)))
        results.append(result)
        if board_digest is not None:
            all_board_digests.append(board_digest)
        all_action_ids.extend(action_ids)
    total_cases = len(results)
    total_tasks = sum((item.task_count for item in results))
    mapped_actions = sum((item.mapped_action_count for item in results))
    baseline_bytes = sum((item.baseline_bytes for item in results))
    candidate_bytes = sum((item.candidate_bytes for item in results))
    baseline_tokens = sum((item.baseline_token_proxy for item in results))
    candidate_tokens = sum((item.candidate_token_proxy for item in results))
    board_collisions = len(all_board_digests) - len(set(all_board_digests))
    action_collisions = len(all_action_ids) - len(set(all_action_ids))
    identifier_collisions = board_collisions + action_collisions
    action_coverage = mapped_actions / total_tasks if total_tasks else 0.0
    deterministic_rate = sum((1 for item in results if item.deterministic)) / total_cases
    order_rate = sum((1 for item in results if item.task_order_preserved)) / total_cases
    verifier_rate = sum((item.verifier_declaration_rate * item.task_count for item in results)) / total_tasks if total_tasks else 0.0
    mutation_drift_count = sum((1 for item in results if item.legacy_mutated))
    authority_drift_count = sum((1 for item in results if item.authority_changed))
    passed_cases = sum((1 for item in results if item.passed))
    gate_passed = passed_cases == total_cases and action_coverage == 1.0 and (deterministic_rate == 1.0) and (order_rate == 1.0) and (verifier_rate == 1.0) and (mutation_drift_count == 0) and (authority_drift_count == 0) and (identifier_collisions == 0)
    return CodingArenaBenchmarkReport(version=CODING_ARENA_BENCHMARK_VERSION, measurement_class='EMPIRICAL_FIXTURE_WITH_HEURISTIC_TOKEN_PROXY', repeats=repeats, total_cases=total_cases, passed_cases=passed_cases, total_tasks=total_tasks, mapped_actions=mapped_actions, action_coverage=action_coverage, deterministic_case_rate=deterministic_rate, order_preservation_rate=order_rate, verifier_declaration_rate=verifier_rate, mutation_drift_count=mutation_drift_count, authority_drift_count=authority_drift_count, identifier_collision_count=identifier_collisions, baseline_bytes=baseline_bytes, candidate_bytes=candidate_bytes, baseline_token_proxy=baseline_tokens, candidate_token_proxy=candidate_tokens, overhead_ratio=candidate_bytes / baseline_bytes if baseline_bytes else 0.0, gate_passed=gate_passed, cases=tuple(results), limitations=('Fixture measurements prove adapter parity only for the committed cases.', 'Byte counts are exact canonical UTF-8 sizes; token counts are a deterministic four-bytes-per-token proxy.', 'No latency, provider quality, model quality, execution success, or general efficiency improvement is claimed.', 'The benchmark never stages patches, runs tests, grants authority, hotswaps, or merges.'))

def main(argv: Sequence[str] | None=None) -> int:
    parser = argparse.ArgumentParser(description='Run the deterministic P7 Coding Arena Planning Board benchmark.')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--repeats', type=int, default=3)
    args = parser.parse_args(argv)
    report = run_coding_arena_planning_benchmark(repeats=args.repeats)
    text = report.to_json() + '\n'
    if args.output is not None:
        args.output.write_text(text, encoding='utf-8')
    else:
        print(text, end='')
    return 0 if report.gate_passed else 1
if __name__ == '__main__':
    raise SystemExit(main())
