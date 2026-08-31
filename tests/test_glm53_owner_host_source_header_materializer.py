from __future__ import annotations

from io import BytesIO
import struct
import unittest
from unittest.mock import patch

from tools.quantization import aura_glm53_official_source_admission as source
from tools.quantization import aura_glm53_owner_host_source_header_materializer as s1


class _Headers(dict):
    def get(self, key, default=None):
        return super().get(key, default)


class _Response:
    def __init__(self, raw: bytes, *, status: int = 206, content_range: str = ""):
        self._stream = BytesIO(raw)
        self.status = status
        self.headers = _Headers({"Content-Range": content_range})

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, n: int = -1) -> bytes:
        return self._stream.read(n)

    def getcode(self) -> int:
        return self.status


class SourceHeaderMaterializerTests(unittest.TestCase):
    def test_parent_and_scope_constants_are_exact(self):
        self.assertEqual(s1.Q5_HEAD, "23c8345a1e3d5034ce88bea1ab32c69c1a9cf3f2")
        self.assertEqual(s1.Q7_HEAD, "7340091202f3f1a859841c3ec4314191f18fa1ad")
        self.assertEqual(s1.CONVERGENCE_COMMIT, "63a411a0eaea18bfbdf60346fe19bdc7fa93d397")
        self.assertLess(s1.Q5_AGGREGATE_E8_OVER_CONTROL, 1.0)
        self.assertEqual(s1.EXPERT_PREFIX, "model.layers.3.mlp.experts.0")

    def test_config_profile_is_accepted_by_existing_source_owner(self):
        observation = source.observe_official_config(s1.official_config_profile())
        self.assertEqual(observation.repository, source.OFFICIAL_REPO)
        self.assertEqual(observation.revision, source.OFFICIAL_COMMIT)
        self.assertEqual(observation.weight_block_size, (128, 128))
        self.assertEqual(observation.fp8_fmt, "e4m3")

    def test_k27_external_coordinate_is_retrieval_only_and_deterministic(self):
        url = s1.hf_resolve_url(source.OFFICIAL_INDEX_FILENAME)
        self.assertEqual(s1.k27_coordinate(url), (9, 13, 4))
        self.assertEqual(s1._sha(url.encode("utf-8")), "90caf7eda697ff95dcb4ab638cdece01312afc2db9fd68cb08156079a68d2cf6")

    def test_range_reader_requires_exact_partial_range(self):
        good = _Response(b"abcd", content_range="bytes 10-13/999")
        with patch.object(s1.urllib.request, "urlopen", return_value=good):
            self.assertEqual(s1.urllib_read_range("https://example.invalid/x", 10, 4), b"abcd")

        wrong_status = _Response(b"abcd", status=200, content_range="")
        with patch.object(s1.urllib.request, "urlopen", return_value=wrong_status):
            with self.assertRaisesRegex(ValueError, "RANGE_RESPONSE_NOT_PARTIAL"):
                s1.urllib_read_range("https://example.invalid/x", 10, 4)

        wrong_range = _Response(b"abcd", content_range="bytes 0-3/999")
        with patch.object(s1.urllib.request, "urlopen", return_value=wrong_range):
            with self.assertRaisesRegex(ValueError, "CONTENT_RANGE_MISMATCH"):
                s1.urllib_read_range("https://example.invalid/x", 10, 4)

    def test_header_length_is_bounded_before_second_fetch(self):
        oversized = struct.pack("<Q", s1.MAX_HEADER_PREFIX_BYTES + 1)
        with patch.object(s1, "urllib_read_range", return_value=oversized) as read_range:
            with self.assertRaisesRegex(ValueError, "SAFETENSORS_HEADER_BOUND_VIOLATION"):
                s1.materialize_header_prefix("model-00038-of-00141.safetensors")
        self.assertEqual(read_range.call_count, 1)

    def test_receipt_has_no_authority_promotion_surface(self):
        fields = s1.SourceHeaderMaterializationReceipt.__dataclass_fields__
        for name in (
            "tensor_payload_bytes_materialized",
            "model_execution_observed",
            "physical_io_performance_proven",
            "native_private_transformer_kv_accessed",
            "semantic_k27_authority_minted",
            "gate10_promoted",
            "execution_authorized_by_this_contract",
        ):
            self.assertIn(name, fields)


if __name__ == "__main__":
    unittest.main()
