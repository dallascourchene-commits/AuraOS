from __future__ import annotations

import inspect
import struct
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.quantization import aura_glm53_minimum_official_metadata_admission as q15


class Q15MinimumOfficialMetadataTests(unittest.TestCase):
    def _index_observation(self):
        return SimpleNamespace(
            sha256=q15.OFFICIAL_INDEX_SHA256,
            weight_map_sha256="a" * 64,
            tensor_count=123,
            shard_count=141,
        )

    def _green_disposition(self, **overrides):
        values = dict(
            source_admission_digest="b" * 64,
            disposition_digest="c" * 64,
            source_header_trial_eligible=True,
            source_bound_c2_request_admissible=True,
            blocker="NONE_HEADER_LEVEL_REQUEST_ADMISSIBLE",
            source_tensor_payload_bound=False,
            real_tensor_quantization_eligible=False,
            execution_authorized_by_this_contract=False,
            owner_host_execution_observed=False,
            physical_io_attested=False,
            semantic_k27_authority_minted=False,
            native_private_transformer_kv_accessed=False,
            gate10_promoted=False,
        )
        values.update(overrides)
        return SimpleNamespace(**values)

    def test_q15_is_exactly_two_fresh_parent_composition(self):
        self.assertEqual(
            q15.CONVERGENCE_COMMIT,
            "b8b17171ef5538478505530eb05e22ff4ea7365d",
        )
        self.assertEqual(
            (q15.Q7_PROOF_HEAD, q15.Q6_PROOF_HEAD),
            (
                "7340091202f3f1a859841c3ec4314191f18fa1ad",
                "6906337dd6e75f49a70a84652bfd9ab70d967eef",
            ),
        )
        self.assertEqual(q15.Q7_RUN, 33400557094)
        self.assertEqual(q15.Q6_RUN, 33401482324)

    def test_public_materializer_has_no_authority_or_payload_escape_hatch(self):
        params = set(inspect.signature(q15.materialize_minimum_official_metadata).parameters)
        self.assertEqual(params, {"full_fetch", "range_fetch"})
        forbidden = {
            "eligible",
            "admitted",
            "execution_authorized",
            "payload",
            "gate10",
            "semantic_k27_authority",
        }
        self.assertTrue(params.isdisjoint(forbidden))

    def test_header_prefix_uses_only_length_then_exact_header_range(self):
        calls = []

        def range_fetch(_url: str, start: int, length: int) -> bytes:
            calls.append((start, length))
            if (start, length) == (0, 8):
                return struct.pack("<Q", 16)
            if (start, length) == (8, 16):
                return b"x" * 16
            raise AssertionError((start, length))

        prefix, header_len, header_sha = q15._fetch_header_prefix(
            "model-00038-of-00141.safetensors", range_fetch=range_fetch
        )
        self.assertEqual(calls, [(0, 8), (8, 16)])
        self.assertEqual(header_len, 16)
        self.assertEqual(len(prefix), 24)
        self.assertEqual(len(header_sha), 64)

    def test_materializer_closes_only_metadata_cone(self):
        shard = "model-00038-of-00141.safetensors"
        index_obs = self._index_observation()
        disposition = self._green_disposition()

        def full_fetch(url: str, _maximum: int) -> bytes:
            return b"{}" if url.endswith("config.json?download=true") else b"index"

        def range_fetch(_url: str, start: int, length: int) -> bytes:
            if (start, length) == (0, 8):
                return struct.pack("<Q", 16)
            if (start, length) == (8, 16):
                return b"h" * 16
            raise AssertionError((start, length))

        with patch.object(q15, "verify_official_index_bytes", return_value=index_obs), patch.object(
            q15,
            "extract_expert_bundle",
            return_value={f"{q15.EXPERT_PREFIX}.gate_proj.weight": shard},
        ), patch.object(
            q15, "admit_source_bound_c2_request", return_value=disposition
        ) as admit:
            out = q15.materialize_minimum_official_metadata(
                full_fetch=full_fetch, range_fetch=range_fetch
            )

        admit.assert_called_once()
        self.assertTrue(out["source_header_trial_eligible"])
        self.assertTrue(out["source_bound_c2_request_admissible"])
        self.assertEqual(out["minimum_metadata_evidence_cone_after"], [])
        self.assertEqual(out["tensor_payload_bytes_materialized"], 0)
        self.assertFalse(out["source_tensor_payload_bound"])
        self.assertFalse(out["real_tensor_quantization_eligible"])
        self.assertFalse(out["execution_authorized_by_this_contract"])
        self.assertFalse(out["model_execution_observed"])
        self.assertFalse(out["full_tensor_or_model_claim_earned"])
        self.assertEqual(len(out["receipt_digest"]), 64)

    def test_execution_widening_fails_closed_even_if_source_gate_green(self):
        shard = "model-00038-of-00141.safetensors"

        def full_fetch(url: str, _maximum: int) -> bytes:
            return b"{}" if url.endswith("config.json?download=true") else b"index"

        def range_fetch(_url: str, start: int, length: int) -> bytes:
            if (start, length) == (0, 8):
                return struct.pack("<Q", 8)
            return b"h" * length

        with patch.object(q15, "verify_official_index_bytes", return_value=self._index_observation()), patch.object(
            q15,
            "extract_expert_bundle",
            return_value={f"{q15.EXPERT_PREFIX}.gate_proj.weight": shard},
        ), patch.object(
            q15,
            "admit_source_bound_c2_request",
            return_value=self._green_disposition(execution_authorized_by_this_contract=True),
        ):
            with self.assertRaisesRegex(RuntimeError, "nonpromotion ceiling"):
                q15.materialize_minimum_official_metadata(
                    full_fetch=full_fetch, range_fetch=range_fetch
                )

    def test_empty_representative_shard_cone_fails_closed(self):
        def full_fetch(url: str, _maximum: int) -> bytes:
            return b"{}" if url.endswith("config.json?download=true") else b"index"

        with patch.object(q15, "verify_official_index_bytes", return_value=self._index_observation()), patch.object(
            q15, "extract_expert_bundle", return_value={}
        ):
            with self.assertRaisesRegex(RuntimeError, "unexpectedly empty"):
                q15.materialize_minimum_official_metadata(full_fetch=full_fetch)


if __name__ == "__main__":
    unittest.main()
