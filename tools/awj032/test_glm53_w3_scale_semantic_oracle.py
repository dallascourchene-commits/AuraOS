import hashlib
import json
import math
import os
import struct
import tempfile
import unittest

from tools.awj032.glm53_per_expert_index_pager import (
    PerExpertIndexPager,
    build_standard_glm_per_expert_binding,
)
from tools.awj032.test_glm53_w3_native_per_expert_fixture import (
    EXPECTED_HEADER_SHA256,
    INDEX,
    LAYER,
    MODEL,
    SHARD,
    TinySafetensorsBackend,
    _fixture_values,
    _forward,
    _tensor_spec,
    _weight_map,
)


EXPERT1_INPUT = [0.5, -0.25, 1.0, 0.25]
EXPECTED_EXPERT1_OUTPUT = (
    0.011111936999645605,
    0.31823785230114443,
    0.6988272529749557,
    -1.0593528164620791,
)


def _discriminative_scales(expert):
    if expert == 0:
        return {
            "gate_scale": [[0.5, 2.0]],
            "up_scale": [[2.0, 0.25]],
            "down_scale": [[2.0], [0.25]],
        }
    return {
        "gate_scale": [[2.0, 0.5]],
        "up_scale": [[0.25, 2.0]],
        "down_scale": [[0.5], [2.0]],
    }


def _build_discriminative_safetensors(path):
    tensors = {}
    for expert in range(2):
        values = _fixture_values(expert)
        scales = _discriminative_scales(expert)
        tensors[f"{LAYER}.mlp.experts.{expert}.gate_proj.weight"] = _tensor_spec("F8_E4M3", values["gate"])
        tensors[f"{LAYER}.mlp.experts.{expert}.gate_proj.weight_scale_inv"] = _tensor_spec(
            "F32", scales["gate_scale"]
        )
        tensors[f"{LAYER}.mlp.experts.{expert}.up_proj.weight"] = _tensor_spec("F8_E4M3", values["up"])
        tensors[f"{LAYER}.mlp.experts.{expert}.up_proj.weight_scale_inv"] = _tensor_spec(
            "F32", scales["up_scale"]
        )
        tensors[f"{LAYER}.mlp.experts.{expert}.down_proj.weight"] = _tensor_spec("F8_E4M3", values["down"])
        tensors[f"{LAYER}.mlp.experts.{expert}.down_proj.weight_scale_inv"] = _tensor_spec(
            "F32", scales["down_scale"]
        )

    header = {}
    payload = bytearray()
    for key in sorted(tensors):
        dtype, shape, raw = tensors[key]
        start = len(payload)
        payload.extend(raw)
        header[key] = {"dtype": dtype, "shape": shape, "data_offsets": [start, len(payload)]}
    header_bytes = json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8")
    with open(path, "wb") as handle:
        handle.write(struct.pack("<Q", len(header_bytes)))
        handle.write(header_bytes)
        handle.write(payload)
    return hashlib.sha256(header_bytes).hexdigest()


def _independent_expert1_reference(x):
    """Explicit oracle: no paged-side _dequant, _matvec, or _forward calls."""
    if len(x) != 4:
        raise ValueError("reference input must have four elements")

    # Literal expert-1 weight*scale products for BLOCK=(2,2).
    gate0 = 1.0 * x[0] + 0.5 * x[1] + 0.5 * x[2] - 0.25 * x[3]
    gate1 = -0.5 * x[0] + 2.0 * x[1] + 0.25 * x[2] + 0.125 * x[3]
    up0 = 0.25 * x[0] - 0.125 * x[1] + 1.0 * x[2] + 0.5 * x[3]
    up1 = 0.0625 * x[0] + 0.125 * x[1] + 2.0 * x[2] - 0.5 * x[3]

    hidden0 = (gate0 / (1.0 + math.exp(-gate0))) * up0
    hidden1 = (gate1 / (1.0 + math.exp(-gate1))) * up1

    return (
        0.25 * hidden0 + 0.5 * hidden1,
        0.5 * hidden0 + 0.125 * hidden1,
        0.5 * hidden0 - 1.0 * hidden1,
        -1.0 * hidden0 + 1.0 * hidden1,
    )


def _vectors_close(left, right):
    return all(math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12) for a, b in zip(left, right))


class W3ScaleSemanticOracleTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tempdir.name, SHARD)
        self.header_sha = _build_discriminative_safetensors(self.path)
        self.assertEqual(EXPECTED_HEADER_SHA256, self.header_sha)
        self.binding = build_standard_glm_per_expert_binding(
            weight_map=_weight_map(),
            model_revision=MODEL,
            index_digest=INDEX,
            layer_id=LAYER,
            num_experts=2,
            require_fp8_scales=True,
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def _load_expert1(self):
        backend = TinySafetensorsBackend(self.path)
        pager = PerExpertIndexPager(self.binding, backend)
        page = pager.load_selected([1], model_revision=MODEL, index_digest=INDEX)
        return pager, page

    def _assert_mismatch(self, actual):
        reference = _independent_expert1_reference(EXPERT1_INPUT)
        self.assertFalse(_vectors_close(actual, reference))

    def test_nonuniform_scales_match_independent_explicit_oracle(self):
        pager, page = self._load_expert1()
        self.assertEqual([[2.0, 0.5]], page.scales_by_expert[1]["gate_scale"])
        self.assertEqual([[0.25, 2.0]], page.scales_by_expert[1]["up_scale"])
        self.assertEqual([[0.5], [2.0]], page.scales_by_expert[1]["down_scale"])

        actual = _forward(page.weights_by_expert[1], page.scales_by_expert[1], EXPERT1_INPUT)
        reference = _independent_expert1_reference(EXPERT1_INPUT)
        self.assertTrue(_vectors_close(reference, EXPECTED_EXPERT1_OUTPUT))
        self.assertTrue(_vectors_close(actual, reference))
        self.assertFalse(pager.receipt().g2_admitted)

    def test_gate_up_scale_companion_swap_is_detected(self):
        _, page = self._load_expert1()
        scales = page.scales_by_expert[1]
        swapped = {
            "gate_scale": scales["up_scale"],
            "up_scale": scales["gate_scale"],
            "down_scale": scales["down_scale"],
        }
        self._assert_mismatch(_forward(page.weights_by_expert[1], swapped, EXPERT1_INPUT))

    def test_down_scale_row_misindex_is_detected(self):
        _, page = self._load_expert1()
        scales = page.scales_by_expert[1]
        misindexed = {
            "gate_scale": scales["gate_scale"],
            "up_scale": scales["up_scale"],
            "down_scale": list(reversed(scales["down_scale"])),
        }
        self._assert_mismatch(_forward(page.weights_by_expert[1], misindexed, EXPERT1_INPUT))

    def test_ignoring_scale_application_is_detected(self):
        _, page = self._load_expert1()
        all_ones = {
            "gate_scale": [[1.0, 1.0]],
            "up_scale": [[1.0, 1.0]],
            "down_scale": [[1.0], [1.0]],
        }
        self._assert_mismatch(_forward(page.weights_by_expert[1], all_ones, EXPERT1_INPUT))

    def test_single_scale_block_mutation_is_detected(self):
        _, page = self._load_expert1()
        scales = page.scales_by_expert[1]
        gate_scale = [row[:] for row in scales["gate_scale"]]
        gate_scale[0][1] = 1.0
        mutated = {
            "gate_scale": gate_scale,
            "up_scale": scales["up_scale"],
            "down_scale": scales["down_scale"],
        }
        self._assert_mismatch(_forward(page.weights_by_expert[1], mutated, EXPERT1_INPUT))


if __name__ == "__main__":
    unittest.main()
