from __future__ import annotations

import base64
import copy
from io import BytesIO
from typing import Any
from urllib import error, request

import pytest

from aura_agent_arena_github_bridge import (
    GITHUB_PUBLICATION_VERSION,
    GitHubPublicationError,
    GitHubPublishingAuraAgentArenaBridge,
    GitHubRestTransport,
    _MAX_BASE64_CHARS,
    _MAX_UTF8_CHARS,
    _NoRedirectHandler,
    _fresh_branch_recovery_evidence,
    _utf8_byte_count,
    compile_merge_connector_packet,
    compile_publication_contract,
    execute_publication_contract,
)


REPOSITORY = "dallascourchene-commits/AuraOS"
BASE_SHA = "1" * 40
PARENT_SHA = "2" * 40
COMMIT_SHA = "7" * 40
BRANCH = "feature/atomic-publication-test"


def _request(**overrides: Any) -> dict[str, Any]:
    payload = {
        "repository_full_name": REPOSITORY,
        "publication_mode": "create",
        "base_branch": "main",
        "head_branch": BRANCH,
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
            {"path": "obsolete.py", "operation": "delete"},
        ],
    }
    payload.update(overrides)
    return payload


def _repo_mapping() -> dict[str, str]:
    return {"full_name": REPOSITORY}


def _pr_payload(
    *,
    number: int = 170,
    head_repo: str = REPOSITORY,
    head_sha: str = PARENT_SHA,
) -> dict[str, Any]:
    return {
        "number": number,
        "html_url": f"https://github.com/{REPOSITORY}/pull/{number}",
        "state": "open",
        "merged": False,
        "head": {
            "ref": BRANCH,
            "sha": head_sha,
            "repo": {"full_name": head_repo},
        },
        "base": {
            "ref": "main",
            "repo": _repo_mapping(),
        },
    }


class FakeTransport:
    def __init__(
        self,
        *,
        mode: str = "create",
        graphql_error: bool = False,
        graphql_advance_then_error: bool = False,
        pr_error: bool = False,
        head_repo: str = REPOSITORY,
    ) -> None:
        self.mode = mode
        self.graphql_error = graphql_error
        self.graphql_advance_then_error = graphql_advance_then_error
        self.pr_error = pr_error
        self.head_repo = head_repo
        self.calls: list[tuple[str, str, dict[str, Any] | None, bool]] = []
        self.graphql_calls: list[tuple[str, dict[str, Any]]] = []
        self.branch_sha: str | None = None if mode == "create" else PARENT_SHA

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        allow_404: bool = False,
    ) -> Any:
        self.calls.append((method, path, copy.deepcopy(payload), allow_404))
        if method == "GET" and path.endswith("/git/ref/heads/main"):
            return {"object": {"sha": BASE_SHA}}
        if method == "GET" and path.endswith(f"/git/ref/heads/{BRANCH}"):
            if self.branch_sha is None:
                assert allow_404 is True
                return None
            return {"object": {"sha": self.branch_sha}}
        if method == "GET" and "/pulls?" in path:
            return []
        if method == "GET" and path.endswith("/pulls/170"):
            return _pr_payload(
                head_repo=self.head_repo,
                head_sha=self.branch_sha or PARENT_SHA,
            )
        if method == "POST" and path.endswith("/git/refs"):
            assert payload == {
                "ref": f"refs/heads/{BRANCH}",
                "sha": BASE_SHA,
            }
            self.branch_sha = BASE_SHA
            return {}
        if method == "POST" and path.endswith("/pulls"):
            if self.pr_error:
                raise GitHubPublicationError("PR create rejected")
            assert payload is not None
            assert payload["head"] == BRANCH
            assert payload["base"] == "main"
            return _pr_payload(head_sha=COMMIT_SHA)
        if method == "DELETE" and path.endswith(
            f"/git/refs/heads/{BRANCH}"
        ):
            self.branch_sha = None
            return {}
        raise AssertionError(f"unexpected request: {method} {path} {payload}")

    def graphql(
        self,
        query: str,
        variables: dict[str, Any],
    ) -> dict[str, Any]:
        self.graphql_calls.append((query, copy.deepcopy(variables)))
        if self.graphql_error:
            raise GitHubPublicationError("expectedHeadOid mismatch")
        if self.graphql_advance_then_error:
            self.branch_sha = COMMIT_SHA
            raise GitHubPublicationError("response lost after mutation")
        expected = variables["input"]["expectedHeadOid"]
        assert self.branch_sha == expected
        self.branch_sha = COMMIT_SHA
        return {
            "createCommitOnBranch": {
                "commit": {
                    "oid": COMMIT_SHA,
                    "url": f"https://github.com/{REPOSITORY}/commit/{COMMIT_SHA}",
                }
            }
        }


def test_contract_is_deterministic_and_sorts_changes() -> None:
    first = compile_publication_contract(_request())
    reversed_request = _request()
    reversed_request["changes"] = list(
        reversed(reversed_request["changes"])
    )
    second = compile_publication_contract(reversed_request)

    assert first["contract_id"] == second["contract_id"]
    assert [item["path"] for item in first["changes"]] == [
        "alpha.py",
        "obsolete.py",
        "zeta.py",
    ]
    assert first["compare_and_swap"] is True
    assert first["transport"] == "github_graphql_create_commit_on_branch"
    assert first["merge_authority"] is False


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
def test_contract_rejects_temporary_or_unsafe_paths(path: str) -> None:
    with pytest.raises(GitHubPublicationError):
        compile_publication_contract(
            _request(changes=[{"path": path, "content": "x"}])
        )


def test_contract_rejects_unsupported_executable_mode() -> None:
    with pytest.raises(GitHubPublicationError, match="100644 only"):
        compile_publication_contract(
            _request(
                changes=[
                    {
                        "path": "tool.py",
                        "mode": "100755",
                        "content": "print('x')",
                    }
                ]
            )
        )


def test_delete_rejects_schema_forbidden_content_and_encoding() -> None:
    for forbidden in (
        {"content": ""},
        {"encoding": "utf-8"},
        {"content": "", "encoding": "base64"},
    ):
        with pytest.raises(GitHubPublicationError, match="forbidden keys"):
            compile_publication_contract(
                _request(
                    changes=[
                        {
                            "path": "obsolete.py",
                            "operation": "delete",
                            **forbidden,
                        }
                    ]
                )
            )


def test_bounds_apply_before_large_utf8_or_base64_conversion() -> None:
    with pytest.raises(GitHubPublicationError, match="input characters"):
        compile_publication_contract(
            _request(
                changes=[
                    {
                        "path": "huge.txt",
                        "content": "x" * (_MAX_UTF8_CHARS + 1),
                    }
                ]
            )
        )
    with pytest.raises(GitHubPublicationError, match="encoded characters"):
        compile_publication_contract(
            _request(
                changes=[
                    {
                        "path": "huge.bin",
                        "encoding": "base64",
                        "content": "A" * (_MAX_BASE64_CHARS + 1),
                    }
                ]
            )
        )


def test_multibyte_utf8_is_bounded_before_encoding() -> None:
    content = "😀" * ((_MAX_UTF8_CHARS // 4) + 1)
    assert len(content) < _MAX_UTF8_CHARS
    with pytest.raises(GitHubPublicationError, match="decoded bytes"):
        compile_publication_contract(
            _request(changes=[{"path": "emoji.txt", "content": content}])
        )


def test_utf8_byte_counter_rejects_surrogates() -> None:
    with pytest.raises(GitHubPublicationError, match="surrogate"):
        _utf8_byte_count("\ud800")


def test_temporary_transport_escape_hatch_is_rejected() -> None:
    with pytest.raises(GitHubPublicationError, match="unknown keys"):
        compile_publication_contract(
            _request(
                allow_temporary_transport=True,
                changes=[
                    {
                        "path": ".github/workflows/materialize-temp.yml",
                        "content": "name: forbidden\n",
                    }
                ],
            )
        )


def test_create_uses_graphql_cas_refname_and_base64() -> None:
    contract = compile_publication_contract(_request())
    transport = FakeTransport()

    receipt = execute_publication_contract(contract, transport=transport)

    assert receipt["ok"] is True
    assert receipt["commit_sha"] == COMMIT_SHA
    assert receipt["compare_and_swap"] is True
    assert len(transport.graphql_calls) == 1
    query, variables = transport.graphql_calls[0]
    assert "createCommitOnBranch" in query
    input_payload = variables["input"]
    assert input_payload["branch"] == {
        "repositoryNameWithOwner": REPOSITORY,
        "refName": BRANCH,
    }
    assert input_payload["expectedHeadOid"] == BASE_SHA
    additions = input_payload["fileChanges"]["additions"]
    assert [item["path"] for item in additions] == [
        "alpha.py",
        "zeta.py",
    ]
    assert base64.b64decode(additions[0]["contents"]).decode() == "print('a')\n"
    assert input_payload["fileChanges"]["deletions"] == [
        {"path": "obsolete.py"}
    ]


def test_caller_base64_is_retained_in_graphql_variables() -> None:
    encoded = base64.b64encode(b"\x00\x01payload").decode("ascii")
    contract = compile_publication_contract(
        _request(
            changes=[
                {
                    "path": "payload.bin",
                    "encoding": "base64",
                    "content": encoded,
                }
            ]
        )
    )
    transport = FakeTransport()
    execute_publication_contract(contract, transport=transport)
    additions = transport.graphql_calls[0][1]["input"]["fileChanges"][
        "additions"
    ]
    assert additions == [{"path": "payload.bin", "contents": encoded}]


def test_create_returns_recovery_evidence_when_graphql_cas_fails() -> None:
    contract = compile_publication_contract(_request())
    transport = FakeTransport(graphql_error=True)

    with pytest.raises(
        GitHubPublicationError,
        match='manual_cleanup_required_no_cas_delete',
    ):
        execute_publication_contract(contract, transport=transport)

    assert transport.branch_sha == BASE_SHA
    assert not any(method == "DELETE" for method, *_ in transport.calls)


def test_graphql_advanced_then_failed_reports_observed_commit() -> None:
    contract = compile_publication_contract(_request())
    transport = FakeTransport(graphql_advance_then_error=True)

    with pytest.raises(GitHubPublicationError) as error_info:
        execute_publication_contract(contract, transport=transport)

    message = str(error_info.value)
    assert "outcome ambiguous" in message
    assert COMMIT_SHA in message
    assert "ref_moved_manual_investigation_required" in message
    assert transport.branch_sha == COMMIT_SHA
    assert not any(method == "DELETE"" for method, *_ in transport.calls)


def test_create_returns_recovery_evidence_when_pr_creation_fails() -> None:
    contract = compile_publication_contract(_request())
    transport = FakeTransport(pr_error=True)

    with pytest.raises(
        GitHubPublicationError,
        match='manual_cleanup_required_no_cas_delete',
    ):
        execute_publication_contract(contract, transport=transport)

    assert transport.branch_sha == COMMIT_SHA
    assert not any(method == "DELETE" for method, *_ in transport.calls)


def test_recovery_never_deletes_a_moved_branch() -> None:
    transport = FakeTransport()
    transport.branch_sha = COMMIT_SHA

    evidence = _fresh_branch_recovery_evidence(
        transport,
        repository=REPOSITORY,
        branch=BRANCH,
        expected_sha=BASE_SHA,
    )

    assert evidence["recovery_required"] is True
    assert evidence["safe_manual_delete"] is False
    assert evidence["observed_sha"] == COMMIT_SHA
    assert evidence["detail"] == "ref_moved_manual_investigation_required"
    assert not any(method == "DELETE" for method, *_ in transport.calls)


def test_update_rejects_fork_pr_before_graphql() -> None:
    contract = compile_publication_contract(
        _request(
            publication_mode="update",
            expected_parent_sha=PARENT_SHA,
            pr_number=170,
        )
    )
    transport = FakeTransport(
        mode="update",
        head_repo="someone/AuraOS-fork",
    )

    with pytest.raises(GitHubPublicationError, match="same-repository"):
        execute_publication_contract(contract, transport=transport)

    assert transport.graphql_calls == []


def test_update_uses_cas_and_never_patches_pr_metadata() -> None:
    contract = compile_publication_contract(
        _request(
            publication_mode="update",
            expected_parent_sha=PARENT_SHA,
            pr_number=170,
        )
    )
    transport = FakeTransport(mode="update")

    receipt = execute_publication_contract(contract, transport=transport)

    assert receipt["pr_number"] == 170
    assert transport.graphql_calls[0][1]["input"][
        "expectedHeadOid"
    ] == PARENT_SHA
    assert not any(
        method == "PATCH" and "/pulls/" in path
        for method, path, _, _ in transport.calls
    )
    assert not any(
        method == "PATCH" and "/git/refs/" in path
        for method, path, _, _ in transport.calls
    )


def test_update_cas_rejection_does_not_move_branch() -> None:
    contract = compile_publication_contract(
        _request(
            publication_mode="update",
            expected_parent_sha=PARENT_SHA,
            pr_number=170,
        )
    )
    transport = FakeTransport(mode="update", graphql_error=True)

    with pytest.raises(GitHubPublicationError, match="expectedHeadOid"):
        execute_publication_contract(contract, transport=transport)

    assert transport.branch_sha == PARENT_SHA


def test_contract_tampering_is_rejected() -> None:
    contract = compile_publication_contract(_request())
    tampered = copy.deepcopy(contract)
    tampered["pr_title"] = "Changed"
    with pytest.raises(GitHubPublicationError, match="identity mismatch"):
        execute_publication_contract(tampered, transport=FakeTransport())


def test_no_redirect_handler_refuses_redirects() -> None:
    handler = _NoRedirectHandler()
    req = request.Request(
        "https://api.github.com/graphql",
        headers={"Authorization": "Bearer secret"},
    )
    assert handler.redirect_request(
        req,
        None,
        302,
        "Found",
        {},
        "https://attacker.example/token",
    ) is None


class _RedirectingOpener:
    def __init__(self) -> None:
        self.calls = 0

    def open(self, req: request.Request, timeout: int) -> Any:
        del timeout
        self.calls += 1
        raise error.HTTPError(
            req.full_url,
            302,
            "Found",
            {"Location": "https://attacker.example/token"},
            BytesIO(b"redirect refused"),
        )


def test_transport_rejects_injected_opener_argument() -> None:
    with pytest.raises(TypeError, match="opener"):
        GitHubRestTransport(  # type: ignore[call-arg]
            token="secret",
            opener=_RedirectingOpener(),
        )


def test_transport_does_not_follow_redirect(monkeypatch: pytest.MonkeyPatch) -> None:
    opener = _RedirectingOpener()
    handlers: list[tuple[Any, ...]] = []

    def fake_build_opener(*args: Any) -> _RedirectingOpener:
        handlers.append(args)
        return opener

    monkeypatch.setattr(request, "build_opener", fake_build_opener)
    transport = GitHubRestTransport(token="secret")
    assert len(handlers) == 1
    assert any(isinstance(item, _NoRedirectHandler) for item in handlers[0])
    with pytest.raises(GitHubPublicationError, match="HTTP 302"):
        transport.graphql("query { viewer { login } }", {})
    assert opener.calls == 1


class _BinaryResponse:
    def __enter__(self) -> "_BinaryResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def geturl(self) -> str:
        return "https://api.github.com/graphql"

    def read(self, limit: int) -> bytes:
        del limit
        return b"\xff\xfe"


class _BinaryOpener:
    def open(self, req: request.Request, timeout: int) -> _BinaryResponse:
        del req, timeout
        return _BinaryResponse()


def test_transport_converts_non_utf8_response_to_publication_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        request,
        "build_opener",
        lambda *handlers: _BinaryOpener(),
    )
    transport = GitHubRestTransport(token="secret")
    with pytest.raises(GitHubPublicationError, match="failed"):
        transport.graphql("query { viewer { login } }", {})


def test_merge_packet_is_evidence_only() -> None:
    packet = compile_merge_connector_packet(
        repository_full_name=REPOSITORY,
        pr_number=170,
        expected_head_sha=COMMIT_SHA,
        checks_passed=True,
        review_threads_resolved=True,
        codemap_regenerated=True,
    )
    assert packet["status"] == "READY_FOR_TRUSTED_HUMAN_AUTHORIZATION"
    assert packet["merge_authority"] is False
    assert packet["connector_tool"] is None
    assert packet["connector_arguments"] is None


def test_merge_runtime_rejects_caller_human_authority_key() -> None:
    bridge = object.__new__(GitHubPublishingAuraAgentArenaBridge)
    bridge._sessions = {}
    result = bridge.aura_github_prepare_merge(
        {
            "repository_full_name": REPOSITORY,
            "pr_number": 170,
            "expected_head_sha": COMMIT_SHA,
            "human_merge_authorized": True,
        }
    )
    assert result["ok"] is False
    assert "unknown keys" in str(result)


def test_bridge_hides_private_file_content_and_stores_contract() -> None:
    bridge = object.__new__(GitHubPublishingAuraAgentArenaBridge)
    bridge._sessions = {}
    result = bridge.aura_github_prepare_publication(_request())
    assert result["ok"] is True
    assert result["version"] == GITHUB_PUBLICATION_VERSION
    assert "_private" not in result
    stored = bridge._sessions["github_publications"][
        result["contract_id"]
    ]
    assert stored["_private"]["changes"][0].content is not None


def test_mcp_schema_matches_upsert_delete_runtime_and_installs_once() -> None:
    import aura_agent_arena_github_mcp as github_mcp

    github_mcp.install_github_tools()
    github_mcp.install_github_tools()
    names = [
        item["name"]
        for item in github_mcp._base_mcp.TOOL_DEFINITIONS
        if item["name"].startswith("aura_github_")
    ]
    assert all(names.count(name) == 1 for name in names)

    prepare = next(
        item
        for item in github_mcp._GITHUB_TOOL_DEFINITIONS
        if item["name"] == "aura_github_prepare_publication"
    )
    variants = prepare["inputSchema"]["properties"]["changes"][
        "items"
    ]["oneOf"]
    assert variants[0]["required"] == ["path", "content"]
    assert variants[1]["properties"]["operation"]["const"] == "delete"

    merge = next(
        item
        for item in github_mcp._GITHUB_TOOL_DEFINITIONS
        if item["name"] == "aura_github_prepare_merge"
    )
    assert "human_merge_authorized" not in merge["inputSchema"]["properties"]
    assert (
        "allow_temporary_transport"
        not in prepare["inputSchema"]["properties"]
    )
