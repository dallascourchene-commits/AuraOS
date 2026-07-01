"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f5-[Q-SYS:6C2848D106FBD645]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: json, aura_dream_retrieval, __future__, typing, time, pathlib, base64, dataclasses, hashlib, urllib.parse, struct
FUNCTIONS: _digest, compile_st3gg_pointer, _key_token, _esc, compile_visible_st3gg_capsule, index_path_for_ledger, store_path_for_ledger, hash_table_path_for_ledger, _load_index, _file_size, decode_st3gg_compaction_blob, compute_compaction_efficiency, st3gg_recall_index_stats, _target_capacity, _hash_key, _init_hash_table, _read_hash_header, _slot_offset, _write_hash_count, _record_matches_key, _append_store_record, _read_store_record, _insert_hash_alias, _lookup_hash_recall, _rebuild_hash_sidecar, _upsert_hash_sidecar, upsert_st3gg_recall, lookup_st3gg_recall, rerank_st3gg_recall_candidates, to_jsonable, from_jsonable
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import struct
import time
from typing import Any
from urllib.parse import quote

from aura_dream_retrieval import DREAM_LEDGER_PATH, DreamCandidate, rerank_for_arena

ST3GG_RECALL_VERSION = "AURA_ST3GG_RECALL_V1"
DEFAULT_HASH_CAPACITY = 2048
MAX_HASH_LOAD = 0.68
FROZEN_COMPACTION_ALIAS_THRESHOLD = 4096
ST3GG_COMPACTION_MAGIC = b"AST3CMP1"
ST3GG_COMPACTION_VERSION = 1
ST3GG_COMPACTION_TABLE_SCALE = 2
ST3GG_COMPACTION_HASH_PROFILE_DJB2_SEED8 = 1
_ST3GG_COMPACTION_HEADER = struct.Struct("<8sIIIII")
_HASH_MAGIC = b"AST3GGH1"
_HASH_HEADER = struct.Struct("<8sII")
_HASH_SLOT = struct.Struct("<QQII")
_EMPTY_SLOT = _HASH_SLOT.pack(0, 0, 0, 0)


@dataclass(frozen=True)
class ST3GGRecallRecord:
    pointer: str
    dash_key: str
    glyph: str
    holographic_header: str
    original_hash: str
    content_type: str
    original: str
    compressed: str = ""
    source_hint: str = ""
    created_unix: float = 0.0

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "version": ST3GG_RECALL_VERSION,
            "pointer": self.pointer,
            "dash_key": self.dash_key,
            "glyph": self.glyph,
            "holographic_header": self.holographic_header,
            "original_hash": self.original_hash,
            "content_type": self.content_type,
            "source_hint": self.source_hint,
            "created_unix": self.created_unix or time.time(),
            "original": self.original,
            "compressed": self.compressed,
        }

    @classmethod
    def from_jsonable(cls, payload: dict[str, Any]) -> ST3GGRecallRecord:
        return cls(
            pointer=str(payload.get("pointer", "")),
            dash_key=str(payload.get("dash_key", "")),
            glyph=str(payload.get("glyph", "")),
            holographic_header=str(payload.get("holographic_header", "")),
            original_hash=str(payload.get("original_hash", "")),
            content_type=str(payload.get("content_type", "")),
            source_hint=str(payload.get("source_hint", "")),
            created_unix=float(payload.get("created_unix", 0.0) or 0.0),
            original=str(payload.get("original", "")),
            compressed=str(payload.get("compressed", "")),
        )


def _digest(content: str, *, size: int) -> str:
    return hashlib.blake2b(content.encode("utf-8", errors="replace"), digest_size=size).hexdigest()


def compile_st3gg_pointer(content: str, *, namespace: str = "CCR", seed: int = 0xA901) -> tuple[str, str, str, str]:
    """Return (pointer, dash_key, glyph, holographic_header) for visible O(1) recall."""
    safe_namespace = "".join(
        ch if ch.isascii() and (ch.isalnum() or ch in "_-") else "_"
        for ch in namespace.upper()
    ) or "CCR"
    material = f"{seed}:{safe_namespace}:{content}"
    dash_key = _digest(material, size=8)
    glyph = _digest(f"GLYPH:{material}", size=2).upper()
    pointer = f"ST3GG-L2::{safe_namespace}:{glyph}:{dash_key}"
    header_raw = hashlib.blake2b(f"HOLO:{material}".encode("utf-8", errors="replace"), digest_size=48).digest()
    holographic_header = base64.urlsafe_b64encode(header_raw).decode("ascii").rstrip("=")
    return pointer, dash_key, glyph, holographic_header


def _key_token(key: str, seed: int, index: int) -> str:
    digest = hashlib.blake2b(f"{seed}:{index}:{key}".encode(), digest_size=2).hexdigest().upper()
    return f"K{index:X}{digest[:2]}"


def _esc(value: Any, *, limit: int = 180) -> str:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    else:
        text = str(value)
    text = text.replace("\r", " ").replace("\n", "\\n").strip()
    return quote(text[:limit], safe=" ._-/+#")


def compile_visible_st3gg_capsule(
    data: Any,
    *,
    seed: int = 0xA901,
    max_rows: int = 24,
) -> str | None:
    """Compile JSON-like structures into a visible ASCII ST3GG capsule."""
    if isinstance(data, list) and data and all(isinstance(item, dict) for item in data):
        keys = sorted({str(key) for item in data for key in item.keys()})
        tokens = [_key_token(key, seed, idx) for idx, key in enumerate(keys)]
        key_spec = ",".join(f"{token}:{_esc(key, limit=80)}" for token, key in zip(tokens, keys))
        rows = []
        for item in data[:max_rows]:
            rows.append(",".join(_esc(item.get(key, "")) for key in keys))
        omitted = max(0, len(data) - len(rows))
        return f"ST3GG1|S={seed:X}|M=rows|K={key_spec}|R={';'.join(rows)}|O={omitted}"

    if isinstance(data, dict) and data:
        keys = sorted(str(key) for key in data.keys())
        tokens = [_key_token(key, seed, idx) for idx, key in enumerate(keys)]
        key_spec = ",".join(f"{token}:{_esc(key, limit=80)}" for token, key in zip(tokens, keys))
        pairs = ";".join(f"{token}={_esc(data.get(key, ''))}" for token, key in zip(tokens, keys))
        return f"ST3GG1|S={seed:X}|M=dict|K={key_spec}|D={pairs}"
    return None


def index_path_for_ledger(ledger_path: str | Path) -> Path:
    path = Path(ledger_path)
    return path.with_suffix(path.suffix + ".st3gg_index.json")


def store_path_for_ledger(ledger_path: str | Path) -> Path:
    path = Path(ledger_path)
    return path.with_suffix(path.suffix + ".st3gg_store.jsonl")


def hash_table_path_for_ledger(ledger_path: str | Path) -> Path:
    path = Path(ledger_path)
    return path.with_suffix(path.suffix + ".st3gg_hash.bin")


def _load_index(index_path: Path) -> dict[str, Any]:
    if not index_path.exists():
        return {"version": ST3GG_RECALL_VERSION, "records": {}, "aliases": {}}
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": ST3GG_RECALL_VERSION, "records": {}, "aliases": {}}
    payload.setdefault("version", ST3GG_RECALL_VERSION)
    payload.setdefault("records", {})
    payload.setdefault("aliases", {})
    return payload


def _file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def decode_st3gg_compaction_blob(blob: bytes) -> dict[str, Any]:
    """Decode and validate the Stage 2 Rust compactor binary output."""
    if len(blob) < _ST3GG_COMPACTION_HEADER.size:
        raise ValueError("st3gg_compaction_blob_truncated")
    magic, version, key_count, table_size, table_scale, hash_profile = _ST3GG_COMPACTION_HEADER.unpack_from(blob)
    if magic != ST3GG_COMPACTION_MAGIC:
        raise ValueError("st3gg_compaction_bad_magic")
    if version != ST3GG_COMPACTION_VERSION:
        raise ValueError("st3gg_compaction_unsupported_version")
    if table_scale != ST3GG_COMPACTION_TABLE_SCALE:
        raise ValueError("st3gg_compaction_table_scale_mismatch")
    if hash_profile != ST3GG_COMPACTION_HASH_PROFILE_DJB2_SEED8:
        raise ValueError("st3gg_compaction_hash_profile_mismatch")
    pilots = blob[_ST3GG_COMPACTION_HEADER.size:]
    if len(pilots) != key_count:
        raise ValueError("st3gg_compaction_pilot_count_mismatch")
    expected_table = key_count * table_scale
    if table_size != expected_table:
        raise ValueError("st3gg_compaction_table_size_mismatch")
    return {
        "magic": magic.decode("ascii"),
        "version": version,
        "key_count": key_count,
        "table_size": table_size,
        "table_scale": table_scale,
        "hash_profile": hash_profile,
        "hash_profile_name": "djb2_u64_seed8",
        "pilots": tuple(pilots),
    }


def compute_compaction_efficiency(
    raw_keys_count: int,
    file_size_bytes: int,
    lookup_latency_sec: float,
) -> dict[str, Any]:
    """Score a recall sidecar against the 1.44 bits/key MPHF lower-bound target."""
    keys = max(1, int(raw_keys_count))
    bits_per_key = (max(0, int(file_size_bytes)) * 8) / keys
    latency = max(0.0, float(lookup_latency_sec))
    structural_coherence = 0.99
    lower_bound_bits_per_key = 1.44
    space_ratio = lower_bound_bits_per_key / max(0.1, bits_per_key)
    efficiency = (structural_coherence * space_ratio) / (latency + 1e-6)
    return {
        "metric_profile": "AURA_ST3GG_HASH_COMPACTION_ANALYTICS",
        "computed_system_efficiency": round(efficiency, 4),
        "allocated_bits_per_key": round(bits_per_key, 2),
        "mphf_lower_bound_bits_per_key": lower_bound_bits_per_key,
        "space_optimization_ratio": round(space_ratio, 6),
        "lookup_latency_sec": latency,
        "recall_complexity_profile": "BOUNDED_O_1_ACTIVE_HASH",
    }


def st3gg_recall_index_stats(
    ledger_path: str | Path,
    *,
    lookup_latency_sec: float = 0.0,
) -> dict[str, Any]:
    """Return active sidecar metrics and whether a frozen MPHF segment is warranted."""
    table_path = hash_table_path_for_ledger(ledger_path)
    store_path = store_path_for_ledger(ledger_path)
    index_path = index_path_for_ledger(ledger_path)
    header = _read_hash_header(table_path)
    capacity, alias_count = header if header is not None else (0, 0)
    table_bytes = _file_size(table_path)
    store_bytes = _file_size(store_path)
    index_bytes = _file_size(index_path)
    stats = compute_compaction_efficiency(
        raw_keys_count=alias_count,
        file_size_bytes=table_bytes,
        lookup_latency_sec=lookup_latency_sec,
    )
    load_factor = alias_count / capacity if capacity else 0.0
    return {
        **stats,
        "index_profile": "AURA_ST3GG_OPEN_ADDRESS_HASH",
        "hash_capacity": capacity,
        "indexed_alias_count": alias_count,
        "estimated_record_count": alias_count // 3,
        "hash_load_factor": round(load_factor, 4),
        "hash_table_bytes": table_bytes,
        "record_store_bytes": store_bytes,
        "json_compat_index_bytes": index_bytes,
        "total_sidecar_bytes": table_bytes + store_bytes + index_bytes,
        "frozen_compaction_recommended": alias_count >= FROZEN_COMPACTION_ALIAS_THRESHOLD,
        "future_frozen_profile": "PTRHASH_OR_TPH_MPHF_SEGMENT",
    }


def _target_capacity(entry_count: int) -> int:
    capacity = DEFAULT_HASH_CAPACITY
    needed = max(1, int((entry_count / MAX_HASH_LOAD) + 1))
    while capacity < needed:
        capacity *= 2
    return capacity


def _hash_key(key: str) -> int:
    digest = hashlib.blake2b(key.encode("utf-8", errors="replace"), digest_size=8).digest()
    value = int.from_bytes(digest, "little")
    return value or 1


def _init_hash_table(path: Path, capacity: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(_HASH_HEADER.pack(_HASH_MAGIC, capacity, 0))
        chunk = _EMPTY_SLOT * 1024
        full, partial = divmod(capacity, 1024)
        for _ in range(full):
            handle.write(chunk)
        if partial:
            handle.write(_EMPTY_SLOT * partial)


def _read_hash_header(path: Path) -> tuple[int, int] | None:
    if not path.exists():
        return None
    try:
        with path.open("rb") as handle:
            raw = handle.read(_HASH_HEADER.size)
    except OSError:
        return None
    if len(raw) != _HASH_HEADER.size:
        return None
    magic, capacity, count = _HASH_HEADER.unpack(raw)
    if magic != _HASH_MAGIC or capacity <= 0:
        return None
    return capacity, count


def _slot_offset(slot: int) -> int:
    return _HASH_HEADER.size + slot * _HASH_SLOT.size


def _write_hash_count(handle: Any, capacity: int, count: int) -> None:
    handle.seek(0)
    handle.write(_HASH_HEADER.pack(_HASH_MAGIC, capacity, count))


def _record_matches_key(record: ST3GGRecallRecord, key: str) -> bool:
    return key in {record.pointer, record.dash_key, record.original_hash}


def _append_store_record(store_path: Path, record: ST3GGRecallRecord) -> tuple[int, int]:
    store_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record.to_jsonable(), sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
    with store_path.open("ab") as handle:
        offset = handle.tell()
        handle.write(line)
    return offset, len(line)


def _read_store_record(store_path: Path, offset: int, length: int) -> ST3GGRecallRecord | None:
    try:
        with store_path.open("rb") as handle:
            handle.seek(offset)
            raw = handle.read(length)
    except OSError:
        return None
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return ST3GGRecallRecord.from_jsonable(payload)


def _insert_hash_alias(
    table_path: Path,
    store_path: Path,
    *,
    key: str,
    record_offset: int,
    record_length: int,
) -> bool:
    header = _read_hash_header(table_path)
    if header is None:
        return False
    capacity, count = header
    key_hash = _hash_key(key)
    with table_path.open("r+b") as handle:
        start = key_hash % capacity
        for step in range(capacity):
            slot = (start + step) % capacity
            handle.seek(_slot_offset(slot))
            raw = handle.read(_HASH_SLOT.size)
            if len(raw) != _HASH_SLOT.size:
                return False
            stored_hash, stored_offset, stored_length, _flags = _HASH_SLOT.unpack(raw)
            if stored_hash == 0:
                handle.seek(_slot_offset(slot))
                handle.write(_HASH_SLOT.pack(key_hash, record_offset, record_length, 1))
                _write_hash_count(handle, capacity, count + 1)
                return True
            if stored_hash != key_hash:
                continue
            existing = _read_store_record(store_path, stored_offset, stored_length)
            if existing is not None and _record_matches_key(existing, key):
                handle.seek(_slot_offset(slot))
                handle.write(_HASH_SLOT.pack(key_hash, record_offset, record_length, 1))
                return True
    return False


def _lookup_hash_recall(key: str, *, ledger_path: str | Path) -> ST3GGRecallRecord | None:
    table_path = hash_table_path_for_ledger(ledger_path)
    store_path = store_path_for_ledger(ledger_path)
    header = _read_hash_header(table_path)
    if header is None or not store_path.exists():
        return None
    capacity, _count = header
    key_hash = _hash_key(key)
    try:
        with table_path.open("rb") as handle:
            start = key_hash % capacity
            for step in range(capacity):
                slot = (start + step) % capacity
                handle.seek(_slot_offset(slot))
                raw = handle.read(_HASH_SLOT.size)
                if len(raw) != _HASH_SLOT.size:
                    return None
                stored_hash, stored_offset, stored_length, _flags = _HASH_SLOT.unpack(raw)
                if stored_hash == 0:
                    return None
                if stored_hash != key_hash:
                    continue
                record = _read_store_record(store_path, stored_offset, stored_length)
                if record is not None and _record_matches_key(record, key):
                    return record
    except OSError:
        return None
    return None


def _rebuild_hash_sidecar(ledger_path: str | Path, records: list[dict[str, Any]]) -> None:
    live_records = [ST3GGRecallRecord.from_jsonable(record) for record in records if isinstance(record, dict)]
    alias_count = len(live_records) * 3
    table_path = hash_table_path_for_ledger(ledger_path)
    store_path = store_path_for_ledger(ledger_path)
    _init_hash_table(table_path, _target_capacity(alias_count))
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_bytes(b"")
    for record in live_records:
        offset, length = _append_store_record(store_path, record)
        for key in (record.pointer, record.original_hash, record.dash_key):
            _insert_hash_alias(table_path, store_path, key=key, record_offset=offset, record_length=length)


def _upsert_hash_sidecar(
    *,
    ledger_path: str | Path,
    record: ST3GGRecallRecord,
    records: list[dict[str, Any]],
) -> None:
    table_path = hash_table_path_for_ledger(ledger_path)
    store_path = store_path_for_ledger(ledger_path)
    header = _read_hash_header(table_path)
    if header is None:
        _init_hash_table(table_path, _target_capacity(max(3, len(records) * 3)))
        header = _read_hash_header(table_path)
    if header is None:
        return
    capacity, count = header
    if count + 3 > int(capacity * MAX_HASH_LOAD):
        _rebuild_hash_sidecar(ledger_path, records)
    offset, length = _append_store_record(store_path, record)
    for key in (record.pointer, record.original_hash, record.dash_key):
        if not _insert_hash_alias(table_path, store_path, key=key, record_offset=offset, record_length=length):
            _rebuild_hash_sidecar(ledger_path, records)
            return


def upsert_st3gg_recall(
    *,
    ledger_path: str | Path,
    original_hash: str,
    content_type: str,
    original: str,
    compressed: str = "",
    source_hint: str = "",
) -> ST3GGRecallRecord:
    pointer, dash_key, glyph, header = compile_st3gg_pointer(original, namespace=content_type.upper() or "CCR")
    record = ST3GGRecallRecord(
        pointer=pointer,
        dash_key=dash_key,
        glyph=glyph,
        holographic_header=header,
        original_hash=original_hash,
        content_type=content_type,
        source_hint=source_hint,
        created_unix=time.time(),
        original=original,
        compressed=compressed,
    )
    index_path = index_path_for_ledger(ledger_path)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _load_index(index_path)
    payload["records"][pointer] = record.to_jsonable()
    payload["aliases"][original_hash] = pointer
    payload["aliases"][dash_key] = pointer
    index_path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    try:
        _upsert_hash_sidecar(
            ledger_path=ledger_path,
            record=record,
            records=list(payload["records"].values()),
        )
    except OSError:
        pass
    return record


def lookup_st3gg_recall(
    key: str,
    *,
    ledger_path: str | Path,
) -> ST3GGRecallRecord | None:
    hash_hit = _lookup_hash_recall(key, ledger_path=ledger_path)
    if hash_hit is not None:
        return hash_hit
    payload = _load_index(index_path_for_ledger(ledger_path))
    pointer = key
    if key not in payload.get("records", {}):
        pointer = str(payload.get("aliases", {}).get(key, ""))
    record = payload.get("records", {}).get(pointer)
    if not isinstance(record, dict):
        return None
    return ST3GGRecallRecord.from_jsonable(record)


def rerank_st3gg_recall_candidates(
    query: str,
    records: list[ST3GGRecallRecord | dict[str, Any]],
    *,
    target_type: str = "st3gg_memory",
    ledger_path: str | Path | None = None,
    record: bool = False,
) -> dict[str, Any]:
    """Rank existing ST3GG recall records by downstream usefulness without changing storage."""
    candidates: list[DreamCandidate] = []
    for item in records:
        record_obj = item if isinstance(item, ST3GGRecallRecord) else ST3GGRecallRecord.from_jsonable(dict(item))
        candidates.append(
            DreamCandidate(
                candidate_id=record_obj.pointer,
                candidate_type=f"st3gg_{record_obj.content_type or 'memory'}",
                source=record_obj.source_hint or "ST3GG",
                content=record_obj.compressed or record_obj.original,
                semantic_score=0.68,
                truth_boundary="ST3GG pointer retrieves memory; DREAM only reranks usefulness",
                metadata={
                    "dash_key": record_obj.dash_key,
                    "glyph": record_obj.glyph,
                    "original_hash": record_obj.original_hash,
                    "content_type": record_obj.content_type,
                },
            )
        )
    return rerank_for_arena(
        query,
        candidates,
        target_type,
        arena_domain="memory",
        ledger_path=ledger_path or DREAM_LEDGER_PATH,
        record=record,
    )
