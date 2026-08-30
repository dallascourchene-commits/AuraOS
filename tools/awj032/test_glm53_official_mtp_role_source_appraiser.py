import copy
import hashlib
import json

import pytest

from tools.awj032 import glm53_checkpoint_source_binding as source_binding
from tools.awj032 import glm53_official_mtp_role_source_appraiser as m
from tools.awj032.glm53_checkpoint_extra_layer_classification import (
    CheckpointExtraLayerClassification,
    CheckpointExtraLayerEvidenceObservation,
)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _sha_json(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def sources(*, nextn=1, include_layer79=False, include_marker=True):
    config = {
        "num_hidden_layers": 78,
        "num_nextn_predict_layers": nextn,
        "hidden_size": 4,
        "n_routed_experts": 2,
        "moe_intermediate_size": 2,
        "quantization_config": {
            "quant_method": "fp8",
            "weight_block_size": [2, 2],
        },
    }
    wm = {
        "model.layers.0.input_layernorm.weight": "model-00001-of-00141.safetensors",
        "model.layers.77.input_layernorm.weight": "model-00140-of-00141.safetensors",
        "model.layers.78.self_attn.q_proj.weight": "model-00141-of-00141.safetensors",
    }
    for expert in range(2):
        for role in ("gate_proj", "up_proj", "down_proj"):
            base = f"model.layers.3.mlp.experts.{expert}.{role}"
            wm[f"{base}.weight"] = "model-00038-of-00141.safetensors"
            wm[f"{base}.weight_scale_inv"] = "model-00038-of-00141.safetensors"
    if include_marker:
        wm["model.layers.78.eh_proj.weight"] = "model-00141-of-00141.safetensors"
    if include_layer79:
        wm["model.layers.79.eh_proj.weight"] = "model-00141-of-00141.safetensors"
    index = {"metadata": {"total_size": 123}, "weight_map": wm}
    return _canonical(config), _canonical(index)


def reader_for(config_raw, index_raw):
    def read(url, max_bytes):
        if url.endswith("/config.json?download=true"):
            assert max_bytes == m.MAX_CONFIG_BYTES
            return config_raw
        if url.endswith("/model.safetensors.index.json?download=true"):
            assert max_bytes == m.MAX_INDEX_BYTES
            return index_raw
        raise AssertionError(url)
    return read


def observe_synthetic(**kwargs):
    config_raw, index_raw = sources(**kwargs)
    old = m.OFFICIAL_INDEX_SHA256
    try:
        m.OFFICIAL_INDEX_SHA256 = hashlib.sha256(index_raw).hexdigest()
        evidence = m.observe_official_mtp_role(read_full=reader_for(config_raw, index_raw))
    finally:
        m.OFFICIAL_INDEX_SHA256 = old
    return evidence


def _classification_for(evidence):
    roles = ((78, "MTP_NON_DECODER"),)
    classification = CheckpointExtraLayerClassification(
        model_revision=evidence.immutable_model_revision,
        index_sha256=evidence.index_sha256,
        num_hidden_layers=78,
        roles=roles,
        evidence_ref="synthetic-official-role",
        evidence_digest="1" * 64,
        evidence_generation="synthetic-generation-1",
        resolver_ref="synthetic-role-resolver",
        resolver_generation="synthetic-resolver-generation-1",
    )
    observation = CheckpointExtraLayerEvidenceObservation(
        evidence_ref=classification.evidence_ref,
        evidence_digest=classification.evidence_digest,
        evidence_generation=classification.evidence_generation,
        resolver_ref=classification.resolver_ref,
        resolver_generation=classification.resolver_generation,
        resolution_receipt_ref="synthetic-resolution-receipt-1",
        model_revision=evidence.immutable_model_revision,
        index_sha256=evidence.index_sha256,
        num_hidden_layers=78,
        roles=roles,
        evidence_current=True,
    )
    return classification, observation


def producer_report_for(evidence):
    config_raw, index_raw = sources()
    assert hashlib.sha256(index_raw).hexdigest() == evidence.index_sha256
    sources_bundle = source_binding.bind_checkpoint_sources(
        model_revision=evidence.immutable_model_revision,
        config_raw_bytes=config_raw,
        expected_config_sha256=hashlib.sha256(config_raw).hexdigest(),
        index_raw_bytes=index_raw,
        expected_index_sha256=evidence.index_sha256,
    )
    classification, observation = _classification_for(evidence)
    report = source_binding.source_bound_probe(
        sources=sources_bundle,
        airllm_revision="a" * 40,
        security_hard_false_remote_code=True,
        representative_sparse_layer=3,
        extra_layer_classification=classification,
        extra_layer_evidence_observation=observation,
        observation_time="t1",
    )
    assert report["blockers"] == [m.PROVENANCE_BLOCKER]
    assert report["source_bundle_id"] == evidence.source_bundle_id
    assert report["config_parsed_sha256"] == evidence.config_parsed_sha256
    assert report["index_parsed_sha256"] == evidence.index_parsed_sha256
    assert report["weight_map_digest"] == evidence.weight_map_digest
    return report


def _independent_pr340_logical_id(report):
    # Mirror the actual PR340 boundary independently of the appraiser helper:
    # classification mints logical_id; source_bound_probe appends these five
    # source/currentness fields afterward.
    excluded = {
        "logical_id",
        "observation_time",
        "claim_ceiling",
        "source_bundle_id",
        "config_parsed_sha256",
        "index_parsed_sha256",
        "weight_map_digest",
        "source_binding_proven",
    }
    logical = {key: value for key, value in report.items() if key not in excluded}
    return _sha_json(logical)


def _with_producer_blockers(report, blockers):
    out = copy.deepcopy(report)
    out["blockers"] = sorted(set(blockers))
    out["status"] = "PARTIAL" if out["blockers"] else "READY_FOR_HEADER_AND_TINY_FIXTURE"
    out["logical_id"] = _independent_pr340_logical_id(out)
    return out


def apply_synthetic(
    report,
    evidence,
    *,
    expected_id=None,
    expected_generation=m.PR340_PRODUCER_SEMANTIC_GENERATION,
):
    if expected_id is None:
        expected_id = report.get("logical_id")
    old = m.OFFICIAL_INDEX_SHA256
    try:
        m.OFFICIAL_INDEX_SHA256 = evidence.index_sha256
        return m._apply_verified_source_role(
            report,
            evidence,
            expected_pr340_logical_id=expected_id,
            expected_pr340_semantic_generation=expected_generation,
        )
    finally:
        m.OFFICIAL_INDEX_SHA256 = old


def test_observe_source_derives_exact_single_mtp_role():
    evidence = observe_synthetic()
    assert evidence.role_index == 78
    assert evidence.role == "MTP_NON_DECODER"
    assert evidence.observed_extra_checkpoint_layer_indices == (78,)
    assert evidence.num_nextn_predict_layers == 1
    assert any(k.startswith("model.layers.78.eh_proj") for k in evidence.mtp_marker_keys)
    assert not evidence.decoder_pager_membership
    assert not evidence.g2_admitted and not evidence.runtime_executed and not evidence.authority


def test_nextn_count_substitution_fails():
    config_raw, index_raw = sources(nextn=2)
    old = m.OFFICIAL_INDEX_SHA256
    try:
        m.OFFICIAL_INDEX_SHA256 = hashlib.sha256(index_raw).hexdigest()
        with pytest.raises(m.OfficialSourceMTPRoleError, match="OFFICIAL_NUM_NEXTN_PREDICT_LAYERS_MISMATCH"):
            m.observe_official_mtp_role(read_full=reader_for(config_raw, index_raw))
    finally:
        m.OFFICIAL_INDEX_SHA256 = old


def test_extra_layer79_substitution_fails():
    config_raw, index_raw = sources(include_layer79=True)
    old = m.OFFICIAL_INDEX_SHA256
    try:
        m.OFFICIAL_INDEX_SHA256 = hashlib.sha256(index_raw).hexdigest()
        with pytest.raises(m.OfficialSourceMTPRoleError, match="OFFICIAL_EXTRA_LAYER_SET_MISMATCH"):
            m.observe_official_mtp_role(read_full=reader_for(config_raw, index_raw))
    finally:
        m.OFFICIAL_INDEX_SHA256 = old


def test_missing_eh_proj_marker_fails():
    config_raw, index_raw = sources(include_marker=False)
    old = m.OFFICIAL_INDEX_SHA256
    try:
        m.OFFICIAL_INDEX_SHA256 = hashlib.sha256(index_raw).hexdigest()
        with pytest.raises(m.OfficialSourceMTPRoleError, match="OFFICIAL_MTP_MARKER_REQUIRED"):
            m.observe_official_mtp_role(read_full=reader_for(config_raw, index_raw))
    finally:
        m.OFFICIAL_INDEX_SHA256 = old


def test_index_digest_is_not_a_caller_claim():
    config_raw, index_raw = sources()
    with pytest.raises(m.OfficialSourceMTPRoleError, match="OFFICIAL_INDEX_SHA256_MISMATCH"):
        m.observe_official_mtp_role(read_full=reader_for(config_raw, index_raw))


def test_actual_pr340_producer_identity_recomputes_independently():
    evidence = observe_synthetic()
    report = producer_report_for(evidence)
    assert report["logical_id"] == _independent_pr340_logical_id(report)
    assert report["blockers"] == [m.PROVENANCE_BLOCKER]
    assert report["extra_layer_resolver_provenance_proven"] is False


def test_apply_removes_only_provenance_blocker():
    evidence = observe_synthetic()
    report = _with_producer_blockers(
        producer_report_for(evidence),
        [m.PROVENANCE_BLOCKER, "OTHER_BLOCKER"],
    )
    out = apply_synthetic(report, evidence)
    assert out["blockers"] == ["OTHER_BLOCKER"]
    assert out["status"] == "PARTIAL"
    assert out["extra_layer_resolver_provenance_proven"] is True
    assert out["extra_layer_resolver_provenance_method"] == "OFFICIAL_IMMUTABLE_SOURCE_DERIVATION"
    assert out["official_mtp_role_source_evidence_id"] == evidence.evidence_id
    assert out["pr340_producer_logical_id_verified"] is True
    assert out["pr340_producer_logical_id"] == report["logical_id"]
    assert out["pr340_producer_semantic_generation"] == m.PR340_PRODUCER_SEMANTIC_GENERATION


def test_clean_actual_pr340_source_role_becomes_tiny_fixture_ready_only():
    evidence = observe_synthetic()
    report = producer_report_for(evidence)
    out = apply_synthetic(report, evidence)
    assert out["status"] == "READY_FOR_HEADER_AND_TINY_FIXTURE"
    assert out["blockers"] == []
    assert out["extra_layer_resolver_provenance_proven"] is True
    assert out["g2_admitted"] is False
    assert out["large_checkpoint_admitted"] is False
    assert out["runtime_execution_proven"] is False


def test_source_bundle_substitution_fails():
    evidence = observe_synthetic()
    report = producer_report_for(evidence)
    report["source_bundle_id"] = "0" * 64
    with pytest.raises(m.OfficialSourceMTPRoleError, match="OFFICIAL_SOURCE_REPORT_MISMATCH"):
        apply_synthetic(report, evidence)


def test_role_substitution_fails():
    evidence = observe_synthetic()
    report = producer_report_for(evidence)
    report["classified_extra_checkpoint_layers"][0]["role"] = "DECODER"
    with pytest.raises(m.OfficialSourceMTPRoleError, match="OFFICIAL_REPORT_ROLE_MISMATCH"):
        apply_synthetic(report, evidence)


def test_unclassified_extra_layer_fails():
    evidence = observe_synthetic()
    report = producer_report_for(evidence)
    report["unclassified_extra_checkpoint_layer_indices"] = [78]
    with pytest.raises(m.OfficialSourceMTPRoleError, match="UNCLASSIFIED_EXTRA_LAYER_REMAINS"):
        apply_synthetic(report, evidence)


def test_provenance_prestate_must_be_false():
    evidence = observe_synthetic()
    report = producer_report_for(evidence)
    report["extra_layer_resolver_provenance_proven"] = True
    with pytest.raises(m.OfficialSourceMTPRoleError, match="PROVENANCE_PRESTATE_INVALID"):
        apply_synthetic(report, evidence)


def test_blocker_omission_with_stale_producer_id_fails():
    evidence = observe_synthetic()
    legitimate = _with_producer_blockers(
        producer_report_for(evidence),
        [m.PROVENANCE_BLOCKER, "OTHER_BLOCKER"],
    )
    forged = copy.deepcopy(legitimate)
    forged["blockers"] = [m.PROVENANCE_BLOCKER]
    forged["status"] = "PARTIAL"
    with pytest.raises(m.OfficialSourceMTPRoleError, match="PR340_PRODUCER_LOGICAL_ID_MISMATCH"):
        apply_synthetic(forged, evidence, expected_id=legitimate["logical_id"])


def test_self_consistent_forged_blocker_set_fails_independent_expectation():
    evidence = observe_synthetic()
    legitimate = _with_producer_blockers(
        producer_report_for(evidence),
        [m.PROVENANCE_BLOCKER, "OTHER_BLOCKER"],
    )
    forged = _with_producer_blockers(legitimate, [m.PROVENANCE_BLOCKER])
    assert forged["logical_id"] == _independent_pr340_logical_id(forged)
    assert forged["logical_id"] != legitimate["logical_id"]
    with pytest.raises(m.OfficialSourceMTPRoleError, match="PR340_PRODUCER_EXPECTATION_MISMATCH"):
        apply_synthetic(forged, evidence, expected_id=legitimate["logical_id"])


def test_missing_independent_expected_producer_id_fails_closed():
    evidence = observe_synthetic()
    report = producer_report_for(evidence)
    old = m.OFFICIAL_INDEX_SHA256
    try:
        m.OFFICIAL_INDEX_SHA256 = evidence.index_sha256
        with pytest.raises(m.OfficialSourceMTPRoleError, match="PR340_EXPECTED_PRODUCER_LOGICAL_ID_REQUIRED"):
            m._apply_verified_source_role(
                report,
                evidence,
                expected_pr340_semantic_generation=m.PR340_PRODUCER_SEMANTIC_GENERATION,
            )
    finally:
        m.OFFICIAL_INDEX_SHA256 = old


def test_wrong_pr340_semantic_generation_fails_closed():
    evidence = observe_synthetic()
    report = producer_report_for(evidence)
    with pytest.raises(m.OfficialSourceMTPRoleError, match="PR340_PRODUCER_SEMANTIC_GENERATION_MISMATCH"):
        apply_synthetic(
            report,
            evidence,
            expected_generation="f" * 40,
        )
