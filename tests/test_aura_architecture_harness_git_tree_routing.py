from __future__ import annotations

from dataclasses import replace

import pytest

from aura_architecture_harness_git_tree_routing import (
    AUTHORITY_CONTRACT,
    GitTreeBlobIntent,
    GitTreeRoutingError,
    build_git_tree_routing_record,
    proven_pr184_route_record,
)


HEAD = "e67d6bdf96e6ba909846295ff9f5fd50d87697e4"


def _blob(path: str = "aura_example.py") -> GitTreeBlobIntent:
    return GitTreeBlobIntent.from_bytes(path, b"print('ok')\n")


def test_builds_deterministic_atomic_route_with_no_force_or_merge_authority() -> None:
    first = build_git_tree_routing_record(
        repository_full_name="dallascourchene-commits/AuraOS",
        pull_request_number=184,
        branch="work/construction-arena-real-asset-pack-g4-20260722",
        expected_head_sha=HEAD,
        blobs=(_blob("b.py"), _blob("a.py")),
        deletions=("tmp/z", "tmp/a"),
    )
    second = build_git_tree_routing_record(
        repository_full_name="dallascourchene-commits/AuraOS",
        pull_request_number=184,
        branch="work/construction-arena-real-asset-pack-g4-20260722",
        expected_head_sha=HEAD,
        blobs=(_blob("a.py"), _blob("b.py")),
        deletions=("tmp/a", "tmp/z"),
    )

    assert first == second
    assert [item["path"] for item in first["blob_intents"]] == ["a.py", "b.py"]
    assert first["deletions"] == ["tmp/a", "tmp/z"]
    assert [item["action"] for item in first["connector_sequence"]] == [
        "get_pr_info",
        "create_blob",
        "create_tree",
        "create_commit",
        "update_ref",
        "verify",
    ]
    assert next(item for item in first["connector_sequence"] if item["action"] == "update_ref")["force"] is False
    assert first["authority"] == AUTHORITY_CONTRACT
    assert first["authority"]["automatic_merge"] is False
    assert first["authority"]["human_review_required"] is True


def test_records_the_base_branch_pull_request_workflow_limitation() -> None:
    record = proven_pr184_route_record()
    discovery = record["workflow_discovery"]

    assert discovery["pull_request_definition_source"] == "base_branch"
    assert discovery["branch_new_pull_request_workflow_jobs_reliable"] is False
    assert discovery["preferred_fallback"] == "atomic_git_object_route"
    assert record["case_study"]["confirmed_base_tree_accepts_commit_sha"] is True


def test_rejects_unsafe_paths_duplicate_paths_and_head_drift() -> None:
    with pytest.raises(GitTreeRoutingError, match="unsafe repository path"):
        _blob("../escape.py")

    with pytest.raises(GitTreeRoutingError, match="lowercase 40-character"):
        build_git_tree_routing_record(
            repository_full_name="dallascourchene-commits/AuraOS",
            pull_request_number=184,
            branch="work/example",
            expected_head_sha="bad",
            blobs=(_blob(),),
        )

    with pytest.raises(GitTreeRoutingError, match="unique"):
        build_git_tree_routing_record(
            repository_full_name="dallascourchene-commits/AuraOS",
            pull_request_number=184,
            branch="work/example",
            expected_head_sha=HEAD,
            blobs=(_blob(), _blob()),
        )

    with pytest.raises(GitTreeRoutingError, match="replaced and deleted"):
        build_git_tree_routing_record(
            repository_full_name="dallascourchene-commits/AuraOS",
            pull_request_number=184,
            branch="work/example",
            expected_head_sha=HEAD,
            blobs=(_blob(),),
            deletions=("aura_example.py",),
        )


def test_blob_intent_binds_exact_bytes_and_regular_file_modes() -> None:
    regular = GitTreeBlobIntent.from_bytes("path/file.txt", b"abc")
    executable = GitTreeBlobIntent.from_bytes("scripts/tool.py", b"#!/usr/bin/env python3\n", executable=True)

    assert regular.byte_length == 3
    assert regular.content_sha256 == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert regular.mode == "100644"
    assert executable.mode == "100755"

    with pytest.raises(GitTreeRoutingError, match="regular-file"):
        replace(regular, mode="120000")
