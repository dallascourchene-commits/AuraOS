import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

PATH = Path(__file__).with_name("glm53_checkpoint_source_binding.py")
SPEC = importlib.util.spec_from_file_location("glm53_checkpoint_source_binding", PATH)
m = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = m
assert SPEC.loader is not None
SPEC.loader.exec_module(m)


def raw(value):
    return json.dumps(value, indent=2, sort_keys=False).encode("utf-8")


def sha(value):
    return hashlib.sha256(value).hexdigest()


class SourceBindingTests(unittest.TestCase):
    def sources(self):
        cfg = raw({"hidden_size": 6144, "num_hidden_layers": 78})
        idx = raw({"metadata": {"total_size": 1}, "weight_map": {"model.layers.3.x": "s1"}})
        return m.bind_checkpoint_sources(
            model_revision="a" * 40,
            config_raw_bytes=cfg,
            expected_config_sha256=sha(cfg),
            index_raw_bytes=idx,
            expected_index_sha256=sha(idx),
        ), cfg, idx

    def test_hash_and_parse_same_raw_bytes(self):
        sources, cfg, idx = self.sources()
        self.assertEqual(sha(cfg), sources.config.raw_sha256)
        self.assertEqual(sha(idx), sources.index.raw_sha256)
        self.assertEqual({"model.layers.3.x": "s1"}, sources.index.mapping()["weight_map"])
        self.assertEqual(64, len(sources.config.parsed_sha256))
        self.assertEqual(64, len(sources.index.parsed_sha256))

    def test_digest_mismatch_fails_before_parse_use(self):
        cfg = raw({"hidden_size": 1})
        idx = raw({"weight_map": {"x": "s"}})
        with self.assertRaises(m.SourceBindingError) as ctx:
            m.bind_checkpoint_sources(
                model_revision="a" * 40,
                config_raw_bytes=cfg,
                expected_config_sha256="0" * 64,
                index_raw_bytes=idx,
                expected_index_sha256=sha(idx),
            )
        self.assertEqual("RAW_SHA256_MISMATCH", ctx.exception.code)

    def test_symbolic_revision_rejected(self):
        cfg = raw({"hidden_size": 1})
        idx = raw({"weight_map": {"x": "s"}})
        with self.assertRaises(m.SourceBindingError) as ctx:
            m.bind_checkpoint_sources(
                model_revision="main",
                config_raw_bytes=cfg,
                expected_config_sha256=sha(cfg),
                index_raw_bytes=idx,
                expected_index_sha256=sha(idx),
            )
        self.assertEqual("IMMUTABLE_MODEL_REVISION_REQUIRED", ctx.exception.code)

    def test_invalid_weight_map_fails_closed(self):
        cfg = raw({"hidden_size": 1})
        idx = raw({"weight_map": {"x": ""}})
        with self.assertRaises(m.SourceBindingError) as ctx:
            m.bind_checkpoint_sources(
                model_revision="b" * 40,
                config_raw_bytes=cfg,
                expected_config_sha256=sha(cfg),
                index_raw_bytes=idx,
                expected_index_sha256=sha(idx),
            )
        self.assertEqual("INDEX_WEIGHT_MAP_ENTRY_INVALID", ctx.exception.code)

    def test_probe_receives_only_bound_parsed_sources(self):
        sources, _, _ = self.sources()
        seen = {}

        def fake_probe(**kwargs):
            seen.update(kwargs)
            return {"status": "PARTIAL", "g2_admitted": False}

        report = m.source_bound_probe(
            sources=sources,
            airllm_revision="c" * 40,
            security_hard_false_remote_code=True,
            probe_fn=fake_probe,
        )
        self.assertEqual(sources.model_revision, seen["model_revision"])
        self.assertEqual(sources.config.raw_sha256, seen["config_sha256"])
        self.assertEqual(sources.index.raw_sha256, seen["index_sha256"])
        self.assertEqual(sources.index.mapping()["weight_map"], seen["weight_map"])
        self.assertTrue(report["source_binding_proven"])
        self.assertFalse(report["g2_admitted"])
        self.assertEqual(sources.source_bundle_id, report["source_bundle_id"])


if __name__ == "__main__":
    unittest.main()
