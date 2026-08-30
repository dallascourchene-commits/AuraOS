import math
import unittest

import glm53_packed_expert_pager as p


class FakeSliceBackend:
    def __init__(self, tensors):
        self.tensors = tensors
        self.reads = []
        self.whole_reads = 0

    def read_rows(self, key, start, end):
        self.reads.append((key, start, end))
        if key not in self.tensors:
            raise p.MissingSliceError(f"missing tensor {key}")
        return self.tensors[key][start:end]

    def read_tensor(self, key):
        self.whole_reads += 1
        raise p.WholeTensorReadForbidden(key)

    def io_attestation(self, binding_digest):
        return {
            "schema": p.BACKEND_IO_ATTESTATION_SCHEMA,
            "binding_digest": binding_digest,
            "attestation_id": "fake-selected-only",
            "physical_selected_only": True,
            "whole_bank_reads": self.whole_reads,
            "whole_bank_materialized": False,
        }


class UnattestedSliceBackend:
    def __init__(self, tensors):
        self.tensors = tensors
        self.reads = []

    def read_rows(self, key, start, end):
        self.reads.append((key, start, end))
        if key not in self.tensors:
            raise p.MissingSliceError(f"missing tensor {key}")
        return self.tensors[key][start:end]


def tiny_banks(offset=0.0):
    # E=4, H=2, I=2. gate_up[e] is [2I,H], down[e] is [H,I].
    gate_up = []
    down = []
    for e in range(4):
        b = offset + e + 1.0
        gate_up.append(
            [
                [0.10 * b, 0.20 * b],
                [0.30 * b, -0.10 * b],
                [0.40 * b, 0.05 * b],
                [-0.20 * b, 0.25 * b],
            ]
        )
        down.append(
            [
                [0.15 * b, -0.05 * b],
                [0.07 * b, 0.11 * b],
            ]
        )
    return gate_up, down


def make_binding(layer, suffix, revision="rev-glm53", index_digest="idx-digest"):
    return p.ExpertSourceBinding(
        model_revision=revision,
        index_digest=index_digest,
        layer_id=layer,
        num_experts=4,
        tensor_map={
            "gate_up": f"{layer}.mlp.experts.gate_up_proj.{suffix}",
            "down": f"{layer}.mlp.experts.down_proj.{suffix}",
        },
        scale_map={
            "gate_up_scale": f"{layer}.mlp.experts.gate_up_proj_scale_inv.{suffix}",
            "down_scale": f"{layer}.mlp.experts.down_proj_scale_inv.{suffix}",
        },
        representation="SYNTHETIC_FP8_SHAPE_ANALOGUE",
    )


def tensors_for_binding(binding, offset=0.0):
    gate_up, down = tiny_banks(offset)
    tensors = {
        binding.tensor_map["gate_up"]: gate_up,
        binding.tensor_map["down"]: down,
        binding.scale_map["gate_up_scale"]: [f"gu-scale-{offset}-{e}" for e in range(4)],
        binding.scale_map["down_scale"]: [f"down-scale-{offset}-{e}" for e in range(4)],
    }
    return tensors, gate_up, down


def make_backend(binding, offset=0.0):
    tensors, gate_up, down = tensors_for_binding(binding, offset)
    return FakeSliceBackend(tensors), gate_up, down


class PackedExpertPagerTests(unittest.TestCase):
    def load(self, pager, ids):
        return pager.load_selected(ids, model_revision="rev-glm53", index_digest="idx-digest")

    def test_contiguous_runs_dedupe_and_never_whole_read(self):
        binding = make_binding("model.layers.7", "weight")
        backend, _, _ = make_backend(binding)
        page = self.load(p.PackedExpertPager(binding, backend), [3, 1, 0, 1])
        self.assertEqual((0, 1, 3), page.expert_ids)
        self.assertEqual(((0, 2), (3, 4)), page.contiguous_runs)
        # 4 families (2 weights + 2 scale companions) * 2 bounded runs.
        self.assertEqual(8, page.read_count)
        self.assertEqual(0, backend.whole_reads)
        self.assertNotIn((binding.tensor_map["gate_up"], 0, 4), backend.reads)

    def test_single_call_all_experts_is_forbidden_before_read(self):
        binding = make_binding("model.layers.7", "weight")
        backend, _, _ = make_backend(binding)
        pager = p.PackedExpertPager(binding, backend)
        with self.assertRaises(p.WholeTensorReadForbidden):
            self.load(pager, [0, 1, 2, 3])
        self.assertEqual([], backend.reads)

    def test_reference_equivalence_with_overlapping_routes(self):
        binding = make_binding("model.layers.8", "weight")
        backend, gate_up, down = make_backend(binding)
        pager = p.PackedExpertPager(binding, backend)
        page = self.load(pager, [2, 0, 2])
        x = [0.7, -0.25]
        routed_ids = [2, 0, 2]
        weights = [0.4, 0.35, 0.25]
        reference = p.routed_reference(x, routed_ids, weights, gate_up, down)
        paged = p.routed_paged(x, routed_ids, weights, page)
        self.assertEqual(len(reference), len(paged))
        for a, b in zip(reference, paged):
            self.assertTrue(math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12), (a, b))
        self.assertEqual(0, backend.whole_reads)

    def test_scale_companions_are_expert_aligned(self):
        binding = make_binding("model.layers.9", "weight")
        backend, _, _ = make_backend(binding)
        page = self.load(p.PackedExpertPager(binding, backend), [1, 3])
        self.assertEqual(("gu-scale-0.0-1", "gu-scale-0.0-3"), page.scale_bundle["gate_up_scale"])
        self.assertEqual(("down-scale-0.0-1", "down-scale-0.0-3"), page.scale_bundle["down_scale"])

    def test_same_expert_ids_across_layers_cannot_cross_read(self):
        binding_a = make_binding("model.layers.10", "weight")
        binding_b = make_binding("model.layers.11", "weight")
        backend_a, _, _ = make_backend(binding_a, offset=0.0)
        backend_b, _, _ = make_backend(binding_b, offset=100.0)
        page_a = self.load(p.PackedExpertPager(binding_a, backend_a), [2])
        page_b = self.load(p.PackedExpertPager(binding_b, backend_b), [2])
        self.assertNotEqual(page_a.gate_up, page_b.gate_up)
        self.assertNotEqual(page_a.binding_digest, page_b.binding_digest)
        self.assertTrue(all(key.startswith("model.layers.10") for key, _, _ in backend_a.reads))
        self.assertTrue(all(key.startswith("model.layers.11") for key, _, _ in backend_b.reads))

    def test_stale_revision_or_index_stops_before_read(self):
        binding = make_binding("model.layers.12", "weight")
        backend, _, _ = make_backend(binding)
        pager = p.PackedExpertPager(binding, backend)
        with self.assertRaises(p.StaleSourceError):
            pager.load_selected([1], model_revision="wrong", index_digest="idx-digest")
        with self.assertRaises(p.StaleSourceError):
            pager.load_selected([1], model_revision="rev-glm53", index_digest="wrong")
        self.assertEqual([], backend.reads)

    def test_out_of_range_and_non_integer_fail_before_read(self):
        binding = make_binding("model.layers.13", "weight")
        backend, _, _ = make_backend(binding)
        pager = p.PackedExpertPager(binding, backend)
        for bad in ([-1], [4], [True], [1.5]):
            with self.assertRaises(p.ExpertRangeError):
                self.load(pager, bad)
        self.assertEqual([], backend.reads)

    def test_missing_slice_fails_closed_never_zero_fills(self):
        binding = make_binding("model.layers.14", "weight")
        backend, _, _ = make_backend(binding)
        del backend.tensors[binding.tensor_map["down"]]
        with self.assertRaises(p.MissingSliceError):
            self.load(p.PackedExpertPager(binding, backend), [0, 2])

    def test_all_experts_remain_reopenable_across_bounded_calls(self):
        binding = make_binding("model.layers.15", "weight")
        backend, _, _ = make_backend(binding)
        pager = p.PackedExpertPager(binding, backend)
        seen = set()
        for expert in range(binding.num_experts):
            page = self.load(pager, [expert])
            seen.update(page.expert_ids)
        self.assertEqual(set(range(binding.num_experts)), seen)
        self.assertEqual(0, backend.whole_reads)

    def test_attested_receipt_never_admits_g2(self):
        binding = make_binding("model.layers.16", "weight")
        backend, _, _ = make_backend(binding)
        pager = p.PackedExpertPager(binding, backend)
        self.load(pager, [0, 3])
        receipt = pager.receipt()
        self.assertFalse(receipt.g2_admitted)
        self.assertTrue(receipt.logical_bounded_row_requests)
        self.assertTrue(receipt.physical_io_attested)
        self.assertTrue(receipt.physical_selected_only)
        self.assertEqual(0, receipt.whole_tensor_reads)
        self.assertFalse(receipt.whole_bank_materialized)
        self.assertEqual("fake-selected-only", receipt.backend_attestation_id)
        self.assertIn("SYNTHETIC_PAGER_CORE_ONLY", receipt.claim_ceiling)

    def test_unattested_backend_keeps_physical_io_unknown(self):
        binding = make_binding("model.layers.16", "weight")
        tensors, _, _ = tensors_for_binding(binding)
        pager = p.PackedExpertPager(binding, UnattestedSliceBackend(tensors))
        self.load(pager, [0, 3])
        receipt = pager.receipt()
        self.assertTrue(receipt.logical_bounded_row_requests)
        self.assertFalse(receipt.physical_io_attested)
        self.assertIsNone(receipt.physical_selected_only)
        self.assertIsNone(receipt.whole_tensor_reads)
        self.assertIsNone(receipt.whole_bank_materialized)
        self.assertIsNone(receipt.backend_attestation_id)

    def test_attestation_must_match_binding(self):
        binding = make_binding("model.layers.16", "weight")
        backend, _, _ = make_backend(binding)
        backend.io_attestation = lambda _: {
            "schema": p.BACKEND_IO_ATTESTATION_SCHEMA,
            "binding_digest": "wrong",
            "attestation_id": "bad",
            "physical_selected_only": True,
            "whole_bank_reads": 0,
            "whole_bank_materialized": False,
        }
        with self.assertRaises(p.SourceBindingError):
            self.load(p.PackedExpertPager(binding, backend), [0, 3])

    def test_ambiguous_source_binding_rejected(self):
        with self.assertRaises(p.SourceBindingError):
            p.ExpertSourceBinding(
                model_revision="rev-glm53",
                index_digest="idx-digest",
                layer_id="model.layers.17",
                num_experts=4,
                tensor_map={"gate_up": "same-key", "down": "same-key"},
                scale_map={},
                representation="synthetic",
            )


if __name__ == "__main__":
    unittest.main()
