"""
Aura Capability Lane Registry — formal registry of cockpit-routable capability lanes.

Each lane defines a routed, explainable, token-sparing capability that the
Native Cockpit can invoke before agent handoff. Lanes are advisory/routing/
planning unless they have exact source spans, hashes, tests, verifier gates,
and human approval.

Dependencies: stdlib only. All Aura imports are lazy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
LANE_REGISTRY_VERSION = "AURA_CAPABILITY_LANE_REGISTRY_V1"


@dataclass
class CapabilityLane:
    """A single cockpit-routable capability lane."""
    lane_id: str = ""
    name: str = ""
    purpose: str = ""
    source_modules: list[str] = field(default_factory=list)
    public_symbols: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    docs: list[str] = field(default_factory=list)
    command_index_entries: list[str] = field(default_factory=list)
    when_to_use: str = ""
    when_not_to_use: str = ""
    required_inputs: list[str] = field(default_factory=list)
    output_packet_type: str = ""
    advisory_only: bool = True
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    token_savings_role: str = "advisory"
    workflow_gate_requirements: list[str] = field(default_factory=list)
    compatible_agents: list[str] = field(default_factory=list)
    cockpit_menu_label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "lane_id": self.lane_id,
            "name": self.name,
            "purpose": self.purpose,
            "source_modules": list(self.source_modules),
            "public_symbols": list(self.public_symbols),
            "tests": list(self.tests),
            "docs": list(self.docs),
            "command_index_entries": list(self.command_index_entries),
            "when_to_use": self.when_to_use,
            "when_not_to_use": self.when_not_to_use,
            "required_inputs": list(self.required_inputs),
            "output_packet_type": self.output_packet_type,
            "advisory_only": self.advisory_only,
            "patch_authority": self.patch_authority,
            "vsa_patch_authority": self.vsa_patch_authority,
            "token_savings_role": self.token_savings_role,
            "workflow_gate_requirements": list(self.workflow_gate_requirements),
            "compatible_agents": list(self.compatible_agents),
            "cockpit_menu_label": self.cockpit_menu_label,
        }


# ---------------------------------------------------------------------------
# Seed lanes (17)
# ---------------------------------------------------------------------------

SEED_LANES: list[dict[str, Any]] = [
    {
        "lane_id": "music_coding_lane",
        "name": "MUSIC Coding Arena",
        "purpose": "Rank/refine candidate code routes, inverse-search coding topology, MUSIC-based advisory ranking.",
        "source_modules": ["aura_music_coding_arena.py", "aura_music_inversion.py"],
        "public_symbols": [],
        "tests": [],
        "docs": [],
        "command_index_entries": [],
        "when_to_use": "When you need to rank candidate code routes or inverse-search coding topology.",
        "when_not_to_use": "When you need exact source spans for patching — use CODEMAP grounding instead.",
        "required_inputs": ["objective", "candidate_files"],
        "output_packet_type": "MusicRankPacket",
        "advisory_only": True,
        "token_savings_role": "routing",
        "workflow_gate_requirements": ["CODEMAP_LOCALIZED"],
        "compatible_agents": ["hermes", "codex"],
        "cockpit_menu_label": "Run MUSIC Rank",
    },
    {
        "lane_id": "mitosis_decomposition_lane",
        "name": "Mitosis Objective Decomposition",
        "purpose": "Split large objectives into child act-capsules, branch work into smaller atomic tasks, reduce context by decomposition.",
        "source_modules": ["aura_mitosis.py"],
        "public_symbols": ["AuraMitosisEngine"],
        "tests": [],
        "docs": [],
        "command_index_entries": [],
        "when_to_use": "When an objective is too large for a single PR and needs decomposition into smaller tasks.",
        "when_not_to_use": "When the objective is already scoped to a single file/symbol.",
        "required_inputs": ["objective"],
        "output_packet_type": "MitosisSplitPacket",
        "advisory_only": True,
        "token_savings_role": "context_reduction",
        "workflow_gate_requirements": ["INGESTED", "POLYSYNTHETIC_COMPRESSED"],
        "compatible_agents": ["hermes", "codex"],
        "cockpit_menu_label": "Split with Mitosis",
    },
    {
        "lane_id": "research_arxiv_lane",
        "name": "Research / arXiv Grounding",
        "purpose": "Research-grounded planning, arXiv/paper memory lookup, research manifest linkage, evidence-backed refactor proposals.",
        "source_modules": ["arxiv_forager.py", "aura_paper_memory.py", "aura_research_manifest.py"],
        "public_symbols": ["ArXivForager", "ArxivPaper"],
        "tests": ["test_aura_research_manifest.py", "test_aura_paper_memory.py"],
        "docs": [],
        "command_index_entries": ["!research", "!forage"],
        "when_to_use": "When you need research evidence to support a refactor approach or find prior art.",
        "when_not_to_use": "When you need exact code grounding — use CODEMAP instead.",
        "required_inputs": ["objective"],
        "output_packet_type": "ResearchEvidencePacket",
        "advisory_only": True,
        "token_savings_role": "localization",
        "workflow_gate_requirements": ["INGESTED"],
        "compatible_agents": ["hermes"],
        "cockpit_menu_label": "Search Research Manifest",
    },
    {
        "lane_id": "skillweaver_lane",
        "name": "SkillWeaver Discovery",
        "purpose": "Discover, compose, and recommend skills for objectives.",
        "source_modules": ["aura_skillweaver.py"],
        "public_symbols": ["AuraSkillWeaver", "AuraSkill"],
        "tests": [],
        "docs": [],
        "command_index_entries": [],
        "when_to_use": "When you need to find existing Aura skills that can help with an objective.",
        "when_not_to_use": "When the objective requires exact code grounding, not skill discovery.",
        "required_inputs": ["objective"],
        "output_packet_type": "SkillDiscoveryPacket",
        "advisory_only": True,
        "token_savings_role": "localization",
        "workflow_gate_requirements": ["INGESTED"],
        "compatible_agents": ["hermes", "codex"],
        "cockpit_menu_label": "Discover Skills",
    },
    {
        "lane_id": "mesh_swarm_lane",
        "name": "Mesh / Multi-Agent Swarm",
        "purpose": "Plan multi-agent execution across Hermes/Codex/Fireworks/local workers.",
        "source_modules": ["aura_mesh.py"],
        "public_symbols": ["AuraMeshSwarm"],
        "tests": [],
        "docs": [],
        "command_index_entries": ["!mesh_status", "!ping_mesh"],
        "when_to_use": "When you need to coordinate multiple agents on different parts of a task.",
        "when_not_to_use": "When a single agent is sufficient.",
        "required_inputs": ["objective", "agents"],
        "output_packet_type": "SwarmPlanPacket",
        "advisory_only": True,
        "token_savings_role": "routing",
        "workflow_gate_requirements": ["PLAN_READY"],
        "compatible_agents": ["hermes", "codex", "fireworks", "local"],
        "cockpit_menu_label": "Build Swarm Plan",
    },
    {
        "lane_id": "mcp_gateway_lane",
        "name": "MCP Gateway Exposure",
        "purpose": "Expose cockpit commands and Agent Arena tools as MCP-compatible tools.",
        "source_modules": ["aura_mcp_gateway.py"],
        "public_symbols": ["AuraMCPGateway", "AuraMCPTool", "AuraMCPToolResult"],
        "tests": [],
        "docs": [],
        "command_index_entries": [],
        "when_to_use": "When you need to expose cockpit operations to MCP-capable agents.",
        "when_not_to_use": "When the agent already uses the CLI directly.",
        "required_inputs": ["cockpit_commands"],
        "output_packet_type": "MCPToolListPacket",
        "advisory_only": True,
        "token_savings_role": "advisory",
        "workflow_gate_requirements": [],
        "compatible_agents": ["mcp_agent"],
        "cockpit_menu_label": "Prepare MCP Tool Surface",
    },
    {
        "lane_id": "plugin_registry_lane",
        "name": "Plugin Registry",
        "purpose": "Register cockpit capabilities and make them discoverable.",
        "source_modules": ["aura_plugin_registry.py"],
        "public_symbols": ["AuraPluginRegistry", "AuraPluginManifest"],
        "tests": [],
        "docs": [],
        "command_index_entries": [],
        "when_to_use": "When you need to register or discover cockpit plugins.",
        "when_not_to_use": "When the capability is already built-in.",
        "required_inputs": ["plugin_manifest"],
        "output_packet_type": "PluginRegistrationPacket",
        "advisory_only": True,
        "token_savings_role": "advisory",
        "workflow_gate_requirements": [],
        "compatible_agents": [],
        "cockpit_menu_label": "Register Plugin",
    },
    {
        "lane_id": "goap_planner_lane",
        "name": "GOAP Planner",
        "purpose": "Decompose objectives into ordered actions, prerequisites, effects, and checkpoints.",
        "source_modules": ["aura_goal_planner.py"],
        "public_symbols": ["AuraGOAPPlanner"],
        "tests": [],
        "docs": [],
        "command_index_entries": [],
        "when_to_use": "When you need to plan a multi-step objective with prerequisites and effects.",
        "when_not_to_use": "When the objective is a single-step task.",
        "required_inputs": ["objective", "initial_state", "goal_conditions"],
        "output_packet_type": "GOAPPlanPacket",
        "advisory_only": True,
        "token_savings_role": "routing",
        "workflow_gate_requirements": ["PLAN_READY"],
        "compatible_agents": ["hermes", "codex"],
        "cockpit_menu_label": "Plan with GOAP",
    },
    {
        "lane_id": "live_architect_lane",
        "name": "Live Architect Patch Lifecycle",
        "purpose": "Integrate !stage, !stage_review, !stage_merge, !stage_purge lifecycle with cockpit checkpoint gates.",
        "source_modules": ["aura_live_architect.py"],
        "public_symbols": ["ArchitectFusionCouncil", "ArchitectBuilderBridge"],
        "tests": ["test_aura_live_architect.py"],
        "docs": [],
        "command_index_entries": ["!stage", "!stage_review", "!stage_merge", "!stage_purge"],
        "when_to_use": "When you need to stage, review, merge, or purge patches through the architect lifecycle.",
        "when_not_to_use": "When the patch has not yet been proposed by an agent.",
        "required_inputs": ["patch_id", "task_id"],
        "output_packet_type": "LiveArchitectPlanPacket",
        "advisory_only": True,
        "token_savings_role": "verification",
        "workflow_gate_requirements": ["PATCH_PROPOSED", "VERIFIED"],
        "compatible_agents": ["hermes"],
        "cockpit_menu_label": "Create Live Architect Stage Plan",
    },
    {
        "lane_id": "associative_core_lane",
        "name": "Associative Core Recall",
        "purpose": "Associative recall to improve DREAM-lite candidate ranking and objective interpretation.",
        "source_modules": ["aura_associative_core.py"],
        "public_symbols": ["AuraAssociativeCore"],
        "tests": [],
        "docs": [],
        "command_index_entries": [],
        "when_to_use": "When you need associative recall to improve candidate ranking.",
        "when_not_to_use": "When exact CODEMAP search is sufficient.",
        "required_inputs": ["objective"],
        "output_packet_type": "AssociativeRecallPacket",
        "advisory_only": True,
        "token_savings_role": "advisory",
        "workflow_gate_requirements": ["CODEMAP_LOCALIZED"],
        "compatible_agents": [],
        "cockpit_menu_label": "Associative Recall",
    },
    {
        "lane_id": "phase_capsule_lane",
        "name": "Phase Capsule State",
        "purpose": "Carry phase-specific context between workflow gates.",
        "source_modules": ["aura_phase_capsule.py"],
        "public_symbols": ["AuraPhaseCapsule", "capture_phase_capsule"],
        "tests": [],
        "docs": [],
        "command_index_entries": [],
        "when_to_use": "When you need to persist phase state between workflow gate transitions.",
        "when_not_to_use": "When the workflow is a single-step task.",
        "required_inputs": ["phase_data"],
        "output_packet_type": "PhaseCapsulePacket",
        "advisory_only": True,
        "token_savings_role": "context_reduction",
        "workflow_gate_requirements": [],
        "compatible_agents": ["hermes", "codex"],
        "cockpit_menu_label": "Create Phase Capsules",
    },
    {
        "lane_id": "audit_staking_lane",
        "name": "Audit / Memory Staking",
        "purpose": "Tamper-evident audit trail for workflow gate transitions and approvals.",
        "source_modules": ["aura_blockchain/memory_staking.py", "aura_blockchain/node.py"],
        "public_symbols": [],
        "tests": [],
        "docs": [],
        "command_index_entries": [],
        "when_to_use": "When you need a tamper-evident audit trail for gate transitions.",
        "when_not_to_use": "When audit is not required.",
        "required_inputs": ["gate_transition"],
        "output_packet_type": "AuditTrailPacket",
        "advisory_only": True,
        "token_savings_role": "safety",
        "workflow_gate_requirements": [],
        "compatible_agents": [],
        "cockpit_menu_label": "Export Audit Packet",
    },
    {
        "lane_id": "federation_lane",
        "name": "Federation (Cross-Repository)",
        "purpose": "Future cross-repository cockpit operation.",
        "source_modules": ["aura_federation.py"],
        "public_symbols": ["AuraFederation"],
        "tests": [],
        "docs": [],
        "command_index_entries": [],
        "when_to_use": "When you need cross-repository operations.",
        "when_not_to_use": "When operating within a single repository.",
        "required_inputs": ["federation_config"],
        "output_packet_type": "FederationPacket",
        "advisory_only": True,
        "token_savings_role": "advisory",
        "workflow_gate_requirements": [],
        "compatible_agents": [],
        "cockpit_menu_label": "Federation",
    },
    {
        "lane_id": "empirical_lab_lane",
        "name": "Empirical Software Lab",
        "purpose": "Benchmark refactor plans, measure outcomes, compare token/cost/quality.",
        "source_modules": ["aura_empirical_software_lab.py"],
        "public_symbols": [],
        "tests": [],
        "docs": [],
        "command_index_entries": [],
        "when_to_use": "When you need to benchmark or compare refactor plans.",
        "when_not_to_use": "When the plan is simple and doesn't need empirical comparison.",
        "required_inputs": ["objective", "candidate_plans"],
        "output_packet_type": "EmpiricalLabPacket",
        "advisory_only": True,
        "token_savings_role": "verification",
        "workflow_gate_requirements": ["PLAN_READY"],
        "compatible_agents": [],
        "cockpit_menu_label": "Empirical Lab",
    },
    {
        "lane_id": "resonant_test_oracle_lane",
        "name": "Resonant Test Oracle",
        "purpose": "Recommend relevant tests and test gaps for proposed act-capsules.",
        "source_modules": ["aura_resonant_test_oracle.py"],
        "public_symbols": [],
        "tests": ["test_resonant_oracle.py"],
        "docs": [],
        "command_index_entries": [],
        "when_to_use": "When you need to identify relevant tests or test gaps before patching.",
        "when_not_to_use": "When tests are already known.",
        "required_inputs": ["objective", "target_files"],
        "output_packet_type": "TestOraclePacket",
        "advisory_only": True,
        "token_savings_role": "verification",
        "workflow_gate_requirements": ["CODEMAP_LOCALIZED"],
        "compatible_agents": [],
        "cockpit_menu_label": "What Tests Prove This",
    },
    {
        "lane_id": "symbolic_trace_memory_lane",
        "name": "Symbolic Trace Memory",
        "purpose": "Store symbolic traces of approved/rejected cockpit decisions.",
        "source_modules": ["aura_symbolic_trace_memory.py"],
        "public_symbols": [],
        "tests": [],
        "docs": [],
        "command_index_entries": [],
        "when_to_use": "When you need to record decision traces for future pattern learning.",
        "when_not_to_use": "When the decision is trivial.",
        "required_inputs": ["decision_record"],
        "output_packet_type": "SymbolicTracePacket",
        "advisory_only": True,
        "token_savings_role": "advisory",
        "workflow_gate_requirements": [],
        "compatible_agents": [],
        "cockpit_menu_label": "Symbolic Trace",
    },
    {
        "lane_id": "module_manifest_lane",
        "name": "Module Manifest",
        "purpose": "Map module responsibility, ownership, and manifest metadata into the cockpit.",
        "source_modules": ["aura_module_manifest.py"],
        "public_symbols": [],
        "tests": [],
        "docs": [],
        "command_index_entries": [],
        "when_to_use": "When you need to understand module ownership or manifest metadata.",
        "when_not_to_use": "When CODEMAP already provides sufficient module info.",
        "required_inputs": ["module_name"],
        "output_packet_type": "ModuleManifestPacket",
        "advisory_only": True,
        "token_savings_role": "localization",
        "workflow_gate_requirements": [],
        "compatible_agents": [],
        "cockpit_menu_label": "Module Manifest",
    },
]


def load_capability_lanes() -> list[CapabilityLane]:
    """Load all capability lanes from the seed list."""
    lanes: list[CapabilityLane] = []
    for seed in SEED_LANES:
        lane = CapabilityLane(
            lane_id=seed.get("lane_id", ""),
            name=seed.get("name", ""),
            purpose=seed.get("purpose", ""),
            source_modules=seed.get("source_modules", []),
            public_symbols=seed.get("public_symbols", []),
            tests=seed.get("tests", []),
            docs=seed.get("docs", []),
            command_index_entries=seed.get("command_index_entries", []),
            when_to_use=seed.get("when_to_use", ""),
            when_not_to_use=seed.get("when_not_to_use", ""),
            required_inputs=seed.get("required_inputs", []),
            output_packet_type=seed.get("output_packet_type", ""),
            advisory_only=seed.get("advisory_only", True),
            patch_authority=PATCH_AUTHORITY,
            vsa_patch_authority=VSA_PATCH_AUTHORITY,
            token_savings_role=seed.get("token_savings_role", "advisory"),
            workflow_gate_requirements=seed.get("workflow_gate_requirements", []),
            compatible_agents=seed.get("compatible_agents", []),
            cockpit_menu_label=seed.get("cockpit_menu_label", ""),
        )
        lanes.append(lane)
    return lanes


def get_lane(lane_id: str) -> CapabilityLane | None:
    """Get a single capability lane by ID."""
    for lane in load_capability_lanes():
        if lane.lane_id == lane_id:
            return lane
    return None


def list_lane_ids() -> list[str]:
    """Return all lane IDs."""
    return [lane.lane_id for lane in load_capability_lanes()]


def lane_registry_packet() -> dict[str, Any]:
    """Return a compact JSON packet of all lanes."""
    lanes = load_capability_lanes()
    return {
        "ok": True,
        "version": LANE_REGISTRY_VERSION,
        "lane_count": len(lanes),
        "lanes": [lane.to_dict() for lane in lanes],
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def explain_lane(lane_id: str) -> dict[str, Any]:
    """Explain a single capability lane in detail."""
    lane = get_lane(lane_id)
    if lane is None:
        return {
            "ok": False,
            "error": f"Lane not found: {lane_id}",
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
    return {
        "ok": True,
        "version": LANE_REGISTRY_VERSION,
        "lane": lane.to_dict(),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
