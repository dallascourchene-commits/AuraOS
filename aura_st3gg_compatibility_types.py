"""Immutable P5.3 ST3GG compatibility evidence contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import math
import re
from typing import Any

from aura_st3gg_codec import ST3GGFrame
from aura_st3gg_contracts import (
    PATCH_AUTHORITY,
    ST3GGDecision,
    ST3GGRestorationMode,
    canonical_json_bytes,
    canonical_pointer,
    digest_text,
    exact_ref_for,
    parse_canonical_pointer,
)
from aura_st3gg_recall import ST3GG_RECALL_VERSION

ST3GG_COMPATIBILITY_VERSION = "AURA_ST3GG_COMPATIBILITY_P5_3"
EXECUTION_MODE = "OPT_IN_COMPATIBILITY"
V1_STORAGE_OWNER = ST3GG_RECALL_VERSION
REPORT_SOURCE_HINT = "arena_st3gg_egress_p5_3"
PROPOSAL_ONLY = True
ST3GG_PATCH_AUTHORITY = False

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_V1_POINTER_RE = re.compile(r"^ST3GG-L2::[A-Z0-9_-]+:[0-9A-F]{4}:[0-9a-f]{16}$")
_DASH_RE = re.compile(r"^[0-9a-f]{16}$")
_GLYPH_RE = re.compile(r"^[0-9A-F]{4}$")
_HEADER_RE = re.compile(r"^[A-Za-z0-9_-]{64}$")
_EGRESS_POINTER_RE = re.compile(r"^ST3GG_PTR:[0-9a-f]{12}$")


class ST3GGCompatibilityError(ValueError):
    """Deterministic fail-closed compatibility verification error."""


class ST3GGLegacyDisposition(str, Enum):
    RETAIN_V1 = "RETAIN_V1"
    BEGIN_SEPARATE_DEPRECATION = "BEGIN_SEPARATE_DEPRECATION"
    BLOCK_DEPRECATION = "BLOCK_DEPRECATION"


@dataclass(frozen=True)
class ST3GGCanonicalBinding:
    namespace: str
    pointer: str
    exact_ref: str
    original_digest: str
    original_bytes: int
    content_type: str
    source_hint: str
    legacy_recall_pointer: str
    legacy_dash_key: str
    legacy_glyph: str
    legacy_holographic_header: str
    legacy_surface: str
    legacy_surface_pointer: str | None = None
    legacy_compact_digest: str | None = None
    version: str = ST3GG_COMPATIBILITY_VERSION
    storage_owner: str = V1_STORAGE_OWNER

    def __post_init__(self) -> None:
        constitutional(self.version, EXECUTION_MODE, self.storage_owner, True, PATCH_AUTHORITY, False)
        require(
            type(self.original_digest) is str and _SHA256_RE.fullmatch(self.original_digest) is not None,
            "binding_digest_invalid",
        )
        require(type(self.original_bytes) is int and self.original_bytes >= 0, "binding_length_invalid")
        require(self.pointer == canonical_pointer(self.namespace, self.original_digest), "binding_pointer_mismatch")
        require(self.exact_ref == exact_ref_for(self.namespace, self.original_digest), "binding_ref_mismatch")
        require(parse_canonical_pointer(self.pointer)[0] == self.namespace, "binding_namespace_mismatch")
        require(type(self.content_type) is str and bool(self.content_type.strip()), "binding_content_type_required")
        require(type(self.source_hint) is str, "binding_source_hint_invalid")
        require(type(self.legacy_surface) is str and bool(self.legacy_surface), "binding_surface_required")
        require(
            type(self.legacy_recall_pointer) is str
            and _V1_POINTER_RE.fullmatch(self.legacy_recall_pointer) is not None,
            "binding_v1_pointer_invalid",
        )
        require(
            type(self.legacy_dash_key) is str and _DASH_RE.fullmatch(self.legacy_dash_key) is not None,
            "binding_dash_invalid",
        )
        require(
            type(self.legacy_glyph) is str and _GLYPH_RE.fullmatch(self.legacy_glyph) is not None,
            "binding_glyph_invalid",
        )
        require(
            type(self.legacy_holographic_header) is str
            and _HEADER_RE.fullmatch(self.legacy_holographic_header) is not None,
            "binding_header_invalid",
        )
        if self.legacy_surface_pointer is not None:
            require(
                type(self.legacy_surface_pointer) is str
                and _EGRESS_POINTER_RE.fullmatch(self.legacy_surface_pointer) is not None,
                "binding_surface_pointer_invalid",
            )
        if self.legacy_compact_digest is not None:
            require(
                type(self.legacy_compact_digest) is str
                and _SHA256_RE.fullmatch(self.legacy_compact_digest) is not None,
                "binding_compact_digest_invalid",
            )
        if self.legacy_surface_pointer is not None and self.legacy_compact_digest is not None:
            require(
                self.legacy_surface_pointer == f"ST3GG_PTR:{self.legacy_compact_digest[:12]}",
                "binding_surface_pointer_digest_mismatch",
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ST3GGRecallDualReadEvidence:
    verified: bool
    restoration_mode: ST3GGRestorationMode
    binding: ST3GGCanonicalBinding
    resolved_pointer: str | None = None
    resolved_original_digest: str | None = None
    resolved_content_type: str | None = None
    resolved_original_bytes: int | None = None
    resolved_compact_digest: str | None = None
    alias_record_digests: tuple[tuple[str, str], ...] = ()
    json_index_record_digest: str | None = None
    mismatch_reasons: tuple[str, ...] = ()
    version: str = ST3GG_COMPATIBILITY_VERSION
    execution_mode: str = EXECUTION_MODE
    storage_owner: str = V1_STORAGE_OWNER
    proposal_only: bool = PROPOSAL_ONLY
    patch_authority: str = PATCH_AUTHORITY
    st3gg_patch_authority: bool = ST3GG_PATCH_AUTHORITY

    def __post_init__(self) -> None:
        constitutional(
            self.version,
            self.execution_mode,
            self.storage_owner,
            self.proposal_only,
            self.patch_authority,
            self.st3gg_patch_authority,
        )
        require(type(self.verified) is bool, "evidence_verified_flag_invalid")
        require(isinstance(self.restoration_mode, ST3GGRestorationMode), "evidence_restoration_mode_invalid")
        require(isinstance(self.binding, ST3GGCanonicalBinding), "evidence_binding_invalid")
        require(type(self.alias_record_digests) is tuple, "alias_evidence_container_invalid")
        require(
            all(
                type(item) is tuple
                and len(item) == 2
                and type(item[0]) is str
                and type(item[1]) is str
                for item in self.alias_record_digests
            ),
            "alias_evidence_shape_invalid",
        )
        require(type(self.mismatch_reasons) is tuple, "evidence_mismatch_container_invalid")
        if self.verified:
            require(self.restoration_mode is ST3GGRestorationMode.EXACT_RECALL, "verified_mode_not_exact")
            require(not self.mismatch_reasons, "verified_evidence_has_mismatch")
            require(self.resolved_pointer == self.binding.legacy_recall_pointer, "evidence_pointer_mismatch")
            require(self.resolved_original_digest == self.binding.original_digest, "evidence_digest_mismatch")
            require(self.resolved_content_type == self.binding.content_type, "evidence_content_type_mismatch")
            require(self.resolved_original_bytes == self.binding.original_bytes, "evidence_length_mismatch")
            if self.binding.legacy_compact_digest is not None:
                require(
                    self.resolved_compact_digest == self.binding.legacy_compact_digest,
                    "evidence_compact_digest_mismatch",
                )
            names = tuple(name for name, _digest in self.alias_record_digests)
            digests = {record_digest for _name, record_digest in self.alias_record_digests}
            require(names == ("pointer", "digest", "dash_key"), "verified_alias_evidence_incomplete")
            require(len(digests) == 1, "verified_alias_evidence_disagreement")
            require(self.json_index_record_digest in digests, "verified_json_evidence_disagreement")
        else:
            require(self.restoration_mode is ST3GGRestorationMode.NONE, "failed_evidence_mode_not_none")
            require(bool(self.mismatch_reasons), "failed_evidence_reason_required")
            require(
                self.resolved_pointer is None
                and self.resolved_original_digest is None
                and self.resolved_content_type is None
                and self.resolved_original_bytes is None
                and self.resolved_compact_digest is None
                and not self.alias_record_digests
                and self.json_index_record_digest is None,
                "failed_evidence_carries_verified_state",
            )
        for alias, record_digest in self.alias_record_digests:
            require(bool(alias) and _SHA256_RE.fullmatch(record_digest) is not None, "alias_evidence_invalid")
        if self.resolved_compact_digest is not None:
            require(
                type(self.resolved_compact_digest) is str
                and _SHA256_RE.fullmatch(self.resolved_compact_digest) is not None,
                "evidence_compact_digest_invalid",
            )
        if self.json_index_record_digest is not None:
            require(
                type(self.json_index_record_digest) is str
                and _SHA256_RE.fullmatch(self.json_index_record_digest) is not None,
                "json_evidence_digest_invalid",
            )
        require(
            all(type(reason) is str and bool(reason) for reason in self.mismatch_reasons),
            "evidence_mismatch_reason_invalid",
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["restoration_mode"] = self.restoration_mode.value
        value["alias_record_digests"] = [list(item) for item in self.alias_record_digests]
        value["mismatch_reasons"] = list(self.mismatch_reasons)
        return value

    @property
    def evidence_digest(self) -> str:
        return hashlib.blake2b(canonical_json_bytes(self.to_dict()), digest_size=16).hexdigest()


@dataclass(frozen=True)
class ST3GGASTCompatibilityResult:
    legacy_frame: ST3GGFrame
    v2_decision: ST3GGDecision
    exact_span_count: int
    legacy_frame_digest: str
    mismatch_reasons: tuple[str, ...] = ()
    version: str = ST3GG_COMPATIBILITY_VERSION
    execution_mode: str = EXECUTION_MODE
    proposal_only: bool = PROPOSAL_ONLY
    patch_authority: str = PATCH_AUTHORITY
    st3gg_patch_authority: bool = ST3GG_PATCH_AUTHORITY

    def __post_init__(self) -> None:
        constitutional(
            self.version,
            self.execution_mode,
            V1_STORAGE_OWNER,
            self.proposal_only,
            self.patch_authority,
            self.st3gg_patch_authority,
        )
        require(isinstance(self.legacy_frame, ST3GGFrame), "ast_legacy_frame_invalid")
        require(isinstance(self.v2_decision, ST3GGDecision), "ast_v2_decision_invalid")
        require(self.exact_span_count == len(self.legacy_frame.spans), "ast_span_count_disagreement")
        require(
            type(self.legacy_frame_digest) is str
            and _SHA256_RE.fullmatch(self.legacy_frame_digest) is not None,
            "ast_frame_digest_invalid",
        )
        require(
            self.legacy_frame_digest == hashlib.sha256(canonical_json_bytes(self.legacy_frame.to_dict())).hexdigest(),
            "ast_frame_digest_disagreement",
        )
        require(
            self.v2_decision.restoration_mode
            in {ST3GGRestorationMode.LOSSY_ADVISORY, ST3GGRestorationMode.NONE},
            "ast_false_exact_claim",
        )
        require(type(self.mismatch_reasons) is tuple, "ast_mismatch_container_invalid")
        require(
            all(type(reason) is str and bool(reason) for reason in self.mismatch_reasons),
            "ast_mismatch_reason_invalid",
        )
        require(
            (self.v2_decision.enabled and self.v2_decision.restoration_mode is ST3GGRestorationMode.LOSSY_ADVISORY)
            or (not self.v2_decision.enabled and self.v2_decision.restoration_mode is ST3GGRestorationMode.NONE),
            "ast_enabled_restoration_mode_disagreement",
        )


@dataclass(frozen=True)
class ST3GGReportCompatibilityResult:
    legacy_compressed: str
    legacy_savings_ratio: float
    legacy_pointer: str
    legacy_restored_preview: str
    v2_payload: str
    v2_decision: ST3GGDecision
    binding: ST3GGCanonicalBinding | None
    recall_evidence: ST3GGRecallDualReadEvidence | None
    mismatch_reasons: tuple[str, ...] = ()
    version: str = ST3GG_COMPATIBILITY_VERSION
    execution_mode: str = EXECUTION_MODE
    storage_owner: str = V1_STORAGE_OWNER
    proposal_only: bool = PROPOSAL_ONLY
    patch_authority: str = PATCH_AUTHORITY
    st3gg_patch_authority: bool = ST3GG_PATCH_AUTHORITY

    def __post_init__(self) -> None:
        constitutional(
            self.version,
            self.execution_mode,
            self.storage_owner,
            self.proposal_only,
            self.patch_authority,
            self.st3gg_patch_authority,
        )
        require(
            type(self.legacy_compressed) is str
            and type(self.legacy_pointer) is str
            and type(self.legacy_restored_preview) is str
            and type(self.v2_payload) is str,
            "report_legacy_fields_invalid",
        )
        require(
            type(self.legacy_savings_ratio) is float
            and math.isfinite(self.legacy_savings_ratio)
            and 0.0 <= self.legacy_savings_ratio <= 1.0,
            "report_savings_invalid",
        )
        require(isinstance(self.v2_decision, ST3GGDecision), "report_v2_decision_invalid")
        require(type(self.mismatch_reasons) is tuple, "report_mismatch_container_invalid")
        require(
            all(type(reason) is str and bool(reason) for reason in self.mismatch_reasons),
            "report_mismatch_reason_invalid",
        )
        if self.v2_decision.enabled:
            require(_EGRESS_POINTER_RE.fullmatch(self.legacy_pointer) is not None, "enabled_report_pointer_invalid")
            require(self.v2_decision.legacy_pointer == self.legacy_pointer, "enabled_report_legacy_pointer_disagreement")
        exact = self.v2_decision.restoration_mode is ST3GGRestorationMode.EXACT_RECALL
        if exact:
            require(self.v2_decision.enabled, "exact_report_decision_not_enabled")
            require(self.binding is not None and self.recall_evidence is not None, "exact_report_binding_missing")
            require(self.recall_evidence.verified and bool(self.v2_payload), "exact_report_not_verified")
            require(self.v2_decision.pointer == self.binding.pointer, "exact_report_pointer_disagreement")
            require(self.v2_decision.exact_ref == self.binding.exact_ref, "exact_report_ref_disagreement")
            require(self.v2_decision.legacy_pointer == self.legacy_pointer, "exact_report_legacy_pointer_disagreement")
            require(self.v2_decision.legacy_surface == self.binding.legacy_surface, "exact_report_surface_disagreement")
            require(self.binding.legacy_surface_pointer == self.legacy_pointer, "exact_report_binding_pointer_disagreement")
            require(
                self.binding.legacy_compact_digest == digest_text(self.legacy_compressed),
                "exact_report_compact_digest_disagreement",
            )
            require(self.recall_evidence.binding == self.binding, "exact_report_evidence_binding_disagreement")
        else:
            require(
                not self.v2_payload and self.binding is None and self.recall_evidence is None,
                "non_exact_report_has_exact_state",
            )

    @property
    def legacy_result(self) -> tuple[str, float, str]:
        return self.legacy_compressed, self.legacy_savings_ratio, self.legacy_pointer


@dataclass(frozen=True)
class ST3GGLegacyDispositionRecord:
    disposition: ST3GGLegacyDisposition
    reason: str
    blockers: tuple[str, ...]
    satisfied_evidence: tuple[str, ...]
    version: str = ST3GG_COMPATIBILITY_VERSION
    proposal_only: bool = PROPOSAL_ONLY
    patch_authority: str = PATCH_AUTHORITY
    st3gg_patch_authority: bool = ST3GG_PATCH_AUTHORITY

    def __post_init__(self) -> None:
        constitutional(
            self.version,
            EXECUTION_MODE,
            V1_STORAGE_OWNER,
            self.proposal_only,
            self.patch_authority,
            self.st3gg_patch_authority,
        )
        require(isinstance(self.disposition, ST3GGLegacyDisposition), "disposition_invalid")
        require(type(self.reason) is str and bool(self.reason), "disposition_reason_invalid")
        require(
            type(self.blockers) is tuple
            and bool(self.blockers)
            and all(type(item) is str and bool(item) for item in self.blockers),
            "disposition_blockers_invalid",
        )
        require(
            type(self.satisfied_evidence) is tuple
            and bool(self.satisfied_evidence)
            and all(type(item) is str and bool(item) for item in self.satisfied_evidence),
            "disposition_evidence_invalid",
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["disposition"] = self.disposition.value
        return value

    @property
    def decision_digest(self) -> str:
        return hashlib.blake2b(canonical_json_bytes(self.to_dict()), digest_size=16).hexdigest()


def constitutional(
    version: str,
    mode: str,
    owner: str,
    proposal: bool,
    authority: str,
    st3gg_authority: bool,
) -> None:
    require(version == ST3GG_COMPATIBILITY_VERSION, "compatibility_version_changed")
    require(mode == EXECUTION_MODE, "compatibility_mode_changed")
    require(owner == V1_STORAGE_OWNER, "v1_storage_owner_changed")
    require(
        proposal is True and authority == PATCH_AUTHORITY and st3gg_authority is False,
        "compatibility_authority_changed",
    )


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ST3GGCompatibilityError(reason)
