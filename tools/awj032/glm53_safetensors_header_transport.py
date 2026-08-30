"""Bounded source transport for AWJ032 GLM-5.3 safetensors index/header evidence.

This module may download the small index JSON and safetensors JSON headers only.
It never reads tensor payload bytes, imports a model, or admits G2.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
import struct
from typing import Any, Callable, Mapping
from urllib.parse import quote
from urllib.request import Request, urlopen

SCHEMA = "GLM53SafetensorsHeaderEvidenceV1"
DEFAULT_MAX_INDEX_BYTES = 16 * 1024 * 1024
DEFAULT_MAX_HEADER_BYTES = 64 * 1024 * 1024
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_SHARD_RE = re.compile(r"^model-\d{5}-of-\d{5}\.safetensors$")


class HeaderTransportError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _commit(value: str) -> str:
    if not isinstance(value, str) or not _COMMIT_RE.fullmatch(value.strip().lower()):
        raise HeaderTransportError("IMMUTABLE_MODEL_REVISION_REQUIRED")
    return value.strip().lower()


def _digest(value: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value.strip().lower()):
        raise HeaderTransportError("SHA256_INVALID")
    return value.strip().lower()


def _repo(value: str) -> str:
    if not isinstance(value, str) or not _REPO_RE.fullmatch(value.strip()):
        raise HeaderTransportError("REPO_ID_INVALID")
    return value.strip()


def _path(value: str, *, shard_only: bool = False) -> str:
    if not isinstance(value, str) or not value or value.startswith("/") or ".." in value.split("/"):
        raise HeaderTransportError("REMOTE_PATH_INVALID")
    if shard_only and not _SHARD_RE.fullmatch(value):
        raise HeaderTransportError("SHARD_NAME_INVALID", value)
    return value


def hf_resolve_url(repo_id: str, revision: str, path: str) -> str:
    repo = _repo(repo_id)
    rev = _commit(revision)
    safe_path = _path(path)
    return f"https://huggingface.co/{repo}/resolve/{rev}/{quote(safe_path, safe='/')}?download=true"


@dataclass(frozen=True)
class TensorHeaderEvidence:
    tensor_key: str
    shard_name: str
    dtype: str
    shape: tuple[int, ...]
    data_offsets: tuple[int, int]
    header_sha256: str


@dataclass(frozen=True)
class GLM53SafetensorsHeaderEvidence:
    repo_id: str
    model_revision: str
    index_sha256: str
    index_size_bytes: int
    selected_layer: int
    selected_expert: int
    entries: tuple[TensorHeaderEvidence, ...]
    payload_bytes_read: int = 0
    g2_admitted: bool = False
    runtime_executed: bool = False
    authority: bool = False
    schema: str = SCHEMA

    def __post_init__(self) -> None:
        _repo(self.repo_id)
        _commit(self.model_revision)
        _digest(self.index_sha256)
        if self.schema != SCHEMA:
            raise HeaderTransportError("SCHEMA_MISMATCH")
        if not isinstance(self.index_size_bytes, int) or self.index_size_bytes <= 0:
            raise HeaderTransportError("INDEX_SIZE_INVALID")
        if not isinstance(self.selected_layer, int) or self.selected_layer < 0:
            raise HeaderTransportError("LAYER_INVALID")
        if not isinstance(self.selected_expert, int) or self.selected_expert < 0:
            raise HeaderTransportError("EXPERT_INVALID")
        if not self.entries:
            raise HeaderTransportError("HEADER_ENTRIES_REQUIRED")
        if self.payload_bytes_read != 0:
            raise HeaderTransportError("PAYLOAD_READ_FORBIDDEN")
        if self.g2_admitted or self.runtime_executed or self.authority:
            raise HeaderTransportError("AUTHORITY_WIDENING_FORBIDDEN")

    @property
    def receipt_digest(self) -> str:
        body = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.blake2b(body.encode(), digest_size=20).hexdigest()


def _read_http_response(resp: Any, *, expected_max: int) -> bytes:
    raw = resp.read(expected_max + 1)
    if len(raw) > expected_max:
        raise HeaderTransportError("BYTE_CEILING_EXCEEDED")
    return raw


def urllib_read_full(url: str, max_bytes: int) -> bytes:
    if max_bytes <= 0:
        raise HeaderTransportError("BYTE_CEILING_INVALID")
    req = Request(url, headers={"User-Agent": "AuraOS-AWJ032/1"})
    with urlopen(req, timeout=60) as resp:
        return _read_http_response(resp, expected_max=max_bytes)


def urllib_read_range(url: str, start: int, length: int) -> bytes:
    if not isinstance(start, int) or start < 0 or not isinstance(length, int) or length <= 0:
        raise HeaderTransportError("RANGE_INVALID")
    end = start + length - 1
    req = Request(
        url,
        headers={
            "User-Agent": "AuraOS-AWJ032/1",
            "Range": f"bytes={start}-{end}",
            "Accept-Encoding": "identity",
        },
    )
    with urlopen(req, timeout=60) as resp:
        status = getattr(resp, "status", None) or resp.getcode()
        if status != 206:
            raise HeaderTransportError("RANGE_NOT_HONORED", str(status))
        content_range = str(resp.headers.get("Content-Range", ""))
        if not content_range.startswith(f"bytes {start}-{end}/"):
            raise HeaderTransportError("CONTENT_RANGE_MISMATCH", content_range)
        raw = _read_http_response(resp, expected_max=length)
        if len(raw) != length:
            raise HeaderTransportError("RANGE_LENGTH_MISMATCH")
        return raw


def fetch_index(
    *,
    repo_id: str,
    model_revision: str,
    expected_index_sha256: str,
    read_full: Callable[[str, int], bytes] = urllib_read_full,
    max_index_bytes: int = DEFAULT_MAX_INDEX_BYTES,
) -> tuple[bytes, dict[str, str]]:
    expected = _digest(expected_index_sha256)
    url = hf_resolve_url(repo_id, model_revision, "model.safetensors.index.json")
    raw = read_full(url, max_index_bytes)
    if _sha256(raw) != expected:
        raise HeaderTransportError("INDEX_SHA256_MISMATCH")
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HeaderTransportError("INDEX_JSON_INVALID") from exc
    if not isinstance(parsed, dict) or not isinstance(parsed.get("weight_map"), dict):
        raise HeaderTransportError("INDEX_WEIGHT_MAP_REQUIRED")
    weight_map = parsed["weight_map"]
    normalized: dict[str, str] = {}
    for key, shard in weight_map.items():
        if not isinstance(key, str) or not key or not isinstance(shard, str):
            raise HeaderTransportError("INDEX_WEIGHT_MAP_ENTRY_INVALID")
        _path(shard, shard_only=True)
        normalized[key] = shard
    if not normalized:
        raise HeaderTransportError("INDEX_WEIGHT_MAP_REQUIRED")
    return raw, normalized


def representative_expert_keys(weight_map: Mapping[str, str], *, layer: int, expert: int) -> tuple[str, ...]:
    if not isinstance(layer, int) or layer < 0 or not isinstance(expert, int) or expert < 0:
        raise HeaderTransportError("REPRESENTATIVE_COORDINATE_INVALID")
    prefix = f"model.layers.{layer}.mlp.experts.{expert}."
    suffixes = (
        "gate_proj.weight",
        "gate_proj.weight_scale_inv",
        "up_proj.weight",
        "up_proj.weight_scale_inv",
        "down_proj.weight",
        "down_proj.weight_scale_inv",
    )
    keys = tuple(prefix + suffix for suffix in suffixes)
    missing = [key for key in keys if key not in weight_map]
    if missing:
        raise HeaderTransportError("REPRESENTATIVE_KEYS_MISSING", ",".join(missing))
    return keys


def fetch_safetensors_header(
    *,
    shard_url: str,
    read_range: Callable[[str, int, int], bytes] = urllib_read_range,
    max_header_bytes: int = DEFAULT_MAX_HEADER_BYTES,
) -> tuple[bytes, dict[str, Any]]:
    prefix = read_range(shard_url, 0, 8)
    if len(prefix) != 8:
        raise HeaderTransportError("HEADER_LENGTH_PREFIX_INVALID")
    header_len = struct.unpack("<Q", prefix)[0]
    if header_len <= 1 or header_len > max_header_bytes:
        raise HeaderTransportError("HEADER_LENGTH_OUT_OF_BOUNDS", str(header_len))
    raw = read_range(shard_url, 8, header_len)
    if len(raw) != header_len:
        raise HeaderTransportError("HEADER_LENGTH_MISMATCH")
    try:
        parsed = json.loads(raw.rstrip(b" ").decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HeaderTransportError("HEADER_JSON_INVALID") from exc
    if not isinstance(parsed, dict):
        raise HeaderTransportError("HEADER_JSON_OBJECT_REQUIRED")
    return raw, parsed


def _entry_from_header(*, key: str, shard: str, header_sha256: str, header: Mapping[str, Any]) -> TensorHeaderEvidence:
    value = header.get(key)
    if not isinstance(value, dict):
        raise HeaderTransportError("TENSOR_HEADER_ENTRY_MISSING", key)
    dtype = value.get("dtype")
    shape = value.get("shape")
    offsets = value.get("data_offsets")
    if not isinstance(dtype, str) or not dtype:
        raise HeaderTransportError("TENSOR_DTYPE_INVALID", key)
    if not isinstance(shape, list) or not shape or any(type(v) is not int or v < 0 for v in shape):
        raise HeaderTransportError("TENSOR_SHAPE_INVALID", key)
    if (
        not isinstance(offsets, list)
        or len(offsets) != 2
        or any(type(v) is not int or v < 0 for v in offsets)
        or offsets[1] < offsets[0]
    ):
        raise HeaderTransportError("TENSOR_OFFSETS_INVALID", key)
    return TensorHeaderEvidence(
        tensor_key=key,
        shard_name=shard,
        dtype=dtype,
        shape=tuple(shape),
        data_offsets=(offsets[0], offsets[1]),
        header_sha256=header_sha256,
    )


def collect_header_evidence(
    *,
    repo_id: str,
    model_revision: str,
    expected_index_sha256: str,
    selected_layer: int = 3,
    selected_expert: int = 0,
    read_full: Callable[[str, int], bytes] = urllib_read_full,
    read_range: Callable[[str, int, int], bytes] = urllib_read_range,
    max_index_bytes: int = DEFAULT_MAX_INDEX_BYTES,
    max_header_bytes: int = DEFAULT_MAX_HEADER_BYTES,
) -> GLM53SafetensorsHeaderEvidence:
    raw_index, weight_map = fetch_index(
        repo_id=repo_id,
        model_revision=model_revision,
        expected_index_sha256=expected_index_sha256,
        read_full=read_full,
        max_index_bytes=max_index_bytes,
    )
    keys = representative_expert_keys(weight_map, layer=selected_layer, expert=selected_expert)
    shards = sorted({weight_map[key] for key in keys})
    headers: dict[str, tuple[str, dict[str, Any]]] = {}
    for shard in shards:
        shard_url = hf_resolve_url(repo_id, model_revision, _path(shard, shard_only=True))
        raw_header, header = fetch_safetensors_header(
            shard_url=shard_url,
            read_range=read_range,
            max_header_bytes=max_header_bytes,
        )
        headers[shard] = (_sha256(raw_header), header)
    entries = tuple(
        _entry_from_header(
            key=key,
            shard=weight_map[key],
            header_sha256=headers[weight_map[key]][0],
            header=headers[weight_map[key]][1],
        )
        for key in keys
    )
    return GLM53SafetensorsHeaderEvidence(
        repo_id=_repo(repo_id),
        model_revision=_commit(model_revision),
        index_sha256=_digest(expected_index_sha256),
        index_size_bytes=len(raw_index),
        selected_layer=selected_layer,
        selected_expert=selected_expert,
        entries=entries,
    )
