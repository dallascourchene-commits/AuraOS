from __future__ import annotations

from aura_dikwp_router_pipeline import (
    DIKWPEnvelope,
    DIKWPStage,
    purpose_digest,
    validate_dikwp_chain,
)


def test_complete_consequential_chain_is_valid() -> None:
    purpose_payload = {"authority": "human", "privacy": "local"}
    purpose = DIKWPEnvelope.create(
        correlation_id="c1", stage=DIKWPStage.PURPOSE, payload=purpose_payload
    )
    data = DIKWPEnvelope.create(
        correlation_id="c1", stage=DIKWPStage.DATA, payload={"verifier_pass": True}
    )
    information = DIKWPEnvelope.create(
        correlation_id="c1",
        stage=DIKWPStage.INFORMATION,
        payload={"task_bucket": "coding"},
        source_record_ids=(data.envelope_id,),
    )
    knowledge = DIKWPEnvelope.create(
        correlation_id="c1",
        stage=DIKWPStage.KNOWLEDGE,
        payload={"posterior": 0.9},
        source_record_ids=(information.envelope_id,),
    )
    wisdom = DIKWPEnvelope.create(
        correlation_id="c1",
        stage=DIKWPStage.WISDOM,
        payload={"route": "DIRECT"},
        source_record_ids=(knowledge.envelope_id, purpose.envelope_id),
        purpose_digest=purpose_digest(purpose_payload),
    )
    result = validate_dikwp_chain([purpose, data, information, knowledge, wisdom])
    assert result["ok"] is True


def test_wisdom_requires_purpose_digest() -> None:
    try:
        DIKWPEnvelope.create(
            correlation_id="c1",
            stage=DIKWPStage.WISDOM,
            payload={"route": "DIRECT"},
            source_record_ids=("knowledge",),
        )
    except ValueError as exc:
        assert "purpose_digest" in str(exc)
    else:
        raise AssertionError("WISDOM without purpose must fail")
