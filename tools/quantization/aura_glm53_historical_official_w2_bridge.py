#!/usr/bin/env python3
"""Bind the exact historical PR398 official GLM-5.3 W2 canary into Q5/Q6 source evidence.

This module does **not** pretend that the PR398 raw index/header bytes are present in
this consumer process.  It verifies the exact independently hosted producer
observation, re-expresses its six representative tensor-header consequences using
the current PR639 header grammar, and keeps the current raw-byte admission path on
HOLD until those bytes are materialized again.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import json
from typing import Any, Mapping

from tools.quantization import aura_glm53_official_source_admission as q5

VERSION = "AURA_GLM53_HISTORICAL_OFFICIAL_W2_BRIDGE_V1"
PR639_HEAD = "730426b82235b0ff4e75fef1cff00707877a84ad"
PR639_RUN = 33369967425
PR398_HEAD = "131dd2a5fc8b4e2cf96c0bf598845d35e6706ef8"
PR398_RUN = 33336508527
PR398_JOB = 99324255699
PR398_DRIVE_OBSERVATION = "1FIz2aGHogE32scM4pmxDkHT7MiGfr2UbUkWlIDfpI_w"
PR398_RECEIPT_DIGEST = "736f0a117eb02c486736e7224c4e0f5363ae60b9"
PR398_HEADER_SHA256 = "8607b1b281f5ca8c7b166376e8f6d7eb9ca07f79200f6095f0f55ca35149ba56"
PR398_LAYER = 3
PR398_EXPERT = 0
PR398_SHARD = "model-00038-of-00141.safetensors"
EXPERT_PREFIX = "model.layers.3.mlp.experts.0"


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


_EXPECTED_ENTRIES = (
    {
        "key": f"{EXPERT_PREFIX}.gate_proj.weight",
        "shard": PR398_SHARD,
        "dtype": "F8_E4M3",
        "shape": [2048, 6144],
        "data_offsets": [4070207936, 4082790848],
        "header_sha256": PR398_HEADER_SHA256,
    },
    {
        "key": f"{EXPERT_PREFIX}.gate_proj.weight_scale_inv",
        "shard": PR398_SHARD,
        "dtype": "F32",
        "shape": [16, 48],
        "data_offsets": [993728, 996800],
        "header_sha256": PR398_HEADER_SHA256,
    },
    {
        "key": f"{EXPERT_PREFIX}.up_proj.weight",
        "shard": PR398_SHARD,
        "dtype": "F8_E4M3",
        "shape": [2048, 6144],
        "data_offsets": [4082790848, 4095373760],
        "header_sha256": PR398_HEADER_SHA256,
    },
    {
        "key": f"{EXPERT_PREFIX}.up_proj.weight_scale_inv",
        "shard": PR398_SHARD,
        "dtype": "F32",
        "shape": [16, 48],
        "data_offsets": [996800, 999872],
        "header_sha256": PR398_HEADER_SHA256,
    },
    {
        "key": f"{EXPERT_PREFIX}.down_proj.weight",
        "shard": PR398_SHARD,
        "dtype": "F8_E4M3",
        "shape": [6144, 2048],
        "data_offsets": [4057625024, 4070207936],
        "header_sha256": PR398_HEADER_SHA256,
    },
    {
        "key": f"{EXPERT_PREFIX}.down_proj.weight_scale_inv",
        "shard": PR398_SHARD,
        "dtype": "F32",
        "shape": [48, 16],
        "data_offsets": [990656, 993728],
        "header_sha256": PR398_HEADER_SHA256,
    },
)


def canonical_pr398_observation() -> dict[str, Any]:
    """Exact consequence object transcribed from hosted run 33336508527 / Drive receipt."""
    return {
        "repo_id": q5.OFFICIAL_REPO,
        "model_revision": q5.OFFICIAL_COMMIT,
        "index_sha256": q5.OFFICIAL_INDEX_SHA256,
        "index_size_bytes": q5.OFFICIAL_INDEX_SIZE,
        "selected_layer": PR398_LAYER,
        "selected_expert": PR398_EXPERT,
        "receipt_digest": PR398_RECEIPT_DIGEST,
        "producer_semantic_head": PR398_HEAD,
        "producer_run": PR398_RUN,
        "producer_job": PR398_JOB,
        "drive_observation_id": PR398_DRIVE_OBSERVATION,
        "payload_bytes_read": 0,
        "g2_admitted": False,
        "runtime_executed": False,
        "authority": False,
        "status": "OFFICIAL_HEADER_OBSERVED",
        "entries": [dict(entry) for entry in _EXPECTED_ENTRIES],
    }


@dataclass(frozen=True)
class HistoricalOfficialW2BridgeReceipt:
    version: str
    parent_heads: tuple[str, str]
    parent_runs: tuple[int, int]
    producer_job: int
    producer_drive_observation: str
    official_repository: str
    official_revision: str
    official_index_sha256: str
    official_index_size_bytes: int
    representative_layer: int
    representative_expert: int
    representative_shard: str
    producer_receipt_digest: str
    producer_header_sha256: str
    historical_raw_index_verification_observed: bool
    historical_weight_map_relation_observed: bool
    historical_representative_headers_observed: bool
    historical_fp8_companions_bound: bool
    historical_payload_bytes_read: int
    current_pr639_schema_header_geometry_conforms: bool
    representative_per_expert_serialization_proven: bool
    all_layers_experts_uniformity_proven: bool
    current_consumer_raw_index_bytes_materialized: bool
    current_consumer_raw_header_prefixes_materialized: bool
    current_pr639_raw_byte_header_trial_eligible: bool
    source_tensor_payload_bound: bool
    real_tensor_quantization_eligible: bool
    semantic_k27_authority: bool
    native_transformer_kv_accessed: bool
    gate10_promoted: bool
    blocker: str

    @property
    def digest(self) -> str:
        return _sha(asdict(self))


def _require_exact_observation(observation: Mapping[str, Any]) -> None:
    expected = canonical_pr398_observation()
    if set(observation) != set(expected):
        raise ValueError("PR398_OBSERVATION_FIELD_SET_MISMATCH")
    for key in expected:
        if observation[key] != expected[key]:
            raise ValueError(f"PR398_OBSERVATION_MISMATCH:{key}")


def _rebind_entries_to_pr639(observation: Mapping[str, Any]) -> q5.ExpertHeaderBundle:
    raw_entries = observation["entries"]
    if not isinstance(raw_entries, list) or len(raw_entries) != 6:
        raise ValueError("PR398_EXACT_SIX_ENTRIES_REQUIRED")
    entries: dict[str, q5.HeaderEntry] = {}
    for raw in raw_entries:
        if not isinstance(raw, Mapping):
            raise ValueError("PR398_HEADER_ENTRY_INVALID")
        if set(raw) != {"key", "shard", "dtype", "shape", "data_offsets", "header_sha256"}:
            raise ValueError("PR398_HEADER_ENTRY_FIELD_SET_MISMATCH")
        entry = q5.HeaderEntry(
            key=str(raw["key"]),
            shard=str(raw["shard"]),
            dtype=str(raw["dtype"]),
            shape=tuple(int(x) for x in raw["shape"]),
            data_offsets=tuple(int(x) for x in raw["data_offsets"]),
            header_sha256=str(raw["header_sha256"]),
        )
        entries[entry.key] = entry
    if len(entries) != 6:
        raise ValueError("PR398_DUPLICATE_HEADER_KEY")
    key_to_shard = {key: entry.shard for key, entry in entries.items()}
    parsed_headers = {PR398_SHARD: entries}
    return q5.bind_expert_headers(EXPERT_PREFIX, key_to_shard, parsed_headers)


def build_historical_official_w2_bridge(
    observation: Mapping[str, Any],
) -> HistoricalOfficialW2BridgeReceipt:
    """Join historical producer evidence to PR639 semantics without minting current raw bytes."""
    _require_exact_observation(observation)
    bundle = _rebind_entries_to_pr639(observation)
    if len(bundle.entries) != 6:
        raise ValueError("PR639_REBOUND_BUNDLE_INCOMPLETE")
    if any(entry.shard != PR398_SHARD for entry in bundle.entries):
        raise ValueError("PR398_REPRESENTATIVE_SHARD_MISMATCH")
    if any(entry.header_sha256 != PR398_HEADER_SHA256 for entry in bundle.entries):
        raise ValueError("PR398_HEADER_DIGEST_MISMATCH")

    # The current PR639 public execution surface is still raw-byte HOLD.  Historical
    # producer evidence constrains the source geometry; it does not materialize bytes
    # into this consumer process.
    current = q5.current_public_state()
    if current.index_bytes_verified or current.representative_headers_observed or current.header_trial_eligible:
        raise ValueError("PR639_CURRENT_PUBLIC_STATE_UNEXPECTEDLY_PROMOTED")

    return HistoricalOfficialW2BridgeReceipt(
        version=VERSION,
        parent_heads=(PR639_HEAD, PR398_HEAD),
        parent_runs=(PR639_RUN, PR398_RUN),
        producer_job=PR398_JOB,
        producer_drive_observation=PR398_DRIVE_OBSERVATION,
        official_repository=q5.OFFICIAL_REPO,
        official_revision=q5.OFFICIAL_COMMIT,
        official_index_sha256=q5.OFFICIAL_INDEX_SHA256,
        official_index_size_bytes=q5.OFFICIAL_INDEX_SIZE,
        representative_layer=PR398_LAYER,
        representative_expert=PR398_EXPERT,
        representative_shard=PR398_SHARD,
        producer_receipt_digest=PR398_RECEIPT_DIGEST,
        producer_header_sha256=PR398_HEADER_SHA256,
        historical_raw_index_verification_observed=True,
        historical_weight_map_relation_observed=True,
        historical_representative_headers_observed=True,
        historical_fp8_companions_bound=True,
        historical_payload_bytes_read=0,
        current_pr639_schema_header_geometry_conforms=True,
        representative_per_expert_serialization_proven=True,
        all_layers_experts_uniformity_proven=False,
        current_consumer_raw_index_bytes_materialized=False,
        current_consumer_raw_header_prefixes_materialized=False,
        current_pr639_raw_byte_header_trial_eligible=False,
        source_tensor_payload_bound=False,
        real_tensor_quantization_eligible=False,
        semantic_k27_authority=False,
        native_transformer_kv_accessed=False,
        gate10_promoted=False,
        blocker="CURRENT_CONSUMER_RAW_BYTES_NOT_REMATERIALIZED_AND_SOURCE_TENSOR_PAYLOAD_NOT_BOUND",
    )


def main() -> None:
    receipt = build_historical_official_w2_bridge(canonical_pr398_observation())
    body = asdict(receipt)
    body["receipt_sha256"] = receipt.digest
    body["law"] = (
        "HistoricalRawByteVerification != CurrentConsumerRawBytesMaterialized; "
        "RepresentativeOfficialHeaderEvidence != GlobalLayoutUniformity"
    )
    print(json.dumps(body, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
