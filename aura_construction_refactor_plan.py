"""Reuse-first SCO Construction Arena refactor planning adapter.

This module implements only the governed refactor-control foundation. It does
not implement or control physical construction activity.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from aura_refactor_skeleton import (
    IntegrationDisposition,
    PATCH_AUTHORITY,
    RefactorSkeleton,
    RefactorSkeletonNode,
)

CONSTRUCTION_REFACTOR_PLAN_VERSION = "AURA_SCO_CONSTRUCTION_REFACTOR_PLAN_V1"
VSA_PATCH_AUTHORITY = False
DOMAIN = "sco_construction_refactor"

REQUIRED_STRUCTURES = (
    "Human Agent Arena",
    "Coding Arena",
    "Agent Arena Bridge",
    "Liquid Planning Arena",
    "Civic/project structures",
    "Capability Connectome/Resolver",
    "Router/Cognome",
    "Observatory",
    "Experience Ledger",
    "Crucible",
)
FORBIDDEN_CONSTRUCTION_AUTHORITY = (
    "authorize physical work",
    "certify safety or engineering",
    "release payment or transfer funds",
    "control physical access",
    "operate equipment",
    "discipline workers",
    "treat sensor or location data as proof",
    "replace professional contractual legal or regulatory authority",
)


@dataclass(frozen=True)
class CapabilityRequirement:
    capability_id: str
    objective: str
    candidate_files: tuple[str, ...]
    candidate_symbols: tuple[str, ...]
    expected_owner: str
    reuse_decision: str
    integration_reason: str


CAPABILITY_REQUIREMENTS = (
    CapabilityRequirement(
        "construction_event_evidence_contracts",
        "Reuse Aura's canonical event, decision, evidence, privacy, and authority "
        "contracts for a construction domain adapter.",
        ("aura_event_contracts.py", "aura_civic_planning_types.py"),
        ("ActorType", "DIKWPStage", "MeasurementClass"),
        "aura_event_contracts.py plus domain contracts after exact gap proof",
        "EXTEND_CANONICAL_OWNER",
        "Construction records must reuse canonical event/evidence semantics.",
    ),
    CapabilityRequirement(
        "bounded_capsules_contracts_leases",
        "Reuse ActionCapsule, BoundaryContract, ArenaLease, WorldStateDelta, and "
        "BaseArenaAdapter for construction planning.",
        ("aura_liquid_planning_arena.py",),
        (
            "ActionCapsule",
            "BoundaryContract",
            "ArenaLease",
            "WorldStateDelta",
            "BaseArenaAdapter",
        ),
        "aura_liquid_planning_arena.py",
        "ADD_NARROW_ADAPTER",
        "Construction is a domain adapter, not a parallel planner.",
    ),
    CapabilityRequirement(
        "capability_reuse_resolution",
        "Resolve construction capabilities through Connectome, Resolver, CODEMAP, "
        "topology, tests, and affordances before invention.",
        (
            "aura_capability_connectome.py",
            "aura_capability_resolver.py",
            "aura_capability_resolver_v2.py",
        ),
        (
            "build_capability_connectome",
            "find_capability_path",
            "resolve_capabilities",
        ),
        "aura_capability_resolver_v2.py",
        "REUSE",
        "Mandatory reuse-before-invention gate.",
    ),
    CapabilityRequirement(
        "emergent_refactor_evidence",
        "Preserve construction reports, findings, research, and strict evidence "
        "packets in the Human Agent Emergent workspace.",
        ("aura_emergent_refactor_workspace.py",),
        ("EmergentResultsStore", "search_findings", "build_refactor_packet"),
        "aura_emergent_refactor_workspace.py",
        "EXTEND_CANONICAL_OWNER",
        "Do not create a second evidence store.",
    ),
    CapabilityRequirement(
        "revisioned_refactor_skeleton",
        "Persist a human-editable, digest-bound, revisioned refactor skeleton.",
        ("aura_refactor_skeleton.py",),
        ("RefactorSkeleton", "RefactorSkeletonNode", "RefactorSkeletonStore"),
        "aura_refactor_skeleton.py",
        "TRUE_NEW_CAPABILITY",
        "No canonical revisioned skeleton object existed.",
    ),
    CapabilityRequirement(
        "guarded_staging_verification",
        "Reuse ArchitectFusionLoop and Agent Arena Bridge staging, verifier, repair, "
        "hotswap, rollback, and export boundaries.",
        ("aura_architect_loop.py", "aura_agent_arena_bridge.py"),
        ("ArchitectFusionLoop", "AuraAgentArenaBridge"),
        "aura_architect_loop.py and aura_agent_arena_bridge.py",
        "REUSE",
        "No Bridge change without an exact interface gap.",
    ),
    CapabilityRequirement(
        "experience_and_crucible",
        "Project only complete verified episodes into ArenaExperience and "
        "proposal-only Crucible learning.",
        ("aura_arena_experience.py", "aura_arena_experience_ledger.py"),
        ("ArenaExperience", "OutcomeVector", "ArenaExperienceLedger"),
        "aura_arena_experience.py and aura_arena_experience_ledger.py",
        "REUSE",
        "Experience is descriptive and cannot activate behavior.",
    ),
    CapabilityRequirement(
        "code_quality_record",
        "Reuse the standard executable refactor output record.",
        ("aura_refactor_output_record.py",),
        ("RefactorOutputRecord",),
        "aura_refactor_output_record.py",
        "REUSE",
        "Construction results never inherit scores from other fixtures.",
    ),
)


def _default_resolver() -> Callable[..., dict[str, Any]]:
    from aura_capability_resolver_v2 import resolve_capabilities
    return resolve_capabilities


def _exact_hits(
    result: Mapping[str, Any],
    requirement: CapabilityRequirement,
) -> list[dict[str, Any]]:
    """Accept only exact requested owner symbols in declared candidate files."""
    files = set(requirement.candidate_files)
    symbols = set(requirement.candidate_symbols)
    seen: set[tuple[str, str, str]] = set()
    hits: list[dict[str, Any]] = []
    for collection in ("exact_matches", "related_functions"):
        for raw in result.get(collection) or ():
            item = dict(raw)
            file_name = str(item.get("file") or "")
            symbol = str(item.get("symbol") or "")
            kind = str(item.get("kind") or "function")
            grounding = str(item.get("grounding_class") or "EXACT")
            if (
                file_name not in files
                or symbol not in symbols
                or kind in {"file", "unresolved"}
                or grounding != "EXACT"
            ):
                continue
            key = (file_name, symbol, kind)
            if key not in seen:
                hits.append(item)
                seen.add(key)
    return hits


def build_construction_capability_reuse_matrix(
    *,
    repo_root: str = ".",
    resolver: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Resolve every proposed capability against exact current owner symbols."""
    resolve = resolver or _default_resolver()
    rows: list[dict[str, Any]] = []
    unresolved: list[str] = []
    for requirement in CAPABILITY_REQUIREMENTS:
        result = resolve(
            requirement.objective,
            target_files=list(requirement.candidate_files),
            target_symbols=list(requirement.candidate_symbols),
            repo_root=repo_root,
            top_k=16,
            token_budget=3200,
        )
        hits = _exact_hits(result, requirement)
        resolver_ok = bool(result.get("version")) and bool(
            (result.get("topology_health") or {}).get("topology_nodes", 0)
        )
        status = (
            "GROUNDED_REUSE_CANDIDATE"
            if resolver_ok and hits
            else "NEEDS_EXACT_GROUNDING"
        )
        if status != "GROUNDED_REUSE_CANDIDATE":
            unresolved.append(requirement.capability_id)
        rows.append(
            {
                "capability_id": requirement.capability_id,
                "objective": requirement.objective,
                "expected_owner": requirement.expected_owner,
                "reuse_decision": requirement.reuse_decision,
                "candidate_files": list(requirement.candidate_files),
                "candidate_symbols": list(requirement.candidate_symbols),
                "integration_reason": requirement.integration_reason,
                "status": status,
                "exact_hits": hits,
                "capability_ids": list(result.get("required_capability_ids") or ()),
                "capability_path": list(result.get("capability_path") or ()),
                "tests": list(
                    result.get("capability_tests")
                    or result.get("tests")
                    or ()
                ),
                "truth_boundaries": list(
                    result.get("capability_truth_boundaries") or ()
                ),
                "risks": list(result.get("capability_risks") or ()),
                "codemap_digest": str(result.get("codemap_digest") or ""),
                "capability_graph_digest": str(
                    result.get("capability_graph_digest") or ""
                ),
                "capability_path_digest": str(
                    result.get("capability_path_digest") or ""
                ),
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": False,
            }
        )
    return {
        "ok": not unresolved,
        "version": CONSTRUCTION_REFACTOR_PLAN_VERSION,
        "domain": DOMAIN,
        "rows": rows,
        "unresolved_capability_ids": unresolved,
        "decision_rule": "existing_path | missing_adapter | true_capability_gap",
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": False,
        "proposal_only": True,
    }


def _integrations(
    *,
    runtime: str = "DEFERRED",
    reason: str,
) -> tuple[IntegrationDisposition, ...]:
    dispositions = {
        "Human Agent Arena": "INTEGRATED",
        "Coding Arena": "INTEGRATED",
        "Agent Arena Bridge": "NOT_APPLICABLE",
        "Liquid Planning Arena": runtime,
        "Civic/project structures": "ADAPTER_REQUIRED",
        "Capability Connectome/Resolver": "INTEGRATED",
        "Router/Cognome": "DEFERRED",
        "Observatory": "DEFERRED",
        "Experience Ledger": "DEFERRED",
        "Crucible": "DEFERRED",
    }
    return tuple(
        IntegrationDisposition.create(structure, disposition, reason)
        for structure, disposition in dispositions.items()
    )


def create_construction_refactor_skeleton(
    *,
    baseline_commit: str,
    source_plan_digest: str,
    addendum_digest: str,
    reuse_matrix: Mapping[str, Any],
    emergent_packet_id: str = "",
    emergent_packet_digest: str = "",
) -> RefactorSkeleton:
    """Create the original E0-E14 planning skeleton.

    Current completion is validated by aura_construction_refactor_completion.py;
    this historical skeleton remains stable for provenance and replay.
    """
    unresolved = tuple(
        str(item)
        for item in reuse_matrix.get("unresolved_capability_ids", ())
        if item
    )
    row_count = len(reuse_matrix.get("rows", ()))
    invariants = (
        "exact source spans and hashes are the only patch evidence",
        "external research, VSA, topology, sensors, and models grant no authority",
        "construction safety, payment, professional, contractual, legal, and "
        "regulatory decisions remain human-authorized",
        "denied actions leave workflow and project evidence unchanged",
    )
    nodes = (
        RefactorSkeletonNode.create(
            node_id="E0",
            objective="Lock baseline and register source/evidence boundaries.",
            canonical_owner="Human Agent Emergent workspace plus planning docs",
            reuse_decision="EXTEND_CANONICAL_OWNER",
            invariants=invariants,
            acceptance_criteria=(
                "all source digests recorded",
                "no source mutation",
                "unresolved selected evidence fails closed",
            ),
            required_tests=("tests/test_aura_emergent_refactor_workspace.py",),
            risk_lanes=("provenance", "authority", "privacy"),
            status="PLANNED",
            integration_dispositions=_integrations(
                reason="Phase-one evidence and continuity integration."
            ),
            metadata={"unresolved_reuse_capabilities": list(unresolved)},
        ),
        RefactorSkeletonNode.create(
            node_id="E1",
            objective="Prove canonical owners before invention.",
            canonical_owner="aura_capability_resolver_v2.py",
            reuse_decision="REUSE",
            target_files=(
                "aura_capability_resolver.py",
                "aura_capability_resolver_v2.py",
                "aura_capability_connectome.py",
            ),
            dependencies=("E0",),
            invariants=invariants,
            acceptance_criteria=(
                "every proposed capability has an owner decision",
                "no new module lacks a reuse row",
            ),
            required_tests=(
                "tests/test_aura_capability_resolver.py",
                "tests/test_aura_capability_connectome.py",
            ),
            risk_lanes=("scope", "compatibility", "duplication"),
            status="NEEDS_GROUNDING" if unresolved else "GROUNDED",
            integration_dispositions=_integrations(
                reason="Mandatory reuse-before-invention gate."
            ),
            metadata={
                "reuse_matrix_rows": row_count,
                "unresolved_capability_ids": list(unresolved),
            },
        ),
        RefactorSkeletonNode.create(
            node_id="E2",
            objective="Persist a revisioned digest-bound refactor skeleton.",
            canonical_owner="aura_refactor_skeleton.py",
            reuse_decision="TRUE_NEW_CAPABILITY",
            target_files=(
                "aura_refactor_skeleton.py",
                "aura_construction_refactor_plan.py",
            ),
            dependencies=("E1",),
            invariants=invariants,
            acceptance_criteria=(
                "stable content identity",
                "revision history preserved",
                "all relevant Arenas classified",
            ),
            required_tests=(
                "tests/test_aura_refactor_skeleton.py",
                "tests/test_aura_construction_refactor_plan.py",
            ),
            risk_lanes=("persistence", "authority", "continuity"),
            status="PLANNED",
            integration_dispositions=_integrations(
                reason="General skeleton owner; Construction is first adapter."
            ),
        ),
        RefactorSkeletonNode.create(
            node_id="E3",
            objective="Compile exact-grounded ready nodes into bounded code capsules.",
            canonical_owner=(
                "aura_liquid_planning_arena.py plus Aura routing owners"
            ),
            reuse_decision="ADD_NARROW_ADAPTER",
            target_files=(
                "aura_liquid_planning_arena.py",
                "aura_construction_refactor_plan.py",
            ),
            dependencies=("E2",),
            invariants=invariants,
            acceptance_criteria=(
                "ZERO_MODEL supported",
                "workers receive bounded scope",
                "unready nodes fail closed",
            ),
            required_tests=("tests/test_aura_construction_refactor_plan.py",),
            risk_lanes=("scope", "routing", "cost"),
            status="NEEDS_GROUNDING",
            integration_dispositions=_integrations(
                reason="Coding-only capsule boundary; runtime remains deferred."
            ),
        ),
        RefactorSkeletonNode.create(
            node_id="E4-E14",
            objective=(
                "Implement Construction contracts, state, advisory lanes, runtime, "
                "Human Agent, Experience, benchmark, docs, review, and merge only "
                "after E0-E3 pass."
            ),
            canonical_owner="future exact-grounded owners from reuse matrix",
            reuse_decision="DEFER",
            dependencies=("E3",),
            invariants=invariants,
            acceptance_criteria=(
                "phase-specific plan approved",
                "cross-Arena handoff updated",
                "final external or equivalent manual review complete",
            ),
            required_tests=(
                "future focused hidden integration and regression tests",
            ),
            risk_lanes=(
                "safety", "payment", "privacy", "security", "authority", "rollback",
            ),
            status="DRAFT",
            integration_dispositions=_integrations(
                runtime="ADAPTER_REQUIRED",
                reason="Deferred until the foundation phase is verified.",
            ),
        ),
    )
    return RefactorSkeleton.create(
        objective=(
            "Build an SCO-governed symbolic Construction Arena through Aura's "
            "existing governed spine."
        ),
        domain=DOMAIN,
        baseline_commit=baseline_commit,
        source_plan_digest=source_plan_digest,
        addendum_digest=addendum_digest,
        emergent_packet_id=emergent_packet_id,
        emergent_packet_digest=emergent_packet_digest,
        nodes=nodes,
        status="PLANNED",
        metadata={
            "plan_version": CONSTRUCTION_REFACTOR_PLAN_VERSION,
            "unresolved_capability_ids": list(unresolved),
            "forbidden_construction_authority": list(
                FORBIDDEN_CONSTRUCTION_AUTHORITY
            ),
        },
    )


def compile_ready_nodes_to_action_capsules(
    skeleton: RefactorSkeleton,
    *,
    repo_root: str | Path,
    node_ids: Sequence[str] = (),
    capsule_factory: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Compile only exact-span, byte-hash-verified READY_FOR_ACT nodes."""
    validation = skeleton.validate(
        required_structures=REQUIRED_STRUCTURES,
        repo_root=repo_root,
        verify_sources=True,
    )
    if not validation["ok"]:
        return {
            "ok": False,
            "error": "invalid_refactor_skeleton",
            "errors": list(validation["errors"]),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
        }
    requested = tuple(str(item) for item in node_ids if str(item).strip())
    selected = [
        node
        for node in skeleton.nodes
        if not requested or node.node_id in requested
    ]
    missing = sorted(set(requested) - {node.node_id for node in selected})
    if missing:
        return {
            "ok": False,
            "error": "unknown_skeleton_node_ids",
            "missing_node_ids": missing,
        }
    if not selected:
        return {"ok": False, "error": "no_skeleton_nodes_selected"}
    blocked = [
        node.node_id for node in selected if node.status != "READY_FOR_ACT"
    ]
    if blocked:
        return {
            "ok": False,
            "error": "nodes_not_ready_for_act",
            "blocked_node_ids": blocked,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
        }

    factory = capsule_factory
    if factory is None:
        from aura_liquid_planning_arena import ActionCapsule
        factory = ActionCapsule.create

    capsules: list[Any] = []
    for node in selected:
        spans = [item.to_dict() for item in node.exact_source_spans]
        capsules.append(
            factory(
                capsule_id=f"SCO-{node.node_id}-R{node.revision}",
                domain="code",
                role="sliced_surgeon",
                objective=node.objective,
                target={
                    "files": list(node.target_files),
                    "symbols": list(node.target_symbols),
                },
                scope={
                    "files": list(node.target_files),
                    "source_hashes": dict(node.exact_source_hashes),
                    "source_spans": spans,
                    "skeleton_id": skeleton.skeleton_id,
                    "skeleton_digest": skeleton.skeleton_digest,
                },
                allowed_actions=(
                    "read exact grounded slices",
                    "emit one bounded unified diff",
                    "declare affected tests",
                ),
                forbidden_actions=(
                    "mutate production directly",
                    "touch unleased files",
                    "invent missing source hashes or spans",
                    *FORBIDDEN_CONSTRUCTION_AUTHORITY,
                ),
                acceptance_checks=(
                    list(node.acceptance_criteria) + list(node.required_tests)
                ),
                expected_output="UNIFIED_DIFF",
                escalation_triggers=list(node.risk_lanes),
                metadata={
                    "node_digest": node.node_digest,
                    "reuse_decision": node.reuse_decision,
                    "canonical_owner": node.canonical_owner,
                    "proposal_only": True,
                },
            )
        )
    return {
        "ok": True,
        "capsules": [
            item.to_dict() if hasattr(item, "to_dict") else item
            for item in capsules
        ],
        "count": len(capsules),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": False,
        "proposal_only": True,
    }


def validate_construction_refactor_plan(
    skeleton: RefactorSkeleton,
    *,
    repo_root: str | Path | None = None,
    verify_sources: bool = False,
) -> dict[str, Any]:
    result = skeleton.validate(
        required_structures=REQUIRED_STRUCTURES,
        repo_root=repo_root,
        verify_sources=verify_sources,
    )
    errors = list(result.get("errors", ()))
    if not skeleton.proposal_only:
        errors.append("construction refactor skeleton must remain proposal-only")
    return {
        **result,
        "ok": not errors,
        "errors": errors,
        "plan_version": CONSTRUCTION_REFACTOR_PLAN_VERSION,
        "forbidden_construction_authority": list(
            FORBIDDEN_CONSTRUCTION_AUTHORITY
        ),
    }
