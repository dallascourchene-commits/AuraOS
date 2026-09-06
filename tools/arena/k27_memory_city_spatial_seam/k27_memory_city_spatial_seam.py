from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence
import json

D0 = "D0"
ROUTE_TRANSITION = "SPATIAL.GROUND.COMPILE_SCENE"
BINDING_SCHEMA = "AURA-K27-SPATIAL-SEAM-v1"
SOURCE_ROOT = "outputs/k27_memory/"
ARCHIVE_SHA256 = "042e78055f23def062e07aaf412524be01a590f969d8f474c143b34f6b45c319"
SCENE_SOURCE = "outputs/k27_memory/cold_sources/MC-SRC-O1O9.md"
SCENE_SOURCE_SHA256 = "b2cb2a2c1ebe65848d61da4db6225dbce2c686357bb427e1584468c44787a5a7"
EMBEDDED_SCENE_COMPILER = "o2/src/aura_xr/xr_scene.py"
SCENE_SCHEMA = "AURA-XR-SCENE-v1"
ADAPTERS = ("desktop_webgl", "webxr", "openxr")
PROJECTION_LAWS = (
    "SceneLabel!=CanonicalID",
    "Anchor!=Authority",
    "Visible!=Hydrated",
    "Gesture!=Effect",
)
READ_APIS = (
    "CITY_K27_CONTEXT",
    "CITY_SCENE_SHELL",
    "CITY_ROUTE",
    "CITY_WHY",
    "CITY_ACTIVE_DOMAINS",
    "CITY_INVALIDATION_CONE",
)


class SeamDisposition(str, Enum):
    READY_FOR_INDEPENDENT_REVIEW = "READY_FOR_INDEPENDENT_REVIEW"
    HOLD = "HOLD"


@dataclass(frozen=True)
class SeamReceipt:
    disposition: SeamDisposition
    reasons: tuple[str, ...]
    route_sha256: str
    binding_root: str | None
    adapters: tuple[str, ...]
    read_apis: tuple[str, ...]
    authority_ceiling: str = D0
    authority_minted: bool = False
    gate10: bool = False
    execution_authority: bool = False
    effect_authority: bool = False

    @property
    def receipt_root(self) -> str:
        payload = asdict(self)
        payload["disposition"] = self.disposition.value
        return _digest(payload)


def _digest(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def _find_transition(route: Mapping[str, Any]) -> Mapping[str, Any] | None:
    for transition in route.get("transitions", ()):  # type: ignore[union-attr]
        if isinstance(transition, Mapping) and transition.get("transition_id") == ROUTE_TRANSITION:
            return transition
    return None


def _authority_false(reasons: list[str], label: str, value: Any) -> None:
    if value is not False:
        reasons.append(f"{label}_MUST_BE_FALSE")


def validate_spatial_seam(route_bytes: bytes, provenance_manifest: Mapping[str, Any]) -> SeamReceipt:
    reasons: list[str] = []
    route_sha = _sha256_bytes(route_bytes)
    try:
        route = json.loads(route_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return SeamReceipt(SeamDisposition.HOLD, ("ROUTE_JSON_INVALID",), route_sha, None, (), ())
    if not isinstance(route, Mapping):
        return SeamReceipt(SeamDisposition.HOLD, ("ROUTE_ROOT_INVALID",), route_sha, None, (), ())

    transition = _find_transition(route)
    binding: Mapping[str, Any] | None = None
    if transition is None:
        reasons.append("COMPILE_SCENE_TRANSITION_MISSING")
    else:
        candidate = transition.get("memory_city_binding")
        if not isinstance(candidate, Mapping):
            reasons.append("MEMORY_CITY_BINDING_MISSING")
        else:
            binding = candidate

    adapters: tuple[str, ...] = ()
    read_apis: tuple[str, ...] = ()
    binding_root: str | None = None
    if binding is not None:
        binding_root = _digest(binding)
        if binding.get("binding_schema") != BINDING_SCHEMA:
            reasons.append("BINDING_SCHEMA_MISMATCH")
        if binding.get("source_root") != SOURCE_ROOT:
            reasons.append("SOURCE_ROOT_MISMATCH")
        if binding.get("provenance_archive_sha256") != ARCHIVE_SHA256:
            reasons.append("ARCHIVE_DIGEST_MISMATCH")
        if binding.get("scene_source") != SCENE_SOURCE:
            reasons.append("SCENE_SOURCE_MISMATCH")
        if binding.get("scene_source_sha256") != SCENE_SOURCE_SHA256:
            reasons.append("SCENE_SOURCE_DIGEST_MISMATCH")
        if binding.get("embedded_scene_compiler") != EMBEDDED_SCENE_COMPILER:
            reasons.append("SCENE_COMPILER_PATH_MISMATCH")
        if binding.get("scene_schema") != SCENE_SCHEMA:
            reasons.append("SCENE_SCHEMA_MISMATCH")

        raw_adapters = binding.get("adapters")
        if isinstance(raw_adapters, list) and all(type(x) is str for x in raw_adapters):
            adapters = tuple(raw_adapters)
        if adapters != ADAPTERS:
            reasons.append("ADAPTER_SET_OR_ORDER_MISMATCH")

        raw_laws = binding.get("projection_laws")
        laws = tuple(raw_laws) if isinstance(raw_laws, list) and all(type(x) is str for x in raw_laws) else ()
        if laws != PROJECTION_LAWS:
            reasons.append("PROJECTION_LAWS_MISMATCH")

        raw_apis = binding.get("read_apis")
        if isinstance(raw_apis, Mapping):
            read_apis = tuple(raw_apis.keys())
            if set(raw_apis.keys()) != set(READ_APIS):
                reasons.append("READ_API_SET_MISMATCH")
            for api in READ_APIS:
                if raw_apis.get(api) != "REVIEW_ONLY":
                    reasons.append(f"{api}_NOT_REVIEW_ONLY")
        else:
            reasons.append("READ_APIS_INVALID")

        if binding.get("strict_hold_unknown") is not True:
            reasons.append("STRICT_HOLD_UNKNOWN_REQUIRED")
        if binding.get("projection_only") is not True:
            reasons.append("PROJECTION_ONLY_REQUIRED")
        _authority_false(reasons, "BINDING_RENDERER_AUTHORITY", binding.get("renderer_authority"))
        _authority_false(reasons, "BINDING_EXECUTION_AUTHORITY", binding.get("execution_authority"))
        _authority_false(reasons, "BINDING_EFFECT_AUTHORITY", binding.get("effect_authority"))
        _authority_false(reasons, "BINDING_GATE10", binding.get("gate10"))

    route_authority = route.get("authority")
    if not isinstance(route_authority, Mapping):
        reasons.append("ROUTE_AUTHORITY_INVALID")
    else:
        _authority_false(reasons, "ROUTE_RENDERER_AUTHORITY", route_authority.get("renderer_authority"))
        _authority_false(reasons, "ROUTE_EXECUTION_AUTHORITY", route_authority.get("execution_authority"))
        _authority_false(reasons, "ROUTE_AUTOMATIC_PROMOTION", route_authority.get("automatic_grammar_promotion"))
        _authority_false(reasons, "ROUTE_AUTOMATIC_MERGE", route_authority.get("automatic_merge"))

    files = provenance_manifest.get("files") if isinstance(provenance_manifest, Mapping) else None
    if not isinstance(files, Mapping):
        reasons.append("PROVENANCE_FILES_MISSING")
    else:
        source_entry = files.get("k27_memory/cold_sources/MC-SRC-O1O9.md")
        if not isinstance(source_entry, Mapping) or source_entry.get("sha256") != SCENE_SOURCE_SHA256:
            reasons.append("PROVENANCE_SCENE_SOURCE_NOT_PINNED")

    reasons = sorted(set(reasons))
    return SeamReceipt(
        SeamDisposition.READY_FOR_INDEPENDENT_REVIEW if not reasons else SeamDisposition.HOLD,
        tuple(reasons),
        route_sha,
        binding_root,
        adapters,
        tuple(sorted(read_apis)),
    )


def validate_files(route_path: str | Path, manifest_path: str | Path) -> SeamReceipt:
    route_bytes = Path(route_path).read_bytes()
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    return validate_spatial_seam(route_bytes, manifest)


def validate_scene_source_snapshot(snapshot_bytes: bytes) -> tuple[bool, tuple[str, ...]]:
    """Validate the frozen provenance source that supplies the scene/interface contract.

    This proves byte identity + interface declarations only. It does not execute a renderer.
    """
    reasons: list[str] = []
    if _sha256_bytes(snapshot_bytes) != SCENE_SOURCE_SHA256:
        reasons.append("SCENE_SOURCE_BYTES_NOT_PINNED")
    try:
        text = snapshot_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return False, ("SCENE_SOURCE_NOT_UTF8",)
    required = (
        "SceneManifest('AURA-XR-SCENE-v1'",
        "adapters:Tuple[str,...]=('desktop_webgl','webxr','openxr')",
        "'desktop':('desktop_webgl',400,'mouse-keyboard')",
        "'webxr':('webxr',180,'6dof')",
        "'openxr':('openxr',220,'6dof')",
        "'SceneLabel!=CanonicalID','Anchor!=Authority','Visible!=Hydrated','Gesture!=Effect'",
    )
    for fragment in required:
        if fragment not in text:
            reasons.append("SCENE_SOURCE_INTERFACE_FRAGMENT_MISSING:" + fragment)
    return not reasons, tuple(reasons)
