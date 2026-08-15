"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa902-[Q-SYS:ARCHITECT_LOOP]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Grounded Refactor Orchestration)
DEPENDENCIES: dataclasses, hashlib, json, logging, pathlib, typing, aura_codebase_navigator, aura_dream_retrieval, aura_fusion, aura_phase_capsule, aura_st3gg_recall, aura_substrate
FUNCTIONS: ActCapsule, FractalPlanCapsule, GroundingEvidence, ShadowFinding, ShadowReport, RefactorArenaTransaction, ArenaPatch, PatchStageResult, VerificationResult, ArchitectLedgerRecord, ArchitectLoopResult, ArchitectExecutionResult, CodemapLoadError, architect_capability_cards, build_fractal_plan_capsule, ground_plan_capsule, shadow_plan_capsule, build_refactor_arena, stage_arena_patch, verify_refactor_arena, judge_refactor_arena, build_rollback_capsule, build_hotswap_capsule, build_architect_ledger_record, append_architect_ledger, route_intensity, ArchitectFusionLoop
SYNOPSIS: Deterministic ArchitectFusionLoop substrate. Converts an architect intent into a sharded Plan Capsule, CODEMAP-grounded Act Capsules, Shadow findings, intensity routing, continuity handoff metadata, a bounded refactor arena projected into the Liquid Planning Arena substrate, verifier-gated hot-swap capsule, rollback capsule, and append-only ledger record before any patch is promoted.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
import hashlib
import json
import logging
from pathlib import Path
import subprocess
import time
from typing import Any

from aura_codebase_navigator import refresh_codemap_for_paths
from aura_dream_retrieval import DreamCandidate, rerank_for_arena
from aura_fst_routing import AuraCodingArenaRouter, RoutingFrame
from aura_fusion import DEFAULT_CONSTRAINTS, build_task_capsule
from aura_liquid_planning_arena import CodeArenaAdapter
from aura_phase_capsule import AuraPhaseCapsule, capture_phase_capsule
from aura_st3gg_recall import compile_st3gg_pointer, compile_visible_st3gg_capsule
from aura_substrate import REPO_ROOT, estimate_tokens

ARCHITECT_LOOP_VERSION = "AURA_ARCHITECT_LOOP_V1"
PLAN_CAPSULE_VERSION = "AURA_FRACTAL_PLAN_CAPSULE_V1"
ACT_CAPSULE_VERSION = "AURA_ACT_CAPSULE_V1"
SHADOW_REPORT_VERSION = "AURA_SHADOW_REPORT_V1"
REFACTOR_ARENA_VERSION = "AURA_REFACTOR_ARENA_V1"
ARENA_PATCH_VERSION = "AURA_ARENA_PATCH_V1"
ARCHITECT_VERIFICATION_VERSION = "AURA_ARCHITECT_VERIFICATION_V1"
ARCHITECT_HOTSWAP_VERSION = "AURA_ARCHITECT_HOTSWAP_V1"
ARCHITECT_ROLLBACK_VERSION = "AURA_ARCHITECT_ROLLBACK_V1"
ARCHITECT_LEDGER_VERSION = "AURA_ARCHITECT_LEDGER_V1"
ARCHITECT_LEDGER_PATH = Path(REPO_ROOT) / "Aura_Memory" / "architect_loop_ledger.jsonl"
_LOG = logging.getLogger(__name__)
_CODING_ARENA_ROUTER = AuraCodingArenaRouter()

ARCHITECT_CAPABILITY_ORDER = [
    "plan",
    "act",
    "ground",
    "shadow",
    "verify",
    "escalate",
    "handoff",
    "judge",
    "hotswap",
    "rollback",
    "ledger",
]

DEFAULT_ESCALATION_RULES = [
    "missing_file_or_symbol -> run Shadow before Builder",
    "act_capsule_too_large -> re-shard before cheap model execution",
    "tests_fail_twice -> escalate to planner or judge",
    "context_pressure_high -> emit phase continuity capsule",
    "topology_regression -> block Incubator",
]

DEFAULT_ACT_ESCALATIONS = [
    "missing target file",
    "missing target symbol",
    "requires public API change",
    "requires new dependency",
    "touches files outside allowed scope",
]

ACT_SIZE_ORDER = {"S": 0, "M": 1, "L": 2, "XL": 3}
PATCH_OUTPUT_MODES = {"PATCH", "UNIFIED_DIFF", "JSON_EDIT_PLAN", "PYTHON"}


class CodemapLoadError(RuntimeError):
    """Raised when Architect grounding cannot load a usable CODEMAP artifact."""


@dataclass
class ActCapsule:
    capsule_version: str
    task_id: str
    role: str
    objective: str
    target_file: str | None = None
    target_symbol: str | None = None
    related_files: list[str] = field(default_factory=list)
    allowed_scope: str = "single bounded edit"
    context_ref: str = ""
    topological_grounding: dict[str, Any] = field(default_factory=dict)
    acceptance: str = "Return a bounded patch or a refusal reason."
    escalate_if: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    expected_output: str = "UNIFIED_DIFF"
    size: str = "S"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ActCapsule:
        return cls(**data)


@dataclass
class FractalPlanCapsule:
    capsule_version: str
    objective: str
    architecture_decision: str
    constraints: list[str]
    acceptance_criteria: list[str]
    rollback_conditions: list[str]
    risk_map: list[str]
    act_capsules: list[ActCapsule]
    escalation_rules: list[str]
    fusion_capsule: dict[str, Any]
    context_ref: str
    st3gg_capsule: str | None
    continuity_capsule: AuraPhaseCapsule | None
    phase_hash: str
    bilateral_contract: dict[str, Any] = field(default_factory=dict)
    bilateral_plan_gate: dict[str, Any] = field(default_factory=dict)
    bilateral_proof_plan: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.continuity_capsule is not None:
            payload["continuity_capsule"] = self.continuity_capsule.to_dict()
        for key in (
            "bilateral_contract",
            "bilateral_plan_gate",
            "bilateral_proof_plan",
        ):
            if not payload.get(key):
                payload.pop(key, None)
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FractalPlanCapsule:
        payload = dict(data)
        payload["act_capsules"] = [ActCapsule.from_dict(item) for item in payload.get("act_capsules", [])]
        if payload.get("continuity_capsule"):
            payload["continuity_capsule"] = AuraPhaseCapsule.from_dict(payload["continuity_capsule"])
        return cls(**payload)


@dataclass
class GroundingEvidence:
    task_id: str
    target_file: str | None
    target_symbol: str | None
    file_exists: bool
    codemap_file_hit: bool
    symbol_exists: bool
    codemap_symbol_hits: list[dict[str, Any]]
    test_files: list[str]
    neighbor_files: list[str]
    dream_scores: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in (
            "bilateral_contract",
            "bilateral_plan_gate",
            "bilateral_proof_plan",
        ):
            if not payload.get(key):
                payload.pop(key, None)
        return payload


@dataclass
class ShadowFinding:
    shadow_type: str
    severity: str
    message: str
    task_id: str
    target_file: str | None = None
    target_symbol: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ShadowReport:
    report_version: str
    ok: bool
    phase_hash: str
    findings: list[ShadowFinding]
    gate: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["findings"] = [finding.to_dict() for finding in self.findings]
        return payload


@dataclass
class RefactorArenaTransaction:
    arena_version: str
    plan_phase_hash: str
    affected_files: list[str]
    boundary_contracts: list[dict[str, Any]]
    agent_capsules: list[dict[str, Any]]
    shared_patch_queue: list[dict[str, Any]]
    conflict_resolver: dict[str, Any]
    shadow_report: dict[str, Any]
    verification_ledger: list[dict[str, Any]]
    ready_for_incubator: bool
    rollback_hint: str
    agent_leases: list[dict[str, Any]] = field(default_factory=list)
    liquid_arena: dict[str, Any] = field(default_factory=dict)
    routing_decisions: list[dict[str, Any]] = field(default_factory=list)
    bilateral_contract: dict[str, Any] = field(default_factory=dict)
    bilateral_plan_gate: dict[str, Any] = field(default_factory=dict)
    bilateral_proof_plan: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ArenaPatch:
    patch_version: str
    patch_id: str
    task_id: str
    owner: str
    diff: str
    affected_files: list[str]
    affected_symbols: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    status: str = "staged"
    phase_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PatchStageResult:
    ok: bool
    arena: RefactorArenaTransaction
    patch: ArenaPatch | None
    findings: list[ShadowFinding]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "arena": self.arena.to_dict(),
            "patch": self.patch.to_dict() if self.patch else None,
            "findings": [finding.to_dict() for finding in self.findings],
        }


@dataclass
class VerificationResult:
    verification_version: str
    ok: bool
    stage: str
    checks: list[dict[str, Any]]
    failures: list[dict[str, Any]]
    hotswap_ready: bool
    phase_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ArchitectLedgerRecord:
    ledger_version: str
    event: str
    plan_phase_hash: str
    intensity: int
    stage_results: list[dict[str, Any]]
    verification: dict[str, Any]
    hotswap_capsule: dict[str, Any]
    phase_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ArchitectLoopResult:
    plan: FractalPlanCapsule
    grounding: list[GroundingEvidence]
    shadow_report: ShadowReport
    arena: RefactorArenaTransaction
    intensity: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan": self.plan.to_dict(),
            "grounding": [item.to_dict() for item in self.grounding],
            "shadow_report": self.shadow_report.to_dict(),
            "arena": self.arena.to_dict(),
            "intensity": self.intensity,
        }


@dataclass
class ArchitectExecutionResult:
    prepared: ArchitectLoopResult
    stage_results: list[PatchStageResult]
    verification: VerificationResult
    hotswap_capsule: dict[str, Any]
    ledger_record: ArchitectLedgerRecord

    def to_dict(self) -> dict[str, Any]:
        return {
            "prepared": self.prepared.to_dict(),
            "stage_results": [item.to_dict() for item in self.stage_results],
            "verification": self.verification.to_dict(),
            "hotswap_capsule": self.hotswap_capsule,
            "ledger_record": self.ledger_record.to_dict(),
        }


def _hash_payload(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=16).hexdigest()


def _normalize_path(path: str | None) -> str | None:
    if path is None:
        return None
    normalized = str(path).replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized or None


def _load_codemap(repo_root: str | Path) -> dict[str, Any]:
    path = Path(repo_root) / ".aura" / "CODEMAP.json"
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except OSError as exc:
        raise CodemapLoadError(f"CODEMAP artifact is unavailable at {path}") from exc
    except json.JSONDecodeError as exc:
        raise CodemapLoadError(f"CODEMAP artifact is not valid JSON at {path}") from exc
    if not isinstance(data, dict):
        raise CodemapLoadError(f"CODEMAP artifact must be a JSON object at {path}")
    return data



def _refresh_plan_codemap_targets(plan: FractalPlanCapsule, repo_root: str | Path) -> None:
    root = Path(repo_root)
    # Refresh may update an existing snapshot, but must never create truth
    # in a repository that has no CODEMAP. Grounding fails closed there.
    if not (root / ".aura" / "CODEMAP.json").is_file():
        return
    targets = sorted({
        normalized
        for normalized in (_normalize_path(act.target_file) for act in plan.act_capsules)
        if normalized
    })
    if not targets:
        return
    try:
        refresh_codemap_for_paths(targets, root=root, include_topology=True)
    except Exception as exc:
        _LOG.debug("CODEMAP target preflight refresh skipped: %s", type(exc).__name__)
        return

def _normalized_path_list(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        raw_values = [values]
    else:
        raw_values = list(values)
    normalized = []
    seen = set()
    for value in raw_values:
        item = _normalize_path(str(value))
        if item and item not in seen:
            normalized.append(item)
            seen.add(item)
    return normalized


def _diff_path_token(path: str) -> str | None:
    token = path.strip().strip('"').strip("'")
    if not token or token == "/dev/null":
        return None
    if "\t" in token:
        token = token.split("\t", 1)[0]
    for prefix in ("a/", "b/"):
        if token.startswith(prefix):
            token = token[2:]
            break
    return _normalize_path(token)


def _add_diff_file(files: list[str], seen: set[str], path: str) -> None:
    normalized = _diff_path_token(path)
    if normalized and normalized not in seen:
        files.append(normalized)
        seen.add(normalized)


def _diff_touched_files(diff: str) -> list[str]:
    files: list[str] = []
    seen: set[str] = set()
    previous_was_minus_header = False
    for line in str(diff or "").splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4:
                _add_diff_file(files, seen, parts[2])
                _add_diff_file(files, seen, parts[3])
            previous_was_minus_header = False
            continue
        if line.startswith("--- "):
            _add_diff_file(files, seen, line[4:])
            previous_was_minus_header = True
            continue
        if line.startswith("+++ ") and previous_was_minus_header:
            _add_diff_file(files, seen, line[4:])
            previous_was_minus_header = False
            continue
        previous_was_minus_header = False
        for marker in ("*** Update File: ", "*** Add File: ", "*** Delete File: "):
            if line.startswith(marker):
                _add_diff_file(files, seen, line[len(marker):])
                break
    return files


def _agent_capsule_for_task(arena: RefactorArenaTransaction, task_id: str) -> dict[str, Any] | None:
    for capsule in arena.agent_capsules:
        if str(capsule.get("task_id")) == str(task_id):
            return capsule
    return None


def _arena_files_for_task(arena: RefactorArenaTransaction, task_id: str) -> set[str]:
    capsule = _agent_capsule_for_task(arena, task_id)
    if capsule is None:
        return set()
    scoped = {
        _normalize_path(capsule.get("target_file")),
        *(_normalize_path(item) for item in capsule.get("related_files", []) or []),
    }
    scoped.discard(None)
    arena_files = set(arena.affected_files)
    return {str(item) for item in scoped if item in arena_files}


def _lease_files_for_task(arena: RefactorArenaTransaction, task_id: str) -> set[str]:
    files = set()
    for lease in arena.agent_leases:
        if str(lease.get("capsule_id")) != str(task_id):
            continue
        for region in lease.get("regions", []) or []:
            if region.get("region_type") == "file" and region.get("mode") == "write":
                normalized = _normalize_path(region.get("id"))
                if normalized:
                    files.add(normalized)
    return files


def _routing_decision_for_task(arena: RefactorArenaTransaction, task_id: str) -> dict[str, Any] | None:
    for decision in arena.routing_decisions:
        if str(decision.get("task_id")) == str(task_id):
            return decision
    return None


def _file_digest(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.blake2b(digest_size=16)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _runner_status(outcome: Any) -> tuple[bool, dict[str, Any]]:
    if isinstance(outcome, dict):
        status = str(outcome.get("status", "")).lower()
        returncode = outcome.get("returncode")
        ok = outcome.get("ok")
        if ok is not None:
            passed = bool(ok)
        elif status in {"ok", "pass", "passed", "success"}:
            passed = True
        elif status in {"fail", "failed", "failure", "error"}:
            passed = False
        else:
            passed = returncode == 0
        return passed, outcome
    if isinstance(outcome, bool):
        return outcome, {"status": "passed" if outcome else "failed"}
    if isinstance(outcome, str):
        status = outcome.strip().lower()
        if status in {"ok", "pass", "passed", "success"}:
            return True, {"status": status}
        if status in {"fail", "failed", "failure", "error"}:
            return False, {"status": status}
    if isinstance(outcome, tuple) and outcome:
        passed, details = _runner_status(outcome[0])
        if len(outcome) > 1:
            details = dict(details)
            details["detail"] = outcome[1]
        return passed, details
    if isinstance(outcome, int):
        return outcome == 0, {"returncode": outcome}
    return bool(outcome), {"status": "passed" if outcome else "failed"}


def architect_capability_cards() -> list[dict[str, Any]]:
    """Return the callable capability map for the final Architect loop."""
    return [
        {
            "capability": "plan",
            "function": "build_fractal_plan_capsule",
            "input": "architect objective, constraints, risk map, requested Act shards",
            "output": "FractalPlanCapsule",
            "gate": "PLAN mode",
        },
        {
            "capability": "act",
            "function": "stage_arena_patch",
            "input": "Builder diff emitted from a bounded Act Capsule",
            "output": "ArenaPatch in the shared patch queue",
            "gate": "one owner, one bounded scope",
        },
        {
            "capability": "ground",
            "function": "ground_plan_capsule",
            "input": "FractalPlanCapsule and CODEMAP",
            "output": "GroundingEvidence",
            "gate": "fail closed when CODEMAP is unavailable",
        },
        {
            "capability": "shadow",
            "function": "shadow_plan_capsule",
            "input": "Plan Capsule plus GroundingEvidence",
            "output": "ShadowReport",
            "gate": "blocks fake files, fake symbols, oversized work, and weak local truth",
        },
        {
            "capability": "verify",
            "function": "verify_refactor_arena",
            "input": "RefactorArenaTransaction with staged patches",
            "output": "VerificationResult",
            "gate": "no hot-swap until patch ownership, boundaries, conflicts, and tests pass",
        },
        {
            "capability": "escalate",
            "function": "route_intensity",
            "input": "Plan Capsule and ShadowReport",
            "output": "0-5 orchestration intensity",
            "gate": "premium planner or judge required for blockers and high-risk shards",
        },
        {
            "capability": "handoff",
            "function": "capture_phase_capsule",
            "input": "high context pressure plan state",
            "output": "AuraPhaseCapsule",
            "gate": "context rollover keeps target and phase hash stable",
        },
        {
            "capability": "judge",
            "function": "judge_refactor_arena",
            "input": "VerificationResult",
            "output": "promote, repair, or escalate decision",
            "gate": "conflicts and failed tests must not be promoted",
        },
        {
            "capability": "hotswap",
            "function": "build_hotswap_capsule",
            "input": "verified RefactorArenaTransaction",
            "output": "hot-swap capsule",
            "gate": "verifier hotswap_ready must be true",
        },
        {
            "capability": "rollback",
            "function": "build_rollback_capsule",
            "input": "affected files before promotion",
            "output": "file digest rollback capsule",
            "gate": "phase-hash anchored discard/revert path",
        },
        {
            "capability": "ledger",
            "function": "append_architect_ledger",
            "input": "ArchitectLedgerRecord",
            "output": "append-only JSONL record",
            "gate": "verified or blocked outcome is recorded",
        },
    ]



def _codemap_paths(codemap: dict[str, Any]) -> set[str]:
    coverage = codemap.get("coverage", {})
    paths = set()
    for item in coverage.get("all_included_paths_sorted", []) or []:
        normalized = _normalize_path(str(item))
        if normalized:
            paths.add(normalized)
    for key in ("file_cards", "files"):
        for card in codemap.get(key, []) or []:
            if not isinstance(card, dict):
                continue
            normalized = _normalize_path(str(card.get("path", "")))
            if normalized:
                paths.add(normalized)
    return paths


def _file_card(codemap: dict[str, Any], target_file: str | None) -> dict[str, Any]:
    normalized = _normalize_path(target_file)
    if not normalized:
        return {}
    for key in ("file_cards", "files"):
        for card in codemap.get(key, []) or []:
            if not isinstance(card, dict):
                continue
            if _normalize_path(str(card.get("path", ""))) == normalized:
                return card
    return {}

def _symbol_hits(codemap: dict[str, Any], target_symbol: str | None, target_file: str | None) -> list[dict[str, Any]]:
    if not target_symbol:
        return []
    normalized_file = _normalize_path(target_file)
    raw_hits = codemap.get("symbol_index", {}).get(str(target_symbol), []) or []
    hits = []
    for hit in raw_hits:
        if not isinstance(hit, dict):
            continue
        hit_file = _normalize_path(str(hit.get("file", "")))
        if normalized_file is None or hit_file == normalized_file:
            hits.append(hit)
    return hits


def _test_candidates(repo_root: str | Path, target_file: str | None) -> list[str]:
    normalized = _normalize_path(target_file)
    if not normalized:
        return []
    root = Path(repo_root)
    stem = Path(normalized).stem
    candidates = [
        f"test_{stem}.py",
        f"tests/test_{stem}.py",
    ]
    return [candidate for candidate in candidates if (root / candidate).exists()]


def _dream_candidates_for_grounding(
    *,
    target_file: str | None,
    target_symbol: str | None,
    symbol_hits: list[dict[str, Any]],
    test_files: list[str],
    neighbor_files: list[str],
) -> list[DreamCandidate]:
    candidates: list[DreamCandidate] = []
    if target_file:
        candidates.append(
            DreamCandidate(
                candidate_id=f"file:{target_file}",
                candidate_type="codemap_file",
                source="CODEMAP",
                content=target_file,
                semantic_score=0.82,
                truth_boundary="code truth remains in repository files and tests",
                metadata={"path": target_file, "target_symbol": target_symbol},
            )
        )
    for hit in symbol_hits:
        symbol_name = str(hit.get("name") or target_symbol or "")
        hit_file = _normalize_path(hit.get("file")) or target_file or ""
        candidates.append(
            DreamCandidate(
                candidate_id=f"symbol:{hit_file}:{symbol_name}",
                candidate_type="codemap_symbol",
                source="CODEMAP",
                content=f"{hit_file} {symbol_name}",
                semantic_score=0.78,
                truth_boundary="symbol truth remains in CODEMAP and parsed source",
                metadata=hit,
            )
        )
    for test_file in test_files:
        candidates.append(
            DreamCandidate(
                candidate_id=f"test:{test_file}",
                candidate_type="nearby_test",
                source="CODEMAP/test-neighbor surface",
                content=test_file,
                semantic_score=0.72,
                truth_boundary="test truth remains in executable test files",
                metadata={"path": test_file},
            )
        )
    for neighbor_file in neighbor_files:
        candidates.append(
            DreamCandidate(
                candidate_id=f"neighbor:{neighbor_file}",
                candidate_type="neighbor_file",
                source="CODEMAP/topology",
                content=neighbor_file,
                semantic_score=0.58,
                truth_boundary="neighbor context is read-only unless leased",
                metadata={"path": neighbor_file},
            )
        )
    return candidates


def _classify_act_size(task: dict[str, Any]) -> str:
    files = {
        _normalize_path(task.get("target_file")),
        *(_normalize_path(item) for item in task.get("related_files", []) or []),
        *(_normalize_path(item) for item in task.get("target_files", []) or []),
    }
    files.discard(None)
    steps = task.get("steps", []) or []
    text = " ".join(
        str(task.get(key, ""))
        for key in ("objective", "allowed_scope", "acceptance", "expected_output")
    ).lower()
    risk_hits = sum(1 for word in ("rewrite", "public api", "multi-file", "dependency", "schema") if word in text)
    if len(files) > 4 or len(steps) > 7 or risk_hits >= 3:
        return "XL"
    if len(files) > 2 or len(steps) > 4 or risk_hits >= 2:
        return "L"
    if len(files) > 1 or len(steps) > 2 or risk_hits == 1:
        return "M"
    return "S"


def _act_context_ref(plan_objective: str, task_id: str, target_file: str | None, target_symbol: str | None) -> str:
    material = json.dumps(
        {
            "objective": plan_objective,
            "task_id": task_id,
            "target_file": _normalize_path(target_file),
            "target_symbol": target_symbol,
        },
        sort_keys=True,
    )
    pointer, _dash_key, _glyph, _header = compile_st3gg_pointer(material, namespace="ACT")
    return pointer


def _build_act_capsule(
    objective: str,
    raw_task: str | dict[str, Any],
    *,
    index: int,
    constraints: list[str],
    bilateral_contract_ref: str = "",
) -> ActCapsule:
    if isinstance(raw_task, str):
        task = {"objective": raw_task}
    else:
        task = dict(raw_task)
    task_id = str(task.get("task_id") or task.get("id") or f"A{index + 1}")
    target_file = _normalize_path(task.get("target_file"))
    related_files = [_normalize_path(item) for item in task.get("related_files", []) or []]
    related_files = [item for item in related_files if item]
    size = str(task.get("size") or _classify_act_size(task)).upper()
    if size not in ACT_SIZE_ORDER:
        size = _classify_act_size(task)
    target_symbol = task.get("target_symbol")
    topological_grounding = dict(
        task.get("topological_grounding", {})
        if isinstance(task.get("topological_grounding"), dict)
        else {}
    )
    if bilateral_contract_ref:
        topological_grounding["bilateral_contract_ref"] = bilateral_contract_ref
    return ActCapsule(
        capsule_version=ACT_CAPSULE_VERSION,
        task_id=task_id,
        role=str(task.get("role", "cheap_builder")),
        objective=str(task.get("objective", "")).strip(),
        target_file=target_file,
        target_symbol=str(target_symbol) if target_symbol else None,
        related_files=related_files,
        allowed_scope=str(task.get("allowed_scope", "single bounded edit")),
        context_ref=str(task.get("context_ref") or _act_context_ref(objective, task_id, target_file, target_symbol)),
        topological_grounding=topological_grounding,
        acceptance=str(task.get("acceptance", "Return a bounded patch or a refusal reason.")),
        escalate_if=list(task.get("escalate_if", DEFAULT_ACT_ESCALATIONS)),
        constraints=list(task.get("constraints", constraints)),
        expected_output=str(task.get("expected_output", "UNIFIED_DIFF")).upper(),
        size=size,
    )


def _artifact_for_target(target_file: str | None, expected_output: str) -> str:
    path = _normalize_path(target_file)
    if path and Path(path).name.startswith("test_"):
        return "test_file"
    if path and path.endswith(".py"):
        return "python_module"
    if path and path.endswith((".md", ".txt", ".rst")):
        return "documentation"
    if expected_output.upper() in PATCH_OUTPUT_MODES:
        return "patch"
    return "documentation"


def _scope_for_act(act: ActCapsule) -> str:
    scope_text = " ".join([act.allowed_scope, act.objective, act.acceptance]).lower()
    if "repo" in scope_text or "repository" in scope_text:
        return "repo"
    if "subsystem" in scope_text or "multi-file" in scope_text or act.size in {"L", "XL"}:
        return "subsystem"
    if act.target_symbol:
        return "symbol"
    return "file"


def _risk_for_act(plan: FractalPlanCapsule, act: ActCapsule) -> str:
    task_text = " ".join([plan.objective, act.objective, act.allowed_scope]).lower()
    explicit_risk_text = " ".join(plan.risk_map).lower()
    if any(term in task_text for term in ("live", "hot-swap", "hotswap", "promote")):
        return "live"
    if any(term in explicit_risk_text for term in ("live traffic", "production", "customer-facing", "promote immediately")):
        return "live"
    if act.size in {"L", "XL"} or any(term in f"{task_text} {explicit_risk_text}" for term in ("high risk", "public api", "dependency", "schema", "rewrite")):
        return "high"
    if any(term in task_text for term in ("read-only", "explain", "inspect")):
        return "low"
    return "medium"


def _routing_frame_for_act(plan: FractalPlanCapsule, act: ActCapsule, evidence: GroundingEvidence | None) -> RoutingFrame:
    grounding: list[str] = []
    if evidence is not None:
        if evidence.file_exists:
            grounding.append("file_exists")
        if evidence.symbol_exists:
            grounding.append("symbol_exists")
        if evidence.test_files:
            grounding.append("tests_exist")
        if evidence.codemap_file_hit and (not act.target_symbol or evidence.symbol_exists):
            grounding.append("codemap_grounded")
        if evidence.file_exists and evidence.codemap_file_hit and evidence.symbol_exists and evidence.test_files:
            grounding.append("full")
    tests = "existing" if evidence is not None and evidence.test_files else "none"
    expected_output = str(act.expected_output or "UNIFIED_DIFF").upper()
    action = "modify" if expected_output in PATCH_OUTPUT_MODES else "inspect"
    return RoutingFrame(
        intent="code_refactor",
        artifact=_artifact_for_target(act.target_file, expected_output),
        action=action,
        scope=_scope_for_act(act),
        risk=_risk_for_act(plan, act),
        grounding=tuple(grounding),
        tests=tests,
        quality="balanced",
        cost="local_first",
        target_file=act.target_file,
        target_symbol=act.target_symbol,
    )


def build_fractal_plan_capsule(
    objective: str,
    *,
    architecture_decision: str,
    act_tasks: list[str | dict[str, Any]],
    target_file: str | None = None,
    target_symbol: str | None = None,
    acceptance_criteria: list[str] | None = None,
    rollback_conditions: list[str] | None = None,
    risk_map: list[str] | None = None,
    constraints: list[str] | None = None,
    escalation_rules: list[str] | None = None,
    repo_root: str | Path = REPO_ROOT,
    context_pressure: float = 0.0,
    continuity_threshold: float = 0.86,
    bilateral_contract: Mapping[str, Any] | None = None,
    bilateral_plan_gate: Mapping[str, Any] | None = None,
    bilateral_proof_plan: Mapping[str, Any] | None = None,
) -> FractalPlanCapsule:
    """Build a deterministic plan capsule that is pre-sharded into bounded Act Capsules."""
    plan_constraints = list(constraints or DEFAULT_CONSTRAINTS)
    bilateral_data = dict(bilateral_contract or {})
    bilateral_gate = dict(bilateral_plan_gate or {})
    bilateral_proof = dict(bilateral_proof_plan or {})
    contract_ref = str(bilateral_data.get("contract_digest") or "")
    act_capsules = [
        _build_act_capsule(
            objective,
            task,
            index=index,
            constraints=plan_constraints,
            bilateral_contract_ref=contract_ref,
        )
        for index, task in enumerate(act_tasks)
    ]
    fusion_capsule = build_task_capsule(
        objective,
        target_file=_normalize_path(target_file),
        target_symbol=target_symbol,
        output_mode="JSON_EDIT_PLAN",
        constraints=plan_constraints,
        repo_root=str(repo_root),
        extra={
            "architect_loop_version": ARCHITECT_LOOP_VERSION,
            "plan_mode": "PLAN",
            "act_task_count": len(act_capsules),
        },
    )
    pointer, _dash_key, _glyph, _header = compile_st3gg_pointer(
        json.dumps(
            {
                "objective": objective,
                "architecture_decision": architecture_decision,
                "act_task_count": len(act_capsules),
            },
            sort_keys=True,
        ),
        namespace="PLAN",
    )
    st3gg_capsule = compile_visible_st3gg_capsule([
        {
            "task_id": act.task_id,
            "file": act.target_file or "",
            "symbol": act.target_symbol or "",
            "size": act.size,
        }
        for act in act_capsules
    ])
    continuity_capsule = None
    if context_pressure >= continuity_threshold:
        continuity_seed = json.dumps(
            {
                "objective": objective,
                "fusion_phase_hash": fusion_capsule["phase_hash"],
                "act_ids": [act.task_id for act in act_capsules],
            },
            sort_keys=True,
        )
        continuity_capsule = capture_phase_capsule(
            continuity_seed,
            run_id=fusion_capsule["phase_hash"],
            previous_agent="ARCHITECT",
            next_role="WORKER",
            target_file=_normalize_path(target_file),
            target_symbol=target_symbol,
            next_action="Resume fractal plan execution at the next unverified Act Capsule.",
        )

    base_payload = {
        "capsule_version": PLAN_CAPSULE_VERSION,
        "objective": objective,
        "architecture_decision": architecture_decision,
        "constraints": plan_constraints,
        "acceptance_criteria": acceptance_criteria or [],
        "rollback_conditions": rollback_conditions or [],
        "risk_map": risk_map or [],
        "act_capsules": [act.to_dict() for act in act_capsules],
        "escalation_rules": escalation_rules or list(DEFAULT_ESCALATION_RULES),
        "fusion_phase_hash": fusion_capsule["phase_hash"],
        "context_ref": pointer,
        "continuity_phase_hash": continuity_capsule.phase_hash if continuity_capsule else None,
    }
    if bilateral_data:
        base_payload.update(
            {
                "bilateral_contract_digest": contract_ref,
                "bilateral_plan_gate_digest": bilateral_gate.get("gate_digest"),
                "bilateral_proof_plan": bilateral_proof,
            }
        )
    return FractalPlanCapsule(
        capsule_version=PLAN_CAPSULE_VERSION,
        objective=objective,
        architecture_decision=architecture_decision,
        constraints=plan_constraints,
        acceptance_criteria=acceptance_criteria or [],
        rollback_conditions=rollback_conditions or [],
        risk_map=risk_map or [],
        act_capsules=act_capsules,
        escalation_rules=escalation_rules or list(DEFAULT_ESCALATION_RULES),
        fusion_capsule=fusion_capsule,
        context_ref=pointer,
        st3gg_capsule=st3gg_capsule,
        continuity_capsule=continuity_capsule,
        phase_hash=_hash_payload(base_payload),
        bilateral_contract=bilateral_data,
        bilateral_plan_gate=bilateral_gate,
        bilateral_proof_plan=bilateral_proof,
    )


def ground_plan_capsule(
    plan: FractalPlanCapsule,
    *,
    repo_root: str | Path = REPO_ROOT,
    refresh_codemap: bool = True,
) -> list[GroundingEvidence]:
    """Map every Act Capsule to actual CODEMAP files, symbols, and nearby tests.

    ``refresh_codemap=False`` is reserved for read-only analysis callers that
    must consume the exact checked-in navigation snapshot without rewriting it.
    """
    root = Path(repo_root)
    resolved_root = root.resolve()
    if refresh_codemap:
        _refresh_plan_codemap_targets(plan, root)
    try:
        codemap = _load_codemap(root)
    except CodemapLoadError as exc:
        raise CodemapLoadError(f"Cannot ground Architect plan without CODEMAP: {exc}") from exc
    codemap_paths = _codemap_paths(codemap)
    evidence = []
    for act in plan.act_capsules:
        target_file = _normalize_path(act.target_file)
        resolved_target = (root / target_file).resolve() if target_file else None
        in_repo = False
        grounded_target_file = target_file
        if resolved_target is not None:
            try:
                grounded_target_file = resolved_target.relative_to(resolved_root).as_posix()
                in_repo = True
            except ValueError:
                in_repo = False
        file_exists = bool(target_file and in_repo and resolved_target and resolved_target.exists())
        codemap_file_hit = bool(grounded_target_file and in_repo and grounded_target_file in codemap_paths)
        symbol_hits = _symbol_hits(codemap, act.target_symbol, grounded_target_file if in_repo else target_file)
        card = _file_card(codemap, grounded_target_file if in_repo else None)
        topology = card.get("topology", {}) if isinstance(card, dict) else {}
        neighbor_files = [
            _normalize_path(item)
            for item in topology.get("neighbor_files", []) or []
            if _normalize_path(item)
        ]
        test_files = _test_candidates(root, grounded_target_file if in_repo else None)
        dream_candidates = _dream_candidates_for_grounding(
            target_file=grounded_target_file if in_repo else target_file,
            target_symbol=act.target_symbol,
            symbol_hits=symbol_hits,
            test_files=test_files,
            neighbor_files=neighbor_files,
        )
        dream_result = rerank_for_arena(
            plan.objective,
            dream_candidates,
            "code_context",
            arena_domain="code",
            expected_output=act.expected_output,
            record=False,
            metadata={"task_id": act.task_id, "plan_phase_hash": plan.phase_hash},
        ) if dream_candidates else {"scores": []}
        evidence.append(
            GroundingEvidence(
                task_id=act.task_id,
                target_file=grounded_target_file,
                target_symbol=act.target_symbol,
                file_exists=file_exists,
                codemap_file_hit=codemap_file_hit,
                symbol_exists=bool(symbol_hits) if act.target_symbol else True,
                codemap_symbol_hits=symbol_hits,
                test_files=test_files,
                neighbor_files=neighbor_files,
                dream_scores=dream_result.get("scores", []),
            )
        )
    return evidence


def shadow_plan_capsule(
    plan: FractalPlanCapsule,
    grounding: list[GroundingEvidence],
) -> ShadowReport:
    """Detect fake files, fake symbols, weak tests, and oversized act capsules before Builder runs."""
    by_task = {item.task_id: item for item in grounding}
    findings: list[ShadowFinding] = []
    bilateral = plan.bilateral_contract
    bilateral_gate = plan.bilateral_plan_gate
    if bilateral:
        if bilateral_gate.get("passed") is not True:
            findings.append(
                ShadowFinding(
                    shadow_type="bilateral_plan_gate",
                    severity="blocker",
                    message="Deterministic bilateral plan gate did not pass.",
                    task_id="PLAN",
                )
            )
        contract_ref = str(bilateral.get("contract_digest") or "")
        allowed_paths = set(bilateral.get("allowed_paths") or ())
        for act in plan.act_capsules:
            if (
                not contract_ref
                or act.topological_grounding.get("bilateral_contract_ref")
                != contract_ref
            ):
                findings.append(
                    ShadowFinding(
                        shadow_type="intent_trace_missing",
                        severity="blocker",
                        message="Act Capsule does not trace to the confirmed bilateral contract.",
                        task_id=act.task_id,
                        target_file=act.target_file,
                        target_symbol=act.target_symbol,
                    )
                )
            act_paths = {
                item
                for item in [act.target_file, *act.related_files]
                if item
            }
            if not act_paths.issubset(allowed_paths):
                findings.append(
                    ShadowFinding(
                        shadow_type="confirmed_scope_changed",
                        severity="blocker",
                        message="Act Capsule exceeds the confirmed allowed path set.",
                        task_id=act.task_id,
                        target_file=act.target_file,
                        target_symbol=act.target_symbol,
                    )
                )
    for act in plan.act_capsules:
        evidence = by_task.get(act.task_id)
        if evidence is None:
            findings.append(
                ShadowFinding(
                    shadow_type="missing_grounding",
                    severity="blocker",
                    message="Act Capsule has no Grounder evidence.",
                    task_id=act.task_id,
                    target_file=act.target_file,
                    target_symbol=act.target_symbol,
                )
            )
            continue
        if act.expected_output in PATCH_OUTPUT_MODES and not act.target_file:
            findings.append(
                ShadowFinding(
                    shadow_type="ungrounded_mutation",
                    severity="blocker",
                    message="Patch-like Act Capsule has no target_file.",
                    task_id=act.task_id,
                    target_file=act.target_file,
                    target_symbol=act.target_symbol,
                )
            )
        if _normalize_path(act.target_file) == "aura_incubator.py":
            findings.append(
                ShadowFinding(
                    shadow_type="legacy_incubator_target",
                    severity="blocker",
                    message="Live Architect patches must use the Refactor Arena; aura_incubator.py is legacy quarantine only.",
                    task_id=act.task_id,
                    target_file=act.target_file,
                    target_symbol=act.target_symbol,
                )
            )
        if act.target_file and not evidence.file_exists:
            findings.append(
                ShadowFinding(
                    shadow_type="fake_file",
                    severity="blocker",
                    message="Target file is absent from the working tree.",
                    task_id=act.task_id,
                    target_file=act.target_file,
                    target_symbol=act.target_symbol,
                )
            )
        elif act.target_file and not evidence.codemap_file_hit:
            findings.append(
                ShadowFinding(
                    shadow_type="weak_codemap_grounding",
                    severity="warn",
                    message="Target file exists but is absent from CODEMAP.",
                    task_id=act.task_id,
                    target_file=act.target_file,
                    target_symbol=act.target_symbol,
                )
            )
        if act.target_symbol and not evidence.symbol_exists:
            findings.append(
                ShadowFinding(
                    shadow_type="fake_symbol",
                    severity="blocker",
                    message="Target symbol is absent from CODEMAP for the target file.",
                    task_id=act.task_id,
                    target_file=act.target_file,
                    target_symbol=act.target_symbol,
                )
            )
        if act.expected_output in PATCH_OUTPUT_MODES and evidence.file_exists and not evidence.test_files:
            findings.append(
                ShadowFinding(
                    shadow_type="missing_test",
                    severity="warn",
                    message="No nearby test file was found for the target file.",
                    task_id=act.task_id,
                    target_file=act.target_file,
                    target_symbol=act.target_symbol,
                )
            )
        if ACT_SIZE_ORDER.get(act.size, 0) >= ACT_SIZE_ORDER["L"]:
            findings.append(
                ShadowFinding(
                    shadow_type="act_capsule_too_large",
                    severity="warn" if act.size == "L" else "blocker",
                    message=f"Act Capsule size {act.size} should be re-sharded before cheap model execution.",
                    task_id=act.task_id,
                    target_file=act.target_file,
                    target_symbol=act.target_symbol,
                )
            )

    blockers = [finding for finding in findings if finding.severity == "blocker"]
    gate = "BLOCK_BUILDER" if blockers else "ALLOW_BUILDER_WITH_WARNINGS" if findings else "ALLOW_BUILDER"
    return ShadowReport(
        report_version=SHADOW_REPORT_VERSION,
        ok=not blockers,
        phase_hash=_hash_payload({
            "plan_phase_hash": plan.phase_hash,
            "findings": [finding.to_dict() for finding in findings],
        }),
        findings=findings,
        gate=gate,
    )


def build_refactor_arena(
    plan: FractalPlanCapsule,
    grounding: list[GroundingEvidence],
    shadow_report: ShadowReport,
) -> RefactorArenaTransaction:
    """Create the shared bounded workspace metadata for Builder, Verifier, and Incubator."""
    by_task = {item.task_id: item for item in grounding}
    routing_decisions = []
    for act in plan.act_capsules:
        frame = _routing_frame_for_act(plan, act, by_task.get(act.task_id))
        decision = _CODING_ARENA_ROUTER.route(frame).to_dict()
        routing_decisions.append(
            {
                **decision,
                "task_id": act.task_id,
                "target_file": act.target_file,
                "target_symbol": act.target_symbol,
                "frame": frame.to_dict(),
            }
        )
    affected_files = sorted({
        evidence.target_file
        for evidence in grounding
        if evidence.target_file and evidence.file_exists
    })
    liquid_arena = CodeArenaAdapter().build_arena(
        objective=plan.objective,
        plan_phase_hash=plan.phase_hash,
        act_capsules=plan.act_capsules,
        grounding=grounding,
        shadow_report=shadow_report,
    )
    boundary_contracts = []
    for contract in liquid_arena.boundary_contracts:
        metadata = dict(contract.get("metadata", {}) or {})
        boundary_contracts.append(
            {
                **contract,
                "task_id": metadata.get("task_id"),
                "target_file": metadata.get("target_file"),
                "target_symbol": metadata.get("target_symbol"),
                "upstream": metadata.get("upstream"),
                "downstream": metadata.get("downstream"),
                "agent_scope": next((act.allowed_scope for act in plan.act_capsules if act.task_id == metadata.get("task_id")), ""),
                "neighbor_files": metadata.get("neighbor_files", []),
            }
        )
    builder_authorized = bool(routing_decisions) and all(
        decision.get("route") == "BUILDER_PATCH"
        for decision in routing_decisions
    )
    ready = (
        shadow_report.ok
        and all(item.file_exists for item in grounding if item.target_file)
        and builder_authorized
    )
    return RefactorArenaTransaction(
        arena_version=REFACTOR_ARENA_VERSION,
        plan_phase_hash=plan.phase_hash,
        affected_files=affected_files,
        boundary_contracts=boundary_contracts,
        agent_capsules=[act.to_dict() for act in plan.act_capsules],
        shared_patch_queue=[],
        conflict_resolver={
            "mode": "liquid_region_lease",
            "cross_boundary_edit": "escalate_to_shadow",
            "same_file_conflict": "judge_then_reground",
            "lease_violation": "block_transaction",
        },
        shadow_report=shadow_report.to_dict(),
        verification_ledger=[
            {"stage": "ground", "status": "passed" if all(item.file_exists for item in grounding if item.target_file) else "blocked"},
            {"stage": "shadow", "status": "passed" if shadow_report.ok else "blocked", "gate": shadow_report.gate},
            {
                "stage": "arena_router",
                "status": "passed" if builder_authorized else "routed",
                "routes": [
                    {
                        "task_id": item.get("task_id"),
                        "route": item.get("route"),
                        "reason": item.get("reason"),
                        "symbol_output": item.get("symbol_output"),
                    }
                    for item in routing_decisions
                ],
            },
            {"stage": "liquid_arena", "status": "leased", "domain": liquid_arena.domain, "lease_count": len(liquid_arena.agent_leases)},
            {"stage": "tests", "status": "pending", "test_files": sorted({name for item in grounding for name in item.test_files})},
            {"stage": "codemap_refresh", "status": "pending", "files_to_refresh": affected_files},
        ],
        ready_for_incubator=ready,
        rollback_hint="Keep patches staged in the arena until verifier passes; use the plan phase hash to discard the transaction.",
        agent_leases=liquid_arena.agent_leases,
        liquid_arena=liquid_arena.to_dict(),
        routing_decisions=routing_decisions,
        bilateral_contract=dict(plan.bilateral_contract),
        bilateral_plan_gate=dict(plan.bilateral_plan_gate),
        bilateral_proof_plan=dict(plan.bilateral_proof_plan),
    )


def stage_arena_patch(
    arena: RefactorArenaTransaction,
    *,
    task_id: str,
    owner: str,
    diff: str,
    affected_files: list[str],
    affected_symbols: list[str] | None = None,
    tests: list[str] | None = None,
    repo_root: str | Path = REPO_ROOT,
) -> PatchStageResult:
    """Stage one Builder patch only if it stays inside the task's arena boundary."""
    normalized_files = _normalized_path_list(affected_files)
    normalized_tests = _normalized_path_list(tests)
    normalized_symbols = [str(item) for item in affected_symbols or [] if str(item).strip()]
    owner_name = str(owner or "cheap_builder").strip() or "cheap_builder"
    task_name = str(task_id)
    diff_files = _diff_touched_files(diff)
    all_patch_files = _normalized_path_list([*normalized_files, *diff_files])
    findings: list[ShadowFinding] = []
    if arena.bilateral_contract:
        from aura_arena_gate_dialogue import _repository_identity
        from aura_relationship_contracts import BilateralPlanningContract

        contract = BilateralPlanningContract.from_dict(arena.bilateral_contract)
        identity = _repository_identity(Path(repo_root))
        if not contract.is_current(
            repository_head=str(identity["repository_head"]),
            source_tree_digest=str(identity["source_tree_digest"]),
            observed_at=time.time(),
        ):
            findings.append(
                ShadowFinding(
                    shadow_type="bilateral_confirmation_stale",
                    severity="blocker",
                    message="Patch lease no longer matches the current repository identity or confirmation time.",
                    task_id=task_name,
                )
            )
        allowed_paths = set(
            _normalized_path_list(
                arena.bilateral_contract.get("allowed_paths") or ()
            )
        )
        outside_confirmation = sorted(
            path for path in all_patch_files if path not in allowed_paths
        )
        if outside_confirmation:
            findings.append(
                ShadowFinding(
                    shadow_type="bilateral_scope_violation",
                    severity="blocker",
                    message=(
                        "Patch touches files outside the confirmed bilateral path lease: "
                        + ", ".join(outside_confirmation)
                    ),
                    task_id=task_name,
                )
            )
        expected_owner = str(
            arena.bilateral_proof_plan.get("temporary_agent_identity") or ""
        )
        if expected_owner and owner_name != expected_owner:
            findings.append(
                ShadowFinding(
                    shadow_type="bilateral_owner_mismatch",
                    severity="blocker",
                    message="Patch owner does not match the temporary Surgeon lease.",
                    task_id=task_name,
                )
            )
    capsule = _agent_capsule_for_task(arena, task_name)
    if capsule is None:
        findings.append(
            ShadowFinding(
                shadow_type="unassigned_patch_task",
                severity="blocker",
                message="Patch submission does not match an Act Capsule in this arena.",
                task_id=task_name,
            )
        )
    route_decision = _routing_decision_for_task(arena, task_name)
    if route_decision is not None and route_decision.get("route") != "BUILDER_PATCH":
        route = str(route_decision.get("route") or "BLOCKED_WITH_REASON")
        reason = str(route_decision.get("reason") or "missing_grounding")
        findings.append(
            ShadowFinding(
                shadow_type="arena_route_blocks_builder",
                severity="blocker",
                message=f"Aura Routing DSL selected {route}; Builder patch is not authorized until route reason is resolved: {reason}.",
                task_id=task_name,
                target_file=route_decision.get("target_file") or (capsule or {}).get("target_file"),
                target_symbol=route_decision.get("target_symbol") or (capsule or {}).get("target_symbol"),
            )
        )
    if not normalized_files:
        findings.append(
            ShadowFinding(
                shadow_type="missing_patch_files",
                severity="blocker",
                message="Patch submission must name at least one affected file.",
                task_id=task_name,
            )
        )
    if normalized_files and not diff_files:
        findings.append(
            ShadowFinding(
                shadow_type="unparseable_patch_diff",
                severity="blocker",
                message="Patch diff must include file headers that can be matched against affected_files.",
                task_id=task_name,
            )
        )
    undeclared_diff_files = sorted(file for file in diff_files if file not in normalized_files)
    if undeclared_diff_files:
        findings.append(
            ShadowFinding(
                shadow_type="undeclared_diff_file",
                severity="blocker",
                message=f"Patch diff touches files not declared in affected_files: {', '.join(undeclared_diff_files)}",
                task_id=task_name,
                target_file=undeclared_diff_files[0],
            )
        )
    declared_without_diff = sorted(file for file in normalized_files if file not in diff_files)
    if declared_without_diff and diff_files:
        findings.append(
            ShadowFinding(
                shadow_type="declared_file_missing_from_diff",
                severity="blocker",
                message=f"Patch affected_files includes paths absent from diff headers: {', '.join(declared_without_diff)}",
                task_id=task_name,
                target_file=declared_without_diff[0],
            )
        )
    arena_files = set(arena.affected_files)
    outside_arena = sorted(file for file in all_patch_files if file not in arena_files)
    if outside_arena:
        findings.append(
            ShadowFinding(
                shadow_type="cross_boundary_patch",
                severity="blocker",
                message=f"Patch touches files outside the Refactor Arena: {', '.join(outside_arena)}",
                task_id=task_name,
                target_file=outside_arena[0],
            )
        )
    allowed_files = _arena_files_for_task(arena, task_name)
    outside_task = sorted(file for file in all_patch_files if allowed_files and file not in allowed_files)
    if outside_task:
        findings.append(
            ShadowFinding(
                shadow_type="cross_task_boundary_patch",
                severity="blocker",
                message=f"Patch touches files outside the Act Capsule scope: {', '.join(outside_task)}",
                task_id=task_name,
                target_file=outside_task[0],
            )
        )
    leased_files = _lease_files_for_task(arena, task_name)
    outside_lease = sorted(file for file in all_patch_files if leased_files and file not in leased_files)
    if outside_lease:
        findings.append(
            ShadowFinding(
                shadow_type="lease_scope_violation",
                severity="blocker",
                message=f"Patch touches files outside the Action Capsule lease: {', '.join(outside_lease)}",
                task_id=task_name,
                target_file=outside_lease[0],
            )
        )
    if not str(diff or "").strip():
        findings.append(
            ShadowFinding(
                shadow_type="empty_patch",
                severity="blocker",
                message="Patch submission has no diff body.",
                task_id=task_name,
            )
        )

    if findings:
        return PatchStageResult(ok=False, arena=arena, patch=None, findings=findings)

    patch_payload = {
        "patch_version": ARENA_PATCH_VERSION,
        "plan_phase_hash": arena.plan_phase_hash,
        "task_id": task_name,
        "owner": owner_name,
        "diff": diff,
        "affected_files": normalized_files,
        "affected_symbols": normalized_symbols,
        "tests": normalized_tests,
        "status": "staged",
    }
    patch = ArenaPatch(
        patch_version=ARENA_PATCH_VERSION,
        patch_id=_hash_payload(patch_payload),
        task_id=task_name,
        owner=owner_name,
        diff=diff,
        affected_files=normalized_files,
        affected_symbols=normalized_symbols,
        tests=normalized_tests,
        status="staged",
        phase_hash=_hash_payload({**patch_payload, "patch_id": _hash_payload(patch_payload)}),
    )
    arena.shared_patch_queue.append(patch.to_dict())
    if isinstance(arena.liquid_arena, dict):
        arena.liquid_arena.setdefault("shared_action_queue", []).append(
            {
                "action_type": "patch_staged",
                "task_id": task_name,
                "owner": owner_name,
                "patch_id": patch.patch_id,
                "affected_files": normalized_files,
                "lease_files": sorted(_lease_files_for_task(arena, task_name)),
                "phase_hash": patch.phase_hash,
            }
        )
    arena.verification_ledger.append(
        {
            "stage": "patch_stage",
            "status": "staged",
            "task_id": task_name,
            "patch_id": patch.patch_id,
            "owner": owner_name,
            "affected_files": normalized_files,
            "tests": normalized_tests,
        }
    )
    return PatchStageResult(ok=True, arena=arena, patch=patch, findings=[])


def verify_refactor_arena(
    arena: RefactorArenaTransaction,
    *,
    repo_root: str | Path = REPO_ROOT,
    runner: Callable[[str], Any] | None = None,
) -> VerificationResult:
    """Verify staged arena patches before hot-swap authority is granted."""
    checks: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    def record(stage: str, status: str, **extra: Any) -> None:
        checks.append({"stage": stage, "status": status, **extra})

    def fail(stage: str, message: str, **extra: Any) -> None:
        failure = {"stage": stage, "status": "failed", "message": message, **extra}
        failures.append(failure)
        checks.append(failure)

    shadow_ok = bool(arena.shadow_report.get("ok"))
    if arena.ready_for_incubator and shadow_ok:
        record("arena_gate", "passed", plan_phase_hash=arena.plan_phase_hash)
    else:
        fail("arena_gate", "Arena is not ready for patch promotion.", shadow_gate=arena.shadow_report.get("gate"))
    if arena.bilateral_contract:
        gate = arena.bilateral_plan_gate
        if gate.get("passed") is True:
            record(
                "bilateral_plan_gate",
                "passed",
                confirmation_digest=arena.bilateral_contract.get("confirmation_digest"),
                gate_digest=gate.get("gate_digest"),
            )
        else:
            fail(
                "bilateral_plan_gate",
                "Bilateral plan gate is absent or failed.",
                failure_classes=list(gate.get("failure_classes") or ()),
            )

    if arena.shared_patch_queue:
        record("patch_queue", "passed", patch_count=len(arena.shared_patch_queue))
    else:
        fail("patch_queue", "No Builder patches have been staged in the arena.")

    known_tasks = {str(item.get("task_id")) for item in arena.agent_capsules}
    route_by_task = {
        str(item.get("task_id")): item
        for item in arena.routing_decisions
        if item.get("task_id") is not None
    }
    arena_files = set(arena.affected_files)
    lease_tasks = {str(item.get("capsule_id")) for item in arena.agent_leases}
    if arena.agent_leases:
        missing_leases = sorted(task for task in known_tasks if task not in lease_tasks)
        if missing_leases:
            fail("arena_lease", "Act Capsules are missing scoped Arena leases.", task_ids=missing_leases)
        else:
            record("arena_lease", "passed", lease_count=len(arena.agent_leases))
    file_locks: dict[str, tuple[str, str]] = {}
    all_tests: set[str] = set()
    passed_tests: set[str] = set()
    for item in arena.verification_ledger:
        if item.get("stage") == "tests":
            all_tests.update(_normalized_path_list(item.get("test_files", [])))

    for patch in arena.shared_patch_queue:
        patch_id = str(patch.get("patch_id") or "")
        task_id = str(patch.get("task_id") or "")
        owner = str(patch.get("owner") or "")
        patch_files = _normalized_path_list(patch.get("affected_files", []))
        diff_files = _diff_touched_files(str(patch.get("diff") or ""))
        all_patch_files = _normalized_path_list([*patch_files, *diff_files])
        all_tests.update(_normalized_path_list(patch.get("tests", [])))
        if patch.get("status") != "staged":
            fail("patch_status", "Patch is not in staged status.", patch_id=patch_id, status=patch.get("status"))
        if task_id not in known_tasks:
            fail("patch_task", "Patch task is not owned by an Act Capsule.", patch_id=patch_id, task_id=task_id)
        route_decision = route_by_task.get(task_id)
        if route_decision is not None and route_decision.get("route") != "BUILDER_PATCH":
            fail(
                "arena_route",
                "Routing decision does not authorize Builder patch.",
                patch_id=patch_id,
                task_id=task_id,
                route=route_decision.get("route"),
                reason=route_decision.get("reason"),
                symbol_output=route_decision.get("symbol_output"),
            )
        if not owner:
            fail("patch_owner", "Patch has no owner.", patch_id=patch_id, task_id=task_id)
        if not patch_files:
            fail("patch_files", "Patch has no affected files.", patch_id=patch_id, task_id=task_id)
        if patch_files and not diff_files:
            fail("patch_diff_files", "Patch diff has no parseable file headers.", patch_id=patch_id, task_id=task_id)
        undeclared_diff_files = sorted(file for file in diff_files if file not in patch_files)
        if undeclared_diff_files:
            fail(
                "patch_diff_files",
                "Patch diff touches files not declared in affected_files.",
                patch_id=patch_id,
                task_id=task_id,
                files=undeclared_diff_files,
            )
        declared_without_diff = sorted(file for file in patch_files if file not in diff_files)
        if declared_without_diff and diff_files:
            fail(
                "patch_diff_files",
                "Patch affected_files includes paths absent from diff headers.",
                patch_id=patch_id,
                task_id=task_id,
                files=declared_without_diff,
            )
        outside_arena = sorted(file for file in all_patch_files if file not in arena_files)
        if outside_arena:
            fail("patch_boundary", "Patch touches files outside the arena.", patch_id=patch_id, files=outside_arena)
        allowed_files = _arena_files_for_task(arena, task_id)
        outside_task = sorted(file for file in all_patch_files if allowed_files and file not in allowed_files)
        if outside_task:
            fail("patch_task_boundary", "Patch touches files outside its Act Capsule.", patch_id=patch_id, files=outside_task)
        lease_files = _lease_files_for_task(arena, task_id)
        outside_lease = sorted(file for file in all_patch_files if lease_files and file not in lease_files)
        if outside_lease:
            fail("patch_lease_boundary", "Patch touches files outside its Arena lease.", patch_id=patch_id, files=outside_lease)
        if not str(patch.get("diff") or "").strip():
            fail("patch_diff", "Patch has no diff body.", patch_id=patch_id, task_id=task_id)
        for file in all_patch_files:
            lock = file_locks.get(file)
            next_lock = (owner, task_id)
            if lock and lock != next_lock:
                fail(
                    "patch_conflict",
                    "Multiple owners/tasks staged patches for the same file.",
                    file=file,
                    first_owner=lock[0],
                    first_task=lock[1],
                    next_owner=owner,
                    next_task=task_id,
                )
            else:
                file_locks[file] = next_lock
        if patch_files:
            record("patch_scope", "passed", patch_id=patch_id, files=patch_files, diff_files=diff_files)

    root = Path(repo_root)
    for file in sorted(arena_files):
        target = (root / file).resolve()
        try:
            target.relative_to(root.resolve())
        except ValueError:
            fail("repo_boundary", "Arena affected file resolves outside repo_root.", file=file)
            continue
        if target.exists():
            record("repo_boundary", "passed", file=file)
        else:
            fail("repo_boundary", "Arena affected file is missing from the working tree.", file=file)

    if all_tests:
        if runner is None:
            fail("tests", "Verifier requires a test runner before hot-swap.", test_files=sorted(all_tests))
        else:
            for test_name in sorted(all_tests):
                try:
                    passed, details = _runner_status(runner(test_name))
                except Exception as exc:
                    fail("tests", "Verifier test runner raised.", test=test_name, details={"error": str(exc)})
                    continue
                if passed:
                    passed_tests.add(test_name)
                    record("tests", "passed", test=test_name, details=details)
                else:
                    fail("tests", "Verifier test failed.", test=test_name, details=details)
    else:
        record("tests", "passed", test_files=[])
    if arena.bilateral_contract:
        negative_coverage = arena.bilateral_proof_plan.get(
            "negative_requirement_coverage"
        )
        negative_requirements = list(
            arena.bilateral_contract.get("negative_requirements") or ()
        )
        trusted_verifiers = set(
            arena.bilateral_contract.get("required_verifiers") or ()
        )
        # Candidate-supplied ``verifier_receipts`` are untrusted proposal data
        # (the same origin as the plan itself) and must never establish
        # negative-requirement proof on their own, even when the verifier
        # name is admitted and the payload claims ``passed: true``. The only
        # canonical source of proof is ``passed_tests``, populated above from
        # the trusted ``runner`` callback actually executing each test file
        # against the current repository state as part of this verification
        # run. A receipt is only meaningful when it corresponds to one of
        # those independently-executed, independently-passed test names.
        missing_negative_proof: list[str] = []
        for requirement in negative_requirements:
            coverage = (
                negative_coverage.get(requirement)
                if isinstance(negative_coverage, Mapping)
                else None
            )
            verifier = (
                str(coverage.get("verifier") or "").strip()
                if isinstance(coverage, Mapping)
                else ""
            )
            if (
                not verifier
                or verifier not in trusted_verifiers
                or verifier not in passed_tests
            ):
                missing_negative_proof.append(str(requirement))
        if missing_negative_proof:
            fail(
                "bilateral_negative_proof",
                "Negative requirements remain without independent verifier proof.",
                requirements=missing_negative_proof,
            )
        else:
            record(
                "bilateral_negative_proof",
                "passed",
                requirement_count=len(negative_requirements),
                verifier_identity=list(
                    arena.bilateral_contract.get("required_verifiers") or ()
                ),
            )

    hotswap_ready = not failures and bool(arena.shared_patch_queue) and arena.ready_for_incubator
    phase_payload = {
        "verification_version": ARCHITECT_VERIFICATION_VERSION,
        "plan_phase_hash": arena.plan_phase_hash,
        "patch_ids": [patch.get("patch_id") for patch in arena.shared_patch_queue],
        "checks": checks,
        "failures": failures,
        "hotswap_ready": hotswap_ready,
    }
    return VerificationResult(
        verification_version=ARCHITECT_VERIFICATION_VERSION,
        ok=hotswap_ready,
        stage="verified" if hotswap_ready else "blocked",
        checks=checks,
        failures=failures,
        hotswap_ready=hotswap_ready,
        phase_hash=_hash_payload(phase_payload),
    )


def judge_refactor_arena(verification: VerificationResult) -> dict[str, Any]:
    """Return the deterministic Judge decision for a verified or blocked arena."""
    if verification.hotswap_ready:
        decision = "promote_hotswap"
    elif any(
        item.get("stage") in {"bilateral_plan_gate", "bilateral_negative_proof"}
        for item in verification.failures
    ):
        decision = "block_bilateral_contract"
    elif any(item.get("stage") in {"patch_boundary", "patch_task_boundary", "patch_conflict"} for item in verification.failures):
        decision = "escalate_to_judge"
    elif any(item.get("stage") == "tests" for item in verification.failures):
        decision = "repair_with_builder"
    elif any(item.get("stage") == "patch_queue" for item in verification.failures):
        decision = "wait_for_builder"
    else:
        decision = "block_transaction"
    return {
        "decision": decision,
        "verification_phase_hash": verification.phase_hash,
        "failure_count": len(verification.failures),
        "next_gate": "HOTSWAP" if decision == "promote_hotswap" else "REPAIR_OR_ESCALATE",
    }


def build_rollback_capsule(
    arena: RefactorArenaTransaction,
    *,
    repo_root: str | Path = REPO_ROOT,
) -> dict[str, Any]:
    """Capture a compact rollback capsule for every file in the arena."""
    root = Path(repo_root).resolve()
    file_snapshots = []
    for file in arena.affected_files:
        normalized = _normalize_path(file)
        target = (root / normalized).resolve() if normalized else root
        in_repo = False
        if normalized:
            try:
                target.relative_to(root)
                in_repo = True
            except ValueError:
                in_repo = False
        file_snapshots.append(
            {
                "path": normalized,
                "in_repo": in_repo,
                "exists": bool(in_repo and target.exists()),
                "digest": _file_digest(target) if in_repo else None,
            }
        )
    payload = {
        "rollback_version": ARCHITECT_ROLLBACK_VERSION,
        "plan_phase_hash": arena.plan_phase_hash,
        "files": file_snapshots,
        "rollback_hint": arena.rollback_hint,
    }
    return {**payload, "phase_hash": _hash_payload(payload)}


def build_hotswap_capsule(
    arena: RefactorArenaTransaction,
    verification: VerificationResult,
    *,
    repo_root: str | Path = REPO_ROOT,
) -> dict[str, Any]:
    """Build the promotion capsule only after Verifier grants hot-swap readiness."""
    rollback_capsule = build_rollback_capsule(arena, repo_root=repo_root)
    judge = judge_refactor_arena(verification)
    payload = {
        "hotswap_version": ARCHITECT_HOTSWAP_VERSION,
        "status": "ready" if verification.hotswap_ready else "blocked",
        "plan_phase_hash": arena.plan_phase_hash,
        "verification_phase_hash": verification.phase_hash,
        "judge": judge,
        "affected_files": list(arena.affected_files),
        "liquid_arena": {
            "arena_id": arena.liquid_arena.get("arena_id") if isinstance(arena.liquid_arena, dict) else None,
            "domain": arena.liquid_arena.get("domain") if isinstance(arena.liquid_arena, dict) else None,
            "phase_hash": arena.liquid_arena.get("phase_hash") if isinstance(arena.liquid_arena, dict) else None,
            "lease_count": len(arena.agent_leases),
            "boundary_contract_count": len(arena.boundary_contracts),
            "shared_action_count": len(arena.liquid_arena.get("shared_action_queue", [])) if isinstance(arena.liquid_arena, dict) else 0,
        },
        "patches": [
            {
                "patch_id": patch.get("patch_id"),
                "task_id": patch.get("task_id"),
                "owner": patch.get("owner"),
                "affected_files": patch.get("affected_files", []),
                "phase_hash": patch.get("phase_hash"),
            }
            for patch in arena.shared_patch_queue
        ],
        "rollback_capsule": rollback_capsule,
        "failures": verification.failures,
    }
    return {**payload, "phase_hash": _hash_payload(payload)}


def build_architect_ledger_record(
    prepared: ArchitectLoopResult,
    stage_results: list[PatchStageResult],
    verification: VerificationResult,
    hotswap_capsule: dict[str, Any],
) -> ArchitectLedgerRecord:
    """Build the append-only Architect ledger row for this transaction."""
    stage_summaries = [
        {
            "ok": result.ok,
            "patch_id": result.patch.patch_id if result.patch else None,
            "task_id": result.patch.task_id if result.patch else None,
            "findings": [finding.to_dict() for finding in result.findings],
        }
        for result in stage_results
    ]
    payload = {
        "ledger_version": ARCHITECT_LEDGER_VERSION,
        "event": "architect_transaction",
        "plan_phase_hash": prepared.plan.phase_hash,
        "intensity": prepared.intensity,
        "stage_results": stage_summaries,
        "verification": verification.to_dict(),
        "hotswap_capsule": hotswap_capsule,
    }
    return ArchitectLedgerRecord(
        ledger_version=ARCHITECT_LEDGER_VERSION,
        event="architect_transaction",
        plan_phase_hash=prepared.plan.phase_hash,
        intensity=prepared.intensity,
        stage_results=stage_summaries,
        verification=verification.to_dict(),
        hotswap_capsule=hotswap_capsule,
        phase_hash=_hash_payload(payload),
    )


def append_architect_ledger(
    record: ArchitectLedgerRecord | dict[str, Any],
    *,
    ledger_path: str | Path = ARCHITECT_LEDGER_PATH,
) -> Path:
    """Append one Architect transaction row to the local JSONL ledger."""
    path = Path(ledger_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = record.to_dict() if isinstance(record, ArchitectLedgerRecord) else dict(record)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, default=str))
        handle.write("\n")
    return path


def route_intensity(plan: FractalPlanCapsule, shadow_report: ShadowReport) -> int:
    """Choose a 0-5 orchestration intensity from local risk signals."""
    blocker_count = sum(1 for finding in shadow_report.findings if finding.severity == "blocker")
    warning_count = len(shadow_report.findings) - blocker_count
    max_size = max((ACT_SIZE_ORDER.get(act.size, 0) for act in plan.act_capsules), default=0)
    token_est = estimate_tokens(json.dumps(plan.to_dict(), sort_keys=True, default=str))
    if blocker_count >= 2 or max_size >= ACT_SIZE_ORDER["XL"]:
        return 4
    if blocker_count == 1 or max_size >= ACT_SIZE_ORDER["L"]:
        return 3
    if warning_count or max_size >= ACT_SIZE_ORDER["M"] or token_est > 3500:
        return 2
    if plan.act_capsules:
        return 1
    return 0


@dataclass(frozen=True)
class _TrustedBilateralHandoff:
    """Private, non-serializable carrier for an already-authorized bilateral handoff.

    This carrier is actively validated and enforced: ``_validate_trusted_bilateral_handoff``
    recomputes its binding digest against the live repository state and exact preparation
    context, and ``prepare()`` fails closed when bilateral artifacts are supplied without
    a genuine handoff. It is not registered, persisted, exported, or given a
    ``to_dict``/serializer of any kind—it exists only so a trusted caller can pass a
    single opaque, tamper-evident object instead of raw bilateral kwargs.
    """

    bilateral_contract: Any
    bilateral_plan_gate: Any
    bilateral_proof_plan: Any
    selected_plan_digest: str
    binding_digest: str


def _project_exact_act_tasks(act_tasks: list[str | dict[str, Any]]) -> tuple[Any, ...]:
    """Deterministically project act_tasks into an immutable, hashable form.

    Strings are kept as-is; mapping tasks are projected into sorted-key tuples so
    the projection is stable regardless of dict key ordering.
    """
    projected: list[Any] = []
    for task in act_tasks:
        if isinstance(task, Mapping):
            projected.append(tuple(sorted((str(k), task[k]) for k in task)))
        else:
            projected.append(task)
    return tuple(projected)


def _bind_trusted_bilateral_handoff(
    *,
    bilateral_contract: Mapping[str, Any] | Any | None,
    bilateral_plan_gate: Mapping[str, Any] | None,
    bilateral_proof_plan: Mapping[str, Any] | None,
    selected_plan_digest: str,
    objective: str,
    architecture_decision: str,
    act_tasks: list[str | dict[str, Any]],
    target_file: str | None,
    target_symbol: str | None,
    repository_head: str,
    source_tree_digest: str,
) -> str:
    """Compute a deterministic binding digest over the full authorized context."""
    contract_data = (
        bilateral_contract.to_dict()
        if hasattr(bilateral_contract, "to_dict")
        else dict(bilateral_contract or {})
    )
    gate_data = dict(bilateral_plan_gate or {})
    proof_data = dict(bilateral_proof_plan or {})
    binding_payload = {
        "bilateral_contract": contract_data,
        "bilateral_plan_gate": gate_data,
        "bilateral_proof_plan_digest": _hash_payload(proof_data),
        "objective": objective,
        "architecture_decision": architecture_decision,
        "act_tasks": _project_exact_act_tasks(act_tasks),
        "target_file": _normalize_path(target_file),
        "target_symbol": target_symbol,
        "repository_head": repository_head,
        "source_tree_digest": source_tree_digest,
        "selected_plan_digest": selected_plan_digest,
    }
    return _hash_payload(binding_payload)


def _mint_trusted_bilateral_handoff(
    *,
    bilateral_contract: Mapping[str, Any] | Any | None,
    bilateral_plan_gate: Mapping[str, Any] | None,
    bilateral_proof_plan: Mapping[str, Any] | None,
    selected_plan_digest: str,
    objective: str,
    architecture_decision: str,
    act_tasks: list[str | dict[str, Any]],
    target_file: str | None,
    target_symbol: str | None,
    repository_head: str,
    source_tree_digest: str,
) -> _TrustedBilateralHandoff:
    """Mint a `_TrustedBilateralHandoff` from already-authorized artifacts.

    This factory only computes a deterministic binding; it performs no
    authorization decisions itself and does not consult any external state.
    """
    binding_digest = _bind_trusted_bilateral_handoff(
        bilateral_contract=bilateral_contract,
        bilateral_plan_gate=bilateral_plan_gate,
        bilateral_proof_plan=bilateral_proof_plan,
        selected_plan_digest=selected_plan_digest,
        objective=objective,
        architecture_decision=architecture_decision,
        act_tasks=act_tasks,
        target_file=target_file,
        target_symbol=target_symbol,
        repository_head=repository_head,
        source_tree_digest=source_tree_digest,
    )
    return _TrustedBilateralHandoff(
        bilateral_contract=bilateral_contract,
        bilateral_plan_gate=bilateral_plan_gate,
        bilateral_proof_plan=bilateral_proof_plan,
        selected_plan_digest=selected_plan_digest,
        binding_digest=binding_digest,
    )


def _validate_trusted_bilateral_handoff(
    *,
    bilateral_contract: Mapping[str, Any] | Any | None,
    bilateral_plan_gate: Mapping[str, Any] | None,
    bilateral_proof_plan: Mapping[str, Any] | None,
    _trusted_bilateral_handoff: Any,
    objective: str,
    architecture_decision: str,
    act_tasks: list[str | dict[str, Any]],
    target_file: str | None,
    target_symbol: str | None,
    repo_root: Path,
) -> None:
    """Fail closed on any bilateral artifact unless it is bound to a genuine,
    already-authorized `_TrustedBilateralHandoff` recomputed against the live
    repository identity and the exact context being prepared.

    Raises ``ValueError`` on any missing, forged, stale, or mismatched
    handoff. Callers that supply no bilateral artifacts at all are unaffected
    (the non-bilateral path is preserved unchanged).
    """
    if bilateral_contract is None and bilateral_plan_gate is None and bilateral_proof_plan is None:
        return
    if not isinstance(_trusted_bilateral_handoff, _TrustedBilateralHandoff):
        raise ValueError(
            "bilateral artifacts were supplied without a genuine "
            "_TrustedBilateralHandoff; raw bilateral kwargs are never authority"
        )
    from aura_arena_gate_dialogue import _repository_identity

    try:
        identity = _repository_identity(repo_root)
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        raise ValueError(
            "repository identity unavailable for bilateral handoff"
        ) from exc
    expected_binding_digest = _bind_trusted_bilateral_handoff(
        bilateral_contract=_trusted_bilateral_handoff.bilateral_contract,
        bilateral_plan_gate=_trusted_bilateral_handoff.bilateral_plan_gate,
        bilateral_proof_plan=_trusted_bilateral_handoff.bilateral_proof_plan,
        selected_plan_digest=_trusted_bilateral_handoff.selected_plan_digest,
        objective=objective,
        architecture_decision=architecture_decision,
        act_tasks=act_tasks,
        target_file=target_file,
        target_symbol=target_symbol,
        repository_head=str(identity["repository_head"]),
        source_tree_digest=str(identity["source_tree_digest"]),
    )
    if expected_binding_digest != _trusted_bilateral_handoff.binding_digest:
        raise ValueError(
            "trusted bilateral handoff binding digest does not match the "
            "exact context, live repository identity, or selected-plan "
            "binding being prepared"
        )
    gate = dict(_trusted_bilateral_handoff.bilateral_plan_gate or {})
    if gate.get("passed") is not True:
        raise ValueError(
            "trusted bilateral handoff gate did not record passed=True"
        )
    for label, supplied, canonical in (
        ("bilateral_contract", bilateral_contract, _trusted_bilateral_handoff.bilateral_contract),
        ("bilateral_plan_gate", bilateral_plan_gate, _trusted_bilateral_handoff.bilateral_plan_gate),
        ("bilateral_proof_plan", bilateral_proof_plan, _trusted_bilateral_handoff.bilateral_proof_plan),
    ):
        if supplied is None:
            continue
        supplied_data = (
            supplied.to_dict() if hasattr(supplied, "to_dict") else dict(supplied)
        )
        canonical_data = (
            canonical.to_dict() if hasattr(canonical, "to_dict") else dict(canonical or {})
        )
        if _hash_payload(supplied_data) != _hash_payload(canonical_data):
            raise ValueError(
                f"raw {label} does not match the handoff-carried canonical value; "
                "raw bilateral kwargs may never override the trusted handoff"
            )


class ArchitectFusionLoop:
    """Plan/Act/Shadow/Arena coordinator for Architect-driven refactor work."""

    def __init__(self, *, repo_root: str | Path = REPO_ROOT):
        self.repo_root = Path(repo_root)

    def prepare(
        self,
        objective: str,
        *,
        architecture_decision: str,
        act_tasks: list[str | dict[str, Any]],
        target_file: str | None = None,
        target_symbol: str | None = None,
        acceptance_criteria: list[str] | None = None,
        rollback_conditions: list[str] | None = None,
        risk_map: list[str] | None = None,
        constraints: list[str] | None = None,
        escalation_rules: list[str] | None = None,
        context_pressure: float = 0.0,
        refresh_codemap: bool = True,
        bilateral_contract: Mapping[str, Any] | Any | None = None,
        bilateral_plan_gate: Mapping[str, Any] | None = None,
        bilateral_proof_plan: Mapping[str, Any] | None = None,
        _trusted_bilateral_handoff: Any = None,
    ) -> ArchitectLoopResult:
        _validate_trusted_bilateral_handoff(
            bilateral_contract=bilateral_contract,
            bilateral_plan_gate=bilateral_plan_gate,
            bilateral_proof_plan=bilateral_proof_plan,
            _trusted_bilateral_handoff=_trusted_bilateral_handoff,
            objective=objective,
            architecture_decision=architecture_decision,
            act_tasks=act_tasks,
            target_file=target_file,
            target_symbol=target_symbol,
            repo_root=self.repo_root,
        )
        bilateral_data = (
            bilateral_contract.to_dict()
            if hasattr(bilateral_contract, "to_dict")
            else dict(bilateral_contract or {})
        )
        plan = build_fractal_plan_capsule(
            objective,
            architecture_decision=architecture_decision,
            act_tasks=act_tasks,
            target_file=target_file,
            target_symbol=target_symbol,
            acceptance_criteria=acceptance_criteria,
            rollback_conditions=rollback_conditions,
            risk_map=risk_map,
            constraints=constraints,
            escalation_rules=escalation_rules,
            repo_root=self.repo_root,
            context_pressure=context_pressure,
            bilateral_contract=bilateral_data,
            bilateral_plan_gate=bilateral_plan_gate,
            bilateral_proof_plan=bilateral_proof_plan,
        )
        grounding = ground_plan_capsule(
            plan,
            repo_root=self.repo_root,
            refresh_codemap=refresh_codemap,
        )
        shadow_report = shadow_plan_capsule(plan, grounding)
        arena = build_refactor_arena(plan, grounding, shadow_report)
        return ArchitectLoopResult(
            plan=plan,
            grounding=grounding,
            shadow_report=shadow_report,
            arena=arena,
            intensity=route_intensity(plan, shadow_report),
        )

    def execute(
        self,
        objective: str,
        *,
        architecture_decision: str,
        act_tasks: list[str | dict[str, Any]],
        patch_submissions: list[dict[str, Any]] | None = None,
        target_file: str | None = None,
        target_symbol: str | None = None,
        acceptance_criteria: list[str] | None = None,
        rollback_conditions: list[str] | None = None,
        risk_map: list[str] | None = None,
        constraints: list[str] | None = None,
        escalation_rules: list[str] | None = None,
        context_pressure: float = 0.0,
        runner: Callable[[str], Any] | None = None,
        ledger_path: str | Path | None = None,
    ) -> ArchitectExecutionResult:
        """Run the complete Plan/Act/Ground/Shadow/Arena/Verify/Hot-swap/Ledger loop."""
        prepared = self.prepare(
            objective,
            architecture_decision=architecture_decision,
            act_tasks=act_tasks,
            target_file=target_file,
            target_symbol=target_symbol,
            acceptance_criteria=acceptance_criteria,
            rollback_conditions=rollback_conditions,
            risk_map=risk_map,
            constraints=constraints,
            escalation_rules=escalation_rules,
            context_pressure=context_pressure,
        )
        stage_results = []
        for submission in patch_submissions or []:
            stage_results.append(
                stage_arena_patch(
                    prepared.arena,
                    task_id=str(submission.get("task_id", "")),
                    owner=str(submission.get("owner", "cheap_builder")),
                    diff=str(submission.get("diff", "")),
                    affected_files=_normalized_path_list(submission.get("affected_files", [])),
                    affected_symbols=[str(item) for item in submission.get("affected_symbols", []) or []],
                    tests=_normalized_path_list(submission.get("tests", [])),
                )
            )
        verification = verify_refactor_arena(prepared.arena, repo_root=self.repo_root, runner=runner)
        hotswap_capsule = build_hotswap_capsule(prepared.arena, verification, repo_root=self.repo_root)
        ledger_record = build_architect_ledger_record(prepared, stage_results, verification, hotswap_capsule)
        if ledger_path is not None:
            append_architect_ledger(ledger_record, ledger_path=ledger_path)
        return ArchitectExecutionResult(
            prepared=prepared,
            stage_results=stage_results,
            verification=verification,
            hotswap_capsule=hotswap_capsule,
            ledger_record=ledger_record,
        )
