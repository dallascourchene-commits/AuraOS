from __future__ import annotations

import ast
import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

# This import intentionally exercises the exact existing V1 manifest compatibility
# boundary rather than replacing the canonical owner with a test-only stub in-repo.
from aura_ephemeral_manifest import create_manifest
from aura_ephemeral_workspace_contracts import (
    AuthorityEnvelope,
    CanonicalReference,
    CODING_SPATIAL_WORKSPACE_V1_DEFINITION,
    DependencyEdge,
    EphemeralWorkspaceRecipe,
    MAX_TTL_SECONDS,
    MultimodalSpatialObservation,
    ProjectContextProjection,
    RepositoryIdentity,
    SpatialReferentBinding,
    WorkspaceBudget,
    canonical_json,
    compile_coding_spatial_workspace_recipe,
    stable_digest,
    validate_observation_semantics,
    validate_project_semantics,
    validate_recipe_semantics,
)

ROOT = Path(__file__).resolve().parents[1]
D = {str(i): f"{i:x}" * 64 for i in range(1, 10)}
MAIN = "879b5fb056b70d150b1646e082223330a36c2912"


def ref(name: str, digest: str, freshness: str = "CURRENT", metadata=None,
        *, owner: str = "canonical.owner", truth: str = "EXACT") -> CanonicalReference:
    """Build one exact canonical reference fixture."""
    return CanonicalReference(
        name,
        owner,
        f"owner://{name}",
        digest,
        truth_class=truth,
        freshness_class=freshness,
        metadata={} if metadata is None else metadata,
    )


def project() -> ProjectContextProjection:
    """Build the bounded project fixture."""
    repo = RepositoryIdentity(
        "dallascourchene-commits/AuraOS",
        "refs/heads/main",
        MAIN,
        D["6"],
    )
    return ProjectContextProjection(
        "project:auraos-intent-spatial-pr1",
        "repository:dallascourchene-commits/AuraOS",
        "aura_unified_memory_continuity",
        D["1"],
        D["2"],
        repo,
        (ref("artifact:codemap", D["3"]),),
        decision_refs=(ref("decision:pr1", D["4"]),),
        relationship_refs=(ref("relationship:compass", D["5"]),),
        freshness_timestamp_ms=1_722_737_640_000,
        completeness_warnings=("No connected external project store was admitted.",),
    )


def recipe(*, ttl_seconds: int = 300, manifest_ttl: int = 300,
           budgets: WorkspaceBudget | dict | None = None,
           adapters=None, evidence=None):
    """Build the frozen coding-workspace recipe and V1 manifest."""
    manifest = create_manifest(
        "Compile an intent-native coding spatial workspace without operational invocation.",
        organ_id="EORG-intent-spatial-pr1",
        ttl_seconds=manifest_ttl,
        requested_capabilities=["resolve_capabilities", "read_slice", "dissolve"],
    )
    value = compile_coding_spatial_workspace_recipe(
        base_manifest=manifest,
        project_projection=project(),
        canonical_intent_digest=D["1"],
        adapter_refs=adapters or (ref("adapter:compass", D["2"]), ref("adapter:spatial", D["3"])),
        evidence_refs=evidence or (ref("evidence:source", D["4"]), ref("evidence:tests", D["5"])),
        budgets=budgets,
        ttl_seconds=ttl_seconds,
    )
    return value, manifest


def observation(*, sources=("VOICE", "GAZE", "HAND"), binding_sources=("GAZE", "HAND"),
                speech="Show relationships for this function") -> MultimodalSpatialObservation:
    """Build the normalized multimodal observation fixture."""
    binding = SpatialReferentBinding(
        "binding:function-node",
        "scene:coding-workspace",
        D["1"],
        "session:local",
        D["2"],
        "entity:function-node",
        D["3"],
        0.97,
        ref("evidence:referent", D["4"]),
        binding_sources,
    )
    return MultimodalSpatialObservation(
        "observation:select-function",
        "scene:coding-workspace",
        D["1"],
        "session:local",
        D["2"],
        sources,
        "REFERENT_SELECTED",
        "REQUEST_RELATIONAL_SYNTHESIS",
        (binding,),
        speech_text=speech,
        transcript_digest=stable_digest(speech) if speech else "",
        temporal_window_start_ms=1000,
        temporal_window_end_ms=1800,
        evidence_class="MEASURED",
        tracking_quality=0.94,
    )


def expected_project_refs(value: ProjectContextProjection) -> dict[str, str]:
    """Return the complete project reference identity map."""
    return {item.reference_id: item.digest for item in value.all_references()}


def expected_observation_evidence(value: MultimodalSpatialObservation) -> dict[str, str]:
    """Return the complete referent-evidence identity map."""
    return {item.evidence_ref.reference_id: item.evidence_ref.digest for item in value.target_candidates}


def test_v1_manifest_is_unchanged_when_wrapped_and_serialized_mapping_is_verified() -> None:
    """Wrapping must preserve V1 bytes and reject altered serialized snapshots."""
    manifest = create_manifest("Inspect the exact bounded project", organ_id="EORG-v1-compat")
    before, digest = copy.deepcopy(manifest.to_dict()), manifest.compute_digest()
    compile_coding_spatial_workspace_recipe(
        base_manifest=manifest,
        project_projection=project(),
        canonical_intent_digest=D["1"],
        adapter_refs=(ref("adapter:compass", D["2"]),),
        evidence_refs=(ref("evidence:source", D["3"]),),
    )
    assert manifest.to_dict() == before
    assert canonical_json(manifest.to_dict()) == canonical_json(before)
    assert manifest.compute_digest() == digest

    serialized = manifest.to_dict()
    compile_coding_spatial_workspace_recipe(
        base_manifest=serialized,
        project_projection=project(),
        canonical_intent_digest=D["1"],
        adapter_refs=(ref("adapter:compass", D["2"]),),
        evidence_refs=(ref("evidence:source", D["3"]),),
    )
    tampered = copy.deepcopy(serialized)
    tampered["objective"] = "tampered while retaining phase_hash"
    with pytest.raises(ValueError, match="digest does not match"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=tampered,
            project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )
    wrong_version = copy.deepcopy(serialized)
    wrong_version["manifest_version"] = "AURA_EPHEMERAL_ORGAN_V2"
    with pytest.raises(ValueError, match="unsupported base manifest version"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=wrong_version,
            project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )


def test_contracts_round_trip_and_complete_current_bindings_validate() -> None:
    """Every exact record must round-trip and rebind to complete current truth."""
    p, (r, manifest), o = project(), recipe(), observation()
    assert ProjectContextProjection.from_dict(p.to_dict()).to_dict() == p.to_dict()
    assert EphemeralWorkspaceRecipe.from_dict(r.to_dict()).to_dict() == r.to_dict()
    assert MultimodalSpatialObservation.from_dict(o.to_dict()).to_dict() == o.to_dict()
    p.validate_bindings(
        expected_repository_identity_digest=p.repository_identity.identity_digest,
        expected_project_ref=p.project_ref,
        expected_reference_digests=expected_project_refs(p),
    )
    r.validate_bindings(
        expected_intent_digest=D["1"],
        expected_project_projection_digest=p.projection_digest,
        expected_base_manifest_digest=manifest.compute_digest(),
        expected_adapter_digests={item.reference_id: item.digest for item in r.adapter_refs},
        expected_evidence_digests={item.reference_id: item.digest for item in r.evidence_refs},
    )
    o.validate_bindings(
        expected_scene_digest=D["1"],
        expected_session_digest=D["2"],
        expected_entity_digests={"entity:function-node": D["3"]},
        expected_evidence_digests=expected_observation_evidence(o),
    )


def test_canonicalization_and_primitive_parsing_are_strict_and_lossless() -> None:
    """Malformed JSON-like values must never be coerced into valid identities."""
    with pytest.raises(ValueError, match="keys must be strings"):
        stable_digest({1: "x"})
    with pytest.raises(ValueError, match="sets are not JSON"):
        stable_digest({1, 2})
    with pytest.raises(ValueError, match="must be a string"):
        CanonicalReference(1, "owner", "owner://x", D["1"])
    with pytest.raises(ValueError, match="JSON number"):
        SpatialReferentBinding("b", "s", D["1"], "session", D["2"], "e", D["3"], True,
                               ref("evidence:x", D["4"]), ("GAZE",))
    with pytest.raises(ValueError, match="JSON number"):
        replace(observation(), tracking_quality="0.5", observation_digest="")
    with pytest.raises(ValueError, match="complete 40- or 64-character"):
        RepositoryIdentity("owner/repo", "main", "a" * 32, D["1"])


def test_metadata_is_closed_scalar_and_detached() -> None:
    """Unknown aliases, nested payloads, and raw sensor families must fail closed."""
    for metadata in (
        {"automaticMerge": False},
        {"merge_permission": False},
        {"camera_image": "encoded"},
        {"hand_joints": [1, 2]},
        {"attributes": ["automaticMerge"]},
        {"fields": [{"name": "room_mesh"}]},
    ):
        with pytest.raises(ValueError, match="unsupported fields"):
            ref("artifact:bad", D["1"], metadata=metadata)
    good = ref("artifact:good", D["1"], metadata={"source_path": "aura.py", "line_start": 1})
    detached = good.to_dict()
    detached["metadata"]["source_path"] = "changed.py"
    assert good.to_dict()["metadata"]["source_path"] == "aura.py"


def test_serialized_records_require_nonempty_matching_digests() -> None:
    """Clearing an integrity field must not bless tampered serialized content."""
    records = (
        (RepositoryIdentity, project().repository_identity.to_dict(), "identity_digest"),
        (ProjectContextProjection, project().to_dict(), "projection_digest"),
        (EphemeralWorkspaceRecipe, recipe()[0].to_dict(), "recipe_digest"),
        (SpatialReferentBinding, observation().target_candidates[0].to_dict(), "binding_digest"),
        (MultimodalSpatialObservation, observation().to_dict(), "observation_digest"),
    )
    for record_type, payload, field_name in records:
        payload[field_name] = ""
        with pytest.raises(ValueError, match=field_name):
            record_type.from_dict(payload)


def test_project_binding_requires_complete_reference_set_and_current_projection() -> None:
    """Partial maps and stale projection-level freshness must be rejected."""
    p = project()
    with pytest.raises(ValueError, match="expected_reference_digests is required"):
        p.validate_bindings(expected_repository_identity_digest=p.repository_identity.identity_digest)
    partial = expected_project_refs(p)
    partial.pop(next(iter(partial)))
    with pytest.raises(ValueError, match="reference set mismatch"):
        p.validate_bindings(
            expected_repository_identity_digest=p.repository_identity.identity_digest,
            expected_reference_digests=partial,
        )
    stale = replace(p, freshness_class="STALE", projection_digest="")
    with pytest.raises(ValueError, match="stale or unknown project projection"):
        stale.validate_bindings(
            expected_repository_identity_digest=stale.repository_identity.identity_digest,
            expected_reference_digests=expected_project_refs(stale),
        )
    with pytest.raises(ValueError, match="privacy_class"):
        replace(p, privacy_class="RAW_PRIVATE_MEMORY", projection_digest="")
    with pytest.raises(ValueError, match="egress_class"):
        replace(p, egress_class="NETWORK_ALLOWED", projection_digest="")


def test_dependency_graph_fails_closed_for_self_dangling_duplicate_cycle_and_bounds() -> None:
    """All graph invariants must be enforced by the semantic model."""
    with pytest.raises(ValueError, match="self dependency"):
        DependencyEdge("compile_compass_packet", "compile_compass_packet")
    r, _ = recipe()
    self_edge = r.to_dict()
    self_edge["dependency_edges"] = [{"source_capability_id": "compile_compass_packet", "target_capability_id": "compile_compass_packet"}]
    with pytest.raises(ValueError, match="self dependency"):
        EphemeralWorkspaceRecipe.from_dict(self_edge)
    payload = r.to_dict()
    payload["dependency_edges"] = [{"source_capability_id": "compile_compass_packet", "target_capability_id": "unknown_capability"}]
    with pytest.raises(ValueError, match="invalid recipe dependency"):
        EphemeralWorkspaceRecipe.from_dict(payload)
    duplicate = r.to_dict()
    duplicate["dependency_edges"] = [r.dependency_edges[0].to_dict(), r.dependency_edges[0].to_dict()]
    with pytest.raises(ValueError, match="duplicate recipe dependency"):
        EphemeralWorkspaceRecipe.from_dict(duplicate)
    cycle = r.to_dict()
    cycle["dependency_edges"] = [
        {"source_capability_id": "compile_compass_packet", "target_capability_id": "fetch_bounded_neighborhood"},
        {"source_capability_id": "fetch_bounded_neighborhood", "target_capability_id": "compile_compass_packet"},
    ]
    with pytest.raises(ValueError, match="cycle"):
        EphemeralWorkspaceRecipe.from_dict(cycle)
    with pytest.raises(ValueError, match="bounded sequence"):
        replace(r, dependency_edges=tuple(r.dependency_edges) * 65, recipe_digest="")


def test_frozen_recipe_profile_owner_gates_and_lifecycle_cannot_be_redirected() -> None:
    """Untrusted parsing cannot introduce shell capabilities or bypass owners/gates."""
    r, _ = recipe()
    mutations = (
        ("capability_ids", ["shell"], "capability profile|invalid recipe dependency"),
        ("domain_owner_handoff_map", {"architecture": "attacker.owner"}, "handoff owners"),
        ("required_verification_gates", [], "verification gates"),
        ("lifecycle_policy", "NEVER_DISSOLVE", "lifecycle_policy"),
        ("dissolution_policy", "OPTIONAL", "dissolution_policy"),
    )
    for field_name, value, message in mutations:
        payload = r.to_dict()
        payload[field_name] = value
        with pytest.raises(ValueError, match=message):
            EphemeralWorkspaceRecipe.from_dict(payload)
    with pytest.raises(TypeError):
        CODING_SPATIAL_WORKSPACE_V1_DEFINITION["capability_ids"] = ("shell",)


def test_recipe_references_are_canonical_current_and_globally_unique() -> None:
    """Reference ordering, role uniqueness, owner, and freshness are deterministic."""
    adapters = (ref("adapter:z", D["2"]), ref("adapter:a", D["3"]))
    evidence = (ref("evidence:z", D["4"]), ref("evidence:a", D["5"]))
    first, _ = recipe(adapters=adapters, evidence=evidence)
    second, _ = recipe(adapters=tuple(reversed(adapters)), evidence=tuple(reversed(evidence)))
    assert first.recipe_digest == second.recipe_digest
    assert first.recipe_id == second.recipe_id

    duplicate = first.to_dict()
    duplicate["evidence_refs"][0]["reference_id"] = duplicate["adapter_refs"][0]["reference_id"]
    with pytest.raises(ValueError, match="across adapter and evidence"):
        EphemeralWorkspaceRecipe.from_dict(duplicate)
    with pytest.raises(ValueError, match="base manifest reference"):
        replace(first, base_manifest_ref=replace(first.base_manifest_ref, freshness_class="STALE"), recipe_digest="")
    with pytest.raises(ValueError, match="base manifest reference"):
        replace(first, base_manifest_ref=replace(first.base_manifest_ref, owner="attacker.owner"), recipe_digest="")


def test_recipe_lifetime_budget_and_identity_are_fully_bound() -> None:
    """Recipes cannot outlive manifests and IDs change with behavior-defining inputs."""
    short, _ = recipe(ttl_seconds=300, manifest_ttl=10)
    assert short.ttl_seconds == 10
    assert short.budgets.wall_time_ms <= 10_000
    with pytest.raises(ValueError, match="budget keys mismatch"):
        recipe(budgets={})
    with pytest.raises(ValueError, match="effective workspace TTL"):
        recipe(ttl_seconds=10, manifest_ttl=10, budgets=WorkspaceBudget(wall_time_ms=10_001))
    with pytest.raises(ValueError, match="integer in 1"):
        recipe(ttl_seconds=0)
    with pytest.raises(ValueError, match="integer in 1"):
        recipe(ttl_seconds=MAX_TTL_SECONDS + 1)
    first, _ = recipe()
    changed, _ = recipe(adapters=(ref("adapter:other", D["7"]),))
    assert first.recipe_id != changed.recipe_id
    assert first.recipe_digest != changed.recipe_digest


def test_observation_temporal_transcript_inputs_targets_and_evidence_fail_closed() -> None:
    """Cross-field multimodal bindings must be exact, bounded, and current."""
    base = observation()
    with pytest.raises(ValueError, match="invalid temporal"):
        replace(base, temporal_window_start_ms=1000, temporal_window_end_ms=999, observation_digest="")
    with pytest.raises(ValueError, match="invalid temporal"):
        replace(base, temporal_window_start_ms=0, temporal_window_end_ms=60_001, observation_digest="")
    with pytest.raises(ValueError, match="transcript digest"):
        replace(base, transcript_digest=D["8"], observation_digest="")
    with pytest.raises(ValueError, match="unique"):
        observation(sources=("voice", "VOICE"))
    with pytest.raises(ValueError, match="unique"):
        observation(binding_sources=("gaze", "GAZE"))
    with pytest.raises(ValueError, match="bounded target sequence"):
        replace(base, target_candidates=(item for item in base.target_candidates), observation_digest="")
    with pytest.raises(ValueError, match="expected_evidence_digests is required"):
        base.validate_bindings(
            expected_scene_digest=D["1"],
            expected_session_digest=D["2"],
            expected_entity_digests={"entity:function-node": D["3"]},
            expected_evidence_digests=None,
        )
    wrong_evidence = expected_observation_evidence(base)
    wrong_evidence["evidence:referent"] = D["9"]
    with pytest.raises(ValueError, match="stale referent evidence"):
        base.validate_bindings(
            expected_scene_digest=D["1"],
            expected_session_digest=D["2"],
            expected_entity_digests={"entity:function-node": D["3"]},
            expected_evidence_digests=wrong_evidence,
        )
    with pytest.raises(ValueError, match="referent evidence must be current"):
        replace(
            base.target_candidates[0],
            evidence_ref=replace(base.target_candidates[0].evidence_ref, freshness_class="UNKNOWN"),
            binding_digest="",
        )


def test_schemas_enforce_structural_safety_and_semantic_validators_close_cross_field_gaps() -> None:
    """Published schemas and mandatory semantic validators must agree on exact records."""
    values = {
        "aura_project_context_projection.schema.json": (project().to_dict(), validate_project_semantics),
        "aura_ephemeral_workspace_recipe.schema.json": (recipe()[0].to_dict(), validate_recipe_semantics),
        "aura_multimodal_spatial_observation.schema.json": (observation().to_dict(), validate_observation_semantics),
    }
    for filename, (payload, semantic_validator) in values.items():
        schema = json.loads((ROOT / "schemas" / filename).read_text())
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        assert not list(validator.iter_errors(payload))
        assert schema["x-aura-semantic-validator"].endswith(semantic_validator.__name__)
        assert semantic_validator(payload).to_dict() == payload
        tampered = copy.deepcopy(payload)
        tampered["authority"]["automatic_merge"] = True
        assert list(validator.iter_errors(tampered))

    project_schema = Draft202012Validator(json.loads((ROOT / "schemas" / "aura_project_context_projection.schema.json").read_text()))
    bad_metadata = project().to_dict()
    bad_metadata["artifact_evidence_refs"][0]["metadata"] = {"hand_joints": [1, 2]}
    assert list(project_schema.iter_errors(bad_metadata))

    recipe_schema = Draft202012Validator(json.loads((ROOT / "schemas" / "aura_ephemeral_workspace_recipe.schema.json").read_text()))
    dangling = recipe()[0].to_dict()
    dangling["dependency_edges"] = [{"source_capability_id": "compile_compass_packet", "target_capability_id": "unknown"}]
    assert list(recipe_schema.iter_errors(dangling))
    with pytest.raises(ValueError, match="invalid recipe dependency"):
        validate_recipe_semantics(dangling)

    observation_schema = Draft202012Validator(json.loads((ROOT / "schemas" / "aura_multimodal_spatial_observation.schema.json").read_text()))
    bad_window = observation().to_dict()
    bad_window["temporal_window_end_ms"] = bad_window["temporal_window_start_ms"] - 1
    assert not list(observation_schema.iter_errors(bad_window))  # Cross-field arithmetic is semantic.
    with pytest.raises(ValueError, match="invalid temporal"):
        validate_observation_semantics(bad_window)


def test_contract_module_has_docstrings_and_no_operational_or_persistence_calls() -> None:
    """The contract module remains documented, stdlib-only, and non-operational."""
    source = (ROOT / "aura_ephemeral_workspace_contracts.py").read_text()
    tree = ast.parse(source)
    imports = set()
    definitions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(item.name.split(".")[0] for item in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            definitions.append(node)
    assert imports <= {"__future__", "collections", "dataclasses", "enum", "hashlib", "json", "math", "re", "types", "typing"}
    assert all(ast.get_docstring(node) for node in definitions)
    prohibited_names = {"open", "exec", "eval", "compile", "__import__", "Popen"}
    prohibited_attributes = {"connect", "run", "Popen", "system", "unlink", "write_text", "write_bytes"}
    bare_calls = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    attribute_calls = {node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
    assert not bare_calls & prohibited_names
    assert not attribute_calls & prohibited_attributes
    dynamic_getattrs = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "getattr"
        and (not node.args or not isinstance(node.args[0], ast.Name) or node.args[0].id != "self")
    ]
    assert not dynamic_getattrs
