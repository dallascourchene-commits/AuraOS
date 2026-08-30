import unittest

import glm53_per_expert_index_pager as p


def weight_map(layer="model.layers.3", experts=4, scales=True):
    out = {}
    for e in range(experts):
        for proj in ("gate_proj", "up_proj", "down_proj"):
            key = f"{layer}.mlp.experts.{e}.{proj}.weight"
            out[key] = f"shard-{e % 2}.safetensors"
            if scales:
                out[f"{layer}.mlp.experts.{e}.{proj}.weight_scale_inv"] = f"shard-{e % 2}.safetensors"
    return out


class FakeBackend:
    def __init__(self):
        self.reads = []

    def read_tensor(self, shard, key):
        self.reads.append((shard, key))
        return f"payload:{key}"


class PerExpertIndexPagerTests(unittest.TestCase):
    def binding(self, layer="model.layers.3"):
        return p.build_standard_glm_per_expert_binding(
            weight_map=weight_map(layer),
            model_revision="glm53-rev",
            index_digest="index-sha",
            layer_id=layer,
            num_experts=4,
            require_fp8_scales=True,
        )

    def test_index_proves_complete_per_expert_layout(self):
        b = self.binding()
        self.assertEqual(set(range(4)), set(b.experts))
        self.assertEqual("PER_EXPERT_PHYSICAL_LAYOUT", b.representation)
        self.assertEqual(6, len(b.experts[0].shard_by_key))

    def test_selected_experts_only_are_read_and_deduped(self):
        b = self.binding()
        backend = FakeBackend()
        page = p.PerExpertIndexPager(b, backend).load_selected(
            [3, 1, 3], model_revision="glm53-rev", index_digest="index-sha"
        )
        self.assertEqual((1, 3), page.expert_ids)
        self.assertEqual(12, page.tensor_reads)
        self.assertEqual(12, len(backend.reads))
        keys = [key for _, key in backend.reads]
        self.assertTrue(all(".experts.1." in key or ".experts.3." in key for key in keys))
        self.assertFalse(any(".experts.0." in key or ".experts.2." in key for key in keys))

    def test_stale_source_fails_before_any_read(self):
        b = self.binding()
        backend = FakeBackend()
        pager = p.PerExpertIndexPager(b, backend)
        with self.assertRaises(p.PerExpertSourceError):
            pager.load_selected([1], model_revision="wrong", index_digest="index-sha")
        with self.assertRaises(p.PerExpertSourceError):
            pager.load_selected([1], model_revision="glm53-rev", index_digest="wrong")
        self.assertEqual([], backend.reads)

    def test_missing_weight_key_fails_at_binding_before_backend_exists(self):
        wm = weight_map()
        del wm["model.layers.3.mlp.experts.2.up_proj.weight"]
        with self.assertRaises(p.PerExpertSourceError) as ctx:
            p.build_standard_glm_per_expert_binding(
                weight_map=wm,
                model_revision="glm53-rev",
                index_digest="index-sha",
                layer_id="model.layers.3",
                num_experts=4,
            )
        self.assertEqual("PER_EXPERT_WEIGHT_KEY_MISSING", ctx.exception.code)

    def test_missing_fp8_scale_key_fails_closed(self):
        wm = weight_map()
        del wm["model.layers.3.mlp.experts.0.gate_proj.weight_scale_inv"]
        with self.assertRaises(p.PerExpertSourceError) as ctx:
            p.build_standard_glm_per_expert_binding(
                weight_map=wm,
                model_revision="glm53-rev",
                index_digest="index-sha",
                layer_id="model.layers.3",
                num_experts=4,
                require_fp8_scales=True,
            )
        self.assertEqual("FP8_SCALE_KEYS_UNRESOLVED", ctx.exception.code)

    def test_same_expert_number_different_layers_cannot_cross_read(self):
        a = self.binding("model.layers.3")
        b = self.binding("model.layers.4")
        ba, bb = FakeBackend(), FakeBackend()
        p.PerExpertIndexPager(a, ba).load_selected([2], model_revision="glm53-rev", index_digest="index-sha")
        p.PerExpertIndexPager(b, bb).load_selected([2], model_revision="glm53-rev", index_digest="index-sha")
        self.assertTrue(all(key.startswith("model.layers.3") for _, key in ba.reads))
        self.assertTrue(all(key.startswith("model.layers.4") for _, key in bb.reads))
        self.assertNotEqual(a.digest, b.digest)

    def test_every_expert_remains_addressable(self):
        b = self.binding()
        backend = FakeBackend()
        pager = p.PerExpertIndexPager(b, backend)
        seen = set()
        for e in range(4):
            seen.update(pager.load_selected([e], model_revision="glm53-rev", index_digest="index-sha").expert_ids)
        self.assertEqual(set(range(4)), seen)
        self.assertTrue(pager.receipt().all_experts_addressable)

    def test_receipt_never_admits_g2_or_whole_bank(self):
        b = self.binding()
        pager = p.PerExpertIndexPager(b, FakeBackend())
        pager.load_selected([0, 2], model_revision="glm53-rev", index_digest="index-sha")
        receipt = pager.receipt()
        self.assertFalse(receipt.g2_admitted)
        self.assertFalse(receipt.whole_expert_bank_materialized)
        self.assertTrue(receipt.selected_expert_tensor_reads_only)
        self.assertIn("NO_FLAGSHIP_RUNTIME_OR_G2_PROOF", receipt.claim_ceiling)

    def test_bad_ids_fail_closed(self):
        b = self.binding()
        backend = FakeBackend()
        pager = p.PerExpertIndexPager(b, backend)
        for ids in ([], [-1], [4], [True], [1.2]):
            with self.assertRaises(p.PerExpertRangeError):
                pager.load_selected(ids, model_revision="glm53-rev", index_digest="index-sha")
        self.assertEqual([], backend.reads)

    def test_gate_up_fusion_order_matches_runtime_contract(self):
        gate = ((1, 2), (3, 4))
        up = ((5, 6), (7, 8))
        self.assertEqual(((1, 2), (3, 4), (5, 6), (7, 8)), p.fuse_gate_up_rows(gate, up))


if __name__ == "__main__":
    unittest.main()
