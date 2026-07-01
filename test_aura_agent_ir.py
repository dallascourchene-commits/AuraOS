import pytest
from aura_agent_ir import IRFloor, AgentIRNode, MorphologyIRBridge, AURA_AGENT_IR_V1
from aura_agent_ir_compiler import AgentIRCompiler


def test_morphology_to_ir_bridge_preserves_slots() -> None:
    """Verifies that the bridge map correctly translates morphological coordinates without modifying them."""
    morph_packet = {
        "DIR": "PATCH",
        "ASP": "STAGED",
        "CLASS": "CODE_SYMBOL",
        "SUBJ": "cheap_builder",
        "VOICE": "VERIFIER_MEDIATED",
        "STEM": "TokenEncoder",
    }
    
    bridge = MorphologyIRBridge.bridge_packet(morph_packet, IRFloor.SPEC)
    
    assert bridge["morphology"] == morph_packet
    assert bridge["ir_floor"] == IRFloor.SPEC.value
    assert bridge["version"] == AURA_AGENT_IR_V1

    # Verify invalid slot is rejected
    invalid_packet = {"INVALID_SLOT": "DATA"}
    with pytest.raises(ValueError, match="Invalid morphological slot"):
        MorphologyIRBridge.bridge_packet(invalid_packet, IRFloor.SPEC)


def test_ir_floor_does_not_overwrite_morphology_slot() -> None:
    """Asserts that promoting a node's IR floor does not interfere with the underlying slot mapping."""
    morph_packet = {
        "DIR": "PATCH",
        "ASP": "PROPOSED",
        "CLASS": "CODE_SYMBOL",
        "SUBJ": "cheap_builder",
        "VOICE": "CPU_ONLY",
        "STEM": "VerifierGate",
    }
    
    bridge = MorphologyIRBridge.bridge_packet(morph_packet, IRFloor.TEXT)
    
    # Simulate promotion in AgentIRCompiler
    node = AgentIRNode(node_id="test_node", floor=IRFloor.TEXT, payload={"bridge": bridge})
    
    promoted = AgentIRCompiler.promote(node, IRFloor.TYPED, {"status": "promoted"})
    
    # Assert promoted node has new floor
    assert promoted.floor == IRFloor.TYPED
    
    # Assert the underlying bridge morph slots are untouched
    underlying_bridge = promoted.payload["bridge"]
    assert underlying_bridge["morphology"] == morph_packet
    assert underlying_bridge["ir_floor"] == IRFloor.TEXT.value  # keeps original text tag in bridge, or is bridged separately
