#!/usr/bin/env python3
"""Materialize the minimum official GLM-5.3 metadata cone required by Q7.

Q15 is a bounded metadata producer. It fetches the exact pinned config and model
index plus only the safetensors JSON header prefixes needed for layer 3 / expert 0,
then delegates semantic admission to the existing PR639/Q7 owners. It never reads
a tensor payload, quantizes a tensor, executes the model, or authorizes an effect.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import struct
import urllib.request
from typing import Callable

from tools.quantization.aura_glm53_official_source_admission import (
    OFFICIAL_COMMIT,
    OFFICIAL_INDEX_FILENAME,
    OFFICIAL_INDEX_SHA256,
    OFFICIAL_INDEX_SIZE,
    OFFICIAL_REPO,
    PR628_E8_PAGE_ARTIFACT_SHA,
    extract_expert_bundle,
    verify_official_index_bytes,
)
from tools.quantization.aura_glm53_official_source_c2_request_admission import (
    admit_source_bound_c2_request,
    deterministic_request_fixture,
)

SCHEMA = "AURA_GLM53_MINIMUM_OFFICIAL_METADATA_ADMISSION_V1"
CONVERGENCE_COMMIT = "b8b17171ef5538478505530eb05e22ff4ea7365d"
Q7_PROOF_HEAD = "7340091202f3f1a859841c3ec4314191f18fa1ad"
Q7_RUN = 33400557094
Q6_PROOF_HEAD = "6906337dd6e75f49a70a84652bfd9ab70d967eef"
Q6_RUN = 33401482324
Q7_SOURCE_OWNER_BLOB = "7ed09c57699fe303f555a3b6bdaadb791c64223f"
Q7_C2_OWNER_BLOB = "31837eb716139170cbdd5290f7aae889cd7b90be"
Q6_MINIMUM_CONE_OWNER_BLOB = "400a28e12b2c8ac37b59c36ef7386bcb443b1923"
EXPERT_PREFIX = "model.layers.3.mlp.experts.0"
MAX_CONFIG_BYTES = 2_000_000
MAX_HEADER_BYTES = 4_000_000
USER_AGENT = "AuraOS-Q15-MinimumOfficialMetadata/1"


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _object_sha(value: object) -> str:
    return _sha256(_canonical(value))


def _resolve_url(filename: str) -> str:
    return f"https://huggingface.co/{OFFICIAL_REPO}/resolve/{OFFICIAL_COMMIT}/{filename}?download=true"


def _fetch_full(url: str, maximum_bytes: int) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=120) as response:
        status = getattr(response, "status", None) or response.getcode()
        if status != 200:
            raise RuntimeError(f"full metadata fetch requires HTTP 200, got {status}")
        raw = response.read(maximum_bytes + 1)
    if len(raw) > maximum_bytes:
        raise RuntimeError("metadata object exceeds bounded maximum")
    return raw


def _fetch_range(url: str, start: int, length: int) -> bytes:
    if start < 0 or length <= 0:
        raise ValueError("invalid range")
    end = start + length - 1
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Range": f"bytes={start}-{end}",
            "Accept-Encoding": "identity",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        status = getattr(response, "status", None) or response.getcode()
        content_range = response.headers.get("Content-Range", "")
        if status != 206:
            raise RuntimeError(f"bounded header fetch requires HTTP 206, got {status}")
        if not content_range.startswith(f"bytes {start}-{end}/"):
            raise RuntimeError("Content-Range does not match requested metadata span")
        raw = response.read(length + 1)
    if len(raw) != length:
        raise RuntimeError("bounded header response length mismatch")
    return raw


def _parse_config(raw: bytes) -> dict[str, object]:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("official config is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeError("official config must be a JSON object")
    return value


def _fetch_header_prefix(
    shard: str,
    *,
    range_fetch: Callable[[str, int, int], bytes],
) -> tuple[bytes, int, str]:
    url = _resolve_url(shard)
    first8 = range_fetch(url, 0, 8)
    header_len = struct.unpack("<Q", first8)[0]
    if header_len <= 0 or header_len > MAX_HEADER_BYTES:
        raise RuntimeError("safetensors header length outside Q15 metadata bound")
    header = range_fetch(url, 8, header_len)
    return first8 + header, header_len, _sha256(header)


def materialize_minimum_official_metadata(
    *,
    full_fetch: Callable[[str, int], bytes] = _fetch_full,
    range_fetch: Callable[[str, int, int], bytes] = _fetch_range,
) -> dict[str, object]:
    """Close exactly Q7's index/header blocker from pinned raw metadata."""
    config_raw = full_fetch(_resolve_url("config.json"), MAX_CONFIG_BYTES)
    config = _parse_config(config_raw)

    index_raw = full_fetch(_resolve_url(OFFICIAL_INDEX_FILENAME), OFFICIAL_INDEX_SIZE)
    index = verify_official_index_bytes(index_raw)
    key_to_shard = extract_expert_bundle(index, EXPERT_PREFIX)
    needed_shards = sorted(set(key_to_shard.values()))
    if not needed_shards:
        raise RuntimeError("representative metadata cone unexpectedly empty")

    prefixes: dict[str, bytes] = {}
    header_records: list[dict[str, object]] = []
    for shard in needed_shards:
        prefix, header_len, header_sha = _fetch_header_prefix(shard, range_fetch=range_fetch)
        prefixes[shard] = prefix
        header_records.append(
            {
                "shard": shard,
                "header_length_bytes": header_len,
                "header_sha256": header_sha,
                "prefix_bytes_materialized": len(prefix),
            }
        )

    disposition = admit_source_bound_c2_request(
        request=deterministic_request_fixture(),
        config=config,
        index_bytes=index_raw,
        expert_prefix=EXPERT_PREFIX,
        shard_header_prefixes=prefixes,
        candidate_parent_sha=PR628_E8_PAGE_ARTIFACT_SHA,
    )
    if not disposition.source_header_trial_eligible or not disposition.source_bound_c2_request_admissible:
        raise RuntimeError(f"Q15 metadata cone did not close Q7 blocker: {disposition.blocker}")

    metadata_bytes = len(config_raw) + len(index_raw) + sum(len(prefix) for prefix in prefixes.values())
    body: dict[str, object] = {
        "schema": SCHEMA,
        "convergence_commit": CONVERGENCE_COMMIT,
        "exact_parent_heads": [Q7_PROOF_HEAD, Q6_PROOF_HEAD],
        "exact_parent_runs": [Q7_RUN, Q6_RUN],
        "exact_parent_owner_blobs": {
            "q7_source_admission": Q7_SOURCE_OWNER_BLOB,
            "q7_source_c2_join": Q7_C2_OWNER_BLOB,
            "q6_minimum_evidence_cone": Q6_MINIMUM_CONE_OWNER_BLOB,
        },
        "official_repository": OFFICIAL_REPO,
        "official_revision": OFFICIAL_COMMIT,
        "expert_prefix": EXPERT_PREFIX,
        "minimum_metadata_evidence_cone_before": [
            "exact_official_index_bytes",
            "exact_representative_shard_headers",
        ],
        "minimum_metadata_evidence_cone_after": [],
        "config_bytes_materialized": len(config_raw),
        "config_sha256": _sha256(config_raw),
        "index_bytes_materialized": len(index_raw),
        "index_sha256": index.sha256,
        "index_weight_map_sha256": index.weight_map_sha256,
        "index_tensor_count": index.tensor_count,
        "index_shard_count": index.shard_count,
        "needed_representative_shards": needed_shards,
        "representative_header_records": header_records,
        "total_metadata_bytes_materialized": metadata_bytes,
        "source_admission_digest": disposition.source_admission_digest,
        "q7_disposition_digest": disposition.disposition_digest,
        "source_header_trial_eligible": disposition.source_header_trial_eligible,
        "source_bound_c2_request_admissible": disposition.source_bound_c2_request_admissible,
        "blocker": disposition.blocker,
        "source_tensor_payload_bound": disposition.source_tensor_payload_bound,
        "real_tensor_quantization_eligible": disposition.real_tensor_quantization_eligible,
        "execution_authorized_by_this_contract": disposition.execution_authorized_by_this_contract,
        "owner_host_execution_observed": disposition.owner_host_execution_observed,
        "physical_io_attested": disposition.physical_io_attested,
        "semantic_k27_authority_minted": disposition.semantic_k27_authority_minted,
        "native_private_transformer_kv_accessed": disposition.native_private_transformer_kv_accessed,
        "gate10_promoted": disposition.gate10_promoted,
        "tensor_payload_bytes_materialized": 0,
        "model_execution_observed": False,
        "full_tensor_or_model_claim_earned": False,
        "laws": [
            "OfficialModelRevisionBound!=OfficialSourceBytesAdmitted",
            "ExactIndexBytes+ExactRequiredHeaders=>HeaderLevelSourceAdmission",
            "HeaderLevelSourceAdmission!=TensorPayloadBound",
            "HeaderLevelC2RequestAdmissible!=ExecutionAuthorized",
            "MinimumMissingEvidenceConeBeforeFanout",
            "RepresentativeEvidenceScopeCannotWidenSourceAuthority",
            "K27Coordinate!=SourceAuthority!=EffectAuthority",
        ],
    }
    ceiling = (
        body["source_tensor_payload_bound"],
        body["real_tensor_quantization_eligible"],
        body["execution_authorized_by_this_contract"],
        body["owner_host_execution_observed"],
        body["physical_io_attested"],
        body["semantic_k27_authority_minted"],
        body["native_private_transformer_kv_accessed"],
        body["gate10_promoted"],
        body["model_execution_observed"],
        body["full_tensor_or_model_claim_earned"],
    )
    if any(ceiling) or body["tensor_payload_bytes_materialized"] != 0:
        raise RuntimeError("Q15 nonpromotion ceiling violated")
    body["receipt_digest"] = _object_sha(body)
    return body


def main() -> None:
    print(json.dumps(materialize_minimum_official_metadata(), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
