from __future__ import annotations

from aura_coding_waboose_breadboard import compile_waboose_breadboard


def _contract() -> dict:
    return {
        "contract_id": "contract-1234567890abcdef",
        "request_digest": "request-1234567890abcdef",
        "diff_digest": "diff-1234567890abcdef",
        "objective": "Review malformed packet handling and caller compatibility",
        "changed_files": ["core.py"],
        "impact_slice": [
            {
                "node_id": "core.py::guarded",
                "file": "core.py",
                "symbol": "guarded",
                "kind": "function",
                "edge_kind": "changed",
                "direction": "changed",
            },
            {
                "node_id": "caller.py::use_guarded",
                "file": "caller.py",
                "symbol": "use_guarded",
                "kind": "function",
                "edge_kind": "call",
                "direction": "caller_or_dependent",
            },
        ],
        "focus_directives": [
            {
                "directive_id": "FOCUS-PACKETS",
                "name": "fail_closed_packets",
                "question": "Can a malformed packet preserve stale success state?",
                "risk": "correctness",
                "direction": "callees",
                "target_patterns": ["guarded", "packet"],
                "required_evidence": ["exact_source", "malformed_packet"],
                "suggested_tools": ["pytest"],
            },
            {
                "directive_id": "FOCUS-AUTHORITY",
                "name": "authority_non_mutation",
                "question": "Can any review path mutate production or merge?",
                "risk": "authority",
                "direction": "both",
                "target_patterns": ["automatic_merge"],
                "required_evidence": ["contract_invariant"],
                "suggested_tools": [],
            },
        ],
    }


def test_breadboard_compiles_typed_proposal_only_components() -> None:
    packet = compile_waboose_breadboard(_contract())

    assert packet["ok"] is True
    assert packet["circuit_status"] == "GROUNDED_DIAGNOSTIC_CIRCUIT_UNPOWERED"
    assert packet["board"]["arena_id"] == "coding_waboose"
    assert len(packet["board"]["actions"]) == 2
    assert packet["authority"]["execution_authority"] is False
    assert packet["authority"]["patch_authority"] is False
    assert packet["authority"]["automatic_merge"] is False
    assert all(action["proposal_only"] is True for action in packet["board"]["actions"])
    assert all(action["authority_requirement"] == "NONE" for action in packet["board"]["actions"])
    assert packet["continuity"]["highest_contiguous_level"] == "BC4_AUTHORIZED"
    assert packet["continuity"]["continuity_complete"] is False


def test_missing_target_is_explicitly_mocked_not_invented() -> None:
    packet = compile_waboose_breadboard(_contract())
    authority = next(
        item for item in packet["components"] if item["directive_id"] == "FOCUS-AUTHORITY"
    )

    assert authority["mocked_input_refs"] == [
        "mock:FOCUS-AUTHORITY:unresolved_impact_target"
    ]
    assert authority["status"] == "MOCKED_GROUNDED_UNPOWERED"
    assert authority["energized"] is False


def test_energizing_one_focus_creates_receipts_without_authority() -> None:
    packet = compile_waboose_breadboard(
        _contract(),
        energized_directive_ids=["FOCUS-PACKETS"],
        phase="SCAN",
    )
    packet_focus = next(
        item for item in packet["components"] if item["directive_id"] == "FOCUS-PACKETS"
    )
    authority_focus = next(
        item for item in packet["components"] if item["directive_id"] == "FOCUS-AUTHORITY"
    )

    assert packet["circuit_status"] == "PARTIALLY_ENERGIZED_DIAGNOSTIC_CIRCUIT"
    assert packet_focus["energized"] is True
    assert packet_focus["status"] == "VERIFIED_DIAGNOSTIC_COMPONENT"
    assert authority_focus["energized"] is False
    assert packet["authority"]["automatic_fix"] is False
    assert packet["authority"]["automatic_pull_request"] is False


def test_all_focus_receipts_reach_bc5_without_execution_grant() -> None:
    packet = compile_waboose_breadboard(
        _contract(),
        energized_directive_ids=["FOCUS-PACKETS", "FOCUS-AUTHORITY"],
        phase="FINALIZE",
    )

    assert packet["circuit_status"] == "VERIFIED_DIAGNOSTIC_CIRCUIT"
    assert packet["continuity"]["highest_contiguous_level"] == "BC5_VERIFIED"
    assert packet["continuity"]["continuity_complete"] is True
    assert packet["authority"]["execution_authority"] is False
    assert packet["authority"]["human_authorizes"] is True


def test_forward_and_backward_paths_preserve_circuit_semantics() -> None:
    packet = compile_waboose_breadboard(_contract())

    forward = packet["forward_simulation"][0]["path"]
    backward = packet["backward_proof_requirements"][0]["required_for_repair_handoff"]
    assert forward[0].startswith("source:core.py#diff:")
    assert any(item.startswith("topology:") for item in forward)
    assert any(item.startswith("action:waboose_action_") for item in forward)
    assert "human_review_decision" in backward
