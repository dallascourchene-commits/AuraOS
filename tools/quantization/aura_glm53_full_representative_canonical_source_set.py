#!/usr/bin/env python3
"""Derive the representative official GLM-5.3 canonical E8 source-tensor set.

Q13 joins two exact-green non-self consequences:
- PR656 semantic generation owns all six live raw layer-3/expert-0 FP8+scale slices.
- PR641 owns the concrete E8 source-tensor-set identity grammar.

This module deterministically dequantizes gate/up/down, composes gate+up exactly as
GLM-MoE-DSA loading does, and emits the two canonical source identities expected
by PR628/PR641: ``gate_up_proj`` and ``down_proj``. It does not compress or
materialize an E8 page, prove any page came from these tensors, execute a model,
or grant authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import struct

import numpy as np

from tools.quantization import aura_glm53_live_official_tensor_payload_canary as canary

SCHEMA = "AURA_GLM53_FULL_REPRESENTATIVE_CANONICAL_SOURCE_SET_V1"
SOURCE_SET_SCHEMA = "AURA_GLM53_E8_SOURCE_TENSOR_SET_V1"
CONVERGENCE_COMMIT = "6a1247b7ab091e67e52939e688f95bcc64139d4b"
PR656_SEMANTIC_HEAD = "ac3247ed75aa8646490db8d953b16aecd5ebec2d"
PR656_RUN = 33395608248
PR656_JOB = 99499276445
PR656_SOURCE_BLOB = "87e581cbe5a25c538a34eb3475bdd13bb52bd158"
PR656_RECEIPT_DIGEST = "f3bbd2f6654d0cc254ff2bc5a14e9dff3b59cdca83ccf86729e9f5ad270a1943"
PR641_HEAD = "a8d4605a36e04d64cf03f43f457be4bde553e602"
PR641_RUN = 33370700852
PR641_SOURCE_BLOB = "157afcb2e457c630d03a8c72aef09f0a6ba04a4d"
PR628_SOURCE_BLOB = "5df2cd69a1519b2626cb52c1d8f23a25504425d9"

OFFICIAL_REPOSITORY = "zai-org/GLM-5.3"
OFFICIAL_REVISION = "7cda81930d6e4cef42f48555de830aa32ecdde28"
SELECTED_SHARD = "model-00038-of-00141.safetensors"
SELECTED_LAYER = 3
SELECTED_EXPERT = 0
EXPECTED_HEADER_LENGTH = 105_424
BLOCK_SHAPE = (128, 128)
CANONICAL_FLOAT32_DOMAIN = "IEEE754_BINARY32_LITTLE_ENDIAN_C_ORDER"

# Exact live payload generation established by PR650 + PR656.
SLICES = {
    "gate_weight": {
        "key": "model.layers.3.mlp.experts.0.gate_proj.weight",
        "shape": (2048, 6144), "dtype": "F8_E4M3", "offset": (4_070_207_936, 4_082_790_848),
        "bytes": 12_582_912, "sha256": "2d4e5f36478b598043431b3691ce6a48639e01b6f804b1db62ca4af4d14063e8",
    },
    "gate_scale": {
        "key": "model.layers.3.mlp.experts.0.gate_proj.weight_scale_inv",
        "shape": (16, 48), "dtype": "F32", "offset": (993_728, 996_800),
        "bytes": 3_072, "sha256": "671dd3b32b3f4cc651b93f3420ae47957ae09c1f745d278c0795d56e5d511c55",
    },
    "up_weight": {
        "key": "model.layers.3.mlp.experts.0.up_proj.weight",
        "shape": (2048, 6144), "dtype": "F8_E4M3", "offset": (4_082_790_848, 4_095_373_760),
        "bytes": 12_582_912, "sha256": "cabf58cb2f5f63d4c12c9530a861686c18c9f5e1a716a3e560c0e6a963414421",
    },
    "up_scale": {
        "key": "model.layers.3.mlp.experts.0.up_proj.weight_scale_inv",
        "shape": (16, 48), "dtype": "F32", "offset": (996_800, 999_872),
        "bytes": 3_072, "sha256": "84ec09e9e009a48eb3deda92b20fa1f2cdf16fb38dfe2c9a8f1b47fe73562501",
    },
    "down_weight": {
        "key": "model.layers.3.mlp.experts.0.down_proj.weight",
        "shape": (6144, 2048), "dtype": "F8_E4M3", "offset": (4_057_625_024, 4_070_207_936),
        "bytes": 12_582_912, "sha256": "1626de120c6b7c58fe56c536653e4cb8b942a7e6a792c4af2f4eacf6a9d2d0b6",
    },
    "down_scale": {
        "key": "model.layers.3.mlp.experts.0.down_proj.weight_scale_inv",
        "shape": (48, 16), "dtype": "F32", "offset": (990_656, 993_728),
        "bytes": 3_072, "sha256": "cd80ffba7a858206f51153e81df635c9d488e38b1c89aef0d091a984a23a37a6",
    },
}


class CanonicalSourceSetError(ValueError):
    pass


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def _object_sha(value: object) -> str:
    return _sha256(_canonical(value))


def decode_e4m3fn_table() -> np.ndarray:
    table = np.empty(256, dtype="<f4")
    for code in range(256):
        sign = -1.0 if code & 0x80 else 1.0
        exponent = (code >> 3) & 0x0F
        mantissa = code & 0x07
        if exponent == 0x0F and mantissa == 0x07:
            table[code] = np.nan
        elif exponent == 0:
            table[code] = sign * math.ldexp(float(mantissa), -9)
        else:
            table[code] = sign * math.ldexp(1.0 + mantissa / 8.0, exponent - 7)
    return table


def dequantize_pair(weight_raw: bytes, scale_raw: bytes, weight_shape: tuple[int, int], scale_shape: tuple[int, int]) -> bytes:
    rows, cols = weight_shape
    sr, sc = scale_shape
    if rows <= 0 or cols <= 0 or sr <= 0 or sc <= 0 or rows % sr or cols % sc:
        raise CanonicalSourceSetError("INVALID_WEIGHT_SCALE_GEOMETRY")
    br, bc = rows // sr, cols // sc
    if (br, bc) != BLOCK_SHAPE:
        raise CanonicalSourceSetError("UNEXPECTED_FP8_BLOCK_GEOMETRY")
    if len(weight_raw) != rows * cols or len(scale_raw) != sr * sc * 4:
        raise CanonicalSourceSetError("PAYLOAD_LENGTH_MISMATCH")
    codes = np.frombuffer(weight_raw, dtype=np.uint8)
    if np.any((codes == 0x7F) | (codes == 0xFF)):
        raise CanonicalSourceSetError("E4M3FN_NAN_IN_WEIGHT")
    scales = np.frombuffer(scale_raw, dtype="<f4").reshape(scale_shape)
    if not np.all(np.isfinite(scales)) or not np.all(scales > 0.0):
        raise CanonicalSourceSetError("INVALID_SCALE_GRID")
    q = decode_e4m3fn_table()[codes].reshape(weight_shape)
    out = (q.reshape(sr, br, sc, bc) * scales[:, None, :, None]).reshape(weight_shape)
    return np.asarray(out, dtype="<f4", order="C").tobytes(order="C")


def _read_all_slices() -> tuple[int, dict[str, bytes]]:
    url = canary.hf_resolve_url(OFFICIAL_REPOSITORY, OFFICIAL_REVISION, SELECTED_SHARD)
    prefix = canary.urllib_read_range(url, 0, 8)
    header_len = struct.unpack("<Q", prefix)[0]
    if header_len != EXPECTED_HEADER_LENGTH:
        raise CanonicalSourceSetError("LIVE_HEADER_LENGTH_DRIFT")
    base = 8 + header_len
    payloads: dict[str, bytes] = {}
    for name, spec in SLICES.items():
        raw = canary.urllib_read_range(url, base + spec["offset"][0], spec["bytes"])
        if _sha256(raw) != spec["sha256"]:
            raise CanonicalSourceSetError(f"RAW_GENERATION_DRIFT:{name}")
        payloads[name] = raw
    return header_len, payloads


def source_set_digest(*, gate_up_sha256: str, down_sha256: str) -> tuple[str, tuple[dict[str, object], ...]]:
    for digest in (gate_up_sha256, down_sha256):
        if len(digest) != 64:
            raise CanonicalSourceSetError("SOURCE_SHA256_REQUIRED")
        bytes.fromhex(digest)
    entries = [
        {
            "layer_id": SELECTED_LAYER,
            "expert_id": SELECTED_EXPERT,
            "tensor_role": "gate_up_proj",
            "source_tensor_sha256": gate_up_sha256,
            "source_shape": [4096, 6144],
        },
        {
            "layer_id": SELECTED_LAYER,
            "expert_id": SELECTED_EXPERT,
            "tensor_role": "down_proj",
            "source_tensor_sha256": down_sha256,
            "source_shape": [6144, 2048],
        },
    ]
    entries.sort(key=lambda x: (x["layer_id"], x["expert_id"], x["tensor_role"], x["source_tensor_sha256"]))
    digest = _object_sha({"schema": SOURCE_SET_SCHEMA, "entries": entries})
    return digest, tuple(entries)


@dataclass(frozen=True)
class FullRepresentativeCanonicalSourceSetReceipt:
    schema: str
    convergence_commit: str
    exact_parent_heads: tuple[str, str]
    exact_parent_runs: tuple[int, int]
    exact_parent_source_blobs: tuple[str, str]
    pr656_job: int
    pr656_receipt_digest: str
    pr628_source_blob: str
    official_repository: str
    official_revision: str
    selected_layer: int
    selected_expert: int
    selected_shard: str
    live_header_length_bytes: int
    total_raw_payload_bytes_reobserved: int
    raw_slice_hashes: tuple[tuple[str, str], ...]
    fp8_block_shape: tuple[int, int]
    canonical_float32_domain: str
    gate_canonical_float32_sha256: str
    up_canonical_float32_sha256: str
    down_canonical_float32_sha256: str
    gate_up_canonical_float32_sha256: str
    gate_up_source_shape: tuple[int, int]
    down_source_shape: tuple[int, int]
    source_set_schema: str
    source_set_entries: tuple[dict[str, object], ...]
    source_tensor_set_digest: str
    full_representative_raw_payload_coverage_reobserved: bool
    fp8_dequantization_semantics_bound_for_all_three_projections: bool
    gate_up_source_layout_relation_bound: bool
    pr628_source_hash_byte_domain_matched: bool
    pr641_source_tensor_set_grammar_matched: bool
    full_representative_canonical_source_set_bound: bool
    representative_official_source_tensor_set_authenticated: bool
    representative_scope_only: bool
    actual_e8_page_payload_materialized: bool
    official_tensor_to_e8_page_derivation_proven: bool
    candidate_page_materialization_owner_bound: bool
    baseline_same_official_source_tensor_set_proven: bool
    whole_model_coverage_proven: bool
    model_execution_observed: bool
    generalized_quality_proven: bool
    runtime_performance_proven: bool
    semantic_k27_authority: bool
    native_private_transformer_kv_accessed: bool
    gate10_promoted: bool
    merge_or_deployment_authorized: bool

    @property
    def receipt_digest(self) -> str:
        return _object_sha(asdict(self))


def current_full_representative_source_set() -> FullRepresentativeCanonicalSourceSetReceipt:
    header_len, p = _read_all_slices()
    gate = dequantize_pair(p["gate_weight"], p["gate_scale"], (2048, 6144), (16, 48))
    gate_sha = _sha256(gate)
    gate_up_hasher = hashlib.sha256(); gate_up_hasher.update(gate)
    del gate

    up = dequantize_pair(p["up_weight"], p["up_scale"], (2048, 6144), (16, 48))
    up_sha = _sha256(up); gate_up_hasher.update(up); del up
    gate_up_sha = gate_up_hasher.hexdigest()

    down = dequantize_pair(p["down_weight"], p["down_scale"], (6144, 2048), (48, 16))
    down_sha = _sha256(down); del down

    set_digest, entries = source_set_digest(gate_up_sha256=gate_up_sha, down_sha256=down_sha)
    raw_hashes = tuple(sorted((SLICES[name]["key"], SLICES[name]["sha256"]) for name in SLICES))
    total_raw = sum(int(SLICES[name]["bytes"]) for name in SLICES)
    if total_raw != 37_757_952:
        raise CanonicalSourceSetError("TOTAL_RAW_BYTE_COUNT_DRIFT")

    return FullRepresentativeCanonicalSourceSetReceipt(
        schema=SCHEMA,
        convergence_commit=CONVERGENCE_COMMIT,
        exact_parent_heads=(PR656_SEMANTIC_HEAD, PR641_HEAD),
        exact_parent_runs=(PR656_RUN, PR641_RUN),
        exact_parent_source_blobs=(PR656_SOURCE_BLOB, PR641_SOURCE_BLOB),
        pr656_job=PR656_JOB,
        pr656_receipt_digest=PR656_RECEIPT_DIGEST,
        pr628_source_blob=PR628_SOURCE_BLOB,
        official_repository=OFFICIAL_REPOSITORY,
        official_revision=OFFICIAL_REVISION,
        selected_layer=SELECTED_LAYER,
        selected_expert=SELECTED_EXPERT,
        selected_shard=SELECTED_SHARD,
        live_header_length_bytes=header_len,
        total_raw_payload_bytes_reobserved=total_raw,
        raw_slice_hashes=raw_hashes,
        fp8_block_shape=BLOCK_SHAPE,
        canonical_float32_domain=CANONICAL_FLOAT32_DOMAIN,
        gate_canonical_float32_sha256=gate_sha,
        up_canonical_float32_sha256=up_sha,
        down_canonical_float32_sha256=down_sha,
        gate_up_canonical_float32_sha256=gate_up_sha,
        gate_up_source_shape=(4096, 6144),
        down_source_shape=(6144, 2048),
        source_set_schema=SOURCE_SET_SCHEMA,
        source_set_entries=entries,
        source_tensor_set_digest=set_digest,
        full_representative_raw_payload_coverage_reobserved=True,
        fp8_dequantization_semantics_bound_for_all_three_projections=True,
        gate_up_source_layout_relation_bound=True,
        pr628_source_hash_byte_domain_matched=True,
        pr641_source_tensor_set_grammar_matched=True,
        full_representative_canonical_source_set_bound=True,
        representative_official_source_tensor_set_authenticated=True,
        representative_scope_only=True,
        actual_e8_page_payload_materialized=False,
        official_tensor_to_e8_page_derivation_proven=False,
        candidate_page_materialization_owner_bound=False,
        baseline_same_official_source_tensor_set_proven=False,
        whole_model_coverage_proven=False,
        model_execution_observed=False,
        generalized_quality_proven=False,
        runtime_performance_proven=False,
        semantic_k27_authority=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
        merge_or_deployment_authorized=False,
    )


def main() -> None:
    r = current_full_representative_source_set()
    print(json.dumps({**asdict(r), "receipt_digest": r.receipt_digest}, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
