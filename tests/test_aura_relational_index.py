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
    _canonical_python_sources,
    _working_tree_digest,
    query_relational_index,
)
from aura_relational_synthesis import RelationalParticipant, RelationType
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
    implementations = [
        item
        for item in index.relations
        if item.relation_type is RelationType.IMPLEMENTS_CAPABILITY
    ]
    assert structural
    assert implementations
    assert all(
        item.truth_class in {TruthClass.EXACT_SOURCE, TruthClass.EXACT_TEST}
        for item in structural
    )
    assert all(
        item.truth_class is TruthClass.ADVISORY_CONNECTOME
        for item in implementations
    )


def test_same_named_methods_keep_qualified_identity() -> None:
    index = _build()
    qualified = {
        item.qualified_symbol
        for item in index.participants
        if item.qualified_symbol in {"Alpha.run", "Beta.run"}
    }
    assert qualified == {"Alpha.run", "Beta.run"}
    refs = {
        item.canonical_ref
        for item in index.participants
        if item.qualified_symbol in qualified
    }
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

        def build_full(self) -> RelationalIndex:
            return self.value

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
