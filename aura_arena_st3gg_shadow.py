"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xab52-[Q-SYS:ARENA_ST3GG_V2_SHADOW]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Verified Shadow Compatibility)
DEPENDENCIES: __future__, dataclasses, hashlib, json, math, pathlib, typing,
              aura_arena_st3gg_codec, aura_st3gg_contracts, aura_st3gg_recall
FUNCTIONS: encode_arena_capsule_with_v2_shadow, project_arena_st3gg_v2_shadow
SYNOPSIS: Read-only shadow projection of the live Arena ST3GG V1 writer into
          canonical V2 exact-recall contracts without changing V1 output.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Callable, Mapping

from aura_arena_st3gg_codec import (
    ARENA_ST3GG_CODEC_VERSION,
    DEFAULT_RECALL_LEDGER,
    MIN_RAW_CHARS,
    MIN_SAVINGS_RATIO,
    MAX_ROWS,
    PATCH_AUTHORITY,
    SAFE_MODE,
    ArenaST3GGCapsule,
    ArenaST3GGDecision,
    encode_arena_capsule_for_egress,
    estimate_tokens,
)
from aura_st3gg_contracts import (
    ST3GGDecision,
    ST3GGExactRecallRecord,
    ST3GGMeasurementClass,
    ST3GGRestorationMode,
    ST3GGSavingsPolicy,
    adapt_legacy_arena_decision,
    canonical_json_bytes,
    digest_text,
    prepare_st3gg_artifact,
    verify_exact_recall_record,
)
from aura_st3gg_recall import (
    ST3GGRecallRecord,
    compile_st3gg_pointer,
    lookup_st3gg_recall,
)

ARENA_ST3GG_SHADOW_VERSION = "AURA_ARENA_ST3GG_V2_SHADOW_P5_2"
V1_STORAGE_OWNER = "AURA_ST3GG_RECALL_V1"
V2_EXECUTION_MODE = "SHADOW_ONLY"
PROPOSAL_ONLY = True

LookupRecall = Callable[..., ST3GGRecallRecord | None]
CountUnits = Callable[[str], int]


class ArenaST3GGShadowError(ValueError):
    """A deterministic fail-closed V1-to-V2 binding error."""


@dataclass(frozen=True)
class ArenaST3GGV2ShadowComparison:
    """Deterministic, proposal-only evidence comparing live V1 with shadow V2."""

    eligible: bool
    exact_recall_verified: bool
    legacy_phase_hash: str
    legacy_decision: ArenaST3GGDecision
    legacy_pointer: str | None
    legacy_original_hash: str | None
    legacy_payload_digest: str
    legacy_raw_units: int
    legacy_final_units: int
    legacy_savings_ratio: float
    legacy_record_pointer: str | None
    legacy_record_digest: str | None
    legacy_record_content_type: str | None
    v2_decision: ST3GGDecision
    v2_payload_digest: str | None
    mismatch_reasons: tuple[str, ...] = ()
    version: str = ARENA_ST3GG_SHADOW_VERSION
    execution_mode: str = V2_EXECUTION_MODE
    v1_storage_owner: str = V1_STORAGE_OWNER
    proposal_only: bool = PROPOSAL_ONLY
    patch_authority: str = PATCH_AUTHORITY
    st3gg_patch_authority: bool = False

    def __post_init__(self) -> None:
        if type(self.eligible) is not bool or type(self.exact_recall_verified) is not bool:
            raise TypeError("shadow_boolean_fields_must_be_bool")
        if self.version != ARENA_ST3GG_SHADOW_VERSION:
            raise ValueError("unsupported_arena_st3gg_shadow_version")
        if self.execution_mode != V2_EXECUTION_MODE:
            raise ValueError("arena_st3gg_v2_must_remain_shadow_only")
        if self.v1_storage_owner != V1_STORAGE_OWNER:
            raise ValueError("arena_st3gg_v1_storage_owner_changed")
        if self.proposal_only is not True:
            raise ValueError("arena_st3gg_shadow_must_remain_proposal_only")
        if self.patch_authority != PATCH_AUTHORITY or self.st3gg_patch_authority is not False:
            raise ValueError("arena_st3gg_shadow_cannot_gain_patch_authority")
        if not _is_hex_digest(self.legacy_phase_hash, size=32):
            raise ValueError("legacy_phase_hash_invalid")
        if not isinstance(self.legacy_decision, ArenaST3GGDecision):
            raise TypeError("legacy_decision_must_be_arena_st3gg_decision")
        for name, value in (
            ("legacy_raw_units", self.legacy_raw_units),
            ("legacy_final_units", self.legacy_final_units),
        ):
            if type(value) is not int or value < 0:
                raise ValueError(f"{name}_invalid")
        if type(self.legacy_savings_ratio) is not float or not 0.0 <= self.legacy_savings_ratio <= 1.0:
            raise ValueError("legacy_savings_ratio_invalid")
        if not _is_sha256(self.legacy_payload_digest):
            raise ValueError("legacy_payload_digest_invalid")
        for name, value in (
            ("legacy_original_hash", self.legacy_original_hash),
            ("legacy_record_digest", self.legacy_record_digest),
            ("v2_payload_digest", self.v2_payload_digest),
        ):
            if value is not None and not _is_sha256(value):
                raise ValueError(f"{name}_invalid")
        if not isinstance(self.v2_decision, ST3GGDecision):
            raise TypeError("v2_decision_must_be_st3gg_decision")
        if self.exact_recall_verified and not self.eligible:
            raise ValueError("verified_exact_recall_must_be_eligible")
        if self.v2_decision.enabled and not self.exact_recall_verified:
            raise ValueError("enabled_v2_requires_verified_v1_exact_recall")
        if self.v2_decision.enabled and self.v2_decision.restoration_mode is not ST3GGRestorationMode.EXACT_RECALL:
            raise ValueError("enabled_v2_requires_exact_recall_mode")
        if any(type(reason) is not str or not reason for reason in self.mismatch_reasons):
            raise ValueError("mismatch_reasons_invalid")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["legacy_decision"]["warnings"] = list(self.legacy_decision.warnings)
        payload["v2_decision"] = self.v2_decision.to_dict()
        payload["mismatch_reasons"] = list(self.mismatch_reasons)
        return payload

    @property
    def comparison_digest(self) -> str:
        return hashlib.blake2b(canonical_json_bytes(self.to_dict()), digest_size=16).hexdigest()


@dataclass(frozen=True)
class ArenaST3GGShadowResult:
    """Live V1 result plus its read-only canonical V2 shadow comparison."""

    legacy_capsule: ArenaST3GGCapsule
    comparison: ArenaST3GGV2ShadowComparison

    def __post_init__(self) -> None:
        if not isinstance(self.legacy_capsule, ArenaST3GGCapsule):
            raise TypeError("legacy_capsule_must_be_arena_st3gg_capsule")
        if not isinstance(self.comparison, ArenaST3GGV2ShadowComparison):
            raise TypeError("comparison_must_be_arena_st3gg_shadow_comparison")


def encode_arena_capsule_with_v2_shadow(
    capsule: dict[str, Any],
    *,
    namespace: str = "ARENA",
    min_raw_chars: int = MIN_RAW_CHARS,
    min_savings_ratio: float = MIN_SAVINGS_RATIO,
    max_rows: int = MAX_ROWS,
    recall_root: str | Path | None = None,
    lookup_record: LookupRecall = lookup_st3gg_recall,
    count_units: CountUnits = estimate_tokens,
) -> ArenaST3GGShadowResult:
    """Run the unchanged V1 writer and add a fail-closed, read-only V2 shadow.

    Once the V1 writer succeeds, no shadow-only defect is allowed to suppress or
    alter that live result. Unexpected shadow exceptions are converted into a
    deterministic disabled V2 comparison using Aura's built-in token estimate.
    """

    legacy = encode_arena_capsule_for_egress(
        capsule,
        namespace=namespace,
        min_raw_chars=min_raw_chars,
        min_savings_ratio=min_savings_ratio,
        max_rows=max_rows,
        recall_root=recall_root,
    )
    try:
        comparison = project_arena_st3gg_v2_shadow(
            capsule,
            legacy,
            namespace=namespace,
            minimum_savings_ratio=min_savings_ratio,
            recall_root=recall_root,
            lookup_record=lookup_record,
            count_units=count_units,
        )
    except Exception as exc:  # final compatibility guard after V1 has succeeded
        comparison = _failure_comparison(
            capsule,
            legacy,
            namespace=namespace,
            minimum_savings_ratio=min_savings_ratio,
            reason=f"shadow_projection_failed:{type(exc).__name__}",
        )
    return ArenaST3GGShadowResult(legacy_capsule=legacy, comparison=comparison)


def project_arena_st3gg_v2_shadow(
    capsule: dict[str, Any],
    legacy_capsule: ArenaST3GGCapsule,
    *,
    namespace: str = "ARENA",
    minimum_savings_ratio: float = MIN_SAVINGS_RATIO,
    recall_root: str | Path | None = None,
    lookup_record: LookupRecall = lookup_st3gg_recall,
    count_units: CountUnits = estimate_tokens,
) -> ArenaST3GGV2ShadowComparison:
    """Project one already-emitted V1 Arena result into canonical V2 evidence.

    The function never mutates V1 recall. A canonical persistence receipt is
    synthesized only after the exact V1 record is recovered through both live
    V1 aliases and verified against the caller capsule and emitted V1 bytes.
    """

    if not isinstance(legacy_capsule, ArenaST3GGCapsule):
        raise TypeError("legacy_capsule_must_be_arena_st3gg_capsule")
    if not isinstance(legacy_capsule.decision, ArenaST3GGDecision):
        raise TypeError("legacy_decision_must_be_arena_st3gg_decision")

    original_json = _legacy_original_json(capsule)
    original_digest = digest_text(original_json)
    legacy_payload = legacy_capsule.payload
    if type(legacy_payload) is not str:
        raise TypeError("legacy_payload_must_be_string")
    legacy_raw_units = estimate_tokens(original_json)
    legacy_final_units = estimate_tokens(legacy_payload) if legacy_payload else legacy_raw_units
    legacy_savings = _legacy_ratio(legacy_raw_units, legacy_final_units)
    legacy_payload_digest = digest_text(legacy_payload)
    legacy_pointer = legacy_capsule.decision.st3gg_pointer

    if legacy_capsule.decision.enabled is not True:
        projected = adapt_legacy_arena_decision(legacy_capsule.decision, namespace=namespace)
        return _comparison(
            eligible=False,
            exact_recall_verified=False,
            legacy_capsule=legacy_capsule,
            legacy_payload_digest=legacy_payload_digest,
            legacy_raw_units=legacy_raw_units,
            legacy_final_units=legacy_final_units,
            legacy_savings_ratio=legacy_savings,
            v2_decision=projected,
            mismatch_reasons=(f"legacy_not_enabled:{legacy_capsule.decision.reason}",),
        )

    record: ST3GGRecallRecord | None = None
    try:
        if not callable(lookup_record):
            raise TypeError("lookup_record_must_be_callable")
        if not callable(count_units):
            raise TypeError("count_units_must_be_callable")
        policy_ratio = _validated_policy_ratio(minimum_savings_ratio)
        _verify_live_v1_capsule(
            legacy_capsule,
            original_json=original_json,
            original_digest=original_digest,
            minimum_savings_ratio=policy_ratio,
        )
        candidate = _extract_compact_candidate(
            legacy_payload,
            pointer=str(legacy_pointer),
            original_digest=original_digest,
        )
        ledger_path = _recall_ledger_path(recall_root)
        record = lookup_record(str(legacy_pointer), ledger_path=ledger_path)
        _require(record is not None, "legacy_exact_record_missing")
        _verify_v1_record(
            record,
            expected_namespace=_legacy_namespace(namespace),
            expected_original=original_json,
            expected_digest=original_digest,
            expected_pointer=str(legacy_pointer),
            expected_payload=legacy_payload,
        )
        digest_record = lookup_record(original_digest, ledger_path=ledger_path)
        _require(digest_record is not None, "legacy_digest_alias_missing")
        _require(isinstance(digest_record, ST3GGRecallRecord), "legacy_digest_alias_record_type_invalid")
        _verify_v1_record(
            digest_record,
            expected_namespace=_legacy_namespace(namespace),
            expected_original=original_json,
            expected_digest=original_digest,
            expected_pointer=str(legacy_pointer),
            expected_payload=legacy_payload,
        )
        _require(digest_record == record, "legacy_digest_alias_record_substitution")

        def confirm_v1_exact(v2_record: ST3GGExactRecallRecord) -> Mapping[str, str]:
            verify_exact_recall_record(v2_record)
            _require(record is not None, "legacy_exact_record_missing")
            _require(v2_record.original == record.original, "v2_original_not_bound_to_v1_record")
            _require(v2_record.original_digest == record.original_hash, "v2_digest_not_bound_to_v1_record")
            return {
                "exact_ref": v2_record.exact_ref,
                "original_digest": v2_record.original_digest,
                "storage_owner": V1_STORAGE_OWNER,
                "legacy_pointer": record.pointer,
            }

        artifact = prepare_st3gg_artifact(
            original_json,
            candidate,
            namespace=namespace,
            content_type="application/json",
            source_hint="coding_arena_st3gg_v1_shadow_binding",
            policy=ST3GGSavingsPolicy(
                minimum_savings_ratio=policy_ratio,
                minimum_raw_units=1,
                measurement_class=ST3GGMeasurementClass.TOKEN_ESTIMATE,
            ),
            count_units=count_units,
            persist_exact=confirm_v1_exact,
        )
        v2_decision = replace(
            artifact.decision,
            warnings=_unique((*artifact.decision.warnings, "shadow_only_v1_live_owner")),
            legacy_surface=ARENA_ST3GG_CODEC_VERSION,
            legacy_pointer=str(legacy_pointer),
        )
        mismatch_reasons: tuple[str, ...] = ()
        if not v2_decision.enabled:
            mismatch_reasons = (f"v2_not_enabled:{v2_decision.reason}",)
        return _comparison(
            eligible=True,
            exact_recall_verified=True,
            legacy_capsule=legacy_capsule,
            legacy_payload_digest=legacy_payload_digest,
            legacy_raw_units=legacy_raw_units,
            legacy_final_units=legacy_final_units,
            legacy_savings_ratio=legacy_savings,
            legacy_record=record,
            v2_decision=v2_decision,
            v2_payload_digest=digest_text(artifact.payload) if artifact.payload else None,
            mismatch_reasons=mismatch_reasons,
        )
    except ArenaST3GGShadowError as exc:
        reason = str(exc)
    except Exception as exc:  # fail closed without changing the already-produced V1 result
        reason = f"shadow_projection_failed:{type(exc).__name__}"

    disabled = _disabled_v2_decision(
        namespace=namespace,
        original_digest=original_digest,
        raw_units=legacy_raw_units,
        minimum_savings_ratio=_safe_policy_ratio(minimum_savings_ratio),
        reason=reason,
        legacy_pointer=str(legacy_pointer or "") or None,
    )
    return _comparison(
        eligible=False,
        exact_recall_verified=False,
        legacy_capsule=legacy_capsule,
        legacy_payload_digest=legacy_payload_digest,
        legacy_raw_units=legacy_raw_units,
        legacy_final_units=legacy_final_units,
        legacy_savings_ratio=legacy_savings,
        legacy_record=record if isinstance(record, ST3GGRecallRecord) else None,
        v2_decision=disabled,
        mismatch_reasons=(reason,),
    )


def _verify_live_v1_capsule(
    legacy_capsule: ArenaST3GGCapsule,
    *,
    original_json: str,
    original_digest: str,
    minimum_savings_ratio: float,
) -> None:
    decision = legacy_capsule.decision
    _require(legacy_capsule.capsule_version == ARENA_ST3GG_CODEC_VERSION, "legacy_capsule_version_noncanonical")
    _require(legacy_capsule.mode == SAFE_MODE, "legacy_capsule_mode_noncanonical")
    _require(type(legacy_capsule.payload) is str and bool(legacy_capsule.payload), "legacy_enabled_empty_payload")
    _require(type(legacy_capsule.phase_hash) is str, "legacy_phase_hash_type_invalid")
    _require(decision.enabled is True, "legacy_decision_not_enabled")
    _require(decision.reason == "savings_threshold_met", "legacy_enabled_reason_noncanonical")
    _require(bool(decision.st3gg_pointer), "legacy_enabled_missing_pointer")
    _require(legacy_capsule.original_hash == original_digest, "legacy_capsule_digest_disagreement")
    _require(decision.original_hash == original_digest, "legacy_decision_digest_disagreement")
    _require(
        legacy_capsule.retrieval_marker == _retrieval_marker(original_digest),
        "legacy_retrieval_marker_disagreement",
    )
    raw_units = estimate_tokens(original_json)
    final_units = estimate_tokens(legacy_capsule.payload)
    measured_savings = _legacy_ratio(raw_units, final_units)
    _require(decision.raw_tokens_est == raw_units, "legacy_raw_measurement_disagreement")
    _require(decision.compact_tokens_est == final_units, "legacy_final_measurement_disagreement")
    _require(decision.savings_ratio == measured_savings, "legacy_savings_measurement_disagreement")
    _require(measured_savings >= minimum_savings_ratio, "legacy_enabled_below_requested_threshold")
    expected_phase_hash = _legacy_enabled_phase_hash(legacy_capsule)
    _require(legacy_capsule.phase_hash == expected_phase_hash, "legacy_phase_hash_disagreement")


def _verify_v1_record(
    record: ST3GGRecallRecord,
    *,
    expected_namespace: str,
    expected_original: str,
    expected_digest: str,
    expected_pointer: str,
    expected_payload: str,
) -> None:
    _require(isinstance(record, ST3GGRecallRecord), "legacy_exact_record_type_invalid")
    _require(record.content_type == expected_namespace, "legacy_record_content_type_noncanonical")
    _require(record.source_hint == "coding_arena_st3gg_egress", "legacy_record_source_hint_noncanonical")
    _require(record.original == expected_original, "legacy_exact_record_stale")
    _require(record.original_hash == expected_digest, "legacy_record_digest_disagreement")
    _require(digest_text(record.original) == expected_digest, "legacy_record_original_digest_mismatch")
    _require(record.pointer == expected_pointer, "legacy_record_pointer_substitution")
    _require(record.compressed == expected_payload, "legacy_record_compact_payload_disagreement")
    pointer, dash_key, glyph, header = compile_st3gg_pointer(record.original, namespace=record.content_type)
    _require(pointer == record.pointer, "legacy_record_pointer_not_derived")
    _require(dash_key == record.dash_key, "legacy_record_dash_key_not_derived")
    _require(glyph == record.glyph, "legacy_record_glyph_not_derived")
    _require(header == record.holographic_header, "legacy_record_header_not_derived")


def _extract_compact_candidate(payload: str, *, pointer: str, original_digest: str) -> str:
    suffix = (
        f"|PTR={pointer}|HASH={original_digest}|MARK={_retrieval_marker(original_digest)}|"
        f"AUTH={PATCH_AUTHORITY}|VSA_AUTH=false"
    )
    _require(payload.endswith(suffix), "legacy_payload_metadata_noncanonical")
    candidate = payload[: -len(suffix)]
    _require(bool(candidate), "legacy_compact_candidate_empty")
    _require(candidate.isascii(), "legacy_compact_candidate_not_ascii")
    _require(all(32 <= ord(char) <= 126 for char in candidate), "legacy_compact_candidate_not_visible_ascii")
    return candidate


def _legacy_enabled_phase_hash(legacy_capsule: ArenaST3GGCapsule) -> str:
    body = json.dumps(
        {
            "version": ARENA_ST3GG_CODEC_VERSION,
            "mode": SAFE_MODE,
            "payload": legacy_capsule.payload,
            "original_hash": legacy_capsule.original_hash,
            "decision": legacy_capsule.decision,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.blake2b(body.encode("utf-8", errors="replace"), digest_size=16).hexdigest()


def _comparison(
    *,
    eligible: bool,
    exact_recall_verified: bool,
    legacy_capsule: ArenaST3GGCapsule,
    legacy_payload_digest: str,
    legacy_raw_units: int,
    legacy_final_units: int,
    legacy_savings_ratio: float,
    v2_decision: ST3GGDecision,
    mismatch_reasons: tuple[str, ...],
    legacy_record: ST3GGRecallRecord | None = None,
    v2_payload_digest: str | None = None,
) -> ArenaST3GGV2ShadowComparison:
    return ArenaST3GGV2ShadowComparison(
        eligible=eligible,
        exact_recall_verified=exact_recall_verified,
        legacy_phase_hash=legacy_capsule.phase_hash,
        legacy_decision=legacy_capsule.decision,
        legacy_pointer=legacy_capsule.decision.st3gg_pointer,
        legacy_original_hash=_trusted_sha256(
            legacy_capsule.original_hash or legacy_capsule.decision.original_hash
        ),
        legacy_payload_digest=legacy_payload_digest,
        legacy_raw_units=legacy_raw_units,
        legacy_final_units=legacy_final_units,
        legacy_savings_ratio=legacy_savings_ratio,
        legacy_record_pointer=legacy_record.pointer if legacy_record is not None else None,
        legacy_record_digest=(
            _trusted_sha256(legacy_record.original_hash) if legacy_record is not None else None
        ),
        legacy_record_content_type=legacy_record.content_type if legacy_record is not None else None,
        v2_decision=v2_decision,
        v2_payload_digest=v2_payload_digest,
        mismatch_reasons=_unique(mismatch_reasons),
    )


def _failure_comparison(
    capsule: dict[str, Any],
    legacy_capsule: ArenaST3GGCapsule,
    *,
    namespace: str,
    minimum_savings_ratio: Any,
    reason: str,
) -> ArenaST3GGV2ShadowComparison:
    original_json = _legacy_original_json(capsule)
    original_digest = digest_text(original_json)
    payload = legacy_capsule.payload if type(legacy_capsule.payload) is str else str(legacy_capsule.payload)
    raw_units = estimate_tokens(original_json)
    final_units = estimate_tokens(payload) if payload else raw_units
    disabled = _disabled_v2_decision(
        namespace=namespace,
        original_digest=original_digest,
        raw_units=raw_units,
        minimum_savings_ratio=_safe_policy_ratio(minimum_savings_ratio),
        reason=reason,
        legacy_pointer=legacy_capsule.decision.st3gg_pointer,
    )
    return _comparison(
        eligible=False,
        exact_recall_verified=False,
        legacy_capsule=legacy_capsule,
        legacy_payload_digest=digest_text(payload),
        legacy_raw_units=raw_units,
        legacy_final_units=final_units,
        legacy_savings_ratio=_legacy_ratio(raw_units, final_units),
        v2_decision=disabled,
        mismatch_reasons=(reason,),
    )


def _disabled_v2_decision(
    *,
    namespace: str,
    original_digest: str,
    raw_units: int,
    minimum_savings_ratio: float,
    reason: str,
    legacy_pointer: str | None,
) -> ST3GGDecision:
    trusted_raw = max(0, raw_units)
    return ST3GGDecision(
        enabled=False,
        reason=reason,
        namespace=_canonical_namespace(namespace),
        measurement_class=ST3GGMeasurementClass.TOKEN_ESTIMATE,
        raw_units=trusted_raw,
        candidate_units=trusted_raw,
        final_units=trusted_raw,
        overhead_units=0,
        savings_ratio=0.0,
        minimum_savings_ratio=minimum_savings_ratio,
        restoration_mode=ST3GGRestorationMode.NONE,
        original_digest=original_digest,
        warnings=(reason,),
        legacy_surface=ARENA_ST3GG_CODEC_VERSION,
        legacy_pointer=legacy_pointer,
    )


def _legacy_original_json(capsule: dict[str, Any]) -> str:
    value: Any = capsule
    if not isinstance(value, dict):
        value = {"value": value}
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    decoded = json.loads(encoded)
    safe = decoded if isinstance(decoded, dict) else {"value": decoded}
    return json.dumps(safe, sort_keys=True, separators=(",", ":"), default=str)


def _recall_ledger_path(recall_root: str | Path | None) -> Path:
    root = Path("Aura_Memory") if recall_root is None else Path(recall_root)
    if root.suffix == ".jsonl":
        return root
    if root.name == "Aura_Memory":
        return root / DEFAULT_RECALL_LEDGER
    return root / "Aura_Memory" / DEFAULT_RECALL_LEDGER


def _legacy_namespace(namespace: str) -> str:
    safe = "".join(
        char if char.isascii() and (char.isalnum() or char in "_-") else "_"
        for char in str(namespace or "ARENA")
    )
    return safe.upper() or "ARENA"


def _canonical_namespace(namespace: str) -> str:
    return _legacy_namespace(namespace)[:32] or "ST3GG"


def _retrieval_marker(original_digest: str) -> str:
    return f"<<aura_arena_st3gg:{original_digest}>>"


def _validated_policy_ratio(value: Any) -> float:
    if type(value) is bool:
        raise ArenaST3GGShadowError("minimum_savings_ratio_invalid")
    try:
        ratio = float(value)
    except (TypeError, ValueError) as exc:
        raise ArenaST3GGShadowError("minimum_savings_ratio_invalid") from exc
    if not math.isfinite(ratio) or not 0.0 <= ratio <= 1.0:
        raise ArenaST3GGShadowError("minimum_savings_ratio_invalid")
    return ratio


def _safe_policy_ratio(value: Any) -> float:
    try:
        return _validated_policy_ratio(value)
    except ArenaST3GGShadowError:
        return MIN_SAVINGS_RATIO


def _legacy_ratio(raw_units: int, final_units: int) -> float:
    if raw_units <= 0 or final_units >= raw_units:
        return 0.0
    return round((raw_units - final_units) / raw_units, 4)


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ArenaST3GGShadowError(reason)


def _is_hex_digest(value: Any, *, size: int) -> bool:
    return type(value) is str and len(value) == size and all(char in "0123456789abcdef" for char in value)


def _is_sha256(value: Any) -> bool:
    return _is_hex_digest(value, size=64)


def _trusted_sha256(value: Any) -> str | None:
    text = str(value or "")
    return text if _is_sha256(text) else None


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
