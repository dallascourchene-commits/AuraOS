from __future__ import annotations

from dataclasses import replace

import pytest

from tools.quantization.aura_canary_result_source_c2_work_admission import (
    admit_canary_result_to_c2_work,
    current_q5_fixture,
    current_q7_fixture,
)


def test_current_strong_e8_result_still_holds_on_source_gate():
    receipt = admit_canary_result_to_c2_work(current_q5_fixture(), current_q7_fixture())
    assert receipt["representative_outcome"] == "E8_WIN"
    assert receipt["disposition"] == "SOURCE_ADMISSION_HOLD"
    assert receipt["reason"] == "OFFICIAL_INDEX_BYTES_AND_REPRESENTATIVE_HEADERS_NOT_MATERIALIZED"
    assert receipt["c2_request_proposal_eligible"] is False


def test_future_source_green_plus_e8_win_can_only_propose_bounded_request():
    q7 = replace(
        current_q7_fixture(),
        source_header_trial_eligible=True,
        source_bound_c2_request_admissible=True,
        blocker="NONE_HEADER_LEVEL_REQUEST_ADMISSIBLE",
    )
    receipt = admit_canary_result_to_c2_work(current_q5_fixture(), q7)
    assert receipt["disposition"] == "BOUNDED_REPRESENTATIVE_E8_C2_REQUEST_PROPOSAL_ELIGIBLE"
    assert receipt["c2_request_proposal_eligible"] is True
    assert receipt["execution_authorized"] is False
    assert receipt["owner_host_execution_observed"] is False


@pytest.mark.parametrize("outcome,candidate,control", [
    ("CONTROL_WIN", 2.0, 1.0),
    ("TIE", 1.0, 1.0),
])
def test_non_e8_outcome_stops_e8_escalation_after_source_gate(outcome, candidate, control):
    q5 = replace(
        current_q5_fixture(),
        aggregate_candidate_mse=candidate,
        aggregate_control_mse=control,
        aggregate_outcome=outcome,
    )
    q7 = replace(
        current_q7_fixture(),
        source_header_trial_eligible=True,
        source_bound_c2_request_admissible=True,
        blocker="NONE_HEADER_LEVEL_REQUEST_ADMISSIBLE",
    )
    receipt = admit_canary_result_to_c2_work(q5, q7)
    assert receipt["disposition"] == "STOP_E8_ESCALATION_NO_REPRESENTATIVE_ADVANTAGE"
    assert receipt["c2_request_proposal_eligible"] is False


def test_q5_generation_substitution_rejected():
    with pytest.raises(ValueError, match="Q5_PRODUCER_GENERATION_MISMATCH"):
        admit_canary_result_to_c2_work(replace(current_q5_fixture(), producer_head="f" * 40), current_q7_fixture())


def test_q5_receipt_substitution_rejected():
    with pytest.raises(ValueError, match="Q5_RECEIPT_IDENTITY_MISMATCH"):
        admit_canary_result_to_c2_work(replace(current_q5_fixture(), receipt_digest="f" * 64), current_q7_fixture())


def test_q5_source_set_substitution_rejected():
    with pytest.raises(ValueError, match="Q5_SOURCE_SET_MISMATCH"):
        admit_canary_result_to_c2_work(replace(current_q5_fixture(), source_set_digest="f" * 64), current_q7_fixture())


def test_q5_rate_drift_rejected():
    with pytest.raises(ValueError, match="Q5_EQUAL_RATE_DRIFT"):
        admit_canary_result_to_c2_work(replace(current_q5_fixture(), candidate_bpw=1.5), current_q7_fixture())


def test_q5_outcome_mse_contradiction_rejected():
    with pytest.raises(ValueError, match="Q5_OUTCOME_MSE_CONTRADICTION"):
        admit_canary_result_to_c2_work(replace(current_q5_fixture(), aggregate_outcome="CONTROL_WIN"), current_q7_fixture())


def test_q5_claim_widening_rejected():
    with pytest.raises(ValueError, match="Q5_CLAIM_CEILING_WIDENED"):
        admit_canary_result_to_c2_work(replace(current_q5_fixture(), quality_proven=True), current_q7_fixture())


def test_q7_generation_substitution_rejected():
    with pytest.raises(ValueError, match="Q7_PRODUCER_GENERATION_MISMATCH"):
        admit_canary_result_to_c2_work(current_q5_fixture(), replace(current_q7_fixture(), producer_run=1))


def test_q7_disposition_substitution_rejected():
    with pytest.raises(ValueError, match="Q7_DISPOSITION_IDENTITY_MISMATCH"):
        admit_canary_result_to_c2_work(current_q5_fixture(), replace(current_q7_fixture(), disposition_digest="e" * 64))


def test_q7_admission_without_header_rejected():
    with pytest.raises(ValueError, match="Q7_REQUEST_ADMISSION_WITHOUT_HEADER_ELIGIBILITY"):
        admit_canary_result_to_c2_work(current_q5_fixture(), replace(current_q7_fixture(), source_bound_c2_request_admissible=True))


def test_q7_effect_widening_rejected():
    with pytest.raises(ValueError, match="Q7_AUTHORITY_OR_EFFECT_WIDENING"):
        admit_canary_result_to_c2_work(current_q5_fixture(), replace(current_q7_fixture(), owner_host_execution_observed=True))


def test_cross_parent_source_mismatch_rejected():
    with pytest.raises(ValueError, match="Q7_OFFICIAL_SOURCE_MISMATCH"):
        admit_canary_result_to_c2_work(current_q5_fixture(), replace(current_q7_fixture(), official_revision="wrong"))


def test_receipt_is_deterministic_and_claim_ceiling_remains_false():
    a = admit_canary_result_to_c2_work(current_q5_fixture(), current_q7_fixture())
    b = admit_canary_result_to_c2_work(current_q5_fixture(), current_q7_fixture())
    assert a == b
    for key in (
        "source_tensor_payload_bound",
        "real_tensor_quantization_eligible",
        "execution_authorized",
        "owner_host_execution_observed",
        "physical_io_attested",
        "quality_superiority_proven",
        "runtime_superiority_proven",
        "full_tensor_superiority_proven",
        "whole_model_superiority_proven",
        "g2_admitted",
        "gate10_promoted",
        "semantic_k27_authority",
        "native_private_transformer_kv_accessed",
    ):
        assert a[key] is False
