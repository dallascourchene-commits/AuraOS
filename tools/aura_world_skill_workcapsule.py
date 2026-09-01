"""Aura WorldWiki -> WorkCapsule skill/hydration compiler.

D0 / HS1 / NONPROMOTING.

This module is the missing planning membrane between:
- EKI external World nodes (stable subject + source generation + L0-L4 + K27),
- a persistent Wiki/skill registry (procedural knowledge + validation history), and
- WorkCapsuleV2 (small, exact, job-scoped hot context).

It deliberately does *not* own source truth, source currentness, skill acceptance,
tool admission, WorkCapsule authority, or execution.  Its job is to compile a
small route: where the job is, which already-admissible skills cover the stated
capabilities, which tools they require, and which external subjects need deeper
hydration before the job can proceed.

Core laws:
- WorldMap != Territory.
- K27Coordinate != SemanticIdentity != Currentness != Authority.
- WikiKnowledge != HotWorkCapsuleContext.
- SkillDiscovery != SkillAcceptance != SkillUseAuthority.
- SearchMiss != KnownAbsent.
- CacheHit != CurrentnessWitness.
- LargeReconstructibleWorld + SmallActiveBoundary.
- CoordinateMemory != MODEL_PREFIX_KV.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import itertools
import json
from typing import Any, Iterable, Sequence

from tools.aura_external_knowledge_ingress import ExternalKnowledgeNode, KnowledgeState


SCHEMA = "AURA-WORLD-SKILL-WORKCAPSULE-v1"
SKILL_SCHEMA = "AURA-WORLD-WIKI-SKILL-CARD-v1"
ROUTE_CACHE_SCHEMA = "AURA-WORLD-ROUTE-CACHE-v1"
HYDRATION_POLICY = "AURA-L0-L4-DEMAND-HYDRATION-v1"
WORKCAPSULE_TARGET_SCHEMA = "WorkCapsuleV2"
WORKCAPSULE_TARGET_VERSION = "2.1.0"

LEVELS = ("L0", "L1", "L2", "L3", "L4")
SKILL_STATES = frozenset({"EXISTING", "EVOLVED_ACCEPTED", "CANDIDATE", "REJECTED"})
CURRENTNESS = frozenset({"CURRENT", "STALE", "UNKNOWN"})


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}_REQUIRED")
    return value.strip()


def _canonical_strings(values: Iterable[str], field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    out = tuple(sorted({_text(v, field) for v in values}))
    if not out and not allow_empty:
        raise ValueError(f"{field}_REQUIRED")
    return out


def _level_index(level: str) -> int:
    if level not in LEVELS:
        raise ValueError("HYDRATION_LEVEL_INVALID")
    return LEVELS.index(level)


@dataclass(frozen=True)
class ObjectiveRouteProfile:
    objective_id: str
    objective: str
    world_id: str
    required_capabilities: tuple[str, ...]
    model_family: str
    available_tools: tuple[str, ...]
    skill_registry_generation: str
    tool_registry_generation: str
    authority_scope: str

    def validate(self) -> None:
        _text(self.objective_id, "OBJECTIVE_ID")
        _text(self.objective, "OBJECTIVE")
        _text(self.world_id, "WORLD_ID")
        if self.required_capabilities != _canonical_strings(
            self.required_capabilities, "REQUIRED_CAPABILITY"
        ):
            raise ValueError("REQUIRED_CAPABILITIES_MUST_BE_CANONICAL")
        _text(self.model_family, "MODEL_FAMILY")
        if self.available_tools != _canonical_strings(
            self.available_tools, "AVAILABLE_TOOL", allow_empty=True
        ):
            raise ValueError("AVAILABLE_TOOLS_MUST_BE_CANONICAL")
        _text(self.skill_registry_generation, "SKILL_REGISTRY_GENERATION")
        _text(self.tool_registry_generation, "TOOL_REGISTRY_GENERATION")
        _text(self.authority_scope, "AUTHORITY_SCOPE")


@dataclass(frozen=True)
class SkillRouteCard:
    """Persistent Wiki/registry projection of one reusable procedure.

    PURPOSE/pattern provenance and validation generation remain explicit so a
    skill can be reused without erasing why it exists or whether it transferred
    safely to the current model/tool environment.
    """

    schema: str
    skill_id: str
    skill_generation: str
    name: str
    kind: str
    path: str
    description: str
    capabilities: tuple[str, ...]
    purpose_pattern_ids: tuple[str, ...]
    required_tools: tuple[str, ...]
    source_kinds: tuple[str, ...]
    min_hydration_level: str
    compatible_model_families: tuple[str, ...]
    registry_status: str
    currentness: str
    validation_generation: str
    provenance_refs: tuple[str, ...]
    estimated_cost: float = 0.0

    def validate(self) -> None:
        if self.schema != SKILL_SCHEMA:
            raise ValueError("SKILL_SCHEMA_MISMATCH")
        for value, field in (
            (self.skill_id, "SKILL_ID"),
            (self.skill_generation, "SKILL_GENERATION"),
            (self.name, "SKILL_NAME"),
            (self.kind, "SKILL_KIND"),
            (self.path, "SKILL_PATH"),
            (self.description, "SKILL_DESCRIPTION"),
            (self.validation_generation, "SKILL_VALIDATION_GENERATION"),
        ):
            _text(value, field)
        for values, field, allow_empty in (
            (self.capabilities, "SKILL_CAPABILITY", False),
            (self.purpose_pattern_ids, "PURPOSE_PATTERN_ID", True),
            (self.required_tools, "REQUIRED_TOOL", True),
            (self.source_kinds, "SOURCE_KIND", False),
            (self.compatible_model_families, "MODEL_FAMILY", False),
            (self.provenance_refs, "PROVENANCE_REF", False),
        ):
            if values != _canonical_strings(values, field, allow_empty=allow_empty):
                raise ValueError(f"{field}S_MUST_BE_CANONICAL")
        _level_index(self.min_hydration_level)
        if self.registry_status not in SKILL_STATES:
            raise ValueError("SKILL_REGISTRY_STATUS_INVALID")
        if self.currentness not in CURRENTNESS:
            raise ValueError("SKILL_CURRENTNESS_INVALID")
        if not isinstance(self.estimated_cost, (int, float)) or self.estimated_cost < 0:
            raise ValueError("SKILL_ESTIMATED_COST_INVALID")

    @property
    def identity(self) -> str:
        self.validate()
        return _sha(
            {
                "schema": self.schema,
                "skill_id": self.skill_id,
                "skill_generation": self.skill_generation,
                "validation_generation": self.validation_generation,
            }
        )


def _skill_rejection_reason(card: SkillRouteCard, objective: ObjectiveRouteProfile) -> str | None:
    if card.registry_status not in {"EXISTING", "EVOLVED_ACCEPTED"}:
        return f"SKILL_{card.registry_status}_NOT_ROUTABLE"
    if card.currentness != "CURRENT":
        return f"SKILL_{card.currentness}_REVALIDATION_REQUIRED"
    if "*" not in card.compatible_model_families and objective.model_family not in card.compatible_model_families:
        return "MODEL_COMPATIBILITY_NOT_ESTABLISHED"
    missing_tools = set(card.required_tools) - set(objective.available_tools)
    if missing_tools:
        return "REQUIRED_TOOLS_UNAVAILABLE:" + ",".join(sorted(missing_tools))
    if not (set(card.capabilities) & set(objective.required_capabilities)):
        return "NO_REQUIRED_CAPABILITY_OVERLAP"
    return None


def _minimal_cover(
    required: set[str],
    cards: Sequence[SkillRouteCard],
) -> tuple[SkillRouteCard, ...]:
    """Exact deterministic set cover for a deliberately bounded WorkCapsule frontier."""
    if not required:
        return ()
    if len(cards) > 20:
        raise ValueError("EXACT_SKILL_FRONTIER_TOO_LARGE_REQUIRES_HYPERSCALE_REDUCTION")
    useful = [card for card in cards if set(card.capabilities) & required]
    for size in range(1, len(useful) + 1):
        winners: list[tuple[float, tuple[str, ...], tuple[SkillRouteCard, ...]]] = []
        for combo in itertools.combinations(useful, size):
            covered: set[str] = set()
            for card in combo:
                covered.update(card.capabilities)
            if required <= covered:
                winners.append(
                    (
                        sum(float(card.estimated_cost) for card in combo),
                        tuple(sorted(card.skill_id for card in combo)),
                        tuple(combo),
                    )
                )
        if winners:
            winners.sort(key=lambda row: (row[0], row[1]))
            return tuple(sorted(winners[0][2], key=lambda c: c.skill_id))
    return ()


def _world_route(node: ExternalKnowledgeNode, selected: Sequence[SkillRouteCard]) -> dict[str, Any]:
    node.validate()
    current_level = node.hydration[-1].level
    applicable = [
        card
        for card in selected
        if "*" in card.source_kinds or node.subject.source_kind in card.source_kinds
    ]
    target_level = max(
        (card.min_hydration_level for card in applicable),
        key=_level_index,
        default="L0",
    )

    if node.knowledge_state != KnowledgeState.CURRENT_REFERENCE:
        disposition = "REVERIFY_CURRENTNESS_BEFORE_ACTIVE_HYDRATION"
    elif _level_index(current_level) < _level_index(target_level):
        disposition = f"HYDRATE_{current_level}_TO_{target_level}"
    else:
        disposition = "REUSE_CURRENT_HYDRATION"

    return {
        "subject_key": node.subject_key,
        "evidence_generation_key": node.evidence_generation_key,
        "provider": node.subject.provider,
        "source_kind": node.subject.source_kind,
        "canonical_id": node.subject.canonical_id,
        "knowledge_state": node.knowledge_state.value,
        "current_hydration_level": current_level,
        "required_hydration_level": target_level,
        "hydration_disposition": disposition,
        "k27_xyz": list(node.coordinate.k27_xyz),
        "exact_source_uri": node.observation.exact_source_uri,
        "validation_fingerprint": node.validation_fingerprint,
        "node_digest": node.node_digest,
        "coordinate_is_authority": False,
    }


def compile_world_skill_workcapsule(
    *,
    objective: ObjectiveRouteProfile,
    external_nodes: Sequence[ExternalKnowledgeNode],
    skill_cards: Sequence[SkillRouteCard],
) -> dict[str, Any]:
    """Compile a small, non-authorizing WorkCapsule routing projection.

    The persistent wiki/registry may be large.  This receipt carries only the
    selected skill identities/procedures and bounded World routes needed by the
    current objective.  Rejected skill details remain audit/wiki state instead
    of being injected into the hot capsule.
    """
    objective.validate()
    if not external_nodes:
        raise ValueError("WORLD_ROUTE_REQUIRES_AT_LEAST_ONE_EXTERNAL_NODE")
    for node in external_nodes:
        if not isinstance(node, ExternalKnowledgeNode):
            raise TypeError("EXTERNAL_KNOWLEDGE_NODE_REQUIRED")
        node.validate()
    for card in skill_cards:
        if not isinstance(card, SkillRouteCard):
            raise TypeError("SKILL_ROUTE_CARD_REQUIRED")
        card.validate()

    ordered_cards = sorted(skill_cards, key=lambda c: (c.skill_id, c.skill_generation))
    rejection_reasons: dict[str, str] = {}
    eligible: list[SkillRouteCard] = []
    for card in ordered_cards:
        reason = _skill_rejection_reason(card, objective)
        if reason is None:
            eligible.append(card)
        else:
            rejection_reasons[card.identity] = reason

    required = set(objective.required_capabilities)
    selected = _minimal_cover(required, eligible)
    covered: set[str] = set()
    for card in selected:
        covered.update(card.capabilities)
    uncovered = tuple(sorted(required - covered))

    routes = sorted(
        (_world_route(node, selected) for node in external_nodes),
        key=lambda row: (row["subject_key"], row["evidence_generation_key"]),
    )

    selected_projection = [
        {
            "skill_identity": card.identity,
            "skill_id": card.skill_id,
            "skill_generation": card.skill_generation,
            "name": card.name,
            "kind": card.kind,
            "path": card.path,
            "description": card.description,
            "capabilities": list(card.capabilities),
            "purpose_pattern_ids": list(card.purpose_pattern_ids),
            "required_tools": list(card.required_tools),
            "min_hydration_level": card.min_hydration_level,
            "validation_generation": card.validation_generation,
            "provenance_refs": list(card.provenance_refs),
        }
        for card in selected
    ]

    negative_space = [
        {
            "kind": "CAPABILITY",
            "value": capability,
            "disposition": "NO_ELIGIBLE_SKILL_IN_SUPPLIED_REGISTRY_GENERATION",
            "global_absence_claimed": False,
        }
        for capability in uncovered
    ]
    for route in routes:
        if route["knowledge_state"] != KnowledgeState.CURRENT_REFERENCE.value:
            negative_space.append(
                {
                    "kind": "CURRENTNESS",
                    "value": route["subject_key"],
                    "disposition": "CURRENT_REFERENCE_NOT_ESTABLISHED",
                    "global_absence_claimed": False,
                }
            )

    cache_basis = {
        "schema": ROUTE_CACHE_SCHEMA,
        "objective_id": objective.objective_id,
        "world_id": objective.world_id,
        "required_capabilities": objective.required_capabilities,
        "model_family": objective.model_family,
        "available_tools": objective.available_tools,
        "skill_registry_generation": objective.skill_registry_generation,
        "tool_registry_generation": objective.tool_registry_generation,
        "authority_scope": objective.authority_scope,
        "world_generations": [
            (route["subject_key"], route["evidence_generation_key"])
            for route in routes
        ],
        "selected_skill_generations": [
            (card.skill_id, card.skill_generation, card.validation_generation)
            for card in selected
        ],
        "hydration_policy": HYDRATION_POLICY,
    }
    route_cache_key = _sha(cache_basis)

    planning_complete = not uncovered
    all_world_current = all(
        route["knowledge_state"] == KnowledgeState.CURRENT_REFERENCE.value
        for route in routes
    )

    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "owner_mode": "DERIVED_WORLD_SKILL_WORKCAPSULE_PLANNING_MEMBRANE",
        "objective": asdict(objective),
        "workcapsule_target": {
            "schema_id": WORKCAPSULE_TARGET_SCHEMA,
            "schema_version": WORKCAPSULE_TARGET_VERSION,
        },
        "world_routes": routes,
        "selected_skills": selected_projection,
        "selected_skill_count": len(selected_projection),
        "eligible_skill_count": len(eligible),
        "rejected_skill_count": len(rejection_reasons),
        "rejection_reason_digest": _sha(rejection_reasons),
        "negative_space": negative_space,
        "planning_complete": planning_complete,
        "world_current_for_read_only_reference": all_world_current,
        "route_cache_key": route_cache_key,
        "route_cache_basis_digest": _sha(cache_basis),
        "laws": {
            "search_miss_is_known_absence": False,
            "cache_hit_is_currentness_witness": False,
            "k27_coordinate_is_semantic_identity": False,
            "wiki_is_hot_execution_context": False,
            "skill_discovery_is_skill_acceptance": False,
            "skill_selection_is_execution_authority": False,
            "coordinate_memory_is_model_prefix_kv": False,
        },
        "authority": {
            "semantic_truth_minted": False,
            "source_currentness_minted": False,
            "skill_acceptance_minted": False,
            "tool_use_authorized": False,
            "code_execution_authorized": False,
            "model_download_authorized": False,
            "network_write_authorized": False,
            "provider_effect_authorized": False,
            "workcapsule_execution_authorized": False,
            "gate10_promoted": False,
            "native_private_transformer_kv_accessed": False,
        },
    }
    receipt["receipt_digest"] = _sha(receipt)
    return receipt


def verify_world_skill_workcapsule(receipt: dict[str, Any]) -> list[str]:
    """Detect authority/currentness/cache laundering in a compiled receipt."""
    violations: list[str] = []
    if receipt.get("schema") != SCHEMA:
        violations.append("SCHEMA_MISMATCH")
    authority = receipt.get("authority")
    laws = receipt.get("laws")
    if not isinstance(authority, dict) or not isinstance(laws, dict):
        return violations + ["MALFORMED_CLAIM_CEILING"]
    if any(bool(v) for v in authority.values()):
        violations.append("PLANNER_MINTED_AUTHORITY")
    for forbidden_true in (
        "search_miss_is_known_absence",
        "cache_hit_is_currentness_witness",
        "k27_coordinate_is_semantic_identity",
        "wiki_is_hot_execution_context",
        "skill_discovery_is_skill_acceptance",
        "skill_selection_is_execution_authority",
        "coordinate_memory_is_model_prefix_kv",
    ):
        if laws.get(forbidden_true) is not False:
            violations.append("LAW_WIDENED:" + forbidden_true)
    supplied = receipt.get("receipt_digest")
    without = dict(receipt)
    without.pop("receipt_digest", None)
    if supplied != _sha(without):
        violations.append("RECEIPT_DIGEST_MISMATCH")
    return violations
