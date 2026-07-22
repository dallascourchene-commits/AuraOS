from __future__ import annotations

from dataclasses import replace
import unicodedata

import pytest

from aura_architecture_harness_git_tree_routing import (
    AUTHORITY_CONTRACT,
    GitTreeBlobIntent,
    GitTreeRoutingError,
    PullRequestRouteBinding,
    build_git_tree_routing_record,
    pr184_atomic_publication_case_study,
)

HEAD = "d7bd9de40b787254164b4df3b546ecba30e4a25d"
TREE = "ce520012667d55f5829da372ae3a2f9aecf1d3fe"
HEAD_BRANCH = "work/construction-arena-real-asset-pack-g4-20260722"
BASE_BRANCH = "work/ai-safe-architecture-harness-20260722"


def binding() -> PullRequestRouteBinding:
    return PullRequestRouteBinding.from_connector_metadata(
        repository_full_name="dallascourchene-commits/AuraOS",
        pull_request_metadata={
            "number": 184,
            "state": "open",
            "merged": False,
            "head": HEAD_BRANCH,
            "base": BASE_BRANCH,
            "head_sha": HEAD,
        },
        commit_metadata={"sha": HEAD, "tree": {"sha": TREE}},
    )


def blob(path: str = "a.py") -> GitTreeBlobIntent:
    return GitTreeBlobIntent.from_bytes(path, b"print('ok')\n")


def test_binding_derives_pr_head_base_commit_and_tree_together() -> None:
    value = binding()
    assert value.head_branch == HEAD_BRANCH
    assert value.base_branch == BASE_BRANCH
    assert value.head_sha == HEAD
    assert value.tree_sha == TREE
    assert value.metadata_sources == ("get_pr_info", "fetch_commit")


def test_binding_rejects_base_target_and_commit_drift() -> None:
    with pytest.raises(GitTreeRoutingError, match="differ from base"):
        PullRequestRouteBinding.from_connector_metadata(
            repository_full_name="dallascourchene-commits/AuraOS",
            pull_request_metadata={
                "number": 184,
                "state": "open",
                "merged": False,
                "head": "main",
                "base": "main",
                "head_sha": HEAD,
            },
            commit_metadata={"sha": HEAD, "tree": {"sha": TREE}},
        )
    with pytest.raises(GitTreeRoutingError, match="does not match"):
        PullRequestRouteBinding.from_connector_metadata(
            repository_full_name="dallascourchene-commits/AuraOS",
            pull_request_metadata={
                "number": 184,
                "state": "open",
                "merged": False,
                "head": HEAD_BRANCH,
                "base": BASE_BRANCH,
                "head_sha": HEAD,
            },
            commit_metadata={"sha": "0" * 40, "tree": {"sha": TREE}},
        )


def test_directly_constructed_or_deserialized_binding_is_rejected() -> None:
    fabricated = object.__new__(PullRequestRouteBinding)
    for name, value in {
        "repository_full_name": "dallascourchene-commits/AuraOS",
        "pull_request_number": 184,
        "state": "open",
        "merged": False,
        "head_branch": HEAD_BRANCH,
        "base_branch": BASE_BRANCH,
        "head_sha": HEAD,
        "tree_sha": TREE,
        "metadata_sources": ("get_pr_info", "fetch_commit"),
        "_factory_token": object(),
    }.items():
        object.__setattr__(fabricated, name, value)
    with pytest.raises(GitTreeRoutingError, match="factory-created"):
        build_git_tree_routing_record(binding=fabricated, blobs=(blob(),))


def test_record_supports_deletion_only_and_revalidates_before_ref_update() -> None:
    record = build_git_tree_routing_record(
        binding=binding(),
        deletions=("unsafe/workflow.yml",),
    )
    assert record["blob_intents"] == []
    assert record["deletions"] == ["unsafe/workflow.yml"]
    assert record["executor_must_independently_refetch"] is True
    steps = record["connector_sequence"]
    assert [step["action"] for step in steps] == [
        "get_pr_info",
        "fetch_commit",
        "create_blob",
        "create_tree",
        "create_commit",
        "get_pr_info",
        "update_ref",
        "verify",
    ]
    assert steps[5]["purpose"].startswith("stale-head")
    assert steps[6]["branch"] == HEAD_BRANCH
    assert steps[6]["force"] is False
    assert record["authority"] == AUTHORITY_CONTRACT


def test_record_rejects_empty_route_overlap_and_portable_collisions() -> None:
    with pytest.raises(GitTreeRoutingError, match="at least one path"):
        build_git_tree_routing_record(binding=binding())
    with pytest.raises(GitTreeRoutingError, match="replaced and deleted"):
        build_git_tree_routing_record(
            binding=binding(), blobs=(blob("a"),), deletions=("a",)
        )
    with pytest.raises(GitTreeRoutingError, match="common filesystems"):
        build_git_tree_routing_record(
            binding=binding(), blobs=(blob("README"), blob("Readme"))
        )
    nfc = "docs/caf\u00e9.txt"
    nfd = unicodedata.normalize("NFD", nfc)
    with pytest.raises(GitTreeRoutingError, match="common filesystems"):
        build_git_tree_routing_record(
            binding=binding(), blobs=(blob(nfc), blob(nfd))
        )
    with pytest.raises(GitTreeRoutingError, match="ancestor"):
        build_git_tree_routing_record(
            binding=binding(), blobs=(blob("a"), blob("a/b"))
        )


def test_case_study_is_historical_not_synthetic_route_provenance() -> None:
    record = pr184_atomic_publication_case_study()
    case = record["case_study"]
    assert record["record_kind"] == "HISTORICAL_NON_REPLAYABLE_CASE_STUDY"
    assert record["replayable_route"] is False
    assert "route_digest" not in record
    assert "blob_intents" not in record
    assert case["actual_blob_intents_recorded"] is False
    assert case["route_digest_is_provenance_receipt"] is False
    assert case["created_commit_sha"] == "ea9675ada226bae31fbd74e10dced81797aac1a8"


def test_blob_intent_binds_exact_bytes_and_regular_modes() -> None:
    regular = GitTreeBlobIntent.from_bytes("path/file.txt", b"abc")
    executable = GitTreeBlobIntent.from_bytes(
        "scripts/tool.py", b"#!/usr/bin/env python3\n", executable=True
    )
    assert regular.byte_length == 3
    assert regular.mode == "100644"
    assert executable.mode == "100755"
    with pytest.raises(GitTreeRoutingError, match="regular-file"):
        replace(regular, mode="120000")
