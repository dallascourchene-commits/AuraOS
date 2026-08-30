import hashlib
import json
import math
import os
import struct
import tempfile
import unittest

from tools.awj032.glm53_official_w2_observation import (
    OFFICIAL_INDEX_SHA256,
    OFFICIAL_LAYER,
    OFFICIAL_MODEL_REVISION,
    OFFICIAL_REPO_ID,
    OfficialW2ObservationError,
    bind_official_w2_observation,
)
from tools.awj032.glm53_per_expert_index_pager import (
    BACKEND_IO_ATTESTATION_SCHEMA,
    PerExpertIndexPager,
    build_standard_glm_per_expert_binding,
)

MODEL = "w3-native-fixture-revision"
INDEX = "w3-native-fixture-index"
REPO = "local/w3-native-fixture"
LAYER = "model.layers.3"
SHARD = "tiny-w3.safetensors"
BLOCK = (2, 2)
EXPECTED_HEADER_SHA256 = "1c32807a28c447db79928a0886c3a03fc5ed2968f5a02188da3f95e18c63194c"

_FP8_ENCODE = {
    0.0: 0x00,
    0.25: 0x28,
    0.5: 0x30,
    1.0: 0x38,
    2.0: 0x40,
    -0.25: 0xA8,
    -0.5: 0xB0,
    -1.0: 0xB8,
    -2.0: 0xC0,
}


def _decode_e4m3(byte):
    sign = -1.0 if byte & 0x80 else 1.0
    exp = (byte >> 3) & 0x0F
    mant = byte & 0x07
    if exp == 0:
        return sign * (mant / 8.0) * (2.0 ** -6)
    if exp == 0x0F:
        raise ValueError("fixture forbids E4M3 special exponent")
    return sign * (1.0 + mant / 8.0) * (2.0 ** (exp - 7))


def _fp8_bytes(matrix):
    return bytes(_FP8_ENCODE[value] for row in matrix for value in row)


def _f32_bytes(matrix):
    flat = [value for row in matrix for value in row]
    return struct.pack("<" + "f" * len(flat), *flat)


def _fixture_values(expert):
    if expert == 0:
        return {
            "gate": [[1.0, 0.5, -0.5, 0.25], [0.25, -0.25, 1.0, -1.0]],
            "up": [[0.5, 1.0, 0.25, -0.5], [1.0, 0.5, -0.25, 0.25]],
            "down": [[1.0, 0.5], [0.5, 1.0], [-0.5, 0.25], [0.25, -0.5]],
        }
    return {
        "gate": [[0.5, 0.25, 1.0, -0.5], [-0.25, 1.0, 0.5, 0.25]],
        "up": [[1.0, -0.5, 0.5, 0.25], [0.25, 0.5, 1.0, -0.25]],
        "down": [[0.5, 1.0], [1.0, 0.25], [0.25, -0.5], [-0.5, 0.5]],
    }


def _weight_map():
    out = {}
    for expert in range(2):
        for proj in ("gate_proj", "up_proj", "down_proj"):
            out[f"{LAYER}.mlp.experts.{expert}.{proj}.weight"] = SHARD
            out[f"{LAYER}.mlp.experts.{expert}.{proj}.weight_scale_inv"] = SHARD
    return out


def _tensor_spec(dtype, matrix):
    shape = [len(matrix), len(matrix[0])]
    raw = _fp8_bytes(matrix) if dtype == "F8_E4M3" else _f32_bytes(matrix)
    return dtype, shape, raw


def _build_safetensors(path):
    tensors = {}
    for expert in range(2):
        values = _fixture_values(expert)
        tensors[f"{LAYER}.mlp.experts.{expert}.gate_proj.weight"] = _tensor_spec("F8_E4M3", values["gate"])
        tensors[f"{LAYER}.mlp.experts.{expert}.gate_proj.weight_scale_inv"] = _tensor_spec("F32", [[1.0, 1.0]])
        tensors[f"{LAYER}.mlp.experts.{expert}.up_proj.weight"] = _tensor_spec("F8_E4M3", values["up"])
        tensors[f"{LAYER}.mlp.experts.{expert}.up_proj.weight_scale_inv"] = _tensor_spec("F32", [[1.0, 1.0]])
        tensors[f"{LAYER}.mlp.experts.{expert}.down_proj.weight"] = _tensor_spec("F8_E4M3", values["down"])
        tensors[f"{LAYER}.mlp.experts.{expert}.down_proj.weight_scale_inv"] = _tensor_spec("F32", [[1.0], [1.0]])

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


def _read_matrix(dtype, shape, raw):
    rows, cols = shape
    if dtype == "F8_E4M3":
        values = [_decode_e4m3(b) for b in raw]
    elif dtype == "F32":
        values = list(struct.unpack("<" + "f" * (len(raw) // 4), raw))
    else:
        raise AssertionError(dtype)
    return [values[r * cols : (r + 1) * cols] for r in range(rows)]


class TinySafetensorsBackend:
    def __init__(self, path):
        self.path = path
        self.payload_reads = []

    def _header(self):
        with open(self.path, "rb") as handle:
            header_len = struct.unpack("<Q", handle.read(8))[0]
            raw = handle.read(header_len)
        return json.loads(raw), 8 + header_len

    def read_tensor(self, shard, key):
        if shard != SHARD:
            raise FileNotFoundError(shard)
        header, payload_start = self._header()
        spec = header[key]
        start, end = spec["data_offsets"]
        with open(self.path, "rb") as handle:
            handle.seek(payload_start + start)
            raw = handle.read(end - start)
        if len(raw) != end - start:
            raise OSError("short bounded tensor read")
        self.payload_reads.append((key, start, end))
        return _read_matrix(spec["dtype"], spec["shape"], raw)

    def io_attestation(self, binding_digest):
        return {
            "schema": BACKEND_IO_ATTESTATION_SCHEMA,
            "binding_digest": binding_digest,
            "attestation_id": "w3-tiny-safetensors-selected-only",
            "physical_selected_only": True,
            "whole_bank_reads": 0,
            "whole_bank_materialized": False,
        }


def _matvec(matrix, vector):
    return [sum(a * b for a, b in zip(row, vector)) for row in matrix]


def _dequant(weight, scale):
    return [
        [weight[r][c] * scale[r // BLOCK[0]][c // BLOCK[1]] for c in range(len(weight[0]))]
        for r in range(len(weight))
    ]


def _forward(weights, scales, x):
    gate = _dequant(weights["gate"], scales["gate_scale"])
    up = _dequant(weights["up"], scales["up_scale"])
    down = _dequant(weights["down"], scales["down_scale"])
    g = _matvec(gate, x)
    u = _matvec(up, x)
    h = [(v / (1.0 + math.exp(-v))) * u_i for v, u_i in zip(g, u)]
    return _matvec(down, h)


class W3NativePerExpertFixtureTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tempdir.name, SHARD)
        self.header_sha = _build_safetensors(self.path)
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

    def test_actual_per_expert_pager_reads_only_selected_tiny_safetensors_ranges(self):
        backend = TinySafetensorsBackend(self.path)
        pager = PerExpertIndexPager(self.binding, backend)
        page = pager.load_selected([1, 1], model_revision=MODEL, index_digest=INDEX)
        self.assertEqual((1,), page.expert_ids)
        self.assertEqual(6, page.tensor_reads)
        self.assertEqual(6, len(backend.payload_reads))
        self.assertTrue(all(".experts.1." in key for key, _, _ in backend.payload_reads))
        receipt = pager.receipt()
        self.assertTrue(receipt.physical_io_attested)
        self.assertTrue(receipt.selected_expert_tensor_reads_only)
        self.assertEqual(0, receipt.whole_bank_reads)
        self.assertFalse(receipt.whole_expert_bank_materialized)
        self.assertFalse(receipt.g2_admitted)
        self.assertIn("NO_FLAGSHIP_RUNTIME_OR_G2_PROOF", receipt.claim_ceiling)

    def test_test_local_fp8_oracle_matches_actual_pager_payload(self):
        backend = TinySafetensorsBackend(self.path)
        pager = PerExpertIndexPager(self.binding, backend)
        page = pager.load_selected([1], model_revision=MODEL, index_digest=INDEX)
        x = [0.5, -0.25, 1.0, 0.25]
        paged = _forward(page.weights_by_expert[1], page.scales_by_expert[1], x)
        values = _fixture_values(1)
        reference = _forward(
            {"gate": values["gate"], "up": values["up"], "down": values["down"]},
            {"gate_scale": [[1.0, 1.0]], "up_scale": [[1.0, 1.0]], "down_scale": [[1.0], [1.0]]},
            x,
        )
        for actual, expected in zip(paged, reference):
            self.assertTrue(math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12))
        self.assertFalse(pager.receipt().g2_admitted)

    def test_synthetic_fixture_stays_below_official_w2_producer_plane(self):
        self.assertIsNone(
            bind_official_w2_observation(
                repo_id=REPO,
                model_revision=MODEL,
                index_sha256=INDEX,
                layer=3,
                expert=1,
                observed_receipt_digest="0" * 40,
            )
        )

    def test_official_source_receipt_contradiction_fails_hard(self):
        with self.assertRaises(OfficialW2ObservationError) as ctx:
            bind_official_w2_observation(
                repo_id=OFFICIAL_REPO_ID,
                model_revision=OFFICIAL_MODEL_REVISION,
                index_sha256=OFFICIAL_INDEX_SHA256,
                layer=OFFICIAL_LAYER,
                expert=0,
                observed_receipt_digest="0" * 40,
            )
        self.assertEqual("OFFICIAL_W2_OBSERVATION_RECEIPT_MISMATCH", ctx.exception.code)


if __name__ == "__main__":
    unittest.main()
