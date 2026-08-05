from __future__ import annotations

from pathlib import Path
from textwrap import dedent


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def replace_count(
    text: str, old: str, new: str, expected_count: int, label: str
) -> str:
    count = text.count(old)
    if count != expected_count:
        raise SystemExit(
            f"{label}: expected {expected_count} anchors, found {count}"
        )
    return text.replace(old, new)


def main() -> None:
    code_path = Path("aura_ephemeral_workspace_contracts.py")
    code = code_path.read_text(encoding="utf-8")

    code = replace_once(
        code,
        "            edge if isinstance(edge, DependencyEdge) else DependencyEdge.from_dict(edge)\n",
        "            _exact_contract_record(edge, DependencyEdge, \"recipe.dependency_edges item\")\n",
        "dependency-edge exact admission",
    )
    code = replace_once(
        code,
        "            item if isinstance(item, SpatialReferentBinding) else SpatialReferentBinding.from_dict(item)\n",
        "            _exact_contract_record(item, SpatialReferentBinding, \"observation.target_candidates item\")\n",
        "target-binding exact admission",
    )

    project_old = (
        "        expected = (\n"
        "            expected_projection\n"
        "            if isinstance(expected_projection, ProjectContextProjection)\n"
        "            else ProjectContextProjection.from_dict(expected_projection)\n"
        "        )\n"
    )
    project_new = (
        "        expected = _exact_contract_record(\n"
        "            expected_projection, ProjectContextProjection, \"expected_projection\"\n"
        "        )\n"
    )
    code = replace_count(
        code, project_old, project_new, 2, "expected project exact admission"
    )

    recipe_old = (
        "        expected = (\n"
        "            expected_recipe\n"
        "            if isinstance(expected_recipe, EphemeralWorkspaceRecipe)\n"
        "            else EphemeralWorkspaceRecipe.from_dict(expected_recipe)\n"
        "        )\n"
    )
    recipe_new = (
        "        expected = _exact_contract_record(\n"
        "            expected_recipe, EphemeralWorkspaceRecipe, \"expected_recipe\"\n"
        "        )\n"
    )
    code = replace_count(
        code, recipe_old, recipe_new, 2, "expected recipe exact admission"
    )

    observation_old = (
        "        expected = (\n"
        "            expected_observation\n"
        "            if isinstance(expected_observation, MultimodalSpatialObservation)\n"
        "            else MultimodalSpatialObservation.from_dict(expected_observation)\n"
        "        )\n"
    )
    observation_new = (
        "        expected = _exact_contract_record(\n"
        "            expected_observation,\n"
        "            MultimodalSpatialObservation,\n"
        "            \"expected_observation\",\n"
        "        )\n"
    )
    code = replace_count(
        code,
        observation_old,
        observation_new,
        2,
        "expected observation exact admission",
    )

    key_guard = "not isinstance(key, str)"
    key_guard_count = code.count(key_guard)
    if key_guard_count < 3:
        raise SystemExit(
            f"exact built-in key guards: expected at least 3 anchors, found {key_guard_count}"
        )
    code = code.replace(key_guard, "type(key) is not str")

    expected_refs_old = (
        "    expected_payload: dict[str, Any] = {}\n"
        "    for key, value in expected_pairs:\n"
        "        if type(key) is not str:\n"
        "            raise ValueError(f\"expected_{name}_refs keys must be strings\")\n"
        "        if key in expected_payload:\n"
        "            raise ValueError(f\"duplicate expected_{name}_refs reference: {key}\")\n"
        "        expected_payload[key] = value\n"
    )
    expected_refs_new = (
        "    expected_payload: dict[str, Any] = {}\n"
        "    for key, value in expected_pairs:\n"
        "        validated_key = _id(key, f\"expected_{name}_refs key\")\n"
        "        if validated_key in expected_payload:\n"
        "            raise ValueError(\n"
        "                f\"duplicate expected_{name}_refs reference: {validated_key}\"\n"
        "            )\n"
        "        expected_payload[validated_key] = value\n"
    )
    code = replace_once(
        code,
        expected_refs_old,
        expected_refs_new,
        "expected reference exact-key normalization",
    )

    expected_entities_old = (
        "        expected_entities: dict[str, Any] = {}\n"
        "        for key, value in entity_pairs:\n"
        "            if type(key) is not str:\n"
        "                raise ValueError(\"expected entity identifiers must be strings\")\n"
        "            if key in expected_entities:\n"
        "                raise ValueError(f\"duplicate expected entity identifier: {key}\")\n"
        "            expected_entities[key] = value\n"
    )
    expected_entities_new = (
        "        expected_entities: dict[str, Any] = {}\n"
        "        for key, value in entity_pairs:\n"
        "            entity_id = _id(key, \"expected entity identifier\")\n"
        "            if entity_id in expected_entities:\n"
        "                raise ValueError(\n"
        "                    f\"duplicate expected entity identifier: {entity_id}\"\n"
        "                )\n"
        "            expected_entities[entity_id] = value\n"
    )
    code = replace_once(
        code,
        expected_entities_old,
        expected_entities_new,
        "expected entity exact-key normalization",
    )

    for fragment in (
        "isinstance(edge, DependencyEdge)",
        "isinstance(item, SpatialReferentBinding)",
        "isinstance(expected_projection, ProjectContextProjection)",
        "isinstance(expected_recipe, EphemeralWorkspaceRecipe)",
        "isinstance(expected_observation, MultimodalSpatialObservation)",
        "not isinstance(key, str)",
    ):
        if fragment in code:
            raise SystemExit(f"stale subclass/key-retaining branch remains: {fragment}")
    code_path.write_text(code, encoding="utf-8")

    test_path = Path("tests/test_aura_ephemeral_workspace_contracts.py")
    tests = test_path.read_text(encoding="utf-8")
    tests = replace_once(
        tests,
        "from dataclasses import dataclass, replace\n",
        "from dataclasses import dataclass, fields, replace\n",
        "dataclass fields import",
    )
    marker = "def test_remaining_exact_record_and_key_boundaries_fail_closed()"
    if marker in tests:
        raise SystemExit("exact-record closure regression already exists")
    tests += dedent('''\


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

    trusted_project = project()
    redirected_project = clone_as_subclass(trusted_project, RedirectedProject)
    with pytest.raises(ValueError, match="exact ProjectContextProjection"):
        trusted_project.validate_bindings(expected_projection=redirected_project)
    with pytest.raises(ValueError, match="exact ProjectContextProjection"):
        validate_project_semantics(
            trusted_project.to_dict(), expected_projection=redirected_project
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
    '''))
    test_path.write_text(tests, encoding="utf-8")

    docs_path = Path("docs/AURA_INTENT_NATIVE_SPATIAL_WORKSPACE_PR1.md")
    docs = docs_path.read_text(encoding="utf-8")
    docs = replace_once(
        docs,
        "The focused suite contains **44 tests** covering the original review waves plus the structural repair:",
        "The focused suite contains **45 tests** covering the original review waves plus the structural repair:",
        "documentation test count",
    )
    docs = replace_once(
        docs,
        "- focused tests: **44 passed**;",
        "- focused tests: **45 passed**;",
        "documentation verification receipt",
    )
    docs_path.write_text(docs, encoding="utf-8")


if __name__ == "__main__":
    main()
