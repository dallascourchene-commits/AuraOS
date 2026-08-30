import copy
import hashlib
import json
import unittest

from tools.awj032.glm53_w2_header_bound_plan import W2HeaderBindingError
from tools.awj032.glm53_w2_strict_current_plan import compile_strict_current_w2_plan

MODEL = "7cda81930d6e4cef42f48555de830aa32ecdde28"
INDEX = "e0fe7f28c1f853d4824e4d796374e3dacf1fe470988773952c79b063768134bf"
HEADER = "8607b1b281f5ca8c7b166376e8f6d7eb9ca07f79200f6095f0f55ca35149ba56"
SHARD = "model-00038-of-00141.safetensors"


def report():
    return {
        "schema": "GLM53CheckpointLayoutProbeV1",
        "model_revision": MODEL,
        "index_sha256": INDEX,
        "logical_id": "probe-official-layer3-per-expert",
        "status": "READY_FOR_HEADER_AND_TINY_FIXTURE",
        "blockers": [],
        "layer": {
            "layer": 3,
            "layout": "PER_EXPERT_PHYSICAL_LAYOUT",
            "geometry": {
                "num_experts": 256,
                "hidden_size": 6144,
                "intermediate_size": 2048,
                "block_size": [128, 128],
            },
        },
    }


def weight_map():
    out = {}
    for eid in range(256):
        prefix = f"model.layers.3.mlp.experts.{eid}."
        shard = SHARD if eid == 0 else f"model-{40 + eid // 16:05d}-of-00141.safetensors"
        for role in ("gate_proj", "up_proj", "down_proj"):
            out[prefix + role + ".weight"] = shard
            out[prefix + role + ".weight_scale_inv"] = shard
    return out


def _receipt_digest(body):
    producer = {
        key: body[key]
        for key in (
            "repo_id",
            "model_revision",
            "index_sha256",
            "index_size_bytes",
            "selected_layer",
            "selected_expert",
            "entries",
            "payload_bytes_read",
            "g2_admitted",
            "runtime_executed",
            "authority",
            "schema",
        )
    }
    raw = json.dumps(producer, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.blake2b(raw, digest_size=20).hexdigest()


def evidence():
    prefix = "model.layers.3.mlp.experts.0."
    entries = [
        {"tensor_key": prefix + "gate_proj.weight", "shard_name": SHARD, "dtype": "F8_E4M3", "shape": [2048, 6144], "data_offsets": [4070207936, 4082790848], "header_sha256": HEADER},
        {"tensor_key": prefix + "gate_proj.weight_scale_inv", "shard_name": SHARD, "dtype": "F32", "shape": [16, 48], "data_offsets": [993728, 996800], "header_sha256": HEADER},
        {"tensor_key": prefix + "up_proj.weight", "shard_name": SHARD, "dtype": "F8_E4M3", "shape": [2048, 6144], "data_offsets": [4082790848, 4095373760], "header_sha256": HEADER},
        {"tensor_key": prefix + "up_proj.weight_scale_inv", "shard_name": SHARD, "dtype": "F32", "shape": [16, 48], "data_offsets": [996800, 999872], "header_sha256": HEADER},
        {"tensor_key": prefix + "down_proj.weight", "shard_name": SHARD, "dtype": "F8_E4M3", "shape": [6144, 2048], "data_offsets": [4057625024, 4070207936], "header_sha256": HEADER},
        {"tensor_key": prefix + "down_proj.weight_scale_inv", "shard_name": SHARD, "dtype": "F32", "shape": [48, 16], "data_offsets": [990656, 993728], "header_sha256": HEADER},
    ]
    body = {
        "repo_id": "zai-org/GLM-5.3",
        "model_revision": MODEL,
        "index_sha256": INDEX,
        "index_size_bytes": 11_359_251,
        "selected_layer": 3,
        "selected_expert": 0,
        "entries": entries,
        "payload_bytes_read": 0,
        "g2_admitted": False,
        "runtime_executed": False,
        "authority": False,
        "schema": "GLM53SafetensorsHeaderEvidenceV1",
    }
    body["receipt_digest"] = _receipt_digest(body)
    return body


def compile_it(ev=None):
    return compile_strict_current_w2_plan(
        report(),
        weight_map=weight_map(),
        header_evidence=evidence() if ev is None else ev,
        expected_model_revision=MODEL,
        expected_index_digest=INDEX,
    )


class StrictCurrentPlanTests(unittest.TestCase):
    def code(self, expected, fn):
        with self.assertRaises(W2HeaderBindingError) as ctx:
            fn()
        self.assertEqual(ctx.exception.code, expected)

    def test_official_w2_receipt_composes_with_current_pr350_owner(self):
        plan = compile_it()
        self.assertEqual(plan.inner_plan.binding_kind, "PER_EXPERT_INDEX")
        self.assertTrue(plan.inner_plan.representative_header_bound)
        self.assertEqual(plan.inner_plan.representative_layer, 3)
        self.assertEqual(plan.inner_plan.representative_expert, 0)
        self.assertFalse(plan.inner_plan.all_experts_header_uniformity_proven)
        self.assertTrue(plan.representative_header_bound)
        self.assertFalse(plan.all_experts_header_uniformity_proven)
        self.assertFalse(plan.g2_admitted)
        self.assertNotEqual(plan.source_plan_digest, plan.inner_plan.source_plan_digest)

    def test_impossible_weight_offset_span_fails_even_with_fresh_receipt(self):
        ev = evidence()
        ev["entries"][0]["data_offsets"] = [4070207936, 4070208036]
        ev["receipt_digest"] = _receipt_digest(ev)
        self.code("HEADER_BYTE_GEOMETRY_MISMATCH", lambda: compile_it(ev))

    def test_impossible_scale_offset_span_fails_even_with_fresh_receipt(self):
        ev = evidence()
        ev["entries"][1]["data_offsets"] = [993728, 993732]
        ev["receipt_digest"] = _receipt_digest(ev)
        self.code("HEADER_BYTE_GEOMETRY_MISMATCH", lambda: compile_it(ev))

    def test_header_change_changes_strict_plan_identity(self):
        first = compile_it()
        ev = evidence()
        ev["entries"][0]["header_sha256"] = "b" * 64
        ev["receipt_digest"] = _receipt_digest(ev)
        second = compile_it(ev)
        self.assertNotEqual(first.source_plan_digest, second.source_plan_digest)

    def test_representative_canary_never_universalizes(self):
        payload = compile_it().to_dict()
        self.assertTrue(payload["representative_header_bound"])
        self.assertFalse(payload["all_experts_header_uniformity_proven"])
        self.assertFalse(payload["g2_admitted"])
        self.assertFalse(payload["large_checkpoint_admitted"])
        self.assertFalse(payload["runtime_execution_proven"])
        self.assertFalse(payload["authority"])


if __name__ == "__main__":
    unittest.main()
