"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9b5-[Q-SYS:TOPOLOGY_ACTION_ROUTER]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Gated Execution)
DEPENDENCIES: __future__, typing, aura_scene_graph_schema, aura_topology_state_machine
FUNCTIONS: AuraTopologyActionRouter, route_action
SYNOPSIS: Evaluates client actions against graph snapshots to yield transition envelopes without mutating disk state.
[/AURA_MASTER_KEY]
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
from aura_scene_graph_schema import SceneGraphSnapshot
from aura_topology_state_machine import TopologyStateMachine


class AuraTopologyActionRouter:
    """
    Exposes non-mutating operational routing logic.
    Determines if actions are safe to stage and generates requests/intent envelopes.
    """

    def __init__(self, codemap_engine: Any = None, graphify_engine: Any = None, shadow_verifier: Any = None):
        self.codemap = codemap_engine
        self.graphify = graphify_engine
        self.shadow = shadow_verifier

    def route_action(
        self, snapshot: SceneGraphSnapshot, action: str, payload: Dict[str, Any]
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        node_id = payload.get("node_id")
        if not node_id or node_id not in snapshot.nodes:
            return False, f"Error: Node {node_id} is missing from the active snapshot.", None

        target_node = snapshot.nodes[node_id]
        
        # Derive active allowed/forbidden lists on the fly to enforce safety
        allowed, forbidden = TopologyStateMachine.derive_gates(target_node)
        
        if action not in allowed or action in forbidden:
            return False, f"Security Violation: Action {action} is locked for {node_id}.", None

        if action == "reground_symbol":
            symbol_name = payload.get("symbol_name", "")
            
            # Check codemap exact search
            if self.codemap and hasattr(self.codemap, "exact_lookup"):
                ref = self.codemap.exact_lookup(symbol_name)
                if ref:
                    return True, "Resolved: Exact AST match found.", {"target": ref, "strategy": "EXACT"}

            # Check graphify fuzzy/semantic proximity match
            if self.graphify and hasattr(self.graphify, "find_semantic_neighbors"):
                neighbors = self.graphify.find_semantic_neighbors(symbol_name)
                if neighbors:
                    return True, "Resolved: Proximity match found via Graphify.", {"candidates": neighbors, "strategy": "FUZZY"}

            # Check shadow verifier for hallucination risks
            if self.shadow and hasattr(self.shadow, "analyze_hallucination_risk"):
                is_hallucinated = self.shadow.analyze_hallucination_risk(symbol_name)
                if is_hallucinated:
                    return True, "Blocked: Unverifiable symbol detected.", {
                        "strategy": "PROPOSAL_ONLY_CAPSULE",
                        "reason": "High probability of model hallucination."
                    }
            
            return False, f"Regrounding failed for symbol: {symbol_name}", None

        if action == "request_lease":
            return True, "Success: Lease transaction envelope emitted.", {
                "intent": "LeaseRequest",
                "source_ref_digest": target_node.source_ref.digest
            }

        if action == "stage_action_capsule":
            return True, "Success: Action execution capsule staged for verification.", {
                "intent": "ActionCapsuleRequest",
                "patch_hash": payload.get("patch_hash")
            }

        if action == "run_verifier":
            return True, "Success: External test execution requested.", {
                "intent": "VerifierRunRequest",
                "target_capsule": payload.get("capsule_id")
            }

        return False, f"Unhandled action parameter: {action}", None
