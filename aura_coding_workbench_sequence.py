"""
Aura Coding Workbench Sequence — 18-state coding-native workbench state machine.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


class WorkbenchState(str, Enum):
    WORKSPACE_OPENED = "WORKSPACE_OPENED"
    TASK_SCOPED = "TASK_SCOPED"
    CONTEXT_FILTERED = "CONTEXT_FILTERED"
    CODE_LOCALIZED = "CODE_LOCALIZED"
    CODE_REGIONS_RANKED = "CODE_REGIONS_RANKED"
    CONTEXT_SLICED = "CONTEXT_SLICED"
    CHANGE_GRAPH_BUILT = "CHANGE_GRAPH_BUILT"
    REFACTOR_CANDIDATES_FOUND = "REFACTOR_CANDIDATES_FOUND"
    WORK_SPLIT = "WORK_SPLIT"
    ACT_CAPSULES_CREATED = "ACT_CAPSULES_CREATED"
    AGENT_HANDOFF_READY = "AGENT_HANDOFF_READY"
    PATCH_STAGED = "PATCH_STAGED"
    TESTS_RUNNING = "TESTS_RUNNING"
    PATCH_VERIFIED = "PATCH_VERIFIED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    PR_READY = "PR_READY"
    NEED_TOPOLOGY_REPAIR = "NEED_TOPOLOGY_REPAIR"
    BLOCKED_SECURITY_RISK = "BLOCKED_SECURITY_RISK"


@dataclass
class WorkbenchGate:
    state: WorkbenchState
    allowed_actions: list[str] = field(default_factory=list)
    blocked_actions: list[str] = field(default_factory=list)
    required_evidence: list[str] = field(default_factory=list)
    coding_artifacts_visible: list[str] = field(default_factory=list)
    topology_health: str = "required"
    command_risk: str = "unchecked"
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    human_approval_required: bool = False
    next_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value, "allowed_actions": list(self.allowed_actions),
            "blocked_actions": list(self.blocked_actions),
            "required_evidence": list(self.required_evidence),
            "coding_artifacts_visible": list(self.coding_artifacts_visible),
            "topology_health": self.topology_health, "command_risk": self.command_risk,
            "patch_authority": self.patch_authority,
            "vsa_patch_authority": self.vsa_patch_authority,
            "human_approval_required": self.human_approval_required,
            "next_actions": list(self.next_actions),
        }


GATE_DEFINITIONS: dict[WorkbenchState, WorkbenchGate] = {
    WorkbenchState.WORKSPACE_OPENED: WorkbenchGate(
        WorkbenchState.WORKSPACE_OPENED,
        allowed_actions=["scope_task", "check_topology"],
        blocked_actions=["build_change_graph", "detect_refactor_candidates"],
        required_evidence=["topology_health"],
        coding_artifacts_visible=["codemap_summary", "file_list"],
        next_actions=["TASK_SCOPED"]),
    WorkbenchState.TASK_SCOPED: WorkbenchGate(
        WorkbenchState.TASK_SCOPED,
        allowed_actions=["filter_context", "localize_code"],
        blocked_actions=["stage_patch"],
        required_evidence=["objective"],
        coding_artifacts_visible=["objective", "scope"],
        next_actions=["CONTEXT_FILTERED"]),
    WorkbenchState.CONTEXT_FILTERED: WorkbenchGate(
        WorkbenchState.CONTEXT_FILTERED,
        allowed_actions=["localize_code"],
        blocked_actions=["stage_patch"],
        required_evidence=["filtered_context"],
        coding_artifacts_visible=["filtered_files", "filtered_symbols"],
        next_actions=["CODE_LOCALIZED"]),
    WorkbenchState.CODE_LOCALIZED: WorkbenchGate(
        WorkbenchState.CODE_LOCALIZED,
        allowed_actions=["rank_code_regions", "slice_context"],
        blocked_actions=["stage_patch"],
        required_evidence=["localized_files", "localized_symbols"],
        coding_artifacts_visible=["localized_files", "localized_symbols", "line_ranges"],
        next_actions=["CODE_REGIONS_RANKED"]),
    WorkbenchState.CODE_REGIONS_RANKED: WorkbenchGate(
        WorkbenchState.CODE_REGIONS_RANKED,
        allowed_actions=["slice_context", "build_change_graph"],
        blocked_actions=["stage_patch"],
        required_evidence=["ranked_regions"],
        coding_artifacts_visible=["ranked_regions", "confidence", "token_budget"],
        next_actions=["CONTEXT_SLICED"]),
    WorkbenchState.CONTEXT_SLICED: WorkbenchGate(
        WorkbenchState.CONTEXT_SLICED,
        allowed_actions=["build_change_graph"],
        blocked_actions=["stage_patch"],
        required_evidence=["context_slices"],
        coding_artifacts_visible=["sliced_files", "sliced_symbols", "exact_line_ranges"],
        next_actions=["CHANGE_GRAPH_BUILT"]),
    WorkbenchState.CHANGE_GRAPH_BUILT: WorkbenchGate(
        WorkbenchState.CHANGE_GRAPH_BUILT,
        allowed_actions=["detect_refactor_candidates"],
        blocked_actions=["stage_patch"],
        required_evidence=["change_graph"],
        coding_artifacts_visible=["change_graph", "files", "symbols", "tests", "risks"],
        next_actions=["REFACTOR_CANDIDATES_FOUND"]),
    WorkbenchState.REFACTOR_CANDIDATES_FOUND: WorkbenchGate(
        WorkbenchState.REFACTOR_CANDIDATES_FOUND,
        allowed_actions=["split_work", "create_act_capsules"],
        blocked_actions=["stage_patch"],
        required_evidence=["refactor_candidates"],
        coding_artifacts_visible=["candidates", "risk_levels", "suggested_agents"],
        next_actions=["WORK_SPLIT"]),
    WorkbenchState.WORK_SPLIT: WorkbenchGate(
        WorkbenchState.WORK_SPLIT,
        allowed_actions=["create_act_capsules"],
        blocked_actions=["stage_patch"],
        required_evidence=["work_split"],
        coding_artifacts_visible=["child_tasks", "sequencing"],
        next_actions=["ACT_CAPSULES_CREATED"]),
    WorkbenchState.ACT_CAPSULES_CREATED: WorkbenchGate(
        WorkbenchState.ACT_CAPSULES_CREATED,
        allowed_actions=["prepare_agent_handoff"],
        blocked_actions=["stage_patch"],
        required_evidence=["act_capsules"],
        coding_artifacts_visible=["act_capsules", "target_files", "target_symbols"],
        next_actions=["AGENT_HANDOFF_READY"]),
    WorkbenchState.AGENT_HANDOFF_READY: WorkbenchGate(
        WorkbenchState.AGENT_HANDOFF_READY,
        allowed_actions=["send_to_agent"],
        blocked_actions=["stage_patch"],
        required_evidence=["agent_handoff_packet"],
        human_approval_required=True,
        coding_artifacts_visible=["handoff_packet", "agent", "compressed_context"],
        next_actions=["PATCH_STAGED"]),
    WorkbenchState.PATCH_STAGED: WorkbenchGate(
        WorkbenchState.PATCH_STAGED,
        allowed_actions=["run_targeted_tests"],
        blocked_actions=["commit", "push"],
        required_evidence=["staged_patch"],
        coding_artifacts_visible=["staged_diff", "affected_files"],
        next_actions=["TESTS_RUNNING"]),
    WorkbenchState.TESTS_RUNNING: WorkbenchGate(
        WorkbenchState.TESTS_RUNNING,
        allowed_actions=["wait_for_tests"],
        blocked_actions=["commit", "push"],
        required_evidence=["test_results"],
        coding_artifacts_visible=["test_results", "pass_fail"],
        next_actions=["PATCH_VERIFIED"]),
    WorkbenchState.PATCH_VERIFIED: WorkbenchGate(
        WorkbenchState.PATCH_VERIFIED,
        allowed_actions=["request_human_review"],
        blocked_actions=["commit", "push"],
        required_evidence=["verification_ok"],
        coding_artifacts_visible=["verification", "test_results"],
        next_actions=["HUMAN_REVIEW_REQUIRED"]),
    WorkbenchState.HUMAN_REVIEW_REQUIRED: WorkbenchGate(
        WorkbenchState.HUMAN_REVIEW_REQUIRED,
        allowed_actions=["approve_for_pr", "reject"],
        blocked_actions=["push"],
        required_evidence=["human_approval"],
        human_approval_required=True,
        coding_artifacts_visible=["review_packet", "diff_summary"],
        next_actions=["PR_READY"]),
    WorkbenchState.PR_READY: WorkbenchGate(
        WorkbenchState.PR_READY,
        allowed_actions=["open_pr", "generate_pr_command"],
        blocked_actions=[],
        required_evidence=["human_approval", "verification_ok"],
        human_approval_required=True,
        coding_artifacts_visible=["pr_title", "pr_body", "branch"],
        next_actions=[]),
    WorkbenchState.NEED_TOPOLOGY_REPAIR: WorkbenchGate(
        WorkbenchState.NEED_TOPOLOGY_REPAIR,
        allowed_actions=["repair_topology", "text_only_search"],
        blocked_actions=["build_change_graph", "detect_refactor_candidates", "stage_patch"],
        required_evidence=["topology_repair"],
        topology_health="degraded",
        coding_artifacts_visible=["repair_commands"],
        next_actions=["WORKSPACE_OPENED"]),
    WorkbenchState.BLOCKED_SECURITY_RISK: WorkbenchGate(
        WorkbenchState.BLOCKED_SECURITY_RISK,
        allowed_actions=["review_risk", "human_override"],
        blocked_actions=["execute_command", "stage_patch", "commit", "push"],
        required_evidence=["security_review"],
        command_risk="blocked",
        human_approval_required=True,
        coding_artifacts_visible=["risk_report"],
        next_actions=["WORKSPACE_OPENED"]),
}


def get_gate(state: WorkbenchState | str) -> WorkbenchGate:
    if isinstance(state, str):
        state = WorkbenchState(state)
    return GATE_DEFINITIONS.get(state, GATE_DEFINITIONS[WorkbenchState.WORKSPACE_OPENED])


def can_transition(current: WorkbenchState, target: WorkbenchState) -> bool:
    gate = get_gate(current)
    return target.value in gate.next_actions or target == current


def workbench_state_machine() -> dict[str, Any]:
    return {
        "ok": True, "state_count": len(GATE_DEFINITIONS),
        "states": [s.value for s in WorkbenchState],
        "gates": [g.to_dict() for g in GATE_DEFINITIONS.values()],
        "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
