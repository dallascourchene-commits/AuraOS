"""
Aura Native Cockpit — primary human coding interface orchestrator.

Unifies Aura's systems into a single cockpit:
  * Intent Ingestion (polysynthetic parsing, LEXC/FST routing)
  * Capability Connectome (living graph of Aura capabilities)
  * Workflow Gates (18-state checkpoint machine)
  * Token Economy Orchestrator (savings measurement)
  * Agent Arena Bridge (CODEMAP, grounding, micro-context, patch staging)
  * Hermes Arena Mode (agent handoff contracts)

The cockpit is read-only — it never mutates production code. All mutations
go through the Agent Arena Bridge staging pipeline.

Dependencies: stdlib only at module level. All Aura imports are lazy.
numpy is NOT required.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants and invariants
# ---------------------------------------------------------------------------

COCKPIT_VERSION = "AURA_NATIVE_COCKPIT_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


# ---------------------------------------------------------------------------
# Cockpit orchestrator
# ---------------------------------------------------------------------------


class AuraNativeCockpit:
    """Aura's primary human coding interface orchestrator.

    The cockpit is the entry point for a human who wants to:
    1. Paste/load a long refactor plan or intent document
    2. Let Aura compress it polysynthetically
    3. Route it through FST architecture
    4. Inspect relevant code topology
    5. Generate checkpointed task capsules
    6. Send approved work to Hermes/Codex/Agent Arena as compact packets

    The cockpit never mutates production code. All mutations go through
    the Agent Arena Bridge.
    """

    def __init__(self, repo_root: str | Path = ".") -> None:
        self.repo_root = Path(repo_root).resolve()

    # ------------------------------------------------------------------
    # Intent ingestion
    # ------------------------------------------------------------------

    def ingest_intent(self, path_or_text: str, skip_grounding: bool = False) -> dict[str, Any]:
        """Ingest an intent document and compile it into an IntentPacket."""
        from aura_intent_ingestion import parse_intent_document, compile_intent_packet
        parsed = parse_intent_document(path_or_text, repo_root=self.repo_root)
        if not parsed.get("ok"):
            return parsed
        packet = compile_intent_packet(parsed, repo_root=self.repo_root, skip_grounding=skip_grounding)
        return packet

    def validate_lexc_route(self, path_or_text: str) -> dict[str, Any]:
        """Validate the LEXC route from an intent document."""
        from aura_intent_ingestion import parse_intent_document, route_intent_to_lexc
        parsed = parse_intent_document(path_or_text, repo_root=self.repo_root)
        return route_intent_to_lexc(parsed, repo_root=self.repo_root)

    # ------------------------------------------------------------------
    # Capability connectome
    # ------------------------------------------------------------------

    def capability_connectome(self) -> dict[str, Any]:
        """Build the full capability connectome."""
        from aura_capability_connectome import build_capability_connectome
        return build_capability_connectome(repo_root=self.repo_root)

    def capability_path(self, objective: str) -> dict[str, Any]:
        """Find the capability path for an objective."""
        from aura_capability_connectome import find_capability_path
        return find_capability_path(objective, repo_root=self.repo_root)

    def explain_capability(self, capability_id: str) -> dict[str, Any]:
        """Explain a single capability in detail."""
        from aura_capability_connectome import explain_capability
        return explain_capability(capability_id, repo_root=self.repo_root)

    # ------------------------------------------------------------------
    # Token economy
    # ------------------------------------------------------------------

    def token_economy(self, objective: str, files: list[str]) -> dict[str, Any]:
        """Compute a token economy report."""
        from aura_token_economy_orchestrator import compute_token_economy
        return compute_token_economy(objective, files, repo_root=self.repo_root)

    # ------------------------------------------------------------------
    # Workflow gates
    # ------------------------------------------------------------------

    def workflow_gates(self) -> dict[str, Any]:
        """Return the full workflow state machine."""
        from aura_workflow_gates import workflow_state_machine
        return workflow_state_machine()

    def evaluate_gate(self, state: str, evidence: dict) -> dict[str, Any]:
        """Evaluate whether a workflow gate's requirements are met."""
        from aura_workflow_gates import evaluate_gate as _evaluate
        return _evaluate(state, evidence)

    # ------------------------------------------------------------------
    # Grounding
    # ------------------------------------------------------------------

    def ground_intent(self, objective: str, target_symbol: str | None = None) -> dict[str, Any]:
        """Ground an intent through Coding Arena Grounding."""
        try:
            from aura_coding_arena_grounding import ground_coding_arena_intent
            return ground_coding_arena_intent(objective, self.repo_root, target_symbol)
        except Exception as exc:
            return {
                "ok": False,
                "error": f"Grounding failed: {exc}",
                "grounding_ok": False,
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }

    # ------------------------------------------------------------------
    # Hermes contract / handoff
    # ------------------------------------------------------------------

    def hermes_contract(self, objective: str, mode: str = "pr") -> dict[str, Any]:
        """Generate a Hermes operating contract."""
        from aura_hermes_arena_mode import generate_hermes_contract
        return generate_hermes_contract(objective, mode=mode, repo_root=self.repo_root)

    def prepare_handoff(self, intent_packet: dict, agent: str = "hermes") -> dict[str, Any]:
        """Prepare an agent handoff packet from an IntentPacket."""
        from aura_intent_ingestion import intent_to_agent_handoff
        return intent_to_agent_handoff(intent_packet, agent=agent, repo_root=self.repo_root)

    # ------------------------------------------------------------------
    # Cockpit contract
    # ------------------------------------------------------------------

    def cockpit_contract(self, objective: str) -> dict[str, Any]:
        """Generate a native cockpit contract for an objective.

        This is the main entry point for a human who wants to understand
        how Aura will handle their objective.
        """
        # Ingest the objective as a plain text intent
        from aura_intent_ingestion import compile_intent_packet
        packet = compile_intent_packet(objective, repo_root=self.repo_root, skip_grounding=True)

        # Get capability path
        from aura_capability_connectome import find_capability_path
        cap_path = find_capability_path(objective, repo_root=self.repo_root)

        # Get token economy
        likely_files = packet.get("likely_files", [])[:3]
        from aura_token_economy_orchestrator import compute_token_economy
        economy = compute_token_economy(objective, likely_files, repo_root=self.repo_root)

        # Get workflow gates
        from aura_workflow_gates import workflow_state_machine
        gates = workflow_state_machine()

        # Build the contract
        contract_lines: list[str] = []
        contract_lines.append("# Aura Native Cockpit Contract")
        contract_lines.append("")
        contract_lines.append(f"**Objective:** {objective}")
        contract_lines.append(f"**Cockpit Version:** {COCKPIT_VERSION}")
        contract_lines.append("")
        contract_lines.append("## Polysynthetic Packet")
        contract_lines.append(f"```\n{packet.get('polysynthetic_packet', '')}\n```")
        contract_lines.append("")
        contract_lines.append("## Routing")
        route_decision = packet.get("route_decision", {})
        contract_lines.append(f"- Route: {route_decision.get('route', 'unknown')}")
        contract_lines.append(f"- Reason: {route_decision.get('reason', '')}")
        contract_lines.append(f"- Next state: {route_decision.get('next_state', '')}")
        contract_lines.append("")
        contract_lines.append("## Grounding")
        grounding = packet.get("grounding", {})
        contract_lines.append(f"- Grounding OK: {grounding.get('grounding_ok', False)}")
        contract_lines.append(f"- Route: {grounding.get('route', '')}")
        if grounding.get("target_file"):
            contract_lines.append(f"- Target file: {grounding['target_file']}")
        contract_lines.append("")
        contract_lines.append("## Likely Files")
        for fp in packet.get("likely_files", [])[:5]:
            contract_lines.append(f"- {fp}")
        contract_lines.append("")
        contract_lines.append("## Likely Symbols")
        for sym in packet.get("likely_symbols", [])[:5]:
            contract_lines.append(f"- {sym}")
        contract_lines.append("")
        contract_lines.append("## Capability Path")
        for cap in cap_path.get("recommended_capabilities", [])[:5]:
            contract_lines.append(f"- {cap.get('name', '')} ({cap.get('token_savings_role', '')})")
        contract_lines.append("")
        contract_lines.append("## Token Economy")
        contract_lines.append(f"- Raw tokens: {economy.get('raw_prompt_tokens_est', 0) + economy.get('raw_file_tokens_est', 0):,}")
        contract_lines.append(f"- Aura tokens: {economy.get('total_aura_tokens_est', 0):,}")
        contract_lines.append(f"- Savings: {economy.get('estimated_percent_saved', 0)}%")
        contract_lines.append(f"- Cost saved: ${economy.get('estimated_cost_saved_usd', 0):.6f}")
        contract_lines.append("")
        contract_lines.append("## Savings Sources")
        for source in economy.get("savings_sources", []):
            contract_lines.append(f"- {source}")
        contract_lines.append("")
        contract_lines.append("## Workflow Checkpoints")
        contract_lines.append(f"- Total states: {gates.get('state_count', 0)}")
        contract_lines.append("- Human approval required at: HUMAN_APPROVED_FOR_AGENT, HUMAN_APPROVED_FOR_COMMIT, PR_READY")
        contract_lines.append("")
        contract_lines.append("## Invariants")
        contract_lines.append(f"- patch_authority: `{PATCH_AUTHORITY}`")
        contract_lines.append(f"- vsa_patch_authority: `{VSA_PATCH_AUTHORITY}`")
        contract_lines.append("- JSpace, VSA, ST3GG, DREAM-lite, QDKT are advisory only")
        contract_lines.append("- No production mutation from cockpit commands")
        contract_lines.append("")

        contract = "\n".join(contract_lines)

        return {
            "ok": packet.get("ok", False),
            "version": COCKPIT_VERSION,
            "objective": objective,
            "contract": contract,
            "intent_packet": packet,
            "capability_path": cap_path,
            "token_economy": economy,
            "workflow_gates": gates,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    # ------------------------------------------------------------------
    # Diagnose / inspect
    # ------------------------------------------------------------------

    def diagnose_selection(self, node_id: str) -> dict[str, Any]:
        """Diagnose a selected topology node through the Node Inspector."""
        try:
            from aura_node_inspector import inspect_node
            pkt = inspect_node(node_id, repo_root=self.repo_root)
            return {
                "ok": True,
                "node_intelligence": pkt.to_dict(),
                "truth_packet": pkt.to_truth_packet(),
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }
        except Exception as exc:
            return {
                "ok": False,
                "error": f"Node inspection failed: {exc}",
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }

    # ------------------------------------------------------------------
    # Emergent capability audit
    # ------------------------------------------------------------------

    def emergent_audit(self, objective: str) -> dict[str, Any]:
        """Run an emergent capability audit for an objective."""
        try:
            from aura_coding_arena_grounding import query_coding_arena_capability_audit
            return query_coding_arena_capability_audit(objective, self.repo_root)
        except Exception as exc:
            return {
                "ok": False,
                "error": f"Emergent audit failed: {exc}",
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }

    # ------------------------------------------------------------------
    # External call investigation
    # ------------------------------------------------------------------

    def investigate_external_calls(self, objective: str) -> dict[str, Any]:
        """Investigate external API/subprocess calls related to an objective."""
        try:
            from aura_coding_arena_grounding import query_coding_arena_external_calls
            return query_coding_arena_external_calls(objective, self.repo_root)
        except Exception as exc:
            return {
                "ok": False,
                "error": f"External call investigation failed: {exc}",
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }
