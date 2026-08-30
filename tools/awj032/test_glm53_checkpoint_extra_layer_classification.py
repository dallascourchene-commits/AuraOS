import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).parent


def load(name):
    path = ROOT / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


c = load("glm53_checkpoint_extra_layer_classification")
s = load("glm53_checkpoint_source_binding")


def report(*, extra=(78,), unexpected=(), blockers=None):
    if blockers is None:
        blockers = ["GLM53_MTP_CHECKPOINT_CLASSIFICATION_REQUIRED"]
        if unexpected:
            blockers.append("GLM53_UNEXPECTED_CHECKPOINT_LAYER_CLASSIFICATION_REQUIRED")
    return {
        "schema": "GLM53CheckpointLayoutProbeV1",
        "model_revision": "a" * 40,
        "config_sha256": "c" * 64,
        "index_sha256": "i" * 64,
        "airllm_revision": "b" * 40,
        "security_hard_false_remote_code": True,
        "representative_sparse_layer": 3,
        "layer": {"layout": "PER_EXPERT_PHYSICAL_LAYOUT"},
        "num_hidden_layers": 78,
        "checkpoint_layer_indices": [3, *extra],
        "extra_checkpoint_layer_indices": list(extra),
        "unexpected_extra_checkpoint_layer_indices": list(unexpected),
        "mtp_index_present": 78 in extra,
        "status": "PARTIAL",
        "blockers": list(blockers),
        "large_checkpoint_admitted": False,
        "g2_admitted": False,
        "runtime_execution_proven": False,
        "provider_calls": 0,
        "logical_id": "old",
        "observation_time": "t1",
        "claim_ceiling": "METADATA_ONLY_NO_MODEL_WEIGHT_EFFECT",
    }


def classification(*, roles=((78, "MTP_NON_DECODER"),), index_sha=None):
    return c.CheckpointExtraLayerClassification(
        model_revision="a" * 40,
        index_sha256=index_sha or "i" * 64,
        num_hidden_layers=78,
        roles=roles,
        provenance_ref="drive://mtp-role/current",
    )


def raw(value):
    return json.dumps(value, sort_keys=True).encode("utf-8")


def sha(value):
    return hashlib.sha256(value).hexdigest()


class ExtraLayerClassificationTests(unittest.TestCase):
    def test_exact_mtp_classification_discharges_only_mtp_blocker(self):
        r = c.apply_extra_layer_classification(report(), classification())
        self.assertEqual([], r["blockers"])
        self.assertEqual("READY_FOR_HEADER_AND_TINY_FIXTURE", r["status"])
        self.assertEqual(
            [{"index": 78, "role": "MTP_NON_DECODER", "decoder_pager_membership": False}],
            r["classified_extra_checkpoint_layers"],
        )
        self.assertEqual([], r["unclassified_extra_checkpoint_layer_indices"])
        self.assertNotEqual("old", r["logical_id"])

    def test_wrong_index_generation_fails_closed(self):
        with self.assertRaises(c.ExtraLayerClassificationError) as ctx:
            c.apply_extra_layer_classification(
                report(), classification(index_sha="x" * 64)
            )
        self.assertEqual("EXTRA_LAYER_CLASSIFICATION_SOURCE_MISMATCH", ctx.exception.code)

    def test_decoder_layer_cannot_be_relabelled_mtp(self):
        with self.assertRaises(c.ExtraLayerClassificationError) as ctx:
            c.apply_extra_layer_classification(
                report(), classification(roles=((77, "MTP_NON_DECODER"),))
            )
        self.assertEqual("DECODER_LAYER_CLASSIFICATION_FORBIDDEN", ctx.exception.code)

    def test_unclassified_layer79_keeps_unexpected_blocker(self):
        r = c.apply_extra_layer_classification(
            report(extra=(78, 79), unexpected=(79,)), classification()
        )
        self.assertNotIn("GLM53_MTP_CHECKPOINT_CLASSIFICATION_REQUIRED", r["blockers"])
        self.assertIn(
            "GLM53_UNEXPECTED_CHECKPOINT_LAYER_CLASSIFICATION_REQUIRED", r["blockers"]
        )
        self.assertEqual([79], r["unclassified_extra_checkpoint_layer_indices"])
        self.assertEqual("PARTIAL", r["status"])

    def test_classification_cannot_clear_unrelated_blockers(self):
        r = c.apply_extra_layer_classification(
            report(
                blockers=[
                    "GLM53_MTP_CHECKPOINT_CLASSIFICATION_REQUIRED",
                    "GLM53_FP8_SCALE_LAYOUT_UNRESOLVED",
                ]
            ),
            classification(),
        )
        self.assertEqual(["GLM53_FP8_SCALE_LAYOUT_UNRESOLVED"], r["blockers"])
        self.assertEqual("PARTIAL", r["status"])

    def test_effect_ceiling_remains_hard_false(self):
        r = c.apply_extra_layer_classification(report(), classification())
        self.assertFalse(r["large_checkpoint_admitted"])
        self.assertFalse(r["g2_admitted"])
        self.assertFalse(r["runtime_execution_proven"])
        self.assertEqual(0, r["provider_calls"])

    def test_source_bound_probe_is_the_discharge_channel(self):
        cfg = raw({"hidden_size": 6144, "num_hidden_layers": 78})
        idx = raw({"weight_map": {"model.layers.78.mtp.weight": "s1"}})
        sources = s.bind_checkpoint_sources(
            model_revision="a" * 40,
            config_raw_bytes=cfg,
            expected_config_sha256=sha(cfg),
            index_raw_bytes=idx,
            expected_index_sha256=sha(idx),
        )
        cls = c.CheckpointExtraLayerClassification(
            model_revision=sources.model_revision,
            index_sha256=sources.index.raw_sha256,
            num_hidden_layers=78,
            roles=((78, "MTP_NON_DECODER"),),
            provenance_ref="drive://mtp-role/current",
        )

        def fake_probe(**kwargs):
            return {
                "schema": "GLM53CheckpointLayoutProbeV1",
                "model_revision": kwargs["model_revision"],
                "config_sha256": kwargs["config_sha256"],
                "index_sha256": kwargs["index_sha256"],
                "airllm_revision": kwargs["airllm_revision"],
                "security_hard_false_remote_code": True,
                "representative_sparse_layer": 3,
                "layer": {"layout": "PER_EXPERT_PHYSICAL_LAYOUT"},
                "num_hidden_layers": 78,
                "checkpoint_layer_indices": [78],
                "extra_checkpoint_layer_indices": [78],
                "unexpected_extra_checkpoint_layer_indices": [],
                "mtp_index_present": True,
                "status": "PARTIAL",
                "blockers": ["GLM53_MTP_CHECKPOINT_CLASSIFICATION_REQUIRED"],
                "large_checkpoint_admitted": False,
                "g2_admitted": False,
                "runtime_execution_proven": False,
                "provider_calls": 0,
                "logical_id": "pre",
                "observation_time": kwargs["observation_time"],
                "claim_ceiling": "METADATA_ONLY_NO_MODEL_WEIGHT_EFFECT",
            }

        out = s.source_bound_probe(
            sources=sources,
            airllm_revision="b" * 40,
            security_hard_false_remote_code=True,
            extra_layer_classification=cls,
            probe_fn=fake_probe,
        )
        self.assertEqual("READY_FOR_HEADER_AND_TINY_FIXTURE", out["status"])
        self.assertEqual([], out["blockers"])
        self.assertTrue(out["source_binding_proven"])
        self.assertFalse(out["g2_admitted"])


if __name__ == "__main__":
    unittest.main()
