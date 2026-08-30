import copy
import hashlib
import json
import unittest

from tools.awj032.glm53_layout_binding_bridge import LayoutBindingError, compile_pager_source_plan

MODEL = "glm53-pinned-revision"
INDEX = "index-pinned-digest"
GATE = "model.layers.3.mlp.experts.gate_up_proj.weight"
DOWN = "model.layers.3.mlp.experts.down_proj.weight"
GS = "model.layers.3.mlp.experts.gate_up_proj.weight_scale_inv"
DS = "model.layers.3.mlp.experts.down_proj.weight_scale_inv"


def packed_fixture():
    report = {
        "schema": "GLM53CheckpointLayoutProbeV1",
        "model_revision": MODEL,
        "index_sha256": INDEX,
        "logical_id": "probe-packed",
        "status": "READY_FOR_HEADER_AND_TINY_FIXTURE",
        "blockers": [],
        "layer": {
            "layer": 3,
            "layout": "PACKED_PHYSICAL_LAYOUT",
            "packed_gate_key": GATE,
            "packed_down_key": DOWN,
            "scale_keys": [GS, DS],
            "geometry": {"num_experts": 256, "block_size": [128, 128]},
        },
        "observation_time": "t1",
    }
    wm = {GATE: "s10", GS: "s10", DOWN: "s11", DS: "s11"}
    hs = {
        GATE: {"shape": [256, 4096, 6144], "dtype": "F8_E4M3", "shard": "s10", "header_digest": "hg"},
        GS: {"shape": [256, 32, 48], "dtype": "F32", "shard": "s10", "header_digest": "hgs"},
        DOWN: {"shape": [256, 6144, 2048], "dtype": "F8_E4M3", "shard": "s11", "header_digest": "hd"},
        DS: {"shape": [256, 48, 16], "dtype": "F32", "shard": "s11", "header_digest": "hds"},
    }
    return report, wm, hs


def per_expert_fixture():
    report = {
        "schema": "GLM53CheckpointLayoutProbeV1",
        "model_revision": MODEL,
        "index_sha256": INDEX,
        "logical_id": "probe-per-expert",
        "status": "READY_FOR_HEADER_AND_TINY_FIXTURE",
        "blockers": [],
        "layer": {
            "layer": 3,
            "layout": "PER_EXPERT_PHYSICAL_LAYOUT",
            "geometry": {"num_experts": 256, "block_size": [128, 128]},
        },
    }
    wm = {}
    for eid in range(256):
        for proj in ("gate_proj", "up_proj", "down_proj"):
            key = f"model.layers.3.mlp.experts.{eid}.{proj}.weight"
            scale = f"model.layers.3.mlp.experts.{eid}.{proj}.weight_scale_inv"
            wm[key] = f"shard-{eid // 16:02d}"
            wm[scale] = f"shard-{eid // 16:02d}"
    return report, wm


def refresh_receipt(evidence):
    body = copy.deepcopy(evidence)
    body.pop("receipt_digest", None)
    evidence["receipt_digest"] = hashlib.blake2b(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(),
        digest_size=20,
    ).hexdigest()
    return evidence


def per_expert_header_fixture(wm, *, expert=0):
    prefix = f"model.layers.3.mlp.experts.{expert}."
    rows = [
        ("gate_proj.weight", "F8_E4M3", [2048, 6144], [100, 200]),
        ("gate_proj.weight_scale_inv", "F32", [16, 48], [200, 220]),
        ("up_proj.weight", "F8_E4M3", [2048, 6144], [220, 320]),
        ("up_proj.weight_scale_inv", "F32", [16, 48], [320, 340]),
        ("down_proj.weight", "F8_E4M3", [6144, 2048], [340, 440]),
        ("down_proj.weight_scale_inv", "F32", [48, 16], [440, 460]),
    ]
    entries = []
    for suffix, dtype, shape, offsets in rows:
        key = prefix + suffix
        entries.append(
            {
                "tensor_key": key,
                "shard_name": wm[key],
                "dtype": dtype,
                "shape": shape,
                "data_offsets": offsets,
                "header_sha256": "a" * 64,
            }
        )
    evidence = {
        "repo_id": "zai-org/GLM-5.3",
        "model_revision": MODEL,
        "index_sha256": INDEX,
        "index_size_bytes": 11_359_251,
        "selected_layer": 3,
        "selected_expert": expert,
        "entries": entries,
        "payload_bytes_read": 0,
        "g2_admitted": False,
        "runtime_executed": False,
        "authority": False,
        "schema": "GLM53SafetensorsHeaderEvidenceV1",
    }
    return refresh_receipt(evidence)


def compile_packed(report=None, wm=None, hs=None):
    r, w, h = packed_fixture()
    return compile_pager_source_plan(
        r if report is None else report,
        weight_map=w if wm is None else wm,
        headers=h if hs is None else hs,
        expected_model_revision=MODEL,
        expected_index_digest=INDEX,
    )


def compile_per_expert(report=None, wm=None, evidence=None):
    r, w = per_expert_fixture()
    chosen_wm = w if wm is None else wm
    chosen_evidence = per_expert_header_fixture(chosen_wm) if evidence is None else evidence
    return compile_pager_source_plan(
        r if report is None else report,
        weight_map=chosen_wm,
        headers=None,
        expected_model_revision=MODEL,
        expected_index_digest=INDEX,
        per_expert_header_evidence=chosen_evidence,
    )


class BridgeTests(unittest.TestCase):
    def code(self, expected, fn):
        with self.assertRaises(LayoutBindingError) as ctx:
            fn()
        self.assertEqual(ctx.exception.code, expected)

    def test_packed_layout_binds_current_pager_abi(self):
        plan = compile_packed()
        self.assertEqual(plan.binding_kind, "PACKED_FIRST_AXIS")
        self.assertEqual(plan.binding.tensor_map, {"gate_up": GATE, "down": DOWN})
        self.assertEqual(plan.binding.scale_map, {"gate_up_scale": GS, "down_scale": DS})
        self.assertFalse(plan.g2_admitted)
        self.assertFalse(plan.representative_header_bound)

    def test_per_expert_layout_binds_current_per_expert_abi_and_w2_canary(self):
        plan = compile_per_expert()
        self.assertEqual(plan.binding_kind, "PER_EXPERT_INDEX")
        self.assertEqual(len(plan.binding.experts), 256)
        self.assertTrue(plan.binding.require_fp8_scales)
        self.assertTrue(plan.representative_header_bound)
        self.assertEqual(3, plan.representative_layer)
        self.assertEqual(0, plan.representative_expert)
        self.assertFalse(plan.all_experts_header_uniformity_proven)
        self.assertNotEqual("INDEX_PROVEN_NO_HEADER_BINDING", plan.header_evidence_digest)
        self.assertFalse(plan.to_dict()["g2_admitted"])

    def test_per_expert_index_only_plan_is_no_longer_w3_eligible(self):
        report, wm = per_expert_fixture()
        self.code(
            "PER_EXPERT_HEADER_EVIDENCE_REQUIRED",
            lambda: compile_pager_source_plan(
                report,
                weight_map=wm,
                headers=None,
                expected_model_revision=MODEL,
                expected_index_digest=INDEX,
            ),
        )

    def test_per_expert_missing_scale_fails_in_sibling_abi(self):
        report, wm = per_expert_fixture()
        del wm["model.layers.3.mlp.experts.7.down_proj.weight_scale_inv"]
        with self.assertRaises(Exception) as ctx:
            compile_pager_source_plan(
                report,
                weight_map=wm,
                headers=None,
                expected_model_revision=MODEL,
                expected_index_digest=INDEX,
                per_expert_header_evidence={},
            )
        self.assertIn("FP8_SCALE_KEYS_UNRESOLVED", str(ctx.exception))

    def test_per_expert_header_source_and_shard_substitution_fail_closed(self):
        _, wm = per_expert_fixture()
        evidence = per_expert_header_fixture(wm)
        evidence["index_sha256"] = "other-index"
        self.code("PER_EXPERT_HEADER_INDEX_MISMATCH", lambda: compile_per_expert(evidence=evidence))

        evidence = per_expert_header_fixture(wm)
        evidence["entries"][0]["shard_name"] = "wrong-shard"
        self.code("PER_EXPERT_HEADER_SHARD_MISMATCH", lambda: compile_per_expert(evidence=evidence))

    def test_per_expert_header_shape_dtype_and_effect_widening_fail_closed(self):
        _, wm = per_expert_fixture()
        evidence = per_expert_header_fixture(wm)
        evidence["entries"][1]["shape"] = [15, 48]
        self.code("PER_EXPERT_HEADER_FORWARD_SCALE_SHAPE_MISMATCH", lambda: compile_per_expert(evidence=evidence))

        evidence = per_expert_header_fixture(wm)
        evidence["entries"][4]["dtype"] = "BF16"
        self.code("PER_EXPERT_HEADER_WEIGHT_DTYPE_MISMATCH", lambda: compile_per_expert(evidence=evidence))

        evidence = per_expert_header_fixture(wm)
        evidence["payload_bytes_read"] = 1
        self.code("PER_EXPERT_HEADER_PAYLOAD_EFFECT_FORBIDDEN", lambda: compile_per_expert(evidence=evidence))

        evidence = per_expert_header_fixture(wm)
        evidence["authority"] = True
        self.code("PER_EXPERT_HEADER_AUTHORITY_WIDENING_FORBIDDEN", lambda: compile_per_expert(evidence=evidence))

    def test_per_expert_transport_receipt_is_recomputed_not_trusted(self):
        _, wm = per_expert_fixture()
        evidence = per_expert_header_fixture(wm)
        evidence["receipt_digest"] = "0" * 40
        self.code("PER_EXPERT_HEADER_RECEIPT_MISMATCH", lambda: compile_per_expert(evidence=evidence))

    def test_per_expert_canary_change_changes_plan_identity_without_universalizing(self):
        _, wm = per_expert_fixture()
        first = per_expert_header_fixture(wm)
        second = copy.deepcopy(first)
        second["entries"][0]["header_sha256"] = "b" * 64
        refresh_receipt(second)
        p1 = compile_per_expert(evidence=first)
        p2 = compile_per_expert(evidence=second)
        self.assertNotEqual(p1.header_evidence_digest, p2.header_evidence_digest)
        self.assertNotEqual(p1.source_plan_digest, p2.source_plan_digest)
        self.assertFalse(p1.all_experts_header_uniformity_proven)
        self.assertFalse(p2.all_experts_header_uniformity_proven)

    def test_stale_currentness_and_probe_blockers_fail_closed(self):
        r, wm, hs = packed_fixture()
        self.code("STALE_MODEL_REVISION", lambda: compile_pager_source_plan(r, weight_map=wm, headers=hs, expected_model_revision="other", expected_index_digest=INDEX))
        r["blockers"] = ["GLM53_MTP_CHECKPOINT_CLASSIFICATION_REQUIRED"]
        self.code("PROBE_BLOCKED", lambda: compile_packed(report=r))

    def test_packed_requires_header_axis_shard_and_fp8_dtype(self):
        _, _, hs = packed_fixture()
        hs[GATE]["shape"][0] = 255
        self.code("EXPERT_AXIS_HEADER_MISMATCH", lambda: compile_packed(hs=hs))
        _, _, hs = packed_fixture()
        hs[GATE]["shard"] = "wrong"
        self.code("HEADER_SHARD_BINDING_MISMATCH", lambda: compile_packed(hs=hs))
        _, _, hs = packed_fixture()
        hs[GATE]["dtype"] = "BF16"
        self.code("PACKED_WEIGHT_DTYPE_MISMATCH", lambda: compile_packed(hs=hs))

    def test_vendor_and_partial_layouts_are_typed_residuals(self):
        r, _, _ = packed_fixture()
        r["layer"]["layout"] = "CHUNKED_OR_VENDOR_LAYOUT"
        self.code("VENDOR_LAYOUT_ADAPTER_REQUIRED", lambda: compile_packed(report=r))
        r["layer"]["layout"] = "PARTIAL_PER_EXPERT_LAYOUT"
        self.code("PER_EXPERT_LAYOUT_PARTIAL", lambda: compile_packed(report=r))

    def test_scale_ambiguity_is_not_guessed(self):
        r, _, _ = packed_fixture()
        r["layer"]["scale_keys"].append("model.layers.3.mlp.experts.gate_up_proj.alt_scale")
        self.code("FP8_SCALE_ROLE_AMBIGUOUS", lambda: compile_packed(report=r))

    def test_serialized_plan_remains_nonpromoting(self):
        payload = compile_per_expert().to_dict()
        self.assertTrue(payload["representative_header_bound"])
        self.assertFalse(payload["all_experts_header_uniformity_proven"])
        self.assertFalse(payload["g2_admitted"])
        self.assertFalse(payload["large_checkpoint_admitted"])
        self.assertFalse(payload["runtime_execution_proven"])

    def test_clock_metadata_does_not_churn_source_plan(self):
        a, _, _ = packed_fixture()
        b = copy.deepcopy(a)
        b["observation_time"] = "later"
        self.assertEqual(compile_packed(report=a).source_plan_digest, compile_packed(report=b).source_plan_digest)


if __name__ == "__main__":
    unittest.main()
