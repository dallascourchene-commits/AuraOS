"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xab51-[Q-SYS:CANONICAL_ST3GG_CONTRACTS]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Measured Exact-Recall Compression)
DEPENDENCIES: __future__, dataclasses, enum, hashlib, json, re, typing, urllib.parse
FUNCTIONS: canonical_json_bytes, digest_text, canonical_pointer, parse_canonical_pointer,
exact_ref_for, sanitize_visible_ascii, count_utf8_bytes, prepare_st3gg_artifact,
verify_exact_recall_record, adapt_legacy_arena_decision, adapt_legacy_ast_frame,
adapt_legacy_report_result
SYNOPSIS: Canonical proposal-only ST3GG decision, pointer, exact-recall, and savings contracts.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import json
import math
import re
from typing import Any, Callable, Mapping
from urllib.parse import quote

ST3GG_CONTRACT_VERSION = "AURA_ST3GG_CONTRACT_V2"
ST3GG_POINTER_VERSION = "ST3GG2"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
PROPOSAL_ONLY = True

_POINTER_RE = re.compile(r"^ST3GG2::([A-Z0-9_-]{1,32}):([0-9a-f]{32})$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_EXACT_REF_RE = re.compile(r"^aura://st3gg/v2/[A-Z0-9_-]{1,32}/[0-9a-f]{64}$")


class ST3GGMeasurementClass(str, Enum):
    PROVIDER_MEASURED = "PROVIDER_MEASURED"
    TOKENIZER_EXACT = "TOKENIZER_EXACT"
    TOKEN_ESTIMATE = "TOKEN_ESTIMATE"
    BYTE_EXACT = "BYTE_EXACT"


class ST3GGRestorationMode(str, Enum):
    NONE = "NONE"
    LOSSY_ADVISORY = "LOSSY_ADVISORY"
    EXACT_RECALL = "EXACT_RECALL"


@dataclass(frozen=True)
class ST3GGSavingsPolicy:
    minimum_savings_ratio: float = 0.08
    minimum_raw_units: int = 1
    measurement_class: ST3GGMeasurementClass = ST3GGMeasurementClass.BYTE_EXACT

    def __post_init__(self) -> None:
        if type(self.minimum_savings_ratio) is not float:
            raise TypeError("minimum_savings_ratio_must_be_float")
        if not math.isfinite(self.minimum_savings_ratio):
            raise ValueError("minimum_savings_ratio_must_be_finite")
        if not 0.0 <= self.minimum_savings_ratio <= 1.0:
            raise ValueError("minimum_savings_ratio_out_of_range")
        if type(self.minimum_raw_units) is not int:
            raise TypeError("minimum_raw_units_must_be_int")
        if self.minimum_raw_units < 0:
            raise ValueError("minimum_raw_units_must_be_nonnegative")
        if not isinstance(self.measurement_class, ST3GGMeasurementClass):
            raise TypeError("measurement_class_must_be_enum")


@dataclass(frozen=True)
class ST3GGExactRecallRecord:
    namespace: str
    exact_ref: str
    original_digest: str
    original_bytes: int
    content_type: str
    source_hint: str
    original: str

    def __post_init__(self) -> None:
        namespace = _normalize_namespace(self.namespace)
        if namespace != self.namespace:
            raise ValueError("namespace_not_canonical")
        if not _EXACT_REF_RE.fullmatch(self.exact_ref):
            raise ValueError("exact_ref_not_canonical")
        if not _DIGEST_RE.fullmatch(self.original_digest):
            raise ValueError("original_digest_invalid")
        if type(self.original_bytes) is not int or self.original_bytes < 0:
            raise ValueError("original_bytes_invalid")
        if type(self.original) is not str:
            raise TypeError("original_must_be_string")
        if type(self.content_type) is not str or not self.content_type.strip():
            raise ValueError("content_type_required")
        if type(self.source_hint) is not str:
            raise TypeError("source_hint_must_be_string")
        verify_exact_recall_record(self)

    def sidecar_dict(self) -> dict[str, Any]:
        return {
            "version": ST3GG_CONTRACT_VERSION,
            "namespace": self.namespace,
            "exact_ref": self.exact_ref,
            "original_digest": self.original_digest,
            "original_bytes": self.original_bytes,
            "content_type": self.content_type,
            "source_hint": self.source_hint,
            "original": self.original,
        }


@dataclass(frozen=True)
class ST3GGDecision:
    enabled: bool
    reason: str
    namespace: str
    measurement_class: ST3GGMeasurementClass
    raw_units: int
    candidate_units: int
    final_units: int
    overhead_units: int
    savings_ratio: float
    minimum_savings_ratio: float
    restoration_mode: ST3GGRestorationMode
    original_digest: str
    compact_digest: str | None = None
    pointer: str | None = None
    exact_ref: str | None = None
    warnings: tuple[str, ...] = ()
    legacy_surface: str | None = None
    legacy_pointer: str | None = None
    version: str = ST3GG_CONTRACT_VERSION
    proposal_only: bool = PROPOSAL_ONLY
    patch_authority: str = PATCH_AUTHORITY
    st3gg_patch_authority: bool = False

    def __post_init__(self) -> None:
        if type(self.enabled) is not bool:
            raise TypeError("enabled_must_be_bool")
        if self.version != ST3GG_CONTRACT_VERSION:
            raise ValueError("unsupported_st3gg_contract_version")
        if self.proposal_only is not True:
            raise ValueError("st3gg_must_remain_proposal_only")
        if self.patch_authority != PATCH_AUTHORITY or self.st3gg_patch_authority is not False:
            raise ValueError("st3gg_cannot_gain_patch_authority")
        if _normalize_namespace(self.namespace) != self.namespace:
            raise ValueError("namespace_not_canonical")
        if not isinstance(self.measurement_class, ST3GGMeasurementClass):
            raise TypeError("measurement_class_must_be_enum")
        if not isinstance(self.restoration_mode, ST3GGRestorationMode):
            raise TypeError("restoration_mode_must_be_enum")
        for name, value in (
            ("raw_units", self.raw_units),
            ("candidate_units", self.candidate_units),
            ("final_units", self.final_units),
            ("overhead_units", self.overhead_units),
        ):
            if type(value) is not int or value < 0:
                raise ValueError(f"{name}_invalid")
        for name, value in (
            ("savings_ratio", self.savings_ratio),
            ("minimum_savings_ratio", self.minimum_savings_ratio),
        ):
            if type(value) is not float or not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name}_invalid")
        if self.final_units != self.candidate_units + self.overhead_units:
            raise ValueError("final_units_do_not_match_candidate_plus_overhead")
        if self.savings_ratio != _ratio(self.raw_units, self.final_units):
            raise ValueError("savings_ratio_not_derived_from_final_units")
        if not _DIGEST_RE.fullmatch(self.original_digest):
            raise ValueError("original_digest_invalid")
        if self.compact_digest is not None and not _DIGEST_RE.fullmatch(self.compact_digest):
            raise ValueError("compact_digest_invalid")
        if self.pointer is not None:
            parse_canonical_pointer(self.pointer)
            if self.pointer != canonical_pointer(self.namespace, self.original_digest):
                raise ValueError("pointer_digest_mismatch")
        if self.exact_ref is not None:
            if not _EXACT_REF_RE.fullmatch(self.exact_ref):
                raise ValueError("exact_ref_not_canonical")
            if self.exact_ref != exact_ref_for(self.namespace, self.original_digest):
                raise ValueError("exact_ref_digest_mismatch")
        if self.enabled:
            if self.candidate_units == 0:
                raise ValueError("enabled_artifact_empty_candidate")
            if self.final_units >= self.raw_units:
                raise ValueError("enabled_artifact_must_be_smaller")
            if self.savings_ratio < self.minimum_savings_ratio:
                raise ValueError("enabled_artifact_below_savings_threshold")
            if not self.pointer or not self.compact_digest:
                raise ValueError("enabled_artifact_missing_pointer_or_digest")
            if self.restoration_mode is ST3GGRestorationMode.EXACT_RECALL and not self.exact_ref:
                raise ValueError("exact_recall_requires_exact_ref")
        if self.restoration_mode is ST3GGRestorationMode.EXACT_RECALL and not self.exact_ref:
            raise ValueError("exact_recall_requires_exact_ref")
        if self.restoration_mode is ST3GGRestorationMode.LOSSY_ADVISORY and self.exact_ref is not None:
            raise ValueError("lossy_advisory_cannot_claim_exact_ref")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["measurement_class"] = self.measurement_class.value
        payload["restoration_mode"] = self.restoration_mode.value
        payload["warnings"] = list(self.warnings)
        return payload

    @property
    def decision_digest(self) -> str:
        return hashlib.blake2b(canonical_json_bytes(self.to_dict()), digest_size=16).hexdigest()


@dataclass(frozen=True)
class ST3GGPreparedArtifact:
    payload: str
    decision: ST3GGDecision
    persistence_receipt: Mapping[str, Any] | None = field(default=None, compare=False)


PersistExact = Callable[[ST3GGExactRecallRecord], Mapping[str, Any] | None]
CountUnits = Callable[[str], int]


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def digest_text(text: str) -> str:
    if type(text) is not str:
        raise TypeError("text_must_be_string")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize_namespace(namespace: str) -> str:
    if type(namespace) is not str:
        raise TypeError("namespace_must_be_string")
    safe = "".join(ch if ch.isascii() and (ch.isalnum() or ch in "_-") else "_" for ch in namespace.upper())
    safe = safe[:32]
    return safe or "ST3GG"


def canonical_pointer(namespace: str, original_digest: str) -> str:
    safe = _normalize_namespace(namespace)
    if not _DIGEST_RE.fullmatch(original_digest):
        raise ValueError("original_digest_invalid")
    material = canonical_json_bytes(
        {
            "version": ST3GG_POINTER_VERSION,
            "namespace": safe,
            "original_digest": original_digest,
        }
    )
    pointer_digest = hashlib.blake2b(material, digest_size=16).hexdigest()
    return f"ST3GG2::{safe}:{pointer_digest}"


def parse_canonical_pointer(pointer: str) -> tuple[str, str]:
    if type(pointer) is not str:
        raise TypeError("pointer_must_be_string")
    match = _POINTER_RE.fullmatch(pointer)
    if not match:
        raise ValueError("pointer_not_canonical")
    return match.group(1), match.group(2)


def exact_ref_for(namespace: str, original_digest: str) -> str:
    safe = _normalize_namespace(namespace)
    if not _DIGEST_RE.fullmatch(original_digest):
        raise ValueError("original_digest_invalid")
    return f"aura://st3gg/v2/{safe}/{original_digest}"


def sanitize_visible_ascii(text: str) -> tuple[str, tuple[str, ...]]:
    if type(text) is not str:
        raise TypeError("compact_candidate_must_be_string")
    warnings: list[str] = []
    visible = text
    try:
        from aura_tokenizer_guard import sanitize_tokenizer_channels
    except Exception:
        sanitize_tokenizer_channels = None
    if sanitize_tokenizer_channels is not None:
        report = sanitize_tokenizer_channels(visible)
        visible = report.sanitized_text
        warnings.extend(str(item) for item in report.warnings())
    if not visible.isascii():
        visible = visible.encode("ascii", errors="backslashreplace").decode("ascii")
        warnings.append("non_ascii_escaped")
    cleaned: list[str] = []
    stripped = 0
    for char in visible:
        codepoint = ord(char)
        if 32 <= codepoint <= 126:
            cleaned.append(char)
        elif char in "\t\r\n":
            cleaned.append(" ")
            stripped += 1
        else:
            stripped += 1
    if stripped:
        warnings.append(f"ascii_control_stripped:{stripped}")
    return "".join(cleaned).strip(), _unique(warnings)


def count_utf8_bytes(text: str) -> int:
    if type(text) is not str:
        raise TypeError("text_must_be_string")
    return len(text.encode("utf-8"))


def verify_exact_recall_record(record: ST3GGExactRecallRecord) -> None:
    if digest_text(record.original) != record.original_digest:
        raise ValueError("exact_recall_digest_mismatch")
    if count_utf8_bytes(record.original) != record.original_bytes:
        raise ValueError("exact_recall_length_mismatch")
    expected_ref = exact_ref_for(record.namespace, record.original_digest)
    if record.exact_ref != expected_ref:
        raise ValueError("exact_recall_ref_mismatch")


def _ratio(raw_units: int, final_units: int) -> float:
    if raw_units <= 0 or final_units >= raw_units:
        return 0.0
    return round((raw_units - final_units) / raw_units, 6)


def _metadata_suffix(
    *,
    pointer: str,
    original_digest: str,
    exact_ref: str,
    measurement_class: ST3GGMeasurementClass,
) -> str:
    encoded_ref = quote(exact_ref, safe=":/")
    return (
        f"|PTR={pointer}|HASH={original_digest}|REF={encoded_ref}|"
        f"RESTORE={ST3GGRestorationMode.EXACT_RECALL.value}|"
        f"MEASURE={measurement_class.value}|AUTH={PATCH_AUTHORITY}|ST3GG_AUTH=false"
    )


def prepare_st3gg_artifact(
    original: str,
    compact_candidate: str,
    *,
    namespace: str,
    content_type: str,
    source_hint: str = "",
    policy: ST3GGSavingsPolicy | None = None,
    count_units: CountUnits = count_utf8_bytes,
    persist_exact: PersistExact | None = None,
) -> ST3GGPreparedArtifact:
    if type(original) is not str:
        raise TypeError("original_must_be_string")
    if type(content_type) is not str or not content_type.strip():
        raise ValueError("content_type_required")
    if type(source_hint) is not str:
        raise TypeError("source_hint_must_be_string")
    active_policy = policy or ST3GGSavingsPolicy()
    if not isinstance(active_policy, ST3GGSavingsPolicy):
        raise TypeError("policy_must_be_st3gg_savings_policy")
    if not callable(count_units):
        raise TypeError("count_units_must_be_callable")

    safe_namespace = _normalize_namespace(namespace)
    original_digest = digest_text(original)
    exact_ref = exact_ref_for(safe_namespace, original_digest)
    pointer = canonical_pointer(safe_namespace, original_digest)
    visible_candidate, warnings = sanitize_visible_ascii(compact_candidate)

    raw_units = count_units(original)
    candidate_units = count_units(visible_candidate)
    suffix = _metadata_suffix(
        pointer=pointer,
        original_digest=original_digest,
        exact_ref=exact_ref,
        measurement_class=active_policy.measurement_class,
    )
    payload = visible_candidate + suffix if visible_candidate else ""
    final_units = count_units(payload) if payload else 0
    overhead_units = max(0, final_units - candidate_units)
    savings_ratio = _ratio(raw_units, final_units)

    reason = "savings_threshold_met"
    enabled = True
    if not visible_candidate:
        enabled = False
        reason = "empty_compact_candidate"
    elif raw_units < active_policy.minimum_raw_units:
        enabled = False
        reason = "below_minimum_raw_units"
    elif final_units >= raw_units:
        enabled = False
        reason = "protocol_overhead_erased_savings"
    elif savings_ratio < active_policy.minimum_savings_ratio:
        enabled = False
        reason = "below_savings_threshold"
    elif persist_exact is None:
        enabled = False
        reason = "exact_recall_persistence_required"

    compact_digest = digest_text(payload) if payload else None
    receipt: Mapping[str, Any] | None = None

    if enabled:
        exact_record = ST3GGExactRecallRecord(
            namespace=safe_namespace,
            exact_ref=exact_ref,
            original_digest=original_digest,
            original_bytes=count_utf8_bytes(original),
            content_type=content_type.strip(),
            source_hint=source_hint,
            original=original,
        )
        try:
            receipt = persist_exact(exact_record) if persist_exact is not None else None
        except Exception as exc:
            enabled = False
            reason = f"exact_recall_persistence_failed:{type(exc).__name__}"
            warnings = _unique((*warnings, reason))
            receipt = None
        if enabled and receipt is None:
            enabled = False
            reason = "exact_recall_persistence_unconfirmed"
        if enabled:
            confirmed_ref = str(receipt.get("exact_ref", "")) if isinstance(receipt, Mapping) else ""
            confirmed_digest = str(receipt.get("original_digest", "")) if isinstance(receipt, Mapping) else ""
            if confirmed_ref != exact_ref or confirmed_digest != original_digest:
                enabled = False
                reason = "exact_recall_receipt_mismatch"
                warnings = _unique((*warnings, reason))
                receipt = None

    decision = ST3GGDecision(
        enabled=enabled,
        reason=reason,
        namespace=safe_namespace,
        measurement_class=active_policy.measurement_class,
        raw_units=raw_units,
        candidate_units=candidate_units,
        final_units=final_units,
        overhead_units=overhead_units,
        savings_ratio=savings_ratio,
        minimum_savings_ratio=active_policy.minimum_savings_ratio,
        restoration_mode=ST3GGRestorationMode.EXACT_RECALL if enabled else ST3GGRestorationMode.NONE,
        original_digest=original_digest,
        compact_digest=compact_digest if enabled else None,
        pointer=pointer if enabled else None,
        exact_ref=exact_ref if enabled else None,
        warnings=warnings,
    )
    return ST3GGPreparedArtifact(
        payload=payload if enabled else "",
        decision=decision,
        persistence_receipt=receipt if enabled else None,
    )


def _legacy_get(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _legacy_int(value: Any, name: str, default: int = 0) -> int:
    item = _legacy_get(value, name, default)
    if type(item) is bool:
        return default
    try:
        number = int(item)
    except (TypeError, ValueError):
        return default
    return max(0, number)


def _legacy_float(value: Any, name: str, default: float = 0.0) -> float:
    item = _legacy_get(value, name, default)
    try:
        number = float(item)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return max(0.0, min(1.0, number))


def adapt_legacy_arena_decision(
    legacy: Any,
    *,
    namespace: str = "ARENA",
) -> ST3GGDecision:
    original_digest = str(_legacy_get(legacy, "original_hash", "") or "")
    if not _DIGEST_RE.fullmatch(original_digest):
        original_digest = digest_text(f"legacy-arena:{original_digest}")
    enabled = _legacy_get(legacy, "enabled", False) is True
    raw_units = _legacy_int(legacy, "raw_tokens_est")
    candidate_units = _legacy_int(legacy, "compact_tokens_est")
    supplied_savings = _legacy_float(legacy, "savings_ratio")
    measured_savings = _ratio(raw_units, candidate_units)
    pointer = str(_legacy_get(legacy, "st3gg_pointer", "") or "")
    reason = str(_legacy_get(legacy, "reason", "legacy_arena_projection") or "legacy_arena_projection")
    warnings = _unique(tuple(_legacy_get(legacy, "warnings", ()) or ()))
    if supplied_savings != measured_savings:
        warnings = _unique((*warnings, "legacy_savings_recomputed"))
    if enabled:
        warnings = _unique((*warnings, "legacy_arena_exact_ref_not_canonicalized"))
    return ST3GGDecision(
        enabled=False,
        reason="legacy_projection_requires_exact_recall_migration" if enabled else reason,
        namespace=_normalize_namespace(namespace),
        measurement_class=ST3GGMeasurementClass.TOKEN_ESTIMATE,
        raw_units=raw_units,
        candidate_units=candidate_units,
        final_units=candidate_units,
        overhead_units=0,
        savings_ratio=measured_savings,
        minimum_savings_ratio=0.08,
        restoration_mode=ST3GGRestorationMode.NONE,
        original_digest=original_digest,
        warnings=warnings,
        legacy_surface="AURA_ARENA_ST3GG_CODEC_V1",
        legacy_pointer=pointer or None,
    )


def adapt_legacy_ast_frame(frame: Any) -> ST3GGDecision:
    metrics = _legacy_get(frame, "metrics", {})
    raw_units = _legacy_int(metrics, "raw_token_estimate")
    candidate_units = _legacy_int(metrics, "encoded_token_estimate")
    original_digest = str(_legacy_get(frame, "source_hash", "") or "")
    if not _DIGEST_RE.fullmatch(original_digest):
        original_digest = digest_text(f"legacy-ast:{original_digest}")
    profile = str(_legacy_get(frame, "profile", "SYMBOLIC"))
    if hasattr(_legacy_get(frame, "profile", None), "value"):
        profile = str(_legacy_get(frame, "profile").value)
    savings = _ratio(raw_units, candidate_units)
    return ST3GGDecision(
        enabled=0 < candidate_units < raw_units,
        reason="legacy_ast_lossy_advisory_projection",
        namespace="AST",
        measurement_class=ST3GGMeasurementClass.TOKEN_ESTIMATE,
        raw_units=raw_units,
        candidate_units=candidate_units,
        final_units=candidate_units,
        overhead_units=0,
        savings_ratio=savings,
        minimum_savings_ratio=0.0,
        restoration_mode=ST3GGRestorationMode.LOSSY_ADVISORY,
        original_digest=original_digest,
        compact_digest=digest_text(str(_legacy_get(frame, "encoded", ""))),
        pointer=canonical_pointer("AST", original_digest) if 0 < candidate_units < raw_units else None,
        warnings=_unique((*tuple(_legacy_get(frame, "warnings", ()) or ()), f"legacy_profile:{profile}")),
        legacy_surface="AURA_ST3GG_CODEC_V1",
    )


def adapt_legacy_report_result(
    original: str,
    compressed: str,
    savings_ratio: float,
    legacy_pointer: str,
) -> ST3GGDecision:
    if type(original) is not str or type(compressed) is not str:
        raise TypeError("legacy_report_text_must_be_string")
    original_digest = digest_text(original)
    raw_units = count_utf8_bytes(original)
    candidate_units = count_utf8_bytes(compressed)
    measured_savings = _ratio(raw_units, candidate_units)
    supplied = 0.0
    try:
        supplied = float(savings_ratio)
    except (TypeError, ValueError):
        supplied = 0.0
    warnings: tuple[str, ...] = ()
    if not math.isfinite(supplied) or round(max(0.0, supplied), 6) != measured_savings:
        warnings = ("legacy_savings_recomputed",)
    enabled = 0 < candidate_units < raw_units
    return ST3GGDecision(
        enabled=enabled,
        reason="legacy_report_lossy_advisory_projection",
        namespace="REPORT",
        measurement_class=ST3GGMeasurementClass.BYTE_EXACT,
        raw_units=raw_units,
        candidate_units=candidate_units,
        final_units=candidate_units,
        overhead_units=0,
        savings_ratio=measured_savings,
        minimum_savings_ratio=0.0,
        restoration_mode=ST3GGRestorationMode.LOSSY_ADVISORY,
        original_digest=original_digest,
        compact_digest=digest_text(compressed) if enabled else None,
        pointer=canonical_pointer("REPORT", original_digest) if enabled else None,
        warnings=warnings,
        legacy_surface="AURA_ARENA_ST3GG_EGRESS_V1",
        legacy_pointer=str(legacy_pointer or "") or None,
    )


def _unique(values: Any) -> tuple[str, ...]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = str(value or "")
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return tuple(output)
