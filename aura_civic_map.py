"""Aura Civic Map — policy-aware GeoJSON projection for the Civic Arena.

The map is an interface over governed civic data, not an authority layer. The
server filters data by active jurisdiction, viewport, zoom, privacy, and location
precision before the browser receives a projection.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

LAYER_TYPES = (
    "boundary", "facility", "transit", "services", "needs_heatmap",
    "community_spaces", "resource_offers", "scenario_locations",
    "planning_areas", "civic_issues",
)

PROHIBITED_HEATMAPS = (
    "person_level_crime", "person_level_addiction", "person_level_homelessness",
    "health_diagnoses", "child_welfare", "indigenous_identity",
    "poverty", "immigration_status",
)

SAFE_HEATMAP_SIGNALS = (
    "service_access_distance", "transit_access", "facility_coverage",
    "public_engagement_volume", "aggregate_311_trends", "grant_distribution",
    "program_capacity", "community_stated_priority_density",
    "accessibility_barriers", "scenario_benefit_coverage",
)

PUBLIC_PRIVACY_CLASSES = {"PUBLIC_ATTRIBUTED", "PUBLIC_PSEUDONYMOUS"}
COMMUNITY_PRIVACY_CLASSES = PUBLIC_PRIVACY_CLASSES | {"COMMUNITY_ONLY"}
VISIBLE_LOCATION_CLASSES = {
    "EXACT_PUBLIC_LOCATION", "APPROXIMATE_LOCATION", "NEIGHBOURHOOD_ONLY", "NOT_MAPPED",
}

DEFAULT_ZOOM_BY_TYPE = {
    "boundary": 3,
    "planning_area": 7,
    "neighbourhood": 9,
    "facility": 10,
    "transit": 11,
    "service": 11,
    "community_space": 11,
    "candidate": 12,
    "scenario": 12,
    "resource_offer": 13,
    "civic_issue": 10,
}


def validate_geojson(geojson: dict[str, Any]) -> dict[str, Any]:
    if geojson.get("type") != "FeatureCollection":
        return {"ok": False, "error": "invalid GeoJSON: not a FeatureCollection"}
    features = geojson.get("features", [])
    if not isinstance(features, list):
        return {"ok": False, "error": "invalid GeoJSON: features must be a list"}
    for feature in features:
        if not isinstance(feature, dict):
            return {"ok": False, "error": "invalid GeoJSON: feature is not an object"}
        geom = feature.get("geometry") or {}
        if not isinstance(geom, dict):
            return {"ok": False, "error": "invalid GeoJSON: geometry is not an object"}
        coords = geom.get("coordinates")
        if not coords:
            return {"ok": False, "error": "feature missing coordinates"}
        if geom.get("type") == "Point":
            if not (isinstance(coords, list) and len(coords) == 2):
                return {"ok": False, "error": "invalid Point coordinates"}
            lon, lat = coords
            if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                return {"ok": False, "error": f"coordinates out of range: {coords}"}
    return {"ok": True, "feature_count": len(features)}


def validate_heatmap(heatmap: dict[str, Any]) -> dict[str, Any]:
    metric = heatmap.get("metric", "")
    if metric in PROHIBITED_HEATMAPS:
        return {"ok": False, "error": f"prohibited heatmap: {metric}"}
    required_fields = [
        "metric", "source", "time_range", "geographic_unit", "aggregation",
        "denominator", "missing_data_rate", "freshness", "uncertainty", "truth_class",
    ]
    missing = [field for field in required_fields if field not in heatmap]
    if missing:
        return {"ok": False, "error": f"missing required heatmap metadata: {missing}"}
    return {"ok": True, "metric": metric}


def validate_layer(layer_type: str) -> dict[str, Any]:
    if layer_type not in LAYER_TYPES:
        return {"ok": False, "error": f"unknown layer: {layer_type}"}
    return {"ok": True}


def _feature_type(feature: dict[str, Any]) -> str:
    props = feature.get("properties") or {}
    explicit = str(props.get("type") or props.get("layer_type") or "").strip().lower()
    if explicit:
        return explicit
    geometry_type = str((feature.get("geometry") or {}).get("type") or "").lower()
    return "boundary" if geometry_type in {"polygon", "multipolygon"} else "feature"


def _normalize_feature(feature: dict[str, Any], *, default_jurisdiction: str) -> dict[str, Any]:
    item = deepcopy(feature)
    props = dict(item.get("properties") or {})
    feature_type = _feature_type(item)
    geometry_type = str((item.get("geometry") or {}).get("type") or "")
    props.setdefault("type", feature_type)
    props.setdefault("jurisdiction_id", default_jurisdiction)
    props.setdefault("truth_class", "UNKNOWN")
    props.setdefault("privacy_class", "PUBLIC_ATTRIBUTED")
    props.setdefault(
        "location_class",
        "EXACT_PUBLIC_LOCATION" if geometry_type == "Point" else "NEIGHBOURHOOD_ONLY",
    )
    props.setdefault("min_zoom", DEFAULT_ZOOM_BY_TYPE.get(feature_type, 9))
    props.setdefault("max_zoom", 20)
    props.setdefault("source_ref", props.get("truth_class", "UNKNOWN"))
    props.setdefault("feature_id", props.get("id") or props.get("name") or f"{feature_type}-feature")
    item["properties"] = props
    return item


def build_map_manifest(
    geojson: dict[str, Any],
    layers: list[str],
    heatmap: dict[str, Any] | None = None,
    *,
    jurisdiction_id: str = "demo_neighbourhood",
    jurisdiction_label: str = "Demo Neighbourhood",
) -> dict[str, Any]:
    gj_valid = validate_geojson(geojson)
    if not gj_valid["ok"]:
        return {"ok": False, "error": gj_valid["error"]}
    for layer in layers:
        layer_valid = validate_layer(layer)
        if not layer_valid["ok"]:
            return {"ok": False, "error": layer_valid["error"]}

    normalized = {
        "type": "FeatureCollection",
        "features": [
            _normalize_feature(feature, default_jurisdiction=jurisdiction_id)
            for feature in geojson.get("features", [])
        ],
    }
    result = {
        "ok": True,
        "geojson": normalized,
        "layers": layers,
        "jurisdictions": [{
            "jurisdiction_id": jurisdiction_id,
            "label": jurisdiction_label,
            "authority": "community_or_human",
            "data_boundary": "server_enforced",
        }],
        "default_jurisdiction": jurisdiction_id,
        "zoom_contract": {
            "3-6": "jurisdiction boundaries and aggregate regional context",
            "7-9": "planning areas and neighbourhood summaries",
            "10-12": "public facilities, transit, services, and civic issues",
            "13-18": "public or community-authorized local records and scenarios",
        },
        "viewport_contract": {
            "filter_location": "server",
            "jurisdiction_required": True,
            "privacy_enforced": True,
            "location_precision_enforced": True,
            "accessible_table_parity": True,
        },
        "attribution": "OpenStreetMap contributors (demo fixture — no bulk download)",
        "renderer": "Canvas projection / GeoJSON fallback (MVP); MapLibre-compatible manifest",
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
    if heatmap:
        heatmap_valid = validate_heatmap(heatmap)
        if not heatmap_valid["ok"]:
            return {"ok": False, "error": heatmap_valid["error"]}
        result["heatmap"] = heatmap
    return result


def _iter_coordinate_pairs(value: Any) -> Iterable[tuple[float, float]]:
    if isinstance(value, (list, tuple)):
        if len(value) >= 2 and all(isinstance(part, (int, float)) for part in value[:2]):
            yield float(value[0]), float(value[1])
            return
        for child in value:
            yield from _iter_coordinate_pairs(child)


def _geometry_bbox(geometry: dict[str, Any]) -> tuple[float, float, float, float] | None:
    pairs = list(_iter_coordinate_pairs(geometry.get("coordinates")))
    if not pairs:
        return None
    xs = [pair[0] for pair in pairs]
    ys = [pair[1] for pair in pairs]
    return min(xs), min(ys), max(xs), max(ys)


def _intersects(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])


def parse_bbox(value: str | list[float] | tuple[float, ...] | None) -> tuple[float, float, float, float] | None:
    if value in (None, "", []):
        return None
    try:
        raw = [float(part) for part in value.split(",")] if isinstance(value, str) else [float(part) for part in value]
    except (TypeError, ValueError):
        return None
    if len(raw) != 4:
        return None
    west, south, east, north = raw
    if west > east or south > north:
        return None
    return west, south, east, north


def project_map_manifest(
    manifest: dict[str, Any],
    *,
    bbox: str | list[float] | tuple[float, ...] | None = None,
    zoom: int | float = 10,
    jurisdiction_id: str = "",
    viewer_scope: str = "community",
) -> dict[str, Any]:
    """Return a server-filtered map projection for one viewport and jurisdiction."""
    if not manifest.get("ok"):
        return {"ok": False, "error": manifest.get("error", "invalid_map_manifest")}
    geojson = manifest.get("geojson") or {"type": "FeatureCollection", "features": []}
    validation = validate_geojson(geojson)
    if not validation.get("ok"):
        return validation

    active_jurisdiction = str(jurisdiction_id or manifest.get("default_jurisdiction") or "")
    viewport = parse_bbox(bbox)
    zoom_value = max(0.0, min(24.0, float(zoom)))
    allowed_privacy = COMMUNITY_PRIVACY_CLASSES if viewer_scope == "community" else PUBLIC_PRIVACY_CLASSES

    visible: list[dict[str, Any]] = []
    accessible_rows: list[dict[str, Any]] = []
    suppressed = {"jurisdiction": 0, "viewport": 0, "zoom": 0, "privacy": 0, "location": 0}

    for raw_feature in geojson.get("features", []):
        feature = _normalize_feature(raw_feature, default_jurisdiction=active_jurisdiction)
        props = feature.get("properties") or {}
        feature_jurisdiction = str(props.get("jurisdiction_id") or "")
        if active_jurisdiction and feature_jurisdiction != active_jurisdiction:
            suppressed["jurisdiction"] += 1
            continue
        if str(props.get("privacy_class")) not in allowed_privacy:
            suppressed["privacy"] += 1
            continue
        if str(props.get("location_class")) not in VISIBLE_LOCATION_CLASSES:
            suppressed["location"] += 1
            continue
        if zoom_value < float(props.get("min_zoom", 0)) or zoom_value > float(props.get("max_zoom", 24)):
            suppressed["zoom"] += 1
            continue
        feature_bbox = _geometry_bbox(feature.get("geometry") or {})
        if viewport and feature_bbox and not _intersects(feature_bbox, viewport):
            suppressed["viewport"] += 1
            continue
        visible.append(feature)
        accessible_rows.append({
            "feature_id": props.get("feature_id", ""),
            "name": props.get("name", "Unnamed feature"),
            "type": props.get("type", "feature"),
            "jurisdiction_id": feature_jurisdiction,
            "truth_class": props.get("truth_class", "UNKNOWN"),
            "privacy_class": props.get("privacy_class", "PUBLIC_ATTRIBUTED"),
            "location_class": props.get("location_class", "NOT_MAPPED"),
            "source_ref": props.get("source_ref", ""),
        })

    visible_types = sorted({str((feature.get("properties") or {}).get("type", "feature")) for feature in visible})
    heatmap = manifest.get("heatmap")
    heatmap_visible = bool(heatmap) and zoom_value <= 12
    return {
        "ok": True,
        "projection_version": "AURA_CIVIC_MAP_PROJECTION_V1",
        "jurisdiction_id": active_jurisdiction,
        "viewer_scope": viewer_scope,
        "zoom": zoom_value,
        "bbox": list(viewport) if viewport else None,
        "geojson": {"type": "FeatureCollection", "features": visible},
        "visible_feature_count": len(visible),
        "visible_layer_types": visible_types,
        "available_jurisdictions": manifest.get("jurisdictions", []),
        "heatmap": heatmap if heatmap_visible else None,
        "heatmap_visible": heatmap_visible,
        "suppressed_counts": suppressed,
        "accessible_rows": accessible_rows,
        "accessible_table_parity": True,
        "attribution": manifest.get("attribution", ""),
        "policy": manifest.get("viewport_contract", {}),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
