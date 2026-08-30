import inspect
import math
import unittest

from packed_expert_pager import (
    ExpertSlice,
    InMemoryPackedTensorReader,
    PackedExpertPager,
    PackedExpertPagerError,
    PagerBinding,
    SafetensorsFirstAxisReader,
    selected_expert_ids,
)


FAMILIES = ("gate_up", "gate_up_scale", "down", "down_scale")


def fixture_tensors(num_experts=4):
    gate_up = []
    down = []
    gate_scale = []
    down_scale = []
    for e in range(num_experts):
        # hidden=2, intermediate=2. First two rows are gate, next two are up.
        s = float(e + 1)
        gate_up.append(
            [
                [0.10 * s, 0.20 * s],
                [-0.15 * s, 0.05 * s],
                [0.25 * s, -0.10 * s],
                [0.05 * s, 0.30 * s],
            ]
        )
        down.append(
            [
                [0.20 * s, -0.05 * s],
                [0.10 * s, 0.15 * s],
            ]
        )
        gate_scale.append([[1.0]])
        down_scale.append([[1.0]])
    return {
        "gate_up": gate_up,
        "gate_up_scale": gate_scale,
        "down": down,
        "down_scale": down_scale,
    }


def matvec(matrix, vector):
    return [sum(row[j] * vector[j] for j in range(len(vector))) for row in matrix]


def silu(x):
    return x / (1.0 + math.exp(-x))


def expert_math(hidden, gate_up, down):
    fused = matvec(gate_up, hidden)
    half = len(fused) // 2
    gate = fused[:half]
    up = fused[half:]
    mixed = [silu(g) * u for g, u in zip(gate, up)]
    return matvec(down, mixed)


def reference_forward(tensors, hidden_states, top_k_index, top_k_weights):
    out = []
    for hidden, ids, weights in zip(hidden_states, top_k_index, top_k_weights):
        row = [0.0 for _ in hidden]
        for expert_id, weight in zip(ids, weights):
            y = expert_math(hidden, tensors["gate_up"][expert_id], tensors["down"][expert_id])
            row = [a + weight * b for a, b in zip(row, y)]
        out.append(row)
    return out


def paged_forward(pager, hidden_states, top_k_index, top_k_weights):
    loaded = pager.load_selected(selected_expert_ids(top_k_index, num_experts=pager.binding.total_experts))
    out = []
    for hidden, ids, weights in zip(hidden_states, top_k_index, top_k_weights):
        row = [0.0 for _ in hidden]
        for expert_id, weight in zip(ids, weights):
            slices = loaded.slices[expert_id]
            # Scale slices are intentionally loaded and provenance-bound even though
            # this float32 fixture uses unity scales and does not emulate FP8 kernels.
            assert slices["gate_up_scale"].payload == [[1.0]]
            assert slices["down_scale"].payload == [[1.0]]
            y = expert_math(hidden, slices["gate_up"].payload, slices["down"].payload)
            row = [a + weight * b for a, b in zip(row, y)]
        out.append(row)
    return out, loaded.receipt


class MissingExpertReader(InMemoryPackedTensorReader):
    def __init__(self, *args, missing, **kwargs):
        super().__init__(*args, **kwargs)
        self.missing = missing

    def read_expert(self, tensor_key, expert_id):
        if (tensor_key, expert_id) == self.missing:
            raise FileNotFoundError(f"missing {tensor_key}:{expert_id}")
        return super().read_expert(tensor_key, expert_id)


class BadSliceReader(InMemoryPackedTensorReader):
    def read_expert(self, tensor_key, expert_id):
        item = super().read_expert(tensor_key, expert_id)
        if tensor_key == "down":
            return ExpertSlice(
                tensor_key=item.tensor_key,
                expert_id=item.expert_id,
                payload=item.payload,
                shape=(2,) + item.shape[1:],
                nbytes=item.nbytes,
                source_revision=item.source_revision,
                source_digest=item.source_digest,
            )
        return item


class PackedExpertPagerTests(unittest.TestCase):
    def make(self, *, cache_budget=0, reader_cls=InMemoryPackedTensorReader, reader_kwargs=None, representation="fp8-e4m3"):
        tensors = fixture_tensors()
        reader = reader_cls(tensors, source_revision="glm53-fixture-r1", **(reader_kwargs or {}))
        binding = PagerBinding(
            model_revision="glm53-fixture-model-r1",
            layer_id="model.layers.3",
            representation=representation,
            total_experts=4,
            tensor_families=FAMILIES,
            expected_source_revision=reader.source_revision,
            expected_source_digest=reader.source_digest,
        )
        return PackedExpertPager(binding, reader, cache_budget_bytes=cache_budget), reader, tensors

    def assertRowsClose(self, a, b, places=12):
        self.assertEqual(len(a), len(b))
        for ra, rb in zip(a, b):
            self.assertEqual(len(ra), len(rb))
            for xa, xb in zip(ra, rb):
                self.assertAlmostEqual(xa, xb, places=places)

    def test_selected_expert_ids_are_deduplicated_and_stable(self):
        self.assertEqual((0, 1, 3), selected_expert_ids([[3, 1], [1, 0], [3, 3]], num_experts=4))

    def test_selected_expert_ids_fail_closed_out_of_range(self):
        with self.assertRaisesRegex(PackedExpertPagerError, "EXPERT_ID_OUT_OF_RANGE"):
            selected_expert_ids([[4]], num_experts=4)

    def test_synthetic_reference_equals_paged_for_overlapping_routes(self):
        pager, reader, tensors = self.make()
        hidden = [[0.4, -0.2], [0.1, 0.7], [-0.3, 0.25]]
        ids = [[0, 2], [2, 3], [0, 3]]
        weights = [[0.6, 0.4], [0.25, 0.75], [0.5, 0.5]]
        reference = reference_forward(tensors, hidden, ids, weights)
        paged, receipt = paged_forward(pager, hidden, ids, weights)
        self.assertRowsClose(reference, paged)
        self.assertEqual((0, 2, 3), receipt.requested_expert_ids)
        self.assertFalse(receipt.whole_bank_materialized)
        self.assertFalse(receipt.execution_authorized)
        self.assertFalse(receipt.model_execution_proven)
        self.assertFalse(receipt.g2_admitted)
        self.assertEqual(0, reader.whole_tensor_reads)

    def test_nonoverlapping_routes_load_only_union(self):
        pager, reader, _ = self.make()
        pager.load_selected(selected_expert_ids([[0, 1], [2, 3]], num_experts=4))
        self.assertEqual(16, len(reader.slice_reads))  # 4 experts x 4 tensor families
        self.assertEqual({0, 1, 2, 3}, {expert for _, expert in reader.slice_reads})
        self.assertEqual(0, reader.whole_tensor_reads)

    def test_single_route_does_not_read_unselected_experts(self):
        pager, reader, _ = self.make()
        load = pager.load_selected([2])
        self.assertEqual({2}, set(load.slices))
        self.assertEqual({2}, {expert for _, expert in reader.slice_reads})
        self.assertEqual(4, len(reader.slice_reads))

    def test_scale_families_are_paged_with_weights(self):
        pager, _, _ = self.make()
        load = pager.load_selected([1])
        self.assertEqual(set(FAMILIES), set(load.slices[1]))
        self.assertEqual([[1.0]], load.slices[1]["gate_up_scale"].payload)
        self.assertEqual([[1.0]], load.slices[1]["down_scale"].payload)

    def test_all_experts_remain_addressable_across_repeated_routes(self):
        pager, reader, _ = self.make()
        seen = set()
        for expert_id in range(4):
            load = pager.load_selected([expert_id])
            seen.update(load.slices)
        self.assertEqual({0, 1, 2, 3}, seen)
        self.assertEqual({0, 1, 2, 3}, {expert for _, expert in reader.slice_reads})

    def test_zero_cache_reopens_exact_slice(self):
        pager, reader, _ = self.make(cache_budget=0)
        pager.load_selected([1])
        pager.load_selected([1])
        self.assertEqual(8, len(reader.slice_reads))

    def test_cache_hit_avoids_second_physical_reader_call(self):
        pager, reader, _ = self.make(cache_budget=256)
        first = pager.load_selected([1])
        reads = len(reader.slice_reads)
        second = pager.load_selected([1])
        self.assertEqual(reads, len(reader.slice_reads))
        self.assertEqual((1,), first.receipt.materialized_expert_ids)
        self.assertEqual((1,), second.receipt.cache_hit_expert_ids)
        self.assertEqual((), second.receipt.materialized_expert_ids)

    def test_cache_budget_is_never_exceeded(self):
        pager, _, _ = self.make(cache_budget=64)
        receipt = pager.load_selected([0, 1, 2, 3]).receipt
        self.assertLessEqual(receipt.cache_bytes_after, 64)

    def test_evict_selected_expert_only(self):
        pager, reader, _ = self.make(cache_budget=512)
        pager.load_selected([0, 1])
        reads = len(reader.slice_reads)
        self.assertEqual(4, pager.evict(expert_ids=[0]))
        pager.load_selected([1])
        self.assertEqual(reads, len(reader.slice_reads))
        pager.load_selected([0])
        self.assertEqual(reads + 4, len(reader.slice_reads))

    def test_missing_slice_fails_without_silent_substitution(self):
        pager, _, _ = self.make(
            reader_cls=MissingExpertReader,
            reader_kwargs={"missing": ("down_scale", 2)},
            cache_budget=512,
        )
        with self.assertRaisesRegex(PackedExpertPagerError, "EXPERT_SLICE_MISSING"):
            pager.load_selected([2])
        # The expert load is atomic: earlier family reads were not committed.
        self.assertEqual(0, len(pager._cache))
        self.assertEqual(0, pager._cache_bytes)

    def test_bad_first_axis_slice_fails_closed(self):
        pager, _, _ = self.make(reader_cls=BadSliceReader)
        with self.assertRaisesRegex(PackedExpertPagerError, "SLICE_FIRST_AXIS_INVALID"):
            pager.load_selected([0])

    def test_missing_tensor_family_fails_at_construction(self):
        tensors = fixture_tensors()
        tensors.pop("down_scale")
        reader = InMemoryPackedTensorReader(tensors, source_revision="r1")
        binding = PagerBinding(
            model_revision="m1",
            layer_id="l1",
            representation="fp8",
            total_experts=4,
            tensor_families=FAMILIES,
            expected_source_revision=reader.source_revision,
            expected_source_digest=reader.source_digest,
        )
        with self.assertRaisesRegex(PackedExpertPagerError, "TENSOR_FAMILY_MISSING"):
            PackedExpertPager(binding, reader)

    def test_misaligned_scale_expert_axis_fails(self):
        tensors = fixture_tensors()
        tensors["down_scale"] = tensors["down_scale"][:3]
        reader = InMemoryPackedTensorReader(tensors, source_revision="r1")
        binding = PagerBinding(
            model_revision="m1",
            layer_id="l1",
            representation="fp8",
            total_experts=4,
            tensor_families=FAMILIES,
            expected_source_revision=reader.source_revision,
            expected_source_digest=reader.source_digest,
        )
        with self.assertRaisesRegex(PackedExpertPagerError, "TENSOR_EXPERT_AXIS_MISMATCH"):
            PackedExpertPager(binding, reader)

    def test_stale_revision_fails_before_any_read(self):
        tensors = fixture_tensors()
        reader = InMemoryPackedTensorReader(tensors, source_revision="observed-r2")
        binding = PagerBinding(
            model_revision="m1",
            layer_id="l1",
            representation="fp8",
            total_experts=4,
            tensor_families=FAMILIES,
            expected_source_revision="expected-r1",
            expected_source_digest=reader.source_digest,
        )
        with self.assertRaisesRegex(PackedExpertPagerError, "SOURCE_REVISION_MISMATCH"):
            PackedExpertPager(binding, reader)
        self.assertEqual([], reader.slice_reads)

    def test_source_digest_mismatch_fails_before_any_read(self):
        tensors = fixture_tensors()
        reader = InMemoryPackedTensorReader(tensors, source_revision="r1")
        binding = PagerBinding(
            model_revision="m1",
            layer_id="l1",
            representation="fp8",
            total_experts=4,
            tensor_families=FAMILIES,
            expected_source_revision="r1",
            expected_source_digest="0" * 64,
        )
        with self.assertRaisesRegex(PackedExpertPagerError, "SOURCE_DIGEST_MISMATCH"):
            PackedExpertPager(binding, reader)
        self.assertEqual([], reader.slice_reads)

    def test_representation_changes_pager_identity(self):
        a, _, _ = self.make(representation="fp8-e4m3")
        b, _, _ = self.make(representation="derived-bf16")
        self.assertNotEqual(a.pager_id, b.pager_id)

    def test_receipt_separates_logical_from_physical_bytes(self):
        pager, _, _ = self.make()
        receipt = pager.load_selected([0]).receipt
        self.assertGreater(receipt.logical_bytes_returned, 0)
        self.assertEqual("UNKNOWN", receipt.physical_bytes_observed)
        self.assertFalse(receipt.whole_bank_materialized)

    def test_safetensors_reader_uses_get_slice_not_get_tensor(self):
        source = inspect.getsource(SafetensorsFirstAxisReader.read_expert)
        self.assertIn("get_slice", source)
        self.assertNotIn("get_tensor", source)
        self.assertIn("expert_id : expert_id + 1", source)

    def test_empty_routing_set_has_zero_reads(self):
        pager, reader, _ = self.make()
        load = pager.load_selected([])
        self.assertEqual({}, load.slices)
        self.assertEqual([], reader.slice_reads)
        self.assertEqual(0, load.receipt.logical_bytes_returned)

    def test_receipt_is_deterministic_for_fresh_identical_pagers(self):
        a, _, _ = self.make()
        b, _, _ = self.make()
        self.assertEqual(a.load_selected([3, 1]).receipt.to_dict(), b.load_selected([1, 3]).receipt.to_dict())


if __name__ == "__main__":
    unittest.main()
