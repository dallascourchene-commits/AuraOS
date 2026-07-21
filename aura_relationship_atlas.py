"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9e7-[Q-SYS:RELATIONSHIP_ATLAS]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Architecture Relationship Atlas Plane)
DEPENDENCIES: __future__, dataclasses, enum, hashlib, json, os, pathlib, re, time, typing
FUNCTIONS: build_relationship_atlas, load_relationship_atlas, validate_relationship_atlas, relationship_assessment, relationships_for_participant, relationships_for_objective, find_overlapping_unwired, find_auxiliary_adjacent, find_missing_configurations, find_candidate_wirings, find_prohibited_wirings, explain_relationship, diff_relationship_atlases, compile_atlas_projection
SYNOPSIS: Compiles, classifies, and projects the architectural relationship status plane of AuraOS.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import argparse
from collections import OrderedDict
from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import time
from typing import Any, Mapping, Sequence

from aura_event_contracts import stable_digest

# ---------------------------------------------------------------------------
# Constants and Versions
# ---------------------------------------------------------------------------
ATLAS_SNAPSHOT_VERSION = "AURA_ARCHITECTURE_RELATIONSHIP_ATLAS_V1"
ATLAS_RELATIONSHIP_ASSESSMENT_VERSION = "AURA_RELATIONSHIP_ASSESSMENT_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

DEFAULT_ATLAS_PATH = Path(".aura/RELATIONSHIP_ATLAS.json")
DEFAULT_RECEIPT_PATH = Path(".aura/RELATIONSHIP_ATLAS_RECEIPT.json")
DEFAULT_MARKDOWN_PATH = Path(".aura/RELATIONSHIP_ATLAS.md")

ATLAS_GENERATED_PATHS = frozenset({
    DEFAULT_ATLAS_PATH.as_posix(),
    DEFAULT_RECEIPT_PATH.as_posix(),
    DEFAULT_MARKDOWN_PATH.as_posix(),
})


# ---------------------------------------------------------------------------
# Enums and Types
# ---------------------------------------------------------------------------
class StructuralStatus(str, Enum):
    EXACTLY_WIRED = "EXACTLY_WIRED"
    DECLARED_WIRED = "DECLARED_WIRED"
    UNWIRED = "UNWIRED"
    PARTIALLY_WIRED = "PARTIALLY_WIRED"
    TEMPORARILY_WIRED = "TEMPORARILY_WIRED"
    STALE_WIRING = "STALE_WIRING"
    UNRESOLVED = "UNRESOLVED"


class SemanticRelationship(str, Enum):
    DIRECTLY_RELATED = "DIRECTLY_RELATED"
    OVERLAPPING = "OVERLAPPING"
    COMPLEMENTARY = "COMPLEMENTARY"
    AUXILIARY = "AUXILIARY"
    ADJACENT = "ADJACENT"
    REDUNDANT = "REDUNDANT"
    COMPETING = "COMPETING"
    UNRELATED = "UNRELATED"
    CONTRADICTED = "CONTRADICTED"


class WiringDisposition(str, Enum):
    REQUIRED = "REQUIRED"
    RECOMMENDED = "RECOMMENDED"
    OPTIONAL = "OPTIONAL"
    CANDIDATE = "CANDIDATE"
    DEFERRED = "DEFERRED"
    NOT_NEEDED = "NOT_NEEDED"
    PROHIBITED = "PROHIBITED"


class Readiness(str, Enum):
    READY = "READY"
    NEEDS_GROUNDING = "NEEDS_GROUNDING"
    NEEDS_MISSING_ROLE = "NEEDS_MISSING_ROLE"
    NEEDS_SCHEMA = "NEEDS_SCHEMA"
    NEEDS_TEST = "NEEDS_TEST"
    NEEDS_VERIFIER = "NEEDS_VERIFIER"
    NEEDS_AUTHORITY = "NEEDS_AUTHORITY"
    NEEDS_CONSENT = "NEEDS_CONSENT"
    NEEDS_LEASE = "NEEDS_LEASE"
    NEEDS_RESEARCH = "NEEDS_RESEARCH"
    TOO_RISKY = "TOO_RISKY"
    DREAM_ONLY = "DREAM_ONLY"


class Lifecycle(str, Enum):
    PERSISTENT = "PERSISTENT"
    OBJECTIVE_SCOPED = "OBJECTIVE_SCOPED"
    LEASED = "LEASED"
    EPHEMERAL = "EPHEMERAL"
    DORMANT = "DORMANT"
    DEPRECATED = "DEPRECATED"
    DISSOLVED = "DISSOLVED"


class TruthClass(str, Enum):
    EXACT_SOURCE = "EXACT_SOURCE"
    EXACT_SCHEMA = "EXACT_SCHEMA"
    EXACT_TEST = "EXACT_TEST"
    EXACT_MANIFEST = "EXACT_MANIFEST"
    EXACT_RUNTIME = "EXACT_RUNTIME"
    ADVISORY_CONNECTOME = "ADVISORY_CONNECTOME"
    ADVISORY_AFFINITY = "ADVISORY_AFFINITY"
    INFERRED_MOTIF = "INFERRED_MOTIF"
    UNRESOLVED = "UNRESOLVED"


class AuthorityPosture(str, Enum):
    READ_ONLY = "READ_ONLY"
    ADVISORY_ONLY = "ADVISORY_ONLY"
    PROPOSAL_ONLY = "PROPOSAL_ONLY"
    VERIFIER_REQUIRED = "VERIFIER_REQUIRED"
    HUMAN_AUTHORIZATION_REQUIRED = "HUMAN_AUTHORIZATION_REQUIRED"
    COMMUNITY_AUTHORIZATION_REQUIRED = "COMMUNITY_AUTHORIZATION_REQUIRED"
    MUTATION_LEASE_REQUIRED = "MUTATION_LEASE_REQUIRED"
    EXECUTION_ALLOWED = "EXECUTION_ALLOWED"
    EXECUTION_PROHIBITED = "EXECUTION_PROHIBITED"


class ProofStatus(str, Enum):
    OPEN = "OPEN"
    SATISFIED = "SATISFIED"
    CONTRADICTED = "CONTRADICTED"
    DEFERRED = "DEFERRED"


class OperationalProfile(str, Enum):
    """Atlas scan profile controlling global coverage versus objective-local depth."""
    MINIMAL = "MINIMAL"
    STANDARD = "STANDARD"
    DEEP = "DEEP"
    MINIMAL_GLOBAL = "MINIMAL_GLOBAL"
    OBJECTIVE_STANDARD = "OBJECTIVE_STANDARD"
    OBJECTIVE_DEEP = "OBJECTIVE_DEEP"


# Profile configuration: which scan features are enabled at each level
PROFILE_CONFIG: dict[OperationalProfile, dict[str, bool]] = {
    OperationalProfile.MINIMAL: {
        "exact_relations": True,
        "declared_relations": True,
        "applicable_prohibitions": True,
        "one_hop_missing_roles": True,
        "overlap_detection": False,
        "auxiliary_detection": False,
        "candidate_discovery": False,
        "motif_search": False,
        "redundancy_competition": False,
        "cross_arena_candidates": False,
    },
    OperationalProfile.STANDARD: {
        "exact_relations": True,
        "declared_relations": True,
        "applicable_prohibitions": True,
        "one_hop_missing_roles": True,
        "overlap_detection": True,
        "auxiliary_detection": True,
        "candidate_discovery": True,
        "motif_search": True,
        "redundancy_competition": False,
        "cross_arena_candidates": False,
    },
    OperationalProfile.DEEP: {
        "exact_relations": True,
        "declared_relations": True,
        "applicable_prohibitions": True,
        "one_hop_missing_roles": True,
        "overlap_detection": True,
        "auxiliary_detection": True,
        "candidate_discovery": True,
        "motif_search": True,
        "redundancy_competition": True,
        "cross_arena_candidates": True,
    },
}
PROFILE_CONFIG[OperationalProfile.MINIMAL_GLOBAL] = dict(PROFILE_CONFIG[OperationalProfile.MINIMAL])
PROFILE_CONFIG[OperationalProfile.OBJECTIVE_STANDARD] = dict(PROFILE_CONFIG[OperationalProfile.STANDARD])
PROFILE_CONFIG[OperationalProfile.OBJECTIVE_DEEP] = dict(PROFILE_CONFIG[OperationalProfile.DEEP])

GLOBAL_ATLAS_PAIR_LIMIT = 32_640
OBJECTIVE_ATLAS_MAX_PARTICIPANTS = 256
OBJECTIVE_ATLAS_CACHE_MAX_BYTES = 8_000_000
_OBJECTIVE_ATLAS_CACHE: "OrderedDict[tuple[str, str, str, str], tuple[dict[str, Any], int]]" = OrderedDict()
_OBJECTIVE_ATLAS_CACHE_BYTES = 0


# ---------------------------------------------------------------------------
# Data Contracts
# ---------------------------------------------------------------------------
@dataclass
class AtlasParticipantRef:
    participant_id: str
    participant_digest: str
    participant_type: str
    canonical_owner: str
    canonical_ref: str
    freshness: str = "CURRENT"

    def to_dict(self) -> dict[str, Any]:
        """Serialize the participant reference to a canonical dict."""
        return asdict(self)


@dataclass
class AtlasRelationshipAssessment:
    assessment_id: str
    assessment_version: str
    participant_refs: list[AtlasParticipantRef]
    role_bindings: dict[str, str]
    relation_types: list[str]
    structural_status: StructuralStatus
    semantic_relationship: SemanticRelationship
    wiring_disposition: WiringDisposition
    readiness: Readiness
    lifecycle: Lifecycle
    truth_class: str
    proof_status: ProofStatus
    canonical_owner_refs: list[str]
    evidence_refs: list[str]
    missing_roles: list[str]
    required_adapters: list[str]
    authority_constraints: list[str]
    temporal_conditions: list[str]
    expected_benefits: list[str]
    risks: list[str]
    prohibited_effects: list[str]
    relationships_to_preserve: list[str]
    confidence: float
    freshness: str
    boundary: dict[str, Any] = field(default_factory=dict)
    assessment_digest: str = ""
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    def __post_init__(self) -> None:
        """Validate canonical owner refs and compute the assessment digest."""
        if not self.canonical_owner_refs:
            raise ValueError("Every Atlas assessment must reference at least one canonical owner.")
        if not self.assessment_digest:
            self.assessment_digest = self.compute_digest()

    def compute_digest(self) -> str:
        """Hash every serialized assessment field except the digest itself."""
        data = self.to_dict()
        data.pop("assessment_digest", None)
        serialized = json.dumps(
            data, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        """Serialize the assessment to a canonical dict with enum values as strings."""
        d = asdict(self)
        d["structural_status"] = self.structural_status.value
        d["semantic_relationship"] = self.semantic_relationship.value
        d["wiring_disposition"] = self.wiring_disposition.value
        d["readiness"] = self.readiness.value
        d["lifecycle"] = self.lifecycle.value
        d["proof_status"] = self.proof_status.value
        return d


@dataclass
class MissingRelationalConfiguration:
    configuration_id: str
    motif_type: str
    objective_family: str
    bound_roles: dict[str, str]
    missing_roles: list[str]
    existing_relations: list[str]
    missing_relations: list[str]
    completion_ratio: float
    candidate_participants_by_role: dict[str, list[str]]
    hard_blockers: list[str]
    required_evidence: list[str]
    required_verifiers: list[str]
    required_authority: list[str]
    expected_capability: str
    risk_class: str
    truth_class: str = "INFERRED_MOTIF"

    def to_dict(self) -> dict[str, Any]:
        """Serialize the missing configuration to a canonical dict."""
        return asdict(self)


@dataclass
class RelationshipProhibition:
    prohibition_id: str
    pattern: str
    participant_types: list[str]
    relation_types: list[str]
    prohibition_family: str
    reason: str
    canonical_rule_refs: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    exceptions: list[str] = field(default_factory=list)
    current_reproof_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Serialize the prohibition record to a canonical dict."""
        return asdict(self)


@dataclass
class AtlasSnapshot:
    snapshot_version: str
    repository_head: str
    working_tree_digest: str
    codemap_digest: str
    topology_digest: str
    connectome_digest: str
    atomic_inventory_digest: str
    relational_index_digest: str
    atlas_ontology_digest: str
    prohibition_registry_digest: str
    motif_registry_digest: str
    profile_digest: str
    assessments: list[AtlasRelationshipAssessment]
    missing_configurations: list[MissingRelationalConfiguration]
    prohibitions: list[RelationshipProhibition]
    reverse_indexes: dict[str, list[str]]
    boundary: dict[str, Any]
    snapshot_digest: str = ""

    def __post_init__(self) -> None:
        """Compute the snapshot digest if not already set."""
        if not self.snapshot_digest:
            self.snapshot_digest = self.compute_digest()

    def compute_digest(self) -> str:
        """Hash the complete serialized Atlas snapshot except the digest itself."""
        data = self.to_dict()
        data.pop("snapshot_digest", None)
        serialized = json.dumps(
            data, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        """Serialize the full snapshot to a canonical dict for persistence."""
        return {
            "snapshot_version": self.snapshot_version,
            "repository_head": self.repository_head,
            "working_tree_digest": self.working_tree_digest,
            "codemap_digest": self.codemap_digest,
            "topology_digest": self.topology_digest,
            "connectome_digest": self.connectome_digest,
            "atomic_inventory_digest": self.atomic_inventory_digest,
            "relational_index_digest": self.relational_index_digest,
            "atlas_ontology_digest": self.atlas_ontology_digest,
            "prohibition_registry_digest": self.prohibition_registry_digest,
            "motif_registry_digest": self.motif_registry_digest,
            "profile_digest": self.profile_digest,
            "assessments": [a.to_dict() for a in self.assessments],
            "missing_configurations": [m.to_dict() for m in self.missing_configurations],
            "prohibitions": [p.to_dict() for p in self.prohibitions],
            "reverse_indexes": self.reverse_indexes,
            "boundary": self.boundary,
            "snapshot_digest": self.snapshot_digest,
        }


@dataclass
class AtlasDeltaReceipt:
    previous_snapshot_digest: str
    current_snapshot_digest: str
    changed_participants: list[str] = field(default_factory=list)
    added_exact_relations: list[str] = field(default_factory=list)
    removed_exact_relations: list[str] = field(default_factory=list)
    reclassified_relationships: list[str] = field(default_factory=list)
    new_candidates: list[str] = field(default_factory=list)
    resolved_candidates: list[str] = field(default_factory=list)
    new_prohibitions: list[str] = field(default_factory=list)
    resolved_missing_roles: list[str] = field(default_factory=list)
    new_missing_roles: list[str] = field(default_factory=list)
    stale_assessments: list[str] = field(default_factory=list)
    verification_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the delta receipt to a canonical dict."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Built-in Registry and Motif Specifications (spec §8.6 & §12)
# ---------------------------------------------------------------------------
BUILTIN_PROHIBITIONS: list[RelationshipProhibition] = [
    RelationshipProhibition(
        prohibition_id="prohib_000000000000000000000001",
        pattern="affinity_mutation_block",
        participant_types=["atomic_symbol", "capability"],
        relation_types=["REQUIRES_AUTHORITY"],
        prohibition_family="authority",
        reason="Fuzzy VSA/affinity similarity must never authorize a codebase mutation or patch approval.",
        canonical_rule_refs=["ARCHITECTURE.md#2.1", "README.md#truth-authority-and-safety"],
        exceptions=[]
    ),
    RelationshipProhibition(
        prohibition_id="prohib_000000000000000000000002",
        pattern="self_verification_block",
        participant_types=["verifier", "atomic_symbol"],
        relation_types=["VERIFIED_BY", "CORROBORATED_BY"],
        prohibition_family="security",
        reason="A component producer must not verify its own evidence or results without independent verifier corroboration.",
        canonical_rule_refs=["ARCHITECTURE.md#8.5", "AURA_EPHEMERAL_SECURITY_MODEL.md"],
        exceptions=[]
    ),
    RelationshipProhibition(
        prohibition_id="prohib_000000000000000000000003",
        pattern="agent_self_upgrade_block",
        participant_types=["agent", "capability"],
        relation_types=["IMPLEMENTS_CAPABILITY"],
        prohibition_family="truth_ownership",
        reason="External agents are forbidden from self-upgrading their candidate connections to exact wiring status.",
        canonical_rule_refs=["AURA_AGENT_ARENA_BRIDGE.md"],
        exceptions=[]
    ),
    RelationshipProhibition(
        prohibition_id="prohib_000000000000000000000004",
        pattern="circular_authorization_block",
        participant_types=["authority", "authority"],
        relation_types=["REQUIRES_AUTHORITY"],
        prohibition_family="recursion",
        reason="Circular authority paths where A authorizes B and B authorizes A are architecturally prohibited.",
        canonical_rule_refs=["ARCHITECTURE.md#2.4"],
        exceptions=[]
    ),
    RelationshipProhibition(
        prohibition_id="prohib_000000000000000000000005",
        pattern="ephemeral_lease_leak_block",
        participant_types=["lease", "state"],
        relation_types=["DISSOLVES_AFTER"],
        prohibition_family="lifecycle",
        reason="Ephemeral capability leases and temporary organ state must not persist beyond their specified TTL.",
        canonical_rule_refs=["AURA_EPHEMERAL_ORGAN_RUNTIME.md"],
        exceptions=[]
    ),
    RelationshipProhibition(
        prohibition_id="prohib_000000000000000000000006",
        pattern="research_production_coupling_block",
        participant_types=["research_artifact", "atomic_symbol"],
        relation_types=["REPAIRED_BY", "IMPLEMENTS_CAPABILITY"],
        prohibition_family="domain",
        reason="Direct coupling of production runtime or codebase mutation to unverified research memory is prohibited.",
        canonical_rule_refs=["README.md#research-relations"],
        exceptions=[]
    ),
    RelationshipProhibition(
        prohibition_id="prohib_000000000000000000000007",
        pattern="cross_arena_coupling_block",
        participant_types=["arena", "arena"],
        relation_types=["CALLS", "WRITES_STATE"],
        prohibition_family="domain",
        reason="Direct un-adapted coupling of state or calling sequences between isolated Arenas is prohibited.",
        canonical_rule_refs=["README.md#the-arena-system"],
        exceptions=[]
    )
]

BUILTIN_MOTIFS: dict[str, dict[str, Any]] = {
    "input_to_authority": {
        "motif_type": "input_to_authority",
        "required_roles": ["external_input", "parser", "schema_validator", "authority_guard", "verifier"],
        "expected_capability": "admitted_governed_operation",
        "risk_class": "HIGH"
    },
    "state_lifecycle": {
        "motif_type": "state_lifecycle",
        "required_roles": ["state_read", "transformation", "state_write", "persistence", "restore", "invalidation"],
        "expected_capability": "safe_state_management",
        "risk_class": "CRITICAL"
    },
    "review_packet_integrity": {
        "motif_type": "review_packet_integrity",
        "required_roles": ["focal_symbol", "dependency_closure", "exact_endpoints", "source_slices", "verifier"],
        "expected_capability": "verifiable_review_packet",
        "risk_class": "HIGH"
    },
    "external_agent_lease": {
        "motif_type": "external_agent_lease",
        "required_roles": ["objective", "route", "lease", "temporary_identity", "verifier", "dissolution"],
        "expected_capability": "governed_external_agent_task",
        "risk_class": "CRITICAL"
    },
    "learning_to_reproof": {
        "motif_type": "learning_to_reproof",
        "required_roles": ["finding", "grounding", "crucible_proposal", "validation", "current_reproof"],
        "expected_capability": "verified_empirical_learning",
        "risk_class": "MEDIUM"
    },
    "spatial_explanation": {
        "motif_type": "spatial_explanation",
        "required_roles": ["participant", "assessment", "scene_projection", "drill_down"],
        "expected_capability": "grounded_visual_orientation",
        "risk_class": "LOW"
    },
    "cross_arena_adapter": {
        "motif_type": "cross_arena_adapter",
        "required_roles": ["source_arena", "export_schema", "privacy_filter", "adapter", "destination_arena"],
        "expected_capability": "sovereign_arena_federation",
        "risk_class": "HIGH"
    }
}


# ---------------------------------------------------------------------------
# Relational Index Freshness Validation
# ---------------------------------------------------------------------------
def _current_relational_index_identity(
    repo_root: Path,
    relational_index: Mapping[str, Any],
) -> dict[str, Any]:
    """Recompute the canonical repository identity for an in-memory index."""
    from aura_relational_index import RelationalIndexBuilder

    profile = relational_index.get("profile") or {}
    profile_name = str(profile.get("name") or "MINIMAL") if isinstance(profile, Mapping) else "MINIMAL"
    return RelationalIndexBuilder(repo_root, profile=profile_name).repository_identity_snapshot()


def _validate_relational_index_freshness(
    repo_root: Path,
    relational_index: Mapping[str, Any],
    *,
    index_label: Path,
) -> None:
    """Fail closed unless the index identity exactly matches the checkout."""
    from aura_relational_index import _REPOSITORY_IDENTITY_KEYS

    stored = relational_index.get("repository_identity")
    if not isinstance(stored, Mapping):
        raise ValueError(
            f"Relational index at {index_label} is missing repository_identity. "
            "Please rebuild it from the current repository head."
        )
    current = _current_relational_index_identity(repo_root, relational_index)
    mismatches = {
        name: {"stored": stored.get(name), "current": current.get(name)}
        for name in sorted(_REPOSITORY_IDENTITY_KEYS)
        if stored.get(name) != current.get(name)
    }
    if mismatches:
        names = ", ".join(mismatches)
        raise ValueError(
            f"Relational index at {index_label} is STALE for the current repository "
            f"identity ({names}). Please rebuild the relational index."
        )


# ---------------------------------------------------------------------------
# Core Public API Functions
# ---------------------------------------------------------------------------
def build_relationship_atlas(
    repo_root: Path = Path("."),
    relational_index_path: Path | None = None,
    output_path: Path | None = None,
    receipt_path: Path | None = None,
    profile: str | OperationalProfile = "STANDARD",
    *,
    relational_index_data: Mapping[str, Any] | None = None,
    persist: bool = True,
) -> AtlasSnapshot:
    """Ahead-of-Time relationship classification compile pass.

    The Atlas is a compiled view over the existing Relational Index — it never
    duplicates truth, only classifies and projects. The *profile* argument
    controls scan depth: MINIMAL (exact + prohibitions only), STANDARD (adds
    overlap/auxiliary/candidate/motif), or DEEP (adds redundancy/competition
    and cross-Arena candidate generation).
    """
    idx_path = relational_index_path or repo_root / ".aura" / "RELATIONAL_INDEX.json"
    out_path = output_path or repo_root / DEFAULT_ATLAS_PATH
    rec_path = receipt_path or repo_root / DEFAULT_RECEIPT_PATH

    # Resolve operational profile
    if isinstance(profile, str):
        op_profile = OperationalProfile(profile.upper())
    else:
        op_profile = profile
    prof_cfg = PROFILE_CONFIG[op_profile]
    objective_scoped = op_profile in {
        OperationalProfile.OBJECTIVE_STANDARD,
        OperationalProfile.OBJECTIVE_DEEP,
    }

    # 1. Fail closed on stale or missing index. Callers that already hold the
    # exact generated index may supply it directly for a read-only in-memory
    # compile; the canonical persisted workflow remains the default.
    if relational_index_data is None:
        if not idx_path.exists():
            raise FileNotFoundError(
                f"Relational index is stale or missing at {idx_path}. "
                "Please run 'python aura_relational_index.py build' first."
            )
        with idx_path.open("r", encoding="utf-8") as f:
            rel_index = json.load(f)
    else:
        rel_index = dict(relational_index_data)

    # Validate index freshness — fail closed on stale or missing identity.
    # This recomputes the checkout identity rather than trusting CURRENT flags
    # or caller-supplied digest metadata.
    _validate_relational_index_freshness(
        repo_root.resolve(),
        rel_index,
        index_label=idx_path,
    )
    index_digest = rel_index.get("index_digest", "")
    if not index_digest:
        raise ValueError(
            f"Relational index at {idx_path} is missing index_digest. "
            "The index may be corrupted or built by an incompatible version. "
            "Please run 'python aura_relational_index.py build' first."
        )
    # Check that participants carry freshness metadata
    participants_early = rel_index.get("participants", [])
    stale_participants = [p.get("participant_id", "?") for p in participants_early
                          if p.get("freshness", "CURRENT") == "STALE"]
    if stale_participants:
        raise ValueError(
            f"Relational index at {idx_path} contains STALE participants: {stale_participants[:5]}. "
            "Please rebuild the relational index from the current repository head."
        )

    # Validate index identity metadata — use real digests from the index
    rep_identity = rel_index.get("repository_identity", {})
    repo_head = rep_identity.get("repo_head", "unknown_head")
    working_tree_digest = rep_identity.get("working_tree_digest", "dirty")
    codemap_digest = rep_identity.get("codemap_digest", "")
    topology_digest = rep_identity.get("topology_digest", "")
    connectome_digest = rep_identity.get("connectome_graph_digest", "connectome_digest_placeholder")
    atomic_inventory_digest = rep_identity.get("atomic_inventory_digest", "atomic_digest_placeholder")
    profile_digest = rep_identity.get("profile_digest", "profile_digest_placeholder")

    # Get exact index list of participants and relations
    participants_raw = rel_index.get("participants", [])
    relations_raw = rel_index.get("relations", [])
    groups_raw = rel_index.get("groups", [])
    participant_pair_count = len(participants_raw) * (len(participants_raw) - 1) // 2
    if objective_scoped and len(participants_raw) > OBJECTIVE_ATLAS_MAX_PARTICIPANTS:
        raise ValueError("objective-scoped Atlas exceeds the bounded participant limit")
    if (
        op_profile in {OperationalProfile.STANDARD, OperationalProfile.DEEP}
        and participant_pair_count > GLOBAL_ATLAS_PAIR_LIMIT
    ):
        raise ValueError(
            "global STANDARD/DEEP Atlas scan refused above pair limit; "
            "extract a bounded relational neighborhood and use OBJECTIVE_STANDARD/OBJECTIVE_DEEP"
        )

    # Load participants into Python objects with role and truth_class metadata
    participants: dict[str, AtlasParticipantRef] = {}
    participant_meta: dict[str, dict[str, Any]] = {}
    for p in participants_raw:
        pid = p.get("participant_id")
        participants[pid] = AtlasParticipantRef(
            participant_id=pid,
            participant_digest=p.get("digest") or "",
            participant_type=p.get("participant_type", "atomic_symbol"),
            canonical_owner=p.get("canonical_owner", ""),
            canonical_ref=p.get("canonical_ref", ""),
            freshness=p.get("freshness", "CURRENT")
        )
        participant_meta[pid] = {
            "role": p.get("role", ""),
            "truth_class": p.get("truth_class", "EXACT_SOURCE"),
            "evidence_refs": p.get("evidence_refs", []),
            "qualified_symbol": p.get("qualified_symbol", ""),
        }

    assessments: list[AtlasRelationshipAssessment] = []

    # Track existing edge pairs to separate candidates and overlaps
    wired_pairs: set[frozenset[str]] = set()

    # 2. Classify Explicitly Wired Relationships (always enabled)
    if prof_cfg["exact_relations"]:
        for r in relations_raw:
            src = r.get("source_participant_id")
            tgt = r.get("target_participant_id")
            if src not in participants or tgt not in participants:
                continue

            pair = frozenset((src, tgt))
            wired_pairs.add(pair)

            rel_type = r.get("relation_type", "CALLS")
            truth_cls = r.get("truth_class", "EXACT_SOURCE")

            # Determine enums based on relation metadata
            struc_status = StructuralStatus.EXACTLY_WIRED if truth_cls.startswith("EXACT") else StructuralStatus.DECLARED_WIRED
            sem_rel = SemanticRelationship.DIRECTLY_RELATED
            wiring_disp = WiringDisposition.REQUIRED if r.get("required", False) else WiringDisposition.RECOMMENDED
            readiness = Readiness.READY
            lifecycle = Lifecycle.PERSISTENT
            proof_stat = ProofStatus.SATISFIED if truth_cls.startswith("EXACT") else ProofStatus.OPEN

            # Create assessment referencing the canonical relational index relation ID
            assessment_id = f"atlas_{hashlib.md5(r['relation_id'].encode(), usedforsecurity=False).hexdigest()[:24]}"
            assessments.append(
                AtlasRelationshipAssessment(
                    assessment_id=assessment_id,
                    assessment_version=ATLAS_RELATIONSHIP_ASSESSMENT_VERSION,
                    participant_refs=[participants[src], participants[tgt]],
                    role_bindings={"source": src, "target": tgt},
                    relation_types=[rel_type],
                    structural_status=struc_status,
                    semantic_relationship=sem_rel,
                    wiring_disposition=wiring_disp,
                    readiness=readiness,
                    lifecycle=lifecycle,
                    truth_class=truth_cls,
                    proof_status=proof_stat,
                    canonical_owner_refs=[idx_path.name + "::" + r["relation_id"]],
                    evidence_refs=r.get("evidence_refs", []),
                    missing_roles=[],
                    required_adapters=[],
                    authority_constraints=[],
                    temporal_conditions=[],
                    expected_benefits=[],
                    risks=[],
                    prohibited_effects=[],
                    relationships_to_preserve=[],
                    confidence=1.0,
                    freshness="CURRENT"
                )
            )

    # 3. Detect Overlapping Unwired Participants
    unwired_assessments: list[AtlasRelationshipAssessment] = []
    if prof_cfg["overlap_detection"]:
        p_keys = list(participants.keys())
        for i in range(len(p_keys)):
            for j in range(i + 1, len(p_keys)):
                pid_a, pid_b = p_keys[i], p_keys[j]
                pair = frozenset((pid_a, pid_b))
                if pair in wired_pairs:
                    continue

                ref_a = participants[pid_a]
                ref_b = participants[pid_b]
                meta_a = participant_meta[pid_a]
                meta_b = participant_meta[pid_b]

                # Multi-signal overlap detection:
                # (a) shared name words (excluding common stop words)
                # (b) shared canonical owner module
                # (c) shared role
                # (d) shared truth class beyond exact
                name_a = ref_a.canonical_ref.split("::")[-1].lower() if "::" in ref_a.canonical_ref else ref_a.canonical_ref.split("/")[-1].lower()
                name_b = ref_b.canonical_ref.split("::")[-1].lower() if "::" in ref_b.canonical_ref else ref_b.canonical_ref.split("/")[-1].lower()

                overlap_words = set(name_a.split("_")) & set(name_b.split("_")) - {"aura", "test", "helper", "mock", "py", "module"}
                shared_owner = ref_a.canonical_owner and ref_a.canonical_owner == ref_b.canonical_owner
                shared_role = meta_a.get("role") and meta_a.get("role") == meta_b.get("role")
                shared_truth = (meta_a.get("truth_class") == meta_b.get("truth_class")
                                and meta_a.get("truth_class", "").startswith("ADVISORY"))

                if overlap_words or shared_owner or shared_role or shared_truth:
                    overlap_reasons = []
                    if overlap_words:
                        overlap_reasons.append(f"shared_name_words:{sorted(overlap_words)}")
                    if shared_owner:
                        overlap_reasons.append(f"shared_owner:{ref_a.canonical_owner}")
                    if shared_role:
                        overlap_reasons.append(f"shared_role:{meta_a.get('role')}")
                    if shared_truth:
                        overlap_reasons.append(f"shared_truth_class:{meta_a.get('truth_class')}")

                    assess_id = f"atlas_{hashlib.md5(f'{pid_a}_{pid_b}_overlap'.encode(), usedforsecurity=False).hexdigest()[:24]}"
                    unwired_assessments.append(
                        AtlasRelationshipAssessment(
                            assessment_id=assess_id,
                            assessment_version=ATLAS_RELATIONSHIP_ASSESSMENT_VERSION,
                            participant_refs=[ref_a, ref_b],
                            role_bindings={"candidate_a": pid_a, "candidate_b": pid_b},
                            relation_types=["SHARES_DATA_SHAPE"],
                            structural_status=StructuralStatus.UNWIRED,
                            semantic_relationship=SemanticRelationship.OVERLAPPING,
                            wiring_disposition=WiringDisposition.CANDIDATE,
                            readiness=Readiness.NEEDS_GROUNDING,
                            lifecycle=Lifecycle.PERSISTENT,
                            truth_class="ADVISORY_AFFINITY",
                            proof_status=ProofStatus.OPEN,
                            canonical_owner_refs=["aura_relationship_atlas::overlap_heuristic"],
                            evidence_refs=overlap_reasons,
                            missing_roles=[],
                            required_adapters=[],
                            authority_constraints=[],
                            temporal_conditions=[],
                            expected_benefits=["code_deduplication", "motif_completion"],
                            risks=["tight_coupling"],
                            prohibited_effects=[],
                            relationships_to_preserve=[],
                            confidence=0.7,
                            freshness="CURRENT"
                        )
                    )

    assessments.extend(unwired_assessments)

    # 3b. Detect Auxiliary and Adjacent Participants
    auxiliary_assessments: list[AtlasRelationshipAssessment] = []
    if prof_cfg["auxiliary_detection"]:
        # Auxiliary: a participant that can support explanation, testing, rollback,
        # or verification without belonging to the primary execution path.
        # Heuristic: verifier/test participants adjacent to atomic_symbol participants
        # with exact relations, or participants sharing a canonical owner module but
        # no direct relation between them.
        for i in range(len(p_keys := list(participants.keys()))):
            for j in range(i + 1, len(p_keys)):
                pid_a, pid_b = p_keys[i], p_keys[j]
                pair = frozenset((pid_a, pid_b))
                if pair in wired_pairs:
                    continue
                # Skip if already classified as overlapping
                existing_ids = {a.assessment_id for a in unwired_assessments
                                if pid_a in {p.participant_id for p in a.participant_refs}
                                and pid_b in {p.participant_id for p in a.participant_refs}}
                if existing_ids:
                    continue

                ref_a = participants[pid_a]
                ref_b = participants[pid_b]
                meta_a = participant_meta[pid_a]
                meta_b = participant_meta[pid_b]

                # Detect auxiliary: one is a verifier/test, the other is an atomic symbol
                type_a = ref_a.participant_type
                type_b = ref_b.participant_type
                is_aux = (
                    (type_a in ("verifier", "test") and type_b == "atomic_symbol") or
                    (type_b in ("verifier", "test") and type_a == "atomic_symbol")
                )

                # Also detect adjacency: participants in the same module file but not directly related
                is_adjacent = (
                    ref_a.canonical_owner and ref_a.canonical_owner == ref_b.canonical_owner
                    and type_a == type_b == "atomic_symbol"
                    and not is_aux
                )

                if is_aux or is_adjacent:
                    aux_type = "auxiliary" if is_aux else "adjacent"
                    assess_id = f"atlas_{hashlib.md5(f'{pid_a}_{pid_b}_{aux_type}'.encode(), usedforsecurity=False).hexdigest()[:24]}"
                    auxiliary_assessments.append(
                        AtlasRelationshipAssessment(
                            assessment_id=assess_id,
                            assessment_version=ATLAS_RELATIONSHIP_ASSESSMENT_VERSION,
                            participant_refs=[ref_a, ref_b],
                            role_bindings={"support": pid_a, "primary": pid_b} if is_aux else {"neighbor_a": pid_a, "neighbor_b": pid_b},
                            relation_types=["CORROBORATED_BY" if is_aux else "ADJACENT_TO"],
                            structural_status=StructuralStatus.UNWIRED,
                            semantic_relationship=SemanticRelationship.AUXILIARY if is_aux else SemanticRelationship.ADJACENT,
                            wiring_disposition=WiringDisposition.OPTIONAL,
                            readiness=Readiness.READY if is_aux else Readiness.NEEDS_GROUNDING,
                            lifecycle=Lifecycle.PERSISTENT,
                            truth_class="ADVISORY_AFFINITY",
                            proof_status=ProofStatus.OPEN,
                            canonical_owner_refs=["aura_relationship_atlas::auxiliary_heuristic"],
                            evidence_refs=[f"{aux_type}_detection"],
                            missing_roles=[],
                            required_adapters=[],
                            authority_constraints=[],
                            temporal_conditions=[],
                            expected_benefits=["explanation_support", "rollback_assist"] if is_aux else ["module_awareness"],
                            risks=[],
                            prohibited_effects=[],
                            relationships_to_preserve=[],
                            confidence=0.6,
                            freshness="CURRENT"
                        )
                    )

    assessments.extend(auxiliary_assessments)

    # 4. Filter Candidate Wirings & Evaluate Prohibitions
    prohibitions = BUILTIN_PROHIBITIONS
    final_assessments: list[AtlasRelationshipAssessment] = []
    for a in assessments:
        is_prohibited = False
        prohib_reason = ""
        prohib_ref = ""

        # Check against builtin prohibition registry patterns
        for p in prohibitions:
            types_in_play = {pr.participant_type for pr in a.participant_refs}
            type_overlap = set(p.participant_types) & types_in_play
            relation_overlap = set(p.relation_types) & set(a.relation_types)

            match_type = not p.participant_types or bool(type_overlap)
            match_relation = not p.relation_types or bool(relation_overlap)

            if match_type and match_relation:
                # Evaluate each prohibition pattern specifically
                pattern = p.pattern
                should_prohibit = False

                if pattern == "affinity_mutation_block":
                    # VSA/affinity similarity must not authorize mutation
                    if a.truth_class == "ADVISORY_AFFINITY" and "REQUIRES_AUTHORITY" in a.relation_types:
                        should_prohibit = True

                elif pattern == "self_verification_block":
                    # A producer must not verify its own results
                    if "VERIFIED_BY" in a.relation_types or "CORROBORATED_BY" in a.relation_types:
                        # Check if both participants share the same canonical owner
                        owners = {pr.canonical_owner for pr in a.participant_refs}
                        if len(owners) == 1 and owners != {""}:
                            should_prohibit = True

                elif pattern == "agent_self_upgrade_block":
                    # External agents cannot self-upgrade candidate to exact
                    if ("IMPLEMENTS_CAPABILITY" in a.relation_types and
                            any(pr.participant_type == "agent" for pr in a.participant_refs) and
                            a.wiring_disposition == WiringDisposition.CANDIDATE):
                        should_prohibit = True

                elif pattern == "circular_authorization_block":
                    # Circular authority: A requires authority from B, B requires from A
                    # Detected when both directions have REQUIRES_AUTHORITY
                    # (simplified: same pair, both have REQUIRES_AUTHORITY)
                    if "REQUIRES_AUTHORITY" in a.relation_types:
                        # Check if reverse relation exists among assessments
                        pair_ids = {pr.participant_id for pr in a.participant_refs}
                        for other in assessments:
                            if other.assessment_id == a.assessment_id:
                                continue
                            other_ids = {pr.participant_id for pr in other.participant_refs}
                            if other_ids == pair_ids and "REQUIRES_AUTHORITY" in other.relation_types:
                                should_prohibit = True
                                break

                elif pattern == "ephemeral_lease_leak_block":
                    # Ephemeral leases must not persist beyond TTL
                    if ("DISSOLVES_AFTER" in a.relation_types and
                            a.lifecycle == Lifecycle.PERSISTENT):
                        should_prohibit = True

                elif pattern == "research_production_coupling_block":
                    # Production mutation directly coupled to unverified research
                    if (("REPAIRED_BY" in a.relation_types or "IMPLEMENTS_CAPABILITY" in a.relation_types) and
                            any(pr.participant_type == "research_artifact" for pr in a.participant_refs) and
                            a.truth_class == "INFERRED_MOTIF"):
                        should_prohibit = True

                elif pattern == "cross_arena_coupling_block":
                    # Direct un-adapted coupling between isolated Arenas
                    if ("CALLS" in a.relation_types or "WRITES_STATE" in a.relation_types):
                        arena_ids = {pr.participant_id for pr in a.participant_refs
                                     if pr.participant_type == "arena"}
                        if len(arena_ids) >= 2:
                            should_prohibit = True

                if should_prohibit:
                    is_prohibited = True
                    prohib_reason = p.reason
                    prohib_ref = p.prohibition_id
                    break

        if is_prohibited:
            a.wiring_disposition = WiringDisposition.PROHIBITED
            a.readiness = Readiness.TOO_RISKY
            a.semantic_relationship = SemanticRelationship.CONTRADICTED
            a.proof_status = ProofStatus.CONTRADICTED
            a.prohibited_effects.append(prohib_reason)
            a.evidence_refs.append(prohib_ref)

        final_assessments.append(a)

    # 5. Missing Configurations Scan
    missing_configs: list[MissingRelationalConfiguration] = []
    if prof_cfg["motif_search"] or prof_cfg["one_hop_missing_roles"]:
        for motif_id, spec in BUILTIN_MOTIFS.items():
            bound: dict[str, str] = {}
            missing = list(spec["required_roles"])

            # Scan participants to bind roles based on keyword match in ref names and roles
            for pid, ref in participants.items():
                name = ref.canonical_ref.lower()
                role = participant_meta[pid].get("role", "").lower()
                for role_name in list(missing):
                    if role_name in name or role_name in role:
                        bound[role_name] = pid
                        if role_name in missing:
                            missing.remove(role_name)

            # Only report if at least one role is bound (partially complete motif)
            if missing and len(bound) > 0:
                ratio = len(bound) / len(spec["required_roles"])
                cfg_id = f"config_{hashlib.md5(motif_id.encode(), usedforsecurity=False).hexdigest()[:24]}"
                missing_configs.append(
                    MissingRelationalConfiguration(
                        configuration_id=cfg_id,
                        motif_type=motif_id,
                        objective_family="structural_completeness",
                        bound_roles=bound,
                        missing_roles=missing,
                        existing_relations=[],
                        missing_relations=missing,
                        completion_ratio=round(ratio, 2),
                        candidate_participants_by_role={},
                        hard_blockers=[],
                        required_evidence=[f"role_{r}_presence" for r in missing],
                        required_verifiers=["test_motif_completeness"],
                        required_authority=["human_approval"],
                        expected_capability=spec["expected_capability"],
                        risk_class=spec["risk_class"]
                    )
                )

    # 6. Build Snapshot objects and reverse indexes
    rev_idx: dict[str, list[str]] = {}
    for a in final_assessments:
        for p in a.participant_refs:
            rev_idx.setdefault(p.participant_id, []).append(a.assessment_id)

    snapshot = AtlasSnapshot(
        snapshot_version=ATLAS_SNAPSHOT_VERSION,
        repository_head=repo_head,
        working_tree_digest=working_tree_digest,
        codemap_digest=codemap_digest,
        topology_digest=topology_digest,
        connectome_digest=connectome_digest,
        atomic_inventory_digest=atomic_inventory_digest,
        relational_index_digest=rel_index.get("index_digest", "index_digest_placeholder"),
        atlas_ontology_digest=hashlib.sha256(json.dumps(BUILTIN_MOTIFS, sort_keys=True).encode()).hexdigest(),
        prohibition_registry_digest=hashlib.sha256(json.dumps([p.to_dict() for p in prohibitions], sort_keys=True).encode()).hexdigest(),
        motif_registry_digest=hashlib.sha256(json.dumps(BUILTIN_MOTIFS, sort_keys=True).encode()).hexdigest(),
        profile_digest=hashlib.sha256(
            json.dumps(
                {"profile": op_profile.value, "config": prof_cfg},
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
        assessments=final_assessments,
        missing_configurations=missing_configs,
        prohibitions=prohibitions,
        reverse_indexes=rev_idx,
        boundary={
            "excluded_generated_paths": list(ATLAS_GENERATED_PATHS),
            "operational_profile": op_profile.value,
            "objective_scoped": objective_scoped,
            "participant_pair_count": participant_pair_count,
        }
    )

    if persist:
        # Generated artifacts are caches/navigation outputs. Persist only when
        # explicitly requested by the canonical build workflow.
        out_path.parent.mkdir(parents=True, exist_ok=True)

        delta_receipt: AtlasDeltaReceipt | None = None
        delta_path = repo_root / ".aura" / "RELATIONSHIP_ATLAS_DELTA.json"
        if out_path.exists():
            try:
                with out_path.open("r", encoding="utf-8") as f:
                    prev_data = json.load(f)
                prev_snap = _snapshot_from_dict(prev_data)
                delta_receipt = diff_relationship_atlases(prev_snap, snapshot)
            except (json.JSONDecodeError, KeyError, ValueError):
                pass

        with out_path.open("w", encoding="utf-8") as f:
            json.dump(snapshot.to_dict(), f, indent=2, sort_keys=True)

        receipt = {
            "snapshot_digest": snapshot.snapshot_digest,
            "built_at": int(time.time()),
            "assessments_count": len(final_assessments),
            "prohibitions_count": len(prohibitions),
            "missing_configurations_count": len(missing_configs),
            "operational_profile": op_profile.value,
            "freshness": "CURRENT",
        }
        with rec_path.open("w", encoding="utf-8") as f:
            json.dump(receipt, f, indent=2)

        if delta_receipt is not None:
            with delta_path.open("w", encoding="utf-8") as f:
                json.dump(delta_receipt.to_dict(), f, indent=2)

        render_relationship_atlas_markdown(snapshot, repo_root / DEFAULT_MARKDOWN_PATH)

    return snapshot


def load_relationship_atlas(
    path: str | Path = DEFAULT_ATLAS_PATH,
    *,
    validate: bool = True,
) -> AtlasSnapshot:
    """Load a serialized Atlas snapshot and fail closed on invalid content."""
    snapshot_path = Path(path)
    if not snapshot_path.is_file():
        raise FileNotFoundError(f"Relationship Atlas snapshot is missing at {snapshot_path}")
    with snapshot_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Relationship Atlas snapshot must be a JSON object")
    if validate:
        stored_snapshot_digest = data.get("snapshot_digest")
        if not isinstance(stored_snapshot_digest, str) or not re.fullmatch(
            r"[0-9a-f]{64}", stored_snapshot_digest
        ):
            raise ValueError(
                "Relationship Atlas snapshot is missing a valid stored snapshot_digest"
            )
    snapshot = _snapshot_from_dict(data)
    if validate:
        report = validate_relationship_atlas(snapshot)
        if not report.get("ok"):
            raise ValueError(
                "Relationship Atlas snapshot failed validation: "
                + "; ".join(str(item) for item in report.get("issues", [])[:5])
            )
    return snapshot



def _snapshot_from_dict(data: dict[str, Any]) -> AtlasSnapshot:
    """Reconstruct an AtlasSnapshot from a serialized dict (for delta computation)."""
    assessments_list: list[AtlasRelationshipAssessment] = []
    for a in data.get("assessments", []):
        p_refs = [AtlasParticipantRef(**p) for p in a.get("participant_refs", [])]
        a_copy = dict(a)
        a_copy["participant_refs"] = p_refs
        a_copy["structural_status"] = StructuralStatus(a_copy["structural_status"])
        a_copy["semantic_relationship"] = SemanticRelationship(a_copy["semantic_relationship"])
        a_copy["wiring_disposition"] = WiringDisposition(a_copy["wiring_disposition"])
        a_copy["readiness"] = Readiness(a_copy["readiness"])
        a_copy["lifecycle"] = Lifecycle(a_copy["lifecycle"])
        a_copy["proof_status"] = ProofStatus(a_copy["proof_status"])
        assessments_list.append(AtlasRelationshipAssessment(**a_copy))

    prohibitions_list = [RelationshipProhibition(**p) for p in data.get("prohibitions", [])]
    missing_list = [MissingRelationalConfiguration(**m) for m in data.get("missing_configurations", [])]

    return AtlasSnapshot(
        snapshot_version=data.get("snapshot_version", ATLAS_SNAPSHOT_VERSION),
        repository_head=data.get("repository_head", ""),
        working_tree_digest=data.get("working_tree_digest", ""),
        codemap_digest=data.get("codemap_digest", ""),
        topology_digest=data.get("topology_digest", ""),
        connectome_digest=data.get("connectome_digest", ""),
        atomic_inventory_digest=data.get("atomic_inventory_digest", ""),
        relational_index_digest=data.get("relational_index_digest", ""),
        atlas_ontology_digest=data.get("atlas_ontology_digest", ""),
        prohibition_registry_digest=data.get("prohibition_registry_digest", ""),
        motif_registry_digest=data.get("motif_registry_digest", ""),
        profile_digest=data.get("profile_digest", ""),
        assessments=assessments_list,
        missing_configurations=missing_list,
        prohibitions=prohibitions_list,
        reverse_indexes=data.get("reverse_indexes", {}),
        boundary=data.get("boundary", {}),
        snapshot_digest=data.get("snapshot_digest", ""),
    )


def validate_relationship_atlas(snapshot: AtlasSnapshot) -> dict[str, Any]:
    """Validates Relationship Atlas invariants and content-addressed integrity."""
    issues = []
    for a in snapshot.assessments:
        if not a.canonical_owner_refs:
            issues.append(f"Assessment {a.assessment_id} lacks canonical owner references.")
        if a.wiring_disposition == WiringDisposition.PROHIBITED and not a.prohibited_effects:
            issues.append(f"Prohibited assessment {a.assessment_id} lacks prohibition evidence.")
        expected_assessment_digest = a.compute_digest()
        if not isinstance(a.assessment_digest, str) or not hmac.compare_digest(
            a.assessment_digest, expected_assessment_digest
        ):
            issues.append(
                f"Assessment {a.assessment_id} digest mismatch: serialized content was modified."
            )

    expected_snapshot_digest = snapshot.compute_digest()
    if not isinstance(snapshot.snapshot_digest, str) or not hmac.compare_digest(
        snapshot.snapshot_digest, expected_snapshot_digest
    ):
        issues.append(
            "Relationship Atlas snapshot digest mismatch: serialized content was modified."
        )

    return {
        "ok": len(issues) == 0,
        "issues": issues,
        "assessments_count": len(snapshot.assessments),
        "missing_configurations_count": len(snapshot.missing_configurations)
    }


def relationship_assessment(
    participant_ids: list[str],
    snapshot: AtlasSnapshot,
) -> AtlasRelationshipAssessment | None:
    """Finds exact relationship assessment between specific participants."""
    target = set(participant_ids)
    for a in snapshot.assessments:
        pids = {p.participant_id for p in a.participant_refs}
        if pids == target:
            return a
    return None


def relationships_for_participant(
    participant_id: str,
    snapshot: AtlasSnapshot,
) -> list[AtlasRelationshipAssessment]:
    """Finds all relationship assessments involving the given participant."""
    related = []
    target_ids = snapshot.reverse_indexes.get(participant_id, [])
    for a in snapshot.assessments:
        if a.assessment_id in target_ids:
            related.append(a)
    return related


def relationships_for_objective(
    objective_keywords: list[str],
    snapshot: AtlasSnapshot,
) -> list[AtlasRelationshipAssessment]:
    """Retrieves all relationship assessments matching objective keywords."""
    matching = []
    keywords = [kw.lower() for kw in objective_keywords]
    for a in snapshot.assessments:
        matches = False
        for p in a.participant_refs:
            ref_lower = p.canonical_ref.lower()
            if any(kw in ref_lower for kw in keywords):
                matches = True
                break
        if matches:
            matching.append(a)
    return matching


def find_overlapping_unwired(snapshot: AtlasSnapshot) -> list[AtlasRelationshipAssessment]:
    """Returns all classified overlapping unwired relationships."""
    return [a for a in snapshot.assessments if a.structural_status == StructuralStatus.UNWIRED and a.semantic_relationship == SemanticRelationship.OVERLAPPING]


def find_auxiliary_adjacent(snapshot: AtlasSnapshot) -> list[AtlasRelationshipAssessment]:
    """Returns all classified auxiliary and adjacent relationships."""
    return [a for a in snapshot.assessments if a.semantic_relationship in (SemanticRelationship.AUXILIARY, SemanticRelationship.ADJACENT)]


def find_missing_configurations(snapshot: AtlasSnapshot) -> list[MissingRelationalConfiguration]:
    """Returns all identified missing configuration motifs."""
    return snapshot.missing_configurations


def find_candidate_wirings(snapshot: AtlasSnapshot) -> list[AtlasRelationshipAssessment]:
    """Returns all candidate relationships eligible for wiring (not prohibited, not exact)."""
    return [
        a for a in snapshot.assessments
        if a.wiring_disposition == WiringDisposition.CANDIDATE
        and a.structural_status != StructuralStatus.EXACTLY_WIRED
    ]


def find_prohibited_wirings(snapshot: AtlasSnapshot) -> list[RelationshipProhibition]:
    """Returns all active relationship prohibitions."""
    return snapshot.prohibitions


def explain_relationship(
    assessment_id: str,
    snapshot: AtlasSnapshot,
) -> dict[str, Any]:
    """Returns full human-readable analysis of a relationship's status."""
    for a in snapshot.assessments:
        if a.assessment_id == assessment_id:
            return {
                "assessment_id": a.assessment_id,
                "participants": [p.canonical_ref for p in a.participant_refs],
                "structural_status": a.structural_status.value,
                "semantic_relationship": a.semantic_relationship.value,
                "wiring_disposition": a.wiring_disposition.value,
                "readiness": a.readiness.value,
                "lifecycle": a.lifecycle.value,
                "truth_class": a.truth_class,
                "evidence_refs": a.evidence_refs,
                "canonical_owner_refs": a.canonical_owner_refs,
                "prohibited_effects": a.prohibited_effects
            }
    return {}


def diff_relationship_atlases(
    previous: AtlasSnapshot,
    current: AtlasSnapshot,
) -> AtlasDeltaReceipt:
    """Computes differences and changes between two Relationship Atlas snapshots."""
    prev_ids = {a.assessment_id: a for a in previous.assessments}
    curr_ids = {a.assessment_id: a for a in current.assessments}

    added_exact: list[str] = []
    removed_exact: list[str] = []
    reclassified: list[str] = []
    new_candidates: list[str] = []
    new_prohibitions: list[str] = []
    resolved_candidates: list[str] = []
    new_missing_roles: list[str] = []
    resolved_missing_roles: list[str] = []
    stale_assessments: list[str] = []

    for aid, a in curr_ids.items():
        if aid not in prev_ids:
            # Classify the added assessment by its disposition/status
            if a.structural_status == StructuralStatus.EXACTLY_WIRED:
                added_exact.append(aid)
            elif a.wiring_disposition == WiringDisposition.PROHIBITED:
                new_prohibitions.append(aid)
            elif a.wiring_disposition == WiringDisposition.CANDIDATE:
                new_candidates.append(aid)
            # Overlaps, auxiliary, and other non-exact additions are tracked
            # implicitly via the assessment set difference
        else:
            prev_a = prev_ids[aid]
            if (prev_a.structural_status != a.structural_status or
                    prev_a.semantic_relationship != a.semantic_relationship or
                    prev_a.wiring_disposition != a.wiring_disposition):
                reclassified.append(aid)
            # Detect stale: was current, now stale freshness
            if prev_a.freshness == "CURRENT" and a.freshness == "STALE":
                stale_assessments.append(aid)
            # Detect resolved candidates: was CANDIDATE, now not
            if (prev_a.wiring_disposition == WiringDisposition.CANDIDATE and
                    a.wiring_disposition != WiringDisposition.CANDIDATE):
                resolved_candidates.append(aid)

    for aid in prev_ids:
        if aid not in curr_ids:
            prev_a = prev_ids[aid]
            if prev_a.structural_status == StructuralStatus.EXACTLY_WIRED:
                removed_exact.append(aid)
            elif prev_a.wiring_disposition == WiringDisposition.CANDIDATE:
                resolved_candidates.append(aid)

    # Track missing roles changes
    prev_missing = {m.configuration_id: m for m in previous.missing_configurations}
    curr_missing = {m.configuration_id: m for m in current.missing_configurations}
    for mid in curr_missing:
        if mid not in prev_missing:
            new_missing_roles.append(mid)
    for mid in prev_missing:
        if mid not in curr_missing:
            resolved_missing_roles.append(mid)

    return AtlasDeltaReceipt(
        previous_snapshot_digest=previous.snapshot_digest,
        current_snapshot_digest=current.snapshot_digest,
        changed_participants=[],
        added_exact_relations=added_exact,
        removed_exact_relations=removed_exact,
        reclassified_relationships=reclassified,
        new_candidates=new_candidates,
        resolved_candidates=resolved_candidates,
        new_prohibitions=new_prohibitions,
        resolved_missing_roles=resolved_missing_roles,
        new_missing_roles=new_missing_roles,
        stale_assessments=stale_assessments,
        verification_refs=[],
    )



def _objective_index_from_neighborhood(
    relational_index: Mapping[str, Any],
    neighborhood: Mapping[str, Any],
):
    """Create a canonical reduced RelationalIndex from a validated neighborhood."""
    from aura_relational_index import RelationalIndex, _build_reverse_indexes
    from aura_relational_synthesis import RelationalGroup, RelationalParticipant, TypedRelation

    full = RelationalIndex.from_dict(relational_index)
    if neighborhood.get("index_digest") != full.index_digest:
        raise ValueError("relational neighborhood is not bound to the supplied index digest")
    participant_ids = {
        str(item.get("participant_id"))
        for item in neighborhood.get("participants", ())
        if isinstance(item, Mapping)
    }
    relation_ids = {
        str(item.get("relation_id"))
        for item in neighborhood.get("relations", ())
        if isinstance(item, Mapping)
    }
    if not participant_ids:
        raise ValueError("objective Atlas requires a non-empty bounded neighborhood")
    if len(participant_ids) > OBJECTIVE_ATLAS_MAX_PARTICIPANTS:
        raise ValueError("objective Atlas neighborhood exceeds participant limit")
    participant_map = {item.participant_id: item for item in full.participants}
    relation_map = {item.relation_id: item for item in full.relations}
    missing_participants = sorted(participant_ids - set(participant_map))
    missing_relations = sorted(relation_ids - set(relation_map))
    if missing_participants or missing_relations:
        raise ValueError("objective Atlas neighborhood references IDs absent from the current index")
    participants = tuple(participant_map[item] for item in sorted(participant_ids))
    relations = tuple(relation_map[item] for item in sorted(relation_ids))
    if any(
        relation.source_participant_id not in participant_ids
        or relation.target_participant_id not in participant_ids
        for relation in relations
    ):
        raise ValueError("objective Atlas neighborhood omitted a selected relation endpoint")
    groups = tuple(
        group
        for group in full.groups
        if group.boundary.included_participant_ids
        and set(group.boundary.included_participant_ids).issubset(participant_ids)
        and {item.relation_id for item in group.relations}.issubset(relation_ids)
    )
    reverse_indexes = _build_reverse_indexes(
        participants=participants,
        relations=relations,
        groups=groups,
        connectome={"nodes": ()},
    )
    exact_count = sum(1 for item in relations if item.truth_class.value.startswith("EXACT"))
    advisory_count = len(relations) - exact_count
    boundary = {
        **dict(full.boundary),
        "warnings": sorted(set((*full.boundary.get("warnings", ()), "objective_scoped_subset"))),
        "all_relation_endpoints_present": True,
    }
    build_facts = {
        **dict(full.build_facts),
        "participant_count": len(participants),
        "exact_relation_count": exact_count,
        "advisory_relation_count": advisory_count,
        "group_count": len(groups),
    }
    return RelationalIndex.create(
        repository_identity=dict(full.repository_identity),
        profile=dict(full.profile),
        participants=participants,
        relations=relations,
        groups=groups,
        reverse_indexes=reverse_indexes,
        boundary=boundary,
        build_facts=build_facts,
    )


def build_objective_relationship_atlas(
    *,
    repo_root: str | Path,
    relational_index: Mapping[str, Any],
    neighborhood: Mapping[str, Any],
    profile: str | OperationalProfile = OperationalProfile.OBJECTIVE_STANDARD,
    use_cache: bool = True,
) -> AtlasSnapshot:
    """Compile STANDARD/DEEP Atlas intelligence over a bounded local subgraph."""
    global _OBJECTIVE_ATLAS_CACHE_BYTES
    root = Path(repo_root).resolve()
    op_profile = OperationalProfile(profile.upper()) if isinstance(profile, str) else profile
    if op_profile not in {OperationalProfile.OBJECTIVE_STANDARD, OperationalProfile.OBJECTIVE_DEEP}:
        raise ValueError("objective Atlas profile must be OBJECTIVE_STANDARD or OBJECTIVE_DEEP")
    neighborhood_digest = str(neighborhood.get("neighborhood_digest") or "")
    if not neighborhood_digest:
        raise ValueError("objective Atlas requires a content-addressed neighborhood")
    expected_neighborhood_digest = stable_digest(
        {key: value for key, value in neighborhood.items() if key != "neighborhood_digest"},
        digest_size=20,
    )
    if not hmac.compare_digest(neighborhood_digest, expected_neighborhood_digest):
        raise ValueError("relational neighborhood_digest does not match canonical neighborhood content")
    local_index = _objective_index_from_neighborhood(relational_index, neighborhood)
    _validate_relational_index_freshness(
        root,
        local_index.to_dict(),
        index_label=root / "<objective-relational-index>",
    )
    key = (
        str(local_index.repository_identity.get("repo_head") or ""),
        local_index.index_digest,
        neighborhood_digest,
        op_profile.value,
    )
    if use_cache and key in _OBJECTIVE_ATLAS_CACHE:
        payload, size = _OBJECTIVE_ATLAS_CACHE.pop(key)
        _OBJECTIVE_ATLAS_CACHE[key] = (payload, size)
        return _snapshot_from_dict(json.loads(json.dumps(payload)))

    snapshot = build_relationship_atlas(
        repo_root=root,
        profile=op_profile,
        relational_index_data=local_index.to_dict(),
        persist=False,
    )
    snapshot.boundary["neighborhood_digest"] = neighborhood_digest
    snapshot.boundary["source_relational_index_digest"] = str(neighborhood.get("index_digest") or "")
    snapshot.snapshot_digest = snapshot.compute_digest()
    payload = snapshot.to_dict()
    payload_size = len(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    if use_cache and payload_size <= OBJECTIVE_ATLAS_CACHE_MAX_BYTES:
        while _OBJECTIVE_ATLAS_CACHE and _OBJECTIVE_ATLAS_CACHE_BYTES + payload_size > OBJECTIVE_ATLAS_CACHE_MAX_BYTES:
            _, (_, evicted_size) = _OBJECTIVE_ATLAS_CACHE.popitem(last=False)
            _OBJECTIVE_ATLAS_CACHE_BYTES -= evicted_size
        _OBJECTIVE_ATLAS_CACHE[key] = (json.loads(json.dumps(payload)), payload_size)
        _OBJECTIVE_ATLAS_CACHE_BYTES += payload_size
    return snapshot


def clear_objective_atlas_cache() -> None:
    """Clear the non-semantic objective Atlas cache."""
    global _OBJECTIVE_ATLAS_CACHE_BYTES
    _OBJECTIVE_ATLAS_CACHE.clear()
    _OBJECTIVE_ATLAS_CACHE_BYTES = 0

def compile_atlas_projection(
    focal_participant_ids: list[str],
    snapshot: AtlasSnapshot,
    include_auxiliary: bool = True,
    include_prohibited: bool = True,
) -> dict[str, Any]:
    """Compiles a bounded visual or structured projection for a participant subset."""
    nodes = []
    edges = []
    seen_nodes = set()

    for f_id in focal_participant_ids:
        related = relationships_for_participant(f_id, snapshot)
        for a in related:
            if not include_auxiliary and a.semantic_relationship in (SemanticRelationship.AUXILIARY, SemanticRelationship.ADJACENT):
                continue
            if not include_prohibited and a.wiring_disposition == WiringDisposition.PROHIBITED:
                continue

            for p in a.participant_refs:
                if p.participant_id not in seen_nodes:
                    seen_nodes.add(p.participant_id)
                    nodes.append({
                        "id": p.participant_id,
                        "label": p.canonical_ref.split("::")[-1],
                        "type": p.participant_type,
                        "freshness": p.freshness
                    })
            
            # Form edge
            if len(a.participant_refs) >= 2:
                edges.append({
                    "id": a.assessment_id,
                    "source": a.participant_refs[0].participant_id,
                    "target": a.participant_refs[1].participant_id,
                    "type": "/".join(a.relation_types),
                    "structural_status": a.structural_status.value,
                    "semantic_relationship": a.semantic_relationship.value,
                    "wiring_disposition": a.wiring_disposition.value
                })

    return {
        "nodes": nodes,
        "edges": edges,
        "boundary_excluded": list(ATLAS_GENERATED_PATHS)
    }


# ---------------------------------------------------------------------------
# Re-rendering Markdown Index
# ---------------------------------------------------------------------------
def render_relationship_atlas_markdown(snapshot: AtlasSnapshot, output_path: Path) -> None:
    """Writes a human-readable index overview from the snapshot."""
    lines = [
        "# Aura Architecture Relationship Atlas (AARA)",
        "",
        "## Snapshot Summary",
        f"- **Snapshot Version**: `{snapshot.snapshot_version}`",
        f"- **Snapshot Digest**: `{snapshot.snapshot_digest}`",
        f"- **Relational Index Digest**: `{snapshot.relational_index_digest}`",
        f"- **Total Relationship Assessments**: `{len(snapshot.assessments)}`",
        f"- **Missing Configuration Motifs**: `{len(snapshot.missing_configurations)}`",
        f"- **Prohibitions Registered**: `{len(snapshot.prohibitions)}`",
        "",
        "## Active Prohibitions Registry",
        "| ID | Prohibition Family | Reason |",
        "| --- | --- | --- |"
    ]

    for p in snapshot.prohibitions:
        lines.append(f"| `{p.prohibition_id}` | `{p.prohibition_family}` | {p.reason} |")

    lines.extend([
        "",
        "## Missing Relational Configurations",
        "| Motif Type | Completion Ratio | Expected Capability | Missing Roles |",
        "| --- | --- | --- | --- |"
    ])

    for m in snapshot.missing_configurations:
        roles_str = ", ".join(m.missing_roles)
        lines.append(f"| `{m.motif_type}` | `{m.completion_ratio}` | `{m.expected_capability}` | {roles_str} |")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# CLI Command Setup
# ---------------------------------------------------------------------------
def _cli_parser() -> argparse.ArgumentParser:
    """Build the argparse CLI with all Atlas subcommands."""
    parser = argparse.ArgumentParser(description="Aura Architecture Relationship Atlas CLI")
    parser.add_argument("--repo-root", default=".")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sub_build = subparsers.add_parser("build", help="Build relationship atlas from relational index")
    sub_build.add_argument("--profile", choices=["MINIMAL", "STANDARD", "DEEP"], default="STANDARD")

    sub_refresh = subparsers.add_parser("refresh", help="Rebuild atlas incrementally after changed paths")
    sub_refresh.add_argument("--changed", nargs="*", default=[], help="Changed file paths (for future incremental refresh)")

    subparsers.add_parser("status", help="Show atlas snapshot summary and build receipt")

    subparsers.add_parser("validate", help="Validate atlas invariants and structural constraints")

    query = subparsers.add_parser("query", help="Query atlas by participant ID")
    query.add_argument("--participant", required=True)

    subparsers.add_parser("overlaps", help="List all overlapping unwired relationships")

    subparsers.add_parser("candidates", help="List all candidate wirings (non-prohibited)")

    subparsers.add_parser("missing", help="List all missing configuration motifs")

    subparsers.add_parser("prohibited", help="List all active prohibitions")

    explain = subparsers.add_parser("explain", help="Explain relationship details")
    explain.add_argument("--assessment", required=True)

    diff = subparsers.add_parser("diff", help="Compute deltas between snapshots")
    diff.add_argument("--previous", required=True)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point — dispatches build, status, validate, query, and other Atlas commands."""
    args = _cli_parser().parse_args(argv)
    repo = Path(args.repo_root)

    # Setup paths
    idx_path = repo / ".aura" / "RELATIONAL_INDEX.json"
    out_path = repo / DEFAULT_ATLAS_PATH
    rec_path = repo / DEFAULT_RECEIPT_PATH

    if args.command == "build":
        try:
            snapshot = build_relationship_atlas(
                repo_root=repo,
                relational_index_path=idx_path,
                profile=getattr(args, "profile", "STANDARD"),
            )
            print(json.dumps({
                "ok": True,
                "snapshot_digest": snapshot.snapshot_digest,
                "assessments": len(snapshot.assessments),
                "missing_configurations": len(snapshot.missing_configurations),
                "prohibitions": len(snapshot.prohibitions),
            }, indent=2))
            return 0
        except Exception as e:
            print(json.dumps({"ok": False, "error": str(e)}, indent=2))
            return 1

    if args.command == "refresh":
        # Refresh is equivalent to build for now; incremental refresh uses the same path
        try:
            snapshot = build_relationship_atlas(repo_root=repo, relational_index_path=idx_path)
            print(json.dumps({
                "ok": True,
                "snapshot_digest": snapshot.snapshot_digest,
                "refreshed": True,
                "assessments": len(snapshot.assessments),
            }, indent=2))
            return 0
        except Exception as e:
            print(json.dumps({"ok": False, "error": str(e)}, indent=2))
            return 1

    # Commands that need a built snapshot
    if not out_path.exists():
        print(json.dumps({"ok": False, "error": "Atlas snapshot is missing. Run 'build' command first."}, indent=2))
        return 1

    with out_path.open("r", encoding="utf-8") as f:
        snapshot_data = json.load(f)

    snapshot = _snapshot_from_dict(snapshot_data)

    if args.command == "status":
        with rec_path.open("r", encoding="utf-8") as f:
            receipt = json.load(f)
        print(json.dumps({
            "snapshot_version": snapshot.snapshot_version,
            "snapshot_digest": snapshot.snapshot_digest,
            "repository_head": snapshot.repository_head,
            "assessments_count": len(snapshot.assessments),
            "missing_configurations_count": len(snapshot.missing_configurations),
            "prohibitions_count": len(snapshot.prohibitions),
            "boundary": snapshot.boundary,
            "receipt": receipt,
        }, indent=2))
        return 0

    if args.command == "validate":
        report = validate_relationship_atlas(snapshot)
        print(json.dumps(report, indent=2))
        return 0 if report["ok"] else 1

    if args.command == "query":
        related = relationships_for_participant(args.participant, snapshot)
        print(json.dumps([r.to_dict() for r in related], indent=2))
        return 0

    if args.command == "overlaps":
        overlaps = find_overlapping_unwired(snapshot)
        print(json.dumps([r.to_dict() for r in overlaps], indent=2))
        return 0

    if args.command == "candidates":
        candidates = find_candidate_wirings(snapshot)
        print(json.dumps([r.to_dict() for r in candidates], indent=2))
        return 0

    if args.command == "explain":
        explanation = explain_relationship(args.assessment, snapshot)
        print(json.dumps(explanation, indent=2))
        return 0

    if args.command == "missing":
        print(json.dumps([m.to_dict() for m in snapshot.missing_configurations], indent=2))
        return 0

    if args.command == "prohibited":
        print(json.dumps([p.to_dict() for p in snapshot.prohibitions], indent=2))
        return 0

    if args.command == "diff":
        prev_path = Path(args.previous)
        if not prev_path.exists():
            print(json.dumps({"ok": False, "error": f"Previous snapshot missing at {prev_path}"}, indent=2))
            return 1
        with prev_path.open("r", encoding="utf-8") as f:
            prev_data = json.load(f)
        previous_snap = _snapshot_from_dict(prev_data)
        delta = diff_relationship_atlases(previous_snap, snapshot)
        print(json.dumps(delta.to_dict(), indent=2))
        return 0

    return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
