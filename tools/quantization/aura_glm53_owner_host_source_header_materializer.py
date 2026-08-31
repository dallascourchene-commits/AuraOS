#!/usr/bin/env python3
"""Materialize the minimum exact official GLM-5.3 source/header evidence cone.

This is an evidence producer, not an execution authorizer.  It downloads the exact
pinned index object plus only the bounded safetensors header prefixes required for
layer-3/expert-0 source admission, then feeds those raw bytes through the existing
Q7 source->C2 admission owner.

The objective is derived from two consequence-distinct exact-green agents:
- Q5 / PR671: equal-rate E8 distortion evidence on official source canaries;
- Q7 / PR672: source-bound C2 request admission, currently HOLD only below exact
  index bytes and representative safetensors headers.

No tensor payload bytes beyond safetensors headers are read by this tool.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import struct
import urllib.request
from typing import Mapping

from tools.quantization import aura_glm53_official_source_admission as source
from tools.quantization import aura_glm53_official_source_c2_request_admission as q7

SCHEMA = "AURA_GLM53_OWNER_HOST_SOURCE_HEADER_MATERIALIZER_V1"
Q5_HEAD = "23c8345a1e3d5034ce88bea1ab32c69c1a9cf3f2"
Q5_RUN = 33400399223
Q5_JOB = 99515030515
Q5_AGGREGATE_E8_OVER_CONTROL = 0.6220981458103897
Q7_HEAD = "7340091202f3f1a859841c3ec4314191f18fa1ad"
Q7_RUN = 33400557094
Q7_JOB = 99515552580
CONVERGENCE_COMMIT = "63a411a0eaea18bfbdf60346fe19bdc7fa93d397"
EXPERT_PREFIX = "model.layers.3.mlp.experts.0"
MAX_HEADER_PREFIX_BYTES = 2 * 1024 * 1024
USER_AGENT = "AuraOS-S1-SourceHeaderMaterializer/1"


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _digest(value: object) -> str:
    return _sha(_canonical(value))


def k27_coordinate(identity: str) -> tuple[int, int, int]:
    """Project an external identity string into retrieval-only B3MOD27 coordinates."""
    raw = hashlib.sha256(identity.encode("utf-8")).digest()
    return (raw[0] % 27, raw[1] % 27, raw[2] % 27)


def hf_resolve_url(filename: str) -> str:
    return f"https://huggingface.co/{source.OFFICIAL_REPO}/resolve/{source.OFFICIAL_COMMIT}/{filename}?download=true"


def official_config_profile() -> Mapping[str, object]:
    """Re-express the already-bound PR639 config profile; this is not a config-byte claim."""
    return {
        "architectures": [source.EXPECTED_ARCHITECTURE],
        "model_type": source.EXPECTED_MODEL_TYPE,
        "hidden_size": source.EXPECTED_HIDDEN_SIZE,
        "moe_intermediate_size": source.EXPECTED_MOE_INTERMEDIATE,
        "n_routed_experts": source.EXPECTED_ROUTED_EXPERTS,
        "num_experts_per_tok": source.EXPECTED_EXPERTS_PER_TOKEN,
        "num_hidden_layers": source.EXPECTED_HIDDEN_LAYERS,
        "num_nextn_predict_layers": source.EXPECTED_NEXTN_LAYERS,
        "max_position_embeddings": source.EXPECTED_MAX_POSITION,
        "quantization_config": {
            "quant_method": source.EXPECTED_QUANT_METHOD,
            "fmt": source.EXPECTED_FP8_FMT,
            "weight_block_size": list(source.EXPECTED_WEIGHT_BLOCK),
        },
    }


def urllib_read_exact(url: str, *, max_bytes: int) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=120) as response:
        raw = response.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError("REMOTE_OBJECT_EXCEEDS_BOUND")
    return raw


def urllib_read_range(url: str, start: int, length: int) -> bytes:
    if start < 0 or length <= 0:
        raise ValueError("INVALID_RANGE")
    end = start + length - 1
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Encoding": "identity",
            "Range": f"bytes={start}-{end}",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        status = getattr(response, "status", None) or response.getcode()
        if status != 206:
            raise ValueError("RANGE_RESPONSE_NOT_PARTIAL")
        content_range = str(response.headers.get("Content-Range", ""))
        if not content_range.startswith(f"bytes {start}-{end}/"):
            raise ValueError("CONTENT_RANGE_MISMATCH")
        raw = response.read(length + 1)
    if len(raw) != length:
        raise ValueError("RANGE_LENGTH_MISMATCH")
    return raw


def materialize_header_prefix(shard: str) -> bytes:
    url = hf_resolve_url(shard)
    lead = urllib_read_range(url, 0, 8)
    header_len = struct.unpack("<Q", lead)[0]
    total = 8 + header_len
    if header_len <= 0 or total > MAX_HEADER_PREFIX_BYTES:
        raise ValueError("SAFETENSORS_HEADER_BOUND_VIOLATION")
    return urllib_read_range(url, 0, total)


@dataclass(frozen=True)
class SourceHeaderMaterializationReceipt:
    schema: str
    exact_parent_heads: tuple[str, str]
    exact_parent_runs: tuple[int, int]
    exact_parent_jobs: tuple[int, int]
    convergence_commit: str
    official_repository: str
    official_revision: str
    expert_prefix: str
    index_sha256: str
    index_size_bytes: int
    index_url_sha256: str
    index_k27_coordinate: tuple[int, int, int]
    representative_shards: tuple[str, ...]
    header_prefix_sha256_by_shard: Mapping[str, str]
    header_prefix_bytes_by_shard: Mapping[str, int]
    total_source_evidence_bytes_materialized: int
    q5_aggregate_e8_over_control: float
    q5_scope_only: bool
    source_admission_digest: str
    c2_request_digest: str
    source_header_trial_eligible: bool
    source_bound_c2_request_admissible: bool
    blocker: str
    tensor_payload_bytes_materialized: bool
    model_execution_observed: bool
    physical_io_performance_proven: bool
    native_private_transformer_kv_accessed: bool
    semantic_k27_authority_minted: bool
    gate10_promoted: bool
    execution_authorized_by_this_contract: bool

    @property
    def receipt_digest(self) -> str:
        return _digest(asdict(self))


def materialize_current_source_header_evidence() -> SourceHeaderMaterializationReceipt:
    index_url = hf_resolve_url(source.OFFICIAL_INDEX_FILENAME)
    index_bytes = urllib_read_exact(index_url, max_bytes=source.OFFICIAL_INDEX_SIZE)
    index = source.verify_official_index_bytes(index_bytes)
    key_to_shard = source.extract_expert_bundle(index, EXPERT_PREFIX)
    shards = tuple(sorted(set(key_to_shard.values())))
    if not shards:
        raise ValueError("NO_REPRESENTATIVE_SHARDS")

    prefixes = {shard: materialize_header_prefix(shard) for shard in shards}
    request = q7.deterministic_request_fixture()
    disposition = q7.admit_source_bound_c2_request(
        request=request,
        config=official_config_profile(),
        index_bytes=index_bytes,
        expert_prefix=EXPERT_PREFIX,
        shard_header_prefixes=prefixes,
        candidate_parent_sha=source.PR628_E8_PAGE_ARTIFACT_SHA,
    )
    if not disposition.source_header_trial_eligible or not disposition.source_bound_c2_request_admissible:
        raise ValueError("SOURCE_HEADER_EVIDENCE_DID_NOT_CLOSE_Q7_BLOCKER")

    header_hashes = {name: _sha(raw) for name, raw in sorted(prefixes.items())}
    header_sizes = {name: len(raw) for name, raw in sorted(prefixes.items())}
    return SourceHeaderMaterializationReceipt(
        schema=SCHEMA,
        exact_parent_heads=(Q7_HEAD, Q5_HEAD),
        exact_parent_runs=(Q7_RUN, Q5_RUN),
        exact_parent_jobs=(Q7_JOB, Q5_JOB),
        convergence_commit=CONVERGENCE_COMMIT,
        official_repository=source.OFFICIAL_REPO,
        official_revision=source.OFFICIAL_COMMIT,
        expert_prefix=EXPERT_PREFIX,
        index_sha256=_sha(index_bytes),
        index_size_bytes=len(index_bytes),
        index_url_sha256=_sha(index_url.encode("utf-8")),
        index_k27_coordinate=k27_coordinate(index_url),
        representative_shards=shards,
        header_prefix_sha256_by_shard=header_hashes,
        header_prefix_bytes_by_shard=header_sizes,
        total_source_evidence_bytes_materialized=len(index_bytes) + sum(header_sizes.values()),
        q5_aggregate_e8_over_control=Q5_AGGREGATE_E8_OVER_CONTROL,
        q5_scope_only=True,
        source_admission_digest=disposition.source_admission_digest,
        c2_request_digest=disposition.c2_request_digest,
        source_header_trial_eligible=disposition.source_header_trial_eligible,
        source_bound_c2_request_admissible=disposition.source_bound_c2_request_admissible,
        blocker=disposition.blocker,
        tensor_payload_bytes_materialized=False,
        model_execution_observed=False,
        physical_io_performance_proven=False,
        native_private_transformer_kv_accessed=False,
        semantic_k27_authority_minted=False,
        gate10_promoted=False,
        execution_authorized_by_this_contract=False,
    )


def main() -> None:
    receipt = materialize_current_source_header_evidence()
    body = asdict(receipt)
    body["receipt_digest"] = receipt.receipt_digest
    print(json.dumps(body, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
