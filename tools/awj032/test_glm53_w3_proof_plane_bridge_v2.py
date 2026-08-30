import hashlib
import json

import pytest

from tools.awj032 import glm53_w3_proof_plane_bridge_v2 as m


def canonical(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def sha(v):
    return hashlib.sha256(canonical(v)).hexdigest()


def w2():
    return {
        "schema": m.W2_SCHEMA,
        "inner_source_plan_digest": "a" * 64,
        "official_w2_observation_digest": m.EXPECTED_W2_OBSERVATION_DIGEST,
        "official_w2_receipt_digest": m.W2_RECEIPT,
        "official_w2_producer_semantic_head": m.W2_PRODUCER_SEMANTIC_HEAD,
        "official_w2_producer_run_ref": m.W2_PRODUCER_RUN_REF,
        "official_w2_drive_observation_ref": m.W2_DRIVE_REF,
        "representative_layer": 3,
        "representative_expert": 0,
        "official_w2_producer_observation_proven": True,
        "all_experts_header_uniformity_proven": False,
        "g2_admitted": False,
        "runtime_execution_proven": False,
        "large_checkpoint_admitted": False,
        "authority": False,
    }


def mtp():
    body = {
        "owner_repo": m.OFFICIAL_REPO,
        "immutable_model_revision": m.OFFICIAL_REVISION,
        "config_raw_sha256": m.OFFICIAL_CONFIG_RAW_SHA256,
        "config_parsed_sha256": m.OFFICIAL_CONFIG_PARSED_SHA256,
        "index_sha256": m.OFFICIAL_INDEX_SHA256,
        "index_parsed_sha256": m.OFFICIAL_INDEX_PARSED_SHA256,
        "weight_map_digest": m.OFFICIAL_WEIGHT_MAP_DIGEST,
        "source_bundle_id": m.OFFICIAL_SOURCE_BUNDLE_ID,
        "num_hidden_layers": 78,
        "num_nextn_predict_layers": 1,
        "observed_extra_checkpoint_layer_indices": [78],
        "mtp_marker_keys": ["model.layers.78.eh_proj.weight"],
        "role_index": 78,
        "role": "MTP_NON_DECODER",
        "decoder_pager_membership": False,
        "source_verified": True,
        "payload_bytes_read": 0,
        "g2_admitted": False,
        "runtime_executed": False,
        "authority": False,
        "schema": m.MTP_SCHEMA,
    }
    assert sha(body) == m.OFFICIAL_MTP_EVIDENCE_ID
    return {**body, "evidence_id": sha(body)}


def security():
    return {
        "semantic_head": m.AIRLLM_SECURITY_SEMANTIC_HEAD,
        "hosted_contract_pass": True,
        "hard_false_remote_code_proven": True,
        "static_source_security_only": True,
    }


def eval_(wp=None, me=None, se=None):
    return m.evaluate_w3_proof_planes(
        official_w2_plan=w2() if wp is None else wp,
        official_mtp_role_evidence=mtp() if me is None else me,
        airllm_security_evidence=security() if se is None else se,
    )


def err(code, fn):
    with pytest.raises(m.W3ProofPlaneError) as e:
        fn()
    assert e.value.code == code


def test_exact_control_is_native_synthetic_only():
    r = eval_()
    assert r.status == "ELIGIBLE_FOR_NATIVE_SYNTHETIC_W3_FIXTURE"
    assert r.native_synthetic_w3_fixture_admitted
    assert not r.official_tensor_payload_admitted
    assert not r.g2_admitted and not r.runtime_execution_admitted
    assert not r.provider_effect_admitted and not r.quality_proven and not r.authority
    assert r.pr350_base_head == m.PR350_BASE_HEAD
    assert r.pr409_appraiser_head == m.PR409_APPRAISER_HEAD


def test_lower_pager_plan_rejected():
    p = {"schema": "GLM53PagerSourcePlanV2", "source_plan_digest": "a" * 64}
    err("OFFICIAL_W2_BOUND_PLAN_REQUIRED", lambda: eval_(wp=p))


def test_w2_producer_proof_false_rejected():
    p = w2(); p["official_w2_producer_observation_proven"] = False
    err("W2_PRODUCER_PROOF_REQUIRED", lambda: eval_(wp=p))


@pytest.mark.parametrize("field", [
    "all_experts_header_uniformity_proven", "g2_admitted",
    "runtime_execution_proven", "large_checkpoint_admitted", "authority",
])
def test_w2_scope_or_effect_widening_rejected(field):
    p = w2(); p[field] = True
    err("W2_EFFECT_OR_SCOPE_WIDENING", lambda: eval_(wp=p))


@pytest.mark.parametrize("field,value", [
    ("official_w2_observation_digest", "0" * 64),
    ("official_w2_receipt_digest", "0" * 40),
    ("official_w2_producer_semantic_head", "0" * 40),
    ("official_w2_producer_run_ref", "github-actions:run:wrong"),
    ("official_w2_drive_observation_ref", "drive:wrong"),
    ("representative_layer", 4),
    ("representative_expert", 1),
])
def test_w2_independent_producer_identity_substitution_rejected(field, value):
    p = w2(); p[field] = value
    err("W2_OFFICIAL_PRODUCER_IDENTITY_MISMATCH", lambda: eval_(wp=p))


@pytest.mark.parametrize("field,value", [
    ("owner_repo", "other/model"),
    ("immutable_model_revision", "0" * 40),
    ("index_sha256", "0" * 64),
    ("config_raw_sha256", "0" * 64),
    ("source_bundle_id", "0" * 64),
    ("num_hidden_layers", 77),
    ("num_nextn_predict_layers", 0),
    ("observed_extra_checkpoint_layer_indices", [79]),
    ("role_index", 79),
    ("role", "DECODER"),
    ("decoder_pager_membership", True),
    ("source_verified", False),
    ("payload_bytes_read", 1),
    ("g2_admitted", True),
    ("runtime_executed", True),
    ("authority", True),
])
def test_mtp_source_substitution_or_effect_widening_rejected(field, value):
    e = mtp(); e[field] = value
    err("OFFICIAL_MTP_SOURCE_IDENTITY_MISMATCH", lambda: eval_(me=e))


def test_mtp_marker_required():
    e = mtp(); e["mtp_marker_keys"] = []
    err("OFFICIAL_MTP_MARKER_REQUIRED", lambda: eval_(me=e))


def test_forged_mtp_evidence_id_rejected():
    e = mtp(); e["evidence_id"] = "0" * 64
    err("OFFICIAL_MTP_EVIDENCE_ID_MISMATCH", lambda: eval_(me=e))


def test_raw_resolver_boolean_is_not_source_role_evidence():
    e = {"resolver_provenance_proven": True}
    err("OFFICIAL_MTP_EVIDENCE_ID_REQUIRED", lambda: eval_(me=e))


def test_airllm_stale_generation_rejected():
    s = security(); s["semantic_head"] = "0" * 40
    err("AIRLLM_SECURITY_GENERATION_STALE", lambda: eval_(se=s))


def test_airllm_hosted_pass_required():
    s = security(); s["hosted_contract_pass"] = False
    err("AIRLLM_SECURITY_HOSTED_CONTRACT_REQUIRED", lambda: eval_(se=s))


def test_airllm_hard_false_required():
    s = security(); s["hard_false_remote_code_proven"] = False
    err("AIRLLM_HARD_FALSE_REMOTE_CODE_REQUIRED", lambda: eval_(se=s))


def test_airllm_static_ceiling_required():
    s = security(); s["static_source_security_only"] = False
    err("AIRLLM_SECURITY_CLAIM_CEILING_INVALID", lambda: eval_(se=s))


def test_clock_or_unrelated_fields_do_not_enter_receipt():
    a = eval_()
    p = w2(); p["observation_time"] = "later"
    e = mtp(); e["observation_time"] = "later"
    s = security(); s["observation_time"] = "later"
    b = eval_(wp=p, me=e, se=s)
    assert a.logical_id == b.logical_id
