"""Source-bound raw JSON intake for the AWJ032 GLM-5.3 checkpoint layout probe.

D0 metadata-only helper. It couples the raw config/index bytes, their SHA-256
identities, and the parsed mappings so a caller cannot classify parsed source Y
while emitting a receipt that claims raw source X. It performs no network access,
weight materialization, model import, or G2 admission.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Callable, Mapping

SOURCE_SCHEMA = "GLM53CheckpointSourceBundleV1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class SourceBindingError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise SourceBindingError("NONCANONICAL_JSON_MAPPING") from exc


def _expected_sha(value: str, field: str) -> str:
    if not isinstance(value, str):
        raise SourceBindingError("SHA256_REQUIRED", field)
    value = value.strip().lower()
    if not _SHA256_RE.fullmatch(value):
        raise SourceBindingError("SHA256_INVALID", field)
    return value


def _immutable_commit(value: str) -> str:
    if not isinstance(value, str):
        raise SourceBindingError("IMMUTABLE_MODEL_REVISION_REQUIRED")
    value = value.strip().lower()
    if not _COMMIT_RE.fullmatch(value):
        raise SourceBindingError("IMMUTABLE_MODEL_REVISION_REQUIRED", value)
    return value


@dataclass(frozen=True)
class BoundJsonSource:
    name: str
    raw_sha256: str
    parsed_sha256: str
    canonical_json: bytes

    def mapping(self) -> dict[str, Any]:
        value = json.loads(self.canonical_json)
        if not isinstance(value, dict):
            raise SourceBindingError("TOP_LEVEL_JSON_OBJECT_REQUIRED", self.name)
        return value


@dataclass(frozen=True)
class GLM53CheckpointSourceBundle:
    model_revision: str
    config: BoundJsonSource
    index: BoundJsonSource
    schema: str = SOURCE_SCHEMA

    @property
    def weight_map_digest(self) -> str:
        index_map = self.index.mapping()
        weight_map = index_map.get("weight_map")
        if not isinstance(weight_map, Mapping) or not weight_map:
            raise SourceBindingError("INDEX_WEIGHT_MAP_REQUIRED")
        normalized = dict(sorted((str(k), str(v)) for k, v in weight_map.items()))
        return _sha256_bytes(_canonical(normalized))

    @property
    def source_bundle_id(self) -> str:
        return hashlib.sha256(
            _canonical(
                {
                    "schema": self.schema,
                    "model_revision": self.model_revision,
                    "config_raw_sha256": self.config.raw_sha256,
                    "config_parsed_sha256": self.config.parsed_sha256,
                    "index_raw_sha256": self.index.raw_sha256,
                    "index_parsed_sha256": self.index.parsed_sha256,
                    "weight_map_digest": self.weight_map_digest,
                }
            )
        ).hexdigest()


def bind_json_source(*, name: str, raw_bytes: bytes, expected_sha256: str) -> BoundJsonSource:
    if not isinstance(raw_bytes, bytes):
        raise SourceBindingError("RAW_BYTES_REQUIRED", name)
    expected = _expected_sha(expected_sha256, name)
    observed = _sha256_bytes(raw_bytes)
    if observed != expected:
        raise SourceBindingError("RAW_SHA256_MISMATCH", f"{name}:expected={expected},observed={observed}")
    try:
        parsed = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceBindingError("JSON_PARSE_FAILED", name) from exc
    if not isinstance(parsed, dict):
        raise SourceBindingError("TOP_LEVEL_JSON_OBJECT_REQUIRED", name)
    canonical = _canonical(parsed)
    return BoundJsonSource(
        name=name,
        raw_sha256=observed,
        parsed_sha256=_sha256_bytes(canonical),
        canonical_json=canonical,
    )


def bind_checkpoint_sources(
    *,
    model_revision: str,
    config_raw_bytes: bytes,
    expected_config_sha256: str,
    index_raw_bytes: bytes,
    expected_index_sha256: str,
) -> GLM53CheckpointSourceBundle:
    revision = _immutable_commit(model_revision)
    config = bind_json_source(
        name="config.json",
        raw_bytes=config_raw_bytes,
        expected_sha256=expected_config_sha256,
    )
    index = bind_json_source(
        name="model.safetensors.index.json",
        raw_bytes=index_raw_bytes,
        expected_sha256=expected_index_sha256,
    )
    index_map = index.mapping()
    weight_map = index_map.get("weight_map")
    if not isinstance(weight_map, Mapping) or not weight_map:
        raise SourceBindingError("INDEX_WEIGHT_MAP_REQUIRED")
    for key, shard in weight_map.items():
        if not isinstance(key, str) or not key or not isinstance(shard, str) or not shard:
            raise SourceBindingError("INDEX_WEIGHT_MAP_ENTRY_INVALID")
    return GLM53CheckpointSourceBundle(
        model_revision=revision,
        config=config,
        index=index,
    )


def source_bound_probe(
    *,
    sources: GLM53CheckpointSourceBundle,
    airllm_revision: str,
    security_hard_false_remote_code: bool,
    representative_sparse_layer: int = 3,
    shard_sizes: Mapping[str, int] | None = None,
    observation_time: str | None = None,
    probe_fn: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not isinstance(sources, GLM53CheckpointSourceBundle) or sources.schema != SOURCE_SCHEMA:
        raise SourceBindingError("SOURCE_BUNDLE_REQUIRED")
    config = sources.config.mapping()
    index = sources.index.mapping()
    weight_map = index.get("weight_map")
    if not isinstance(weight_map, Mapping):
        raise SourceBindingError("INDEX_WEIGHT_MAP_REQUIRED")
    if probe_fn is None:
        try:
            from .glm53_checkpoint_layout_probe import probe_checkpoint as probe_fn  # type: ignore
        except ImportError:
            from glm53_checkpoint_layout_probe import probe_checkpoint as probe_fn  # type: ignore
    report = probe_fn(
        config=config,
        weight_map=weight_map,
        model_revision=sources.model_revision,
        config_sha256=sources.config.raw_sha256,
        index_sha256=sources.index.raw_sha256,
        airllm_revision=airllm_revision,
        security_hard_false_remote_code=security_hard_false_remote_code,
        representative_sparse_layer=representative_sparse_layer,
        shard_sizes=shard_sizes,
        observation_time=observation_time,
    )
    if not isinstance(report, dict):
        raise SourceBindingError("PROBE_REPORT_INVALID")
    return {
        **report,
        "source_bundle_id": sources.source_bundle_id,
        "config_parsed_sha256": sources.config.parsed_sha256,
        "index_parsed_sha256": sources.index.parsed_sha256,
        "weight_map_digest": sources.weight_map_digest,
        "source_binding_proven": True,
    }
