"""Objective-scoped relationship intelligence for bounded Aura coding work.

The Coding Relationship Compass combines four existing Aura views without
becoming a duplicate truth owner:

* Capability Connectome selects useful capabilities and implementations.
* Emergent Evidence Spine grounds exact atomic functions, tests, and hashes.
* Relational Synthesis compiles a JIT proposal-only working capsule.
* Relationship Atlas classifies exact relations, prohibitions, and missing roles.

The output is orientation and planning evidence. It never grants patch,
execution, commit, push, pull-request, or merge authority.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from aura_capability_connectome import build_capability_connectome, find_capability_path
from aura_capability_connectome_v2 import enrich_connectome, enrich_path
from aura_emergent_evidence_spine import AuraEmergentEvidenceSpine, EmergentEvidenceRequest
from aura_polysynthetic_intent import PolysyntheticIntentPacket
from aura_relational_index import build_relational_index
from aura_relational_synthesis import compile_relational_shadow_capsule
from aura_relationship_atlas import (
    AtlasSnapshot,
    WiringDisposition,
    build_relationship_atlas,
    compile_atlas_projection,
    relationships_for_participant,
)

COMPASS_VERSION = "AURA_CODING_RELATIONSHIP_COMPASS_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


@dataclass(frozen=True)
class ArchitectureComponent:
    """Canonical target hints for architecture-owned concepts."""

    component_id: str
    keywords: tuple[str, ...]
    phrases: tuple[str, ...]
    files: tuple[str, ...]
    symbols: tuple[str, ...]


_COMPONENTS: tuple[ArchitectureComponent, ...] = (
    ArchitectureComponent(
        component_id="coding_relationship_compass",
        keywords=("compass",),
        phrases=(
            "code better",
            "combine connectome relational synthesis atlas",
            "connectome relational synthesis and atlas",
            "coding relationship compass",
        ),
        files=("aura_coding_relationship_compass.py",),
        symbols=(
            "compile_coding_relationship_compass",
            "relationship_compass_grounding",
            "is_coding_relationship_compass_intent",
        ),
    ),
    ArchitectureComponent(
        component_id="capability_connectome",
        keywords=("connectome", "capability"),
        phrases=("connectome", "capability graph", "capability anatomy"),
        files=("aura_capability_connectome.py", "aura_capability_connectome_v2.py"),
        symbols=(
            "build_capability_connectome",
            "find_capability_path",
            "enrich_connectome",
            "enrich_path",
        ),
    ),
    ArchitectureComponent(
        component_id="relational_synthesis",
        keywords=("relational", "synthesis"),
        phrases=("relational synthesis", "jit relational capsule"),
        files=("aura_relational_synthesis.py",),
        symbols=("compile_relational_shadow_capsule",),
    ),
    ArchitectureComponent(
        component_id="relationship_atlas",
        keywords=("atlas", "relationship"),
        phrases=("atlas", "relationship atlas", "architecture relationship atlas"),
        files=("aura_relationship_atlas.py",),
        symbols=(
            "build_relationship_atlas",
            "compile_atlas_projection",
            "relationships_for_participant",
        ),
    ),
    ArchitectureComponent(
        component_id="relational_index",
        keywords=("index", "anatomy"),
        phrases=("relational index", "relational anatomy"),
        files=("aura_relational_index.py",),
        symbols=("build_relational_index", "query_relational_index"),
    ),
    ArchitectureComponent(
        component_id="emergent_properties",
        keywords=("emergent", "emergence"),
        phrases=("emergent properties", "future potential", "unwired connection"),
        files=("aura_emergent_evidence_spine.py", "aura_emergent_potential_repl.py"),
        symbols=(
            "AuraEmergentEvidenceSpine.run",
            "audit_emergent_potential",
        ),
    ),
    ArchitectureComponent(
        component_id="architect",
        keywords=("architect", "surgeon"),
        phrases=("architect repl", "live architect"),
        files=("aura_live_architect.py", "aura_architect_loop.py"),
        symbols=(
            "ArchitectModelRouter.deterministic_plan_spec",
            "ArchitectFusionCouncil.select_plan",
            "run_live_architect_transaction",
        ),
    ),
    ArchitectureComponent(
        component_id="change_capsules",
        keywords=("capsule", "change", "act"),
        phrases=("change capsule", "act capsule", "capsule compiler"),
        files=("aura_change_graph.py", "aura_agent_ir_compiler.py"),
        symbols=("change_graph_to_act_capsules", "AgentIRCompiler"),
    ),
)

_TOKEN_RE = re.compile(r"[a-z][a-z0-9_]+", re.ASCII)

_RELATIONAL_PLANE_CACHE: dict[tuple[str, str, str, str], tuple[dict[str, Any], AtlasSnapshot]] = {}
_RELATIONAL_PLANE_CACHE_LIMIT = 4


def _stable_digest(value: Any, *, digest_size: int = 24) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.blake2b(raw, digest_size=digest_size).hexdigest()


def _ordered_unique(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if str(value)))


def _tokens(value: str) -> set[str]:
    return set(_TOKEN_RE.findall(str(value or "").lower()))


def is_coding_relationship_compass_intent(objective: str) -> bool:
    """Return whether a broad coding objective benefits from relational localization."""
    lowered = " ".join(str(objective or "").lower().split())
    if not lowered:
        return False
    tokens = _tokens(lowered)
    architecture_hits = tokens & {
        "architecture",
        "atlas",
        "capability",
        "combine",
        "connectome",
        "emergent",
        "relation",
        "relational",
        "relationship",
        "synthesis",
        "wire",
        "wiring",
    }
    coding_hits = tokens & {"architect", "code", "coding", "function", "refactor", "surgeon"}
    return bool(architecture_hits) and bool(coding_hits or len(architecture_hits) >= 2)


def _component_targets(
    objective: str,
    repo_root: Path,
    *,
    explicit_files: Sequence[str] = (),
    explicit_symbols: Sequence[str] = (),
) -> tuple[list[str], list[str], list[str]]:
    lowered = " ".join(str(objective or "").lower().split())
    objective_tokens = _tokens(lowered)
    matched: list[str] = []
    files = list(explicit_files)
    symbols = list(explicit_symbols)
    for component in _COMPONENTS:
        phrase_hit = any(phrase in lowered for phrase in component.phrases)
        keyword_hits = objective_tokens.intersection(component.keywords)
        threshold = 1 if len(component.keywords) == 1 else 2
        if phrase_hit or len(keyword_hits) >= threshold:
            matched.append(component.component_id)
            files.extend(component.files)
            symbols.extend(component.symbols)
    files = [path for path in _ordered_unique(files) if (repo_root / path).is_file()]
    return matched, files, _ordered_unique(symbols)


def _connectome_targets(path_packet: Mapping[str, Any], repo_root: Path) -> tuple[list[str], list[str], list[str]]:
    files = [
        path
        for path in path_packet.get("implemented_by", []) or []
        if isinstance(path, str) and (repo_root / path).is_file()
    ]
    tests = [
        path
        for path in path_packet.get("tests", []) or []
        if isinstance(path, str) and (repo_root / path).is_file()
    ]
    symbols = [str(item) for item in path_packet.get("symbols", []) or [] if str(item)]
    return _ordered_unique(files), _ordered_unique(symbols), _ordered_unique(tests)


def _selected_atomic_functions(evidence_packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    inventory = evidence_packet.get("atomic_inventory") or {}
    if not isinstance(inventory, Mapping):
        return []
    return [dict(item) for item in inventory.get("selected_atomic_functions", []) or [] if isinstance(item, Mapping)]


def _select_focal_participants(
    relational_index: Mapping[str, Any],
    evidence_packet: Mapping[str, Any],
    target_files: Sequence[str],
    target_symbols: Sequence[str],
    capability_ids: Sequence[str],
    *,
    limit: int,
) -> list[str]:
    participants = [item for item in relational_index.get("participants", []) or [] if isinstance(item, Mapping)]
    exact_pairs = {
        (str(item.get("file_path") or ""), str(item.get("qualified_symbol") or item.get("symbol") or ""))
        for item in _selected_atomic_functions(evidence_packet)
    }
    file_set = set(target_files)
    symbol_set = set(target_symbols)
    capability_set = set(capability_ids)
    scored: list[tuple[int, str]] = []
    for participant in participants:
        participant_id = str(participant.get("participant_id") or "")
        if not participant_id:
            continue
        metadata = participant.get("metadata") or {}
        if not isinstance(metadata, Mapping):
            metadata = {}
        file_path = str(metadata.get("file_path") or "")
        qualified_symbol = str(participant.get("qualified_symbol") or "")
        role = str(participant.get("role") or "")
        canonical_ref = str(participant.get("canonical_ref") or "")
        score = 0
        if (file_path, qualified_symbol) in exact_pairs:
            score += 500
        if file_path in file_set:
            score += 180
        if qualified_symbol in symbol_set or qualified_symbol.split(".")[-1] in symbol_set:
            score += 240
        if capability_set and any(capability_id in canonical_ref or capability_id in role for capability_id in capability_set):
            score += 120
        if str(participant.get("truth_class") or "").startswith("EXACT"):
            score += 10
        if score:
            line_start = int(metadata.get("line_start") or 0)
            scored.append((score * 1_000_000 - line_start, participant_id))
    scored.sort(reverse=True)
    return _ordered_unique([participant_id for _, participant_id in scored])[: max(1, limit)]


def _bounded_atlas_intelligence(
    snapshot: AtlasSnapshot,
    focal_participant_ids: Sequence[str],
    *,
    max_assessments: int,
) -> dict[str, Any]:
    focal = set(focal_participant_ids)
    assessments_by_id: dict[str, Any] = {}
    for participant_id in focal_participant_ids:
        for assessment in relationships_for_participant(participant_id, snapshot):
            assessments_by_id[assessment.assessment_id] = assessment

    ranked: list[tuple[int, Any]] = []
    for assessment in assessments_by_id.values():
        participant_ids = {item.participant_id for item in assessment.participant_refs}
        score = 100 * len(participant_ids & focal)
        if str(assessment.truth_class).startswith("EXACT"):
            score += 20
        if assessment.wiring_disposition == WiringDisposition.PROHIBITED:
            score += 40
        if assessment.missing_roles:
            score += 15
        ranked.append((score, assessment))
    ranked.sort(key=lambda item: (-item[0], item[1].assessment_id))
    selected = [item[1] for item in ranked[: max(1, max_assessments)]]

    preserve: list[dict[str, Any]] = []
    assessment_summaries: list[dict[str, Any]] = []
    required_adapters: list[str] = []
    authority_constraints: list[str] = []
    missing_roles: list[str] = []
    required_verifiers: list[str] = []
    for assessment in selected:
        refs = [item.canonical_ref for item in assessment.participant_refs]
        summary = {
            "assessment_id": assessment.assessment_id,
            "participant_refs": refs,
            "relation_types": list(assessment.relation_types),
            "structural_status": assessment.structural_status.value,
            "semantic_relationship": assessment.semantic_relationship.value,
            "wiring_disposition": assessment.wiring_disposition.value,
            "readiness": assessment.readiness.value,
            "truth_class": assessment.truth_class,
            "proof_status": assessment.proof_status.value,
            "evidence_refs": list(assessment.evidence_refs)[:6],
            "risks": list(assessment.risks),
            "prohibited_effects": list(assessment.prohibited_effects),
        }
        assessment_summaries.append(summary)
        if assessment.structural_status.value in {"EXACTLY_WIRED", "DECLARED_WIRED"}:
            preserve.append(
                {
                    "participant_refs": refs,
                    "relation_types": list(assessment.relation_types),
                    "truth_class": assessment.truth_class,
                    "evidence_refs": list(assessment.evidence_refs)[:4],
                }
            )
        required_adapters.extend(assessment.required_adapters)
        authority_constraints.extend(assessment.authority_constraints)
        missing_roles.extend(assessment.missing_roles)
        required_verifiers.extend(
            item for item in assessment.evidence_refs if "test" in str(item).lower() or "verif" in str(item).lower()
        )

    relevant_missing = []
    for configuration in snapshot.missing_configurations:
        bound_ids = set(configuration.bound_roles.values())
        if bound_ids & focal or not focal:
            relevant_missing.append(configuration.to_dict())
    if not relevant_missing:
        relevant_missing = [item.to_dict() for item in snapshot.missing_configurations[:8]]

    projection = compile_atlas_projection(list(focal_participant_ids)[:16], snapshot)
    projection["nodes"] = list(projection.get("nodes", []))[:128]
    projection["edges"] = list(projection.get("edges", []))[:256]
    projection["truncated"] = (
        len(projection.get("nodes", [])) >= 128 or len(projection.get("edges", [])) >= 256
    )

    return {
        "snapshot_digest": snapshot.snapshot_digest,
        "repository_head": snapshot.repository_head,
        "relational_index_digest": snapshot.relational_index_digest,
        "profile": snapshot.boundary.get("operational_profile", ""),
        "focal_participant_ids": list(focal_participant_ids),
        "assessment_count_considered": len(assessments_by_id),
        "assessments": assessment_summaries,
        "relationships_to_preserve": preserve[:96],
        "required_adapters": _ordered_unique(required_adapters),
        "authority_constraints": _ordered_unique(authority_constraints),
        "missing_roles": _ordered_unique(missing_roles),
        "required_verifiers": _ordered_unique(required_verifiers),
        "missing_configurations": relevant_missing[:16],
        "prohibitions": [item.to_dict() for item in snapshot.prohibitions],
        "projection": projection,
        "advisory_only": True,
    }


def _recommended_targets(
    evidence_packet: Mapping[str, Any],
    preferred_files: Sequence[str],
    preferred_symbols: Sequence[str],
) -> list[dict[str, Any]]:
    preferred_file_order = {path: index for index, path in enumerate(preferred_files)}
    preferred_symbol_order = {symbol: index for index, symbol in enumerate(preferred_symbols)}
    candidates: list[tuple[int, dict[str, Any]]] = []
    for item in evidence_packet.get("source_slices", []) or []:
        if not isinstance(item, Mapping):
            continue
        file_path = str(item.get("file_path") or "")
        symbol = str(item.get("qualified_symbol") or item.get("symbol") or "")
        score = 0
        if file_path in preferred_file_order:
            score += 1_000 - preferred_file_order[file_path]
        symbol_key = symbol if symbol in preferred_symbol_order else symbol.split(".")[-1]
        if symbol_key in preferred_symbol_order:
            score += 3_000 - preferred_symbol_order[symbol_key]
        if symbol and not symbol.split(".")[-1].startswith("_"):
            score += 20
        candidates.append(
            (
                score,
                {
                    "file_path": file_path,
                    "symbol": symbol,
                    "line_start": item.get("line_start"),
                    "line_end": item.get("line_end"),
                    "source_hash": item.get("source_hash"),
                    "file_source_hash": item.get("file_source_hash"),
                    "node_id": item.get("node_id"),
                },
            )
        )
    candidates.sort(key=lambda entry: (-entry[0], entry[1]["file_path"], int(entry[1].get("line_start") or 0)))
    return [item for _, item in candidates]


def compile_coding_relationship_compass(
    objective: str,
    repo_root: str | Path = ".",
    *,
    target_files: Sequence[str] = (),
    target_symbols: Sequence[str] = (),
    max_target_files: int = 16,
    max_target_symbols: int = 32,
    max_atomic_nodes: int = 36,
    max_atlas_participants: int = 32,
    max_atlas_assessments: int = 96,
    max_required_tests: int = 24,
    include_source: bool = False,
    relational_index_data: Mapping[str, Any] | None = None,
    atlas_snapshot: AtlasSnapshot | None = None,
    evidence_packet: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile a bounded coding relationship packet for Architect/Surgeon review.

    The default path builds the Relational Index and MINIMAL Atlas in memory, so
    a query does not write generated architecture artifacts into the repository.
    Optional precomputed inputs support deterministic callers and focused tests.
    """
    normalized_objective = " ".join(str(objective or "").split())
    if not normalized_objective:
        raise ValueError("objective is required")
    root = Path(repo_root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"repository root is missing: {root}")

    graph = enrich_connectome(build_capability_connectome(root))
    capability_path = enrich_path(find_capability_path(normalized_objective, root), graph)
    matched_components, component_files, component_symbols = _component_targets(
        normalized_objective,
        root,
        explicit_files=target_files,
        explicit_symbols=target_symbols,
    )
    path_files, path_symbols, path_tests = _connectome_targets(capability_path, root)
    selected_files = _ordered_unique([*component_files, *path_files])[: max(1, max_target_files)]
    selected_symbols = _ordered_unique([*component_symbols, *path_symbols])[: max(1, max_target_symbols)]
    if not selected_files:
        raise ValueError("Connectome and architecture registry found no current implementation files")

    if evidence_packet is None:
        evidence = AuraEmergentEvidenceSpine(root).run(
            EmergentEvidenceRequest(
                objective=normalized_objective,
                target_files=tuple(selected_files),
                target_symbols=tuple(selected_symbols),
                target_arena="coding_arena",
                radius=1,
                max_atomic_nodes=max(8, min(120, int(max_atomic_nodes))),
                max_source_lines=160 if include_source else 24,
                include_source=include_source,
                include_future=True,
                include_research_plan=False,
                include_offline_research=False,
            )
        )
    else:
        evidence = dict(evidence_packet)
    if not evidence.get("ok") or not evidence.get("grounding_ok"):
        raise ValueError("Emergent Evidence Spine did not produce an exact grounded packet")

    intent_packet = PolysyntheticIntentPacket.from_slots(
        {
            "DIR": "IN",
            "ASP": "GROUND",
            "CLASS": "REVIEW",
            "SUBJ": "REPOSITORY_RELATION",
            "VOICE": "HUMAN_AGENT",
            "STEM": "INSPECT",
        },
        adjuncts={
            "grounding": "exact_current_source",
            "risk": "proposal_only",
            "tests": "required_before_patch",
        },
        objective=normalized_objective,
    )
    inventory = evidence.get("atomic_inventory") or {}
    relational_capsule = compile_relational_shadow_capsule(
        evidence,
        intent_packet=intent_packet,
        expected_repo_head=str(evidence.get("repo_head") or ""),
        expected_packet_digest=str(evidence.get("packet_digest") or ""),
        expected_inventory_digest=str(inventory.get("inventory_digest") or ""),
        active_arena="coding",
    )

    cache_hit = False
    cache_key = (
        str(root),
        str(evidence.get("repo_head") or ""),
        str(inventory.get("inventory_digest") or ""),
        str(graph.get("graph_digest") or ""),
    )
    if relational_index_data is None and atlas_snapshot is None and cache_key in _RELATIONAL_PLANE_CACHE:
        cached_index, cached_atlas = _RELATIONAL_PLANE_CACHE[cache_key]
        relational_index = cached_index
        atlas = cached_atlas
        cache_hit = True
    else:
        if relational_index_data is None:
            index_result = build_relational_index(
                root,
                profile="MINIMAL",
                persist=False,
                include_index=True,
            )
            relational_index = dict(index_result["index"])
        else:
            relational_index = dict(relational_index_data)
        if atlas_snapshot is None:
            atlas = build_relationship_atlas(
                repo_root=root,
                profile="MINIMAL",
                relational_index_data=relational_index,
                persist=False,
            )
        else:
            atlas = atlas_snapshot
        if relational_index_data is None and atlas_snapshot is None:
            if len(_RELATIONAL_PLANE_CACHE) >= _RELATIONAL_PLANE_CACHE_LIMIT:
                _RELATIONAL_PLANE_CACHE.pop(next(iter(_RELATIONAL_PLANE_CACHE)))
            _RELATIONAL_PLANE_CACHE[cache_key] = (relational_index, atlas)

    capability_ids = [str(item) for item in capability_path.get("required_capability_ids", []) or []]
    focal_ids = _select_focal_participants(
        relational_index,
        evidence,
        selected_files,
        selected_symbols,
        capability_ids,
        limit=max(1, max_atlas_participants),
    )
    atlas_intelligence = _bounded_atlas_intelligence(
        atlas,
        focal_ids,
        max_assessments=max(1, max_atlas_assessments),
    )
    targets = _recommended_targets(evidence, selected_files, selected_symbols)
    if not targets:
        raise ValueError("exact evidence packet contained no source target")
    primary = targets[0]

    required_tests = _ordered_unique(
        [
            *[str(item) for item in evidence.get("tests", []) or []],
            *[str(item) for item in evidence.get("required_tests", []) or []],
            *path_tests,
            *atlas_intelligence.get("required_verifiers", []),
        ]
    )[: max(1, max_required_tests)]
    action_capsule_hints = [
        {
            "task_id": f"CRC-{index:02d}",
            "objective": normalized_objective,
            "target_file": item["file_path"],
            "target_symbol": item["symbol"],
            "source_hash": item["source_hash"],
            "allowed_scope": "exact grounded source span plus declared tests",
            "expected_output": "PROPOSAL_OR_UNIFIED_DIFF",
            "human_review_required": True,
        }
        for index, item in enumerate(targets[:8], start=1)
    ]

    packet: dict[str, Any] = {
        "version": COMPASS_VERSION,
        "objective": normalized_objective,
        "matched_components": matched_components,
        "target_file": primary["file_path"],
        "target_symbol": primary["symbol"],
        "recommended_targets": targets[:16],
        "required_tests": required_tests,
        "action_capsule_hints": action_capsule_hints,
        "connectome": {
            "version": graph.get("version"),
            "graph_digest": graph.get("graph_digest"),
            "path_digest": capability_path.get("path_digest"),
            "required_capability_ids": capability_ids,
            "path_details": list(capability_path.get("path_details", []) or []),
            "execution_classes": {
                "deterministic": list(capability_path.get("deterministic_capability_ids", []) or []),
                "model_dependent": list(capability_path.get("model_dependent_capability_ids", []) or []),
                "unresolved": list(capability_path.get("unresolved_execution_capability_ids", []) or []),
            },
        },
        "emergent_evidence": {
            "packet_id": evidence.get("packet_id"),
            "packet_digest": evidence.get("packet_digest"),
            "repo_head": evidence.get("repo_head"),
            "status": evidence.get("status"),
            "atomic_inventory_digest": inventory.get("inventory_digest"),
            "atomic_inventory_total": inventory.get("total_count"),
            "selected_atomic_functions": _selected_atomic_functions(evidence),
            "source_slices": list(evidence.get("source_slices", []) or []),
            "dependency_edges": list(evidence.get("dependency_edges", []) or []),
            "selected_findings": list(evidence.get("selected_findings", []) or []),
            "risk_map": list(evidence.get("risk_map", []) or []),
        },
        "relational_synthesis": relational_capsule,
        "atlas": {**atlas_intelligence, "cache_hit": cache_hit},
        "relationships_to_preserve": atlas_intelligence.get("relationships_to_preserve", []),
        "prohibitions": atlas_intelligence.get("prohibitions", []),
        "missing_roles": atlas_intelligence.get("missing_roles", []),
        "required_adapters": atlas_intelligence.get("required_adapters", []),
        "authority_constraints": atlas_intelligence.get("authority_constraints", []),
        "route": "CODING_RELATIONSHIP_COMPASS",
        "grounding_ok": True,
        "safe_to_patch": False,
        "production_mutation": False,
        "automatic_fix": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_pull_request": False,
        "automatic_merge": False,
        "human_review_required": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
    digest_payload = dict(packet)
    packet["compass_digest"] = _stable_digest(digest_payload)
    return packet


def relationship_compass_grounding(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Project a compact Architect-compatible grounding packet."""
    targets = [dict(item) for item in packet.get("recommended_targets", []) or [] if isinstance(item, Mapping)]
    primary = targets[0] if targets else {}
    atlas = packet.get("atlas") or {}
    if not isinstance(atlas, Mapping):
        atlas = {}
    return {
        "route": packet.get("route", "CODING_RELATIONSHIP_COMPASS"),
        "target_file": packet.get("target_file") or primary.get("file_path"),
        "target_symbol": packet.get("target_symbol") or primary.get("symbol"),
        "candidate_files": [
            {"path": item.get("file_path"), "symbol": item.get("symbol"), "source_hash": item.get("source_hash")}
            for item in targets[:8]
        ],
        "source_spans": [
            {
                "file_path": item.get("file_path"),
                "symbol": item.get("symbol"),
                "line_start": item.get("line_start"),
                "line_end": item.get("line_end"),
                "source_hash": item.get("source_hash"),
                "file_source_hash": item.get("file_source_hash"),
            }
            for item in targets[:16]
        ],
        "exact_hits": targets[:16],
        "tests": list(packet.get("required_tests", []) or []),
        "capability_path": list((packet.get("connectome") or {}).get("required_capability_ids", []) or []),
        "relationship_compass_digest": packet.get("compass_digest"),
        "relationship_atlas_digest": atlas.get("snapshot_digest"),
        "relationships_to_preserve": list(packet.get("relationships_to_preserve", []) or [])[:32],
        "prohibitions": list(packet.get("prohibitions", []) or []),
        "missing_roles": list(packet.get("missing_roles", []) or []),
        "required_adapters": list(packet.get("required_adapters", []) or []),
        "action_capsule_hints": list(packet.get("action_capsule_hints", []) or []),
        "grounding_ok": bool(packet.get("grounding_ok")),
        "safe_to_patch": False,
        "human_review_required": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


__all__ = [
    "COMPASS_VERSION",
    "ArchitectureComponent",
    "compile_coding_relationship_compass",
    "is_coding_relationship_compass_intent",
    "relationship_compass_grounding",
]
