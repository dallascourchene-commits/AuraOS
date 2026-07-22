"""Immutable provenance contracts for the synthetic Construction Arena demo.

The contracts in this module own demo source and representation identity only.
They never own Construction project state, schedule truth, financial truth,
regulatory truth, professional release, renderer authority, or physical location
truth. Every asset is local, content-addressed, projection-only, and explicitly
non-survey-authoritative.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from pathlib import PurePosixPath
import re
from typing import Any, Mapping

from aura_event_contracts import stable_digest

CONSTRUCTION_DEMO_CONTRACTS_VERSION = "AURA_CONSTRUCTION_DEMO_CONTRACTS_V1"
CONSTRUCTION_DEMO_SOURCE_MANIFEST_VERSION = "AURA_CONSTRUCTION_DEMO_SOURCE_MANIFEST_V1"
CONSTRUCTION_DEMO_ASSET_PACK_VERSION = "AURA_CONSTRUCTION_DEMO_ASSET_PACK_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
TU_WIEN_SOURCE_ID = "tuwien-custom-escape-route-ifc-v2"
TU_WIEN_DOI = "10.48436/a185k-86v39"
TU_WIEN_SOURCE_FILENAME = "CustomTestModel-EscapeRouteAnalysis-ZDB-v2.ifc"
TU_WIEN_PUBLISHED_MD5 = "58a6e009b16bd3808cacd72b11fcf216"
CC_BY_4_0 = "CC-BY-4.0"
CC_BY_4_0_URL = "https://creativecommons.org/licenses/by/4.0/"

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_HEX_DIGEST = re.compile(r"^(?:[0-9a-f]{32}|[0-9a-f]{64})$")
_MD5 = re.compile(r"^[0-9a-f]{32}$")
_RFC3339_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class ConstructionDemoRepresentation(str, Enum):
    IFC_SOURCE = "IFC_SOURCE"
    MESH_GLB = "MESH_GLB"
    FLOOR_PLAN_SVG = "FLOOR_PLAN_SVG"
    GAUSSIAN_PLY = "GAUSSIAN_PLY"
    GAUSSIAN_SPZ = "GAUSSIAN_SPZ"


class ConstructionDemoTruthClass(str, Enum):
    FICTIONAL_SOURCE_GEOMETRY = "FICTIONAL_SOURCE_GEOMETRY"
    DERIVED_PRESENTATION = "DERIVED_PRESENTATION"


def _identifier(value: Any, name: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        raise ValueError(f"{name} must be a canonical identifier")
    return value


def _text(value: Any, name: str, *, maximum: int = 512) -> str:
    if type(value) is not str or not value.strip() or value != " ".join(value.split()):
        raise ValueError(f"{name} must be a normalized non-empty string")
    if len(value.encode("utf-8")) > maximum:
        raise ValueError(f"{name} exceeds {maximum} bytes")
    return value


def _tuple_text(value: Any, name: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise ValueError(f"{name} must be a tuple")
    normalized = tuple(_text(item, f"{name}[]") for item in value)
    if not allow_empty and not normalized:
        raise ValueError(f"{name} must not be empty")
    if normalized != tuple(sorted(set(normalized))):
        raise ValueError(f"{name} must be sorted and unique")
    return normalized


def _sha256(value: Any, name: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _digest(value: Any, name: str) -> str:
    if type(value) is not str or _HEX_DIGEST.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase 32- or 64-character digest")
    return value


def _nonnegative_int(value: Any, name: str, *, maximum: int = 4_294_967_296) -> int:
    if type(value) is not int or value < 0 or value > maximum:
        raise ValueError(f"{name} must be an integer in [0, {maximum}]")
    return value


def _finite(value: Any, name: str) -> float:
    if type(value) not in {int, float}:
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _finite_vector(value: Any, name: str) -> tuple[float, float, float]:
    if type(value) is not tuple or len(value) != 3:
        raise ValueError(f"{name} must be a three-value tuple")
    return tuple(_finite(item, f"{name}[]") for item in value)  # type: ignore[return-value]


def _local_uri(value: Any, name: str = "uri") -> str:
    if type(value) is not str or not value or "\\" in value:
        raise ValueError(f"{name} must be a non-empty POSIX repository-relative path")
    if "://" in value or value.startswith(("/", "~")):
        raise ValueError(f"{name} must not be absolute or network-addressed")
    path = PurePosixPath(value)
    if not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"{name} must be a normalized repository-relative path")
    if path.as_posix() != value:
        raise ValueError(f"{name} must use canonical POSIX form")
    return value


def _strict_bool(value: Any, name: str, expected: bool) -> bool:
    if type(value) is not bool or value is not expected:
        raise ValueError(f"{name} must be {str(expected).lower()}")
    return value


def _enum_value(value: Any, enum_type: type[Enum], name: str) -> str:
    raw = value.value if isinstance(value, enum_type) else value
    if type(raw) is not str or raw not in {item.value for item in enum_type}:
        raise ValueError(f"{name} is unsupported")
    return raw


def _digest_body(value: Mapping[str, Any]) -> str:
    return stable_digest(dict(value))


@dataclass(frozen=True)
class ConstructionDemoSourceManifest:
    source_id: str
    title: str
    creators: tuple[str, ...]
    publisher: str
    doi: str
    source_filename: str
    source_byte_length: int
    published_md5: str
    observed_sha256: str
    license_id: str
    license_url: str
    downloaded_at: str
    fictional_source: bool = True
    survey_authority: bool = False
    person_level_data_included: bool = False
    external_fetch_required_at_runtime: bool = False
    source_manifest_digest: str = ""
    version: str = CONSTRUCTION_DEMO_SOURCE_MANIFEST_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _identifier(self.source_id, "source_id"))
        object.__setattr__(self, "title", _text(self.title, "title"))
        object.__setattr__(self, "creators", _tuple_text(self.creators, "creators"))
        object.__setattr__(self, "publisher", _text(self.publisher, "publisher"))
        object.__setattr__(self, "doi", _text(self.doi, "doi", maximum=128))
        object.__setattr__(self, "source_filename", _text(self.source_filename, "source_filename", maximum=256))
        object.__setattr__(self, "source_byte_length", _nonnegative_int(self.source_byte_length, "source_byte_length", maximum=268_435_456))
        if type(self.published_md5) is not str or _MD5.fullmatch(self.published_md5) is None:
            raise ValueError("published_md5 must be a lowercase MD5 digest")
        object.__setattr__(self, "observed_sha256", _sha256(self.observed_sha256, "observed_sha256"))
        if self.license_id != CC_BY_4_0 or self.license_url != CC_BY_4_0_URL:
            raise ValueError("Construction demo source must use the pinned CC BY 4.0 contract")
        if type(self.downloaded_at) is not str or _RFC3339_UTC.fullmatch(self.downloaded_at) is None:
            raise ValueError("downloaded_at must be canonical UTC RFC3339 seconds")
        _strict_bool(self.fictional_source, "fictional_source", True)
        _strict_bool(self.survey_authority, "survey_authority", False)
        _strict_bool(self.person_level_data_included, "person_level_data_included", False)
        _strict_bool(self.external_fetch_required_at_runtime, "external_fetch_required_at_runtime", False)
        if self.version != CONSTRUCTION_DEMO_SOURCE_MANIFEST_VERSION:
            raise ValueError("unsupported source manifest version")
        digest = _digest_body(self._identity_body())
        if self.source_manifest_digest and self.source_manifest_digest != digest:
            raise ValueError("source_manifest_digest does not match manifest body")
        object.__setattr__(self, "source_manifest_digest", digest)

    def _identity_body(self) -> dict[str, Any]:
        """Return stable source identity without acquisition-time receipt metadata."""
        return {
            "version": self.version,
            "source_id": self.source_id,
            "title": self.title,
            "creators": list(self.creators),
            "publisher": self.publisher,
            "doi": self.doi,
            "source_filename": self.source_filename,
            "source_byte_length": self.source_byte_length,
            "published_md5": self.published_md5,
            "observed_sha256": self.observed_sha256,
            "license_id": self.license_id,
            "license_url": self.license_url,
            "fictional_source": self.fictional_source,
            "survey_authority": self.survey_authority,
            "person_level_data_included": self.person_level_data_included,
            "external_fetch_required_at_runtime": self.external_fetch_required_at_runtime,
        }

    def _body(self) -> dict[str, Any]:
        return {**self._identity_body(), "downloaded_at": self.downloaded_at}

    def to_dict(self) -> dict[str, Any]:
        return {**self._body(), "source_manifest_digest": self.source_manifest_digest}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ConstructionDemoSourceManifest":
        return cls(
            source_id=value["source_id"],
            title=value["title"],
            creators=tuple(value["creators"]),
            publisher=value["publisher"],
            doi=value["doi"],
            source_filename=value["source_filename"],
            source_byte_length=value["source_byte_length"],
            published_md5=value["published_md5"],
            observed_sha256=value["observed_sha256"],
            license_id=value["license_id"],
            license_url=value["license_url"],
            downloaded_at=value["downloaded_at"],
            fictional_source=value.get("fictional_source", True),
            survey_authority=value.get("survey_authority", False),
            person_level_data_included=value.get("person_level_data_included", False),
            external_fetch_required_at_runtime=value.get("external_fetch_required_at_runtime", False),
            source_manifest_digest=value.get("source_manifest_digest", ""),
            version=value.get("version", CONSTRUCTION_DEMO_SOURCE_MANIFEST_VERSION),
        )


@dataclass(frozen=True)
class ConstructionDemoStorey:
    storey_id: str
    ifc_global_id: str
    name: str
    elevation_m: float
    ordinal: int
    source_ifc_ref: str
    mesh_asset_id: str
    floor_plan_asset_id: str
    gaussian_asset_id: str
    bounds_min: tuple[float, float, float]
    bounds_max: tuple[float, float, float]
    frame_id: str
    source_refs: tuple[str, ...]
    storey_digest: str = ""
    version: str = CONSTRUCTION_DEMO_CONTRACTS_VERSION

    def __post_init__(self) -> None:
        for field_name in ("storey_id", "ifc_global_id", "mesh_asset_id", "floor_plan_asset_id", "gaussian_asset_id", "frame_id"):
            object.__setattr__(self, field_name, _identifier(getattr(self, field_name), field_name))
        object.__setattr__(self, "name", _text(self.name, "name"))
        object.__setattr__(self, "elevation_m", _finite(self.elevation_m, "elevation_m"))
        object.__setattr__(self, "ordinal", _nonnegative_int(self.ordinal, "ordinal", maximum=10_000))
        object.__setattr__(self, "source_ifc_ref", _local_uri(self.source_ifc_ref, "source_ifc_ref"))
        minimum = _finite_vector(self.bounds_min, "bounds_min")
        maximum = _finite_vector(self.bounds_max, "bounds_max")
        if any(low > high for low, high in zip(minimum, maximum)):
            raise ValueError("storey bounds are inverted")
        object.__setattr__(self, "bounds_min", minimum)
        object.__setattr__(self, "bounds_max", maximum)
        object.__setattr__(self, "source_refs", _tuple_text(self.source_refs, "source_refs"))
        if self.version != CONSTRUCTION_DEMO_CONTRACTS_VERSION:
            raise ValueError("unsupported storey contract version")
        digest = _digest_body(self._body())
        if self.storey_digest and self.storey_digest != digest:
            raise ValueError("storey_digest does not match storey body")
        object.__setattr__(self, "storey_digest", digest)

    def _body(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "storey_id": self.storey_id,
            "ifc_global_id": self.ifc_global_id,
            "name": self.name,
            "elevation_m": self.elevation_m,
            "ordinal": self.ordinal,
            "source_ifc_ref": self.source_ifc_ref,
            "mesh_asset_id": self.mesh_asset_id,
            "floor_plan_asset_id": self.floor_plan_asset_id,
            "gaussian_asset_id": self.gaussian_asset_id,
            "bounds_min": list(self.bounds_min),
            "bounds_max": list(self.bounds_max),
            "frame_id": self.frame_id,
            "source_refs": list(self.source_refs),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._body(), "storey_digest": self.storey_digest}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ConstructionDemoStorey":
        return cls(
            storey_id=value["storey_id"], ifc_global_id=value["ifc_global_id"], name=value["name"],
            elevation_m=value["elevation_m"], ordinal=value["ordinal"], source_ifc_ref=value["source_ifc_ref"],
            mesh_asset_id=value["mesh_asset_id"], floor_plan_asset_id=value["floor_plan_asset_id"],
            gaussian_asset_id=value["gaussian_asset_id"], bounds_min=tuple(value["bounds_min"]),
            bounds_max=tuple(value["bounds_max"]), frame_id=value["frame_id"],
            source_refs=tuple(value["source_refs"]), storey_digest=value.get("storey_digest", ""),
            version=value.get("version", CONSTRUCTION_DEMO_CONTRACTS_VERSION),
        )


@dataclass(frozen=True)
class ConstructionDemoAssetBinding:
    asset_id: str
    storey_id: str
    representation: ConstructionDemoRepresentation | str
    uri: str
    media_type: str
    content_digest: str
    byte_length: int
    coordinate_system: str
    unit_scale_meters: float
    bounds_min: tuple[float, float, float]
    bounds_max: tuple[float, float, float]
    source_refs: tuple[str, ...]
    import_receipt_digest: str
    representation_digest: str
    truth_class: ConstructionDemoTruthClass | str
    survey_authority: bool = False
    person_level_data_included: bool = False
    projection_only: bool = True
    version: str = CONSTRUCTION_DEMO_CONTRACTS_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "asset_id", _identifier(self.asset_id, "asset_id"))
        object.__setattr__(self, "storey_id", _identifier(self.storey_id, "storey_id"))
        representation = _enum_value(self.representation, ConstructionDemoRepresentation, "representation")
        object.__setattr__(self, "representation", representation)
        object.__setattr__(self, "uri", _local_uri(self.uri))
        object.__setattr__(self, "media_type", _text(self.media_type, "media_type", maximum=128))
        object.__setattr__(self, "content_digest", _sha256(self.content_digest, "content_digest"))
        object.__setattr__(self, "byte_length", _nonnegative_int(self.byte_length, "byte_length"))
        object.__setattr__(self, "coordinate_system", _identifier(self.coordinate_system, "coordinate_system"))
        unit_scale = _finite(self.unit_scale_meters, "unit_scale_meters")
        if unit_scale <= 0.0:
            raise ValueError("unit_scale_meters must be positive")
        object.__setattr__(self, "unit_scale_meters", unit_scale)
        minimum = _finite_vector(self.bounds_min, "bounds_min")
        maximum = _finite_vector(self.bounds_max, "bounds_max")
        if any(low > high for low, high in zip(minimum, maximum)):
            raise ValueError("asset bounds are inverted")
        object.__setattr__(self, "bounds_min", minimum)
        object.__setattr__(self, "bounds_max", maximum)
        object.__setattr__(self, "source_refs", _tuple_text(self.source_refs, "source_refs"))
        object.__setattr__(self, "import_receipt_digest", _digest(self.import_receipt_digest, "import_receipt_digest"))
        object.__setattr__(self, "representation_digest", _digest(self.representation_digest, "representation_digest"))
        truth_class = _enum_value(self.truth_class, ConstructionDemoTruthClass, "truth_class")
        object.__setattr__(self, "truth_class", truth_class)
        _strict_bool(self.survey_authority, "survey_authority", False)
        _strict_bool(self.person_level_data_included, "person_level_data_included", False)
        _strict_bool(self.projection_only, "projection_only", True)
        if representation == ConstructionDemoRepresentation.IFC_SOURCE.value:
            if truth_class != ConstructionDemoTruthClass.FICTIONAL_SOURCE_GEOMETRY.value:
                raise ValueError("IFC source assets must use fictional source geometry truth class")
        elif truth_class != ConstructionDemoTruthClass.DERIVED_PRESENTATION.value:
            raise ValueError("derived assets must use derived presentation truth class")
        if self.version != CONSTRUCTION_DEMO_CONTRACTS_VERSION:
            raise ValueError("unsupported asset binding version")

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version, "asset_id": self.asset_id, "storey_id": self.storey_id,
            "representation": self.representation, "uri": self.uri, "media_type": self.media_type,
            "content_digest": self.content_digest, "byte_length": self.byte_length,
            "coordinate_system": self.coordinate_system, "unit_scale_meters": self.unit_scale_meters,
            "bounds_min": list(self.bounds_min), "bounds_max": list(self.bounds_max),
            "source_refs": list(self.source_refs), "import_receipt_digest": self.import_receipt_digest,
            "representation_digest": self.representation_digest, "truth_class": self.truth_class,
            "survey_authority": self.survey_authority,
            "person_level_data_included": self.person_level_data_included,
            "projection_only": self.projection_only,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ConstructionDemoAssetBinding":
        return cls(
            asset_id=value["asset_id"], storey_id=value["storey_id"], representation=value["representation"],
            uri=value["uri"], media_type=value["media_type"], content_digest=value["content_digest"],
            byte_length=value["byte_length"], coordinate_system=value["coordinate_system"],
            unit_scale_meters=value["unit_scale_meters"], bounds_min=tuple(value["bounds_min"]),
            bounds_max=tuple(value["bounds_max"]), source_refs=tuple(value["source_refs"]),
            import_receipt_digest=value["import_receipt_digest"], representation_digest=value["representation_digest"],
            truth_class=value["truth_class"], survey_authority=value.get("survey_authority", False),
            person_level_data_included=value.get("person_level_data_included", False),
            projection_only=value.get("projection_only", True),
            version=value.get("version", CONSTRUCTION_DEMO_CONTRACTS_VERSION),
        )


@dataclass(frozen=True)
class ConstructionDemoAssetPack:
    source_manifest: ConstructionDemoSourceManifest
    building_id: str
    building_frame_id: str
    storeys: tuple[ConstructionDemoStorey, ...]
    assets: tuple[ConstructionDemoAssetBinding, ...]
    element_index_digest: str
    hierarchy_digest: str
    generator_version: str
    generator_request_digest: str
    asset_pack_digest: str = ""
    version: str = CONSTRUCTION_DEMO_ASSET_PACK_VERSION
    construction_project_state_owner: bool = False
    schedule_truth_owner: bool = False
    financial_truth_owner: bool = False
    regulatory_truth_owner: bool = False
    professional_release_owner: bool = False
    renderer_authority: bool = False
    physical_location_truth_owner: bool = False
    production_mutation: bool = False
    automatic_merge: bool = False
    human_review_required: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.source_manifest, ConstructionDemoSourceManifest):
            raise ValueError("source_manifest must be a ConstructionDemoSourceManifest")
        object.__setattr__(self, "building_id", _identifier(self.building_id, "building_id"))
        object.__setattr__(self, "building_frame_id", _identifier(self.building_frame_id, "building_frame_id"))
        if type(self.storeys) is not tuple or not self.storeys or not all(isinstance(item, ConstructionDemoStorey) for item in self.storeys):
            raise ValueError("storeys must be a non-empty tuple of ConstructionDemoStorey")
        if type(self.assets) is not tuple or not self.assets or not all(isinstance(item, ConstructionDemoAssetBinding) for item in self.assets):
            raise ValueError("assets must be a non-empty tuple of ConstructionDemoAssetBinding")
        storey_ids = [item.storey_id for item in self.storeys]
        if storey_ids != sorted(set(storey_ids)):
            raise ValueError("storeys must use unique canonical storey_id order")
        if [item.ordinal for item in self.storeys] != sorted(item.ordinal for item in self.storeys):
            raise ValueError("storeys must use ascending ordinal order")
        asset_ids = [item.asset_id for item in self.assets]
        if asset_ids != sorted(set(asset_ids)):
            raise ValueError("assets must use unique canonical asset_id order")
        assets_by_id = {item.asset_id: item for item in self.assets}
        storey_id_set = set(storey_ids)
        for asset in self.assets:
            if asset.storey_id not in storey_id_set:
                raise ValueError("asset references an unknown storey")
        for storey in self.storeys:
            expected = {storey.mesh_asset_id, storey.floor_plan_asset_id, storey.gaussian_asset_id}
            if not expected.issubset(assets_by_id):
                raise ValueError("storey references an unknown required asset")
            role_bindings = (
                (storey.mesh_asset_id, ConstructionDemoRepresentation.MESH_GLB.value),
                (storey.floor_plan_asset_id, ConstructionDemoRepresentation.FLOOR_PLAN_SVG.value),
                (storey.gaussian_asset_id, ConstructionDemoRepresentation.GAUSSIAN_SPZ.value),
            )
            if any(assets_by_id[asset_id].representation != representation for asset_id, representation in role_bindings):
                raise ValueError("storey GLB/SVG/SPZ asset roles do not match their bindings")
            if any(assets_by_id[item].storey_id != storey.storey_id for item in expected):
                raise ValueError("storey asset binding references a different storey")
        for field_name in ("element_index_digest", "hierarchy_digest", "generator_request_digest"):
            object.__setattr__(self, field_name, _digest(getattr(self, field_name), field_name))
        object.__setattr__(self, "generator_version", _identifier(self.generator_version, "generator_version"))
        for name, expected in {
            "construction_project_state_owner": False,
            "schedule_truth_owner": False,
            "financial_truth_owner": False,
            "regulatory_truth_owner": False,
            "professional_release_owner": False,
            "renderer_authority": False,
            "physical_location_truth_owner": False,
            "production_mutation": False,
            "automatic_merge": False,
            "human_review_required": True,
        }.items():
            _strict_bool(getattr(self, name), name, expected)
        if self.version != CONSTRUCTION_DEMO_ASSET_PACK_VERSION:
            raise ValueError("unsupported asset pack version")
        digest = _digest_body(self._body())
        if self.asset_pack_digest and self.asset_pack_digest != digest:
            raise ValueError("asset_pack_digest does not match asset pack body")
        object.__setattr__(self, "asset_pack_digest", digest)

    def _body(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "source_manifest": self.source_manifest.to_dict(),
            "building_id": self.building_id,
            "building_frame_id": self.building_frame_id,
            "storeys": [item.to_dict() for item in self.storeys],
            "assets": [item.to_dict() for item in self.assets],
            "element_index_digest": self.element_index_digest,
            "hierarchy_digest": self.hierarchy_digest,
            "generator_version": self.generator_version,
            "generator_request_digest": self.generator_request_digest,
            "construction_project_state_owner": self.construction_project_state_owner,
            "schedule_truth_owner": self.schedule_truth_owner,
            "financial_truth_owner": self.financial_truth_owner,
            "regulatory_truth_owner": self.regulatory_truth_owner,
            "professional_release_owner": self.professional_release_owner,
            "renderer_authority": self.renderer_authority,
            "physical_location_truth_owner": self.physical_location_truth_owner,
            "production_mutation": self.production_mutation,
            "automatic_merge": self.automatic_merge,
            "human_review_required": self.human_review_required,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._body(), "asset_pack_digest": self.asset_pack_digest}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ConstructionDemoAssetPack":
        return cls(
            source_manifest=ConstructionDemoSourceManifest.from_dict(value["source_manifest"]),
            building_id=value["building_id"], building_frame_id=value["building_frame_id"],
            storeys=tuple(ConstructionDemoStorey.from_dict(item) for item in value["storeys"]),
            assets=tuple(ConstructionDemoAssetBinding.from_dict(item) for item in value["assets"]),
            element_index_digest=value["element_index_digest"], hierarchy_digest=value["hierarchy_digest"],
            generator_version=value["generator_version"], generator_request_digest=value["generator_request_digest"],
            asset_pack_digest=value.get("asset_pack_digest", ""),
            version=value.get("version", CONSTRUCTION_DEMO_ASSET_PACK_VERSION),
            construction_project_state_owner=value.get("construction_project_state_owner", False),
            schedule_truth_owner=value.get("schedule_truth_owner", False),
            financial_truth_owner=value.get("financial_truth_owner", False),
            regulatory_truth_owner=value.get("regulatory_truth_owner", False),
            professional_release_owner=value.get("professional_release_owner", False),
            renderer_authority=value.get("renderer_authority", False),
            physical_location_truth_owner=value.get("physical_location_truth_owner", False),
            production_mutation=value.get("production_mutation", False),
            automatic_merge=value.get("automatic_merge", False),
            human_review_required=value.get("human_review_required", True),
        )


__all__ = [
    "CC_BY_4_0", "CC_BY_4_0_URL", "CONSTRUCTION_DEMO_ASSET_PACK_VERSION",
    "CONSTRUCTION_DEMO_CONTRACTS_VERSION", "CONSTRUCTION_DEMO_SOURCE_MANIFEST_VERSION",
    "ConstructionDemoAssetBinding", "ConstructionDemoAssetPack", "ConstructionDemoRepresentation",
    "ConstructionDemoSourceManifest", "ConstructionDemoStorey", "ConstructionDemoTruthClass",
    "PATCH_AUTHORITY", "TU_WIEN_DOI", "TU_WIEN_PUBLISHED_MD5", "TU_WIEN_SOURCE_FILENAME",
    "TU_WIEN_SOURCE_ID", "VSA_PATCH_AUTHORITY",
]
