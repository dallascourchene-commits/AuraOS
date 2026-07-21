from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import jsonschema
import pytest

from aura_relationship_contracts import (
    AuthorityPosture,
    CapabilitySelection,
    CapabilitySelectionStatus,
    CompassObjectiveContract,
    CompatibilityOutcome,
    ProofStatus,
    RelationalNeighborhoodRequest,
    RelationshipCompatibilityAssessment,
    RelationshipContract,
    RelationshipDomain,
    RepositoryIdentity,
    ResourceBudget,
    SixSlotProjection,
    SourceReference,
    TruthClass,
    capability_class_index,
    capability_selections_from_path,
    canonical_json,
    evaluate_relationship_compatibility,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "schemas"


def _schema(name: str) -> dict:
    return json.loads((SCHEMA_ROOT / name).read_text(encoding="utf-8"))


def _slots() -> SixSlotProjection:
    return SixSlotProjection.from_mapping(
        {
            "DIR": "IN",
            "ASP": "GROUND",
            "CLASS": "REVIEW",
            "SUBJ": "REPOSITORY_RELATION",
            "VOICE": "HUMAN_AGENT",
            "STEM": "INSPECT",
        }
    )


def _source_ref(symbol: str = "compile") -> SourceReference:
    return SourceReference.from_dict(
        {
            "file_path": "aura_example.py",
            "symbol": symbol,
            "line_start": 10,
            "line_end": 20,
            "source_hash": "a" * 64,
            "file_source_hash": "b" * 64,
        }
    )


def _relationship_contract(*, prohibition_ids: tuple[str, ...] = ()) -> RelationshipContract:
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
        slots=_slots(),
        truth_class=TruthClass.EXACT_SOURCE,
        authority_posture=AuthorityPosture.PROPOSAL_ONLY,
        proof_status=ProofStatus.GROUNDED,
        policy_scope=("coding_arena",),
        resource_budget=ResourceBudget(),
        source_refs=(_source_ref(),),
        prohibition_ids=prohibition_ids,
    )


def test_capability_selection_classes_and_objective_contract_roundtrip() -> None:
    path = {
        "required_capability_ids": ["aura.relational.index", "aura.relationship.atlas"],
        "deterministic_capability_ids": ["aura.relational.index"],
        "model_dependent_capability_ids": ["aura.relationship.atlas"],
        "unresolved_execution_capability_ids": [],
        "path_details": [
            {
                "capability_id": "aura.relational.index",
                "reason": "exact repository anatomy",
                "implemented_by": ["aura_relational_index.py"],
                "symbols": ["build_relational_index"],
                "tests": ["tests/test_aura_relational_index.py"],
            },
            {
                "capability_id": "aura.relationship.atlas",
                "selection_reason": "classify relationships",
                "implemented_by": ["aura_relationship_atlas.py"],
                "symbols": ["build_relationship_atlas"],
                "tests": ["tests/test_aura_relationship_atlas.py"],
            },
        ],
    }
    selections = capability_selections_from_path(path)
    classes = capability_class_index(selections)
    assert classes["ACTIVE"] == ["aura.relational.index"]
    assert classes["SELECTED"] == ["aura.relationship.atlas"]

    contract = CompassObjectiveContract.create(
        objective="  Combine Connectome and Atlas for bounded coding work  ",
        intent_packet={"slots": _slots().to_dict()},
        intent_packet_digest="intent-digest",
        repository_head="head-sha",
        target_files=["aura_relationship_atlas.py", "aura_relational_index.py"],
        target_symbols=["build_relationship_atlas"],
        capabilities=selections,
        route_reasons=["explicit_compass_request"],
    )
    payload = contract.to_dict()
    jsonschema.Draft202012Validator(_schema("aura_coding_relationship_compass.schema.json")).validate(payload)
    assert CompassObjectiveContract.from_dict(payload) == contract
    assert contract.zero_model_eligible is False
    assert payload["safe_to_patch"] is False
    assert payload["production_mutation"] is False


def test_objective_contract_rejects_unknown_keys_tamper_and_boolean_aliases() -> None:
    contract = CompassObjectiveContract.create(
        objective="Bounded relationship review",
        intent_packet={"slots": _slots().to_dict()},
        intent_packet_digest="intent-digest",
        repository_head="head-sha",
        target_files=["aura_relationship_contracts.py"],
        target_symbols=[],
        capabilities=(),
        route_reasons=["explicit_compass_request"],
    )
    payload = contract.to_dict()
    unknown = {**payload, "automatic_merge": True}
    with pytest.raises(ValueError, match="unknown keys"):
        CompassObjectiveContract.from_dict(unknown)
    tampered = {**payload, "objective": "different objective"}
    with pytest.raises(ValueError, match="digest mismatch"):
        CompassObjectiveContract.from_dict(tampered)
    bad_bool = {**payload, "zero_model_eligible": "false"}
    with pytest.raises(TypeError, match="boolean"):
        CompassObjectiveContract.from_dict(bad_bool)


def test_relationship_contract_roundtrip_schema_and_authority_tamper() -> None:
    contract = _relationship_contract()
    payload = contract.to_dict()
    jsonschema.Draft202012Validator(_schema("aura_relationship_contract.schema.json")).validate(payload)
    assert RelationshipContract.from_dict(payload) == contract

    for key, value in (
        ("safe_to_patch", True),
        ("production_mutation", True),
        ("human_review_required", False),
        ("patch_authority", "semantic_similarity"),
        ("vsa_patch_authority", True),
    ):
        tampered = {**payload, key: value}
        with pytest.raises(ValueError):
            RelationshipContract.from_dict(tampered)

    bad_path = deepcopy(payload)
    bad_path["source_refs"][0]["file_path"] = "../escape.py"
    with pytest.raises(ValueError, match="canonical"):
        RelationshipContract.from_dict(bad_path)


def test_hard_guards_precede_advisory_ranking_and_roundtrip() -> None:
    left = _relationship_contract()
    right = _relationship_contract(prohibition_ids=("no_self_authorization",))
    assessment = evaluate_relationship_compatibility(left, right)
    assert assessment.outcome is CompatibilityOutcome.PROHIBITED
    assert assessment.advisory_score is None
    assert [item.code.value for item in assessment.hard_guard_results] == [
        "REPOSITORY_IDENTITY",
        "SOURCE_FRESHNESS",
        "CAPABILITY_POLICY_SCOPE",
        "ACTOR_AUTHORITY",
        "PROHIBITED_RELATIONSHIP",
        "RESOURCE_BUDGET",
        "PROOF_READINESS",
    ]
    payload = assessment.to_dict()
    jsonschema.Draft202012Validator(_schema("aura_relationship_compatibility.schema.json")).validate(payload)
    assert RelationshipCompatibilityAssessment.from_dict(payload) == assessment

    ranked_too_early = {**payload, "advisory_score": 0.99}
    # Rebind the digest so this specifically tests the hard-guard/ranking invariant.
    ranked_too_early["assessment_id"] = "0" * 48
    with pytest.raises(ValueError, match="only after every hard guard"):
        RelationshipCompatibilityAssessment.from_dict(ranked_too_early)


def test_neighborhood_request_roundtrip_bounds_and_authority() -> None:
    request = RelationalNeighborhoodRequest(
        objective_digest="objective-digest",
        seed_participant_ids=("relp_1",),
        seed_source_refs=(_source_ref(),),
        max_hops=2,
        max_nodes=128,
        max_edges=512,
        max_candidate_pairs=8128,
    )
    payload = request.to_dict()
    jsonschema.Draft202012Validator(_schema("aura_relational_neighborhood_request.schema.json")).validate(payload)
    assert RelationalNeighborhoodRequest.from_dict(payload) == request

    with pytest.raises(ValueError, match="at least one exact seed"):
        RelationalNeighborhoodRequest(objective_digest="x", seed_participant_ids=(), seed_source_refs=())
    with pytest.raises(ValueError, match="max_nodes"):
        RelationalNeighborhoodRequest(
            objective_digest="x", seed_participant_ids=("relp",), seed_source_refs=(), max_nodes=257
        )
    tampered = {**payload, "safe_to_patch": True}
    with pytest.raises(ValueError, match="mutation authority"):
        RelationalNeighborhoodRequest.from_dict(tampered)


def test_canonical_serialization_rejects_nan_and_text_as_sequence() -> None:
    with pytest.raises(ValueError):
        canonical_json({"score": float("nan")})
    with pytest.raises(TypeError, match="non-text iterable"):
        CapabilitySelection.from_dict(
            {
                "capability_id": "aura.test",
                "status": CapabilitySelectionStatus.SELECTED.value,
                "reasons": "not-a-sequence",
                "implementation_files": [],
                "symbols": [],
                "tests": [],
                "model_required": False,
            }
        )


def test_six_slot_contract_keeps_cultural_claim_boundary() -> None:
    import aura_polysynthetic_intent

    module_text = (aura_polysynthetic_intent.__doc__ or "").casefold()
    assert "engineering contract" in module_text
    assert "not asserted as a universal linguistic model" in module_text


def test_sequence_fields_reject_mapping_payloads() -> None:
    contract_payload = _relationship_contract().to_dict()
    contract_payload["policy_scope"] = {"coding_arena": True}
    with pytest.raises(TypeError, match="non-text.*sequence"):
        RelationshipContract.from_dict(contract_payload)

    request = RelationalNeighborhoodRequest(
        objective_digest="objective-digest",
        seed_participant_ids=("seed",),
        seed_source_refs=(),
        allowed_relation_types=("CALLS",),
    )
    request_payload = request.to_dict()
    request_payload["seed_participant_ids"] = {"seed": True}
    with pytest.raises(TypeError, match="non-text.*sequence"):
        RelationalNeighborhoodRequest.from_dict(request_payload)
