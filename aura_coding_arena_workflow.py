"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f5-[Q-SYS:6C2848D106FBD645]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: json, __future__, dataclasses, hashlib, time, pathlib, typing, os, aura_substrate, aura_liquid_planning_arena, aura_patch_quality_gate
FUNCTIONS: to_dict, to_dict, to_dict, to_dict, to_dict, from_dict, begin_workflow, record_event, append_batch, record_plan_candidate, record_shadow_critique, record_builder_context, record_patch_submission, record_patch_preflight, record_temp_workspace_apply, record_py_compile_test_topology, record_repair_attempt, record_premium_judge_decision, record_hotswap_decision, record_outcome, get_workflow_trace, get_coding_arena_memory, convert_research_proposal_to_action_capsule, validate_research_staging_gate, enforce_research_no_direct_mutation
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any

from aura_substrate import REPO_ROOT

try:
    from aura_liquid_planning_arena import ActionCapsule
except Exception:
    ActionCapsule = None  # type: ignore[assignment]

try:
    from aura_patch_quality_gate import PatchPreflightResult
except Exception:
    PatchPreflightResult = None  # type: ignore[assignment]

try:
    from aura_qdkt import get_qdkt
except Exception:
    get_qdkt = None  # type: ignore[assignment]

try:
    from aura_dream_retrieval import record_arena_retrieval_feedback, DreamCandidate
except Exception:
    record_arena_retrieval_feedback = None  # type: ignore[assignment]
    DreamCandidate = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CODING_ARENA_WORKFLOW_VERSION = "AURA_CODING_ARENA_WORKFLOW_V1"
WORKFLOW_LEDGER_PATH = Path(REPO_ROOT) / "Aura_Memory" / "coding_arena_workflows.jsonl"

# Research gate policy: ALLOW_MUTATION is replaced by ALLOW_ARENA_STAGING
# for research-derived patches. This ensures research output is staged
# through the Arena verifier pipeline, never directly mutating production.
ALLOW_ARENA_STAGING = "ALLOW_ARENA_STAGING"
REFUSE_MUTATION = "REFUSE_MUTATION"
NEED_MORE_SOURCES = "NEED_MORE_SOURCES"

# Backward-compatible alias for any legacy callers that check ALLOW_MUTATION
ALLOW_MUTATION = ALLOW_ARENA_STAGING

# Event type constants
EVENT_PLAN_CANDIDATE = "plan_candidate"
EVENT_SHADOW_CRITIQUE = "shadow_critique"
EVENT_BUILDER_CONTEXT_PACKET = "builder_context_packet"
EVENT_PATCH_SUBMISSION = "patch_submission"
EVENT_PATCH_PREFLIGHT_RESULT = "patch_preflight_result"
EVENT_TEMP_WORKSPACE_APPLY_RESULT = "temp_workspace_apply_result"
EVENT_PY_COMPILE_TEST_TOPOLOGY_DELTA_RESULT = "py_compile_test_topology_delta_result"
EVENT_REPAIR_ATTEMPT = "repair_attempt"
EVENT_PREMIUM_JUDGE_DECISION = "premium_judge_decision"
EVENT_HOTSWAP_DECISION = "hotswap_decision"
EVENT_WORKFLOW_OUTCOME = "workflow_outcome"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class WorkflowEvent:
    """A single real Arena workflow event, tracked for memory and learning.

    Research basis: DREAM usefulness tracking; QDKT knowledge tracing;
    Context Engineering survey's workflow observability pattern.
    """

    event_id: str
    workflow_id: str
    event_type: str
    timestamp: float
    phase: str
    payload: dict[str, Any] = field(default_factory=dict)
    phase_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowEvent:
        return cls(
            event_id=str(data.get("event_id", "")),
            workflow_id=str(data.get("workflow_id", "")),
            event_type=str(data.get("event_type", "")),
            timestamp=float(data.get("timestamp", 0.0)),
            phase=str(data.get("phase", "")),
            payload=dict(data.get("payload", {})),
            phase_hash=str(data.get("phase_hash", "")),
        )


@dataclass
class PatchAttemptRecord:
    """Record of a single patch attempt through the Arena pipeline."""

    task_id: str
    status: str
    preflight: dict[str, Any] = field(default_factory=dict)
    repair: dict[str, Any] | None = None
    diff_hash: str = ""
    affected_files: list[str] = field(default_factory=list)
    affected_symbols: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BuilderContextRecord:
    """Record of a builder context packet delivered before patch generation."""

    task_id: str
    target_file: str
    target_symbol: str
    context_packet: dict[str, Any] = field(default_factory=dict)
    source_excerpt_length: int = 0
    nearby_tests_count: int = 0
    callers_count: int = 0
    neighbors_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RepairAttemptRecord:
    """Record of a patch format repair attempt."""

    task_id: str
    repair_ok: bool
    repaired_diff_hash: str = ""
    rejections_before: list[str] = field(default_factory=list)
    rejections_after: list[str] = field(default_factory=list)
    repair_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WorkflowOutcome:
    """Final outcome of a complete Arena workflow run."""

    workflow_id: str
    success: bool
    hotswap_ready: bool
    failures_count: int
    stage: str
    phase_hash: str = ""
    intent: str = ""
    target_file: str = ""
    outcome_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hash_payload(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=16).hexdigest()


def _hash_diff(diff: str) -> str:
    return hashlib.sha256(str(diff or "").encode("utf-8")).hexdigest()[:16]


def _new_event_id(prefix: str = "CAW") -> str:
    return f"{prefix}-{hashlib.sha256(f'{time.time()}:{prefix}'.encode()).hexdigest()[:16]}"


# ---------------------------------------------------------------------------
# CodingArenaWorkflowMemory
# ---------------------------------------------------------------------------

class CodingArenaWorkflowMemory:
    """Aura-native memory for real Coding Arena workflow events.

    Tracks real Arena workflow events (not synthetic random NumPy vectors),
    persists them to Aura_Memory/coding_arena_workflows.jsonl, and wires
    successful/failed outcomes into UnifiedQDKT.observe() and context
    usefulness into aura_dream_retrieval.record_arena_retrieval_feedback().

    Research basis: DREAM usefulness tracking; QDKT knowledge tracing;
    Agentless patch validation; Context Engineering survey.
    """

    def __init__(
        self,
        *,
        ledger_path: str | Path = WORKFLOW_LEDGER_PATH,
        qdkt: Any = None,
        dream_feedback_fn: Any = None,
    ) -> None:
        self.ledger_path = Path(ledger_path)
        self._qdkt = qdkt
        self._dream_feedback_fn = dream_feedback_fn
        self._active_workflows: dict[str, dict[str, Any]] = {}

    def _get_qdkt(self) -> Any:
        if self._qdkt is not None:
            return self._qdkt
        if get_qdkt is not None:
            try:
                return get_qdkt()
            except Exception:
                return None
        return None

    def _get_dream_feedback_fn(self) -> Any:
        if self._dream_feedback_fn is not None:
            return self._dream_feedback_fn
        return record_arena_retrieval_feedback

    def _append_jsonl(self, record: dict[str, Any]) -> None:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True, default=str) + "\n")

    def begin_workflow(self, intent: str, target_file: str = "") -> str:
        """Begin a new workflow and return its workflow_id."""
        workflow_id = _new_event_id("WF")
        self._active_workflows[workflow_id] = {
            "intent": intent,
            "target_file": target_file,
            "start_time": time.time(),
            "events": [],
        }
        return workflow_id

    def record_event(
        self,
        workflow_id: str,
        event_type: str,
        phase: str,
        payload: dict[str, Any],
    ) -> str:
        """Record a single workflow event and append it to the JSONL ledger."""
        event_id = _new_event_id("EVT")
        event = WorkflowEvent(
            event_id=event_id,
            workflow_id=workflow_id,
            event_type=event_type,
            timestamp=time.time(),
            phase=phase,
            payload=payload,
            phase_hash=_hash_payload({"event_type": event_type, "phase": phase, "payload": payload}),
        )
        record = event.to_dict()
        record["version"] = CODING_ARENA_WORKFLOW_VERSION
        self._append_jsonl(record)
        if workflow_id in self._active_workflows:
            self._active_workflows[workflow_id]["events"].append(record)
        return event_id

    def append_batch(self, events: list[WorkflowEvent]) -> None:
        """Batch append a list of workflow events into the JSONL ledger."""
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        for event in events:
            record = event.to_dict()
            record["version"] = CODING_ARENA_WORKFLOW_VERSION
            lines.append(json.dumps(record, sort_keys=True, default=str))
        with open(self.ledger_path, "a", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")

    # --- Convenience methods for each event type ---

    def record_plan_candidate(self, workflow_id: str, candidate: dict[str, Any]) -> str:
        return self.record_event(
            workflow_id,
            EVENT_PLAN_CANDIDATE,
            "plan",
            {
                "candidate_id": candidate.get("candidate_id", ""),
                "source": candidate.get("source", ""),
                "cost_tier": candidate.get("cost_tier", ""),
                "score": candidate.get("score", 0.0),
                "plan": candidate.get("plan", {}),
                "phase_hash": candidate.get("phase_hash", ""),
            },
        )

    def record_shadow_critique(self, workflow_id: str, critic_report: dict[str, Any]) -> str:
        return self.record_event(
            workflow_id,
            EVENT_SHADOW_CRITIQUE,
            "plan_shadow",
            {
                "critic_id": critic_report.get("critic_id", ""),
                "candidate_id": critic_report.get("candidate_id", ""),
                "approved": critic_report.get("approved", True),
                "score": critic_report.get("score", 0.0),
                "blockers": critic_report.get("blockers", []),
                "rationale": critic_report.get("rationale", ""),
            },
        )

    def record_builder_context(
        self,
        workflow_id: str,
        context_packet: Any,
        task_id: str,
    ) -> str:
        packet_dict = context_packet.to_dict() if hasattr(context_packet, "to_dict") else dict(context_packet or {})
        record = BuilderContextRecord(
            task_id=task_id,
            target_file=str(packet_dict.get("target_file", "")),
            target_symbol=str(packet_dict.get("target_symbol") or ""),
            context_packet=packet_dict,
            source_excerpt_length=len(str(packet_dict.get("source_excerpt", ""))),
            nearby_tests_count=len(list(packet_dict.get("nearby_tests", []))),
            callers_count=len(list(packet_dict.get("callers", []))),
            neighbors_count=len(list(packet_dict.get("neighbors", []))),
        )
        return self.record_event(
            workflow_id,
            EVENT_BUILDER_CONTEXT_PACKET,
            "builder_context",
            record.to_dict(),
        )

    def record_patch_submission(self, workflow_id: str, submission: dict[str, Any]) -> str:
        diff = str(submission.get("diff", ""))
        return self.record_event(
            workflow_id,
            EVENT_PATCH_SUBMISSION,
            "patch_submission",
            {
                "task_id": submission.get("task_id", ""),
                "owner": submission.get("owner", ""),
                "diff_hash": _hash_diff(diff),
                "affected_files": submission.get("affected_files", []),
                "affected_symbols": submission.get("affected_symbols", []),
                "tests": submission.get("tests", []),
            },
        )

    def record_patch_preflight(
        self,
        workflow_id: str,
        task_id: str,
        preflight_result: Any,
    ) -> str:
        preflight_dict = preflight_result.to_dict() if hasattr(preflight_result, "to_dict") else dict(preflight_result or {})
        record = PatchAttemptRecord(
            task_id=task_id,
            status="preflight_passed" if preflight_dict.get("ok") else "preflight_failed",
            preflight=preflight_dict,
            diff_hash=_hash_diff(preflight_dict.get("diff", "")),
        )
        return self.record_event(
            workflow_id,
            EVENT_PATCH_PREFLIGHT_RESULT,
            "patch_preflight",
            record.to_dict(),
        )

    def record_temp_workspace_apply(self, workflow_id: str, workspace_result: Any) -> str:
        ws_dict = workspace_result.to_dict() if hasattr(workspace_result, "to_dict") else dict(workspace_result or {})
        return self.record_event(
            workflow_id,
            EVENT_TEMP_WORKSPACE_APPLY_RESULT,
            "temp_workspace_apply",
            {
                "ok": ws_dict.get("ok", False),
                "checks": ws_dict.get("checks", []),
                "failures": ws_dict.get("failures", []),
                "workspace_path": ws_dict.get("workspace_path"),
            },
        )

    def record_py_compile_test_topology(self, workflow_id: str, workspace_result: Any) -> str:
        ws_dict = workspace_result.to_dict() if hasattr(workspace_result, "to_dict") else dict(workspace_result or {})
        topology_delta = ws_dict.get("topology_delta", {}) or {}
        return self.record_event(
            workflow_id,
            EVENT_PY_COMPILE_TEST_TOPOLOGY_DELTA_RESULT,
            "py_compile_test_topology_delta",
            {
                "ok": ws_dict.get("ok", False),
                "test_results": ws_dict.get("test_results", {}),
                "topology_delta": topology_delta,
                "topology_summary": topology_delta.get("summary", {}) if isinstance(topology_delta, dict) else {},
                "failures": ws_dict.get("failures", []),
            },
        )

    def record_repair_attempt(self, workflow_id: str, task_id: str, repair_result: Any) -> str:
        repair_dict = repair_result.to_dict() if hasattr(repair_result, "to_dict") else dict(repair_result or {})
        record = RepairAttemptRecord(
            task_id=task_id,
            repair_ok=bool(repair_dict.get("ok", False)),
            repaired_diff_hash=_hash_diff(repair_dict.get("repaired_diff", "")),
            rejections_before=list(repair_dict.get("rejections_before", [])),
            rejections_after=list(repair_dict.get("rejections_after", [])),
            repair_reason=str(repair_dict.get("reason", "")),
        )
        return self.record_event(
            workflow_id,
            EVENT_REPAIR_ATTEMPT,
            "patch_repair",
            record.to_dict(),
        )

    def record_premium_judge_decision(self, workflow_id: str, judge_decision: dict[str, Any]) -> str:
        return self.record_event(
            workflow_id,
            EVENT_PREMIUM_JUDGE_DECISION,
            "premium_judge",
            {
                "role": judge_decision.get("role", ""),
                "approved": judge_decision.get("approved", False),
                "rationale": judge_decision.get("rationale", ""),
                "premium_called": judge_decision.get("premium_called", False),
                "selected_candidate_id": judge_decision.get("selected_candidate_id", ""),
                "phase_hash": judge_decision.get("phase_hash", ""),
            },
        )

    def record_hotswap_decision(self, workflow_id: str, hotswap_capsule: dict[str, Any]) -> str:
        return self.record_event(
            workflow_id,
            EVENT_HOTSWAP_DECISION,
            "hotswap",
            {
                "status": hotswap_capsule.get("status", ""),
                "hotswap_ready": hotswap_capsule.get("hotswap_ready", False),
                "phase_hash": hotswap_capsule.get("phase_hash", ""),
                "promotion_entrypoint": hotswap_capsule.get("promotion_entrypoint", {}),
            },
        )

    def record_outcome(
        self,
        workflow_id: str,
        outcome: WorkflowOutcome,
        *,
        context_packets: list[Any] | None = None,
    ) -> str:
        """Record the final workflow outcome.

        Wires successful and failed outcomes into UnifiedQDKT.observe(...)
        and wires context usefulness into
        aura_dream_retrieval.record_arena_retrieval_feedback(...).
        """
        event_id = self.record_event(
            workflow_id,
            EVENT_WORKFLOW_OUTCOME,
            "outcome",
            outcome.to_dict(),
        )

        # Wire to QDKT
        qdkt = self._get_qdkt()
        if qdkt is not None:
            try:
                qdkt.observe(
                    "coding_arena_workflow_outcome",
                    {
                        "workflow_id": workflow_id,
                        "success": outcome.success,
                        "hotswap_ready": outcome.hotswap_ready,
                        "failures_count": outcome.failures_count,
                        "stage": outcome.stage,
                        "target_file": outcome.target_file,
                    },
                    rationale=(
                        f"Workflow {'succeeded' if outcome.success else 'failed'}: "
                        f"{'hotswap_ready' if outcome.hotswap_ready else 'blocked'}"
                    ),
                    concept=f"coding_arena_workflow:{workflow_id}",
                    confidence=0.9 if outcome.success else 0.3,
                    subsystem="aura_coding_arena_workflow",
                )
            except Exception:
                pass

        # Wire context usefulness to DREAM
        dream_fn = self._get_dream_feedback_fn()
        if dream_fn is not None and DreamCandidate is not None and context_packets:
            verifier_result = {
                "approved": outcome.success,
                "hotswap_ready": outcome.hotswap_ready,
            }
            candidates: list[Any] = []
            for packet in context_packets:
                packet_dict = packet.to_dict() if hasattr(packet, "to_dict") else dict(packet or {})
                if packet_dict.get("source_excerpt"):
                    candidates.append(DreamCandidate(
                        candidate_id=f"source:{packet_dict.get('target_file', '')}",
                        candidate_type="source_excerpt",
                        source="CODEMAP/source_file",
                        content=str(packet_dict.get("source_excerpt", ""))[:200],
                        semantic_score=0.85,
                        verifier_result=verifier_result,
                    ))
                for test in packet_dict.get("nearby_tests", []):
                    candidates.append(DreamCandidate(
                        candidate_id=f"test:{test}",
                        candidate_type="nearby_test",
                        source="CODEMAP/test-neighbor",
                        content=str(test),
                        semantic_score=0.72,
                        verifier_result=verifier_result,
                    ))
                for caller in packet_dict.get("callers", []):
                    candidates.append(DreamCandidate(
                        candidate_id=f"caller:{caller}",
                        candidate_type="graph_node",
                        source="CODEMAP/topology",
                        content=str(caller),
                        semantic_score=0.65,
                        verifier_result=verifier_result,
                    ))
            if candidates:
                try:
                    dream_fn(
                        outcome.intent,
                        candidates,
                        target_type="code_context",
                        verifier_result=verifier_result,
                        arena_domain="code",
                    )
                except Exception:
                    pass

        # Clean up active workflow
        self._active_workflows.pop(workflow_id, None)
        return event_id

    def get_workflow_trace(self, workflow_id: str) -> list[dict[str, Any]]:
        """Read back all events for a given workflow_id from the JSONL ledger."""
        if not self.ledger_path.exists():
            return []
        trace: list[dict[str, Any]] = []
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("workflow_id") == workflow_id:
                    trace.append(record)
        return trace


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_CODING_ARENA_MEMORY: CodingArenaWorkflowMemory | None = None


def get_coding_arena_memory() -> CodingArenaWorkflowMemory:
    """Get the singleton CodingArenaWorkflowMemory instance."""
    global _CODING_ARENA_MEMORY
    if _CODING_ARENA_MEMORY is None:
        _CODING_ARENA_MEMORY = CodingArenaWorkflowMemory()
    return _CODING_ARENA_MEMORY


# ---------------------------------------------------------------------------
# Research gate policy enforcement
# ---------------------------------------------------------------------------

def convert_research_proposal_to_action_capsule(proposal: dict[str, Any]) -> Any:
    """Convert a research proposal suggesting new classes into an ActionCapsule first.

    Requirement 9: If a research proposal suggests new classes, convert it
    into an ActionCapsule first before any staging or application.

    This ensures research output flows through the bounded Arena pipeline
    rather than directly mutating production code.
    """
    if ActionCapsule is None:
        raise RuntimeError("ActionCapsule is not available from aura_liquid_planning_arena")

    capsule_id = str(proposal.get("capsule_id") or f"research-{_new_event_id('CAP')}")
    target_modules = list(proposal.get("target_modules", []) or [])
    # Preserve an explicit proposal target_file when present; otherwise fall back
    # to the first target_module when available, and finally to a safe default.
    _proposal_target = proposal.get("target_file")
    if _proposal_target:
        target_file = str(_proposal_target)
    elif target_modules:
        target_file = str(target_modules[0])
    else:
        target_file = "aura_node.py"
    concept = str(proposal.get("concept") or "research_synthesis")
    proposed_patch = str(proposal.get("proposed_patch") or proposal.get("clean_source") or "")

    return ActionCapsule.create(
        capsule_id=capsule_id,
        domain="code",
        role="research_act_worker",
        objective=f"Research-derived refactor: {concept}",
        target={
            "target_file": target_file,
            "target_symbol": proposal.get("target_symbol"),
            "target_modules": target_modules,
        },
        scope={
            "allowed_scope": "single research-derived Act Capsule",
            "proposed_patch_hash": _hash_diff(proposed_patch),
        },
        allowed_actions=["generate_unified_diff", "stage_patch"],
        forbidden_actions=["direct_production_write", "direct_incubator_write", "bypass_verifier"],
        acceptance_checks=[
            "Patch applies cleanly in temporary workspace",
            "py_compile passes on affected files",
            "Tests pass in temporary workspace",
            "Topology delta is coherent",
            "Premium Judge approves hot-swap",
        ],
        expected_output="UNIFIED_DIFF",
        escalation_triggers=[
            "preflight_failure",
            "temp_workspace_apply_failure",
            "test_failure",
            "topology_delta_incoherent",
        ],
        metadata={
            "source": "ingested_academic_engrams",
            "concept": concept,
            "gate_decision": proposal.get("gate_decision", ""),
            "gate_score": proposal.get("gate_score"),
            "mutation_policy": "arena_staging_required",
        },
    )


def validate_research_staging_gate(
    proposal: dict[str, Any],
    *,
    source_context: dict[str, Any] | None = None,
    tests: list[str] | None = None,
    preflight_result: Any = None,
) -> tuple[bool, str]:
    """Validate that a research-derived patch can proceed to Arena staging.

    Requirement 8: Require target source context, tests, and preflight
    validation before patch application.

    Returns (allowed: bool, reason: str).
    """
    # Must have target source context
    if not source_context or not source_context.get("target_file"):
        return False, "Research staging gate blocked: missing target source context."

    # Must have tests identified
    if not tests:
        return False, "Research staging gate blocked: no tests identified for validation."

    # Must have preflight validation result
    if preflight_result is None:
        return False, "Research staging gate blocked: no preflight validation result provided."

    preflight_dict = preflight_result.to_dict() if hasattr(preflight_result, "to_dict") else dict(preflight_result or {})
    if not preflight_dict.get("ok"):
        rejections = preflight_dict.get("rejections", [])
        return False, f"Research staging gate blocked: preflight validation failed: {rejections}"

    return True, "Research staging gate passed: source context, tests, and preflight validation all present."


def enforce_research_no_direct_mutation(research_output: dict[str, Any]) -> dict[str, Any]:
    """Ensure research output is staged, never directly mutating production.

    Requirement 7: Never allow !research output to directly mutate production.

    Wraps the research output in a staging envelope that enforces the
    arena_staging_required mutation policy.
    """
    return {
        "capsule_version": "AURA_RESEARCH_STAGING_ENVELOPE_V1",
        "timestamp": time.time(),
        "concept": research_output.get("concept", ""),
        "proposed_patch": research_output.get("proposed_patch") or research_output.get("clean_source") or "",
        "target_modules": list(research_output.get("target_modules", []) or [])[:5],
        "gate_decision": research_output.get("gate_decision", ""),
        "gate_score": research_output.get("gate_score"),
        "source": "ingested_academic_engrams",
        "mutation_policy": "arena_staging_required",
        "direct_mutation_allowed": False,
        "must_convert_to_action_capsule": True,
        "must_pass_staging_gate": True,
        "staging_path": "Aura_Staging/research_refactor_request.json",
    }