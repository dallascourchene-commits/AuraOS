from __future__ import annotations

from copy import deepcopy

from aura_coding_waboose_breadboard import compile_waboose_breadboard, compile_relationship_breadboard
from aura_relationship_contracts import (
    AuthorityPosture, CompatibilityOutcome, InterfaceActor, InterfaceBoundary,
    InterfaceDataClass, InterfaceLifecycle, InterfaceOperation, InterfacePortCardinality,
    InterfacePortDirection, InterfaceResourceClass, ProofStatus, RelationshipDomain,
    RelationshipInterfaceSpec, RepositoryIdentity, ResourceBudget, SixSlotProjection,
    SourceReference, TruthClass, RelationshipContract, evaluate_typed_relationship_compatibility,
)


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


def _fully_resolved_contract() -> dict:
    contract = deepcopy(_contract())
    contract["focus_directives"][1]["target_patterns"] = ["core.py"]
    return contract


def test_breadboard_compiles_typed_proposal_only_components() -> None:
    packet = compile_waboose_breadboard(_contract())

    assert packet["ok"] is True
    assert packet["circuit_status"] == "DIAGNOSTIC_CIRCUIT_WITH_EXPLICIT_MOCKS"
    assert packet["has_explicit_mocks"] is True
    assert packet["repair_handoff_eligible"] is False
    assert packet["board"]["arena_id"] == "coding_waboose"
    assert len(packet["board"]["actions"]) == 2
    assert packet["authority"]["execution_authority"] is False
    assert packet["authority"]["patch_authority"] is False
    assert packet["authority"]["automatic_merge"] is False
    assert all(action["proposal_only"] is True for action in packet["board"]["actions"])
    assert all(action["authority_requirement"] == "NONE" for action in packet["board"]["actions"])
    assert packet["continuity"]["highest_contiguous_level"] == "BC2_CONSTRAINED"
    assert packet["continuity"]["continuity_complete"] is False


def test_missing_target_is_explicitly_mocked_not_invented() -> None:
    packet = compile_waboose_breadboard(_contract())
    authority = next(
        item for item in packet["components"] if item["directive_id"] == "FOCUS-AUTHORITY"
    )

    assert authority["mocked_input_refs"] == [
        "mock:FOCUS-AUTHORITY:unresolved_impact_target"
    ]
    assert authority["status"] == "MOCKED_LOCALLY_VALID_UNPOWERED"
    assert authority["continuity"] == "BC2_CONSTRAINED"
    assert authority["energized"] is False


def test_energizing_one_focus_does_not_ground_an_unresolved_mock() -> None:
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

    assert packet["circuit_status"] == "PARTIALLY_ENERGIZED_WITH_EXPLICIT_MOCKS"
    assert packet_focus["energized"] is True
    assert packet_focus["status"] == "VERIFIED_DIAGNOSTIC_COMPONENT"
    assert authority_focus["energized"] is False
    assert packet["repair_handoff_eligible"] is False
    assert packet["authority"]["automatic_fix"] is False
    assert packet["authority"]["automatic_pull_request"] is False


def test_energizing_mocked_focus_remains_below_grounded_proof() -> None:
    packet = compile_waboose_breadboard(
        _contract(),
        energized_directive_ids=["FOCUS-PACKETS", "FOCUS-AUTHORITY"],
        phase="FINALIZE",
    )
    authority_focus = next(
        item for item in packet["components"] if item["directive_id"] == "FOCUS-AUTHORITY"
    )

    assert packet["circuit_status"] == "PARTIALLY_ENERGIZED_WITH_EXPLICIT_MOCKS"
    assert packet["continuity"]["highest_contiguous_level"] == "BC2_CONSTRAINED"
    assert packet["continuity"]["continuity_complete"] is False
    assert authority_focus["status"] == "ENERGIZED_WITH_EXPLICIT_MOCKS"
    assert packet["repair_handoff_eligible"] is False


def test_all_resolved_focus_receipts_reach_bc5_without_execution_grant() -> None:
    packet = compile_waboose_breadboard(
        _fully_resolved_contract(),
        energized_directive_ids=["FOCUS-PACKETS", "FOCUS-AUTHORITY"],
        phase="FINALIZE",
    )

    assert packet["circuit_status"] == "VERIFIED_DIAGNOSTIC_CIRCUIT"
    assert packet["has_explicit_mocks"] is False
    assert packet["repair_handoff_eligible"] is True
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
    assert "resolved_non_mocked_impact_or_control_flow_evidence" in backward
    assert "human_review_decision" in backward



def _relationship_contract_fixture() -> RelationshipContract:
    return RelationshipContract.create(
        objective_digest="objective-digest",
        intent_packet_digest="intent-digest",
        source_repository=RepositoryIdentity(
            repo_head="head-sha",
            working_tree_digest="tree-digest",
            relational_index_digest="index-digest",
            atlas_digest="atlas-digest",
        ),
        domain=RelationshipDomain.CODE,
        slots=SixSlotProjection.from_mapping(
            {"DIR": "IN", "ASP": "GROUND", "CLASS": "REVIEW", "SUBJ": "RELATION", "VOICE": "HUMAN_AGENT", "STEM": "INSPECT"}
        ),
        truth_class=TruthClass.EXACT_SOURCE,
        authority_posture=AuthorityPosture.PROPOSAL_ONLY,
        proof_status=ProofStatus.GROUNDED,
        policy_scope=("coding_arena",),
        resource_budget=ResourceBudget(),
        source_refs=(
            SourceReference(
                file_path="aura_example.py",
                symbol="compile",
                line_start=1,
                line_end=2,
                source_hash="a" * 64,
                file_source_hash="b" * 64,
            ),
        ),
    )


def _relationship_interface(direction: InterfacePortDirection) -> RelationshipInterfaceSpec:
    return RelationshipInterfaceSpec.create(
        port_name="relationship_packet",
        direction=direction,
        cardinality=InterfacePortCardinality.ONE,
        lifecycle=InterfaceLifecycle.SESSION,
        actor=InterfaceActor.SYSTEM,
        boundary=InterfaceBoundary.SAME_ARENA,
        resource_class=InterfaceResourceClass.CODE,
        data_class=InterfaceDataClass.CONTRACT,
        operation=InterfaceOperation.VALIDATE,
    )


def test_relationship_breadboard_projects_typed_preflight_without_authority() -> None:
    left = _relationship_contract_fixture()
    right = _relationship_contract_fixture()
    left_interface = _relationship_interface(InterfacePortDirection.OUTPUT)
    right_interface = _relationship_interface(InterfacePortDirection.INPUT)
    assessment = evaluate_typed_relationship_compatibility(
        left,
        right,
        left_interface=left_interface,
        right_interface=right_interface,
    )
    packet = compile_relationship_breadboard(
        objective="Validate relationship compatibility",
        left_contract=left,
        right_contract=right,
        left_interface=left_interface,
        right_interface=right_interface,
        assessment=assessment,
    )
    assert packet["compatibility"]["outcome"] == CompatibilityOutcome.COMPATIBLE.value
    assert packet["machine_status"]["preflight_ready"] is True
    assert packet["planning_board"]["actions"][0]["proposal_only"] is True
    assert packet["authority"]["execution_authority"] is False
    assert packet["authority"]["automatic_merge"] is False
