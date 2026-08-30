import inspect
from dataclasses import replace

import pytest

from tools.awj032 import glm53_w3_canonical_owner_composite as c
from tools.awj032 import glm53_w3_official_producer_admission as w3
from tools.awj032.test_glm53_w3_official_producer_admission import (
    LowerPlan,
    metadata,
    security,
)


def current_w3_receipt():
    return w3.evaluate_w3_official_producer_admission(
        pager_plan=LowerPlan(),
        airllm_security_evidence=security(),
        glm53_metadata_evidence=metadata(),
    )


def compose_current():
    return c.compose_canonical_w3_admission(
        pager_plan=LowerPlan(),
        airllm_security_evidence=security(),
        glm53_metadata_evidence=metadata(),
    )


def test_exact_current_owners_open_only_native_synthetic_fixture_eligibility():
    out = compose_current()
    assert out.status == "ELIGIBLE_FOR_NATIVE_SYNTHETIC_W3_FIXTURE"
    assert out.blockers == ()
    assert out.official_w2_producer_proof_consumed is True
    assert out.registry_bound_mtp_owner_consumed is True
    assert out.native_synthetic_w3_eligible is True
    assert out.native_synthetic_w3_numerical_proven is False
    assert out.official_tensor_payload_admitted is False
    assert out.runtime_execution_admitted is False
    assert out.quality_proven is False
    assert out.g2_admitted is False
    assert out.provider_effect_admitted is False
    assert out.authority is False
    assert out.pr410_current_head == c.PR410_CURRENT_HEAD
    assert out.pr421_report_logical_id == c.PR421_REPORT_LOGICAL_ID


def test_canonical_public_api_accepts_live_pr410_inputs_only():
    params = set(inspect.signature(c.compose_canonical_w3_admission).parameters)
    assert params == {"pager_plan", "airllm_security_evidence", "glm53_metadata_evidence"}

    with pytest.raises(TypeError):
        c.compose_canonical_w3_admission(w3_receipt=current_w3_receipt())

    with pytest.raises(TypeError):
        c.compose_canonical_w3_admission(
            pager_plan=LowerPlan(),
            airllm_security_evidence=security(),
            glm53_metadata_evidence=metadata(),
            pr421_owner_receipt={},
        )


def test_direct_serialized_pr410_receipt_cannot_enter_public_boundary():
    raw = current_w3_receipt().to_dict()
    assert raw["official_w2_producer_proof_consumed"] is True
    with pytest.raises(TypeError):
        c.compose_canonical_w3_admission(w3_receipt=raw)


def test_public_boundary_actually_invokes_pr410(monkeypatch):
    calls = []
    original = c.evaluate_w3_official_producer_admission

    def traced(**kwargs):
        calls.append(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(c, "evaluate_w3_official_producer_admission", traced)
    out = compose_current()
    assert out.status == "ELIGIBLE_FOR_NATIVE_SYNTHETIC_W3_FIXTURE"
    assert len(calls) == 1
    assert isinstance(calls[0]["pager_plan"], LowerPlan)


def test_pr410_must_be_blocked_only_on_mtp_provenance():
    stale_security = security()
    stale_security["semantic_head"] = "0" * 40
    with pytest.raises(c.CanonicalOwnerCompositeError, match="PR410_W3_BLOCKER_SET_NOT_COMPOSABLE"):
        c.compose_canonical_w3_admission(
            pager_plan=LowerPlan(),
            airllm_security_evidence=stale_security,
            glm53_metadata_evidence=metadata(),
        )


def test_caller_provenance_widening_from_pr410_cannot_be_laundered():
    with pytest.raises(c.CanonicalOwnerCompositeError, match="PR410_W3_BLOCKER_SET_NOT_COMPOSABLE"):
        c.compose_canonical_w3_admission(
            pager_plan=LowerPlan(),
            airllm_security_evidence=security(),
            glm53_metadata_evidence=metadata(resolver_provenance_proven=True),
        )


def test_private_receipt_validator_still_rejects_missing_producer_proof():
    raw = current_w3_receipt().to_dict()
    raw["official_w2_producer_proof_consumed"] = False
    with pytest.raises(c.CanonicalOwnerCompositeError, match="PR410_W2_PRODUCER_PROOF_REQUIRED"):
        c._compose_verified_pr410_receipt(raw)


def test_private_receipt_validator_still_rejects_generation_substitution():
    raw = current_w3_receipt().to_dict()
    raw["glm53_metadata_semantic_head"] = "0" * 40
    with pytest.raises(c.CanonicalOwnerCompositeError, match="PR410_RECEIPT_GENERATION_MISMATCH"):
        c._compose_verified_pr410_receipt(raw)


def test_private_receipt_validator_rejects_effect_widening():
    for field in (
        "synthetic_tiny_fixture_admitted",
        "g2_admitted",
        "runtime_execution_admitted",
        "checkpoint_payload_admitted",
        "provider_effect_admitted",
        "authority",
    ):
        raw = current_w3_receipt().to_dict()
        raw[field] = True
        with pytest.raises(c.CanonicalOwnerCompositeError, match="PR410_EFFECT_CEILING_WIDENED"):
            c._compose_verified_pr410_receipt(raw)


def test_pr421_owner_is_exact_code_owned_receipt_not_shape_matching_input():
    original = c.CANONICAL_PR421_OWNER_RECEIPT
    substitutions = (
        replace(original, report_logical_id="0" * 64),
        replace(original, observation_head="1" * 40),
        replace(original, run_id=1),
        replace(original, job_id=2),
        replace(original, output_pin_ref="drive:caller"),
        replace(original, pr340_registry_pin_digest="2" * 64),
        replace(original, pr340_final_report_digest="3" * 64),
        replace(original, pr340_snapshot_digest="4" * 64),
        replace(original, official_mtp_source_evidence_id="5" * 64),
    )
    try:
        for substituted in substitutions:
            c.CANONICAL_PR421_OWNER_RECEIPT = substituted
            with pytest.raises(c.CanonicalOwnerCompositeError, match="PR421_CANONICAL_OWNER_RECEIPT_MISMATCH"):
                compose_current()
    finally:
        c.CANONICAL_PR421_OWNER_RECEIPT = original


def test_pr421_owner_effect_or_proof_widening_fails_closed():
    original = c.CANONICAL_PR421_OWNER_RECEIPT
    substitutions = (
        replace(original, source_binding_proven=False),
        replace(original, mtp_resolver_provenance_proven=False),
        replace(original, pr340_producer_logical_id_verified=False),
        replace(original, pr340_final_report_registry_proven=False),
        replace(original, g2_admitted=True),
        replace(original, large_checkpoint_admitted=True),
        replace(original, runtime_execution_proven=True),
        replace(original, authority=True),
    )
    try:
        for substituted in substitutions:
            c.CANONICAL_PR421_OWNER_RECEIPT = substituted
            with pytest.raises(c.CanonicalOwnerCompositeError):
                compose_current()
    finally:
        c.CANONICAL_PR421_OWNER_RECEIPT = original


def test_owner_receipt_binds_exact_independent_output_pin():
    owner = c.CANONICAL_PR421_OWNER_RECEIPT
    assert owner.semantic_head == "11afbd64db600e8839c8d18d72dd0320d074a0ac"
    assert owner.observation_head == "85813c6a9218e77d1a5e92ba2b82d27f08a65ea4"
    assert owner.run_id == 33340370095
    assert owner.job_id == 99334783653
    assert owner.report_logical_id == "bdcda54659157ed8249d258e3db20e1141b25ffb51d1e6d593e3c8a788b1eb23"
    assert owner.output_pin_ref == "drive:14Q8kBD76D_OvmdxT1CVx52kbIrMlec-Xk1iPImOF5Ks"
    assert owner.pr340_registry_pin_digest == "2b162e1598d3fa2d086f207318d338178e9645e55891f4f5de6bf211a8dd93da"
    assert owner.pr340_registry_receipt_ref == "drive:1Tb7F-vu_Rb8bImIQXscword8tRRpt_DawtJV9dMnKEw"
    assert owner.pr340_final_report_digest == "d7ff1b34d091a92449d59c0cb561bc5a87724c67ab9bdb7504a5b38f5c3dfaa9"


def test_composite_is_deterministic_and_owner_receipt_is_content_addressed():
    a = compose_current()
    b = compose_current()
    assert a.logical_id == b.logical_id
    assert a.pr410_input_receipt_digest == b.pr410_input_receipt_digest
    assert a.pr421_owner_receipt_digest == b.pr421_owner_receipt_digest
    assert a.pr421_owner_receipt_digest == c.CANONICAL_PR421_OWNER_RECEIPT.receipt_digest
