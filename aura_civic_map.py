"""Aura Civic Map — GeoJSON layers and heatmap validation.

Uses GeoJSON fallback for MVP. MapLibre GL JS for frontend rendering.
"""
from __future__ import annotations
import json
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

LAYER_TYPES = (
    "boundary","facility","transit","services","needs_heatmap",
    "community_spaces","resource_offers","scenario_locations",
    "planning_areas","civic_issues",
)

PROHIBITED_HEATMAPS = (
    "person_level_crime","person_level_addiction","person_level_homelessness",
    "health_diagnoses","child_welfare","indigenous_identity",
    "poverty","immigration_status",
)

SAFE_HEATMAP_SIGNALS = (
    "service_access_distance","transit_access","facility_coverage",
    "public_engagement_volume","aggregate_311_trends","grant_distribution",
    "program_capacity","community_stated_priority_density",
    "accessibility_barriers","scenario_benefit_coverage",
)

def validate_geojson(geojson: dict[str, Any]) -> dict[str, Any]:
    if geojson.get("type") != "FeatureCollection":
        return {"ok": False, "error": "invalid GeoJSON: not a FeatureCollection"}
    features = geojson.get("features", [])
    if not isinstance(features, list):
        return {"ok": False, "error": "invalid GeoJSON: features must be a list"}
    for f in features:
        if not isinstance(f, dict):
            return {"ok": False, "error": "invalid GeoJSON: feature is not an object"}
        geom = f.get("geometry") or {}
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
    required_fields = ["metric","source","time_range","geographic_unit","aggregation","denominator","missing_data_rate","freshness","uncertainty","truth_class"]
    missing = [f for f in required_fields if f not in heatmap]
    if missing:
        return {"ok": False, "error": f"missing required heatmap metadata: {missing}"}
    return {"ok": True, "metric": metric}

def validate_layer(layer_type: str) -> dict[str, Any]:
    if layer_type not in LAYER_TYPES:
        return {"ok": False, "error": f"unknown layer: {layer_type}"}
    return {"ok": True}

def build_map_manifest(geojson: dict[str, Any], layers: list[str], heatmap: dict[str, Any] | None = None) -> dict[str, Any]:
    gj_valid = validate_geojson(geojson)
    if not gj_valid["ok"]:
        return {"ok": False, "error": gj_valid["error"]}
    for layer in layers:
        lv = validate_layer(layer)
        if not lv["ok"]:
            return {"ok": False, "error": lv["error"]}
    result = {"ok": True, "geojson": geojson, "layers": layers,
              "attribution": "OpenStreetMap contributors (demo fixture — no bulk download)",
              "renderer": "MapLibre GL JS (frontend) / GeoJSON fallback (MVP)",
              "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    if heatmap:
        hv = validate_heatmap(heatmap)
        if not hv["ok"]:
            return {"ok": False, "error": hv["error"]}
        result["heatmap"] = heatmap
    return result
