"""Guarded GitHub publication for Aura's Agent Bridge.

Publication uses GitHub GraphQL ``createCommitOnBranch`` so commit creation and
branch advancement are one server-side compare-and-swap operation. Pull-request
merge remains outside MCP and requires a separately authenticated human action.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import base64
import hashlib
import json
import os
import re
from typing import Any
from urllib import error, parse, request

from aura_agent_arena_errors import make_error_packet
from aura_agent_arena_persistence_bridge import PersistentAuraAgentArenaBridge


GITHUB_PUBLICATION_VERSION = "AURA_AGENT_BRIDGE_GITHUB_PUBLICATION_V2"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

_MAX_FILES = 512
_MAX_FILE_BYTES = 4 * 1024 * 1024
_MAX_TOTAL_BYTES = 32 * 1024 * 1024
_MAX_RESPONSE_BYTES = 8 * 1024 * 1024
_MAX_UTF8_CHARS = _MAX_FILE_BYTES
_MAX_BASE64_CHARS = ((_MAX_FILE_BYTES + 2) // 3) * 4
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_BRANCH_RE = re.compile(
    r"^(?!/)(?!.*//)(?!.*\.\.)(?!.*[~^:?*\[\\])"
    r"[^\x00-\x20\x7f]+(?<!/)$"
)
_REQUEST_KEYS = frozenset(
    {
        "repository_full_name",
        "publication_mode",
        "base_branch",
        "head_branch",
        "expected_base_sha",
        "expected_parent_sha",
        "commit_message",
        "pr_title",
        "pr_body",
        "pr_number",
        "draft",
        "publish_authorized",
        "changes",
    }
)
_CHANGE_KEYS = frozenset({"path", "operation", "mode", "encoding", "content"})
_MERGE_REQUEST_KEYS = frozenset(
    {
        "repository_full_name",
        "pr_number",
        "expected_head_sha",
        "merge_method",
        "checks_passed",
        "review_threads_resolved",
        "codemap_regenerated",
    }
)
_IDENTITY_KEYS = (
    "version",
    "repository_full_name",
    "publication_mode",
    "base_branch",
    "head_branch",
    "expected_base_sha",
    "expected_parent_sha",
    "commit_message",
    "pr_title",
    "pr_body_sha256",
    "pr_number",
    "draft",
    "changes",
    "publish_authorized",
)

_CREATE_COMMIT_MUTATION = """
mutation AuraCreateCommitOnBranch($input: CreateCommitOnBranchInput!) {
  createCommitOnBranch(input: $input) {
    commit {
      oid
      url
    }
  }
}
""".strip()


class GitHubPublicationError(ValueError):
    """Fail-closed publication-contract or transport error."""


@dataclass(frozen=True)
class PublicationChange:
    path: str
    operation: str
    mode: str
    encoding: str
    content: str | None
    graphql_contents: str | None
    content_sha256: str
    byte_count: int

    def public_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "operation": self.operation,
            "mode": self.mode,
            "encoding": self.encoding,
            "content_sha256": self.content_sha256,
            "byte_count": self.byte_count,
        }


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _sha(value: Any, field: str) -> str:
    text = str(value or "").strip().lower()
    if not _SHA_RE.fullmatch(text):
        raise GitHubPublicationError(
            f"{field} must be a full lowercase 40-character Git SHA"
        )
    return text


def _repo(value: Any) -> str:
    text = str(value or "").strip()
    if not _REPO_RE.fullmatch(text):
        raise GitHubPublicationError("repository_full_name must be owner/name")
    return text


def _branch(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if (
        not text
        or len(text) > 240
        or not _BRANCH_RE.fullmatch(text)
        or text.startswith("-")
        or text.endswith(".lock")
    ):
        raise GitHubPublicationError(f"{field} is not a safe Git branch name")
    return text


def _path(value: Any) -> str:
    text = str(value or "").replace("\\", "/").strip()
    while text.startswith("./"):
        text = text[2:]
    parts = text.split("/")
    if (
        not text
        or text.startswith("/")
        or text.endswith("/")
        or len(text) > 1024
        or "\x00" in text
        or any(part in {"", ".", ".."} for part in parts)
        or parts[0] == ".git"
    ):
        raise GitHubPublicationError(f"unsafe repository path: {value!r}")
    return text


def _temporary_transport(path: str) -> bool:
    lower = path.lower()
    return (
        lower.startswith((".aura/tmp/", "scripts/.tmp/"))
        or lower.endswith(
            (
                "_temp.md",
                "-temp.yml",
                "-temp.yaml",
                "_temp.yml",
                "_temp.yaml",
            )
        )
        or (
            lower.startswith(".github/workflows/")
            and any(
                marker in lower
                for marker in ("materialize", "bootstrap", "publisher", "trigger")
            )
        )
    )


def _utf8_byte_count(content: str) -> int:
    """Count UTF-8 bytes without allocating the encoded payload."""

    total = 0
    for character in content:
        codepoint = ord(character)
        if codepoint <= 0x7F:
            total += 1
        elif codepoint <= 0x7FF:
            total += 2
        elif 0xD800 <= codepoint <= 0xDFFF:
            raise GitHubPublicationError("utf-8 content contains a surrogate")
        elif codepoint <= 0xFFFF:
            total += 3
        else:
            total += 4
        if total > _MAX_FILE_BYTES:
            raise GitHubPublicationError(
                f"utf-8 content exceeds {_MAX_FILE_BYTES} decoded bytes"
            )
    return total


def _decode_content(
    content: Any,
    encoding: str,
) -> tuple[str, str, bytes]:
    if not isinstance(content, str):
        raise GitHubPublicationError(f"{encoding} content must be a string")

    if encoding == "utf-8":
        if len(content) > _MAX_UTF8_CHARS:
            raise GitHubPublicationError(
                f"utf-8 content exceeds {_MAX_UTF8_CHARS} input characters"
            )
        expected_bytes = _utf8_byte_count(content)
        try:
            decoded = content.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise GitHubPublicationError("invalid utf-8 content") from exc
        if len(decoded) != expected_bytes:
            raise GitHubPublicationError("utf-8 byte-count validation failed")
        encoded = base64.b64encode(decoded).decode("ascii")
        return content, encoded, decoded

    if encoding == "base64":
        if len(content) > _MAX_BASE64_CHARS:
            raise GitHubPublicationError(
                f"base64 content exceeds {_MAX_BASE64_CHARS} encoded characters"
            )
        try:
            ascii_content = content.encode("ascii")
            decoded = base64.b64decode(ascii_content, validate=True)
        except (UnicodeEncodeError, ValueError) as exc:
            raise GitHubPublicationError("invalid RFC 4648 base64 content") from exc
        if len(decoded) > _MAX_FILE_BYTES:
            raise GitHubPublicationError(
                f"base64 content exceeds {_MAX_FILE_BYTES} decoded bytes"
            )
        return content, content, decoded

    raise GitHubPublicationError("encoding must be utf-8 or base64")


def _changes(raw: Any) -> list[PublicationChange]:
    if not isinstance(raw, Sequence) or isinstance(
        raw,
        (str, bytes, bytearray),
    ):
        raise GitHubPublicationError("changes must be an array")
    if not 1 <= len(raw) <= _MAX_FILES:
        raise GitHubPublicationError(
            f"changes must contain between 1 and {_MAX_FILES} entries"
        )

    result: list[PublicationChange] = []
    seen: set[str] = set()
    total = 0
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise GitHubPublicationError(f"changes[{index}] must be an object")
        unknown = sorted(set(item) - _CHANGE_KEYS)
        if unknown:
            raise GitHubPublicationError(
                f"changes[{index}] contains unknown keys: {', '.join(unknown)}"
            )

        path = _path(item.get("path"))
        if path in seen:
            raise GitHubPublicationError(f"duplicate publication path: {path}")
        seen.add(path)
        if _temporary_transport(path):
            raise GitHubPublicationError(
                f"temporary workflow/transport artifact rejected: {path}"
            )

        operation = str(item.get("operation", "upsert")).strip().lower()
        mode = str(item.get("mode", "100644")).strip()
        if operation not in {"upsert", "delete"}:
            raise GitHubPublicationError("operation must be upsert or delete")
        if mode != "100644":
            raise GitHubPublicationError(
                "GraphQL createCommitOnBranch supports regular-file mode 100644 only"
            )

        if operation == "delete":
            forbidden_delete_keys = sorted(
                key for key in ("content", "encoding") if key in item
            )
            if forbidden_delete_keys:
                raise GitHubPublicationError(
                    f"delete entry contains forbidden keys for {path}: "
                    f"{', '.join(forbidden_delete_keys)}"
                )
            result.append(
                PublicationChange(
                    path=path,
                    operation=operation,
                    mode=mode,
                    encoding="utf-8",
                    content=None,
                    graphql_contents=None,
                    content_sha256=hashlib.sha256(b"").hexdigest(),
                    byte_count=0,
                )
            )
            continue

        encoding = str(item.get("encoding", "utf-8")).strip().lower()
        content, graphql_contents, decoded = _decode_content(
            item.get("content"),
            encoding,
        )
        total += len(decoded)
        if total > _MAX_TOTAL_BYTES:
            raise GitHubPublicationError(
                f"publication exceeds {_MAX_TOTAL_BYTES} decoded bytes"
            )
        result.append(
            PublicationChange(
                path=path,
                operation=operation,
                mode=mode,
                encoding=encoding,
                content=content,
                graphql_contents=graphql_contents,
                content_sha256=hashlib.sha256(decoded).hexdigest(),
                byte_count=len(decoded),
            )
        )
    return sorted(result, key=lambda item: item.path)


def _identity(contract: Mapping[str, Any]) -> dict[str, Any]:
    missing = [key for key in _IDENTITY_KEYS if key not in contract]
    if missing:
        raise GitHubPublicationError(
            f"contract omitted identity fields: {', '.join(missing)}"
        )
    return {key: contract[key] for key in _IDENTITY_KEYS}


def _private_changes(contract: Mapping[str, Any]) -> list[PublicationChange]:
    private = contract.get("_private")
    public = contract.get("changes")
    if (
        not isinstance(private, Mapping)
        or not isinstance(public, Sequence)
        or isinstance(public, (str, bytes, bytearray))
    ):
        raise GitHubPublicationError("private/public change payload is unavailable")
    raw_private = private.get("changes")
    if not isinstance(raw_private, Sequence) or isinstance(
        raw_private,
        (str, bytes, bytearray),
    ):
        raise GitHubPublicationError("private changes are unavailable")
    if len(raw_private) != len(public):
        raise GitHubPublicationError("private/public change counts differ")

    validated: list[PublicationChange] = []
    for index, (private_item, public_item) in enumerate(
        zip(raw_private, public, strict=True)
    ):
        if not isinstance(private_item, PublicationChange):
            raise GitHubPublicationError(
                f"private change {index} has an invalid type"
            )
        if (
            not isinstance(public_item, Mapping)
            or private_item.public_dict() != dict(public_item)
        ):
            raise GitHubPublicationError(
                f"private/public change {index} differs"
            )
        if private_item.operation == "upsert":
            _, graphql_contents, decoded = _decode_content(
                private_item.content,
                private_item.encoding,
            )
            if (
                graphql_contents != private_item.graphql_contents
                or len(decoded) != private_item.byte_count
                or hashlib.sha256(decoded).hexdigest()
                != private_item.content_sha256
            ):
                raise GitHubPublicationError(
                    f"private content changed for {private_item.path}"
                )
        validated.append(private_item)
    return validated


def compile_publication_contract(
    request_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Compile a deterministic create/update publication contract."""

    if not isinstance(request_payload, Mapping):
        raise GitHubPublicationError("publication request must be an object")
    unknown = sorted(set(request_payload) - _REQUEST_KEYS)
    if unknown:
        raise GitHubPublicationError(
            f"publication request contains unknown keys: {', '.join(unknown)}"
        )

    repository = _repo(request_payload.get("repository_full_name"))
    publication_mode = str(
        request_payload.get("publication_mode", "create")
    ).strip().lower()
    if publication_mode not in {"create", "update"}:
        raise GitHubPublicationError(
            "publication_mode must be create or update"
        )
    base_branch = _branch(
        request_payload.get("base_branch", "main"),
        "base_branch",
    )
    head_branch = _branch(
        request_payload.get("head_branch"),
        "head_branch",
    )
    if head_branch == base_branch:
        raise GitHubPublicationError(
            "head_branch must differ from base_branch"
        )

    base_sha = _sha(
        request_payload.get("expected_base_sha"),
        "expected_base_sha",
    )
    parent_sha = _sha(
        request_payload.get("expected_parent_sha", base_sha),
        "expected_parent_sha",
    )
    if publication_mode == "create" and parent_sha != base_sha:
        raise GitHubPublicationError(
            "create mode requires expected_parent_sha == expected_base_sha"
        )

    raw_pr_number = request_payload.get("pr_number")
    if publication_mode == "update":
        if (
            not isinstance(raw_pr_number, int)
            or isinstance(raw_pr_number, bool)
            or raw_pr_number <= 0
        ):
            raise GitHubPublicationError(
                "update mode requires a positive pr_number"
            )
        pr_number: int | None = raw_pr_number
    else:
        if raw_pr_number is not None:
            raise GitHubPublicationError(
                "create mode must not include pr_number"
            )
        pr_number = None

    commit_message = str(
        request_payload.get("commit_message") or ""
    ).strip()
    pr_title = str(request_payload.get("pr_title") or "").strip()
    pr_body = str(request_payload.get("pr_body") or "")
    if (
        not commit_message
        or len(commit_message) > 4096
        or len(commit_message.encode("utf-8")) > 4096
    ):
        raise GitHubPublicationError(
            "commit_message is required and must be <= 4096 bytes"
        )
    if (
        not pr_title
        or len(pr_title) > 512
        or len(pr_title.encode("utf-8")) > 512
    ):
        raise GitHubPublicationError(
            "pr_title is required and must be <= 512 bytes"
        )
    if (
        len(pr_body) > 256 * 1024
        or len(pr_body.encode("utf-8")) > 256 * 1024
    ):
        raise GitHubPublicationError("pr_body exceeds 256 KiB")

    draft = request_payload.get("draft", True)
    if not isinstance(draft, bool):
        raise GitHubPublicationError("draft must be a boolean")
    normalized_changes = _changes(request_payload.get("changes"))

    public = {
        "version": GITHUB_PUBLICATION_VERSION,
        "repository_full_name": repository,
        "publication_mode": publication_mode,
        "base_branch": base_branch,
        "head_branch": head_branch,
        "expected_base_sha": base_sha,
        "expected_parent_sha": parent_sha,
        "commit_message": commit_message,
        "pr_title": pr_title,
        "pr_body_sha256": hashlib.sha256(
            pr_body.encode("utf-8")
        ).hexdigest(),
        "pr_number": pr_number,
        "draft": draft,
        "changes": [item.public_dict() for item in normalized_changes],
        "publish_authorized": (
            request_payload.get("publish_authorized") is True
        ),
    }
    contract_id = f"GHPUB-{_digest(_identity(public))[:24]}"
    return {
        **public,
        "contract_id": contract_id,
        "change_count": len(normalized_changes),
        "total_bytes": sum(
            item.byte_count for item in normalized_changes
        ),
        "branch_policy": (
            "fresh_snapshot_then_graphql_cas"
            if publication_mode == "create"
            else "exact_pr_head_graphql_cas"
        ),
        "transport": "github_graphql_create_commit_on_branch",
        "atomic_commit": True,
        "compare_and_swap": True,
        "force_ref_update": False,
        "temporary_workflow_transport": False,
        "automatic_merge": False,
        "merge_authority": False,
        "human_review_required": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "execution_status": (
            "AUTHORIZED"
            if public["publish_authorized"]
            else "PROPOSAL_ONLY"
        ),
        "_private": {
            "pr_body": pr_body,
            "changes": normalized_changes,
        },
    }


class _NoRedirectHandler(request.HTTPRedirectHandler):
    """Reject redirects before urllib can replay Authorization headers."""

    def redirect_request(
        self,
        req: request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Mapping[str, Any],
        newurl: str,
    ) -> None:
        del req, fp, code, msg, headers, newurl
        return None


class GitHubRestTransport:
    """Pinned GitHub REST/GraphQL transport with redirects disabled."""

    def __init__(
        self,
        *,
        token: str,
        timeout_seconds: int = 30,
    ) -> None:
        token_text = str(token or "").strip()
        if not token_text:
            raise GitHubPublicationError(
                "AURA_GITHUB_TOKEN is required for publication"
            )
        self._token = token_text
        self.timeout_seconds = max(
            1,
            min(int(timeout_seconds), 120),
        )
        # Never accept an injected opener: an opener with a default redirect
        # handler could replay the bearer token before the final-host check.
        self._opener = request.build_opener(_NoRedirectHandler())

    def _send(
        self,
        *,
        method: str,
        url: str,
        payload: Mapping[str, Any] | None,
        allow_404: bool = False,
    ) -> Any:
        parsed_url = parse.urlparse(url)
        if (
            parsed_url.scheme != "https"
            or parsed_url.hostname != "api.github.com"
            or parsed_url.port not in (None, 443)
        ):
            raise GitHubPublicationError(
                "GitHub request escaped the pinned API host"
            )

        data = None
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self._token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "AuraOS-Agent-Bridge-GitHub-Publisher",
        }
        if payload is not None:
            data = _canonical_json(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = request.Request(
            url,
            method=method,
            data=data,
            headers=headers,
        )
        try:
            with self._opener.open(
                req,
                timeout=self.timeout_seconds,
            ) as response:
                final_url = parse.urlparse(response.geturl())
                if (
                    final_url.scheme != "https"
                    or final_url.hostname != "api.github.com"
                    or final_url.port not in (None, 443)
                ):
                    raise GitHubPublicationError(
                        "GitHub response escaped the pinned API host"
                    )
                raw = response.read(_MAX_RESPONSE_BYTES + 1)
                if len(raw) > _MAX_RESPONSE_BYTES:
                    raise GitHubPublicationError(
                        "GitHub response exceeded 8 MiB"
                    )
                parsed = json.loads(raw.decode("utf-8")) if raw else {}
                if not isinstance(parsed, (dict, list)):
                    raise GitHubPublicationError(
                        "GitHub response must be an object or array"
                    )
                return parsed
        except error.HTTPError as exc:
            if allow_404 and exc.code == 404:
                return None
            detail = exc.read(16 * 1024).decode(
                "utf-8",
                errors="replace",
            )
            raise GitHubPublicationError(
                f"GitHub API {method} {parsed_url.path} failed with "
                f"HTTP {exc.code}: {detail[:2000]}"
            ) from exc
        except (
            error.URLError,
            TimeoutError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise GitHubPublicationError(
                f"GitHub API {method} {parsed_url.path} failed: {exc}"
            ) from exc

    def request(
        self,
        method: str,
        path: str,
        payload: Mapping[str, Any] | None = None,
        *,
        allow_404: bool = False,
    ) -> Any:
        if not path.startswith("/") or path.startswith("//"):
            raise GitHubPublicationError("GitHub REST path must be absolute")
        return self._send(
            method=method,
            url=f"https://api.github.com{path}",
            payload=payload,
            allow_404=allow_404,
        )

    def graphql(
        self,
        query: str,
        variables: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        response = self._send(
            method="POST",
            url="https://api.github.com/graphql",
            payload={"query": query, "variables": dict(variables)},
        )
        if not isinstance(response, Mapping):
            raise GitHubPublicationError(
                "GitHub GraphQL response must be an object"
            )
        errors = response.get("errors")
        if errors:
            raise GitHubPublicationError(
                f"GitHub GraphQL mutation failed: "
                f"{_canonical_json(errors)[:2000]}"
            )
        data = response.get("data")
        if not isinstance(data, Mapping):
            raise GitHubPublicationError(
                "GitHub GraphQL response omitted data"
            )
        return data


def _repo_path(repository: str) -> str:
    owner, name = repository.split("/", 1)
    return (
        f"/repos/{parse.quote(owner, safe='')}/"
        f"{parse.quote(name, safe='')}"
    )


def _ref_path(repository: str, branch: str, *, plural: bool = False) -> str:
    encoded = "/".join(
        parse.quote(part, safe="")
        for part in branch.split("/")
    )
    noun = "refs" if plural else "ref"
    return f"{_repo_path(repository)}/git/{noun}/heads/{encoded}"


def _ref_sha(payload: Mapping[str, Any], field: str) -> str:
    obj = payload.get("object")
    if not isinstance(obj, Mapping):
        raise GitHubPublicationError(f"{field} omitted object")
    return _sha(obj.get("sha"), field)


def _get_ref(
    transport: GitHubRestTransport,
    repository: str,
    branch: str,
    *,
    allow_404: bool = False,
) -> Any:
    return transport.request(
        "GET",
        _ref_path(repository, branch),
        allow_404=allow_404,
    )


def _repository_name(payload: Mapping[str, Any] | None) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    value = payload.get("full_name")
    return str(value) if isinstance(value, str) else None


def _assert_update_pr(
    transport: GitHubRestTransport,
    *,
    repository: str,
    pr_number: int,
    base_branch: str,
    head_branch: str,
    expected_head_sha: str,
) -> Mapping[str, Any]:
    pr = transport.request(
        "GET",
        f"{_repo_path(repository)}/pulls/{pr_number}",
    )
    if not isinstance(pr, Mapping):
        raise GitHubPublicationError(
            "update pull request does not exist"
        )
    head = pr.get("head")
    base = pr.get("base")
    if (
        not isinstance(head, Mapping)
        or not isinstance(base, Mapping)
        or head.get("ref") != head_branch
        or base.get("ref") != base_branch
        or head.get("sha") != expected_head_sha
        or _repository_name(head.get("repo")) != repository
        or _repository_name(base.get("repo")) != repository
        or pr.get("state") != "open"
        or pr.get("merged") is True
    ):
        raise GitHubPublicationError(
            "update PR no longer matches the exact same-repository open "
            "head/base contract"
        )
    return pr


def _commit_message_payload(message: str) -> dict[str, str]:
    headline, separator, body = message.partition("\n")
    result = {"headline": headline.strip()}
    if separator and body.strip():
        result["body"] = body.strip()
    return result


def _graphql_file_changes(
    changes: Sequence[PublicationChange],
) -> dict[str, list[dict[str, str]]]:
    additions = [
        {
            "path": change.path,
            "contents": str(change.graphql_contents),
        }
        for change in changes
        if change.operation == "upsert"
    ]
    deletions = [
        {"path": change.path}
        for change in changes
        if change.operation == "delete"
    ]
    return {
        "additions": additions,
        "deletions": deletions,
    }


def _create_commit_on_branch(
    transport: GitHubRestTransport,
    *,
    repository: str,
    branch: str,
    expected_head_sha: str,
    commit_message: str,
    changes: Sequence[PublicationChange],
) -> tuple[str, str]:
    variables = {
        "input": {
            "branch": {
                "repositoryNameWithOwner": repository,
                "refName": branch,
            },
            "message": _commit_message_payload(commit_message),
            "expectedHeadOid": expected_head_sha,
            "fileChanges": _graphql_file_changes(changes),
        }
    }
    data = transport.graphql(_CREATE_COMMIT_MUTATION, variables)
    mutation = data.get("createCommitOnBranch")
    commit = mutation.get("commit") if isinstance(mutation, Mapping) else None
    if not isinstance(commit, Mapping):
        raise GitHubPublicationError(
            "createCommitOnBranch response omitted commit"
        )
    return (
        _sha(commit.get("oid"), "commit_oid"),
        str(commit.get("url") or ""),
    )


def _fresh_branch_recovery_evidence(
    transport: GitHubRestTransport,
    *,
    repository: str,
    branch: str,
    expected_sha: str,
) -> dict[str, Any]:
    """Inspect a partial create without performing a racy ref deletion.

    GitHub's REST/GraphQL ref-deletion operations do not accept an expected OID.
    A GET followed by DELETE would therefore be a TOCTOU race that could remove a
    newer writer's commit. Return durable recovery evidence for a trusted operator
    instead of claiming that automatic cleanup is compare-and-swap guarded.
    """

    try:
        current = _get_ref(
            transport,
            repository,
            branch,
            allow_404=True,
        )
        if current is None:
            return {
                "automatic_delete_attempted": False,
                "recovery_required": False,
                "detail": "already_absent",
            }
        if not isinstance(current, Mapping):
            return {
                "automatic_delete_attempted": False,
                "recovery_required": True,
                "safe_manual_delete": False,
                "detail": "invalid_ref_evidence",
            }
        observed_sha = _ref_sha(current, "recovery_ref")
        return {
            "automatic_delete_attempted": False,
            "recovery_required": True,
            "safe_manual_delete": observed_sha == expected_sha,
            "expected_sha": expected_sha,
            "observed_sha": observed_sha,
            "detail": (
                "manual_cleanup_required_no_cas_delete"
                if observed_sha == expected_sha
                else "ref_moved_manual_investigation_required"
            ),
        }
    except GitHubPublicationError as exc:
        return {
            "automatic_delete_attempted": False,
            "recovery_required": True,
            "safe_manual_delete": False,
            "detail": f"recovery_inspection_failed:{exc}",
        }


def _raise_partial_failure(
    stage: str,
    primary: Exception,
    cleanup: Mapping[str, Any],
) -> None:
    raise GitHubPublicationError(
        f"{stage} failed: {primary}; cleanup={_canonical_json(cleanup)}"
    ) from primary


def execute_publication_contract(
    contract: Mapping[str, Any],
    *,
    transport: GitHubRestTransport,
) -> dict[str, Any]:
    """Publish one authorized GraphQL-CAS snapshot; never merge."""

    if contract.get("version") != GITHUB_PUBLICATION_VERSION:
        raise GitHubPublicationError(
            "unsupported publication contract version"
        )
    if contract.get("publish_authorized") is not True:
        raise GitHubPublicationError("publication is proposal-only")
    if (
        contract.get("automatic_merge") is not False
        or contract.get("merge_authority") is not False
    ):
        raise GitHubPublicationError(
            "publication contract cannot contain merge authority"
        )
    expected_id = f"GHPUB-{_digest(_identity(contract))[:24]}"
    if contract.get("contract_id") != expected_id:
        raise GitHubPublicationError(
            "publication contract identity mismatch"
        )

    repository = _repo(contract.get("repository_full_name"))
    publication_mode = str(contract.get("publication_mode") or "")
    base_branch = _branch(contract.get("base_branch"), "base_branch")
    head_branch = _branch(contract.get("head_branch"), "head_branch")
    base_sha = _sha(
        contract.get("expected_base_sha"),
        "expected_base_sha",
    )
    parent_sha = _sha(
        contract.get("expected_parent_sha"),
        "expected_parent_sha",
    )
    private = contract.get("_private")
    if not isinstance(private, Mapping):
        raise GitHubPublicationError(
            "private contract payload is unavailable"
        )
    pr_body = str(private.get("pr_body") or "")
    if (
        hashlib.sha256(pr_body.encode("utf-8")).hexdigest()
        != contract.get("pr_body_sha256")
    ):
        raise GitHubPublicationError(
            "contract PR body digest mismatch"
        )
    changes = _private_changes(contract)

    base_ref = _get_ref(transport, repository, base_branch)
    if (
        not isinstance(base_ref, Mapping)
        or _ref_sha(base_ref, "base_ref") != base_sha
    ):
        raise GitHubPublicationError(
            "base branch does not match expected_base_sha"
        )
    head_ref = _get_ref(
        transport,
        repository,
        head_branch,
        allow_404=True,
    )

    update_pr_number: int | None = None
    existing_pr: Mapping[str, Any] | None = None
    fresh_branch_created = False

    if publication_mode == "create":
        if head_ref is not None:
            raise GitHubPublicationError(
                "create mode requires a nonexistent head branch"
            )
        owner = repository.split("/", 1)[0]
        query = parse.urlencode(
            {
                "state": "all",
                "head": f"{owner}:{head_branch}",
                "per_page": 1,
            }
        )
        historical = transport.request(
            "GET",
            f"{_repo_path(repository)}/pulls?{query}",
        )
        if not isinstance(historical, list):
            raise GitHubPublicationError(
                "historical PR lookup returned an invalid response"
            )
        if historical:
            raise GitHubPublicationError(
                "branch name was used by a historical pull request"
            )
        transport.request(
            "POST",
            f"{_repo_path(repository)}/git/refs",
            {
                "ref": f"refs/heads/{head_branch}",
                "sha": base_sha,
            },
        )
        fresh_branch_created = True
        mutation_parent = base_sha
    elif publication_mode == "update":
        if not isinstance(head_ref, Mapping):
            raise GitHubPublicationError(
                "update mode requires an existing head branch"
            )
        if _ref_sha(head_ref, "head_ref") != parent_sha:
            raise GitHubPublicationError(
                "head branch moved before publication"
            )
        raw_pr_number = contract.get("pr_number")
        if (
            not isinstance(raw_pr_number, int)
            or isinstance(raw_pr_number, bool)
            or raw_pr_number <= 0
        ):
            raise GitHubPublicationError(
                "update contract omitted pr_number"
            )
        update_pr_number = raw_pr_number
        existing_pr = _assert_update_pr(
            transport,
            repository=repository,
            pr_number=update_pr_number,
            base_branch=base_branch,
            head_branch=head_branch,
            expected_head_sha=parent_sha,
        )
        mutation_parent = parent_sha
    else:
        raise GitHubPublicationError("unsupported publication mode")

    try:
        commit_sha, commit_url = _create_commit_on_branch(
            transport,
            repository=repository,
            branch=head_branch,
            expected_head_sha=mutation_parent,
            commit_message=str(contract.get("commit_message") or ""),
            changes=changes,
        )
    except GitHubPublicationError as exc:
        if fresh_branch_created:
            cleanup = _fresh_branch_recovery_evidence(
                transport,
                repository=repository,
                branch=head_branch,
                expected_sha=base_sha,
            )
            _raise_partial_failure(
                "createCommitOnBranch outcome ambiguous",
                exc,
                cleanup,
            )
        raise

    if publication_mode == "create":
        pr_payload = {
            "title": str(contract.get("pr_title") or ""),
            "body": pr_body,
            "base": base_branch,
            "head": head_branch,
            "draft": contract.get("draft") is True,
        }
        try:
            pr = transport.request(
                "POST",
                f"{_repo_path(repository)}/pulls",
                pr_payload,
            )
        except GitHubPublicationError as exc:
            cleanup = _fresh_branch_recovery_evidence(
                transport,
                repository=repository,
                branch=head_branch,
                expected_sha=commit_sha,
            )
            _raise_partial_failure("pull request creation", exc, cleanup)
        if not isinstance(pr, Mapping):
            cleanup = _fresh_branch_recovery_evidence(
                transport,
                repository=repository,
                branch=head_branch,
                expected_sha=commit_sha,
            )
            _raise_partial_failure(
                "pull request creation",
                GitHubPublicationError("pull request response missing"),
                cleanup,
            )
    else:
        pr = existing_pr
        if not isinstance(pr, Mapping):
            raise GitHubPublicationError(
                "bound update PR evidence is unavailable"
            )

    core = {
        "version": GITHUB_PUBLICATION_VERSION,
        "contract_id": contract["contract_id"],
        "repository_full_name": repository,
        "publication_mode": publication_mode,
        "base_branch": base_branch,
        "base_sha": base_sha,
        "parent_sha": mutation_parent,
        "head_branch": head_branch,
        "commit_sha": commit_sha,
        "commit_url": commit_url,
        "pr_number": int(pr.get("number") or update_pr_number or 0),
        "pr_url": str(pr.get("html_url") or ""),
        "transport": "github_graphql_create_commit_on_branch",
        "compare_and_swap": True,
        "force_ref_update": False,
        "atomic_commit": True,
        "automatic_merge": False,
        "merge_authority": False,
        "human_review_required": True,
    }
    return {
        "ok": True,
        **core,
        "receipt_digest": _digest(core),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def compile_merge_connector_packet(
    *,
    repository_full_name: str,
    pr_number: int,
    expected_head_sha: str,
    merge_method: str = "squash",
    checks_passed: bool = False,
    review_threads_resolved: bool = False,
    codemap_regenerated: bool = False,
) -> dict[str, Any]:
    """Prepare non-authoritative merge evidence for a trusted human boundary."""

    repository = _repo(repository_full_name)
    expected = _sha(expected_head_sha, "expected_head_sha")
    if (
        not isinstance(pr_number, int)
        or isinstance(pr_number, bool)
        or pr_number <= 0
    ):
        raise GitHubPublicationError(
            "pr_number must be a positive integer"
        )
    if merge_method not in {"merge", "squash", "rebase"}:
        raise GitHubPublicationError(
            "merge_method must be merge, squash, or rebase"
        )

    gates = {
        "checks_passed": checks_passed is True,
        "review_threads_resolved": review_threads_resolved is True,
        "codemap_regenerated": codemap_regenerated is True,
    }
    ready_for_human = all(gates.values())
    core = {
        "version": GITHUB_PUBLICATION_VERSION,
        "repository_full_name": repository,
        "pr_number": pr_number,
        "expected_head_sha": expected,
        "merge_method": merge_method,
        "gates": gates,
        "ready_for_trusted_human_authorization": ready_for_human,
        "automatic_merge": False,
        "merge_authority": False,
        "human_review_required": True,
    }
    return {
        **core,
        "packet_id": f"GHMERGE-{_digest(core)[:24]}",
        "connector_tool": None,
        "connector_arguments": None,
        "status": (
            "READY_FOR_TRUSTED_HUMAN_AUTHORIZATION"
            if ready_for_human
            else "BLOCKED"
        ),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


class GitHubPublishingAuraAgentArenaBridge(
    PersistentAuraAgentArenaBridge
):
    """Persistent Agent Bridge with guarded GitHub publication tools."""

    def aura_github_prepare_publication(
        self,
        request_payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        try:
            contract = compile_publication_contract(request_payload)
        except GitHubPublicationError as exc:
            return make_error_packet(
                "patch_outside_arena",
                str(exc),
                repair_hint="Repair the exact GitHub publication request.",
            )
        self._sessions.setdefault(
            "github_publications",
            {},
        )[contract["contract_id"]] = contract
        return {
            "ok": True,
            **{
                key: value
                for key, value in contract.items()
                if key != "_private"
            },
        }

    def aura_github_execute_publication(
        self,
        *,
        contract_id: str,
    ) -> dict[str, Any]:
        contracts = self._sessions.get(
            "github_publications",
            {},
        )
        contract = contracts.get(str(contract_id or ""))
        if not isinstance(contract, Mapping):
            return make_error_packet(
                "missing_grounding",
                "Unknown GitHub publication contract.",
                repair_hint=(
                    "Prepare the contract in this bridge process first."
                ),
            )
        try:
            return execute_publication_contract(
                contract,
                transport=GitHubRestTransport(
                    token=os.environ.get("AURA_GITHUB_TOKEN", "")
                ),
            )
        except GitHubPublicationError as exc:
            return make_error_packet(
                "test_failed",
                str(exc),
                repair_hint=(
                    "Refresh exact refs and recompile; do not retry blindly."
                ),
            )

    def aura_github_prepare_merge(
        self,
        request_payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        try:
            if not isinstance(request_payload, Mapping):
                raise GitHubPublicationError(
                    "merge evidence request must be an object"
                )
            unknown = sorted(set(request_payload) - _MERGE_REQUEST_KEYS)
            if unknown:
                raise GitHubPublicationError(
                    f"merge evidence request contains unknown keys: "
                    f"{', '.join(unknown)}"
                )
            packet = compile_merge_connector_packet(
                repository_full_name=str(
                    request_payload.get("repository_full_name") or ""
                ),
                pr_number=int(request_payload.get("pr_number") or 0),
                expected_head_sha=str(
                    request_payload.get("expected_head_sha") or ""
                ),
                merge_method=str(
                    request_payload.get("merge_method", "squash")
                ),
                checks_passed=(
                    request_payload.get("checks_passed") is True
                ),
                review_threads_resolved=(
                    request_payload.get("review_threads_resolved") is True
                ),
                codemap_regenerated=(
                    request_payload.get("codemap_regenerated") is True
                ),
            )
            return {"ok": True, **packet}
        except (
            GitHubPublicationError,
            TypeError,
            ValueError,
        ) as exc:
            return make_error_packet(
                "test_failed",
                str(exc),
                repair_hint=(
                    "Supply exact-head evidence; human merge authority "
                    "remains outside MCP."
                ),
            )

    @staticmethod
    def list_tools() -> list[dict[str, Any]]:
        return [
            *PersistentAuraAgentArenaBridge.list_tools(),
            {
                "name": "aura_github_prepare_publication",
                "description": (
                    "Compile an exact-head GraphQL-CAS branch/commit/PR contract."
                ),
                "required_inputs": [
                    "repository_full_name",
                    "head_branch",
                    "expected_base_sha",
                    "commit_message",
                    "pr_title",
                    "changes",
                ],
            },
            {
                "name": "aura_github_execute_publication",
                "description": (
                    "Execute one authorized createCommitOnBranch contract; "
                    "never merge."
                ),
                "required_inputs": ["contract_id"],
            },
            {
                "name": "aura_github_prepare_merge",
                "description": (
                    "Prepare non-authoritative exact-head merge evidence."
                ),
                "required_inputs": [
                    "repository_full_name",
                    "pr_number",
                    "expected_head_sha",
                ],
            },
        ]


def github_publication_status() -> dict[str, Any]:
    return {
        "ok": True,
        "version": GITHUB_PUBLICATION_VERSION,
        "transport": "github_graphql_create_commit_on_branch",
        "atomic_commit": True,
        "compare_and_swap": True,
        "temporary_workflow_transport": False,
        "automatic_merge": False,
        "merge_authority": False,
        "human_review_required": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


__all__ = [
    "GITHUB_PUBLICATION_VERSION",
    "GitHubPublicationError",
    "GitHubPublishingAuraAgentArenaBridge",
    "GitHubRestTransport",
    "PublicationChange",
    "compile_merge_connector_packet",
    "compile_publication_contract",
    "execute_publication_contract",
    "github_publication_status",
]
