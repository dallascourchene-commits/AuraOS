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

from typing import Dict, List, Any, Mapping

from aura_event_contracts import PATCH_AUTHORITY, VSA_PATCH_AUTHORITY, stable_digest
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
    def compile_compass_act_capsules(cls, capsule_packet: Mapping[str, Any]) -> Dict[str, Any]:
        """Compile proposal-only Compass Act Capsules to SPEC-floor Agent IR nodes."""
        if not isinstance(capsule_packet, Mapping) or not capsule_packet.get("ok"):
            raise ValueError("Agent IR requires a valid Compass capsule packet")
        capsules = [dict(item) for item in capsule_packet.get("act_capsules", ()) or () if isinstance(item, Mapping)]
        if not capsules:
            raise ValueError("Agent IR requires at least one Compass Act Capsule")
        nodes: List[AgentIRNode] = []
        for capsule in capsules:
            required = ("task_id", "phase_id", "target_file", "source_span", "declared_tests", "capsule_digest")
            missing = [key for key in required if not capsule.get(key)]
            if missing:
                raise ValueError(f"Compass capsule missing Agent IR fields: {sorted(missing)}")
            supplied_digest = str(capsule.get("capsule_digest") or "")
            digest_body = dict(capsule)
            digest_body.pop("capsule_digest", None)
            if supplied_digest != stable_digest(digest_body):
                raise ValueError("Compass capsule digest mismatch")
            forbidden = (
                not capsule.get("proposal_only")
                or capsule.get("safe_to_patch")
                or capsule.get("automatic_commit")
                or capsule.get("automatic_pull_request")
                or capsule.get("automatic_merge")
                or capsule.get("patch_authority") != PATCH_AUTHORITY
                or bool(capsule.get("vsa_patch_authority")) != VSA_PATCH_AUTHORITY
            )
            if forbidden:
                raise ValueError("Compass capsule carries forbidden authority")
            source_span = capsule.get("source_span")
            if not isinstance(source_span, Mapping) or not str(source_span.get("source_hash") or ""):
                raise ValueError("Compass capsule source span is not exact")
            declared_tests = capsule.get("declared_tests")
            if isinstance(declared_tests, (str, bytes, bytearray)) or not declared_tests:
                raise ValueError("Compass capsule declared tests are not canonical")
            payload = {
                "capsule_digest": capsule["capsule_digest"],
                "phase_id": capsule.get("phase_id"),
                "target_file": capsule["target_file"],
                "target_symbol": capsule.get("target_symbol"),
                "source_span": dict(source_span),
                "declared_tests": list(declared_tests),
                "surgeon_request": dict(capsule.get("surgeon_request") or {}),
                "proposal_only": True,
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }
            nodes.append(
                AgentIRNode(
                    node_id=f"air_{stable_digest({'task_id': capsule['task_id'], 'capsule_digest': capsule['capsule_digest']}, digest_size=12)}",
                    floor=IRFloor.SPEC,
                    payload=payload,
                )
            )
        result = {
            "ok": True,
            "version": AURA_AGENT_IR_V1,
            "floor": IRFloor.SPEC.value,
            "nodes": [
                {
                    "node_id": node.node_id,
                    "floor": node.floor.value,
                    "payload": node.payload,
                    "effect": node.effect.value,
                    "version": node.version,
                }
                for node in nodes
            ],
            "proposal_only": True,
            "safe_to_patch": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        result["agent_ir_digest"] = stable_digest(result)
        return result

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
