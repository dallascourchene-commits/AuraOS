"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa902-[Q-SYS:ARCHITECT_LOOP]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Grounded Refactor Orchestration)
DEPENDENCIES: dataclasses, hashlib, json, pathlib, typing, aura_fusion, aura_phase_capsule, aura_st3gg_recall, aura_substrate
FUNCTIONS: ActCapsule, FractalPlanCapsule, GroundingEvidence, ShadowFinding, ShadowReport, RefactorArenaTransaction, ArchitectLoopResult, build_fractal_plan_capsule, ground_plan_capsule, shadow_plan_capsule, build_refactor_arena, route_intensity, ArchitectFusionLoop
SYNOPSIS: Deterministic ArchitectFusionLoop substrate. Converts an architect intent into a sharded Plan Capsule, CODEMAP-grounded Act Capsules, Shadow findings, intensity routing, continuity handoff metadata, and a bounded refactor arena before any builder or incubator patch can run.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any

from aura_fusion import DEFAULT_CONSTRAINTS, build_task_capsule
from aura_phase_capsule import AuraPhaseCapsule, capture_phase_capsule
from aura_st3gg_recall import compile_st3gg_pointer, compile_visible_st3gg_capsule
from aura_substrate import REPO_ROOT, estimate_tokens


ARCHITECT_LOOP_VERSION = "AURA_ARCHITECT_LOOP_V1"
PLAN_CAPSULE_VERSION = "AURA_FRACTAL_PLAN_CAPSULE_V1"
ACT_CAPSULE_VERSION = "AURA_ACT_CAPSULE_V1"
SHADOW_REPORT_VERSION = "AURA_SHADOW_REPORT_V1"
REFACTOR_ARENA_VERSION = "AURA_REFACTOR_ARENA_V1"

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
    acceptance: str = "Return a bounded patch or a refusal reason."
    escalate_if: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    expected_output: str = "UNIFIED_DIFF"
    size: str = "S"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActCapsule":
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

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.continuity_capsule is not None:
            payload["continuity_capsule"] = self.continuity_capsule.to_dict()
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FractalPlanCapsule":
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _codemap_paths(codemap: dict[str, Any]) -> set[str]:
    coverage = codemap.get("coverage", {})
    paths = set()
    for item in coverage.get("all_included_paths_sorted", []) or []:
        normalized = _normalize_path(str(item))
        if normalized:
            paths.add(normalized)
    for card in codemap.get("file_cards", []) or []:
        normalized = _normalize_path(str(card.get("path", "")))
        if normalized:
            paths.add(normalized)
    return paths


def _file_card(codemap: dict[str, Any], target_file: str | None) -> dict[str, Any]:
    normalized = _normalize_path(target_file)
    if not normalized:
        return {}
    for card in codemap.get("file_cards", []) or []:
        if _normalize_path(str(card.get("path", ""))) == normalized:
            return card if isinstance(card, dict) else {}
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
        acceptance=str(task.get("acceptance", "Return a bounded patch or a refusal reason.")),
        escalate_if=list(task.get("escalate_if", DEFAULT_ACT_ESCALATIONS)),
        constraints=list(task.get("constraints", constraints)),
        expected_output=str(task.get("expected_output", "UNIFIED_DIFF")).upper(),
        size=size,
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
) -> FractalPlanCapsule:
    """Build a deterministic plan capsule that is pre-sharded into bounded Act Capsules."""
    plan_constraints = list(constraints or DEFAULT_CONSTRAINTS)
    act_capsules = [
        _build_act_capsule(objective, task, index=index, constraints=plan_constraints)
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
    )


def ground_plan_capsule(
    plan: FractalPlanCapsule,
    *,
    repo_root: str | Path = REPO_ROOT,
) -> list[GroundingEvidence]:
    """Map every Act Capsule to actual CODEMAP files, symbols, and nearby tests."""
    root = Path(repo_root)
    codemap = _load_codemap(root)
    codemap_paths = _codemap_paths(codemap)
    evidence = []
    for act in plan.act_capsules:
        target_file = _normalize_path(act.target_file)
        file_exists = bool(target_file and (root / target_file).exists())
        codemap_file_hit = bool(target_file and target_file in codemap_paths)
        symbol_hits = _symbol_hits(codemap, act.target_symbol, target_file)
        card = _file_card(codemap, target_file)
        topology = card.get("topology", {}) if isinstance(card, dict) else {}
        neighbor_files = [
            _normalize_path(item)
            for item in topology.get("neighbor_files", []) or []
            if _normalize_path(item)
        ]
        evidence.append(
            GroundingEvidence(
                task_id=act.task_id,
                target_file=target_file,
                target_symbol=act.target_symbol,
                file_exists=file_exists,
                codemap_file_hit=codemap_file_hit,
                symbol_exists=bool(symbol_hits) if act.target_symbol else True,
                codemap_symbol_hits=symbol_hits,
                test_files=_test_candidates(root, target_file),
                neighbor_files=neighbor_files,
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
    affected_files = sorted({
        evidence.target_file
        for evidence in grounding
        if evidence.target_file and evidence.file_exists
    })
    boundary_contracts = []
    for act in plan.act_capsules:
        evidence = by_task.get(act.task_id)
        boundary_contracts.append({
            "task_id": act.task_id,
            "target_file": act.target_file,
            "target_symbol": act.target_symbol,
            "upstream": "aura_fusion.build_task_capsule",
            "downstream": "aura_phase_capsule.capture_phase_capsule",
            "invariant": "preserve phase_hash, codemap_epoch, target_file, and target_symbol",
            "agent_scope": act.allowed_scope,
            "neighbor_files": evidence.neighbor_files if evidence else [],
        })
    ready = shadow_report.ok and all(item.file_exists for item in grounding if item.target_file)
    return RefactorArenaTransaction(
        arena_version=REFACTOR_ARENA_VERSION,
        plan_phase_hash=plan.phase_hash,
        affected_files=affected_files,
        boundary_contracts=boundary_contracts,
        agent_capsules=[act.to_dict() for act in plan.act_capsules],
        shared_patch_queue=[],
        conflict_resolver={
            "mode": "diff_owner_lock",
            "cross_boundary_edit": "escalate_to_shadow",
            "same_file_conflict": "judge_then_reground",
        },
        shadow_report=shadow_report.to_dict(),
        verification_ledger=[
            {"stage": "ground", "status": "passed" if all(item.file_exists for item in grounding if item.target_file) else "blocked"},
            {"stage": "shadow", "status": "passed" if shadow_report.ok else "blocked", "gate": shadow_report.gate},
            {"stage": "tests", "status": "pending", "test_files": sorted({name for item in grounding for name in item.test_files})},
            {"stage": "codemap_refresh", "status": "pending", "files_to_refresh": affected_files},
        ],
        ready_for_incubator=ready,
        rollback_hint="Keep patches staged in the arena until verifier passes; use the plan phase hash to discard the transaction.",
    )


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
    ) -> ArchitectLoopResult:
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
        )
        grounding = ground_plan_capsule(plan, repo_root=self.repo_root)
        shadow_report = shadow_plan_capsule(plan, grounding)
        arena = build_refactor_arena(plan, grounding, shadow_report)
        return ArchitectLoopResult(
            plan=plan,
            grounding=grounding,
            shadow_report=shadow_report,
            arena=arena,
            intensity=route_intensity(plan, shadow_report),
        )
