from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from typing import Any, Mapping
from zipfile import BadZipFile, ZipFile
import json

from k27_memory_city_spatial_seam import (
    ARCHIVE_SHA256,
    ROUTE_TRANSITION,
    SCENE_SOURCE_SHA256,
    SeamDisposition,
    validate_spatial_seam,
)

PROVENANCE_MANIFEST_SHA256 = "1c8c69ab9d3c8ed9a7badff9fb22da187cbc22c73019210b4dc2194690e1588b"
PROVENANCE_MANIFEST_CANONICAL_ROOT = "266fe9d98f3d6701e484675ebd9061c2cd7756be382df0035793d66f6a56e1b2"
PROVENANCE_SCHEMA = "aura-k27-provenance-v1"
PROVENANCE_PAYLOAD_FILE_COUNT = 69
ARCHIVE_MANIFEST_PATH = "PROVENANCE_MANIFEST.json"
ARCHIVE_SCENE_PATH = "k27_memory/cold_sources/MC-SRC-O1O9.md"
EXPECTED_BINDING_KEYS = frozenset({
    "binding_schema", "source_root", "provenance_archive_sha256", "scene_source",
    "scene_source_sha256", "embedded_scene_compiler", "scene_schema", "adapters",
    "projection_laws", "read_apis", "strict_hold_unknown", "projection_only",
    "renderer_authority", "execution_authority", "effect_authority", "gate10",
})


def _sha(data: bytes) -> str:
    return sha256(data).hexdigest()


def _root(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class HardenedReceipt:
    disposition: SeamDisposition
    reasons: tuple[str, ...]
    base_receipt_root: str | None
    manifest_sha256: str
    archive_sha256: str
    authority_minted: bool = False
    gate10: bool = False


def validate_hardened(route_bytes: bytes, manifest_bytes: bytes, archive_bytes: bytes) -> HardenedReceipt:
    """D0 donor: exact route shape + archive -> manifest -> scene-source provenance chain."""
    reasons: list[str] = []
    manifest_sha, archive_sha = _sha(manifest_bytes), _sha(archive_bytes)

    try:
        route = json.loads(route_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return HardenedReceipt(SeamDisposition.HOLD, ("ROUTE_JSON_INVALID",), None, manifest_sha, archive_sha)
    if not isinstance(route, Mapping):
        return HardenedReceipt(SeamDisposition.HOLD, ("ROUTE_ROOT_INVALID",), None, manifest_sha, archive_sha)

    transitions = route.get("transitions")
    target = None
    if not isinstance(transitions, list):
        reasons.append("TRANSITIONS_LIST_REQUIRED")
    else:
        for idx, transition in enumerate(transitions):
            if not isinstance(transition, Mapping):
                reasons.append(f"TRANSITION_ENTRY_INVALID:{idx}")
        matches = [t for t in transitions if isinstance(t, Mapping) and t.get("transition_id") == ROUTE_TRANSITION]
        if len(matches) != 1:
            reasons.append("COMPILE_SCENE_TRANSITION_NOT_EXACTLY_ONE")
        else:
            target = matches[0]

    if target is not None:
        binding = target.get("memory_city_binding")
        if not isinstance(binding, Mapping):
            reasons.append("MEMORY_CITY_BINDING_MISSING")
        else:
            unknown = sorted(set(binding) - EXPECTED_BINDING_KEYS)
            missing = sorted(EXPECTED_BINDING_KEYS - set(binding))
            reasons.extend(f"UNKNOWN_BINDING_KEY:{key}" for key in unknown)
            reasons.extend(f"MISSING_BINDING_KEY:{key}" for key in missing)
            if binding.get("strict_hold_unknown") is not True:
                reasons.append("STRICT_HOLD_UNKNOWN_REQUIRED")

    if archive_sha != ARCHIVE_SHA256:
        reasons.append("PROVENANCE_ARCHIVE_BYTES_MISMATCH")
    if manifest_sha != PROVENANCE_MANIFEST_SHA256:
        reasons.append("PROVENANCE_MANIFEST_BYTES_MISMATCH")

    manifest: Mapping[str, Any] | None = None
    try:
        parsed = json.loads(manifest_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError):
        reasons.append("PROVENANCE_MANIFEST_JSON_INVALID")
    else:
        if not isinstance(parsed, Mapping):
            reasons.append("PROVENANCE_MANIFEST_ROOT_INVALID")
        else:
            manifest = parsed
            if parsed.get("schema") != PROVENANCE_SCHEMA:
                reasons.append("PROVENANCE_SCHEMA_MISMATCH")
            if parsed.get("payload_file_count") != PROVENANCE_PAYLOAD_FILE_COUNT:
                reasons.append("PROVENANCE_PAYLOAD_COUNT_MISMATCH")
            if _root(parsed) != PROVENANCE_MANIFEST_CANONICAL_ROOT:
                reasons.append("PROVENANCE_MANIFEST_IDENTITY_MISMATCH")
            files = parsed.get("files")
            if not isinstance(files, Mapping) or len(files) != PROVENANCE_PAYLOAD_FILE_COUNT:
                reasons.append("PROVENANCE_FILE_SET_MISMATCH")
            else:
                scene = files.get(ARCHIVE_SCENE_PATH)
                if not isinstance(scene, Mapping) or scene.get("sha256") != SCENE_SOURCE_SHA256:
                    reasons.append("PROVENANCE_SCENE_SOURCE_NOT_PINNED")

    try:
        with ZipFile(BytesIO(archive_bytes)) as archive:
            embedded_manifest = archive.read(ARCHIVE_MANIFEST_PATH)
            scene_source = archive.read(ARCHIVE_SCENE_PATH)
    except (BadZipFile, KeyError):
        reasons.append("PROVENANCE_ARCHIVE_STRUCTURE_INVALID")
    else:
        if embedded_manifest != manifest_bytes:
            reasons.append("ARCHIVE_MANIFEST_MEMBERSHIP_MISMATCH")
        if _sha(scene_source) != SCENE_SOURCE_SHA256:
            reasons.append("ARCHIVE_SCENE_SOURCE_BYTES_MISMATCH")

    base_root = None
    if manifest is not None:
        base = validate_spatial_seam(route_bytes, manifest)
        base_root = base.receipt_root
        reasons.extend(base.reasons)

    reasons = sorted(set(reasons))
    return HardenedReceipt(
        SeamDisposition.READY_FOR_INDEPENDENT_REVIEW if not reasons else SeamDisposition.HOLD,
        tuple(reasons), base_root, manifest_sha, archive_sha,
    )
