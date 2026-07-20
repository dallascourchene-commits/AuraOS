from __future__ import annotations

import copy
from typing import Any

import pytest

from aura_agent_arena_github_bridge import (
    GITHUB_PUBLICATION_VERSION,
    GitHubPublicationError,
    GitHubPublishingAuraAgentArenaBridge,
    compile_merge_connector_packet,
    compile_publication_contract,
    execute_publication_contract,
)


BASE_SHA = "1" * 40
PARENT_SHA = "2" * 40
BASE_TREE_SHA = "3" * 40
BLOB_A_SHA = "4" * 40
BLOB_B_SHA = "5" * 40
TREE_SHA = "6" * 40
COMMIT_SHA = "7" * 40


def _request(**overrides: Any) -> dict[str, Any]:
    payload = {
        "repository_full_name": "dallascourchene-commits/AuraOS",
        "publication_mode": "create",
        "base_branch": "main",
        "head_branch": "feature/atomic-publication-test",
        "expected_base_sha": BASE_SHA,
        "expected_parent_sha": BASE_SHA,
        "commit_message": "feat: publish atomically",
        "pr_title": "Atomic publication",
        "pr_body": "Exact-head publication test.",
        "draft": True,
        "publish_authorized": True,
        "changes": [
            {"path": "zeta.py", "content": "print('z')\n"},
            {"path": "alpha.py", "content": "print('a')\n"},
        ],
    }
    payload.update(overrides)
    return payload


def test_contract_is_deterministic_and_sorts_changes() -> None:
    first = compile_publication_contract(_request())
    reversed_request = _request()
    reversed_request["changes"] = list(reversed(reversed_request["changes"]))
    second = compile_publication_contract(reversed_request)

    assert first["contract_id"] == second["contract_id"]
    assert [item["path"] for item in first["changes"]] == ["alpha.py", "zeta.py"]
    assert first["atomic_commit"] is True
    assert first["temporary_workflow_transport"] is False
    assert first["automatic_merge"] is False
    assert first["execution_status"] == "AUTHORIZED"


@pytest.mark.parametrize(
    "path",
    [
        ".aura/tmp/payload.bin",
        ".github/workflows/materialize-temp.yml",
        "docs/IMPLEMENTATION_TEMP.md",
        "../escape.py",
        "/absolute.py",
    ],
)
def test_contract_rejects_temporary_or_unsafe_transport_paths(path: str) -> None:
    request_payload = _request(changes=[{"path": path, "content": "x"}])
    with pytest.raises(GitHubPublicationError):
        compile_publication_contract(request_payload)


def test_contract_requires_fresh_exact_base_in_create_mode() -> None:
    with pytest.raises(GitHubPublicationError):
        compile_publication_contract(_request(expected_parent_sha=PARENT_SHA))


def test_contract_rejects_unknown_keys_and_string_boolean() -> None:
    with pytest.raises(GitHubPublicationError, match="unknown keys"):
        compile_publication_contract(_request(api_root="https://evil.example"))
    with pytest.raises(GitHubPublicationError, match="must be a boolean"):
        compile_publication_contract(_request(allow_temporary_transport="false"))


def test_update_mode_binds_pr_number_into_contract_identity() -> None:
    request_payload = _request(
        publication_mode="update",
        expected_parent_sha=PARENT_SHA,
        pr_number=170,
    )
    contract = compile_publication_contract(request_payload)
    assert contract["pr_number"] == 170
    assert contract["branch_policy"] == "exact_parent_fast_forward"

    tampered = copy.deepcopy(contract)
    tampered["pr_number"] = 171
    transport = FakeTransport()
    with pytest.raises(GitHubPublicationError, match="identity mismatch"):
        execute_publication_contract(tampered, transport=transport)


class FakeTransport:
    def __init__(self, *, base_moves: bool = False) -> None:
        self.calls: list[tuple[str, str, dict[str, Any] | None, bool]] = []
        self.base_reads = 0
        self.base_moves = base_moves
        self.blobs = iter([BLOB_A_SHA, BLOB_B_SHA])

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        allow_404: bool = False,
    ) -> dict[str, Any] | None:
        self.calls.append((method, path, copy.deepcopy(payload), allow_404))
        if method == "GET" and path.endswith("/git/ref/heads/main"):
            self.base_reads += 1
            sha = PARENT_SHA if self.base_moves and self.base_reads > 1 else BASE_SHA
            return {"object": {"sha": sha}}
        if method == "GET" and path.endswith(
            "/git/ref/heads/feature/atomic-publication-test"
        ):
            assert allow_404 is True
            return None
        if method == "GET" and "/pulls?" in path:
            return []
        if method == "GET" and path.endswith(f"/git/commits/{BASE_SHA}"):
            return {"tree": {"sha": BASE_TREE_SHA}}
        if method == "POST" and path.endswith("/git/blobs"):
            return {"sha": next(self.blobs)}
        if method == "POST" and path.endswith("/git/trees"):
            assert payload is not None
            assert payload["base_tree"] == BASE_TREE_SHA
            assert [item["path"] for item in payload["tree"]] == [
                "alpha.py",
                "zeta.py",
            ]
            return {"sha": TREE_SHA}
        if method == "POST" and path.endswith("/git/commits"):
            assert payload == {
                "message": "feat: publish atomically",
                "tree": TREE_SHA,
                "parents": [BASE_SHA],
            }
            return {"sha": COMMIT_SHA}
        if method == "POST" and path.endswith("/git/refs"):
            assert payload == {
                "ref": "refs/heads/feature/atomic-publication-test",
                "sha": COMMIT_SHA,
            }
            return {}
        if method == "POST" and path.endswith("/pulls"):
            assert payload is not None
            assert payload["head"] == "feature/atomic-publication-test"
            assert payload["base"] == "main"
            return {
                "number": 170,
                "html_url": "https://github.com/dallascourchene-commits/AuraOS/pull/170",
            }
        raise AssertionError(f"unexpected request: {method} {path} {payload}")


def test_execute_publication_uses_one_tree_and_one_commit() -> None:
    contract = compile_publication_contract(_request())
    transport = FakeTransport()

    receipt = execute_publication_contract(contract, transport=transport)

    assert receipt["ok"] is True
    assert receipt["commit_sha"] == COMMIT_SHA
    assert receipt["tree_sha"] == TREE_SHA
    assert receipt["pr_number"] == 170
    assert receipt["atomic_commit"] is True
    assert receipt["force_ref_update"] is False
    assert receipt["automatic_merge"] is False
    assert sum(
        1
        for method, path, _, _ in transport.calls
        if method == "POST" and path.endswith("/git/trees")
    ) == 1
    assert sum(
        1
        for method, path, _, _ in transport.calls
        if method == "POST" and path.endswith("/git/commits")
    ) == 1


def test_execute_fails_closed_if_base_moves_before_ref_creation() -> None:
    contract = compile_publication_contract(_request())
    transport = FakeTransport(base_moves=True)

    with pytest.raises(GitHubPublicationError, match="base branch moved"):
        execute_publication_contract(contract, transport=transport)

    assert not any(
        method == "POST" and path.endswith("/git/refs")
        for method, path, _, _ in transport.calls
    )
    assert not any(
        method == "POST" and path.endswith("/pulls")
        for method, path, _, _ in transport.calls
    )


def test_merge_packet_requires_every_explicit_gate() -> None:
    blocked = compile_merge_connector_packet(
        repository_full_name="dallascourchene-commits/AuraOS",
        pr_number=170,
        expected_head_sha=COMMIT_SHA,
        human_merge_authorized=True,
        checks_passed=True,
        review_threads_resolved=False,
        codemap_regenerated=True,
    )
    assert blocked["status"] == "BLOCKED"
    assert blocked["connector_arguments"] is None

    ready = compile_merge_connector_packet(
        repository_full_name="dallascourchene-commits/AuraOS",
        pr_number=170,
        expected_head_sha=COMMIT_SHA,
        human_merge_authorized=True,
        checks_passed=True,
        review_threads_resolved=True,
        codemap_regenerated=True,
    )
    assert ready["status"] == "READY_FOR_EXPLICIT_MERGE"
    assert ready["connector_arguments"]["expected_head_sha"] == COMMIT_SHA
    assert ready["connector_tool"] == "GitHub.merge_pull_request"


def test_bridge_hides_private_file_content_and_stores_contract() -> None:
    bridge = object.__new__(GitHubPublishingAuraAgentArenaBridge)
    bridge._sessions = {}

    result = bridge.aura_github_prepare_publication(_request())

    assert result["ok"] is True
    assert result["version"] == GITHUB_PUBLICATION_VERSION
    assert "_private" not in result
    contract_id = result["contract_id"]
    stored = bridge._sessions["github_publications"][contract_id]
    assert stored["_private"]["changes"][0].content is not None


def test_github_mcp_installs_tools_idempotently() -> None:
    import aura_agent_arena_github_mcp as github_mcp

    github_mcp.install_github_tools()
    github_mcp.install_github_tools()

    names = [
        item["name"]
        for item in github_mcp._base_mcp.TOOL_DEFINITIONS
        if item["name"].startswith("aura_github_")
    ]
    assert sorted(names) == [
        "aura_github_execute_publication",
        "aura_github_prepare_merge",
        "aura_github_prepare_publication",
    ]
    assert all(names.count(name) == 1 for name in names)
