"""Aura Relational Synthesis Phase 2: generated AOT relational anatomy index.

The index materializes a deterministic navigation/cache view over Aura's current
canonical owners:

* ``CodeTopoAnchor`` owns exact current source identities and structural edges.
* the atomic inventory owns the exact callable-inventory digest.
* Capability Connectome V2 owns advisory capability declarations.
* Phase 1 relational contracts own participants, relations, groups, boundaries,
  truth classes, and canonical serialization.

The generated index never becomes patch, routing, verification, model, learning,
or merge authority. Every exact relationship remains pinned to current source
and every capability relationship remains advisory unless a different canonical
owner supplies exact evidence in a later phase.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import heapq
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
import gc
import json
import math
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import subprocess
import tempfile
import threading
import time
from types import MappingProxyType
from typing import Any, BinaryIO

if os.name == "nt":
    import msvcrt as _file_lock_backend
else:
    import fcntl as _file_lock_backend

from aura_capability_connectome import build_capability_connectome
from aura_capability_connectome_v2 import (
    CONNECTOME_ENRICHMENT_VERSION,
    enrich_connectome,
)
from aura_codebase_navigator import (
    DEFAULT_INDEX_PATH as CODEMAP_INDEX_PATH,
)
from aura_codebase_navigator import (
    DEFAULT_TOPOLOGY_PATH as CODEMAP_TOPOLOGY_PATH,
)
from aura_emergent_evidence_spine import (
    ATOMIC_INVENTORY_VERSION,
    _inventory_from_anchor,
    _repo_python_sources,
)
from aura_event_contracts import canonical_json, stable_digest, stable_id
from aura_relationship_contracts import RelationalNeighborhoodRequest
from aura_relational_synthesis import (
    Freshness,
    GroupKind,
    ParticipantType,
    RelationalBoundary,
    RelationalGroup,
    RelationalParticipant,
    RelationType,
    RoleBinding,
    TruthClass,
    TypedRelation,
)
from aura_topological_context_anchor import (
    ANCHOR_VERSION,
    PATCH_AUTHORITY_POLICY,
    CodeTopoAnchor,
)

RELATIONAL_INDEX_VERSION = "AURA_RELATIONAL_INDEX_V1"
RELATIONAL_INDEX_RECEIPT_VERSION = "AURA_RELATIONAL_INDEX_RECEIPT_V1"
PATCH_AUTHORITY = PATCH_AUTHORITY_POLICY
VSA_PATCH_AUTHORITY = False

DEFAULT_INDEX_PATH = Path(".aura/RELATIONAL_INDEX.json")
DEFAULT_RECEIPT_PATH = Path(".aura/RELATIONAL_INDEX_RECEIPT.json")
DEFAULT_MARKDOWN_PATH = Path(".aura/RELATIONAL_INDEX.md")
DEFAULT_LOCK_PATH = Path(".aura/RELATIONAL_INDEX.lock")
INDEX_GENERATED_PATHS = frozenset(
    {
        DEFAULT_INDEX_PATH.as_posix(),
        DEFAULT_RECEIPT_PATH.as_posix(),
        DEFAULT_MARKDOWN_PATH.as_posix(),
        DEFAULT_LOCK_PATH.as_posix(),
    }
)

_REQUIRED_REPOSITORY_TEXT_IDENTITIES = (
    "repo_head",
    "working_tree_digest",
    "codemap_digest",
    "topology_digest",
    "topology_version",
    "connectome_graph_digest",
    "connectome_version",
    "atomic_inventory_digest",
    "atomic_inventory_version",
    "relation_ontology_digest",
    "profile_digest",
    "schema_digest",
)
_REPOSITORY_IDENTITY_KEYS = frozenset((*_REQUIRED_REPOSITORY_TEXT_IDENTITIES, "topology_health"))
_PROFILE_KEYS = frozenset({"name", "budgets", "profile_digest"})
_PROFILE_BUDGET_KEYS = frozenset({"max_group_relations", "max_group_participants"})
_BOUNDARY_KEYS = frozenset(
    {
        "unsupported_languages",
        "unresolved_dynamic_calls",
        "advisory_only_mappings",
        "excluded_generated_paths",
        "warnings",
        "all_relation_endpoints_present",
    }
)
_BUILD_FACT_KEYS = frozenset(
    {
        "anchor_version",
        "source_file_count",
        "topology_node_count",
        "topology_edge_count",
        "atomic_callable_count",
        "participant_count",
        "exact_relation_count",
        "advisory_relation_count",
        "group_count",
        "unresolved_mapping_count",
    }
)

_EXACT_EDGE_RELATIONS = {
    "call": RelationType.CALLS,
    "import": RelationType.IMPORTS,
    "test": RelationType.TESTS,
}

# The registry is explicit and architecture-owned. It deliberately does not use
# filename keyword inference to turn advisory similarity into group membership.
MACRO_DOMAIN_CAPABILITIES: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "intent_lexical_routing": (
            "aura.fst.intent_routing",
            "aura.tokenizer_guard",
        ),
        "wfst_route_admission": (
            "aura.fst.intent_routing",
            "aura.coding_arena.capsule_compiler",
        ),
        "codemap_topology_grounding": (
            "aura.coding_arena.topology",
            "aura.concept_workspace",
            "aura.node_inspector",
            "aura.understand_graph",
        ),
        "connectome_resolution": (
            "aura.concept_workspace",
            "aura.emergent_potential.audit",
        ),
        "planning_board_breadboards": (
            "aura.architect_loop",
            "aura.coding_arena.capsule_compiler",
        ),
        "relational_authority_governance": (
            "aura.patch_quality_gate",
            "aura.tokenizer_guard",
        ),
        "coding_workbench_forge_waboose": (
            "aura.coding_waboose.learning",
            "aura.patch_quality_gate",
            "aura.architect_loop",
        ),
        "agent_bridge_external_workers": (
            "aura.agent_arena.bridge",
            "aura.llm_egress",
        ),
        "evidence_verification_telemetry": (
            "aura.patch_quality_gate",
            "aura.emergent_potential.audit",
            "aura.understand_graph",
        ),
        "memory_dream_qdkt_crucible": (
            "aura.dream.reranking",
            "aura.qdkt.memory",
            "aura.coding_waboose.learning",
        ),
        "persistence_checkpoints_jspace": (
            "aura.jspace.advisory_state",
            "aura.qdkt.memory",
        ),
        "observatory_human_agent": (
            "aura.concept_workspace",
            "aura.node_inspector",
        ),
        "civic_commons": (),
        "construction": (),
        "financial_exact_state": (),
        "tensor_evidence": (),
    }
)

SURGICAL_BUNDLE_CAPABILITIES: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "coding_waboose_coderabbit_dream_qdkt": (
            "aura.coding_waboose.learning",
            "aura.dream.reranking",
            "aura.qdkt.memory",
        ),
        "construction_tensor_hdc_vsa": (),
        "agent_bridge_temporal_persistence_slice_leases": (
            "aura.agent_arena.bridge",
            "aura.jspace.advisory_state",
        ),
        "fst_resolver_route_capsules_capability_leases": (
            "aura.fst.intent_routing",
            "aura.coding_arena.capsule_compiler",
        ),
        "crucible_verifier_receipts_arena_experience": (
            "aura.qdkt.memory",
            "aura.patch_quality_gate",
        ),
        "codemap_connectome_emergent_auditor_research_lane": (
            "aura.coding_arena.topology",
            "aura.concept_workspace",
            "aura.emergent_potential.audit",
            "aura.research_arxiv_memory",
        ),
    }
)

_PROFILE_BUDGETS: Mapping[str, Mapping[str, int]] = MappingProxyType(
    {
        "MINIMAL": MappingProxyType(
            {"max_group_relations": 300, "max_group_participants": 300}
        ),
        "STANDARD": MappingProxyType(
            {"max_group_relations": 1500, "max_group_participants": 1500}
        ),
        "DEEP": MappingProxyType(
            {"max_group_relations": 10000, "max_group_participants": 10000}
        ),
    }
)

_THREAD_LOCKS: dict[str, threading.Lock] = {}
_THREAD_LOCKS_GUARD = threading.Lock()

_SECRET_FIELD_NAMES = frozenset(
    {
        "api_key",
        "apikey",
        "access_token",
        "auth_token",
        "authorization",
        "password",
        "private_key",
        "secret",
        "token",
    }
)
_SECRET_FIELD_SUFFIXES = (
    "_api_key",
    "_access_token",
    "_auth_token",
    "_token",
    "_password",
    "_private_key",
    "_secret",
)
_PRIVATE_REASONING_FIELD_NAMES = frozenset(
    {
        "chain_of_thought",
        "cot",
        "hidden_reasoning",
        "private_reasoning",
        "inner_thought",
        "innerthought",
        "scratchpad",
        "scratch_pad",
    }
)
_FIELD_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
_HIGH_CONFIDENCE_SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9._~+/=%-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=%-]{12,}"),
    re.compile(r"(?i)\bbasic\s+[A-Za-z0-9+/=]{12,}"),
    re.compile(
        r"(?is)-----BEGIN [^-\r\n]*PRIVATE KEY-----.*?"
        r"-----END [^-\r\n]*PRIVATE KEY-----"
    ),
)


def _normalized_field_name(value: str) -> str:
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", value.strip())
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _assert_no_secret_shaped_content(
    value: Any,
    *,
    path: str = "$",
    inspect_mapping_keys: bool = True,
) -> None:
    """Reject actual secrets without misclassifying source-identity lookup keys.

    Reverse-index lookup keys are repository paths, qualified symbols, capability
    IDs, and relation names. They are data, not payload field names, so their keys
    are exempt from field-name policy while their values are still scanned.
    """
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            if inspect_mapping_keys and _FIELD_NAME_RE.fullmatch(key_text):
                normalized = _normalized_field_name(key_text)
                if normalized in _PRIVATE_REASONING_FIELD_NAMES:
                    raise ValueError(
                        f"private reasoning field is prohibited: {path}.{key_text}"
                    )
                if normalized in _SECRET_FIELD_NAMES or normalized.endswith(
                    _SECRET_FIELD_SUFFIXES
                ):
                    raise ValueError(f"secret-shaped field is prohibited: {path}.{key_text}")
            child_inspect = not (
                path == "$.reverse_indexes" and key_text.startswith("by_")
            )
            _assert_no_secret_shaped_content(
                item,
                path=f"{path}.{key_text}",
                inspect_mapping_keys=child_inspect,
            )
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _assert_no_secret_shaped_content(
                item,
                path=f"{path}[{index}]",
                inspect_mapping_keys=inspect_mapping_keys,
            )
        return
    if isinstance(value, str) and any(
        pattern.search(value) for pattern in _HIGH_CONFIDENCE_SECRET_PATTERNS
    ):
        raise ValueError(f"secret-shaped value is prohibited: {path}")


def _required_text(value: Any, field_name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _strict_bool(value: Any, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field_name} must be a boolean")
    return value


def _nonnegative_int(value: Any, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


def _freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _freeze_json(item) for key, item in sorted(value.items(), key=lambda item: str(item[0]))}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_thaw_json(item) for item in value]
    return value


def _immutable_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be an object")
    canonical_json(value)
    frozen = _freeze_json(value)
    if not isinstance(frozen, Mapping):
        raise ValueError(f"{field_name} must be an object")
    return frozen


def _require_exact_keys(value: Mapping[str, Any], expected: frozenset[str], field_name: str) -> None:
    actual = set(value)
    if actual == expected:
        return
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    details: list[str] = []
    if missing:
        details.append(f"missing={missing}")
    if extra:
        details.append(f"extra={extra}")
    raise ValueError(f"{field_name} keys do not match the V1 contract: {'; '.join(details)}")


def _topology_health(value: Any, field_name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a finite number or null")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field_name} must be a finite number or null")
    return result


def _string_tuple(value: Any, field_name: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{field_name} must be an ordered sequence")
    result = tuple(sorted(_required_text(item, f"{field_name}[]") for item in value))
    if not allow_empty and not result:
        raise ValueError(f"{field_name} must not be empty")
    if len(result) != len(set(result)):
        raise ValueError(f"{field_name} must not contain duplicates")
    return result


def _safe_repo_path(value: str) -> str:
    text = _required_text(value, "repository path").replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    path = PurePosixPath(text)
    windows_path = PureWindowsPath(text)
    if path.is_absolute() or windows_path.drive or ".." in path.parts:
        raise ValueError(f"repository path escapes workspace: {value}")
    normalized = path.as_posix()
    if normalized in {"", "."}:
        raise ValueError("repository path must not be empty")
    return normalized


def _contained_repo_target(repo_root: Path, value: str | Path) -> Path:
    root = repo_root.resolve()
    relative = _safe_repo_path(str(value))
    target = root / relative
    resolved_parent = target.parent.resolve(strict=False)
    try:
        resolved_parent.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"repository path parent escapes workspace: {value}") from exc
    if target.exists() or target.is_symlink():
        try:
            target.resolve(strict=False).relative_to(root)
        except ValueError as exc:
            raise ValueError(f"repository path target escapes workspace: {value}") from exc
    return target


_VIRTUAL_ENV_DIR_RE = re.compile(r"^(?:\.?venv|\.?env)(?:[-_.].*)?$", re.IGNORECASE)
_EPHEMERAL_SOURCE_DIRS = frozenset({"site-packages", ".tox", ".nox", ".direnv"})


def _is_ephemeral_repository_path(path: str) -> bool:
    parent_parts = PurePosixPath(path).parts[:-1]
    return any(part in _EPHEMERAL_SOURCE_DIRS or _VIRTUAL_ENV_DIR_RE.fullmatch(part) for part in parent_parts)


def _canonical_python_sources(root: Path) -> dict[str, str]:
    """Return Aura-scanned sources with local interpreter environments removed.

    The Emergent Evidence Spine scanner remains the source collector. This
    boundary only removes environment-local Python packages that can appear
    under names such as ``.venv_phase2`` and would otherwise make the AOT index
    depend on a developer's temporary virtual environment.
    """
    return {
        path: source
        for path, source in _repo_python_sources(root).items()
        if not _is_ephemeral_repository_path(path)
    }


def _is_test_path(path: str) -> bool:
    parts = str(path).replace("\\", "/").lower().split("/")
    return any(
        part == "tests" or part.startswith("test_") or part.endswith("_test.py")
        for part in parts
    )


def _qualified_symbol(node: Any) -> str:
    if node.kind == "module":
        return "<module>"
    return f"{node.parent_symbol}.{node.symbol}" if node.parent_symbol else node.symbol


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _digest_file(path: Path) -> str:
    if not path.exists() or not path.is_file():
        raise ValueError(f"required freshness artifact is missing: {path.as_posix()}")
    return stable_digest(path.read_bytes().hex(), digest_size=20)


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return completed.stdout.strip()


def _repo_head(root: Path) -> str:
    return _required_text(_git(root, "rev-parse", "HEAD"), "repo_head")


def _working_tree_digest(root: Path) -> str:
    """Digest tracked changes and relevant untracked files deterministically."""
    tracked = subprocess.run(
        ["git", "-C", str(root), "diff", "--binary", "HEAD", "--", "."],
        check=True,
        capture_output=True,
        timeout=30,
    ).stdout
    untracked_raw = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
        ],
        check=True,
        capture_output=True,
        timeout=30,
    ).stdout
    untracked: list[dict[str, str]] = []
    for raw_path in untracked_raw.split(b"\0"):
        if not raw_path:
            continue
        relative = _safe_repo_path(raw_path.decode("utf-8", errors="surrogateescape"))
        if relative in INDEX_GENERATED_PATHS or _is_ephemeral_repository_path(relative):
            continue
        path = root / relative
        if path.is_file():
            untracked.append(
                {
                    "path": relative,
                    "digest": stable_digest(path.read_bytes().hex(), digest_size=20),
                }
            )
    return stable_digest(
        {
            "tracked_diff_digest": stable_digest(tracked.hex(), digest_size=20),
            "untracked": sorted(untracked, key=lambda item: item["path"]),
        },
        digest_size=20,
    )


def _topology_facts(path: Path) -> tuple[str, str, float | None]:
    data = _read_json(path)
    version = str(
        data.get("version")
        or data.get("schema_version")
        or data.get("metadata", {}).get("version")
        or "UNVERSIONED_TOPOLOGY"
    )
    candidates = (
        data.get("global_health"),
        data.get("health"),
        data.get("metadata", {}).get("global_health"),
    )
    health_value = next((item for item in candidates if item is not None), None)
    health = _topology_health(health_value, "topology health")
    return _digest_file(path), version, health


def _relation_ontology_digest() -> str:
    return stable_digest(sorted(item.value for item in RelationType), digest_size=20)


def _schema_digest(root: Path) -> str:
    return _digest_file(root / "schemas" / "aura_relational_index.schema.json")


class RelationalIndexProfile(str, Enum):
    MINIMAL = "MINIMAL"
    STANDARD = "STANDARD"
    DEEP = "DEEP"

    @property
    def budgets(self) -> Mapping[str, int]:
        return _PROFILE_BUDGETS[self.value]

    @property
    def digest(self) -> str:
        return stable_digest(
            {"name": self.value, "budgets": dict(self.budgets)}, digest_size=20
        )


@dataclass(frozen=True)
class RelationalIndex:
    """Canonical generated relational anatomy cache."""

    index_id: str
    repository_identity: Mapping[str, Any]
    profile: Mapping[str, Any]
    participants: tuple[RelationalParticipant, ...]
    relations: tuple[TypedRelation, ...]
    groups: tuple[RelationalGroup, ...]
    reverse_indexes: Mapping[str, Any]
    boundary: Mapping[str, Any]
    build_facts: Mapping[str, Any]
    generated_only: bool = True
    safe_to_patch: bool = False
    production_mutation: bool = False
    automatic_fix: bool = False
    automatic_commit: bool = False
    automatic_push: bool = False
    automatic_pull_request: bool = False
    automatic_merge: bool = False
    human_review_required: bool = True
    _validated_index_digest: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        repository_identity = _immutable_mapping(self.repository_identity, "repository_identity")
        _require_exact_keys(
            repository_identity,
            _REPOSITORY_IDENTITY_KEYS,
            "repository_identity",
        )
        for name in _REQUIRED_REPOSITORY_TEXT_IDENTITIES:
            _required_text(repository_identity.get(name), f"repository_identity.{name}")
        topology_health = _topology_health(
            repository_identity.get("topology_health"),
            "repository_identity.topology_health",
        )
        repository_identity = MappingProxyType({**dict(repository_identity), "topology_health": topology_health})
        object.__setattr__(self, "repository_identity", repository_identity)

        profile = _immutable_mapping(self.profile, "profile")
        _require_exact_keys(profile, _PROFILE_KEYS, "profile")
        name = _required_text(profile.get("name"), "profile.name")
        try:
            profile_enum = RelationalIndexProfile(name)
        except ValueError as exc:
            raise ValueError(f"unsupported relational index profile: {name}") from exc
        budgets = _immutable_mapping(profile.get("budgets"), "profile.budgets")
        _require_exact_keys(budgets, _PROFILE_BUDGET_KEYS, "profile.budgets")
        supplied_budgets = {
            key: int(budgets[key])
            for key in sorted(_PROFILE_BUDGET_KEYS)
            if isinstance(budgets.get(key), int) and not isinstance(budgets.get(key), bool)
        }
        if len(supplied_budgets) != len(_PROFILE_BUDGET_KEYS):
            raise ValueError("profile budgets must be integers")
        if supplied_budgets != dict(profile_enum.budgets):
            raise ValueError("profile budgets do not match canonical profile")
        if profile.get("profile_digest") != profile_enum.digest:
            raise ValueError("profile_digest does not match canonical profile")
        profile = MappingProxyType(
            {
                "name": name,
                "budgets": MappingProxyType(supplied_budgets),
                "profile_digest": profile_enum.digest,
            }
        )
        object.__setattr__(self, "profile", profile)

        if (
            type(self.participants) is not tuple
            or not self.participants
            or not all(isinstance(item, RelationalParticipant) for item in self.participants)
        ):
            raise ValueError("participants must be a non-empty tuple of RelationalParticipant")
        participants = tuple(sorted(self.participants, key=lambda item: item.participant_id))
        participant_ids = [item.participant_id for item in participants]
        if len(participant_ids) != len(set(participant_ids)):
            raise ValueError("participants contain duplicate IDs")
        object.__setattr__(self, "participants", participants)
        participant_id_set = set(participant_ids)

        if type(self.relations) is not tuple or not all(
            isinstance(item, TypedRelation) for item in self.relations
        ):
            raise ValueError("relations must be a tuple of TypedRelation")
        relations = tuple(sorted(self.relations, key=lambda item: item.relation_id))
        relation_ids = [item.relation_id for item in relations]
        if len(relation_ids) != len(set(relation_ids)):
            raise ValueError("relations contain duplicate IDs")
        for relation in relations:
            if relation.source_participant_id not in participant_id_set:
                raise ValueError("relation source endpoint is missing from participants")
            if relation.target_participant_id not in participant_id_set:
                raise ValueError("relation target endpoint is missing from participants")
        object.__setattr__(self, "relations", relations)
        relation_id_set = set(relation_ids)

        if type(self.groups) is not tuple or not all(
            isinstance(item, RelationalGroup) for item in self.groups
        ):
            raise ValueError("groups must be a tuple of RelationalGroup")
        groups = tuple(sorted(self.groups, key=lambda item: item.group_id))
        group_ids = [item.group_id for item in groups]
        if len(group_ids) != len(set(group_ids)):
            raise ValueError("groups contain duplicate IDs")
        for group in groups:
            if not set(group.boundary.included_participant_ids).issubset(participant_id_set):
                raise ValueError("group boundary references unknown participant")
            if not {item.relation_id for item in group.relations}.issubset(relation_id_set):
                raise ValueError("group references relation absent from index")
        object.__setattr__(self, "groups", groups)
        group_id_set = set(group_ids)

        reverse_indexes = _immutable_mapping(self.reverse_indexes, "reverse_indexes")
        _validate_reverse_indexes(
            reverse_indexes,
            participant_ids=participant_id_set,
            relation_ids=relation_id_set,
            group_ids=group_id_set,
        )
        object.__setattr__(self, "reverse_indexes", reverse_indexes)

        boundary = _immutable_mapping(self.boundary, "boundary")
        _require_exact_keys(boundary, _BOUNDARY_KEYS, "boundary")
        if boundary.get("all_relation_endpoints_present") is not True:
            raise ValueError("index boundary must declare all relation endpoints present")
        object.__setattr__(self, "boundary", boundary)
        build_facts = _immutable_mapping(self.build_facts, "build_facts")
        _require_exact_keys(build_facts, _BUILD_FACT_KEYS, "build_facts")
        object.__setattr__(self, "build_facts", build_facts)

        for name, expected in (
            ("generated_only", True),
            ("safe_to_patch", False),
            ("production_mutation", False),
            ("automatic_fix", False),
            ("automatic_commit", False),
            ("automatic_push", False),
            ("automatic_pull_request", False),
            ("automatic_merge", False),
            ("human_review_required", True),
        ):
            value = _strict_bool(getattr(self, name), name)
            if value is not expected:
                raise ValueError(f"{name} crossed the relational index authority boundary")
        if self.index_id != self.expected_id():
            raise ValueError("index_id does not match canonical relational index identity")

    @classmethod
    def create(
        cls,
        *,
        repository_identity: Mapping[str, Any],
        profile: Mapping[str, Any],
        participants: Sequence[RelationalParticipant],
        relations: Sequence[TypedRelation],
        groups: Sequence[RelationalGroup],
        reverse_indexes: Mapping[str, Any],
        boundary: Mapping[str, Any],
        build_facts: Mapping[str, Any],
    ) -> RelationalIndex:
        participant_tuple = tuple(sorted(participants, key=lambda item: item.participant_id))
        relation_tuple = tuple(sorted(relations, key=lambda item: item.relation_id))
        group_tuple = tuple(sorted(groups, key=lambda item: item.group_id))
        identity = {
            "repository_identity": dict(repository_identity),
            "profile": dict(profile),
            "participant_ids": [item.participant_id for item in participant_tuple],
            "relation_ids": [item.relation_id for item in relation_tuple],
            "group_ids": [item.group_id for item in group_tuple],
            "reverse_indexes_digest": stable_digest(reverse_indexes, digest_size=20),
            "boundary_digest": stable_digest(boundary, digest_size=20),
        }
        return cls(
            index_id=stable_id("relindex", identity),
            repository_identity=dict(repository_identity),
            profile=dict(profile),
            participants=participant_tuple,
            relations=relation_tuple,
            groups=group_tuple,
            reverse_indexes=dict(reverse_indexes),
            boundary=dict(boundary),
            build_facts=dict(build_facts),
        )

    def expected_id(self) -> str:
        return stable_id(
            "relindex",
            {
                "repository_identity": _thaw_json(self.repository_identity),
                "profile": _thaw_json(self.profile),
                "participant_ids": [item.participant_id for item in self.participants],
                "relation_ids": [item.relation_id for item in self.relations],
                "group_ids": [item.group_id for item in self.groups],
                "reverse_indexes_digest": stable_digest(
                    _thaw_json(self.reverse_indexes), digest_size=20
                ),
                "boundary_digest": stable_digest(_thaw_json(self.boundary), digest_size=20),
            },
        )

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": RELATIONAL_INDEX_VERSION,
            "index_id": self.index_id,
            "repository_identity": _thaw_json(self.repository_identity),
            "profile": _thaw_json(self.profile),
            "participants": [item.to_dict() for item in self.participants],
            "relations": [item.to_dict() for item in self.relations],
            "groups": [item.to_dict() for item in self.groups],
            "reverse_indexes": _thaw_json(self.reverse_indexes),
            "boundary": _thaw_json(self.boundary),
            "build_facts": _thaw_json(self.build_facts),
            "generated_only": self.generated_only,
            "safe_to_patch": self.safe_to_patch,
            "production_mutation": self.production_mutation,
            "automatic_fix": self.automatic_fix,
            "automatic_commit": self.automatic_commit,
            "automatic_push": self.automatic_push,
            "automatic_pull_request": self.automatic_pull_request,
            "automatic_merge": self.automatic_merge,
            "human_review_required": self.human_review_required,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        return {**body, "index_digest": stable_digest(body, digest_size=20)}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> RelationalIndex:
        if not isinstance(value, Mapping):
            raise ValueError("relational index must be an object")
        data = dict(value)
        allowed = {
            "schema_version",
            "index_id",
            "repository_identity",
            "profile",
            "participants",
            "relations",
            "groups",
            "reverse_indexes",
            "boundary",
            "build_facts",
            "generated_only",
            "safe_to_patch",
            "production_mutation",
            "automatic_fix",
            "automatic_commit",
            "automatic_push",
            "automatic_pull_request",
            "automatic_merge",
            "human_review_required",
            "patch_authority",
            "vsa_patch_authority",
            "index_digest",
        }
        unknown = sorted(set(data) - allowed)
        if unknown:
            raise ValueError(f"unknown relational index fields: {', '.join(unknown)}")
        if data.get("schema_version") != RELATIONAL_INDEX_VERSION:
            raise ValueError("unsupported relational index schema_version")
        if data.get("patch_authority") != PATCH_AUTHORITY:
            raise ValueError("unsupported relational index patch_authority")
        if data.get("vsa_patch_authority") is not False:
            raise ValueError("relational index cannot grant VSA patch authority")
        index = cls(
            index_id=data.get("index_id"),
            repository_identity=data.get("repository_identity", {}),
            profile=data.get("profile", {}),
            participants=tuple(
                RelationalParticipant.from_dict(item)
                for item in data.get("participants", [])
            ),
            relations=tuple(TypedRelation.from_dict(item) for item in data.get("relations", [])),
            groups=tuple(RelationalGroup.from_dict(item) for item in data.get("groups", [])),
            reverse_indexes=data.get("reverse_indexes", {}),
            boundary=data.get("boundary", {}),
            build_facts=data.get("build_facts", {}),
            generated_only=data.get("generated_only"),
            safe_to_patch=data.get("safe_to_patch"),
            production_mutation=data.get("production_mutation"),
            automatic_fix=data.get("automatic_fix"),
            automatic_commit=data.get("automatic_commit"),
            automatic_push=data.get("automatic_push"),
            automatic_pull_request=data.get("automatic_pull_request"),
            automatic_merge=data.get("automatic_merge"),
            human_review_required=data.get("human_review_required"),
        )
        calculated_digest = index.to_dict()["index_digest"]
        if data.get("index_digest") != calculated_digest:
            raise ValueError("index_digest does not match canonical relational index")
        object.__setattr__(index, "_validated_index_digest", calculated_digest)
        return index

    @property
    def index_digest(self) -> str:
        """Return the validated persisted digest without rebuilding the body."""

        return self._validated_index_digest or str(self.to_dict()["index_digest"])


@dataclass(frozen=True)
class RelationalIndexReceipt:
    """Empirical build receipt kept outside the deterministic index identity."""

    index_id: str
    index_digest: str
    build_mode: str
    changed_paths: tuple[str, ...]
    wall_time_ms: int
    index_bytes: int
    participant_count: int
    relation_count: int
    group_count: int
    unresolved_mapping_count: int
    full_equivalence_verified: bool
    created_at_unix_ms: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "index_id", _required_text(self.index_id, "index_id"))
        object.__setattr__(self, "index_digest", _required_text(self.index_digest, "index_digest"))
        object.__setattr__(self, "build_mode", _required_text(self.build_mode, "build_mode"))
        if self.build_mode not in {"full", "incremental"}:
            raise ValueError("build_mode must be full or incremental")
        object.__setattr__(self, "changed_paths", _string_tuple(self.changed_paths, "changed_paths"))
        for name in (
            "wall_time_ms",
            "index_bytes",
            "participant_count",
            "relation_count",
            "group_count",
            "unresolved_mapping_count",
            "created_at_unix_ms",
        ):
            object.__setattr__(self, name, _nonnegative_int(getattr(self, name), name))
        object.__setattr__(
            self,
            "full_equivalence_verified",
            _strict_bool(self.full_equivalence_verified, "full_equivalence_verified"),
        )

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": RELATIONAL_INDEX_RECEIPT_VERSION,
            "index_id": self.index_id,
            "index_digest": self.index_digest,
            "build_mode": self.build_mode,
            "changed_paths": list(self.changed_paths),
            "wall_time_ms": self.wall_time_ms,
            "index_bytes": self.index_bytes,
            "participant_count": self.participant_count,
            "relation_count": self.relation_count,
            "group_count": self.group_count,
            "unresolved_mapping_count": self.unresolved_mapping_count,
            "full_equivalence_verified": self.full_equivalence_verified,
            "created_at_unix_ms": self.created_at_unix_ms,
            "generated_only": True,
            "safe_to_patch": False,
            "production_mutation": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
        }
        return {**body, "receipt_digest": stable_digest(body, digest_size=20)}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> RelationalIndexReceipt:
        if not isinstance(value, Mapping):
            raise ValueError("relational index receipt must be an object")
        data = dict(value)
        allowed = {
            "schema_version",
            "index_id",
            "index_digest",
            "build_mode",
            "changed_paths",
            "wall_time_ms",
            "index_bytes",
            "participant_count",
            "relation_count",
            "group_count",
            "unresolved_mapping_count",
            "full_equivalence_verified",
            "created_at_unix_ms",
            "generated_only",
            "safe_to_patch",
            "production_mutation",
            "patch_authority",
            "vsa_patch_authority",
            "receipt_digest",
        }
        unknown = sorted(set(data) - allowed)
        if unknown:
            raise ValueError(f"unknown relational index receipt fields: {', '.join(unknown)}")
        if data.get("schema_version") != RELATIONAL_INDEX_RECEIPT_VERSION:
            raise ValueError("unsupported relational index receipt schema_version")
        for name, expected in (
            ("generated_only", True),
            ("safe_to_patch", False),
            ("production_mutation", False),
            ("vsa_patch_authority", False),
        ):
            if data.get(name) is not expected:
                raise ValueError(f"receipt authority boundary crossed: {name}")
        if data.get("patch_authority") != PATCH_AUTHORITY:
            raise ValueError("unsupported receipt patch_authority")
        receipt = cls(
            index_id=data.get("index_id"),
            index_digest=data.get("index_digest"),
            build_mode=data.get("build_mode"),
            changed_paths=tuple(data.get("changed_paths", ())),
            wall_time_ms=data.get("wall_time_ms"),
            index_bytes=data.get("index_bytes"),
            participant_count=data.get("participant_count"),
            relation_count=data.get("relation_count"),
            group_count=data.get("group_count"),
            unresolved_mapping_count=data.get("unresolved_mapping_count"),
            full_equivalence_verified=data.get("full_equivalence_verified"),
            created_at_unix_ms=data.get("created_at_unix_ms"),
        )
        if data.get("receipt_digest") != receipt.to_dict()["receipt_digest"]:
            raise ValueError("receipt_digest does not match canonical receipt")
        return receipt



class RelationalIndexBuilder:
    """Build deterministic full or conservative incremental relational anatomy."""

    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        profile: RelationalIndexProfile | str = RelationalIndexProfile.STANDARD,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.profile = (
            profile if isinstance(profile, RelationalIndexProfile) else RelationalIndexProfile(str(profile).upper())
        )

    def build_full(
        self,
        *,
        anchor: CodeTopoAnchor | None = None,
        connectome: Mapping[str, Any] | None = None,
        repository_identity: Mapping[str, Any] | None = None,
    ) -> RelationalIndex:
        anchor_value = anchor or CodeTopoAnchor.build_from_files(
            _canonical_python_sources(self.repo_root)
        )
        inventory = _inventory_from_anchor(anchor_value, include_source=False)
        connectome_value = dict(
            connectome
            or enrich_connectome(build_capability_connectome(self.repo_root))
        )
        _validate_connectome(connectome_value)

        identity = dict(
            repository_identity
            or self._repository_identity(
                inventory_digest=inventory["inventory_digest"],
                connectome=connectome_value,
            )
        )
        identity["profile_digest"] = self.profile.digest

        participants, node_to_participant = _source_participants(anchor_value)
        capability_participants, capability_to_participant = _capability_participants(connectome_value)
        participants.extend(capability_participants)

        relations = _structural_relations(
            anchor_value,
            node_to_participant=node_to_participant,
        )
        implementation_relations, unresolved = _implementation_relations(
            anchor_value,
            connectome_value,
            node_to_participant=node_to_participant,
            capability_to_participant=capability_to_participant,
        )
        relations.extend(implementation_relations)
        relations = _dedupe_relations(relations)

        groups = _build_groups(
            relations=relations,
            connectome=connectome_value,
            capability_to_participant=capability_to_participant,
            unresolved_mappings=unresolved,
            profile=self.profile,
        )
        reverse_indexes = _build_reverse_indexes(
            participants=participants,
            relations=relations,
            groups=groups,
            connectome=connectome_value,
        )
        exact_count = sum(
            item.truth_class in {TruthClass.EXACT_SOURCE, TruthClass.EXACT_TEST}
            for item in relations
        )
        advisory_count = sum(
            item.truth_class is TruthClass.ADVISORY_CONNECTOME for item in relations
        )
        boundary = {
            "unsupported_languages": [],
            "unresolved_dynamic_calls": sorted(set(anchor_value.warnings)),
            "advisory_only_mappings": sorted(unresolved),
            "excluded_generated_paths": sorted(INDEX_GENERATED_PATHS),
            "warnings": sorted(set(anchor_value.warnings)),
            "all_relation_endpoints_present": True,
        }
        build_facts = {
            "anchor_version": ANCHOR_VERSION,
            "source_file_count": len(anchor_value.source_texts),
            "topology_node_count": len(anchor_value.nodes),
            "topology_edge_count": len(anchor_value.edges),
            "atomic_callable_count": inventory["total_count"],
            "participant_count": len(participants),
            "exact_relation_count": exact_count,
            "advisory_relation_count": advisory_count,
            "group_count": len(groups),
            "unresolved_mapping_count": len(unresolved),
        }
        return RelationalIndex.create(
            repository_identity=identity,
            profile={
                "name": self.profile.value,
                "budgets": dict(self.profile.budgets),
                "profile_digest": self.profile.digest,
            },
            participants=participants,
            relations=relations,
            groups=groups,
            reverse_indexes=reverse_indexes,
            boundary=boundary,
            build_facts=build_facts,
        )

    def build_incremental(
        self,
        previous: RelationalIndex | None,
        *,
        changed_paths: Sequence[str],
    ) -> RelationalIndex:
        """Conservative exact refresh.

        Phase 2 prioritizes correctness: changed paths are validated and recorded,
        then the canonical full anatomy is rebuilt. This establishes the required
        incremental/full equivalence contract without introducing a fragile AST
        delta engine. A later optimization may replace only affected groups while
        retaining this method's exact output contract.
        """
        del previous
        for path in changed_paths:
            _safe_repo_path(path)
        return self.build_full()

    def repository_identity_snapshot(self) -> dict[str, Any]:
        """Compute current freshness identity without materializing relational payloads."""

        anchor = CodeTopoAnchor.build_from_files(_canonical_python_sources(self.repo_root))
        inventory = _inventory_from_anchor(anchor, include_source=False)
        connectome = enrich_connectome(build_capability_connectome(self.repo_root))
        _validate_connectome(connectome)
        return self._repository_identity(
            inventory_digest=inventory["inventory_digest"],
            connectome=connectome,
        )

    def _repository_identity(
        self,
        *,
        inventory_digest: str,
        connectome: Mapping[str, Any],
    ) -> dict[str, Any]:
        codemap_path = self.repo_root / CODEMAP_INDEX_PATH
        topology_path = self.repo_root / CODEMAP_TOPOLOGY_PATH
        topology_digest, topology_version, topology_health = _topology_facts(topology_path)
        identity = {
            "repo_head": _repo_head(self.repo_root),
            "working_tree_digest": _working_tree_digest(self.repo_root),
            "codemap_digest": _digest_file(codemap_path),
            "topology_digest": topology_digest,
            "topology_version": topology_version,
            "topology_health": topology_health,
            "connectome_graph_digest": _required_text(
                connectome.get("graph_digest"), "connectome.graph_digest"
            ),
            "connectome_version": _required_text(
                connectome.get("version"), "connectome.version"
            ),
            "atomic_inventory_digest": _required_text(
                inventory_digest, "atomic_inventory_digest"
            ),
            "atomic_inventory_version": ATOMIC_INVENTORY_VERSION,
            "relation_ontology_digest": _relation_ontology_digest(),
            "profile_digest": self.profile.digest,
            "schema_digest": _schema_digest(self.repo_root),
        }
        return identity


class RelationalIndexStore:
    """Atomic, process-safe generated index persistence."""

    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        index_path: str | Path = DEFAULT_INDEX_PATH,
        receipt_path: str | Path = DEFAULT_RECEIPT_PATH,
        markdown_path: str | Path = DEFAULT_MARKDOWN_PATH,
        lock_path: str | Path = DEFAULT_LOCK_PATH,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.index_path = _contained_repo_target(self.repo_root, index_path)
        self.receipt_path = _contained_repo_target(self.repo_root, receipt_path)
        self.markdown_path = _contained_repo_target(self.repo_root, markdown_path)
        self.lock_path = _contained_repo_target(self.repo_root, lock_path)

    def _validated_path(self, path: Path) -> Path:
        relative = path.relative_to(self.repo_root)
        return _contained_repo_target(self.repo_root, relative)

    def write(
        self,
        index: RelationalIndex,
        *,
        build_mode: str,
        changed_paths: Sequence[str] = (),
        wall_time_ms: int = 0,
        full_equivalence_verified: bool = False,
    ) -> RelationalIndexReceipt:
        data = index.to_dict()
        _assert_no_secret_shaped_content(data)
        encoded = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        receipt = RelationalIndexReceipt(
            index_id=index.index_id,
            index_digest=data["index_digest"],
            build_mode=build_mode,
            changed_paths=tuple(_safe_repo_path(path) for path in changed_paths),
            wall_time_ms=max(0, int(wall_time_ms)),
            index_bytes=len(encoded.encode("utf-8")),
            participant_count=len(index.participants),
            relation_count=len(index.relations),
            group_count=len(index.groups),
            unresolved_mapping_count=len(index.boundary.get("advisory_only_mappings", ())),
            full_equivalence_verified=full_equivalence_verified,
            created_at_unix_ms=int(time.time() * 1000),
        )
        receipt_encoded = json.dumps(receipt.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        markdown = render_relational_index_markdown(index, receipt)
        lock_path = self._validated_path(self.lock_path)
        with _exclusive_store_lock(lock_path):
            _atomic_write_text(self._validated_path(self.index_path), encoded)
            _atomic_write_text(self._validated_path(self.receipt_path), receipt_encoded)
            _atomic_write_text(self._validated_path(self.markdown_path), markdown)
            restored = self.load()
            if restored.to_dict() != data:
                raise ValueError("written relational index failed exact reload validation")
        return receipt

    def load(self) -> RelationalIndex:
        return RelationalIndex.from_dict(_read_json(self._validated_path(self.index_path)))

    def load_receipt(self) -> RelationalIndexReceipt:
        return RelationalIndexReceipt.from_dict(_read_json(self._validated_path(self.receipt_path)))

    def validate_current(
        self,
        *,
        builder: RelationalIndexBuilder | None = None,
    ) -> dict[str, Any]:
        with _exclusive_store_lock(self._validated_path(self.lock_path)):
            index = self.load()
            receipt = self.load_receipt()
            if receipt.index_id != index.index_id or receipt.index_digest != index.index_digest:
                raise ValueError("relational index receipt is not linked to the stored index")
            expected = dict(index.repository_identity)
            stored_profile = str(index.profile["name"])
            index_id = index.index_id
            index_digest = index.index_digest
        del index, receipt
        gc.collect()
        builder_value = builder or RelationalIndexBuilder(self.repo_root, profile=stored_profile)
        actual = builder_value.repository_identity_snapshot()
        mismatches = {
            name: {"stored": expected.get(name), "current": actual.get(name)}
            for name in sorted(_REPOSITORY_IDENTITY_KEYS)
            if expected.get(name) != actual.get(name)
        }
        return {
            "ok": not mismatches,
            "status": "CURRENT" if not mismatches else "STALE",
            "index_id": index_id,
            "index_digest": index_digest,
            "mismatches": mismatches,
            "safe_to_patch": False,
            "production_mutation": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
        }


def _validate_connectome(connectome: Mapping[str, Any]) -> None:
    if connectome.get("ok") is not True:
        raise ValueError("Capability Connectome V2 is not valid")
    if connectome.get("version") != CONNECTOME_ENRICHMENT_VERSION:
        raise ValueError("unsupported Capability Connectome version")
    _required_text(connectome.get("graph_digest"), "connectome.graph_digest")
    if connectome.get("vsa_patch_authority") is not False:
        raise ValueError("Connectome cannot grant VSA patch authority")


def _source_participants(
    anchor: CodeTopoAnchor,
) -> tuple[list[RelationalParticipant], dict[str, str]]:
    participants: list[RelationalParticipant] = []
    node_to_participant: dict[str, str] = {}
    for node in sorted(
        anchor.nodes.values(),
        key=lambda item: (item.file_path, item.start_line, item.kind, item.symbol),
    ):
        if node.file_path in INDEX_GENERATED_PATHS:
            continue
        qualified = _qualified_symbol(node)
        truth = TruthClass.EXACT_TEST if _is_test_path(node.file_path) else TruthClass.EXACT_SOURCE
        participant = RelationalParticipant.create(
            participant_type=ParticipantType.ATOMIC_SYMBOL,
            role="repository_topology_node",
            truth_class=truth,
            canonical_owner="CodeTopoAnchor",
            canonical_ref=node.node_id,
            digest=node.source_hash,
            evidence_refs=(
                f"codetopo:{node.node_id}",
                f"source:{node.file_path}:{node.start_line}-{node.end_line}:{node.source_hash}",
                f"file:{node.file_path}:{anchor.file_hashes.get(node.file_path, '')}",
            ),
            freshness=Freshness.CURRENT,
            qualified_symbol=qualified,
            metadata={
                "node_id": node.node_id,
                "file_path": node.file_path,
                "kind": node.kind,
                "line_start": node.start_line,
                "line_end": node.end_line,
                "file_source_hash": anchor.file_hashes.get(node.file_path, ""),
            },
        )
        participants.append(participant)
        node_to_participant[node.node_id] = participant.participant_id
    return participants, node_to_participant


def _capability_participants(
    connectome: Mapping[str, Any],
) -> tuple[list[RelationalParticipant], dict[str, str]]:
    participants: list[RelationalParticipant] = []
    capability_to_participant: dict[str, str] = {}
    graph_digest = _required_text(connectome.get("graph_digest"), "connectome.graph_digest")
    for node in sorted(connectome.get("nodes", ()), key=lambda item: str(item.get("id", ""))):
        capability_id = _required_text(node.get("id"), "connectome.nodes[].id")
        node_digest = _required_text(node.get("node_digest"), "connectome.nodes[].node_digest")
        participant = RelationalParticipant.create(
            participant_type=ParticipantType.CAPABILITY,
            role="advisory_capability",
            truth_class=TruthClass.ADVISORY_CONNECTOME,
            canonical_owner="CapabilityConnectomeV2",
            canonical_ref=capability_id,
            digest=node_digest,
            evidence_refs=(
                f"connectome:{graph_digest}",
                f"capability:{capability_id}:{node_digest}",
            ),
            freshness=Freshness.CURRENT,
            metadata={
                "name": node.get("name", ""),
                "purpose": node.get("purpose", ""),
                "implemented_by": sorted(set(node.get("implemented_by", ()) or ())),
                "symbols": sorted(set(node.get("symbols", ()) or ())),
                "tests": sorted(set(node.get("tests", ()) or ())),
                "docs": sorted(set(node.get("docs", ()) or ())),
                "truth_boundary": node.get("truth_boundary", "advisory"),
                "grounding": node.get("grounding", "NEEDS_GROUNDING"),
            },
        )
        participants.append(participant)
        capability_to_participant[capability_id] = participant.participant_id
    return participants, capability_to_participant


def _structural_relations(
    anchor: CodeTopoAnchor,
    *,
    node_to_participant: Mapping[str, str],
) -> list[TypedRelation]:
    relations: list[TypedRelation] = []
    for edge in sorted(
        anchor.edges,
        key=lambda item: (item.edge_type, item.src_id, item.dst_id, item.evidence),
    ):
        relation_type = _EXACT_EDGE_RELATIONS.get(edge.edge_type)
        if relation_type is None:
            continue
        if edge.src_id not in node_to_participant or edge.dst_id not in node_to_participant:
            continue
        truth = TruthClass.EXACT_TEST if relation_type is RelationType.TESTS else TruthClass.EXACT_SOURCE
        relations.append(
            TypedRelation.create(
                relation_type=relation_type,
                source_participant_id=node_to_participant[edge.src_id],
                target_participant_id=node_to_participant[edge.dst_id],
                truth_class=truth,
                evidence_refs=(f"codetopo-edge:{edge.evidence}",),
                metadata={
                    "edge_type": edge.edge_type,
                    "confidence": edge.confidence,
                },
            )
        )
    return relations


def _implementation_relations(
    anchor: CodeTopoAnchor,
    connectome: Mapping[str, Any],
    *,
    node_to_participant: Mapping[str, str],
    capability_to_participant: Mapping[str, str],
) -> tuple[list[TypedRelation], list[str]]:
    relations: list[TypedRelation] = []
    unresolved: list[str] = []
    nodes_by_file: dict[str, list[Any]] = defaultdict(list)
    for node in anchor.nodes.values():
        nodes_by_file[node.file_path].append(node)

    graph_digest = str(connectome.get("graph_digest", ""))
    for capability in sorted(connectome.get("nodes", ()), key=lambda item: str(item.get("id", ""))):
        capability_id = str(capability.get("id", ""))
        target_id = capability_to_participant.get(capability_id)
        if not target_id:
            continue
        files = tuple(sorted(set(str(item) for item in capability.get("implemented_by", ()) or () if item)))
        symbols = tuple(sorted(set(str(item) for item in capability.get("symbols", ()) or () if item)))
        resolved_node_ids: set[str] = set()

        for file_path in files:
            candidates = nodes_by_file.get(file_path, [])
            if not candidates:
                unresolved.append(f"capability_file:{capability_id}:{file_path}")

        if symbols:
            for symbol in symbols:
                matches = []
                for file_path in files:
                    for node in nodes_by_file.get(file_path, []):
                        qualified = _qualified_symbol(node)
                        if "." in symbol:
                            if qualified == symbol:
                                matches.append(node)
                        elif node.symbol == symbol:
                            matches.append(node)
                unique = {item.node_id: item for item in matches}
                if len(unique) == 1:
                    resolved_node_ids.add(next(iter(unique)))
                elif not unique:
                    unresolved.append(f"capability_symbol:{capability_id}:{symbol}:missing")
                else:
                    unresolved.append(f"capability_symbol:{capability_id}:{symbol}:ambiguous")
        else:
            for file_path in files:
                module_id = anchor.module_nodes.get(file_path)
                if module_id:
                    resolved_node_ids.add(module_id)

        for node_id in sorted(resolved_node_ids):
            source_id = node_to_participant.get(node_id)
            if not source_id:
                unresolved.append(f"capability_endpoint:{capability_id}:{node_id}")
                continue
            relations.append(
                TypedRelation.create(
                    relation_type=RelationType.IMPLEMENTS_CAPABILITY,
                    source_participant_id=source_id,
                    target_participant_id=target_id,
                    truth_class=TruthClass.ADVISORY_CONNECTOME,
                    evidence_refs=(
                        f"connectome:{graph_digest}",
                        f"capability-declaration:{capability_id}",
                        f"codetopo:{node_id}",
                    ),
                    metadata={"capability_id": capability_id, "declaration_only": True},
                )
            )
    return relations, sorted(set(unresolved))


def _dedupe_relations(relations: Sequence[TypedRelation]) -> list[TypedRelation]:
    return sorted(
        {item.relation_id: item for item in relations}.values(),
        key=lambda item: item.relation_id,
    )


def _build_groups(
    *,
    relations: Sequence[TypedRelation],
    connectome: Mapping[str, Any],
    capability_to_participant: Mapping[str, str],
    unresolved_mappings: Sequence[str],
    profile: RelationalIndexProfile,
) -> list[RelationalGroup]:
    relation_by_capability: dict[str, list[TypedRelation]] = defaultdict(list)
    for relation in relations:
        capability_id = str(relation.metadata.get("capability_id", ""))
        if capability_id:
            relation_by_capability[capability_id].append(relation)

    groups: list[RelationalGroup] = []
    registries = (
        (GroupKind.MACRO_DOMAIN, MACRO_DOMAIN_CAPABILITIES),
        (GroupKind.CROSS_DOMAIN_BUNDLE, SURGICAL_BUNDLE_CAPABILITIES),
    )
    for group_kind, registry in registries:
        for purpose, capability_ids in registry.items():
            required_participant_ids: set[str] = set()
            candidate_participant_ids: set[str] = set()
            group_relations: list[TypedRelation] = []
            unresolved: list[str] = []
            bindings: list[RoleBinding] = []
            for capability_id in capability_ids:
                capability_participant_id = capability_to_participant.get(capability_id)
                if capability_participant_id is None:
                    unresolved.append(f"required_capability:{capability_id}")
                    continue
                required_participant_ids.add(capability_participant_id)
                candidate_participant_ids.add(capability_participant_id)
                bindings.append(RoleBinding(capability_participant_id, "capability", True))
                for relation in relation_by_capability.get(capability_id, ()):
                    group_relations.append(relation)
                    candidate_participant_ids.add(relation.source_participant_id)
                    candidate_participant_ids.add(relation.target_participant_id)
                    bindings.append(
                        RoleBinding(
                            relation.source_participant_id,
                            "advisory_implementation",
                            True,
                        )
                    )
                unresolved.extend(item for item in unresolved_mappings if f":{capability_id}:" in item)

            structural = [
                relation
                for relation in relations
                if relation.relation_type is not RelationType.IMPLEMENTS_CAPABILITY
                and relation.source_participant_id in candidate_participant_ids
                and relation.target_participant_id in candidate_participant_ids
            ]
            group_relations.extend(structural)
            candidate_relations = _dedupe_relations(group_relations)
            max_relations = int(profile.budgets["max_group_relations"])
            max_participants = int(profile.budgets["max_group_participants"])
            if len(required_participant_ids) > max_participants:
                raise ValueError(f"profile {profile.value} cannot contain required participants for {purpose}")
            participant_ids = set(required_participant_ids)
            group_relations = []
            budget_truncated = False
            omitted_reasons: dict[str, int] = {}
            for relation in candidate_relations:
                endpoints = {
                    relation.source_participant_id,
                    relation.target_participant_id,
                }
                if len(group_relations) >= max_relations:
                    omitted_reasons["profile_relation_budget"] = omitted_reasons.get("profile_relation_budget", 0) + 1
                    budget_truncated = True
                    continue
                if len(participant_ids | endpoints) > max_participants:
                    # The count records relations omitted because their mandatory
                    # endpoints would exceed the participant budget. This keeps
                    # omitted_relation_count in relation units while preserving
                    # the participant-budget cause in omitted_reasons.
                    omitted_reasons["profile_participant_budget"] = (
                        omitted_reasons.get("profile_participant_budget", 0) + 1
                    )
                    budget_truncated = True
                    continue
                group_relations.append(relation)
                participant_ids |= endpoints
            bindings = [item for item in bindings if item.participant_id in participant_ids]
            bindings = sorted(
                {(item.participant_id, item.role, item.required): item for item in bindings}.values(),
                key=lambda item: (item.role, item.participant_id),
            )
            if not capability_ids:
                unresolved.append(f"domain_capability_registry:{purpose}:unresolved")
            elif not participant_ids:
                unresolved.append(f"required_capabilities:{purpose}:unresolved")
            reasons = dict(sorted(omitted_reasons.items()))
            omitted_count = sum(reasons.values())
            boundary = RelationalBoundary(
                included_participant_ids=tuple(sorted(participant_ids)),
                omitted_relation_count=omitted_count,
                omitted_reasons=reasons,
                unresolved_relations=tuple(sorted(set(unresolved))),
                budget_truncated=budget_truncated,
                all_relation_endpoints_present=True,
            )
            groups.append(
                RelationalGroup.create(
                    group_kind=group_kind,
                    purpose=purpose,
                    role_bindings=bindings,
                    relations=group_relations,
                    predicates=(
                        "exact_structural_relations_require_codetopo_evidence",
                        "capability_membership_is_advisory_connectome_evidence",
                    ),
                    authority_constraints=(
                        "generated_navigation_only",
                        "human_review_required",
                        "no_patch_or_route_authority",
                    ),
                    boundary=boundary,
                    canonical_owner_refs=(
                        "CodeTopoAnchor",
                        "CapabilityConnectomeV2",
                        "RelationalIndexRegistry",
                    ),
                )
            )
    return sorted(groups, key=lambda item: item.group_id)


def _build_reverse_indexes(
    *,
    participants: Sequence[RelationalParticipant],
    relations: Sequence[TypedRelation],
    groups: Sequence[RelationalGroup],
    connectome: Mapping[str, Any],
) -> dict[str, Any]:
    by_participant: dict[str, set[str]] = defaultdict(set)
    by_node_id: dict[str, set[str]] = defaultdict(set)
    by_qualified_symbol: dict[str, set[str]] = defaultdict(set)
    by_file_path: dict[str, set[str]] = defaultdict(set)
    by_capability: dict[str, set[str]] = defaultdict(set)
    by_group_kind: dict[str, set[str]] = defaultdict(set)
    by_relation_type: dict[str, set[str]] = defaultdict(set)
    by_test_path: dict[str, set[str]] = defaultdict(set)
    by_schema: dict[str, set[str]] = defaultdict(set)
    by_authority_family: dict[str, set[str]] = defaultdict(set)

    for participant in participants:
        by_participant[participant.participant_id].add(participant.participant_id)
        metadata = participant.metadata
        node_id = str(metadata.get("node_id", ""))
        file_path = str(metadata.get("file_path", ""))
        if node_id:
            by_node_id[node_id].add(participant.participant_id)
        if participant.qualified_symbol and file_path:
            by_qualified_symbol[f"{file_path}#{participant.qualified_symbol}"].add(participant.participant_id)
        if file_path:
            by_file_path[file_path].add(participant.participant_id)
        if participant.participant_type is ParticipantType.CAPABILITY:
            by_capability[participant.canonical_ref].add(participant.participant_id)
        if file_path and _is_test_path(file_path):
            by_test_path[file_path].add(participant.participant_id)
        if participant.participant_type is ParticipantType.SCHEMA or file_path.endswith(".schema.json"):
            by_schema[participant.canonical_ref].add(participant.participant_id)
            if file_path:
                by_schema[file_path].add(participant.participant_id)
        by_authority_family[participant.canonical_owner].add(participant.participant_id)

    for relation in relations:
        by_participant[relation.source_participant_id].add(relation.relation_id)
        by_participant[relation.target_participant_id].add(relation.relation_id)
        by_relation_type[relation.relation_type.value].add(relation.relation_id)
        capability_id = str(relation.metadata.get("capability_id", ""))
        if capability_id:
            by_capability[capability_id].update(
                {relation.source_participant_id, relation.target_participant_id, relation.relation_id}
            )

    participant_map = {item.participant_id: item for item in participants}
    for group in groups:
        by_group_kind[group.group_kind.value].add(group.group_id)
        for participant_id in group.boundary.included_participant_ids:
            by_participant[participant_id].add(group.group_id)
            participant = participant_map.get(participant_id)
            if participant is not None:
                file_path = str(participant.metadata.get("file_path", ""))
                if file_path:
                    by_file_path[file_path].add(group.group_id)

    for node in connectome.get("nodes", ()):
        capability_id = str(node.get("id", ""))
        for test_path in node.get("tests", ()) or ():
            if capability_id:
                by_test_path[str(test_path)].update(by_capability.get(capability_id, ()))

    def finish(value: Mapping[str, set[str]]) -> dict[str, list[str]]:
        return {
            key: sorted(items)
            for key, items in sorted(value.items())
            if key and items
        }

    return {
        "by_participant": finish(by_participant),
        "by_node_id": finish(by_node_id),
        "by_qualified_symbol": finish(by_qualified_symbol),
        "by_file_path": finish(by_file_path),
        "by_capability": finish(by_capability),
        "by_group_kind": finish(by_group_kind),
        "by_relation_type": finish(by_relation_type),
        "by_test_path": finish(by_test_path),
        "by_schema": finish(by_schema),
        "by_authority_family": finish(by_authority_family),
        "by_arena": {},
    }


def _validate_reverse_indexes(
    reverse_indexes: Mapping[str, Any],
    *,
    participant_ids: set[str],
    relation_ids: set[str],
    group_ids: set[str],
) -> None:
    required = {
        "by_participant",
        "by_node_id",
        "by_qualified_symbol",
        "by_file_path",
        "by_capability",
        "by_group_kind",
        "by_relation_type",
        "by_test_path",
        "by_schema",
        "by_authority_family",
        "by_arena",
    }
    if set(reverse_indexes) != required:
        raise ValueError("reverse_indexes keys do not match the V1 contract")
    valid_ids = participant_ids | relation_ids | group_ids
    for index_name, index_value in reverse_indexes.items():
        if not isinstance(index_value, Mapping):
            raise ValueError(f"reverse_indexes.{index_name} must be an object")
        for key, values in index_value.items():
            _required_text(key, f"reverse_indexes.{index_name} key")
            if not isinstance(values, (list, tuple)):
                raise ValueError(f"reverse_indexes.{index_name}.{key} must be a list")
            normalized = [_required_text(item, "reverse index ID") for item in values]
            if normalized != sorted(set(normalized)):
                raise ValueError("reverse index values must be sorted and unique")
            dangling = sorted(set(normalized) - valid_ids)
            if dangling:
                raise ValueError(
                    f"reverse index {index_name}.{key} contains dangling IDs: {dangling[:3]}"
                )


def build_relational_index(
    repo_root: str | Path = ".",
    *,
    profile: RelationalIndexProfile | str = RelationalIndexProfile.STANDARD,
    persist: bool = False,
    include_index: bool = True,
) -> dict[str, Any]:
    started = time.perf_counter()
    builder = RelationalIndexBuilder(repo_root, profile=profile)
    index = builder.build_full()
    receipt = None
    if persist:
        elapsed = int((time.perf_counter() - started) * 1000)
        receipt = RelationalIndexStore(repo_root).write(
            index,
            build_mode="full",
            wall_time_ms=elapsed,
            full_equivalence_verified=True,
        )
    result = {
        "ok": True,
        "index_id": index.index_id,
        "profile": index.profile["name"],
        "participant_count": len(index.participants),
        "relation_count": len(index.relations),
        "group_count": len(index.groups),
        "receipt": receipt.to_dict() if receipt is not None else None,
        "safe_to_patch": False,
        "production_mutation": False,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": False,
    }
    if include_index:
        result["index"] = index.to_dict()
    return result


def refresh_relational_index(
    changed_paths: Sequence[str],
    repo_root: str | Path = ".",
    *,
    profile: RelationalIndexProfile | str = RelationalIndexProfile.STANDARD,
    persist: bool = True,
    include_index: bool = True,
) -> dict[str, Any]:
    started = time.perf_counter()
    builder = RelationalIndexBuilder(repo_root, profile=profile)
    store = RelationalIndexStore(repo_root)
    previous = store.load() if store.index_path.exists() else None
    index = builder.build_incremental(previous, changed_paths=changed_paths)
    full = builder.build_full()
    equivalent = index.to_dict() == full.to_dict()
    if not equivalent:
        raise ValueError("incremental relational index differs from canonical full build")
    receipt = None
    if persist:
        elapsed = int((time.perf_counter() - started) * 1000)
        receipt = store.write(
            index,
            build_mode="incremental",
            changed_paths=changed_paths,
            wall_time_ms=elapsed,
            full_equivalence_verified=equivalent,
        )
    result = {
        "ok": True,
        "index_id": index.index_id,
        "profile": index.profile["name"],
        "participant_count": len(index.participants),
        "relation_count": len(index.relations),
        "group_count": len(index.groups),
        "receipt": receipt.to_dict() if receipt is not None else None,
        "incremental_full_equivalence": equivalent,
        "safe_to_patch": False,
        "production_mutation": False,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": False,
    }
    if include_index:
        result["index"] = index.to_dict()
    return result


def query_relational_index(
    index: RelationalIndex | Mapping[str, Any],
    *,
    participant_id: str | None = None,
    node_id: str | None = None,
    qualified_symbol: str | None = None,
    file_path: str | None = None,
    capability_id: str | None = None,
    test_path: str | None = None,
    schema_ref: str | None = None,
    canonical_owner: str | None = None,
    relation_type: str | None = None,
) -> dict[str, Any]:
    value = index if isinstance(index, RelationalIndex) else RelationalIndex.from_dict(index)
    selectors = {
        "by_participant": participant_id,
        "by_node_id": node_id,
        "by_qualified_symbol": qualified_symbol,
        "by_file_path": _safe_repo_path(file_path) if file_path else None,
        "by_capability": capability_id,
        "by_test_path": _safe_repo_path(test_path) if test_path else None,
        "by_schema": _safe_repo_path(schema_ref) if schema_ref and ("/" in schema_ref or schema_ref.endswith(".json")) else schema_ref,
        "by_authority_family": canonical_owner,
        "by_relation_type": relation_type,
    }
    supplied = [(name, item) for name, item in selectors.items() if item]
    if len(supplied) != 1:
        raise ValueError("exactly one relational index query selector is required")
    index_name, key = supplied[0]
    ids = list(value.reverse_indexes[index_name].get(str(key), ()))
    if index_name == "by_qualified_symbol" and not ids and "#" not in str(key):
        ids = sorted(
            {
                item
                for lookup_key, lookup_ids in value.reverse_indexes[index_name].items()
                if str(lookup_key).endswith(f"#{key}")
                for item in lookup_ids
            }
        )
    participant_map = {item.participant_id: item.to_dict() for item in value.participants}
    relation_map = {item.relation_id: item.to_dict() for item in value.relations}
    group_map = {item.group_id: item.to_dict() for item in value.groups}
    return {
        "ok": True,
        "index_id": value.index_id,
        "selector": {"index": index_name, "key": key},
        "ids": ids,
        "participants": [participant_map[item] for item in ids if item in participant_map],
        "relations": [relation_map[item] for item in ids if item in relation_map],
        "groups": [group_map[item] for item in ids if item in group_map],
        "safe_to_patch": False,
        "production_mutation": False,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": False,
    }



RELATIONAL_NEIGHBORHOOD_VERSION = "AURA_RELATIONAL_NEIGHBORHOOD_V1"

_RELATION_CLASS_PRIORITY: Mapping[str, int] = MappingProxyType(
    {
        RelationType.CALLS.value: 0,
        RelationType.CALLED_BY.value: 0,
        RelationType.IMPORTS.value: 1,
        RelationType.IMPORTED_BY.value: 1,
        RelationType.TESTS.value: 2,
        RelationType.TESTED_BY.value: 2,
        RelationType.DECLARES.value: 3,
        RelationType.DEFINED_IN.value: 3,
        RelationType.IMPLEMENTS_CAPABILITY.value: 4,
        RelationType.REQUIRES_CAPABILITY.value: 5,
        RelationType.REQUIRES_VERIFIER.value: 5,
        RelationType.PRODUCES_EVIDENCE.value: 5,
    }
)

_TRUTH_PRIORITY: Mapping[str, int] = MappingProxyType(
    {
        TruthClass.EXACT_SOURCE.value: 0,
        TruthClass.EXACT_TEST.value: 0,
        TruthClass.EXACT_SCHEMA.value: 0,
        TruthClass.EXACT_MANIFEST.value: 0,
        TruthClass.EXACT_RUNTIME.value: 0,
        TruthClass.ADVISORY_CONNECTOME.value: 2,
        TruthClass.ADVISORY_AFFINITY.value: 3,
        TruthClass.INFERRED_MOTIF.value: 4,
        TruthClass.UNRESOLVED.value: 5,
    }
)


_REQUEST_TRUTH_CLASSES: Mapping[str, frozenset[str]] = MappingProxyType(
    {
        "EXACT_SOURCE": frozenset(
            {
                TruthClass.EXACT_SOURCE.value,
                TruthClass.EXACT_TEST.value,
                TruthClass.EXACT_SCHEMA.value,
                TruthClass.EXACT_MANIFEST.value,
                TruthClass.EXACT_RUNTIME.value,
            }
        ),
        "EXACT_DECLARED": frozenset(
            {
                TruthClass.EXACT_SOURCE.value,
                TruthClass.EXACT_TEST.value,
                TruthClass.EXACT_SCHEMA.value,
                TruthClass.EXACT_MANIFEST.value,
                TruthClass.EXACT_RUNTIME.value,
            }
        ),
        "EXACT_RUNTIME": frozenset(
            {
                TruthClass.EXACT_SOURCE.value,
                TruthClass.EXACT_TEST.value,
                TruthClass.EXACT_SCHEMA.value,
                TruthClass.EXACT_MANIFEST.value,
                TruthClass.EXACT_RUNTIME.value,
            }
        ),
        "DERIVED": frozenset(
            {
                TruthClass.EXACT_SOURCE.value,
                TruthClass.EXACT_TEST.value,
                TruthClass.EXACT_SCHEMA.value,
                TruthClass.EXACT_MANIFEST.value,
                TruthClass.EXACT_RUNTIME.value,
                TruthClass.INFERRED_MOTIF.value,
            }
        ),
        "ADVISORY": frozenset(
            {
                TruthClass.EXACT_SOURCE.value,
                TruthClass.EXACT_TEST.value,
                TruthClass.EXACT_SCHEMA.value,
                TruthClass.EXACT_MANIFEST.value,
                TruthClass.EXACT_RUNTIME.value,
                TruthClass.INFERRED_MOTIF.value,
                TruthClass.ADVISORY_CONNECTOME.value,
                TruthClass.ADVISORY_AFFINITY.value,
            }
        ),
        "UNKNOWN": frozenset(item.value for item in TruthClass),
    }
)


def _resolve_neighborhood_seeds(
    request: RelationalNeighborhoodRequest,
    index: RelationalIndex,
) -> tuple[list[str], dict[str, list[str]]]:
    participant_ids = {item.participant_id for item in index.participants}
    reasons: dict[str, list[str]] = defaultdict(list)
    missing = sorted(set(request.seed_participant_ids) - participant_ids)
    if missing:
        raise ValueError(f"relational neighborhood seed participants are missing: {missing[:5]}")
    for participant_id in request.seed_participant_ids:
        reasons[participant_id].append("exact_seed_participant_id")

    for source_ref in request.seed_source_refs:
        lookup_keys = []
        if source_ref.symbol:
            lookup_keys.append(("by_qualified_symbol", f"{source_ref.file_path}#{source_ref.symbol}"))
        lookup_keys.append(("by_file_path", source_ref.file_path))
        if request.include_tests:
            lookup_keys.append(("by_test_path", source_ref.file_path))
        resolved: set[str] = set()
        for reverse_name, key in lookup_keys:
            reverse = index.reverse_indexes.get(reverse_name, {})
            if not isinstance(reverse, Mapping):
                continue
            resolved.update(
                item for item in reverse.get(key, ()) if item in participant_ids
            )
            if reverse_name == "by_qualified_symbol" and not resolved and source_ref.symbol:
                resolved.update(
                    item
                    for lookup_key, values in reverse.items()
                    if str(lookup_key).endswith(f"#{source_ref.symbol}")
                    for item in values
                    if item in participant_ids
                )
        for participant_id in sorted(resolved):
            reasons[participant_id].append(
                f"exact_source_ref:{source_ref.file_path}#{source_ref.symbol or '*'}"
            )
    seeds = sorted(reasons)
    if not seeds:
        raise ValueError("relational neighborhood exact seeds did not resolve in the current index")
    if len(seeds) > request.max_nodes:
        raise ValueError("exact relational neighborhood seeds exceed max_nodes")
    return seeds, {key: sorted(set(value)) for key, value in sorted(reasons.items())}


def extract_relational_neighborhood(
    request: RelationalNeighborhoodRequest | Mapping[str, Any],
    index: RelationalIndex | Mapping[str, Any],
) -> dict[str, Any]:
    """Extract a deterministic, exact-seeded, resource-bounded index subgraph."""
    started = time.perf_counter()
    req = request if isinstance(request, RelationalNeighborhoodRequest) else RelationalNeighborhoodRequest.from_dict(request)
    value = index if isinstance(index, RelationalIndex) else RelationalIndex.from_dict(index)
    seeds, inclusion_reasons = _resolve_neighborhood_seeds(req, value)

    participant_map = {item.participant_id: item for item in value.participants}
    relation_map = {item.relation_id: item for item in value.relations}
    adjacency: dict[str, list[str]] = defaultdict(list)
    for relation in value.relations:
        adjacency[relation.source_participant_id].append(relation.relation_id)
        adjacency[relation.target_participant_id].append(relation.relation_id)
    for relation_ids in adjacency.values():
        relation_ids.sort()

    allowed = set(req.allowed_relation_types)
    selected_nodes: set[str] = set(seeds)
    seed_pair_count = len(selected_nodes) * (len(selected_nodes) - 1) // 2
    if seed_pair_count > req.max_candidate_pairs:
        raise ValueError("exact relational neighborhood seeds exceed max_candidate_pairs")
    selected_edges: set[str] = set()
    node_hops: dict[str, int] = {item: 0 for item in seeds}
    edge_reasons: dict[str, list[str]] = defaultdict(list)
    frontier: list[dict[str, Any]] = []
    exhausted: set[str] = set()
    queue: list[tuple[int, int, int, str, str, str]] = []

    seed_tokens = {
        token.casefold()
        for source_ref in req.seed_source_refs
        for token in (source_ref.file_path, source_ref.symbol, source_ref.source_hash)
        if token
    }

    minimum_truth_classes = _REQUEST_TRUTH_CLASSES[req.minimum_truth_class.value]

    def eligible(relation: TypedRelation) -> bool:
        if allowed and relation.relation_type.value not in allowed:
            return False
        if relation.truth_class.value not in minimum_truth_classes:
            return False
        if not req.include_auxiliary and _TRUTH_PRIORITY.get(relation.truth_class.value, 9) > 0:
            return False
        if not req.include_tests and relation.relation_type in {RelationType.TESTS, RelationType.TESTED_BY}:
            return False
        if not req.include_docs and relation.relation_type is RelationType.DOCUMENTED_BY:
            return False
        return True

    def push_from(participant_id: str, hop: int) -> None:
        if hop > req.max_hops:
            return
        for relation_id in adjacency.get(participant_id, ()):
            relation = relation_map[relation_id]
            if not eligible(relation):
                continue
            other = (
                relation.target_participant_id
                if relation.source_participant_id == participant_id
                else relation.source_participant_id
            )
            evidence_text = " ".join(relation.evidence_refs).casefold()
            objective_rank = 0 if any(token in evidence_text for token in seed_tokens) else 1
            heapq.heappush(
                queue,
                (
                    hop,
                    _TRUTH_PRIORITY.get(relation.truth_class.value, 9) * 10
                    + _RELATION_CLASS_PRIORITY.get(relation.relation_type.value, 8),
                    objective_rank,
                    relation_id,
                    participant_id,
                    other,
                ),
            )

    for seed in seeds:
        push_from(seed, 1)

    while queue:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        if elapsed_ms >= req.max_elapsed_ms:
            exhausted.add("max_elapsed_ms")
            break
        hop, _, _, relation_id, source_id, other_id = heapq.heappop(queue)
        if relation_id in selected_edges:
            continue
        if len(selected_edges) >= req.max_edges:
            exhausted.add("max_edges")
            frontier.append({"participant_id": other_id, "via_relation_id": relation_id, "hop": hop, "reason": "edge_budget"})
            continue
        if other_id not in selected_nodes and len(selected_nodes) >= req.max_nodes:
            exhausted.add("max_nodes")
            frontier.append({"participant_id": other_id, "via_relation_id": relation_id, "hop": hop, "reason": "node_budget"})
            continue
        if other_id not in selected_nodes:
            next_node_count = len(selected_nodes) + 1
            next_pair_count = next_node_count * (next_node_count - 1) // 2
            if next_pair_count > req.max_candidate_pairs:
                exhausted.add("max_candidate_pairs")
                frontier.append(
                    {
                        "participant_id": other_id,
                        "via_relation_id": relation_id,
                        "hop": hop,
                        "reason": "candidate_pair_budget",
                    }
                )
                continue
        selected_edges.add(relation_id)
        edge_reasons[relation_id].append(
            f"priority_expansion:hop={hop}:from={source_id}"
        )
        if other_id not in selected_nodes:
            selected_nodes.add(other_id)
            node_hops[other_id] = hop
            relation = relation_map[relation_id]
            inclusion_reasons.setdefault(other_id, []).append(
                f"related_by:{relation.relation_type.value}:{relation_id}"
            )
            if hop < req.max_hops:
                push_from(other_id, hop + 1)

    def build_packet() -> dict[str, Any]:
        candidate_pair_count = len(selected_nodes) * (len(selected_nodes) - 1) // 2
        groups = [
            group.to_dict()
            for group in value.groups
            if (group.boundary.included_participant_ids or group.relations)
            and set(group.boundary.included_participant_ids).issubset(selected_nodes)
            and {item.relation_id for item in group.relations}.issubset(selected_edges)
        ]
        packet = {
            "version": RELATIONAL_NEIGHBORHOOD_VERSION,
            "objective_digest": req.objective_digest,
            "index_id": value.index_id,
            "index_digest": value.index_digest,
            "profile": _thaw_json(value.profile),
            "seed_participant_ids": seeds,
            "participants": [participant_map[item].to_dict() for item in sorted(selected_nodes)],
            "relations": [relation_map[item].to_dict() for item in sorted(selected_edges)],
            "groups": groups,
            "inclusion_reasons": {
                item: sorted(set(inclusion_reasons.get(item, ())))
                for item in sorted(selected_nodes)
            },
            "edge_inclusion_reasons": {
                item: sorted(set(edge_reasons.get(item, ())))
                for item in sorted(selected_edges)
            },
            "frontier": sorted(frontier, key=lambda item: (item["hop"], item["via_relation_id"], item["participant_id"])),
            "truncation_receipt": {
                "truncated": bool(exhausted or frontier),
                "exhausted_budgets": sorted(exhausted),
                "node_count": len(selected_nodes),
                "edge_count": len(selected_edges),
                "candidate_pair_count": candidate_pair_count,
                "unexpanded_frontier_count": len(frontier),
                "elapsed_ms": 0,
                "budgets": {
                    "max_hops": req.max_hops,
                    "max_nodes": req.max_nodes,
                    "max_edges": req.max_edges,
                    "max_candidate_pairs": req.max_candidate_pairs,
                    "max_output_bytes": req.max_output_bytes,
                    "max_elapsed_ms": req.max_elapsed_ms,
                },
            },
            "safe_to_patch": False,
            "production_mutation": False,
            "automatic_fix": False,
            "automatic_merge": False,
            "human_review_required": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
        }
        packet["neighborhood_digest"] = stable_digest(packet, digest_size=20)
        return packet

    packet = build_packet()
    while len(canonical_json(packet).encode("utf-8")) > req.max_output_bytes:
        removable = sorted(selected_nodes - set(seeds), key=lambda item: (node_hops.get(item, 0), item), reverse=True)
        if not removable:
            raise ValueError("max_output_bytes is too small to retain exact neighborhood seeds")
        removed = removable[0]
        selected_nodes.remove(removed)
        exhausted.add("max_output_bytes")
        for relation_id in list(selected_edges):
            relation = relation_map[relation_id]
            if removed in {relation.source_participant_id, relation.target_participant_id}:
                selected_edges.remove(relation_id)
                edge_reasons.pop(relation_id, None)
        inclusion_reasons.pop(removed, None)
        frontier.append({"participant_id": removed, "via_relation_id": "output_byte_trim", "hop": node_hops.get(removed, req.max_hops), "reason": "output_byte_budget"})
        packet = build_packet()

    packet["truncation_receipt"]["output_bytes"] = len(canonical_json(packet).encode("utf-8"))
    packet["neighborhood_digest"] = stable_digest(
        {key: value for key, value in packet.items() if key != "neighborhood_digest"},
        digest_size=20,
    )
    if len(canonical_json(packet).encode("utf-8")) > req.max_output_bytes:
        raise ValueError("relational neighborhood exceeded max_output_bytes after canonicalization")
    return packet

def relational_index_status(repo_root: str | Path = ".") -> dict[str, Any]:
    store = RelationalIndexStore(repo_root)
    if not store.index_path.exists():
        return {
            "ok": False,
            "status": "MISSING",
            "path": store.index_path.relative_to(store.repo_root).as_posix(),
            "safe_to_patch": False,
            "production_mutation": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
        }
    try:
        return store.validate_current()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "status": "CORRUPT_OR_UNSUPPORTED",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "safe_to_patch": False,
            "production_mutation": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
        }


def render_relational_index_markdown(
    index: RelationalIndex,
    receipt: RelationalIndexReceipt | None = None,
) -> str:
    facts = index.build_facts
    lines = [
        "# Aura Relational Anatomy Index",
        "",
        f"- Schema: `{RELATIONAL_INDEX_VERSION}`",
        f"- Index ID: `{index.index_id}`",
        f"- Repository HEAD: `{index.repository_identity['repo_head']}`",
        f"- Profile: `{index.profile['name']}`",
        f"- Participants: {len(index.participants)}",
        f"- Relations: {len(index.relations)}",
        f"- Groups: {len(index.groups)}",
        f"- Atomic callables: {facts.get('atomic_callable_count', 0)}",
        f"- Exact relations: {facts.get('exact_relation_count', 0)}",
        f"- Advisory relations: {facts.get('advisory_relation_count', 0)}",
        f"- Unresolved mappings: {facts.get('unresolved_mapping_count', 0)}",
        "- Authority: generated navigation only; no patch, route, model, or merge authority",
    ]
    if receipt is not None:
        lines.extend(
            [
                "",
                "## Build receipt",
                "",
                f"- Mode: `{receipt.build_mode}`",
                f"- Wall time: {receipt.wall_time_ms} ms",
                f"- Bytes: {receipt.index_bytes}",
                f"- Full equivalence verified: `{receipt.full_equivalence_verified}`",
            ]
        )
    lines.extend(["", "## Groups", ""])
    for group in index.groups:
        lines.append(
            f"- `{group.group_kind.value}` / `{group.purpose}`: "
            f"{len(group.boundary.included_participant_ids)} participants, "
            f"{len(group.relations)} relations, "
            f"{len(group.boundary.unresolved_relations)} unresolved"
        )
    return "\n".join(lines) + "\n"


def _thread_lock_for(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _THREAD_LOCKS_GUARD:
        return _THREAD_LOCKS.setdefault(key, threading.Lock())


def _acquire_process_lock(handle: BinaryIO) -> None:
    handle.seek(0)
    if os.name == "nt":
        if not handle.read(1):
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        _file_lock_backend.locking(handle.fileno(), _file_lock_backend.LK_LOCK, 1)
    else:
        _file_lock_backend.flock(handle.fileno(), _file_lock_backend.LOCK_EX)


def _release_process_lock(handle: BinaryIO) -> None:
    handle.seek(0)
    if os.name == "nt":
        _file_lock_backend.locking(handle.fileno(), _file_lock_backend.LK_UNLCK, 1)
    else:
        _file_lock_backend.flock(handle.fileno(), _file_lock_backend.LOCK_UN)


@contextmanager
def _exclusive_store_lock(path: Path) -> Iterator[None]:
    thread_lock = _thread_lock_for(path)
    with thread_lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a+b") as handle:
            _acquire_process_lock(handle)
            try:
                yield
            finally:
                _release_process_lock(handle)


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        if os.name != "nt":
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--profile",
        choices=[item.value.lower() for item in RelationalIndexProfile],
        default="standard",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("build")
    refresh = subparsers.add_parser("refresh")
    refresh.add_argument("--changed", nargs="+", required=True)
    subparsers.add_parser("status")
    subparsers.add_parser("validate")
    query = subparsers.add_parser("query")
    query_group = query.add_mutually_exclusive_group(required=True)
    query_group.add_argument("--participant")
    query_group.add_argument("--node")
    query_group.add_argument("--symbol")
    query_group.add_argument("--file")
    query_group.add_argument("--capability")
    query_group.add_argument("--relation")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _cli_parser().parse_args(argv)
    profile = RelationalIndexProfile(args.profile.upper())
    if args.command == "build":
        result = build_relational_index(
            args.repo_root,
            profile=profile,
            persist=True,
            include_index=False,
        )
    elif args.command == "refresh":
        result = refresh_relational_index(
            args.changed,
            args.repo_root,
            profile=profile,
            persist=True,
            include_index=False,
        )
    elif args.command == "status":
        result = relational_index_status(args.repo_root)
    elif args.command == "validate":
        result = RelationalIndexStore(args.repo_root).validate_current()
    else:
        index = RelationalIndexStore(args.repo_root).load()
        result = query_relational_index(
            index,
            participant_id=args.participant,
            node_id=args.node,
            qualified_symbol=args.symbol,
            file_path=args.file,
            capability_id=args.capability,
            relation_type=args.relation,
        )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("ok") is True else 1


__all__ = [
    "RELATIONAL_INDEX_RECEIPT_VERSION",
    "RELATIONAL_INDEX_VERSION",
    "RelationalIndex",
    "RelationalIndexBuilder",
    "RelationalIndexProfile",
    "RelationalIndexReceipt",
    "RelationalIndexStore",
    "build_relational_index",
    "query_relational_index",
    "refresh_relational_index",
    "relational_index_status",
    "render_relational_index_markdown",
]


if __name__ == "__main__":
    raise SystemExit(main())
