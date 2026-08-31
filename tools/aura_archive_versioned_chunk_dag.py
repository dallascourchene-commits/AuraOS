"""Versioned content-defined chunk DAG addendum for Aura's structural archive.

This module does not replace the structural archive codec. Each unique exact byte
chunk is delegated to ``aura_structural_archive_probe.encode`` and reconstructed
through that owner's ``decode`` path.

The addendum owns only multi-artifact / multi-generation structure:
- content-defined chunk boundaries;
- exact SHA-256 chunk deduplication across generations;
- ordered per-artifact chunk manifests;
- orthogonal L0-L3, domain, bitemporal, scale, Connectome, 13D and K27 indexes;
- deterministic exact reconstruction with fail-closed integrity checks.

Semantic similarity is never a lossless-dedup criterion. A future structural
transform may enter the source plane only after an exact round-trip witness.
"""

from __future__ import annotations

import hashlib
import json
import struct
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from tools import aura_structural_archive_probe as structural

MAGIC = b"AURAVDG1"
SCHEMA = "AURA-ARCHIVE-VERSIONED-CHUNK-DAG-v1"
CDC_ALGORITHM = "AURA_GEAR_CDC_V1"
_MAX_U64 = (1 << 64) - 1
_GEAR = tuple(
    int.from_bytes(hashlib.sha256(b"AURA-CDC-GEAR-v1" + bytes([i])).digest()[:8], "big")
    for i in range(256)
)


class VersionedArchiveError(ValueError):
    pass


@dataclass(frozen=True)
class ChunkingPolicy:
    min_size: int = 16 * 1024
    avg_size: int = 64 * 1024
    max_size: int = 256 * 1024

    def validate(self) -> None:
        if not (0 < self.min_size <= self.avg_size <= self.max_size):
            raise VersionedArchiveError("CDC_SIZE_ORDER_INVALID")
        if self.max_size > 16 * 1024 * 1024:
            raise VersionedArchiveError("CDC_MAX_SIZE_EXCEEDS_D0_CEILING")

    @property
    def boundary_mask(self) -> int:
        bits = max(1, (self.avg_size - 1).bit_length())
        return (1 << bits) - 1


@dataclass(frozen=True)
class VersionedArtifact:
    artifact_id: str
    subject_key: str
    generation_id: str
    source_bytes: bytes
    sector: str
    event_at: str
    recorded_at: str
    scale: str
    hydration_index: Mapping[str, Any]
    connectome_edges: Sequence[Mapping[str, Any]] = ()
    d13: tuple[int, ...] | None = None
    k27: tuple[int, int, int] | None = None


@dataclass(frozen=True)
class VersionedArchiveStats:
    logical_source_bytes: int
    unique_chunk_source_bytes: int
    encoded_unique_chunk_bytes: int
    manifest_bytes: int
    archive_bytes: int
    unique_chunks: int
    referenced_chunks: int
    structural_modes: tuple[tuple[str, int], ...]

    @property
    def exact_dedup_savings_fraction(self) -> float:
        if not self.logical_source_bytes:
            return 0.0
        return 1.0 - self.unique_chunk_source_bytes / self.logical_source_bytes

    @property
    def final_archive_savings_fraction(self) -> float:
        if not self.logical_source_bytes:
            return 0.0
        return 1.0 - self.archive_bytes / self.logical_source_bytes


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canon(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise VersionedArchiveError("INDEX_NOT_CANONICAL_JSON") from exc


def _validate_index(artifact: VersionedArtifact) -> None:
    if not all(
        isinstance(value, str) and value
        for value in (
            artifact.artifact_id,
            artifact.subject_key,
            artifact.generation_id,
            artifact.sector,
            artifact.event_at,
            artifact.recorded_at,
            artifact.scale,
        )
    ):
        raise VersionedArchiveError("ARTIFACT_IDENTITY_OR_AXIS_MISSING")
    if not isinstance(artifact.source_bytes, bytes):
        raise VersionedArchiveError("EXACT_SOURCE_BYTES_REQUIRED")
    if "L4" in artifact.hydration_index:
        raise VersionedArchiveError("L4_BELONGS_TO_EXACT_SOURCE_PLANE_NOT_INDEX_OVERLAY")
    allowed_levels = {"L0", "L1", "L2", "L3"}
    if not set(artifact.hydration_index).issubset(allowed_levels):
        raise VersionedArchiveError("HYDRATION_INDEX_LEVEL_INVALID")
    if artifact.k27 is not None:
        if len(artifact.k27) != 3 or any(
            isinstance(v, bool) or not isinstance(v, int) or not 0 <= v < 27
            for v in artifact.k27
        ):
            raise VersionedArchiveError("K27_XYZ_INVALID")
    if artifact.d13 is not None:
        if len(artifact.d13) != 13 or any(v not in (-1, 0, 1) for v in artifact.d13):
            raise VersionedArchiveError("D13_TERNARY_PROJECTION_INVALID")
    _canon(dict(artifact.hydration_index))
    _canon(list(artifact.connectome_edges))


def content_defined_chunks(
    data: bytes,
    policy: ChunkingPolicy = ChunkingPolicy(),
) -> tuple[bytes, ...]:
    policy.validate()
    if not data:
        return (b"",)
    start = 0
    rolling = 0
    chunks: list[bytes] = []
    for pos, byte in enumerate(data, start=1):
        rolling = ((rolling << 1) + _GEAR[byte]) & _MAX_U64
        length = pos - start
        if length >= policy.min_size and (
            (rolling & policy.boundary_mask) == 0 or length >= policy.max_size
        ):
            chunks.append(data[start:pos])
            start = pos
            rolling = 0
    if start < len(data):
        chunks.append(data[start:])
    return tuple(chunks)


def _artifact_row(artifact: VersionedArtifact, chunk_digests: Sequence[str]) -> dict[str, Any]:
    row = {
        "artifact_id": artifact.artifact_id,
        "subject_key": artifact.subject_key,
        "generation_id": artifact.generation_id,
        "source_sha256": _sha(artifact.source_bytes),
        "source_length": len(artifact.source_bytes),
        "ordered_chunk_digests": list(chunk_digests),
        "index_plane": {
            "sector": artifact.sector,
            "event_at": artifact.event_at,
            "recorded_at": artifact.recorded_at,
            "scale": artifact.scale,
            "hydration": dict(artifact.hydration_index),
            "connectome_edges": list(artifact.connectome_edges),
            "d13": list(artifact.d13) if artifact.d13 is not None else None,
            "k27": list(artifact.k27) if artifact.k27 is not None else None,
        },
        "index_plane_is_reconstruction_authority": False,
        "event_time_is_record_time": False,
        "temporal_adjacency_is_causal_dependency": False,
        "source_plane_exact": True,
    }
    row["manifest_identity"] = _sha(_canon(row))
    return row


def pack_versioned_archive(
    artifacts: Sequence[VersionedArtifact],
    *,
    policy: ChunkingPolicy = ChunkingPolicy(),
) -> tuple[bytes, VersionedArchiveStats]:
    policy.validate()
    if not artifacts:
        raise VersionedArchiveError("AT_LEAST_ONE_ARTIFACT_REQUIRED")

    unique_raw: dict[str, bytes] = {}
    rows: list[dict[str, Any]] = []
    seen_artifact_ids: set[str] = set()
    referenced_chunks = 0

    for artifact in artifacts:
        _validate_index(artifact)
        if artifact.artifact_id in seen_artifact_ids:
            raise VersionedArchiveError("DUPLICATE_ARTIFACT_ID")
        seen_artifact_ids.add(artifact.artifact_id)
        refs: list[str] = []
        for chunk in content_defined_chunks(artifact.source_bytes, policy):
            digest = _sha(chunk)
            existing = unique_raw.get(digest)
            if existing is not None and existing != chunk:
                raise VersionedArchiveError("SHA256_CHUNK_COLLISION")
            unique_raw[digest] = chunk
            refs.append(digest)
        referenced_chunks += len(refs)
        rows.append(_artifact_row(artifact, refs))

    rows.sort(key=lambda row: row["artifact_id"])
    encoded_chunks: dict[str, bytes] = {}
    modes: dict[str, int] = {}
    for digest in sorted(unique_raw):
        raw = unique_raw[digest]
        encoded, receipt = structural.encode(raw)
        if structural.decode(encoded) != raw:
            raise VersionedArchiveError("STRUCTURAL_OWNER_ROUNDTRIP_FAILED")
        if getattr(receipt, "original_sha256", _sha(raw)) != _sha(raw):
            raise VersionedArchiveError("STRUCTURAL_OWNER_DIGEST_MISMATCH")
        encoded_chunks[digest] = encoded
        mode = str(getattr(receipt, "mode", "UNKNOWN"))
        modes[mode] = modes.get(mode, 0) + 1

    manifest = {
        "schema": SCHEMA,
        "source_plane": {
            "chunk_identity": "SHA256_EXACT_BYTES",
            "chunking": {
                "algorithm": CDC_ALGORITHM,
                "min_size": policy.min_size,
                "avg_size": policy.avg_size,
                "max_size": policy.max_size,
            },
            "per_chunk_codec_owner": structural.SCHEMA,
        },
        "index_plane": {
            "reconstruction_authority": False,
            "semantic_similarity_dedup_authority": False,
            "k27_identity_authority": False,
            "d13_truth_authority": False,
            "timeline_causality_authority": False,
            "scale_authority": False,
        },
        "claim_ceiling": {
            "universal_compression_superiority": False,
            "semantic_truth": False,
            "coordinate_memory_write_authority": False,
            "native_private_transformer_kv": False,
            "effect_authority": False,
            "gate10": False,
        },
        "artifacts": rows,
    }
    manifest_bytes = _canon(manifest)
    out = bytearray(MAGIC)
    out.extend(struct.pack(">Q", len(manifest_bytes)))
    out.extend(manifest_bytes)

    encoded_total = 0
    for digest in sorted(encoded_chunks):
        blob = encoded_chunks[digest]
        encoded_total += len(blob)
        out.extend(bytes.fromhex(digest))
        out.extend(struct.pack(">Q", len(blob)))
        out.extend(blob)

    archive = bytes(out)
    stats = VersionedArchiveStats(
        logical_source_bytes=sum(len(a.source_bytes) for a in artifacts),
        unique_chunk_source_bytes=sum(len(c) for c in unique_raw.values()),
        encoded_unique_chunk_bytes=encoded_total,
        manifest_bytes=len(manifest_bytes),
        archive_bytes=len(archive),
        unique_chunks=len(unique_raw),
        referenced_chunks=referenced_chunks,
        structural_modes=tuple(sorted(modes.items())),
    )
    return archive, stats


def _parse(
    archive: bytes,
    *,
    max_unique_source_bytes: int = 1 << 30,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    if not isinstance(archive, bytes) or not archive.startswith(MAGIC):
        raise VersionedArchiveError("VERSIONED_ARCHIVE_MAGIC_INVALID")
    if len(archive) < len(MAGIC) + 8:
        raise VersionedArchiveError("VERSIONED_ARCHIVE_HEADER_TRUNCATED")
    pos = len(MAGIC)
    manifest_len = struct.unpack(">Q", archive[pos : pos + 8])[0]
    pos += 8
    if manifest_len > len(archive) - pos:
        raise VersionedArchiveError("VERSIONED_ARCHIVE_MANIFEST_TRUNCATED")
    manifest_bytes = archive[pos : pos + manifest_len]
    pos += manifest_len
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VersionedArchiveError("VERSIONED_ARCHIVE_MANIFEST_INVALID") from exc
    if _canon(manifest) != manifest_bytes:
        raise VersionedArchiveError("VERSIONED_ARCHIVE_MANIFEST_NONCANONICAL")
    if manifest.get("schema") != SCHEMA:
        raise VersionedArchiveError("VERSIONED_ARCHIVE_SCHEMA_MISMATCH")
    index = manifest.get("index_plane", {})
    if index.get("reconstruction_authority") is not False:
        raise VersionedArchiveError("INDEX_PLANE_RECONSTRUCTION_AUTHORITY_FORBIDDEN")
    if index.get("semantic_similarity_dedup_authority") is not False:
        raise VersionedArchiveError("SEMANTIC_SIMILARITY_DEDUP_AUTHORITY_FORBIDDEN")

    chunks: dict[str, bytes] = {}
    total_raw = 0
    while pos < len(archive):
        if len(archive) - pos < 40:
            raise VersionedArchiveError("VERSIONED_CHUNK_RECORD_TRUNCATED")
        digest = archive[pos : pos + 32].hex()
        pos += 32
        encoded_len = struct.unpack(">Q", archive[pos : pos + 8])[0]
        pos += 8
        if encoded_len > len(archive) - pos:
            raise VersionedArchiveError("VERSIONED_CHUNK_PAYLOAD_TRUNCATED")
        encoded = archive[pos : pos + encoded_len]
        pos += encoded_len
        try:
            raw = structural.decode(encoded)
        except Exception as exc:
            raise VersionedArchiveError("STRUCTURAL_CHUNK_DECODE_FAILED") from exc
        if _sha(raw) != digest:
            raise VersionedArchiveError("VERSIONED_CHUNK_DIGEST_MISMATCH")
        total_raw += len(raw)
        if total_raw > max_unique_source_bytes:
            raise VersionedArchiveError("UNIQUE_SOURCE_BYTE_CEILING_EXCEEDED")
        prior = chunks.get(digest)
        if prior is not None and prior != raw:
            raise VersionedArchiveError("VERSIONED_DUPLICATE_CHUNK_CONFLICT")
        chunks[digest] = raw
    return manifest, chunks


def unpack_versioned_archive(
    archive: bytes,
    *,
    max_unique_source_bytes: int = 1 << 30,
) -> dict[str, bytes]:
    manifest, chunks = _parse(archive, max_unique_source_bytes=max_unique_source_bytes)
    result: dict[str, bytes] = {}
    for row in manifest.get("artifacts", []):
        artifact_id = row.get("artifact_id")
        if not isinstance(artifact_id, str) or not artifact_id or artifact_id in result:
            raise VersionedArchiveError("ARTIFACT_MANIFEST_ID_INVALID")
        if row.get("index_plane_is_reconstruction_authority") is not False:
            raise VersionedArchiveError("ARTIFACT_INDEX_RECONSTRUCTION_AUTHORITY_FORBIDDEN")
        refs = row.get("ordered_chunk_digests")
        if not isinstance(refs, list) or not all(
            isinstance(ref, str) and len(ref) == 64 for ref in refs
        ):
            raise VersionedArchiveError("ARTIFACT_CHUNK_REFS_INVALID")
        try:
            raw = b"".join(chunks[ref] for ref in refs)
        except KeyError as exc:
            raise VersionedArchiveError("ARTIFACT_REFERENCED_CHUNK_MISSING") from exc
        if len(raw) != row.get("source_length") or _sha(raw) != row.get("source_sha256"):
            raise VersionedArchiveError("ARTIFACT_EXACT_SOURCE_RECONSTRUCTION_FAILED")
        result[artifact_id] = raw
    return result


def inspect_versioned_archive(archive: bytes) -> Mapping[str, Any]:
    manifest, chunks = _parse(archive)
    return {
        "schema": manifest["schema"],
        "archive_sha256": _sha(archive),
        "artifact_count": len(manifest.get("artifacts", [])),
        "unique_chunk_count": len(chunks),
        "source_plane": manifest["source_plane"],
        "index_plane": manifest["index_plane"],
        "claim_ceiling": manifest["claim_ceiling"],
        "artifacts": manifest["artifacts"],
    }


def k27_url_coordinate(url: str) -> tuple[int, int, int]:
    digest = hashlib.sha256(url.encode("utf-8")).digest()
    return (digest[0] % 27, digest[1] % 27, digest[2] % 27)


def require_exact_reversible_transform(encode, decode, source: bytes) -> bytes:
    transformed = encode(source)
    if decode(transformed) != source:
        raise VersionedArchiveError("TRANSFORM_NOT_EXACTLY_REVERSIBLE")
    return transformed


__all__ = [
    "ChunkingPolicy",
    "VersionedArtifact",
    "VersionedArchiveError",
    "VersionedArchiveStats",
    "content_defined_chunks",
    "inspect_versioned_archive",
    "k27_url_coordinate",
    "pack_versioned_archive",
    "require_exact_reversible_transform",
    "unpack_versioned_archive",
]
