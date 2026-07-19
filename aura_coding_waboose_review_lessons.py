"""Typed PR-review lessons, detectors, Crucible replay, and durable engine.

External reviewers are teacher signals, never patch authority. This facade
composes bounded contracts, deterministic detector packs, review normalization,
and the repository-bound lesson engine without granting mutation authority.
"""
from __future__ import annotations

from aura_review_lessons_contracts import (
    CRUCIBLE_REPLAY_VERSION,
    DEFAULT_LEARNING_ROOT,
    DEFAULT_REGISTRY_PATH,
    PATCH_AUTHORITY,
    REGISTRY_VERSION,
    REVIEW_FINDING_VERSION,
    REVIEW_LESSON_VERSION,
    VSA_PATCH_AUTHORITY,
    ReviewLessonError,
)
from aura_review_lessons_determinism import (
    detect_implicit_coordinate_basis_change,
    detect_nested_unit_double_application,
    detect_noncanonical_interchange_acceptance,
    detect_order_dependent_digesting,
    detect_truncate_before_sort,
)
from aura_review_lessons_engine import ReviewLessonEngine
from aura_review_lessons_external import normalize_external_review
from aura_review_lessons_registry import (
    DETECTORS,
    load_review_lesson_registry,
    validate_review_lesson_registry,
)
from aura_review_lessons_replay import run_crucible_replay, run_review_detector
from aura_review_lessons_security import (
    detect_authority_aliases,
    detect_count_without_byte_budget,
    detect_noncanonical_source_path,
    detect_protected_metadata_overrides,
    detect_schema_runtime_drift,
    detect_stale_evidence_claim,
    detect_unwired_regression,
    detect_uri_alias_encoding,
)
from aura_review_lessons_source_scan import scan_source_for_review_lessons

__all__ = [
    "CRUCIBLE_REPLAY_VERSION", "DEFAULT_LEARNING_ROOT", "DEFAULT_REGISTRY_PATH",
    "DETECTORS", "PATCH_AUTHORITY", "REGISTRY_VERSION", "REVIEW_FINDING_VERSION",
    "REVIEW_LESSON_VERSION", "VSA_PATCH_AUTHORITY", "ReviewLessonEngine",
    "ReviewLessonError", "detect_authority_aliases",
    "detect_count_without_byte_budget", "detect_implicit_coordinate_basis_change",
    "detect_nested_unit_double_application",
    "detect_noncanonical_interchange_acceptance", "detect_noncanonical_source_path",
    "detect_order_dependent_digesting", "detect_protected_metadata_overrides",
    "detect_schema_runtime_drift", "detect_stale_evidence_claim",
    "detect_truncate_before_sort", "detect_unwired_regression",
    "detect_uri_alias_encoding", "load_review_lesson_registry",
    "normalize_external_review", "run_crucible_replay", "run_review_detector",
    "scan_source_for_review_lessons", "validate_review_lesson_registry",
]
