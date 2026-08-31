"""AURA-ARCHIVE-01: lossless structural archive probe.

This is an experimental artifact-compression surface, not a KV-cache, model-state,
or coordinate-memory performance claim.

It is deliberately conservative:
* arbitrary bytes are always supported through a raw fallback;
* canonical homogeneous JSON object arrays may be transposed into columns;
* the encoder tries RAW, zlib, lzma, and structured+backend candidates and keeps
  the smallest exact container;
* decoding verifies the original byte length and SHA-256;
* K27/13D/hydration metadata are optional routing annotations only and never
  participate in byte identity or decompression authority.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import json
import lzma
import struct
import time
import zlib
from typing import Any, Mapping

MAGIC = b"AURAAR1"
SCHEMA = "AURA-ARCHIVE-STRUCTURAL-PROBE-v1"
HEADER_VERSION = 1

MODE_RAW = "RAW"
MODE_ZLIB = "ZLIB"
MODE_LZMA = "LZMA"
MODE_JSON_COLUMNS_ZLIB = "JSON_COLUMNS_ZLIB"
MODE_JSON_COLUMNS_LZMA = "JSON_COLUMNS_LZMA"

RESPONSIBILITY = "ARTIFACT_COMPRESSION"


class ArchiveError(ValueError):
    pass


@dataclass(frozen=True)
class ArchiveReceipt:
    schema: str
    responsibility: str
    mode: str
    original_size: int
    archive_size: int
    original_sha256: str
    structured_candidate_admissible: bool
    structured_candidate_selected: bool
    exact_roundtrip_required: bool = True
    transformer_kv_claim: bool = False
    coordinate_memory_claim: bool = False
    model_state_claim: bool = False
    semantic_truth_claim: bool = False
    k27_authority: bool = False
    effect_authority: bool = False

    @property
    def ratio(self) -> float:
        return self.archive_size / self.original_size if self.original_size else 1.0


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _structured_columns_payload(data: bytes) -> bytes | None:
    """Return a reversible column projection only for already-canonical JSON rows.

    Restricting the transform to canonical input preserves byte exactness: the
    decoder serializes with the same canonical serializer and must recover
    identical bytes. Noncanonical JSON falls back to opaque-byte compression.
    """
    try:
        parsed = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None

    if _canon(parsed) != data:
        return None
    if not isinstance(parsed, list) or not parsed:
        return None
    if not all(isinstance(row, dict) for row in parsed):
        return None

    keys = tuple(parsed[0].keys())
    if not keys:
        return None
    keyset = set(keys)
    if any(set(row.keys()) != keyset for row in parsed):
        return None

    keys = tuple(sorted(keys))
    columns = {key: [row[key] for row in parsed] for key in keys}
    return _canon(
        {
            "schema": "AURA-JSON-COLUMNS-v1",
            "row_count": len(parsed),
            "keys": list(keys),
            "columns": columns,
        }
    )


def _restore_structured_columns(payload: bytes) -> bytes:
    try:
        body = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArchiveError("STRUCTURED_PAYLOAD_INVALID_JSON") from exc
    if body.get("schema") != "AURA-JSON-COLUMNS-v1":
        raise ArchiveError("STRUCTURED_SCHEMA_MISMATCH")
    keys = body.get("keys")
    columns = body.get("columns")
    row_count = body.get("row_count")
    if not isinstance(keys, list) or not isinstance(columns, dict) or not isinstance(row_count, int):
        raise ArchiveError("STRUCTURED_SHAPE_INVALID")
    if set(keys) != set(columns):
        raise ArchiveError("STRUCTURED_KEYS_COLUMNS_MISMATCH")
    if any(not isinstance(columns[k], list) or len(columns[k]) != row_count for k in keys):
        raise ArchiveError("STRUCTURED_COLUMN_LENGTH_MISMATCH")
    rows = [{key: columns[key][i] for key in keys} for i in range(row_count)]
    return _canon(rows)


def _pack(mode: str, original: bytes, payload: bytes) -> bytes:
    header = _canon(
        {
            "schema": SCHEMA,
            "version": HEADER_VERSION,
            "mode": mode,
            "original_size": len(original),
            "original_sha256": _sha(original),
            "responsibility": RESPONSIBILITY,
            "transformer_kv_claim": False,
            "coordinate_memory_claim": False,
            "model_state_claim": False,
            "semantic_truth_claim": False,
            "k27_authority": False,
            "effect_authority": False,
        }
    )
    return MAGIC + struct.pack(">I", len(header)) + header + payload


def _unpack(blob: bytes) -> tuple[Mapping[str, Any], bytes]:
    if not blob.startswith(MAGIC) or len(blob) < len(MAGIC) + 4:
        raise ArchiveError("ARCHIVE_MAGIC_INVALID")
    off = len(MAGIC)
    header_len = struct.unpack(">I", blob[off : off + 4])[0]
    off += 4
    if header_len <= 0 or off + header_len > len(blob):
        raise ArchiveError("ARCHIVE_HEADER_LENGTH_INVALID")
    try:
        header = json.loads(blob[off : off + header_len].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArchiveError("ARCHIVE_HEADER_INVALID") from exc
    if header.get("schema") != SCHEMA or header.get("version") != HEADER_VERSION:
        raise ArchiveError("ARCHIVE_SCHEMA_MISMATCH")
    if header.get("responsibility") != RESPONSIBILITY:
        raise ArchiveError("ARCHIVE_RESPONSIBILITY_MISMATCH")
    for field in (
        "transformer_kv_claim",
        "coordinate_memory_claim",
        "model_state_claim",
        "semantic_truth_claim",
        "k27_authority",
        "effect_authority",
    ):
        if header.get(field) is not False:
            raise ArchiveError("ARCHIVE_CLAIM_CEILING_WIDENED")
    return header, blob[off + header_len :]


def encode(data: bytes) -> tuple[bytes, ArchiveReceipt]:
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("BYTES_REQUIRED")
    original = bytes(data)
    structured = _structured_columns_payload(original)

    candidates: list[tuple[str, bytes]] = [(MODE_RAW, original)]
    candidates.append((MODE_ZLIB, zlib.compress(original, 9)))
    candidates.append((MODE_LZMA, lzma.compress(original, preset=9)))

    if structured is not None:
        candidates.append((MODE_JSON_COLUMNS_ZLIB, zlib.compress(structured, 9)))
        candidates.append((MODE_JSON_COLUMNS_LZMA, lzma.compress(structured, preset=9)))

    packed = [(mode, _pack(mode, original, payload)) for mode, payload in candidates]
    mode, archive = min(packed, key=lambda item: (len(item[1]), item[0]))
    receipt = ArchiveReceipt(
        schema=SCHEMA,
        responsibility=RESPONSIBILITY,
        mode=mode,
        original_size=len(original),
        archive_size=len(archive),
        original_sha256=_sha(original),
        structured_candidate_admissible=structured is not None,
        structured_candidate_selected=mode in {MODE_JSON_COLUMNS_ZLIB, MODE_JSON_COLUMNS_LZMA},
    )
    return archive, receipt


def decode(blob: bytes) -> bytes:
    header, payload = _unpack(bytes(blob))
    mode = header["mode"]
    if mode == MODE_RAW:
        recovered = payload
    elif mode == MODE_ZLIB:
        recovered = zlib.decompress(payload)
    elif mode == MODE_LZMA:
        recovered = lzma.decompress(payload)
    elif mode == MODE_JSON_COLUMNS_ZLIB:
        recovered = _restore_structured_columns(zlib.decompress(payload))
    elif mode == MODE_JSON_COLUMNS_LZMA:
        recovered = _restore_structured_columns(lzma.decompress(payload))
    else:
        raise ArchiveError("ARCHIVE_MODE_UNKNOWN")

    if len(recovered) != header.get("original_size"):
        raise ArchiveError("ROUNDTRIP_SIZE_MISMATCH")
    if _sha(recovered) != header.get("original_sha256"):
        raise ArchiveError("ROUNDTRIP_DIGEST_MISMATCH")
    return recovered


def benchmark(data: bytes, iterations: int = 3) -> Mapping[str, Any]:
    if iterations <= 0:
        raise ValueError("ITERATIONS_MUST_BE_POSITIVE")
    baseline_sizes = {
        "raw": len(data),
        "zlib9": len(zlib.compress(data, 9)),
        "lzma9": len(lzma.compress(data, preset=9)),
    }
    encode_times = []
    decode_times = []
    receipt = None
    archive = None
    for _ in range(iterations):
        t0 = time.perf_counter()
        archive, receipt = encode(data)
        encode_times.append((time.perf_counter() - t0) * 1000)
        t0 = time.perf_counter()
        recovered = decode(archive)
        decode_times.append((time.perf_counter() - t0) * 1000)
        if recovered != data:
            raise ArchiveError("ROUNDTRIP_BYTES_DIFFER")
    assert receipt is not None and archive is not None
    return {
        "receipt": asdict(receipt),
        "baseline_sizes": baseline_sizes,
        "archive_bytes": len(archive),
        "encode_ms_median": sorted(encode_times)[len(encode_times) // 2],
        "decode_ms_median": sorted(decode_times)[len(decode_times) // 2],
        "beats_zlib9_final_bytes": len(archive) < baseline_sizes["zlib9"],
        "beats_lzma9_final_bytes": len(archive) < baseline_sizes["lzma9"],
        "responsibility": RESPONSIBILITY,
        "kv_or_model_claim_granted": False,
    }


def make_aura_node_rows(count: int, *, generations: int = 7) -> bytes:
    """Deterministic canonical structured fixture approximating Aura record shape."""
    if count <= 0:
        raise ValueError("COUNT_MUST_BE_POSITIVE")
    sectors = ("00_MEM", "01_WRK", "04_TRU", "05_GOV", "06_RUN", "07_SEC", "08_RSH")
    relations = (
        "DEPENDS_ON",
        "DERIVED_FROM",
        "GROUNDED_IN",
        "VERIFIES",
        "IMPLEMENTS",
        "STALE_RELATIVE_TO",
    )
    levels = ("L0", "L1", "L2", "L3", "L4")
    providers = ("ARXIV", "GITHUB", "REDDIT", "DRIVE")
    rows = []
    for i in range(count):
        subject = i % max(1, count // generations)
        rows.append(
            {
                "SID": hashlib.sha256(f"subject:{subject}".encode()).hexdigest(),
                "GID": hashlib.sha256(f"generation:{i}".encode()).hexdigest(),
                "sector": sectors[i % len(sectors)],
                "event_at": f"2026-08-{1 + (i % 31):02d}T{(i % 24):02d}:00:00Z",
                "recorded_at": f"2026-08-{1 + (i % 31):02d}T{(i % 24):02d}:05:00Z",
                "hydration": levels[i % len(levels)],
                "provider": providers[i % len(providers)],
                "k27": [(i * 3) % 27, (i * 7) % 27, (i * 11) % 27],
                "relation": relations[i % len(relations)],
                "candidate_only": True,
                "effect_authority": False,
                "summary": f"subject {subject} generation {i} in {sectors[i % len(sectors)]}",
            }
        )
    return _canon(rows)


def build_40_rack_matrix() -> tuple[bytes, ...]:
    """40 deterministic racks spanning structured, prose, high-entropy and compressed inputs."""
    racks: list[bytes] = []
    for n in range(64, 704, 64):
        racks.append(make_aura_node_rows(n))

    phrase = (
        b"CURRENT_REFERENCE != CurrentAtRead | K27Placement != SemanticIdentity | "
        b"HydrationLevel != VerificationLevel | "
    )
    for i in range(10):
        racks.append((phrase + f"rack={i}\n".encode()) * (32 + i * 7))

    state = 0x9E3779B97F4A7C15
    mask = (1 << 64) - 1
    for i in range(10):
        body = bytearray()
        for _ in range(4096 + i * 257):
            state ^= (state << 13) & mask
            state ^= state >> 7
            state ^= (state << 17) & mask
            body.append(state & 0xFF)
        racks.append(bytes(body))

    for i in range(10):
        source = make_aura_node_rows(48 + i * 8) if i % 2 == 0 else (phrase * (40 + i))
        racks.append(zlib.compress(source, 9))

    if len(racks) != 40:
        raise AssertionError("FORTY_RACKS_REQUIRED")
    return tuple(racks)
