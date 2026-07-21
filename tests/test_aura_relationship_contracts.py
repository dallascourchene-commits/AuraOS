from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from aura_relationship_contracts import (
    AuthorityPosture,
    CapabilitySelectionStatus,
    CompatibilityOutcome,
    CompassObjectiveContract,
    ProofStatus,
    RelationshipContract,
    RelationshipDomain,
    RepositoryIdentity,
    ResourceBudget,
    SixSlotProjection,
    SourceReference,
    TruthClass,
    capability_class_index,
    capability_selections_from_path,
    evaluate_relationship_compatibility,
)


SLOTS = {
    "DIR": "IN",
    "ASP": "GROUND",
    "CLASS": "REVIEW",
    "SUBJ": "REPOSITORY_RELATION",
    "VOICE": "HUMAN_AGENT",
    "STEM": "INSPECT",
}


def _relationship_contract(*, prohibition_ids: tuple[str, ...] = ()) -> RelationshipContract:
    return RelationshipContract.create(
        objective_digest="objective-digest",
        intent_packet_digest="intent-digest",
        source_repository=RepositoryIdentity(
            repo_head="head-sha",
            working_tree_digest="worktree-digest",
            relational_index_digest="index-digest",
            atlas_digest="atlas-digest",
        ),
        domain=RelationshipDomain.CODE,
        slots=SixSlotProjection.from_mapping(SLOTS),
        truth_class=TruthClass.EXACT_SOURCE,
        authority_posture=AuthorityPosture.PROPOSAL_ONLY,
        proof_status=ProofStatus.GROUNDED,
        policy_scope=("coding", "review"),
        resource_budget=ResourceBudget(),
        source_refs=(
            SourceReference(
                file_path="aura_example.py",
                symbol="example",
                line_start=1,
                line_end=3,
                source_hash="source-hash",
                file_source_hash="file-hash",
            ),
        ),
        prohibition_ids=prohibition_ids,
    )


def test_relationship_contract_is_deterministic_and_tamper_evident() -> None:
    first = _relationship_contract()
    second = _relationship_contract()
    assert first.contract_id == second.contract_id
    assert first.to_dict()["safe_to_patch"] is False
    assert first.to_dict()["production_mutation"] is False

    loaded = RelationshipContract.from_dict(first.to_dict())
    assert loaded == first

    tampered = copy.deepcopy(first.to_dict())
    tampered["policy_scope"].append("mutation")
    with pytest.raises(ValueError, match="digest mismatch"):
        RelationshipContract.from_dict(tampered)


def test_relationship_contract_rejects_unknown_keys_and_authority_drift() -> None:
    unknown = _relationship_contract().to_dict()
    unknown["regex_authority"] = True
    with pytest.raises(ValueError, match="unknown keys"):
        RelationshipContract.from_dict(unknown)

    authority = _relationship_contract().to_dict()
    authority["safe_to_patch"] = True
    with pytest.raises(ValueError, match="cannot carry mutation authority"):
        RelationshipContract.from_dict(authority)


def test_capability_path_classification_is_explicit_and_zero_model_safe() -> None:
    selections = capability_selections_from_path(
        {
            "required_capability_ids": ["cap.det", "cap.model", "cap.unresolved"],
            "deterministic_capability_ids": ["cap.det"],
            "model_dependent_capability_ids": ["cap.model"],
            "unresolved_execution_capability_ids": ["cap.unresolved"],
            "auxiliary_capability_ids": ["cap.aux"],
            "prohibited_capability_ids": ["cap.blocked"],
            "path_details": [],
        }
    )
    classes = capability_class_index(selections)
    assert classes[CapabilitySelectionStatus.ACTIVE.value] == ["cap.det"]
    assert classes[CapabilitySelectionStatus.SELECTED.value] == ["cap.model"]
    assert classes[CapabilitySelectionStatus.UNRESOLVED.value] == ["cap.unresolved"]
    assert classes[CapabilitySelectionStatus.AUXILIARY.value] == ["cap.aux"]
    assert classes[CapabilitySelectionStatus.PROHIBITED.value] == ["cap.blocked"]

    objective = CompassObjectiveContract.create(
        objective="Compile a bounded relationship plan",
        intent_packet={"slots": SLOTS},
        intent_packet_digest="intent-digest",
        repository_head="head-sha",
        target_files=["aura_example.py"],
        target_symbols=["example"],
        capabilities=selections,
        route_reasons=["explicit_relationship_compass_intent"],
    )
    assert objective.zero_model_eligible is False
    assert CompassObjectiveContract.from_dict(objective.to_dict()) == objective


def test_hard_guards_precede_any_advisory_compatibility_score() -> None:
    compatible = evaluate_relationship_compatibility(_relationship_contract(), _relationship_contract())
    assert compatible.outcome is CompatibilityOutcome.COMPATIBLE
    assert compatible.advisory_score is None
    assert all(item.passed for item in compatible.hard_guard_results)

    prohibited = evaluate_relationship_compatibility(
        _relationship_contract(prohibition_ids=("self_verification_block",)),
        _relationship_contract(),
    )
    assert prohibited.outcome is CompatibilityOutcome.PROHIBITED
    assert prohibited.advisory_score is None


def test_runtime_contract_keys_match_declared_schemas() -> None:
    root = Path(__file__).resolve().parents[1]
    contract = _relationship_contract().to_dict()
    objective = CompassObjectiveContract.create(
        objective="Inspect exact source relationships",
        intent_packet={"slots": SLOTS},
        intent_packet_digest="intent-digest",
        repository_head="head-sha",
        target_files=["aura_example.py"],
        target_symbols=["example"],
        capabilities=(),
        route_reasons=["explicit_relationship_compass_intent"],
    ).to_dict()
    for path, value in (
        (root / "schemas/aura_relationship_contract.schema.json", contract),
        (root / "schemas/aura_coding_relationship_compass.schema.json", objective),
    ):
        schema = json.loads(path.read_text(encoding="utf-8"))
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == set(value)
