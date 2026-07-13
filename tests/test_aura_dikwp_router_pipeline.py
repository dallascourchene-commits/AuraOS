from __future__ import annotations

import pytest

from aura_dikwp_router_pipeline import (
    DIKWPEnvelope,
    DIKWPStage,
    purpose_digest,
    validate_dikwp_chain,
)


def _complete_chain(correlation: str = "c1"):
    purpose_payload = {"authority": "human", "privacy": "local"}
    purpose = DIKWPEnvelope.create(
        correlation_id=correlation, stage=DIKWPStage.PURPOSE,
        payload=purpose_payload, created_at=1,
    )
    data = DIKWPEnvelope.create(
        correlation_id=correlation, stage=DIKWPStage.DATA,
        payload={"verifier_pass": True}, created_at=2,
    )
    information = DIKWPEnvelope.create(
        correlation_id=correlation, stage=DIKWPStage.INFORMATION,
        payload={"task_bucket": "coding"},
        source_record_ids=(data.envelope_id,), created_at=3,
    )
    knowledge = DIKWPEnvelope.create(
        correlation_id=correlation, stage=DIKWPStage.KNOWLEDGE,
        payload={"posterior": 0.9},
        source_record_ids=(information.envelope_id,), created_at=4,
    )
    wisdom = DIKWPEnvelope.create(
        correlation_id=correlation, stage=DIKWPStage.WISDOM,
        payload={"route": "DIRECT"},
        source_record_ids=(knowledge.envelope_id, purpose.envelope_id),
        purpose_digest=purpose_digest(purpose_payload), created_at=5,
    )
    return purpose, data, information, knowledge, wisdom


def test_complete_consequential_chain_is_valid() -> None:
    result = validate_dikwp_chain(_complete_chain())
    assert result["ok"] is True
    assert result["correlation_id"] == "c1"


def test_wisdom_requires_purpose_digest() -> None:
    with pytest.raises(ValueError, match="purpose_digest"):
        DIKWPEnvelope.create(
            correlation_id="c1",
            stage=DIKWPStage.WISDOM,
            payload={"route": "DIRECT"},
            source_record_ids=("knowledge",),
        )


def test_wisdom_must_cite_both_knowledge_and_purpose() -> None:
    purpose, data, information, knowledge, wisdom = _complete_chain()
    broken = DIKWPEnvelope.create(
        correlation_id="c1", stage=DIKWPStage.WISDOM,
        payload={"route": "DIRECT"},
        source_record_ids=(knowledge.envelope_id,),
        purpose_digest=purpose.payload_digest, created_at=5,
    )
    result = validate_dikwp_chain([purpose, data, information, knowledge, broken])
    assert result["ok"] is False
    assert any("PURPOSE" in error for error in result["errors"])


def test_cross_correlation_sources_are_rejected() -> None:
    purpose, data, information, knowledge, wisdom = _complete_chain()
    foreign_data = DIKWPEnvelope.create(
        correlation_id="other", stage=DIKWPStage.DATA,
        payload={"x": 1}, created_at=2,
    )
    broken_information = DIKWPEnvelope.create(
        correlation_id="c1", stage=DIKWPStage.INFORMATION,
        payload={"x": 1}, source_record_ids=(foreign_data.envelope_id,), created_at=3,
    )
    result = validate_dikwp_chain([purpose, foreign_data, broken_information, knowledge, wisdom])
    assert result["ok"] is False
    assert any("correlation" in error for error in result["errors"])


def test_future_parent_and_non_proposal_wisdom_are_rejected() -> None:
    purpose, data, information, knowledge, _ = _complete_chain()
    wisdom = DIKWPEnvelope.create(
        correlation_id="c1", stage=DIKWPStage.WISDOM,
        payload={"route": "DIRECT"},
        source_record_ids=(knowledge.envelope_id, purpose.envelope_id),
        purpose_digest=purpose.payload_digest,
        created_at=0.5, proposal_only=False,
    )
    result = validate_dikwp_chain([purpose, data, information, knowledge, wisdom])
    assert result["ok"] is False
    assert any("created later" in error for error in result["errors"])
    assert any("proposal_only" in error for error in result["errors"])
