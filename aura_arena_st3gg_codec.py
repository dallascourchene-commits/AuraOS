"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xaa41-[Q-SYS:ARENA_ST3GG_EGRESS]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Visible Reversible Arena Egress)
DEPENDENCIES: __future__, dataclasses, hashlib, json, pathlib, typing, aura_st3gg_recall, aura_tokenizer_guard
FUNCTIONS: estimate_tokens, encode_arena_capsule_for_egress, retrieve_arena_capsule, should_st3gg_encode_arena_capsule
SYNOPSIS: Safe visible-ASCII ST3GG egress codec for Coding Arena capsules. Compact payloads are advisory recall handles only; exact spans, hashes, tests, and verifier gates remain patch authority.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
from typing import Any

from aura_st3gg_recall import (
    compile_st3gg_pointer,
    compile_visible_st3gg_capsule,
    lookup_st3gg_recall,
    upsert_st3gg_recall,
)

try:
    from aura_tokenizer_guard import sanitize_tokenizer_channels
except Exception:
    sanitize_tokenizer_channels = None  # type: ignore[assignment]


ARENA_ST3GG_CODEC_VERSION = "AURA_ARENA_ST3GG_CODEC_V1"
MIN_RAW_CHARS = 1200
MIN_SAVINGS_RATIO = 0.08
MAX_ROWS = 24
SAFE_MODE = "visible_ascii_recall_pointer"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
DEFAULT_RECALL_LEDGER = "st3gg_arena_recall.jsonl"


@dataclass(frozen=True)
class ArenaST3GGDecision:
    enabled: bool
    reason: str
    raw_tokens_est: int
    compact_tokens_est: int
    savings_ratio: float
    st3gg_pointer: str | None = None
    original_hash: str | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ArenaST3GGCapsule:
    capsule_version: str
    mode: str
    payload: str
    decision: ArenaST3GGDecision
    retrieval_marker: str | None
    original_hash: str | None
    phase_hash: str


def estimate_tokens(text: str) -> int:
    """Return Aura's local fallback token estimate.

    TODO: benchmark harnesses should replace this heuristic with provider-specific
    tokenizer counts or billing-log usage when those are available.
    """
    return max(1, len(str(text)) // 4)


def encode_arena_capsule_for_egress(
    capsule: dict[str, Any],
    *,
    namespace: str = "ARENA",
    min_raw_chars: int = MIN_RAW_CHARS,
    min_savings_ratio: float = MIN_SAVINGS_RATIO,
    max_rows: int = MAX_ROWS,
    recall_root: str | Path | None = None,
) -> ArenaST3GGCapsule:
    """Return a safe worker-facing ST3GG view plus local recall pointer."""
    prepared = _prepare_capsule(
        capsule,
        namespace=namespace,
        min_raw_chars=min_raw_chars,
        min_savings_ratio=min_savings_ratio,
        max_rows=max_rows,
    )
    decision: ArenaST3GGDecision = prepared["decision"]
    if not decision.enabled:
        return ArenaST3GGCapsule(
            capsule_version=ARENA_ST3GG_CODEC_VERSION,
            mode=SAFE_MODE,
            payload="",
            decision=decision,
            retrieval_marker=None,
            original_hash=decision.original_hash,
            phase_hash=_hash_payload(
                {
                    "version": ARENA_ST3GG_CODEC_VERSION,
                    "decision": decision,
                    "original_hash": decision.original_hash,
                }
            ),
        )

    original_json = str(prepared["original_json"])
    candidate_payload = str(prepared["payload"])
    original_hash = str(prepared["original_hash"])
    ledger_path = _recall_ledger_path(recall_root)
    record = upsert_st3gg_recall(
        ledger_path=ledger_path,
        original_hash=original_hash,
        content_type=_safe_namespace(namespace),
        original=original_json,
        compressed=candidate_payload,
        source_hint="coding_arena_st3gg_egress",
    )
    final_payload = _payload_with_recall(
        str(prepared["candidate"]),
        pointer=record.pointer,
        original_hash=original_hash,
        retrieval_marker=_retrieval_marker(original_hash),
    )
    final_payload, final_warnings = _sanitize_visible_ascii(final_payload)
    final_tokens = estimate_tokens(final_payload)
    raw_tokens = decision.raw_tokens_est
    final_savings = _savings_ratio(raw_tokens, final_tokens)
    if final_savings < min_savings_ratio:
        disabled = ArenaST3GGDecision(
            enabled=False,
            reason="below_savings_threshold",
            raw_tokens_est=raw_tokens,
            compact_tokens_est=final_tokens,
            savings_ratio=final_savings,
            st3gg_pointer=None,
            original_hash=original_hash,
            warnings=_unique((*decision.warnings, *final_warnings, "pointer_overhead_erased_savings")),
        )
        return ArenaST3GGCapsule(
            capsule_version=ARENA_ST3GG_CODEC_VERSION,
            mode=SAFE_MODE,
            payload="",
            decision=disabled,
            retrieval_marker=None,
            original_hash=original_hash,
            phase_hash=_hash_payload({"decision": disabled, "original_hash": original_hash}),
        )

    enabled = replace(
        decision,
        compact_tokens_est=final_tokens,
        savings_ratio=final_savings,
        st3gg_pointer=record.pointer,
        warnings=_unique((*decision.warnings, *final_warnings)),
    )
    return ArenaST3GGCapsule(
        capsule_version=ARENA_ST3GG_CODEC_VERSION,
        mode=SAFE_MODE,
        payload=final_payload,
        decision=enabled,
        retrieval_marker=_retrieval_marker(original_hash),
        original_hash=original_hash,
        phase_hash=_hash_payload(
            {
                "version": ARENA_ST3GG_CODEC_VERSION,
                "mode": SAFE_MODE,
                "payload": final_payload,
                "original_hash": original_hash,
                "decision": enabled,
            }
        ),
    )


def retrieve_arena_capsule(
    pointer_or_hash: str,
    *,
    recall_root: str | Path | None = None,
) -> dict[str, Any] | None:
    """Recover the exact original Coding Arena capsule from local ST3GG recall."""
    key = str(pointer_or_hash or "").strip()
    if key.startswith("<<aura_arena_st3gg:") and key.endswith(">>"):
        key = key[len("<<aura_arena_st3gg:") : -2]
    if not key:
        return None
    try:
        record = lookup_st3gg_recall(key, ledger_path=_recall_ledger_path(recall_root))
    except Exception:
        return None
    if record is None:
        return None
    try:
        restored = json.loads(record.original)
    except (TypeError, json.JSONDecodeError):
        return None
    return restored if isinstance(restored, dict) else None


def should_st3gg_encode_arena_capsule(
    capsule: dict[str, Any],
    *,
    min_raw_chars: int = MIN_RAW_CHARS,
    min_savings_ratio: float = MIN_SAVINGS_RATIO,
) -> ArenaST3GGDecision:
    """Return the egress decision without writing recall sidecars."""
    prepared = _prepare_capsule(
        capsule,
        namespace="ARENA",
        min_raw_chars=min_raw_chars,
        min_savings_ratio=min_savings_ratio,
        max_rows=MAX_ROWS,
    )
    return prepared["decision"]


def _prepare_capsule(
    capsule: dict[str, Any],
    *,
    namespace: str,
    min_raw_chars: int,
    min_savings_ratio: float,
    max_rows: int,
) -> dict[str, Any]:
    capsule_copy = _defensive_json_copy(capsule)
    original_json = json.dumps(capsule_copy, sort_keys=True, separators=(",", ":"), default=str)
    original_hash = _hash_text(original_json)
    raw_tokens = estimate_tokens(original_json)
    warnings: list[str] = []
    candidate_source, source_warnings = _sanitize_json_strings(capsule_copy)
    warnings.extend(source_warnings)

    candidates = _candidate_visible_capsules(candidate_source, max_rows=max_rows)
    if not candidates:
        return {
            "decision": ArenaST3GGDecision(
                enabled=False,
                reason="no_compact_candidate",
                raw_tokens_est=raw_tokens,
                compact_tokens_est=raw_tokens,
                savings_ratio=0.0,
                original_hash=original_hash,
            ),
            "original_json": original_json,
            "original_hash": original_hash,
            "payload": "",
            "candidate": "",
        }

    pointer_hint, _, _, _ = compile_st3gg_pointer(original_json, namespace=_safe_namespace(namespace))
    marker = _retrieval_marker(original_hash)
    payload_candidates: list[tuple[str, int, tuple[str, ...], str]] = []
    for candidate in candidates:
        visible, candidate_warnings = _sanitize_visible_ascii(candidate)
        payload = _payload_with_recall(
            visible,
            pointer=pointer_hint,
            original_hash=original_hash,
            retrieval_marker=marker,
        )
        payload, payload_warnings = _sanitize_visible_ascii(payload)
        payload_candidates.append(
            (
                payload,
                estimate_tokens(payload),
                _unique((*candidate_warnings, *payload_warnings)),
                visible,
            )
        )

    payload, compact_tokens, payload_warnings, visible_candidate = min(payload_candidates, key=lambda item: (item[1], len(item[0])))
    warnings.extend(payload_warnings)
    savings_ratio = _savings_ratio(raw_tokens, compact_tokens)
    enabled = len(original_json) >= min_raw_chars and savings_ratio >= min_savings_ratio
    if len(original_json) < min_raw_chars:
        reason = "below_min_raw_chars"
    elif compact_tokens >= raw_tokens:
        reason = "compact_not_smaller"
    elif savings_ratio < min_savings_ratio:
        reason = "below_savings_threshold"
    else:
        reason = "savings_threshold_met"
    decision = ArenaST3GGDecision(
        enabled=enabled,
        reason=reason,
        raw_tokens_est=raw_tokens,
        compact_tokens_est=compact_tokens,
        savings_ratio=savings_ratio,
        st3gg_pointer=None,
        original_hash=original_hash,
        warnings=tuple(warnings),
    )
    return {
        "decision": decision,
        "original_json": original_json,
        "original_hash": original_hash,
        "payload": payload,
        "candidate": visible_candidate,
    }


def _candidate_visible_capsules(capsule: dict[str, Any], *, max_rows: int) -> list[str]:
    candidates: list[str] = []
    for item in (
        capsule,
        capsule.get("context") if isinstance(capsule.get("context"), dict) else None,
        _selected_subset(capsule),
    ):
        if item:
            candidate = compile_visible_st3gg_capsule(item, max_rows=max_rows)
            if candidate:
                candidates.append(candidate)
    return _unique(candidates)


def _selected_subset(capsule: dict[str, Any]) -> dict[str, Any]:
    jspace_state = capsule.get("jspace_state") if isinstance(capsule.get("jspace_state"), dict) else {}
    subset = {
        "capsule_version": capsule.get("capsule_version"),
        "op": capsule.get("op"),
        "selected": capsule.get("selected"),
        "context": capsule.get("context"),
        "route_decision": capsule.get("route_decision"),
        "jspace_packet": capsule.get("jspace_packet"),
        "jspace_next_state": jspace_state.get("next_state"),
        "phase_hash": capsule.get("phase_hash"),
    }
    return {key: value for key, value in subset.items() if value not in (None, "", [], {})}


def _payload_with_recall(candidate: str, *, pointer: str, original_hash: str, retrieval_marker: str) -> str:
    return (
        f"{candidate}|PTR={pointer}|HASH={original_hash}|MARK={retrieval_marker}|"
        f"AUTH={PATCH_AUTHORITY}|VSA_AUTH=false"
    )


def _defensive_json_copy(capsule: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(capsule, dict):
        capsule = {"value": capsule}
    encoded = json.dumps(capsule, sort_keys=True, separators=(",", ":"), default=str)
    decoded = json.loads(encoded)
    return decoded if isinstance(decoded, dict) else {"value": decoded}


def _sanitize_json_strings(value: Any) -> tuple[Any, tuple[str, ...]]:
    warnings: list[str] = []
    if isinstance(value, dict):
        output: dict[str, Any] = {}
        for key, item in value.items():
            safe_key, key_warnings = _sanitize_visible_ascii(str(key))
            safe_item, item_warnings = _sanitize_json_strings(item)
            output[safe_key] = safe_item
            warnings.extend(key_warnings)
            warnings.extend(item_warnings)
        return output, _unique(warnings)
    if isinstance(value, list):
        output_list = []
        for item in value:
            safe_item, item_warnings = _sanitize_json_strings(item)
            output_list.append(safe_item)
            warnings.extend(item_warnings)
        return output_list, _unique(warnings)
    if isinstance(value, str):
        return _sanitize_visible_ascii(value)
    return value, ()


def _sanitize_visible_ascii(text: str) -> tuple[str, tuple[str, ...]]:
    warnings: list[str] = []
    visible = str(text or "")
    if sanitize_tokenizer_channels is not None:
        report = sanitize_tokenizer_channels(visible)
        visible = report.sanitized_text
        warnings.extend(report.warnings())
    if not visible.isascii():
        visible = visible.encode("ascii", errors="backslashreplace").decode("ascii")
        warnings.append("non_ascii_escaped")
    cleaned = []
    stripped_controls = 0
    for ch in visible:
        codepoint = ord(ch)
        if 32 <= codepoint <= 126:
            cleaned.append(ch)
        elif ch in "\t\n\r":
            cleaned.append(" ")
            stripped_controls += 1
        else:
            stripped_controls += 1
    if stripped_controls:
        warnings.append(f"ascii_control_stripped:{stripped_controls}")
    return "".join(cleaned).strip(), tuple(warnings)


def _recall_ledger_path(recall_root: str | Path | None) -> Path:
    if recall_root is None:
        root = Path("Aura_Memory")
    else:
        root = Path(recall_root)
    if root.suffix == ".jsonl":
        return root
    if root.name == "Aura_Memory":
        return root / DEFAULT_RECALL_LEDGER
    return root / "Aura_Memory" / DEFAULT_RECALL_LEDGER


def _retrieval_marker(original_hash: str) -> str:
    return f"<<aura_arena_st3gg:{original_hash}>>"


def _safe_namespace(namespace: str) -> str:
    safe = "".join(ch if ch.isascii() and (ch.isalnum() or ch in "_-") else "_" for ch in str(namespace or "ARENA"))
    return safe.upper() or "ARENA"


def _savings_ratio(raw_tokens: int, compact_tokens: int) -> float:
    if compact_tokens >= raw_tokens:
        return 0.0
    return round((raw_tokens - compact_tokens) / max(1, raw_tokens), 4)


def _hash_text(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8", errors="replace")).hexdigest()


def _hash_payload(payload: Any) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8", errors="replace"), digest_size=16).hexdigest()


def _unique(values: Any) -> tuple[Any, ...]:
    seen: set[str] = set()
    output: list[Any] = []
    for value in values:
        if value in (None, ""):
            continue
        key = repr(value)
        if key in seen:
            continue
        seen.add(key)
        output.append(value)
    return tuple(output)
