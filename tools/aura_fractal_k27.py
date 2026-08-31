#!/usr/bin/env python3
"""NAV-03A: legacy-compatible recursive K27 path codec and adaptive zoom.

K27 remains routing/locality metadata only. A legacy K27 XYZ segment has three
axes in [0,26]. Each axis is exactly three base-3 digits, so one legacy segment
can be losslessly interpreted as three nested local 3x3x3 micro-cells without
changing the existing segment identity.

This module proves representation and resolution mechanics only. It does not
grant semantic identity, evidence rank, currentness, authority, hydration, or
effect permission.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Sequence

SCHEMA = "AURA-FRACTAL-K27-PATH-v1"
AXIS_RADIX = 27
TRIT_RADIX = 3
TRITS_PER_SEGMENT = 3


class K27Error(ValueError):
    pass


class ZoomDisposition(str, Enum):
    DISTINGUISHED = "DISTINGUISHED"
    LOCALITY_COLLISION = "LOCALITY_COLLISION"
    ANCESTOR_DESCENDANT_COLLISION = "ANCESTOR_DESCENDANT_COLLISION"


def _axis_to_trits(value: int) -> tuple[int, int, int]:
    if type(value) is not int or not 0 <= value < AXIS_RADIX:
        raise K27Error("K27_AXIS_MUST_BE_INTEGER_0_TO_26")
    return (value // 9, (value // 3) % 3, value % 3)


def _trits_to_axis(trits: Sequence[int]) -> int:
    if len(trits) != TRITS_PER_SEGMENT:
        raise K27Error("K27_AXIS_REQUIRES_EXACTLY_THREE_TRITS")
    if any(type(t) is not int or not 0 <= t < TRIT_RADIX for t in trits):
        raise K27Error("K27_TRIT_MUST_BE_INTEGER_0_TO_2")
    return 9 * trits[0] + 3 * trits[1] + trits[2]


@dataclass(frozen=True, order=True)
class K27Segment:
    x: int
    y: int
    z: int

    def validate(self) -> None:
        for value in (self.x, self.y, self.z):
            _axis_to_trits(value)

    def to_micro_levels(self) -> tuple[tuple[int, int, int], ...]:
        self.validate()
        xt, yt, zt = map(_axis_to_trits, (self.x, self.y, self.z))
        return tuple((xt[i], yt[i], zt[i]) for i in range(TRITS_PER_SEGMENT))

    @classmethod
    def from_micro_levels(
        cls, levels: Sequence[Sequence[int]]
    ) -> "K27Segment":
        if len(levels) != TRITS_PER_SEGMENT:
            raise K27Error("K27_SEGMENT_REQUIRES_THREE_MICRO_LEVELS")
        normalized: list[tuple[int, int, int]] = []
        for level in levels:
            if len(level) != 3:
                raise K27Error("K27_MICRO_LEVEL_MUST_BE_XYZ")
            xyz = tuple(level)
            if any(type(v) is not int or not 0 <= v < TRIT_RADIX for v in xyz):
                raise K27Error("K27_MICRO_COMPONENT_MUST_BE_INTEGER_0_TO_2")
            normalized.append(xyz)
        x = _trits_to_axis(tuple(level[0] for level in normalized))
        y = _trits_to_axis(tuple(level[1] for level in normalized))
        z = _trits_to_axis(tuple(level[2] for level in normalized))
        return cls(x, y, z)

    def __str__(self) -> str:
        return f"{self.x}.{self.y}.{self.z}"


@dataclass(frozen=True)
class K27Path:
    segments: tuple[K27Segment, ...]

    def __post_init__(self) -> None:
        if not self.segments:
            raise K27Error("K27_PATH_REQUIRES_AT_LEAST_ONE_SEGMENT")
        for segment in self.segments:
            if not isinstance(segment, K27Segment):
                raise K27Error("K27_PATH_SEGMENTS_MUST_BE_TYPED")
            segment.validate()

    @classmethod
    def parse(cls, value: str) -> "K27Path":
        if not isinstance(value, str) or not value.startswith("K27:/"):
            raise K27Error("K27_PATH_PREFIX_REQUIRED")
        body = value[5:]
        if not body:
            raise K27Error("K27_PATH_REQUIRES_SEGMENT")
        segments: list[K27Segment] = []
        for raw in body.split("/"):
            parts = raw.split(".")
            if len(parts) != 3 or any(not part.isdigit() for part in parts):
                raise K27Error("K27_PATH_SEGMENT_MUST_BE_DECIMAL_XYZ")
            segments.append(K27Segment(*(int(part) for part in parts)))
        return cls(tuple(segments))

    def __str__(self) -> str:
        return "K27:/" + "/".join(str(segment) for segment in self.segments)

    @property
    def parent(self) -> "K27Path | None":
        if len(self.segments) == 1:
            return None
        return K27Path(self.segments[:-1])

    def child(self, segment: K27Segment) -> "K27Path":
        if not isinstance(segment, K27Segment):
            raise K27Error("K27_CHILD_SEGMENT_MUST_BE_TYPED")
        return K27Path(self.segments + (segment,))

    def is_ancestor_of(self, other: "K27Path") -> bool:
        if not isinstance(other, K27Path):
            return False
        return (
            len(self.segments) < len(other.segments)
            and other.segments[: len(self.segments)] == self.segments
        )

    def micro_levels(self) -> tuple[tuple[int, int, int], ...]:
        return tuple(
            level
            for segment in self.segments
            for level in segment.to_micro_levels()
        )

    @classmethod
    def from_micro_levels(
        cls, levels: Sequence[Sequence[int]]
    ) -> "K27Path":
        if not levels or len(levels) % TRITS_PER_SEGMENT:
            raise K27Error("K27_PATH_MICRO_DEPTH_MUST_BE_POSITIVE_MULTIPLE_OF_THREE")
        segments = tuple(
            K27Segment.from_micro_levels(levels[i : i + TRITS_PER_SEGMENT])
            for i in range(0, len(levels), TRITS_PER_SEGMENT)
        )
        return cls(segments)


@dataclass(frozen=True)
class K27Candidate:
    owner_ref: str
    path: K27Path

    def validate(self) -> None:
        if not isinstance(self.owner_ref, str) or not self.owner_ref.strip():
            raise K27Error("OWNER_REF_REQUIRED")
        if not isinstance(self.path, K27Path):
            raise K27Error("K27_CANDIDATE_PATH_REQUIRED")


@dataclass(frozen=True)
class AdaptiveZoomReceipt:
    disposition: ZoomDisposition
    distinguishing_micro_depth: int | None
    common_prefix: tuple[tuple[int, int, int], ...]
    candidate_count: int
    algorithm: str
    semantic_identity: bool = False
    evidence_rank: bool = False
    currentness_witness: bool = False
    authority: bool = False
    effect_authority: bool = False
    schema: str = SCHEMA

    def validate(self) -> None:
        if not isinstance(self.disposition, ZoomDisposition):
            raise K27Error("ZOOM_DISPOSITION_MUST_BE_TYPED")
        if self.distinguishing_micro_depth is not None and (
            type(self.distinguishing_micro_depth) is not int
            or self.distinguishing_micro_depth <= 0
        ):
            raise K27Error("DISTINGUISHING_DEPTH_MUST_BE_POSITIVE")
        if self.candidate_count < 2:
            raise K27Error("ADAPTIVE_ZOOM_REQUIRES_AT_LEAST_TWO_CANDIDATES")
        if self.algorithm not in {"PAIRWISE_LCP", "PREFIX_TRIE"}:
            raise K27Error("UNKNOWN_ZOOM_ALGORITHM")
        if any(
            (
                self.semantic_identity,
                self.evidence_rank,
                self.currentness_witness,
                self.authority,
                self.effect_authority,
            )
        ):
            raise K27Error("K27_ZOOM_CANNOT_WIDEN_AUTHORITY")
        if self.schema != SCHEMA:
            raise K27Error("K27_SCHEMA_MISMATCH")


def _normalize_candidates(
    candidates: Iterable[K27Candidate],
) -> tuple[K27Candidate, ...]:
    items = tuple(candidates)
    if len(items) < 2:
        raise K27Error("ADAPTIVE_ZOOM_REQUIRES_AT_LEAST_TWO_CANDIDATES")
    for item in items:
        item.validate()
    if len({item.owner_ref for item in items}) != len(items):
        raise K27Error("OWNER_REFS_MUST_BE_UNIQUE")
    return items


def _pairwise_common_prefix(
    paths: Sequence[tuple[tuple[int, int, int], ...]],
) -> tuple[tuple[int, int, int], ...]:
    min_len = min(len(path) for path in paths)
    depth = 0
    while depth < min_len and len({path[depth] for path in paths}) == 1:
        depth += 1
    return paths[0][:depth]


def _classify_path_collision(
    paths: Sequence[tuple[tuple[int, int, int], ...]],
) -> ZoomDisposition | None:
    if len(set(paths)) != len(paths):
        return ZoomDisposition.LOCALITY_COLLISION
    for i, left in enumerate(paths):
        for right in paths[i + 1 :]:
            n = min(len(left), len(right))
            if left[:n] == right[:n]:
                return ZoomDisposition.ANCESTOR_DESCENDANT_COLLISION
    return None


def adaptive_zoom_pairwise(
    candidates: Iterable[K27Candidate],
) -> AdaptiveZoomReceipt:
    items = _normalize_candidates(candidates)
    paths = tuple(item.path.micro_levels() for item in items)
    collision = _classify_path_collision(paths)
    prefix = _pairwise_common_prefix(paths)
    if collision is not None:
        receipt = AdaptiveZoomReceipt(
            collision, None, prefix, len(items), "PAIRWISE_LCP"
        )
    else:
        receipt = AdaptiveZoomReceipt(
            ZoomDisposition.DISTINGUISHED,
            len(prefix) + 1,
            prefix,
            len(items),
            "PAIRWISE_LCP",
        )
    receipt.validate()
    return receipt


def adaptive_zoom_trie(
    candidates: Iterable[K27Candidate],
) -> AdaptiveZoomReceipt:
    items = _normalize_candidates(candidates)
    paths = tuple(item.path.micro_levels() for item in items)
    collision = _classify_path_collision(paths)
    prefix: list[tuple[int, int, int]] = []
    active = list(paths)
    depth = 0
    while True:
        if any(len(path) == depth for path in active):
            break
        children = {path[depth] for path in active}
        if len(children) != 1:
            break
        prefix.append(next(iter(children)))
        depth += 1
    if collision is not None:
        receipt = AdaptiveZoomReceipt(
            collision, None, tuple(prefix), len(items), "PREFIX_TRIE"
        )
    else:
        receipt = AdaptiveZoomReceipt(
            ZoomDisposition.DISTINGUISHED,
            depth + 1,
            tuple(prefix),
            len(items),
            "PREFIX_TRIE",
        )
    receipt.validate()
    return receipt


def prove_different_j(
    candidates: Iterable[K27Candidate],
) -> AdaptiveZoomReceipt:
    items = _normalize_candidates(candidates)
    left = adaptive_zoom_pairwise(items)
    right = adaptive_zoom_trie(items)
    comparable_left = (
        left.disposition,
        left.distinguishing_micro_depth,
        left.common_prefix,
        left.candidate_count,
    )
    comparable_right = (
        right.disposition,
        right.distinguishing_micro_depth,
        right.common_prefix,
        right.candidate_count,
    )
    if comparable_left != comparable_right:
        raise K27Error("DIFFERENT_J_RESOLVERS_DISAGREE")
    return left


def legacy_segment_micro_equivalence(
    segment: K27Segment,
) -> tuple[tuple[int, int, int], ...]:
    """Explicit compatibility witness; round-trip is mandatory."""
    levels = segment.to_micro_levels()
    if K27Segment.from_micro_levels(levels) != segment:
        raise AssertionError("K27_SEGMENT_MICRO_ROUNDTRIP_FAILED")
    return levels
