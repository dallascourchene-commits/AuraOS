#!/usr/bin/env python3
"""NAV-03B: bind an exact EKI version candidate to fractal K27 locality.

Version selection remains owned by the subject-version resolver. K27 remains
routing/locality metadata only. This adapter may expose a selected version's
path and the first micro-level that distinguishes it from historical version
placements, but it can never use locality to choose a version, prove freshness,
or widen read/write/effect authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from typing import Iterable

from tools.aura_external_cognition_subject_version_resolver import (
    SubjectVersionDisposition,
    SubjectVersionResolutionReceiptV1,
)
from tools.aura_fractal_k27 import (
    K27Candidate,
    K27Path,
    ZoomDisposition,
    prove_different_j,
)

SCHEMA = "AURA-NAV03B-VERSION-SAFE-FRACTAL-K27-v1"


class VersionK27Disposition(str, Enum):
    NAVIGATION_BOUND_SINGLE = "NAVIGATION_BOUND_SINGLE"
    NAVIGATION_BOUND_DISTINGUISHED = "NAVIGATION_BOUND_DISTINGUISHED"
    HOLD_LOCALITY_COLLISION = "HOLD_LOCALITY_COLLISION"
    HOLD_ANCESTOR_DESCENDANT_COLLISION = "HOLD_ANCESTOR_DESCENDANT_COLLISION"


def _canon(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _sha(value: object) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


@dataclass(frozen=True)
class VersionK27PlacementV1:
    record_key: str
    record_generation: str
    path: K27Path

    def validate(self) -> None:
        if not isinstance(self.record_key, str) or not self.record_key.strip():
            raise ValueError("VERSION_RECORD_KEY_REQUIRED")
        if not isinstance(self.record_generation, str) or len(self.record_generation) != 64:
            raise ValueError("VERSION_RECORD_GENERATION_SHA256_REQUIRED")
        int(self.record_generation, 16)
        if not isinstance(self.path, K27Path):
            raise ValueError("TYPED_K27_PATH_REQUIRED")


@dataclass(frozen=True)
class VersionSafeK27NavigationReceiptV1:
    schema: str
    disposition: VersionK27Disposition
    semantic_subject_id: str
    store_generation: str
    version_record_key: str
    version_record_generation: str
    selected_k27_path: str
    compared_version_count: int
    distinguishing_micro_depth: int | None
    collision_record_keys: tuple[str, ...]
    resolver_receipt_digest: str
    reason: str
    version_selected_by_k27: bool = False
    source_currentness_proven: bool = False
    read_time_currentness_required: bool = True
    semantic_identity_from_k27: bool = False
    version_order_from_k27: bool = False
    semantic_truth_proven: bool = False
    read_authority: bool = False
    write_authority: bool = False
    effect_authority: bool = False
    native_private_transformer_kv_accessed: bool = False

    @property
    def receipt_digest(self) -> str:
        return _sha({"domain": SCHEMA, "receipt": asdict(self)})


def bind_version_candidate_to_k27(
    *,
    resolution: SubjectVersionResolutionReceiptV1,
    placements: Iterable[VersionK27PlacementV1],
) -> VersionSafeK27NavigationReceiptV1:
    """Bind a resolver-selected version to locality without rerunning selection."""
    if not isinstance(resolution, SubjectVersionResolutionReceiptV1):
        raise TypeError("SUBJECT_VERSION_RESOLUTION_RECEIPT_REQUIRED")
    if resolution.disposition is not SubjectVersionDisposition.SELECTED_VERSION_CANDIDATE:
        raise ValueError("SELECTED_VERSION_CANDIDATE_REQUIRED")
    if not resolution.candidate_record_key or not resolution.candidate_record_generation:
        raise ValueError("RESOLUTION_CANDIDATE_IDENTITY_REQUIRED")
    if resolution.source_currentness_proven or resolution.selected_head_is_currentness_witness:
        raise ValueError("RESOLUTION_CURRENTNESS_CEILING_WIDENED")
    if resolution.k27_used_for_version_selection:
        raise ValueError("K27_MUST_NOT_HAVE_SELECTED_VERSION")

    items = tuple(placements)
    if not items:
        raise ValueError("AT_LEAST_ONE_VERSION_PLACEMENT_REQUIRED")
    for item in items:
        item.validate()
    keys = [item.record_key for item in items]
    if len(keys) != len(set(keys)):
        raise ValueError("VERSION_PLACEMENT_KEYS_MUST_BE_UNIQUE")

    selected = [item for item in items if item.record_key == resolution.candidate_record_key]
    if len(selected) != 1:
        raise ValueError("SELECTED_VERSION_PLACEMENT_REQUIRED_EXACTLY_ONCE")
    chosen = selected[0]
    if chosen.record_generation != resolution.candidate_record_generation:
        raise ValueError("SELECTED_VERSION_GENERATION_MISMATCH")

    historical_keys = set(resolution.historical_record_keys)
    foreign = [item.record_key for item in items if item.record_key != chosen.record_key and item.record_key not in historical_keys]
    if foreign:
        raise ValueError("PLACEMENT_NOT_SELECTED_OR_HISTORICAL_VERSION")

    common = dict(
        schema=SCHEMA,
        semantic_subject_id=resolution.semantic_subject_id,
        store_generation=resolution.store_generation,
        version_record_key=chosen.record_key,
        version_record_generation=chosen.record_generation,
        selected_k27_path=str(chosen.path),
        compared_version_count=len(items),
        resolver_receipt_digest=resolution.receipt_digest,
    )

    if len(items) == 1:
        return VersionSafeK27NavigationReceiptV1(
            **common,
            disposition=VersionK27Disposition.NAVIGATION_BOUND_SINGLE,
            distinguishing_micro_depth=None,
            collision_record_keys=(),
            reason="SINGLE_SELECTED_VERSION_LOCALITY_BOUND_WITH_READ_TIME_CURRENTNESS_DEBT",
        )

    zoom = prove_different_j(K27Candidate(item.record_key, item.path) for item in items)
    if zoom.disposition is ZoomDisposition.LOCALITY_COLLISION:
        collisions = tuple(sorted(item.record_key for item in items if item.path == chosen.path and item.record_key != chosen.record_key))
        return VersionSafeK27NavigationReceiptV1(
            **common,
            disposition=VersionK27Disposition.HOLD_LOCALITY_COLLISION,
            distinguishing_micro_depth=None,
            collision_record_keys=collisions,
            reason="EXACT_LOCALITY_COLLISION_CANNOT_COLLAPSE_DISTINCT_VERSION_IDENTITIES",
        )
    if zoom.disposition is ZoomDisposition.ANCESTOR_DESCENDANT_COLLISION:
        collisions = tuple(sorted(item.record_key for item in items if item.record_key != chosen.record_key))
        return VersionSafeK27NavigationReceiptV1(
            **common,
            disposition=VersionK27Disposition.HOLD_ANCESTOR_DESCENDANT_COLLISION,
            distinguishing_micro_depth=None,
            collision_record_keys=collisions,
            reason="ANCESTRY_LOCALITY_CANNOT_INFER_VERSION_ORDER_OR_SUPERSESSION",
        )
    return VersionSafeK27NavigationReceiptV1(
        **common,
        disposition=VersionK27Disposition.NAVIGATION_BOUND_DISTINGUISHED,
        distinguishing_micro_depth=zoom.distinguishing_micro_depth,
        collision_record_keys=(),
        reason="VERSION_ALREADY_SELECTED_BY_EXPLICIT_SUPERSESSION_GRAPH;_K27_ONLY_BOUNDS_LOCALITY_ZOOM",
    )


__all__ = [
    "SCHEMA",
    "VersionK27Disposition",
    "VersionK27PlacementV1",
    "VersionSafeK27NavigationReceiptV1",
    "bind_version_candidate_to_k27",
]
