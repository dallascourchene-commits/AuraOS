"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9b5-[Q-SYS:AGENT_IR]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Compilation Bridge)
DEPENDENCIES: __future__, dataclasses, enum, typing
FUNCTIONS: IRFloor, EffectType, AgentIRNode, MorphologyIRBridge
SYNOPSIS: Defines the Agent IR floors, effect annotations, and morphological bridge mapping for compilation promotions.
[/AURA_MASTER_KEY]
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict

AURA_AGENT_IR_V1 = "AURA_AGENT_IR_V1"


class IRFloor(str, Enum):
    TEXT = "TEXT"
    TYPED = "TYPED"
    SPEC = "SPEC"
    STUB = "STUB"
    SHIM = "SHIM"
    PURE = "PURE"


class EffectType(str, Enum):
    IO = "IO"
    CPU = "CPU"
    MEM = "MEM"
    NET = "NET"


@dataclass(frozen=True)
class AgentIRNode:
    node_id: str
    floor: IRFloor
    payload: Dict[str, Any] = field(default_factory=dict)
    effect: EffectType = EffectType.CPU
    version: str = AURA_AGENT_IR_V1


class MorphologyIRBridge:
    """
    Decoupled bridge mapping morphological slot intent-routing coordinates
    to implementation maturity floors (IR floors).
    """

    # Slot mappings to categories
    SLOT_MAP = {
        "DIR": "orientation/action direction",
        "ASP": "lifecycle/phase/temporal aspect",
        "CLASS": "domain class/object class/operation class",
        "SUBJ": "actor/owner/target agent",
        "VOICE": "agency mode/active-passive-reflexive/tool mediation",
        "STEM": "executable semantic root",
    }

    # IR Floor definitions
    IR_FLOORS = {
        IRFloor.TEXT: "raw expression",
        IRFloor.TYPED: "slot-typed intent",
        IRFloor.SPEC: "formal contract",
        IRFloor.STUB: "interface skeleton",
        IRFloor.SHIM: "adapter/bridge",
        IRFloor.PURE: "verified deterministic implementation",
    }

    @classmethod
    def bridge_packet(cls, morphology_packet: Dict[str, str], ir_floor: IRFloor) -> Dict[str, Any]:
        """Creates a bridge object linking a morphological packet to an IR floor."""
        validated_morphology = {}
        for slot, val in morphology_packet.items():
            if slot not in cls.SLOT_MAP:
                raise ValueError(f"Invalid morphological slot: {slot}")
            validated_morphology[slot] = val

        return {
            "morphology": validated_morphology,
            "ir_floor": ir_floor.value,
            "version": AURA_AGENT_IR_V1
        }
