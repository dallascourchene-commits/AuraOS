"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9f4-[Q-SYS:HUMAN_AGENT_CONCEPTS]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Concept Workspace Engine)
DEPENDENCIES: __future__, hashlib, json, pathlib, re, time, typing
FUNCTIONS: ConceptProfile, ConceptWorkspace, build_concept_workspace, resolve_node_ref,
           CONCEPT_PROFILES
SYNOPSIS: Concept Workspace Engine for the Human Agent Arena. Searches the full
CODEMAP index (files, symbol_index, command_index, topology neighbors) rather than
only the already-projected visual graph. Creates ArenaNode-compatible dicts for
CODEMAP matches not present in the current projected topology. These are
CODEMAP-projected nodes — real CODEMAP-grounded entities projected into the visual
workspace (visual_projection_only: true, entity_exists: true, patch_authority: false).
Exact source facts (file path, line range, hash) are authoritative in the truth_packet.
No production code is mutated. No network calls are made.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any

CONCEPT_ENGINE_VERSION = "AURA_HUMAN_AGENT_CONCEPTS_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

# ---------------------------------------------------------------------------
# Concept profiles
# ---------------------------------------------------------------------------

@dataclass
class ConceptProfile:
    key: str
    display_name: str
    aliases: list[str] = field(default_factory=list)
    # Known files for this concept (checked even if not in projected topology)
    seed_files: list[str] = field(default_factory=list)
    # Known symbols
    seed_symbols: list[str] = field(default_factory=list)
    # Known docs
    seed_docs: list[str] = field(default_factory=list)
    # Related concept keys
    related_concepts: list[str] = field(default_factory=list)


CONCEPT_PROFILES: dict[str, ConceptProfile] = {
    "coding_arena": ConceptProfile(
        key="coding_arena",
        display_name="Coding Arena",
        aliases=[
            "coding arena", "aura_coding_arena", "coding_arena_3d",
            "compile_action_capsule", "select_micro_arena", "detect_wiring_faults",
            "simulate_model_route", "apply_marked_edge", "load_arena_topology",
        ],
        seed_files=[
            "aura_coding_arena_3d.py",
            "aura_coding_arena_server.py",
            "aura_coding_arena_grounding.py",
            "aura_coding_arena_workflow.py",
            "aura_coding_arena/main.js",
            "aura_coding_arena/index.html",
            "aura_coding_arena/arena.css",
            "AURA_CODING_ARENA_README.md",
            "tests/test_aura_coding_arena_3d.py",
            "tests/test_aura_coding_arena_grounding.py",
            "test_aura_coding_arena_workflow.py",
        ],
        seed_symbols=[
            "load_arena_topology", "select_micro_arena", "compile_action_capsule",
            "detect_wiring_faults", "simulate_model_route", "apply_marked_edge",
            "ArenaNode", "ArenaLink", "WiringFault",
        ],
        seed_docs=["AURA_CODING_ARENA_README.md", "docs/AURA_AGENT_ARENA_BRIDGE.md"],
        related_concepts=["agent_arena_bridge", "human_agent_arena", "st3gg"],
    ),
    "agent_arena_bridge": ConceptProfile(
        key="agent_arena_bridge",
        display_name="Agent Arena Bridge",
        aliases=[
            "agent arena", "agent bridge", "aura_agent_arena",
            "agent arena bridge", "agent_arena_bridge",
            "aura_repo_digest", "aura_prepare_arena", "aura_get_micro_context",
            "aura_stage_patch", "aura_verify_arena", "aura_repair_packet",
            "aura_hotswap_status", "aura_export_icm",
        ],
        seed_files=[
            "aura_agent_arena_bridge.py",
            "aura_agent_arena_cli.py",
            "aura_agent_arena_mcp.py",
            "aura_agent_arena_fireworks.py",
            "aura_agent_arena_errors.py",
            "scripts/aura-agent-arena",
            "tests/test_aura_agent_arena_bridge.py",
            "tests/test_aura_agent_arena_cli.py",
            "tests/test_aura_agent_arena_mcp.py",
            "docs/AURA_AGENT_ARENA_BRIDGE.md",
            "docs/AURA_AGENT_PROMPT_STATIC.md",
        ],
        seed_symbols=[
            "AuraAgentArenaBridge", "aura_prepare_arena", "aura_get_micro_context",
            "aura_stage_patch", "aura_verify_arena", "aura_repair_packet",
            "aura_hotswap_status", "aura_export_icm", "aura_repo_digest",
        ],
        seed_docs=["docs/AURA_AGENT_ARENA_BRIDGE.md", "docs/AURA_AGENT_PROMPT_STATIC.md"],
        related_concepts=["coding_arena", "human_agent_arena"],
    ),
    "human_agent_arena": ConceptProfile(
        key="human_agent_arena",
        display_name="Human Agent Arena",
        aliases=[
            "human agent arena", "human_agent_arena",
            "aura_human_agent_arena", "route_command", "ghost_edge",
            "concept workspace", "jarvis",
        ],
        seed_files=[
            "aura_human_agent_arena.py",
            "aura_human_agent_arena_server.py",
            "aura_human_agent_concepts.py",
            "aura_human_agent_arena/main.js",
            "aura_human_agent_arena/index.html",
            "aura_human_agent_arena/arena.css",
            "tests/test_aura_human_agent_arena.py",
            "docs/AURA_HUMAN_AGENT_ARENA.md",
        ],
        seed_symbols=[
            "HumanAgentArena", "HumanAgentArenaState", "GhostEdge",
            "route_command", "build_concept_workspace", "resolve_node_ref",
        ],
        seed_docs=["docs/AURA_HUMAN_AGENT_ARENA.md"],
        related_concepts=["coding_arena", "agent_arena_bridge"],
    ),
    "st3gg": ConceptProfile(
        key="st3gg",
        display_name="ST3GG",
        aliases=[
            "st3gg", "ST3GG", "aura_arena_st3gg", "aura_st3gg",
            "encode_arena_capsule_for_egress", "st3gg_egress", "visible ascii",
            "recall sidecar", "aura_arena_st3gg_codec", "aura_st3gg_codec",
            "arena_st3gg",
        ],
        seed_files=[
            "aura_arena_st3gg_codec.py",
            "aura_arena_st3gg_egress.py",
            "aura_st3gg_codec.py",
            "aura_st3gg_recall.py",
            "aura_st3gg_compact.rs",
            "tests/test_aura_st3gg_codec.py",
            "test_aura_arena_st3gg_codec.py",
            "test_aura_st3gg_recall.py",
            "test_aura_st3gg_compact.py",
        ],
        seed_symbols=[
            "encode_arena_capsule_for_egress", "ST3GGEgressPayload",
            "AuraArenaCodec", "st3gg_egress",
        ],
        seed_docs=[],
        related_concepts=["jspace", "coding_arena", "emergent_potential"],
    ),
    "jspace": ConceptProfile(
        key="jspace",
        display_name="JSpace",
        aliases=[
            "jspace", "JSpace", "aura_jspace_codec", "jspace_packet",
            "jspace_state", "attach_jspace_to_capsule", "j_space",
        ],
        seed_files=[
            "aura_jspace_codec.py",
            "tests/test_aura_jspace_codec.py",
        ],
        seed_symbols=["attach_jspace_to_capsule", "JSpacePacket", "JSpaceState"],
        seed_docs=[],
        related_concepts=["st3gg", "coding_arena"],
    ),
    "architect": ConceptProfile(
        key="architect",
        display_name="Architect",
        aliases=[
            "architect", "aura_architect", "architect_loop", "live_architect",
            "ArchitectFusionCouncil", "ArchitectFusionLoop", "aura_live_architect",
            "aura_architect_loop",
        ],
        seed_files=[
            "aura_architect_loop.py",
            "aura_live_architect.py",
            "test_aura_architect_loop.py",
            "test_aura_live_architect.py",
        ],
        seed_symbols=["ArchitectFusionLoop", "ArchitectFusionCouncil", "ArchitectBuilderBridge"],
        seed_docs=[],
        related_concepts=["coding_arena", "agent_arena_bridge"],
    ),
    "dream": ConceptProfile(
        key="dream",
        display_name="DREAM",
        aliases=[
            "dream", "DREAM", "aura_dream", "dream_engine",
            "aura_dream_engine", "aura_dream_retrieval", "DreamCandidate",
            "rerank_for_arena",
        ],
        seed_files=[
            "aura_dream_engine.py",
            "aura_dream_retrieval.py",
            "test_aura_dream_retrieval.py",
        ],
        seed_symbols=["AuraDreamEngine", "DreamCandidate", "rerank_for_arena"],
        seed_docs=[],
        related_concepts=["qdkt", "architect"],
    ),
    "qdkt": ConceptProfile(
        key="qdkt",
        display_name="QDKT",
        aliases=["qdkt", "QDKT", "aura_qdkt", "get_qdkt", "observe"],
        seed_files=["aura_qdkt.py"],
        seed_symbols=["get_qdkt"],
        seed_docs=[],
        related_concepts=["dream"],
    ),
    "emergent_potential": ConceptProfile(
        key="emergent_potential",
        display_name="Emergent Potential",
        aliases=[
            "emergent potential", "emergent_potential", "aura_emergent",
            "aura_emergent_potential_repl", "audit_emergent_potential",
            "aura_emergent_result_verifier", "aura_emergent_capability_auditor",
            "EmergentCluster",
        ],
        seed_files=[
            "aura_emergent_potential_repl.py",
            "aura_emergent_result_verifier.py",
            "aura_emergent_capability_auditor.py",
            "tests/test_aura_emergent_potential_repl.py",
            "tests/test_aura_emergent_result_verifier.py",
            "tests/test_aura_emergent_capability_auditor.py",
        ],
        seed_symbols=["audit_emergent_potential", "EmergentCluster"],
        seed_docs=[],
        related_concepts=["st3gg", "coding_arena"],
    ),
    "context_crusher": ConceptProfile(
        key="context_crusher",
        display_name="Context Crusher",
        aliases=[
            "context crusher", "context_crusher", "aura_context_crusher",
            "apply_context_crush_to_prompt", "AuraContextCrusher",
        ],
        seed_files=[
            "aura_context_crusher.py",
            "test_aura_context_crusher.py",
        ],
        seed_symbols=["AuraContextCrusher", "apply_context_crush_to_prompt"],
        seed_docs=[],
        related_concepts=["st3gg", "jspace"],
    ),
    "llm_egress": ConceptProfile(
        key="llm_egress",
        display_name="LLM Egress",
        aliases=[
            "llm egress", "llm_egress", "aura_llm_egress",
            "pre_egress_interceptor", "aura_pre_egress_interceptor",
        ],
        seed_files=[
            "aura_llm_egress.py",
            "aura_pre_egress_interceptor.py",
        ],
        seed_symbols=["AuraLLMEgress"],
        seed_docs=[],
        related_concepts=["st3gg", "context_crusher"],
    ),
    "verifier": ConceptProfile(
        key="verifier",
        display_name="Verifier",
        aliases=[
            "verifier", "aura_validation", "aura_tokenizer_guard",
            "verify", "verifier_gate", "patch_quality_gate",
        ],
        seed_files=[
            "aura_validation.py",
            "aura_tokenizer_guard.py",
            "aura_patch_quality_gate.py",
            "test_aura_tokenizer_guard.py",
            "test_aura_patch_quality.py",
        ],
        seed_symbols=["sanitize_tokenizer_channels"],
        seed_docs=[],
        related_concepts=["coding_arena", "agent_arena_bridge"],
    ),
    "research_arxiv": ConceptProfile(
        key="research_arxiv",
        display_name="Research / ArXiv",
        aliases=[
            "research", "arxiv", "arxiv_forager", "aura_research",
            "aura_research_manifest", "aura_paper_memory",
            "aura_research_ingest_bridge", "ArXivForager",
        ],
        seed_files=[
            "arxiv_forager.py",
            "aura_research_manifest.py",
            "aura_paper_memory.py",
            "aura_research_ingest_bridge.py",
            "test_aura_research_manifest.py",
            "test_aura_paper_memory.py",
        ],
        seed_symbols=["ArXivForager"],
        seed_docs=[],
        related_concepts=["dream", "qdkt"],
    ),
}


# ---------------------------------------------------------------------------
# Concept workspace dataclass
# ---------------------------------------------------------------------------

@dataclass
class ConceptWorkspace:
    concept: str
    query: str
    profile_key: str
    workspace_id: str = ""
    seed_matches: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    docs: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    neighbors: list[str] = field(default_factory=list)
    # ArenaNode-compatible dicts (existing topology + CODEMAP-projected)
    nodes: list[dict[str, Any]] = field(default_factory=list)
    links: list[dict[str, Any]] = field(default_factory=list)
    token_estimates: dict[str, Any] = field(default_factory=dict)
    grounding: str = "NEEDS_GROUNDING"

    def to_truth_packet(self) -> dict[str, Any]:
        # Build origin breakdown for the grounded node ontology
        codemap_projected = [
            n for n in self.nodes
            if n.get("metadata", {}).get("node_origin") == "codemap_projected_node"
        ]
        exact_topology = [
            n for n in self.nodes
            if n.get("metadata", {}).get("node_origin") == "exact_topology_node"
            or (
                n.get("metadata", {}).get("projected_from_codemap") is not True
                and not n.get("metadata", {}).get("node_origin")
            )
        ]
        node_origins = {
            n["id"]: n.get("metadata", {}).get("node_origin", "exact_topology_node")
            for n in self.nodes
            if n.get("id")
        }
        edge_origins = {}
        for link in self.links:
            meta = link.get("metadata", {})
            eid = f'{link.get("source", "")}->{link.get("target", "")}'
            edge_origins[eid] = meta.get("edge_origin", "inferred_relationship_edge")
        line_ranges: list[dict[str, Any]] = []
        source_hashes: list[str] = []
        signature_hashes: list[str] = []
        for n in self.nodes:
            nid = n.get("id", "")
            lr = n.get("line_range") or n.get("metadata", {}).get("line_range") or []
            if lr:
                line_ranges.append({
                    "node_id": nid,
                    "file_path": str(n.get("file_path", "")),
                    "symbol": str(n.get("symbol", "")),
                    "line_range": list(lr),
                })
            d8 = n.get("metadata", {}).get("digest8") or n.get("digest8", "")
            if d8:
                source_hashes.append(d8)
            sh = n.get("metadata", {}).get("signature_hash") or n.get("signature_hash", "")
            if sh:
                signature_hashes.append(sh)

        return {
            "concept": self.concept,
            "workspace_id": self.workspace_id,
            "files": list(self.files),
            "symbols": list(self.symbols),
            "docs": list(self.docs),
            "tests": list(self.tests),
            "commands": list(self.commands),
            "neighbors": list(self.neighbors),
            "line_ranges": line_ranges,
            "source_hashes": source_hashes,
            "signature_hashes": signature_hashes,
            "node_origins": node_origins,
            "edge_origins": edge_origins,
            "codemap_projected_nodes": [n.get("id", "") for n in codemap_projected],
            "exact_topology_nodes": [n.get("id", "") for n in exact_topology],
            "ghost_hypothesis_edges": [],
            "unresolved_candidates": [],
            "grounding_source": ".aura/CODEMAP.json",
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "grounding": self.grounding,
            "notes": (
                "CODEMAP-projected nodes are real CODEMAP-grounded entities projected "
                "into the visual workspace (visual_projection_only). Exact source facts "
                "in this truth_packet are authoritative. Patch authority remains exact "
                "source spans and hashes only."
            ),
        }

    def to_visual_update(
        self,
        existing_node_ids: set[str],
        selected_node_ids: list[str] | None = None,
        current_ghost_edges: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        workspace_node_ids = [n["id"] for n in self.nodes if n.get("id")]
        highlighted = [nid for nid in workspace_node_ids if nid]
        hidden: list[str] = [
            nid for nid in existing_node_ids
            if nid not in set(highlighted)
        ]
        codemap_projected_count = sum(
            1 for n in self.nodes
            if n.get("metadata", {}).get("node_origin") == "codemap_projected_node"
            or n.get("metadata", {}).get("projected_from_codemap")
        )
        return {
            "highlighted_node_ids": highlighted,
            "hidden_node_ids": hidden,
            "selected_node_ids": list(selected_node_ids or []),
            "ghost_edges": list(current_ghost_edges or []),
            "labels": {nid: self.concept for nid in highlighted},
            "ui_hints": [f"{self.profile_key}_concept_workspace_active"],
            "concept_workspace": {
                "files_count": len(self.files),
                "symbols_count": len(self.symbols),
                "tests_count": len(self.tests),
                "docs_count": len(self.docs),
                "neighbors_count": len(self.neighbors),
                "token_estimate": self.token_estimates,
                "workspace_id": self.workspace_id,
                "profile_key": self.profile_key,
                "codemap_projected_node_count": codemap_projected_count,
                "synthetic_node_count": codemap_projected_count,  # backward compat
                "action_buttons": [
                    "show all functions",
                    "show neighbors",
                    "show tests",
                    "show docs",
                    "show agent handoff",
                    "prepare refactor plan",
                    "what Aura tools can help here",
                ],
            },
            "codemap_projected_nodes": [
                n for n in self.nodes
                if n.get("metadata", {}).get("node_origin") == "codemap_projected_node"
                or n.get("metadata", {}).get("projected_from_codemap")
            ],
            "synthetic_nodes": [  # backward compat alias
                n for n in self.nodes
                if n.get("metadata", {}).get("projected_from_codemap")
            ],
            "links": list(self.links),
        }


# ---------------------------------------------------------------------------
# CODEMAP loader (read-only, cached)
# ---------------------------------------------------------------------------

_CODEMAP_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CODEMAP_TTL = 120.0  # seconds


def _load_codemap(repo_root: Path) -> dict[str, Any]:
    path = repo_root / ".aura" / "CODEMAP.json"
    key = str(path)
    now = time.time()
    if key in _CODEMAP_CACHE:
        ts, data = _CODEMAP_CACHE[key]
        if now - ts < _CODEMAP_TTL:
            return data
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        _CODEMAP_CACHE[key] = (now, data)
        return data
    except Exception:
        return {}


def _short_hash(text: str, *, size: int = 12) -> str:
    return hashlib.blake2b(text.encode("utf-8", errors="replace"), digest_size=size).hexdigest()


def _stable_node_id(file_path: str, symbol: str = "") -> str:
    if symbol:
        return f"{file_path}::{symbol}"
    return f"{file_path}::global_scope"


def _node_color_for_type(node_type: str) -> str:
    return {
        "file": "#4f8cff",
        "class": "#f2b84b",
        "function": "#38c98b",
        "method": "#78d9a2",
        "test": "#ef5da8",
        "router": "#c084fc",
        "context": "#22d3ee",
        "research": "#a3e635",
        "verifier": "#ff6b6b",
        "capsule": "#2dd4bf",
        "doc": "#facc15",
        "synthetic": "#8b5cf6",
    }.get(node_type, "#94a3b8")


def _node_type_for_path(path: str) -> str:
    if path.startswith("test_") or "/test_" in path or path.startswith("tests/"):
        return "test"
    if path.endswith(".md") or path.endswith(".rst") or path.endswith(".txt"):
        return "doc"
    if "router" in path or "routing" in path:
        return "router"
    if "verifier" in path or "guard" in path or "validation" in path:
        return "verifier"
    if "research" in path or "arxiv" in path or "paper" in path:
        return "research"
    return "file"


def _codemap_projected_node(
    file_path: str,
    symbol: str = "",
    *,
    kind: str = "file",
    line_range: list[int] | None = None,
    tokens_est: int = 0,
    note: str = "",
    digest8: str = "",
    semantic_id: str = "",
    signature_hash: str = "",
) -> dict[str, Any]:
    """Build an ArenaNode-compatible dict for a real CODEMAP file/symbol not in the
    current projected topology.

    This is a CODEMAP-projected node — the file/symbol is real (entity_exists: true),
    grounded in .aura/CODEMAP.json. The visual projection is UI-only
    (visual_projection_only: true) and carries no patch authority.
    """
    node_id = _stable_node_id(file_path, symbol)
    label = Path(file_path).name if not symbol else f"{symbol}"
    ntype = kind if kind in ("file", "function", "class", "method", "test", "doc", "router") else _node_type_for_path(file_path)
    return {
        "id": node_id,
        "label": label,
        "node_type": ntype,
        "file_path": file_path,
        "symbol": symbol,
        "kind": kind,
        "line_range": list(line_range or []),
        "tokens_est": tokens_est,
        "status": "concept_match",
        "color": _node_color_for_type(ntype),
        "x": 0.0,
        "y": 0.0,
        "z": 0.0,
        "digest8": digest8,
        "semantic_id": semantic_id,
        "signature_hash": signature_hash,
        "metadata": {
            "node_origin": "codemap_projected_node",
            "projected_from_codemap": True,
            "grounding_source": ".aura/CODEMAP.json",
            "visual_projection_only": True,
            "entity_exists": True,
            "patch_authority": False,
            "visual_only": True,  # backward compat
            "concept_note": note or "Projected from CODEMAP by concept workspace engine.",
        },
    }


# Backward-compatible alias
_synthetic_node = _codemap_projected_node


# ---------------------------------------------------------------------------
# Concept resolution
# ---------------------------------------------------------------------------

def _detect_profile(query: str) -> ConceptProfile | None:
    """Return the best-matching ConceptProfile for a query string, or None."""
    q = query.lower().strip()
    # Direct key match
    if q in CONCEPT_PROFILES:
        return CONCEPT_PROFILES[q]
    # Alias match (longest alias wins to avoid partial false positives)
    best: tuple[int, ConceptProfile | None] = (0, None)
    for profile in CONCEPT_PROFILES.values():
        for alias in [profile.key, profile.display_name.lower()] + [a.lower() for a in profile.aliases]:
            if alias and alias in q and len(alias) > best[0]:
                best = (len(alias), profile)
    return best[1]


def resolve_node_ref(
    ref: str,
    workspace: ConceptWorkspace | None = None,
    *,
    existing_nodes: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Resolve a human-friendly node reference to a node ID if possible.

    Returns:
        {
            "resolved": str,          # best node ID (or ref as-is if unresolved)
            "ambiguous": bool,
            "candidates": list[str],  # alternative node IDs if ambiguous
            "method": str,            # how it was resolved
        }
    """
    ref_clean = str(ref or "").strip()
    ref_lower = ref_clean.lower()

    # 1. Exact node ID match in existing nodes
    if existing_nodes and ref_clean in existing_nodes:
        return {"resolved": ref_clean, "ambiguous": False, "candidates": [], "method": "exact_node_id"}

    # 2. Match in workspace nodes
    if workspace:
        ws_node_ids = [n["id"] for n in workspace.nodes if n.get("id")]
        if ref_clean in ws_node_ids:
            return {"resolved": ref_clean, "ambiguous": False, "candidates": [], "method": "workspace_exact"}

        # File path / basename match
        for n in workspace.nodes:
            fp = str(n.get("file_path", ""))
            if ref_lower in fp.lower() or ref_lower == Path(fp).stem.lower():
                return {"resolved": str(n["id"]), "ambiguous": False, "candidates": [], "method": "file_path_match"}

        # Symbol match
        sym_matches = [n["id"] for n in workspace.nodes if ref_lower in str(n.get("symbol", "")).lower()]
        if len(sym_matches) == 1:
            return {"resolved": sym_matches[0], "ambiguous": False, "candidates": [], "method": "symbol_match"}
        if len(sym_matches) > 1:
            return {"resolved": sym_matches[0], "ambiguous": True, "candidates": sym_matches[:5], "method": "symbol_match_ambiguous"}

        # Concept alias match
        profile = _detect_profile(ref_lower)
        if profile and workspace.nodes:
            first_seed = workspace.nodes[0]["id"]
            return {"resolved": first_seed, "ambiguous": False, "candidates": [n["id"] for n in workspace.nodes[:3]], "method": "concept_alias_match"}

    # 3. Concept alias → return profile key as best ref
    profile = _detect_profile(ref_lower)
    if profile:
        return {"resolved": profile.key, "ambiguous": False, "candidates": [], "method": "concept_profile_match"}

    # 4. Unresolved — return ref as-is
    return {"resolved": ref_clean, "ambiguous": False, "candidates": [], "method": "unresolved"}


# ---------------------------------------------------------------------------
# Core: build_concept_workspace
# ---------------------------------------------------------------------------

def build_concept_workspace(
    concept_or_query: str,
    *,
    repo_root: str | Path = ".",
    selected_node_ids: list[str] | None = None,
    existing_nodes: dict[str, dict[str, Any]] | None = None,
    depth: int = 1,
    max_files: int = 80,
    max_symbols: int = 200,
    mode: str = "explore",
) -> ConceptWorkspace:
    """Build a scoped concept workspace by searching the full CODEMAP index.

    Args:
        concept_or_query: Human phrase like "show Agent Arena Bridge" or "st3gg".
        repo_root: Repository root path.
        selected_node_ids: Node IDs currently selected in the visual graph.
        existing_nodes: Nodes already in the projected topology {node_id: node_dict}.
        depth: Neighbor expansion depth (1 = direct neighbors).
        max_files: Maximum files to include.
        max_symbols: Maximum symbols to include.
        mode: "explore" | "functions" | "full" | "prepare".

    Returns:
        ConceptWorkspace with files, symbols, docs, tests, commands, neighbors,
        synthesised nodes, links, truth_packet, and visual_update ready data.
    """
    root = Path(repo_root).resolve()
    query = str(concept_or_query or "").strip()
    query_lower = query.lower()

    # Detect concept profile
    profile = _detect_profile(query_lower)
    profile_key = profile.key if profile else "custom"
    concept_name = profile.display_name if profile else query

    workspace_id = _short_hash(f"{profile_key}:{query}:{time.time()}", size=8)

    ws = ConceptWorkspace(
        concept=concept_name,
        query=query,
        profile_key=profile_key,
        workspace_id=workspace_id,
    )

    # Load CODEMAP (read-only)
    codemap = _load_codemap(root)
    if not codemap:
        ws.grounding = "NEEDS_GROUNDING"
        return ws

    codemap_files: list[dict[str, Any]] = [
        item for item in codemap.get("files", []) or []
        if isinstance(item, dict)
    ]
    symbol_index: dict[str, list[dict[str, Any]]] = codemap.get("symbol_index", {}) or {}
    command_index: dict[str, Any] = codemap.get("command_index", {}) or {}
    topology_index: dict[str, Any] = codemap.get("topology", {}).get("file_index", {}) or {}

    existing_nodes = existing_nodes or {}

    # Build search terms from profile + raw query words
    search_terms: list[str] = []
    if profile:
        search_terms += [profile.key, profile.display_name.lower()]
        search_terms += [a.lower() for a in profile.aliases]
    # Add raw query words (length >= 3 to avoid noise)
    search_terms += [w for w in re.split(r"\W+", query_lower) if len(w) >= 3]
    search_terms = list(dict.fromkeys(t for t in search_terms if t))  # dedupe, preserve order

    # 1. Seed files from profile
    seed_file_paths: set[str] = set()
    if profile:
        seed_file_paths.update(profile.seed_files)

    # 2. Search CODEMAP files
    matched_files: list[str] = []
    for item in codemap_files:
        path = str(item.get("path", ""))
        if not path:
            continue
        path_lower = path.lower()
        if any(term in path_lower for term in search_terms):
            matched_files.append(path)
        # Also check topology neighbors of matched files
    # 2. Search CODEMAP files
    # Keep track of primary matches before topology neighbor expansion
    primary_matched_files = set(matched_files) | seed_file_paths
    matched_files_set = set(primary_matched_files)

    # 3. Expand with topology neighbors (depth=1 by default)
    neighbor_files: set[str] = set()
    for path in list(matched_files_set)[:20]:  # limit BFS cost
        topo_entry = topology_index.get(path, {}) or {}
        nbrs = topo_entry.get("neighbor_files", []) or []
        for nbr in nbrs[:8]:
            neighbor_files.add(str(nbr))
    # Add neighbors if depth > 0
    if depth > 0:
        matched_files_set.update(neighbor_files)

    # 4. Search symbol_index for matching symbols
    matched_symbols: list[dict[str, Any]] = []
    profile_seed_syms = set(profile.seed_symbols if profile else [])
    for sym_name, occurrences in symbol_index.items():
        if not isinstance(occurrences, list):
            continue
        sym_lower = sym_name.lower()
        is_seed = sym_name in profile_seed_syms
        term_match = any(term in sym_lower for term in search_terms)
        if not (is_seed or term_match):
            continue
        for occ in occurrences:
            if not isinstance(occ, dict):
                continue
            file_path = str(occ.get("file", ""))
            matched_files_set.add(file_path)
            matched_symbols.append({
                "symbol": sym_name,
                "file": file_path,
                "kind": occ.get("kind", ""),
                "line": occ.get("line", 0),
                "end_line": occ.get("end_line", 0),
                "semantic_id": occ.get("semantic_id", ""),
                "signature_hash": occ.get("signature_hash", ""),
            })
            if len(matched_symbols) >= max_symbols:
                break
        if len(matched_symbols) >= max_symbols:
            break

    # 5. Find test files
    test_files: list[str] = []
    for path in list(matched_files_set):
        stem = Path(path).stem
        for candidate in [f"test_{stem}.py", f"tests/test_{stem}.py", f"test_{stem.replace('aura_', '')}.py"]:
            if candidate not in matched_files_set:
                # Check if it actually exists in CODEMAP
                if any(str(f.get("path", "")) == candidate for f in codemap_files):
                    test_files.append(candidate)
    # Profile seed docs
    doc_files: list[str] = list(profile.seed_docs if profile else [])
    for path in matched_files_set:
        if path.endswith(".md") or path.endswith(".rst"):
            if path not in doc_files:
                doc_files.append(path)

    # 6. Find matching command_index entries
    matched_commands: list[str] = []
    for cmd, locations in command_index.items():
        cmd_lower = cmd.lower().lstrip("!")
        if any(term in cmd_lower for term in search_terms):
            matched_commands.append(cmd)

    # 7. Enforce limits
    all_files = _stable_list_limited(
        list(matched_files_set),
        max_files,
        # Prefer seed files first, then test files, then others
        priority=list(seed_file_paths) + test_files + doc_files,
    )
    all_symbols = [s["symbol"] for s in matched_symbols[:max_symbols]]
    all_tests = [p for p in all_files if p.startswith("test_") or p.startswith("tests/") or "/test_" in p]
    all_docs = [p for p in all_files if p.endswith(".md") or p.endswith(".rst")]

    ws.files = all_files
    ws.symbols = all_symbols
    ws.docs = all_docs
    ws.tests = all_tests
    ws.commands = matched_commands[:40]
    # Neighbors are topological neighbors of matched files, excluding files that matched keywords/symbols directly
    primary_and_symbol_matches = primary_matched_files | {sym["file"] for sym in matched_symbols if sym.get("file")}
    ws.neighbors = sorted(neighbor_files - primary_and_symbol_matches)[:40]
    ws.seed_matches = sorted(matched_files_set & seed_file_paths)

    # 8. Build nodes — existing topology nodes first, then synthetic for others
    nodes_by_id: dict[str, dict[str, Any]] = {}

    # Existing projected nodes that match — tag with exact_topology_node origin
    for nid, node in existing_nodes.items():
        fp = str(node.get("file_path", "") or node.get("id", ""))
        sym = str(node.get("symbol", ""))
        if fp in matched_files_set or sym in set(all_symbols):
            # Add origin metadata if not already present
            meta = dict(node.get("metadata", {}) or {})
            meta.setdefault("node_origin", "exact_topology_node")
            tagged = dict(node)
            tagged["metadata"] = meta
            nodes_by_id[nid] = tagged

    # CODEMAP-projected nodes for files not in existing topology
    existing_file_paths = {str(n.get("file_path", "")) for n in existing_nodes.values()}
    for file_path in all_files[:max_files]:
        if file_path in existing_file_paths:
            continue
        # Create file-level CODEMAP-projected node
        node_id = _stable_node_id(file_path)
        if node_id not in nodes_by_id:
            ntype = _node_type_for_path(file_path)
            entry = next((f for f in codemap_files if f.get("path") == file_path), {})
            # Compute digest8 from file path for stable identification
            digest8 = _short_hash(file_path, size=8)
            nodes_by_id[node_id] = _codemap_projected_node(
                file_path, "",
                kind=ntype,
                tokens_est=int(entry.get("tokens_est", 0)),
                digest8=digest8,
            )

    # CODEMAP-projected symbol nodes for matched symbols (functions-mode or full-mode)
    if mode in ("functions", "full"):
        for sym_entry in matched_symbols[:50]:
            fp = sym_entry["file"]
            sym = sym_entry["symbol"]
            kind_raw = sym_entry["kind"].lower()
            if "class" in kind_raw:
                kind = "class"
            elif "method" in kind_raw:
                kind = "method"
            else:
                kind = "function"
            node_id = _stable_node_id(fp, sym)
            if node_id not in nodes_by_id:
                nodes_by_id[node_id] = _codemap_projected_node(
                    fp, sym,
                    kind=kind,
                    line_range=[sym_entry["line"], sym_entry["end_line"]],
                    semantic_id=sym_entry.get("semantic_id", ""),
                    signature_hash=sym_entry.get("signature_hash", ""),
                )

    ws.nodes = list(nodes_by_id.values())

    # 9. Synthesise links between matched files (inferred_relationship_edge)
    links: list[dict[str, Any]] = []
    node_id_set = {n["id"] for n in ws.nodes}
    for sym_entry in matched_symbols[:max_symbols]:
        fp = sym_entry["file"]
        sym = sym_entry["symbol"]
        file_node_id = _stable_node_id(fp)
        sym_node_id = _stable_node_id(fp, sym)
        if file_node_id in node_id_set and sym_node_id in node_id_set:
            links.append({
                "source": file_node_id,
                "target": sym_node_id,
                "link_type": "contains",
                "weight": 1.0,
                "status": "known",
                "label": "contains",
                "metadata": {
                    "synthetic": True,  # backward compat
                    "edge_origin": "inferred_relationship_edge",
                    "inference_source": "codemap_symbol_contains",
                },
            })
    # Test → target links (inferred from naming convention)
    for test_path in all_tests:
        stem = Path(test_path).stem
        target_stem = stem[5:] if stem.startswith("test_") else stem  # strip test_ prefix
        for fp in all_files:
            if Path(fp).stem == target_stem or Path(fp).stem == f"aura_{target_stem}":
                src_id = _stable_node_id(test_path)
                tgt_id = _stable_node_id(fp)
                if src_id in node_id_set and tgt_id in node_id_set:
                    links.append({
                        "source": src_id,
                        "target": tgt_id,
                        "link_type": "tested_by",
                        "weight": 0.9,
                        "status": "known",
                        "label": "tested_by",
                        "metadata": {
                            "synthetic": True,  # backward compat
                            "edge_origin": "inferred_relationship_edge",
                            "inference_source": "naming_convention_test",
                        },
                    })
    ws.links = links

    # 10. Token estimates
    ws.token_estimates = {
        "files": len(ws.files),
        "symbols": len(ws.symbols),
        "nodes": len(ws.nodes),
        "links": len(ws.links),
        "estimated_context_tokens": sum(
            int(next((f.get("tokens_est", 0) for f in codemap_files if f.get("path") == fp), 0))
            for fp in ws.files[:20]
        ),
    }

    ws.grounding = "grounded" if ws.files else "NEEDS_GROUNDING"
    return ws


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stable_list_limited(
    items: list[str],
    limit: int,
    *,
    priority: list[str] | None = None,
) -> list[str]:
    """Return up to `limit` items, prioritising items in `priority`."""
    seen: set[str] = set()
    result: list[str] = []
    for item in list(priority or []):
        if item and item not in seen:
            seen.add(item)
            result.append(item)
            if len(result) >= limit:
                break
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
            if len(result) >= limit:
                break
    return result


def get_profile(key_or_alias: str) -> ConceptProfile | None:
    """Public accessor — return a ConceptProfile by key or alias, or None."""
    return _detect_profile(key_or_alias.lower())


def list_concept_keys() -> list[str]:
    """Return all registered concept profile keys."""
    return sorted(CONCEPT_PROFILES.keys())
