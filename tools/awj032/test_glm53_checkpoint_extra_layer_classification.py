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

MODEL = "a" * 40
INDEX = "d" * 64
EVIDENCE_DIGEST = "e" * 64


def report(*, extra=(78,), unexpected=(), blockers=None):
    if blockers is None:
        blockers = ["GLM53_MTP_CHECKPOINT_CLASSIFICATION_REQUIRED"]
        if unexpected:
            blockers.append("GLM53_UNEXPECTED_CHECKPOINT_LAYER_CLASSIFICATION_REQUIRED")
    return {
        "schema": "GLM53CheckpointLayoutProbeV1",
        "model_revision": MODEL,
        "config_sha256": "c" * 64,
        "index_sha256": INDEX,
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


def classification(*, roles=((78, "MTP_NON_DECODER"),), index_sha=None, evidence_digest=None):
    return c.CheckpointExtraLayerClassification(
        model_revision=MODEL,
        index_sha256=index_sha or INDEX,
        num_hidden_layers=78,
        roles=roles,
        evidence_ref="drive:glm53-mtp-role",
        evidence_digest=evidence_digest or EVIDENCE_DIGEST,
        evidence_generation="gen:20260830-1",
        resolver_ref="aura:source-evidence-resolver",
        resolver_generation="resolver:1",
    )


def evidence(
    *,
    roles=((78, "MTP_NON_DECODER"),),
    index_sha=None,
    evidence_digest=None,
    resolver_generation="resolver:1",
    current=True,
):
    return c.CheckpointExtraLayerEvidenceObservation(
        evidence_ref="drive:glm53-mtp-role",
        evidence_digest=evidence_digest or EVIDENCE_DIGEST,
        evidence_generation="gen:20260830-1",
        resolver_ref="aura:source-evidence-resolver",
        resolver_generation=resolver_generation,
        resolution_receipt_ref="drive:glm53-mtp-role-resolution",
        model_revision=MODEL,
        index_sha256=index_sha or INDEX,
        num_hidden_layers=78,
        roles=roles,
        evidence_current=current,
    )


def raw(value):
    return json.dumps(value, sort_keys=True).encode("utf-8")


def sha(value):
    return hashlib.sha256(value).hexdigest()


class ExtraLayerClassificationTests(unittest.TestCase):
    def test_exact_current_evidence_discharges_role_but_not_resolver_provenance(self):
        out = c.apply_extra_layer_classification(report(), classification(), evidence())
        self.assertEqual([c.RESOLVER_PROVENANCE_BLOCKER], out["blockers"])
        self.assertEqual("PARTIAL", out["status"])
        self.assertEqual(
            [{"index": 78, "role": "MTP_NON_DECODER", "decoder_pager_membership": False}],
            out["classified_extra_checkpoint_layers"],
        )
        self.assertTrue(out["extra_layer_evidence_observation"]["evidence_current"])
        self.assertFalse(out["extra_layer_resolver_provenance_proven"])
        self.assertNotEqual("old", out["logical_id"])

    def test_classification_without_resolver_observation_cannot_clear_blocker(self):
        with self.assertRaises(c.ExtraLayerClassificationError) as ctx:
            c.apply_extra_layer_classification(report(), classification(), None)
        self.assertEqual("EXTRA_LAYER_EVIDENCE_REQUIRED", ctx.exception.code)

    def test_arbitrary_evidence_digest_mismatch_fails_closed(self):
        with self.assertRaises(c.ExtraLayerClassificationError) as ctx:
            c.apply_extra_layer_classification(
                report(),
                classification(),
                evidence(evidence_digest="f" * 64),
            )
        self.assertEqual("EXTRA_LAYER_EVIDENCE_MISMATCH", ctx.exception.code)
        self.assertIn("evidence_digest", ctx.exception.detail)

    def test_stale_evidence_cannot_clear_blocker(self):
        with self.assertRaises(c.ExtraLayerClassificationError) as ctx:
            c.apply_extra_layer_classification(
                report(), classification(), evidence(current=False)
            )
        self.assertEqual("EXTRA_LAYER_EVIDENCE_CURRENTNESS_REQUIRED", ctx.exception.code)

    def test_resolver_generation_mismatch_fails_closed(self):
        with self.assertRaises(c.ExtraLayerClassificationError) as ctx:
            c.apply_extra_layer_classification(
                report(),
                classification(),
                evidence(resolver_generation="resolver:2"),
            )
        self.assertEqual("EXTRA_LAYER_EVIDENCE_MISMATCH", ctx.exception.code)
        self.assertIn("resolver_generation", ctx.exception.detail)

    def test_wrong_index_generation_fails_closed_even_when_evidence_agrees(self):
        wrong = "f" * 64
        with self.assertRaises(c.ExtraLayerClassificationError) as ctx:
            c.apply_extra_layer_classification(
                report(),
                classification(index_sha=wrong),
                evidence(index_sha=wrong),
            )
        self.assertEqual("EXTRA_LAYER_CLASSIFICATION_SOURCE_MISMATCH", ctx.exception.code)

    def test_decoder_layer_cannot_be_relabelled_mtp(self):
        roles = ((77, "MTP_NON_DECODER"),)
        with self.assertRaises(c.ExtraLayerClassificationError) as ctx:
            c.apply_extra_layer_classification(
                report(), classification(roles=roles), evidence(roles=roles)
            )
        self.assertEqual("DECODER_LAYER_CLASSIFICATION_FORBIDDEN", ctx.exception.code)

    def test_unclassified_layer79_keeps_unexpected_and_resolver_blockers(self):
        out = c.apply_extra_layer_classification(
            report(extra=(78, 79), unexpected=(79,)), classification(), evidence()
        )
        self.assertNotIn("GLM53_MTP_CHECKPOINT_CLASSIFICATION_REQUIRED", out["blockers"])
        self.assertIn(c.RESOLVER_PROVENANCE_BLOCKER, out["blockers"])
        self.assertIn(
            "GLM53_UNEXPECTED_CHECKPOINT_LAYER_CLASSIFICATION_REQUIRED", out["blockers"]
        )
        self.assertEqual([79], out["unclassified_extra_checkpoint_layer_indices"])
        self.assertEqual("PARTIAL", out["status"])

    def test_classification_cannot_clear_unrelated_blockers(self):
        out = c.apply_extra_layer_classification(
            report(
                blockers=[
                    "GLM53_MTP_CHECKPOINT_CLASSIFICATION_REQUIRED",
                    "GLM53_FP8_SCALE_LAYOUT_UNRESOLVED",
                ]
            ),
            classification(),
            evidence(),
        )
        self.assertEqual(
            ["GLM53_FP8_SCALE_LAYOUT_UNRESOLVED", c.RESOLVER_PROVENANCE_BLOCKER],
            out["blockers"],
        )
        self.assertEqual("PARTIAL", out["status"])

    def test_effect_ceiling_remains_hard_false(self):
        out = c.apply_extra_layer_classification(report(), classification(), evidence())
        self.assertFalse(out["large_checkpoint_admitted"])
        self.assertFalse(out["g2_admitted"])
        self.assertFalse(out["runtime_execution_proven"])
        self.assertEqual(0, out["provider_calls"])

    def test_source_bound_probe_requires_separate_resolver_observation(self):
        cfg = raw({"hidden_size": 6144, "num_hidden_layers": 78})
        idx = raw({"weight_map": {"model.layers.78.mtp.weight": "s1"}})
        sources = s.bind_checkpoint_sources(
            model_revision=MODEL,
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
            evidence_ref="drive:glm53-mtp-role",
            evidence_digest=EVIDENCE_DIGEST,
            evidence_generation="gen:20260830-1",
            resolver_ref="aura:source-evidence-resolver",
            resolver_generation="resolver:1",
        )
        obs = c.CheckpointExtraLayerEvidenceObservation(
            evidence_ref=cls.evidence_ref,
            evidence_digest=cls.evidence_digest,
            evidence_generation=cls.evidence_generation,
            resolver_ref=cls.resolver_ref,
            resolver_generation=cls.resolver_generation,
            resolution_receipt_ref="drive:glm53-mtp-role-resolution",
            model_revision=sources.model_revision,
            index_sha256=sources.index.raw_sha256,
            num_hidden_layers=78,
            roles=cls.roles,
            evidence_current=True,
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

        with self.assertRaises(c.ExtraLayerClassificationError) as ctx:
            s.source_bound_probe(
                sources=sources,
                airllm_revision="b" * 40,
                security_hard_false_remote_code=True,
                extra_layer_classification=cls,
                probe_fn=fake_probe,
            )
        self.assertEqual("EXTRA_LAYER_EVIDENCE_REQUIRED", ctx.exception.code)

        out = s.source_bound_probe(
            sources=sources,
            airllm_revision="b" * 40,
            security_hard_false_remote_code=True,
            extra_layer_classification=cls,
            extra_layer_evidence_observation=obs,
            probe_fn=fake_probe,
        )
        self.assertEqual("PARTIAL", out["status"])
        self.assertEqual([c.RESOLVER_PROVENANCE_BLOCKER], out["blockers"])
        self.assertTrue(out["source_binding_proven"])
        self.assertFalse(out["extra_layer_resolver_provenance_proven"])
        self.assertFalse(out["g2_admitted"])


if __name__ == "__main__":
    unittest.main()