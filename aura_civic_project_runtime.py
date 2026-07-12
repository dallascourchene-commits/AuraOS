"""Verified organ execution adapters for declarative Civic projects."""
from __future__ import annotations

from typing import Any

from aura_civic_projects import CivicProjectDefinition, require_project

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


def runtime_module():
    import aura_civic_runtime as runtime
    return runtime


def project_for_session(session: dict[str, Any]) -> CivicProjectDefinition:
    return require_project(str(session.get("project_id") or session.get("story") or "winnipeg_pathways"))


def _map_adapter(project: CivicProjectDefinition):
    def adapter(session: dict[str, Any]) -> dict[str, Any]:
        from aura_civic_map import build_map_manifest
        fixture = project.fixtures_factory()
        manifest = build_map_manifest(
            fixture.get("geojson", {"type": "FeatureCollection", "features": []}),
            ["boundary", "facility", "transit", "services", "needs_heatmap", "community_spaces", "scenario_locations"],
            fixture.get("heatmap"),
            jurisdiction_id=project.jurisdiction_id,
            jurisdiction_label=project.jurisdiction_label,
        )
        return {"ok": bool(manifest.get("ok")), "organ_type": "CivicMapOrgan", "map_manifest": manifest, "accessible_table_parity": True, "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": False}
    return adapter


def _music_adapter(project: CivicProjectDefinition):
    def adapter(session: dict[str, Any]) -> dict[str, Any]:
        from aura_civic_reasoning import civic_music
        result = civic_music(project.fixtures_factory().get("scenarios", []))
        return {"ok": bool(result.get("ok")), "organ_type": "CivicMUSICOrgan", "music": result.get("comparison", {}), "note": result.get("note", ""), "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": False}
    return adapter


def run_project_organ(session_id: str, organ_type: str) -> dict[str, Any]:
    runtime = runtime_module()
    current = runtime.get_session(session_id)
    if not current.get("ok"):
        return current
    session = dict(current["session"])
    project = project_for_session(session)
    fixture = project.fixtures_factory()
    session.update({
        "story": project.project_id,
        "story_fixtures": fixture,
        "mandatory_constraints": session.get("mandatory_constraints") or list(project.mandatory_constraints),
        "what_if_changes": session.get("what_if_changes") or dict(fixture.get("what_if_defaults") or {}),
    })
    from aura_civic_ephemeral_integration import execute_civic_organ_through_runtime
    adapter = _map_adapter(project) if organ_type == "CivicMapOrgan" else (_music_adapter(project) if organ_type == "CivicMUSICOrgan" else None)
    result = execute_civic_organ_through_runtime(organ_type, session, adapter_fn=adapter, store=runtime._get_ephemeral_store())
    if result.get("ok"):
        runtime._project_organ_result(session_id, organ_type, result)
    return result
