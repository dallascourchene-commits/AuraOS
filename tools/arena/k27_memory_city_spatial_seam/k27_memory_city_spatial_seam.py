from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any, Mapping
import json
import zipfile

D0 = "D0"
ROUTE_TRANSITION = "SPATIAL.GROUND.COMPILE_SCENE"
BINDING_SCHEMA = "AURA-K27-SPATIAL-SEAM-v1"
SOURCE_ROOT = "outputs/k27_memory/"
ARCHIVE_SHA256 = "042e78055f23def062e07aaf412524be01a590f969d8f474c143b34f6b45c319"
PROVENANCE_MANIFEST_SHA256 = "1c8c69ab9d3c8ed9a7badff9fb22da187cbc22c73019210b4dc2194690e1588b"
PROVENANCE_PAYLOAD_COUNT = 69
SCENE_SOURCE = "outputs/k27_memory/cold_sources/MC-SRC-O1O9.md"
ARCHIVE_SCENE_SOURCE = "k27_memory/cold_sources/MC-SRC-O1O9.md"
SCENE_SOURCE_SHA256 = "b2cb2a2c1ebe65848d61da4db6225dbce2c686357bb427e1584468c44787a5a7"
EMBEDDED_SCENE_COMPILER = "o2/src/aura_xr/xr_scene.py"
SCENE_SCHEMA = "AURA-XR-SCENE-v1"
ADAPTERS = ("desktop_webgl", "webxr", "openxr")
PROJECTION_LAWS = (
    "SceneLabel!=CanonicalID", "Anchor!=Authority", "Visible!=Hydrated", "Gesture!=Effect",
)
READ_APIS = (
    "CITY_K27_CONTEXT", "CITY_SCENE_SHELL", "CITY_ROUTE", "CITY_WHY",
    "CITY_ACTIVE_DOMAINS", "CITY_INVALIDATION_CONE",
)
BINDING_KEYS = frozenset({
    "binding_schema", "source_root", "provenance_archive_sha256", "scene_source",
    "scene_source_sha256", "embedded_scene_compiler", "scene_schema", "adapters",
    "projection_laws", "read_apis", "strict_hold_unknown", "projection_only",
    "renderer_authority", "execution_authority", "effect_authority", "gate10",
})

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
    provider_bytes_bound: bool = False
    provenance_manifest_sha256: str | None = None
    manifest_payloads_verified: int = 0
    authority_ceiling: str = D0
    authority_minted: bool = False
    gate10: bool = False
    execution_authority: bool = False
    effect_authority: bool = False

    @property
    def receipt_root(self) -> str:
        payload = asdict(self); payload["disposition"] = self.disposition.value
        return _digest(payload)

def _digest(value: Any) -> str:
    """Strict canonical digest: ambiguous/non-finite JSON values are invalid."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(encoded.encode()).hexdigest()

def _sha(data: bytes) -> str:
    return sha256(data).hexdigest()

def _authority_false(reasons: list[str], label: str, value: Any) -> None:
    if value is not False: reasons.append(f"{label}_MUST_BE_FALSE")

def _parse_route(route_bytes: bytes) -> tuple[Mapping[str, Any] | None, list[str]]:
    try: route = json.loads(route_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError): return None, ["ROUTE_JSON_INVALID"]
    if not isinstance(route, Mapping): return None, ["ROUTE_ROOT_INVALID"]
    transitions = route.get("transitions")
    if not isinstance(transitions, list): return route, ["TRANSITIONS_LIST_REQUIRED"]
    if any(not isinstance(t, Mapping) for t in transitions): return route, ["TRANSITIONS_MAPPING_REQUIRED"]
    matches = [t for t in transitions if t.get("transition_id") == ROUTE_TRANSITION]
    if len(matches) != 1: return route, ["COMPILE_SCENE_TRANSITION_CARDINALITY_NOT_ONE"]
    return route, []

def _validate_route_structure(route_bytes: bytes, manifest: Mapping[str, Any]) -> SeamReceipt:
    reasons: list[str] = []
    route_sha = _sha(route_bytes)
    route, parse_reasons = _parse_route(route_bytes)
    if parse_reasons:
        return SeamReceipt(SeamDisposition.HOLD, tuple(parse_reasons), route_sha, None, (), ())
    assert route is not None
    transition = [t for t in route["transitions"] if t.get("transition_id") == ROUTE_TRANSITION][0]
    candidate = transition.get("memory_city_binding")
    binding = candidate if isinstance(candidate, Mapping) else None
    if binding is None: reasons.append("MEMORY_CITY_BINDING_MISSING")
    adapters: tuple[str, ...] = (); read_apis: tuple[str, ...] = (); binding_root = None
    if binding is not None:
        try:
            binding_root = _digest(binding)
        except (TypeError, ValueError):
            reasons.append("BINDING_CANONICALIZATION_INVALID")
        if set(binding) != BINDING_KEYS: reasons.append("BINDING_KEYSET_MISMATCH")
        if binding.get("binding_schema") != BINDING_SCHEMA: reasons.append("BINDING_SCHEMA_MISMATCH")
        if binding.get("source_root") != SOURCE_ROOT: reasons.append("SOURCE_ROOT_MISMATCH")
        if binding.get("provenance_archive_sha256") != ARCHIVE_SHA256: reasons.append("ARCHIVE_DIGEST_MISMATCH")
        if binding.get("scene_source") != SCENE_SOURCE: reasons.append("SCENE_SOURCE_MISMATCH")
        if binding.get("scene_source_sha256") != SCENE_SOURCE_SHA256: reasons.append("SCENE_SOURCE_DIGEST_MISMATCH")
        if binding.get("embedded_scene_compiler") != EMBEDDED_SCENE_COMPILER: reasons.append("SCENE_COMPILER_PATH_MISMATCH")
        if binding.get("scene_schema") != SCENE_SCHEMA: reasons.append("SCENE_SCHEMA_MISMATCH")
        raw = binding.get("adapters")
        if isinstance(raw, list) and all(type(x) is str for x in raw): adapters = tuple(raw)
        if adapters != ADAPTERS: reasons.append("ADAPTER_SET_OR_ORDER_MISMATCH")
        raw = binding.get("projection_laws")
        laws = tuple(raw) if isinstance(raw, list) and all(type(x) is str for x in raw) else ()
        if laws != PROJECTION_LAWS: reasons.append("PROJECTION_LAWS_MISMATCH")
        raw_apis = binding.get("read_apis")
        if isinstance(raw_apis, Mapping):
            read_apis = tuple(raw_apis.keys())
            if set(raw_apis) != set(READ_APIS): reasons.append("READ_API_SET_MISMATCH")
            for api in READ_APIS:
                if raw_apis.get(api) != "REVIEW_ONLY": reasons.append(f"{api}_NOT_REVIEW_ONLY")
        else: reasons.append("READ_APIS_INVALID")
        if binding.get("strict_hold_unknown") is not True: reasons.append("STRICT_HOLD_UNKNOWN_REQUIRED")
        if binding.get("projection_only") is not True: reasons.append("PROJECTION_ONLY_REQUIRED")
        _authority_false(reasons, "BINDING_RENDERER_AUTHORITY", binding.get("renderer_authority"))
        _authority_false(reasons, "BINDING_EXECUTION_AUTHORITY", binding.get("execution_authority"))
        _authority_false(reasons, "BINDING_EFFECT_AUTHORITY", binding.get("effect_authority"))
        _authority_false(reasons, "BINDING_GATE10", binding.get("gate10"))
    authority = route.get("authority")
    if not isinstance(authority, Mapping): reasons.append("ROUTE_AUTHORITY_INVALID")
    else:
        _authority_false(reasons, "ROUTE_RENDERER_AUTHORITY", authority.get("renderer_authority"))
        _authority_false(reasons, "ROUTE_EXECUTION_AUTHORITY", authority.get("execution_authority"))
        _authority_false(reasons, "ROUTE_AUTOMATIC_PROMOTION", authority.get("automatic_grammar_promotion"))
        _authority_false(reasons, "ROUTE_AUTOMATIC_MERGE", authority.get("automatic_merge"))
    files = manifest.get("files") if isinstance(manifest, Mapping) else None
    if not isinstance(files, Mapping): reasons.append("PROVENANCE_FILES_MISSING")
    else:
        src = files.get(ARCHIVE_SCENE_SOURCE)
        if not isinstance(src, Mapping) or src.get("sha256") != SCENE_SOURCE_SHA256:
            reasons.append("PROVENANCE_SCENE_SOURCE_NOT_PINNED")
    return SeamReceipt(
        SeamDisposition.READY_FOR_INDEPENDENT_REVIEW if not reasons else SeamDisposition.HOLD,
        tuple(sorted(set(reasons))), route_sha, binding_root, adapters, tuple(sorted(read_apis)),
        provider_bytes_bound=False,
    )

def validate_spatial_seam(route_bytes: bytes, provenance_manifest: Mapping[str, Any]) -> SeamReceipt:
    """Structural validator for independent review; never proves provider-byte provenance."""
    return _validate_route_structure(route_bytes, provenance_manifest)

def validate_provider_bytes(route_bytes: bytes, archive_bytes: bytes, manifest_bytes: bytes, scene_source_bytes: bytes) -> SeamReceipt:
    reasons: list[str] = []
    if _sha(archive_bytes) != ARCHIVE_SHA256: reasons.append("PROVENANCE_ARCHIVE_BYTES_NOT_PINNED")
    manifest_sha = _sha(manifest_bytes)
    if manifest_sha != PROVENANCE_MANIFEST_SHA256: reasons.append("PROVENANCE_MANIFEST_BYTES_NOT_PINNED")
    if _sha(scene_source_bytes) != SCENE_SOURCE_SHA256: reasons.append("SCENE_SOURCE_BYTES_NOT_PINNED")
    try: manifest = json.loads(manifest_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError):
        manifest = {}; reasons.append("PROVENANCE_MANIFEST_JSON_INVALID")
    payloads = 0
    if not reasons:
        try:
            with zipfile.ZipFile(BytesIO(archive_bytes)) as zf:
                if zf.read("PROVENANCE_MANIFEST.json") != manifest_bytes:
                    reasons.append("ARCHIVE_MANIFEST_BYTES_MISMATCH")
                files = manifest.get("files") if isinstance(manifest, Mapping) else None
                if not isinstance(files, Mapping) or len(files) != PROVENANCE_PAYLOAD_COUNT:
                    reasons.append("PROVENANCE_PAYLOAD_COUNT_MISMATCH")
                else:
                    for name, rec in files.items():
                        if not isinstance(rec, Mapping): reasons.append("PROVENANCE_ENTRY_INVALID"); break
                        try: payload = zf.read(name)
                        except KeyError: reasons.append("PROVENANCE_PAYLOAD_MISSING:" + str(name)); break
                        if len(payload) != rec.get("bytes") or _sha(payload) != rec.get("sha256"):
                            reasons.append("PROVENANCE_PAYLOAD_IDENTITY_MISMATCH:" + str(name)); break
                        payloads += 1
                    if zf.read(ARCHIVE_SCENE_SOURCE) != scene_source_bytes:
                        reasons.append("ARCHIVE_SCENE_SOURCE_BYTES_MISMATCH")
        except (zipfile.BadZipFile, KeyError): reasons.append("PROVENANCE_ARCHIVE_INVALID")
    structural = _validate_route_structure(route_bytes, manifest if isinstance(manifest, Mapping) else {})
    reasons.extend(structural.reasons)
    reasons = sorted(set(reasons))
    return SeamReceipt(
        SeamDisposition.READY_FOR_INDEPENDENT_REVIEW if not reasons else SeamDisposition.HOLD,
        tuple(reasons), structural.route_sha256, structural.binding_root, structural.adapters,
        structural.read_apis, provider_bytes_bound=not reasons,
        provenance_manifest_sha256=manifest_sha, manifest_payloads_verified=payloads,
    )

def validate_files(route_path: str | Path, archive_path: str | Path, manifest_path: str | Path, scene_source_path: str | Path) -> SeamReceipt:
    return validate_provider_bytes(
        Path(route_path).read_bytes(), Path(archive_path).read_bytes(), Path(manifest_path).read_bytes(), Path(scene_source_path).read_bytes()
    )

def validate_scene_source_snapshot(snapshot_bytes: bytes) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    if _sha(snapshot_bytes) != SCENE_SOURCE_SHA256: reasons.append("SCENE_SOURCE_BYTES_NOT_PINNED")
    try: text = snapshot_bytes.decode()
    except UnicodeDecodeError: return False, ("SCENE_SOURCE_NOT_UTF8",)
    required = (
        "SceneManifest('AURA-XR-SCENE-v1'", "adapters:Tuple[str,...]=('desktop_webgl','webxr','openxr')",
        "'desktop':('desktop_webgl',400,'mouse-keyboard')", "'webxr':('webxr',180,'6dof')",
        "'openxr':('openxr',220,'6dof')", "'SceneLabel!=CanonicalID','Anchor!=Authority','Visible!=Hydrated','Gesture!=Effect'",
    )
    for fragment in required:
        if fragment not in text: reasons.append("SCENE_SOURCE_INTERFACE_FRAGMENT_MISSING:" + fragment)
    return not reasons, tuple(reasons)
