import hashlib
import json
import unittest

import glm53_checkpoint_source_binding as source_binding
import glm53_mtp_checkpoint_classifier as mtp


def config(*, nextn=1):
    return {
        "n_routed_experts": 256,
        "hidden_size": 6144,
        "moe_intermediate_size": 2048,
        "num_hidden_layers": 78,
        "num_nextn_predict_layers": nextn,
        "quantization_config": {
            "quant_method": "fp8",
            "fmt": "e4m3",
            "weight_block_size": [128, 128],
        },
    }


def weight_map(*, include_mtp=True, extra_layer=None, missing_marker=None):
    wm = {}
    for expert in range(256):
        for projection in ("gate_proj", "up_proj", "down_proj"):
            wm[f"model.layers.3.mlp.experts.{expert}.{projection}.weight"] = "layer3.safetensors"
    # The metadata probe only needs one scale/quant companion to keep the generic
    # scale-layout blocker out of this isolated MTP classification fixture.
    wm["model.layers.3.mlp.experts.0.gate_proj.weight_scale_inv"] = "layer3.safetensors"

    if include_mtp:
        markers = (
            "model.layers.78.eh_proj.weight",
            "model.layers.78.enorm.weight",
            "model.layers.78.hnorm.weight",
            "model.layers.78.shared_head.norm.weight",
        )
        for key in markers:
            if missing_marker and key.startswith(f"model.layers.78.{missing_marker}"):
                continue
            wm[key] = "mtp.safetensors"
        wm["model.layers.78.self_attn.q_a_proj.weight"] = "mtp.safetensors"
    if extra_layer is not None:
        wm[f"model.layers.{extra_layer}.self_attn.q_a_proj.weight"] = "extra.safetensors"
    return wm


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def bundle_and_report(*, cfg=None, wm=None):
    cfg = config() if cfg is None else cfg
    wm = weight_map() if wm is None else wm
    cfg_raw = raw(cfg)
    index_raw = raw({"weight_map": wm})
    sources = source_binding.bind_checkpoint_sources(
        model_revision="a" * 40,
        config_raw_bytes=cfg_raw,
        expected_config_sha256=sha(cfg_raw),
        index_raw_bytes=index_raw,
        expected_index_sha256=sha(index_raw),
    )
    report = source_binding.source_bound_probe(
        sources=sources,
        airllm_revision="c92cea691412715a218306acb01fc9c2c681a8f2",
        security_hard_false_remote_code=True,
    )
    return sources, report


class GLM53MTPCheckpointClassifierTests(unittest.TestCase):
    def test_source_bound_mtp_signature_clears_only_mtp_blocker(self):
        sources, report = bundle_and_report()
        self.assertEqual([mtp.MTP_BLOCKER], report["blockers"])
        self.assertEqual("PARTIAL", report["status"])

        receipt = mtp.classify_mtp_checkpoint(sources=sources, report=report)
        self.assertEqual("NON_DECODER_MULTI_TOKEN_PREDICTION", receipt.classification)
        self.assertEqual((78,), receipt.mtp_layer_indices)
        self.assertFalse(receipt.g2_admitted)

        resolved = mtp.apply_mtp_classification(report, receipt)
        self.assertEqual([], resolved["blockers"])
        self.assertEqual("READY_FOR_HEADER_AND_TINY_FIXTURE", resolved["status"])
        self.assertFalse(resolved["g2_admitted"])
        self.assertFalse(resolved["large_checkpoint_admitted"])
        self.assertFalse(resolved["runtime_execution_proven"])

    def test_unrelated_blocker_survives_overlay(self):
        sources, report = bundle_and_report()
        report = dict(report)
        report["blockers"] = sorted(report["blockers"] + ["GLM53_CHUNK_MAPPING_REQUIRED"])
        receipt = mtp.classify_mtp_checkpoint(sources=sources, report=report)
        resolved = mtp.apply_mtp_classification(report, receipt)
        self.assertEqual(["GLM53_CHUNK_MAPPING_REQUIRED"], resolved["blockers"])
        self.assertEqual("PARTIAL", resolved["status"])

    def test_missing_marker_family_fails_closed(self):
        for marker in ("eh_proj", "enorm", "hnorm", "shared_head.norm"):
            sources, report = bundle_and_report(wm=weight_map(missing_marker=marker))
            with self.assertRaises(mtp.MTPClassificationError) as ctx:
                mtp.classify_mtp_checkpoint(sources=sources, report=report)
            self.assertEqual("MTP_MARKER_FAMILY_MISSING", ctx.exception.code)

    def test_extra_post_decoder_layer_fails_closed(self):
        sources, report = bundle_and_report(wm=weight_map(extra_layer=79))
        self.assertIn("GLM53_UNEXPECTED_CHECKPOINT_LAYER_CLASSIFICATION_REQUIRED", report["blockers"])
        with self.assertRaises(mtp.MTPClassificationError) as ctx:
            mtp.classify_mtp_checkpoint(sources=sources, report=report)
        self.assertEqual("MTP_EXTRA_LAYER_SET_MISMATCH", ctx.exception.code)

    def test_nextn_declaration_must_be_exactly_one(self):
        for nextn, expected in ((0, "NUM_NEXTN_PREDICT_LAYERS_REQUIRED"), (2, "MTP_LAYER_COUNT_UNSUPPORTED")):
            sources, report = bundle_and_report(cfg=config(nextn=nextn))
            with self.assertRaises(mtp.MTPClassificationError) as ctx:
                mtp.classify_mtp_checkpoint(sources=sources, report=report)
            self.assertEqual(expected, ctx.exception.code)

    def test_source_bundle_substitution_rejected(self):
        sources, report = bundle_and_report()
        report = dict(report)
        report["source_bundle_id"] = "b" * 64
        with self.assertRaises(mtp.MTPClassificationError) as ctx:
            mtp.classify_mtp_checkpoint(sources=sources, report=report)
        self.assertEqual("SOURCE_BUNDLE_MISMATCH", ctx.exception.code)

    def test_weight_map_substitution_rejected(self):
        sources, report = bundle_and_report()
        report = dict(report)
        report["weight_map_digest"] = "b" * 64
        with self.assertRaises(mtp.MTPClassificationError) as ctx:
            mtp.classify_mtp_checkpoint(sources=sources, report=report)
        self.assertEqual("SOURCE_WEIGHT_MAP_DIGEST_MISMATCH", ctx.exception.code)

    def test_overlay_requires_current_mtp_blocker(self):
        sources, report = bundle_and_report()
        receipt = mtp.classify_mtp_checkpoint(sources=sources, report=report)
        no_blocker = dict(report)
        no_blocker["blockers"] = []
        with self.assertRaises(mtp.MTPClassificationError) as ctx:
            mtp.apply_mtp_classification(no_blocker, receipt)
        self.assertEqual("MTP_BLOCKER_NOT_PRESENT", ctx.exception.code)

    def test_classification_digest_ignores_observation_clock(self):
        sources, first = bundle_and_report()
        second = dict(first)
        first["observation_time"] = "t1"
        second["observation_time"] = "t2"
        a = mtp.classify_mtp_checkpoint(sources=sources, report=first)
        b = mtp.classify_mtp_checkpoint(sources=sources, report=second)
        self.assertEqual(a.classification_digest, b.classification_digest)

    def test_serialized_receipt_never_promotes(self):
        sources, report = bundle_and_report()
        payload = mtp.classify_mtp_checkpoint(sources=sources, report=report).to_dict()
        self.assertFalse(payload["g2_admitted"])
        self.assertFalse(payload["large_checkpoint_admitted"])
        self.assertFalse(payload["runtime_execution_proven"])


if __name__ == "__main__":
    unittest.main()
