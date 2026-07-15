"""P5.3 exact-recall persistence binding and adversarial dual-read verification."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Callable

from aura_arena_st3gg_egress import EGRESS_VERSION
from aura_st3gg_contracts import (
    ST3GGExactRecallRecord,
    ST3GGRestorationMode,
    canonical_json_bytes,
    canonical_pointer,
    count_utf8_bytes,
    digest_text,
    verify_exact_recall_record,
)
from aura_st3gg_recall import (
    ST3GG_RECALL_VERSION,
    ST3GGRecallRecord,
    compile_st3gg_pointer,
    index_path_for_ledger,
    lookup_st3gg_recall,
    upsert_st3gg_recall,
)
from aura_st3gg_compatibility_types import (
    ST3GGCanonicalBinding,
    ST3GGCompatibilityError,
    ST3GGRecallDualReadEvidence,
    require,
)

_V1_POINTER_RE = re.compile(r"^ST3GG-L2::[A-Z0-9_-]+:[0-9A-F]{4}:[0-9a-f]{16}$")
_DASH_RE = re.compile(r"^[0-9a-f]{16}$")
_GLYPH_RE = re.compile(r"^[0-9A-F]{4}$")
_HEADER_RE = re.compile(r"^[A-Za-z0-9_-]{64}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

LookupRecall = Callable[..., ST3GGRecallRecord | None]
UpsertRecall = Callable[..., ST3GGRecallRecord]


def dual_read_st3gg_recall(
    binding: ST3GGCanonicalBinding,
    *,
    ledger_path: str | Path,
    expected_original: str | None = None,
    expected_compact: str | None = None,
    lookup_record: LookupRecall = lookup_st3gg_recall,
) -> ST3GGRecallDualReadEvidence:
    if not isinstance(binding, ST3GGCanonicalBinding):
        raise TypeError("dual_read_binding_must_be_canonical_binding")
    try:
        payload = _strict_index(ledger_path)
        records, aliases = payload["records"], payload["aliases"]
        require(
            aliases.get(binding.original_digest) == binding.legacy_recall_pointer,
            "legacy_json_digest_alias_disagreement",
        )
        require(
            aliases.get(binding.legacy_dash_key) == binding.legacy_recall_pointer,
            "legacy_json_dash_alias_disagreement",
        )
        direct = _strict_record(records.get(binding.legacy_recall_pointer))
        identity = _record_dict(direct)
        reads: list[tuple[str, ST3GGRecallRecord]] = []
        for name, key in (
            ("pointer", binding.legacy_recall_pointer),
            ("digest", binding.original_digest),
            ("dash_key", binding.legacy_dash_key),
        ):
            record = lookup_record(key, ledger_path=ledger_path)
            require(isinstance(record, ST3GGRecallRecord), f"legacy_{name}_read_missing")
            require(_record_dict(record) == identity, f"legacy_{name}_record_substitution")
            reads.append((name, record))
        matching = []
        for key, raw_record in records.items():
            record = _strict_record(raw_record)
            if (
                record.pointer == binding.legacy_recall_pointer
                or record.original_hash == binding.original_digest
                or record.dash_key == binding.legacy_dash_key
            ):
                matching.append(key)
        require(matching == [binding.legacy_recall_pointer], "legacy_duplicate_or_conflicting_records")
        _verify_record(direct, binding, expected_original, expected_compact)
        exact = ST3GGExactRecallRecord(
            binding.namespace,
            binding.exact_ref,
            binding.original_digest,
            binding.original_bytes,
            binding.content_type,
            binding.source_hint,
            direct.original,
        )
        verify_exact_recall_record(exact)
        return ST3GGRecallDualReadEvidence(
            True,
            ST3GGRestorationMode.EXACT_RECALL,
            binding,
            direct.pointer,
            direct.original_hash,
            direct.content_type,
            count_utf8_bytes(direct.original),
            digest_text(direct.compressed) if direct.compressed else None,
            tuple((name, _record_digest(record)) for name, record in reads),
            _record_digest(direct),
        )
    except Exception as exc:
        return ST3GGRecallDualReadEvidence(
            False,
            ST3GGRestorationMode.NONE,
            binding,
            mismatch_reasons=(_reason(exc, "dual_read_verification_failed"),),
        )


def persist_report_exact_to_v1(
    exact: ST3GGExactRecallRecord,
    compact: str,
    surface_pointer: str,
    ledger_path: str | Path,
    lookup: LookupRecall = lookup_st3gg_recall,
    upsert: UpsertRecall = upsert_st3gg_recall,
) -> tuple[ST3GGCanonicalBinding, ST3GGRecallDualReadEvidence]:
    verify_exact_recall_record(exact)
    record = _existing_digest_record(ledger_path, exact.original_digest)
    if record is None:
        record = upsert(
            ledger_path=ledger_path,
            original_hash=exact.original_digest,
            content_type=exact.content_type,
            original=exact.original,
            compressed=compact,
            source_hint=exact.source_hint,
        )
    else:
        require(record.original == exact.original, "existing_digest_record_original_conflict")
        require(record.content_type == exact.content_type, "existing_digest_record_content_type_conflict")
        require(record.source_hint == exact.source_hint, "existing_digest_record_source_hint_conflict")
        require(record.compressed == compact, "existing_digest_record_compact_conflict")
    require(isinstance(record, ST3GGRecallRecord), "v1_persistence_record_type_invalid")
    binding = ST3GGCanonicalBinding(
        exact.namespace,
        canonical_pointer(exact.namespace, exact.original_digest),
        exact.exact_ref,
        exact.original_digest,
        exact.original_bytes,
        exact.content_type,
        exact.source_hint,
        record.pointer,
        record.dash_key,
        record.glyph,
        record.holographic_header,
        EGRESS_VERSION,
        surface_pointer,
    )
    evidence = dual_read_st3gg_recall(
        binding,
        ledger_path=ledger_path,
        expected_original=exact.original,
        expected_compact=compact,
        lookup_record=lookup,
    )
    require(evidence.verified, "v1_persistence_dual_read_failed")
    return binding, evidence


def _existing_digest_record(ledger_path: str | Path, digest: str) -> ST3GGRecallRecord | None:
    if not index_path_for_ledger(ledger_path).exists():
        return None
    payload = _strict_index(ledger_path)
    pointer = payload["aliases"].get(digest)
    matches = [
        _strict_record(item)
        for item in payload["records"].values()
        if isinstance(item, dict) and item.get("original_hash") == digest
    ]
    if pointer is None:
        require(not matches, "existing_digest_record_missing_alias")
        return None
    require(len(matches) == 1, "existing_digest_duplicate_or_conflict")
    return _strict_record(payload["records"].get(pointer))


def _strict_index(ledger_path: str | Path) -> dict[str, Any]:
    path = index_path_for_ledger(ledger_path)
    require(path.exists(), "legacy_json_index_missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ST3GGCompatibilityError("legacy_json_index_unreadable") from exc
    except json.JSONDecodeError as exc:
        raise ST3GGCompatibilityError("legacy_json_index_malformed") from exc
    require(
        isinstance(payload, dict) and payload.get("version") == ST3GG_RECALL_VERSION,
        "legacy_json_index_version_mismatch",
    )
    require(
        isinstance(payload.get("records"), dict) and isinstance(payload.get("aliases"), dict),
        "legacy_json_index_shape_invalid",
    )
    return payload


def _strict_record(payload: Any) -> ST3GGRecallRecord:
    require(isinstance(payload, dict), "legacy_json_pointer_record_missing")
    require(payload.get("version") == ST3GG_RECALL_VERSION, "legacy_record_version_mismatch")
    for name in (
        "pointer",
        "dash_key",
        "glyph",
        "holographic_header",
        "original_hash",
        "content_type",
        "source_hint",
        "original",
        "compressed",
    ):
        require(type(payload.get(name)) is str, f"legacy_record_{name}_type_invalid")
    created = payload.get("created_unix")
    require(
        type(created) in {int, float}
        and not isinstance(created, bool)
        and math.isfinite(float(created))
        and created >= 0,
        "legacy_record_created_unix_invalid",
    )
    record = ST3GGRecallRecord.from_jsonable(payload)
    require(_V1_POINTER_RE.fullmatch(record.pointer) is not None, "legacy_record_pointer_malformed")
    require(_DASH_RE.fullmatch(record.dash_key) is not None, "legacy_record_dash_key_malformed")
    require(_GLYPH_RE.fullmatch(record.glyph) is not None, "legacy_record_glyph_malformed")
    require(_HEADER_RE.fullmatch(record.holographic_header) is not None, "legacy_record_holographic_header_malformed")
    require(_SHA256_RE.fullmatch(record.original_hash) is not None, "legacy_record_digest_invalid")
    require(bool(record.content_type.strip()), "legacy_record_content_type_required")
    return record


def _verify_record(
    record: ST3GGRecallRecord,
    binding: ST3GGCanonicalBinding,
    expected_original: str | None,
    expected_compact: str | None,
) -> None:
    require(record.pointer == binding.legacy_recall_pointer, "legacy_record_pointer_disagreement")
    require(record.dash_key == binding.legacy_dash_key, "legacy_record_dash_key_disagreement")
    require(record.glyph == binding.legacy_glyph, "legacy_record_glyph_disagreement")
    require(
        record.holographic_header == binding.legacy_holographic_header,
        "legacy_record_holographic_header_disagreement",
    )
    require(record.original_hash == binding.original_digest, "legacy_record_digest_disagreement")
    require(record.content_type == binding.content_type, "legacy_record_content_type_disagreement")
    require(record.source_hint == binding.source_hint, "legacy_record_source_hint_disagreement")
    require(digest_text(record.original) == binding.original_digest, "legacy_record_original_digest_mismatch")
    require(count_utf8_bytes(record.original) == binding.original_bytes, "legacy_record_original_length_mismatch")
    if expected_original is not None:
        require(record.original == expected_original, "legacy_record_exact_original_disagreement")
    if expected_compact is not None:
        require(record.compressed == expected_compact, "legacy_record_compact_disagreement")
    identity = compile_st3gg_pointer(record.original, namespace=record.content_type.upper() or "CCR")
    require(
        (record.pointer, record.dash_key, record.glyph, record.holographic_header) == identity,
        "legacy_record_identity_not_derived",
    )


def _record_dict(record: ST3GGRecallRecord) -> dict[str, Any]:
    return {
        "version": ST3GG_RECALL_VERSION,
        "pointer": record.pointer,
        "dash_key": record.dash_key,
        "glyph": record.glyph,
        "holographic_header": record.holographic_header,
        "original_hash": record.original_hash,
        "content_type": record.content_type,
        "source_hint": record.source_hint,
        "original": record.original,
        "compressed": record.compressed,
    }


def _record_digest(record: ST3GGRecallRecord) -> str:
    return hashlib.sha256(canonical_json_bytes(_record_dict(record))).hexdigest()


def _reason(exc: Exception, fallback: str) -> str:
    return str(exc) if isinstance(exc, ST3GGCompatibilityError) and str(exc) else f"{fallback}:{type(exc).__name__}"
