from __future__ import annotations

import ast
import copy
from collections.abc import Mapping, Sequence
import json
from dataclasses import dataclass, fields, replace
from enum import Enum
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

# This import intentionally exercises the exact existing V1 manifest compatibility
# boundary rather than replacing the canonical owner with a test-only stub in-repo.
from aura_ephemeral_manifest import create_manifest
import aura_ephemeral_workspace_contracts as workspace_contracts
from aura_ephemeral_workspace_contracts import (
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


def _trusted_manifest_timestamps(manifest: Any) -> tuple[Any, Any]:
    """Return the externally retained timestamp binding used by compiler tests."""
    if isinstance(manifest, Mapping):
        return manifest.get("created_at"), manifest.get("expires_at")
    return manifest.created_at, manifest.expires_at


def recipe(*, ttl_seconds: int = 300, manifest_ttl: int = 300,
           budgets: WorkspaceBudget | dict | None = None,
           adapters=None, evidence=None, manifest=None):
    """Build the frozen coding-workspace recipe and V1 manifest."""
    manifest = manifest or create_manifest(
        "Compile an intent-native coding spatial workspace without operational invocation.",
        organ_id="EORG-intent-spatial-pr1",
        ttl_seconds=manifest_ttl,
        requested_capabilities=["resolve_capabilities", "read_slice", "dissolve"],
    )
    value = compile_coding_spatial_workspace_recipe(
        base_manifest=manifest,
        expected_manifest_timestamps=_trusted_manifest_timestamps(manifest),
        project_projection=project(),
        expected_project_projection=project(),
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


def expected_project_refs(value: ProjectContextProjection) -> dict[str, dict]:
    """Return the complete project canonical-reference identity map."""
    return {item.reference_id: item.to_dict() for item in value.all_references()}


def expected_observation_evidence(value: MultimodalSpatialObservation) -> dict[str, dict]:
    """Return the complete referent-evidence canonical-reference identity map."""
    return {item.evidence_ref.reference_id: item.evidence_ref.to_dict() for item in value.target_candidates}


def _reidentified_recipe_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Recompute one mutated recipe's behavior-derived ID and integrity digest."""
    result = copy.deepcopy(dict(payload))
    identity_body = {
        key: value
        for key, value in result.items()
        if key not in {"recipe_id", "recipe_digest"}
    }
    result["recipe_id"] = workspace_contracts._compiled_recipe_id(identity_body)
    digest_body = dict(result)
    digest_body.pop("recipe_digest")
    result["recipe_digest"] = stable_digest(digest_body)
    return result


def test_v1_manifest_is_unchanged_when_wrapped_and_serialized_mapping_is_verified() -> None:
    """Wrapping must preserve V1 bytes and reject altered serialized snapshots."""
    manifest = create_manifest("Inspect the exact bounded project", organ_id="EORG-v1-compat")
    before, digest = copy.deepcopy(manifest.to_dict()), manifest.compute_digest()
    compile_coding_spatial_workspace_recipe(
        base_manifest=manifest,
        expected_manifest_timestamps=_trusted_manifest_timestamps(manifest),
        project_projection=project(),
        expected_project_projection=project(),
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
        expected_project_projection=project(),
        canonical_intent_digest=D["1"],
        adapter_refs=(ref("adapter:compass", D["2"]),),
        evidence_refs=(ref("evidence:source", D["3"]),),
        expected_manifest_timestamps=(serialized["created_at"], serialized["expires_at"]),
    )
    tampered = copy.deepcopy(serialized)
    tampered["objective"] = "tampered while retaining phase_hash"
    with pytest.raises(ValueError, match="digest does not match"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=tampered,
            expected_manifest_timestamps=_trusted_manifest_timestamps(tampered),
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )
    wrong_version = copy.deepcopy(serialized)
    wrong_version["manifest_version"] = "AURA_EPHEMERAL_ORGAN_V2"
    with pytest.raises(ValueError, match="unsupported base manifest version"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=wrong_version,
            expected_manifest_timestamps=_trusted_manifest_timestamps(wrong_version),
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )


def test_contracts_round_trip_and_complete_current_bindings_validate() -> None:
    """Every exact record must round-trip and rebind to complete current truth."""
    p, (r, _), o = project(), recipe(), observation()
    assert ProjectContextProjection.from_dict(p.to_dict()).to_dict() == p.to_dict()
    assert EphemeralWorkspaceRecipe.from_dict(r.to_dict()).to_dict() == r.to_dict()
    assert MultimodalSpatialObservation.from_dict(o.to_dict()).to_dict() == o.to_dict()
    p.validate_bindings(expected_projection=p)
    r.validate_bindings(
        expected_intent_digest=D["1"],
        expected_project_projection_id=p.projection_id,
        expected_project_projection_digest=p.projection_digest,
        expected_base_manifest_ref=r.base_manifest_ref,
        expected_adapter_refs={item.reference_id: item.to_dict() for item in r.adapter_refs},
        expected_evidence_refs={item.reference_id: item.to_dict() for item in r.evidence_refs},
        expected_recipe=r,
    )
    o.validate_bindings(
        expected_scene_id="scene:coding-workspace",
        expected_scene_digest=D["1"],
        expected_session_id="session:local",
        expected_session_digest=D["2"],
        expected_entity_digests={"entity:function-node": D["3"]},
        expected_evidence_refs=expected_observation_evidence(o),
        expected_observation=o,
    )


def test_canonicalization_and_primitive_parsing_are_strict_and_lossless() -> None:
    """Malformed JSON-like values must never be coerced into valid identities."""
    with pytest.raises(ValueError, match="keys must be strings"):
        stable_digest({1: "x"})
    with pytest.raises(ValueError, match="sets are not JSON"):
        stable_digest({1, 2})
    with pytest.raises(ValueError, match="object exceeds its item ceiling"):
        stable_digest({f"key-{index}": index for index in range(workspace_contracts.MAX_CANONICAL_ITEMS + 1)})
    with pytest.raises(ValueError, match="sequence exceeds its item ceiling"):
        stable_digest(list(range(workspace_contracts.MAX_CANONICAL_ITEMS + 1)))
    with pytest.raises(ValueError, match="valid Unicode scalar values"):
        stable_digest("\ud800")
    with pytest.raises(ValueError, match="must be a string"):
        CanonicalReference(1, "owner", "owner://x", D["1"])
    with pytest.raises(ValueError, match="JSON number"):
        SpatialReferentBinding("b", "s", D["1"], "session", D["2"], "e", D["3"], True,
                               ref("evidence:x", D["4"]), ("GAZE",))
    with pytest.raises(ValueError, match="JSON number"):
        replace(observation(), tracking_quality="0.5", observation_digest="")
    with pytest.raises(ValueError, match="complete 40- or 64-character"):
        RepositoryIdentity("owner/repo", "main", "a" * 32, D["1"])
    zero = replace(observation().target_candidates[0], confidence=0.0, binding_digest="")
    zero_payload = zero.to_dict()
    zero_payload["confidence"] = 0
    with pytest.raises(ValueError, match="binding_digest does not match"):
        SpatialReferentBinding.from_dict(zero_payload)
    malformed_keys: dict[Any, Any] = dict(ref("artifact:keys", D["1"]).to_dict())
    malformed_keys[1] = "integer"
    malformed_keys[(2,)] = "tuple"
    with pytest.raises(ValueError, match="reference keys must be strings"):
        CanonicalReference.from_dict(malformed_keys)


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
    with pytest.raises(ValueError, match="keys must be unique"):
        ref(
            "artifact:duplicate-metadata",
            D["1"],
            metadata=(("source_path", "aura.py"), ("source_path", "other.py")),
        )
    good = ref("artifact:good", D["1"], metadata={"source_path": "aura.py", "line_start": 1, "line_end": 1})
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


def test_project_binding_requires_complete_identity_and_current_projection() -> None:
    """Every intent, owner, repository, and nested reference field is rebound."""
    p = project()
    p.validate_bindings(expected_projection=p)
    stale = replace(p, freshness_class="STALE", projection_digest="")
    with pytest.raises(ValueError, match="stale or unknown project projection"):
        stale.validate_bindings(expected_projection=stale)
    redirected_records = (
        replace(p, projection_id="project:redirected", projection_digest=""),
        replace(p, objective_digest=D["8"], projection_digest=""),
        replace(p, purpose_digest=D["9"], projection_digest=""),
        replace(
            p,
            artifact_evidence_refs=(replace(p.artifact_evidence_refs[0], owner="attacker.owner"),),
            projection_digest="",
        ),
    )
    for redirected in redirected_records:
        with pytest.raises(ValueError, match="projection identity"):
            redirected.validate_bindings(expected_projection=p)
    with pytest.raises(ValueError, match="continuity owner"):
        replace(p, canonical_owner="attacker.owner", projection_digest="")
    with pytest.raises(ValueError, match="privacy_class"):
        replace(p, privacy_class="RAW_PRIVATE_MEMORY", projection_digest="")
    with pytest.raises(ValueError, match="egress_class"):
        replace(p, egress_class="NETWORK_ALLOWED", projection_digest="")
    with pytest.raises(ValueError, match="EXACT canonical truth"):
        replace(
            p,
            artifact_evidence_refs=(replace(p.artifact_evidence_refs[0], truth_class="HYPOTHESIS"),),
            projection_digest="",
        )


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


def test_owner_map_malformed_pair_sequences_fail_with_value_error() -> None:
    """Malformed handoff entries preserve the public ValueError parse contract."""
    r, _ = recipe()
    malformed_maps = ([1, 2], ["a"], [["architecture"]], [["architecture", "owner", "extra"]])
    for malformed in malformed_maps:
        payload = r.to_dict()
        payload["domain_owner_handoff_map"] = malformed
        with pytest.raises(ValueError, match="handoff map entries must be key/owner pairs"):
            EphemeralWorkspaceRecipe.from_dict(payload)


def test_recipe_references_are_canonical_current_and_globally_unique() -> None:
    """Reference ordering, role uniqueness, owner, and freshness are deterministic."""
    adapters = (ref("adapter:z", D["2"]), ref("adapter:a", D["3"]))
    evidence = (ref("evidence:z", D["4"]), ref("evidence:a", D["5"]))
    first, manifest = recipe(adapters=adapters, evidence=evidence)
    second, _ = recipe(manifest=manifest, adapters=tuple(reversed(adapters)), evidence=tuple(reversed(evidence)))
    assert first.recipe_digest == second.recipe_digest
    assert first.recipe_id == second.recipe_id

    duplicate = first.to_dict()
    duplicate["evidence_refs"][0]["reference_id"] = duplicate["adapter_refs"][0]["reference_id"]
    with pytest.raises(ValueError, match="across manifest, adapter, and evidence"):
        EphemeralWorkspaceRecipe.from_dict(duplicate)
    with pytest.raises(ValueError, match="base manifest reference"):
        replace(first, base_manifest_ref=replace(first.base_manifest_ref, freshness_class="STALE"), recipe_digest="")
    with pytest.raises(ValueError, match="base manifest reference"):
        replace(first, base_manifest_ref=replace(first.base_manifest_ref, owner="attacker.owner"), recipe_digest="")
    with pytest.raises(ValueError, match="name does not match wrapper digest"):
        replace(
            first,
            base_manifest_ref=replace(
                first.base_manifest_ref,
                reference_id="organ-manifest-projection:redirected",
                canonical_ref="ephemeral-organ-projection:redirected@AURA_EPHEMERAL_ORGAN_V1",
            ),
            recipe_digest="",
        )


def test_recipe_lifetime_budget_resource_ceiling_and_identity_are_fully_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Recipes cannot outlive manifests, exceed resources, or reuse content IDs."""
    manifest = create_manifest(
        "Bound workspace lifetime",
        organ_id="EORG-bound-lifetime",
        ttl_seconds=10,
    )
    fixed_now = manifest.expires_at - 2.5
    monkeypatch.setattr(workspace_contracts.time, "time", lambda: fixed_now)
    short, _ = recipe(ttl_seconds=300, manifest=manifest)
    assert short.ttl_seconds == 2
    assert short.budgets.wall_time_ms <= 2_000
    assert short.budgets.memory_mb == 256
    assert short.budgets.output_bytes == 1_000_000
    assert short.budgets.tool_calls == 20
    assert short.budgets.model_calls == 0
    with pytest.raises(ValueError, match="budget keys mismatch"):
        recipe(budgets={})
    ttl_budget = WorkspaceBudget(
        wall_time_ms=10_001, memory_mb=256, output_bytes=1_000_000,
        tool_calls=20, model_calls=0, cost_microusd=0, network_calls=0,
    )
    with pytest.raises(ValueError, match="effective workspace TTL"):
        recipe(ttl_seconds=10, manifest_ttl=10, budgets=ttl_budget)
    oversized = WorkspaceBudget(
        wall_time_ms=30_000, memory_mb=257, output_bytes=1_000_000,
        tool_calls=20, model_calls=0, cost_microusd=0, network_calls=0,
    )
    with pytest.raises(ValueError, match="memory_mb exceeds base manifest resource ceiling"):
        recipe(budgets=oversized)
    with pytest.raises(ValueError, match="integer in 1"):
        recipe(ttl_seconds=0)
    with pytest.raises(ValueError, match="integer in 1"):
        recipe(ttl_seconds=MAX_TTL_SECONDS + 1)
    first, manifest = recipe()
    changed, _ = recipe(manifest=manifest, adapters=(ref("adapter:other", D["7"]),))
    assert first.recipe_id != changed.recipe_id
    assert first.recipe_digest != changed.recipe_digest

    with pytest.raises(ValueError, match="recipe_id does not match"):
        replace(first, recipe_id="workspace-recipe:forged-identity", recipe_digest="")

    for field_name in ("network_calls", "model_calls"):
        unsafe_budget = first.to_dict()
        unsafe_budget["budgets"][field_name] = 1
        with pytest.raises(ValueError, match=f"{field_name} at zero"):
            EphemeralWorkspaceRecipe.from_dict(unsafe_budget)


def test_observation_temporal_transcript_inputs_targets_and_evidence_fail_closed() -> None:
    """Cross-field multimodal bindings must be exact, bounded, and current."""
    base = observation()
    duplicate_entity_target = replace(
        base.target_candidates[0],
        binding_id="binding:duplicate-entity",
        evidence_ref=ref("evidence:duplicate-entity", D["5"]),
        binding_digest="",
    )
    with pytest.raises(ValueError, match="unique target entity IDs"):
        replace(
            base,
            target_candidates=(base.target_candidates[0], duplicate_entity_target),
            observation_digest="",
        )
    with pytest.raises(ValueError, match="invalid temporal"):
        replace(base, temporal_window_start_ms=1000, temporal_window_end_ms=999, observation_digest="")
    with pytest.raises(ValueError, match="invalid temporal"):
        replace(base, temporal_window_start_ms=0, temporal_window_end_ms=60_001, observation_digest="")
    with pytest.raises(ValueError, match="transcript digest"):
        replace(base, transcript_digest=D["8"], observation_digest="")
    with pytest.raises(ValueError, match="unique"):
        observation(sources=("VOICE", "VOICE"))
    with pytest.raises(ValueError, match="unique"):
        observation(binding_sources=("GAZE", "GAZE"))
    with pytest.raises(ValueError, match="bounded target sequence"):
        replace(base, target_candidates=(item for item in base.target_candidates), observation_digest="")
    with pytest.raises(ValueError, match="expected_referent evidence_refs is required"):
        base.validate_bindings(
            expected_scene_id="scene:coding-workspace",
            expected_scene_digest=D["1"],
            expected_session_id="session:local",
            expected_session_digest=D["2"],
            expected_entity_digests={"entity:function-node": D["3"]},
            expected_evidence_refs=None,
        )
    oversized_entities = {
        f"entity:{index}": D["3"]
        for index in range(33)
    }
    with pytest.raises(ValueError, match="entity reference set mismatch"):
        base.validate_bindings(
            expected_scene_id=base.scene_id,
            expected_scene_digest=base.scene_digest,
            expected_session_id=base.session_id,
            expected_session_digest=base.session_digest,
            expected_entity_digests=oversized_entities,
            expected_evidence_refs=expected_observation_evidence(base),
            expected_observation=base,
        )
    wrong_evidence = expected_observation_evidence(base)
    wrong_evidence["evidence:referent"]["digest"] = D["9"]
    with pytest.raises(ValueError, match="stale referent evidence"):
        base.validate_bindings(
            expected_scene_id="scene:coding-workspace",
            expected_scene_digest=D["1"],
            expected_session_id="session:local",
            expected_session_digest=D["2"],
            expected_entity_digests={"entity:function-node": D["3"]},
            expected_evidence_refs=wrong_evidence,
        )
    with pytest.raises(ValueError, match="referent evidence must be current"):
        replace(
            base.target_candidates[0],
            evidence_ref=replace(base.target_candidates[0].evidence_ref, freshness_class="UNKNOWN"),
            binding_digest="",
        )
    original_target = base.target_candidates[0]
    conflicting_target = replace(
        original_target,
        binding_id="binding:conflicting-evidence",
        entity_id="entity:conflicting-evidence",
        entity_digest=D["8"],
        evidence_ref=replace(
            original_target.evidence_ref,
            owner="attacker.owner",
            digest=D["9"],
        ),
        binding_digest="",
    )
    with pytest.raises(ValueError, match="unique evidence reference IDs"):
        replace(
            base,
            target_candidates=(original_target, conflicting_target),
            observation_digest="",
        )
    redirected_target = replace(
        original_target,
        scene_id="scene:redirected",
        session_id="session:redirected",
        binding_digest="",
    )
    redirected_observation = replace(
        base,
        scene_id="scene:redirected",
        session_id="session:redirected",
        target_candidates=(redirected_target,),
        observation_digest="",
    )
    with pytest.raises(ValueError, match="stale scene id"):
        redirected_observation.validate_bindings(
            expected_scene_id=base.scene_id,
            expected_scene_digest=base.scene_digest,
            expected_session_id=base.session_id,
            expected_session_digest=base.session_digest,
            expected_entity_digests={original_target.entity_id: original_target.entity_digest},
            expected_evidence_refs=expected_observation_evidence(redirected_observation),
        )


def test_contract_dataclass_canonicalization_whitespace_digest_and_metadata_are_exact() -> None:
    """Public serializers and exact spellings must define one canonical identity."""
    reference = ref("artifact:canonical", D["1"], metadata={"manifest_version": "AURA_EPHEMERAL_ORGAN_V1"})
    assert stable_digest(reference) == stable_digest(reference.to_dict())

    @dataclass
    class PlainDataclass:
        value: int

    assert canonical_json(PlainDataclass(1)) == '{"value":1}'
    with pytest.raises(ValueError, match="surrounding whitespace"):
        CanonicalReference("artifact:space", "owner", " owner://artifact ", D["1"])
    with pytest.raises(ValueError, match="lowercase"):
        CanonicalReference("artifact:upper", "owner", "owner://artifact", "A" * 64)
    with pytest.raises(ValueError, match="lowercase"):
        RepositoryIdentity("owner/repo", "main", "A" * 40, D["1"])
    with pytest.raises(ValueError, match="unsupported characters"):
        ref("artifact:bad-version", D["1"], metadata={"manifest_version": "bad version"})


def test_manifest_snapshot_requires_stored_hash_complete_shape_and_safe_policy() -> None:
    """Live and serialized V1 manifests must preserve their stored safe identity."""
    live = create_manifest("Verify stored phase hash", organ_id="EORG-stored-hash")
    live.creator = "attacker"
    with pytest.raises(ValueError, match="digest does not match"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=live,
            expected_manifest_timestamps=_trusted_manifest_timestamps(live),
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )

    incomplete = {
        "manifest_version": "AURA_EPHEMERAL_ORGAN_V1",
        "organ_id": "EORG-incomplete",
        "ttl_seconds": 300,
        "phase_hash": "0" * 32,
    }
    with pytest.raises(ValueError, match="base manifest keys mismatch"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=incomplete,
            expected_manifest_timestamps=_trusted_manifest_timestamps(incomplete),
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )

    resolved = create_manifest("Accept canonical resolver digest", organ_id="EORG-resolved")
    resolved.capability_resolution_digest = "a" * 16
    resolved.phase_hash = resolved.compute_digest()
    compile_coding_spatial_workspace_recipe(
        base_manifest=resolved,
        expected_manifest_timestamps=_trusted_manifest_timestamps(resolved),
        project_projection=project(),
        expected_project_projection=project(),
        canonical_intent_digest=D["1"],
        adapter_refs=(ref("adapter:compass", D["2"]),),
        evidence_refs=(ref("evidence:source", D["3"]),),
    )

    leased = create_manifest(
        "Verify canonical read-only arena lease",
        organ_id="EORG-leased",
        requested_capabilities=["resolve_capabilities", "read_slice", "dissolve"],
    )
    lease_body = {
        "lease_version": "AURA_ARENA_LEASE_V1",
        "domain": "ephemeral",
        "capsule_id": leased.organ_id,
        "holder": leased.organ_id,
        "regions": [{"organ_id": leased.organ_id, "scope": "read_only"}],
        "allowed_actions": sorted(leased.granted_capabilities),
        "forbidden_actions": sorted({
            "network", "install", "shell", "production_mutation",
            "secret_access", "commit", "push", "automatic_crystallization",
        }),
        "mode": "read_only",
        "conflict_policy": "judge_then_reground",
        "status": "active",
        "metadata": {},
    }
    lease_body["lease_id"] = "LEASE-" + workspace_contracts.hashlib.blake2b(
        json.dumps(
            lease_body,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8"),
        digest_size=16,
    ).hexdigest()[:12]
    lease_body["phase_hash"] = workspace_contracts.hashlib.blake2b(
        json.dumps(
            lease_body,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8"),
        digest_size=16,
    ).hexdigest()
    leased.arena_lease = lease_body
    leased.phase_hash = leased.compute_digest()
    compile_coding_spatial_workspace_recipe(
        base_manifest=leased,
        expected_manifest_timestamps=_trusted_manifest_timestamps(leased),
        project_projection=project(),
        expected_project_projection=project(),
        canonical_intent_digest=D["1"],
        adapter_refs=(ref("adapter:compass", D["2"]),),
        evidence_refs=(ref("evidence:source", D["3"]),),
    )

    tampered_lease_hash = copy.deepcopy(leased)
    tampered_lease_hash.arena_lease["phase_hash"] = "0" * 32
    tampered_lease_hash.phase_hash = tampered_lease_hash.compute_digest()
    with pytest.raises(ValueError, match="arena_lease digest does not match content"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=tampered_lease_hash,
            expected_manifest_timestamps=_trusted_manifest_timestamps(tampered_lease_hash),
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )

    redirected_lease_id = copy.deepcopy(leased)
    redirected_lease_id.arena_lease["lease_id"] = "LEASE-000000000000"
    redirected_lease_id_body = dict(redirected_lease_id.arena_lease)
    redirected_lease_id_body.pop("phase_hash")
    redirected_lease_id.arena_lease["phase_hash"] = workspace_contracts.hashlib.blake2b(
        json.dumps(
            redirected_lease_id_body,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8"),
        digest_size=16,
    ).hexdigest()
    redirected_lease_id.phase_hash = redirected_lease_id.compute_digest()
    with pytest.raises(ValueError, match="arena_lease lease_id does not match content"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=redirected_lease_id,
            expected_manifest_timestamps=_trusted_manifest_timestamps(redirected_lease_id),
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )

    unsafe_lease = copy.deepcopy(leased)
    unsafe_lease.arena_lease["allowed_actions"] = ["shell"]
    unsafe_lease.arena_lease["mode"] = "read_write"
    unsafe_identity_body = dict(unsafe_lease.arena_lease)
    unsafe_identity_body.pop("phase_hash")
    unsafe_identity_body.pop("lease_id")
    unsafe_lease.arena_lease["lease_id"] = "LEASE-" + workspace_contracts.hashlib.blake2b(
        json.dumps(
            unsafe_identity_body,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8"),
        digest_size=16,
    ).hexdigest()[:12]
    unsafe_phase_body = dict(unsafe_lease.arena_lease)
    unsafe_phase_body.pop("phase_hash")
    unsafe_lease.arena_lease["phase_hash"] = workspace_contracts.hashlib.blake2b(
        json.dumps(
            unsafe_phase_body,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8"),
        digest_size=16,
    ).hexdigest()
    unsafe_lease.phase_hash = unsafe_lease.compute_digest()
    with pytest.raises(
        ValueError,
        match="arena_lease allowed actions disagree with grants",
    ):
        compile_coding_spatial_workspace_recipe(
            base_manifest=unsafe_lease,
            expected_manifest_timestamps=_trusted_manifest_timestamps(unsafe_lease),
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )

    shifted = create_manifest("Reject shifted live timestamps", organ_id="EORG-shifted")
    trusted_timestamps = (shifted.created_at, shifted.expires_at)
    shifted.created_at += 60
    shifted.expires_at += 60
    with pytest.raises(ValueError, match="timestamp binding mismatch"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=shifted,
            expected_manifest_timestamps=trusted_timestamps,
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )

    huge_cost = create_manifest("Reject cost overflow", organ_id="EORG-cost-overflow")
    huge_cost.resource_budget["cost_usd"] = 1e308
    huge_cost.phase_hash = huge_cost.compute_digest()
    with pytest.raises(ValueError, match="numeric ceiling|micro-USD ceiling"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=huge_cost,
            expected_manifest_timestamps=_trusted_manifest_timestamps(huge_cost),
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )

    paid_cost = create_manifest("Reject paid legacy budget", organ_id="EORG-paid-cost")
    paid_cost.resource_budget["cost_usd"] = 0.01
    paid_cost.phase_hash = paid_cost.compute_digest()
    with pytest.raises(ValueError, match="paid cost authority must remain disabled"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=paid_cost,
            expected_manifest_timestamps=_trusted_manifest_timestamps(paid_cost),
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )

    denied_grant = create_manifest("Reject contradictory denial", organ_id="EORG-denied-grant")
    denied_grant.denied_capabilities.append({"capability": "read_slice", "reason": "contradiction"})
    denied_grant.phase_hash = denied_grant.compute_digest()
    with pytest.raises(ValueError, match="both grant and deny"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=denied_grant,
            expected_manifest_timestamps=_trusted_manifest_timestamps(denied_grant),
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )

    missing_forbidden_paths = create_manifest("Reject open path policy", organ_id="EORG-open-paths")
    missing_forbidden_paths.data_policy["forbidden_paths"] = []
    missing_forbidden_paths.phase_hash = missing_forbidden_paths.compute_digest()
    with pytest.raises(ValueError, match="closed PR1 denylist"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=missing_forbidden_paths,
            expected_manifest_timestamps=_trusted_manifest_timestamps(missing_forbidden_paths),
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )

    model_enabled = create_manifest("Reject model authority", organ_id="EORG-model-enabled")
    model_enabled.resource_budget["model_calls"] = 1
    model_enabled.phase_hash = model_enabled.compute_digest()
    with pytest.raises(ValueError, match="model invocation"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=model_enabled,
            expected_manifest_timestamps=_trusted_manifest_timestamps(model_enabled),
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )

    verifier_extra = create_manifest("Reject verifier expansion", organ_id="EORG-verifier-extra")
    verifier_extra.verifier_requirements["auto_approve"] = False
    verifier_extra.phase_hash = verifier_extra.compute_digest()
    with pytest.raises(ValueError, match="verifier_requirements (?:keys mismatch|exceeds its item ceiling)"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=verifier_extra,
            expected_manifest_timestamps=_trusted_manifest_timestamps(verifier_extra),
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )

    verifier_expanded = create_manifest("Reject extra verifier", organ_id="EORG-verifier-expanded")
    verifier_expanded.verifier_requirements["must_pass"].append("auto_approve")
    verifier_expanded.phase_hash = verifier_expanded.compute_digest()
    with pytest.raises(ValueError, match="closed PR1 profile"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=verifier_expanded,
            expected_manifest_timestamps=_trusted_manifest_timestamps(verifier_expanded),
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )

    unsafe = create_manifest("Reject unsafe policy", organ_id="EORG-unsafe")
    unsafe.granted_capabilities.append("shell")
    unsafe.requested_capabilities.append({
        "capability": "shell", "requested": True, "granted": True, "denied_reason": "",
    })
    unsafe.phase_hash = unsafe.compute_digest()
    with pytest.raises(ValueError, match="closed canonical V1 profile"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=unsafe,
            expected_manifest_timestamps=_trusted_manifest_timestamps(unsafe),
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )


def test_compiler_rejects_expired_stale_and_redirected_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Compilation must fail before emitting wrappers over expired or stale truth."""
    expired = create_manifest("Expired organ", organ_id="EORG-expired", ttl_seconds=10)
    with monkeypatch.context() as trusted_clock:
        trusted_clock.setattr(workspace_contracts.time, "time", lambda: expired.expires_at)
        with pytest.raises(ValueError, match="expired"):
            compile_coding_spatial_workspace_recipe(
                base_manifest=expired,
                expected_manifest_timestamps=_trusted_manifest_timestamps(expired),
                project_projection=project(),
                expected_project_projection=project(),
                canonical_intent_digest=D["1"],
                adapter_refs=(ref("adapter:compass", D["2"]),),
                evidence_refs=(ref("evidence:source", D["3"]),),
            )
    manifest = create_manifest("Reject stale inputs", organ_id="EORG-stale-inputs")
    stale_project = replace(project(), freshness_class="STALE", projection_digest="")
    with pytest.raises(ValueError, match="stale or unknown"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=manifest,
            expected_manifest_timestamps=_trusted_manifest_timestamps(manifest),
            project_projection=stale_project,
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )
    with pytest.raises(ValueError, match="continuity owner"):
        replace(project(), canonical_owner="attacker.owner", projection_digest="")
    with pytest.raises(ValueError, match="current or bounded"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=manifest,
            expected_manifest_timestamps=_trusted_manifest_timestamps(manifest),
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:stale", D["2"], "STALE"),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )


def test_recipe_binding_revalidates_complete_manifest_and_dependency_identities() -> None:
    """Digest-only equality cannot redirect canonical owners or projection identity."""
    original, _ = recipe()
    altered_payload = original.to_dict()
    altered_payload["adapter_refs"][0]["owner"] = "attacker.owner"
    altered_payload = _reidentified_recipe_payload(altered_payload)
    altered = EphemeralWorkspaceRecipe.from_dict(altered_payload)
    with pytest.raises(ValueError, match="stale adapter reference"):
        altered.validate_bindings(
            expected_intent_digest=original.canonical_intent_digest,
            expected_project_projection_id=original.project_projection_id,
            expected_project_projection_digest=original.project_projection_digest,
            expected_base_manifest_ref=original.base_manifest_ref,
            expected_adapter_refs={item.reference_id: item.to_dict() for item in original.adapter_refs},
            expected_evidence_refs={item.reference_id: item.to_dict() for item in original.evidence_refs},
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
        if semantic_validator is validate_recipe_semantics:
            assert semantic_validator(payload, expected_recipe=payload).to_dict() == payload
        elif semantic_validator is validate_project_semantics:
            assert semantic_validator(payload, expected_projection=payload).to_dict() == payload
        else:
            assert semantic_validator(payload, expected_observation=payload).to_dict() == payload
        tampered = copy.deepcopy(payload)
        tampered["authority"]["automatic_merge"] = True
        assert list(validator.iter_errors(tampered))

    project_schema = Draft202012Validator(json.loads((ROOT / "schemas" / "aura_project_context_projection.schema.json").read_text()))
    bad_metadata = project().to_dict()
    bad_metadata["artifact_evidence_refs"][0]["metadata"] = {"hand_joints": [1, 2]}
    assert list(project_schema.iter_errors(bad_metadata))

    project_truth = project().to_dict()
    project_truth["artifact_evidence_refs"][0]["truth_class"] = "HYPOTHESIS"
    assert list(project_schema.iter_errors(project_truth))

    recipe_schema = Draft202012Validator(json.loads((ROOT / "schemas" / "aura_ephemeral_workspace_recipe.schema.json").read_text()))
    recipe_truth = recipe()[0].to_dict()
    recipe_truth["adapter_refs"][0]["truth_class"] = "HYPOTHESIS"
    assert list(recipe_schema.iter_errors(recipe_truth))
    dangling = recipe()[0].to_dict()
    dangling["dependency_edges"] = [{"source_capability_id": "compile_compass_packet", "target_capability_id": "unknown"}]
    assert list(recipe_schema.iter_errors(dangling))
    with pytest.raises(ValueError, match="invalid recipe dependency"):
        validate_recipe_semantics(dangling, expected_recipe=recipe()[0])

    observation_schema = Draft202012Validator(json.loads((ROOT / "schemas" / "aura_multimodal_spatial_observation.schema.json").read_text()))
    observation_truth = observation().to_dict()
    observation_truth["target_candidates"][0]["evidence_ref"]["truth_class"] = "HYPOTHESIS"
    assert list(observation_schema.iter_errors(observation_truth))
    bad_window = observation().to_dict()
    bad_window["temporal_window_end_ms"] = bad_window["temporal_window_start_ms"] - 1
    assert not list(observation_schema.iter_errors(bad_window))
    with pytest.raises(ValueError, match="invalid temporal"):
        validate_observation_semantics(bad_window)


def test_contract_module_has_docstrings_and_no_operational_or_persistence_calls() -> None:
    """The contract module remains documented and non-operational."""
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
    assert imports <= {"__future__", "collections", "dataclasses", "enum", "hashlib", "json", "math", "re", "time", "types", "typing", "aura_ephemeral_path_policy"}
    assert all(ast.get_docstring(node) for node in definitions)
    prohibited_names = {"open", "exec", "eval", "compile", "__import__", "Popen"}
    prohibited_attributes = {"connect", "run", "Popen", "system", "unlink", "write_text", "write_bytes"}
    bare_calls = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    attribute_calls = {node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
    assert not bare_calls & prohibited_names
    assert not attribute_calls & prohibited_attributes


def _rehash_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    """Refresh the retained V1 phase hash after an intentional test mutation."""
    payload["phase_hash"] = workspace_contracts._legacy_manifest_digest(payload)
    return payload


def test_review_wave6_nested_manifest_and_capability_boundaries_fail_closed() -> None:
    """Nested routes, path policy, capability sufficiency, and ceilings stay closed."""
    manifest = create_manifest(
        "Compile the bounded workspace",
        organ_id="EORG-wave6",
        requested_capabilities=["resolve_capabilities", "read_slice", "dissolve"],
    )
    base = manifest.to_dict()

    unsafe_cases = (
        ("intent_packet", {"effect": "shell"}, "intent_packet"),
        ("machine_route", {"command": "subprocess"}, "machine_route"),
        ("lexc_route", ["EXECUTE"], "lexc_route"),
        ("boundary_contracts", [{"authority": "write"}], "boundary_contracts"),
    )
    for field, value, message in unsafe_cases:
        payload = copy.deepcopy(base)
        payload[field] = value
        _rehash_manifest(payload)
        with pytest.raises(ValueError, match=message):
            compile_coding_spatial_workspace_recipe(
                base_manifest=payload,
                expected_manifest_timestamps=_trusted_manifest_timestamps(payload),
                project_projection=project(),
                expected_project_projection=project(),
                canonical_intent_digest=D["1"],
                adapter_refs=(ref("adapter:compass", D["2"]),),
                evidence_refs=(ref("evidence:source", D["3"]),),
            )

    unsafe_policy = copy.deepcopy(base)
    unsafe_policy["data_policy"]["readable_paths"] = ["/etc/passwd"]
    _rehash_manifest(unsafe_policy)
    with pytest.raises(ValueError, match="readable paths"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=unsafe_policy,
            expected_manifest_timestamps=_trusted_manifest_timestamps(unsafe_policy),
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )

    under_granted = create_manifest(
        "Under-granted",
        organ_id="EORG-under-granted",
        requested_capabilities=["resolve_capabilities"],
    ).to_dict()
    with pytest.raises(ValueError, match="closed canonical V1 profile"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=under_granted,
            expected_manifest_timestamps=_trusted_manifest_timestamps(under_granted),
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )

    oversized = copy.deepcopy(base)
    oversized["requested_capabilities"] = [
        {
            "capability": f"read_slice_{index}",
            "requested": True,
            "granted": False,
            "denied_reason": "unknown_capability",
        }
        for index in range(workspace_contracts.MAX_ITEMS + 1)
    ]
    _rehash_manifest(oversized)
    with pytest.raises(ValueError, match="item ceiling"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=oversized,
            expected_manifest_timestamps=_trusted_manifest_timestamps(oversized),
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )


def test_review_wave6_serialization_numbers_unicode_and_map_bounds_fail_closed() -> None:
    """Canonical serialization rejects reordering, huge numerics, surrogates, and huge maps."""
    r, _ = recipe(adapters=(ref("adapter:z", D["2"]), ref("adapter:a", D["3"])))
    reordered = r.to_dict()
    reordered["adapter_refs"] = list(reversed(reordered["adapter_refs"]))
    with pytest.raises(ValueError, match="canonical serialized"):
        EphemeralWorkspaceRecipe.from_dict(reordered)

    with pytest.raises(ValueError, match="finite JSON number"):
        workspace_contracts._finite_number(10**10000, "huge")
    with pytest.raises(ValueError, match="Unicode scalar"):
        ref("artifact:surrogate", D["1"], metadata={"description": "\ud800"})

    oversized_actual = tuple(
        ref(f"artifact:{index}", D["1"])
        for index in range(workspace_contracts.MAX_ITEMS + 1)
    )
    oversized_expected = {
        reference.reference_id: reference.to_dict()
        for reference in oversized_actual
    }
    with pytest.raises(ValueError, match="size mismatch"):
        workspace_contracts._validate_reference_set(
            oversized_actual,
            oversized_expected,
            "project",
        )


def test_review_wave6_sources_truth_manifest_identity_and_fractional_ttl_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Input spelling, modality containment, exact truth, IDs, and TTL remain exact."""
    with pytest.raises(ValueError, match="uppercase canonical spelling"):
        observation(sources=("voice", "GAZE", "HAND"))

    with pytest.raises(ValueError, match="declared by the observation"):
        observation(sources=("VOICE",), binding_sources=("GAZE",))

    with pytest.raises(ValueError, match="EXACT canonical references"):
        recipe(adapters=(ref("adapter:hypothesis", D["2"], truth="HYPOTHESIS"),))

    long_manifest = create_manifest(
        "Long identifier",
        organ_id="E" * 192,
        requested_capabilities=["resolve_capabilities", "read_slice", "dissolve"],
    )
    compiled = compile_coding_spatial_workspace_recipe(
        base_manifest=long_manifest,
        expected_manifest_timestamps=_trusted_manifest_timestamps(long_manifest),
        project_projection=project(),
        expected_project_projection=project(),
        canonical_intent_digest=D["1"],
        adapter_refs=(ref("adapter:compass", D["2"]),),
        evidence_refs=(ref("evidence:source", D["3"]),),
    )
    assert len(compiled.base_manifest_ref.reference_id) <= 192
    assert len(compiled.base_manifest_ref.canonical_ref) <= 192

    short = create_manifest(
        "Fractional expiry",
        organ_id="EORG-fractional",
        ttl_seconds=2,
        requested_capabilities=["resolve_capabilities", "read_slice", "dissolve"],
    )
    monkeypatch.setattr(workspace_contracts.time, "time", lambda: short.expires_at - 0.5)
    with pytest.raises(ValueError, match="less than one whole second"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=short,
            expected_manifest_timestamps=_trusted_manifest_timestamps(short),
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )


def test_waboose_request_reviews_itself() -> None:
    """The review request must include itself in its complete review scope."""
    request_path = ROOT / ".aura/waboose_requests/intent_native_spatial_workspace_pr1.v1.json"
    payload = json.loads(request_path.read_text(encoding="utf-8"))
    assert ".aura/waboose_requests/intent_native_spatial_workspace_pr1.v1.json" in payload["review_files"]


def test_review_wave7_recursion_frozen_profile_and_wrapper_metadata_fail_closed() -> None:
    """Depth, immutable demonstration state, and wrapper metadata stay exact."""
    nested: Any = "leaf"
    for _ in range(workspace_contracts.MAX_CANONICAL_DEPTH + 2):
        nested = [nested]
    with pytest.raises(ValueError, match="depth ceiling"):
        stable_digest(nested)

    with pytest.raises(TypeError):
        workspace_contracts._FROZEN_DEFINITION["capability_ids"] = ("shell",)
    with pytest.raises(TypeError):
        CODING_SPATIAL_WORKSPACE_V1_DEFINITION["capability_ids"] = ("shell",)

    r, _ = recipe()
    with pytest.raises(ValueError, match="metadata is incomplete"):
        replace(
            r,
            base_manifest_ref=replace(r.base_manifest_ref, metadata={}),
            recipe_digest="",
        )


def test_review_wave7_exact_referent_and_complete_recipe_observation_bindings() -> None:
    """Rebinding authenticates complete lifecycle, parent, target, and evidence records."""
    r, _ = recipe()
    changed_budget = replace(
        r.budgets,
        output_bytes=max(0, r.budgets.output_bytes - 1),
    )
    changed_payload = r.to_dict()
    changed_payload["budgets"] = changed_budget.to_dict()
    changed_payload = _reidentified_recipe_payload(changed_payload)
    changed_recipe = EphemeralWorkspaceRecipe.from_dict(changed_payload)
    with pytest.raises(ValueError, match="complete recipe identity"):
        changed_recipe.validate_bindings(
            expected_intent_digest=r.canonical_intent_digest,
            expected_project_projection_id=r.project_projection_id,
            expected_project_projection_digest=r.project_projection_digest,
            expected_base_manifest_ref=r.base_manifest_ref,
            expected_adapter_refs={item.reference_id: item.to_dict() for item in r.adapter_refs},
            expected_evidence_refs={item.reference_id: item.to_dict() for item in r.evidence_refs},
            expected_recipe=r,
        )

    o = observation()
    weak_evidence = replace(
        o.target_candidates[0].evidence_ref,
        truth_class="HYPOTHESIS",
    )
    with pytest.raises(ValueError, match="EXACT"):
        replace(
            o.target_candidates[0],
            evidence_ref=weak_evidence,
            binding_digest="",
        )

    changed_parent = replace(
        o,
        normalized_action="COMPARE",
        observation_digest="",
    )
    with pytest.raises(ValueError, match="complete observation identity"):
        changed_parent.validate_bindings(
            expected_scene_id=o.scene_id,
            expected_scene_digest=o.scene_digest,
            expected_session_id=o.session_id,
            expected_session_digest=o.session_digest,
            expected_entity_digests={
                target.entity_id: target.entity_digest
                for target in changed_parent.target_candidates
            },
            expected_evidence_refs=expected_observation_evidence(changed_parent),
            expected_observation=o,
        )

    changed_target = replace(
        o.target_candidates[0],
        confidence=0.5,
        binding_digest="",
    )
    changed_targets_observation = replace(
        o,
        target_candidates=(changed_target,),
        observation_digest="",
    )
    with pytest.raises(ValueError, match="complete observation identity"):
        changed_targets_observation.validate_bindings(
            expected_scene_id=o.scene_id,
            expected_scene_digest=o.scene_digest,
            expected_session_id=o.session_id,
            expected_session_digest=o.session_digest,
            expected_entity_digests={
                target.entity_id: target.entity_digest
                for target in changed_targets_observation.target_candidates
            },
            expected_evidence_refs=expected_observation_evidence(
                changed_targets_observation
            ),
            expected_observation=o,
        )


def test_review_wave7_duplicate_requests_and_serialized_timestamp_rebinding_fail_closed() -> None:
    """Ambiguous capability requests and unauthenticated serialized clocks are rejected."""
    manifest = create_manifest(
        "Reject duplicate capability requests",
        organ_id="EORG-wave7-duplicates",
        requested_capabilities=["resolve_capabilities", "read_slice", "dissolve"],
    )
    manifest.requested_capabilities.append(
        dict(manifest.requested_capabilities[0])
    )
    manifest.phase_hash = manifest.compute_digest()
    with pytest.raises(ValueError, match="duplicate capability requests"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=manifest,
            expected_manifest_timestamps=_trusted_manifest_timestamps(manifest),
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )

    serialized_manifest = create_manifest(
        "Bind serialized timestamps",
        organ_id="EORG-wave7-timestamps",
        requested_capabilities=["resolve_capabilities", "read_slice", "dissolve"],
    ).to_dict()
    with pytest.raises(ValueError, match="requires trusted timestamp bindings"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=serialized_manifest,
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )

    original_timestamps = (
        serialized_manifest["created_at"],
        serialized_manifest["expires_at"],
    )
    resurrected = copy.deepcopy(serialized_manifest)
    resurrected["created_at"] += 3600
    resurrected["expires_at"] += 3600
    with pytest.raises(ValueError, match="timestamp binding mismatch"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=resurrected,
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
            expected_manifest_timestamps=original_timestamps,
        )


def test_review_wave10_bounded_policy_parity_fail_closed() -> None:
    """Live snapshots, scalar/path inputs, resource limits, and schemas stay bounded."""
    live = create_manifest(
        "Reject recursive live manifest snapshots",
        organ_id="EORG-wave10-recursion",
        requested_capabilities=["resolve_capabilities", "read_slice", "dissolve"],
    )
    trusted_live_timestamps = _trusted_manifest_timestamps(live)
    nested: dict[str, Any] = {}
    cursor = nested
    for _ in range(2_000):
        child: dict[str, Any] = {}
        cursor["child"] = child
        cursor = child
    live.ui_manifest = {"schema": nested}
    with pytest.raises(ValueError, match="nesting exceeds"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=live,
            expected_manifest_timestamps=trusted_live_timestamps,
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )

    inflated = create_manifest(
        "Cap inherited resource ceilings",
        organ_id="EORG-wave10-resources",
        requested_capabilities=["resolve_capabilities", "read_slice", "dissolve"],
    )
    inflated.resource_budget["memory_mb"] = workspace_contracts.MAX_INTEGER
    inflated.phase_hash = inflated.compute_digest()
    oversized_budget = WorkspaceBudget(
        wall_time_ms=1_000,
        memory_mb=513,
        context_tokens=0,
        output_bytes=1,
        tool_calls=0,
        model_calls=0,
        cost_microusd=0,
        network_calls=0,
        device_events=0,
    )
    with pytest.raises(ValueError, match="memory_mb exceeds base manifest resource ceiling"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=inflated,
            expected_manifest_timestamps=_trusted_manifest_timestamps(inflated),
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
            budgets=oversized_budget,
        )

    recipe_schema = json.loads(
        (ROOT / "schemas/aura_ephemeral_workspace_recipe.schema.json").read_text()
    )
    recipe_payload, _ = recipe()
    unsafe_calls = recipe_payload.to_dict()
    unsafe_calls["budgets"]["model_calls"] = 1
    unsafe_calls["budgets"]["network_calls"] = 1
    error_paths = {
        tuple(error.absolute_path)
        for error in Draft202012Validator(recipe_schema).iter_errors(unsafe_calls)
    }
    assert ("budgets", "model_calls") in error_paths
    assert ("budgets", "network_calls") in error_paths

    with pytest.raises(ValueError, match="scalar byte ceiling"):
        canonical_json("x" * (workspace_contracts.MAX_CANONICAL_SCALAR_BYTES + 1))
    with pytest.raises(ValueError, match="numeric ceiling"):
        canonical_json(workspace_contracts.MAX_CANONICAL_NUMBER_ABS + 1)

    class OversizedMapping(Mapping[str, Any]):
        def __getitem__(self, key: str) -> Any:
            raise KeyError(key)

        def __iter__(self):
            raise AssertionError("_strict must reject by length before iterating")

        def __len__(self) -> int:
            return 1_000_000

    with pytest.raises(ValueError, match="keys mismatch"):
        workspace_contracts._strict(OversizedMapping(), {"version"}, "oversized")

    with pytest.raises(ValueError, match="handoff map exceeds its item ceiling"):
        workspace_contracts._owner_map(
            {f"domain{index}": f"owner{index}" for index in range(7)}
        )

    safe = ref(
        "artifact:safe-source-path",
        D["1"],
        metadata={"source_path": "src/module.py"},
    )
    assert dict(safe.metadata)["source_path"] == "src/module.py"
    for unsafe_path in (
        ".env",
        ".env.local",
        ".git/credentials",
        "../secret",
        "/absolute/path",
        "C:/secret",
        "src/secrets-token",
        "src/.key",
        "src\\secret.py",
        ".ssh/id_rsa",
        "config/passwords.txt",
        "config/client.pem",
    ):
        with pytest.raises(
            ValueError,
            match=(
                "repository-relative POSIX path|unsafe path segment|"
                "targets a path forbidden"
            ),
        ):
            ref(
                f"artifact:unsafe-source-{stable_digest(unsafe_path)[:12]}",
                D["1"],
                metadata={"source_path": unsafe_path},
            )


def test_review_wave11_complete_bounds_and_schema_parity_fail_closed() -> None:
    """Every budget, key, metadata span, schema path, and live snapshot stays bounded."""
    with pytest.raises(ValueError, match="numeric ceiling"):
        canonical_json(1e308)
    with pytest.raises(ValueError, match="object key exceeds its scalar byte ceiling"):
        canonical_json({"x" * (workspace_contracts.MAX_CANONICAL_SCALAR_BYTES + 1): 1})
    with pytest.raises(ValueError, match="object keys must contain valid Unicode"):
        canonical_json({"\ud800": 1})

    class OversizedMetadata(Mapping[str, Any]):
        def __getitem__(self, key: str) -> Any:
            raise KeyError(key)

        def __iter__(self):
            raise AssertionError("metadata must reject by length before copying")

        def __len__(self) -> int:
            return len(workspace_contracts._METADATA_FIELDS) + 1

    with pytest.raises(ValueError, match="field ceiling"):
        workspace_contracts._metadata(OversizedMetadata(), "reference.metadata")

    for metadata, message in (
        ({"source_path": "src/module.py", "line_start": 0, "line_end": 1}, "integer in 1"),
        ({"source_path": "src/module.py", "line_start": 1}, "requires source_path"),
        ({"source_path": "src/module.py", "line_start": 2, "line_end": 1}, "reversed"),
    ):
        with pytest.raises(ValueError, match=message):
            ref(
                f"artifact:bad-span-{stable_digest(metadata)[:12]}",
                D["1"],
                metadata=metadata,
            )
    valid_span = ref(
        "artifact:valid-span",
        D["1"],
        metadata={"source_path": "src/module.py", "line_start": 1, "line_end": 2},
    )
    assert dict(valid_span.metadata)["line_end"] == 2

    manifest = create_manifest(
        "Reject unbounded context authority",
        organ_id="EORG-wave11-context",
        requested_capabilities=["resolve_capabilities", "read_slice", "dissolve"],
    )
    oversized_context = WorkspaceBudget(
        wall_time_ms=1_000,
        memory_mb=1,
        context_tokens=64_001,
        output_bytes=1,
        tool_calls=0,
        model_calls=0,
        cost_microusd=0,
        network_calls=0,
        device_events=0,
    )
    with pytest.raises(ValueError, match="context_tokens exceeds (?:base manifest resource|the PR1 safe) ceiling"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=manifest,
            expected_manifest_timestamps=_trusted_manifest_timestamps(manifest),
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
            budgets=oversized_context,
        )

    parsed_recipe, _ = recipe()
    oversized_device = parsed_recipe.to_dict()
    oversized_device["budgets"]["device_events"] = 100_001
    with pytest.raises(ValueError, match="device_events exceeds the PR1 safe ceiling"):
        EphemeralWorkspaceRecipe.from_dict(oversized_device)

    schema_cases = (
        (
            "schemas/aura_project_context_projection.schema.json",
            project().to_dict(),
            ("artifact_evidence_refs", 0, "metadata"),
        ),
        (
            "schemas/aura_ephemeral_workspace_recipe.schema.json",
            parsed_recipe.to_dict(),
            ("adapter_refs", 0, "metadata"),
        ),
        (
            "schemas/aura_multimodal_spatial_observation.schema.json",
            observation().to_dict(),
            ("target_candidates", 0, "evidence_ref", "metadata"),
        ),
    )

    def metadata_at(payload: dict[str, Any], path: tuple[Any, ...]) -> dict[str, Any]:
        current: Any = payload
        for part in path:
            current = current[part]
        return current

    for schema_name, base_payload, metadata_path in schema_cases:
        schema = json.loads((ROOT / schema_name).read_text())
        validator = Draft202012Validator(schema)
        for unsafe_path in (
            "src/.ENV.local", "SRC/Secrets-token", ".GIT/credentials",
            ".SSH/id_rsa", "config/CLIENT.PEM", "config/Password.txt",
        ):
            payload = copy.deepcopy(base_payload)
            metadata_at(payload, metadata_path).clear()
            metadata_at(payload, metadata_path)["source_path"] = unsafe_path
            assert list(validator.iter_errors(payload)), (schema_name, unsafe_path)
        bad_line = copy.deepcopy(base_payload)
        metadata_at(bad_line, metadata_path).clear()
        metadata_at(bad_line, metadata_path).update(
            {"source_path": "src/module.py", "line_start": 0, "line_end": 1}
        )
        assert list(validator.iter_errors(bad_line)), schema_name

    recipe_schema = json.loads(
        (ROOT / "schemas/aura_ephemeral_workspace_recipe.schema.json").read_text()
    )
    unsafe_budget = parsed_recipe.to_dict()
    unsafe_budget["budgets"]["context_tokens"] = 64_001
    unsafe_budget["budgets"]["device_events"] = 100_001
    budget_error_paths = {
        tuple(error.absolute_path)
        for error in Draft202012Validator(recipe_schema).iter_errors(unsafe_budget)
    }
    assert ("budgets", "context_tokens") in budget_error_paths
    assert ("budgets", "device_events") in budget_error_paths

    observation_schema = json.loads(
        (ROOT / "schemas/aura_multimodal_spatial_observation.schema.json").read_text()
    )
    orphan_transcript = observation().to_dict()
    orphan_transcript["speech_text"] = ""
    orphan_transcript["transcript_digest"] = D["1"]
    assert list(Draft202012Validator(observation_schema).iter_errors(orphan_transcript))

    primary = create_manifest(
        "Single snapshot A",
        organ_id="EORG-wave11-single-snapshot",
        requested_capabilities=["resolve_capabilities", "read_slice", "dissolve"],
    ).to_dict()
    alternate = copy.deepcopy(primary)
    alternate["objective"] = "Single snapshot B"
    alternate["objective_hash"] = workspace_contracts.hashlib.blake2b(
        alternate["objective"].encode("utf-8"), digest_size=12
    ).hexdigest()
    alternate["phase_hash"] = workspace_contracts._legacy_manifest_digest(alternate)

    class TogglingManifest:
        def __init__(self) -> None:
            self.calls = 0

        def to_dict(self) -> dict[str, Any]:
            snapshots = (primary, alternate, primary)
            result = copy.deepcopy(snapshots[self.calls % len(snapshots)])
            self.calls += 1
            return result

    toggling = TogglingManifest()
    compiled = compile_coding_spatial_workspace_recipe(
        base_manifest=toggling,
        expected_manifest_timestamps=(primary["created_at"], primary["expires_at"]),
        project_projection=project(),
        expected_project_projection=project(),
        canonical_intent_digest=D["1"],
        adapter_refs=(ref("adapter:compass", D["2"]),),
        evidence_refs=(ref("evidence:source", D["3"]),),
    )
    assert toggling.calls == 1
    assert dict(compiled.base_manifest_ref.metadata)["source_digest"]


def test_structural_trust_boundary_parse_bind_admit_is_explicit() -> None:
    """Parsing proves structure; admission requires an independently trusted recipe."""
    admitted, _ = recipe()
    parsed = EphemeralWorkspaceRecipe.from_dict(admitted.to_dict())
    assert parsed.to_dict() == admitted.to_dict()
    with pytest.raises(ValueError, match="expected_recipe is required"):
        validate_recipe_semantics(parsed.to_dict())
    assert validate_recipe_semantics(
        parsed.to_dict(), expected_recipe=admitted
    ).to_dict() == admitted.to_dict()

    redirected_payload = admitted.to_dict()
    redirected_payload["adapter_refs"][0]["owner"] = "attacker.owner"
    redirected_payload = _reidentified_recipe_payload(redirected_payload)
    redirected = EphemeralWorkspaceRecipe.from_dict(redirected_payload)
    with pytest.raises(ValueError, match="complete recipe identity"):
        validate_recipe_semantics(
            redirected.to_dict(), expected_recipe=admitted
        )


class _OneShotMapping(Mapping):
    """A mapping that fails if record content is traversed more than once."""

    def __init__(self, payload: Mapping[str, Any]) -> None:
        self._payload = dict(payload)
        self.item_reads = 0

    def __getitem__(self, key: str) -> Any:
        return self._payload[key]

    def __iter__(self):
        return iter(self._payload)

    def __len__(self) -> int:
        return len(self._payload)

    def items(self):
        self.item_reads += 1
        if self.item_reads > 1:
            raise AssertionError("serialized mapping content was read more than once")
        return self._payload.items()


class _LyingSequence(Sequence):
    """A sequence whose reported length understates its observed breadth."""

    def __init__(self, values: Sequence[Any]) -> None:
        self._values = tuple(values)
        self.iterations = 0

    def __getitem__(self, index):
        return self._values[index]

    def __len__(self) -> int:
        return 1

    def __iter__(self):
        self.iterations += 1
        return iter(self._values)


class _SurrogateEnum(Enum):
    BAD = "\ud800"


def test_all_serialized_records_use_one_deep_detached_snapshot() -> None:
    """Every public parser consumes top-level and nested hostile containers once."""
    p, (r, _), o = project(), recipe(), observation()
    cases = (
        (workspace_contracts.AuthorityEnvelope, p.authority.to_dict()),
        (ProjectContextProjection, p.to_dict()),
        (EphemeralWorkspaceRecipe, r.to_dict()),
        (MultimodalSpatialObservation, o.to_dict()),
        (RepositoryIdentity, p.repository_identity.to_dict()),
        (CanonicalReference, p.artifact_evidence_refs[0].to_dict()),
        (SpatialReferentBinding, o.target_candidates[0].to_dict()),
        (WorkspaceBudget, r.budgets.to_dict()),
        (DependencyEdge, r.dependency_edges[0].to_dict()),
    )
    for record_type, payload in cases:
        hostile = _OneShotMapping(payload)
        assert record_type.from_dict(hostile).to_dict() == payload
        assert hostile.item_reads == 1

    nested_payload = p.to_dict()
    nested = _LyingSequence(nested_payload["artifact_evidence_refs"])
    nested_payload["artifact_evidence_refs"] = nested
    assert ProjectContextProjection.from_dict(nested_payload).to_dict() == p.to_dict()
    assert nested.iterations == 1


def test_semantic_validators_and_compiler_require_complete_trusted_binding() -> None:
    """Parsing never becomes project, observation, recipe, or compiler admission."""
    p, (r, manifest), o = project(), recipe(), observation()
    with pytest.raises(ValueError, match="expected_projection is required"):
        validate_project_semantics(p.to_dict())
    with pytest.raises(ValueError, match="expected_observation is required"):
        validate_observation_semantics(o.to_dict())
    with pytest.raises(ValueError, match="expected_recipe is required"):
        validate_recipe_semantics(r.to_dict())
    assert validate_project_semantics(p.to_dict(), expected_projection=p) == p
    assert validate_observation_semantics(o.to_dict(), expected_observation=o) == o
    assert validate_recipe_semantics(r.to_dict(), expected_recipe=r) == r

    redirected_payload = p.to_dict()
    redirected_payload["artifact_evidence_refs"][0]["owner"] = "attacker.owner"
    digest_body = dict(redirected_payload)
    digest_body.pop("projection_digest")
    redirected_payload["projection_digest"] = stable_digest(digest_body)
    redirected = ProjectContextProjection.from_dict(redirected_payload)
    with pytest.raises(ValueError, match="stale project projection identity"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=manifest,
            expected_manifest_timestamps=_trusted_manifest_timestamps(manifest),
            project_projection=redirected,
            expected_project_projection=p,
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )


def test_observed_breadth_and_hostile_metadata_protocols_fail_closed() -> None:
    """Reported lengths, equality hooks, and broken counts cannot bypass bounds."""
    r, _ = recipe()
    with pytest.raises(ValueError, match="adapter_refs exceeds its item ceiling"):
        replace(
            r,
            adapter_refs=_LyingSequence(
                [r.adapter_refs[0]] * (workspace_contracts.MAX_ITEMS + 1)
            ),
            recipe_digest="",
        )
    with pytest.raises(ValueError, match="bounded sequence"):
        replace(
            r,
            dependency_edges=_LyingSequence(
                [r.dependency_edges[0]]
                * (workspace_contracts.MAX_DEPENDENCY_EDGES + 1)
            ),
            recipe_digest="",
        )
    o = observation()
    with pytest.raises(ValueError, match="bounded target sequence"):
        replace(
            o,
            target_candidates=_LyingSequence([o.target_candidates[0]] * 33),
            observation_digest="",
        )

    class EqualityMapping(Mapping[str, Any]):
        def __getitem__(self, key: str) -> Any:
            return {"note": "retained"}[key]

        def __iter__(self):
            return iter(("note",))

        def __len__(self) -> int:
            return 1

        def __eq__(self, other: object) -> bool:
            return True

    assert dict(workspace_contracts._metadata(EqualityMapping(), "metadata")) == {
        "note": "retained"
    }

    class BrokenLengthMapping(EqualityMapping):
        def __len__(self) -> int:
            raise TypeError("hostile length")

    with pytest.raises(ValueError, match="invalid item count"):
        workspace_contracts._metadata(BrokenLengthMapping(), "metadata")

    class BrokenPair(Sequence[Any]):
        def __getitem__(self, index: int) -> Any:
            return ("key", "value")[index]

        def __len__(self) -> int:
            raise TypeError("hostile pair length")

    class BrokenPairMapping(Mapping[str, Any]):
        def __getitem__(self, key: str) -> Any:
            raise KeyError(key)

        def __iter__(self):
            return iter(())

        def __len__(self) -> int:
            return 1

        def items(self):
            return (BrokenPair(),)

    with pytest.raises(ValueError, match="entries must be key/value pairs"):
        workspace_contracts._bounded_mapping_snapshot(
            BrokenPairMapping(), "hostile mapping", 1
        )


def test_enum_backed_strings_fail_before_record_signing() -> None:
    """String-backed enums cannot survive as signed record fields."""
    class Freshness(str, Enum):
        CURRENT = "CURRENT"

    class Evidence(str, Enum):
        DERIVED = "DERIVED"

    with pytest.raises(ValueError, match="project.freshness_class must be a string"):
        replace(
            project(),
            freshness_class=Freshness.CURRENT,
            projection_digest="",
        )
    with pytest.raises(ValueError, match="observation.evidence_class must be a string"):
        replace(
            observation(),
            evidence_class=Evidence.DERIVED,
            observation_digest="",
        )


def test_numeric_subclasses_cannot_spoof_json_or_budget_bounds() -> None:
    """Overloaded numeric subclasses are rejected before comparisons or hashing."""
    class SpoofInt(int):
        def __abs__(self) -> int:
            return 0

        def __ge__(self, other: object) -> bool:
            return True

        def __le__(self, other: object) -> bool:
            return True

    class SpoofFloat(float):
        pass

    hostile = SpoofInt(workspace_contracts.MAX_INTEGER + 1)
    with pytest.raises(ValueError, match="budget.memory_mb must be an integer"):
        WorkspaceBudget(memory_mb=hostile)
    with pytest.raises(ValueError, match="non-JSON value: SpoofInt"):
        canonical_json(hostile)
    with pytest.raises(ValueError, match="must be a finite JSON number"):
        workspace_contracts._finite_number(SpoofFloat(0.5), "hostile.float")
    with pytest.raises(ValueError, match="must be a JSON number"):
        workspace_contracts._prob(SpoofFloat(0.5), "hostile.probability")


def test_authority_subclasses_are_not_trusted_as_exact_records() -> None:
    """Authority subclasses cannot override serialization and become signed."""
    class ForgedAuthority(workspace_contracts.AuthorityEnvelope):
        def to_dict(self) -> dict[str, Any]:
            payload = super().to_dict()
            payload["automatic_merge"] = True
            return payload

    forged = ForgedAuthority()
    cases = (
        (project(), "projection_digest", "project.authority"),
        (recipe()[0], "recipe_digest", "recipe.authority"),
        (observation(), "observation_digest", "observation.authority"),
    )
    for record, digest_field, authority_name in cases:
        with pytest.raises(
            ValueError,
            match=rf"{authority_name} must be an exact AuthorityEnvelope",
        ):
            replace(record, authority=forged, **{digest_field: ""})


def test_schema_delegation_matches_canonical_path_and_text_policy() -> None:
    """Schemas mirror local constraints and explicitly delegate cross-field ordering."""
    for schema_name in (
        "aura_project_context_projection.schema.json",
        "aura_ephemeral_workspace_recipe.schema.json",
        "aura_multimodal_spatial_observation.schema.json",
    ):
        schema = json.loads((ROOT / "schemas" / schema_name).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        assert schema["x-aura-semantic-requires-independent-binding"] is True
        invariants = schema["x-aura-semantic-invariants"]
        assert "UTF-8 byte ceilings" in invariants
        assert "source span ordering delegated to mandatory semantic validation" in invariants
        assert "canonical serialized ordering delegated to mandatory semantic validation" in invariants
        patterns: list[str] = []

        def collect(value: Any) -> None:
            if isinstance(value, dict):
                if "source_path" in value and isinstance(value["source_path"], dict):
                    pattern = value["source_path"].get("pattern")
                    if pattern:
                        patterns.append(pattern)
                for child in value.values():
                    collect(child)
            elif isinstance(value, list):
                for child in value:
                    collect(child)

        collect(schema)
        assert patterns
        for pattern in patterns:
            assert workspace_contracts.re.fullmatch(pattern, "src/credential.txt")
            assert workspace_contracts.re.fullmatch(pattern, "src/credentials.txt") is None

    recipe_schema = json.loads(
        (ROOT / "schemas/aura_ephemeral_workspace_recipe.schema.json").read_text()
    )
    assert recipe_schema["x-aura-semantic-delegations"][
        "base_manifest_resource_budget_binding"
    ] == "mandatory semantic validator"
    assert (
        "base-manifest and trusted compiled-recipe resource ceilings delegated to mandatory semantic validation"
        in recipe_schema["x-aura-semantic-invariants"]
    )

    p = project()
    project_schema = json.loads(
        (ROOT / "schemas" / "aura_project_context_projection.schema.json").read_text()
    )
    for malformed_value in ("main\nredirect", " refs/heads/main", "refs/heads/main "):
        malformed_ref = copy.deepcopy(p.to_dict())
        malformed_ref["repository_identity"]["ref"] = malformed_value
        error_paths = {
            tuple(error.absolute_path)
            for error in Draft202012Validator(project_schema).iter_errors(malformed_ref)
        }
        assert ("repository_identity", "ref") in error_paths

    text_schema_cases = (
        (
            project_schema,
            p.to_dict(),
            ("project_ref",),
        ),
        (
            json.loads(
                (ROOT / "schemas/aura_ephemeral_workspace_recipe.schema.json").read_text()
            ),
            recipe()[0].to_dict(),
            ("adapter_refs", 0, "canonical_ref"),
        ),
        (
            json.loads(
                (ROOT / "schemas/aura_multimodal_spatial_observation.schema.json").read_text()
            ),
            observation().to_dict(),
            ("speech_text",),
        ),
    )
    for validator_schema, payload, path in text_schema_cases:
        current: Any = payload
        for part in path[:-1]:
            current = current[part]
        current[path[-1]] = f" {current[path[-1]]}"
        error_paths = {
            tuple(error.absolute_path)
            for error in Draft202012Validator(validator_schema).iter_errors(payload)
        }
        assert path in error_paths

    reversed_span = p.to_dict()
    reversed_span["artifact_evidence_refs"][0]["metadata"] = {
        "source_path": "src/module.py",
        "line_start": 10,
        "line_end": 1,
    }
    assert not list(Draft202012Validator(project_schema).iter_errors(reversed_span))
    with pytest.raises(ValueError, match="source line range is reversed"):
        validate_project_semantics(reversed_span, expected_projection=p)

    canonical_recipe, _ = recipe()
    reversed_recipe = canonical_recipe.to_dict()
    reversed_recipe["adapter_refs"] = list(reversed(reversed_recipe["adapter_refs"]))
    recipe_schema = json.loads(
        (ROOT / "schemas/aura_ephemeral_workspace_recipe.schema.json").read_text()
    )
    assert not list(Draft202012Validator(recipe_schema).iter_errors(reversed_recipe))
    with pytest.raises(ValueError, match="canonical serialized"):
        EphemeralWorkspaceRecipe.from_dict(reversed_recipe)


def test_enum_unicode_failures_are_normalized_to_value_error() -> None:
    """Recursive Enum canonicalization preserves the public fail-closed exception type."""
    with pytest.raises(ValueError, match="valid Unicode scalar values"):
        stable_digest(_SurrogateEnum.BAD)


def test_hostile_container_protocol_callbacks_fail_closed_at_shared_boundaries() -> None:
    """Accepted hostile containers must not leak protocol-specific exceptions."""
    class ItemsRaisesMapping(Mapping[str, Any]):
        def __getitem__(self, key: str) -> Any:
            raise KeyError(key)

        def __iter__(self):
            return iter(())

        def __len__(self) -> int:
            return 0

        def items(self):
            raise TypeError("hostile items export")

    class ItemsIteratorRaisesMapping(Mapping[str, Any]):
        def __getitem__(self, key: str) -> Any:
            raise KeyError(key)

        def __iter__(self):
            return iter(())

        def __len__(self) -> int:
            return 1

        def items(self):
            class BrokenIterator:
                def __iter__(self):
                    return self

                def __next__(self):
                    raise OverflowError("hostile items iterator")

            return BrokenIterator()

    class SequenceIteratorRaises(Sequence[Any]):
        def __getitem__(self, index: int) -> Any:
            raise OverflowError("hostile sequence iterator")

        def __len__(self) -> int:
            return 1

    class PairLengthRaises(Sequence[Any]):
        def __getitem__(self, index: int) -> Any:
            return ("architecture", "aura_coding_relationship_compass")[index]

        def __len__(self) -> int:
            raise TypeError("hostile pair length")

    for mapping in (ItemsRaisesMapping(), ItemsIteratorRaisesMapping()):
        with pytest.raises(ValueError, match="mapping export protocol"):
            workspace_contracts._bounded_mapping_snapshot(mapping, "hostile mapping", 2)
    with pytest.raises(ValueError, match="sequence protocol"):
        workspace_contracts._bounded_sequence_snapshot(
            SequenceIteratorRaises(), "hostile sequence", 2
        )
    with pytest.raises(ValueError, match="key/value pair"):
        workspace_contracts._bounded_pair_snapshot(PairLengthRaises(), "hostile pair")
    with pytest.raises(ValueError, match="metadata entries must be key/value pairs"):
        workspace_contracts._metadata((PairLengthRaises(),), "metadata")
    with pytest.raises(ValueError, match="handoff map entries must be key/owner pairs"):
        workspace_contracts._owner_map((PairLengthRaises(),))


def test_compiler_timestamp_binding_is_a_bounded_detached_sequence() -> None:
    """Trusted timestamp protocols must fail closed before indexed access."""
    class TimestampIndexRaises(Sequence[Any]):
        def __getitem__(self, index: int) -> Any:
            raise TypeError("hostile timestamp index")

        def __len__(self) -> int:
            return 2

    manifest = create_manifest(
        "Reject hostile trusted timestamp protocols",
        organ_id="EORG-hostile-timestamp-binding",
    )
    with pytest.raises(ValueError, match="trusted timestamp bindings"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=manifest,
            expected_manifest_timestamps=TimestampIndexRaises(),
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )


def test_detached_snapshot_bounds_object_keys_before_using_them_in_paths() -> None:
    """Unknown object keys receive the same scalar/Unicode guard as values."""
    oversized_key = "k" * (workspace_contracts.MAX_CANONICAL_SCALAR_BYTES + 1)
    with pytest.raises(ValueError, match="key exceeds its scalar byte ceiling"):
        workspace_contracts._detached_json_snapshot({oversized_key: 1}, "payload")
    with pytest.raises(ValueError, match="valid Unicode scalar values"):
        workspace_contracts._detached_json_snapshot({"\ud800": 1}, "payload")


def test_schema_delegations_name_all_remaining_public_boundary_semantics() -> None:
    """Schema-only consumers must be told which rejections require admission code."""
    expected = {
        "aura_project_context_projection.schema.json": {
            "current_and_bounded_freshness_admission",
            "unicode_scalar_validation",
            "reference_id_uniqueness_across_project_reference_arrays",
            "repository_identity_digest_equality",
            "project_projection_digest_equality",
            "exact_builtin_integer_representation",
        },
        "aura_ephemeral_workspace_recipe.schema.json": {
            "reference_id_uniqueness_across_adapter_and_evidence_refs",
            "manifest_reference_identity_digest_prefix_binding",
            "unicode_scalar_validation",
            "wall_time_ttl_binding",
            "recipe_digest_equality",
            "behavior_derived_recipe_id",
            "exact_builtin_integer_representation",
            "signed_recipe_expiration_arithmetic",
        },
        "aura_multimodal_spatial_observation.schema.json": {
            "transcript_digest_equality",
            "target_binding_entity_evidence_id_uniqueness",
            "unicode_scalar_validation",
            "target_scene_session_parent_binding",
            "target_input_sources_subset_of_parent",
            "temporal_window_ordering_and_duration_ceiling",
            "binding_digest_equality",
            "observation_digest_equality",
            "exact_builtin_integer_representation",
        },
    }
    for filename, required_delegations in expected.items():
        schema = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
        delegations = schema["x-aura-semantic-delegations"]
        assert required_delegations <= set(delegations)
        assert all(
            delegations[name] == "mandatory semantic validator"
            for name in required_delegations
        )
        invariants = "\n".join(schema["x-aura-semantic-invariants"])
        assert "Unicode scalar validation delegated" in invariants
        assert "exact built-in integer representation delegated" in invariants
        if filename == "aura_ephemeral_workspace_recipe.schema.json":
            assert (
                "signed issued-at plus TTL equals absolute expiration delegated"
                in invariants
            )


def test_exact_builtin_strings_are_required_at_public_scalar_boundaries() -> None:
    """String subclasses and equality-spoof objects cannot become retained identity text."""
    class SpoofedString(str):
        def strip(self) -> str:
            return "trusted"

        def encode(self, *args: Any, **kwargs: Any) -> bytes:
            return b"trusted"

    class EqualitySpoof:
        def __eq__(self, other: object) -> bool:
            return True

        def __hash__(self) -> int:
            return hash("EXACT")

    with pytest.raises(ValueError, match="repository.repository must be a string"):
        RepositoryIdentity(SpoofedString("owner/repo"), "main", MAIN, D["1"])
    with pytest.raises(ValueError, match="reference.truth_class must be a string"):
        CanonicalReference(
            "artifact:spoofed-class",
            "canonical.owner",
            "owner://spoofed",
            D["1"],
            truth_class=EqualitySpoof(),
        )
    with pytest.raises(ValueError, match="non-JSON value"):
        stable_digest(SpoofedString("spoofed canonical scalar"))


def test_dataclass_export_callbacks_are_normalized_to_value_error() -> None:
    """Dataclass exporter lookup, callability, and callback failures fail closed."""
    @dataclass
    class NonCallableExport:
        value: int = 1
        to_dict: Any = 7

    @dataclass
    class RaisingExport:
        value: int = 1

        def to_dict(self) -> dict[str, Any]:
            raise OverflowError("hostile dataclass export")

    for value in (NonCallableExport(), RaisingExport()):
        with pytest.raises(ValueError, match="dataclass has an invalid export protocol"):
            stable_digest(value)


def test_live_manifest_export_callbacks_are_normalized_to_value_error() -> None:
    """Broken live-manifest exporters cannot leak callback-specific exceptions."""
    class NonCallableManifest:
        to_dict: Any = {}

    class RaisingManifest:
        def to_dict(self) -> dict[str, Any]:
            raise TypeError("hostile manifest export")

    for manifest in (NonCallableManifest(), RaisingManifest()):
        with pytest.raises(ValueError, match="base manifest has an invalid export protocol"):
            compile_coding_spatial_workspace_recipe(
                base_manifest=manifest,
                expected_manifest_timestamps=(0, 1),
                project_projection=project(),
                expected_project_projection=project(),
                canonical_intent_digest=D["1"],
                adapter_refs=(ref("adapter:compass", D["2"]),),
                evidence_refs=(ref("evidence:source", D["3"]),),
            )




def test_nested_contract_subclasses_are_rejected_before_parent_signing() -> None:
    """Nested records must be exact types or detached serialized mappings."""
    class RedirectedReference(CanonicalReference):
        def to_dict(self) -> dict[str, Any]:
            payload = super().to_dict()
            payload["owner"] = "attacker.owner"
            return payload

    class RedirectedRepository(RepositoryIdentity):
        def to_dict(self) -> dict[str, Any]:
            payload = super().to_dict()
            payload["repository"] = "attacker/repository"
            return payload

    class RedirectedBudget(WorkspaceBudget):
        def to_dict(self) -> dict[str, int]:
            payload = super().to_dict()
            payload["memory_mb"] = 1
            return payload

    redirected_reference = RedirectedReference(
        "adapter:subclass",
        "canonical.owner",
        "owner://adapter:subclass",
        D["2"],
    )
    with pytest.raises(ValueError, match="exact CanonicalReference"):
        recipe(adapters=(redirected_reference,))

    trusted_project = project()
    repository = trusted_project.repository_identity
    redirected_repository = RedirectedRepository(
        repository.repository,
        repository.ref,
        repository.commit_sha,
        repository.source_tree_digest,
    )
    with pytest.raises(ValueError, match="exact RepositoryIdentity"):
        replace(trusted_project, repository_identity=redirected_repository)

    redirected_budget = RedirectedBudget(memory_mb=512)
    with pytest.raises(ValueError, match="exact WorkspaceBudget"):
        recipe(budgets=redirected_budget)


def test_remaining_exact_record_and_key_boundaries_fail_closed() -> None:
    """Every nested/expected record and map key must cross an exact boundary."""
    class RedirectedEdge(DependencyEdge):
        def to_dict(self) -> dict[str, str]:
            payload = super().to_dict()
            payload["target_capability_id"] = "attacker_capability"
            return payload

    class RedirectedBinding(SpatialReferentBinding):
        def to_dict(self) -> dict[str, Any]:
            payload = super().to_dict()
            payload["entity_id"] = "entity:attacker"
            return payload

    class RedirectedProject(ProjectContextProjection):
        def to_dict(self) -> dict[str, Any]:
            payload = super().to_dict()
            payload["canonical_owner"] = "attacker.owner"
            return payload

    class RedirectedRecipe(EphemeralWorkspaceRecipe):
        def to_dict(self) -> dict[str, Any]:
            payload = super().to_dict()
            payload["ttl_seconds"] += 1
            return payload

    class RedirectedObservation(MultimodalSpatialObservation):
        def to_dict(self) -> dict[str, Any]:
            payload = super().to_dict()
            payload["normalized_action"] = "ATTACKER_ACTION"
            return payload

    class HashBombKey(str):
        def __hash__(self) -> int:
            raise TypeError("hostile key hash")

    class DetachedKeyMapping(Mapping[Any, Any]):
        def __init__(self, key: Any, value: Any) -> None:
            self.key = key
            self.value = value

        def __getitem__(self, key: Any) -> Any:
            if key is self.key:
                return self.value
            raise KeyError(key)

        def __iter__(self):
            return iter((self.key,))

        def __len__(self) -> int:
            return 1

        def items(self):
            return ((self.key, self.value),)

    def clone_as_subclass(record: Any, record_type: type[Any]) -> Any:
        clone = object.__new__(record_type)
        for field in fields(record):
            object.__setattr__(clone, field.name, getattr(record, field.name))
        return clone

    workspace_recipe, _ = recipe()
    dependency = workspace_recipe.dependency_edges[0]
    redirected_edge = RedirectedEdge(
        dependency.source_capability_id,
        dependency.target_capability_id,
    )
    with pytest.raises(ValueError, match="exact DependencyEdge"):
        replace(
            workspace_recipe,
            dependency_edges=(redirected_edge, *workspace_recipe.dependency_edges[1:]),
            recipe_digest="",
        )

    trusted_observation = observation()
    redirected_binding = clone_as_subclass(
        trusted_observation.target_candidates[0], RedirectedBinding
    )
    with pytest.raises(ValueError, match="exact SpatialReferentBinding"):
        replace(
            trusted_observation,
            target_candidates=(redirected_binding,),
            observation_digest="",
        )

    class MasqueradingProject(ProjectContextProjection):
        def to_dict(self) -> dict[str, Any]:
            return project().to_dict()

    trusted_project = project()
    redirected_project = clone_as_subclass(trusted_project, RedirectedProject)
    masquerading_project = clone_as_subclass(trusted_project, MasqueradingProject)
    with pytest.raises(ValueError, match="exact ProjectContextProjection"):
        trusted_project.validate_bindings(expected_projection=redirected_project)
    with pytest.raises(ValueError, match="exact ProjectContextProjection"):
        validate_project_semantics(
            trusted_project.to_dict(), expected_projection=redirected_project
        )

    manifest = create_manifest(
        "Reject projection subclasses at the compiler boundary.",
        organ_id="EORG-project-subclass-boundary",
        requested_capabilities=["resolve_capabilities", "read_slice", "dissolve"],
    )
    with pytest.raises(
        ValueError,
        match="project_projection must be an exact ProjectContextProjection",
    ):
        compile_coding_spatial_workspace_recipe(
            base_manifest=manifest,
            expected_manifest_timestamps=_trusted_manifest_timestamps(manifest),
            project_projection=masquerading_project,
            expected_project_projection=trusted_project,
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )

    redirected_recipe = clone_as_subclass(workspace_recipe, RedirectedRecipe)
    expected_adapters = {
        item.reference_id: item.to_dict() for item in workspace_recipe.adapter_refs
    }
    expected_evidence = {
        item.reference_id: item.to_dict() for item in workspace_recipe.evidence_refs
    }
    with pytest.raises(ValueError, match="exact EphemeralWorkspaceRecipe"):
        workspace_recipe.validate_bindings(
            expected_intent_digest=workspace_recipe.canonical_intent_digest,
            expected_project_projection_id=workspace_recipe.project_projection_id,
            expected_project_projection_digest=workspace_recipe.project_projection_digest,
            expected_base_manifest_ref=workspace_recipe.base_manifest_ref,
            expected_adapter_refs=expected_adapters,
            expected_evidence_refs=expected_evidence,
            expected_recipe=redirected_recipe,
        )
    with pytest.raises(ValueError, match="exact EphemeralWorkspaceRecipe"):
        validate_recipe_semantics(
            workspace_recipe.to_dict(), expected_recipe=redirected_recipe
        )

    redirected_observation = clone_as_subclass(
        trusted_observation, RedirectedObservation
    )
    expected_entities = {
        target.entity_id: target.entity_digest
        for target in trusted_observation.target_candidates
    }
    with pytest.raises(ValueError, match="exact MultimodalSpatialObservation"):
        trusted_observation.validate_bindings(
            expected_scene_id=trusted_observation.scene_id,
            expected_scene_digest=trusted_observation.scene_digest,
            expected_session_id=trusted_observation.session_id,
            expected_session_digest=trusted_observation.session_digest,
            expected_entity_digests=expected_entities,
            expected_evidence_refs=expected_observation_evidence(trusted_observation),
            expected_observation=redirected_observation,
        )
    with pytest.raises(ValueError, match="exact MultimodalSpatialObservation"):
        validate_observation_semantics(
            trusted_observation.to_dict(),
            expected_observation=redirected_observation,
        )

    with pytest.raises(ValueError, match="metadata keys must be strings"):
        workspace_contracts._metadata(((HashBombKey("note"), "retained"),), "metadata")

    expected_reference = ref("adapter:hostile-key", D["2"])
    with pytest.raises(ValueError, match="expected_adapter_refs key must be a string"):
        workspace_contracts._validate_reference_set(
            (expected_reference,),
            DetachedKeyMapping(
                HashBombKey(expected_reference.reference_id),
                expected_reference.to_dict(),
            ),
            "adapter",
        )

    with pytest.raises(ValueError, match="expected entity identifier must be a string"):
        trusted_observation.validate_bindings(
            expected_scene_id=trusted_observation.scene_id,
            expected_scene_digest=trusted_observation.scene_digest,
            expected_session_id=trusted_observation.session_id,
            expected_session_digest=trusted_observation.session_digest,
            expected_entity_digests=DetachedKeyMapping(
                HashBombKey(trusted_observation.target_candidates[0].entity_id),
                trusted_observation.target_candidates[0].entity_digest,
            ),
            expected_evidence_refs=expected_observation_evidence(trusted_observation),
            expected_observation=trusted_observation,
        )

def test_lifecycle_anchor_cross_role_identity_and_explicit_null_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Final contract closure binds delayed admission and every recipe reference role."""
    with pytest.raises(ValueError, match="reference.metadata must be an object"):
        CanonicalReference(
            "artifact:null-metadata",
            "canonical.owner",
            "owner://artifact:null-metadata",
            D["1"],
            metadata=None,
        )
    assert CanonicalReference(
        "artifact:default-metadata",
        "canonical.owner",
        "owner://artifact:default-metadata",
        D["1"],
    ).to_dict()["metadata"] == {}

    current, _ = recipe()
    colliding_adapter = replace(
        current.adapter_refs[0],
        reference_id=current.base_manifest_ref.reference_id,
    )
    with pytest.raises(
        ValueError,
        match="duplicate recipe reference IDs across manifest, adapter, and evidence roles",
    ):
        replace(
            current,
            adapter_refs=(colliding_adapter, *current.adapter_refs[1:]),
            recipe_digest="",
        )

    manifest = create_manifest(
        "Anchor delayed workspace admission to an absolute expiration.",
        organ_id="EORG-absolute-recipe-expiry",
        ttl_seconds=10,
        requested_capabilities=["resolve_capabilities", "read_slice", "dissolve"],
    )
    compile_now = manifest.created_at + 1.25
    monkeypatch.setattr(workspace_contracts.time, "time", lambda: compile_now)
    anchored = compile_coding_spatial_workspace_recipe(
        base_manifest=manifest,
        expected_manifest_timestamps=_trusted_manifest_timestamps(manifest),
        project_projection=project(),
        expected_project_projection=project(),
        canonical_intent_digest=D["1"],
        adapter_refs=(ref("adapter:compass", D["2"]),),
        evidence_refs=(ref("evidence:source", D["3"]),),
        ttl_seconds=3,
    )
    assert anchored.issued_at_epoch_seconds == int(compile_now // 1)
    assert anchored.expires_at_epoch_seconds == anchored.issued_at_epoch_seconds + 3
    assert anchored.expires_at_epoch_seconds <= int(manifest.expires_at // 1)
    assert EphemeralWorkspaceRecipe.from_dict(anchored.to_dict()).to_dict() == anchored.to_dict()

    monkeypatch.setattr(
        workspace_contracts.time,
        "time",
        lambda: float(anchored.expires_at_epoch_seconds),
    )
    with pytest.raises(ValueError, match="workspace recipe is expired"):
        validate_recipe_semantics(anchored.to_dict(), expected_recipe=anchored)
    with pytest.raises(ValueError, match="workspace recipe is expired"):
        anchored.validate_bindings(
            expected_intent_digest=anchored.canonical_intent_digest,
            expected_project_projection_id=anchored.project_projection_id,
            expected_project_projection_digest=anchored.project_projection_digest,
            expected_base_manifest_ref=anchored.base_manifest_ref,
            expected_adapter_refs={
                item.reference_id: item.to_dict() for item in anchored.adapter_refs
            },
            expected_evidence_refs={
                item.reference_id: item.to_dict() for item in anchored.evidence_refs
            },
            expected_recipe=anchored,
        )
