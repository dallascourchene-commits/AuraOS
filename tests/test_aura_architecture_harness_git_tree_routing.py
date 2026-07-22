from __future__ import annotations

from dataclasses import replace

import pytest

from aura_architecture_harness_git_tree_routing import (
    AUTHORITY_CONTRACT,
    GitTreeBlobIntent,
    GitTreeRoutingError,
    VerifiedHeadBinding,
    build_git_tree_routing_record,
    proven_pr184_route_record,
)

HEAD = "7207c2bf6ab179d6af41ca4ed6b9f5adcce1b307"
TREE = "359a19f26aa3f4066c51263965709c8b026eae6c"


def binding() -> VerifiedHeadBinding:
    return VerifiedHeadBinding.from_fetch_commit(
        expected_head_sha=HEAD,
        commit_metadata={"sha": HEAD, "tree": {"sha": TREE}},
    )


def blob(path: str = "a.py") -> GitTreeBlobIntent:
    return GitTreeBlobIntent.from_bytes(path, b"print('ok')\n")


def test_head_binding_is_derived_from_one_commit_record() -> None:
    value = binding()
    assert value.commit_sha == HEAD
    assert value.tree_sha == TREE
    with pytest.raises(GitTreeRoutingError, match="does not match"):
        VerifiedHeadBinding.from_fetch_commit(
            expected_head_sha=HEAD,
            commit_metadata={"sha": "0" * 40, "tree": {"sha": TREE}},
        )
    with pytest.raises(GitTreeRoutingError, match="tree object"):
        replace(value, tree_sha=HEAD)


def test_record_binds_tree_parent_and_non_forced_ref_update() -> None:
    record = build_git_tree_routing_record(
        repository_full_name="dallascourchene-commits/AuraOS",
        pull_request_number=184,
        branch="work/example",
        head_binding=binding(),
        blobs=(blob(),),
        deletions=("tmp/chunk00",),
    )
    steps = {item["action"]: item for item in record["connector_sequence"]}
    assert steps["create_tree"]["base_tree_sha"] == TREE
    assert steps["create_commit"]["parent_sha"] == HEAD
    assert steps["update_ref"]["force"] is False
    assert record["authority"] == AUTHORITY_CONTRACT


def test_rejects_duplicate_overlap_and_unverified_binding() -> None:
    with pytest.raises(GitTreeRoutingError, match="VerifiedHeadBinding"):
        build_git_tree_routing_record(
            repository_full_name="dallascourchene-commits/AuraOS",
            pull_request_number=184,
            branch="work/example",
            head_binding={"commit_sha": HEAD, "tree_sha": TREE},  # type: ignore[arg-type]
            blobs=(blob(),),
        )
    with pytest.raises(GitTreeRoutingError, match="replaced and deleted"):
        build_git_tree_routing_record(
            repository_full_name="dallascourchene-commits/AuraOS",
            pull_request_number=184,
            branch="work/example",
            head_binding=binding(),
            blobs=(blob(),),
            deletions=("a.py",),
        )


def test_case_study_is_truthful_and_not_payload_cleanup_claim() -> None:
    record = proven_pr184_route_record()
    assert record["head_binding"] == {
        "commit_sha": HEAD,
        "tree_sha": TREE,
        "verification_action": "fetch_commit",
    }
    assert record["case_study"]["created_commit_sha"] == "ea9675ada226bae31fbd74e10dced81797aac1a8"
    assert record["case_study"]["scope"] == "manual review remediation publication, not G4 payload cleanup"
    assert all("pr184-g4-adapter/chunk" not in path for path in record["deletions"])
