"""Tests for the Aura Architecture Relationship Atlas (AARA)."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from aura_relationship_atlas import (
    BUILTIN_PROHIBITIONS,
    BUILTIN_MOTIFS,
    StructuralStatus,
    SemanticRelationship,
    WiringDisposition,
    Readiness,
    Lifecycle,
    TruthClass,
    ProofStatus,
    OperationalProfile,
    PROFILE_CONFIG,
    AtlasParticipantRef,
    AtlasRelationshipAssessment,
    MissingRelationalConfiguration,
    RelationshipProhibition,
    AtlasSnapshot,
    AtlasDeltaReceipt,
    build_relationship_atlas,
    validate_relationship_atlas,
    relationship_assessment,
    relationships_for_participant,
    relationships_for_objective,
    find_overlapping_unwired,
    find_auxiliary_adjacent,
    find_missing_configurations,
    find_candidate_wirings,
    find_prohibited_wirings,
    explain_relationship,
    diff_relationship_atlases,
    compile_atlas_projection,
    _snapshot_from_dict,
)


@pytest.fixture
def temp_repo(tmp_path: Path) -> Path:
    # Setup standard relational index mock layout
    idx_dir = tmp_path / ".aura"
    idx_dir.mkdir(parents=True, exist_ok=True)
    idx_file = idx_dir / "RELATIONAL_INDEX.json"

    index_data = {
        "schema_version": "AURA_RELATIONAL_INDEX_V1",
        "index_id": "relindex_123456789012345678901234",
        "repository_identity": {
            "repo_head": "f8a002bc45",
            "working_tree_digest": "wt_digest_hash_val",
            "codemap_digest": "code_digest_hash_val",
            "topology_digest": "topo_digest_hash_val",
            "topology_version": "AURA_TOPOLOGY_V1",
            "topology_health": 1.0,
            "connectome_graph_digest": "conn_digest_hash_val",
            "connectome_version": "AURA_CAPABILITY_CONNECTOME_V2",
            "atomic_inventory_digest": "atomic_digest_hash_val",
            "atomic_inventory_version": "AURA_ATOMIC_FUNCTION_INVENTORY_V1",
            "relation_ontology_digest": "onto_digest_hash_val",
            "profile_digest": "prof_digest_hash_val",
            "schema_digest": "schema_digest_hash_val"
        },
        "participants": [
            {
                "participant_id": "relp_000000000000000000000001",
                "participant_type": "atomic_symbol",
                "role": "intent_parser",
                "truth_class": "EXACT_SOURCE",
                "canonical_owner": "aura_intent_ingestion.py",
                "canonical_ref": "aura_intent_ingestion.py::parse_intent",
                "digest": "p1_digest",
                "evidence_refs": ["file_hash_1"],
                "freshness": "CURRENT",
                "qualified_symbol": "parse_intent",
                "metadata": {}
            },
            {
                "participant_id": "relp_000000000000000000000002",
                "participant_type": "atomic_symbol",
                "role": "authority_guard",
                "truth_class": "EXACT_SOURCE",
                "canonical_owner": "aura_relational_authority.py",
                "canonical_ref": "aura_relational_authority.py::check_authority",
                "digest": "p2_digest",
                "evidence_refs": ["file_hash_2"],
                "freshness": "CURRENT",
                "qualified_symbol": "check_authority",
                "metadata": {}
            },
            {
                "participant_id": "relp_000000000000000000000003",
                "participant_type": "verifier",
                "role": "verifier_gate",
                "truth_class": "EXACT_SOURCE",
                "canonical_owner": "aura_ephemeral_verifier.py",
                "canonical_ref": "aura_ephemeral_verifier.py::verify_ephemeral_organ",
                "digest": "p3_digest",
                "evidence_refs": ["file_hash_3"],
                "freshness": "CURRENT",
                "qualified_symbol": "verify_ephemeral_organ",
                "metadata": {}
            }
        ],
        "relations": [
            {
                "schema_version": "AURA_TYPED_RELATION_V1",
                "relation_id": "rel_000000000000000000000001",
                "relation_type": "CALLS",
                "source_participant_id": "relp_000000000000000000000001",
                "target_participant_id": "relp_000000000000000000000002",
                "truth_class": "EXACT_SOURCE",
                "evidence_refs": ["callsite_evidence_1"],
                "metadata": {}
            }
        ],
        "groups": [],
        "reverse_indexes": {},
        "boundary": {
            "unsupported_languages": [],
            "unresolved_dynamic_calls": [],
            "advisory_only_mappings": [],
            "excluded_generated_paths": [],
            "warnings": [],
            "all_relation_endpoints_present": True
        },
        "build_facts": {
            "anchor_version": "AURA_TOPOLOGICAL_CONTEXT_ANCHOR_V1",
            "source_file_count": 5,
            "topology_node_count": 10,
            "topology_edge_count": 12,
            "atomic_callable_count": 15,
            "participant_count": 3,
            "exact_relation_count": 1,
            "advisory_relation_count": 0,
            "group_count": 0,
            "unresolved_mapping_count": 0
        },
        "generated_only": True,
        "safe_to_patch": False,
        "production_mutation": False,
        "automatic_fix": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_pull_request": False,
        "automatic_merge": False,
        "human_review_required": True,
        "patch_authority": "exact_source_spans_and_hashes_only",
        "vsa_patch_authority": False,
        "index_digest": "0123456789012345678901234567890123456789"
    }

    with idx_file.open("w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2)

    return tmp_path


def test_atlas_builds_from_index(temp_repo: Path) -> None:
    snapshot = build_relationship_atlas(repo_root=temp_repo)
    assert snapshot.snapshot_version == "AURA_ARCHITECTURE_RELATIONSHIP_ATLAS_V1"
    assert snapshot.snapshot_digest != ""
    assert len(snapshot.assessments) > 0


def test_atlas_classification_explicitly_wired(temp_repo: Path) -> None:
    snapshot = build_relationship_atlas(repo_root=temp_repo)
    
    # Check that our Call relation is compiled as EXACTLY_WIRED
    wired = [a for a in snapshot.assessments if a.structural_status == StructuralStatus.EXACTLY_WIRED]
    assert len(wired) == 1
    assert wired[0].relation_types == ["CALLS"]


def test_atlas_classification_overlapping_unwired(temp_repo: Path) -> None:
    # Set name overlapping in index data for overlapping test
    idx_file = temp_repo / ".aura" / "RELATIONAL_INDEX.json"
    with idx_file.open("r") as f:
        data = json.load(f)
    
    # Change name of participant 3 to share name elements with participant 1
    data["participants"][2]["canonical_ref"] = "aura_intent_ingestion.py::verify_intent_structure"
    with idx_file.open("w") as f:
        json.dump(data, f)

    snapshot = build_relationship_atlas(repo_root=temp_repo)
    overlaps = find_overlapping_unwired(snapshot)
    assert len(overlaps) >= 1
    assert overlaps[0].semantic_relationship == SemanticRelationship.OVERLAPPING


def test_prohibition_blocks_affinity_mutation(temp_repo: Path) -> None:
    # Set a prohibited relation in the relational index
    idx_file = temp_repo / ".aura" / "RELATIONAL_INDEX.json"
    with idx_file.open("r") as f:
        data = json.load(f)

    # Add a relation that violates the affinity_mutation_block rule
    data["relations"].append({
        "schema_version": "AURA_TYPED_RELATION_V1",
        "relation_id": "rel_prohibited_affinity_mutation",
        "relation_type": "REQUIRES_AUTHORITY",
        "source_participant_id": "relp_000000000000000000000001",
        "target_participant_id": "relp_000000000000000000000002",
        "truth_class": "ADVISORY_AFFINITY",
        "evidence_refs": ["affinity_match_vector"],
        "metadata": {}
    })

    with idx_file.open("w") as f:
        json.dump(data, f)

    snapshot = build_relationship_atlas(repo_root=temp_repo)
    prohibited = [a for a in snapshot.assessments if a.wiring_disposition == WiringDisposition.PROHIBITED]
    assert len(prohibited) >= 1
    assert prohibited[0].readiness == Readiness.TOO_RISKY


def test_validate_relationship_atlas(temp_repo: Path) -> None:
    snapshot = build_relationship_atlas(repo_root=temp_repo)
    report = validate_relationship_atlas(snapshot)
    assert report["ok"] is True
    assert report["assessments_count"] == len(snapshot.assessments)


def test_relationship_assessment_lookup(temp_repo: Path) -> None:
    snapshot = build_relationship_atlas(repo_root=temp_repo)
    p_ids = ["relp_000000000000000000000001", "relp_000000000000000000000002"]
    assess = relationship_assessment(p_ids, snapshot)
    assert assess is not None
    assert assess.structural_status == StructuralStatus.EXACTLY_WIRED


def test_relationships_for_participant(temp_repo: Path) -> None:
    snapshot = build_relationship_atlas(repo_root=temp_repo)
    related = relationships_for_participant("relp_000000000000000000000001", snapshot)
    assert len(related) > 0


def test_relationships_for_objective(temp_repo: Path) -> None:
    snapshot = build_relationship_atlas(repo_root=temp_repo)
    related = relationships_for_objective(["intent"], snapshot)
    assert len(related) > 0


def test_missing_configurations_detected(temp_repo: Path) -> None:
    # Trigger missing configuration motif detection
    snapshot = build_relationship_atlas(repo_root=temp_repo)
    missing = find_missing_configurations(snapshot)
    assert len(missing) > 0
    assert any(m.motif_type == "input_to_authority" for m in missing)


def test_diff_receipt_correct_on_change(temp_repo: Path) -> None:
    snapshot1 = build_relationship_atlas(repo_root=temp_repo)

    # Modify the index data to add a new relation
    idx_file = temp_repo / ".aura" / "RELATIONAL_INDEX.json"
    with idx_file.open("r") as f:
        data = json.load(f)
    
    data["relations"].append({
        "schema_version": "AURA_TYPED_RELATION_V1",
        "relation_id": "rel_000000000000000000000002",
        "relation_type": "TESTS",
        "source_participant_id": "relp_000000000000000000000003",
        "target_participant_id": "relp_000000000000000000000001",
        "truth_class": "EXACT_TEST",
        "evidence_refs": ["test_evidence_val"],
        "metadata": {}
    })

    with idx_file.open("w") as f:
        json.dump(data, f)

    snapshot2 = build_relationship_atlas(repo_root=temp_repo)
    delta = diff_relationship_atlases(snapshot1, snapshot2)
    assert len(delta.added_exact_relations) == 1


def test_stale_index_fails_closed(temp_repo: Path) -> None:
    bad_path = temp_repo / "nonexistent_index.json"
    with pytest.raises(FileNotFoundError):
        build_relationship_atlas(relational_index_path=bad_path)


def test_atlas_projection_compiles(temp_repo: Path) -> None:
    snapshot = build_relationship_atlas(repo_root=temp_repo)
    projection = compile_atlas_projection(
        focal_participant_ids=["relp_000000000000000000000001"],
        snapshot=snapshot
    )
    assert "nodes" in projection
    assert "edges" in projection
    assert len(projection["nodes"]) > 0


def test_explain_relationship(temp_repo: Path) -> None:
    snapshot = build_relationship_atlas(repo_root=temp_repo)
    a_id = snapshot.assessments[0].assessment_id
    explanation = explain_relationship(a_id, snapshot)
    assert explanation["assessment_id"] == a_id
    assert "structural_status" in explanation


def test_find_candidate_wirings(temp_repo: Path) -> None:
    # Overlapping unwired relationships should be classified as WiringDisposition.CANDIDATE
    idx_file = temp_repo / ".aura" / "RELATIONAL_INDEX.json"
    with idx_file.open("r") as f:
        data = json.load(f)
    data["participants"][2]["canonical_ref"] = "aura_intent_ingestion.py::verify_intent_structure"
    with idx_file.open("w") as f:
        json.dump(data, f)

    snapshot = build_relationship_atlas(repo_root=temp_repo)
    candidates = find_candidate_wirings(snapshot)
    assert len(candidates) >= 1
    assert candidates[0].wiring_disposition == WiringDisposition.CANDIDATE


def test_find_prohibited_wirings(temp_repo: Path) -> None:
    snapshot = build_relationship_atlas(repo_root=temp_repo)
    prohibited = find_prohibited_wirings(snapshot)
    assert len(prohibited) == len(BUILTIN_PROHIBITIONS)


def test_cli_build_command(temp_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import aura_relationship_atlas
    # Test building via CLI entrypoint
    monkeypatch.chdir(temp_repo)
    exit_code = aura_relationship_atlas.main(["build"])
    assert exit_code == 0
    assert (temp_repo / ".aura" / "RELATIONAL_INDEX.json").exists()
    assert (temp_repo / ".aura" / "RELATIONSHIP_ATLAS.json").exists()


def test_cli_query_command(temp_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import aura_relationship_atlas
    monkeypatch.chdir(temp_repo)
    # Build first
    aura_relationship_atlas.main(["build"])
    # Query
    exit_code = aura_relationship_atlas.main(["query", "--participant", "relp_000000000000000000000001"])
    assert exit_code == 0


def test_cli_explain_command(temp_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import aura_relationship_atlas
    monkeypatch.chdir(temp_repo)
    aura_relationship_atlas.main(["build"])
    with (temp_repo / ".aura" / "RELATIONSHIP_ATLAS.json").open("r") as f:
        data = json.load(f)
    a_id = data["assessments"][0]["assessment_id"]
    
    exit_code = aura_relationship_atlas.main(["explain", "--assessment", a_id])
    assert exit_code == 0


def test_cli_missing_and_prohibited_commands(temp_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import aura_relationship_atlas
    monkeypatch.chdir(temp_repo)
    aura_relationship_atlas.main(["build"])

    assert aura_relationship_atlas.main(["missing"]) == 0
    assert aura_relationship_atlas.main(["prohibited"]) == 0


# ---------------------------------------------------------------------------
# Extended tests: operational profiles, expanded prohibition patterns,
# auxiliary detection, CLI new commands, delta generation, schema round-trip
# ---------------------------------------------------------------------------


def test_minimal_profile_excludes_overlap_and_auxiliary(temp_repo: Path) -> None:
    """MINIMAL profile should not produce overlap or auxiliary assessments."""
    # Make two participants share name words so overlap would trigger
    idx_file = temp_repo / ".aura" / "RELATIONAL_INDEX.json"
    with idx_file.open("r") as f:
        data = json.load(f)
    data["participants"][2]["canonical_ref"] = "aura_intent_ingestion.py::verify_intent_structure"
    with idx_file.open("w") as f:
        json.dump(data, f)

    snapshot = build_relationship_atlas(repo_root=temp_repo, profile="MINIMAL")
    overlaps = find_overlapping_unwired(snapshot)
    auxiliaries = find_auxiliary_adjacent(snapshot)
    assert len(overlaps) == 0, "MINIMAL profile should not detect overlaps"
    assert len(auxiliaries) == 0, "MINIMAL profile should not detect auxiliary relationships"


def test_standard_profile_includes_overlap_and_auxiliary(temp_repo: Path) -> None:
    """STANDARD profile should detect overlaps and auxiliary relationships."""
    idx_file = temp_repo / ".aura" / "RELATIONAL_INDEX.json"
    with idx_file.open("r") as f:
        data = json.load(f)
    data["participants"][2]["canonical_ref"] = "aura_intent_ingestion.py::verify_intent_structure"
    with idx_file.open("w") as f:
        json.dump(data, f)

    snapshot = build_relationship_atlas(repo_root=temp_repo, profile="STANDARD")
    # Should have overlap detection enabled
    # Participant 1 and 3 share canonical_ref words -> overlap
    overlaps = find_overlapping_unwired(snapshot)
    assert len(overlaps) >= 1, "STANDARD profile should detect overlaps"


def test_profile_config_completeness() -> None:
    """PROFILE_CONFIG should have all three profiles with consistent keys."""
    expected_keys = {
        "exact_relations", "declared_relations", "applicable_prohibitions",
        "one_hop_missing_roles", "overlap_detection", "auxiliary_detection",
        "candidate_discovery", "motif_search", "redundancy_competition",
        "cross_arena_candidates",
    }
    for profile in OperationalProfile:
        cfg = PROFILE_CONFIG[profile]
        assert set(cfg.keys()) == expected_keys, f"Profile {profile} missing keys: {expected_keys - set(cfg.keys())}"

    # MINIMAL should disable overlap/auxiliary/candidate/motif
    assert not PROFILE_CONFIG[OperationalProfile.MINIMAL]["overlap_detection"]
    assert not PROFILE_CONFIG[OperationalProfile.MINIMAL]["auxiliary_detection"]
    # DEEP should enable everything
    assert PROFILE_CONFIG[OperationalProfile.DEEP]["cross_arena_candidates"]


def test_prohibition_self_verification_block(temp_repo: Path) -> None:
    """Self-verification: a producer must not verify its own results."""
    idx_file = temp_repo / ".aura" / "RELATIONAL_INDEX.json"
    with idx_file.open("r") as f:
        data = json.load(f)

    # Both participants share the same canonical owner → self-verification
    data["participants"][0]["canonical_owner"] = "aura_verifier.py"
    data["participants"][2]["canonical_owner"] = "aura_verifier.py"
    data["relations"].append({
        "schema_version": "AURA_TYPED_RELATION_V1",
        "relation_id": "rel_self_verify_test",
        "relation_type": "VERIFIED_BY",
        "source_participant_id": "relp_000000000000000000000001",
        "target_participant_id": "relp_000000000000000000000003",
        "truth_class": "EXACT_SOURCE",
        "evidence_refs": ["self_verify_evidence"],
        "metadata": {}
    })
    with idx_file.open("w") as f:
        json.dump(data, f)

    snapshot = build_relationship_atlas(repo_root=temp_repo)
    prohibited = [a for a in snapshot.assessments if a.wiring_disposition == WiringDisposition.PROHIBITED]
    # At least the self-verification relation should be prohibited
    self_verif = [a for a in prohibited if "VERIFIED_BY" in a.relation_types]
    assert len(self_verif) >= 1, "Self-verification should be prohibited"
    assert any("producer must not verify" in a.prohibited_effects[0].lower() for a in self_verif if a.prohibited_effects)


def test_prohibition_ephemeral_lease_leak_block(temp_repo: Path) -> None:
    """Ephemeral leases must not persist beyond their TTL."""
    idx_file = temp_repo / ".aura" / "RELATIONAL_INDEX.json"
    with idx_file.open("r") as f:
        data = json.load(f)

    # Add participants with lease/state types
    data["participants"].append({
        "participant_id": "relp_000000000000000000000004",
        "participant_type": "lease",
        "role": "ephemeral_lease",
        "truth_class": "EXACT_RUNTIME",
        "canonical_owner": "aura_ephemeral_organ.py",
        "canonical_ref": "aura_ephemeral_organ.py::lease_organ",
        "digest": "p4_digest",
        "evidence_refs": ["lease_evidence"],
        "freshness": "CURRENT",
        "qualified_symbol": "lease_organ",
        "metadata": {}
    })
    data["participants"].append({
        "participant_id": "relp_000000000000000000000005",
        "participant_type": "state",
        "role": "organ_state",
        "truth_class": "EXACT_RUNTIME",
        "canonical_owner": "aura_ephemeral_organ.py",
        "canonical_ref": "aura_ephemeral_organ.py::organ_state",
        "digest": "p5_digest",
        "evidence_refs": ["state_evidence"],
        "freshness": "CURRENT",
        "qualified_symbol": "organ_state",
        "metadata": {}
    })
    data["relations"].append({
        "schema_version": "AURA_TYPED_RELATION_V1",
        "relation_id": "rel_lease_leak_test",
        "relation_type": "DISSOLVES_AFTER",
        "source_participant_id": "relp_000000000000000000000004",
        "target_participant_id": "relp_000000000000000000000005",
        "truth_class": "EXACT_RUNTIME",
        "evidence_refs": ["lease_leak_evidence"],
        "metadata": {}
    })
    with idx_file.open("w") as f:
        json.dump(data, f)

    snapshot = build_relationship_atlas(repo_root=temp_repo)
    # The DISSOLVES_AFTER relation should be classified as PERSISTENT lifecycle (default)
    # which triggers the ephemeral_lease_leak_block
    prohibited = [a for a in snapshot.assessments if a.wiring_disposition == WiringDisposition.PROHIBITED]
    lease_prohibitions = [a for a in prohibited if "DISSOLVES_AFTER" in a.relation_types]
    assert len(lease_prohibitions) >= 1, "Persistent ephemeral lease should be prohibited"


def test_auxiliary_detection_with_verifier(temp_repo: Path) -> None:
    """Auxiliary detection: verifier adjacent to atomic_symbol without direct edge."""
    snapshot = build_relationship_atlas(repo_root=temp_repo, profile="STANDARD")
    auxiliaries = find_auxiliary_adjacent(snapshot)
    # Participant 1 (atomic_symbol) and 3 (verifier) have no direct relation → auxiliary
    assert len(auxiliaries) >= 1, "Should detect auxiliary relationship between verifier and atomic_symbol"
    assert auxiliaries[0].semantic_relationship == SemanticRelationship.AUXILIARY


def test_cli_status_command(temp_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI status command should show snapshot summary and build receipt."""
    import aura_relationship_atlas
    monkeypatch.chdir(temp_repo)
    aura_relationship_atlas.main(["build"])
    exit_code = aura_relationship_atlas.main(["status"])
    assert exit_code == 0


def test_cli_validate_command(temp_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI validate command should run invariant validation."""
    import aura_relationship_atlas
    monkeypatch.chdir(temp_repo)
    aura_relationship_atlas.main(["build"])
    exit_code = aura_relationship_atlas.main(["validate"])
    assert exit_code == 0


def test_cli_overlaps_command(temp_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI overlaps command should list overlapping unwired relationships."""
    import aura_relationship_atlas
    monkeypatch.chdir(temp_repo)
    idx_file = temp_repo / ".aura" / "RELATIONAL_INDEX.json"
    with idx_file.open("r") as f:
        data = json.load(f)
    data["participants"][2]["canonical_ref"] = "aura_intent_ingestion.py::verify_intent_structure"
    with idx_file.open("w") as f:
        json.dump(data, f)
    aura_relationship_atlas.main(["build"])
    exit_code = aura_relationship_atlas.main(["overlaps"])
    assert exit_code == 0


def test_cli_candidates_command(temp_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI candidates command should list candidate wirings."""
    import aura_relationship_atlas
    monkeypatch.chdir(temp_repo)
    idx_file = temp_repo / ".aura" / "RELATIONAL_INDEX.json"
    with idx_file.open("r") as f:
        data = json.load(f)
    data["participants"][2]["canonical_ref"] = "aura_intent_ingestion.py::verify_intent_structure"
    with idx_file.open("w") as f:
        json.dump(data, f)
    aura_relationship_atlas.main(["build"])
    exit_code = aura_relationship_atlas.main(["candidates"])
    assert exit_code == 0


def test_cli_build_with_profile(temp_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI build --profile MINIMAL should produce fewer assessments than STANDARD."""
    import aura_relationship_atlas
    monkeypatch.chdir(temp_repo)
    idx_file = temp_repo / ".aura" / "RELATIONAL_INDEX.json"
    with idx_file.open("r") as f:
        data = json.load(f)
    data["participants"][2]["canonical_ref"] = "aura_intent_ingestion.py::verify_intent_structure"
    with idx_file.open("w") as f:
        json.dump(data, f)

    # Build with MINIMAL
    aura_relationship_atlas.main(["build", "--profile", "MINIMAL"])
    with (temp_repo / ".aura" / "RELATIONSHIP_ATLAS.json").open("r") as f:
        minimal_data = json.load(f)
    minimal_count = len(minimal_data["assessments"])

    # Build with STANDARD
    aura_relationship_atlas.main(["build", "--profile", "STANDARD"])
    with (temp_repo / ".aura" / "RELATIONSHIP_ATLAS.json").open("r") as f:
        standard_data = json.load(f)
    standard_count = len(standard_data["assessments"])

    assert minimal_count < standard_count, \
        f"MINIMAL ({minimal_count}) should have fewer assessments than STANDARD ({standard_count})"


def test_delta_receipt_generated_on_rebuild(temp_repo: Path) -> None:
    """Building twice should generate a delta receipt on the second build."""
    snapshot1 = build_relationship_atlas(repo_root=temp_repo)

    # Modify index to add a new relation
    idx_file = temp_repo / ".aura" / "RELATIONAL_INDEX.json"
    with idx_file.open("r") as f:
        data = json.load(f)
    data["relations"].append({
        "schema_version": "AURA_TYPED_RELATION_V1",
        "relation_id": "rel_delta_test_new",
        "relation_type": "TESTS",
        "source_participant_id": "relp_000000000000000000000003",
        "target_participant_id": "relp_000000000000000000000001",
        "truth_class": "EXACT_TEST",
        "evidence_refs": ["delta_test_evidence"],
        "metadata": {}
    })
    with idx_file.open("w") as f:
        json.dump(data, f)

    snapshot2 = build_relationship_atlas(repo_root=temp_repo)

    # Delta receipt should have been written
    delta_path = temp_repo / ".aura" / "RELATIONSHIP_ATLAS_DELTA.json"
    assert delta_path.exists(), "Delta receipt should be generated on second build"
    with delta_path.open("r") as f:
        delta_data = json.load(f)
    assert delta_data["previous_snapshot_digest"] == snapshot1.snapshot_digest
    assert delta_data["current_snapshot_digest"] == snapshot2.snapshot_digest


def test_snapshot_from_dict_roundtrip(temp_repo: Path) -> None:
    """_snapshot_from_dict should reconstruct a snapshot that matches the original."""
    snapshot = build_relationship_atlas(repo_root=temp_repo)
    reconstructed = _snapshot_from_dict(snapshot.to_dict())
    assert reconstructed.snapshot_digest == snapshot.snapshot_digest
    assert reconstructed.snapshot_version == snapshot.snapshot_version
    assert len(reconstructed.assessments) == len(snapshot.assessments)
    assert len(reconstructed.prohibitions) == len(snapshot.prohibitions)


def test_schema_round_trip_assessment(temp_repo: Path) -> None:
    """Assessment should survive JSON serialization round-trip."""
    snapshot = build_relationship_atlas(repo_root=temp_repo)
    for a in snapshot.assessments:
        d = a.to_dict()
        # Verify all enum values are serialized as strings
        assert isinstance(d["structural_status"], str)
        assert isinstance(d["semantic_relationship"], str)
        assert isinstance(d["wiring_disposition"], str)
        assert isinstance(d["readiness"], str)
        assert isinstance(d["lifecycle"], str)
        assert isinstance(d["proof_status"], str)
        # Verify patch_authority is always false-safe
        assert d["patch_authority"] == "exact_source_spans_and_hashes_only"
        assert d["vsa_patch_authority"] is False


def test_motif_registry_integrity() -> None:
    """BUILTIN_MOTIFS should have consistent structure across all motifs."""
    for motif_id, spec in BUILTIN_MOTIFS.items():
        assert "motif_type" in spec
        assert "required_roles" in spec
        assert "expected_capability" in spec
        assert "risk_class" in spec
        assert isinstance(spec["required_roles"], list)
        assert len(spec["required_roles"]) > 0
        # Verify no leading/trailing whitespace in role names
        for role in spec["required_roles"]:
            assert role == role.strip(), f"Motif {motif_id} has whitespace in role '{role}'"


def test_find_candidate_wirings_excludes_prohibited(temp_repo: Path) -> None:
    """find_candidate_wirings should not return prohibited assessments."""
    idx_file = temp_repo / ".aura" / "RELATIONAL_INDEX.json"
    with idx_file.open("r") as f:
        data = json.load(f)
    # Add a prohibited relation
    data["relations"].append({
        "schema_version": "AURA_TYPED_RELATION_V1",
        "relation_id": "rel_prohibited_test_candidates",
        "relation_type": "REQUIRES_AUTHORITY",
        "source_participant_id": "relp_000000000000000000000001",
        "target_participant_id": "relp_000000000000000000000002",
        "truth_class": "ADVISORY_AFFINITY",
        "evidence_refs": ["affinity_test"],
        "metadata": {}
    })
    with idx_file.open("w") as f:
        json.dump(data, f)

    snapshot = build_relationship_atlas(repo_root=temp_repo)
    candidates = find_candidate_wirings(snapshot)
    for c in candidates:
        assert c.wiring_disposition != WiringDisposition.PROHIBITED, \
            "Prohibited assessment should not appear in candidate wirings"
        assert c.structural_status != StructuralStatus.EXACTLY_WIRED, \
            "Exactly wired assessment should not appear in candidate wirings"


def test_all_seven_builtin_prohibitions_present() -> None:
    """All seven builtin prohibition patterns from the blueprint should be registered."""
    patterns = {p.pattern for p in BUILTIN_PROHIBITIONS}
    expected = {
        "affinity_mutation_block",
        "self_verification_block",
        "agent_self_upgrade_block",
        "circular_authorization_block",
        "ephemeral_lease_leak_block",
        "research_production_coupling_block",
        "cross_arena_coupling_block",
    }
    assert patterns == expected, f"Missing prohibitions: {expected - patterns}"


def test_atlas_snapshot_digest_stable(temp_repo: Path) -> None:
    """Building from the same index twice should produce identical snapshot digests."""
    s1 = build_relationship_atlas(repo_root=temp_repo)
    s2 = build_relationship_atlas(repo_root=temp_repo)
    assert s1.snapshot_digest == s2.snapshot_digest, "Snapshot digest should be deterministic"


def test_atlas_boundary_includes_generated_paths(temp_repo: Path) -> None:
    """Atlas boundary should list all generated paths for self-exclusion."""
    snapshot = build_relationship_atlas(repo_root=temp_repo)
    excluded = snapshot.boundary.get("excluded_generated_paths", [])
    assert ".aura/RELATIONSHIP_ATLAS.json" in excluded
    assert ".aura/RELATIONSHIP_ATLAS_RECEIPT.json" in excluded
    assert ".aura/RELATIONSHIP_ATLAS.md" in excluded

