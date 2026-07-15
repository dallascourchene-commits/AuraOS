"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xab53-[Q-SYS:ST3GG_COMPATIBILITY_P5_3]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Cross-Surface Truth-Preserving Compatibility)
DEPENDENCIES: aura_st3gg_compatibility_types, aura_st3gg_compatibility_recall,
              aura_arena_st3gg_egress, aura_st3gg_codec, aura_st3gg_contracts
FUNCTIONS: encode_source_with_v2_facade, project_ast_frame_to_v2,
           compress_report_with_v2_facade, project_report_egress_to_v2,
           dual_read_st3gg_recall, p5_3_legacy_disposition
SYNOPSIS: Opt-in P5.3 facades preserving unchanged V1 output while producing
          canonical V2 truth-class and exact-recall evidence.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
import math
from pathlib import Path
import re
from typing import Any, Callable, Mapping

from aura_arena_st3gg_egress import (
    EGRESS_VERSION,
    PATCH_AUTHORITY_POLICY,
    compress_report_st3gg,
    decompress_report_st3gg,
    st3gg_pointer_for,
)
from aura_st3gg_codec import ST3GG_CODEC_VERSION, ST3GGCodec, ST3GGFrame, ST3GGProfile
from aura_st3gg_compatibility_recall import (
    dual_read_st3gg_recall,
    persist_report_exact_to_v1,
)
from aura_st3gg_compatibility_types import (
    EXECUTION_MODE,
    PROPOSAL_ONLY,
    REPORT_SOURCE_HINT,
    ST3GG_PATCH_AUTHORITY,
    ST3GGASTCompatibilityResult,
    ST3GGCanonicalBinding,
    ST3GGCompatibilityError,
    ST3GGLegacyDisposition,
    ST3GGLegacyDispositionRecord,
    ST3GGRecallDualReadEvidence,
    ST3GGReportCompatibilityResult,
    V1_STORAGE_OWNER,
    require,
)
from aura_st3gg_recall import lookup_st3gg_recall, upsert_st3gg_recall
from aura_st3gg_contracts import (
    PATCH_AUTHORITY,
    ST3GGDecision,
    ST3GGExactRecallRecord,
    ST3GGMeasurementClass,
    ST3GGRestorationMode,
    ST3GGSavingsPolicy,
    canonical_json_bytes,
    canonical_pointer,
    count_utf8_bytes,
    digest_text,
    prepare_st3gg_artifact,
)

_EXACT_SPAN_PROFILES = {ST3GGProfile.PATCH, ST3GGProfile.TEST, ST3GGProfile.VERIFIER}
_EGRESS_POINTER_RE = re.compile(r"^ST3GG_PTR:[0-9a-f]{12}$")
_VISIBLE_ASCII_RE = re.compile(r"^[\x20-\x7e]*$")

LookupRecall = Callable[..., Any]
UpsertRecall = Callable[..., Any]
CountUnits = Callable[[str], int]


def encode_source_with_v2_facade(
    source: str,
    source_file: str = "",
    target_symbol: str | None = None,
    profile: ST3GGProfile = ST3GGProfile.SYMBOLIC,
    *,
    codec: ST3GGCodec | None = None,
    count_units: CountUnits | None = None,
) -> ST3GGASTCompatibilityResult:
    active = codec or ST3GGCodec()
    legacy = active.encode_source(
        source,
        source_file=source_file,
        target_symbol=target_symbol,
        profile=profile,
    )
    try:
        return project_ast_frame_to_v2(
            source,
            legacy,
            source_file=source_file,
            target_symbol=target_symbol,
            profile=profile,
            count_units=count_units or active.estimate_token_cost,
        )
    except Exception as exc:
        return _ast_failure(source, legacy, f"ast_projection_failed:{type(exc).__name__}")


def project_ast_frame_to_v2(
    source: str,
    legacy_frame: ST3GGFrame,
    *,
    source_file: str = "",
    target_symbol: str | None = None,
    profile: ST3GGProfile = ST3GGProfile.SYMBOLIC,
    count_units: CountUnits | None = None,
) -> ST3GGASTCompatibilityResult:
    counter = count_units or ST3GGCodec().estimate_token_cost
    try:
        require(type(source) is str and isinstance(legacy_frame, ST3GGFrame), "legacy_ast_input_invalid")
        expected_profile = ST3GGProfile.coerce(profile)
        require(legacy_frame.version == ST3GG_CODEC_VERSION, "legacy_ast_version_mismatch")
        require(legacy_frame.profile is expected_profile, "legacy_ast_profile_mismatch")
        require(legacy_frame.source_file == source_file, "legacy_ast_source_file_mismatch")
        require(legacy_frame.target_symbol == target_symbol, "legacy_ast_target_symbol_mismatch")
        require(legacy_frame.source_hash == _safe_digest(source), "legacy_ast_source_digest_mismatch")
        raw = _units(counter(source), "legacy_ast_raw_units")
        candidate = _units(counter(legacy_frame.encoded), "legacy_ast_candidate_units")
        metrics = legacy_frame.metrics
        require(metrics.raw_char_count == len(source), "legacy_ast_raw_char_count_disagreement")
        require(metrics.encoded_char_count == len(legacy_frame.encoded), "legacy_ast_encoded_char_count_disagreement")
        require(metrics.raw_token_estimate == raw, "legacy_ast_raw_measurement_disagreement")
        require(metrics.encoded_token_estimate == candidate, "legacy_ast_candidate_measurement_disagreement")
        require(metrics.compression_ratio == _part_ratio(candidate, raw), "legacy_ast_ratio_disagreement")
        require(metrics.symbol_count == len(legacy_frame.symbols), "legacy_ast_symbol_count_disagreement")
        require(metrics.span_count == len(legacy_frame.spans), "legacy_ast_span_count_disagreement")
        require(tuple(metrics.warnings) == tuple(legacy_frame.warnings), "legacy_ast_warning_disagreement")
        _verify_spans(source, legacy_frame)
        replay = ST3GGCodec().encode_source(
            source,
            source_file=source_file,
            target_symbol=target_symbol,
            profile=expected_profile,
        )
        require(legacy_frame.to_dict() == replay.to_dict(), "legacy_ast_frame_replay_disagreement")
        decision = _view_decision(
            source,
            legacy_frame.encoded,
            "AST",
            ST3GGMeasurementClass.TOKEN_ESTIMATE,
            raw,
            candidate,
            "legacy_ast_lossy_advisory_compatibility",
            "legacy_ast_no_smaller_candidate",
            ST3GG_CODEC_VERSION,
            warnings=tuple(legacy_frame.warnings),
        )
        return ST3GGASTCompatibilityResult(
            legacy_frame,
            decision,
            len(legacy_frame.spans),
            _frame_digest(legacy_frame),
        )
    except Exception as exc:
        return _ast_failure(
            source,
            legacy_frame,
            _reason(exc, "legacy_ast_projection_failed"),
            counter,
        )


def compress_report_with_v2_facade(
    report_text: str,
    *,
    persist_exact: bool = False,
    ledger_path: str | Path | None = None,
    minimum_savings_ratio: float = 0.08,
    lookup_record: LookupRecall = lookup_st3gg_recall,
    upsert_record: UpsertRecall = upsert_st3gg_recall,
) -> ST3GGReportCompatibilityResult:
    compressed, savings, pointer = compress_report_st3gg(report_text)
    try:
        return project_report_egress_to_v2(
            report_text,
            compressed,
            savings,
            pointer,
            persist_exact=persist_exact,
            ledger_path=ledger_path,
            minimum_savings_ratio=minimum_savings_ratio,
            lookup_record=lookup_record,
            upsert_record=upsert_record,
        )
    except Exception as exc:
        return _report_failure(
            report_text,
            compressed,
            savings,
            pointer,
            f"report_projection_failed:{type(exc).__name__}",
        )


def project_report_egress_to_v2(
    original: str,
    legacy_compressed: str,
    legacy_savings_ratio: float,
    legacy_pointer: str,
    *,
    persist_exact: bool = False,
    ledger_path: str | Path | None = None,
    minimum_savings_ratio: float = 0.08,
    lookup_record: LookupRecall = lookup_st3gg_recall,
    upsert_record: UpsertRecall = upsert_st3gg_recall,
) -> ST3GGReportCompatibilityResult:
    try:
        require(type(original) is str and type(legacy_compressed) is str, "legacy_report_text_invalid")
        require(type(legacy_pointer) is str, "legacy_report_pointer_invalid")
        ratio = _ratio_value(minimum_savings_ratio, "minimum_savings_ratio")
        raw = count_utf8_bytes(original)
        candidate = count_utf8_bytes(legacy_compressed)
        supplied = _ratio_value(legacy_savings_ratio, "legacy_savings_ratio")
        measured = _legacy_savings(raw, candidate)
        warnings = () if math.isclose(supplied, measured, rel_tol=0.0, abs_tol=1e-12) else ("legacy_savings_recomputed",)
        mismatches = () if not warnings else ("legacy_report_savings_disagreement",)
        if not original:
            require((legacy_compressed, legacy_pointer) == ("", ""), "legacy_empty_report_shape_invalid")
            decision = _view_decision(
                original,
                "",
                "REPORT",
                ST3GGMeasurementClass.BYTE_EXACT,
                0,
                0,
                "",
                "empty_report",
                EGRESS_VERSION,
            )
            return _report_result(legacy_compressed, legacy_savings_ratio, legacy_pointer, decision, mismatches)
        require(_EGRESS_POINTER_RE.fullmatch(legacy_pointer) is not None, "legacy_report_pointer_malformed")
        require(legacy_pointer == st3gg_pointer_for(legacy_compressed), "legacy_report_pointer_substitution")
        require(_VISIBLE_ASCII_RE.fullmatch(legacy_compressed) is not None, "legacy_report_compact_not_visible_ascii")
        require(PATCH_AUTHORITY_POLICY == PATCH_AUTHORITY, "legacy_report_patch_authority_mismatch")
        base = _view_decision(
            original,
            legacy_compressed,
            "REPORT",
            ST3GGMeasurementClass.BYTE_EXACT,
            raw,
            candidate,
            "legacy_report_lossy_advisory_compatibility",
            "legacy_report_no_smaller_candidate",
            EGRESS_VERSION,
            legacy_pointer,
            warnings,
        )
        if not persist_exact or base.restoration_mode is ST3GGRestorationMode.NONE:
            return _report_result(legacy_compressed, legacy_savings_ratio, legacy_pointer, base, mismatches)
        require(ledger_path is not None, "exact_report_ledger_path_required")
        state: dict[str, Any] = {}

        def persist(record: ST3GGExactRecallRecord) -> Mapping[str, str]:
            binding, evidence = persist_report_exact_to_v1(
                record,
                legacy_compressed,
                legacy_pointer,
                ledger_path,
                lookup_record,
                upsert_record,
            )
            state.update(binding=binding, evidence=evidence)
            return {"exact_ref": record.exact_ref, "original_digest": record.original_digest}

        artifact = prepare_st3gg_artifact(
            original,
            legacy_compressed,
            namespace="REPORT",
            content_type="text/plain",
            source_hint=REPORT_SOURCE_HINT,
            policy=ST3GGSavingsPolicy(ratio, 1, ST3GGMeasurementClass.BYTE_EXACT),
            count_units=count_utf8_bytes,
            persist_exact=persist,
        )
        if artifact.decision.enabled:
            binding = state.get("binding")
            evidence = state.get("evidence")
            require(isinstance(binding, ST3GGCanonicalBinding), "enabled_report_binding_missing")
            require(
                isinstance(evidence, ST3GGRecallDualReadEvidence) and evidence.verified,
                "enabled_report_evidence_missing",
            )
            decision = replace(
                artifact.decision,
                legacy_surface=EGRESS_VERSION,
                legacy_pointer=legacy_pointer,
                warnings=_unique((*artifact.decision.warnings, *warnings, "v1_storage_owner_retained")),
            )
            return ST3GGReportCompatibilityResult(
                legacy_compressed,
                float(legacy_savings_ratio),
                legacy_pointer,
                decompress_report_st3gg(legacy_compressed),
                artifact.payload,
                decision,
                binding,
                evidence,
                mismatches,
            )
        marker = f"exact_recall_not_admitted:{artifact.decision.reason}"
        decision = replace(
            base,
            reason="legacy_report_lossy_advisory_exact_recall_not_admitted",
            warnings=_unique((*base.warnings, marker, *artifact.decision.warnings)),
        )
        return _report_result(
            legacy_compressed,
            legacy_savings_ratio,
            legacy_pointer,
            decision,
            _unique((*mismatches, marker)),
        )
    except Exception as exc:
        return _report_failure(
            original,
            legacy_compressed,
            legacy_savings_ratio,
            legacy_pointer,
            _reason(exc, "legacy_report_projection_failed"),
        )


def p5_3_legacy_disposition() -> ST3GGLegacyDispositionRecord:
    return ST3GGLegacyDispositionRecord(
        ST3GGLegacyDisposition.RETAIN_V1,
        "v2_compatibility_proven_but_v2_native_storage_and_live_ownership_not_migrated",
        (
            "canonical_v2_pointer_requires_a_binding_to_resolve_against_v1_storage",
            "v1_digest_alias_has_single_record_ownership_and_cannot_represent_conflicting_surface_variants",
            "legacy_ast_and_report_packet_parsers_remain_live_and_intentionally_lossy",
            "no_existing_record_backfill_or_live_caller_redirection_was_permitted_in_p5_3",
            "v1_storage_is_still_the_only_persisted_exact_original_owner",
        ),
        (
            "arena_writer_exact_recall_shadow_verified_in_p5_2",
            "ast_writer_golden_output_and_recomputed_measurements_verified",
            "report_writer_golden_output_and_truth_class_verified",
            "pointer_digest_dash_and_json_index_dual_reads_verified",
            "projection_and_lookup_failures_preserve_unchanged_v1_results",
        ),
    )


def _view_decision(
    original: str,
    compact: str,
    namespace: str,
    measurement: ST3GGMeasurementClass,
    raw: int,
    candidate: int,
    lossy_reason: str,
    none_reason: str,
    surface: str,
    legacy_pointer: str | None = None,
    warnings: tuple[str, ...] = (),
) -> ST3GGDecision:
    enabled = bool(compact) and 0 < candidate < raw
    digest = _safe_digest(original)
    return ST3GGDecision(
        enabled,
        lossy_reason if enabled else none_reason,
        namespace,
        measurement,
        raw,
        candidate,
        candidate,
        0,
        _savings(raw, candidate),
        0.0,
        ST3GGRestorationMode.LOSSY_ADVISORY if enabled else ST3GGRestorationMode.NONE,
        digest,
        _safe_digest(compact) if enabled else None,
        canonical_pointer(namespace, digest) if enabled else None,
        None,
        _unique(warnings),
        surface,
        legacy_pointer,
    )


def _verify_spans(source: str, frame: ST3GGFrame) -> None:
    if frame.profile not in _EXACT_SPAN_PROFILES:
        require(frame.spans == (), "legacy_ast_unexpected_spans_for_lossy_profile")
        return
    lines = source.splitlines()
    for span in frame.spans:
        require(isinstance(span, dict), "legacy_ast_span_not_object")
        start, end, text = span.get("line_start"), span.get("line_end"), span.get("text")
        require(
            type(start) is int and type(end) is int and 1 <= start <= end <= max(1, len(lines)),
            "legacy_ast_span_lines_invalid",
        )
        require(type(text) is str and bool(text) and text in source, "legacy_ast_span_text_not_exact")


def _ast_failure(
    source: str,
    frame: ST3GGFrame,
    reason: str,
    counter: CountUnits | None = None,
) -> ST3GGASTCompatibilityResult:
    active = counter or ST3GGCodec().estimate_token_cost
    raw = _safe_count(active, source)
    decision = _view_decision(
        source if type(source) is str else str(source),
        "",
        "AST",
        ST3GGMeasurementClass.TOKEN_ESTIMATE,
        raw,
        0,
        "",
        reason,
        ST3GG_CODEC_VERSION,
        warnings=(reason,),
    )
    return ST3GGASTCompatibilityResult(
        frame,
        decision,
        len(frame.spans),
        _frame_digest(frame),
        (reason,),
    )


def _report_failure(
    original: str,
    compact: str,
    savings: float,
    pointer: str,
    reason: str,
) -> ST3GGReportCompatibilityResult:
    safe_original, safe_compact = str(original), str(compact)
    raw = _safe_bytes(safe_original)
    decision = _view_decision(
        safe_original,
        "",
        "REPORT",
        ST3GGMeasurementClass.BYTE_EXACT,
        raw,
        0,
        "",
        reason,
        EGRESS_VERSION,
        str(pointer) or None,
        (reason,),
    )
    safe_savings = (
        float(savings)
        if type(savings) in {int, float}
        and not isinstance(savings, bool)
        and math.isfinite(float(savings))
        and 0.0 <= float(savings) <= 1.0
        else 0.0
    )
    return _report_result(safe_compact, safe_savings, str(pointer), decision, (reason,))


def _report_result(
    compact: str,
    savings: float,
    pointer: str,
    decision: ST3GGDecision,
    mismatches: tuple[str, ...],
) -> ST3GGReportCompatibilityResult:
    return ST3GGReportCompatibilityResult(
        compact,
        float(savings),
        pointer,
        decompress_report_st3gg(compact),
        "",
        decision,
        None,
        None,
        mismatches,
    )


def _frame_digest(frame: ST3GGFrame) -> str:
    return hashlib.sha256(canonical_json_bytes(frame.to_dict())).hexdigest()


def _safe_digest(text: str) -> str:
    try:
        return digest_text(text)
    except (TypeError, UnicodeEncodeError):
        return hashlib.sha256(str(text).encode("utf-8", errors="replace")).hexdigest()


def _safe_bytes(text: str) -> int:
    return len(str(text).encode("utf-8", errors="replace"))


def _safe_count(counter: CountUnits, text: str) -> int:
    try:
        return _units(counter(text), "fallback_unit_count")
    except Exception:
        return ST3GGCodec().estimate_token_cost(text)


def _units(value: Any, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ST3GGCompatibilityError(f"{name}_invalid")
    return value


def _number(value: Any, name: str) -> float:
    if (
        type(value) not in {int, float}
        or isinstance(value, bool)
        or not math.isfinite(float(value))
        or float(value) < 0
    ):
        raise ST3GGCompatibilityError(f"{name}_invalid")
    return float(value)


def _ratio_value(value: Any, name: str) -> float:
    number = _number(value, name)
    if number > 1.0:
        raise ST3GGCompatibilityError(f"{name}_invalid")
    return number


def _part_ratio(part: int, whole: int) -> float:
    return 0.0 if whole <= 0 else round(part / whole, 6)


def _savings(raw: int, final: int) -> float:
    return 0.0 if raw <= 0 or final >= raw else round((raw - final) / raw, 6)


def _legacy_savings(raw: int, final: int) -> float:
    return 0.0 if raw <= 0 else max(0.0, (raw - final) / raw)


def _reason(exc: Exception, fallback: str) -> str:
    return (
        str(exc)
        if isinstance(exc, ST3GGCompatibilityError) and str(exc)
        else f"{fallback}:{type(exc).__name__}"
    )


def _unique(values: Any) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values if str(value)))


__all__ = [
    "EXECUTION_MODE",
    "PROPOSAL_ONLY",
    "REPORT_SOURCE_HINT",
    "ST3GG_PATCH_AUTHORITY",
    "ST3GGASTCompatibilityResult",
    "ST3GGCanonicalBinding",
    "ST3GGCompatibilityError",
    "ST3GGLegacyDisposition",
    "ST3GGLegacyDispositionRecord",
    "ST3GGRecallDualReadEvidence",
    "ST3GGReportCompatibilityResult",
    "V1_STORAGE_OWNER",
    "compress_report_with_v2_facade",
    "dual_read_st3gg_recall",
    "encode_source_with_v2_facade",
    "p5_3_legacy_disposition",
    "project_ast_frame_to_v2",
    "project_report_egress_to_v2",
]
