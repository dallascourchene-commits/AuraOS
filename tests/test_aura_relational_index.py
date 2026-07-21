from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess

import pytest

from aura_relational_index import (
    INDEX_GENERATED_PATHS,
    RelationalIndex,
    RelationalIndexBuilder,
    RelationalIndexProfile,
    RelationalIndexStore,
    TruthClass,
    _build_groups,
    _build_reverse_indexes,
    _canonical_python_sources,
    _safe_repo_path,
    _topology_facts,
    _working_tree_digest,
    main,
    query_relational_index,
    extract_relational_neighborhood,
)
from aura_relationship_contracts import RelationalNeighborhoodRequest, SourceReference
from aura_relationship_atlas import build_objective_relationship_atlas, clear_objective_atlas_cache
from aura_relational_synthesis import (
    GroupKind,
    ParticipantType,
    RelationalParticipant,
    RelationType,
    TypedRelation,
)
from aura_relational_synthesis import (
    TruthClass as SynthesisTruthClass,
)
from aura_topological_context_anchor import CodeTopoAnchor


def _files() -> dict[str, str]:
    return {
        "service.py": (
            "class Alpha:\n"
            "    def run(self):\n"
            "        return helper()\n\n"
            "class Beta:\n"
            "    def run(self):\n"
            "        return 2\n\n"
            "def helper():\n"
            "    return 1\n"
        ),
        "tests/test_service.py": (
            "from service import Alpha\n\n"
            "def test_alpha_run():\n"
            "    assert Alpha().run() == 1\n"
        ),
        ".aura/RELATIONAL_INDEX.json": "{}\n",
    }


def _connectome(*, reverse: bool = False, ambiguous: bool = False) -> dict:
    nodes = [
        {
            "id": "aura.coding_arena.topology",
            "node_digest": "1" * 32,
            "name": "Coding topology",
            "purpose": "Exact topology orientation",
            "implemented_by": ["service.py"],
            "symbols": ["run" if ambiguous else "Alpha.run", "helper"],
            "tests": ["tests/test_service.py"],
            "docs": [],
            "truth_boundary": "advisory",
            "grounding": "grounded",
        },
        {
            "id": "aura.patch_quality_gate",
            "node_digest": "2" * 32,
            "name": "Quality gate",
            "purpose": "Verification",
            "implemented_by": ["tests/test_service.py"],
            "symbols": ["test_alpha_run"],
            "tests": ["tests/test_service.py"],
            "docs": [],
            "truth_boundary": "exact_source",
            "grounding": "grounded",
        },
    ]
    if reverse:
        nodes.reverse()
    return {
        "ok": True,
        "version": "AURA_CAPABILITY_CONNECTOME_V2",
        "graph_digest": "a" * 32,
        "nodes": nodes,
        "edges": [],
        "vsa_patch_authority": False,
    }


def _identity(builder: RelationalIndexBuilder) -> dict[str, object]:
    return {
        "repo_head": "b" * 40,
        "working_tree_digest": "c" * 40,
        "codemap_digest": "d" * 40,
        "topology_digest": "e" * 40,
        "topology_version": "FIXTURE_TOPOLOGY_V1",
        "topology_health": 1.0,
        "connectome_graph_digest": "a" * 32,
        "connectome_version": "AURA_CAPABILITY_CONNECTOME_V2",
        "atomic_inventory_digest": "f" * 40,
        "atomic_inventory_version": "AURA_ATOMIC_FUNCTION_INVENTORY_V1",
        "relation_ontology_digest": "1" * 40,
        "profile_digest": builder.profile.digest,
        "schema_digest": "2" * 40,
    }


def _build(*, reverse: bool = False, ambiguous: bool = False) -> RelationalIndex:
    files = _files()
    if reverse:
        files = dict(reversed(list(files.items())))
    anchor = CodeTopoAnchor.build_from_files(files)
    builder = RelationalIndexBuilder(".", profile="STANDARD")
    return builder.build_full(
        anchor=anchor,
        connectome=_connectome(reverse=reverse, ambiguous=ambiguous),
        repository_identity=_identity(builder),
    )


def test_full_index_is_deterministic_under_input_reordering() -> None:
    assert _build().to_dict() == _build(reverse=True).to_dict()


def test_exact_and_advisory_relations_remain_separate() -> None:
    index = _build()
    structural = [
        item
        for item in index.relations
        if item.relation_type in {RelationType.CALLS, RelationType.IMPORTS, RelationType.TESTS}
    ]
    implementations = [item for item in index.relations if item.relation_type is RelationType.IMPLEMENTS_CAPABILITY]
    assert structural
    assert implementations
    assert all(item.truth_class in {TruthClass.EXACT_SOURCE, TruthClass.EXACT_TEST} for item in structural)
    assert all(item.truth_class is TruthClass.ADVISORY_CONNECTOME for item in implementations)
    assert all(not any(ref.startswith("connectome-context:") for ref in item.evidence_refs) for item in structural)
    assert all(binding.role != "exact_implementation" for group in index.groups for binding in group.role_bindings)


def test_same_named_methods_keep_qualified_identity() -> None:
    index = _build()
    qualified = {
        item.qualified_symbol for item in index.participants if item.qualified_symbol in {"Alpha.run", "Beta.run"}
    }
    assert qualified == {"Alpha.run", "Beta.run"}
    refs = {item.canonical_ref for item in index.participants if item.qualified_symbol in qualified}
    assert len(refs) == 2
    assert all(ref.startswith("service.py#method:") for ref in refs)


def test_ambiguous_unqualified_capability_mapping_stays_unresolved() -> None:
    index = _build(ambiguous=True)
    unresolved = index.boundary["advisory_only_mappings"]
    assert any(
        item == "capability_symbol:aura.coding_arena.topology:run:ambiguous"
        for item in unresolved
    )
    mapped = [
        item
        for item in index.relations
        if item.relation_type is RelationType.IMPLEMENTS_CAPABILITY
        and item.metadata.get("capability_id") == "aura.coding_arena.topology"
    ]
    mapped_symbols = {
        next(
            participant.qualified_symbol
            for participant in index.participants
            if participant.participant_id == relation.source_participant_id
        )
        for relation in mapped
    }
    assert "Alpha.run" not in mapped_symbols
    assert "Beta.run" not in mapped_symbols
    assert "helper" in mapped_symbols


def test_all_relation_endpoints_and_reverse_ids_are_inspectable() -> None:
    index = _build()
    participant_ids = {item.participant_id for item in index.participants}
    relation_ids = {item.relation_id for item in index.relations}
    group_ids = {item.group_id for item in index.groups}
    valid = participant_ids | relation_ids | group_ids
    assert all(
        item.source_participant_id in participant_ids
        and item.target_participant_id in participant_ids
        for item in index.relations
    )
    for reverse_index in index.reverse_indexes.values():
        for ids in reverse_index.values():
            assert set(ids).issubset(valid)


def test_generated_index_is_excluded_from_source_participants() -> None:
    index = _build()
    paths = {
        str(item.metadata.get("file_path", ""))
        for item in index.participants
    }
    assert INDEX_GENERATED_PATHS.isdisjoint(paths)
    assert all("source" not in item.metadata for item in index.participants)


def test_macro_and_bundle_registries_are_explicitly_materialized() -> None:
    index = _build()
    macro = [item for item in index.groups if item.group_kind.value == "macro_domain"]
    bundles = [
        item for item in index.groups if item.group_kind.value == "cross_domain_bundle"
    ]
    assert len(macro) == 16
    assert len(bundles) == 6
    unresolved_domain = next(item for item in macro if item.purpose == "civic_commons")
    assert unresolved_domain.boundary.included_participant_ids == ()
    assert unresolved_domain.boundary.unresolved_relations == (
        "domain_capability_registry:civic_commons:unresolved",
    )


def test_round_trip_rejects_forged_digest_and_unknown_version() -> None:
    data = _build().to_dict()
    assert RelationalIndex.from_dict(deepcopy(data)).to_dict() == data
    forged = deepcopy(data)
    forged["index_digest"] = "0" * 40
    with pytest.raises(ValueError, match="index_digest"):
        RelationalIndex.from_dict(forged)
    unsupported = deepcopy(data)
    unsupported["schema_version"] = "AURA_RELATIONAL_INDEX_V2"
    with pytest.raises(ValueError, match="unsupported"):
        RelationalIndex.from_dict(unsupported)


def test_schema_validates_index_and_local_refs() -> None:
    pytest.importorskip("jsonschema")
    pytest.importorskip("referencing")
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource

    root = Path("schemas")
    participant = json.loads(
        (root / "aura_relational_participant.schema.json").read_text(encoding="utf-8")
    )
    group = json.loads(
        (root / "aura_relational_group.schema.json").read_text(encoding="utf-8")
    )
    index_schema = json.loads(
        (root / "aura_relational_index.schema.json").read_text(encoding="utf-8")
    )
    registry = Registry().with_resources(
        [
            (participant["$id"], Resource.from_contents(participant)),
            (group["$id"], Resource.from_contents(group)),
            (index_schema["$id"], Resource.from_contents(index_schema)),
        ]
    )
    Draft202012Validator(index_schema, registry=registry).validate(_build().to_dict())


def test_canonical_sources_exclude_named_virtual_environments(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "aura_relational_index._repo_python_sources",
        lambda root: {
            "aura_real.py": "def real(): pass\n",
            ".venv/lib/site.py": "def ignored(): pass\n",
            ".venv_phase2/lib/site.py": "def ignored_too(): pass\n",
            "venv-review/lib/site.py": "def ignored_three(): pass\n",
            "vendor/site-packages/pkg.py": "def ignored_four(): pass\n",
        },
    )
    assert _canonical_python_sources(tmp_path) == {
        "aura_real.py": "def real(): pass\n"
    }


def test_working_tree_digest_ignores_named_virtual_environments(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Aura Test"], check=True)
    (tmp_path / "tracked.py").write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "tracked.py"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "fixture"], check=True)
    baseline = _working_tree_digest(tmp_path)

    environment_file = tmp_path / ".venv_phase2" / "lib" / "site.py"
    environment_file.parent.mkdir(parents=True)
    environment_file.write_text("VALUE = 'local-only'\n", encoding="utf-8")
    assert _working_tree_digest(tmp_path) == baseline

    (tmp_path / "real_change.py").write_text("VALUE = 2\n", encoding="utf-8")
    assert _working_tree_digest(tmp_path) != baseline


def test_default_store_preserves_dot_aura_paths(tmp_path: Path) -> None:
    store = RelationalIndexStore(tmp_path)
    assert store.index_path == tmp_path / ".aura" / "RELATIONAL_INDEX.json"
    assert store.receipt_path == tmp_path / ".aura" / "RELATIONAL_INDEX_RECEIPT.json"
    assert store.markdown_path == tmp_path / ".aura" / "RELATIONAL_INDEX.md"
    assert store.lock_path == tmp_path / ".aura" / "RELATIONAL_INDEX.lock"


def test_store_allows_legitimate_private_reasoning_symbol_identity(tmp_path: Path) -> None:
    index = _build()
    reverse_indexes = index.to_dict()["reverse_indexes"]
    reverse_indexes["by_qualified_symbol"][
        "tests/test_events.py#test_rejects_private_reasoning"
    ] = [index.participants[0].participant_id]
    rebuilt = RelationalIndex.create(
        repository_identity=index.repository_identity,
        profile=index.profile,
        participants=index.participants,
        relations=index.relations,
        groups=index.groups,
        reverse_indexes=reverse_indexes,
        boundary=index.boundary,
        build_facts=index.build_facts,
    )
    store = RelationalIndexStore(
        tmp_path,
        index_path="generated/index.json",
        receipt_path="generated/receipt.json",
        markdown_path="generated/index.md",
        lock_path="generated/index.lock",
    )
    store.write(rebuilt, build_mode="full", full_equivalence_verified=True)
    assert store.load().to_dict() == rebuilt.to_dict()


def test_atomic_store_round_trip_and_secret_rejection(tmp_path: Path) -> None:
    index = _build()
    store = RelationalIndexStore(
        tmp_path,
        index_path="generated/index.json",
        receipt_path="generated/receipt.json",
        markdown_path="generated/index.md",
        lock_path="generated/index.lock",
    )
    receipt = store.write(
        index,
        build_mode="full",
        wall_time_ms=12,
        full_equivalence_verified=True,
    )
    assert store.load().to_dict() == index.to_dict()
    assert store.load_receipt().to_dict() == receipt.to_dict()
    assert receipt.index_digest == index.to_dict()["index_digest"]
    assert store.index_path.read_text(encoding="utf-8").endswith("\n")
    assert "generated navigation only" in store.markdown_path.read_text(encoding="utf-8")

    data = index.to_dict()
    data["participants"][0]["metadata"]["api_key"] = "sk-secret-value"
    with pytest.raises(ValueError):
        RelationalIndex.from_dict(data)

    original = index.participants[0]
    secret_participant = RelationalParticipant.create(
        participant_type=original.participant_type,
        role=original.role,
        truth_class=original.truth_class,
        canonical_owner=original.canonical_owner,
        canonical_ref=original.canonical_ref,
        digest=original.digest,
        evidence_refs=original.evidence_refs,
        freshness=original.freshness,
        qualified_symbol=original.qualified_symbol,
        metadata={**dict(original.metadata), "api_key": "sk-" + ("1" * 24)},
    )
    participants = (secret_participant, *index.participants[1:])
    secret_index = RelationalIndex.create(
        repository_identity=index.repository_identity,
        profile=index.profile,
        participants=participants,
        relations=index.relations,
        groups=index.groups,
        reverse_indexes=index.reverse_indexes,
        boundary=index.boundary,
        build_facts=index.build_facts,
    )
    with pytest.raises(ValueError, match="secret-shaped field"):
        store.write(secret_index, build_mode="full")


def test_validate_current_reports_current_and_stale_identity(tmp_path: Path) -> None:
    index = _build()
    store = RelationalIndexStore(
        tmp_path,
        index_path="generated/index.json",
        receipt_path="generated/receipt.json",
        markdown_path="generated/index.md",
        lock_path="generated/index.lock",
    )
    store.write(index, build_mode="full", full_equivalence_verified=True)

    class StubBuilder:
        def __init__(self, value: RelationalIndex) -> None:
            self.value = value

        def repository_identity_snapshot(self) -> dict[str, object]:
            return dict(self.value.repository_identity)

    current = store.validate_current(builder=StubBuilder(index))
    assert current["ok"] is True
    assert current["status"] == "CURRENT"
    assert current["mismatches"] == {}

    stale_identity = dict(index.repository_identity)
    stale_identity["codemap_digest"] = "9" * 40
    stale = RelationalIndex.create(
        repository_identity=stale_identity,
        profile=index.profile,
        participants=index.participants,
        relations=index.relations,
        groups=index.groups,
        reverse_indexes=index.reverse_indexes,
        boundary=index.boundary,
        build_facts=index.build_facts,
    )
    status = store.validate_current(builder=StubBuilder(stale))
    assert status["ok"] is False
    assert status["status"] == "STALE"
    assert status["mismatches"] == {
        "codemap_digest": {
            "stored": index.repository_identity["codemap_digest"],
            "current": stale.repository_identity["codemap_digest"],
        }
    }


def test_query_returns_bounded_exact_objects() -> None:
    index = _build()
    result = query_relational_index(
        index,
        capability_id="aura.coding_arena.topology",
    )
    assert result["ok"] is True
    assert result["participants"]
    assert result["relations"]
    assert result["safe_to_patch"] is False



def test_reverse_lookup_supports_test_schema_and_canonical_owner() -> None:
    index = _build()
    test_result = query_relational_index(index, test_path="tests/test_service.py")
    assert test_result["ids"]

    owner_result = query_relational_index(index, canonical_owner="CodeTopoAnchor")
    assert owner_result["participants"]
    assert all(item["canonical_owner"] == "CodeTopoAnchor" for item in owner_result["participants"])

    schema = RelationalParticipant.create(
        participant_type=ParticipantType.SCHEMA,
        role="machine_contract",
        truth_class=SynthesisTruthClass.EXACT_SCHEMA,
        canonical_owner="RelationshipContracts",
        canonical_ref="schemas/example.schema.json",
        digest="9" * 64,
        evidence_refs=("schema:schemas/example.schema.json",),
        metadata={"file_path": "schemas/example.schema.json"},
    )
    reverse = _build_reverse_indexes(
        participants=(schema,),
        relations=(),
        groups=(),
        connectome={"nodes": []},
    )
    assert reverse["by_schema"]["schemas/example.schema.json"] == [schema.participant_id]
    assert reverse["by_authority_family"]["RelationshipContracts"] == [schema.participant_id]

def test_incremental_path_is_validated_and_uses_canonical_full_build(monkeypatch: pytest.MonkeyPatch) -> None:
    index = _build()
    builder = RelationalIndexBuilder(".", profile=RelationalIndexProfile.STANDARD)
    monkeypatch.setattr(builder, "build_full", lambda: index)
    assert builder.build_incremental(index, changed_paths=["service.py"]) is index
    with pytest.raises(ValueError, match="escapes workspace"):
        builder.build_incremental(index, changed_paths=["../escape.py"])


def test_index_authority_is_permanently_confined() -> None:
    data = _build().to_dict()
    assert data["generated_only"] is True
    assert data["safe_to_patch"] is False
    assert data["production_mutation"] is False
    assert data["automatic_fix"] is False
    assert data["automatic_commit"] is False
    assert data["automatic_push"] is False
    assert data["automatic_pull_request"] is False
    assert data["automatic_merge"] is False
    assert data["human_review_required"] is True
    assert data["vsa_patch_authority"] is False


def test_affordance_directory_exposes_relational_index() -> None:
    from aura_affordance_directory import load_affordance_directory
    from aura_capability_connectome import build_capability_connectome
    from aura_capability_connectome_v2 import enrich_connectome

    affordances = {
        item.id: item for item in load_affordance_directory(".")
    }
    assert "aura.relational.index" in affordances
    affordance = affordances["aura.relational.index"]
    assert affordance.patch_authority is False
    assert affordance.vsa_patch_authority is False
    graph = enrich_connectome(build_capability_connectome("."))
    node = next(item for item in graph["nodes"] if item["id"] == "aura.relational.index")
    assert node["truth_boundary"] == "advisory"
    assert node["node_digest"]


def test_topology_health_preserves_zero_and_participates_in_freshness(
    tmp_path: Path,
) -> None:
    topology_path = tmp_path / "topology.json"
    topology_path.write_text(
        json.dumps(
            {
                "version": "TOPOLOGY_V1",
                "global_health": 0.0,
                "health": 0.8,
            }
        ),
        encoding="utf-8",
    )
    _, _, health = _topology_facts(topology_path)
    assert health == 0.0

    index = _build()
    store = RelationalIndexStore(
        tmp_path,
        index_path="generated/index.json",
        receipt_path="generated/receipt.json",
        markdown_path="generated/index.md",
        lock_path="generated/index.lock",
    )
    store.write(index, build_mode="full", full_equivalence_verified=True)

    class StubBuilder:
        def repository_identity_snapshot(self) -> dict[str, object]:
            value = dict(index.repository_identity)
            value["topology_health"] = 0.0
            return value

    status = store.validate_current(builder=StubBuilder())
    assert status["status"] == "STALE"
    assert status["mismatches"] == {"topology_health": {"stored": 1.0, "current": 0.0}}


def test_nested_contracts_reject_unknown_keys_and_noncanonical_budgets() -> None:
    data = _build().to_dict()
    for field in ("repository_identity", "profile", "boundary", "build_facts"):
        forged = deepcopy(data)
        forged[field]["unexpected"] = True
        with pytest.raises(ValueError, match="keys do not match"):
            RelationalIndex.from_dict(forged)

    forged_budget = deepcopy(data)
    forged_budget["profile"]["budgets"]["max_group_relations"] = 1499
    with pytest.raises(ValueError, match="budgets do not match"):
        RelationalIndex.from_dict(forged_budget)


def test_schema_rejects_noncanonical_profile_budget() -> None:
    pytest.importorskip("jsonschema")
    pytest.importorskip("referencing")
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource

    root = Path("schemas")
    resources = []
    for name in (
        "aura_relational_participant.schema.json",
        "aura_relational_group.schema.json",
        "aura_relational_index.schema.json",
    ):
        value = json.loads((root / name).read_text(encoding="utf-8"))
        resources.append((value["$id"], Resource.from_contents(value)))
    index_schema = json.loads((root / "aura_relational_index.schema.json").read_text(encoding="utf-8"))
    registry = Registry().with_resources(resources)
    forged = _build().to_dict()
    forged["profile"]["budgets"]["max_group_participants"] = 1499
    errors = list(Draft202012Validator(index_schema, registry=registry).iter_errors(forged))
    assert errors


def test_store_rejects_windows_drives_and_symlinked_parents(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="escapes workspace"):
        _safe_repo_path("C:/outside/index.json")
    with pytest.raises(ValueError, match="escapes workspace"):
        RelationalIndexStore(tmp_path, index_path="C:/outside/index.json")

    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (tmp_path / "generated").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="parent escapes workspace"):
        RelationalIndexStore(
            tmp_path,
            index_path="generated/index.json",
            receipt_path="receipts/receipt.json",
            markdown_path="receipts/index.md",
            lock_path="receipts/index.lock",
        )


def test_store_verification_and_linked_reads_are_locked(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    index = _build()
    store = RelationalIndexStore(
        tmp_path,
        index_path="generated/index.json",
        receipt_path="generated/receipt.json",
        markdown_path="generated/index.md",
        lock_path="generated/index.lock",
    )
    state = {"locked": False, "load_under_lock": False, "receipt_under_lock": False}

    from contextlib import contextmanager

    @contextmanager
    def tracked_lock(path: Path):
        del path
        assert state["locked"] is False
        state["locked"] = True
        try:
            yield
        finally:
            state["locked"] = False

    original_load = store.load
    original_receipt = store.load_receipt

    def tracked_load() -> RelationalIndex:
        state["load_under_lock"] = state["load_under_lock"] or state["locked"]
        return original_load()

    def tracked_receipt():
        state["receipt_under_lock"] = state["receipt_under_lock"] or state["locked"]
        return original_receipt()

    monkeypatch.setattr("aura_relational_index._exclusive_store_lock", tracked_lock)
    monkeypatch.setattr(store, "load", tracked_load)
    monkeypatch.setattr(store, "load_receipt", tracked_receipt)
    store.write(index, build_mode="full", full_equivalence_verified=True)
    assert state["load_under_lock"] is True

    class StubBuilder:
        def repository_identity_snapshot(self) -> dict[str, object]:
            return dict(index.repository_identity)

    store.validate_current(builder=StubBuilder())
    assert state["receipt_under_lock"] is True


def test_group_selection_respects_relation_and_participant_budgets() -> None:
    capability = "capability-participant"
    source_one = "source-one"
    source_two = "source-two"
    relations = [
        TypedRelation.create(
            relation_type=RelationType.IMPLEMENTS_CAPABILITY,
            source_participant_id=source_one,
            target_participant_id=capability,
            truth_class=SynthesisTruthClass.ADVISORY_CONNECTOME,
            evidence_refs=("connectome:a",),
            metadata={"capability_id": "aura.coding_arena.topology"},
        ),
        TypedRelation.create(
            relation_type=RelationType.IMPLEMENTS_CAPABILITY,
            source_participant_id=source_two,
            target_participant_id=capability,
            truth_class=SynthesisTruthClass.ADVISORY_CONNECTOME,
            evidence_refs=("connectome:b",),
            metadata={"capability_id": "aura.coding_arena.topology"},
        ),
    ]

    class TinyProfile:
        def __init__(self) -> None:
            self.value = "TINY"
            self.budgets = {
                "max_group_relations": 2,
                "max_group_participants": 2,
            }

    groups = _build_groups(
        relations=relations,
        connectome={},
        capability_to_participant={"aura.coding_arena.topology": capability},
        unresolved_mappings=(),
        profile=TinyProfile(),
    )
    group = next(
        item
        for item in groups
        if item.group_kind is GroupKind.MACRO_DOMAIN and item.purpose == "codemap_topology_grounding"
    )
    assert len(group.relations) == 1
    assert len(group.boundary.included_participant_ids) == 2
    assert group.boundary.omitted_relation_count == 1
    assert group.boundary.omitted_reasons == {"profile_participant_budget": 1}


def test_participant_reverse_lookup_returns_self_and_incident_relations() -> None:
    index = _build()
    helper = next(item for item in index.participants if item.qualified_symbol == "helper")
    incident = {
        relation.relation_id
        for relation in index.relations
        if helper.participant_id in {relation.source_participant_id, relation.target_participant_id}
    }
    result = query_relational_index(index, participant_id=helper.participant_id)
    assert [item["participant_id"] for item in result["participants"]] == [helper.participant_id]
    assert {item["relation_id"] for item in result["relations"]} == incident


def test_validate_uses_stored_profile_and_identity_only(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    original = _build()
    minimal = RelationalIndexProfile.MINIMAL
    identity = dict(original.repository_identity)
    identity["profile_digest"] = minimal.digest
    index = RelationalIndex.create(
        repository_identity=identity,
        profile={
            "name": minimal.value,
            "budgets": dict(minimal.budgets),
            "profile_digest": minimal.digest,
        },
        participants=original.participants,
        relations=original.relations,
        groups=original.groups,
        reverse_indexes=original.reverse_indexes,
        boundary=original.boundary,
        build_facts=original.build_facts,
    )
    store = RelationalIndexStore(
        tmp_path,
        index_path="generated/index.json",
        receipt_path="generated/receipt.json",
        markdown_path="generated/index.md",
        lock_path="generated/index.lock",
    )
    store.write(index, build_mode="full", full_equivalence_verified=True)
    seen: list[str] = []

    def snapshot(self: RelationalIndexBuilder) -> dict[str, object]:
        seen.append(self.profile.value)
        return dict(index.repository_identity)

    def forbidden_full(self: RelationalIndexBuilder):
        raise AssertionError("validate_current must not build a second full index")

    monkeypatch.setattr(RelationalIndexBuilder, "repository_identity_snapshot", snapshot)
    monkeypatch.setattr(RelationalIndexBuilder, "build_full", forbidden_full)
    status = store.validate_current()
    assert status["status"] == "CURRENT"
    assert seen == ["MINIMAL"]


def test_cli_build_requests_bounded_summary(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fake_build(repo_root, *, profile, persist, include_index):
        assert repo_root == "."
        assert profile is RelationalIndexProfile.STANDARD
        assert persist is True
        assert include_index is False
        return {
            "ok": True,
            "index_id": "relindex-test",
            "participant_count": 1,
            "relation_count": 0,
            "group_count": 0,
        }

    monkeypatch.setattr("aura_relational_index.build_relational_index", fake_build)
    assert main(["build"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["index_id"] == "relindex-test"
    assert "index" not in payload



def test_extract_relational_neighborhood_is_deterministic_and_bounded() -> None:
    index = _build()
    seed = next(item.participant_id for item in index.participants if item.qualified_symbol == "Alpha.run")
    request = RelationalNeighborhoodRequest(
        objective_digest="objective-neighborhood",
        seed_participant_ids=(seed,),
        seed_source_refs=(),
        max_hops=2,
        max_nodes=4,
        max_edges=5,
        max_candidate_pairs=6,
        max_output_bytes=100_000,
        max_elapsed_ms=5_000,
    )
    first = extract_relational_neighborhood(request, index)
    second = extract_relational_neighborhood(request, index.to_dict())
    assert first == second
    assert first["seed_participant_ids"] == [seed]
    assert len(first["participants"]) <= 4
    assert len(first["relations"]) <= 5
    assert first["truncation_receipt"]["candidate_pair_count"] <= 6
    assert first["safe_to_patch"] is False


def test_extract_relational_neighborhood_resolves_exact_source_ref() -> None:
    index = _build()
    request = RelationalNeighborhoodRequest(
        objective_digest="objective-source-ref",
        seed_participant_ids=(),
        seed_source_refs=(
            SourceReference(
                file_path="service.py",
                symbol="Alpha.run",
                line_start=1,
                line_end=3,
                source_hash="source-hash",
            ),
        ),
        max_hops=1,
        max_nodes=8,
        max_edges=16,
    )
    packet = extract_relational_neighborhood(request, index)
    assert packet["seed_participant_ids"]
    assert any(
        item["qualified_symbol"] == "Alpha.run" for item in packet["participants"]
    )
    assert any(
        reason.startswith("exact_source_ref:service.py#Alpha.run")
        for reasons in packet["inclusion_reasons"].values()
        for reason in reasons
    )


def test_extract_relational_neighborhood_retains_seed_under_dense_budget() -> None:
    index = _build()
    seed = index.participants[0].participant_id
    request = RelationalNeighborhoodRequest(
        objective_digest="objective-dense",
        seed_participant_ids=(seed,),
        seed_source_refs=(),
        max_hops=3,
        max_nodes=1,
        max_edges=1,
        max_candidate_pairs=0,
        max_output_bytes=50_000,
        max_elapsed_ms=5_000,
    )
    packet = extract_relational_neighborhood(request, index)
    assert [item["participant_id"] for item in packet["participants"]] == [seed]
    assert packet["truncation_receipt"]["truncated"] is True
    assert "max_nodes" in packet["truncation_receipt"]["exhausted_budgets"]


def test_extract_relational_neighborhood_rejects_tampered_index_digest() -> None:
    data = _build().to_dict()
    data["relations"][0]["metadata"]["tampered"] = True
    seed = data["participants"][0]["participant_id"]
    request = RelationalNeighborhoodRequest(
        objective_digest="objective-tampered",
        seed_participant_ids=(seed,),
        seed_source_refs=(),
    )
    with pytest.raises(ValueError, match="index_digest"):
        extract_relational_neighborhood(request, data)



def test_objective_atlas_compiles_from_bounded_neighborhood_and_cache_is_semantic_noop(monkeypatch) -> None:
    import aura_relationship_atlas as atlas_module

    index = _build()
    monkeypatch.setattr(
        atlas_module,
        "_current_relational_index_identity",
        lambda repo_root, relational_index: dict(relational_index["repository_identity"]),
    )
    seed = next(item.participant_id for item in index.participants if item.qualified_symbol == "Alpha.run")
    request = RelationalNeighborhoodRequest(
        objective_digest="objective-atlas",
        seed_participant_ids=(seed,),
        seed_source_refs=(),
        max_hops=2,
        max_nodes=6,
        max_edges=12,
        max_candidate_pairs=15,
    )
    neighborhood = extract_relational_neighborhood(request, index)
    clear_objective_atlas_cache()
    first = build_objective_relationship_atlas(
        repo_root=".",
        relational_index=index.to_dict(),
        neighborhood=neighborhood,
        profile="OBJECTIVE_DEEP",
    )
    second = build_objective_relationship_atlas(
        repo_root=".",
        relational_index=index.to_dict(),
        neighborhood=neighborhood,
        profile="OBJECTIVE_DEEP",
    )
    clear_objective_atlas_cache()
    third = build_objective_relationship_atlas(
        repo_root=".",
        relational_index=index.to_dict(),
        neighborhood=neighborhood,
        profile="OBJECTIVE_DEEP",
    )
    assert first.to_dict() == second.to_dict() == third.to_dict()
    assert first.boundary["objective_scoped"] is True
    assert first.boundary["operational_profile"] == "OBJECTIVE_DEEP"
    assert first.boundary["neighborhood_digest"] == neighborhood["neighborhood_digest"]
    assert atlas_module.validate_relationship_atlas(first)["ok"] is True


def test_objective_atlas_cache_evicts_oldest_by_byte_budget(monkeypatch) -> None:
    import aura_relationship_atlas as atlas_module

    index = _build()
    monkeypatch.setattr(
        atlas_module,
        "_current_relational_index_identity",
        lambda repo_root, relational_index: dict(relational_index["repository_identity"]),
    )
    seed = next(item.participant_id for item in index.participants if item.qualified_symbol == "Alpha.run")
    first_request = RelationalNeighborhoodRequest(
        objective_digest="cache-objective-1",
        seed_participant_ids=(seed,),
        seed_source_refs=(),
        max_hops=1,
        max_nodes=4,
        max_edges=8,
    )
    second_request = RelationalNeighborhoodRequest(
        objective_digest="cache-objective-2",
        seed_participant_ids=(seed,),
        seed_source_refs=(),
        max_hops=1,
        max_nodes=4,
        max_edges=8,
    )
    first_neighborhood = extract_relational_neighborhood(first_request, index)
    second_neighborhood = extract_relational_neighborhood(second_request, index)
    probe = build_objective_relationship_atlas(
        repo_root=".",
        relational_index=index.to_dict(),
        neighborhood=first_neighborhood,
        profile="OBJECTIVE_STANDARD",
        use_cache=False,
    )
    payload_size = len(json.dumps(probe.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8"))
    monkeypatch.setattr(atlas_module, "OBJECTIVE_ATLAS_CACHE_MAX_BYTES", payload_size + 128)
    clear_objective_atlas_cache()
    build_objective_relationship_atlas(
        repo_root=".", relational_index=index.to_dict(), neighborhood=first_neighborhood, profile="OBJECTIVE_STANDARD"
    )
    build_objective_relationship_atlas(
        repo_root=".", relational_index=index.to_dict(), neighborhood=second_neighborhood, profile="OBJECTIVE_STANDARD"
    )
    assert len(atlas_module._OBJECTIVE_ATLAS_CACHE) == 1
    only_key = next(iter(atlas_module._OBJECTIVE_ATLAS_CACHE))
    assert only_key[2] == second_neighborhood["neighborhood_digest"]
    assert atlas_module._OBJECTIVE_ATLAS_CACHE_BYTES <= atlas_module.OBJECTIVE_ATLAS_CACHE_MAX_BYTES
