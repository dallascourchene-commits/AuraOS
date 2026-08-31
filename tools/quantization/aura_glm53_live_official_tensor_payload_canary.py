#!/usr/bin/env python3
"""Bounded live official GLM-5.3 tensor-payload canary.

This consumer crosses exactly one new evidence boundary beyond PR398: it reads
one representative official FP8 tensor payload plus its F32 inverse-scale
companion from the immutable shard and hashes the raw bytes.  It deliberately
stops before dequantization, PR628 canonical-float32 source identity, E8 page
materialization, baseline equivalence, model execution, or authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import re
import struct
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen

SCHEMA = "AURA_GLM53_LIVE_OFFICIAL_TENSOR_PAYLOAD_CANARY_V1"
CONVERGENCE_COMMIT = "cd7ea64f104fc2dcfb89839306412a5e831bf683"
PR628_HEAD = "b8fd399ee0ca6b45a4ec7db58750e6d4105ae3ae"
PR628_RUN = 33367948262
PR398_HEAD = "131dd2a5fc8b4e2cf96c0bf598845d35e6706ef8"
PR398_RUN = 33336508527
PR398_JOB = 99324255699
OFFICIAL_REPOSITORY = "zai-org/GLM-5.3"
OFFICIAL_REVISION = "7cda81930d6e4cef42f48555de830aa32ecdde28"
OFFICIAL_INDEX_SHA256 = "e0fe7f28c1f853d4824e4d796374e3dacf1fe470988773952c79b063768134bf"
SELECTED_LAYER = 3
SELECTED_EXPERT = 0
SELECTED_SHARD = "model-00038-of-00141.safetensors"
SELECTED_HEADER_SHA256 = "8607b1b281f5ca8c7b166376e8f6d7eb9ca07f79200f6095f0f55ca35149ba56"
WEIGHT_KEY = "model.layers.3.mlp.experts.0.gate_proj.weight"
SCALE_KEY = "model.layers.3.mlp.experts.0.gate_proj.weight_scale_inv"
WEIGHT_DTYPE = "F8_E4M3"
WEIGHT_SHAPE = (2048, 6144)
WEIGHT_OFFSETS = (4_070_207_936, 4_082_790_848)
SCALE_DTYPE = "F32"
SCALE_SHAPE = (16, 48)
SCALE_OFFSETS = (993_728, 996_800)
MAX_HEADER_BYTES = 64 * 1024 * 1024
MAX_CANARY_PAYLOAD_BYTES = 16 * 1024 * 1024
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class PayloadCanaryError(ValueError):
    pass


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _receipt_sha(value: object) -> str:
    return _sha256(_canonical(value))


def _expected_bytes(dtype: str, shape: tuple[int, ...]) -> int:
    sizes = {"F8_E4M3": 1, "F32": 4}
    if dtype not in sizes or not shape or any(type(x) is not int or x <= 0 for x in shape):
        raise PayloadCanaryError("invalid dtype/shape")
    return math.prod(shape) * sizes[dtype]


def _validate_parent_metadata() -> None:
    if WEIGHT_OFFSETS[1] - WEIGHT_OFFSETS[0] != _expected_bytes(WEIGHT_DTYPE, WEIGHT_SHAPE):
        raise PayloadCanaryError("weight offset/shape mismatch")
    if SCALE_OFFSETS[1] - SCALE_OFFSETS[0] != _expected_bytes(SCALE_DTYPE, SCALE_SHAPE):
        raise PayloadCanaryError("scale offset/shape mismatch")
    total = _expected_bytes(WEIGHT_DTYPE, WEIGHT_SHAPE) + _expected_bytes(SCALE_DTYPE, SCALE_SHAPE)
    if total > MAX_CANARY_PAYLOAD_BYTES:
        raise PayloadCanaryError("canary byte ceiling exceeded")


def hf_resolve_url(repo_id: str, revision: str, path: str) -> str:
    if repo_id != OFFICIAL_REPOSITORY or revision != OFFICIAL_REVISION or path != SELECTED_SHARD:
        raise PayloadCanaryError("immutable source identity mismatch")
    return f"https://huggingface.co/{repo_id}/resolve/{revision}/{quote(path, safe='/')}?download=true"


def urllib_read_range(url: str, start: int, length: int) -> bytes:
    if type(start) is not int or start < 0 or type(length) is not int or length <= 0:
        raise PayloadCanaryError("invalid range")
    end = start + length - 1
    request = Request(
        url,
        headers={
            "User-Agent": "AuraOS-Q10-PayloadCanary/1",
            "Range": f"bytes={start}-{end}",
            "Accept-Encoding": "identity",
        },
    )
    with urlopen(request, timeout=120) as response:
        status = getattr(response, "status", None) or response.getcode()
        if status != 206:
            raise PayloadCanaryError(f"range not honored: {status}")
        content_range = str(response.headers.get("Content-Range", ""))
        if not content_range.startswith(f"bytes {start}-{end}/"):
            raise PayloadCanaryError(f"content-range mismatch: {content_range}")
        raw = response.read(length + 1)
    if len(raw) != length:
        raise PayloadCanaryError(f"range length mismatch: {len(raw)} != {length}")
    return raw


@dataclass(frozen=True)
class LiveOfficialTensorPayloadCanaryReceipt:
    schema: str
    convergence_commit: str
    exact_parent_heads: tuple[str, str]
    exact_parent_runs: tuple[int, int]
    pr398_job: int
    official_repository: str
    official_revision: str
    official_index_sha256: str
    selected_layer: int
    selected_expert: int
    selected_shard: str
    historical_header_sha256: str
    live_header_length_bytes: int
    weight_key: str
    weight_dtype: str
    weight_shape: tuple[int, ...]
    weight_relative_offsets: tuple[int, int]
    weight_absolute_range: tuple[int, int]
    weight_payload_bytes: int
    weight_payload_sha256: str
    scale_key: str
    scale_dtype: str
    scale_shape: tuple[int, ...]
    scale_relative_offsets: tuple[int, int]
    scale_absolute_range: tuple[int, int]
    scale_payload_bytes: int
    scale_payload_sha256: str
    total_payload_bytes_read: int
    live_representative_tensor_payload_pair_observed: bool
    representative_scope_only: bool
    full_expert_payload_observed: bool
    all_layer_expert_payload_uniformity_proven: bool
    raw_fp8_payload_is_pr628_canonical_float32_source_identity: bool
    official_tensor_to_pr628_source_tensor_relation_proven: bool
    candidate_page_materialization_owner_bound: bool
    baseline_same_official_source_tensor_set_proven: bool
    real_tensor_quantization_eligible: bool
    model_execution_observed: bool
    generalized_quality_proven: bool
    runtime_performance_proven: bool
    semantic_k27_authority: bool
    native_private_transformer_kv_accessed: bool
    gate10_promoted: bool
    deployment_authorized: bool

    @property
    def receipt_digest(self) -> str:
        return _receipt_sha(asdict(self))


def _build_receipt(*, header_len: int, weight_raw: bytes, scale_raw: bytes) -> LiveOfficialTensorPayloadCanaryReceipt:
    _validate_parent_metadata()
    if type(header_len) is not int or header_len <= 1 or header_len > MAX_HEADER_BYTES:
        raise PayloadCanaryError("header length out of bounds")
    weight_len = _expected_bytes(WEIGHT_DTYPE, WEIGHT_SHAPE)
    scale_len = _expected_bytes(SCALE_DTYPE, SCALE_SHAPE)
    if len(weight_raw) != weight_len or len(scale_raw) != scale_len:
        raise PayloadCanaryError("payload length mismatch")
    data_base = 8 + header_len
    weight_start = data_base + WEIGHT_OFFSETS[0]
    scale_start = data_base + SCALE_OFFSETS[0]
    receipt = LiveOfficialTensorPayloadCanaryReceipt(
        schema=SCHEMA,
        convergence_commit=CONVERGENCE_COMMIT,
        exact_parent_heads=(PR628_HEAD, PR398_HEAD),
        exact_parent_runs=(PR628_RUN, PR398_RUN),
        pr398_job=PR398_JOB,
        official_repository=OFFICIAL_REPOSITORY,
        official_revision=OFFICIAL_REVISION,
        official_index_sha256=OFFICIAL_INDEX_SHA256,
        selected_layer=SELECTED_LAYER,
        selected_expert=SELECTED_EXPERT,
        selected_shard=SELECTED_SHARD,
        historical_header_sha256=SELECTED_HEADER_SHA256,
        live_header_length_bytes=header_len,
        weight_key=WEIGHT_KEY,
        weight_dtype=WEIGHT_DTYPE,
        weight_shape=WEIGHT_SHAPE,
        weight_relative_offsets=WEIGHT_OFFSETS,
        weight_absolute_range=(weight_start, weight_start + weight_len),
        weight_payload_bytes=weight_len,
        weight_payload_sha256=_sha256(weight_raw),
        scale_key=SCALE_KEY,
        scale_dtype=SCALE_DTYPE,
        scale_shape=SCALE_SHAPE,
        scale_relative_offsets=SCALE_OFFSETS,
        scale_absolute_range=(scale_start, scale_start + scale_len),
        scale_payload_bytes=scale_len,
        scale_payload_sha256=_sha256(scale_raw),
        total_payload_bytes_read=weight_len + scale_len,
        live_representative_tensor_payload_pair_observed=True,
        representative_scope_only=True,
        full_expert_payload_observed=False,
        all_layer_expert_payload_uniformity_proven=False,
        raw_fp8_payload_is_pr628_canonical_float32_source_identity=False,
        official_tensor_to_pr628_source_tensor_relation_proven=False,
        candidate_page_materialization_owner_bound=False,
        baseline_same_official_source_tensor_set_proven=False,
        real_tensor_quantization_eligible=False,
        model_execution_observed=False,
        generalized_quality_proven=False,
        runtime_performance_proven=False,
        semantic_k27_authority=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
        deployment_authorized=False,
    )
    if not _SHA256_RE.fullmatch(receipt.weight_payload_sha256) or not _SHA256_RE.fullmatch(receipt.scale_payload_sha256):
        raise PayloadCanaryError("payload digest invalid")
    return receipt


def current_live_observation() -> LiveOfficialTensorPayloadCanaryReceipt:
    """Perform one live, bounded, immutable-source payload observation."""
    _validate_parent_metadata()
    url = hf_resolve_url(OFFICIAL_REPOSITORY, OFFICIAL_REVISION, SELECTED_SHARD)
    prefix = urllib_read_range(url, 0, 8)
    if len(prefix) != 8:
        raise PayloadCanaryError("header prefix length mismatch")
    header_len = struct.unpack("<Q", prefix)[0]
    if header_len <= 1 or header_len > MAX_HEADER_BYTES:
        raise PayloadCanaryError("header length out of bounds")
    data_base = 8 + header_len
    weight_len = _expected_bytes(WEIGHT_DTYPE, WEIGHT_SHAPE)
    scale_len = _expected_bytes(SCALE_DTYPE, SCALE_SHAPE)
    weight_raw = urllib_read_range(url, data_base + WEIGHT_OFFSETS[0], weight_len)
    scale_raw = urllib_read_range(url, data_base + SCALE_OFFSETS[0], scale_len)
    return _build_receipt(header_len=header_len, weight_raw=weight_raw, scale_raw=scale_raw)


def main() -> None:
    receipt = current_live_observation()
    print(json.dumps({**asdict(receipt), "receipt_digest": receipt.receipt_digest}, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
