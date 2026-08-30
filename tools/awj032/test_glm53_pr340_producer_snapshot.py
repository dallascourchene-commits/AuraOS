import hashlib
import json
import unittest
from unittest.mock import patch

from tools.awj032 import glm53_pr340_producer_snapshot as s
from tools.awj032.glm53_checkpoint_source_binding import bind_checkpoint_sources


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def fixture_sources():
    config = {
        "num_hidden_layers": 78,
        "num_nextn_predict_layers": 1,
        "hidden_size": 4,
        "n_routed_experts": 2,
        "moe_intermediate_size": 2,
        "quantization_config": {"quant_method": "fp8", "weight_block_size": [2, 2]},
    }
    wm = {
        "model.layers.77.input_layernorm.weight": "model-00140-of-00141.safetensors",
        "model.layers.78.eh_proj.weight": "model-00141-of-00141.safetensors",
    }
    for expert in range(2):
        for role in ("gate_proj", "up_proj", "down_proj"):
            base = f"model.layers.3.mlp.experts.{expert}.{role}"
            wm[f"{base}.weight"] = "model-00038-of-00141.safetensors"
            wm[f"{base}.weight_scale_inv"] = "model-00038-of-00141.safetensors"
    index = {"metadata": {"total_size": 123}, "weight_map": wm}
    config_raw = _canonical(config)
    index_raw = _canonical(index)
    bundle = bind_checkpoint_sources(
        model_revision="a" * 40,
        config_raw_bytes=config_raw,
        expected_config_sha256=hashlib.sha256(config_raw).hexdigest(),
        index_raw_bytes=index_raw,
        expected_index_sha256=hashlib.sha256(index_raw).hexdigest(),
    )
    return bundle


class PR340ProducerSnapshotTests(unittest.TestCase):
    def patched(self, sources):
        return (
            patch.object(s, "OFFICIAL_REVISION", sources.model_revision),
            patch.object(s, "OFFICIAL_CONFIG_SHA256", sources.config.raw_sha256),
            patch.object(s, "OFFICIAL_INDEX_SHA256", sources.index.raw_sha256),
            patch.object(s, "OFFICIAL_SOURCE_BUNDLE_ID", sources.source_bundle_id),
            patch.object(s, "CURRENT_AIRLLM_SECURITY_GENERATION", "b" * 40),
            patch.object(s, "PR340_PRODUCER_BASE_HEAD", "c" * 40),
        )

    def emit(self):
        sources = fixture_sources()
        patches = self.patched(sources)
        for p in patches:
            p.start()
        try:
            return s.emit_pr340_producer_snapshot(
                sources,
                producer_execution_head="d" * 40,
                observation_time="volatile-time",
            )
        finally:
            for p in reversed(patches):
                p.stop()

    def test_real_source_bound_path_emits_only_resolver_blocker(self):
        snapshot, report = self.emit()
        self.assertEqual(("GLM53_MTP_RESOLVER_PROVENANCE_REQUIRED",), snapshot.blocker_set)
        self.assertEqual(["GLM53_MTP_RESOLVER_PROVENANCE_REQUIRED"], report["blockers"])
        self.assertTrue(snapshot.source_binding_proven)
        self.assertFalse(snapshot.producer_snapshot_verified_by_external_registry)
        self.assertFalse(snapshot.g2_admitted)
        self.assertFalse(snapshot.runtime_execution_proven)
        self.assertFalse(snapshot.authority)

    def test_final_digest_binds_fields_appended_after_legacy_logical_id(self):
        _, report = self.emit()
        baseline = s.final_source_bound_report_digest(report)
        mutated = dict(report)
        mutated["source_bundle_id"] = "0" * 64
        self.assertNotEqual(baseline, s.final_source_bound_report_digest(mutated))
        mutated = dict(report)
        mutated["source_binding_proven"] = False
        self.assertNotEqual(baseline, s.final_source_bound_report_digest(mutated))

    def test_final_digest_binds_blocker_classification_and_claim_ceiling(self):
        _, report = self.emit()
        baseline = s.final_source_bound_report_digest(report)
        for key, value in (
            ("blockers", []),
            ("classified_extra_checkpoint_layers", []),
            ("claim_ceiling", "WIDENED"),
            ("g2_admitted", True),
        ):
            mutated = dict(report)
            mutated[key] = value
            with self.subTest(key=key):
                self.assertNotEqual(baseline, s.final_source_bound_report_digest(mutated))

    def test_observation_time_and_legacy_logical_id_are_not_final_identity(self):
        _, report = self.emit()
        baseline = s.final_source_bound_report_digest(report)
        mutated = dict(report)
        mutated["observation_time"] = "different"
        mutated["logical_id"] = "f" * 64
        self.assertEqual(baseline, s.final_source_bound_report_digest(mutated))

    def test_snapshot_execution_head_is_receipt_identity_not_report_identity(self):
        sources = fixture_sources()
        patches = self.patched(sources)
        for p in patches:
            p.start()
        try:
            a, _ = s.emit_pr340_producer_snapshot(sources, producer_execution_head="d" * 40)
            b, _ = s.emit_pr340_producer_snapshot(sources, producer_execution_head="e" * 40)
        finally:
            for p in reversed(patches):
                p.stop()
        self.assertEqual(a.final_report_digest, b.final_report_digest)
        self.assertNotEqual(a.snapshot_digest, b.snapshot_digest)

    def test_wrong_source_identity_fails_before_report(self):
        sources = fixture_sources()
        with self.assertRaises(s.PR340ProducerSnapshotError):
            s.emit_pr340_producer_snapshot(sources, producer_execution_head="d" * 40)

    def test_execution_head_is_exact_sha(self):
        sources = fixture_sources()
        patches = self.patched(sources)
        for p in patches:
            p.start()
        try:
            with self.assertRaises(s.PR340ProducerSnapshotError):
                s.emit_pr340_producer_snapshot(sources, producer_execution_head="main")
        finally:
            for p in reversed(patches):
                p.stop()


if __name__ == "__main__":
    unittest.main()
