#!/usr/bin/env python3
"""Provider-neutral Creator Studio timeline and canonical tag-set contract.

This module consumes already-admitted Arena asset references. It does not verify
assets, call providers, mint semantic K27 identity, or serialize private editor
project formats. The canonical interchange target is OpenTimelineIO JSON.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Iterable

import opentimelineio as otio

SCHEMA = "AURA_CREATOR_TIMELINE_V1"
TAG_SCHEMA = "AURA_TAG_SET_V1"
OTIO_ADAPTER = "otio_json"
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")


class TimelineContractError(ValueError):
    pass


def _clean_text(value: str, *, field_name: str, max_len: int = 512) -> str:
    if not isinstance(value, str):
        raise TimelineContractError(f"{field_name}:STRING_REQUIRED")
    normalized = unicodedata.normalize("NFKC", value)
    normalized = " ".join(normalized.strip().split())
    if not normalized:
        raise TimelineContractError(f"{field_name}:EMPTY")
    if len(normalized) > max_len:
        raise TimelineContractError(f"{field_name}:TOO_LONG")
    if any(ord(ch) < 0x20 and ch not in "\t\n\r" for ch in normalized):
        raise TimelineContractError(f"{field_name}:CONTROL_CHARACTER")
    return normalized


def _clean_id(value: str, *, field_name: str) -> str:
    cleaned = _clean_text(value, field_name=field_name, max_len=128)
    if not _ID_RE.fullmatch(cleaned):
        raise TimelineContractError(f"{field_name}:INVALID_ID")
    return cleaned


def canonical_tag_set(tags: Iterable[str]) -> tuple[str, ...]:
    """Canonicalize semantic tags as an unordered set, not an input sequence.

    NFKC + whitespace collapse + casefold is part of TAG_SCHEMA V1. Empty tags
    are invalid rather than silently discarded.
    """
    canonical: set[str] = set()
    for tag in tags:
        cleaned = _clean_text(tag, field_name="tag", max_len=256).casefold()
        canonical.add(cleaned)
    if not canonical:
        raise TimelineContractError("tags:EMPTY_SET")
    return tuple(sorted(canonical))


def tag_set_fingerprint(tags: Iterable[str]) -> str:
    canonical = canonical_tag_set(tags)
    h = hashlib.sha256()
    h.update(TAG_SCHEMA.encode("ascii"))
    h.update(b"\x00")
    for tag in canonical:
        raw = tag.encode("utf-8")
        h.update(len(raw).to_bytes(4, "big"))
        h.update(raw)
    return h.hexdigest()


@dataclass(frozen=True)
class AdmittedAssetRefV1:
    """A read-only reference issued by a higher Arena asset owner.

    `verified` is intentionally absent: this layer cannot upgrade evidence.
    Provider/model/task metadata is intentionally absent from composition
    identity so provider fallback does not silently redefine the edit.
    """

    asset_id: str
    uri: str
    evidence_ref: str
    media_type: str = "video"
    tags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "asset_id", _clean_id(self.asset_id, field_name="asset_id"))
        object.__setattr__(self, "uri", _clean_text(self.uri, field_name="uri", max_len=4096))
        object.__setattr__(self, "evidence_ref", _clean_text(self.evidence_ref, field_name="evidence_ref", max_len=1024))
        media_type = _clean_text(self.media_type, field_name="media_type", max_len=64).casefold()
        if media_type not in {"video", "audio", "image"}:
            raise TimelineContractError("media_type:UNSUPPORTED")
        object.__setattr__(self, "media_type", media_type)
        object.__setattr__(self, "tags", canonical_tag_set(self.tags))

    @property
    def tag_fingerprint(self) -> str:
        return tag_set_fingerprint(self.tags)


@dataclass(frozen=True)
class TimelineClipV1:
    clip_id: str
    asset: AdmittedAssetRefV1
    source_start_frame: int
    duration_frames: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "clip_id", _clean_id(self.clip_id, field_name="clip_id"))
        if not isinstance(self.source_start_frame, int) or self.source_start_frame < 0:
            raise TimelineContractError("source_start_frame:NONNEGATIVE_INT_REQUIRED")
        if not isinstance(self.duration_frames, int) or self.duration_frames <= 0:
            raise TimelineContractError("duration_frames:POSITIVE_INT_REQUIRED")


@dataclass(frozen=True)
class CreatorTimelineV1:
    name: str
    rate_num: int
    rate_den: int
    clips: tuple[TimelineClipV1, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _clean_text(self.name, field_name="name", max_len=256))
        if not isinstance(self.rate_num, int) or not isinstance(self.rate_den, int):
            raise TimelineContractError("rate:INTEGER_RATIONAL_REQUIRED")
        if self.rate_num <= 0 or self.rate_den <= 0:
            raise TimelineContractError("rate:POSITIVE_RATIONAL_REQUIRED")
        if self.rate_num > 240_000 or self.rate_den > 1001:
            raise TimelineContractError("rate:OUT_OF_BOUNDS")
        if not isinstance(self.clips, tuple) or not self.clips:
            raise TimelineContractError("clips:NONEMPTY_TUPLE_REQUIRED")
        clip_ids = [clip.clip_id for clip in self.clips]
        if len(set(clip_ids)) != len(clip_ids):
            raise TimelineContractError("clip_id:DUPLICATE")

    @property
    def rate(self) -> Fraction:
        return Fraction(self.rate_num, self.rate_den)

    def _composition_record(self) -> dict[str, object]:
        return {
            "schema": SCHEMA,
            "rate_num": self.rate_num,
            "rate_den": self.rate_den,
            "clips": [
                {
                    "clip_id": clip.clip_id,
                    "asset_id": clip.asset.asset_id,
                    "source_start_frame": clip.source_start_frame,
                    "duration_frames": clip.duration_frames,
                }
                for clip in self.clips
            ],
        }

    def _evidence_record(self) -> dict[str, object]:
        return {
            "schema": f"{SCHEMA}:EVIDENCE",
            "composition_digest": self.composition_digest,
            "assets": [
                {
                    "asset_id": clip.asset.asset_id,
                    "evidence_ref": clip.asset.evidence_ref,
                    "uri": clip.asset.uri,
                    "tag_fingerprint": clip.asset.tag_fingerprint,
                }
                for clip in self.clips
            ],
        }

    @property
    def composition_digest(self) -> str:
        raw = json.dumps(self._composition_record(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()

    @property
    def evidence_binding_digest(self) -> str:
        raw = json.dumps(self._evidence_record(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()

    def to_otio(self) -> otio.schema.Timeline:
        rate = float(self.rate)
        timeline = otio.schema.Timeline(name=self.name)
        timeline.metadata["aura"] = {
            "schema": SCHEMA,
            "rate_num": self.rate_num,
            "rate_den": self.rate_den,
            "composition_digest": self.composition_digest,
            "evidence_binding_digest": self.evidence_binding_digest,
            "semantic_k27_authority": False,
            "capcut_private_draft_compatibility_proven": False,
        }
        track = otio.schema.Track(name="V1", kind=otio.schema.TrackKind.Video)
        for clip in self.clips:
            ref = otio.schema.ExternalReference(target_url=clip.asset.uri)
            source_range = otio.opentime.TimeRange(
                start_time=otio.opentime.RationalTime(clip.source_start_frame, rate),
                duration=otio.opentime.RationalTime(clip.duration_frames, rate),
            )
            item = otio.schema.Clip(
                name=clip.clip_id,
                media_reference=ref,
                source_range=source_range,
            )
            item.metadata["aura"] = {
                "asset_id": clip.asset.asset_id,
                "evidence_ref": clip.asset.evidence_ref,
                "tag_fingerprint": clip.asset.tag_fingerprint,
                "media_type": clip.asset.media_type,
            }
            track.append(item)
        timeline.tracks.append(track)
        return timeline

    def to_otio_json(self) -> str:
        return otio.adapters.write_to_string(self.to_otio(), adapter_name=OTIO_ADAPTER)


def validate_otio_roundtrip(source: CreatorTimelineV1, payload: str) -> dict[str, object]:
    timeline = otio.adapters.read_from_string(payload, adapter_name=OTIO_ADAPTER)
    tracks = list(timeline.tracks)
    if len(tracks) != 1:
        raise TimelineContractError("otio:TRACK_COUNT_MISMATCH")
    clips = list(tracks[0])
    if len(clips) != len(source.clips):
        raise TimelineContractError("otio:CLIP_COUNT_MISMATCH")
    rate = float(source.rate)
    for expected, observed in zip(source.clips, clips, strict=True):
        if observed.name != expected.clip_id:
            raise TimelineContractError("otio:CLIP_ORDER_OR_ID_MISMATCH")
        if observed.metadata.get("aura", {}).get("asset_id") != expected.asset.asset_id:
            raise TimelineContractError("otio:ASSET_ID_MISMATCH")
        if observed.source_range is None:
            raise TimelineContractError("otio:MISSING_SOURCE_RANGE")
        if observed.source_range.start_time.to_frames(rate) != expected.source_start_frame:
            raise TimelineContractError("otio:SOURCE_START_MISMATCH")
        if observed.source_range.duration.to_frames(rate) != expected.duration_frames:
            raise TimelineContractError("otio:DURATION_MISMATCH")
    aura_meta = timeline.metadata.get("aura", {})
    if aura_meta.get("composition_digest") != source.composition_digest:
        raise TimelineContractError("otio:COMPOSITION_DIGEST_MISMATCH")
    if aura_meta.get("evidence_binding_digest") != source.evidence_binding_digest:
        raise TimelineContractError("otio:EVIDENCE_DIGEST_MISMATCH")
    return {
        "schema": SCHEMA,
        "otio_roundtrip_equivalent": True,
        "clip_order_preserved": True,
        "timing_preserved": True,
        "asset_identity_preserved": True,
        "composition_digest": source.composition_digest,
        "evidence_binding_digest": source.evidence_binding_digest,
        "provider_specific_fields_in_composition_identity": False,
        "capcut_private_draft_compatibility_proven": False,
        "asset_verification_minted_by_timeline_layer": False,
        "semantic_k27_authority": False,
        "native_transformer_kv_accessed": False,
    }
