"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9f6-[Q-SYS:AFFORDANCE_DIRECTORY]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Internal Capability Oracle)
DEPENDENCIES: __future__, dataclasses, hashlib, json, pathlib, re, typing
FUNCTIONS: AuraAffordance, load_affordance_directory, find_affordances,
           explain_affordance, affordance_prompt_cards, route_objective_to_affordances
SYNOPSIS: Aura Affordance Directory / Internal Capability Oracle. Tells Aura and
coding agents which existing internal Aura tools should be reused before inventing
generic solutions. Each affordance is grounded against CODEMAP (files, symbols,
tests). No external provider calls. No heavy dependencies. Affordance cards are
advisory only — never patch authority.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import time
from typing import Any

AFFORDANCE_VERSION = "AURA_AFFORDANCE_DIRECTORY_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


# ---------------------------------------------------------------------------
# AuraAffordance dataclass
# ---------------------------------------------------------------------------


@dataclass
class AuraAffordance:
    """A single Aura-native capability that agents should consider before
    inventing generic solutions."""

    id: str = ""
    name: str = ""
    description: str = ""
    status: str = "active"
    tags: list[str] = field(default_factory=list)
    when_to_use: str = ""
    when_not_to_use: str = ""
    implemented_by: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    docs: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    related_affordances: list[str] = field(default_factory=list)
    safety: str = ""
    patch_authority: bool = False
    vsa_patch_authority: bool = False
    prompt_card: str = ""
    grounding: str = "NEEDS_GROUNDING"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "tags": list(self.tags),
            "when_to_use": self.when_to_use,
            "when_not_to_use": self.when_not_to_use,
            "implemented_by": list(self.implemented_by),
            "symbols": list(self.symbols),
            "tests": list(self.tests),
            "docs": list(self.docs),
            "commands": list(self.commands),
            "requires": list(self.requires),
            "outputs": list(self.outputs),
            "related_affordances": list(self.related_affordances),
            "safety": self.safety,
            "patch_authority": self.patch_authority,
            "vsa_patch_authority": self.vsa_patch_authority,
            "prompt_card": self.prompt_card,
            "grounding": self.grounding,
        }


# ---------------------------------------------------------------------------
# Seed affordances (18 required)
# ---------------------------------------------------------------------------

SEED_AFFORDANCES: list[dict[str, Any]] = [
    {
        "id": "aura.concept_workspace",
        "name": "Concept Workspace Engine",
        "description": "Searches the full CODEMAP index to build scoped concept workspaces with files, symbols, tests, docs, and neighbors — even when targets are not in the current visual topology.",
        "status": "active",
        "tags": ["concept", "workspace", "codemap", "topology", "navigation", "search", "files", "symbols"],
        "when_to_use": "When you need to find all files/symbols/tests/docs related to a concept like 'Coding Arena' or 'ST3GG' — especially when they're not in the current projected topology.",
        "when_not_to_use": "When you already know the exact file path and symbol — use aura_read_slice instead.",
        "implemented_by": ["aura_human_agent_concepts.py"],
        "symbols": ["build_concept_workspace", "resolve_node_ref", "ConceptWorkspace", "ConceptProfile"],
        "tests": ["tests/test_aura_human_agent_concepts.py"],
        "docs": ["docs/AURA_HUMAN_AGENT_ARENA.md"],
        "commands": ["show Coding Arena", "show Agent Arena Bridge", "show all functions related to <concept>"],
        "requires": [".aura/CODEMAP.json"],
        "outputs": ["files", "symbols", "tests", "docs", "neighbors", "nodes", "links", "truth_packet"],
        "related_affordances": ["aura.node_inspector", "aura.coding_arena.topology", "aura.fst.intent_routing"],
        "safety": "Read-only CODEMAP search. No production mutation. CODEMAP-projected nodes are visual-only.",
        "patch_authority": False,
        "vsa_patch_authority": False,
        "prompt_card": "Use Concept Workspace to find all related files/symbols/tests/docs for a concept before planning changes.",
    },
    {
        "id": "aura.node_inspector",
        "name": "Node Intelligence Inspector",
        "description": "Produces grounded NodeIntelligencePackets for any node — origin, file/symbol/line range, digest/hash, relationships, risks, recommended affordances, and safe next actions.",
        "status": "active",
        "tags": ["node", "inspect", "intelligence", "grounding", "relationships", "risk", "expand"],
        "when_to_use": "When you need to understand a specific node — why it's here, what it connects to, what tests/docs relate to it, what risks it carries.",
        "when_not_to_use": "When you need a broad concept overview — use Concept Workspace instead.",
        "implemented_by": ["aura_node_inspector.py"],
        "symbols": ["inspect_node", "expand_node", "route_node_command", "why_is_node_here", "NodeIntelligencePacket"],
        "tests": ["tests/test_aura_node_inspector.py"],
        "docs": ["docs/AURA_NODE_INSPECTOR.md"],
        "commands": ["inspect selected", "explain selected", "why is this node here", "expand selected", "show callers", "show callees"],
        "requires": [".aura/CODEMAP.json"],
        "outputs": ["node_intelligence_packet", "truth_packet", "relationships", "risk", "recommended_affordances", "next_actions"],
        "related_affordances": ["aura.concept_workspace", "aura.jspace.advisory_state", "aura.fst.intent_routing"],
        "safety": "Read-only inspection. No production mutation. JSpace/FST advisory only.",
        "patch_authority": False,
        "vsa_patch_authority": False,
        "prompt_card": "Use Node Inspector to understand why a node exists, what it connects to, and what risks it carries before modifying it.",
    },
    {
        "id": "aura.coding_arena.topology",
        "name": "Coding Arena Topology",
        "description": "Loads and projects the code topology graph, selects micro-arenas, and detects wiring faults — the foundational topology layer for all arena surfaces.",
        "status": "active",
        "tags": ["topology", "arena", "graph", "micro_arena", "wiring_faults", "nodes", "links"],
        "when_to_use": "When you need to load the code topology, isolate a micro-arena around selected nodes, or detect wiring faults.",
        "when_not_to_use": "When you need CODEMAP search beyond the visual topology — use Concept Workspace.",
        "implemented_by": ["aura_coding_arena_3d.py", "aura_coding_arena_server.py"],
        "symbols": ["load_arena_topology", "select_micro_arena", "detect_wiring_faults", "ArenaNode", "ArenaLink", "WiringFault"],
        "tests": ["tests/test_aura_coding_arena_3d.py"],
        "docs": ["AURA_CODING_ARENA_README.md"],
        "commands": ["!topology", "!topology_deep"],
        "requires": [".aura/CODEMAP.json"],
        "outputs": ["topology", "nodes", "links", "micro_arena", "wiring_faults"],
        "related_affordances": ["aura.coding_arena.capsule_compiler", "aura.concept_workspace", "aura.agent_arena.bridge"],
        "safety": "Read-only topology. No production mutation. Topology is advisory/orientation only.",
        "patch_authority": False,
        "vsa_patch_authority": False,
        "prompt_card": "Use Coding Arena Topology to load the graph, isolate micro-arenas, and detect wiring faults before planning changes.",
    },
    {
        "id": "aura.coding_arena.capsule_compiler",
        "name": "Coding Arena Capsule Compiler",
        "description": "Compiles action capsules from selected nodes with route simulation — deterministic, no model calls.",
        "status": "active",
        "tags": ["capsule", "compile", "action", "route", "simulation"],
        "when_to_use": "When you need to compile an action capsule from a selection and simulate its model route.",
        "when_not_to_use": "When you need actual patching — use Agent Arena Bridge staging instead.",
        "implemented_by": ["aura_coding_arena_3d.py"],
        "symbols": ["compile_action_capsule", "simulate_model_route", "apply_marked_edge"],
        "tests": ["tests/test_aura_coding_arena_3d.py"],
        "docs": ["AURA_CODING_ARENA_README.md"],
        "commands": [],
        "requires": ["topology"],
        "outputs": ["action_capsule", "route_decision"],
        "related_affordances": ["aura.coding_arena.topology", "aura.agent_arena.bridge", "aura.architect_loop"],
        "safety": "Advisory capsules only. No production mutation. Route simulation is deterministic.",
        "patch_authority": False,
        "vsa_patch_authority": False,
        "prompt_card": "Use Capsule Compiler to compile and simulate action capsules before staging patches.",
    },
    {
        "id": "aura.agent_arena.bridge",
        "name": "Agent Arena Bridge",
        "description": "Machine-agent interface for external coding agents — prepare arena, get micro-context, search code, read slices, stage patches, verify, repair, and export ICM.",
        "status": "active",
        "tags": ["agent", "bridge", "external", "handoff", "prepare", "stage", "verify", "repair", "mcp", "cli"],
        "when_to_use": "When an external coding agent needs to prepare a task, get micro-context, stage a patch, or verify results through Aura's boundary logic.",
        "when_not_to_use": "For human-in-the-loop exploration — use Human Agent Arena instead.",
        "implemented_by": ["aura_agent_arena_bridge.py", "aura_agent_arena_cli.py", "aura_agent_arena_mcp.py"],
        "symbols": ["AuraAgentArenaBridge", "aura_prepare_arena", "aura_get_micro_context", "aura_search_code", "aura_read_slice", "aura_stage_patch", "aura_verify_arena", "aura_repair_packet", "aura_find_affordances"],
        "tests": ["tests/test_aura_agent_arena_bridge.py", "tests/test_aura_agent_arena_cli.py", "tests/test_aura_agent_arena_mcp.py"],
        "docs": ["docs/AURA_AGENT_ARENA_BRIDGE.md"],
        "commands": ["aura prepare", "aura search", "aura read-slice", "aura stage-patch", "aura verify"],
        "requires": [".aura/CODEMAP.json"],
        "outputs": ["plan_phase_hash", "act_capsules", "grounding_evidence", "shadow_findings", "routing_decisions"],
        "related_affordances": ["aura.coding_arena.topology", "aura.architect_loop", "aura.concept_workspace", "aura.node_inspector"],
        "safety": "Patches staged + verified only. No direct production mutation. Boundary contracts enforced.",
        "patch_authority": False,
        "vsa_patch_authority": False,
        "prompt_card": "Use Agent Arena Bridge to prepare, stage, and verify patches through Aura's boundary logic — never mutate directly.",
    },
    {
        "id": "aura.jspace.advisory_state",
        "name": "JSpace Advisory State",
        "description": "Compact advisory routing state codec — encodes/decodes FST route frames into compact J0 packets. Advisory only, never patch authority.",
        "status": "active",
        "tags": ["jspace", "advisory", "routing", "state", "codec", "compact"],
        "when_to_use": "When you need to attach advisory routing state to capsules or inspect route frame compactness.",
        "when_not_to_use": "When you need actual routing decisions — use FST intent routing.",
        "implemented_by": ["aura_jspace_codec.py"],
        "symbols": ["build_jspace_packet", "parse_jspace_packet", "active_concepts_from_packet", "attach_jspace_to_capsule", "AuraJState"],
        "tests": ["tests/test_aura_jspace_codec.py"],
        "docs": [],
        "commands": [],
        "requires": [],
        "outputs": ["jspace_packet", "jspace_state", "active_concepts"],
        "related_affordances": ["aura.fst.intent_routing", "aura.node_inspector"],
        "safety": "Advisory only. JSpace state never becomes patch authority.",
        "patch_authority": False,
        "vsa_patch_authority": False,
        "prompt_card": "Use JSpace to attach advisory routing state to capsules — compact, deterministic, never patch authority.",
    },
    {
        "id": "aura.fst.intent_routing",
        "name": "FST Intent Routing",
        "description": "Finite-state transducer lexicon for cognitive routing — maps intents to routes with VSA-weighted transitions. Reduces edge complexity from O(N²) to O(E).",
        "status": "active",
        "tags": ["fst", "routing", "intent", "lexicon", "transducer", "vsa"],
        "when_to_use": "When you need to route a coding intent (refactor, verify, repair, test) to the correct action path.",
        "when_not_to_use": "When you just need to search CODEMAP — use Concept Workspace.",
        "implemented_by": ["aura_fst_routing.py"],
        "symbols": ["route", "find_optimal_path", "weighted_route_scores", "INTENT_SYMBOLS", "ARTIFACT_SYMBOLS"],
        "tests": [],
        "docs": [],
        "commands": ["!route"],
        "requires": ["aura_lexc"],
        "outputs": ["route", "path", "transition_weights"],
        "related_affordances": ["aura.jspace.advisory_state", "aura.node_inspector", "aura.coding_arena.capsule_compiler"],
        "safety": "Advisory routing. Route decisions guide but do not authorize patches.",
        "patch_authority": False,
        "vsa_patch_authority": False,
        "prompt_card": "Use FST Intent Routing to map coding intents to correct action paths — reduces complexity from O(N²) to O(E).",
    },
    {
        "id": "aura.st3gg.egress",
        "name": "ST3GG Egress Codec",
        "description": "Visible-ASCII egress codec for arena capsules — encodes/decodes capsules for compact, human-readable egress. Recall sidecar for audit trail.",
        "status": "active",
        "tags": ["st3gg", "egress", "codec", "encode", "decode", "visible_ascii", "recall"],
        "when_to_use": "When you need to encode arena capsules for compact egress or recall them for audit.",
        "when_not_to_use": "When you need JSpace advisory state — use JSpace codec instead.",
        "implemented_by": ["aura_arena_st3gg_codec.py", "aura_arena_st3gg_egress.py", "aura_st3gg_recall.py"],
        "symbols": ["encode_arena_capsule_for_egress", "ST3GGEgressPayload", "AuraArenaCodec"],
        "tests": ["test_aura_arena_st3gg_codec.py", "test_aura_st3gg_recall.py", "test_aura_st3gg_compact.py"],
        "docs": [],
        "commands": [],
        "requires": [],
        "outputs": ["egress_payload", "recall_packet"],
        "related_affordances": ["aura.jspace.advisory_state", "aura.coding_arena.capsule_compiler"],
        "safety": "Egress is advisory encoding. No production mutation.",
        "patch_authority": False,
        "vsa_patch_authority": False,
        "prompt_card": "Use ST3GG Egress to encode capsules for compact visible-ASCII egress and recall for audit.",
    },
    {
        "id": "aura.context_crusher",
        "name": "Context Crusher",
        "description": "Compresses context for LLM prompts — reduces token usage while preserving essential information.",
        "status": "active",
        "tags": ["context", "crush", "compress", "tokens", "prompt", "reduce"],
        "when_to_use": "When you need to reduce token usage in LLM prompts while preserving essential context.",
        "when_not_to_use": "When you need exact source — use aura_read_slice instead.",
        "implemented_by": ["aura_context_crusher.py"],
        "symbols": ["AuraContextCrusher", "apply_context_crush_to_prompt"],
        "tests": ["test_aura_context_crusher.py"],
        "docs": [],
        "commands": [],
        "requires": [],
        "outputs": ["crushed_context", "token_savings"],
        "related_affordances": ["aura.st3gg.egress", "aura.llm_egress", "aura.tokenizer_guard"],
        "safety": "Advisory compression. Verify essential information is preserved.",
        "patch_authority": False,
        "vsa_patch_authority": False,
        "prompt_card": "Use Context Crusher to reduce token usage in prompts before sending to LLMs.",
    },
    {
        "id": "aura.understand_graph",
        "name": "Understand Graph Bridge",
        "description": "Bridges code topology into a layered understand graph for spectral navigation and concept mapping.",
        "status": "active",
        "tags": ["understand", "graph", "bridge", "spectral", "navigation", "layers"],
        "when_to_use": "When you need to navigate the codebase as a layered understand graph with spectral coordinates.",
        "when_not_to_use": "When you need CODEMAP search — use Concept Workspace.",
        "implemented_by": ["aura_understand_graph_bridge.py"],
        "symbols": ["AuraUnderstandGraph", "GraphNode", "GraphEdge", "GraphLayer"],
        "tests": [],
        "docs": [".aura/understand_graph.json"],
        "commands": [],
        "requires": [".aura/understand_graph.json"],
        "outputs": ["understand_graph", "layers", "spectral_coordinates"],
        "related_affordances": ["aura.coding_arena.topology", "aura.concept_workspace"],
        "safety": "Read-only graph bridge. No production mutation.",
        "patch_authority": False,
        "vsa_patch_authority": False,
        "prompt_card": "Use Understand Graph Bridge for spectral navigation of the codebase as layered concepts.",
    },
    {
        "id": "aura.emergent_potential.audit",
        "name": "Emergent Potential Audit",
        "description": "Read-only audit that discovers unwired connection candidates between code entities — emergence scoring, missing wires, and capability gaps.",
        "status": "active",
        "tags": ["emergent", "potential", "audit", "unwired", "connections", "discovery"],
        "when_to_use": "When you need to find unwired connection candidates or discover capability gaps between code entities.",
        "when_not_to_use": "When you need exact topology — use Coding Arena Topology.",
        "implemented_by": ["aura_emergent_potential_repl.py", "aura_emergent_result_verifier.py", "aura_emergent_capability_auditor.py"],
        "symbols": ["audit_emergent_potential", "EmergentCluster", "EmergentConnection", "EmergentPotentialReport"],
        "tests": ["tests/test_aura_emergent_potential_repl.py", "tests/test_aura_emergent_result_verifier.py"],
        "docs": [],
        "commands": [],
        "requires": [".aura/CODEMAP.json"],
        "outputs": ["connections", "emergence_scores", "missing_wires", "constraints"],
        "related_affordances": ["aura.coding_arena.topology", "aura.concept_workspace"],
        "safety": "Read-only audit. No production mutation. Report only.",
        "patch_authority": False,
        "vsa_patch_authority": False,
        "prompt_card": "Use Emergent Potential Audit to discover unwired connections and capability gaps — read-only, report only.",
    },
    {
        "id": "aura.dream.reranking",
        "name": "DREAM Reranking",
        "description": "Dream engine candidate generation and reranking for arena — explores alternative solutions and reranks by quality.",
        "status": "active",
        "tags": ["dream", "reranking", "candidates", "exploration", "quality", "arena"],
        "when_to_use": "When you need to explore alternative solution candidates and rerank them by quality.",
        "when_not_to_use": "When you need deterministic routing — use FST Intent Routing.",
        "implemented_by": ["aura_dream_engine.py", "aura_dream_retrieval.py"],
        "symbols": ["AuraDreamEngine", "DreamCandidate", "rerank_for_arena"],
        "tests": ["test_aura_dream_retrieval.py"],
        "docs": [],
        "commands": [],
        "requires": [],
        "outputs": ["dream_candidates", "reranked_candidates"],
        "related_affordances": ["aura.qdkt.memory", "aura.architect_loop"],
        "safety": "Advisory exploration. No production mutation.",
        "patch_authority": False,
        "vsa_patch_authority": False,
        "prompt_card": "Use DREAM Reranking to explore alternative solutions and rerank by quality before committing.",
    },
    {
        "id": "aura.qdkt.memory",
        "name": "QDKT Memory",
        "description": "Quantum-driven knowledge transfer memory — observes and transfers knowledge across tasks.",
        "status": "active",
        "tags": ["qdkt", "memory", "knowledge", "transfer", "observe"],
        "when_to_use": "When you need to observe or transfer knowledge across coding tasks.",
        "when_not_to_use": "When you need persistent memory — use Aura Memory Palace.",
        "implemented_by": ["aura_qdkt.py"],
        "symbols": ["get_qdkt"],
        "tests": [],
        "docs": [],
        "commands": ["!qdkt"],
        "requires": [],
        "outputs": ["qdkt_state", "observations"],
        "related_affordances": ["aura.dream.reranking", "aura.architect_loop"],
        "safety": "Advisory memory. No production mutation.",
        "patch_authority": False,
        "vsa_patch_authority": False,
        "prompt_card": "Use QDKT Memory to observe and transfer knowledge across tasks.",
    },
    {
        "id": "aura.llm_egress",
        "name": "LLM Egress",
        "description": "Manages LLM egress — pre-egress interception, token economics, and output formatting for external model calls.",
        "status": "active",
        "tags": ["llm", "egress", "interceptor", "tokens", "output", "formatting"],
        "when_to_use": "When you need to manage LLM egress — intercept, format, or optimize output for external models.",
        "when_not_to_use": "When you need context compression — use Context Crusher.",
        "implemented_by": ["aura_llm_egress.py", "aura_pre_egress_interceptor.py"],
        "symbols": ["AuraLLMEgress"],
        "tests": [],
        "docs": [],
        "commands": [],
        "requires": [],
        "outputs": ["egress_payload", "intercepted_output"],
        "related_affordances": ["aura.context_crusher", "aura.tokenizer_guard", "aura.st3gg.egress"],
        "safety": "Egress management only. No production mutation.",
        "patch_authority": False,
        "vsa_patch_authority": False,
        "prompt_card": "Use LLM Egress to manage and optimize output before sending to external models.",
    },
    {
        "id": "aura.tokenizer_guard",
        "name": "Tokenizer Guard",
        "description": "Validates and sanitizes tokenizer channels — prevents tokenizer injection and channel corruption.",
        "status": "active",
        "tags": ["tokenizer", "guard", "sanitize", "validate", "security", "injection"],
        "when_to_use": "When you need to validate or sanitize tokenizer channels before processing.",
        "when_not_to_use": "When you need general validation — use aura_validation.",
        "implemented_by": ["aura_tokenizer_guard.py"],
        "symbols": ["sanitize_tokenizer_channels"],
        "tests": ["test_aura_tokenizer_guard.py"],
        "docs": [],
        "commands": [],
        "requires": [],
        "outputs": ["sanitized_channels", "validation_result"],
        "related_affordances": ["aura.llm_egress", "aura.patch_quality_gate"],
        "safety": "Security validation. No production mutation.",
        "patch_authority": False,
        "vsa_patch_authority": False,
        "prompt_card": "Use Tokenizer Guard to validate and sanitize tokenizer channels before processing.",
    },
    {
        "id": "aura.patch_quality_gate",
        "name": "Patch Quality Gate",
        "description": "Verifies patch quality — runs tests, checks boundary contracts, and gates patches before staging.",
        "status": "active",
        "tags": ["patch", "quality", "gate", "verify", "tests", "boundary", "contracts"],
        "when_to_use": "When you need to verify a patch meets quality gates before staging.",
        "when_not_to_use": "When you need to stage a patch — use Agent Arena Bridge staging.",
        "implemented_by": ["aura_patch_quality_gate.py", "aura_validation.py"],
        "symbols": ["sanitize_tokenizer_channels"],
        "tests": ["test_aura_patch_quality.py", "test_aura_tokenizer_guard.py"],
        "docs": [],
        "commands": [],
        "requires": [],
        "outputs": ["quality_gate_result", "test_results"],
        "related_affordances": ["aura.agent_arena.bridge", "aura.tokenizer_guard"],
        "safety": "Verification gate only. No production mutation.",
        "patch_authority": False,
        "vsa_patch_authority": False,
        "prompt_card": "Use Patch Quality Gate to verify patches meet quality and boundary contracts before staging.",
    },
    {
        "id": "aura.architect_loop",
        "name": "Architect Loop",
        "description": "Architect fusion loop — prepares coding plans with act capsules, grounding evidence, shadow findings, and routing decisions.",
        "status": "active",
        "tags": ["architect", "loop", "fusion", "plan", "capsules", "grounding", "shadow", "routing"],
        "when_to_use": "When you need to prepare a coding plan with act capsules, grounding, and shadow findings.",
        "when_not_to_use": "When you just need topology — use Coding Arena Topology.",
        "implemented_by": ["aura_architect_loop.py", "aura_live_architect.py"],
        "symbols": ["ArchitectFusionLoop", "ArchitectFusionCouncil", "ArchitectBuilderBridge", "ArchitectLoopResult"],
        "tests": ["test_aura_architect_loop.py", "test_aura_live_architect.py"],
        "docs": [],
        "commands": ["!plan"],
        "requires": [".aura/CODEMAP.json"],
        "outputs": ["plan", "act_capsules", "grounding_evidence", "shadow_findings", "routing_decisions"],
        "related_affordances": ["aura.agent_arena.bridge", "aura.coding_arena.capsule_compiler"],
        "safety": "Plan preparation only. No production mutation. Patches staged separately.",
        "patch_authority": False,
        "vsa_patch_authority": False,
        "prompt_card": "Use Architect Loop to prepare coding plans with capsules, grounding, and shadow findings before staging.",
    },
    {
        "id": "aura.research_arxiv_memory",
        "name": "Research / ArXiv Memory",
        "description": "ArXiv paper foraging, research manifest, and paper memory — discovers, ingests, and remembers research papers.",
        "status": "active",
        "tags": ["research", "arxiv", "paper", "forage", "memory", "manifest", "ingest"],
        "when_to_use": "When you need to discover, ingest, or recall ArXiv research papers.",
        "when_not_to_use": "When you need code topology — use Coding Arena Topology.",
        "implemented_by": ["arxiv_forager.py", "aura_research_manifest.py", "aura_paper_memory.py", "aura_research_ingest_bridge.py"],
        "symbols": ["ArXivForager", "ArxivPaper"],
        "tests": ["test_aura_research_manifest.py", "test_aura_paper_memory.py"],
        "docs": [],
        "commands": ["!research", "!forage"],
        "requires": [],
        "outputs": ["papers", "research_manifest", "paper_memory"],
        "related_affordances": ["aura.dream.reranking", "aura.qdkt.memory"],
        "safety": "Research ingestion only. No production code mutation.",
        "patch_authority": False,
        "vsa_patch_authority": False,
        "prompt_card": "Use Research/ArXiv Memory to discover, ingest, and recall research papers relevant to your task.",
    },
]


# ---------------------------------------------------------------------------
# CODEMAP loader (read-only, cached)
# ---------------------------------------------------------------------------

_CODEMAP_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CODEMAP_TTL = 120.0


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


# ---------------------------------------------------------------------------
# Grounding verification
# ---------------------------------------------------------------------------


def _ground_affordance(aff: dict[str, Any], codemap: dict[str, Any]) -> str:
    """Verify an affordance's files/symbols against CODEMAP. Returns grounding level."""
    files = codemap.get("files", [])
    file_paths_set = {str(f.get("path", "")) for f in files if isinstance(f, dict)}
    si = codemap.get("symbol_index", {})

    implemented_by = aff.get("implemented_by", [])
    symbols = aff.get("symbols", [])
    tests = aff.get("tests", [])

    files_found = sum(1 for fp in implemented_by if fp in file_paths_set)
    symbols_found = sum(1 for sym in symbols if sym in si)
    tests_found = sum(1 for tp in tests if tp in file_paths_set)

    total_items = len(implemented_by) + len(symbols) + len(tests)
    found_items = files_found + symbols_found + tests_found

    if total_items == 0:
        return "NEEDS_GROUNDING"
    if found_items == total_items:
        return "grounded"
    if found_items > 0:
        return "partial"
    return "NEEDS_GROUNDING"


# ---------------------------------------------------------------------------
# load_affordance_directory
# ---------------------------------------------------------------------------


def load_affordance_directory(repo_root: str | Path = ".") -> list[AuraAffordance]:
    """Load all affordances from the seed list, optionally enriched from
    .aura/AFFORDANCE_MAP.json, and ground each against CODEMAP."""
    root = Path(repo_root).resolve()
    codemap = _load_codemap(root)

    # Start with seed affordances
    all_affords: list[dict[str, Any]] = list(SEED_AFFORDANCES)

    # Try to load additional from AFFORDANCE_MAP.json
    affordance_map_path = root / ".aura" / "AFFORDANCE_MAP.json"
    try:
        if affordance_map_path.exists():
            with open(affordance_map_path, "r", encoding="utf-8") as fh:
                extra = json.load(fh)
            if isinstance(extra, dict) and "affordances" in extra:
                existing_ids = {a.get("id") for a in all_affords}
                for aff in extra["affordances"]:
                    if isinstance(aff, dict) and aff.get("id") not in existing_ids:
                        all_affords.append(aff)
    except Exception:
        pass

    # Ground each affordance
    result: list[AuraAffordance] = []
    for aff in all_affords:
        grounding = _ground_affordance(aff, codemap)
        aff["grounding"] = grounding
        result.append(AuraAffordance(**{k: aff.get(k, v) for k, v in {
            "id": "", "name": "", "description": "", "status": "active",
            "tags": [], "when_to_use": "", "when_not_to_use": "",
            "implemented_by": [], "symbols": [], "tests": [], "docs": [],
            "commands": [], "requires": [], "outputs": [],
            "related_affordances": [], "safety": "",
            "patch_authority": False, "vsa_patch_authority": False,
            "prompt_card": "", "grounding": "NEEDS_GROUNDING",
        }.items() if k in aff} | {k: aff[k] for k in aff if k in {
            "id", "name", "description", "status", "tags", "when_to_use",
            "when_not_to_use", "implemented_by", "symbols", "tests", "docs",
            "commands", "requires", "outputs", "related_affordances",
            "safety", "patch_authority", "vsa_patch_authority",
            "prompt_card", "grounding",
        }}))

    return result


# ---------------------------------------------------------------------------
# find_affordances
# ---------------------------------------------------------------------------


def _score_affordance(
    aff: AuraAffordance,
    objective: str,
    target_files: list[str] | None,
    target_symbols: list[str] | None,
    concept_profile_overlap: set[str] | None,
) -> float:
    """Score an affordance against the objective and targets."""
    obj_lower = objective.lower()
    obj_words = set(re.split(r"\W+", obj_lower)) - {"", "the", "a", "an", "is", "to", "for", "of", "in", "on", "and", "or", "with"}

    score = 0.0

    # Tag match
    tags_lower = {t.lower() for t in aff.tags}
    score += sum(1.0 for w in obj_words if w in tags_lower) * 2.0

    # Name/description match
    name_lower = aff.name.lower()
    desc_lower = aff.description.lower()
    score += sum(1.0 for w in obj_words if w in name_lower)
    score += sum(0.5 for w in obj_words if w in desc_lower)

    # when_to_use match
    wtu_lower = aff.when_to_use.lower()
    score += sum(0.7 for w in obj_words if w in wtu_lower)

    # Target file overlap
    if target_files:
        aff_files_set = set(aff.implemented_by)
        target_set = set(target_files)
        overlap = aff_files_set & target_set
        score += len(overlap) * 3.0

    # Target symbol overlap
    if target_symbols:
        aff_syms_set = set(aff.symbols)
        target_sym_set = set(target_symbols)
        overlap = aff_syms_set & target_sym_set
        score += len(overlap) * 3.0

    # Concept profile overlap
    if concept_profile_overlap:
        aff_all = set(aff.tags) | set(aff.implemented_by) | set(aff.symbols)
        aff_all_lower = {a.lower() for a in aff_all}
        score += len(concept_profile_overlap & aff_all_lower) * 1.5

    # Tests available bonus
    if aff.tests:
        score += 0.5

    # Risk/safety penalty
    if aff.safety and "no production" in aff.safety.lower():
        score += 0.3  # safe affordances get slight boost

    # Grounding penalty
    if aff.grounding == "NEEDS_GROUNDING":
        score -= 2.0
    elif aff.grounding == "partial":
        score -= 0.5

    return score


def _detect_concept_overlap(objective: str) -> set[str]:
    """Detect concept profile overlap from the objective text."""
    try:
        from aura_human_agent_concepts import CONCEPT_PROFILES

        obj_lower = objective.lower()
        overlap: set[str] = set()
        for key, profile in CONCEPT_PROFILES.items():
            aliases = [key, profile.display_name.lower()] + [a.lower() for a in profile.aliases]
            for alias in aliases:
                if alias and alias in obj_lower:
                    overlap.add(key)
                    overlap.update(a.lower() for a in profile.aliases[:5])
                    overlap.update(profile.seed_files)
                    overlap.update(profile.seed_symbols)
                    break
        return overlap
    except Exception:
        return set()


def find_affordances(
    objective: str,
    target_files: list[str] | None = None,
    target_symbols: list[str] | None = None,
    selected_node_ids: list[str] | None = None,
    current_workspace: dict[str, Any] | None = None,
    repo_root: str | Path = ".",
    top_k: int = 7,
) -> dict[str, Any]:
    """Find ranked Aura-native affordances for an objective.

    Ranking uses: objective/tag match, target file overlap, symbol overlap,
    concept profile overlap, related affordance expansion, tests available,
    and risk/safety penalty.

    Returns a compact packet with recommended_affordances, prompt_cards,
    do_not_reinvent notes, grounding, and patch authority invariants.
    """
    root = Path(repo_root).resolve()
    directory = load_affordance_directory(root)

    concept_overlap = _detect_concept_overlap(objective)

    # Extract target files/symbols from workspace if not provided
    if not target_files and current_workspace:
        target_files = current_workspace.get("files", [])
    if not target_symbols and current_workspace:
        target_symbols = current_workspace.get("symbols", [])

    # Score all affordances
    scored: list[tuple[float, AuraAffordance]] = []
    for aff in directory:
        score = _score_affordance(aff, objective, target_files, target_symbols, concept_overlap)
        scored.append((score, aff))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    # Take top_k
    top = scored[:top_k]

    # Expand with related affordances — boost score for related items already in scored
    related_ids = {
        related_id
        for _, aff in top
        for related_id in aff.related_affordances
    }
    scored = [
        (score + 0.25 if aff.id in related_ids else score, aff)
        for score, aff in scored
    ]

    # Re-sort and take final top_k
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]

    # Build compact result
    recommended: list[dict[str, Any]] = []
    prompt_cards: list[str] = []
    do_not_reinvent: list[str] = []

    for score, aff in top:
        if score <= 0:
            continue
        recommended.append({
            "id": aff.id,
            "name": aff.name,
            "description": aff.description[:200],
            "when_to_use": aff.when_to_use,
            "when_not_to_use": aff.when_not_to_use,
            "implemented_by": aff.implemented_by,
            "symbols": aff.symbols,
            "tests": aff.tests,
            "safety": aff.safety,
            "grounding": aff.grounding,
            "score": round(score, 2),
            "patch_authority": aff.patch_authority,
            "vsa_patch_authority": aff.vsa_patch_authority,
        })
        if aff.prompt_card:
            prompt_cards.append(aff.prompt_card)
        do_not_reinvent.append(
            f"Do not reinvent: {aff.name} ({aff.id}) already handles this. "
            f"Use: {', '.join(aff.implemented_by[:2])}."
        )

    # Route frame
    route_frame = _route_frame_for_objective(objective, recommended)

    # Grounding summary
    grounding_levels = [r.get("grounding", "NEEDS_GROUNDING") for r in recommended]
    if all(g == "grounded" for g in grounding_levels) and grounding_levels:
        grounding_summary = "grounded"
    elif any(g == "grounded" for g in grounding_levels):
        grounding_summary = "partial"
    else:
        grounding_summary = "NEEDS_GROUNDING"

    return {
        "objective": objective,
        "route_frame": route_frame,
        "recommended_affordances": recommended,
        "prompt_cards": prompt_cards,
        "do_not_reinvent": do_not_reinvent,
        "grounding": grounding_summary,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def _route_frame_for_objective(objective: str, recommended: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a simple route frame from the objective and recommended affordances."""
    obj_lower = objective.lower()

    intent = "explain"
    if any(w in obj_lower for w in ["refactor", "change", "modify", "update"]):
        intent = "code_refactor"
    elif any(w in obj_lower for w in ["test", "verify", "check"]):
        intent = "verify"
    elif any(w in obj_lower for w in ["find", "locate", "where"]):
        intent = "localize"
    elif any(w in obj_lower for w in ["fix", "repair", "debug"]):
        intent = "repair"

    action = "inspect"
    if intent == "code_refactor":
        action = "modify"
    elif intent == "verify":
        action = "verify"
    elif intent == "repair":
        action = "repair"

    return {
        "intent": intent,
        "artifact": "python_module",
        "action": action,
        "scope": "symbol",
        "risk": "low",
        "grounding": "codemap_grounded" if recommended else "none",
        "tests": "existing" if any(r.get("tests") for r in recommended) else "required",
        "quality": "balanced",
        "cost": "no_model",
    }


# ---------------------------------------------------------------------------
# explain_affordance
# ---------------------------------------------------------------------------


def explain_affordance(affordance_id: str, repo_root: str | Path = ".") -> dict[str, Any]:
    """Explain a single affordance in detail."""
    root = Path(repo_root).resolve()
    directory = load_affordance_directory(root)
    aff = next((a for a in directory if a.id == affordance_id), None)
    if aff is None:
        return {
            "ok": False,
            "error": f"Affordance not found: {affordance_id}",
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
    return {
        "ok": True,
        "affordance": aff.to_dict(),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


# ---------------------------------------------------------------------------
# affordance_prompt_cards
# ---------------------------------------------------------------------------


def affordance_prompt_cards(objective: str, top_k: int = 7, repo_root: str | Path = ".") -> list[str]:
    """Return compact prompt cards for the top affordances matching an objective."""
    result = find_affordances(objective, repo_root=repo_root, top_k=top_k)
    return result.get("prompt_cards", [])


# ---------------------------------------------------------------------------
# route_objective_to_affordances
# ---------------------------------------------------------------------------


def route_objective_to_affordances(objective: str, repo_root: str | Path = ".") -> dict[str, Any]:
    """Route an objective to recommended affordances — same as find_affordances
    but with a focus on the route frame for agent handoff."""
    return find_affordances(objective, repo_root=repo_root, top_k=7)
