#!/usr/bin/env python3
"""Q5: equal-rate E8 vs hypercube canary on exact official GLM-5.3 weights.

Derivation anchors (non-self):
- Q13 exact-green full representative canonical source set.
- AGELF no-privilege ablation law (Drive 1qgf9Q0vt2ns5KlyS7Cb21zWsvzI1rre4-f4MgK_OLNQ).

The Q4 codec is implementation substrate only.  This module reads eight fixed 64-weight
windows from the immutable official Q13 source world (four gate-half windows from
``gate_up_proj`` and four ``down_proj`` windows), applies the exact 1.25-bpw E8 and
hypercube codecs, and reports distortion.  E8 win/tie/loss are all valid evidence.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import struct
from typing import Sequence

import numpy as np

from tools.quantization import aura_glm53_full_representative_canonical_source_set as q13
from tools.quantization import aura_glm53_equal_rate_e8_ablation as q4

SCHEMA = "AURA_GLM53_OFFICIAL_EQUAL_RATE_E8_CANARY_V1"
Q13_HEAD = "eb09b5ffd14577d1676f57bb908e5ddd81125605"
Q13_RUN = 33397035043
Q13_SOURCE_BLOB = "5d3b365911ecd78bb2698a9423807dbf13f1b5ad"
Q13_SOURCE_SET_DIGEST = "f41495beb566f4c49f5674f2820f3d5c32591647be552048cf711a885a1b71b6"
AGELF_DRIVE_ID = "1qgf9Q0vt2ns5KlyS7Cb21zWsvzI1rre4-f4MgK_OLNQ"
Q4_CODEC_BLOB = "8c35c47f6b162bf03324f509dc1b820b6eb689f9"
WINDOW_STARTS = (0, 128, 256, 384)
WINDOW_WEIGHTS = 64

ROLE_SPECS = {
    "gate_up_proj": {
        "component": "gate_proj",
        "weight": "gate_weight",
        "scale": "gate_scale",
        "parent_tensor_sha256": "46eb726b48a423865b50ffe261881dc5b3667344f93e24e5732b2484d6096c4a",
        "component_tensor_sha256": "0db00dc5a76ce5b91273dd7be7e12b5d47121154b5c1f440131c399ce245a43e",
    },
    "down_proj": {
        "component": "down_proj",
        "weight": "down_weight",
        "scale": "down_scale",
        "parent_tensor_sha256": "6ddd0776b011cde6948d5d780630700dfd69ce49907356d371a6d54b59040953",
        "component_tensor_sha256": "6ddd0776b011cde6948d5d780630700dfd69ce49907356d371a6d54b59040953",
    },
}

class OfficialCanaryError(ValueError):
    pass


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _classify(e8_mse: float, control_mse: float) -> str:
    if math.isclose(e8_mse, control_mse, rel_tol=0.0, abs_tol=1e-15):
        return "TIE"
    return "E8_WIN" if e8_mse < control_mse else "CONTROL_WIN"


def _validate_start(role: str, start: int) -> tuple[dict[str, object], dict[str, object], int]:
    if role not in ROLE_SPECS or start not in WINDOW_STARTS:
        raise OfficialCanaryError("UNREGISTERED_CANARY_COORDINATE")
    spec = ROLE_SPECS[role]
    w = q13.SLICES[str(spec["weight"])]
    s = q13.SLICES[str(spec["scale"])]
    cols = int(w["shape"][1])
    if start + WINDOW_WEIGHTS > cols or start % 128:
        raise OfficialCanaryError("CANARY_SPAN_NOT_ONE_FP8_BLOCK_CELL")
    scale_col = start // 128
    if scale_col >= int(s["shape"][1]):
        raise OfficialCanaryError("CANARY_SCALE_CELL_OUT_OF_RANGE")
    return w, s, scale_col


def _decode_tile(weight_raw: bytes, scale_raw: bytes) -> tuple[float, ...]:
    if len(weight_raw) != WINDOW_WEIGHTS or len(scale_raw) != 4:
        raise OfficialCanaryError("LIVE_TILE_LENGTH_MISMATCH")
    codes = np.frombuffer(weight_raw, dtype=np.uint8)
    if np.any((codes == 0x7F) | (codes == 0xFF)):
        raise OfficialCanaryError("E4M3FN_NAN_IN_CANARY")
    scale = float(np.frombuffer(scale_raw, dtype="<f4")[0])
    if not math.isfinite(scale) or scale <= 0.0:
        raise OfficialCanaryError("INVALID_CANARY_SCALE")
    values = np.asarray(q13.decode_e4m3fn_table()[codes] * scale, dtype="<f4")
    return tuple(float(x) for x in values)


def _evaluate(values: Sequence[float]) -> tuple[bytes, bytes, float, float, str]:
    e8 = q4.encode_group(values, q4.E8_SCHEME)
    control = q4.encode_group(values, q4.HYPERCUBE_SCHEME)
    if len(e8) != 10 or len(control) != 10 or q4.CODEC_BPW != 1.25:
        raise OfficialCanaryError("EQUAL_RATE_CODEC_DRIFT")
    e8_mse = q4.mse(values, q4.decode_group(e8, q4.E8_SCHEME))
    control_mse = q4.mse(values, q4.decode_group(control, q4.HYPERCUBE_SCHEME))
    return e8, control, e8_mse, control_mse, _classify(e8_mse, control_mse)


@dataclass(frozen=True)
class OfficialTileResult:
    tensor_role: str
    source_component: str
    row: int
    col_start: int
    weights: int
    parent_source_tensor_sha256: str
    component_source_tensor_sha256: str
    raw_weight_window_sha256: str
    raw_scale_cell_sha256: str
    canonical_float32_tile_sha256: str
    e8_payload_sha256: str
    control_payload_sha256: str
    e8_mse: float
    control_mse: float
    e8_over_control: float
    outcome: str


@dataclass(frozen=True)
class OfficialEqualRateCanaryReceipt:
    schema: str
    q13_head: str
    q13_run: int
    q13_source_blob: str
    q13_source_tensor_set_digest: str
    agelf_drive_id: str
    q4_codec_blob: str
    official_repository: str
    official_revision: str
    selected_layer: int
    selected_expert: int
    selected_shard: str
    live_header_length_bytes: int
    codec_bpw_e8: float
    codec_bpw_control: float
    equal_rate: bool
    total_official_weights_observed: int
    tiles: tuple[OfficialTileResult, ...]
    aggregate_e8_mse: float
    aggregate_control_mse: float
    aggregate_e8_over_control: float
    aggregate_outcome: str
    official_source_equal_rate_distortion_evidence: bool
    representative_canary_scope_only: bool
    geometry_privileged: bool
    full_tensor_quantized: bool
    whole_model_quantized: bool
    glm_quality_proven: bool
    runtime_performance_proven: bool
    native_private_transformer_kv_accessed: bool
    semantic_k27_authority: bool
    gate10_promoted: bool

    @property
    def receipt_digest(self) -> str:
        return _sha(_canonical(asdict(self)))


def current_official_equal_rate_canary() -> OfficialEqualRateCanaryReceipt:
    url = q13.canary.hf_resolve_url(q13.OFFICIAL_REPOSITORY, q13.OFFICIAL_REVISION, q13.SELECTED_SHARD)
    header_len = struct.unpack("<Q", q13.canary.urllib_read_range(url, 0, 8))[0]
    if header_len != q13.EXPECTED_HEADER_LENGTH:
        raise OfficialCanaryError("LIVE_HEADER_GENERATION_DRIFT")
    base = 8 + header_len
    tiles: list[OfficialTileResult] = []
    e8_errors: list[float] = []
    control_errors: list[float] = []
    for role in ("gate_up_proj", "down_proj"):
        role_spec = ROLE_SPECS[role]
        for start in WINDOW_STARTS:
            w, s, scale_col = _validate_start(role, start)
            weight_raw = q13.canary.urllib_read_range(url, base + int(w["offset"][0]) + start, WINDOW_WEIGHTS)
            scale_offset = (scale_col * 4)
            scale_raw = q13.canary.urllib_read_range(url, base + int(s["offset"][0]) + scale_offset, 4)
            values = _decode_tile(weight_raw, scale_raw)
            canonical_tile = np.asarray(values, dtype="<f4").tobytes(order="C")
            e8, control, e8_mse, control_mse, outcome = _evaluate(values)
            e8_errors.append(e8_mse); control_errors.append(control_mse)
            tiles.append(OfficialTileResult(
                tensor_role=role,
                source_component=str(role_spec["component"]),
                row=0,
                col_start=start,
                weights=WINDOW_WEIGHTS,
                parent_source_tensor_sha256=str(role_spec["parent_tensor_sha256"]),
                component_source_tensor_sha256=str(role_spec["component_tensor_sha256"]),
                raw_weight_window_sha256=_sha(weight_raw),
                raw_scale_cell_sha256=_sha(scale_raw),
                canonical_float32_tile_sha256=_sha(canonical_tile),
                e8_payload_sha256=_sha(e8),
                control_payload_sha256=_sha(control),
                e8_mse=e8_mse,
                control_mse=control_mse,
                e8_over_control=e8_mse / control_mse if control_mse else math.inf,
                outcome=outcome,
            ))
    e8_mean = sum(e8_errors) / len(e8_errors)
    control_mean = sum(control_errors) / len(control_errors)
    return OfficialEqualRateCanaryReceipt(
        schema=SCHEMA,
        q13_head=Q13_HEAD,
        q13_run=Q13_RUN,
        q13_source_blob=Q13_SOURCE_BLOB,
        q13_source_tensor_set_digest=Q13_SOURCE_SET_DIGEST,
        agelf_drive_id=AGELF_DRIVE_ID,
        q4_codec_blob=Q4_CODEC_BLOB,
        official_repository=q13.OFFICIAL_REPOSITORY,
        official_revision=q13.OFFICIAL_REVISION,
        selected_layer=q13.SELECTED_LAYER,
        selected_expert=q13.SELECTED_EXPERT,
        selected_shard=q13.SELECTED_SHARD,
        live_header_length_bytes=header_len,
        codec_bpw_e8=q4.CODEC_BPW,
        codec_bpw_control=q4.CODEC_BPW,
        equal_rate=True,
        total_official_weights_observed=len(tiles) * WINDOW_WEIGHTS,
        tiles=tuple(tiles),
        aggregate_e8_mse=e8_mean,
        aggregate_control_mse=control_mean,
        aggregate_e8_over_control=e8_mean / control_mean if control_mean else math.inf,
        aggregate_outcome=_classify(e8_mean, control_mean),
        official_source_equal_rate_distortion_evidence=True,
        representative_canary_scope_only=True,
        geometry_privileged=False,
        full_tensor_quantized=False,
        whole_model_quantized=False,
        glm_quality_proven=False,
        runtime_performance_proven=False,
        native_private_transformer_kv_accessed=False,
        semantic_k27_authority=False,
        gate10_promoted=False,
    )


def main() -> None:
    r = current_official_equal_rate_canary()
    body = asdict(r); body["receipt_digest"] = r.receipt_digest
    print(json.dumps(body, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
