"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9b5-[Q-SYS:AGENT_IR_COMPILER]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Compilation Promotion)
DEPENDENCIES: __future__, typing, aura_agent_ir
FUNCTIONS: AgentIRCompiler, promote_node, verify_path_coherence
SYNOPSIS: Manages stage promotion verification and compilation of compiler nodes from TEXT to PURE.
[/AURA_MASTER_KEY]
"""
from __future__ import annotations

from typing import Dict, List, Any
from aura_agent_ir import IRFloor, AgentIRNode, AURA_AGENT_IR_V1


class AgentIRCompiler:
    """
    Validates and promotes Agent IR nodes across maturation levels (floors).
    Ensures transitions respect strict partial order TEXT -> TYPED -> SPEC -> STUB -> SHIM -> PURE.
    """

    FLOOR_ORDER = [
        IRFloor.TEXT,
        IRFloor.TYPED,
        IRFloor.SPEC,
        IRFloor.STUB,
        IRFloor.SHIM,
        IRFloor.PURE,
    ]

    @classmethod
    def can_promote(cls, current_floor: IRFloor, target_floor: IRFloor) -> bool:
        """Checks if a transition between two floors is allowed."""
        try:
            curr_idx = cls.FLOOR_ORDER.index(current_floor)
            target_idx = cls.FLOOR_ORDER.index(target_floor)
            # Must promote strictly forward, usually step-by-step
            return target_idx > curr_idx
        except ValueError:
            return False

    @classmethod
    def promote(cls, node: AgentIRNode, target_floor: IRFloor, new_payload: Dict[str, Any]) -> AgentIRNode:
        """Promotes a node to a new floor, merging the new payload."""
        if not cls.can_promote(node.floor, target_floor):
            raise ValueError(f"Invalid IR promotion: cannot promote from {node.floor} to {target_floor}")

        merged_payload = node.payload.copy()
        merged_payload.update(new_payload)

        return AgentIRNode(
            node_id=node.node_id,
            floor=target_floor,
            payload=merged_payload,
            effect=node.effect
        )

    @classmethod
    def verify_path_coherence(cls, path: List[IRFloor]) -> bool:
        """Verifies that a list of floor transitions strictly respects maturation order."""
        if not path:
            return True
        prev_idx = -1
        for floor in path:
            try:
                curr_idx = cls.FLOOR_ORDER.index(floor)
                if curr_idx <= prev_idx:
                    return False
                prev_idx = curr_idx
            except ValueError:
                return False
        return True
