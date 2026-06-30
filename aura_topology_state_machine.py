"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9b5-[Q-SYS:TOPOLOGY_STATE_MACHINE]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Gating Controls)
DEPENDENCIES: __future__, typing, aura_scene_graph_schema
FUNCTIONS: TopologyStateMachine, derive_gates, resolve_visual_grammar
SYNOPSIS: Derives allowable transitions and visual attributes for topology nodes based on verification states.
[/AURA_MASTER_KEY]
"""
from __future__ import annotations

from typing import List, Tuple
from aura_scene_graph_schema import SceneNode


class TopologyStateMachine:
    """
    Derives valid operations and visual mapping for nodes based on their snapshot state.
    Blocked or ungrounded nodes are strictly forbidden from mutation paths.
    """

    @staticmethod
    def derive_gates(node: SceneNode) -> Tuple[List[str], List[str]]:
        """Determines valid operational paths (allowed, forbidden) purely from node state."""
        if node.missing_symbol_penalty > 0.0 or node.source_grounding_score <= 0.0:
            return (
                ["explain_node", "reground_symbol", "create_proposal_only"],
                ["request_lease", "stage_action_capsule", "run_verifier", "promote_patch"]
            )

        if node.status == "blocked":
            return (
                ["explain_node", "reground_symbol", "create_proposal_only", "add_test_plan"],
                ["request_lease", "stage_action_capsule", "promote_patch"]
            )

        if node.status == "proposed":
            return (
                ["explain_node", "request_lease", "add_test_plan"],
                ["stage_action_capsule", "run_verifier", "promote_patch"]
            )

        if node.status == "leased":
            return (
                ["explain_node", "stage_action_capsule"],
                ["run_verifier", "promote_patch"]
            )

        if node.status == "staged":
            return (
                ["explain_node", "run_verifier"],
                ["promote_patch", "stage_action_capsule"]
            )

        if node.status == "verified":
            return (
                ["explain_node", "request_human_approval"],
                ["stage_action_capsule", "direct_mutation"]
            )

        return (["explain_node"], ["stage_action_capsule", "promote_patch"])

    @staticmethod
    def resolve_visual_grammar(node: SceneNode) -> Tuple[str, str]:
        """Maps logical node type and status to visual representation primitives (shape, color)."""
        shape_map = {
            "file": "cube", "symbol": "sphere", "test": "pyramid",
            "sidecar": "cylinder", "verifier": "shield", "contract": "diamond",
            "capsule": "packet", "memory": "crystal"
        }
        shape = shape_map.get(node.node_type, "cube")

        if node.missing_symbol_penalty > 0.0 or node.status == "blocked":
            color = "red"
        elif node.status == "verified":
            color = "green"
        elif node.status == "leased":
            color = "blue"
        elif node.status == "staged":
            color = "cyan"
        elif node.luminance > 0.8:
            color = "gold"
        else:
            color = "grey"

        return shape, color
