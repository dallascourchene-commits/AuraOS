import unittest

import glm53_packed_expert_pager as packed
import glm53_per_expert_index_pager as per_expert
import glm53_pager_cache_adapter as cache


class PackedBackend:
    def __init__(self, tensors):
        self.tensors = tensors
        self.reads = []

    def read_rows(self, key, start, end):
        self.reads.append((key, start, end))
        return self.tensors[key][start:end]


def packed_binding():
    layer = "model.layers.7"
    return packed.ExpertSourceBinding(
        model_revision="rev",
        index_digest="idx",
        layer_id=layer,
        num_experts=4,
        tensor_map={"gate_up": f"{layer}.gu", "down": f"{layer}.down"},
        scale_map={"gate_up_scale": f"{layer}.gus", "down_scale": f"{layer}.ds"},
        representation="synthetic",
    )


def packed_backend(binding):
    return PackedBackend({
        binding.tensor_map["gate_up"]: [f"gu-{i}" for i in range(4)],
        binding.tensor_map["down"]: [f"down-{i}" for i in range(4)],
        binding.scale_map["gate_up_scale"]: [f"gus-{i}" for i in range(4)],
        binding.scale_map["down_scale"]: [f"ds-{i}" for i in range(4)],
    })


def weight_map(layer="model.layers.3", experts=4):
    out = {}
    for e in range(experts):
        for proj in ("gate_proj", "up_proj", "down_proj"):
            key = f"{layer}.mlp.experts.{e}.{proj}.weight"
            out[key] = f"shard-{e % 2}.safetensors"
            out[f"{layer}.mlp.experts.{e}.{proj}.weight_scale_inv"] = f"shard-{e % 2}.safetensors"
    return out


class PerExpertBackend:
    def __init__(self):
        self.reads = []

    def read_tensor(self, shard, key):
        self.reads.append((shard, key))
        return f"payload:{key}"


class CacheAdapterTests(unittest.TestCase):
    def test_packed_cache_hit_avoids_backend_read_and_reports_logical_bytes_only(self):
        binding = packed_binding()
        backend = packed_backend(binding)
        inner = packed.PackedExpertPager(binding, backend)
        pager = cache.CachedPackedExpertPager(
            inner, cache_budget_bytes=20, logical_bundle_nbytes=lambda _e, _b: 10
        )
        first = pager.load_selected([0, 1], model_revision="rev", index_digest="idx")
        reads_after_first = len(backend.reads)
        self.assertEqual((0, 1), first.expert_ids)
        self.assertEqual(2, pager.receipt().cache_entries_after)
        second = pager.load_selected([1], model_revision="rev", index_digest="idx")
        self.assertEqual((1,), second.expert_ids)
        self.assertEqual(reads_after_first, len(backend.reads))
        receipt = pager.receipt()
        self.assertEqual((1,), receipt.cache_hit_experts)
        self.assertEqual((), receipt.backend_miss_experts)
        self.assertEqual(0, receipt.backend_read_count)
        self.assertEqual(10, receipt.logical_bytes_returned)
        self.assertIsNone(receipt.physical_bytes_saved)
        self.assertFalse(receipt.g2_admitted)

    def test_packed_lru_budget_and_evict(self):
        binding = packed_binding()
        backend = packed_backend(binding)
        pager = cache.CachedPackedExpertPager(
            packed.PackedExpertPager(binding, backend),
            cache_budget_bytes=20,
            logical_bundle_nbytes=lambda _e, _b: 10,
        )
        pager.load_selected([0, 1], model_revision="rev", index_digest="idx")
        pager.load_selected([1], model_revision="rev", index_digest="idx")  # 1 becomes MRU
        pager.load_selected([2], model_revision="rev", index_digest="idx")  # evicts 0
        reads = len(backend.reads)
        pager.load_selected([1], model_revision="rev", index_digest="idx")
        self.assertEqual(reads, len(backend.reads))
        pager.load_selected([0], model_revision="rev", index_digest="idx")
        self.assertGreater(len(backend.reads), reads)
        self.assertEqual(1, pager.evict([0]))

    def test_packed_stale_source_and_whole_bank_fail_before_cache_use(self):
        binding = packed_binding()
        backend = packed_backend(binding)
        pager = cache.CachedPackedExpertPager(
            packed.PackedExpertPager(binding, backend),
            cache_budget_bytes=20,
            logical_bundle_nbytes=lambda _e, _b: 10,
        )
        pager.load_selected([0], model_revision="rev", index_digest="idx")
        reads = len(backend.reads)
        with self.assertRaises(packed.StaleSourceError):
            pager.load_selected([0], model_revision="stale", index_digest="idx")
        with self.assertRaises(packed.WholeTensorReadForbidden):
            pager.load_selected([0, 1, 2, 3], model_revision="rev", index_digest="idx")
        self.assertEqual(reads, len(backend.reads))

    def test_per_expert_cache_hit_and_lru(self):
        binding = per_expert.build_standard_glm_per_expert_binding(
            weight_map=weight_map(), model_revision="rev", index_digest="idx",
            layer_id="model.layers.3", num_experts=4, require_fp8_scales=True,
        )
        backend = PerExpertBackend()
        pager = cache.CachedPerExpertIndexPager(
            per_expert.PerExpertIndexPager(binding, backend),
            cache_budget_bytes=20,
            logical_bundle_nbytes=lambda _e, _b: 10,
        )
        first = pager.load_selected([0, 1], model_revision="rev", index_digest="idx")
        self.assertEqual(12, first.tensor_reads)
        reads = len(backend.reads)
        second = pager.load_selected([1], model_revision="rev", index_digest="idx")
        self.assertEqual(0, second.tensor_reads)
        self.assertEqual(reads, len(backend.reads))
        self.assertEqual((1,), pager.receipt().cache_hit_experts)
        pager.load_selected([2], model_revision="rev", index_digest="idx")
        reads = len(backend.reads)
        pager.load_selected([0], model_revision="rev", index_digest="idx")
        self.assertGreater(len(backend.reads), reads)

    def test_per_expert_stale_source_and_whole_bank_fail_before_cache_use(self):
        binding = per_expert.build_standard_glm_per_expert_binding(
            weight_map=weight_map(), model_revision="rev", index_digest="idx",
            layer_id="model.layers.3", num_experts=4, require_fp8_scales=True,
        )
        backend = PerExpertBackend()
        pager = cache.CachedPerExpertIndexPager(
            per_expert.PerExpertIndexPager(binding, backend),
            cache_budget_bytes=10,
            logical_bundle_nbytes=lambda _e, _b: 10,
        )
        pager.load_selected([0], model_revision="rev", index_digest="idx")
        reads = len(backend.reads)
        with self.assertRaises(per_expert.PerExpertSourceError):
            pager.load_selected([0], model_revision="rev", index_digest="stale")
        with self.assertRaises(per_expert.PerExpertReadError):
            pager.load_selected([0, 1, 2, 3], model_revision="rev", index_digest="idx")
        self.assertEqual(reads, len(backend.reads))

    def test_invalid_logical_size_fails_without_claiming_physical_savings(self):
        binding = packed_binding()
        backend = packed_backend(binding)
        pager = cache.CachedPackedExpertPager(
            packed.PackedExpertPager(binding, backend),
            cache_budget_bytes=10,
            logical_bundle_nbytes=lambda _e, _b: -1,
        )
        with self.assertRaises(cache.CacheAdapterError):
            pager.load_selected([0], model_revision="rev", index_digest="idx")
        with self.assertRaises(cache.CacheAdapterError):
            pager.receipt()


if __name__ == "__main__":
    unittest.main()
