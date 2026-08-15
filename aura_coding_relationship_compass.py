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
from enum import Enum
import hashlib
import hmac
import json
import math
from pathlib import Path
import re
import subprocess
import time
import tokenize
from typing import Any, Mapping, Sequence

from aura_capability_connectome import build_capability_connectome, find_capability_path
from aura_capability_connectome_v2 import enrich_connectome, enrich_path
from aura_emergent_evidence_spine import AuraEmergentEvidenceSpine, EmergentEvidenceRequest
from aura_emergent_potential_repl import discover_bounded_emergent_candidates
from aura_emergent_result_verifier import verify_bounded_emergent_discovery
from aura_change_graph import build_compass_change_graph, compile_compass_act_capsules
from aura_agent_ir_compiler import AgentIRCompiler
from aura_architect_council_v3 import route_compass_failure_classes
from aura_event_contracts import stable_digest
from aura_polysynthetic_intent import PolysyntheticIntentPacket
from aura_relational_index import (
    RelationalIndex,
    RelationalIndexBuilder,
    RelationalIndexStore,
    build_relational_index,
    extract_relational_neighborhood,
)
from aura_relational_synthesis import compile_relational_shadow_capsule
from aura_relationship_contracts import (
    AuthorityPosture,
    BilateralPlanningContract,
    CompassObjectiveContract,
    InterfaceActor,
    InterfaceBoundary,
    InterfaceDataClass,
    InterfaceLifecycle,
    InterfaceOperation,
    InterfacePortCardinality,
    InterfacePortDirection,
    InterfaceResourceClass,
    ProofStatus as ContractProofStatus,
    RelationalNeighborhoodRequest,
    RelationshipDomain,
    RelationshipInterfaceSpec,
    RepositoryIdentity,
    ResourceBudget,
    SourceReference,
    TruthClass as ContractTruthClass,
    capability_class_index,
    capability_selections_from_path,
    content_digest,
    evaluate_typed_relationship_compatibility,
    project_relationship_contract,
)
from aura_coding_waboose_breadboard import compile_relationship_breadboard
from aura_relationship_atlas import (
    AtlasSnapshot,
    WiringDisposition,
    build_objective_relationship_atlas,
    compile_atlas_projection,
    relationships_for_participant,
    validate_relationship_atlas,
)

COMPASS_VERSION = "AURA_CODING_RELATIONSHIP_COMPASS_V1"
COMPASS_GROUNDING_RECEIPT_VERSION = "AURA_COMPASS_GROUNDING_RECEIPT_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


class CompassRolloutMode(str, Enum):
    SHADOW = "SHADOW"
    LIMITED = "LIMITED"
    PAIRED_LIVE = "PAIRED_LIVE"


def _normalize_compass_rollout_budget(budget: Mapping[str, Any] | None) -> dict[str, float | int]:
    if budget is None:
        return {}
    if not isinstance(budget, Mapping):
        raise ValueError("Compass rollout budget must be a mapping")
    allowed = {"max_tokens", "max_cost_usd", "max_seconds", "max_calls"}
    unknown = sorted(set(map(str, budget)) - allowed)
    if unknown:
        raise ValueError(f"unsupported Compass rollout budget fields: {unknown}")
    normalized: dict[str, float | int] = {}
    for key, value in budget.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"Compass rollout budget {key} must be positive")
        numeric = float(value)
        if not math.isfinite(numeric) or numeric <= 0:
            raise ValueError(f"Compass rollout budget {key} must be positive and finite")
        if key in {"max_tokens", "max_calls"}:
            if not numeric.is_integer():
                raise ValueError(f"Compass rollout budget {key} must be a positive integer")
            normalized[str(key)] = int(numeric)
        else:
            normalized[str(key)] = numeric
    return normalized


def validate_compass_rollout(
    mode: CompassRolloutMode | str,
    *,
    provider: str = "",
    budget: Mapping[str, Any] | None = None,
    nonce: str = "",
    verifier_ref: str = "",
) -> dict[str, Any]:
    try:
        rollout = mode if isinstance(mode, CompassRolloutMode) else CompassRolloutMode(str(mode).upper())
    except ValueError as exc:
        raise ValueError("unsupported Compass rollout mode") from exc
    normalized_budget = _normalize_compass_rollout_budget(budget)
    missing: list[str] = []
    if rollout is CompassRolloutMode.LIMITED and not str(verifier_ref or "").strip():
        missing.append("verifier_ref")
    if rollout is CompassRolloutMode.PAIRED_LIVE:
        if not str(provider or "").strip():
            missing.append("provider")
        if not normalized_budget:
            missing.append("budget")
        if not str(nonce or "").strip():
            missing.append("nonce")
        if not str(verifier_ref or "").strip():
            missing.append("verifier_ref")
    admitted = not missing
    return {
        "mode": rollout.value,
        "admitted": admitted,
        "missing": missing,
        "provider": str(provider or ""),
        "budget": normalized_budget,
        "nonce_digest": _stable_digest(str(nonce or "")) if nonce else "",
        "verifier_ref": str(verifier_ref or ""),
        "provider_execution_authorized": False,
        "production_mutation": False,
        "human_review_required": True,
    }


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

_RELATIONAL_PLANE_CACHE: dict[tuple[str, str, str, str], dict[str, Any]] = {}
_RELATIONAL_PLANE_CACHE_LIMIT = 4


def _stable_digest(value: Any, *, digest_size: int = 24) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.blake2b(raw, digest_size=digest_size).hexdigest()


def _ordered_unique(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if str(value)))


_STRUCTURED_ATLAS_REFERENCE_KEYS = frozenset(
    {
        "participant_refs",
        "participant_ref",
        "participant_id",
        "canonical_ref",
        "evidence_refs",
        "evidence_ref",
        "file_path",
        "file",
        "path",
        "qualified_symbol",
        "symbol",
    }
)


def _structured_atlas_references(payload: Mapping[str, Any]) -> set[str]:
    """Collect only explicitly typed Atlas references, never prose tokens."""
    references: set[str] = set()

    def add(raw: Any) -> None:
        value = str(raw or "").replace("\\", "/").strip().lower()
        if not value:
            return
        references.add(value)
        for prefix in ("file:", "path:", "symbol:", "participant:", "participant_id:"):
            if value.startswith(prefix):
                references.add(value[len(prefix):].strip())
        for separator in ("::", "#", "@"):
            if separator in value:
                references.update(
                    part.strip() for part in value.split(separator) if part.strip()
                )

    def visit(value: Any, *, typed: bool = False) -> None:
        if isinstance(value, Mapping):
            for key, item in value.items():
                key_is_typed = str(key).lower() in _STRUCTURED_ATLAS_REFERENCE_KEYS
                visit(item, typed=typed or key_is_typed)
        elif isinstance(value, (list, tuple, set)):
            for item in value:
                visit(item, typed=typed)
        elif typed and isinstance(value, (str, int)):
            add(value)

    visit(payload)
    return references


def _reference_targets_path(reference: str, path: str) -> bool:
    reference = reference.replace("\\", "/").strip().lower()
    path = path.replace("\\", "/").strip().lower().lstrip("./")
    if not reference or not path:
        return False
    candidates = {reference}
    for prefix in ("file:", "path:", "participant:", "participant_id:"):
        if reference.startswith(prefix):
            candidates.add(reference[len(prefix):].strip())
    return any(
        candidate == path
        or candidate.endswith("/" + path)
        or candidate.startswith(path + "#")
        or candidate.startswith(path + "::")
        or candidate.startswith(path + ":")
        or ("/" + path + "#") in candidate
        or ("/" + path + "::") in candidate
        for candidate in candidates
    )


def _semantic_obligations(
    payload: Mapping[str, Any],
    bilateral: BilateralPlanningContract,
) -> dict[str, Any]:
    """Project obligations only from structured Atlas scope references.

    Free-form notes, risks, effects, and other prose are intentionally ignored
    so coincidental words can never become semantic evidence.
    """
    references = _structured_atlas_references(payload)
    scope_grounded = any(
        _reference_targets_path(reference, allowed_path)
        for reference in references
        for allowed_path in bilateral.allowed_paths
    )
    if not scope_grounded:
        return {}
    return {
        "positive_requirements": list(bilateral.positive_requirements),
        "negative_requirements_at_risk": list(bilateral.negative_requirements),
        "guardrail_ids": list(
            dict.fromkeys(
                (
                    *bilateral.hard_guardrail_ids,
                    *bilateral.human_guardrail_ids,
                    *bilateral.editable_guardrail_ids,
                )
            )
        ),
        "required_verifiers": list(bilateral.required_verifiers),
        "repository_head": bilateral.repository_head,
        "allowed_path_set_digest": bilateral.allowed_path_set_digest,
    }


def _compass_digest_payload(value: Mapping[str, Any]) -> dict[str, Any]:
    payload = json.loads(json.dumps(dict(value), sort_keys=True, default=str))
    payload.pop("compass_digest", None)
    neighborhood = payload.get("relational_neighborhood")
    if isinstance(neighborhood, dict):
        neighborhood.pop("index_source", None)
    atlas = payload.get("atlas")
    if isinstance(atlas, dict):
        atlas.pop("cache_hit", None)
    return payload


def _canonical_grounding_binding(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "file_path": str(value.get("file_path") or ""),
        "symbol": str(value.get("qualified_symbol") or value.get("symbol") or ""),
        "line_start": int(value.get("line_start") or value.get("start_line") or 0),
        "line_end": int(value.get("line_end") or value.get("end_line") or 0),
        "source_hash": str(value.get("source_hash") or ""),
        "file_source_hash": str(value.get("file_source_hash") or ""),
    }


def _build_compass_grounding_receipt(
    *,
    packet: Mapping[str, Any],
    evidence: Mapping[str, Any],
    targets: Sequence[Mapping[str, Any]],
    required_tests: Sequence[str],
) -> dict[str, Any]:
    bindings = [_canonical_grounding_binding(item) for item in targets]
    receipt = {
        "version": COMPASS_GROUNDING_RECEIPT_VERSION,
        "grounding_digest": str(packet.get("grounding_digest") or ""),
        "repository_head": str(evidence.get("repo_head") or ""),
        "evidence_packet_digest": str(evidence.get("packet_digest") or ""),
        "atomic_inventory_digest": str((evidence.get("atomic_inventory") or {}).get("inventory_digest") or ""),
        "target_bindings": bindings,
        "source_evidence_digest": stable_digest(bindings),
        "required_tests": _ordered_unique(required_tests),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": False,
    }
    return receipt


def _live_repository_identity(
    repo_root: Path,
    cached_index: Mapping[str, Any],
    *,
    repo_head: str,
    connectome_graph_digest: str,
    connectome_version: str,
    atomic_inventory_digest: str,
) -> dict[str, Any]:
    profile = cached_index.get("profile") or {}
    profile_name = str(profile.get("name") or "STANDARD") if isinstance(profile, Mapping) else "STANDARD"
    return RelationalIndexBuilder(repo_root, profile=profile_name).repository_identity_snapshot(
        repo_head=repo_head,
        inventory_digest=atomic_inventory_digest,
        connectome={
            "ok": True,
            "graph_digest": connectome_graph_digest,
            "version": connectome_version,
            "vsa_patch_authority": False,
        },
    )


def _relational_cache_entry_is_current(
    repo_root: Path,
    cached_index: Mapping[str, Any],
    *,
    repo_head: str,
    connectome_graph_digest: str,
    connectome_version: str,
    atomic_inventory_digest: str,
) -> bool:
    cached_identity = cached_index.get("repository_identity") or {}
    if not isinstance(cached_identity, Mapping) or not cached_identity:
        return False
    grounded_identity = {
        "repo_head": repo_head,
        "connectome_graph_digest": connectome_graph_digest,
        "connectome_version": connectome_version,
        "atomic_inventory_digest": atomic_inventory_digest,
    }
    if any(cached_identity.get(key) != value for key, value in grounded_identity.items()):
        return False
    try:
        live_identity = _live_repository_identity(
            repo_root,
            cached_index,
            repo_head=repo_head,
            connectome_graph_digest=connectome_graph_digest,
            connectome_version=connectome_version,
            atomic_inventory_digest=atomic_inventory_digest,
        )
    except (OSError, ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False
    identity_fields = (
        "working_tree_digest",
        "codemap_digest",
        "topology_digest",
        "topology_version",
        "topology_health",
        "atomic_inventory_version",
        "relation_ontology_digest",
        "profile_digest",
        "schema_digest",
    )
    return all(cached_identity.get(key) == live_identity.get(key) for key in identity_fields)


def _tokens(value: str) -> set[str]:
    return set(_TOKEN_RE.findall(str(value or "").lower()))


def is_coding_relationship_compass_intent(objective: str) -> bool:
    """Return whether a coding objective explicitly requests relational-plane grounding.

    Generic architecture, capability, or refactor language must not divert established
    Architect workflows into the Compass.  Admission requires a named Compass plane or
    an explicit relational-combination request.
    """
    lowered = " ".join(str(objective or "").lower().split())
    if not lowered:
        return False
    if "coding relationship compass" in lowered or "relationship compass" in lowered:
        return True

    tokens = _tokens(lowered)
    coding_hits = tokens & {"architect", "code", "coding", "function", "refactor", "surgeon"}
    named_plane_hits = tokens & {"atlas", "connectome"}
    relational_hits = tokens & {
        "combine",
        "emergent",
        "relation",
        "relational",
        "relationship",
        "synthesis",
        "wire",
        "wiring",
    }

    if named_plane_hits and coding_hits:
        return True
    return bool(coding_hits) and len(relational_hits) >= 2


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


def _partition_explicit_test_targets(
    repo_root: Path,
    target_files: Sequence[str],
    target_tests: Sequence[str],
) -> tuple[list[str], list[str]]:
    """Separate exact source targets from first-class explicit test targets.

    Older callers sometimes supplied test paths through ``target_files``. Preserve
    that intent while giving new callers a dedicated lane whose ordering cannot be
    displaced by topology-only regression suggestions.
    """

    source_files: list[str] = []
    explicit_tests: list[str] = []
    for raw in [*target_files, *target_tests]:
        path = str(raw or "").strip().replace("\\", "/")
        if not path or not (repo_root / path).is_file():
            continue
        basename = Path(path).name
        is_test = path.startswith("tests/") or basename.startswith("test_")
        if is_test:
            explicit_tests.append(path)
        elif raw in target_files:
            source_files.append(path)
    return _ordered_unique(source_files), _ordered_unique(explicit_tests)


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


def _repository_head(repo_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return ""
    head = result.stdout.strip().lower()
    return head if re.fullmatch(r"[0-9a-f]{40}", head) else ""


def _source_text(path: Path) -> str:
    try:
        with tokenize.open(path) as handle:
            return handle.read()
    except (OSError, SyntaxError, UnicodeError) as exc:
        raise ValueError(f"unable to read injected evidence source: {path}") from exc


def _validate_injected_evidence_packet(repo_root: Path, evidence: Mapping[str, Any]) -> dict[str, Any]:
    packet = dict(evidence)
    actual_head = _repository_head(repo_root)
    if not actual_head or str(packet.get("repo_head") or "").lower() != actual_head:
        raise ValueError("injected evidence is not bound to the current repository HEAD")

    source_records = [
        item for item in packet.get("source_slices", []) or []
        if isinstance(item, Mapping)
    ]
    if not source_records:
        raise ValueError("injected evidence has no exact source slices")

    records: list[Mapping[str, Any]] = list(source_records)
    inventory = packet.get("atomic_inventory") or {}
    if isinstance(inventory, Mapping):
        records.extend(
            item
            for item in inventory.get("selected_atomic_functions", []) or []
            if isinstance(item, Mapping)
            and item.get("file_source_hash")
            and item.get("source_hash")
            and (item.get("line_start") or item.get("start_line"))
            and (item.get("line_end") or item.get("end_line"))
        )

    for record in records:
        file_path = str(record.get("file_path") or "")
        relative = Path(file_path)
        if not file_path or relative.is_absolute() or ".." in relative.parts:
            raise ValueError("injected evidence contains a non-canonical source path")
        source_path = repo_root / relative
        if not source_path.is_file():
            raise ValueError(f"injected evidence source is missing: {file_path}")
        source_text = _source_text(source_path)
        actual_file_hash = hashlib.sha256(source_text.encode("utf-8", errors="replace")).hexdigest()
        if str(record.get("file_source_hash") or "") != actual_file_hash:
            raise ValueError(f"injected evidence file hash mismatch: {file_path}")

        line_start = int(record.get("line_start") or record.get("start_line") or 0)
        line_end = int(record.get("line_end") or record.get("end_line") or 0)
        if line_start <= 0 or line_end < line_start:
            raise ValueError(f"injected evidence has an invalid source span: {file_path}")
        lines = source_text.splitlines()
        if line_end > len(lines):
            raise ValueError(f"injected evidence source span is outside the file: {file_path}")
        actual_source_hash = hashlib.sha256(
            "\n".join(lines[line_start - 1:line_end]).encode("utf-8", errors="replace")
        ).hexdigest()
        if str(record.get("source_hash") or "") != actual_source_hash:
            raise ValueError(f"injected evidence source hash mismatch: {file_path}")
    return packet


def _validated_relational_index_digest(relational_index: Mapping[str, Any]) -> str:
    """Recompute and verify the canonical digest of a supplied Relational Index."""
    if not isinstance(relational_index, Mapping):
        raise ValueError("active relational index must be an object")
    body = dict(relational_index)
    supplied_digest = body.pop("index_digest", None)
    if not isinstance(supplied_digest, str) or not supplied_digest:
        raise ValueError("active relational index is missing index_digest")
    calculated_digest = stable_digest(body, digest_size=20)
    if not hmac.compare_digest(supplied_digest, calculated_digest):
        raise ValueError(
            "active relational index digest mismatch: supplied content was modified"
        )
    return calculated_digest


def _validate_supplied_atlas_snapshot(
    atlas: AtlasSnapshot,
    *,
    evidence: Mapping[str, Any],
    relational_index: Mapping[str, Any],
    connectome: Mapping[str, Any],
) -> AtlasSnapshot:
    """Bind a caller-supplied Atlas to current exact evidence and index identity."""
    validated_index_digest = _validated_relational_index_digest(relational_index)
    report = validate_relationship_atlas(atlas)
    if report.get("ok") is not True:
        issues = "; ".join(str(item) for item in report.get("issues", []) or [])
        raise ValueError(f"supplied Atlas snapshot failed integrity validation: {issues}")

    identity = relational_index.get("repository_identity") or {}
    if not isinstance(identity, Mapping):
        raise ValueError("active relational index is missing repository_identity")
    inventory = evidence.get("atomic_inventory") or {}
    if not isinstance(inventory, Mapping):
        inventory = {}
    expected = {
        "repository_head": str(evidence.get("repo_head") or identity.get("repo_head") or ""),
        "working_tree_digest": str(identity.get("working_tree_digest") or ""),
        "codemap_digest": str(identity.get("codemap_digest") or ""),
        "topology_digest": str(identity.get("topology_digest") or ""),
        "connectome_digest": str(connectome.get("graph_digest") or identity.get("connectome_graph_digest") or ""),
        "atomic_inventory_digest": str(inventory.get("inventory_digest") or identity.get("atomic_inventory_digest") or ""),
        "relational_index_digest": validated_index_digest,
    }
    mismatches = {
        name: {"snapshot": getattr(atlas, name), "current": value}
        for name, value in expected.items()
        if not value or getattr(atlas, name) != value
    }
    if mismatches:
        names = ", ".join(sorted(mismatches))
        raise ValueError(
            "supplied Atlas snapshot is stale or belongs to different evidence "
            f"({names})"
        )
    return atlas


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




def _compatibility_neighborhood_from_raw_index(
    request: RelationalNeighborhoodRequest,
    relational_index: Mapping[str, Any],
) -> dict[str, Any]:
    """Project a bounded legacy test fixture after its content digest is verified.

    This compatibility path exists only for pre-C3 caller fixtures paired with an
    already supplied Atlas snapshot. Canonical production indexes must pass
    ``RelationalIndex.from_dict`` and never reach this function.
    """
    index_digest = _validated_relational_index_digest(relational_index)
    participants = [
        dict(item)
        for item in relational_index.get("participants", ()) or ()
        if isinstance(item, Mapping) and item.get("participant_id")
    ]
    participant_map = {str(item["participant_id"]): item for item in participants}
    missing_seed_ids = sorted(
        str(item) for item in request.seed_participant_ids if str(item) not in participant_map
    )
    if missing_seed_ids:
        raise ValueError(
            f"legacy relational neighborhood seed participants are missing: {missing_seed_ids[:5]}"
        )
    exact_seeds = {str(item) for item in request.seed_participant_ids}
    for source_ref in request.seed_source_refs:
        matches: set[str] = set()
        for participant in participants:
            metadata = participant.get("metadata") or {}
            if not isinstance(metadata, Mapping):
                continue
            if (
                str(metadata.get("file_path") or "") == source_ref.file_path
                and (
                    not source_ref.symbol
                    or str(participant.get("qualified_symbol") or "") == source_ref.symbol
                    or (
                        "." not in source_ref.symbol
                        and str(participant.get("qualified_symbol") or "").endswith(
                            f".{source_ref.symbol}"
                        )
                    )
                )
                and int(metadata.get("line_start") or 0) == source_ref.line_start
                and int(metadata.get("line_end") or 0) == source_ref.line_end
                and str(participant.get("digest") or "") == source_ref.source_hash
                and (
                    not source_ref.file_source_hash
                    or str(metadata.get("file_source_hash") or "")
                    == source_ref.file_source_hash
                )
            ):
                matches.add(str(participant["participant_id"]))
        if len(matches) != 1:
            raise ValueError(
                "legacy relational neighborhood source ref must resolve to exactly one current "
                f"source participant: {source_ref.file_path}#{source_ref.symbol or '*'} "
                f"at {source_ref.line_start}-{source_ref.line_end} resolved {len(matches)}"
            )
        exact_seeds.update(matches)
    if not exact_seeds:
        raise ValueError("legacy relational index did not resolve any exact neighborhood seed")
    selected = set(exact_seeds)

    relations = [
        dict(item)
        for item in relational_index.get("relations", ()) or ()
        if isinstance(item, Mapping) and item.get("relation_id")
    ]
    selected_edges: list[dict[str, Any]] = []
    frontier: list[dict[str, Any]] = []
    for hop in range(1, request.max_hops + 1):
        changed = False
        for relation in sorted(relations, key=lambda item: str(item.get("relation_id") or "")):
            source = str(relation.get("source_participant_id") or "")
            target = str(relation.get("target_participant_id") or "")
            if source not in selected and target not in selected:
                continue
            if relation in selected_edges:
                continue
            other = target if source in selected else source
            if len(selected_edges) >= request.max_edges:
                frontier.append({"participant_id": other, "via_relation_id": str(relation.get("relation_id") or ""), "hop": hop, "reason": "edge_budget"})
                continue
            if other not in selected and len(selected) >= request.max_nodes:
                frontier.append({"participant_id": other, "via_relation_id": str(relation.get("relation_id") or ""), "hop": hop, "reason": "node_budget"})
                continue
            selected_edges.append(relation)
            if other in participant_map and other not in selected:
                selected.add(other)
                changed = True
        if not changed:
            break

    pair_count = len(selected) * (len(selected) - 1) // 2
    exhausted = []
    if pair_count > request.max_candidate_pairs:
        exhausted.append("max_candidate_pairs")
    packet: dict[str, Any] = {
        "version": "AURA_RELATIONAL_NEIGHBORHOOD_V1",
        "objective_digest": request.objective_digest,
        "index_id": str(relational_index.get("index_id") or "legacy_digest_validated"),
        "index_digest": index_digest,
        "profile": dict(relational_index.get("profile") or {}),
        "seed_participant_ids": sorted(exact_seeds),
        "participants": [participant_map[item] for item in sorted(selected)],
        "relations": sorted(selected_edges, key=lambda item: str(item.get("relation_id") or "")),
        "groups": [],
        "inclusion_reasons": {item: ["legacy_exact_seed_or_bounded_relation"] for item in sorted(selected)},
        "edge_inclusion_reasons": {str(item.get("relation_id") or ""): ["legacy_bounded_projection"] for item in selected_edges},
        "frontier": sorted(frontier, key=lambda item: (item["hop"], item["via_relation_id"], item["participant_id"])),
        "truncation_receipt": {
            "truncated": bool(exhausted or frontier),
            "exhausted_budgets": exhausted,
            "node_count": len(selected),
            "edge_count": len(selected_edges),
            "candidate_pair_count": min(pair_count, request.max_candidate_pairs),
            "unexpanded_frontier_count": len(frontier),
            "elapsed_ms": 0,
            "budgets": {
                "max_hops": request.max_hops,
                "max_nodes": request.max_nodes,
                "max_edges": request.max_edges,
                "max_candidate_pairs": request.max_candidate_pairs,
                "max_output_bytes": request.max_output_bytes,
                "max_elapsed_ms": request.max_elapsed_ms,
            },
        },
        "compatibility_projection": True,
        "safe_to_patch": False,
        "production_mutation": False,
        "automatic_fix": False,
        "automatic_merge": False,
        "human_review_required": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": False,
    }
    packet["neighborhood_digest"] = stable_digest(packet, digest_size=20)
    if len(json.dumps(packet, sort_keys=True, separators=(",", ":")).encode("utf-8")) > request.max_output_bytes:
        raise ValueError("legacy relational neighborhood exceeded max_output_bytes")
    return packet

def _source_references_from_evidence(evidence: Mapping[str, Any]) -> tuple[SourceReference, ...]:
    records: list[Mapping[str, Any]] = []
    inventory = evidence.get("atomic_inventory") or {}
    if isinstance(inventory, Mapping):
        records.extend(
            item
            for item in inventory.get("selected_atomic_functions", ()) or ()
            if isinstance(item, Mapping)
        )
    records.extend(
        item
        for item in evidence.get("source_slices", ()) or ()
        if isinstance(item, Mapping)
    )
    refs: dict[tuple[str, str, int, int, str], SourceReference] = {}
    for item in records:
        file_path = str(item.get("file_path") or "")
        symbol = str(item.get("qualified_symbol") or item.get("symbol") or "")
        line_start = int(item.get("line_start") or item.get("start_line") or 0)
        line_end = int(item.get("line_end") or item.get("end_line") or 0)
        source_hash = str(item.get("source_hash") or "")
        if not file_path or line_start <= 0 or line_end < line_start or not source_hash:
            continue
        ref = SourceReference(
            file_path=file_path,
            symbol=symbol,
            line_start=line_start,
            line_end=line_end,
            source_hash=source_hash,
            file_source_hash=str(item.get("file_source_hash") or ""),
        )
        refs[(file_path, symbol, line_start, line_end, source_hash)] = ref
    return tuple(refs[key] for key in sorted(refs))


def _applicable_prohibition_ids(atlas_intelligence: Mapping[str, Any]) -> tuple[str, ...]:
    values: set[str] = set()
    for assessment in atlas_intelligence.get("assessments", ()) or ():
        if not isinstance(assessment, Mapping):
            continue
        if assessment.get("wiring_disposition") != WiringDisposition.PROHIBITED.value:
            continue
        for ref in assessment.get("evidence_refs", ()) or ():
            text = str(ref)
            if text.startswith("prohib_"):
                values.add(text.split(":", 1)[0])
    return tuple(sorted(values))

def compile_coding_relationship_compass(
    objective: str,
    repo_root: str | Path = ".",
    *,
    target_files: Sequence[str] = (),
    target_symbols: Sequence[str] = (),
    target_tests: Sequence[str] = (),
    max_target_files: int = 16,
    max_target_symbols: int = 32,
    max_atomic_nodes: int = 36,
    max_atlas_participants: int = 32,
    max_atlas_assessments: int = 96,
    max_required_tests: int = 24,
    max_neighborhood_hops: int = 2,
    max_neighborhood_nodes: int = 64,
    max_neighborhood_edges: int = 256,
    max_neighborhood_candidate_pairs: int = 2016,
    max_neighborhood_output_bytes: int = 1_000_000,
    max_neighborhood_elapsed_ms: int = 30_000,
    atlas_profile: str = "OBJECTIVE_STANDARD",
    include_source: bool = False,
    relational_index_data: Mapping[str, Any] | None = None,
    atlas_snapshot: AtlasSnapshot | None = None,
    evidence_packet: Mapping[str, Any] | None = None,
    rollout_mode: CompassRolloutMode | str = CompassRolloutMode.SHADOW,
    rollout_provider: str = "",
    rollout_budget: Mapping[str, Any] | None = None,
    rollout_nonce: str = "",
    rollout_verifier_ref: str = "",
    max_emergent_candidates: int = 12,
    bilateral_contract: BilateralPlanningContract | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile a bounded coding relationship packet for Architect/Surgeon review.

    The default path loads a validated current Relational Index when available,
    extracts a bounded neighborhood, and compiles an objective-scoped Atlas in
    memory, so a query does not write generated architecture artifacts.
    Optional precomputed inputs support deterministic callers and focused tests.
    """
    normalized_objective = " ".join(str(objective or "").split())
    if not normalized_objective:
        raise ValueError("objective is required")
    root = Path(repo_root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"repository root is missing: {root}")
    rollout = validate_compass_rollout(
        rollout_mode,
        provider=rollout_provider,
        budget=rollout_budget,
        nonce=rollout_nonce,
        verifier_ref=rollout_verifier_ref,
    )
    if rollout["mode"] == CompassRolloutMode.PAIRED_LIVE.value and not rollout["admitted"]:
        raise ValueError(
            "PAIRED_LIVE Compass rollout requires provider, budget, nonce, and verifier_ref"
        )

    graph = enrich_connectome(build_capability_connectome(root))
    capability_path = enrich_path(find_capability_path(normalized_objective, root), graph)
    explicit_source_files, explicit_test_targets = _partition_explicit_test_targets(
        root, target_files, target_tests
    )
    matched_components, component_files, component_symbols = _component_targets(
        normalized_objective,
        root,
        explicit_files=explicit_source_files,
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
        evidence = _validate_injected_evidence_packet(root, evidence_packet)
    if not evidence.get("ok") or not evidence.get("grounding_ok"):
        raise ValueError("Emergent Evidence Spine did not produce an exact grounded packet")
    bilateral = (
        bilateral_contract
        if isinstance(bilateral_contract, BilateralPlanningContract)
        else (
            BilateralPlanningContract.from_dict(bilateral_contract)
            if bilateral_contract is not None
            else None
        )
    )
    if bilateral is not None:
        from aura_arena_gate_dialogue import _repository_identity

        current_identity = _repository_identity(root)
        if (
            bilateral.repository_head != str(evidence.get("repo_head") or "")
            or bilateral.repository_head != current_identity["repository_head"]
            or bilateral.source_tree_digest
            != current_identity["source_tree_digest"]
            or not bilateral.is_current(
                repository_head=current_identity["repository_head"],
                source_tree_digest=current_identity["source_tree_digest"],
                observed_at=time.time(),
            )
        ):
            raise ValueError(
                "bilateral confirmation does not match Compass repository/source identity"
            )
        outside_scope = sorted(set(selected_files) - set(bilateral.allowed_paths))
        if outside_scope:
            raise ValueError(
                f"Compass targets exceed the confirmed allowed paths: {outside_scope}"
            )

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
    capability_selections = capability_selections_from_path(capability_path)
    objective_contract = CompassObjectiveContract.create(
        objective=normalized_objective,
        intent_packet=intent_packet.canonical_dict(),
        intent_packet_digest=intent_packet.digest(),
        repository_head=str(evidence.get("repo_head") or ""),
        target_files=selected_files,
        target_symbols=selected_symbols,
        capabilities=capability_selections,
        route_reasons=(
            "explicit_relationship_compass_admission",
            *[f"matched_component:{item}" for item in matched_components],
            f"connectome_path:{capability_path.get('path_digest') or 'unresolved'}",
        ),
        bilateral_contract=bilateral,
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
    index_source = "in_memory_rebuild"
    cache_key = (
        str(root),
        str(evidence.get("repo_head") or ""),
        str(inventory.get("inventory_digest") or ""),
        str(graph.get("graph_digest") or ""),
    )
    relational_index: dict[str, Any] = {}
    if relational_index_data is None and cache_key in _RELATIONAL_PLANE_CACHE:
        cached_index = dict(_RELATIONAL_PLANE_CACHE[cache_key])
        if _relational_cache_entry_is_current(
            root,
            cached_index,
            repo_head=str(evidence.get("repo_head") or ""),
            connectome_graph_digest=str(graph.get("graph_digest") or ""),
            connectome_version=str(graph.get("version") or ""),
            atomic_inventory_digest=str(inventory.get("inventory_digest") or ""),
        ):
            relational_index = cached_index
            cache_hit = True
            index_source = "process_cache"
        else:
            _RELATIONAL_PLANE_CACHE.pop(cache_key, None)
    if relational_index_data is not None:
        try:
            relational_index = RelationalIndex.from_dict(relational_index_data).to_dict()
            index_source = "caller_supplied_validated"
        except ValueError:
            if atlas_snapshot is None or relational_index_data.get("schema_version"):
                raise
            _validated_relational_index_digest(relational_index_data)
            relational_index = dict(relational_index_data)
            index_source = "caller_supplied_legacy_digest_validated"
    elif not relational_index:
        store = RelationalIndexStore(root)
        if store.index_path.exists() and store.receipt_path.exists():
            try:
                status = store.validate_current()
                if status.get("ok") is True:
                    relational_index = store.load().to_dict()
                    index_source = "persisted_current_index"
            except (OSError, ValueError, json.JSONDecodeError):
                relational_index = {}
        if not relational_index:
            index_result = build_relational_index(
                root,
                profile="MINIMAL",
                persist=False,
                include_index=True,
            )
            relational_index = dict(index_result["index"])
            index_source = "in_memory_rebuild"
        if len(_RELATIONAL_PLANE_CACHE) >= _RELATIONAL_PLANE_CACHE_LIMIT:
            _RELATIONAL_PLANE_CACHE.pop(next(iter(_RELATIONAL_PLANE_CACHE)))
        _RELATIONAL_PLANE_CACHE[cache_key] = dict(relational_index)

    capability_ids = [str(item) for item in capability_path.get("required_capability_ids", []) or []]
    focal_ids = _select_focal_participants(
        relational_index,
        evidence,
        selected_files,
        selected_symbols,
        capability_ids,
        limit=max(1, max_atlas_participants),
    )
    source_refs = _source_references_from_evidence(evidence)
    neighborhood_request = RelationalNeighborhoodRequest(
        objective_digest=objective_contract.objective_digest,
        seed_participant_ids=tuple(focal_ids),
        seed_source_refs=source_refs,
        max_hops=max_neighborhood_hops,
        max_nodes=max_neighborhood_nodes,
        max_edges=max_neighborhood_edges,
        max_candidate_pairs=max_neighborhood_candidate_pairs,
        max_output_bytes=max_neighborhood_output_bytes,
        max_elapsed_ms=max_neighborhood_elapsed_ms,
        include_tests=True,
        include_docs=False,
        include_auxiliary=True,
        stop_on_prohibition=True,
    )
    try:
        neighborhood = extract_relational_neighborhood(
            neighborhood_request,
            relational_index,
        )
    except ValueError:
        if atlas_snapshot is None or relational_index.get("schema_version"):
            raise
        neighborhood = _compatibility_neighborhood_from_raw_index(
            neighborhood_request,
            relational_index,
        )
    neighborhood_focal_ids = [
        str(item["participant_id"])
        for item in neighborhood.get("participants", ())
        if isinstance(item, Mapping)
    ][: max(1, max_atlas_participants)]

    if atlas_snapshot is None:
        atlas = build_objective_relationship_atlas(
            repo_root=root,
            relational_index=relational_index,
            neighborhood=neighborhood,
            profile=atlas_profile,
        )
    else:
        atlas = _validate_supplied_atlas_snapshot(
            atlas_snapshot,
            evidence=evidence,
            relational_index=relational_index,
            connectome=graph,
        )
    atlas_intelligence = _bounded_atlas_intelligence(
        atlas,
        neighborhood_focal_ids,
        max_assessments=max(1, max_atlas_assessments),
    )
    if bilateral is not None:
        assessments = list(atlas_intelligence.get("assessments") or ())
        annotated_assessments: list[dict[str, Any]] = []
        projected: dict[str, set[str]] = {
            "positive_requirements": set(),
            "negative_requirements_at_risk": set(),
            "guardrail_ids": set(),
            "required_verifiers": set(),
        }
        for assessment in assessments:
            annotated = dict(assessment)
            obligation = _semantic_obligations(annotated, bilateral)
            if obligation:
                annotated["bilateral_obligation"] = obligation
                for key in projected:
                    projected[key].update(obligation[key])
            annotated_assessments.append(annotated)
        atlas_intelligence["assessments"] = annotated_assessments
        atlas_intelligence["unprojected_bilateral_obligations"] = {
            "positive_requirements": sorted(
                set(bilateral.positive_requirements)
                - projected["positive_requirements"]
            ),
            "negative_requirements": sorted(
                set(bilateral.negative_requirements)
                - projected["negative_requirements_at_risk"]
            ),
            "guardrail_ids": sorted(
                set(
                    (
                        *bilateral.hard_guardrail_ids,
                        *bilateral.human_guardrail_ids,
                        *bilateral.editable_guardrail_ids,
                    )
                )
                - projected["guardrail_ids"]
            ),
            "required_verifiers": sorted(
                set(bilateral.required_verifiers)
                - projected["required_verifiers"]
            ),
        }
        has_unprojected_bilateral_obligation = any(
            atlas_intelligence["unprojected_bilateral_obligations"].values()
        )
    else:
        has_unprojected_bilateral_obligation = False

    targets = _recommended_targets(evidence, selected_files, selected_symbols)
    if not targets:
        raise ValueError("exact evidence packet contained no source target")
    primary = targets[0]

    index_identity = relational_index.get("repository_identity") or {}
    repository_identity = RepositoryIdentity(
        repo_head=str(index_identity.get("repo_head") or evidence.get("repo_head") or ""),
        working_tree_digest=str(index_identity.get("working_tree_digest") or ""),
        relational_index_digest=str(relational_index.get("index_digest") or ""),
        atlas_digest=atlas.snapshot_digest,
    )
    budget = ResourceBudget(
        max_hops=max_neighborhood_hops,
        max_nodes=max_neighborhood_nodes,
        max_edges=max_neighborhood_edges,
        max_candidate_pairs=max_neighborhood_candidate_pairs,
        max_output_bytes=max_neighborhood_output_bytes,
        max_elapsed_ms=max_neighborhood_elapsed_ms,
    )
    policy_scope = tuple(capability_ids or matched_components or ("coding_arena",))
    prohibition_ids = _applicable_prohibition_ids(atlas_intelligence)
    producer_contract = project_relationship_contract(
        objective_digest=content_digest({"objective": normalized_objective, "role": "producer"}),
        intent_packet=intent_packet.canonical_dict(),
        source_repository=repository_identity,
        source_refs=source_refs,
        policy_scope=policy_scope,
        resource_budget=budget,
        domain=RelationshipDomain.CODE,
        truth_class=ContractTruthClass.EXACT_SOURCE,
        authority_posture=AuthorityPosture.PROPOSAL_ONLY,
        proof_status=ContractProofStatus.GROUNDED,
        prohibition_ids=prohibition_ids,
    )
    consumer_contract = project_relationship_contract(
        objective_digest=content_digest({"objective": normalized_objective, "role": "consumer"}),
        intent_packet=intent_packet.canonical_dict(),
        source_repository=repository_identity,
        source_refs=source_refs,
        policy_scope=policy_scope,
        resource_budget=budget,
        domain=RelationshipDomain.CODE,
        truth_class=ContractTruthClass.EXACT_SOURCE,
        authority_posture=AuthorityPosture.PROPOSAL_ONLY,
        proof_status=ContractProofStatus.GROUNDED,
        prohibition_ids=prohibition_ids,
    )
    producer_interface = RelationshipInterfaceSpec.create(
        port_name="grounded_relationship_packet",
        direction=InterfacePortDirection.OUTPUT,
        cardinality=InterfacePortCardinality.ONE,
        lifecycle=InterfaceLifecycle.SESSION,
        actor=InterfaceActor.SYSTEM,
        boundary=InterfaceBoundary.SAME_ARENA,
        resource_class=InterfaceResourceClass.CODE,
        data_class=InterfaceDataClass.CONTRACT,
        operation=InterfaceOperation.VALIDATE,
    )
    consumer_interface = RelationshipInterfaceSpec.create(
        port_name="grounded_relationship_packet",
        direction=InterfacePortDirection.INPUT,
        cardinality=InterfacePortCardinality.ONE,
        lifecycle=InterfaceLifecycle.SESSION,
        actor=InterfaceActor.SYSTEM,
        boundary=InterfaceBoundary.SAME_ARENA,
        resource_class=InterfaceResourceClass.CODE,
        data_class=InterfaceDataClass.CONTRACT,
        operation=InterfaceOperation.PLAN,
    )
    compatibility = evaluate_typed_relationship_compatibility(
        producer_contract,
        consumer_contract,
        left_interface=producer_interface,
        right_interface=consumer_interface,
    )
    relationship_breadboard = compile_relationship_breadboard(
        objective=normalized_objective,
        left_contract=producer_contract,
        right_contract=consumer_contract,
        left_interface=producer_interface,
        right_interface=consumer_interface,
        assessment=compatibility,
    )

    required_tests = _ordered_unique(
        [
            *explicit_test_targets,
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
            **(
                {
                    "intent_digest": bilateral.intent_digest,
                    "semantic_ledger_digest": bilateral.semantic_ledger_digest,
                    "confirmation_digest": bilateral.confirmation_digest,
                    **(
                        {
                            "bilateral_obligation": obligation,
                        }
                        if (
                            obligation := _semantic_obligations(item, bilateral)
                        )
                        else {}
                    ),
                }
                if bilateral is not None
                else {}
            ),
        }
        for index, item in enumerate(targets[:8], start=1)
    ]

    packet: dict[str, Any] = {
        "version": COMPASS_VERSION,
        "objective": normalized_objective,
        "matched_components": matched_components,
        "objective_contract": objective_contract.to_dict(),
        "capability_classes": capability_class_index(capability_selections),
        "target_file": primary["file_path"],
        "target_symbol": primary["symbol"],
        "recommended_targets": targets[:16],
        "explicit_test_targets": explicit_test_targets,
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
        "relational_neighborhood": {**neighborhood, "index_source": index_source},
        "atlas": {**atlas_intelligence, "cache_hit": cache_hit},
        "typed_compatibility": compatibility.to_dict(),
        "coding_breadboard": relationship_breadboard,
        "relationships_to_preserve": atlas_intelligence.get("relationships_to_preserve", []),
        "prohibitions": atlas_intelligence.get("prohibitions", []),
        "missing_roles": atlas_intelligence.get("missing_roles", []),
        "required_adapters": _ordered_unique([
            *atlas_intelligence.get("required_adapters", []),
            *compatibility.required_adapters,
        ]),
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
    if bilateral is not None:
        packet["bilateral_contract"] = bilateral.to_dict()
        packet["bilateral_scope"] = {
            "repository_head": bilateral.repository_head,
            "source_tree_digest": bilateral.source_tree_digest,
            "allowed_path_set_digest": bilateral.allowed_path_set_digest,
            "allowed_paths": list(bilateral.allowed_paths),
            "prohibition_ids": list(bilateral.hard_guardrail_ids),
            "human_guardrail_ids": list(bilateral.human_guardrail_ids),
        }
    packet["rollout"] = rollout
    packet["grounding_digest"] = _stable_digest(_compass_digest_payload(packet))
    grounding_receipt = _build_compass_grounding_receipt(
        packet=packet,
        evidence=evidence,
        targets=targets[:16],
        required_tests=required_tests,
    )
    packet["grounding_receipt"] = grounding_receipt
    packet["grounding_receipt_digest"] = stable_digest(grounding_receipt)

    # Bilateral intent fidelity is a deterministic admission gate, not a score.
    # Once Atlas projection proves any confirmed obligation is unprojected (or
    # there is no assessment at all), stop before emergent discovery/scoring so
    # secondary resource limits can never mask the human-reconfirmation route.
    intent_fidelity_denied = bool(
        bilateral is not None
        and (
            not atlas_intelligence.get("assessments")
            or has_unprojected_bilateral_obligation
        )
    )
    if intent_fidelity_denied:
        preflight_failure_classes: list[str] = []
        if packet["typed_compatibility"].get("outcome") in {"PROHIBITED", "INCOMPATIBLE", "BLOCKED"}:
            preflight_failure_classes.append("INTERFACE")
        if packet.get("prohibitions"):
            preflight_failure_classes.append("PROHIBITION")
        preflight_failure_classes.append("INTENT_FIDELITY")

        packet["bounded_emergent_discovery"] = {
            "skipped": True,
            "reason": "INTENT_FIDELITY",
            "candidates": [],
            "proposal_only": True,
            "safe_to_patch": False,
        }
        packet["bounded_emergent_verification"] = {
            "skipped": True,
            "reason": "INTENT_FIDELITY",
            "accepted_candidates": [],
            "rejected_candidates": [],
            "proposal_only": True,
        }
        packet["change_graph"] = {
            "ok": False,
            "reason": "INTENT_FIDELITY",
            "phase_capsules": [],
            "proposal_only": True,
            "safe_to_patch": False,
        }
        packet["phase_capsules"] = []
        packet["act_capsules"] = {
            "ok": False,
            "reason": "INTENT_FIDELITY",
            "act_capsules": [],
            "proposal_only": True,
            "safe_to_patch": False,
        }
        packet["agent_ir"] = {
            "ok": False,
            "reason": "INTENT_FIDELITY",
            "nodes": [],
            "proposal_only": True,
            "safe_to_patch": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
        }
        packet["council_route"] = route_compass_failure_classes(preflight_failure_classes)
        packet["experience_projection_template"] = {
            "relationship_ids": [],
            "required_outcomes": ["DENIAL"],
            "valid_time_bound_to_repository_head": True,
            "transaction_time_bound_to_receipt_creation": True,
            "eligibility_gate_closed_by_default": True,
            "proposal_only": True,
        }
        packet["compass_digest"] = _stable_digest(_compass_digest_payload(packet))
        return packet

    # Emergent discovery has its own hard input budget.  Feed it only the
    # source-bearing fields it actually consumes instead of the full Compass/Atlas
    # diagnostic packet.  This preserves the safety ceiling rather than raising it.
    bounded_neighborhood = {
        "neighborhood_digest": neighborhood.get("neighborhood_digest"),
        "participants": [
            {
                key: value
                for key, value in participant.items()
                if key in {
                    "participant_id",
                    "role",
                    "participant_type",
                    "kind",
                    "qualified_symbol",
                    "symbol",
                    "canonical_ref",
                    "source_hash",
                    "tests",
                    "metadata",
                }
            }
            for participant in (neighborhood.get("participants", ()) or ())
            if isinstance(participant, Mapping)
        ],
        "relations": [
            {
                key: value
                for key, value in relation.items()
                if key in {
                    "source_participant_id",
                    "target_participant_id",
                    "truth_class",
                }
            }
            for relation in (neighborhood.get("relations", ()) or ())
            if isinstance(relation, Mapping)
        ],
    }
    # Participant metadata can contain large Compass-side diagnostics.  Retain only
    # evidence fields consumed by bounded discovery.
    for participant in bounded_neighborhood["participants"]:
        metadata = participant.get("metadata")
        if isinstance(metadata, Mapping):
            participant["metadata"] = {
                key: value
                for key, value in metadata.items()
                if key in {
                    "canonical_ref",
                    "source_ref",
                    "source_hash",
                    "file_source_hash",
                    "file_path",
                    "tests",
                }
            }

    bounded_compatibility = {
        key: packet["typed_compatibility"].get(key)
        for key in ("outcome", "assessment_digest", "compatibility_digest")
        if key in packet["typed_compatibility"]
    }
    bounded_atlas = {
        "assessments": [
            {
                key: value
                for key, value in assessment.items()
                if key in {
                    "source_participant_id",
                    "target_participant_id",
                    "participant_a_id",
                    "participant_b_id",
                    "left_participant_id",
                    "right_participant_id",
                    "participant_ids",
                    "wiring_disposition",
                }
            }
            for assessment in (packet["atlas"].get("assessments", ()) or ())
            if isinstance(assessment, Mapping)
        ]
    }

    discovery = discover_bounded_emergent_candidates(
        objective=normalized_objective,
        neighborhood=bounded_neighborhood,
        compatibility=bounded_compatibility,
        atlas=bounded_atlas,
        required_tests=required_tests,
        max_candidates=max_emergent_candidates,
        max_pairs_considered=max_neighborhood_candidate_pairs,
    )
    bounded_verification = verify_bounded_emergent_discovery(
        discovery,
        neighborhood=neighborhood,
        relational_index=relational_index,
        max_clusters=max(1, min(max_emergent_candidates, 16)),
    )
    packet["bounded_emergent_discovery"] = discovery.to_dict()
    packet["bounded_emergent_verification"] = bounded_verification

    change_graph = build_compass_change_graph(packet, repo_root=root)
    capsule_packet = compile_compass_act_capsules(change_graph, repo_root=root)
    agent_ir = (
        AgentIRCompiler.compile_compass_act_capsules(capsule_packet)
        if capsule_packet.get("ok")
        else {
            "ok": False,
            "reason": capsule_packet.get("reason"),
            "nodes": [],
            "proposal_only": True,
            "safe_to_patch": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
        }
    )
    failure_classes: list[str] = []
    if not capsule_packet.get("ok"):
        failure_classes.append("INVARIANT")
    if packet["typed_compatibility"].get("outcome") in {"PROHIBITED", "INCOMPATIBLE", "BLOCKED"}:
        failure_classes.append("INTERFACE")
    if packet.get("prohibitions"):
        failure_classes.append("PROHIBITION")
    if bilateral is not None and not atlas_intelligence.get("assessments"):
        failure_classes.append("INTENT_FIDELITY")
    if has_unprojected_bilateral_obligation:
        failure_classes.append("INTENT_FIDELITY")
    packet["change_graph"] = change_graph
    packet["phase_capsules"] = list(change_graph.get("phase_capsules", []) or [])
    packet["act_capsules"] = capsule_packet
    packet["agent_ir"] = agent_ir
    packet["council_route"] = route_compass_failure_classes(failure_classes)
    packet["experience_projection_template"] = {
        "relationship_ids": [
            str(item.get("candidate_id") or "")
            for item in bounded_verification.get("accepted_candidates", [])
            if item.get("candidate_id")
        ],
        "required_outcomes": ["SUCCESS", "FAILURE", "DENIAL", "ABANDONMENT", "ROLLBACK"],
        "valid_time_bound_to_repository_head": True,
        "transaction_time_bound_to_receipt_creation": True,
        "eligibility_gate_closed_by_default": True,
        "proposal_only": True,
    }

    packet["compass_digest"] = _stable_digest(_compass_digest_payload(packet))
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
        "objective_contract": dict(packet.get("objective_contract") or {}),
        "capability_classes": dict(packet.get("capability_classes") or {}),
        "relationship_atlas_digest": atlas.get("snapshot_digest"),
        "relational_neighborhood_digest": (packet.get("relational_neighborhood") or {}).get("neighborhood_digest"),
        "typed_compatibility": dict(packet.get("typed_compatibility") or {}),
        "coding_breadboard": dict(packet.get("coding_breadboard") or {}),
        "relationships_to_preserve": list(packet.get("relationships_to_preserve", []) or [])[:32],
        "prohibitions": list(packet.get("prohibitions", []) or []),
        "missing_roles": list(packet.get("missing_roles", []) or []),
        "required_adapters": list(packet.get("required_adapters", []) or []),
        "action_capsule_hints": list(packet.get("action_capsule_hints", []) or []),
        "bounded_emergent_verification": dict(packet.get("bounded_emergent_verification") or {}),
        "change_graph": dict(packet.get("change_graph") or {}),
        "phase_capsules": list(packet.get("phase_capsules", []) or []),
        "act_capsules": dict(packet.get("act_capsules") or {}),
        "agent_ir": dict(packet.get("agent_ir") or {}),
        "council_route": dict(packet.get("council_route") or {}),
        "rollout": dict(packet.get("rollout") or {}),
        "bilateral_contract": dict(packet.get("bilateral_contract") or {}),
        "grounding_ok": bool(packet.get("grounding_ok")),
        "safe_to_patch": False,
        "human_review_required": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


__all__ = [
    "COMPASS_VERSION",
    "ArchitectureComponent",
    "CompassRolloutMode",
    "validate_compass_rollout",
    "compile_coding_relationship_compass",
    "is_coding_relationship_compass_intent",
    "relationship_compass_grounding",
]
