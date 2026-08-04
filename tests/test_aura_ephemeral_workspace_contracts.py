from __future__ import annotations

import ast
import copy
import json
from dataclasses import dataclass, replace
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

# This import intentionally exercises the exact existing V1 manifest compatibility
# boundary rather than replacing the canonical owner with a test-only stub in-repo.
from aura_ephemeral_arena import create_ephemeral_lease
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


def expected_project_refs(value: ProjectContextProjection) -> dict[str, dict]:
    """Return the complete project canonical-reference identity map."""
    return {item.reference_id: item.to_dict() for item in value.all_references()}


def expected_observation_evidence(value: MultimodalSpatialObservation) -> dict[str, dict]:
    """Return the complete referent-evidence canonical-reference identity map."""
    return {item.evidence_ref.reference_id: item.evidence_ref.to_dict() for item in value.target_candidates}


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
    p.validate_bindings(expected_projection=p)
    r.validate_bindings(
        expected_intent_digest=D["1"],
        expected_project_projection_id=p.projection_id,
        expected_project_projection_digest=p.projection_digest,
        expected_base_manifest_ref=r.base_manifest_ref,
        expected_adapter_refs={item.reference_id: item.to_dict() for item in r.adapter_refs},
        expected_evidence_refs={item.reference_id: item.to_dict() for item in r.evidence_refs},
    )
    o.validate_bindings(
        expected_scene_id="scene:coding-workspace",
        expected_scene_digest=D["1"],
        expected_session_id="session:local",
        expected_session_digest=D["2"],
        expected_entity_digests={"entity:function-node": D["3"]},
        expected_evidence_refs=expected_observation_evidence(o),
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
    zero = replace(observation().target_candidates[0], confidence=0.0, binding_digest="")
    zero_payload = zero.to_dict()
    zero_payload["confidence"] = 0
    with pytest.raises(ValueError, match="binding_digest does not match"):
        SpatialReferentBinding.from_dict(zero_payload)
    malformed_keys = ref("artifact:keys", D["1"]).to_dict()
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
        replace(p, canonical_owner="attacker.owner", projection_digest=""),
        replace(
            p,
            artifact_evidence_refs=(replace(p.artifact_evidence_refs[0], owner="attacker.owner"),),
            projection_digest="",
        ),
    )
    for redirected in redirected_records:
        with pytest.raises(ValueError, match="projection identity"):
            redirected.validate_bindings(expected_projection=p)
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
    with pytest.raises(ValueError, match="across adapter and evidence"):
        EphemeralWorkspaceRecipe.from_dict(duplicate)
    with pytest.raises(ValueError, match="base manifest reference"):
        replace(first, base_manifest_ref=replace(first.base_manifest_ref, freshness_class="STALE"), recipe_digest="")
    with pytest.raises(ValueError, match="base manifest reference"):
        replace(first, base_manifest_ref=replace(first.base_manifest_ref, owner="attacker.owner"), recipe_digest="")


def test_recipe_lifetime_budget_resource_ceiling_and_identity_are_fully_bound() -> None:
    """Recipes cannot outlive manifests, exceed resources, or reuse content IDs."""
    short, _ = recipe(ttl_seconds=300, manifest_ttl=10)
    assert short.ttl_seconds == 10
    assert short.budgets.wall_time_ms <= 10_000
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

    forged = first.to_dict()
    forged["recipe_id"] = "workspace-recipe:forged-identity"
    digest_body = dict(forged)
    digest_body.pop("recipe_digest")
    forged["recipe_digest"] = stable_digest(digest_body)
    with pytest.raises(ValueError, match="recipe_id does not match"):
        EphemeralWorkspaceRecipe.from_dict(forged)


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
    with pytest.raises(ValueError, match="expected_referent evidence_refs is required"):
        base.validate_bindings(
            expected_scene_id="scene:coding-workspace",
            expected_scene_digest=D["1"],
            expected_session_id="session:local",
            expected_session_digest=D["2"],
            expected_entity_digests={"entity:function-node": D["3"]},
            expected_evidence_refs=None,
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
            project_projection=project(),
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
            project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )

    resolved = create_manifest("Accept canonical resolver digest", organ_id="EORG-resolved")
    resolved.capability_resolution_digest = "a" * 16
    resolved.phase_hash = resolved.compute_digest()
    compile_coding_spatial_workspace_recipe(
        base_manifest=resolved,
        project_projection=project(),
        canonical_intent_digest=D["1"],
        adapter_refs=(ref("adapter:compass", D["2"]),),
        evidence_refs=(ref("evidence:source", D["3"]),),
    )

    leased = create_manifest(
        "Verify canonical read-only arena lease",
        organ_id="EORG-leased",
        requested_capabilities=["resolve_capabilities", "read_slice", "dissolve"],
    )
    leased.arena_lease = create_ephemeral_lease(
        leased.organ_id,
        leased.granted_capabilities,
        leased.ttl_seconds,
    )
    leased.phase_hash = leased.compute_digest()
    compile_coding_spatial_workspace_recipe(
        base_manifest=leased,
        project_projection=project(),
        canonical_intent_digest=D["1"],
        adapter_refs=(ref("adapter:compass", D["2"]),),
        evidence_refs=(ref("evidence:source", D["3"]),),
    )
    unsafe_lease = copy.deepcopy(leased)
    unsafe_lease.arena_lease["allowed_actions"] = ["shell"]
    unsafe_lease.arena_lease["mode"] = "read_write"
    unsafe_lease.phase_hash = unsafe_lease.compute_digest()
    with pytest.raises(ValueError, match="arena_lease"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=unsafe_lease,
            project_projection=project(),
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
    with pytest.raises(ValueError, match="forbidden or unknown capability"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=unsafe,
            project_projection=project(),
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
                project_projection=project(),
                canonical_intent_digest=D["1"],
                adapter_refs=(ref("adapter:compass", D["2"]),),
                evidence_refs=(ref("evidence:source", D["3"]),),
            )
    with pytest.raises(TypeError, match="now_epoch_seconds"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=expired,
            project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
            now_epoch_seconds=expired.created_at,
        )

    manifest = create_manifest("Reject stale inputs", organ_id="EORG-stale-inputs")
    stale_project = replace(project(), freshness_class="STALE", projection_digest="")
    with pytest.raises(ValueError, match="stale or unknown"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=manifest,
            project_projection=stale_project,
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )
    redirected_project = replace(project(), canonical_owner="attacker.owner", projection_digest="")
    with pytest.raises(ValueError, match="canonical continuity owner"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=manifest,
            project_projection=redirected_project,
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )
    with pytest.raises(ValueError, match="current or bounded"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=manifest,
            project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:stale", D["2"], "STALE"),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )


def test_recipe_binding_revalidates_complete_manifest_and_dependency_identities() -> None:
    """Digest-only equality cannot redirect canonical owners or wrapper identity."""
    original, _ = recipe()
    altered_payload = original.to_dict()
    altered_payload["adapter_refs"][0]["owner"] = "attacker.owner"
    identity_body = {key: value for key, value in altered_payload.items() if key not in {"recipe_id", "recipe_digest"}}
    altered_payload["recipe_id"] = f"workspace-recipe:{stable_digest(identity_body)[:24]}"
    digest_body = dict(altered_payload)
    digest_body.pop("recipe_digest")
    altered_payload["recipe_digest"] = stable_digest(digest_body)
    altered = EphemeralWorkspaceRecipe.from_dict(altered_payload)
    with pytest.raises(ValueError, match="adapter canonical reference"):
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
    assert imports <= {"__future__", "collections", "dataclasses", "enum", "hashlib", "json", "math", "re", "time", "types", "typing"}
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
