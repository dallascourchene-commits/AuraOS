"""Deterministic P8 inventory of the live Civic Commons ownership surface."""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from typing import Final

from aura_civic_planning_types import CIVIC_INVENTORY_VERSION, CivicSurfaceEntry, CivicSurfaceInventory

_SURFACE_SPECS: Final[tuple[tuple[str, str, tuple[str, ...]], ...]] = (
    ("aura_agent_arena_cli.py", "PUBLIC_CLI_CALLER", ()),
    ("aura_civic_authority.py", "AUTHORITY_CONSTANT_OWNER", ("PATCH_AUTHORITY", "VSA_PATCH_AUTHORITY")),
    ("aura_civic_context.py", "EXPLICIT_CONTEXT_ACTIVATION_OWNER", ("check_activation",)),
    ("aura_civic_contributions.py", "CONTRIBUTION_RECORD_OWNER", ("create_contribution", "withdraw_contribution", "check_consent_to_match")),
    ("aura_civic_deliberation.py", "PARTICIPATION_RECORD_SCHEMA_OWNER", ("ParticipantResponse", "ConsentArc", "assess_convergence")),
    ("aura_civic_ephemeral_integration.py", "EPHEMERAL_ORGAN_EXECUTION_OWNER", ("execute_civic_organ_through_runtime",)),
    ("aura_civic_evidence.py", "LEGAL_EVIDENCE_OWNER", ("assess_legal_applicability",)),
    ("aura_civic_guided_project.py", "GUIDED_SESSION_OWNER", ("start_project", "advance_project", "record_response")),
    ("aura_civic_map.py", "CIVIC_MAP_OWNER", ("build_map_manifest", "project_map_manifest")),
    ("aura_civic_organs.py", "CIVIC_ORGAN_RESULT_OWNER", ("consent_arc_organ", "pilot_tunnel_organ", "decision_packet_organ")),
    ("aura_civic_project_runtime.py", "DECLARATIVE_PROJECT_RUNTIME_OWNER", ("project_for_session", "run_project_organ")),
    ("aura_civic_projects.py", "PROJECT_SCHEMA_OWNER", ("CivicProjectDefinition", "get_project", "require_project")),
    ("aura_civic_profiles.py", "PROFILE_OWNER", ("CivicProfileSet", "create_winnipeg_demo_profile_set")),
    ("aura_civic_reasoning.py", "WORKSTREAM_REASONING_OWNER", ("Workstream", "civic_mitosis", "civic_music")),
    ("aura_civic_resources.py", "RESOURCE_MATCHING_OWNER", ("match_resources",)),
    ("aura_civic_result_projector.py", "RESULT_PROJECTION_OWNER", ("project_civic_organ_result",)),
    ("aura_civic_runtime.py", "LIVE_SESSION_AND_PIPELINE_OWNER", ("create_civic_session", "get_session", "run_civic_organ")),
    ("aura_civic_scenarios.py", "PILOT_SCHEMA_OWNER", ("PilotPacket", "create_pilot")),
    ("aura_civic_session_store.py", "PERSISTENT_SESSION_STORE_OWNER", ("CivicSessionStore",)),
    ("aura_civic_truth.py", "CIVIC_TRUTH_CLASS_OWNER", ("TRUTH_CLASSES", "validate_truth_class")),
    ("aura_civic_winnipeg_fixture.py", "WINNIPEG_FIXTURE_OWNER", ("winnipeg_pathways_fixtures",)),
    ("aura_civic_world_model.py", "DECISION_PACKET_SCHEMA_OWNER", ("DecisionPacket",)),
    ("aura_ephemeral_registry_store.py", "EPHEMERAL_REGISTRY_STORE_OWNER", ("EphemeralRegistryStore",)),
    ("aura_human_agent_arena_server.py", "HUMAN_AGENT_SERVER_CALLER", ()),
    ("aura_showcase_server.py", "SHOWCASE_SERVER_CALLER", ()),
)


class CivicInventoryError(ValueError):
    pass


def _top_level_symbols(source: str, path: str) -> set[str]:
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as exc:
        raise CivicInventoryError(f"invalid Python syntax in {path}: {exc}") from exc
    symbols: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    symbols.add(target.id)
    return symbols


def _safe_file(root: Path, relative: str) -> Path:
    if not relative or "\\" in relative:
        raise CivicInventoryError(f"non-canonical inventory path: {relative!r}")
    try:
        resolved = (root / relative).resolve(strict=True)
        resolved.relative_to(root)
    except OSError as exc:
        raise CivicInventoryError(f"missing inventory surface: {relative}") from exc
    except ValueError as exc:
        raise CivicInventoryError(f"inventory path escapes repository root: {relative}") from exc
    if not resolved.is_file():
        raise CivicInventoryError(f"inventory surface is not a file: {relative}")
    return resolved


def build_civic_surface_inventory(repo_root: str | Path | None = None) -> CivicSurfaceInventory:
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parent
    try:
        root = root.resolve(strict=True)
    except OSError as exc:
        raise CivicInventoryError("repository root is unavailable") from exc
    if not root.is_dir():
        raise CivicInventoryError("repository root must be a directory")
    entries: list[CivicSurfaceEntry] = []
    for relative, role, required_symbols in sorted(_SURFACE_SPECS, key=lambda item: item[0]):
        raw = _safe_file(root, relative).read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CivicInventoryError(f"inventory surface is not UTF-8: {relative}") from exc
        symbols = _top_level_symbols(text, relative)
        missing = tuple(symbol for symbol in required_symbols if symbol not in symbols)
        if missing:
            raise CivicInventoryError(f"inventory surface {relative} is missing declared symbols: {list(missing)}")
        entries.append(CivicSurfaceEntry(path=relative, role=role, symbols=tuple(required_symbols), sha256=hashlib.sha256(raw).hexdigest()))
    return CivicSurfaceInventory(version=CIVIC_INVENTORY_VERSION, entries=tuple(entries))


__all__ = ["CivicInventoryError", "build_civic_surface_inventory"]
