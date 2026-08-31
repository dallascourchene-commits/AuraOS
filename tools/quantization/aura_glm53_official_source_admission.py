#!/usr/bin/env python3
"""Fail-closed official-source admission for GLM-5.3 quantization trials.

This module closes an evidence-grammar gap.  It can validate the official
configuration profile, verify the *actual bytes* of the official safetensors
index when those bytes become available, parse bounded safetensors headers,
and prove that a routed-expert weight plus its FP8 scale companion share a
source-bound header bundle.

It deliberately does NOT infer missing index/header evidence from filenames,
K27 coordinates, neighboring GLM checkpoints, or a candidate quantizer.
Current public evidence therefore returns HOLD.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

OFFICIAL_REPO = "zai-org/GLM-5.3"
OFFICIAL_COMMIT = "7cda81930d6e4cef42f48555de830aa32ecdde28"
OFFICIAL_INDEX_FILENAME = "model.safetensors.index.json"
OFFICIAL_INDEX_SHA256 = "e0fe7f28c1f853d4824e4d796374e3dacf1fe470988773952c79b063768134bf"
OFFICIAL_INDEX_SIZE = 11_359_251
OFFICIAL_INDEX_XET_HASH = "cc559a187bc99b20039b572a3161f394c51ad19eb2c8eed41371f54740af5f94"

# Exact-green independent candidate artifact.  The mutable PR tip is not an
# authority source; this historical semantic artifact is intentionally pinned.
PR628_E8_PAGE_ARTIFACT_SHA = "b8fd399ee0ca6b45a4ec7db58750e6d4105ae3ae"
PR628_E8_PAGE_WORKFLOW_RUN = 33367948262
PR628_E8_PAGE_SCHEME = "AURA_E8_BALL10_16BIT_REF_V1"

EXPECTED_MODEL_TYPE = "glm_moe_dsa"
EXPECTED_ARCHITECTURE = "GlmMoeDsaForCausalLM"
EXPECTED_HIDDEN_SIZE = 6144
EXPECTED_MOE_INTERMEDIATE = 2048
EXPECTED_ROUTED_EXPERTS = 256
EXPECTED_EXPERTS_PER_TOKEN = 8
EXPECTED_HIDDEN_LAYERS = 78
EXPECTED_NEXTN_LAYERS = 1
EXPECTED_MAX_POSITION = 1_048_576
EXPECTED_QUANT_METHOD = "fp8"
EXPECTED_FP8_FMT = "e4m3"
EXPECTED_WEIGHT_BLOCK = (128, 128)

WEIGHT_ROLES = ("gate_proj.weight", "up_proj.weight", "down_proj.weight")
SCALE_ROLES = (
    "gate_proj.weight_scale_inv",
    "up_proj.weight_scale_inv",
    "down_proj.weight_scale_inv",
)
REQUIRED_ROLES = tuple(role for pair in zip(WEIGHT_ROLES, SCALE_ROLES) for role in pair)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_sha256(value: object) -> str:
    return _sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


@dataclass(frozen=True)
class OfficialConfigObservation:
    repository: str
    revision: str
    model_type: str
    architecture: str
    hidden_size: int
    moe_intermediate_size: int
    n_routed_experts: int
    num_experts_per_tok: int
    num_hidden_layers: int
    num_nextn_predict_layers: int
    max_position_embeddings: int
    quant_method: str
    fp8_fmt: str
    weight_block_size: tuple[int, int]
    config_profile_sha256: str


@dataclass(frozen=True)
class IndexObjectIdentity:
    filename: str
    sha256: str
    size_bytes: int
    xet_hash: str
    bytes_materialized: bool
    weight_map_observed: bool


@dataclass(frozen=True)
class IndexBytesObservation:
    sha256: str
    size_bytes: int
    tensor_count: int
    shard_count: int
    weight_map_sha256: str
    weight_map: Mapping[str, str]


@dataclass(frozen=True)
class HeaderEntry:
    key: str
    shard: str
    dtype: str
    shape: tuple[int, ...]
    data_offsets: tuple[int, int]
    header_sha256: str


@dataclass(frozen=True)
class ExpertHeaderBundle:
    expert_prefix: str
    entries: tuple[HeaderEntry, ...]
    bundle_sha256: str


@dataclass(frozen=True)
class AdmissionState:
    schema: str
    official_repository: str
    official_revision: str
    candidate_parent_sha: str
    candidate_scheme: str
    config_profile_bound: bool
    index_object_identity_bound: bool
    index_bytes_verified: bool
    representative_key_to_shard_bound: bool
    representative_headers_observed: bool
    fp8_companions_bound: bool
    candidate_representation_bound: bool
    header_trial_eligible: bool
    source_tensor_payload_bound: bool
    real_tensor_quantization_eligible: bool
    blocker: str
    semantic_k27_authority: bool
    native_transformer_kv_accessed: bool
    gate10_promoted: bool

    def digest(self) -> str:
        return _canonical_sha256(asdict(self))


def observe_official_config(config: Mapping[str, object]) -> OfficialConfigObservation:
    """Validate exact current public config facts; reject analogy/substitution."""
    architectures = config.get("architectures")
    quant = config.get("quantization_config")
    if not isinstance(architectures, list) or architectures != [EXPECTED_ARCHITECTURE]:
        raise ValueError("official architecture mismatch")
    if not isinstance(quant, Mapping):
        raise ValueError("missing quantization_config")
    block = quant.get("weight_block_size")
    if tuple(block) if isinstance(block, list) else () != EXPECTED_WEIGHT_BLOCK:
        # Parenthesized explicitly below; this branch is retained only for
        # readability after the conditional-expression parse.
        pass
    block_tuple = tuple(block) if isinstance(block, list) else ()
    expected = {
        "model_type": (config.get("model_type"), EXPECTED_MODEL_TYPE),
        "hidden_size": (config.get("hidden_size"), EXPECTED_HIDDEN_SIZE),
        "moe_intermediate_size": (config.get("moe_intermediate_size"), EXPECTED_MOE_INTERMEDIATE),
        "n_routed_experts": (config.get("n_routed_experts"), EXPECTED_ROUTED_EXPERTS),
        "num_experts_per_tok": (config.get("num_experts_per_tok"), EXPECTED_EXPERTS_PER_TOKEN),
        "num_hidden_layers": (config.get("num_hidden_layers"), EXPECTED_HIDDEN_LAYERS),
        "num_nextn_predict_layers": (config.get("num_nextn_predict_layers"), EXPECTED_NEXTN_LAYERS),
        "max_position_embeddings": (config.get("max_position_embeddings"), EXPECTED_MAX_POSITION),
        "quant_method": (quant.get("quant_method"), EXPECTED_QUANT_METHOD),
        "fmt": (quant.get("fmt"), EXPECTED_FP8_FMT),
        "weight_block_size": (block_tuple, EXPECTED_WEIGHT_BLOCK),
    }
    mismatches = [name for name, (observed, wanted) in expected.items() if observed != wanted]
    if mismatches:
        raise ValueError("official config mismatch: " + ",".join(mismatches))
    profile = {
        "repository": OFFICIAL_REPO,
        "revision": OFFICIAL_COMMIT,
        **{name: observed for name, (observed, _wanted) in expected.items()},
        "architecture": architectures[0],
    }
    return OfficialConfigObservation(
        repository=OFFICIAL_REPO,
        revision=OFFICIAL_COMMIT,
        model_type=EXPECTED_MODEL_TYPE,
        architecture=EXPECTED_ARCHITECTURE,
        hidden_size=EXPECTED_HIDDEN_SIZE,
        moe_intermediate_size=EXPECTED_MOE_INTERMEDIATE,
        n_routed_experts=EXPECTED_ROUTED_EXPERTS,
        num_experts_per_tok=EXPECTED_EXPERTS_PER_TOKEN,
        num_hidden_layers=EXPECTED_HIDDEN_LAYERS,
        num_nextn_predict_layers=EXPECTED_NEXTN_LAYERS,
        max_position_embeddings=EXPECTED_MAX_POSITION,
        quant_method=EXPECTED_QUANT_METHOD,
        fp8_fmt=EXPECTED_FP8_FMT,
        weight_block_size=EXPECTED_WEIGHT_BLOCK,
        config_profile_sha256=_canonical_sha256(profile),
    )


def official_index_object_identity() -> IndexObjectIdentity:
    """Return object identity only.  This never claims the remote bytes exist locally."""
    return IndexObjectIdentity(
        filename=OFFICIAL_INDEX_FILENAME,
        sha256=OFFICIAL_INDEX_SHA256,
        size_bytes=OFFICIAL_INDEX_SIZE,
        xet_hash=OFFICIAL_INDEX_XET_HASH,
        bytes_materialized=False,
        weight_map_observed=False,
    )


def verify_index_bytes(index_bytes: bytes, *, expected_sha256: str, expected_size: int) -> IndexBytesObservation:
    """Verify exact bytes and derive the weight-map observation from those bytes."""
    if len(index_bytes) != expected_size:
        raise ValueError("index byte length mismatch")
    digest = _sha256(index_bytes)
    if digest != expected_sha256:
        raise ValueError("index SHA-256 mismatch")
    try:
        parsed = json.loads(index_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("index is not valid UTF-8 JSON") from exc
    weight_map = parsed.get("weight_map") if isinstance(parsed, dict) else None
    if not isinstance(weight_map, dict) or not weight_map:
        raise ValueError("missing weight_map")
    if not all(isinstance(k, str) and isinstance(v, str) and v.endswith(".safetensors") for k, v in weight_map.items()):
        raise ValueError("invalid weight_map entry")
    return IndexBytesObservation(
        sha256=digest,
        size_bytes=len(index_bytes),
        tensor_count=len(weight_map),
        shard_count=len(set(weight_map.values())),
        weight_map_sha256=_canonical_sha256(weight_map),
        weight_map=dict(weight_map),
    )


def verify_official_index_bytes(index_bytes: bytes) -> IndexBytesObservation:
    return verify_index_bytes(
        index_bytes,
        expected_sha256=OFFICIAL_INDEX_SHA256,
        expected_size=OFFICIAL_INDEX_SIZE,
    )


def extract_expert_bundle(index: IndexBytesObservation, expert_prefix: str) -> Mapping[str, str]:
    """Resolve exactly six weight/scale roles from an observed index body."""
    if not expert_prefix or expert_prefix.endswith("."):
        raise ValueError("expert_prefix must be non-empty and omit trailing dot")
    result: dict[str, str] = {}
    for role in REQUIRED_ROLES:
        key = f"{expert_prefix}.{role}"
        shard = index.weight_map.get(key)
        if shard is None:
            raise ValueError(f"required expert role missing: {role}")
        result[key] = shard
    if len(result) != 6:
        raise AssertionError("expert bundle role-count drift")
    return result


def parse_safetensors_header(prefix_bytes: bytes, shard: str) -> Mapping[str, HeaderEntry]:
    """Parse only a safetensors header prefix: uint64 header length + JSON bytes."""
    if len(prefix_bytes) < 8:
        raise ValueError("header prefix shorter than uint64 length")
    header_len = struct.unpack("<Q", prefix_bytes[:8])[0]
    if header_len <= 0 or len(prefix_bytes) < 8 + header_len:
        raise ValueError("incomplete safetensors header prefix")
    header_bytes = prefix_bytes[8 : 8 + header_len]
    try:
        header = json.loads(header_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid safetensors header JSON") from exc
    if not isinstance(header, dict):
        raise ValueError("safetensors header must be an object")
    header_sha = _sha256(header_bytes)
    result: dict[str, HeaderEntry] = {}
    for key, meta in header.items():
        if key == "__metadata__":
            continue
        if not isinstance(key, str) or not isinstance(meta, dict):
            raise ValueError("invalid safetensors header entry")
        dtype, shape, offsets = meta.get("dtype"), meta.get("shape"), meta.get("data_offsets")
        if not isinstance(dtype, str) or not isinstance(shape, list) or not isinstance(offsets, list) or len(offsets) != 2:
            raise ValueError("incomplete safetensors tensor metadata")
        shape_tuple = tuple(int(x) for x in shape)
        offsets_tuple = tuple(int(x) for x in offsets)
        if any(x <= 0 for x in shape_tuple) or offsets_tuple[0] < 0 or offsets_tuple[1] <= offsets_tuple[0]:
            raise ValueError("invalid safetensors shape/offsets")
        result[key] = HeaderEntry(
            key=key,
            shard=shard,
            dtype=dtype,
            shape=shape_tuple,
            data_offsets=(offsets_tuple[0], offsets_tuple[1]),
            header_sha256=header_sha,
        )
    return result


def bind_expert_headers(
    expert_prefix: str,
    key_to_shard: Mapping[str, str],
    parsed_headers: Mapping[str, Mapping[str, HeaderEntry]],
) -> ExpertHeaderBundle:
    """Bind weight headers to their F32 128x128 scale companions."""
    entries: list[HeaderEntry] = []
    for weight_role, scale_role in zip(WEIGHT_ROLES, SCALE_ROLES):
        weight_key = f"{expert_prefix}.{weight_role}"
        scale_key = f"{expert_prefix}.{scale_role}"
        if key_to_shard.get(weight_key) is None or key_to_shard.get(scale_key) is None:
            raise ValueError("weight/scale mapping incomplete")
        weight_shard = key_to_shard[weight_key]
        scale_shard = key_to_shard[scale_key]
        weight = parsed_headers.get(weight_shard, {}).get(weight_key)
        scale = parsed_headers.get(scale_shard, {}).get(scale_key)
        if weight is None or scale is None:
            raise ValueError("required observed header missing")
        if weight.dtype != "F8_E4M3":
            raise ValueError("routed expert weight is not observed F8_E4M3")
        if scale.dtype != "F32":
            raise ValueError("routed expert scale companion is not observed F32")
        if len(weight.shape) != 2 or len(scale.shape) != 2:
            raise ValueError("routed expert weight/scale must be rank-2")
        expected_scale = tuple(math.ceil(dim / block) for dim, block in zip(weight.shape, EXPECTED_WEIGHT_BLOCK))
        if scale.shape != expected_scale:
            raise ValueError("FP8 companion scale shape does not match 128x128 block geometry")
        entries.extend((weight, scale))
    payload = [asdict(entry) for entry in entries]
    return ExpertHeaderBundle(
        expert_prefix=expert_prefix,
        entries=tuple(entries),
        bundle_sha256=_canonical_sha256(payload),
    )


def current_public_state(config_profile_bound: bool = True) -> AdmissionState:
    """Encode the current earned evidence state without caller-promotable proof flags."""
    return AdmissionState(
        schema="AURA_GLM53_OFFICIAL_QUANTIZATION_SOURCE_ADMISSION_V1",
        official_repository=OFFICIAL_REPO,
        official_revision=OFFICIAL_COMMIT,
        candidate_parent_sha=PR628_E8_PAGE_ARTIFACT_SHA,
        candidate_scheme=PR628_E8_PAGE_SCHEME,
        config_profile_bound=bool(config_profile_bound),
        index_object_identity_bound=True,
        index_bytes_verified=False,
        representative_key_to_shard_bound=False,
        representative_headers_observed=False,
        fp8_companions_bound=False,
        candidate_representation_bound=True,
        header_trial_eligible=False,
        source_tensor_payload_bound=False,
        real_tensor_quantization_eligible=False,
        blocker="OFFICIAL_INDEX_BYTES_AND_REPRESENTATIVE_HEADERS_NOT_MATERIALIZED",
        semantic_k27_authority=False,
        native_transformer_kv_accessed=False,
        gate10_promoted=False,
    )


def admitted_header_state(
    config: OfficialConfigObservation,
    index: IndexBytesObservation,
    bundle: ExpertHeaderBundle,
    *,
    candidate_parent_sha: str,
) -> AdmissionState:
    """Admit a header-level trial only from recomputed exact evidence objects."""
    if config.repository != OFFICIAL_REPO or config.revision != OFFICIAL_COMMIT:
        raise ValueError("official config generation mismatch")
    if index.sha256 != OFFICIAL_INDEX_SHA256 or index.size_bytes != OFFICIAL_INDEX_SIZE:
        raise ValueError("official index identity mismatch")
    if candidate_parent_sha != PR628_E8_PAGE_ARTIFACT_SHA:
        raise ValueError("candidate representation parent mismatch")
    if len(bundle.entries) != 6:
        raise ValueError("representative expert header bundle incomplete")
    return AdmissionState(
        schema="AURA_GLM53_OFFICIAL_QUANTIZATION_SOURCE_ADMISSION_V1",
        official_repository=OFFICIAL_REPO,
        official_revision=OFFICIAL_COMMIT,
        candidate_parent_sha=candidate_parent_sha,
        candidate_scheme=PR628_E8_PAGE_SCHEME,
        config_profile_bound=True,
        index_object_identity_bound=True,
        index_bytes_verified=True,
        representative_key_to_shard_bound=True,
        representative_headers_observed=True,
        fp8_companions_bound=True,
        candidate_representation_bound=True,
        header_trial_eligible=True,
        source_tensor_payload_bound=False,
        real_tensor_quantization_eligible=False,
        blocker="SOURCE_TENSOR_PAYLOAD_NOT_BOUND",
        semantic_k27_authority=False,
        native_transformer_kv_accessed=False,
        gate10_promoted=False,
    )


def main() -> None:
    state = current_public_state()
    body = asdict(state)
    body["receipt_sha256"] = state.digest()
    body["law"] = "IndexObjectIdentity != IndexBytesVerified != KeyToShardBound != HeaderObserved != TensorPayloadBound"
    print(json.dumps(body, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
