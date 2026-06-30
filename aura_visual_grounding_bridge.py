"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9b5-[Q-SYS:VISUAL_GROUNDING_BRIDGE]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Visual Grounding)
DEPENDENCIES: __future__, typing, aura_scene_graph_schema
FUNCTIONS: AuraVisualGroundingBridge, export_interaction_frame
SYNOPSIS: Provides coordinate-free visual interface packages mapping unique node IDs and concept hashes.
[/AURA_MASTER_KEY]
"""
from __future__ import annotations

from typing import Any, Dict, List
from aura_scene_graph_schema import SceneGraphSnapshot


class AuraVisualGroundingBridge:
    """
    Bridge enabling coordinate-free visual grounding, mapping unique node IDs
    and concept hashes to allow LLM agents to target graph components reliably.
    """

    @staticmethod
    def export_interaction_frame(
        snapshot: SceneGraphSnapshot, rendered_image_path: str, action_history: List[str]
    ) -> Dict[str, Any]:
        schema_actions = {}
        serialized_nodes = {}

        for n_id, node in snapshot.nodes.items():
            serialized_nodes[n_id] = {
                "id": node.node_id,
                "type": node.node_type,
                "shape": node.shape,
                "color": node.color,
                "luminance": node.luminance,
                "concept_vector_hash": node.concept_vector_hash,
                "hardware_target": node.hardware_profile.preferred_device
            }
            
            # Dynamically resolve allowed and forbidden lists on the fly
            from aura_topology_state_machine import TopologyStateMachine
            allowed, forbidden = TopologyStateMachine.derive_gates(node)
            
            schema_actions[n_id] = {
                "allowed": allowed,
                "forbidden": forbidden
            }

        return {
            "ui_context_screenshot_frame": rendered_image_path,
            "scene_graph_truth": {
                "snapshot_id": snapshot.snapshot_id,
                "nodes": serialized_nodes,
                "density": snapshot.topology_density_score
            },
            "grounding_action_schema": schema_actions,
            "coordinate_free_target_mapping": {
                "selection_protocol": "by_unique_node_id_and_concept_hash",
                "requires_xy_coordinates": False
            },
            "action_history_trace": action_history,
            "visual_history_token_depth": len(snapshot.nodes)
        }
