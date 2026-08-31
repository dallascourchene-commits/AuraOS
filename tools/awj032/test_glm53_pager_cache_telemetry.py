import unittest

import glm53_packed_expert_pager as packed
import glm53_per_expert_index_pager as per_expert
import glm53_pager_cache_telemetry as cache


class PackedBackend:
    def __init__(self, tensors):
        self.tensors = tensors
        self.reads = []

    def read_rows(self, key, start, end):
        self.reads.append((key, start, end))
        if key not in self.tensors:
            raise packed.MissingSliceError(key)
        return self.tensors[key][start:end]

    def io_attestation(self, binding_digest):
        return {
            "schema": packed.BACKEND_IO_ATTESTATION_SCHEMA,
            "binding_digest": binding_digest,
            "attestation_id": "packed-fixture",
            "physical_selected_only": True,
            "whole_bank_reads": 0,
            "whole_bank_materialized": False,
        }


class PerBackend:
    def __init__(self):
        self.reads = []
        self.fail_key = None

    def read_tensor(self, shard, key):
        self.reads.append((shard, key))
        if key == self.fail_key:
            raise FileNotFoundError(key)
        return f"payload:{key}"

    def io_attestation(self, binding_digest):
        return {
            "schema": per_expert.BACKEND_IO_ATTESTATION_SCHEMA,
            "binding_digest": binding_digest,
            "attestation_id": "per-fixture",
            "physical_selected_only": True,
            "whole_bank_reads": 0,
            "whole_bank_materialized": False,
        }


def packed_binding():
    b = packed.ExpertSourceBinding(
        model_revision="glm53-rev",
        index_digest="index-sha",
        layer_id="model.layers.3",
        num_experts=4,
        tensor_map={"gate_up": "gu", "down": "down"},
        scale_map={"gate_up_scale": "gus", "down_scale": "downs"},
        representation="packed-fp8",
    )
    tensors = {
        "gu": [[[e + 0.1, e + 0.2]] for e in range(4)],
        "down": [[[e + 0.3, e + 0.4]] for e in range(4)],
        "gus": [f"gus-{e}" for e in range(4)],
        "downs": [f"downs-{e}" for e in range(4)],
    }
    return b, tensors


def per_binding():
    wm = {}
    for e in range(4):
        for proj in ("gate_proj", "up_proj", "down_proj"):
            key = f"model.layers.3.mlp.experts.{e}.{proj}.weight"
            scale = f"model.layers.3.mlp.experts.{e}.{proj}.weight_scale_inv"
            wm[key] = f"shard-{e % 2}"
            wm[scale] = f"shard-{e % 2}"
    return per_expert.build_standard_glm_per_expert_binding(
        weight_map=wm,
        model_revision="glm53-rev",
        index_digest="index-sha",
        layer_id="model.layers.3",
        num_experts=4,
        require_fp8_scales=True,
    )


class CacheTelemetryTests(unittest.TestCase):
    def test_packed_cold_then_hit_has_zero_backend_io_on_hit(self):
        binding, tensors = packed_binding()
        backend = PackedBackend(tensors)
        pager = cache.CachedPackedExpertPager(binding, backend, cache_budget_bytes=10_000)
        first = pager.load_selected([0, 2], model_revision="glm53-rev", index_digest="index-sha")
        first_receipt = pager.receipt()
        reads_after_first = list(backend.reads)
        self.assertGreater(first.read_count, 0)
        self.assertEqual("COLD", first_receipt.cache_state_before)
        self.assertGreater(first_receipt.cache_miss_entries, 0)
        self.assertGreater(first_receipt.logical_backend_bytes_required, 0)
        self.assertIsNone(first_receipt.physical_expert_bytes_read)

        second = pager.load_selected([2, 0], model_revision="glm53-rev", index_digest="index-sha")
        second_receipt = pager.receipt()
        self.assertEqual(0, second.read_count)
        self.assertEqual(reads_after_first, backend.reads)
        self.assertEqual("WARM", second_receipt.cache_state_before)
        self.assertGreater(second_receipt.cache_hit_entries, 0)
        self.assertGreater(second_receipt.cache_bytes_served, 0)
        self.assertEqual(0, second_receipt.logical_backend_bytes_required)
        self.assertEqual(0, second_receipt.physical_expert_bytes_read)
        self.assertEqual("AURA_CACHE_ONLY_NO_BACKEND_CALL", second_receipt.backend_attestation_id)
        self.assertFalse(second_receipt.g2_admitted)

    def test_packed_budget_evicts_whole_expert_groups_not_partial_roles(self):
        binding, tensors = packed_binding()
        backend = PackedBackend(tensors)
        pager = cache.CachedPackedExpertPager(binding, backend, cache_budget_bytes=80)
        pager.load_selected([0, 1], model_revision="glm53-rev", index_digest="index-sha")
        receipt = pager.receipt()
        self.assertEqual(1, receipt.cache_experts_after)
        self.assertEqual(4, receipt.cache_entries_after)
        self.assertGreaterEqual(receipt.evicted_entries, 4)
        self.assertEqual("BUDGET", receipt.eviction_reason)
        group = next(iter(pager.cache._groups.values()))
        self.assertEqual({"gate_up", "down", "scale:gate_up_scale", "scale:down_scale"}, set(group.values))

    def test_packed_stale_identity_fails_before_cache_serve_or_backend_read(self):
        binding, tensors = packed_binding()
        backend = PackedBackend(tensors)
        pager = cache.CachedPackedExpertPager(binding, backend, cache_budget_bytes=10_000)
        pager.load_selected([1], model_revision="glm53-rev", index_digest="index-sha")
        before = list(backend.reads)
        with self.assertRaises(packed.StaleSourceError):
            pager.load_selected([1], model_revision="wrong", index_digest="index-sha")
        self.assertEqual(before, backend.reads)

    def test_packed_failure_commits_no_new_cache_group(self):
        binding, tensors = packed_binding()
        backend = PackedBackend(tensors)
        pager = cache.CachedPackedExpertPager(binding, backend, cache_budget_bytes=10_000)
        del backend.tensors["down"]
        with self.assertRaises(packed.MissingSliceError):
            pager.load_selected([0, 2], model_revision="glm53-rev", index_digest="index-sha")
        self.assertEqual(0, pager.cache.expert_count)
        self.assertEqual(0, pager.cache.entry_count)

    def test_per_expert_cold_hit_and_exact_role_identity(self):
        binding = per_binding()
        backend = PerBackend()
        pager = cache.CachedPerExpertIndexPager(binding, backend, cache_budget_bytes=100_000)
        pager.load_selected([1, 3], model_revision="glm53-rev", index_digest="index-sha")
        reads_after_first = list(backend.reads)
        first = pager.receipt()
        self.assertEqual(12, first.cache_miss_entries)
        self.assertGreater(first.logical_backend_bytes_required, 0)

        page = pager.load_selected([3, 1], model_revision="glm53-rev", index_digest="index-sha")
        second = pager.receipt()
        self.assertEqual(0, page.tensor_reads)
        self.assertEqual(reads_after_first, backend.reads)
        self.assertEqual(12, second.cache_hit_entries)
        self.assertEqual(0, second.physical_expert_bytes_read)
        group = next(iter(pager.cache._groups.values()))
        role = next(iter(group.values))
        exact = group.identity.role_key(role)
        self.assertEqual("glm53-rev", exact[0])
        self.assertEqual("index-sha", exact[1])
        self.assertEqual("model.layers.3", exact[2])
        self.assertEqual(group.identity.expert_id, exact[4])
        self.assertEqual(role, exact[5])

    def test_per_expert_failure_is_atomic_and_whole_bank_stays_forbidden(self):
        binding = per_binding()
        backend = PerBackend()
        pager = cache.CachedPerExpertIndexPager(binding, backend, cache_budget_bytes=100_000)
        backend.fail_key = binding.experts[2].weight_keys["up"]
        with self.assertRaises(per_expert.PerExpertReadError):
            pager.load_selected([2], model_revision="glm53-rev", index_digest="index-sha")
        self.assertEqual(0, pager.cache.entry_count)
        backend.fail_key = None
        with self.assertRaises(per_expert.PerExpertReadError):
            pager.load_selected([0, 1, 2, 3], model_revision="glm53-rev", index_digest="index-sha")
        self.assertEqual(0, pager.cache.entry_count)

    def test_evict_starts_new_cold_epoch(self):
        binding, tensors = packed_binding()
        pager = cache.CachedPackedExpertPager(binding, PackedBackend(tensors), cache_budget_bytes=10_000)
        pager.load_selected([0], model_revision="glm53-rev", index_digest="index-sha")
        self.assertEqual(0, pager.receipt().cache_epoch)
        removed = pager.evict()
        self.assertGreater(removed, 0)
        pager.load_selected([0], model_revision="glm53-rev", index_digest="index-sha")
        self.assertEqual(1, pager.receipt().cache_epoch)
        self.assertEqual("COLD", pager.receipt().cache_state_before)


if __name__ == "__main__":
    unittest.main()
