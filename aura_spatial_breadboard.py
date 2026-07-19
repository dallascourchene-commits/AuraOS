"""Proposal-only Coding Circuit for Aura's spatial substrate refactor.

This module applies the Coding Waboose breadboard pattern to implementation
planning: typed components, explicit evidence, forward consequences, backward
proof requirements, BC0-BC5 continuity, and Council V3 selective critic routing.
It never edits, commits, pushes, merges, grants a lease, or promotes a renderer.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any

from aura_architect_council_v2 import profile_refactor_length
from aura_architect_council_v3 import (
    ARCHITECT_COUNCIL_V3,
    select_critic_lanes,
)
from aura_event_contracts import stable_digest
from aura_planning_board import (
    ActionContinuityEvidence,
    ActionSpec,
    AuthorityRequirement,
    BoardContinuityLevel,
    ConstraintKind,
    ConstraintSpec,
    EffectSpec,
    GoalSpec,
    PlanningBoard,
    PortDirection,
    PortSpec,
    PredicateSpec,
    ResourceDemand,
    ReversibilityClass,
    VerifierReceiptEvidence,
    verify_board_continuity,
)
from aura_spatial_contracts import PATCH_AUTHORITY

SPATIAL_BREADBOARD_VERSION = "AURA_SPATIAL_BREADBOARD_V1"
SPATIAL_BREADBOARD_AUTHORITY = "proposal_only_spatial_refactor_circuit"


@dataclass(frozen=True)
class SpatialBreadboardComponent:
    component_id: str
    action_id: str
    name: str
    phase: str
    risk: str
    depends_on: tuple[str, ...]
    connected_input_refs: tuple[str, ...]
    output_refs: tuple[str, ...]
    verifier_ids: tuple[str, ...]
    energized: bool
    continuity: str
    status: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        for key in (
            "depends_on",
            "connected_input_refs",
            "output_refs",
            "verifier_ids",
        ):
            value[key] = list(value[key])
        return value


def build_spatial_refactor_plan() -> dict[str, Any]:
    """Return the bounded S0-S2 program used by Council V3 and the breadboard."""
    tasks = [
        _task(
            "S0_CONTRACTS",
            "Create representation-independent spatial contracts",
            "aura_spatial_contracts.py",
            size="L",
            related=["aura_event_contracts.py"],
            risk="authority_and_schema",
        ),
        _task(
            "S1_FRAMES",
            "Validate rooted coordinate-frame graphs and transforms",
            "aura_spatial_coordinate_frames.py",
            depends_on=["S0_CONTRACTS"],
            related=["aura_spatial_contracts.py"],
            risk="coordinate_integrity",
        ),
        _task(
            "S1_ASSETS",
            "Create content-addressed manifest-only asset registry",
            "aura_spatial_asset_registry.py",
            depends_on=["S0_CONTRACTS"],
            related=["aura_spatial_contracts.py"],
            risk="asset_integrity",
        ),
        _task(
            "S1_SCENE",
            "Compile and verify immutable spatial scene snapshots",
            "aura_spatial_scene.py",
            depends_on=["S1_FRAMES", "S1_ASSETS"],
            related=[
                "aura_spatial_contracts.py",
                "aura_spatial_coordinate_frames.py",
                "aura_spatial_asset_registry.py",
            ],
            risk="scene_consistency",
            size="L",
        ),
        _task(
            "S2_CODING_PROJECTION",
            "Adapt canonical Coding Arena micro-topology into spatial scenes",
            "aura_spatial_projection.py",
            depends_on=["S1_SCENE"],
            related=[
                "aura_coding_arena_3d.py",
                "aura_showcase_spatial.py",
            ],
            risk="duplicate_truth_owner",
        ),
        _task(
            "S2_INTERACTIONS",
            "Compile spatial UI actions into six-slot review-only intents",
            "aura_spatial_interaction.py",
            depends_on=["S1_SCENE"],
            related=["aura_fst_routing.py", "aura_forge.py"],
            risk="interaction_authority",
        ),
        _task(
            "S2_HOTSWAP_GUARD",
            ("Replace queued-success hotswap semantics with a Forge handoff guard"),
            "aura_topology_ws_bridge.py",
            depends_on=[
                "S2_INTERACTIONS",
                "S2_CODING_PROJECTION",
            ],
            related=["aura_spatial_interaction.py", "aura_forge.py"],
            risk="false_success_and_mutation",
        ),
        _task(
            "S2_BREADBOARD",
            "Compile the spatial refactor as a typed Coding Circuit",
            "aura_spatial_breadboard.py",
            depends_on=[
                "S0_CONTRACTS",
                "S1_SCENE",
                "S2_INTERACTIONS",
            ],
            related=[
                "aura_planning_board.py",
                "aura_coding_waboose_breadboard.py",
                "aura_architect_council_v3.py",
            ],
            risk="planning_continuity",
        ),
        _task(
            "S2_TESTS_DOCS",
            "Add adversarial tests, schema, and authority documentation",
            "tests/test_aura_spatial_substrate.py",
            depends_on=[
                "S1_FRAMES",
                "S1_ASSETS",
                "S1_SCENE",
                "S2_CODING_PROJECTION",
                "S2_INTERACTIONS",
                "S2_BREADBOARD",
            ],
            related=[
                "docs/AURA_SPATIAL_COMPUTING.md",
                "schemas/aura_spatial_scene.schema.json",
            ],
            risk="regression_and_claim_drift",
        ),
        _task(
            "S2_REGENERATE_MAPS",
            "Regenerate CODEMAP and topology after verified source changes",
            ".aura/CODEMAP.md",
            depends_on=[
                "S2_TESTS_DOCS",
                "S2_HOTSWAP_GUARD",
            ],
            related=[".aura/CODEMAP.json", "topology_map.json"],
            risk="generated_evidence_drift",
        ),
    ]
    return {
        "plan_id": "AURA_SPATIAL_S0_S2",
        "objective": (
            "Establish a representation-independent Aura Spatial Arena "
            "substrate without creating a second topology, truth owner, "
            "or mutation path."
        ),
        "act_tasks": tasks,
        "acceptance_criteria": [
            (
                "Scene, frame, asset, entity, link, and interaction records "
                "are deterministic and immutable at the contract boundary."
            ),
            ("Coding topology projection calls the existing select_micro_arena owner."),
            ("Every spatial entity and interaction has execution_authority=false and patch_authority=false."),
            (
                "Unknown frames, assets, entities, links, unsafe paths, "
                "digest mismatches, cycles, and non-finite transforms fail closed."
            ),
            ("Legacy HOTSWAP_REQUEST cannot emit queued success without a separate governed Forge contract."),
            ("Tests distinguish exact domain truth from derived or presentation-only spatial state."),
            (
                "No renderer, WebXR/OpenXR runtime, Gaussian-splat trainer, "
                "or device sensor becomes a canonical owner in S0-S2."
            ),
        ],
        "rollback_conditions": [
            ("Any new module duplicates CODEMAP or Coding Arena topology scanning."),
            ("Any spatial packet claims patch, execution, commit, push, merge, or promotion authority."),
            ("Scene digests are order-dependent or unstable across equivalent inputs."),
            ("Coordinate frames permit cycles, missing parents, non-finite values, or unrooted islands."),
            "Existing showcase or Coding Arena tests regress.",
            ("The WebSocket bridge continues reporting hotswap success without a governed handoff."),
        ],
        "risk_map": {
            "authority": "critical",
            "duplicate_truth": "critical",
            "coordinate_integrity": "high",
            "content_addressing": "high",
            "backward_compatibility": "high",
            "renderer_lock_in": "medium",
            "performance": "medium",
            "documentation_drift": "medium",
        },
        "constraints": [
            "ADDITIVE_FIRST",
            "NO_NEW_RUNTIME_DEPENDENCIES",
            "NO_SECOND_TOPOLOGY_SCANNER",
            "NO_RENDERER_AUTHORITY",
            "NO_VSA_PATCH_AUTHORITY",
            "NO_AUTOMATIC_MUTATION",
            "STOP_FOR_HUMAN_REVIEW",
        ],
        "escalation_rules": [
            ("Escalate to Council V3 when a canonical owner or authority boundary changes."),
            ("Escalate if more than the declared S0-S2 files require modification."),
            ("Escalate renderer or device integration into a separate S3 program."),
        ],
    }


def council_v3_route_spatial_plan() -> dict[str, Any]:
    """Replay Council V3's deterministic routing without claiming model calls occurred."""
    plan = build_spatial_refactor_plan()
    candidate = {
        "candidate_id": "spatial-s0-s2",
        "score": 0.0,
        "plan": plan,
    }
    profile = profile_refactor_length(plan)
    lanes = select_critic_lanes(candidate)
    return {
        "council_version": ARCHITECT_COUNCIL_V3,
        "routing_mode": "DETERMINISTIC_SELECTIVE_ROUTE_REPLAY",
        "native_model_calls_claimed": False,
        "selected_lanes": lanes,
        "skipped_lanes": [
            lane
            for lane in (
                "scope",
                "tests",
                "cost",
                "sequence",
                "continuity",
                "rollback",
            )
            if lane not in lanes
        ],
        "length_profile": profile.to_dict(),
        "lane_requirements": {
            "scope": [
                "new substrate remains projection-only",
                "no existing planning tools are refactored",
                "S0-S2 excludes renderer and device ownership",
            ],
            "tests": [
                ("contract, adversarial, determinism, and compatibility tests"),
                ("existing Coding Arena/showcase regressions remain green"),
            ],
            "sequence": [
                "contracts before validators",
                "validators before scene compiler",
                "scene compiler before adapters and interactions",
                "guard integration after interaction contract",
            ],
            "continuity": [
                "each task emits a bounded handoff artifact",
                ("all source and verifier references survive context boundaries"),
            ],
            "rollback": [
                "additive files can be reverted independently",
                ("bridge integration fails closed and is separately revertible"),
            ],
            "cost": [
                "stdlib-only core",
                "bounded node/link projections",
                "renderer and 3DGS work deferred to S3/S4",
            ],
        },
    }


def compile_spatial_breadboard(
    *,
    energized_component_ids: Sequence[str] = (),
    phase: str = "IMPLEMENTING_S0_S2",
) -> dict[str, Any]:
    plan = build_spatial_refactor_plan()
    route = council_v3_route_spatial_plan()
    energized = {str(item) for item in energized_component_ids}
    purpose_digest = stable_digest(
        {"plan": plan, "council_route": route},
        digest_size=32,
    )
    constraint_ref = "constraint:spatial-s0-s2:projection-only-no-mutation"
    tasks = [dict(item) for item in plan["act_tasks"]]
    action_by_component: dict[str, ActionSpec] = {}
    evidence_rows: list[ActionContinuityEvidence] = []
    components: list[SpatialBreadboardComponent] = []

    for task in tasks:
        component_id = str(task["task_id"])
        source_refs = tuple(
            dict.fromkeys(
                [
                    f"source:{task['target_file']}",
                    *[f"source:{path}" for path in task.get("related_files", [])],
                    *[f"component:{dependency}:output" for dependency in task.get("depends_on", [])],
                ]
            )
        )
        verifier_ids = (
            f"spatial:{component_id}:contract_check",
            f"spatial:{component_id}:authority_check",
        )
        action_id = "spatial-action:" + stable_digest(
            {"task": task, "purpose": purpose_digest},
            digest_size=12,
        )
        preconditions = [PredicateSpec("spatial.refactor.admitted", True)]
        preconditions.extend(
            PredicateSpec(
                f"spatial.component.{dependency}.complete",
                True,
            )
            for dependency in task.get("depends_on", [])
        )
        action = ActionSpec(
            action_id=action_id,
            name=str(task["description"]),
            domain="spatial_refactor",
            preconditions=tuple(preconditions),
            effects=(
                EffectSpec(
                    f"spatial.component.{component_id}.complete",
                    True,
                ),
                EffectSpec(
                    f"spatial.component.{component_id}.evidence_emitted",
                    True,
                ),
            ),
            input_ports=(
                PortSpec(
                    "source_evidence",
                    "AuraExactSourceRefV1",
                    PortDirection.INPUT,
                ),
                PortSpec(
                    "dependency_outputs",
                    "AuraSpatialComponentOutputListV1",
                    PortDirection.INPUT,
                ),
            ),
            output_ports=(
                PortSpec(
                    "component_output",
                    "AuraSpatialComponentOutputV1",
                    PortDirection.OUTPUT,
                ),
                PortSpec(
                    "verification_packet",
                    "AuraSpatialVerificationPacketV1",
                    PortDirection.OUTPUT,
                ),
            ),
            constraints=(
                ConstraintSpec(
                    constraint_id=("spatial-constraint:" + stable_digest(component_id, digest_size=12)),
                    kind=ConstraintKind.SAFETY,
                    description=(
                        "Spatial implementation may add and verify "
                        "projection contracts but cannot grant renderer, "
                        "interaction, patch, commit, merge, or promotion "
                        "authority."
                    ),
                    evidence_refs=(constraint_ref,),
                    blocking=True,
                ),
            ),
            required_capabilities=(
                "source.read_exact",
                "topology.query",
                "python.compile",
                "pytest.focused",
            ),
            verifier_ids=verifier_ids,
            authority_requirement=AuthorityRequirement.NONE,
            resource_demand=ResourceDemand(),
            reversibility=ReversibilityClass.REVERSIBLE,
            idempotency_key=f"spatial-s0-s2:{component_id}",
            evidence_refs=source_refs,
            proposal_only=True,
        )
        action_by_component[component_id] = action
        receipts: tuple[VerifierReceiptEvidence, ...] = ()
        if component_id in energized:
            receipts = tuple(
                VerifierReceiptEvidence(
                    verifier_id=verifier_id,
                    receipt_id=(
                        "receipt:"
                        + stable_digest(
                            {
                                "component": component_id,
                                "verifier": verifier_id,
                                "phase": phase,
                            },
                            digest_size=12,
                        )
                    ),
                )
                for verifier_id in verifier_ids
            )
        evidence_rows.append(
            ActionContinuityEvidence(
                action_id=action.action_id,
                constrained_evidence_refs=(constraint_ref,),
                grounded_evidence_refs=source_refs,
                authority_decision_ids=(("policy:spatial-s0-s2:proposal-only-no-execution-authority"),),
                verifier_receipts=receipts,
            )
        )

    goal = GoalSpec(
        goal_id=("spatial-goal:" + stable_digest(plan["objective"], digest_size=12)),
        objective=str(plan["objective"]),
        desired_state=(
            PredicateSpec(
                "spatial.s0_s2.review_packet_ready",
                True,
            ),
        ),
        constraints=(
            ConstraintSpec(
                constraint_id="spatial-goal-constraint:no-mutation",
                kind=ConstraintKind.SAFETY,
                description=("Planning and spatial projections cannot mutate or promote production state."),
                evidence_refs=(constraint_ref,),
                blocking=True,
            ),
        ),
        evidence_refs=("plan:AURA_SPATIAL_S0_S2",),
    )
    board = PlanningBoard(
        board_id=(
            "spatial-board:"
            + stable_digest(
                [task["task_id"] for task in tasks],
                digest_size=12,
            )
        ),
        arena_id="spatial_arena_refactor",
        purpose_digest=purpose_digest,
        goal=goal,
        actions=tuple(action_by_component[str(task["task_id"])] for task in tasks),
        current_state_refs=(
            "git-head:f302811ec4c84f194f232e6f475cbd0e64bf94c8",
            "branch:feature/aura-spatial-s0-s2",
            "plan:AURA_SPATIAL_S0_S2",
        ),
    )
    continuity = verify_board_continuity(
        board,
        evidence=tuple(evidence_rows),
    )
    findings_by_action: dict[str, list[dict[str, Any]]] = {}
    for finding in continuity.findings:
        findings_by_action.setdefault(finding.subject_id, []).append(finding.to_dict())

    for task in tasks:
        component_id = str(task["task_id"])
        action = action_by_component[component_id]
        is_energized = component_id in energized
        blocking = findings_by_action.get(action.action_id, [])
        if is_energized and not blocking:
            status = "VERIFIED_SPATIAL_COMPONENT"
            level = BoardContinuityLevel.BC5_VERIFIED.value
        else:
            status = "CONNECTED_GROUNDED_UNPOWERED"
            level = BoardContinuityLevel.BC4_AUTHORIZED.value
        components.append(
            SpatialBreadboardComponent(
                component_id=component_id,
                action_id=action.action_id,
                name=str(task["description"]),
                phase=component_id.split("_", 1)[0],
                risk=str(task.get("risk") or "correctness"),
                depends_on=tuple(task.get("depends_on", [])),
                connected_input_refs=action.evidence_refs,
                output_refs=(
                    f"component:{component_id}:output",
                    f"component:{component_id}:verification_packet",
                ),
                verifier_ids=action.verifier_ids,
                energized=is_energized,
                continuity=level,
                status=status,
            )
        )

    all_energized = all(item.energized for item in components)
    any_energized = any(item.energized for item in components)
    if all_energized and continuity.continuity_complete:
        circuit_status = "VERIFIED_SPATIAL_S0_S2_CIRCUIT"
    elif any_energized:
        circuit_status = "PARTIALLY_ENERGIZED_SPATIAL_S0_S2_CIRCUIT"
    else:
        circuit_status = "GROUNDED_SPATIAL_S0_S2_CIRCUIT_UNPOWERED"

    return {
        "ok": True,
        "version": SPATIAL_BREADBOARD_VERSION,
        "phase": str(phase),
        "plan": plan,
        "council_v3_route": route,
        "circuit_status": circuit_status,
        "board": board.to_dict(),
        "board_digest": board.digest,
        "continuity": continuity.to_dict(),
        "components": [item.to_dict() for item in components],
        "forward_simulation": [
            {
                "component_id": item.component_id,
                "path": [
                    *item.connected_input_refs,
                    f"action:{item.action_id}",
                    *item.output_refs,
                    f"decision:{item.component_id}:verify_or_rollback",
                ],
            }
            for item in components
        ],
        "backward_proof_requirements": [
            {
                "component_id": item.component_id,
                "required_for_completion": [
                    "exact_source_anchor",
                    "declared_dependency_outputs",
                    "contract_check_receipt",
                    "authority_check_receipt",
                    "focused_test_evidence",
                    "human_review_decision",
                ],
            }
            for item in components
        ],
        "deferred_explicit_mocks": [
            {
                "mock_id": "mock:renderer:webxr_or_openxr_adapter",
                "reason": ("renderer selection is deferred to S3 and cannot block S0-S2 contracts"),
                "grounded": False,
                "authority": False,
            },
            {
                "mock_id": "mock:asset:gaussian_splat_runtime",
                "reason": ("3DGS import/render is deferred to S4; no training or runtime is claimed"),
                "grounded": False,
                "authority": False,
            },
            {
                "mock_id": ("mock:device:anchors_gaze_gesture_sensors"),
                "reason": ("device signals remain future adapters and never authority"),
                "grounded": False,
                "authority": False,
            },
        ],
        "authority": {
            "class": SPATIAL_BREADBOARD_AUTHORITY,
            "planning_proposes": True,
            "verification_proves": True,
            "human_authorizes": True,
            "execution_authority": False,
            "patch_authority": PATCH_AUTHORITY,
            "renderer_authority": False,
            "vsa_patch_authority": False,
            "automatic_fix": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_pull_request": False,
            "automatic_merge": False,
        },
    }


def build_spatial_s3a_plan() -> dict[str, Any]:
    """Return the bounded renderer-independent S3-A continuation circuit."""

    tasks = [
        _task(
            "S3A_RENDER_CONTRACTS",
            "Add immutable device, render-plan, receipt, and session contracts",
            "aura_spatial_contracts.py",
            related=[
                "schemas/aura_spatial_device_profile.schema.json",
                "schemas/aura_spatial_render_plan.schema.json",
                "schemas/aura_spatial_render_receipt.schema.json",
            ],
            risk="schema_runtime_parity",
            size="L",
        ),
        _task(
            "S3A_NEGOTIATION",
            "Negotiate deterministic renderer fallbacks and bounded budgets",
            "aura_spatial_render_plan.py",
            depends_on=["S3A_RENDER_CONTRACTS"],
            related=["tests/test_aura_spatial_render_plan.py"],
            risk="renderer_lock_in_and_budget_bypass",
            size="L",
        ),
        _task(
            "S3A_SESSION",
            "Bind ephemeral projection sessions to exact scene and plan digests",
            "aura_spatial_session.py",
            depends_on=["S3A_RENDER_CONTRACTS", "S3A_NEGOTIATION"],
            related=[
                "aura_spatial_receipts.py",
                "tests/test_aura_spatial_session.py",
            ],
            risk="stale_scene_or_resource_leak",
            size="L",
        ),
        _task(
            "S3A_SERVER",
            "Expose bounded no-store scene, plan, session, interaction, and dissolve APIs",
            "aura_spatial_server.py",
            depends_on=["S3A_SESSION"],
            related=["tests/test_aura_spatial_server.py"],
            risk="transport_trust_boundary",
            size="L",
        ),
        _task(
            "S3A_HARNESS",
            "Run Architect, Agent Bridge, Council V3, Surgeon, Connectome, Emergent, Waboose, and Crucible gates",
            "scripts/aura_spatial_continuation_architect_harness.py",
            depends_on=[
                "S3A_RENDER_CONTRACTS",
                "S3A_NEGOTIATION",
                "S3A_SESSION",
                "S3A_SERVER",
            ],
            related=[
                ".github/workflows/aura-spatial-s3a.yml",
                "docs/AURA_SPATIAL_COMPUTING.md",
            ],
            risk="evidence_claim_drift",
            size="M",
        ),
    ]
    return {
        "plan_id": "AURA_SPATIAL_S3A",
        "objective": (
            "Establish renderer-independent render plans and ephemeral projection "
            "sessions without implementing a browser renderer or expanding authority."
        ),
        "act_tasks": tasks,
        "acceptance_criteria": [
            "Every plan binds exact scene and device digests.",
            "ACCESSIBLE_2D remains a mandatory fallback.",
            "WEBXR selection requires explicit request and observed user activation.",
            "Scene, asset, CPU, GPU, and network budgets fail closed.",
            "Sessions are ephemeral, cancellable, digest-bound, and dissolved with receipts.",
            "Server responses use no-store, restrictive CSP, and bounded bodies.",
            "Renderer, execution, patch, merge, promotion, and production authority remain false.",
        ],
        "rollback_conditions": [
            "Any renderer implementation enters S3-A.",
            "Any session survives dissolution or retains raw sensor data.",
            "Schema and runtime acceptance boundaries diverge.",
            "Any fallback can omit accessible 2D presentation.",
            "Any device or renderer packet gains authority.",
        ],
        "risk_map": {
            "authority": "critical",
            "transport": "high",
            "budget_bypass": "high",
            "stale_digest": "high",
            "resource_cleanup": "high",
            "schema_runtime_parity": "high",
            "accessibility": "high",
        },
        "constraints": [
            "NO_RENDERER_IMPLEMENTATION",
            "NO_NEW_RUNTIME_DEPENDENCIES",
            "ACCESSIBLE_2D_REQUIRED",
            "XR_EXPLICIT_USER_ACTIVATION",
            "NO_RAW_SENSOR_RETENTION",
            "NO_AUTOMATIC_MUTATION",
            "STOP_FOR_HUMAN_REVIEW",
        ],
    }


def council_v3_route_spatial_s3a_plan() -> dict[str, Any]:
    plan = build_spatial_s3a_plan()
    candidate = {
        "candidate_id": "spatial-s3a",
        "score": 0.0,
        "plan": plan,
    }
    lanes = select_critic_lanes(candidate)
    return {
        "council_version": ARCHITECT_COUNCIL_V3,
        "routing_mode": "DETERMINISTIC_SELECTIVE_ROUTE_REPLAY",
        "native_model_calls_claimed": False,
        "selected_lanes": lanes,
        "length_profile": profile_refactor_length(plan).to_dict(),
        "supplemental_rubrics": [
            "security_and_authority",
            "protocol_and_interchange",
            "performance_and_accessibility",
            "review_evidence_freshness",
        ],
    }


def compile_spatial_s3a_breadboard() -> dict[str, Any]:
    """Compile a proposal-only S3-A circuit without claiming verifier power."""

    plan = build_spatial_s3a_plan()
    route = council_v3_route_spatial_s3a_plan()
    components = []
    for task in plan["act_tasks"]:
        task_id = str(task["task_id"])
        action_id = "spatial-s3a-action:" + stable_digest(task, digest_size=12)
        components.append(
            SpatialBreadboardComponent(
                component_id=task_id,
                action_id=action_id,
                name=str(task["description"]),
                phase="S3A",
                risk=str(task["risk"]),
                depends_on=tuple(task["depends_on"]),
                connected_input_refs=tuple(
                    [f"source:{task['target_file']}"]
                    + [f"source:{item}" for item in task["related_files"]]
                    + [f"component:{item}:output" for item in task["depends_on"]]
                ),
                output_refs=(
                    f"component:{task_id}:output",
                    f"component:{task_id}:verification_packet",
                ),
                verifier_ids=(
                    f"spatial-s3a:{task_id}:contract",
                    f"spatial-s3a:{task_id}:authority",
                    f"spatial-s3a:{task_id}:regression",
                ),
                energized=False,
                continuity=BoardContinuityLevel.BC4_AUTHORIZED.value,
                status="CONNECTED_GROUNDED_UNPOWERED",
            ).to_dict()
        )
    return {
        "ok": True,
        "version": SPATIAL_BREADBOARD_VERSION,
        "plan": plan,
        "council_v3_route": route,
        "circuit_status": "GROUNDED_SPATIAL_S3A_CIRCUIT_UNPOWERED",
        "components": components,
        "backward_proof_requirements": [
            {
                "component_id": item["component_id"],
                "required_for_completion": [
                    "exact_head_binding",
                    "contract_and_schema_receipts",
                    "authority_tamper_regressions",
                    "focused_test_evidence",
                    "waboose_and_crucible_receipt",
                    "codex_review_clear",
                    "human_review_decision",
                ],
            }
            for item in components
        ],
        "authority": {
            "class": SPATIAL_BREADBOARD_AUTHORITY,
            "execution_authority": False,
            "patch_authority": PATCH_AUTHORITY,
            "renderer_authority": False,
            "vsa_patch_authority": False,
            "automatic_fix": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_pull_request": False,
            "automatic_merge": False,
            "human_review_required": True,
        },
    }


def build_spatial_s3b_s4a_plan() -> dict[str, Any]:
    """Return the bounded S3-B browser and S4-A interchange program."""

    tasks = [
        _task(
            "S3B_ADAPTER_INTERFACE",
            "Define replaceable renderer and headless adapter contracts",
            "aura_spatial_web/renderer_adapter.js",
            related=["aura_spatial_web/headless_renderer.js"],
            risk="renderer_becomes_owner",
        ),
        _task(
            "S3B_ACCESSIBLE",
            "Provide keyboard-first accessible scene parity",
            "aura_spatial_web/accessibility.js",
            depends_on=["S3B_ADAPTER_INTERFACE"],
            related=["aura_spatial_web/index.html", "aura_spatial_web/styles.css"],
            risk="accessibility_regression",
            size="L",
        ),
        _task(
            "S3B_WEBGL2",
            "Render bounded topology primitives with deterministic cleanup",
            "aura_spatial_web/webgl2_renderer.js",
            depends_on=["S3B_ADAPTER_INTERFACE", "S3B_ACCESSIBLE"],
            related=["aura_spatial_web/scene_decoder.js"],
            risk="gpu_resource_and_input_correctness",
            size="XL",
        ),
        _task(
            "S3B_WEBGPU",
            "Run WebGPU as a non-promoted shadow adapter",
            "aura_spatial_web/webgpu_renderer.js",
            depends_on=["S3B_WEBGL2"],
            risk="capability_and_device_loss",
            size="L",
        ),
        _task(
            "S3B_WEBXR",
            "Expose capability-only WebXR behind explicit user activation",
            "aura_spatial_web/webxr_session.js",
            depends_on=["S3B_WEBGL2", "S3B_ACCESSIBLE"],
            related=["aura_spatial_web/app.js"],
            risk="consent_and_activation",
            size="L",
        ),
        _task(
            "S3B_INTERACTION",
            "Compile browser inputs into retained six-slot review-only intents",
            "aura_spatial_web/interaction_adapter.js",
            depends_on=["S3B_WEBGL2", "S3B_WEBXR"],
            related=["aura_spatial_interaction.py"],
            risk="interaction_authority",
            size="L",
        ),
        _task(
            "S3B_TELEMETRY",
            "Bind evidence-classified browser telemetry to exact digests",
            "aura_spatial_web/telemetry.js",
            depends_on=["S3B_WEBGPU", "S3B_INTERACTION"],
            related=["aura_spatial_receipts.py"],
            risk="unsupported_performance_claims",
        ),
        _task(
            "S4_IMPORT_CONTRACTS",
            "Define strict provenance and coordinate-conversion import receipts",
            "aura_spatial_importers/contracts.py",
            depends_on=["S3B_TELEMETRY"],
            related=["schemas/aura_spatial_import_receipt.schema.json"],
            risk="interchange_truth_and_provenance",
            size="L",
        ),
        _task(
            "S4_GLTF",
            "Import bounded local glTF/GLB meshes without executable or network paths",
            "aura_spatial_importers/gltf.py",
            depends_on=["S4_IMPORT_CONTRACTS"],
            related=["aura_spatial_coordinate_frames.py"],
            risk="binary_parser_and_coordinate_integrity",
            size="XL",
        ),
        _task(
            "S4_PLY",
            "Import local-only bounded PLY point clouds with explicit basis",
            "aura_spatial_importers/ply.py",
            depends_on=["S4_IMPORT_CONTRACTS"],
            related=["aura_spatial_coordinate_frames.py"],
            risk="allocation_and_malformed_input",
            size="L",
        ),
        _task(
            "S3B_S4A_REVIEW",
            "Run exact-head Python, Node, Waboose, Crucible, Codex, and CodeRabbit gates",
            ".github/workflows/aura-spatial-s3-s4a.yml",
            depends_on=["S4_GLTF", "S4_PLY"],
            related=["docs/AURA_SPATIAL_COMPUTING.md"],
            risk="review_and_claim_drift",
        ),
    ]
    return {
        "plan_id": "AURA_SPATIAL_S3B_S4A",
        "objective": (
            "Deliver an accessible replaceable browser projection and bounded "
            "standards-based local interchange without granting renderer, importer, "
            "provenance, execution, or patch authority."
        ),
        "act_tasks": tasks,
        "acceptance_criteria": [
            "Accessible 2D, WebGL2, and headless paths inspect the same exact scene.",
            "WebGPU remains shadow-only until separate parity evidence exists.",
            "WebXR requires explicit observed user activation and retains no raw sensor data.",
            "Browser inputs compile into the retained six-slot review-only intent owner.",
            "Telemetry labels metrics measured, calculated, estimated, or unavailable.",
            "glTF/GLB and PLY enforce byte, count, allocation, basis, and provenance bounds.",
            "No remote URI, script, shader, training, or automatic mutation path is admitted.",
        ],
        "rollback_conditions": [
            "Any browser adapter becomes a scene or domain truth owner.",
            "Any renderer or importer gains execution or patch authority.",
            "Accessible parity is omitted by a renderer path.",
            "WebGPU is promoted without separate parity and device-loss evidence.",
            "An importer performs network fetch or executes embedded content.",
            "Coordinate basis or units are inferred where the format does not define them.",
        ],
        "risk_map": {
            "authority": "critical",
            "untrusted_binary_input": "critical",
            "coordinate_integrity": "high",
            "gpu_cleanup": "high",
            "accessibility": "high",
            "consent": "high",
            "performance_claims": "medium",
        },
        "constraints": [
            "NO_NEW_RUNTIME_DEPENDENCIES",
            "ACCESSIBLE_2D_REQUIRED",
            "WEBGPU_SHADOW_ONLY",
            "WEBXR_EXPLICIT_USER_ACTIVATION",
            "LOCAL_ASSET_BYTES_ONLY",
            "NO_EXECUTABLE_ASSET_CONTENT",
            "NO_AUTOMATIC_MUTATION",
            "STOP_FOR_HUMAN_REVIEW",
        ],
    }


def council_v3_route_spatial_s3b_s4a_plan() -> dict[str, Any]:
    plan = build_spatial_s3b_s4a_plan()
    candidate = {"candidate_id": "spatial-s3b-s4a", "score": 0.0, "plan": plan}
    return {
        "council_version": ARCHITECT_COUNCIL_V3,
        "routing_mode": "DETERMINISTIC_SELECTIVE_ROUTE_REPLAY",
        "native_model_calls_claimed": False,
        "selected_lanes": select_critic_lanes(candidate),
        "length_profile": profile_refactor_length(plan).to_dict(),
        "supplemental_rubrics": [
            "security_and_authority",
            "privacy_and_cultural_governance",
            "protocol_and_interchange",
            "performance_and_accessibility",
            "review_evidence_freshness",
        ],
    }


def compile_spatial_s3b_s4a_breadboard() -> dict[str, Any]:
    """Compile the S3-B/S4-A circuit as grounded, unpowered review evidence."""

    plan = build_spatial_s3b_s4a_plan()
    route = council_v3_route_spatial_s3b_s4a_plan()
    components = []
    for task in plan["act_tasks"]:
        task_id = str(task["task_id"])
        components.append(
            SpatialBreadboardComponent(
                component_id=task_id,
                action_id="spatial-s3b-s4a-action:" + stable_digest(task, digest_size=12),
                name=str(task["description"]),
                phase="S3B_S4A",
                risk=str(task["risk"]),
                depends_on=tuple(task["depends_on"]),
                connected_input_refs=tuple(
                    [f"source:{task['target_file']}"]
                    + [f"source:{item}" for item in task["related_files"]]
                    + [f"component:{item}:output" for item in task["depends_on"]]
                ),
                output_refs=(
                    f"component:{task_id}:output",
                    f"component:{task_id}:verification_packet",
                ),
                verifier_ids=(
                    f"spatial-s3b-s4a:{task_id}:contract",
                    f"spatial-s3b-s4a:{task_id}:authority",
                    f"spatial-s3b-s4a:{task_id}:regression",
                ),
                energized=False,
                continuity=BoardContinuityLevel.BC4_AUTHORIZED.value,
                status="CONNECTED_GROUNDED_UNPOWERED",
            ).to_dict()
        )
    return {
        "ok": True,
        "version": SPATIAL_BREADBOARD_VERSION,
        "plan": plan,
        "council_v3_route": route,
        "circuit_status": "GROUNDED_SPATIAL_S3B_S4A_CIRCUIT_UNPOWERED",
        "components": components,
        "authority": {
            "class": SPATIAL_BREADBOARD_AUTHORITY,
            "execution_authority": False,
            "patch_authority": PATCH_AUTHORITY,
            "renderer_authority": False,
            "importer_authority": False,
            "provenance_authority": False,
            "vsa_patch_authority": False,
            "automatic_fix": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_pull_request": False,
            "automatic_merge": False,
            "human_review_required": True,
        },
    }


def _task(
    task_id: str,
    description: str,
    target_file: str,
    *,
    depends_on: list[str] | None = None,
    related: list[str] | None = None,
    risk: str,
    size: str = "M",
) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "description": description,
        "target_file": target_file,
        "related_files": related or [],
        "depends_on": depends_on or [],
        "risk": risk,
        "size": size,
        "output_mode": "PATCH",
        "proposal_only": True,
    }


__all__ = [
    "SPATIAL_BREADBOARD_AUTHORITY",
    "SPATIAL_BREADBOARD_VERSION",
    "SpatialBreadboardComponent",
    "build_spatial_refactor_plan",
    "build_spatial_s3a_plan",
    "build_spatial_s3b_s4a_plan",
    "compile_spatial_breadboard",
    "compile_spatial_s3a_breadboard",
    "compile_spatial_s3b_s4a_breadboard",
    "council_v3_route_spatial_plan",
    "council_v3_route_spatial_s3a_plan",
    "council_v3_route_spatial_s3b_s4a_plan",
]
