import hashlib
import json

import pytest

from tools.awj032 import glm53_official_mtp_role_source_appraiser as m


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def sources(*, nextn=1, include_layer79=False, include_marker=True):
    config = {
        "num_hidden_layers": 78,
        "num_nextn_predict_layers": nextn,
        "hidden_size": 6144,
    }
    wm = {
        "model.layers.0.input_layernorm.weight": "model-00001-of-00141.safetensors",
        "model.layers.77.input_layernorm.weight": "model-00140-of-00141.safetensors",
        "model.layers.78.self_attn.q_proj.weight": "model-00141-of-00141.safetensors",
    }
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


def report_for(evidence, blockers=None):
    if blockers is None:
        blockers = [m.PROVENANCE_BLOCKER]
    return {
        "schema": "GLM53CheckpointLayoutProbeV1",
        "model_revision": evidence.immutable_model_revision,
        "index_sha256": evidence.index_sha256,
        "num_hidden_layers": evidence.num_hidden_layers,
        "source_binding_proven": True,
        "source_bundle_id": evidence.source_bundle_id,
        "config_parsed_sha256": evidence.config_parsed_sha256,
        "index_parsed_sha256": evidence.index_parsed_sha256,
        "weight_map_digest": evidence.weight_map_digest,
        "extra_checkpoint_layer_indices": [78],
        "unexpected_extra_checkpoint_layer_indices": [78],
        "classified_extra_checkpoint_layers": [
            {"index": 78, "role": "MTP_NON_DECODER", "decoder_pager_membership": False}
        ],
        "unclassified_extra_checkpoint_layer_indices": [],
        "extra_layer_resolver_provenance_proven": False,
        "status": "PARTIAL",
        "blockers": list(blockers),
        "g2_admitted": False,
        "large_checkpoint_admitted": False,
        "runtime_execution_proven": False,
        "observation_time": "t1",
        "claim_ceiling": "METADATA_ONLY_NO_MODEL_WEIGHT_EFFECT",
        "logical_id": "old",
    }


def apply_synthetic(report, evidence):
    old = m.OFFICIAL_INDEX_SHA256
    try:
        m.OFFICIAL_INDEX_SHA256 = evidence.index_sha256
        return m._apply_verified_source_role(report, evidence)
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


def test_apply_removes_only_provenance_blocker():
    evidence = observe_synthetic()
    report = report_for(evidence, blockers=[m.PROVENANCE_BLOCKER, "OTHER_BLOCKER"])
    out = apply_synthetic(report, evidence)
    assert out["blockers"] == ["OTHER_BLOCKER"]
    assert out["status"] == "PARTIAL"
    assert out["extra_layer_resolver_provenance_proven"] is True
    assert out["extra_layer_resolver_provenance_method"] == "OFFICIAL_IMMUTABLE_SOURCE_DERIVATION"
    assert out["official_mtp_role_source_evidence_id"] == evidence.evidence_id


def test_clean_source_role_becomes_tiny_fixture_ready_only():
    evidence = observe_synthetic()
    out = apply_synthetic(report_for(evidence), evidence)
    assert out["status"] == "READY_FOR_HEADER_AND_TINY_FIXTURE"
    assert out["blockers"] == []
    assert out["extra_layer_resolver_provenance_proven"] is True
    assert out["g2_admitted"] is False
    assert out["large_checkpoint_admitted"] is False
    assert out["runtime_execution_proven"] is False


def test_source_bundle_substitution_fails():
    evidence = observe_synthetic()
    report = report_for(evidence)
    report["source_bundle_id"] = "0" * 64
    with pytest.raises(m.OfficialSourceMTPRoleError, match="OFFICIAL_SOURCE_REPORT_MISMATCH"):
        apply_synthetic(report, evidence)


def test_role_substitution_fails():
    evidence = observe_synthetic()
    report = report_for(evidence)
    report["classified_extra_checkpoint_layers"][0]["role"] = "DECODER"
    with pytest.raises(m.OfficialSourceMTPRoleError, match="OFFICIAL_REPORT_ROLE_MISMATCH"):
        apply_synthetic(report, evidence)


def test_unclassified_extra_layer_fails():
    evidence = observe_synthetic()
    report = report_for(evidence)
    report["unclassified_extra_checkpoint_layer_indices"] = [78]
    with pytest.raises(m.OfficialSourceMTPRoleError, match="UNCLASSIFIED_EXTRA_LAYER_REMAINS"):
        apply_synthetic(report, evidence)


def test_provenance_prestate_must_be_false():
    evidence = observe_synthetic()
    report = report_for(evidence)
    report["extra_layer_resolver_provenance_proven"] = True
    with pytest.raises(m.OfficialSourceMTPRoleError, match="PROVENANCE_PRESTATE_INVALID"):
        apply_synthetic(report, evidence)
