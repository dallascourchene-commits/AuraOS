from __future__ import annotations

import ast
import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from aura_ephemeral_manifest import create_manifest
from aura_ephemeral_workspace_contracts import (
    AuthorityEnvelope, CanonicalReference, DependencyEdge, EphemeralWorkspaceRecipe,
    MultimodalSpatialObservation, ProjectContextProjection, RepositoryIdentity,
    SpatialReferentBinding, canonical_json, compile_coding_spatial_workspace_recipe,
    stable_digest,
)

ROOT = Path(__file__).resolve().parents[1]
D = {str(i): str(i) * 64 for i in range(1, 7)}
MAIN = "879b5fb056b70d150b1646e082223330a36c2912"


def ref(name: str, digest: str, freshness: str = "CURRENT", metadata=None) -> CanonicalReference:
    return CanonicalReference(name, "canonical.owner", f"owner://{name}", digest,
                              freshness_class=freshness, metadata=metadata or {})


def project() -> ProjectContextProjection:
    repo = RepositoryIdentity("dallascourchene-commits/AuraOS", "refs/heads/main", MAIN, D["6"])
    return ProjectContextProjection(
        "project:auraos-intent-spatial-pr1", "repository:dallascourchene-commits/AuraOS",
        "aura_unified_memory_continuity", D["1"], D["2"], repo,
        (ref("artifact:codemap", D["3"]),), decision_refs=(ref("decision:pr1", D["4"]),),
        relationship_refs=(ref("relationship:compass", D["5"]),),
        freshness_timestamp_ms=1_722_737_640_000,
        completeness_warnings=("No connected external project store was admitted.",),
    )


def recipe():
    manifest = create_manifest(
        "Compile an intent-native coding spatial workspace without operational invocation.",
        organ_id="EORG-intent-spatial-pr1",
        requested_capabilities=["resolve_capabilities", "read_slice", "dissolve"],
    )
    value = compile_coding_spatial_workspace_recipe(
        base_manifest=manifest, project_projection=project(), canonical_intent_digest=D["1"],
        adapter_refs=(ref("adapter:compass", D["2"]), ref("adapter:spatial", D["3"])),
        evidence_refs=(ref("evidence:source", D["4"]), ref("evidence:tests", D["5"])),
    )
    return value, manifest


def observation() -> MultimodalSpatialObservation:
    binding = SpatialReferentBinding(
        "binding:function-node", "scene:coding-workspace", D["1"], "session:local", D["2"],
        "entity:function-node", D["3"], .97, ref("evidence:referent", D["4"]), ("GAZE", "HAND"),
    )
    return MultimodalSpatialObservation(
        "observation:select-function", "scene:coding-workspace", D["1"], "session:local", D["2"],
        ("VOICE", "GAZE", "HAND"), "REFERENT_SELECTED", "REQUEST_RELATIONAL_SYNTHESIS", (binding,),
        speech_text="Show relationships for this function",
        transcript_digest=stable_digest("Show relationships for this function"),
        temporal_window_start_ms=1000, temporal_window_end_ms=1800,
        evidence_class="MEASURED", tracking_quality=.94,
    )


def test_v1_manifest_is_unchanged_when_wrapped() -> None:
    manifest = create_manifest("Inspect the exact bounded project", organ_id="EORG-v1-compat")
    before, digest = copy.deepcopy(manifest.to_dict()), manifest.compute_digest()
    compile_coding_spatial_workspace_recipe(
        base_manifest=manifest, project_projection=project(), canonical_intent_digest=D["1"],
        adapter_refs=(ref("adapter:compass", D["2"]),), evidence_refs=(ref("evidence:source", D["3"]),),
    )
    assert manifest.to_dict() == before
    assert canonical_json(manifest.to_dict()) == canonical_json(before)
    assert manifest.compute_digest() == digest


def test_contracts_round_trip_and_current_bindings_validate() -> None:
    p, (r, manifest), o = project(), recipe(), observation()
    assert ProjectContextProjection.from_dict(p.to_dict()).to_dict() == p.to_dict()
    assert EphemeralWorkspaceRecipe.from_dict(r.to_dict()).to_dict() == r.to_dict()
    assert MultimodalSpatialObservation.from_dict(o.to_dict()).to_dict() == o.to_dict()
    p.validate_bindings(
        expected_repository_identity_digest=p.repository_identity.identity_digest,
        expected_project_ref=p.project_ref,
        expected_reference_digests={x.reference_id: x.digest for x in p.all_references()},
    )
    r.validate_bindings(
        expected_intent_digest=D["1"], expected_project_projection_digest=p.projection_digest,
        expected_base_manifest_digest=manifest.compute_digest(),
        expected_adapter_digests={x.reference_id: x.digest for x in r.adapter_refs},
        expected_evidence_digests={x.reference_id: x.digest for x in r.evidence_refs},
    )
    o.validate_bindings(expected_scene_digest=D["1"], expected_session_digest=D["2"],
                        expected_entity_digests={"entity:function-node": D["3"]})


def test_authority_aliases_and_raw_sensor_payloads_fail_closed() -> None:
    with pytest.raises(ValueError, match="authority alias"):
        ref("artifact:bad", D["1"], metadata={"nested": {"automaticMerge": False}})
    authority = AuthorityEnvelope().to_dict(); authority["automatic_merge"] = True
    with pytest.raises(ValueError, match="automatic_merge"):
        AuthorityEnvelope.from_dict(authority)
    raw = observation().to_dict(); raw["camera_frame"] = "not-retainable"
    with pytest.raises(ValueError, match="raw sensor payload"):
        MultimodalSpatialObservation.from_dict(raw)


def test_all_required_stale_bindings_fail_closed() -> None:
    p, (r, manifest), o = project(), recipe(), observation()
    with pytest.raises(ValueError, match="repository"):
        p.validate_bindings(expected_repository_identity_digest=D["1"])
    with pytest.raises(ValueError, match="project reference"):
        p.validate_bindings(expected_repository_identity_digest=p.repository_identity.identity_digest,
                            expected_project_ref="repository:other/project")
    with pytest.raises(ValueError, match="evidence"):
        p.validate_bindings(expected_repository_identity_digest=p.repository_identity.identity_digest,
                            expected_reference_digests={"artifact:codemap": D["1"]})
    common = dict(
        expected_project_projection_digest=p.projection_digest,
        expected_base_manifest_digest=manifest.compute_digest(),
        expected_adapter_digests={x.reference_id: x.digest for x in r.adapter_refs},
        expected_evidence_digests={x.reference_id: x.digest for x in r.evidence_refs},
    )
    with pytest.raises(ValueError, match="intent"):
        r.validate_bindings(expected_intent_digest=D["2"], **common)
    with pytest.raises(ValueError, match="adapter reference set"):
        r.validate_bindings(expected_intent_digest=D["1"], **{**common, "expected_adapter_digests": {"adapter:compass": D["2"]}})
    with pytest.raises(ValueError, match="scene"):
        o.validate_bindings(expected_scene_digest=D["4"], expected_session_digest=D["2"],
                            expected_entity_digests={"entity:function-node": D["3"]})
    with pytest.raises(ValueError, match="entity"):
        o.validate_bindings(expected_scene_digest=D["1"], expected_session_digest=D["2"],
                            expected_entity_digests={"entity:function-node": D["4"]})


def test_stale_freshness_and_dependency_cycles_fail_closed() -> None:
    p = project(); payload = p.to_dict()
    payload["artifact_evidence_refs"] = [ref("artifact:stale", D["3"], "STALE").to_dict()]
    payload["projection_digest"] = ""; stale = ProjectContextProjection.from_dict(payload)
    with pytest.raises(ValueError, match="stale or unknown"):
        stale.validate_bindings(expected_repository_identity_digest=stale.repository_identity.identity_digest)
    r, _ = recipe(); payload = r.to_dict()
    payload["dependency_edges"] = [
        DependencyEdge("compile_compass_packet", "fetch_bounded_neighborhood").to_dict(),
        DependencyEdge("fetch_bounded_neighborhood", "compile_compass_packet").to_dict(),
    ]; payload["recipe_digest"] = ""
    with pytest.raises(ValueError, match="cycle"):
        EphemeralWorkspaceRecipe.from_dict(payload)


def test_schemas_validate_contracts_and_reject_authority_escalation() -> None:
    r, _ = recipe()
    for filename, payload in (
        ("aura_project_context_projection.schema.json", project().to_dict()),
        ("aura_ephemeral_workspace_recipe.schema.json", r.to_dict()),
        ("aura_multimodal_spatial_observation.schema.json", observation().to_dict()),
    ):
        schema = json.loads((ROOT / "schemas" / filename).read_text())
        Draft202012Validator.check_schema(schema); validator = Draft202012Validator(schema)
        assert not list(validator.iter_errors(payload))
        tampered = copy.deepcopy(payload); tampered["authority"]["automatic_merge"] = True
        assert list(validator.iter_errors(tampered))


def test_contract_module_has_no_operational_or_persistence_calls() -> None:
    tree = ast.parse((ROOT / "aura_ephemeral_workspace_contracts.py").read_text())
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import): imports.update(x.name.split(".")[0] for x in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module: imports.add(node.module.split(".")[0])
    assert imports <= {"__future__", "collections", "dataclasses", "enum", "hashlib", "json", "math", "re", "typing"}
    prohibited = {"open", "exec", "eval", "connect", "run", "Popen", "system", "unlink", "write_text", "write_bytes"}
    calls = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    calls |= {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert not calls & prohibited
