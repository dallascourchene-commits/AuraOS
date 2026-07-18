from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from aura_polysynthetic_intent import PolysyntheticIntentPacket
from aura_relational_synthesis import (
    Freshness,
    ParticipantType,
    RelationalParticipant,
    RelationalSynthesisCapsule,
    RelationalSynthesisShadowCompiler,
    TruthClass,
    compile_relational_shadow_capsule,
)


OBJECTIVE = "Compile a read-only relational synthesis shadow capsule."


def _intent() -> PolysyntheticIntentPacket:
    return PolysyntheticIntentPacket.from_slots(
        {
            "DIR": "IN",
            "ASP": "GROUND",
            "CLASS": "REVIEW",
            "SUBJ": "REPOSITORY_RELATION",
            "VOICE": "HUMAN_AGENT",
            "STEM": "INSPECT",
        },
        adjuncts={
            "grounding": "exact_current_source",
            "risk": "proposal_only",
        },
        objective=OBJECTIVE,
    )


def _packet() -> dict:
    selected = [
        {
            "node_id": "request.py#method:Request.from_value:1111111111111111",
            "file_path": "request.py",
            "symbol": "from_value",
            "kind": "method",
            "line_start": 10,
            "line_end": 20,
            "source_hash": "1" * 64,
        },
        {
            "node_id": "request.py#function:_normalize_repo_path:2222222222222222",
            "file_path": "request.py",
            "symbol": "_normalize_repo_path",
            "kind": "function",
            "line_start": 30,
            "line_end": 35,
            "source_hash": "2" * 64,
        },
        {
            "node_id": "packet.py#function:_assemble_packet:3333333333333333",
            "file_path": "packet.py",
            "symbol": "_assemble_packet",
            "kind": "function",
            "line_start": 40,
            "line_end": 60,
            "source_hash": "3" * 64,
        },
        {
            "node_id": "tests/test_packet.py#function:test_scope_is_bounded:4444444444444444",
            "file_path": "tests/test_packet.py",
            "symbol": "test_scope_is_bounded",
            "kind": "function",
            "line_start": 5,
            "line_end": 15,
            "source_hash": "4" * 64,
        },
    ]
    slices = [
        {
            **item,
            "qualified_symbol": (
                "Request.from_value"
                if item["symbol"] == "from_value"
                else item["symbol"]
            ),
            "file_source_hash": {
                "request.py": "a" * 64,
                "packet.py": "b" * 64,
                "tests/test_packet.py": "c" * 64,
            }[item["file_path"]],
            "emitted_line_end": item["line_end"],
            "truncated": False,
        }
        for item in selected
    ]
    return {
        "ok": True,
        "version": "AURA_EMERGENT_EVIDENCE_SPINE_V1",
        "packet_id": "EMERGENT-RELATIONAL-FIXTURE",
        "packet_digest": "d" * 40,
        "status": "GROUNDED_ATOMIC_CLOSURE",
        "objective": OBJECTIVE,
        "target_arena": "coding_arena",
        "repo_head": "e" * 40,
        "grounding_ok": True,
        "approximate_only": False,
        "atomic_inventory": {
            "version": "AURA_ATOMIC_FUNCTION_INVENTORY_V1",
            "total_count": 4,
            "inventory_digest": "f" * 40,
            "selected_count": 4,
            "selected_atomic_functions": selected,
        },
        "capability_connectome": {
            "version": "AURA_CAPABILITY_CONNECTOME_V2",
            "graph_digest": "9" * 40,
            "node_count": 4,
            "edge_count": 3,
            "path": {"capability_path_digest": "8" * 40},
        },
        "seed_evidence": [],
        "dependency_edges": [
            {
                "src_id": selected[0]["node_id"],
                "dst_id": selected[1]["node_id"],
                "edge_type": "call",
                "evidence": "request.py:15 calls _normalize_repo_path",
                "confidence": 1.0,
            },
            {
                "src_id": selected[0]["node_id"],
                "dst_id": selected[2]["node_id"],
                "edge_type": "call",
                "evidence": "request.py:19 calls _assemble_packet",
                "confidence": 1.0,
            },
            {
                "src_id": selected[3]["node_id"],
                "dst_id": selected[2]["node_id"],
                "edge_type": "test",
                "evidence": "tests/test_packet.py:5 tests packet.py",
                "confidence": 1.0,
            },
        ],
        "source_slices": slices,
        "tests": ["tests/test_packet.py", "tests/test_unresolved.py"],
        "safe_to_patch": False,
        "production_mutation": False,
        "automatic_fix": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_pull_request": False,
        "automatic_merge": False,
        "human_review_required": True,
        "patch_authority": "exact_source_spans_and_hashes_only",
        "vsa_patch_authority": False,
    }


def _compile(packet: dict | None = None) -> RelationalSynthesisCapsule:
    value = packet or _packet()
    return RelationalSynthesisShadowCompiler().compile(
        value,
        intent_packet=_intent(),
        expected_repo_head=value["repo_head"],
        expected_packet_digest=value["packet_digest"],
        expected_inventory_digest=value["atomic_inventory"]["inventory_digest"],
    )


def test_shadow_compiler_is_deterministic_under_input_reordering() -> None:
    first = _packet()
    second = deepcopy(first)
    second["atomic_inventory"]["selected_atomic_functions"].reverse()
    second["source_slices"].reverse()
    second["dependency_edges"].reverse()
    second["tests"].reverse()

    one = _compile(first).to_dict()
    two = _compile(second).to_dict()

    assert one == two
    assert one["shadow_mode"] is True
    assert one["safe_to_patch"] is False
    assert one["production_mutation"] is False
    assert one["automatic_merge"] is False
    assert one["human_review_required"] is True


def test_qualified_symbol_identity_is_preserved() -> None:
    capsule = _compile()
    source_participants = [
        item
        for item in capsule.participants
        if item.participant_type is ParticipantType.ATOMIC_SYMBOL
    ]
    qualified = {item.qualified_symbol for item in source_participants}
    assert "Request.from_value" in qualified
    assert "from_value" not in qualified


def test_duplicate_participant_is_rejected_on_round_trip() -> None:
    data = _compile().to_dict()
    data["participants"].append(deepcopy(data["participants"][0]))
    with pytest.raises(ValueError, match="unique IDs"):
        RelationalSynthesisCapsule.from_dict(data)


def test_missing_relation_endpoint_fails_closed() -> None:
    packet = _packet()
    packet["dependency_edges"][0]["dst_id"] = "missing.py#function:nope:0"
    with pytest.raises(ValueError, match="endpoint is absent"):
        _compile(packet)


def test_exact_participant_requires_digest_and_evidence() -> None:
    unresolved = RelationalParticipant.create(
        participant_type=ParticipantType.TEST,
        role="unresolved_test_owner",
        truth_class=TruthClass.UNRESOLVED,
        canonical_owner="fixture",
        canonical_ref="tests/test_missing.py",
        digest=None,
        evidence_refs=("fixture",),
        freshness=Freshness.UNRESOLVED,
    )
    assert unresolved.truth_class is TruthClass.UNRESOLVED

    with pytest.raises(ValueError, match="exact participants require"):
        RelationalParticipant.create(
            participant_type=ParticipantType.TEST,
            role="test_owner",
            truth_class=TruthClass.EXACT_TEST,
            canonical_owner="fixture",
            canonical_ref="tests/test_missing.py#test_x",
            digest=None,
            evidence_refs=(),
            freshness=Freshness.CURRENT,
        )


def test_stale_repository_or_packet_digest_is_rejected() -> None:
    packet = _packet()
    compiler = RelationalSynthesisShadowCompiler()
    with pytest.raises(ValueError, match="stale evidence packet"):
        compiler.compile(
            packet,
            intent_packet=_intent(),
            expected_repo_head="0" * 40,
            expected_packet_digest=packet["packet_digest"],
            expected_inventory_digest=packet["atomic_inventory"]["inventory_digest"],
        )
    with pytest.raises(ValueError, match="packet digest mismatch"):
        compiler.compile(
            packet,
            intent_packet=_intent(),
            expected_repo_head=packet["repo_head"],
            expected_packet_digest="0" * 40,
            expected_inventory_digest=packet["atomic_inventory"]["inventory_digest"],
        )
    with pytest.raises(ValueError, match="inventory digest mismatch"):
        compiler.compile(
            packet,
            intent_packet=_intent(),
            expected_repo_head=packet["repo_head"],
            expected_packet_digest=packet["packet_digest"],
            expected_inventory_digest="0" * 40,
        )


def test_test_filename_without_callable_is_explicitly_unresolved() -> None:
    capsule = _compile()
    group = next(item for item in capsule.groups if item.purpose == "test_proof_ownership")
    assert group.boundary.omitted_relation_count == 2
    assert group.boundary.omitted_reasons == {
        "unresolved_test_callable_owner": 1,
        "unresolved_test_invariant": 1,
    }
    assert "test_callable_owner:tests/test_unresolved.py" in (
        group.boundary.unresolved_relations
    )
    assert any(
        item.startswith("proved_invariant:")
        for item in group.boundary.unresolved_relations
    )
    unresolved = [
        item
        for item in capsule.participants
        if item.canonical_ref == "tests/test_unresolved.py"
    ]
    assert len(unresolved) == 1
    assert unresolved[0].truth_class is TruthClass.UNRESOLVED


def test_schema_and_contract_round_trip() -> None:
    data = compile_relational_shadow_capsule(
        _packet(),
        intent_packet=_intent(),
        expected_repo_head="e" * 40,
        expected_packet_digest="d" * 40,
        expected_inventory_digest="f" * 40,
    )
    encoded = json.dumps(data, sort_keys=True)
    decoded = json.loads(encoded)
    restored = RelationalSynthesisCapsule.from_dict(decoded)
    assert restored.to_dict() == data

    schema_root = Path("schemas")
    participant_schema = json.loads(
        (schema_root / "aura_relational_participant.schema.json").read_text(
            encoding="utf-8"
        )
    )
    group_schema = json.loads(
        (schema_root / "aura_relational_group.schema.json").read_text(
            encoding="utf-8"
        )
    )
    capsule_schema = json.loads(
        (
            schema_root / "aura_relational_synthesis_capsule.schema.json"
        ).read_text(encoding="utf-8")
    )
    assert participant_schema["properties"]["schema_version"]["const"] == (
        "AURA_RELATIONAL_PARTICIPANT_V1"
    )
    assert group_schema["properties"]["schema_version"]["const"] == (
        "AURA_RELATIONAL_GROUP_V1"
    )
    assert capsule_schema["properties"]["schema_version"]["const"] == (
        "AURA_RELATIONAL_SYNTHESIS_CAPSULE_V1"
    )
    assert capsule_schema["properties"]["shadow_mode"]["const"] is True
    assert capsule_schema["properties"]["safe_to_patch"]["const"] is False
    assert capsule_schema["properties"]["automatic_merge"]["const"] is False

    try:
        import jsonschema
        from jsonschema import Draft202012Validator

        schema_store = {
            participant_schema["$id"]: participant_schema,
            group_schema["$id"]: group_schema,
            capsule_schema["$id"]: capsule_schema,
        }
        resolver = jsonschema.RefResolver.from_schema(
            capsule_schema, store=schema_store
        )
        validator = Draft202012Validator(capsule_schema, resolver=resolver)
        validator.validate(data)
    except ImportError:
        pytest.skip("jsonschema not available for Draft 2020-12 validation")


def test_strict_authority_and_boolean_fields_reject_truthy_values() -> None:
    packet = _packet()
    packet["human_review_required"] = "true"
    with pytest.raises(ValueError, match="authority boundary"):
        _compile(packet)

    data = _compile().to_dict()
    data["shadow_mode"] = 1
    with pytest.raises(ValueError, match="shadow_mode"):
        RelationalSynthesisCapsule.from_dict(data)


def test_objective_mismatch_rejects_unrelated_intent() -> None:
    other = PolysyntheticIntentPacket.from_slots(
        {
            "DIR": "IN",
            "ASP": "GROUND",
            "CLASS": "REVIEW",
            "SUBJ": "OTHER",
            "VOICE": "HUMAN_AGENT",
            "STEM": "INSPECT",
        },
        objective="A different objective",
    )
    with pytest.raises(ValueError, match="does not bind"):
        packet = _packet()
        RelationalSynthesisShadowCompiler().compile(
            packet,
            intent_packet=other,
            expected_repo_head=packet["repo_head"],
            expected_packet_digest=packet["packet_digest"],
            expected_inventory_digest=packet["atomic_inventory"]["inventory_digest"],
        )


def test_test_path_detection_does_not_classify_latest_module_as_test() -> None:
    packet = _packet()
    packet["atomic_inventory"]["selected_atomic_functions"][3]["file_path"] = (
        "latest_feature.py"
    )
    packet["source_slices"][3]["file_path"] = "latest_feature.py"
    packet["source_slices"][3]["file_source_hash"] = "7" * 64
    capsule = _compile(packet)
    participant = next(
        item
        for item in capsule.participants
        if item.qualified_symbol == "test_scope_is_bounded"
    )
    assert participant.truth_class is TruthClass.EXACT_SOURCE


def test_selected_and_source_slice_identities_must_match_exactly() -> None:
    packet = _packet()
    packet["source_slices"][0]["line_end"] += 1
    with pytest.raises(ValueError, match="identity disagrees"):
        _compile(packet)

    packet = _packet()
    packet["source_slices"].append(
        {
            **deepcopy(packet["source_slices"][0]),
            "node_id": "extra.py#function:extra:9999999999999999",
            "file_path": "extra.py",
            "symbol": "extra",
            "qualified_symbol": "extra",
            "source_hash": "6" * 64,
            "file_source_hash": "7" * 64,
        }
    )
    with pytest.raises(ValueError, match="must match selected"):
        _compile(packet)


def test_duplicate_exact_dependency_edge_is_rejected() -> None:
    packet = _packet()
    packet["dependency_edges"].append(deepcopy(packet["dependency_edges"][0]))
    with pytest.raises(ValueError, match="duplicate exact relations"):
        _compile(packet)


def test_expected_freshness_identities_are_required() -> None:
    packet = _packet()
    with pytest.raises(TypeError):
        RelationalSynthesisShadowCompiler().compile(
            packet,
            intent_packet=_intent(),
        )


def test_name_derived_roles_and_test_meaning_remain_open() -> None:
    packet = _packet()
    packet["tests"] = ["tests/test_packet.py"]
    capsule = _compile(packet)

    scope_group = next(
        item for item in capsule.groups if item.purpose == "input_scope_authority"
    )
    binding_roles = {item.role for item in scope_group.role_bindings}
    assert "candidate_input_parser" in binding_roles
    assert "candidate_scope_normalizer" in binding_roles
    assert "candidate_packet_assembler" in binding_roles
    assert "authority_guard" in binding_roles
    assert all(item.status.value == "OPEN" for item in scope_group.proof_obligations)
    assert scope_group.boundary.omitted_reasons == {
        "name_derived_role_requires_proof": 3
    }
    assert len(scope_group.boundary.unresolved_relations) == 3

    test_group = next(
        item for item in capsule.groups if item.purpose == "test_proof_ownership"
    )
    assert all(item.status.value == "OPEN" for item in test_group.proof_obligations)
    assert test_group.boundary.omitted_reasons == {
        "unresolved_test_invariant": 1
    }
    assert any(
        item.startswith("proved_invariant:")
        for item in test_group.boundary.unresolved_relations
    )
